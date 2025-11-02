#!/usr/bin/env bash
set -euo pipefail

# ---------- config ----------
PROJECT_NAME="sky_simulation"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OPS_DIR="$ROOT_DIR/ops"
LOG_DIR="$ROOT_DIR/logs"
RUN_DIR="$ROOT_DIR/run"

MONGO_PORT=27017
MQTT_PORT=1883
VIZ_PORT=8051

TINY_DIR="$ROOT_DIR/tinyFaaS"
TINY_SCRIPTS="$TINY_DIR/scripts"

INGESTER_DIR="$ROOT_DIR/6gn-ingester"
VIEWER_DIR="$ROOT_DIR/sky_viewer"
VIZ_DIR="$VIEWER_DIR/viz"

# ---------- utils ----------
mkdir -p "$OPS_DIR" "$LOG_DIR" "$RUN_DIR"

pidfile() { echo "$RUN_DIR/$1.pid"; }
logfile() { echo "$LOG_DIR/$1.log"; }

is_running() {
  local pf; pf="$(pidfile "$1")"
  [[ -f "$pf" ]] && kill -0 "$(cat "$pf")" 2>/dev/null
}

start_bg() {
  local name="$1"; shift
  local cwd="$1"; shift
  local cmd="$*"
  mkdir -p "$cwd"
  if is_running "$name"; then
    echo "[$name] already running (pid $(cat "$(pidfile "$name")")). Skipping."
    return 0
  fi
  echo "[$name] starting: $cmd"
  # NOTE: setsid = create a new session/process group for everything spawned
  ( cd "$cwd" && nohup setsid bash -lc "$cmd" >"$(logfile "$name")" 2>&1 & echo $! >"$(pidfile "$name")" )
  sleep 1
  if ! is_running "$name"; then
    echo "[$name] failed to start. See $(logfile "$name")"
    return 1
  fi
  echo "[$name] up (pid $(cat "$(pidfile "$name")")). Logs: $(logfile "$name")"
}

stop_bg() {
  local name="$1"; local sig="${2:-TERM}"
  local pf; pf="$(pidfile "$name")"
  if [[ -f "$pf" ]]; then
    local pid; pid="$(cat "$pf")"
    if kill -0 "$pid" 2>/dev/null; then
      # Try service-specific stop first (tinyFaaS may have one)
      if [[ "$name" == "tinyfaas" ]]; then
        if [[ -f "$TINY_DIR/Makefile" ]] && grep -qE '(^|\s)stop\s*:' "$TINY_DIR/Makefile"; then
          echo "[$name] running 'make stop' ..."
          ( cd "$TINY_DIR" && make stop ) || true
        fi
      fi

      # Resolve the process group id and kill the whole group
      local pgid; pgid="$(ps -o pgid= "$pid" | tr -d ' ')"
      [[ -z "$pgid" ]] && pgid="$pid"   # fallback
      echo "Stopping $name (pid $pid, pgid $pgid) ..."
      kill "-$sig" "-$pgid" 2>/dev/null || true

      # Graceful wait
      for _ in {1..30}; do
        kill -0 "$pid" 2>/dev/null || break
        sleep 0.5
      done

      # Force kill the group if needed
      if kill -0 "$pid" 2>/dev/null; then
        echo "Force killing $name process group ..."
        kill -9 "-$pgid" 2>/dev/null || true
      fi
    fi
    rm -f "$pf"
  fi
}

# ---------- compose (mongo + mosquitto) ----------
write_compose() {
  cat >"$OPS_DIR/docker-compose.yml" <<'YML'
services:
  mongo:
    image: mongo:latest
    container_name: mongo
    ports:
      - "27017:27017"
    restart: unless-stopped

  mosquitto:
    image: eclipse-mosquitto:2
    container_name: mosquitto
    ports:
      - "1883:1883"
    volumes:
      - ./mosquitto.conf:/mosquitto/config/mosquitto.conf:ro
    restart: unless-stopped
YML
}

