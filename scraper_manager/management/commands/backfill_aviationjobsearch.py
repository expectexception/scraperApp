from django.core.management.base import BaseCommand
from django.db import transaction
from jobs.models import Job
from scraper_manager.scrapers.base_scraper import BaseScraper
import asyncio
import re
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Backfill posted_date for Aviation Job Search jobs by rendering job pages and parsing visible dates (JSON-LD/datePosted).'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=0, help='Limit number of jobs to process (0 = all)')
        parser.add_argument('--dry-run', action='store_true', help='Do not save changes, just report')

    def handle(self, *args, **options):
        limit = options.get('limit', 0)
        dry = options.get('dry_run', False)

        qs = Job.objects.filter(source__iexact='aviationjobsearch', posted_date__isnull=True).order_by('-created_at')
        if limit and limit > 0:
            qs = qs[:limit]

        jobs = list(qs)
        total = len(jobs)
        if not jobs:
            self.stdout.write(self.style.SUCCESS('No Aviation Job Search jobs found that need backfilling.'))
            return

        self.stdout.write(f'Processing {total} Aviation Job Search jobs (dry_run={dry})...')

        scraper = BaseScraper({}, 'aviationjobsearch')

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
                    try:
                        try:
                            await page.goto(url, wait_until='networkidle', timeout=20000)
                        except Exception:
                            # Retry with domcontentloaded and a longer timeout
                            try:
                                await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                            except Exception:
                                # Will fall back to requests-based fetch below
                                pass
                        
                        # If page content still unavailable due to timeout, fall back to requests
                        html = await page.content()
                        body = await page.inner_text('body')

                        # Candidates collected
                        candidates = []

                        # JSON-LD datePosted
                        for m in re.findall(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html, re.DOTALL|re.IGNORECASE):
                            try:
                                import json as _json
                                data = _json.loads(m)
                                items = data if isinstance(data, list) else [data]
                                for item in items:
                                    if isinstance(item, dict) and (item.get('@type') and 'JobPosting' in item.get('@type')):
                                        if item.get('datePosted'):
                                            candidates.append(item.get('datePosted'))
                            except Exception:
                                continue

                        # meta tags
                        for m in re.findall(r'<meta[^>]+(?:name|property)=["\']([^"\']+)["\'][^>]*content=["\']([^"\']+)["\']', html, re.IGNORECASE):
                            name = m[0].lower()
                            val = m[1].strip()
                            if any(k in name for k in ('date','publish','published','modified','updated')):
                                candidates.append(val)

                        # time tags
                        for t in re.findall(r'<time[^>]*>([^<]+)</time>', html, re.IGNORECASE):
                            candidates.append(t.strip())

                        # body relative patterns
                        for r in re.findall(r'\b\d+\s*(?:minute|hour|day|week|month|year)s?\s+ago\b', body, re.IGNORECASE):
                            candidates.append(r)

                        # month-name absolute dates like 'Dec 2, 2025' or 'December 1, 2024'
                        for m in re.findall(r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2},?\s+\d{4}\b", body, re.IGNORECASE):
                            candidates.append(m)

                        # other common lines: 'Posted: Dec 2, 2025'
                        for l in re.findall(r'(?:Posted|posted|Published|published|Date|date)[:\s]+([^\n\r]{1,120})', body, re.IGNORECASE):
                            candidates.append(l.strip())

                        # Deduplicate preserving order
                        seen = set()
                        uniq = []
                        for c in candidates:
                            key = c.strip().lower()
                            if key and key not in seen:
                                seen.add(key)
                                uniq.append(c.strip())

                        # Try parse candidates using central parser
                        for cand in uniq:
                            pd = scraper.parse_posted_date(cand)
                            if pd:
                                parsed_date = pd
                                break

                    except Exception as e:
                        error = str(e)
                        logger.exception('Error processing %s', url)

                    # Fallback: if we didn't get HTML (playwright may have timed out), try requests
                    if not parsed_date and (not html or len(html) < 200):
                        try:
                            import requests
                            headers = {'User-Agent': scraper.get_random_user_agent()}
                            r = requests.get(url, headers=headers, timeout=15)
                            if r.status_code == 200 and r.text:
                                html = r.text
                                # body from requests
                                body = r.text
                        except Exception as e:
                            # Keep original error if present
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
