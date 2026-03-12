#!/usr/bin/env bash
# AeroOps Intelligence | Production Service Management Script
# Handle lifecycle of Django API and React frontend

set -e

# Configuration
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VIRTUAL_ENV="/home/rajat/Desktop/AeroOps Intel/aeroScrap_backend/backendMain/.venv"
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
    
    # 1. Start Django via Gunicorn
    if [ -f "$DJANGO_PID" ] && kill -0 $(cat "$DJANGO_PID") 2>/dev/null; then
        echo -e "${RED}Django (Gunicorn) is already running (PID: $(cat "$DJANGO_PID"))${NC}"
    else
        echo -n "Starting Django API on port $DJANGO_PORT... "
        gunicorn scraper_service.wsgi:application \
            --bind 0.0.0.0:$DJANGO_PORT \
            --workers 3 \
            --daemon \
            --pid "$DJANGO_PID" \
            --access-logfile "$LOG_DIR/django_access.log" \
            --error-logfile "$LOG_DIR/django_error.log"
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
        nohup "$VIRTUAL_ENV/bin/python" -m http.server "$FRONTEND_PORT" \
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
        fi
        rm -f "$DJANGO_PID"
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