write_mosquitto_conf() {
  cat >"$OPS_DIR/mosquitto.conf" <<'CONF'
listener 1883 0.0.0.0
allow_anonymous true
CONF
}

compose_up() {
  write_compose
  write_mosquitto_conf
  echo "[infra] docker compose -p $PROJECT_NAME up -d"
  ( cd "$OPS_DIR" && docker compose -p "$PROJECT_NAME" up -d )
}

compose_down() {
  if [[ -f "$OPS_DIR/docker-compose.yml" ]]; then
    echo "[infra] docker compose -p $PROJECT_NAME down -v --remove-orphans"
    ( cd "$OPS_DIR" && docker compose -p "$PROJECT_NAME" down -v --remove-orphans || true )
  fi

  # Fallback: kill containers that might have been launched manually or by a different project
  echo "[infra] ensuring mongo/mosquitto are gone (fallback)"
  docker rm -f mongo 2>/dev/null || true
  docker rm -f mosquitto 2>/dev/null || true

  # Extra: remove matching networks left behind by compose (safe best-effort)
  docker network prune -f >/dev/null 2>&1 || true
}

# ---------- services ----------
tinyfaas_start() {
  start_bg "tinyfaas" "$TINY_DIR" "make start"
}

tinyfaas_upload() {
  echo "[tinyfaas] uploading functions ..."
  (
    cd "$TINY_SCRIPTS"
    set -e
    ./upload.sh ../../6gn-functions/update update python3 1
    ./upload.sh ../../6gn-functions/trigger trigger python3 1
    ./upload.sh ../../6gn-functions/collision-detector collisiondetector python3 1
    ./upload.sh ../../6gn-functions/mutate mutate python3 1
    ./upload.sh ../../6gn-functions/release release python3 1
  ) >>"$(logfile tinyfaas-upload)" 2>&1
  echo "[tinyfaas] uploads complete. Logs: $(logfile tinyfaas-upload)"
}

ingester_start() {
  start_bg "ingester" "$INGESTER_DIR" "go run main.go"
}

viz_start() {
  local venv="$VIEWER_DIR/.venv"
  start_bg "viz" "$VIZ_DIR" "
    cd \"$VIEWER_DIR\" \
    && ( [ -d \"$venv\" ] || python3 -m venv \"$venv\" ) \
    && source \"$venv/bin/activate\" \
    && pip -q install --upgrade pip \
    && if [ -f requirements.txt ]; then pip -q install -r requirements.txt; fi \
    && cd \"$VIZ_DIR\" \
    && exec uvicorn server:app --reload --host 0.0.0.0 --port $VIZ_PORT
  "
}

ports_check() {
  echo "Checking ports:"
  echo "  MongoDB:   localhost:$MONGO_PORT"
  echo "  Mosquitto: localhost:$MQTT_PORT"
  echo "  Viz:       http://localhost:$VIZ_PORT"
}

up() {
  compose_up
  ports_check
  tinyfaas_start
  sleep 5 || true
  tinyfaas_upload
  ingester_start
  viz_start
  echo
  echo "✅ All services started."
  echo "  - MongoDB:   tcp://localhost:$MONGO_PORT"
  echo "  - Mosquitto: tcp://localhost:$MQTT_PORT"
  echo "  - Viz:       http://localhost:$VIZ_PORT"
  echo
  echo "Logs:"
  echo "  tail -f $(logfile tinyfaas)"
  echo "  tail -f $(logfile tinyfaas-upload)"
  echo "  tail -f $(logfile ingester)"
  echo "  tail -f $(logfile viz)"
  echo " Run a scenario with:"
  echo " cd sky_viewer"
  echo " python3 -m skybed.scenario_runner ./scenarios/single_collision.json"
}

# ---- tinyFaaS function containers cleanup ----
# Allowlist of function names tinyFaaS creates containers for
TINYFUNCS=(update trigger collisiondetector mutate release)

