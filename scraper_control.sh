#!/usr/bin/env bash
# AeroOps Intelligence | Scraper Control Script
# Controls the scraper batch run, single-site scrapes, job-active verification,
# and delegates app/frontend lifecycle to service.sh.

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"
PYTHON_BIN="$VENV_DIR/bin/python3"
PID_DIR="$PROJECT_DIR/pids"
LOG_DIR="$PROJECT_DIR/scraper_manager/logs"

SCRAPE_PID="$PID_DIR/scrape_all.pid"
SCRAPE_LOG="$LOG_DIR/scraper_all.log"
VERIFY_LOG="$LOG_DIR/verify_job_active.log"

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

mkdir -p "$PID_DIR" "$LOG_DIR"

require_venv() {
    if [ ! -x "$PYTHON_BIN" ]; then
        echo -e "${RED}Error: venv python not found at $PYTHON_BIN${NC}"
        exit 1
    fi
}

scrape_status() {
    if [ -f "$SCRAPE_PID" ] && kill -0 "$(cat "$SCRAPE_PID")" 2>/dev/null; then
        echo -e "Scraper batch: ${GREEN}RUNNING${NC} (PID: $(cat "$SCRAPE_PID"))"
        return 0
    else
        echo -e "Scraper batch: ${RED}STOPPED${NC}"
        return 1
    fi
}

scrape_start() {
    require_venv
    if scrape_status >/dev/null 2>&1; then
        echo -e "${YELLOW}Scraper batch already running (PID: $(cat "$SCRAPE_PID"))${NC}"
        exit 0
    fi

    echo -e "${BLUE}Starting full scraper batch (all enabled sites, under xvfb-run)...${NC}"
    cd "$PROJECT_DIR"
    nohup xvfb-run -a "$PYTHON_BIN" manage.py run_all_scrapers_with_logging --log-level INFO \
        > "$LOG_DIR/scrape_batch_stdout.log" 2>&1 &
    disown
    echo $! > "$SCRAPE_PID"
    sleep 2
    if kill -0 "$(cat "$SCRAPE_PID")" 2>/dev/null; then
        echo -e "${GREEN}Started.${NC} PID: $(cat "$SCRAPE_PID")"
        echo "Live log: tail -f \"$SCRAPE_LOG\""
    else
        echo -e "${RED}Failed to start. Check $LOG_DIR/scrape_batch_stdout.log${NC}"
        rm -f "$SCRAPE_PID"
        exit 1
    fi
}

scrape_stop() {
    if [ -f "$SCRAPE_PID" ]; then
        PID=$(cat "$SCRAPE_PID")
        echo -n "Stopping scraper batch (PID $PID)... "
        if kill -0 "$PID" 2>/dev/null; then
            pkill -P "$PID" 2>/dev/null || true
            kill "$PID" 2>/dev/null || true
        fi
        # xvfb-run spawns Xvfb + the actual python process as children;
        # also sweep any leftover run_all_scrapers_with_logging process.
        pkill -f "run_all_scrapers_with_logging" 2>/dev/null || true
        rm -f "$SCRAPE_PID"
        echo -e "${GREEN}STOPPED${NC}"
    else
        echo "Scraper batch is not running."
    fi
}

scrape_one() {
    require_venv
    local site="$1"; shift || true
    if [ -z "${site:-}" ]; then
        echo -e "${RED}Usage: $0 scrape-one <site_key> [extra run_scraper args]${NC}"
        exit 1
    fi
    cd "$PROJECT_DIR"
    xvfb-run -a "$PYTHON_BIN" manage.py run_scraper "$site" -v 2 "$@"
}

scrape_tail() {
    echo "Tailing $SCRAPE_LOG (Ctrl+C to stop watching; scraper keeps running)"
    tail -f "$SCRAPE_LOG"
}

verify_jobs() {
    require_venv
    cd "$PROJECT_DIR"
    echo -e "${BLUE}Verifying job-active status...${NC}"
    "$PYTHON_BIN" manage.py verify_job_active "$@" 2>&1 | tee -a "$VERIFY_LOG"
}

verify_jobs_bg() {
    require_venv
    cd "$PROJECT_DIR"
    nohup "$PYTHON_BIN" manage.py verify_job_active "$@" >> "$VERIFY_LOG" 2>&1 &
    disown
    echo -e "${GREEN}Verify job running in background (PID: $!).${NC} Log: $VERIFY_LOG"
}

app_start() {
    "$PROJECT_DIR/service.sh" start
}

app_stop() {
    "$PROJECT_DIR/service.sh" stop
}

app_status() {
    "$PROJECT_DIR/service.sh" status
}

full_status() {
    echo -e "${BLUE}=== Scraper ===${NC}"
    scrape_status || true
    echo -e "${BLUE}=== App services ===${NC}"
    app_status
}

usage() {
    cat <<EOF
Usage: $0 <command> [args]

Scraper control:
  scrape-start              Start full batch scrape of all enabled sites (background, xvfb)
  scrape-stop               Stop the running batch scrape
  scrape-status             Show whether the batch scrape is running
  scrape-tail               Live-tail the scrape log
  scrape-one <site> [args]  Run a single scraper by site_key (foreground)

Job verification:
  verify [args]             Run verify_job_active in foreground (e.g. --age-days 3 --dry-run)
  verify-bg [args]          Run verify_job_active in background

App / frontend:
  app-start                 Start Django API, Celery worker/beat, realtime gateway, frontend
  app-stop                  Stop all of the above
  app-status                Show status of all of the above

  status                    Show scraper + app status together
EOF
}

cmd="${1:-}"; shift || true
case "$cmd" in
    scrape-start)   scrape_start ;;
    scrape-stop)    scrape_stop ;;
    scrape-status)  scrape_status ;;
    scrape-tail)    scrape_tail ;;
    scrape-one)     scrape_one "$@" ;;
    verify)         verify_jobs "$@" ;;
    verify-bg)      verify_jobs_bg "$@" ;;
    app-start)      app_start ;;
    app-stop)       app_stop ;;
    app-status)     app_status ;;
    status)         full_status ;;
    *)              usage; exit 1 ;;
esac
