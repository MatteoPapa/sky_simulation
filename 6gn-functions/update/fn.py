#!/usr/bin/env python3

import json
import typing
import logging

from call_next_func import post_trigger
from timestamp_for_logger import CustomFormatter
from tracer import TracerInitializer
from store_update import store_update
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
tracer = TracerInitializer("update").tracer

def fn(input: typing.Optional[str], headers: typing.Optional[typing.Dict[str, str]]) -> typing.Optional[str]: # NOTE: should not be parallelized with postTrigger, as it will read the write update() does
    """
    input: A JSON string of collection of new trajectories
    output: writes to the db, and may call trigger function
    """
    with tracer.start_as_current_span('fn') as main_span:
        main_span.set_attribute("invoke_count", Counter.increment_count())
        main_span.set_attribute("input", input)
        logger.info(f'[update fn] invoke count: {str(Counter.get_count())}')
        # Parse the JSON string into a Python list of dictionaries
        with tracer.start_as_current_span('parse_input'):
            parsed_input = json.loads(input)
            logger.debug(f'[update fn] Parsed input: {parsed_input}')

            data = parsed_input.get('data', [])
            meta = parsed_input.get('meta', {})

        # Check the 'origin' in 'meta'
        origin = meta.get('origin', None)
        if origin is None:
            logger.error(f'[update fn] No origin key found in meta')
            main_span.set_attribute("error", True)
            main_span.set_attribute("error_details", f'No origin key found in meta. dump: {meta}')
            return f'No origin key found in meta. dump: {meta}'

        # store the data and call the trigger function if the origin is 'self_report'
        with tracer.start_as_current_span('store_n_decide_to_trigger') as store_n_decide_span:
            store_n_decide_span.set_attribute("origin", origin)
            if origin == 'system':  # invoked by release()
                logger.info(f'[update fn] will NOT call post_trigger() as it is from system. storing the released data. dump: {data}')
                try: # NOTE: multiple trajectories can be released by the system
                    store_update(data)  # IO operation
                except Exception as e:
                    logger.error(f'[update fn] Error in store_update: {e}')
                    store_n_decide_span.set_attribute("error", True)
                    store_n_decide_span.set_attribute("error_details", e)
            elif origin == 'self_report':  # invoked by ingest
                logger.info('[update fn] storing the reported data.')
                try: # NOTE: usually only one trajectory is reported, but data is a list
                    store_update(data)   # IO operation
                except Exception as e:
                    logger.error(f'[update fn] Error in store_update: {e}')
                    store_n_decide_span.set_attribute("error", True)
                    store_n_decide_span.set_attribute("error_details", e)
                logger.info('[update fn] Calling post_trigger with data and meta')
                with tracer.start_as_current_span('post_trigger') as post_trigger_span:
                    # json_serialiized_data = JSONEncoder().encode(data)  # after adding created_at as python timestamp
                    try:
                        post_trigger("", meta) # IO operation
                    except Exception as e:
                        logger.error(f'[update fn] Error in post_trigger: {e}')
                        post_trigger_span.set_attribute("error", True)
                        post_trigger_span.set_attribute("error_details", e)
            else:
                logger.fatal(f'[update fn] Unknown origin: {origin}')
                store_n_decide_span.set_attribute("error", True)
                store_n_decide_span.set_attribute("error_details", f'Unknown origin: {origin}')
                return f'Unknown origin: {origin}'

        return str(data)


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
