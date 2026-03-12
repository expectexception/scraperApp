"""
AeroOps IFOA Dashboard — v6.0 (Mission Control)
Fully DB-driven status. Persistent across browser restarts.
"""
import os
import sys
import subprocess
import signal
import warnings
import django
import psutil
import pandas as pd
import requests
import streamlit as st
from streamlit_autorefresh import st_autorefresh
import plotly.express as px
from datetime import datetime, timedelta, timezone as dt_timezone

# ── Suppress Django re-registration warnings ──────────────────────────────────
warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*Model '.*' was already registered.*")

# ── Django Setup ──────────────────────────────────────────────────────────────
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "scraper_service.settings")

import django.conf
from django.conf import settings
from django.utils import timezone
import django.db.models

if not settings.configured:
    try:
        django.setup()
    except Exception as e:
        st.error(f"❌ Django Setup Error: {e}")
        st.stop()
# If already configured, skip setup — safe on Streamlit reruns

from scraper_manager.models import ScraperJob, ScraperConfig, WebhookConfig
from scraper_manager.scrapers import list_scrapers
from jobs.models import Job

# ── APScheduler (singleton via cache) ────────────────────────────────────────
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

@st.cache_resource
def get_scheduler():
    s = BackgroundScheduler()
    s.start()
    return s

sched = get_scheduler()

# ── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="IFOA | AeroOps Intelligence",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Session State Init ────────────────────────────────────────────────────────
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "show_login_modal" not in st.session_state:
    st.session_state.show_login_modal = False
if "scraper_queue" not in st.session_state:
    st.session_state.scraper_queue = []

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
:root {
    --primary: #3b82f6;
    --primary-glow: rgba(59,130,246,.35);
    --success: #22c55e;
    --warning: #eab308;
    --danger: #ef4444;
    --bg-main: #020617;
    --bg-card: #0d1829;
    --bg-card2: #111827;
    --border: #1e293b;
    --text: #f1f5f9;
    --muted: #64748b;
}
html, .stApp { background: var(--bg-main); color: var(--text); }
[data-testid="stHeader"] { background: rgba(2,6,23,.95); border-bottom: 1px solid var(--border); }
[data-testid="stDeployButton"] { display: none !important; }
[data-testid="stToolbar"] { display: none !important; }
[data-testid="stDecoration"] { display: none !important; }
[data-testid="stStatusWidget"] { display: none !important; }
#MainMenu { display: none !important; }
footer .viewerBadge_container__r5tak { display: none !important; }
/* Ensure sidebar is always visible */
[data-testid="stSidebar"] { display: block !important; visibility: visible !important; }
[data-testid="stSidebarCollapsedControl"] { display: flex !important; visibility: visible !important; }
[data-testid="stSidebar"] { background: #030712 !important; border-right: 2px solid var(--primary) !important; }

h1,h2,h3 { color: var(--text) !important; }

/* Stat card */
.stat-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 18px 22px;
    margin-bottom: 4px;
}
.stat-val { font-size: 28px; font-weight: 800; color: var(--primary); }
.stat-label { font-size: 11px; text-transform: uppercase; letter-spacing:.08em; color: var(--muted); margin-top:2px; }

/* Scraper cards */
.scraper-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 14px;
    margin-bottom: 8px;
    transition: border .2s;
}
.scraper-card.running { border-color: var(--primary); }
.scraper-card.pending { border-color: var(--warning); }

/* Status badge */
.badge {
    display: inline-flex; align-items: center; gap: 6px;
    font-size: 11px; font-weight: 700; letter-spacing:.06em;
    padding: 2px 8px; border-radius: 20px;
}
.badge-running { background: rgba(59,130,246,.15); color: var(--primary); }
.badge-pending { background: rgba(234,179,8,.15); color: var(--warning); }
.badge-idle    { background: rgba(100,116,139,.15); color: var(--muted); }
.badge-done    { background: rgba(34,197,94,.15); color: var(--success); }
.badge-failed  { background: rgba(239,68,68,.15); color: var(--danger); }

/* Pulse dot */
.dot {
    width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0;
    display: inline-block;
}
@keyframes pulse-anim {
    0%   { box-shadow: 0 0 0 0 var(--primary-glow); }
    70%  { box-shadow: 0 0 0 7px rgba(59,130,246,0); }
    100% { box-shadow: 0 0 0 0 rgba(59,130,246,0); }
}
.dot-running { background: var(--primary); animation: pulse-anim 1.4s infinite; }
.dot-pending { background: var(--warning); }
.dot-idle    { background: var(--muted); }
.dot-done    { background: var(--success); }
.dot-failed  { background: var(--danger); }

/* Monitor table row */
.monitor-row {
    display: flex; align-items: center; gap: 12px;
    padding: 10px 14px;
    border: 1px solid var(--border);
    border-radius: 8px;
    background: var(--bg-card2);
    margin-bottom: 6px;
}
.monitor-name { font-weight: 700; font-size: 13px; min-width:120px; }
.monitor-meta { font-size: 12px; color: var(--muted); flex:1; }
.prog-bar-outer {
    background: var(--border); border-radius: 4px;
    height: 6px; flex: 1; max-width: 160px;
}
.prog-bar-inner { background: var(--primary); border-radius: 4px; height: 6px; }

.monitor-header {
    display:flex;
    gap:12px;
    padding:6px 14px;
    font-size:11px;
    color:var(--muted);
    text-transform:uppercase;
    letter-spacing:.08em;
    margin-bottom:4px;
}

/* Tab tweaks */
.stTabs [data-baseweb="tab-list"] { gap: 6px; background: transparent; }
.stTabs [data-baseweb="tab"] { border-radius: 6px; color: var(--muted); padding: 6px 14px; }
.stTabs [aria-selected="true"] { background: var(--border) !important; color: var(--text) !important; }

button[kind="primary"]   { background: var(--primary) !important; border: none !important; }
button[kind="secondary"] { border-color: var(--border) !important; color: var(--text) !important; }

div[data-testid="stDataFrame"] { border: 1px solid var(--border); border-radius: 8px; }

@media (max-width: 1024px) {
    .stat-card { padding: 14px 16px; }
    .stat-val { font-size: 22px; }
    .monitor-row { flex-wrap: wrap; align-items: flex-start; }
    .monitor-meta { width: 100%; }
    .prog-bar-outer { max-width: none; width: 100%; }
}

