#!/usr/bin/env python3

import json
import typing
import logging
import uuid

from call_next_func import post_collision_detector
from timestamp_for_logger import CustomFormatter
from tracer import TracerInitializer
from get_recent_trajectories import get_recent_trajectories
from json_encoder import JSONEncoder

# Set up Python logger. milliseconds are not supported by default
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S.%f'
)
logger = logging.getLogger(__name__)
for handler in logging.getLogger().handlers:  # Apply the custom formatter to the root logger
    handler.setFormatter(CustomFormatter(handler.formatter._fmt, handler.formatter.datefmt))

# Initialize the OpenTelemetry tracer
tracer = TracerInitializer("trigger").tracer

TTL = 100  # seconds

def fn(input: typing.Optional[str], headers: typing.Optional[typing.Dict[str, str]]) -> typing.Optional[str]:
    """
    input: gets a new trajectory. Invoked by the update function
    output: calls the risk-eval function with the recent trajectories from the db
    """
    with tracer.start_as_current_span('fn') as main_span:
        main_span.set_attribute("invoke_count", Counter.increment_count())
        main_span.set_attribute("input", input)
        logger.info(f'[trigger fn] invoke count: {str(Counter.get_count())}')
        # Parse the JSON string into a Python list of dictionaries
        with tracer.start_as_current_span('parse_input'):
            parsed_input = json.loads(input)
            logger.debug(f'[trigger fn] Parsed input: {parsed_input}')

            # data = parsed_input.get('data', []) # no data expected
            meta = parsed_input.get('meta', {})

        # Check the 'origin' in 'meta'
        origin = meta.get('origin', None)
        if origin is None:
            logger.error(f'[trigger fn] No origin key found in meta. dump: {meta}')
            main_span.set_attribute("error", True)
            main_span.set_attribute("error_details", "No origin key found in meta")
            return f'No origin key found in meta. dump: {meta}'

        # Check if 'origin' is 'self_report'
        if origin != 'self_report':
            logger.error(f'[trigger fn] Origin is not self_report. dump: {meta}')
            main_span.set_attribute("error", True)
            main_span.set_attribute("error_details", "Origin is not self_report")
            return f'Origin is not self_report. dump: {meta}'

        # Generate a unique request_id and add it to the meta dictionary
        with tracer.start_as_current_span('gen_req_uid') as gen_req_uid_span:
            request_id = str(uuid.uuid4())
            meta['request_id'] = request_id
            logger.info(f'[trigger fn] Generated request_id: {request_id}')
            gen_req_uid_span.set_attribute("request_id", request_id)

        # TODO: get the ttl from ENV
        # TODO: if db is slow, call it in parallel with previous code
        # Get recent trajectory from each uav (limited by ttl, in seconds)
        # includes the trajectory from the update (already in db)
        with tracer.start_as_current_span('get_recent_trajectories', attributes={"ttl": TTL}) as get_recent_trajectories_span:
            try:
                recent_trajectories = get_recent_trajectories(TTL)
            except Exception as e:
                logger.error(f'[trigger fn] Error in get_recent_trajectories: {e}')
                get_recent_trajectories_span.set_attribute("error", True)
                get_recent_trajectories_span.set_attribute("error_details", e)
                return f'Error in get_recent_trajectories: {e}'

        # Check if recent_trajectories is not empty, else call risk-eval function
        with tracer.start_as_current_span('post_risk_eval_if_any_traj') as post_risk_eval_if_any_traj_span:
            post_risk_eval_if_any_traj_span.set_attribute("recent_trajectories_size", len(recent_trajectories))
            if not recent_trajectories:
                logger.error(f'[trigger fn] No recent trajectories found')
                post_risk_eval_if_any_traj_span.set_attribute("error", True)
                post_risk_eval_if_any_traj_span.set_attribute("error_details", "No recent trajectories found")
                return f'No recent trajectories found'
            else:
                logger.info(
                    f'[trigger fn] Found {len(recent_trajectories)} trajectories for uav_ids: {[trajectory["uav_id"] for trajectory in recent_trajectories]}')
                # call risk-eval function
                with tracer.start_as_current_span('post_risk_eval') as post_risk_eval_span:
                    with tracer.start_as_current_span('json_encode_recent_trajectories'):
                        encoded_recent_trajectories = [JSONEncoder().default(trajectory) for trajectory in recent_trajectories]
                    try:
                        r = post_collision_detector(encoded_recent_trajectories, meta)
                        post_risk_eval_span.set_attribute("response_code", r.status_code)
                    except Exception as e:
                        logger.error(f'[trigger fn] Error in post_risk_eval: {e}')
                        post_risk_eval_span.set_attribute("error", True)
                        post_risk_eval_span.set_attribute("error_details", e)
                    return str(encoded_recent_trajectories)


class Counter:
    count = None

    @staticmethod
    def get_count():
        if Counter.count is None:  # memoize
            Counter.count = 0
        return Counter.count

    @staticmethod
    def increment_count():
        if Counter.count is None:
            Counter.count = 0
        Counter.count += 1
        return Counter.count
