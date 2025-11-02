import paho.mqtt.client as mqtt
from datetime import datetime

HOST = "localhost"
PORT = 1883
TOPIC = "releases"
QoS = 1  # at least once

def on_connect(client, userdata, flags, rc, properties=None):
    print(f"Connected with result code {rc}")
    if rc == 0:
        client.subscribe(TOPIC, qos=QoS)
    else:
        print(f"Failed to connect, return code {rc}")

def on_subscribe(client, userdata, mid, granted_qos, properties=None):
    if granted_qos[0] != 128:  # 128 indicates failure to subscribe
        print(f"Successfully subscribed to topic '{TOPIC}' with QoS {granted_qos[0]}")
    else:
        print(f"Failed to subscribe to topic '{TOPIC}'")

def on_message(client, userdata, msg):
    timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
    print(f'[{timestamp}] Received message: {msg.payload.decode("utf-8")}')

def create_mqtt_client():
    client = mqtt.Client() # protocol=mqtt.MQTTv5)
    client.on_connect = on_connect
    client.on_subscribe = on_subscribe
    client.on_message = on_message
    client.connect(HOST, PORT, 60)
    return client

if __name__ == "__main__":
    client = create_mqtt_client()
    client.loop_forever()