@media (max-width: 640px) {
    h1 { font-size: 22px !important; }
    .stat-card { padding: 12px; }
    .stat-val { font-size: 20px; }
    .badge { font-size: 10px; }
    .monitor-header { display: none; }
}
</style>
""", unsafe_allow_html=True)

dashboard_username = getattr(settings, "DASHBOARD_USERNAME", "admin")
dashboard_password = (
    os.environ.get("DASHBOARD_PASSWORD")
    or getattr(settings, "DASHBOARD_PASSWORD", None)
)

def render_login_form(location: str, suffix: str, container=st):
    with container.form(f"login_form_{suffix}"):
        st.caption(f"Admin login — needed for {location} controls.")
        user = st.text_input("Username", key=f"login_user_{suffix}")
        pwd = st.text_input("Password", type="password", key=f"login_pw_{suffix}")
        if st.form_submit_button("🔐 Login", use_container_width=True):
            if not dashboard_password:
                st.error("Dashboard password is not configured. Set DASHBOARD_PASSWORD in the environment or Django settings.")
            elif user == dashboard_username and pwd == dashboard_password:
                st.session_state.authenticated = True
                st.session_state.show_login_modal = False
                st.rerun()
            else:
                st.error("Invalid credentials")


# ════════════════════════════════════════════════════════════════════════════
# CORE HELPERS — fully DB-driven, session-state-free for status
# ════════════════════════════════════════════════════════════════════════════

def get_running_jobs():
    """
    Return dict {scraper_name: {pid, job_id, started_at, progress, log}}
    for every ScraperJob marked 'running' whose OS process is still alive.
    Stale DB records are auto-corrected to 'failed'.
    """
    running = {}
    jobs = ScraperJob.objects.filter(status="running").select_related()
    for job in jobs:
        if not job.pid:
            # No PID - mark failed
            job.status = "failed"
            job.error_message = "No PID recorded."
            job.save(update_fields=["status", "error_message"])
            continue
        try:
            p = psutil.Process(job.pid)
            if p.is_running() and "python" in p.name().lower():
                log_file = os.path.join("scraper_logs", f"{job.scraper_name}.log")
                running[job.scraper_name] = {
                    "pid": job.pid,
                    "job_id": job.id,
                    "started_at": job.started_at,
                    "progress": job.progress,
                    "log": log_file,
                }
            else:
                job.status = "failed"
                job.error_message = "Process terminated unexpectedly."
                job.save(update_fields=["status", "error_message"])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            job.status = "failed"
            job.error_message = "Process no longer accessible."
            job.save(update_fields=["status", "error_message"])
    return running


def launch_scraper(name: str) -> dict | None:
    """Launch a scraper subprocess and pre-create its DB record. Returns info dict."""
    log_dir = "scraper_logs"
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"{name}.log")

    try:
        job = ScraperJob.objects.create(
            scraper_name=name,
            status="running",
            started_at=timezone.now(),
            triggered_by="dashboard",
        )
        cmd = [sys.executable, "manage.py", "run_scraper", name, "--job-id", str(job.id)]
        with open(log_file, "a") as f:
            proc = subprocess.Popen(cmd, stdout=f, stderr=f, start_new_session=True)

        # Update PID in DB immediately
        job.pid = proc.pid
        job.save(update_fields=["pid"])

        return {"pid": proc.pid, "job_id": job.id, "started_at": job.started_at,
                "progress": 0, "log": log_file}
    except Exception as e:
        st.error(f"Failed to launch {name}: {e}")
        return None


def stop_scraper_by_pid(pid: int):
    """Terminate a process by PID."""
    try:
        os.kill(pid, signal.SIGTERM)
    except Exception:
        pass
    # Mark stale jobs that had this PID
    ScraperJob.objects.filter(pid=pid, status="running").update(
        status="cancelled",
        error_message="Stopped by user via dashboard."
    )


def trigger_scheduled_scraper(name):
    cmd = [sys.executable, "manage.py", "run_scraper", name]
    subprocess.Popen(cmd)


def refresh_schedules():
    """Re-sync APScheduler jobs with DB config without dropping active jobs."""
    active_ids: set[str] = set()
    for cfg in ScraperConfig.objects.filter(is_enabled=True, schedule_enabled=True):
        if cfg.schedule_cron:
            try:
                sched.add_job(
                    trigger_scheduled_scraper,
                    CronTrigger.from_crontab(cfg.schedule_cron),
                    args=[cfg.scraper_name],
                    id=f"sched_{cfg.scraper_name}",
                    replace_existing=True,
                )
                active_ids.add(f"sched_{cfg.scraper_name}")
            except Exception as e:
                print(f"Schedule error {cfg.scraper_name}: {e}")
    # Remove scheduled jobs that are no longer in DB config
    for job in sched.get_jobs():
        if job.id.startswith("sched_") and job.id not in active_ids:
            sched.remove_job(job.id)


def get_scraper_queue() -> list[str]:
    queue = st.session_state.get("scraper_queue", [])
    if not isinstance(queue, list):
        queue = []
    return queue


def set_scraper_queue(queue: list[str]):
    st.session_state.scraper_queue = queue


def queue_scrapers(scraper_names: list[str]) -> int:
    queue = get_scraper_queue()
    before = len(queue)
    for scraper_name in scraper_names:
        if scraper_name not in queue:
            queue.append(scraper_name)
    set_scraper_queue(queue)
    return len(queue) - before


if "scheduler_init" not in st.session_state:
    refresh_schedules()
    st.session_state.scheduler_init = True


@st.cache_data(ttl=10)
def fetch_recent_history(limit: int = 20):
    """Cached helper for the most recent scraper runs."""
    return list(ScraperJob.objects.order_by("-created_at")[:limit])


running_jobs = get_running_jobs()
running_count = len(running_jobs)
all_scrapers = list_scrapers()

# Drop queue entries for scrapers no longer available.
queue = [name for name in get_scraper_queue() if name in all_scrapers]
if queue != get_scraper_queue():
    set_scraper_queue(queue)

# Run queued scrapers one-by-one: launch next only when none are running.
if running_count == 0 and queue:
    next_scraper = queue.pop(0)
    set_scraper_queue(queue)
    launched = launch_scraper(next_scraper)
    if launched:
        st.toast(f"Queued scraper started: {next_scraper.upper()}", icon="▶")
    st.rerun()


def scraper_status_badge(s_name: str, running_jobs: dict, batch_pids: set) -> tuple[str, str, str]:
    """Return (label, dot_class, badge_class) for a scraper."""
    if s_name in running_jobs:
        return "RUNNING", "dot-running", "badge-running"
    if s_name in batch_pids:
        return "QUEUED", "dot-pending", "badge-pending"
    last = ScraperJob.objects.filter(scraper_name=s_name).order_by("-created_at").first()
    if last:
        if last.status == "running":
            return "RUNNING", "dot-running", "badge-running"
        if last.status == "completed":
            age_h = (datetime.now(dt_timezone.utc) - last.completed_at).total_seconds() / 3600 if last.completed_at else 999
            return f"DONE ({int(age_h)}h ago)", "dot-done", "badge-done"
        if last.status == "failed":
            return "FAILED", "dot-failed", "badge-failed"
        if last.status == "cancelled":
            return "STOPPED", "dot-idle", "badge-idle"
    return "IDLE", "dot-idle", "badge-idle"


def fmt_duration(started_at) -> str:
    if started_at is None:
        return "—"
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=dt_timezone.utc)
    delta = datetime.now(dt_timezone.utc) - started_at
    h, rem = divmod(int(delta.total_seconds()), 3600)
    m, s = divmod(rem, 60)
    if h: return f"{h}h {m}m"
    if m: return f"{m}m {s}s"
    return f"{s}s"


# ════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown('<p style="font-size:50px;font-weight:800;letter-spacing:.05em;">✈ IFOA</p>', unsafe_allow_html=True)
    st.caption("Aviation Job Intelligence")
    if not st.session_state.authenticated:
        render_login_form("sidebar", "sidebar", st.sidebar)
        if not dashboard_password:
            st.warning("Set DASHBOARD_PASSWORD (env or settings) before admin login will work.")
    else:
        st.markdown('<span class="badge badge-done">✓ Admin Session</span>', unsafe_allow_html=True)
        if st.button("Logout", use_container_width=True):
            st.session_state.authenticated = False
            st.rerun()

    st.divider()

    # ── Quick stats ───────────────────────────────────────────────────────
    st.metric("🔴 Active Scrapers", running_count)
    st.metric("📦 Total Jobs", Job.objects.count())
    st.metric("🗓 New Today", Job.objects.filter(
        retrieved_date__date=timezone.now().date()).count())


# ════════════════════════════════════════════════════════════════════════════
# MAIN AREA
# ════════════════════════════════════════════════════════════════════════════

st.markdown('<h1 style="font-size:28px;margin-bottom:0;">🛰 IFOA Scrapers Control</h1>', unsafe_allow_html=True)
st.caption("Real-time aviation job intelligence")
if not st.session_state.authenticated:
    if hasattr(st, "popover"):
        with st.popover("🔐 Admin Login", use_container_width=False):
            render_login_form("main controls", "main_popover", st)
    else:
        login_clicked = st.button("🔐 Admin Login", type="primary", key="main_login_button")
        if login_clicked:
            st.session_state.show_login_modal = not st.session_state.show_login_modal
        if st.session_state.show_login_modal:
            with st.container(border=True):
                render_login_form("main controls", "main_fallback", st)
    if not dashboard_password:
        st.warning("Set DASHBOARD_PASSWORD (env or settings) before admin login will work.")

cpu = psutil.cpu_percent(interval=None)
ram = psutil.virtual_memory().percent
health_color = "#22c55e" if cpu < 75 and ram < 85 else ("#eab308" if cpu < 90 else "#ef4444")
with st.container():
    # st.markdown(f"""
    # <div class="stat-card" style="margin-bottom:10px;">
    #     <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">
    #         <div class="dot" style="background:{health_color};animation:pulse-anim 1.5s infinite;
    #              box-shadow:0 0 8px {health_color};width:10px;height:10px;"></div>
    #         <span style="font-weight:700;font-size:13px;">System Health</span>
    #     </div>
    # </div>
    # """, unsafe_allow_html=True)
    st.progress(cpu / 100, text=f"CPU {cpu:.0f}%")
    st.progress(ram / 100, text=f"RAM {ram:.0f}%")

