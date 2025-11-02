import os
import threading
import paho.mqtt.client as mqtt
from skybed.message_types import UAV

_client: mqtt.Client | None = None
_topic_name = os.getenv("MQTT_UPDATES_TOPIC", "updates")
_qos = int(os.getenv("MQTT_QOS", "1"))

def _ensure_client(host: str, port: int = 1883):
    global _client
    if _client is not None:
        return _client
    cid = os.getenv("MQTT_CLIENT_ID", f"uav-publisher")
    c = mqtt.Client(client_id=cid, clean_session=False)
    user = os.getenv("MQTT_USER"); pwd = os.getenv("MQTT_PASSWORD")
    if user:
        c.username_pw_set(user, pwd or "")
    c.connect(host, port, keepalive=60)
    threading.Thread(target=c.loop_forever, daemon=True).start()
    _client = c
    print(f"[mqtt] publisher → topic '{_topic_name}' (QoS={_qos})")
    return _client

def create_producer(ip: str):
    port = int(os.getenv("MQTT_PORT", "1883"))
    _ensure_client(ip, port)

def publish_position_update(uav: UAV):
    if _client is None:
        return
    payload = uav.model_dump_json()
    _client.publish(_topic_name, payload=payload, qos=_qos, retain=False)
