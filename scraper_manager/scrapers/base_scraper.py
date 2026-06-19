"""
Base Scraper Class
Common functionality for all aviation job scrapers
"""

import asyncio
import random
import logging
import re
import os
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import time
from asgiref.sync import sync_to_async
from fake_useragent import UserAgent
from curl_cffi import requests as curl_requests
from ..category_taxonomy import matches_selected_categories, normalize_job_categories

# Import filter manager
try:
    # Try relative import first (works when run as package)
    from ..filter_manager import JobFilterManager
except (ImportError, ValueError):
    try:
        # Try absolute import (works when scraper_manager is in path)
        from scraper_manager.filter_manager import JobFilterManager
    except ImportError:
        try:
            # Try direct import (works when in scraper_manager dir)
            from filter_manager import JobFilterManager
        except ImportError:
            JobFilterManager = None

# Import location manager
try:
    from ..location_manager import LocationManager
except (ImportError, ValueError):
    try:
        from scraper_manager.location_manager import LocationManager
    except ImportError:
        LocationManager = None

# Setup logging
logger = logging.getLogger(__name__)


class BaseScraper:
    """Base class for all scrapers with common functionality"""

    def __init__(self, config: dict, site_key: str, db_manager=None):
        """
        Initialize base scraper

        Args:
            config: Configuration dictionary with scraper settings
            site_key: Site identifier (e.g., 'signature', 'flygosh')
            db_manager: Optional database manager for URL tracking
        """
        self.site_key = site_key
        self.config = config
        self.site_config = config.get("sites", {}).get(site_key, {})
        self.db_manager = db_manager
        self.job_id = config.get("job_id")  # Passed from management command
        self.scrape_start_time = None
        self.use_db = db_manager is not None

        # Setup logger for this scraper
        self.logger = logging.getLogger(f"{__name__}.{site_key}")

        # Limits
        scraper_config = config.get("scrapers", {}).get(site_key, {})
        self.max_jobs = scraper_config.get("max_jobs") or config.get("max_jobs")
        self.max_pages = scraper_config.get("max_pages") or config.get("max_pages")

        self.batch_size = config.get("scraper_settings", {}).get("batch_size", 5)

        # NO MORE FILE OUTPUT - database only
        logger.info(f"[{site_key}] Initializing scraper (Database-only mode)")

        # Site info
        self.company_name = self.site_config.get("name", "Unknown")
        self.base_url = self.site_config.get("base_url", "")

        # Anti-Detection Settings
        scraper_settings = config.get("scraper_settings", {})
        self.stealth_mode = scraper_settings.get("stealth_mode", True)
        self.request_delay_min = scraper_settings.get("request_delay_min", 2)
        self.request_delay_max = scraper_settings.get("request_delay_max", 5)
        self.page_load_delay = scraper_settings.get("page_load_delay", 3)
        self.random_scroll = scraper_settings.get("random_scroll", True)
        self.random_mouse = scraper_settings.get("random_mouse", True)
        self.user_agents = scraper_settings.get("user_agents", [])
        self.proxy_list = scraper_settings.get("proxy_list", [])
        self.rotate_proxy = scraper_settings.get("rotate_proxy", False)
        self.impersonate_list = scraper_settings.get("impersonate_list", ["chrome110"])
        self.impersonate = (
            random.choice(self.impersonate_list)
            if self.impersonate_list
            else "chrome110"
        )

        # Headless setting (can be overridden per-site in config.py)
        # Default to True, but check if explicitly set in scraper config
        self.headless = (
            config.get("scrapers", {}).get(site_key, {}).get("headless", True)
        )

        # Initialize fake-useragent
        try:
            self.ua = UserAgent()
        except Exception:
            self.ua = None

        # Filter settings with env override for operational control.
        # SCRAPER_USE_FILTER=0 disables title filtering globally.
        env_use_filter = os.environ.get("SCRAPER_USE_FILTER")
        if env_use_filter is None:
            self.use_filter = scraper_settings.get("use_filter", True)
        else:
            self.use_filter = str(env_use_filter).strip().lower() in (
                "1",
                "true",
                "yes",
                "y",
                "on",
            )
        self.filter_manager = None

        if self.use_filter and JobFilterManager:
            filter_file = scraper_settings.get("filter_file", "filter_title.json")
            try:
                # Find the filter file relative to the package structure
                # base_scraper.py is in scraper_manager/scrapers/
                # filter_title.json is in scraper_manager/
                # So we go up one level from current_dir
                current_dir = os.path.dirname(os.path.abspath(__file__))
                filter_path = os.path.join(os.path.dirname(current_dir), filter_file)

                # Check if it exists at this path, if not fallback to just filename
                if not os.path.exists(filter_path):
                    # Try current directory too just in case
                    filter_path = os.path.join(current_dir, filter_file)
                if not os.path.exists(filter_path):
                    # Fallback to direct filename and let Path resolution handle it
                    filter_path = filter_file

                self.filter_manager = JobFilterManager(filter_path)
                logger.info(
                    f"[{site_key}] Loaded filter with {len(self.filter_manager.all_keywords)} keywords"
                )
            except Exception as e:
                logger.error(f"[{site_key}] Failed to load filter: {e}")

            self.selected_job_categories = normalize_job_categories(
                config.get("selected_job_categories")
            )

    def normalize_location(self, location_text: str) -> str:
        """Standardize location string using LocationManager with site hints"""
        if not LocationManager:
            return location_text or "Unknown"

        # Detect hint country from site name or URL for regionally-focused sites
        hint_country = None
        site_context = f"{self.company_name} {self.base_url}".lower()

        if "brasil" in site_context:
            hint_country = "Brazil"
        elif "emploitic" in site_context or "algeria" in site_context:
            hint_country = "Algeria"
        elif "qatar" in site_context:
            hint_country = "Qatar"
        elif "jetblue" in site_context:
            hint_country = "United States"

        return LocationManager.normalize_location(
            location_text, hint_country=hint_country, company=self.company_name
        )

    async def update_progress(self, current: int, total: int):
        """Update job progress in database"""
        if self.job_id:
            try:
                progress_pct = int((current / total) * 100) if total > 0 else 0
                from scraper_manager.models import ScraperJob
                from asgiref.sync import sync_to_async

                await sync_to_async(ScraperJob.objects.filter(id=self.job_id).update)(
                    progress=progress_pct
                )
                logger.debug(f"[{self.site_key}] Progress: {progress_pct}%")
            except Exception as e:
                logger.warning(f"[{self.site_key}] Failed to update progress: {e}")

    async def is_url_already_scraped(self, url: str) -> bool:
        """Check if URL was already scraped (using database if available)"""
        if self.use_db and self.db_manager:
            is_scraped = await self.db_manager.is_url_scraped(url)
            if is_scraped:
                logger.debug(f"[{self.site_key}] URL already scraped: {url}")
            return is_scraped
        return False

    async def filter_new_jobs(self, jobs: List[Dict]) -> tuple[List[Dict], int]:
        """
        Filter out already scraped jobs
        Returns: (new_jobs, duplicate_count)
        """
        if not self.use_db or not self.db_manager:
            logger.warning(
                f"[{self.site_key}] Database not available, cannot filter duplicates"
            )
            return jobs, 0

        logger.info(f"[{self.site_key}] Filtering {len(jobs)} jobs against database...")
        scraped_urls = await self.db_manager.get_scraped_urls(source=self.site_key)
        new_jobs = [job for job in jobs if job.get("url") not in scraped_urls]
        duplicate_count = len(jobs) - len(new_jobs)

        logger.info(
            f"[{self.site_key}] Found {len(new_jobs)} new jobs, {duplicate_count} duplicates"
        )
        return new_jobs, duplicate_count

    def apply_title_filter(
        self, jobs: List[Dict]
    ) -> tuple[List[Dict], List[Dict], Dict]:
        """
        Filter jobs by title keywords
        Returns: (matched_jobs, rejected_jobs, stats)
        """
        if not self.use_filter or not self.filter_manager:
            # No filtering - return all jobs as matched
            return (
                jobs,
                [],
                {
                    "total": len(jobs),
                    "matched": len(jobs),
                    "rejected": 0,
                    "by_category": {},
                },
            )

        matched_jobs, rejected_jobs, stats = self.filter_manager.filter_jobs(jobs)
        if not self.selected_job_categories:
            return matched_jobs, rejected_jobs, stats

        selected_matches = []
        category_rejected = []
        for job in matched_jobs:
            if matches_selected_categories(
                self.selected_job_categories,
                primary_category=job.get("primary_category"),
                matched_categories=job.get("matched_categories"),
                matched_filter_types=job.get("matched_filter_types"),
            ):
                selected_matches.append(job)
            else:
                job["rejection_reason"] = "category_filter"
                category_rejected.append(job)

        stats["matched"] = len(selected_matches)
        stats["rejected"] = len(rejected_jobs) + len(category_rejected)
        stats["selected_categories"] = self.selected_job_categories
        return selected_matches, rejected_jobs + category_rejected, stats

    def should_process_job(self, title: str) -> bool:
        """
        Check if a job title matches the filter criteria before fetching details.

        Args:
            title: The job title to check

        Returns:
            True if the job matches and should be processed, False otherwise
        """
        if not self.use_filter or not self.filter_manager:
            return True

        matches, categories, score, details = self.filter_manager.matches_filter(title, self.company_name)
        if not matches:
            logger.info(
                f"[{self.site_key}] Skipping job: '{title}' (Title doesn't match filter)"
            )
            return False

        if self.selected_job_categories and not matches_selected_categories(
            self.selected_job_categories,
            primary_category=max(
                details.get("category_scores", {}).items(), key=lambda item: item[1]
            )[0]
            if details.get("category_scores")
            else None,
            matched_categories=[cat.get("display_name") for cat in categories],
            matched_filter_types=[cat.get("filter_type") for cat in categories],
        ):
            logger.info(
                f"[{self.site_key}] Skipping job: '{title}' (Outside selected category filters)"
            )
            return False

        return True

    async def save_results(self, jobs: List[Dict], filename: Optional[str] = None):
        """Save results to database only (no file generation)"""

        # Calculate duration
        duration = 0
        if self.scrape_start_time:
            duration = time.time() - self.scrape_start_time

        logger.info(f"[{self.site_key}] Saving {len(jobs)} jobs to database...")

        # Save to database if enabled
        db_stats = None
        if self.use_db and self.db_manager and jobs:
            try:
                # Wrap the synchronous add_jobs_batch call with sync_to_async
                add_jobs_async = sync_to_async(
                    self.db_manager.add_jobs_batch, thread_sensitive=True
                )
                db_stats = await add_jobs_async(jobs, self.site_key)
                await self.db_manager.log_scrape_session(
                    self.site_key, db_stats, duration
                )

                logger.info(
                    f"[{self.site_key}] Database updated: "
                    f"new={db_stats['new']}, updated={db_stats['updated']}, "
                    f"duplicates={db_stats['duplicate']}, errors={db_stats['errors']}"
                )

                logger.info("\n✅ Database updated:")
                logger.info(f"    - New jobs: {db_stats['new']}")
                logger.info(f"    - Updated jobs: {db_stats['updated']}")
                logger.info(f"    - Duplicates skipped: {db_stats['duplicate']}")
                if db_stats["errors"] > 0:
                    logger.info(f"    - Errors: {db_stats['errors']}")
            except Exception as e:
                logger.error(
                    f"[{self.site_key}] Database save failed: {e}", exc_info=True
                )
                logger.info(f"\n❌ Database save failed: {e}")
                return None
        else:
            if not jobs:
                # No jobs to save is expected when all were duplicates
                logger.info(
                    f"[{self.site_key}] No new jobs to save (all duplicates or filtered out)"
                )
                logger.info("\nℹ️  No new jobs to save (all duplicates or filtered out)")
            elif not (self.use_db and self.db_manager):
                # Database manager or DB use is disabled
                logger.warning(
                    f"[{self.site_key}] Database manager not available (skipping save)"
                )
                logger.info("\n⚠️  Database manager not available (skipping save)")
            else:
                # Fallback - general warning
                logger.warning(f"[{self.site_key}] No jobs saved; check DB or job list")
                logger.info("\n⚠️  No jobs saved; check DB or job list")
            return None

        # Print stats
        jobs_with_desc = sum(1 for job in jobs if job.get("description"))
        logger.info(
            f"[{self.site_key}] Extraction stats: total={len(jobs)}, "
            f"with_desc={jobs_with_desc}, duration={duration:.1f}s"
        )

        logger.info("\n📊 Extraction Stats:")
        logger.info(f"  Total jobs extracted: {len(jobs)}")
        logger.info(f"  With descriptions: {jobs_with_desc}")
        if jobs:
            logger.info(f"  Coverage: {jobs_with_desc / len(jobs) * 100:.1f}%")
        if duration > 0:
            logger.info(f"  Duration: {duration:.1f}s")

        return db_stats

    def print_header(self):
        """Print scraper header"""
        self.scrape_start_time = time.time()

        logger.info(f"[{self.site_key}] Starting scraper: {self.company_name}")
        logger.info(
            f"[{self.site_key}] Database tracking: {'ENABLED' if self.use_db else 'DISABLED'}"
        )
        logger.info(
            f"[{self.site_key}] Title filtering: {'ENABLED' if self.use_filter else 'DISABLED'}"
        )

        logger.info("=" * 60)
        logger.info(f"{self.company_name} Job Scraper")
        logger.info("=" * 60)

        if self.use_db:
            logger.info("📊 Database tracking: ENABLED")
        else:
            logger.info("📊 Database tracking: DISABLED")

        if self.use_filter:
            logger.info("🔍 Title filtering: ENABLED")
            if self.filter_manager:
                logger.info(
                    f"   Loaded {len(self.filter_manager.all_keywords)} keywords in {len(self.filter_manager.filters)} categories"
                )
            if self.selected_job_categories:
                logger.info(
                    f"   Selected categories: {', '.join(self.selected_job_categories)}"
                )
        else:
            logger.info("🔍 Title filtering: DISABLED")

        if self.max_jobs:
            logger.info(f"Max jobs limit: {self.max_jobs}")
            logger.info(f"[{self.site_key}] Max jobs limit: {self.max_jobs}")
        if self.max_pages:
            logger.info(f"Max pages limit: {self.max_pages}")
            logger.info(f"[{self.site_key}] Max pages limit: {self.max_pages}")

    def print_sample(self, jobs: List[Dict]):
        """Print sample job with category information"""
        if jobs and jobs[0].get("description"):
            job = jobs[0]
            logger.info(f"\n{'=' * 70}")
            logger.info("📄 SAMPLE JOB")
            logger.info(f"{'=' * 70}")
            logger.info(f"  ID: {job.get('job_id', 'N/A')}")
            logger.info(f"  Title: {job['title']}")
            logger.info(f"  Company: {job.get('company', 'N/A')}")
            logger.info(f"  Location: {job.get('location', 'N/A')}")

            # Show filter information if available
            if job.get("filter_match"):
                logger.info("\n  🎯 Filter Match: YES")
                logger.info(f"  📊 Score: {job.get('filter_score', 0.0)}")
                logger.info(
                    f"  🏷️  Primary Category: {job.get('primary_category', 'N/A')}"
                )
                if job.get("matched_categories"):
                    logger.info(
                        f"  📁 All Categories: {', '.join(job['matched_categories'][:3])}"
                    )
                if job.get("matched_keywords"):
                    keywords = job["matched_keywords"][:5]
                    logger.info(f"  🔑 Keywords: {', '.join(keywords)}")

            logger.info(f"\n  Description Preview: {job['description'][:150]}...")
            logger.info(f"{'=' * 70}\n")

    def get_random_user_agent(self) -> str:
        """Get random user agent for anti-detection"""
        if self.ua:
            try:
                return self.ua.random
            except Exception:
                pass

        if self.user_agents:
            return random.choice(self.user_agents)
        # Fallback user agent
        return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    def _get_default_headers(self, custom_ua: Optional[str] = None) -> Dict:
        """Get default browser-like headers"""
        ua = custom_ua or self.get_random_user_agent()
        return {
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        }

    async def make_request(self, url: str, method: str = "GET", **kwargs):
        """
        Make an asynchronous HTTP request using curl_cffi for TLS fingerprinting.
        Automatically rotates impersonation targets if configured.
        """
        # Pick a random impersonation target from the list if available
        if "impersonate" not in kwargs:
            if self.impersonate_list:
                impersonate_target = random.choice(self.impersonate_list)
                kwargs["impersonate"] = impersonate_target
                logger.debug(
                    f"[{self.site_key}] Rotating impersonation: {impersonate_target}"
                )
            elif self.impersonate:
                kwargs["impersonate"] = self.impersonate

        # Set headers
        if "headers" not in kwargs:
            # If we're not impersonating, we MUST set default headers
            if "impersonate" not in kwargs:
                kwargs["headers"] = self._get_default_headers()
            else:
                # If impersonating, curl_cffi sets its own headers.
                # We can still add specific standard headers if needed,
                # but we should avoid overriding the identity headers.
                kwargs["headers"] = {
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                }

        # Add proxy if configured
        if self.rotate_proxy and self.proxy_list and "proxies" not in kwargs:
            proxy_url = random.choice(self.proxy_list)
            kwargs["proxies"] = {"http": proxy_url, "https": proxy_url}

        # Use AsyncSession for async requests
        async with curl_requests.AsyncSession() as s:
            try:
                # Log the impersonation target for visibility
                impo = kwargs.get("impersonate", "None")
                logger.debug(
                    f"[{self.site_key}] {method} request to {url} (Impersonating: {impo})"
                )

                response = await s.request(method, url, **kwargs)
                return response
            except Exception as e:
                logger.error(f"[{self.site_key}] Request failed to {url}: {e}")
                raise

    def get_random_proxy(self) -> Optional[Dict]:
        """Get random proxy for anti-detection"""
        if self.rotate_proxy and self.proxy_list:
            proxy_url = random.choice(self.proxy_list)
            return {"server": proxy_url}
        return None

    def parse_salary(self, salary_text: str) -> Dict:
        """
        Parse salary strings and extract min/max/currency.
        Handles formats like:
        - '$50,000 - $70,000'
        - '£40k - £60k'
        - '60000 to 80000 USD'
        - '$25 per hour'

        Returns: { 'salary_min': float, 'salary_max': float, 'salary_currency': str }
        """
        if not salary_text or not isinstance(salary_text, str):
            return {"salary_min": None, "salary_max": None, "salary_currency": "USD"}

        text = salary_text.lower().replace(",", "")
        result = {"salary_min": None, "salary_max": None, "salary_currency": "USD"}

        # Detect currency
        if "£" in text or "gbp" in text:
            result["salary_currency"] = "GBP"
        elif "€" in text or "eur" in text:
            result["salary_currency"] = "EUR"
        elif "₹" in text or "inr" in text:
            result["salary_currency"] = "INR"
        elif "aed" in text:
            result["salary_currency"] = "AED"

        # Extract numbers (handles 'k' suffix)
        numbers = []
        for match in re.finditer(r"(\d+(?:\.\d+)?)(\s*[kK])?", text):
            val = float(match.group(1))
            if match.group(2):
                val *= 1000
            numbers.append(val)

        if not numbers:
            return result

        # Hourly to annual if requested/typical
        if "hour" in text or "hr" in text:
            # Simple conversion: hourly * 2080 (standard work hours/year)
            numbers = [v * 2080 for v in numbers]

        if len(numbers) >= 2:
            result["salary_min"] = min(numbers[:2])
            result["salary_max"] = max(numbers[:2])
        else:
            result["salary_min"] = numbers[0]
            result["salary_max"] = numbers[0]

        return result

    async def extract_salary_from_page(self, page) -> Dict:
        """Fallback: try to detect salary information on the page"""
        try:
            body_text = await page.inner_text("body")
            # Look for currency symbols and numeric ranges
            patterns = [
                r"[\$£€₹]\s*(\d+[\d,]*k?)\s*[-–—to]+\s*[\$£€₹]?\s*(\d+[\d,]*k?)",
                r"salary[:\s]+[\$£€₹]?\s*(\d+[\d,]*k?)",
                r"(\d+[\d,]*k?)\s*[-\s]+(\d+[\d,]*k?)\s*(?:usd|gbp|eur|inr|aed)",
            ]

            for pat in patterns:
                m = re.search(pat, body_text, re.IGNORECASE)
                if m:
                    return self.parse_salary(m.group(0))
        except Exception:
            pass
        return {"salary_min": None, "salary_max": None, "salary_currency": "USD"}

    def parse_posted_date(self, date_text: str) -> Optional[str]:
        """
        Parse various date formats and convert 'time ago' formats to ISO date strings.

        Handles formats like:
        - '3 days ago', '1 hour ago', '2 weeks ago', '1 month ago'
        - 'Posted 5 days ago', 'Updated 3 hours ago'
        - '30+ days ago', '30+ ago'
        - Actual dates: '2024-12-01', '01 Dec 2024', 'December 1, 2024'
        - Relative: 'Today', 'Yesterday'

        Returns ISO date string (YYYY-MM-DD) or None if parsing fails
        """
        if not date_text or not isinstance(date_text, str):
            return None

        # Normalize ordinals like '2nd', '1st', '3rd' -> '2', '1', '3'
        text_raw = date_text.strip()
        text_raw = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", text_raw, flags=re.IGNORECASE)
        text = text_raw.lower()
        now = (
            datetime.now()
        )  # Use local time to avoid UTC off-by-one for non-UTC timezones

        # Already ISO format
        if re.match(r"^\d{4}-\d{2}-\d{2}$", text):
            return text

        # Handle 'Today'
        if "today" in text or "just now" in text:
            return now.date().isoformat()

        # Handle 'Yesterday'
        if "yesterday" in text:
            return (now - timedelta(days=1)).date().isoformat()

        # Hours ago
        match = re.search(r"(\d+)\s*(?:hour|hr|h)s?(?:\s+ago)?", text)
        if match:
            try:
                hours = int(match.group(1))
                return (now - timedelta(hours=hours)).date().isoformat()
            except (ValueError, AttributeError):
                pass

        # Minutes ago (treat as today)
        if re.search(r"(\d+)\s*(?:minute|min|m)s?(?:\s+ago)?", text):
            return now.date().isoformat()

        # Days ago
        match = re.search(r"(\d+)\s*(?:day|d)s?(?:\s+ago)?", text)
        if match:
            try:
                days = int(match.group(1))
                return (now - timedelta(days=days)).date().isoformat()
            except (ValueError, AttributeError):
                pass

        # Weeks ago
        match = re.search(r"(\d+)\s*(?:week|wk|w)s?(?:\s+ago)?", text)
        if match:
            try:
                weeks = int(match.group(1))
                return (now - timedelta(weeks=weeks)).date().isoformat()
            except (ValueError, AttributeError):
                pass

        # Months ago (approximate as 30 days)
        match = re.search(r"(\d+)\s*(?:month|mon|mo)s?(?:\s+ago)?", text)
        if match:
            try:
                months = int(match.group(1))
                return (now - timedelta(days=months * 30)).date().isoformat()
            except (ValueError, AttributeError):
                pass

        # Years ago (approximate as 365 days)
        match = re.search(r"(\d+)\s*(?:year|yr|y)s?(?:\s+ago)?", text)
        if match:
            try:
                years = int(match.group(1))
                return (now - timedelta(days=years * 365)).date().isoformat()
            except (ValueError, AttributeError):
                pass

        # Handle '30+' or '30+ days' format
        if re.search(r"30\+|more\s+than\s+30", text):
            return (now - timedelta(days=30)).date().isoformat()

        # Try common date formats (be permissive: strip commas and normalize separators)
        date_patterns = [
            # numeric dates: DD/MM/YYYY or DD-MM-YYYY
            (r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})", ["%d-%m-%Y", "%d-%m-%y"]),
            # numeric ISO: YYYY-MM-DD or YYYY/MM/DD
            (r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})", ["%Y-%m-%d"]),
            # DD Mon YYYY (e.g., 01 Dec 2024) OR with ordinal (e.g., 1st Dec 2024)
            (
                r"(\d{1,2})\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+(\d{4})",
                ["%d %b %Y", "%d %B %Y"],
            ),
            # DD Mon YY (e.g., 01 Dec 25) - two-digit year
            (
                r"(\d{1,2})\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+(\d{2})",
                ["%d %b %y", "%d %B %y"],
            ),
            # Mon DD, YYYY or Mon DD YYYY (e.g., Dec 2, 2025)
            (
                r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2},?\s+\d{4}",
                ["%b %d %Y", "%B %d %Y"],
            ),
            # Mon DD, YY (e.g., Dec 2, 25) - two-digit year
            (
                r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2},?\s+\d{2}",
                ["%b %d %y", "%B %d %y"],
            ),
            # Full month name before day (e.g., December 1, 2024)
            (
                r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+\d{1,2},?\s+\d{4}",
                ["%B %d %Y", "%b %d %Y"],
            ),
        ]

        for pattern, date_formats in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if not match:
                continue
            try:
                date_str_raw = match.group(0)
                # Normalize: remove commas and slashes -> dashes for numeric formats
                date_str = date_str_raw.replace(",", " ").strip()
                date_str = re.sub(r"\s+", " ", date_str)
                # Replace common separators
                date_str_norm = date_str.replace("/", "-").strip()

                for df in date_formats:
                    try:
                        parsed_date_dt = datetime.strptime(date_str_norm, df).date()
                        # Validate parsed date is within reasonable range (not ancient or far future)
                        if parsed_date_dt < (now.date() - timedelta(days=3650)):
                            # Older than 10 years - treat as invalid
                            continue
                        if parsed_date_dt > (now.date() + timedelta(days=30)):
                            # More than 30 days in future - treat as invalid
                            continue
                        return parsed_date_dt.isoformat()
                    except ValueError:
                        # try without normalizing separators (some formats use spaces)
                        try:
                            parsed_date_dt = datetime.strptime(date_str, df).date()
                            if parsed_date_dt < (now.date() - timedelta(days=3650)):
                                continue
                            if parsed_date_dt > (now.date() + timedelta(days=30)):
                                continue
                            return parsed_date_dt.isoformat()
                        except ValueError:
                            continue
            except (AttributeError, IndexError):
                continue

        # Fallback using dateutil.parser.parse (fuzzy matching)
        try:
            from dateutil import parser
            parsed_date_dt = parser.parse(text_raw, fuzzy=True).date()
            if parsed_date_dt >= (now.date() - timedelta(days=3650)) and parsed_date_dt <= (now.date() + timedelta(days=30)):
                return parsed_date_dt.isoformat()
        except Exception:
            pass

        # If nothing matched, return None (don't return original text)
        logger.debug(f"[{self.site_key}] Could not parse date: {date_text}")
        return None


    async def scroll_to_bottom(self, page):
        """Scroll to the bottom of the page to trigger lazy loading"""
        await page.evaluate("""async () => {
            await new Promise((resolve) => {
                let totalHeight = 0;
                let distance = 100;
                let timer = setInterval(() => {
                    let scrollHeight = document.body.scrollHeight;
                    window.scrollBy(0, distance);
                    totalHeight += distance;
                    if(totalHeight >= scrollHeight){
                        clearInterval(timer);
                        resolve();
                    }
                }, 100);
            });
        }""")

    async def random_delay(
        self, min_seconds: Optional[float] = None, max_seconds: Optional[float] = None
    ):
        """Add random delay to mimic human behavior"""
        min_delay = min_seconds if min_seconds is not None else self.request_delay_min
        max_delay = max_seconds if max_seconds is not None else self.request_delay_max
        delay = random.uniform(min_delay, max_delay)
        await asyncio.sleep(delay)

    async def simulate_human_behavior(self, page):
        """Simulate human-like behavior on page"""
        if not self.stealth_mode:
            return

        try:
            # Random mouse movements
            if self.random_mouse:
                for _ in range(random.randint(2, 5)):
                    x = random.randint(100, 800)
                    y = random.randint(100, 600)
                    await page.mouse.move(x, y)
                    await asyncio.sleep(random.uniform(0.1, 0.3))

                # Random scrolling
                scroll_amount = random.randint(200, 800)
                await page.evaluate(f"window.scrollBy(0, {scroll_amount})")
                await asyncio.sleep(random.uniform(0.5, 1.5))

                # Scroll back up a bit
                scroll_back = random.randint(100, 400)
                await page.evaluate(f"window.scrollBy(0, -{scroll_back})")
                await asyncio.sleep(random.uniform(0.3, 0.8))
        except Exception:
            pass  # Ignore errors in behavior simulation

    async def extract_posted_date_from_page(self, page):
        """Fallback: try to detect a posted/published date by searching the page body and meta tags"""
        try:
            # Try meta tags first
            metas = await page.query_selector_all("meta")
            for m in metas:
                name = await m.get_attribute("name") or ""
                prop = await m.get_attribute("property") or ""
                itemprop = await m.get_attribute("itemprop") or ""
                content = await m.get_attribute("content") or ""
                if any(
                    k in (name + prop + itemprop).lower()
                    for k in (
                        "date",
                        "publish",
                        "published",
                        "modified",
                        "updated",
                        "posted",
                    )
                ):
                    parsed = self.parse_posted_date(content)
                    if parsed:
                        return parsed


            # JSON-LD
            scripts = await page.query_selector_all(
                'script[type="application/ld+json"]'
            )
            for s in scripts:
                try:
                    txt = await s.inner_text()
                    import json as _json

                    data = _json.loads(txt)
                    items = data if isinstance(data, list) else [data]
                    for item in items:
                        if isinstance(item, dict):
                            for key in (
                                "datePublished",
                                "datePosted",
                                "publishDate",
                                "published",
                            ):
                                if key in item:
                                    parsed = self.parse_posted_date(item[key])
                                    if parsed:
                                        return parsed
                except Exception:
                    continue

            # Look in body text for relative date strings like 'Posted 3 days ago' or 'Published on Dec 2, 2025'
            body = await page.inner_text("body")
            # Basic patterns
            patterns = [
                r"posted\s*[:\-]?\s*([\w\s,\d]+ago)",
                r"published\s*[:\-]?\s*([\w\s,\d]+ago)",
                r"posted on\s*([\w\s,\d,]+)",
                r"published on\s*([\w\s,\d,]+)",
            ]
            for pat in patterns:
                m = re.search(pat, body, re.IGNORECASE)
                if m:
                    cand = m.group(1).strip()
                    parsed = self.parse_posted_date(cand)
                    if parsed:
                        return parsed
            # No parsed date found
        except Exception:
            pass
        return None

    async def extract_description_from_page(self, page, min_length=100):
        """Fallback: return the largest candidate description on the page"""
        try:
            # Common selectors
            selectors = [
                "#jobDescription",
                'div[id*="job"]',
                'div[class*="job"]',
                ".jobDescription",
                ".job-description",
                ".description",
                "article",
                "main",
                ".content",
            ]
            for sel in selectors:
                try:
                    el = await page.query_selector(sel)
                    if el:
                        txt = await el.inner_text()
                        if txt and len(txt.strip()) >= min_length:
                            return txt.strip()
                except Exception:
                    continue

            # If none found, find the largest text container on page
            # Evaluate all divs and pick the one with the longest text
            longest = ""
            els = await page.query_selector_all("div, section, article")
            for el in els:
                try:
                    txt = await el.inner_text()
                    if txt and len(txt) > len(longest):
                        longest = txt
                except Exception:
                    continue
            if longest and len(longest.strip()) >= min_length:
                return longest.strip()
        except Exception:
            pass
        return ""

    async def setup_stealth_page(
        self,
        browser,
        viewport_width: Optional[int] = None,
        viewport_height: Optional[int] = None,
    ):
        """Create a browser page with anti-detection measures"""
        # Random viewport size
        if viewport_width is None:
            viewport_width = random.randint(1366, 1920)
            viewport_height = random.randint(768, 1080)

        # Context options with anti-detection
        context_options = {
            "viewport": {"width": viewport_width, "height": viewport_height},
            "user_agent": self.get_random_user_agent(),
            "locale": "en-US",
            "timezone_id": "America/New_York",
            "permissions": ["geolocation", "notifications"],
            "color_scheme": "light",
        }

        # Add proxy if configured
        proxy = self.get_random_proxy()
        if proxy:
            context_options["proxy"] = proxy

        # Create context
        context = await browser.new_context(**context_options)

        # Create page
        page = await context.new_page()

        # Anti-detection scripts
        if self.stealth_mode:
            await page.add_init_script("""
                // Remove webdriver flag
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                
                // Mock plugins
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                
                // Mock languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en']
                });
                
                // Mock chrome object
                window.chrome = {
                    runtime: {}
                };
                
                // Override permissions
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
            """)

        return page, context

    def is_job_link(self, title: str, url: str) -> bool:
        """
        Check if a link is likely a job posting based on title and URL.
        Filters out common false positives like 'Privacy Policy', 'Cookies', 'Home', etc.
        """
        if not title or not url:
            return False

        t = title.lower().strip()
        u = url.lower().strip()

        # Skip fragments or empty links
        if "#" in u or len(t) < 4:
            return False

        # Skip root domain or very short paths ending in / (usually navigation)
        # e.g., https://example.com/ or https://example.com/en/
        path = (
            u.replace("https://", "").replace("http://", "").split("/", 1)[-1]
            if "/" in u.replace("://", "___")
            else ""
        )
        if u.endswith("/") and len(path.strip("/")) < 4:
            return False

        # Mandatory exclusions
        skip_words = [
            "privacy",
            "policy",
            "cookies",
            "legal",
            "terms",
            "condition",
            "contact",
            "home",
            "about",
            "news",
            "faq",
            "help",
            "login",
            "sign-up",
            "register",
            "impressum",
            "confidentialite",
            "mentions-legales",
            "politique",
            "rejoindre",
            "notre-equipe",
            "equipe",
            "team",
            "support",
            "feedback",
            "blog",
            "press",
            "media",
            "investor",
            "compagnie",
            "services",
            "destinations",
            "newsletter",
            "sitemap",
            "accessibility",
            "booking",
            "check-in",
            "status",
            "manage",
            "travel",
            "trip",
            "plan",
            "reserve",
            "hotel",
            "car",
            "offer",
            "destination",
            "luggage",
            "baggage",
        ]

        if any(sw in t for sw in skip_words) or any(sw in u for sw in skip_words):
            # Special case: if "job", "vacancy", "career" or "opening" is in the URL,
            # it might be a false positive filter, but only if it's NOT clearly a legal/privacy page
            if any(sw in u for sw in ["privacy", "policy", "legal", "cookie", "terms"]):
                return False

            if any(x in u for x in ["job", "vacancy", "position", "career", "opening"]):
                # Keep if title looks like a real job (e.g. contains "Pilot", "Engineer")
                job_keywords = [
                    "pilot",
                    "engineer",
                    "officer",
                    "captain",
                    "attendant",
                    "crew",
                    "manager",
                    "technician",
                    "analyst",
                    "developer",
                    "staff",
                    "mecanicien",
                    "mechanic",
                    "dispatcher",
                    "ops",
                    "control",
                    "coordinator",
                    "specialist",
                    "planner",
                    "duty",
                    "scheduler",
                    "simulator",
                    "ground",
                    "technical",
                ]
                if any(jk in t for jk in job_keywords):
                    return True
            return False

        return True

    async def run(self):
        """Main execution method - to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement run() method")