if running_count > 0 or len(get_scraper_queue()) > 0:
    st_autorefresh(interval=3000, key="global_scraper_refresh")

# ── Stats Row ─────────────────────────────────────────────────────────────

stats = [
    ("Total Jobs", Job.objects.count()),
    ("Active Scrapers", len(running_jobs)),
    ("New Today", Job.objects.filter(retrieved_date__date=timezone.now().date()).count()),
    ("Scrapers Up", len(all_scrapers)),
    ("Errors (24h)", ScraperJob.objects.filter(
        status="failed",
        created_at__gte=timezone.now() - timedelta(hours=24)
    ).count()),
]

row1 = st.columns(3)
row2 = st.columns(2)
for col, (label, val) in zip(row1 + row2, stats):
    col.markdown(f"""
    <div class="stat-card">
        <div class="stat-label">{label}</div>
        <div class="stat-val">{val:,}</div>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

tabs = st.tabs(["🛰️ Command Center", "➕ Add Job", "📅 Scheduler", "📊 Analytics",
                "🔍 Job Explorer", "⚙️ Config Editor", "🔔 Alerts", "🔄 Dedup & Cleanup"])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — COMMAND CENTER
# ══════════════════════════════════════════════════════════════════════════════
with tabs[0]:
    # ── Top controls ──────────────────────────────────────────────────────
    top_l, top_r = st.columns([5, 2])
    top_l.subheader("Live Scraper Control")

    scraper_list = all_scrapers
    queued_scrapers = get_scraper_queue()
    queued_set = set(queued_scrapers)
    any_running = len(running_jobs) > 0

    btn_cols = top_r.columns(2)
    if btn_cols[0].button("🚀 Start All", type="primary", use_container_width=True,
                           help="Launch all enabled scrapers sequentially"):
        to_queue = [sn for sn in scraper_list if sn not in running_jobs and sn not in queued_set]
        added = queue_scrapers(to_queue)
        if added:
            st.toast(f"Queued {added} scraper(s) for sequential run", icon="🧭")
            st.rerun()
        else:
            st.info("All available scrapers are already running or queued.")

    if btn_cols[1].button("⏹ Stop All", type="secondary", use_container_width=True,
                           help="Terminate all running missions"):
        set_scraper_queue([])
        if any_running:
            for info in running_jobs.values():
                stop_scraper_by_pid(info["pid"])
        st.toast("All running and queued missions stopped", icon="⏹")
        st.rerun()

    if queued_scrapers:
        st.info(f"Queue: {len(queued_scrapers)} pending | Next: {queued_scrapers[0].upper()}")

    # ── Mission Monitor ───────────────────────────────────────────────────
    st.markdown("### 📺 Continuous Scraper Monitor")

    if running_jobs:
        # Table header
        st.markdown("""
        <div class="monitor-header">
            <div style="min-width:130px;">Scraper</div>
            <div style="width:80px;">PID</div>
            <div style="flex:1;">Runtime</div>
            <div style="width:160px;">Progress</div>
            <div style="width:80px;">Job ID</div>
            <div style="width:70px;">Action</div>
        </div>
        """, unsafe_allow_html=True)

        for sn, info in list(running_jobs.items()):
            prog = info["progress"]
            runtime = fmt_duration(info["started_at"])
            row_l, row_r = st.columns([5, 1])
            with row_l:
                st.markdown(f"""
                <div class="monitor-row">
                    <div class="dot dot-running"></div>
                    <div class="monitor-name">{sn.upper()}</div>
                    <div class="monitor-meta">PID {info['pid']} &nbsp;|&nbsp; {runtime} &nbsp;|&nbsp; Job #{info['job_id']}</div>
                    <div class="prog-bar-outer">
                        <div class="prog-bar-inner" style="width:{prog}%;"></div>
                    </div>
                    <div style="font-size:11px;color:var(--primary);width:36px;text-align:right;">{prog}%</div>
                </div>
                """, unsafe_allow_html=True)
            with row_r:
                if st.button("⏹", key=f"mon_stop_{sn}", help=f"Stop {sn}"):
                    stop_scraper_by_pid(info["pid"])
                    st.rerun()

        # Live log viewer for first running scraper
        first_name = list(running_jobs.keys())[0]
        first_info = running_jobs[first_name]
        log_path = first_info["log"]
        lc, rc = st.columns([6, 1])
        lc.markdown(f"**📋 Live Log — {first_name.upper()}**")
        if rc.button("🔄 Refresh", key="mon_refresh"):
            st.rerun()
        if os.path.exists(log_path):
            with open(log_path, "r") as f:
                lines = f.readlines()[-25:]
            st.code("".join(lines) if lines else "(log is empty)", language="text")
        else:
            st.info("Log file not yet created.")

    else:
        st.markdown("""
        <div style="background:var(--bg-card);border:1px solid var(--border);border-radius:10px;
             padding:32px;text-align:center;color:var(--muted);">
            <div style="font-size:32px;margin-bottom:8px;">📡</div>
            <div style="font-weight:600;">No Active Scrapers</div>
            <div style="font-size:13px;margin-top:4px;">All scrapers are idle. Use the controls below to launch.</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Recent runs summary ───────────────────────────────────────────────
    history_key = "recent_history_expander"
    with st.expander("📜 Recent Scraper History", expanded=False, key=history_key):
        if st.session_state.get(history_key):
            recent = fetch_recent_history()
            if recent:
                rows = []
                for j in recent:
                    dur = ""
                    if j.execution_time:
                        dur = f"{j.execution_time:.0f}s"
                    elif j.started_at and j.status == "running":
                        dur = fmt_duration(j.started_at) + " ⏳"
                    rows.append({
                        "Scraper": j.scraper_name.upper(),
                        "Status": j.status.title(),
                        "Progress": f"{j.progress}%",
                        "New Jobs": j.jobs_new,
                        "Duration": dur,
                        "Started": j.started_at.strftime("%d %b %H:%M") if j.started_at else "—",
                    })
                st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
        else:
            st.info("Expand the history panel to load recent run data.")

    # ── Scraper Control Grid ──────────────────────────────────────────────
    st.markdown("### 🎛️ Scraper Control", unsafe_allow_html=False)
    st.caption("Click ▶ to launch individual sensors. Status reflects live DB state.")

    batch_pids = queued_set
    cols = st.columns(3)
    for idx, s_name in enumerate(scraper_list):
        label, dot_cls, badge_cls = scraper_status_badge(s_name, running_jobs, batch_pids)
        is_running = s_name in running_jobs
        is_queued = s_name in queued_set

        with cols[idx % 3]:
            with st.container(border=True):
                name_col, btn_col = st.columns([3, 2])
                name_col.markdown(f"""
                <div style="margin-top:4px;">
                    <span style="font-weight:700;font-size:13px;">{s_name.upper()}</span>
                </div>
                <div class="badge {badge_cls}" style="margin-top:5px;">
                    <div class="dot {dot_cls}"></div>
                    {label}
                </div>
                """, unsafe_allow_html=True)

                with btn_col:
                    if is_running:
                        pid = running_jobs[s_name]["pid"]
                        if st.button("⏹ Stop", key=f"stop_{s_name}", type="secondary",
                                     use_container_width=True, help="Stop mission"):
                            stop_scraper_by_pid(pid)
                            st.rerun()
                    elif is_queued:
                        if st.button("🗑 Unqueue", key=f"unqueue_{s_name}", type="secondary",
                                     use_container_width=True, help="Remove from sequential queue"):
                            set_scraper_queue([q for q in get_scraper_queue() if q != s_name])
                            st.rerun()
                    else:
                        b1, b2 = st.columns(2)
                        if b1.button("▶", key=f"run_{s_name}", type="primary",
                                     use_container_width=True, help="Launch mission"):
                            if any_running or get_scraper_queue():
                                queue_scrapers([s_name])
                                st.toast(f"Queued {s_name.upper()} for sequential run", icon="🧭")
                            else:
                                launch_scraper(s_name)
                            st.rerun()
                        if b2.button("🔍", key=f"info_{s_name}",
                                     use_container_width=True, help="Show last run"):
                            last = ScraperJob.objects.filter(
                                scraper_name=s_name).order_by("-created_at").first()
                            if last:
                                st.info(f"Last run: {last.status} — {last.jobs_new} new jobs — {last.started_at.strftime('%d %b %H:%M') if last.started_at else 'N/A'}")
                            else:
                                st.info(f"No history for {s_name}.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — ADD JOB MANUALLY
# ══════════════════════════════════════════════════════════════════════════════
with tabs[1]:
    st.subheader("➕ Add Job Manually")
    st.caption("Manually add a job listing to the IFOA database.")

    with st.form("add_job_form", clear_on_submit=True):
        col_a, col_b = st.columns(2)
        title    = col_a.text_input("Job Title *", placeholder="e.g. First Officer — B737")
        company  = col_b.text_input("Company *", placeholder="e.g. Eurowings")
        location = col_a.text_input("Location", placeholder="e.g. Düsseldorf, Germany")
        source   = col_b.text_input("Source / Scraper Tag", placeholder="e.g. eurowings")
        url      = st.text_input("Job URL *", placeholder="https://...")
        desc     = st.text_area("Description (optional)", height=120)

        col_d, col_e, col_f = st.columns(3)
        posted   = col_d.date_input("Posted Date", value=timezone.now().date())
        country  = col_e.text_input("Country Code", placeholder="DE", max_chars=3)
        operation_type = col_f.selectbox("Operation Type", ["commercial", "cargo", "general_aviation", "charter", "maintenance", "other"])

        submitted = st.form_submit_button("💾 Add to Database", type="primary", use_container_width=True)

        if submitted:
            if not title or not company or not url:
                st.error("Title, Company and URL are required fields.")
            else:
                try:
                    job, created = Job.objects.get_or_create(
                        url=url,
                        defaults={
                            "title": title,
                            "company": company,
                            "location": location,
                            "source": source or "manual",
                            "description": desc,
                            "posted_date": posted,
                            "country_code": country.upper() if country else None,
                            "operation_type": operation_type,
                            "status": "new",
                        }
                    )
                    if created:
                        st.success(f"✅ Job '{title}' added successfully (ID: {job.pk}).")
                    else:
                        st.warning(f"Job with this URL already exists (ID: {job.pk}).")
                except Exception as e:
                    st.error(f"Error: {e}")

    # Recent manual entries preview
    st.markdown("#### Recently Added (Manual)")
    manual = Job.objects.filter(source="manual").order_by("-created_at")[:10]
    if manual.exists():
        rows = [{"ID": j.pk, "Title": j.title, "Company": j.company,
                 "Location": j.location or "", "URL": j.url,
                 "Added": j.created_at.strftime("%d %b %H:%M")} for j in manual]
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True,
                     column_config={"URL": st.column_config.LinkColumn("URL")})
    else:
        st.info("No manually added jobs yet.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — SCHEDULER
# ══════════════════════════════════════════════════════════════════════════════
with tabs[2]:
    st.subheader("📅 Background Schedules")

    if not st.session_state.authenticated:
        st.warning("🔒 Administrator login required to manage schedules.")
    else:
        with st.expander("🆕 Add / Update Schedule", expanded=False):
            with st.form("sched_form"):
                sc_n = st.selectbox("Scraper", list_scrapers())
                cron = st.text_input("Cron Expression", placeholder="0 */6 * * *  — every 6 hours")
                en   = st.checkbox("Enabled", value=True)
                if st.form_submit_button("💾 Save Schedule", type="primary"):
                    cfg, _ = ScraperConfig.objects.get_or_create(scraper_name=sc_n)
                    cfg.schedule_cron = cron
                    cfg.schedule_enabled = en
                    cfg.save()
                    refresh_schedules()
                    st.success(f"Schedule for {sc_n} saved.")
                    st.rerun()

        configs = ScraperConfig.objects.all().order_by("scraper_name")
        rows = []
        for c in configs:
            if c.schedule_cron:
                job_obj = sched.get_job(f"sched_{c.scraper_name}")
                next_r  = job_obj.next_run_time.strftime("%d %b %H:%M") if job_obj and job_obj.next_run_time else "—"
                rows.append({
                    "Scraper": c.scraper_name.upper(),
                    "Cron": c.schedule_cron,
                    "Enabled": "✅" if c.schedule_enabled else "⏸",
                    "Next Run": next_r,
                })
        if rows:
            st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
        else:
            st.info("No schedules configured yet.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — ANALYTICS
# ══════════════════════════════════════════════════════════════════════════════
with tabs[3]:
    st.subheader("📊 Data Insights")
    c1, c2 = st.columns(2)

    with c1:
        st.markdown("**Scraping Velocity — Last 14 Days**")
        today = timezone.now().date()
        dates  = [today - timedelta(days=i) for i in range(13, -1, -1)]
        counts = [Job.objects.filter(retrieved_date__date=d).count() for d in dates]
        fig1 = px.area(x=dates, y=counts, labels={"x": "Date", "y": "Jobs"},
                       color_discrete_sequence=["#3b82f6"])
        fig1.update_layout(height=280, margin=dict(l=10,r=10,t=10,b=10),
                           paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                           font_color="#94a3b8")
        fig1.update_xaxes(showgrid=False)
        fig1.update_yaxes(gridcolor="#1e293b")
        st.plotly_chart(fig1, use_container_width=True)

    with c2:
        st.markdown("**Top Data Sources**")
        sources = (Job.objects.values("source")
                   .annotate(count=django.db.models.Count("id"))
                   .order_by("-count")[:10])
        if sources:
            fig2 = px.bar(list(sources), x="source", y="count",
                          color="count", color_continuous_scale="blues")
            fig2.update_layout(height=280, margin=dict(l=10,r=10,t=10,b=10),
                               paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                               showlegend=False, font_color="#94a3b8", coloraxis_showscale=False)
            fig2.update_xaxes(showgrid=False)
            fig2.update_yaxes(gridcolor="#1e293b")
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No source data yet.")

    st.markdown("**Scraper Completion Rate**")
    total   = ScraperJob.objects.count()
    done    = ScraperJob.objects.filter(status="completed").count()
    failed  = ScraperJob.objects.filter(status="failed").count()
    running_c = ScraperJob.objects.filter(status="running").count()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Runs", total)
    m2.metric("Completed",  done,    f"{done/max(total,1)*100:.0f}%")
    m3.metric("Failed",     failed,  f"{failed/max(total,1)*100:.0f}%", delta_color="inverse")
    m4.metric("Running Now",running_c)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — JOB EXPLORER
# ══════════════════════════════════════════════════════════════════════════════
with tabs[4]:
    st.subheader("🔍 Job Archive Explorer")

    # ── Filters ───────────────────────────────────────────────────────────
    f1, f2, f3, f4, f5 = st.columns([2, 2, 1, 1, 1])
    srch      = f1.text_input("🔍 Search", placeholder="Title, company…", label_visibility="collapsed")
    source_f  = f2.text_input("Source", placeholder="eurowings…", label_visibility="collapsed")
    status_f  = f3.selectbox("Status", ["all", "new", "expired", "manual"], label_visibility="collapsed")
    sort_f    = f4.selectbox("Sort", ["Newest", "Oldest", "Company", "Title"], label_visibility="collapsed")
    limit     = f5.selectbox("Rows", [50, 100, 250, 500], label_visibility="collapsed")

    q = Job.objects.all()
    if srch:
        q = q.filter(django.db.models.Q(title__icontains=srch) |
                     django.db.models.Q(company__icontains=srch) |
                     django.db.models.Q(location__icontains=srch))
    if source_f:
        q = q.filter(source__icontains=source_f)
    if status_f != "all":
        q = q.filter(status=status_f)

    sort_map = {"Newest": "-retrieved_date", "Oldest": "retrieved_date",
                "Company": "company", "Title": "title"}
    q = q.order_by(sort_map.get(sort_f, "-retrieved_date"))
    total_count = q.count()

    # ── Select All / stats bar ────────────────────────────────────────────
    hl, hr = st.columns([3, 2])
    hl.caption(f"{total_count:,} matching jobs")
    selection_key = "job_explorer_selected_ids"
    if selection_key not in st.session_state:
        st.session_state[selection_key] = []
    select_all = hr.checkbox("Select All Visible", key="sel_all_jobs")

    df = pd.DataFrame(list(q[:limit].values("id", "title", "company", "location",
                                             "source", "status", "posted_date", "url")))
    if not df.empty:
        visible_ids = df["id"].tolist()
        if select_all:
            st.session_state[selection_key] = visible_ids
        stored_selection = st.session_state.get(selection_key, [])
        df["Select"] = df["id"].isin(stored_selection)
        edited = st.data_editor(
            df,
            column_config={
                "url":    st.column_config.LinkColumn("URL"),
                "Select": st.column_config.CheckboxColumn("✓", default=False, width="small"),
                "status": st.column_config.TextColumn("Status", width="small"),
            },
            use_container_width=True,
            hide_index=True,
            num_rows="fixed",
        )
        selected_ids = edited[edited["Select"] == True]["id"].tolist()
        st.session_state[selection_key] = selected_ids
        sel_n = len(selected_ids)

        # ── Bulk Actions ──────────────────────────────────────────────────
        st.markdown(f"**{sel_n}** job(s) selected")
        a1, a2, a3, a4, a5 = st.columns(5)

        if a1.button(f"🗑 Delete ({sel_n})", disabled=not selected_ids,
                     type="secondary", use_container_width=True):
            Job.objects.filter(id__in=selected_ids).delete()
            st.success(f"Deleted {sel_n} jobs.")
            st.rerun()

        if a2.button(f"⏸ Expire ({sel_n})", disabled=not selected_ids,
                     use_container_width=True, help="Mark as expired"):
            Job.objects.filter(id__in=selected_ids).update(status="expired")
            st.success(f"Marked {sel_n} jobs as expired.")
            st.rerun()

        if a3.button(f"✅ Re-activate ({sel_n})", disabled=not selected_ids,
                     use_container_width=True, help="Mark as new"):
            Job.objects.filter(id__in=selected_ids).update(status="new")
            st.success(f"Re-activated {sel_n} jobs.")
            st.rerun()

        export_df = edited[edited["Select"] == True].drop(columns=["Select"]) \
                    if selected_ids else df.drop(columns=["Select"])
        timestamp = timezone.localtime(timezone.now()).strftime("%Y%m%d_%H%M")
        a4.download_button(
            f"📥 Export {'Selected' if selected_ids else 'All'}",
            data=export_df.to_csv(index=False).encode(),
            file_name=f"IFOA_{timestamp}.csv",
            mime="text/csv",
            use_container_width=True,
        )

        if selected_ids and a5.button("📋 Copy IDs", use_container_width=True):
            st.code(", ".join(str(i) for i in selected_ids))
    else:
        st.info("No jobs found for this query.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 6 — SCRAPER CONFIG EDITOR
# ══════════════════════════════════════════════════════════════════════════════
with tabs[5]:
    st.subheader("⚙️ Scraper Configuration Editor")
    st.caption("Edit per-scraper limits, timeouts, and enable/disable scrapers without touching code.")

    if not st.session_state.authenticated:
        st.warning("🔒 Admin login required to edit configurations.")
    else:
        scraper_list = list_scrapers()

        # Search/filter
        cfg_search = st.text_input("🔍 Filter scrapers", placeholder="type a name…", key="cfg_search")
        filtered = [s for s in scraper_list if cfg_search.lower() in s.lower()] if cfg_search else scraper_list

        st.markdown(f"Showing **{len(filtered)}** of **{len(scraper_list)}** scrapers")

        for s_name in filtered:
            cfg, _ = ScraperConfig.objects.get_or_create(
                scraper_name=s_name,
                defaults={"is_enabled": True, "timeout": 300, "retry_count": 3},
            )
            with st.expander(f"{'🟢' if cfg.is_enabled else '⚫'} {s_name.upper()}", expanded=False):
                col_a, col_b, col_c = st.columns(3)
                new_enabled   = col_a.checkbox("Enabled", value=cfg.is_enabled, key=f"e_{s_name}")
                new_max_jobs  = col_b.number_input("Max Jobs (0=unlimited)", min_value=0,
                                                    value=cfg.max_jobs or 0, key=f"mj_{s_name}")
                new_max_pages = col_c.number_input("Max Pages (0=unlimited)", min_value=0,
                                                    value=cfg.max_pages or 0, key=f"mp_{s_name}")
                col_d, col_e = st.columns(2)
                new_timeout   = col_d.number_input("Timeout (s)", min_value=30, max_value=3600,
                                                    value=cfg.timeout, key=f"to_{s_name}")
                new_retry     = col_e.number_input("Retry Count", min_value=0, max_value=10,
                                                    value=cfg.retry_count, key=f"rc_{s_name}")
                new_desc      = st.text_area(
                    "Notes / Description",
                    value=cfg.description or "",
                    key=f"desc_{s_name}", height=68,
                )

                save_col, stat_col = st.columns([1, 3])
                if save_col.button("💾 Save", key=f"save_{s_name}", type="primary", use_container_width=True):
                    cfg.is_enabled   = new_enabled
                    cfg.max_jobs     = new_max_jobs or None
                    cfg.max_pages    = new_max_pages or None
                    cfg.timeout      = new_timeout
                    cfg.retry_count  = new_retry
                    cfg.description  = new_desc.strip() or None
                    cfg.save()
                    refresh_schedules()
                    st.success(f"✅ Config for {s_name} saved.")

                stat_col.markdown(
                    f"Runs: **{cfg.total_runs}** &nbsp;|&nbsp; "
                    f"✅ {cfg.successful_runs} &nbsp;|&nbsp; "
                    f"❌ {cfg.failed_runs} &nbsp;|&nbsp; "
                    f"Last: {cfg.last_run.strftime('%d %b %H:%M') if cfg.last_run else '—'}"
                )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 7 — WEBHOOK ALERTS
# ══════════════════════════════════════════════════════════════════════════════
with tabs[6]:
    st.subheader("🔔 Webhook Alerts")
    st.caption(
        "Receive real-time push notifications when a scraper completes or fails. "
        "Supports **ntfy.sh** (recommended), Slack webhooks, and custom HTTP POST."
    )

    if not st.session_state.authenticated:
        st.warning("🔒 Admin login required to manage alerts.")
    else:
        # ── Add / Edit form ──────────────────────────────────────────────
        with st.expander("➕ Add / Edit Webhook", expanded=False):
            with st.form("webhook_form"):
                wh_name     = st.text_input("Name *", placeholder="e.g. My Phone")
                wh_provider = st.selectbox("Provider", ["ntfy", "slack", "custom"])
                wh_url      = st.text_input(
                    "URL *",
                    placeholder="ntfy → https://ntfy.sh/YOUR_TOPIC | Slack → https://hooks.slack.com/…",
                    help="For ntfy.sh: just paste the full topic URL like https://ntfy.sh/aeroops-alerts"
                )
                wh_event    = st.selectbox("Notify on", ["all", "completed", "failed"])
                wh_active   = st.checkbox("Active", value=True)

                col_test, col_save = st.columns(2)
                test_sent = col_test.form_submit_button("🧪 Test Ping")
                saved     = col_save.form_submit_button("💾 Save", type="primary")

                if test_sent and wh_url:
                    from scraper_manager.webhook_notify import _fire_webhook
                    _fire_webhook(wh_url, {
                        "title":    "AeroOps Test Ping",
                        "message":  "✅ Your AeroOps webhook is configured correctly!",
                        "tags":     "white_check_mark",
                        "priority": "default",
                    }, wh_provider)
                    st.success("Test ping dispatched (check your endpoint in a few seconds).")

                if saved:
                    if not wh_name or not wh_url:
                        st.error("Name and URL are required.")
                    else:
                        obj, created = WebhookConfig.objects.update_or_create(
                            name=wh_name,
                            defaults={"provider": wh_provider, "url": wh_url,
                                      "on_event": wh_event, "is_active": wh_active}
                        )
                        st.success(f"{'Created' if created else 'Updated'} webhook: {wh_name}")
                        st.rerun()

        # ── Existing webhooks ─────────────────────────────────────────────
        hooks = WebhookConfig.objects.all()
        if hooks.exists():
            for hook in hooks:
                hc, hd, htgl = st.columns([4, 1, 1])
                hc.markdown(f"**{hook.name}** — `{hook.provider}` → `{hook.on_event}` "
                            f"| {hook.url[:55]}{'…' if len(hook.url)>55 else ''}")
                hd.markdown(f"{'🟢' if hook.is_active else '⚫'} {'On' if hook.is_active else 'Off'}")
                if htgl.button("🗑", key=f"del_hook_{hook.id}", help="Delete this webhook"):
                    hook.delete()
                    st.rerun()
        else:
            st.info("No webhooks configured yet. Add one above.")

        st.markdown("""
        ---
        **Quick Setup — ntfy.sh (Free, no account needed)**
        1. Install the **ntfy** app on your phone ([iOS](https://apps.apple.com/app/ntfy/id1625396347) / [Android](https://play.google.com/store/apps/details?id=io.heckel.ntfy))
        2. Subscribe to a unique topic name, e.g. `aeroops-MY-SECRET`
        3. Paste `https://ntfy.sh/aeroops-MY-SECRET` as the URL above
        4. Hit "Test Ping" — you'll get a notification immediately 📱
        """)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 8 — DEDUP & CLEANUP
# ══════════════════════════════════════════════════════════════════════════════
with tabs[7]:
    st.subheader("🔄 Deduplication & Cleanup Center")

    if not st.session_state.authenticated:
        st.warning("🔒 Admin login required.")
    else:
        dedup_tab, cleanup_tab = st.tabs(["🔁 Duplicate Jobs", "🗑 Job Expiry & Cleanup"])

        # ── Deduplication ─────────────────────────────────────────────────
        with dedup_tab:
            st.markdown("**Find jobs with identical title + company (different URLs)**")
            st.caption("Review potential duplicates before deletion to avoid losing unique listings.")

            # Find duplicates via SQL annotation
            from django.db.models import Count, Min
            dupes = (
                Job.objects.values("title", "company")
                .annotate(count=Count("id"), first_id=Min("id"))
                .filter(count__gt=1)
                .order_by("-count")[:50]
            )
            dupes_list = list(dupes)

            if dupes_list:
                st.markdown(f"Found **{len(dupes_list)}** duplicate groups (showing first 50).")

                for d in dupes_list[:20]:
                    with st.expander(f"[{d['count']}x] {d['company']} — {d['title'][:60]}", expanded=False):
                        # Fetch all records in this group
                        group_qs = Job.objects.filter(
                            title=d["title"], company=d["company"]
                        ).values("id", "url", "source", "posted_date", "retrieved_date", "status")
                        group_df = pd.DataFrame(list(group_qs))
                        st.dataframe(group_df, hide_index=True, use_container_width=True,
                                     column_config={"url": st.column_config.LinkColumn("URL")})

                        if st.button(
                            f"🗑 Keep earliest, delete {d['count']-1} newer",
                            key=f"dedup_{d['first_id']}", type="secondary"
                        ):
                            keep_id = d["first_id"]
                            deleted, _ = Job.objects.filter(
                                title=d["title"], company=d["company"]
                            ).exclude(id=keep_id).delete()
                            st.success(f"Deleted {deleted} duplicates.")
                            st.rerun()
            else:
                st.success("✅ No duplicate jobs found in the database!")

        # ── Cleanup ───────────────────────────────────────────────────────
        with cleanup_tab:
            url_chk_tab, age_chk_tab = st.tabs(["🌐 URL Validity Checker", "📅 Age-based Expiry"])

            # ── URL VALIDITY CHECKER ──────────────────────────────────────────
            with url_chk_tab:
                st.markdown("**Scan job URLs and auto-expire dead listings.**")
                st.caption(
                    "Checks each URL for 404s, redirects to homepage, or page text containing "
                    "'job not found', 'position filled', etc."
                )

                uc1, uc2, uc3 = st.columns(3)
                check_source = uc1.text_input("Filter by source", placeholder="eurowings (blank=all)")
                check_limit  = uc2.number_input("Max URLs to check", min_value=5, max_value=500, value=50)
                check_action = uc3.selectbox("On detection", ["Mark as expired", "Hard delete", "Dry-run (log only)"])

                # Phrases that indicate the job is no longer available
                DEAD_PATTERNS = [
                    "job not found", "position no longer", "this position has been filled",
                    "no longer available", "vacancy has been closed", "posting has expired",
                    "job has expired", "application closed", "this job is no longer",
                    "position is no longer", "role has been filled", "page not found",
                    "we couldn't find", "job listing not found", "requisition closed",
                    "this role is no longer accepting", "position filled",
                    "this job has been removed", "this vacancy is closed",
                ]

                def check_url_alive(url: str, timeout: int = 8) -> tuple:
                    """Returns (is_alive: bool, reason: str)"""
                    from urllib.parse import urlparse

                    headers = {"User-Agent": "Mozilla/5.0 (AeroOps URL Checker)"}
                    try:
                        resp = requests.get(url, headers=headers, timeout=timeout)
                        status_code = resp.status_code
                        if status_code in (404, 410):
                            return False, f"HTTP {status_code}"
                        if status_code == 403:
                            return True, "HTTP 403 (access denied)"

                        final_url = resp.url
                        content = resp.text.lower()
                        for pat in DEAD_PATTERNS:
                            if pat in content:
                                return False, f"Page text: '{pat}'"

                        orig_path = urlparse(url).path.strip("/")
                        final_path = urlparse(final_url).path.strip("/")
                        if orig_path and not final_path:
                            return False, "Redirected to homepage"
                        return True, "OK"
                    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
                        err = str(exc)
                        return False, f"Connection failed: {err[:80]}"
                    except requests.exceptions.RequestException as exc:
                        err = str(exc)
                        return True, f"Unhandled: {err[:60]}"

                if st.button("🔍 Start URL Scan", type="primary"):
                    chk_q = Job.objects.exclude(status="expired").exclude(url="")
                    if check_source:
                        chk_q = chk_q.filter(source__icontains=check_source)
                    chk_q = chk_q.order_by("-retrieved_date")[:check_limit]
                    jobs_to_check = list(chk_q.values("id", "title", "company", "url"))

                    if not jobs_to_check:
                        st.warning("No jobs match current filters.")
                    else:
                        dead_ids  = []
                        dead_rows = []
                        prog      = st.progress(0, text="Starting URL scan…")
                        total_chk = len(jobs_to_check)

                        for idx, job in enumerate(jobs_to_check):
                            alive, reason = check_url_alive(job["url"])
                            prog.progress(
                                (idx + 1) / total_chk,
                                text=f"Checking {idx+1}/{total_chk}: {job['company'][:22]}"
                            )
                            if not alive:
                                dead_ids.append(job["id"])
                                dead_rows.append({
                                    "ID":      job["id"],
                                    "Company": job["company"],
                                    "Title":   job["title"][:52],
                                    "Reason":  reason,
                                    "URL":     job["url"],
                                })

                        prog.empty()

                        if dead_rows:
                            st.warning(f"Found **{len(dead_rows)}** dead URLs out of {total_chk} checked.")
                            dead_df = pd.DataFrame(dead_rows)
                            st.dataframe(dead_df, hide_index=True, use_container_width=True,
                                         column_config={"URL": st.column_config.LinkColumn("URL")})

                            if check_action == "Mark as expired":
                                n = Job.objects.filter(id__in=dead_ids).update(status="expired")
                                st.success(f"✅ Marked {n} jobs as expired.")
                            elif check_action == "Hard delete":
                                n, _ = Job.objects.filter(id__in=dead_ids).delete()
                                st.success(f"🗑 Hard-deleted {n} jobs.")
                            else:
                                st.info(f"Dry-run: would act on {len(dead_ids)} jobs. No changes made.")

                            timestamp = timezone.localtime(timezone.now()).strftime("%Y%m%d_%H%M")
                            st.download_button(
                                "📥 Export Dead URLs CSV",
                                data=dead_df.to_csv(index=False).encode(),
                                file_name=f"dead_urls_{timestamp}.csv",
                                mime="text/csv",
                            )
                        else:
                            st.success(f"✅ All {total_chk} URLs appear to be alive!")

            # ── AGE-BASED EXPIRY ──────────────────────────────────────────────
            with age_chk_tab:
                st.markdown("**Expire or remove job listings based on age.**")

                cc1, cc2 = st.columns(2)
                exp_days  = cc1.number_input("Expire jobs older than (days)", min_value=7,
                                              max_value=365, value=90)
                hist_days = cc2.number_input("Purge scraper history older than (days)", min_value=7,
                                              max_value=365, value=30)
                hard_del  = st.checkbox(
                    "Hard-delete (permanently removes; otherwise marks as 'expired')", value=False)

                expirable_count = Job.objects.filter(
                    retrieved_date__lt=timezone.now() - timedelta(days=exp_days)
                ).exclude(status="expired").count()
                hist_count = ScraperJob.objects.filter(
                    created_at__lt=timezone.now() - timedelta(days=hist_days),
                    status__in=["completed", "failed", "cancelled"],
                ).count()

                st.markdown(f"""
                <div class="stat-card" style="margin-bottom:12px;">
                    <div style="display:flex;gap:32px;">
                        <div><div class="stat-label">Jobs to expire</div>
                             <div class="stat-val" style="font-size:22px;">{expirable_count:,}</div></div>
                        <div><div class="stat-label">History records to purge</div>
                             <div class="stat-val" style="font-size:22px;">{hist_count:,}</div></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                cl1, cl2 = st.columns(2)
                if cl1.button("🧹 Run Cleanup Now", type="primary", use_container_width=True):
                    cutoff      = timezone.now() - timedelta(days=exp_days)
                    hist_cutoff = timezone.now() - timedelta(days=hist_days)
                    old = Job.objects.filter(retrieved_date__lt=cutoff).exclude(status="expired")
                    if hard_del:
                        n, _ = old.delete()
                        st.success(f"Hard-deleted {n} jobs.")
                    else:
                        n = old.update(status="expired")
                        st.success(f"Marked {n} jobs as expired.")
                    h_del, _ = ScraperJob.objects.filter(
                        created_at__lt=hist_cutoff,
                        status__in=["completed", "failed", "cancelled"],
                    ).delete()
                    st.success(f"Purged {h_del} scraper history records.")
                    st.rerun()

                if cl2.button("👁 Dry-Run (preview)", use_container_width=True):
                    st.info(
                        f"Would {'delete' if hard_del else 'expire'} **{expirable_count:,}** jobs "
                        f"and purge **{hist_count:,}** history records. No changes made."
                    )

                st.markdown("---")
                st.markdown("**⏰ Scheduled Auto-Cleanup**")
                st.info(
                    "Add to `crontab -e` to run daily at 3am:\n"
                    "```\n"
                    "0 3 * * * cd '/home/rajat/Desktop/AeroOps Intel/scraper-standalone' && "
                    "./venv/bin/python manage.py cleanup_jobs --days 90 >> logs/cleanup.log 2>&1\n"
                    "```"
                )


# ── Footer ────────────────────────────────────────────────────────────────
st.divider()
st.caption("✈ IFOA Scrapers 2026")
