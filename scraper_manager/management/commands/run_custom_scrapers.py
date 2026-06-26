import os
import sys
import asyncio
import re
import json
import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.utils import timezone
from asgiref.sync import sync_to_async

from scraper_manager.db_manager import DjangoDBManager
from scraper_manager.scrapers.pacificaviation_scraper import PacificAviationScraper
from scraper_manager.scrapers.sunairjets_scraper import SunAirJetsScraper
from scraper_manager.scrapers.cathay_scraper import CathayPacificScraper
from scraper_manager.scrapers.hkexpress_scraper import HKExpressScraper
from scraper_manager.scrapers.fai_scraper import FAIScraper
from scraper_manager.category_taxonomy import infer_job_category
from jobs.models import Job
from scraper_manager.models import ScrapedURL

logger = logging.getLogger(__name__)

# ── Global title exclusions (apply to ALL scrapers) ──────────────────────────
SKIP_KEYWORDS = [
    "sales manager",
    "logistics",
    "captain",
    " pilot",          # space-prefixed so it doesn't hit e.g. "copilot"
    "first officer",
    "flying instructor",
    "flight instructor",
    "flight examiner",
]

# ── Pacific Aviation: only keep genuine ops roles ────────────────────────────
PACIFIC_KEEP_KEYWORDS = [
    "dispatcher", "dispatch",
    "load control", "load controller", "loadmaster", "load master",
    "baggage handler",
    "turnaround", "trc",
    "flight operations",
    "ramp",
    "operations manager",
    "operations officer",
    "ops agent",
    "station agent",
    "cargo",
    "weight and balance",
    "crew control",
    "maintenance",
    "mechanic",
]


def title_is_unwanted(title: str) -> bool:
    t = (title or "").lower()
    return any(kw in t for kw in SKIP_KEYWORDS)


def pacific_is_relevant(title: str) -> bool:
    t = (title or "").lower()
    return any(kw in t for kw in PACIFIC_KEEP_KEYWORDS)