# Stop & remove any containers whose names equal or start with those
tinyfaas_funcs_down() {
  # build a regex like: ^(update|trigger|collisiondetector|mutate|release)(-|$)
  local rx="^($(IFS='|'; echo "${TINYFUNCS[*]}"))(-|$)"
  # collect matching container IDs (running or exited)
  local ids
  ids="$(docker ps -a --format '{{.ID}}\t{{.Names}}' \
        | awk -v RS='\n' -v rx="$rx" 'tolower($2) ~ rx { print $1 }')"
  if [[ -n "${ids// /}" ]]; then
    echo "[tinyfaas] Removing function containers: $(echo "$ids" | xargs)"
    docker rm -f $ids >/dev/null 2>&1 || true
  else
    echo "[tinyfaas] No function containers to remove."
  fi
}

# (Optional) list function containers in status
tinyfaas_funcs_status() {
  local rx="^($(IFS='|'; echo "${TINYFUNCS[*]}"))(-|$)"
  echo "[tinyfaas] function containers:"
  docker ps -a --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}' \
    | awk -v RS='\n' -v rx="$rx" 'NR==1 || tolower($1) ~ rx'
}

# (Optional) deep prune images built for these functions (safe opt-in)
# Call as: tinyfaas_funcs_prune_images
tinyfaas_funcs_prune_images() {
  local rx="^($(IFS='|'; echo "${TINYFUNCS[*]}"))(:|@|$)"
  local images
  images="$(docker images --format '{{.Repository}}:{{.Tag}} {{.ID}}' \
           | awk -v RS='\n' -v rx="$rx" '$1 ~ rx { print $2 }' | sort -u)"
  if [[ -n "${images// /}" ]]; then
    echo "[tinyfaas] Removing function images: $(echo "$images" | xargs)"
    docker rmi -f $images >/dev/null 2>&1 || true
  else
    echo "[tinyfaas] No function images to remove."
  fi
}

kill_listeners_on_port() {
  # kill_listeners_on_port <port> <label>
  local port="$1" label="${2:-port-$1}"
  # Find LISTENing PIDs on the port
  local pids
  pids="$(lsof -ti -sTCP:LISTEN -i :"$port" 2>/dev/null | tr '\n' ' ')"
  if [[ -n "${pids// /}" ]]; then
    echo "[$label] terminating listeners on :$port -> $pids"
    kill -TERM $pids 2>/dev/null || true
    sleep 1
    # If still alive, force kill
    for p in $pids; do
      kill -0 "$p" 2>/dev/null && kill -KILL "$p" 2>/dev/null || true
    done
  fi
}

down() {
  stop_bg "viz"
  # ensure nothing is left on 8051 (viz)
  kill_listeners_on_port "$VIZ_PORT" "viz"

  stop_bg "ingester"
  stop_bg "tinyfaas"
  pkill -f -u "$(id -u)" -x tinyfaas 2>/dev/null || true
  pkill -f "tinyFaaS|tinyfaas" 2>/dev/null || true

  # remove tinyFaaS function containers if you added that helper earlier
  tinyfaas_funcs_down

  compose_down
  sleep 1
  echo "🛑 Stopped all."
}

status() {
  echo "=== Status ==="
  for s in tinyfaas ingester viz; do
    if is_running "$s"; then
      echo "  $s: running (pid $(cat "$(pidfile "$s")"))"
    else
      echo "  $s: stopped"
    fi
  done
  echo
  docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
}

logs() {
  echo "Log files in $LOG_DIR:"
  ls -1 "$LOG_DIR" || true
  echo
  echo "Example: tail -f $(logfile viz)"
}

case "${1:-}" in
  up) up ;;
  down) down ;;
  status) status ;;
  logs) logs ;;
  *) cat <<USAGE
Usage: ./bootstrap.sh [command]

Commands:
  up         Start infra + tinyFaaS + uploads + ingester + viz
  down       Stop everything (processes + compose)
  status     Show process + container status
  logs       List log files

Notes:
- Logs are under: $LOG_DIR
- PIDs are under:  $RUN_DIR
- Compose files:   $OPS_DIR
USAGE
  ;;
esac
