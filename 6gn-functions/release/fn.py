#!/usr/bin/env python3

import json
import typing
import logging
import paho.mqtt.client as mqtt

from call_next_func import post_update
from timestamp_for_logger import CustomFormatter
from tracer import TracerInitializer

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
tracer = TracerInitializer("release").tracer

# Set up MQTT client
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT Broker!")
    else:
        print("Failed to connect, return code %d\n", rc)


HOST = "172.17.0.1"  # TODO: import from ENV
PORT = 1883
QOS = 1  # At least once delivery
CLIENT = mqtt.Client()
CLIENT.on_connect = on_connect
CLIENT.connect(HOST, PORT, 60)
CLIENT.loop_start()  # Start the loop in a separate thread. it was needed on raspberry to publishes work


def fn(input: typing.Optional[str], headers: typing.Optional[typing.Dict[str, str]]) -> typing.Optional[str]:
    """
    input: trajectories needed to be released and update
    output: publishes the data to the '/release' topic, and calls the update function
    """
    with tracer.start_as_current_span('fn') as main_span:
        main_span.set_attribute("invoke_count", Counter.increment_count())
        main_span.set_attribute("input", input)
        logger.info(f'[release fn] invoke count: {str(Counter.get_count())}')
        # Parse the JSON string into a Python list of dictionaries
        with tracer.start_as_current_span('parse_input'):
            parsed_input = json.loads(input)
            logger.debug(f'[release fn] Parsed input: {parsed_input}')

            data = parsed_input.get('data', [])
            meta = parsed_input.get('meta', {})

        # Select elements where 'origin' is 'mutated'
        with tracer.start_as_current_span('filter_mutated_elems'):
            mutated_data = list(filter(lambda item: item.get('origin', None) == 'mutate', data))
            logger.debug(f'[release fn] Mutated data to release: {mutated_data}')

        # Publish the trajectories to the 'release' topic
        with tracer.start_as_current_span('publish_release') as pub_span:
            pub_span.set_attribute("QoS", QOS)
            result, mid = CLIENT.publish('releases', json.dumps(mutated_data), qos=QOS)
            if result == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f'[release fn] Published mutated_data to releases topic: {mutated_data}')
            else:
                logger.error(f'[release fn] Failed to publish to releases topic, result code: {result}')

        # call update function
        with tracer.start_as_current_span('post_update') as post_update_span:
            try:
                r = post_update(mutated_data, meta)
                post_update_span.set_attribute("response_code", r.status_code)
            except Exception as e:
                logger.error(f'[release fn] Error in post_update: {e}')
                post_update_span.set_attribute("error", True)
                post_update_span.set_attribute("error_details", e)

        return str("release func. check logs for details")


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