class Command(BaseCommand):
    help = "Run new custom scrapers and close inactive jobs on production database"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Do not persist changes or mark jobs closed",
        )
        parser.add_argument(
            "--audit-only",
            action="store_true",
            help="Skip scraping — only audit the DB for unrelated jobs",
        )

    def handle(self, *args, **options):
        dry_run = options.get("dry_run", False)
        audit_only = options.get("audit_only", False)

        if audit_only:
            self.stdout.write(self.style.WARNING("=== AUDIT-ONLY MODE ==="))
            asyncio.run(self.audit_db())
            return

        if dry_run:
            self.stdout.write(self.style.WARNING("=== DRY RUN MODE ==="))

        asyncio.run(self.run_all(dry_run))

    async def run_all(self, dry_run):
        db_manager = DjangoDBManager()
        results = []
        source_urls = defaultdict(set)

        async def save_to_db_and_get_res(job_data, source):
            title = job_data.get("title", "")
            if title_is_unwanted(title):
                self.stdout.write(f"Skipping unwanted job: {title}")
                return None

            source_urls[source].add(job_data["url"])

            if dry_run:
                return {
                    "title": title,
                    "company": job_data["company"],
                    "location": job_data["location"],
                    "url": job_data["url"],
                    "category": "Dry-run",
                    "status": "Dry-run",
                    "message": "Dry-run mode",
                }

            is_new, msg = await sync_to_async(db_manager.add_or_update_job)(
                job_data, source=source
            )
            db_job = await sync_to_async(
                lambda: Job.objects.filter(url=job_data["url"]).first()
            )()
            category = db_job.job_category if db_job else "Unknown"
            location = db_job.location if db_job else job_data["location"]

            return {
                "title": title,
                "company": job_data["company"],
                "location": location,
                "url": job_data["url"],
                "category": category,
                "status": "New" if is_new else "Updated",
                "message": msg,
            }

        # 1. Pacific Aviation (Workable API - all pages, operational roles only)
        self.stdout.write("\n[pacificaviation] Scraping Pacific Aviation (Workable API all pages)...")
        try:
            workable_url = "https://apply.workable.com/api/v3/accounts/pacificaviation/jobs"

            # Only keep genuine aviation ops roles — skip CS agents, wheelchair, golf cart etc.
            PACIFIC_KEEP_KEYWORDS = [
                "dispatcher", "dispatch",
                "load control", "load controller", "loadmaster", "load master",
                "baggage handler",
                "turnaround", "trc",
                "flight operations",
                "ramp",
                "operations manager",
                "operations officer",
                "ops agent",
                "station agent",
                "cargo",
                "weight and balance",
                "crew control",
                "maintenance",
                "mechanic",
            ]

            def pacific_is_relevant(title):
                t = (title or "").lower()
                return any(kw in t for kw in PACIFIC_KEEP_KEYWORDS)

            def fetch_all_pacific():
                payload = {"query": "", "location": [], "department": [], "worktype": [], "remote": []}
                all_jobs = []
                token = None
                while True:
                    if token:
                        payload["token"] = token
                    resp = requests.post(workable_url, json=payload, headers={"Content-Type": "application/json"}, timeout=20)
                    data = resp.json()
                    batch = data.get("results", [])
                    all_jobs.extend(batch)
                    token = data.get("nextPage")
                    if not token or not batch:
                        break
                return all_jobs

            all_pacific_jobs = await asyncio.to_thread(fetch_all_pacific)
            self.stdout.write(f"[pacificaviation] Found {len(all_pacific_jobs)} jobs total (all pages)")
            kept = 0
            for j in all_pacific_jobs:
                title = j.get("title", "").strip()
                if not pacific_is_relevant(title):
                    self.stdout.write(f"[pacificaviation] Skip (not ops role): {title}")
                    continue
                shortcode = j.get("shortcode", "")
                location_parts = [j.get("city", ""), j.get("state", ""), j.get("country", "")]
                location = ", ".join(p for p in location_parts if p) or "United States"
                job_url = f"https://apply.workable.com/pacificaviation/j/{shortcode}/"
                job_data = {
                    "title": title,
                    "company": "Pacific Aviation",
                    "location": location,
                    "url": job_url,
                    "description": "",
                    "job_id": f"pacificaviation_{shortcode}",
                }
                res = await save_to_db_and_get_res(job_data, source="pacificaviation")
                if res:
                    results.append(res)
                    kept += 1
            self.stdout.write(f"[pacificaviation] Kept {kept} relevant jobs out of {len(all_pacific_jobs)}")
        except Exception as e:
            self.stderr.write(f"[pacificaviation] Error: {e}")

        # 2. Walmart
        self.stdout.write("\n[walmart] Scraping Walmart Aviation Jobs...")
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            page = await context.new_page()
            try:
                url = "https://careers.walmart.com/us/en/results?searchQuery=Aviation&careerareas=Supply%20Chain%20and%20Transportation"
                await page.goto(url, wait_until="networkidle", timeout=60000)
                await asyncio.sleep(5)

                titles_els = await page.query_selector_all(
                    'span[data-testid="job-title"]'
                )
                num_jobs = len(titles_els)
                self.stdout.write(f"[walmart] Found {num_jobs} jobs in results")

                for idx in range(num_jobs):
                    try:
                        await page.wait_for_selector('span[data-testid="job-title"]')
                        elements = await page.query_selector_all(
                            'span[data-testid="job-title"]'
                        )
                        el = elements[idx]
                        title_text = (await el.inner_text()).strip()
                        self.stdout.write(f"[walmart] Scraping: {title_text}")

                        await el.click()
                        await page.wait_for_load_state("domcontentloaded")
                        await asyncio.sleep(3)

                        job_url = page.url
                        desc_el = await page.query_selector(
                            "div.jd-description"
                        ) or await page.query_selector("main")
                        description = (
                            (await desc_el.inner_text()).strip() if desc_el else ""
                        )

                        loc_el = await page.query_selector(
                            "span.job-info"
                        ) or await page.query_selector(".location")
                        location = (
                            (await loc_el.inner_text()).strip()
                            if loc_el
                            else "Rogers, AR"
                        )

                        job_id = (
                            job_url.split("/")[-1]
                            if "/jobs/" in job_url
                            else f"walmart_{idx}"
                        )

                        job_data = {
                            "title": title_text,
                            "company": "Walmart",
                            "location": location,
                            "url": job_url,
                            "description": description,
                            "job_id": f"walmart_{job_id}",
                        }

                        res = await save_to_db_and_get_res(job_data, source="walmart")
                        if res:
                            results.append(res)

                        await page.go_back()
                        await page.wait_for_load_state("domcontentloaded")
                        await asyncio.sleep(3)

                    except Exception as ex:
                        self.stderr.write(
                            f"[walmart] Error scraping job index {idx}: {ex}"
                        )
                        if page.url != url:
                            await page.goto(url, wait_until="networkidle")
                            await asyncio.sleep(3)
            except Exception as e:
                self.stderr.write(f"[walmart] Error: {e}")
            finally:
                await browser.close()

        # 3. Sun Air Jets
        self.stdout.write("\n[sunairjets] Scraping Sun Air Jets...")
        try:
            sunair_scraper = SunAirJetsScraper(
                config={"headless": True, "use_filter": False},
                db_manager=db_manager,
            )
            sunair_jobs = await sunair_scraper.run()
            self.stdout.write(f"[sunairjets] Scraper found {len(sunair_jobs)} jobs")
            for job in sunair_jobs:
                res = await save_to_db_and_get_res(job, source="sunairjets")
                if res:
                    results.append(res)
        except Exception as e:
            self.stderr.write(f"[sunairjets] Error: {e}")

        # 4. Cathay Pacific
        self.stdout.write("\n[cathay] Scraping Cathay Pacific...")
        try:
            cathay_scraper = CathayPacificScraper(
                config={"headless": True, "use_filter": False},
                db_manager=db_manager,
            )
            cathay_jobs = await cathay_scraper.run()
            self.stdout.write(f"[cathay] Scraper found {len(cathay_jobs)} jobs")
            for job in cathay_jobs:
                res = await save_to_db_and_get_res(job, source="cathay")
                if res:
                    results.append(res)
        except Exception as e:
            self.stderr.write(f"[cathay] Error: {e}")

        # 5. HK Express
        self.stdout.write("\n[hkexpress] Scraping HK Express...")
        try:
            hkexpress_scraper = HKExpressScraper(
                config={"headless": True, "use_filter": False},
                db_manager=db_manager,
            )
            hkexpress_jobs = await hkexpress_scraper.run()
            self.stdout.write(f"[hkexpress] Scraper found {len(hkexpress_jobs)} jobs")
            for job in hkexpress_jobs:
                res = await save_to_db_and_get_res(job, source="hkexpress")
                if res:
                    results.append(res)
        except Exception as e:
            self.stderr.write(f"[hkexpress] Error: {e}")

        # 6. Malaysia Airlines
        self.stdout.write("\n[malaysia] Scraping Malaysia Airlines SuccessFactors...")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            page = await context.new_page()
            try:
                url = "https://career10.successfactors.com/career?company=malaysiaaiP&career%5fns=job%5flisting%5fsummary&navBarLevel=JOB%5fSEARCH&_s.crb=1ntrw%2bpV5k8sgHRVF9Nuu78ETlFTKK0JBYa4hZjOEN0%3d"
                await page.goto(url, wait_until="networkidle", timeout=60000)
                await asyncio.sleep(5)

                html = await page.content()
                soup = BeautifulSoup(html, "html.parser")

                job_links = []
                for a in soup.find_all("a"):
                    href = a.get("href") or ""
                    text = a.text.strip()
                    if href and (
                        "jobId=" in href
                        or "jobReqId=" in href
                        or "career_ns=job_listing" in href
                        or "career%5fns=job%5flisting" in href
                    ):
                        full_url = urljoin("https://career10.successfactors.com", href)
                        if (text, full_url) not in job_links:
                            job_links.append((text, full_url))

                self.stdout.write(f"[malaysia] Found {len(job_links)} job links")

                for title, job_url in job_links[:10]:
                    self.stdout.write(f"[malaysia] Scraping: {title}")
                    detail_page = await context.new_page()
                    try:
                        await detail_page.goto(
                            job_url, wait_until="domcontentloaded", timeout=45000
                        )
                        await asyncio.sleep(3)

                        detail_html = await detail_page.content()
                        dsoup = BeautifulSoup(detail_html, "html.parser")

                        loc_text = "Malaysia"
                        for span in dsoup.find_all(["span", "div"]):
                            span_text = span.text.strip()
                            if "Location:" in span_text or "Standort:" in span_text:
                                loc_text = (
                                    span_text.replace("Location:", "")
                                    .replace("Standort:", "")
                                    .strip()
                                )
                                break

                        content_div = (
                            dsoup.find("div", class_="jobopp_inner")
                            or dsoup.find("div", id="job-description")
                            or dsoup.find("div", class_="jobLid")
                            or dsoup.find("body")
                        )
                        description = content_div.text.strip() if content_div else ""

                        req_id_match = re.search(
                            r"job_req_id=(\d+)", job_url
                        ) or re.search(r"jobReqId=(\d+)", job_url)
                        job_id = (
                            req_id_match.group(1)
                            if req_id_match
                            else f"malaysia_{hash(job_url)}"
                        )

                        job_data = {
                            "title": title,
                            "company": "Malaysia Airlines",
                            "location": loc_text,
                            "url": job_url,
                            "description": description,
                            "job_id": f"malaysia_{job_id}",
                        }

                        res = await save_to_db_and_get_res(job_data, source="malaysia")
                        if res:
                            results.append(res)
                    except Exception as ex:
                        self.stderr.write(
                            f"[malaysia] Error details for {title}: {ex}"
                        )
                    finally:
                        await detail_page.close()
            except Exception as e:
                self.stderr.write(f"[malaysia] Error: {e}")
            finally:
                await browser.close()

        # 7. Boeing (Single Job)
        boeing_job_url = "https://jobs.boeing.com/job/-/-/185/96531820496?utm_source=linkedin&utm_medium=job_posting&utm_campaign=ra-us"
        self.stdout.write(f"\n[boeing] Scraping Boeing Job page: {boeing_job_url}")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            page = await context.new_page()
            try:
                await page.goto(boeing_job_url, wait_until="networkidle", timeout=60000)
                await asyncio.sleep(3)

                try:
                    accept_btn = await page.wait_for_selector(
                        "#onetrust-accept-btn-handler", timeout=5000
                    )
                    if accept_btn:
                        await accept_btn.click()
                except:
                    pass

                title_el = await page.query_selector("h1")
                title = (
                    (await title_el.inner_text()).strip()
                    if title_el
                    else "Airline Network & Fleet Planning Specialist"
                )

                desc_el = await page.query_selector(
                    "div.ats-description"
                ) or await page.query_selector("main")
                description = (await desc_el.inner_text()).strip() if desc_el else ""

                loc_el = await page.query_selector(
                    ".job-info .location"
                ) or await page.query_selector("[data-job-location]")
                location = (
                    (await loc_el.inner_text()).strip()
                    if loc_el
                    else "United States"
                )

                job_id_match = re.search(r"/(\d+)(?:[/?]|$)", boeing_job_url)
                job_id = (
                    job_id_match.group(1)
                    if job_id_match
                    else f"boeing_{hash(boeing_job_url)}"
                )

                job_data = {
                    "title": title,
                    "company": "Boeing",
                    "location": location,
                    "url": boeing_job_url,
                    "description": description,
                    "job_id": f"boeing_{job_id}",
                }

                res = await save_to_db_and_get_res(job_data, source="boeing")
                if res:
                    results.append(res)
            except Exception as e:
                self.stderr.write(f"[boeing] Error: {e}")
            finally:
                await browser.close()

        # 8. FAI Aviation Group
        self.stdout.write("\n[fai] Scraping FAI Aviation Group...")
        try:
            fai_scraper = FAIScraper(
                config={"headless": True, "use_filter": False},
                db_manager=db_manager,
            )
            fai_jobs = await fai_scraper.run()
            self.stdout.write(f"[fai] Scraper found {len(fai_jobs)} jobs")
            for job in fai_jobs:
                res = await save_to_db_and_get_res(job, source="fai")
                if res:
                    results.append(res)
        except Exception as e:
            self.stderr.write(f"[fai] Error: {e}")

        # 9. Aviation Training & Consulting LLC (Paylocity)
        paylocity_url = "https://recruiting.paylocity.com/recruiting/jobs/All/6d9d6b53-e0d7-4b13-b52f-7ae3b84b5c64/Aviation-Training-Consulting-LLC?source=137523"
        self.stdout.write(
            f"\n[paylocity] Scraping Paylocity URL: {paylocity_url} for Aviation Training Consulting LLC"
        )
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            page = await context.new_page()
            try:
                await page.goto(paylocity_url, wait_until="networkidle", timeout=60000)
                await page.wait_for_selector(".job-listing-job-item", timeout=20000)

                html = await page.content()
                soup = BeautifulSoup(html, "html.parser")
                job_items = soup.find_all("div", class_="job-listing-job-item")
                self.stdout.write(f"[paylocity] Found {len(job_items)} job elements")

                for item in job_items:
                    title_elem = item.find("a", class_="custom-link-color")
                    if not title_elem:
                        continue
                    title = title_elem.text.strip()
                    href = title_elem.get("href")
                    if not href:
                        continue
                    job_url = urljoin(paylocity_url, href)
                    loc_elem = item.find("div", class_="location-column")
                    location = loc_elem.text.strip() if loc_elem else "Unknown"

                    detail_page = await context.new_page()
                    try:
                        await detail_page.goto(
                            job_url, wait_until="domcontentloaded", timeout=30000
                        )
                        await asyncio.sleep(2)
                        detail_html = await detail_page.content()
                        detail_soup = BeautifulSoup(detail_html, "html.parser")
                        content = (
                            detail_soup.find("div", class_="job-preview-container")
                            or detail_soup.find(
                                "div", class_="job-details-content"
                            )
                            or detail_soup.find("body")
                        )
                        description = content.text.strip() if content else ""
                    except Exception as e:
                        self.stderr.write(
                            f"[paylocity] Failed to fetch description for {title}: {e}"
                        )
                        description = ""
                    finally:
                        await detail_page.close()

                    job_id = job_url.split("/")[-1]
                    job_data = {
                        "title": title,
                        "company": "Aviation Training Consulting LLC",
                        "location": location,
                        "url": job_url,
                        "description": description,
                        "job_id": f"paylocity_{job_id}",
                    }

                    res = await save_to_db_and_get_res(job_data, source="paylocity")
                    if res:
                        results.append(res)
            except Exception as e:
                self.stderr.write(f"[paylocity] Error: {e}")
            finally:
                await browser.close()

        # 10. Luminair
        self.stdout.write("\n[luminair] Scraping Luminair Personio XML Feed...")
        try:
            xml_url = "https://luminair.jobs.personio.com/xml"
            resp = requests.get(xml_url, timeout=20)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.content, "xml")
                positions = soup.find_all("position")
                self.stdout.write(
                    f"[luminair] Found {len(positions)} job positions in XML"
                )

                for pos in positions:
                    title = pos.find("name").text.strip()
                    job_id = pos.find("id").text.strip()

                    office = pos.find("office")
                    location = office.text.strip() if office else "Hamburg, Germany"

                    desc_parts = []
                    desc_items = pos.find_all("jobDescription")
                    for item in desc_items:
                        name_elem = item.find("name")
                        val_elem = item.find("value")
                        if val_elem:
                            text_val = BeautifulSoup(
                                val_elem.text, "html.parser"
                            ).get_text().strip()
                            if name_elem:
                                desc_parts.append(
                                    f"### {name_elem.text.strip()}\n{text_val}"
                                )
                            else:
                                desc_parts.append(text_val)
                    description = "\n\n".join(desc_parts)

                    job_url = f"https://luminair.jobs.personio.de/job/{job_id}"

                    job_data = {
                        "title": title,
                        "company": "Luminair",
                        "location": location,
                        "url": job_url,
                        "description": description,
                        "job_id": f"personio_{job_id}",
                    }

                    res = await save_to_db_and_get_res(job_data, source="personio")
                    if res:
                        results.append(res)
            else:
                self.stderr.write(
                    f"[luminair] HTTP Error {resp.status_code} fetching XML"
                )
        except Exception as e:
            self.stderr.write(f"[luminair] Error parsing Personio XML: {e}")

        # 11. Airfast Indonesia
        self.stdout.write("\n[airfast] Scraping Airfast Indonesia...")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                ignore_https_errors=True,
            )
            page = await context.new_page()
            try:
                url = "https://www.airfastindonesia.com/careers"
                await page.goto(url, wait_until="domcontentloaded", timeout=45000)
                await asyncio.sleep(5)

                html = await page.content()
                soup = BeautifulSoup(html, "html.parser")
                table = soup.find("table")
                if table:
                    rows = table.find_all("tr")[1:]  # Skip header
                    self.stdout.write(f"[airfast] Found {len(rows)} jobs in table")

                    for row in rows:
                        cols = row.find_all(["td", "th"])
                        if len(cols) < 5:
                            continue

                        title = cols[1].text.strip()
                        dept = cols[2].text.strip()
                        loc = cols[3].text.strip()

                        link_el = cols[4].find("a")
                        if not link_el or not link_el.get("href"):
                            continue

                        job_url = urljoin(
                            "https://www.airfastindonesia.com",
                            link_el.get("href"),
                        )
                        self.stdout.write(f"[airfast] Found: {title} -> {job_url}")

                        detail_page = await context.new_page()
                        description = ""
                        try:
                            await detail_page.goto(
                                job_url,
                                wait_until="domcontentloaded",
                                timeout=30000,
                            )
                            await asyncio.sleep(3)
                            detail_html = await detail_page.content()
                            dsoup = BeautifulSoup(detail_html, "html.parser")
                            content_div = (
                                dsoup.find("div", class_="post-content")
                                or dsoup.find("article")
                                or dsoup.find("body")
                            )
                            description = (
                                content_div.text.strip() if content_div else ""
                            )
                        except Exception as ex:
                            self.stderr.write(
                                f"[airfast] Error fetching detail for {title}: {ex}"
                            )
                        finally:
                            await detail_page.close()

                        job_id = job_url.split("/")[-1]
                        job_data = {
                            "title": title,
                            "company": "Airfast Indonesia",
                            "location": loc,
                            "url": job_url,
                            "description": description,
                            "job_id": f"airfast_{job_id}",
                        }

                        res = await save_to_db_and_get_res(job_data, source="airfast")
                        if res:
                            results.append(res)
            except Exception as e:
                self.stderr.write(f"[airfast] Error: {e}")
            finally:
                await browser.close()

        # 12. Volotea
        self.stdout.write("\n[volotea] Scraping Volotea (Teamtailor RSS)...")
        try:
            rss_url = "https://volotea.teamtailor.com/jobs.rss"
            resp = requests.get(rss_url, timeout=20)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.content, "xml")
                items = soup.find_all("item")
                self.stdout.write(f"[volotea] Found {len(items)} items in feed")

                for item in items:
                    title = item.find("title").text.strip()
                    job_url = item.find("link").text.strip()
                    guid = item.find("guid").text.strip()

                    loc_parts = []
                    loc_el = item.find("tt:location")
                    if loc_el:
                        city = loc_el.find("tt:city")
                        country = loc_el.find("tt:country")
                        if city:
                            loc_parts.append(city.text.strip())
                        if country:
                            loc_parts.append(country.text.strip())
                    location = (
                        ", ".join(loc_parts) if loc_parts else "Barcelona, Spain"
                    )

                    desc_el = item.find("description") or item.find(
                        "content:encoded"
                    )
                    description = (
                        BeautifulSoup(desc_el.text, "html.parser").get_text().strip()
                        if desc_el
                        else ""
                    )

                    job_data = {
                        "title": title,
                        "company": "Volotea",
                        "location": location,
                        "url": job_url,
                        "description": description,
                        "job_id": f"volotea_{guid}",
                    }

                    res = await save_to_db_and_get_res(job_data, source="volotea")
                    if res:
                        results.append(res)
            else:
                self.stderr.write(
                    f"[volotea] HTTP Error {resp.status_code} fetching RSS feed"
                )
        except Exception as e:
            self.stderr.write(f"[volotea] Error: {e}")

        # 13. Emirates
        self.stdout.write("\n[emirates] Scraping Emirates Group Careers...")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                ignore_https_errors=True,
            )
            page = await context.new_page()
            try:
                url = "https://www.emiratesgroupcareers.com/search-and-apply/?jobcategory=Airline%20--%20Airport%20Operations"
                await page.goto(url, wait_until="domcontentloaded", timeout=45000)
                await asyncio.sleep(3)

                try:
                    accept_btn = await page.query_selector(
                        "#onetrust-accept-btn-handler"
                    )
                    if accept_btn:
                        await accept_btn.click()
                        await asyncio.sleep(2)
                except:
                    pass

                html = await page.content()
                soup = BeautifulSoup(html, "html.parser")
                cards = soup.find_all("section", class_="job-card")
                self.stdout.write(
                    f"[emirates] Found {len(cards)} job cards on search page"
                )

                for card in cards:
                    title_div = card.find("div", class_="job-card__title")
                    title = title_div.text.strip() if title_div else "No Title"

                    loc_div = card.find("div", class_="job-card__location")
                    loc = (
                        loc_div.text.strip()
                        if loc_div
                        else "Dubai, United Arab Emirates"
                    )

                    card_id = card.get("id")
                    if not card_id:
                        continue

                    job_url = f"https://www.emiratesgroupcareers.com/search-and-apply/{card_id}"
                    self.stdout.write(f"[emirates] Found: {title} -> {job_url}")

                    detail_page = await context.new_page()
                    description = ""
                    try:
                        await detail_page.goto(
                            job_url, wait_until="domcontentloaded", timeout=20000
                        )
                        await asyncio.sleep(2)
                        detail_html = await detail_page.content()
                        dsoup = BeautifulSoup(detail_html, "html.parser")
                        main_el = (
                            dsoup.find("main")
                            or dsoup.find("article")
                            or dsoup.find("body")
                        )
                        description = main_el.text.strip() if main_el else ""
                    except Exception as ex:
                        self.stderr.write(
                            f"[emirates] Error fetching detail for {title}: {ex}"
                        )
                    finally:
                        await detail_page.close()

                    job_data = {
                        "title": title,
                        "company": "Emirates",
                        "location": loc,
                        "url": job_url,
                        "description": description,
                        "job_id": f"emirates_{card_id}",
                    }

                    res = await save_to_db_and_get_res(job_data, source="emirates")
                    if res:
                        results.append(res)
            except Exception as e:
                self.stderr.write(f"[emirates] Error: {e}")
            finally:
                await browser.close()

        # 14. Flydubai
        self.stdout.write(
            "\n[flydubai] Scraping Flydubai Flight Dispatcher Programme..."
        )
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                ignore_https_errors=True,
            )
            page = await context.new_page()
            try:
                url = "https://careers.flydubai.com/pilots/uae-national-opportunities/flight-dispatcher-programme"
                await page.goto(url, wait_until="domcontentloaded", timeout=45000)
                await asyncio.sleep(5)

                html = await page.content()
                soup = BeautifulSoup(html, "html.parser")
                title = "Flight Dispatcher Programme (UAE National Opportunities)"
                description = soup.body.text.strip() if soup.body else ""

                job_data = {
                    "title": title,
                    "company": "flydubai",
                    "location": "United Arab Emirates",
                    "url": url,
                    "description": description,
                    "job_id": "flydubai_flight_dispatcher_programme",
                }

                res = await save_to_db_and_get_res(job_data, source="flydubai")
                if res:
                    results.append(res)
            except Exception as e:
                self.stderr.write(f"[flydubai] Error: {e}")
            finally:
                await browser.close()

        # 15. Edelweiss
        self.stdout.write("\n[edelweiss] Scraping Edelweiss Ground Staff...")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                ignore_https_errors=True,
            )
            page = await context.new_page()
            try:
                url = "https://www.flyedelweiss.com/at/de/jobs/vacant-positions.html"
                await page.goto(url, wait_until="domcontentloaded", timeout=45000)
                await asyncio.sleep(5)

                html = await page.content()
                soup = BeautifulSoup(html, "html.parser")

                job_urls = []
                for a in soup.find_all("a"):
                    href = a.get("href") or ""
                    if "lufthansagroup.careers" in href and "jobad" in href:
                        if href not in job_urls:
                            job_urls.append(href)

                self.stdout.write(
                    f"[edelweiss] Found {len(job_urls)} Lufthansa Careers links"
                )

                for job_url in job_urls:
                    detail_page = await context.new_page()
                    try:
                        await detail_page.goto(
                            job_url, wait_until="domcontentloaded", timeout=45000
                        )
                        await asyncio.sleep(5)
                        detail_html = await detail_page.content()
                        dsoup = BeautifulSoup(detail_html, "html.parser")

                        h1 = dsoup.find("h1")
                        title = h1.text.strip() if h1 else "Ground Operations Jobad"

                        description = dsoup.body.text.strip() if dsoup.body else ""

                        loc = "Zürich/Kloten"
                        m = re.search(r"Standort\s*([^\n\r]+)", description)
                        if m:
                            loc = m.group(1).strip()
                            if len(loc) > 100:
                                loc = "Zürich/Kloten"

                        req_id_match = re.search(r"code=([^&]+)", job_url)
                        job_id = (
                            req_id_match.group(1)
                            if req_id_match
                            else f"edelweiss_{hash(job_url)}"
                        )

                        job_data = {
                            "title": title,
                            "company": "Edelweiss",
                            "location": loc,
                            "url": job_url,
                            "description": description,
                            "job_id": f"edelweiss_{job_id}",
                        }

                        res = await save_to_db_and_get_res(job_data, source="edelweiss")
                        if res:
                            results.append(res)
                    except Exception as ex:
                        self.stderr.write(
                            f"[edelweiss] Error fetching detail for {job_url}: {ex}"
                        )
                    finally:
                        await detail_page.close()
            except Exception as e:
                self.stderr.write(f"[edelweiss] Error: {e}")
            finally:
                await browser.close()

        # 16. Root Aviation
        self.stdout.write("\n[rootaviation] Scraping Root Aviation...")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                ignore_https_errors=True,
            )
            page = await context.new_page()
            try:
                url = "https://rootaviation.com/operations-opportunities"
                await page.goto(url, wait_until="domcontentloaded", timeout=45000)
                await asyncio.sleep(5)

                html = await page.content()
                soup = BeautifulSoup(html, "html.parser")

                job_links = []
                for a in soup.find_all("a"):
                    href = a.get("href") or ""
                    text = a.text.strip()
                    if (
                        href
                        and href.startswith("/")
                        and len(href) > 2
                        and not any(
                            x in href
                            for x in ["about", "service", "vacancies", "contact", "home"]
                        )
                    ):
                        full_url = urljoin("https://rootaviation.com", href)
                        if (text, full_url) not in job_links:
                            job_links.append((text, full_url))

                self.stdout.write(f"[rootaviation] Found {len(job_links)} job links")

                for text, job_url in job_links:
                    detail_page = await context.new_page()
                    try:
                        await detail_page.goto(
                            job_url, wait_until="domcontentloaded", timeout=30000
                        )
                        await asyncio.sleep(3)
                        detail_html = await detail_page.content()
                        dsoup = BeautifulSoup(detail_html, "html.parser")

                        title = (
                            text
                            if text
                            else (
                                dsoup.title.text.replace(
                                    "Careers at Root Aviation Ltd", ""
                                ).strip()
                                if dsoup.title
                                else "Aviation Specialist"
                            )
                        )
                        description = dsoup.body.text.strip() if dsoup.body else ""

                        loc = "Middle East"
                        loc_match = re.search(
                            r"Location:\s*([^\n\r]+)", description, re.IGNORECASE
                        )
                        if loc_match:
                            loc = loc_match.group(1).strip()
                        elif "-" in title:
                            loc = title.split("-")[-1].strip()

                        job_id = job_url.split("/")[-1]

                        job_data = {
                            "title": title,
                            "company": "Root Aviation",
                            "location": loc,
                            "url": job_url,
                            "description": description,
                            "job_id": f"rootaviation_{job_id}",
                        }

                        res = await save_to_db_and_get_res(job_data, source="rootaviation")
                        if res:
                            results.append(res)
                    except Exception as ex:
                        self.stderr.write(
                            f"[rootaviation] Error fetching detail for {text}: {ex}"
                        )
                    finally:
                        await detail_page.close()
            except Exception as e:
                self.stderr.write(f"[rootaviation] Error: {e}")
            finally:
                await browser.close()

        # ----------------------------------------------------
        # Close inactive jobs for the processed sources
        # ----------------------------------------------------
        self.stdout.write("\n==================================================")
        self.stdout.write("CLOSING INACTIVE JOBS FOR PROCESSED SOURCES")
        self.stdout.write("==================================================")

        for source, scraped_set in source_urls.items():
            self.stdout.write(
                f"\nChecking active/new jobs for source: {source} (scraped {len(scraped_set)} urls)"
            )
            # Fetch active or new jobs in DB for this source
            active_db_jobs = await sync_to_async(
                lambda: list(
                    Job.objects.filter(
                        source__iexact=source, status__in=["new", "active"]
                    )
                )
            )()

            closed_count = 0
            for job in active_db_jobs:
                if job.url not in scraped_set:
                    self.stdout.write(
                        f"Job no longer found in current scrape. Closing: {job.title} | {job.url}"
                    )
                    if not dry_run:
                        await sync_to_async(db_manager.mark_job_closed)(
                            job.url, reason="Not found in current scrape run"
                        )
                    closed_count += 1

            self.stdout.write(f"Closed {closed_count} inactive jobs for {source}")

        # ----------------------------------------------------
        # Generate reports
        # ----------------------------------------------------
        results = [r for r in results if r is not None]

        # Write TSV output to workspace root
        tsv_path = "/home/rajat/Desktop/AeroOps Intel/scraper-standalone/scraped_jobs.tsv"
        try:
            with open(tsv_path, "w", encoding="utf-8") as f:
                f.write("Job Title\tCompany\tLocation\tCategory\tURL\n")
                for r in results:
                    f.write(
                        f"{r['title']}\t{r['company']}\t{r['location']}\t{r['category']}\t{r['url']}\n"
                    )
            self.stdout.write(self.style.SUCCESS(f"Saved jobs TSV report to {tsv_path}"))
        except Exception as e:
            self.stderr.write(f"Error saving TSV: {e}")

        # Write categorized Markdown report
        jobs_by_cat = defaultdict(list)
        for r in results:
            jobs_by_cat[r["category"]].append(r)

        markdown_lines = ["# Scraped Jobs by Category\n"]
        for cat, jobs in sorted(jobs_by_cat.items()):
            markdown_lines.append(f"## Category: {cat} ({len(jobs)} jobs)\n")
            markdown_lines.append("| Job Title | Company | Location | URL |")
            markdown_lines.append("|-----------|---------|----------|-----|")
            for j in jobs:
                markdown_lines.append(
                    f"| {j['title']} | {j['company']} | {j['location']} | [Link]({j['url']}) |"
                )
            markdown_lines.append("\n")

        report_path = "/home/rajat/.gemini/antigravity/brain/f8a90aa9-d12c-40f4-9b19-e1e260eac8b8/scraped_jobs_report.md"
        try:
            with open(report_path, "w", encoding="utf-8") as f:
                f.write("\n".join(markdown_lines))
            self.stdout.write(
                self.style.SUCCESS(f"Saved Markdown report to {report_path}")
            )
        except Exception as e:
            self.stderr.write(f"Error saving Markdown: {e}")

        # Display final report summary
        self.stdout.write("\n================== SCRAPING SUMMARY ==================")
        self.stdout.write(f"Total jobs scraped: {len(results)}")
        for cat, jobs in sorted(jobs_by_cat.items()):
            self.stdout.write(f"  • {cat:20s}: {len(jobs)} jobs")
        self.stdout.write("======================================================")

        # Always audit DB at end of every scrape run
        await self.audit_db()

    # ─────────────────────────────────────────────────────────────────────────
    async def audit_db(self):
        """
        Scan all active/new jobs in the DB and flag any that look unrelated.
        Prints a warning report — does NOT auto-delete.
        """
        self.stdout.write("\n\n" + "=" * 60)
        self.stdout.write("🔍 DB AUDIT — Checking for unrelated jobs")
        self.stdout.write("=" * 60)

        all_jobs = await sync_to_async(
            lambda: list(Job.objects.filter(status__in=["new", "active"]).values(
                "title", "company", "source", "job_category", "url"
            ))
        )()

        flagged = []

        for j in all_jobs:
            title = j.get("title") or ""
            source = j.get("source") or ""
            category = j.get("job_category") or ""
            reason = None

            # 1. Check global skip keywords
            if title_is_unwanted(title):
                reason = f"title contains banned keyword"

            # 2. Pacific Aviation jobs must match ops whitelist
            elif source == "pacificaviation" and not pacific_is_relevant(title):
                reason = "Pacific Aviation job not in ops whitelist"

            # 3. Category = 'other' is usually a sign of unrelated job
            elif category == "other":
                reason = f"category=other (unclassified)"

            # 4. Re-infer category from title — if it stays 'other' flag it
            elif not category:
                inferred = infer_job_category(title=title, source=source)
                if inferred == "other":
                    reason = "inferred category=other"

            if reason:
                flagged.append({"title": title, "company": j.get("company",""), "source": source, "reason": reason, "url": j.get("url","")})

        if not flagged:
            self.stdout.write(self.style.SUCCESS("✅ No unrelated jobs found in DB!"))
        else:
            self.stdout.write(self.style.WARNING(f"\n⚠️  Found {len(flagged)} possibly unrelated jobs:"))
            self.stdout.write(f"{'Title':<55} {'Company':<25} {'Source':<20} Reason")
            self.stdout.write("-" * 130)
            for f in flagged:
                self.stdout.write(
                    f"{f['title'][:54]:<55} {f['company'][:24]:<25} {f['source'][:19]:<20} {f['reason']}"
                )
            self.stdout.write(
                "\n💡 Run: python manage.py run_custom_scrapers --audit-only  to re-check anytime"
            )
            self.stdout.write(
                "💡 To remove flagged jobs manually use the reclassify_jobs.py or delete from Mongo."
            )
        self.stdout.write("=" * 60)
