# skybed/uav/main.py
import sys
import time
import threading
import typer

from skybed.message_types import UAV
from skybed.uav import position
from skybed.uav.position import update_position_from_trajectory
from skybed.uav.publisher import create_producer, publish_position_update
from skybed.uav.subscriber import subscribe

sys.stdout.reconfigure(line_buffering=True)
app = typer.Typer()

@app.command()
def start_uav(
    ip: str,
    uav_id: str,
    uav_type: str,
    latitude: float,
    longitude: float,
    altitude: float,
    speed: float,
    direction: float,
    vertical_speed: float,
):
    # stato iniziale
    position.uav = UAV(
        uav_id=uav_id, uav_type=uav_type,
        latitude=latitude, longitude=longitude, altitude=altitude,
        speed=speed, direction=direction, vertical_speed=vertical_speed
    )

    # MQTT
    create_producer(ip)
    threading.Thread(target=subscribe, args=(ip, uav_id), daemon=True).start()

    # loop 50 Hz
    hz = 50.0
    dt = 1.0 / hz
    print(f"[uav {uav_id}] loop {hz:.0f} Hz")
    while True:
        update_position_from_trajectory(dt)
        try: position.uav.sync_from_point()
        except Exception: pass
        publish_position_update(position.uav)
        time.sleep(dt)

if __name__ == "__main__":
    app()
