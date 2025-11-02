import os
import typing
import traceback
from datetime import datetime
import paho.mqtt.client as mqtt
from pydantic import RootModel

from skybed.message_types import UAV
from skybed.uav.position import update_trajectory_from_collision_avoidance_msg

_releases_topic = os.getenv("MQTT_RELEASES_TOPIC", "releases")
_qos = int(os.getenv("MQTT_QOS", "1"))

def _on_message_for_uav(uav_id: str):
    def _cb(client, userdata, msg):
        try:
            timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
            msg_str = msg.payload.decode("utf-8", errors="replace")
            # accetta array di UAV o singolo UAV
            try:
                uavs: typing.List[UAV] = RootModel[list[UAV]].model_validate_json(msg_str).root
            except Exception:
                uavs = [UAV.model_validate_json(msg_str)]

            applied = False
            for u in uavs:
                if u.uav_id == uav_id:
                    print(f"[subscriber] update per '{uav_id}': dir={u.direction} spd={u.speed} vs={u.vertical_speed} alt={u.altitude}")
                    update_trajectory_from_collision_avoidance_msg(u)
                    applied = True
            if applied:
                print("[subscriber] update applicato (targets aggiornati).")
        except Exception:
            traceback.print_exc()
    return _cb

def subscribe(ip: str, uav_id: str):
    port = int(os.getenv("MQTT_PORT", "1883"))
    cid = os.getenv("MQTT_CLIENT_ID", f"uav-subscriber-{uav_id}")

    client = mqtt.Client(client_id=cid, clean_session=False)
    client.reconnect_delay_set(min_delay=1, max_delay=30)

    user = os.getenv("MQTT_USER"); pwd = os.getenv("MQTT_PASSWORD")
    if user:
        client.username_pw_set(user, pwd or "")

    client.on_message = _on_message_for_uav(uav_id)

    def _on_connect(c, *_):
        print(f"[mqtt] connected — subscribing '{_releases_topic}' (QoS={_qos})")
        c.subscribe(_releases_topic, qos=_qos)

    client.on_connect = _on_connect
    client.connect(ip, port, keepalive=60)
    client.loop_forever()
