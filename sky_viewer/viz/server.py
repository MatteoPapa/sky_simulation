# MQTT visualizer backend (simple, frame-based)
import asyncio, json, os
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
import paho.mqtt.client as mqtt

# -------- config --------
MQTT_HOST = os.getenv("MQTT_HOST", "127.0.0.1")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
UPDATES_TOPIC = os.getenv("UPDATES_TOPIC", "updates")
MQTT_USER = os.getenv("MQTT_USER", "")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "")

FRAME_HZ = int(os.getenv("FRAME_HZ", "15")) 

# -------- app --------
app = FastAPI()
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

class Hub:
    """Keeps latest UAV states and pushes frames to all clients."""
    def __init__(self):
        self.clients: List[WebSocket] = []
        self.latest: Dict[str, Dict[str, Any]] = {}

    async def add(self, ws: WebSocket):
        await ws.accept()
        self.clients.append(ws)
        await ws.send_text(json.dumps({"type": "snapshot", "uavs": list(self.latest.values())}))

    def remove(self, ws: WebSocket):
        if ws in self.clients:
            self.clients.remove(ws)

    async def update(self, u: Dict[str, Any]):
        self.latest[u["uav_id"]] = u

    async def broadcast_frame(self):
        if not self.clients:
            return
        data = json.dumps({"type": "frame", "uavs": list(self.latest.values())})
        clients = list(self.clients) 
        results = await asyncio.gather(
            *[ws.send_text(data) for ws in clients],
            return_exceptions=True
        )
        for ws, r in zip(clients, results):
            if isinstance(r, Exception):
                self.remove(ws)

hub = Hub()

@app.get("/")
async def index():
    return RedirectResponse(url="/static/index.html")

@app.websocket("/ws")
async def ws_feed(ws: WebSocket):
    await hub.add(ws)
    try:
        async for _ in ws.iter_text(): 
            pass
    except WebSocketDisconnect:
        pass
    finally:
        hub.remove(ws)

# -------- MQTT -> asyncio bridge --------
_mqtt_queue: "asyncio.Queue[bytes]" = asyncio.Queue()
_mqtt_client: Optional[mqtt.Client] = None

def _on_connect(client, userdata, flags, rc, *args):
    if rc == 0:
        client.subscribe(UPDATES_TOPIC, qos=0)
        print(f"[mqtt] connected, subscribed to '{UPDATES_TOPIC}'")
    else:
        print(f"[mqtt] connect failed rc={rc}")

def _on_message(client, userdata, msg: mqtt.MQTTMessage):
    loop: asyncio.AbstractEventLoop = userdata["loop"]
    loop.call_soon_threadsafe(_mqtt_queue.put_nowait, msg.payload)

async def mqtt_consumer():
    """Consume MQTT payloads, update latest state (no per-message broadcast)."""
    while True:
        payload = await _mqtt_queue.get()
        while not _mqtt_queue.empty():
            try:
                payload = _mqtt_queue.get_nowait()
            except asyncio.QueueEmpty:
                break
        try:
            d = json.loads(payload.decode("utf-8"))
            u = {
                "uav_id":   d.get("uav_id") or d.get("id") or "unknown",
                "uav_type": d.get("uav_type", ""),
                "lat":      float(d.get("latitude")  if d.get("latitude")  is not None else d.get("lat")),
                "lon":      float(d.get("longitude") if d.get("longitude") is not None else d.get("lon")),
                "alt":      float(d.get("altitude")  if d.get("altitude")  is not None else d.get("alt") or 0.0),
                "speed":    float(d.get("speed", 0.0)),
                "dir":      float(d.get("direction", 0.0)),
            }
            await hub.update(u)
        except Exception:
            continue

async def frame_publisher():
    """Push a full frame (all UAVs) at a fixed cadence."""
    period = 1.0 / max(1, FRAME_HZ)
    while True:
        await asyncio.sleep(period)
        await hub.broadcast_frame()

@app.on_event("startup")
async def _startup():
    asyncio.create_task(mqtt_consumer())
    asyncio.create_task(frame_publisher())

    global _mqtt_client
    loop = asyncio.get_running_loop()
    _mqtt_client = mqtt.Client(client_id=f"viz-{os.getpid()}", userdata={"loop": loop})
    if MQTT_USER:
        _mqtt_client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
    _mqtt_client.on_connect = _on_connect
    _mqtt_client.on_message = _on_message
    _mqtt_client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    _mqtt_client.loop_start()

@app.on_event("shutdown")
async def _shutdown():
    global _mqtt_client
    if _mqtt_client:
        _mqtt_client.loop_stop()
        _mqtt_client.disconnect()
        _mqtt_client = None
