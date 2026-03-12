import os
import sys
import subprocess
import signal
import time
import pandas as pd
import streamlit as st
import psutil
from datetime import datetime, timedelta
import plotly.express as px
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

import warnings
# Suppress Django model re-registration warnings during Streamlit reruns
warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*Model '.*' was already registered.*")

# --- Django Integration (Safely) ---
if "DJANGO_SETTINGS_MODULE" not in os.environ:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "scraper_service.settings")

import django
from django.conf import settings

if not settings.configured:
    try:
        django.setup()
    except Exception as e:
        st.error(f"Django Setup Error: {e}")

from scraper_manager.models import ScraperJob, ScraperConfig, ScrapedURL
from jobs.models import Job
from scraper_manager.scrapers import list_scrapers

# --- Page Config ---
st.set_page_config(
    page_title="IFOA | Job Intelligence",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)

if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'active_processes' not in st.session_state:
    st.session_state.active_processes = {}

def sync_active_processes():
    """Recover active processes from DB and verify they are still running"""
    active_jobs = ScraperJob.objects.filter(status='running').order_by('-started_at')
    current_active = {}
    
    for job in active_jobs:
        if job.pid:
            try:
                p = psutil.Process(job.pid)
                if p.is_running() and "python" in p.name().lower():
                    # Process is still alive
                    log_file = os.path.join("scraper_logs", f"{job.scraper_name}.log")
                    current_active[job.scraper_name] = {
                        "pid": job.pid,
                        "start": job.started_at,
                        "log": log_file,
                        "job_id": job.id
                    }
                else:
                    # Stale job in DB
                    job.status = 'failed'
                    job.error_message = "Process terminated unexpectedly."
                    job.save()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                job.status = 'failed'
                job.error_message = "Process no longer accessible."
                job.save()
    
    st.session_state.active_processes = current_active

# Perform sync on load
sync_active_processes()

# --- Scheduler Setup (Singleton-like) ---
@st.cache_resource
def get_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.start()
    return scheduler

sched = get_scheduler()

def trigger_scheduled_scraper(name):
    # This runs in a background thread from APScheduler
    cmd = [sys.executable, "manage.py", "run_scraper", name]
    subprocess.Popen(cmd)

def refresh_schedules():
    """Sync APScheduler with ScraperConfig models"""
    sched.remove_all_jobs()
    configs = ScraperConfig.objects.filter(is_enabled=True, schedule_enabled=True)
    for cfg in configs:
        if cfg.schedule_cron:
            try:
                sched.add_job(
                    trigger_scheduled_scraper,
                    CronTrigger.from_crontab(cfg.schedule_cron),
                    args=[cfg.scraper_name],
                    id=f"job_{cfg.scraper_name}",
                    replace_existing=True
                )
            except Exception as e:
                print(f"Error scheduling {cfg.scraper_name}: {e}")

def validate_scraper_config(name):
    """Basic validation of scraper setup"""
    try:
        from scraper_manager.scrapers import get_scraper
        from scraper_manager.db_manager import DjangoDBManager
        db = DjangoDBManager()
        get_scraper(name, settings.CONFIG if hasattr(settings, 'CONFIG') else {}, db_manager=db)
        return True, "Configuration valid. Scraper initialized successfully."
    except Exception as e:
        return False, f"Validation Failed: {str(e)}"

# Initial sync
if 'scheduler_synced' not in st.session_state:
    refresh_schedules()
    st.session_state.scheduler_synced = True

