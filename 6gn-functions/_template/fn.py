#!/usr/bin/env python3

import json
import typing
import logging

from call_next_func import post_
from timestamp_for_logger import CustomFormatter
from tracer import TracerInitializer

# Set up Python logger. milliseconds are not supported by default
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S.%f'
)
logger = logging.getLogger(__name__)
for handler in logging.getLogger().handlers:  # Apply the custom formatter to the root logger
    handler.setFormatter(CustomFormatter(handler.formatter._fmt, handler.formatter.datefmt))

# Initialize the OpenTelemetry tracer
tracer = TracerInitializer("???").tracer

def fn(input: typing.Optional[str]) -> typing.Optional[str]:
    """
    input:
    output:
    """
    with tracer.start_as_current_span('fn') as main_span:
        main_span.set_attribute("invoke_count", Counter.increment_count())
        main_span.set_attribute("input", input)
        logger.info(f'[??? fn] invoke count: {str(Counter.get_count())}')
        # Parse the JSON string into a Python list of dictionaries
        with tracer.start_as_current_span('parse_input'):
            parsed_input = json.loads(input)
            logger.debug(f'[??? fn] Parsed input: {parsed_input}')

            data = parsed_input.get('data', [])
            meta = parsed_input.get('meta', {})

        ###  with tracer.start_as_current_span(''):

        # call ??? function
        with tracer.start_as_current_span('post_') as post__span:
            try:
                r = post_(data, meta)
                post__span.set_attribute("response_code", r.status_code)
            except Exception as e:
                logger.error(f'[??? fn] Error in post_: {e}')
                post__span.set_attribute("error", True)
                post__span.set_attribute("error_details", e)

        return str("???")


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
