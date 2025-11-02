# 🌌 Sky Simulation

Sky Simulation is a modular, containerized simulation environment built around **TinyFaaS**, **Go Ingester**, **MQTT**, and a **FastAPI-based visualization dashboard**.

It provides a reproducible local setup for simulating and visualizing network scenarios such as **collision detection**, **mutation**, and **release events**.

---

## 🚀 Quick Start (Automated)

Use the included `bootstrap.sh` script to bring everything up.

```bash
chmod +x bootstrap.sh
./bootstrap.sh up       # start all services
./bootstrap.sh down     # stop everything
./bootstrap.sh status   # check status
./bootstrap.sh logs     # view logs
```

The `up` command starts:

- MongoDB (port **27017**)
- Mosquitto MQTT broker (port **1883**)
- TinyFaaS (uploads functions automatically)
- Ingester (Go service)
- Visualization server (port **8051**)

Once running, open:

👉 [http://localhost:8051](http://localhost:8051)

---

## ⚙️ Manual Setup

If you prefer to run components manually, follow these steps.

### 1️⃣ MongoDB
```bash
docker run -d   --name mongo   -p 27017:27017   mongo
```

### 2️⃣ Mosquitto MQTT
```bash
cat > mosquitto.conf <<'CONF'
listener 1883 0.0.0.0
allow_anonymous true
CONF

docker rm -f mosquitto 2>/dev/null || true
docker run -d --name mosquitto   -p 1883:1883   -v "$PWD/mosquitto.conf:/mosquitto/config/mosquitto.conf:ro"   eclipse-mosquitto:2
```

### 3️⃣ TinyFaaS
```bash
cd tinyFaaS
make start

cd scripts
./upload.sh ../../6gn-functions/update update python3 1
./upload.sh ../../6gn-functions/trigger trigger python3 1
./upload.sh ../../6gn-functions/collision-detector collisiondetector python3 1
./upload.sh ../../6gn-functions/mutate mutate python3 1
./upload.sh ../../6gn-functions/release release python3 1
```
Each upload creates a Docker container named after the function.

### 4️⃣ Ingester
```bash
cd 6gn-ingester
go run main.go
```

### 5️⃣ Visualization Server
```bash
cd sky_viewer
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cd viz
uvicorn server:app --reload --host 0.0.0.0 --port 8051
```

Visit 👉 [http://localhost:8051](http://localhost:8051)

---

## 🧩 Running Scenarios

Example:
```bash
python3 -m skybed.scenario_runner ./scenarios/single_collision.json
```

---

## 🧹 Cleanup

If using the automation script:
```bash
./bootstrap.sh down
```
This stops all processes, removes Docker containers (Mongo, Mosquitto, TinyFaaS functions), and frees ports 1883, 27017, and 8051.

---

