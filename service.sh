#!/usr/bin/env bash
# AeroOps Intelligence | Production Service Management Script
# Handle lifecycle of Django API and React frontend

set -euo pipefail

# Configuration
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$(cd "$PROJECT_DIR/.." && pwd)"

# Prefer project-local virtualenv, fallback to workspace virtualenv.
if [ -d "$PROJECT_DIR/.venv" ]; then
    VIRTUAL_ENV="$PROJECT_DIR/.venv"
elif [ -d "$WORKSPACE_DIR/.venv" ]; then
    VIRTUAL_ENV="$WORKSPACE_DIR/.venv"
else
    VIRTUAL_ENV="$PROJECT_DIR/.venv"
fi

PYTHON_BIN="$VIRTUAL_ENV/bin/python"
PIP_BIN="$VIRTUAL_ENV/bin/pip"
GUNICORN_BIN="$VIRTUAL_ENV/bin/gunicorn"
PID_DIR="$PROJECT_DIR/pids"
LOG_DIR="$PROJECT_DIR/logs"

# Service Ports
DJANGO_PORT=8008
FRONTEND_PORT=8501

# Frontend
FRONTEND_DIR="$PROJECT_DIR/frontend"
FRONTEND_DIST_DIR="$FRONTEND_DIR/dist"

# PID Files
DJANGO_PID="$PID_DIR/django.pid"
FRONTEND_PID="$PID_DIR/frontend.pid"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

mkdir -p "$PID_DIR" "$LOG_DIR"

is_port_listening() {
    ss -ltn "( sport = :$1 )" 2>/dev/null | tail -n +2 | grep -q LISTEN
}

wait_for_pid_exit() {
    local pid="$1"
    local label="$2"

    for _ in $(seq 1 20); do
        if ! kill -0 "$pid" 2>/dev/null; then
            return 0
        fi
        sleep 0.5
    done

    echo -e "${RED}${label} did not stop gracefully, sending SIGKILL...${NC}"
    kill -9 "$pid" 2>/dev/null || true
}

wait_for_port_release() {
    local port="$1"
    for _ in $(seq 1 20); do
        if ! is_port_listening "$port"; then
            return 0
        fi
        sleep 0.5
    done

    if command -v fuser >/dev/null 2>&1; then
        fuser -k "${port}/tcp" >/dev/null 2>&1 || true
        sleep 1
    fi
}

verify_gunicorn_started() {
    for _ in $(seq 1 20); do
        if [ -f "$DJANGO_PID" ] && kill -0 "$(cat "$DJANGO_PID")" 2>/dev/null && is_port_listening "$DJANGO_PORT"; then
            return 0
        fi
        sleep 0.5
    done

    echo -e "${RED}FAILED${NC}"
    echo "--- Django startup log ---"
    tail -n 40 "$LOG_DIR/django_error.log" || true
    exit 1
}

activate_env() {
    if [ -f "$VIRTUAL_ENV/bin/activate" ]; then
        source "$VIRTUAL_ENV/bin/activate"
    else
        echo -e "${RED}Error: Virtual environment not found at $VIRTUAL_ENV${NC}"
        exit 1
    fi
}

