# AeroOps Scraper Service

Standalone scraper service with a Django API backend and a React + TypeScript frontend.

## Architecture

- Backend API: Django + DRF on `:8008`
- Frontend UI: React static build served on `:8501`
- Scraper jobs: Managed by `manage.py run_scraper` / Celery tasks

## Setup

```bash
cd "/home/rajat/Desktop/AeroOps Intel/scraper-standalone"
cp .env.example .env
cp frontend/.env.example frontend/.env
```

Recommended environment variables:

- `DASHBOARD_USERNAME` (default: `admin`)
- `DASHBOARD_PASSWORD` (required for protected API actions)
- `FRONTEND_URL` (default: `http://localhost:8501`)

## Start Services

```bash
./service.sh start
./service.sh status
```

`service.sh` starts:

- Django API via gunicorn (`:8008`)
- React frontend static server (`:8501`)

## Local Frontend Development

```bash
cd frontend
npm install
npm run dev
```

## Scraper CLI Examples

```bash
python manage.py run_scraper --list
python manage.py run_scraper emirates --max-jobs 20 --max-pages 2
python manage.py run_scraper all --max-jobs 50
python manage.py verify_job_active --age-days 7 --limit 100
```
