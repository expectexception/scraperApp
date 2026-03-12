#!/usr/bin/env bash
# AeroOps Intelligence | Production Service Management Script
# Handle lifecycle of Django API and Streamlit Dashboard

set -e

# Configuration
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VIRTUAL_ENV="/home/rajat/Desktop/AeroOps Intel/aeroScrap_backend/backendMain/.venv"
PID_DIR="$PROJECT_DIR/pids"
LOG_DIR="$PROJECT_DIR/logs"

# Service Ports
DJANGO_PORT=8008
STREAMLIT_PORT=8501

# PID Files
DJANGO_PID="$PID_DIR/django.pid"
STREAMLIT_PID="$PID_DIR/streamlit.pid"

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

    # 2. Start Streamlit Dashboard
    if [ -f "$STREAMLIT_PID" ] && kill -0 $(cat "$STREAMLIT_PID") 2>/dev/null; then
        echo -e "${RED}Streamlit Dashboard is already running (PID: $(cat "$STREAMLIT_PID"))${NC}"
    else
        echo -n "Starting Streamlit Dashboard on port $STREAMLIT_PORT... "
        nohup "$VIRTUAL_ENV/bin/streamlit" run "$PROJECT_DIR/dashboard.py" \
            --server.port $STREAMLIT_PORT \
            --server.headless true \
            --server.address 0.0.0.0 \
            > "$LOG_DIR/streamlit.log" 2>&1 &
        echo $! > "$STREAMLIT_PID"
        echo -e "${GREEN}DONE${NC}"
    fi

    echo -e "${GREEN}Services are now operational.${NC}"
}

stop() {
    echo -e "${BLUE}Stopping Services...${NC}"
    
    if [ -f "$DJANGO_PID" ]; then
        PID=$(cat "$DJANGO_PID")
        echo -n "Stopping Django (PID $PID)... "
        kill $PID && rm "$DJANGO_PID" || echo -e "${RED}Failed to stop${NC}"
        echo -e "${GREEN}STOPPED${NC}"
    else
        echo "Django is not running."
    fi

    if [ -f "$STREAMLIT_PID" ]; then
        PID=$(cat "$STREAMLIT_PID")
        echo -n "Stopping Streamlit (PID $PID)... "
        kill $PID && rm "$STREAMLIT_PID" || echo -e "${RED}Failed to stop${NC}"
        echo -e "${GREEN}STOPPED${NC}"
    else
        echo "Streamlit is not running."
    fi
}

status() {
    echo -e "${BLUE}AeroOps Service Status:${NC}"
    
    if [ -f "$DJANGO_PID" ] && kill -0 $(cat "$DJANGO_PID") 2>/dev/null; then
        echo -e "Django API:     ${GREEN}RUNNING${NC} (PID: $(cat "$DJANGO_PID"))"
    else
        echo -e "Django API:     ${RED}STOPPED${NC}"
    fi

    if [ -f "$STREAMLIT_PID" ] && kill -0 $(cat "$STREAMLIT_PID") 2>/dev/null; then
        echo -e "Dashboard:      ${GREEN}RUNNING${NC} (PID: $(cat "$STREAMLIT_PID"))"
    else
        echo -e "Dashboard:      ${RED}STOPPED${NC}"
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
