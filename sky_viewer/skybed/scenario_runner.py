# skybed/scenario_runner.py
from __future__ import annotations
import json, os, sys, time, signal, subprocess
from pathlib import Path
from typing import Any, Dict, List
import typer

app = typer.Typer(help="Run UAV scenarios (Kafka-only, JSON files)")

def _load_scenario(path: Path) -> Dict[str, Any]:
    if path.suffix.lower() != ".json":
        raise typer.BadParameter(f"Unsupported scenario format: {path.suffix} (use .json)")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        raise typer.BadParameter(f"Failed to read/parse JSON: {e}")

def _uav_args(broker_ip: str, drone: Dict[str, Any], defaults: Dict[str, Any]) -> List[str]:
    cfg = {**defaults, **drone} 
    required = ["uav_id","uav_type","latitude","longitude","altitude","speed","direction","vertical_speed"]
    missing = [k for k in required if k not in cfg]
    if missing:
        raise typer.BadParameter(f"Drone {drone.get('uav_id','<no-id>')} missing fields: {missing}")

    return [
        broker_ip,
        str(cfg["uav_id"]),
        str(cfg["uav_type"]),
        str(cfg["latitude"]),
        str(cfg["longitude"]),
        str(cfg["altitude"]),
        str(cfg["speed"]),
        str(cfg["direction"]),
        str(cfg["vertical_speed"]),
    ]

def _spawn_uav(args: List[str], extra_env: Dict[str,str]) -> subprocess.Popen:
    cmd = [sys.executable, "-m", "skybed.uav.main", *args]
    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
    return subprocess.Popen(
        cmd,
        env={**os.environ, **extra_env},
        creationflags=creationflags,
        stdout=None,
        stderr=None,
        text=True
    )

@app.command("run-scenario")
def run_scenario(
    scenario_path: str = typer.Argument(..., help="Path to .json scenario file"),
    detach: bool = typer.Option(False, help="Start and return immediately (leave children running)"),
    iperf: bool = typer.Option(False, help="Enable iperf3 in child processes (default OFF)"),
):
    """
    Read a JSON scenario and start all UAVs as separate processes.
    Press Ctrl+C to stop all (unless --detach).
    """
    path = Path(scenario_path).expanduser().resolve()
    if not path.exists():
        raise typer.BadParameter(f"Scenario file not found: {path}")

    sc = _load_scenario(path)
    name = sc.get("name", path.stem)
    broker_ip = sc["broker_ip"]
    defaults = sc.get("defaults", {})
    drones: List[Dict[str, Any]] = sc["drones"]
    delay = float(sc.get("spawn_delay_s", 0.1))

    env_child = {"SKYBED_ENABLE_IPERF": "1" if iperf else "0"}

    procs: List[subprocess.Popen] = []
    print(f"[scenario] {name} → broker {broker_ip} | drones: {len(drones)}")

    try:
        for d in drones:
            args = _uav_args(broker_ip, d, defaults)
            p = _spawn_uav(args, env_child)
            procs.append(p)
            # show id + type for quick glance
            print(f"[spawn] {args[1]} ({args[2]}) lat={args[3]} lon={args[4]} speed={args[6]} dir={args[7]}")
            time.sleep(delay)

        if detach:
            print("[scenario] Detach enabled: leaving child UAV processes running.")
            return

        print("[scenario] Running. Press Ctrl+C to stop all UAVs.")
        while True:
            alive = sum(1 for p in procs if p.poll() is None)
            if alive == 0:
                print("[scenario] All UAV processes exited.")
                break
            time.sleep(0.2)


    except KeyboardInterrupt:
        print("\n[scenario] Ctrl+C received: stopping UAVs...")
        for p in procs:
            try:
                if os.name == "nt":
                    p.send_signal(signal.CTRL_BREAK_EVENT)  # requires CREATE_NEW_PROCESS_GROUP
                else:
                    p.terminate()
            except Exception:
                pass
        time.sleep(1.0)
        for p in procs:
            if p.poll() is None:
                try:
                    p.kill()
                except Exception:
                    pass
        print("[scenario] Shutdown complete.")

if __name__ == "__main__":
    app()
