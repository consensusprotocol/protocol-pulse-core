#!/usr/bin/env bash
# startup.sh — Production startup script for Protocol Pulse
#
# Boots Flask app + scheduler + monitoring together.
# Handles graceful shutdown, auto-restart on crash, and health check endpoint.
#
# Usage:
#   ./scripts/startup.sh              # Start all services
#   ./scripts/startup.sh --check      # Health check only
#   ./scripts/startup.sh --stop       # Graceful shutdown
#
# Environment:
#   PORT               — HTTP port (default: 5000)
#   WORKERS            — Gunicorn workers (default: 2)
#   ENABLE_APSCHEDULER — Enable background scheduler (default: false)
#   MAX_RESTARTS       — Max auto-restarts before giving up (default: 5)
#   RESTART_DELAY      — Seconds between restart attempts (default: 5)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PID_FILE="$PROJECT_ROOT/state/startup.pid"
LOG_FILE="$PROJECT_ROOT/logs/startup.log"

PORT="${PORT:-5000}"
WORKERS="${WORKERS:-2}"
MAX_RESTARTS="${MAX_RESTARTS:-5}"
RESTART_DELAY="${RESTART_DELAY:-5}"

# ─── Helpers ───

log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    echo "$msg"
    echo "$msg" >> "$LOG_FILE" 2>/dev/null || true
}

ensure_dirs() {
    mkdir -p "$PROJECT_ROOT/state"
    mkdir -p "$PROJECT_ROOT/logs"
    mkdir -p "$PROJECT_ROOT/data/episodes"
    mkdir -p "$PROJECT_ROOT/data/video_engine"
    mkdir -p "$PROJECT_ROOT/state/checkpoints"
    mkdir -p "$PROJECT_ROOT/state/dead_letter"
}

# ─── Health Check ───

health_check() {
    local url="http://127.0.0.1:${PORT}/"
    local status
    status=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 --max-time 10 "$url" 2>/dev/null || echo "000")

    if [[ "$status" == "200" || "$status" == "302" ]]; then
        echo "HEALTHY (HTTP $status)"
        return 0
    else
        echo "UNHEALTHY (HTTP $status)"
        return 1
    fi
}

# ─── Stop ───

stop_services() {
    log "Stopping services..."

    if [[ -f "$PID_FILE" ]]; then
        local pid
        pid=$(cat "$PID_FILE" 2>/dev/null)
        if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
            log "Sending SIGTERM to gunicorn (PID $pid)"
            kill -TERM "$pid"

            # Wait up to 30s for graceful shutdown
            local waited=0
            while kill -0 "$pid" 2>/dev/null && [[ $waited -lt 30 ]]; do
                sleep 1
                waited=$((waited + 1))
            done

            if kill -0 "$pid" 2>/dev/null; then
                log "Force killing (PID $pid)"
                kill -9 "$pid" 2>/dev/null || true
            fi
        fi
        rm -f "$PID_FILE"
    fi

    log "Services stopped"
}

# ─── Start ───

start_services() {
    ensure_dirs

    log "=============================="
    log "Protocol Pulse — Starting"
    log "Port: $PORT | Workers: $WORKERS"
    log "=============================="

    # Load .env
    if [[ -f "$PROJECT_ROOT/.env" ]]; then
        set -a
        source "$PROJECT_ROOT/.env"
        set +a
        log "Loaded .env"
    fi

    cd "$PROJECT_ROOT"

    # Check for existing process
    if [[ -f "$PID_FILE" ]]; then
        local old_pid
        old_pid=$(cat "$PID_FILE" 2>/dev/null)
        if [[ -n "$old_pid" ]] && kill -0 "$old_pid" 2>/dev/null; then
            log "Already running (PID $old_pid). Use --stop first."
            exit 1
        fi
        rm -f "$PID_FILE"
    fi

    # Find python
    local PYTHON
    if [[ -f "$PROJECT_ROOT/venv/bin/python" ]]; then
        PYTHON="$PROJECT_ROOT/venv/bin/python"
    elif command -v python3 &>/dev/null; then
        PYTHON="python3"
    else
        PYTHON="python"
    fi
    log "Python: $PYTHON"

    # Run DB migrations if Flask-Migrate is available
    $PYTHON -c "import flask_migrate" 2>/dev/null && {
        log "Running database migrations..."
        cd "$PROJECT_ROOT" && FLASK_APP=app $PYTHON -m flask db upgrade 2>&1 | tail -5 || log "Migration skipped (no pending)"
    } || log "Flask-Migrate not available, skipping migrations"

    # Start gunicorn with auto-restart loop
    local restart_count=0

    while [[ $restart_count -lt $MAX_RESTARTS ]]; do
        log "Starting gunicorn (attempt $((restart_count + 1))/$MAX_RESTARTS)..."

        # Determine if gunicorn is available
        if $PYTHON -c "import gunicorn" 2>/dev/null; then
            $PYTHON -m gunicorn \
                --bind "0.0.0.0:${PORT}" \
                --workers "$WORKERS" \
                --timeout 120 \
                --graceful-timeout 30 \
                --access-logfile "$PROJECT_ROOT/logs/access.log" \
                --error-logfile "$PROJECT_ROOT/logs/error.log" \
                --pid "$PID_FILE" \
                --preload \
                "app:app" &
        else
            # Fallback to Flask dev server
            log "Gunicorn not available, using Flask dev server"
            $PYTHON -c "
import os
os.environ.setdefault('PORT', '$PORT')
from app import app
app.run(host='0.0.0.0', port=int('$PORT'), debug=False, use_reloader=False)
" &
            echo $! > "$PID_FILE"
        fi

        local pid=$!

        # Wait for the server to come up
        sleep 3

        if ! kill -0 "$pid" 2>/dev/null; then
            restart_count=$((restart_count + 1))
            log "Server exited immediately (attempt $restart_count/$MAX_RESTARTS)"
            sleep "$RESTART_DELAY"
            continue
        fi

        log "Server running (PID $pid)"

        # Monitor loop — restart if the process dies
        wait "$pid" 2>/dev/null
        local exit_code=$?

        if [[ $exit_code -eq 0 ]]; then
            log "Server exited cleanly (code 0)"
            break
        fi

        restart_count=$((restart_count + 1))
        log "Server crashed (exit $exit_code). Restart $restart_count/$MAX_RESTARTS in ${RESTART_DELAY}s..."
        rm -f "$PID_FILE"
        sleep "$RESTART_DELAY"
    done

    if [[ $restart_count -ge $MAX_RESTARTS ]]; then
        log "MAX RESTARTS ($MAX_RESTARTS) exceeded. Giving up."
        # Send alert
        $PYTHON -c "
try:
    from services.video_engine.pipeline_alerts import send_alert
    send_alert('STARTUP FAILURE', 'Protocol Pulse failed to start after $MAX_RESTARTS attempts', level='error')
except: pass
" 2>/dev/null || true
        exit 1
    fi
}

# ─── Signal Handlers ───

trap 'stop_services; exit 0' SIGTERM SIGINT SIGHUP

# ─── Main ───

case "${1:-start}" in
    --check|check|health)
        health_check
        ;;
    --stop|stop)
        stop_services
        ;;
    --restart|restart)
        stop_services
        sleep 2
        start_services
        ;;
    start|"")
        start_services
        ;;
    *)
        echo "Usage: $0 [start|--stop|--check|--restart]"
        exit 1
        ;;
esac
