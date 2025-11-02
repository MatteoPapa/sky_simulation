import requests
import logging

host = "172.17.0.1"
# host = "host.docker.internal"

# Set up Python logger
logger = logging.getLogger(__name__)


def post_(data, meta):
    url = f"http://{host}:8000/???"
    headers = {
        "Content-Type": "application/json",
        "X-tinyFaaS-Async": "true"}  # tinyfaas will return a 202 response

    payload = {
        "data": data,
        "meta": meta
    }
    logger.debug(f'[??? fn] calling ??? function on {url} with payload: {payload}')
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code != 202:  # async call
        logger.error(f'[??? fn] Error calling ??? function ({response.status_code}): {response.text}')
    else:
        logger.info(f'[??? fn] ({response.status_code}) Response from ??? function: {response.text}')
    return response
