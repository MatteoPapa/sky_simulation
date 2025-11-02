#!/usr/bin/env python3

import json
import typing
import logging

from call_next_func import post_mutate, post_release
from timestamp_for_logger import CustomFormatter
from tracer import TracerInitializer
from collision_detector import detect_collisions

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
tracer = TracerInitializer("collision-detector").tracer

# collision-detector.py
TIME_INTERVAL = 1
NUM_STEPS = 10
HORIZONTAL_SEPARATION = 0.20   # 200m
VERTICAL_SEPARATION   = 300    # metri


def fn(input: typing.Optional[str], headers: typing.Optional[typing.Dict[str, str]]) -> typing.Optional[str]:
    """
    input: A JSON string that represents a dictionary with trajectory set 'data' and 'meta' keys.
    output:  calls the mutate function if the collision detected, otherwise based on 'origin' metadata,
        either calls the Release function or does nothing
    """
    with tracer.start_as_current_span('fn') as main_span:
        main_span.set_attribute("invoke_count", Counter.increment_count())
        main_span.set_attribute("input", input)
        logger.info(f'[collision-detector fn] invoke count: {str(Counter.get_count())}')
        # Parse the JSON string into a Python list of dictionaries
        with tracer.start_as_current_span('parse_input'):
            parsed_input = json.loads(input)
            logger.debug(f'[collision-detector fn] Parsed input: {parsed_input}')

            data = parsed_input.get('data', [])
            meta = parsed_input.get('meta', {})

            # Check if 'origin' key exists in meta
            origin = meta.get('origin', None)
            if origin is None:
                logger.error(f'[collision-detector fn] No origin key found in meta')
                return 'No origin key found in meta'

        # Call collision detector function with the parsed input
        with tracer.start_as_current_span('find_collisions') as collision_span:
            collision_exists, flagged_data = detect_collisions(data, TIME_INTERVAL, NUM_STEPS, HORIZONTAL_SEPARATION,
                                                 VERTICAL_SEPARATION)
            collision_span.set_attribute("collision", collision_exists)
            logger.debug(f'[collision-detector fn] Result of collision detection: {collision_exists}')

        # Make a decision based on the collision detection result + origin metadata
        # TODO move to to a separate function file
        with tracer.start_as_current_span('final_decision',
                                          attributes={"collision": collision_exists, "origin": origin}) as decision_span:
            if not collision_exists:
                if origin == 'self_report':
                    logger.info("Do nothing. (safe and self_report)")
                    return 'Do nothing (safe and self_report)'
                elif origin == 'system':
                    logger.info("calling release. (safe and from system)")
                    with tracer.start_as_current_span('post_release') as post_release_span:
                        try:
                            r = post_release(parsed_input)
                            post_release_span.set_attribute("response_code", r.status_code)
                        except Exception as e:
                            logger.error(f'[collision-detector  fn] Error in post_release: {e}')
                            post_release_span.set_attribute("error", True)
                            post_release_span.set_attribute("error_details", e)

                        return 'called release (safe and from system)'
                else:
                    logger.error("origin is neither system nor self_report")
                    decision_span.set_attribute("error", True)
                    decision_span.set_attribute("error_details", "origin is neither system nor self_report")
                    return 'origin is neither system nor self_report'
            elif collision_exists:
                logger.info("calling mutate trajectories. (unsafe)")
                with tracer.start_as_current_span('post_mutate') as post_mutate_span:
                    try:
                        r = post_mutate(flagged_data, meta, collision_exists)
                        post_mutate_span.set_attribute("response_code", r.status_code)
                    except Exception as e:
                        logger.error(f'[collision-detector  fn] Error in post_mutate: {e}')
                        post_mutate_span.set_attribute("error", True)
                        post_mutate_span.set_attribute("error_details", e)
                    return 'called mutate trajectories. (unsafe)'


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