start() {
    echo -e "${BLUE}Starting Services...${NC}"
    activate_env

    if ! command -v npm >/dev/null 2>&1; then
        echo -e "${RED}Error: npm is required to build frontend assets.${NC}"
        exit 1
    fi

    DB_ENGINE="$(grep -E '^DATABASE_ENGINE=' "$PROJECT_DIR/.env" 2>/dev/null | head -n1 | cut -d'=' -f2- | tr '[:upper:]' '[:lower:]' | tr -d '[:space:]' || true)"
    DB_ENGINE="${DB_ENGINE:-mongodb}"
    if [ "${DB_ENGINE:-mongodb}" = "mongodb" ]; then
        echo -e "Skipping SQL migrations for MongoDB backend."
    else
        echo -n "Applying database migrations... "
        (cd "$PROJECT_DIR" && "$PYTHON_BIN" manage.py migrate --noinput >/dev/null)
        echo -e "${GREEN}DONE${NC}"
    fi

    wait_for_port_release "$DJANGO_PORT"
    
    # 1. Start Django via Gunicorn
    if [ -f "$DJANGO_PID" ] && kill -0 $(cat "$DJANGO_PID") 2>/dev/null; then
        echo -e "${RED}Django (Gunicorn) is already running (PID: $(cat "$DJANGO_PID"))${NC}"
    else
        echo -n "Starting Django API on port $DJANGO_PORT... "
        "$GUNICORN_BIN" scraper_service.wsgi:application \
            --bind 0.0.0.0:$DJANGO_PORT \
            --workers 3 \
            --log-level info \
            --daemon \
            --pid "$DJANGO_PID" \
            --access-logfile "$LOG_DIR/django_access.log" \
            --error-logfile "$LOG_DIR/django_error.log"
        verify_gunicorn_started
        echo -e "${GREEN}DONE${NC}"
    fi

    # 2. Build React frontend (if needed)
    if [ ! -d "$FRONTEND_DIR" ]; then
        echo -e "${RED}Frontend directory not found: $FRONTEND_DIR${NC}"
        exit 1
    fi

    if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
        echo -n "Installing frontend dependencies... "
        (cd "$FRONTEND_DIR" && npm install)
        echo -e "${GREEN}DONE${NC}"
    fi

    echo -n "Building frontend assets... "
    (cd "$FRONTEND_DIR" && npm run build)
    echo -e "${GREEN}DONE${NC}"

    # 3. Start React frontend static server
    if [ -f "$FRONTEND_PID" ] && kill -0 $(cat "$FRONTEND_PID") 2>/dev/null; then
        echo -e "${RED}Frontend is already running (PID: $(cat "$FRONTEND_PID"))${NC}"
    else
        echo -n "Starting React frontend on port $FRONTEND_PORT... "
        nohup "$PYTHON_BIN" -m http.server "$FRONTEND_PORT" \
            --directory "$FRONTEND_DIST_DIR" \
            > "$LOG_DIR/frontend.log" 2>&1 &
        echo $! > "$FRONTEND_PID"
        echo -e "${GREEN}DONE${NC}"
    fi

    echo -e "${GREEN}Services are now operational.${NC}"
}

stop() {
    echo -e "${BLUE}Stopping Services...${NC}"
    
    if [ -f "$DJANGO_PID" ]; then
        PID=$(cat "$DJANGO_PID")
        echo -n "Stopping Django (PID $PID)... "
        if kill -0 "$PID" 2>/dev/null; then
            kill "$PID"
            wait_for_pid_exit "$PID" "Django"
        fi
        rm -f "$DJANGO_PID"
        wait_for_port_release "$DJANGO_PORT"
        echo -e "${GREEN}STOPPED${NC}"
    else
        echo "Django is not running."
    fi

    if [ -f "$FRONTEND_PID" ]; then
        PID=$(cat "$FRONTEND_PID")
        echo -n "Stopping Frontend (PID $PID)... "
        if kill -0 "$PID" 2>/dev/null; then
            kill "$PID"
        fi
        rm -f "$FRONTEND_PID"
        echo -e "${GREEN}STOPPED${NC}"
    else
        echo "Frontend is not running."
    fi
}

status() {
    echo -e "${BLUE}AeroOps Service Status:${NC}"
    
    if [ -f "$DJANGO_PID" ] && kill -0 $(cat "$DJANGO_PID") 2>/dev/null; then
        echo -e "Django API:     ${GREEN}RUNNING${NC} (PID: $(cat "$DJANGO_PID"))"
    else
        echo -e "Django API:     ${RED}STOPPED${NC}"
    fi

    if [ -f "$FRONTEND_PID" ] && kill -0 $(cat "$FRONTEND_PID") 2>/dev/null; then
        echo -e "Frontend:       ${GREEN}RUNNING${NC} (PID: $(cat "$FRONTEND_PID"))"
    else
        echo -e "Frontend:       ${RED}STOPPED${NC}"
    fi
}

case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        stop
        sleep 2
        start
        ;;
    status)
        status
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        exit 1
esac