# --- Clean SaaS CSS (Slate/Zinc Theme) ---
st.markdown("""
    <style>
    :root {
        --primary: #3b82f6;
        --bg-main: #020617;
        --bg-card: #0f172a;
        --border: #1e293b;
        --text-main: #f8fafc;
        --text-muted: #94a3b8;
    }
    
    .stApp {
        background-color: var(--bg-main);
        color: var(--text-main);
    }
    
    /* Hide Streamlit Default UI but allow Sidebar Toggle */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    [data-testid="stDeployButton"] {display:none;}
    
    [data-testid="stHeader"] {
        background: rgba(0,0,0,0) !important;
        color: var(--text-muted) !important;
    }
    
    /* Global Styles */
    div[data-testid="stExpander"] {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 8px;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #030712 !important;
        border-right: 2px solid var(--primary) !important; /* Prominent accent border */
    }
    
    /* Metric Cards */
    .stat-card {
        background: var(--bg-card);
        border: 1px solid var(--border);
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
    }
    .stat-val {
        font-size: 24px;
        font-weight: 700;
        color: var(--primary);
    }
    .stat-label {
        font-size: 14px;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    /* Tab Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 8px 16px;
        border-radius: 6px;
        color: var(--text-muted);
    }
    .stTabs [aria-selected="true"] {
        background-color: var(--border) !important;
        color: var(--text-main) !important;
    }
    
    /* Buttons */
    .stButton>button {
        border-radius: 6px !important;
        font-weight: 500 !important;
    }
    
    /* Custom Table Style */
    .stDataFrame {
        border: 1px solid var(--border);
        border-radius: 8px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- Helper Functions ---

def run_scraper(name):
    log_dir = "scraper_logs"
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"{name}.log")
    
    # Pre-create job to have immediate Job ID
    job = ScraperJob.objects.create(
        scraper_name=name,
        status='running',
        started_at=datetime.now(),
        triggered_by='dashboard'
    )
    
    cmd = [sys.executable, "manage.py", "run_scraper", name, "--job-id", str(job.id)]
    # Use start_new_session=True to detach the process from the dashboard
    with open(log_file, "a") as f:
        process = subprocess.Popen(cmd, stdout=f, stderr=f, start_new_session=True)
    
    st.session_state.active_processes[name] = {
        "pid": process.pid,
        "start": job.started_at,
        "log": log_file,
        "job_id": job.id,
        "last_size": 0
    }

def stop_process(pid):
    try:
        os.kill(pid, signal.SIGTERM)
        return True
    except:
        return False

# --- Sidebar ---
with st.sidebar:
    st.title("IFOA")
    st.caption("Job Scraping Intelligence")
    
    if not st.session_state.authenticated:
        with st.form("auth_form"):
            user = st.text_input("Username")
            pwd = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                if user == "admin" and pwd == "aero123":
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("Invalid credentials")
    else:
        st.success("Authenticated")
        if st.button("Logout"):
            st.session_state.authenticated = False
            st.rerun()
            
    st.divider()
    
    # System Health
    st.subheader("System Pulse")
    
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent
    
    # Pulse Indicator
    health_color = "#22c55e" if cpu < 80 and ram < 90 else "#eab308"
    st.markdown(f"""
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 20px;">
            <div style="width: 12px; height: 12px; background: {health_color}; border-radius: 50%; box-shadow: 0 0 10px {health_color};"></div>
            <span style="font-size: 14px; font-weight: 600; color: var(--text-main);">Engine Online</span>
        </div>
    """, unsafe_allow_html=True)

    st.write(f"CPU Utilization: {cpu}%")
    st.progress(cpu/100)
    st.write(f"RAM Allocation: {ram}%")
    st.progress(ram/100)

# --- Main Page ---
st.title("Dashboard")

# Stats Grid
s1, s2, s3, s4 = st.columns(4)
stats = [
    ("Total Jobs", Job.objects.count()),
    ("Active Tasks", len(st.session_state.active_processes)),
    ("New Today", Job.objects.filter(retrieved_date__date=datetime.now().date()).count()),
    ("Errors", ScraperJob.objects.filter(status="failed").count())
]

for col, (label, val) in zip([s1, s2, s3, s4], stats):
    col.markdown(f"""
        <div class="stat-card">
            <div class="stat-label">{label}</div>
            <div class="stat-val">{val:,}</div>
        </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

tabs = st.tabs(["🛰️ Command Center", "📅 Scheduler", "📊 Analytics", "🔍 Job Explorer"])

# --- Tab 1: Command Center ---
with tabs[0]:
    c_head, c_all = st.columns([5, 1])
    c_head.subheader("Live Scraper Control")
    
    # Run All Button
    is_all_running = "all" in st.session_state.active_processes
    if is_all_running:
        if c_all.button("⏹ Stop All Missions", type="secondary", use_container_width=True, help="Terminate global mission"):
            pid = st.session_state.active_processes['all']['pid']
            stop_process(pid)
            del st.session_state.active_processes['all']
            st.rerun()
    else:
        if c_all.button("🚀 Start All Sensors", type="primary", use_container_width=True, help="Initiate batch mission"):
            run_scraper("all")
            st.toast("Mission control initiated for all scrapers.")
            st.rerun()
    
    # Active Processes Monitor
    with st.expander("📺 Continuous Mission Monitor", expanded=True):
        if st.session_state.active_processes:
            monitor_data = []
            for name, info in list(st.session_state.active_processes.items()):
                # Check if process is still running
                try:
                    p = psutil.Process(info['pid'])
                    if not p.is_running():
                        del st.session_state.active_processes[name]
                        continue
                    age = datetime.now() - info['start']
                    # Fetch live progress from DB
                    job = ScraperJob.objects.get(id=info['job_id'])
                    monitor_data.append({
                        "Scraper": name.upper(),
                        "Runtime": str(age).split(".")[0],
                        "Progress": f"{job.progress}%",
                        "PID": info['pid'],
                        "Job ID": job.id
                    })
                except:
                    del st.session_state.active_processes[name]
            
            if monitor_data:
                m_df = pd.DataFrame(monitor_data)
                st.dataframe(m_df, width="stretch", hide_index=True)
                
                # Enhanced Live Log Viewer
                st.markdown("---")
                primary_proc = list(st.session_state.active_processes.items())[0]
                p_name, p_info = primary_proc
                job = ScraperJob.objects.get(id=p_info['job_id'])
                
                log_col, prog_col, refresh_col = st.columns([3, 1, 1])
                log_col.markdown(f"**Live Output: {p_name.upper()}**")
                prog_col.progress(job.progress/100, text=f"{job.progress}%")
                
                # Auto-refresh mechanism for logs
                if refresh_col.button("🔄 Refresh", use_container_width=True):
                    st.rerun()
                
                log_p = p_info['log']
                if os.path.exists(log_p):
                    with open(log_p, 'r') as f:
                        lines = f.readlines()[-20:] # Show more lines
                        st.code("".join(lines), language="text")
                
                # Subtle auto-rerun if processes are active to keep metrics fresh
                time.sleep(1)
                st.rerun()
            else:
                st.info("Waiting for task data...")

    # Control Grid
    scrapers = list_scrapers()
    cols = st.columns(3)
    for i, s_name in enumerate(scrapers):
        with cols[i % 3]:
            with st.container(border=True):
                c_head, c_btn = st.columns([2, 1])
                # Determine Status
                is_running = s_name in st.session_state.active_processes
                is_batch_active = "all" in st.session_state.active_processes
                
                status_label = "IDLE"
                status_color = "var(--text-muted)"
                pulse = False
                
                if is_running:
                    status_label = "RUNNING MISSION"
                    status_color = "var(--primary)"
                    pulse = True
                elif is_batch_active:
                    status_label = "PENDING (BATCH)"
                    status_color = "#eab308" # Yellow for pending
                
                if pulse:
                    st.markdown(f"""
                        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 5px;">
                            <div style="width: 8px; height: 8px; background: #3b82f6; border-radius: 50%; animation: pulse 1.5s infinite;"></div>
                            <span style="font-size: 12px; color: {status_color}; font-weight: 700;">{status_label}</span>
                        </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 5px;">
                            <div style="width: 8px; height: 8px; background: {status_color}; border-radius: 50%;"></div>
                            <span style="font-size: 12px; color: {status_color}; font-weight: 600;">{status_label}</span>
                        </div>
                    """, unsafe_allow_html=True)

                if is_running or is_batch_active:
                    # Determine which PID to stop
                    current_pid = st.session_state.active_processes.get(s_name, {}).get('pid') or st.session_state.active_processes.get('all', {}).get('pid')
                    
                    if c_btn.button("⏹ Stop", key=f"stop_{s_name}", type="secondary", use_container_width=True, help="Terminate mission"):
                        if current_pid:
                            stop_process(current_pid)
                        if s_name in st.session_state.active_processes:
                            del st.session_state.active_processes[s_name]
                        if is_batch_active:
                             # Stopping a member of a batch stops the batch
                             del st.session_state.active_processes['all']
                        st.rerun()
                else:
                    btn_col1, btn_col2 = c_btn.columns(2)
                    if btn_col1.button("🔍", key=f"test_{s_name}", use_container_width=True, help="Verify configuration"):
                        valid, msg = validate_scraper_config(s_name)
                        if valid: st.success(msg)
                        else: st.error(msg)
                        
                    if btn_col2.button("▶ Run", key=f"run_{s_name}", type="primary", use_container_width=True, help="Start mission"):
                        run_scraper(s_name)
                        st.rerun()

# --- Tab 2: Scheduler ---
with tabs[1]:
    st.subheader("Background Mission Schedules")
    
    if not st.session_state.authenticated:
        st.warning("Please login as administrator to manage schedules.")
    else:
        configs = ScraperConfig.objects.all().order_by('scraper_name')
        
        # Add new schedule form
        with st.expander("🆕 Add/Update Schedule"):
            with st.form("sched_form"):
                s_name = st.selectbox("Select Scraper", scrapers)
                cron = st.text_input("Cron Expression", placeholder="0 */6 * * * (Every 6 hours)")
                enabled = st.checkbox("Schedule Enabled", value=True)
                if st.form_submit_button("Update Schedule"):
                    cfg, _ = ScraperConfig.objects.get_or_create(scraper_name=s_name)
                    cfg.schedule_cron = cron
                    cfg.schedule_enabled = enabled
                    cfg.save()
                    refresh_schedules()
                    st.success(f"Schedule for {s_name} updated.")
                    st.rerun()

        # List existing schedules
        sched_items = []
        for c in configs:
            if c.schedule_cron:
                sched_items.append({
                    "Scraper": c.scraper_name.upper(),
                    "Cron": c.schedule_cron,
                    "Status": "✅ Active" if c.schedule_enabled else "⏸️ Paused",
                    "Next Run": str(sched.get_job(f"job_{c.scraper_name}").next_run_time).split("+")[0] if sched.get_job(f"job_{c.scraper_name}") else "N/A"
                })
        
        if sched_items:
            s_df = pd.DataFrame(sched_items)
            st.dataframe(s_df, width="stretch", hide_index=True)
        else:
            st.info("No schedules configured.")

# --- Tab 3: Analytics ---
with tabs[2]:
    st.subheader("Data Insights")
    c1, c2 = st.columns(2)
    
    # Trend Chart
    with c1:
        st.markdown("**Scraping Velocity (Last 14 Days)**")
        dates = [datetime.now().date() - timedelta(days=i) for i in range(13, -1, -1)]
        counts = [Job.objects.filter(retrieved_date__date=d).count() for d in dates]
        f1 = px.line(x=dates, y=counts, labels={'x': 'Date', 'y': 'New Jobs'})
        f1.update_layout(height=300, margin=dict(l=20, r=20, t=20, b=20), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(f1, width="stretch")
        
    # Source Distribution
    with c2:
        st.markdown("**Top Data Sources**")
        sources = Job.objects.values('source').annotate(count=django.db.models.Count('id')).order_by('-count')[:8]
        if sources:
            f2 = px.bar(sources, x='source', y='count', color='count')
            f2.update_layout(height=300, margin=dict(l=20, r=20, t=20, b=20), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(f2, width="stretch")

# --- Tab 4: Job Explorer ---
with tabs[3]:
    st.subheader("Data Archive")
    srch = st.text_input("Search Archive", placeholder="Job title, company...")
    
    q = Job.objects.all().order_by('-retrieved_date')
    if srch:
        q = q.filter(django.db.models.Q(title__icontains=srch) | django.db.models.Q(company__icontains=srch))
        
    df = pd.DataFrame(list(q[:100].values('id', 'title', 'company', 'location', 'posted_date', 'url')))
    if not df.empty:
        df['Select'] = False
        sel_df = st.data_editor(df, column_config={"url": st.column_config.LinkColumn("Link")}, width="stretch", hide_index=True)
        
        c1, c2 = st.columns([1, 4])
        selected = sel_df[sel_df['Select'] == True]['id'].tolist()
        
        with c1:
            if selected:
                if st.button(f"Delete Selected ({len(selected)})"):
                    Job.objects.filter(id__in=selected).delete()
                    st.success("Deleted successfully")
                    st.rerun()
            else:
                st.button("Delete Selected", disabled=True)
                
        with c2:
            # Export all matching jobs (not just the 100 shown in preview)
            csv = q.to_csv() if hasattr(q, 'to_csv') else df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Export Search Results (CSV)",
                data=df.to_csv(index=False).encode('utf-8'),
                file_name=f"IFOA_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
            )
    else:
        st.info("No data found.")

st.divider()
st.caption("IFOA Intelligence 2026 | Built for Industrial Scalability")
