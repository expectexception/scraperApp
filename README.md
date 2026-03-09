# Scraper Standalone Project

This folder is now the full standalone scraper project.

- Scraping runs here, independent of backend runtime.
- Backend only reads jobs from DB.
- Job status verification also runs here.

## Setup

```bash
cd "/home/rajat/Desktop/AeroOps Intel/scraper-standalone"
cp .env.example .env
```

Set DB values in `.env` to your existing database.

## Run

```bash
python manage.py run_scraper --list
python manage.py run_scraper emirates --max-jobs 20 --max-pages 2
python manage.py run_scraper all --max-jobs 50
python manage.py verify_job_active --age-days 7 --limit 100
```

Or:

```bash
bash start_scraper_service.sh run_scraper airindia --max-jobs 10
```

## Notes

- Tables are reused from existing DB (`jobs`, `company_mapping`, scraper tracking tables).
- No backend scraper app is required anymore.
