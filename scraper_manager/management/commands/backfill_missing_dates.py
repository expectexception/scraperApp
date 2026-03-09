from django.core.management.base import BaseCommand
from django.db import transaction
from jobs.models import Job
from scraper_manager.scrapers.base_scraper import BaseScraper
import asyncio
import re
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Backfill missing posted_date for jobs by fetching job pages and extracting datePosted from JSON-LD, meta tags, or regex.'

    def add_arguments(self, parser):
        parser.add_argument('--source', type=str, help='Source to process (e.g., indigo, aviationjobsearch)')
        parser.add_argument('--limit', type=int, default=0, help='Limit number of jobs to process (0 = all)')
        parser.add_argument('--dry-run', action='store_true', help='Do not save changes, just report')

    def handle(self, *args, **options):
        source = options.get('source')
        limit = options.get('limit', 0)
        dry = options.get('dry_run', False)

        if not source:
            self.stdout.write(self.style.ERROR('Please provide --source to backfill'))
            return

        qs = Job.objects.filter(source__iexact=source, posted_date__isnull=True).order_by('-created_at')
        if limit and limit > 0:
            qs = qs[:limit]

        jobs = list(qs)
        total = len(jobs)
        if not jobs:
            self.stdout.write(self.style.SUCCESS(f'No jobs for {source} need backfilling.'))
            return

        self.stdout.write(f'Processing {total} jobs from source={source} (dry_run={dry})...')

        scraper = BaseScraper({}, source)

        async def fetch_and_parse():
            results = []
            try:
                from playwright.async_api import async_playwright
            except Exception as e:
                self.stderr.write(f'Playwright not available: {e}')
                return results

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(user_agent=scraper.get_random_user_agent())
                page = await context.new_page()

                for job in jobs:
                    url = job.url
                    parsed_date = None
                    error = None
                    html = ''
                    body = ''
                    try:
                        try:
                            await page.goto(url, wait_until='networkidle', timeout=20000)
                        except Exception:
                            try:
                                await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                            except Exception:
                                pass
                        html = await page.content()
                        body = await page.inner_text('body')

                        # JSON-LD first
                        for m in re.findall(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html, re.DOTALL|re.IGNORECASE):
                            try:
                                import json as _json
                                data = _json.loads(m)
                                items = data if isinstance(data, list) else [data]
                                for item in items:
                                    if isinstance(item, dict) and (item.get('@type') and 'JobPosting' in item.get('@type')):
                                        if item.get('datePosted'):
                                            parsed = scraper.parse_posted_date(item.get('datePosted'))
                                            if parsed:
                                                parsed_date = parsed
                                                break
                                if parsed_date:
                                    break
                            except Exception:
                                continue

                        # meta tags
                        if not parsed_date:
                            for m in re.findall(r'<meta[^>]+(?:name|property)=["\']([^"\']+)["\'][^>]*content=["\']([^"\']+)["\']', html, re.IGNORECASE):
                                name = m[0].lower()
                                val = m[1].strip()
                                if any(k in name for k in ('date','publish','published','modified','updated')):
                                    pd = scraper.parse_posted_date(val)
                                    if pd:
                                        parsed_date = pd
                                        break

                        # time tags
                        if not parsed_date:
                            for t in re.findall(r'<time[^>]*>([^<]+)</time>', html, re.IGNORECASE):
                                pd = scraper.parse_posted_date(t.strip())
                                if pd:
                                    parsed_date = pd
                                    break

                        # relative patterns "X ago"
                        if not parsed_date and body:
                            for r in re.findall(r'\b\d+\s*(?:minute|hour|day|week|month|year)s?\s+ago\b', body, re.IGNORECASE):
                                pd = scraper.parse_posted_date(r)
                                if pd:
                                    parsed_date = pd
                                    break

                    except Exception as e:
                        error = str(e)
                        logger.exception('Error processing %s', url)

                    # If Playwright page fetch failed, fallback to requests
                    if not parsed_date and (not html or len(html) < 200):
                        try:
                            import requests
                            headers = {'User-Agent': scraper.get_random_user_agent()}
                            r = requests.get(url, headers=headers, timeout=15)
                            if r.status_code == 200 and r.text:
                                html = r.text
                                body = r.text
                                for m in re.findall(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html, re.DOTALL|re.IGNORECASE):
                                    try:
                                        import json as _json
                                        data = _json.loads(m)
                                        items = data if isinstance(data, list) else [data]
                                        for item in items:
                                            if isinstance(item, dict) and (item.get('@type') and 'JobPosting' in item.get('@type')):
                                                if item.get('datePosted'):
                                                    pd = scraper.parse_posted_date(item.get('datePosted'))
                                                    if pd:
                                                        parsed_date = pd
                                                        break
                                        if parsed_date:
                                            break
                                    except Exception:
                                        continue
                        except Exception as e:
                            logger.debug('Requests fallback failed: %s', e)

                    results.append({'url': url, 'parsed': parsed_date, 'error': error})

                await browser.close()
            return results

        results = asyncio.run(fetch_and_parse())

        updated = 0
        errors = 0
        for r in results:
            if r['error']:
                errors += 1
                continue
            if r['parsed']:
                if not dry:
                    try:
                        with transaction.atomic():
                            job = Job.objects.get(url=r['url'])
                            job.posted_date = r['parsed']
                            job.save(update_fields=['posted_date', 'last_updated'])
                        updated += 1
                    except Exception:
                        errors += 1
                else:
                    updated += 1

        self.stdout.write(self.style.SUCCESS(f'Backfill complete: processed={len(results)}, updated={updated}, errors={errors}'))
        for r in results[:10]:
            self.stdout.write(f"{r['url']} -> parsed={r['parsed']} error={r['error']}")
