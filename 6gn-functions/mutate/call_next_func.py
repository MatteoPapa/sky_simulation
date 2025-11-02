import requests
import logging

host = "172.17.0.1"
# host = "host.docker.internal"

# Set up Python logger
# logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def post_collision_detector(data, meta):
    url = f"http://{host}:8000/collisiondetector"
    headers = {
        "Content-Type": "application/json",
        "X-tinyFaaS-Async": "true"}  # tinyfaas will return a 202 response

    payload = {
        "data": data,
        "meta": meta
    }
    logger.debug(f'[mutate fn] calling collisiondetector function on {url} with payload: {payload}')
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code != 202:  # async call
        logger.error(f'[mutate fn] Error calling collisiondetector function ({response.status_code}): {response.text}')
    else:
        logger.info(f'[mutate fn] ({response.status_code}) Response from collisiondetector function: {response.text}')
    return response
