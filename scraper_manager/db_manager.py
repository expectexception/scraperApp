"""
Django Database Manager for Scrapers
Integrates scraper system with Django ORM
"""

import logging
import re
import json
from typing import List, Dict, Set, Optional
from django.utils import timezone
from asgiref.sync import sync_to_async
from .models import ScrapedURL, ScraperJob
from jobs.models import Job, CompanyMapping
from curl_cffi import requests as curl_requests
from .company_manager import CompanyManager
from .category_taxonomy import infer_job_category
from .location_manager import LocationManager
import hashlib

# Setup logging
logger = logging.getLogger(__name__)


class DjangoDBManager:
    """Database manager using Django ORM"""

    def __init__(self):
        """Initialize Django database manager"""
        pass

    _LOCATION_LABEL_PREFIXES = re.compile(
        r"^(?:location|standort|lieu|ubicaci[oó]n|localisation|lokalizacja|lokalita"
        r"|place|site|city|town|country|region|area|base|work location|job location)"
        r"\s*[:\-–]?\s*",
        re.IGNORECASE,
    )

    def _clean_location(self, location: str, company: str = "") -> str:
        """Strip label prefixes and resolve postal-prefix codes."""
        if not location:
            return location
        return LocationManager.normalize_location(location, company=company)

    def _country_name_from_code(self, code: str) -> Optional[str]:
        """Return full country name for a 2-letter ISO code, e.g. 'AT' → 'Austria'"""
        if not code:
            return None
        return LocationManager.CC_TO_NAME.get(code.upper())

    def _extract_country_code(self, location: str, company: str = "") -> Optional[str]:
        """Extract country code from location string"""
        if not location:
            return None

        # Normalize first if it's not already
        if "," not in location and len(location) > 2:
            location = LocationManager.normalize_location(location, company=company)

        return LocationManager.extract_country_code(location)

    def _infer_operation_type(
        self, title: str, company: str, description: str = ""
    ) -> Optional[str]:
        """
        Infer operation type from job title, company name, and description.
        Now uses prioritized scoring and expanded aviation knowledge base.
        """
        text = f"{title} {company} {description}".lower()
        title_lower = title.lower()
        company_lower = company.lower()

        # 1. Company-First Priority (Direct mapping for known providers)
        company_priorities = {
            "cargo": [
                "fedex",
                "ups",
                "dhl",
                "atlas air",
                "kalitta",
                "cargolux",
                "western global",
                "polar air",
                "amerijet",
                "abx air",
                "ati",
                "omni air",
                "national airlines",
                "blue dart",
                "silk way",
                "cargojet",
                "asl airlines",
                "martinair",
            ],
            "mro": [
                "haeco",
                "gameco",
                "lufthansa technik",
                "air france industries",
                "klm e&m",
                "st engineering",
                "aarf",
                "sia engineering",
                "mtu aero",
                "sr technics",
                "signature aviation",
                "standardaero",
                "aviall",
                "jet aviation",
                "shannon engine",
            ],
            "business": [
                "netjets",
                "flexjet",
                "vista",
                "xo",
                "wheels up",
                "flyexclusive",
                "tag aviation",
                "execujet",
                "air charter service",
                "clay lacy",
                "solairus",
                "privatefly",
                "air partner",
                "jetcraft",
            ],
            "helicopter": [
                "phi",
                "air methods",
                "bristow",
                "era helicopters",
                "chn",
                "cougar helicopters",
                "babcock mission",
                "airbus helicopters",
                "sikorsky",
                "bell flight",
            ],
        }

        for op_type, companies in company_priorities.items():
            for c in companies:
                if c in company_lower:
                    return op_type

        # 2. Weighted Keyword Scoring
        # use float values so that later weight adjustments (1.5, 2.0, etc.)
        # are compatible with the declared type; mypy was complaining about
        # assigning a float to an int.
        scores: Dict[str, float] = {
            "cargo": 0.0,
            "mro": 0.0,
            "business": 0.0,
            "low_cost": 0.0,
            "scheduled": 0.0,
            "helicopter": 0.0,
            "ground_ops": 0.0,
            "atc": 0.0,
        }

        patterns = {
            "cargo": {
                "keywords": [
                    "cargo",
                    "freight",
                    "logistics",
                    "supply chain",
                    "warehouse",
                    "loadmaster",
                    "acm",
                    "main-deck",
                    "pallet",
                ],
                "phrases": [
                    "cargo operations",
                    "freight forwarder",
                    "cargo agent",
                    "main deck",
                    "cargo handler",
                ],
            },
            "mro": {
                "keywords": [
                    "mro",
                    "maintenance",
                    "repair",
                    "overhaul",
                    "mechanic",
                    "technician",
                    "avionics",
                    "sheet metal",
                    "a&p",
                    "license",
                    "b1",
                    "b2",
                    "base maintenance",
                    "line maintenance",
                    "aog",
                    "camu",
                ],
                "phrases": [
                    "aircraft maintenance",
                    "engine repair",
                    "component overhaul",
                    "heavy maintenance",
                    "technical records",
                    "airworthiness engineer",
                ],
            },
            "business": {
                "keywords": [
                    "bizjet",
                    "private jet",
                    "vip",
                    "vvip",
                    "charter",
                    "corporate",
                    "fractional",
                    "fbo",
                    "signature",
                    "signature-aviation",
                    "atlantic aviation",
                ],
                "phrases": [
                    "business aviation",
                    "executive jet",
                    "private aviation",
                    "corporate flight",
                    "vip cabin",
                ],
            },
            "helicopter": {
                "keywords": [
                    "helicopter",
                    "rotor",
                    "rotary",
                    "vtol",
                    "hems",
                    "offshore",
                    "heli-deck",
                ],
                "phrases": [
                    "rotary wing",
                    "helicopter pilot",
                    "rotorcraft maintenance",
                ],
            },
            "ground_ops": {
                "keywords": [
                    "ramp",
                    "baggage",
                    "gate",
                    "station",
                    "dispatcher",
                    "fueler",
                    "lounge",
                    "concierge",
                    "screener",
                    "aisats",
                    "celebi",
                    "menzies",
                    "bird group",
                ],
                "phrases": [
                    "ground handling",
                    "airport operations",
                    "passenger service",
                    "ramp agent",
                    "turnaround coordinator",
                ],
            },
            "atc": {
                "keywords": ["atc", "tower", "radar", "controller", "approach"],
                "phrases": ["air traffic", "flight data", "ground control"],
            },
        }

        # Check phrases (Higher weight)
        for op_type, data in patterns.items():
            for phrase in data["phrases"]:
                if phrase in text:
                    scores[op_type] += 2.0
            for kw in data["keywords"]:
                if kw in title_lower:  # Title matches are very strong
                    scores[op_type] += 1.5
                elif f" {kw} " in f" {text} ":  # Full word match in text
                    scores[op_type] += 1.0

        # Find best score
        # avoid type confusion by explicitly indexing the dict
        best_type = max(scores, key=lambda k: scores[k])
        if scores[best_type] >= 1.5:
            return best_type

        # 3. Airline/Passenger Default Logic
        low_cost_carriers = [
            "southwest",
            "ryanair",
            "easyjet",
            "wizz",
            "spirit",
            "frontier",
            "allegiant",
            "jetblue",
            "indigo",
            "airasia",
            "scoot",
            "volaris",
            "flydubai",
            "air arabia",
            "pegasus",
            "cebu pacific",
            "akasa",
        ]
        scheduled_carriers = [
            "american airlines",
            "delta",
            "united",
            "british airways",
            "lufthansa",
            "air france",
            "klm",
            "emirates",
            "qatar",
            "etihad",
            "singapore",
            "cathay",
            "ana",
            "jal",
            "qantas",
            "air india",
            "vistar",
        ]

        if any(lcc in company_lower for lcc in low_cost_carriers):
            return "low_cost"
        if any(sc in company_lower for sc in scheduled_carriers):
            return "scheduled"

        airline_keywords = [
            "airline",
            "airways",
            "flight",
            "pilot",
            "cabin crew",
            "flight attendant",
            "aircraft",
        ]
        if any(keyword in text for keyword in airline_keywords):
            return "passenger"

        return None

    def _calculate_deduplication_hash(
        self, title: str, company: str, location: str
    ) -> str:
        """
        Calculate a deduplication hash based on title, company, and location.
        This helps identify the same job across different sources.
        """
        # Normalize fields for hashing
        norm_title = title.lower().strip()
        # Use smarter normalization for company
        norm_company = CompanyManager.normalize_company_name(company)
        norm_location = location.lower().strip() if location else ""

        # Create composite string
        composite = f"{norm_title}|{norm_company}|{norm_location}"
        return hashlib.md5(composite.encode("utf-8")).hexdigest()

    @sync_to_async
    def is_url_scraped(self, url: str) -> bool:
        """Check if URL has been scraped before"""
        exists = ScrapedURL.objects.filter(url=url).exists()
        if exists:
            logger.debug(f"URL already in database: {url[:100]}...")
        return exists

    @sync_to_async
    def get_scraped_urls(self, source: Optional[str] = None) -> Set[str]:
        """Get set of all scraped URLs, optionally filtered by source"""
        queryset = ScrapedURL.objects.all()
        if source:
            queryset = queryset.filter(source=source)
            logger.debug(f"Retrieved {queryset.count()} URLs for source: {source}")
        else:
            logger.debug(f"Retrieved {queryset.count()} URLs from all sources")
        return set(queryset.values_list("url", flat=True))

    def add_or_update_job(self, job_data: Dict, source: str) -> tuple[bool, str]:
        """
        Add new job or update existing one
        Returns: (is_new, message)
        """
        url = job_data.get("url")
        job_id = job_data.get("job_id")
        title = (job_data.get("title") or "No Title")[:50]

        if not url:
            logger.warning(f"Job missing URL, skipping: {title}")
            return False, "Missing required field: url"

        try:
            # Update or create ScrapedURL (for tracking/deduplication)
            scraped_url, url_created = ScrapedURL.objects.update_or_create(
                url=url,
                defaults={
                    "job_id": job_id or url,
                    "source": source,
                    "title": job_data.get("title", "No Title"),
                    "company": job_data.get("company", "Unknown"),
                    "job_data": job_data,
                    "is_active": True,
                },
            )

            if not url_created:
                scraped_url.scrape_count += 1
                scraped_url.save(update_fields=["scrape_count", "last_scraped"])
                logger.debug(
                    f"Updated ScrapedURL (count={scraped_url.scrape_count}): {title}"
                )
            else:
                logger.debug(f"Created new ScrapedURL: {title}")

            # Save to main jobs.Job model for application use
            job_obj, job_created = self._save_to_jobs_model(job_data, source)

            # Return True if it's a new job in the main Job table
            if job_created:
                logger.info(f"[{source}] New job added: {title}")
                return True, "New job added"
            else:
                logger.debug(f"[{source}] Job updated: {title}")
                return False, "Job updated"
        except Exception as e:
            logger.error(
                f"[{source}] Error adding/updating job '{title}': {e}", exc_info=True
            )
            return False, f"Error: {str(e)}"

    def _save_to_jobs_model(self, job_data: Dict, source: str):
        """Save job to main jobs.Job model for application use"""
        try:
            # Extract and normalize fields
            title = job_data.get("title", "No Title").strip()
            company = (job_data.get("company") or job_data.get("recruiter") or "Unknown").strip()
            url = job_data.get("url", "").strip()
            location = self._clean_location(job_data.get("location", "").strip(), company=company)
            description = job_data.get("description", "").strip()

            if not url:
                logger.error(f"Job URL is required for: {title}")
                return None, False

            # Parse posted_date if it's a string
            posted_date = job_data.get("posted_date")
            if isinstance(posted_date, str):
                from dateutil import parser
                from datetime import datetime as _dt

                try:
                    # Clean up common prefixes (e.g., "Posted 4 Days Ago" -> "4 days ago")
                    clean_date = posted_date.lower()
                    for prefix in ("posted on", "posted", "updated", "published"):
                        clean_date = clean_date.replace(prefix, "").strip()

                    # Use local date (not UTC) for relative dates to avoid timezone-induced
                    # off-by-one errors (e.g. IST is +5:30 ahead of UTC).
                    local_today = _dt.now().date()

                    # Handle relative dates
                    if "yesterday" in clean_date:
                        from datetime import timedelta as _td

                        posted_date = local_today - _td(days=1)
                    elif "today" in clean_date or "just now" in clean_date:
                        posted_date = local_today
                    elif "ago" in clean_date:
                        # "30+ days ago", "2 days ago", "4 Days Ago"
                        import re as _re
                        from datetime import timedelta as _td

                        # Weeks
                        wm = _re.search(r"(\d+)\s*weeks?", clean_date)
                        if wm:
                            posted_date = local_today - _td(weeks=int(wm.group(1)))
                        else:
                            dm = _re.search(r"(\d+)", clean_date)
                            if dm:
                                days = int(dm.group(1))
                                posted_date = local_today - _td(days=days)
                            else:
                                posted_date = None
                    else:
                        posted_date = parser.parse(posted_date).date()
                except Exception as e:
                    logger.debug(f"Could not parse posted_date '{posted_date}': {e}")
                    posted_date = None

            # Extract country code from location
            country_code = self._extract_country_code(location, company)

            # Infer operation type from job data
            operation_type = self._infer_operation_type(title, company, description)
            job_category = infer_job_category(
                title=title,
                description=description,
                primary_category=job_data.get("primary_category"),
                matched_categories=job_data.get("matched_categories"),
                matched_filter_types=job_data.get("matched_filter_types"),
                existing_category=job_data.get("job_category"),
            )

            # 1. Normalize company name using CompanyManager
            mapped_company = company
            norm_company = CompanyManager.normalize_company_name(company)

            # Use existing mapping if available
            mapping = CompanyMapping.objects.filter(
                normalized_name=norm_company
            ).first()
            if mapping:
                mapped_company = mapping.company_name
                if not operation_type:
                    operation_type = mapping.operation_type
                if not country_code:
                    country_code = mapping.country_code

            # 2. Calculate deduplication hash
            self._calculate_deduplication_hash(title, mapped_company, location)

            # Build defaults dict but avoid overwriting existing fields with None
            defaults = {
                "title": title,
                "company": mapped_company,
                "location": location,
                "description": description,
                "source": source,
                "country_code": country_code,
                "operation_type": operation_type,
                "job_category": job_category,
                "raw_json": job_data,
                "retrieved_date": timezone.now(),
                "salary_min": job_data.get("salary_min"),
                "salary_max": job_data.get("salary_max"),
                "salary_currency": job_data.get("salary_currency", "USD"),
            }

            if posted_date is not None:
                defaults["posted_date"] = posted_date
            else:
                from datetime import datetime as _dt

                defaults["posted_date"] = _dt.now().date()

            # 3. Handle Deduplication - Check by URL first (exact match)
            # Then check by dedup_hash (cross-source match)
            job = Job.objects.filter(url=url).first()
            if not job:
                # Potential cross-source duplicate?
                # We check for active jobs with the same hash
                job = (
                    Job.objects.filter(status="active")
                    .filter(
                        title__iexact=title,
                        company__iexact=mapped_company,
                        location__iexact=location,
                    )
                    .first()
                )
                # Or use the hash if we had a field for it, for now we use an exact field match query
                # as a proxy for the hash logic until we add a field.

            if job:
                # Keep existing status if closed; otherwise update fields
                current_status = job.status
                # If it's the SAME URL, we just update it
                if job.url == url:
                    for k, v in defaults.items():
                        setattr(job, k, v)
                    if current_status != "closed":
                        job.status = "active"
                    job.last_checked = timezone.now()
                    job.save()
                    job_created = False
                else:
                    # DIFFERENT URL but SAME JOB (Deduplication!)
                    # We link the ScrapedURL to this existing Job but don't create a new Job record
                    logger.info(
                        f"[{source}] Deduplicated job (cross-source): {title} already exists from {job.source}"
                    )
                    job_created = False
            else:
                # Create a new Job record and set status to active
                defaults["status"] = "active"
                job = Job.objects.create(url=url, **defaults)
                job_created = True

            if job_created:
                logger.info(f"Created new Job record: {title[:50]}")
            else:
                logger.debug(f"Updated/Deduplicated Job record: {title[:50]}")

            # Auto-create company mapping for standardization
            if mapped_company and mapped_company != "Unknown":
                self._auto_create_company_mapping(mapped_company, source)

            return job, job_created

        except Exception as e:
            logger.error(f"Error saving to Job model: {e}", exc_info=True)
            return None, False

    def _auto_create_company_mapping(self, company_name: str, source: str):
        """Auto-create company mapping for standardization"""
        if not company_name:
            return

        normalized = company_name.strip().lower()

        mapping, created = CompanyMapping.objects.get_or_create(
            normalized_name=normalized,
            defaults={
                "company_name": company_name,
                "auto_created": True,
                "needs_review": True,
            },
        )

        if created:
            logger.debug(
                f"[{source}] Created company mapping: {company_name} -> {normalized}"
            )

    def add_jobs_batch(self, jobs: List[Dict], source: str) -> Dict[str, int]:
        """
        Add multiple jobs at once - optimized with pre-fetching
        """
        from django.db import transaction
        from jobs.models import CompanyMapping

        stats = {
            "total": len(jobs),
            "new": 0,
            "updated": 0,
            "duplicate": 0,
            "errors": 0,
        }

        logger.info(f"[{source}] Starting batch processing of {len(jobs)} jobs")

        # Pre-fetch all company mappings for these jobs to avoid N queries
        companies = {
            job.get("company", "").strip().lower() for job in jobs if job.get("company")
        }
        {
            m.normalized_name: m
            for m in CompanyMapping.objects.filter(normalized_name__in=companies)
        }

        for idx, job in enumerate(jobs, 1):
            try:
                with transaction.atomic():
                    # Pass the pre-fetched mappings to add_or_update_job if possible
                    # For now, we'll just let the transaction handle it, but pre-fetching
                    # here puts them in the ORM cache if using the same process.
                    is_new, message = self.add_or_update_job(job, source)
                    job["_is_new"] = is_new
                    if is_new:
                        stats["new"] += 1
                    else:
                        stats["updated"] += 1

                if idx % 10 == 0:
                    logger.debug(f"[{source}] Processed {idx}/{len(jobs)} jobs")

            except Exception as e:
                stats["errors"] += 1
                job_title = (job.get("title") or "unknown")[:50]
                logger.error(f"[{source}] Error adding job '{job_title}': {e}")

        stats["duplicate"] = stats["total"] - stats["new"]
        return stats

    @sync_to_async
    def log_scrape_session(self, source: str, stats: Dict, duration: float):
        """Log scraping session - already handled by ScraperJob model"""
        pass

    def get_all_jobs(
        self, source: Optional[str] = None, active_only: bool = True
    ) -> List[Dict]:
        """Get all jobs from database"""
        queryset = ScrapedURL.objects.all()

        if source:
            queryset = queryset.filter(source=source)

        if active_only:
            queryset = queryset.filter(is_active=True)

        return [obj.job_data for obj in queryset]

    def get_statistics(self) -> Dict:
        """Get database statistics"""
        from django.db.models import Count

        total_jobs = ScrapedURL.objects.count()
        # build a proper mapping from source -> count instead of passing a
        # ValuesQuerySet to dict() (mypy dislikes the type and the runtime
        # behaviour is not what we want).
        by_source = {
            item["source"]: item["count"]
            for item in ScrapedURL.objects.values("source").annotate(count=Count("id"))
        }

        recent_scrapes = list(
            ScraperJob.objects.order_by("-created_at")[:10].values(
                "scraper_name", "created_at", "jobs_found", "jobs_new", "jobs_duplicate"
            )
        )

        most_scraped = list(
            ScrapedURL.objects.order_by("-scrape_count")[:5].values(
                "url", "title", "company", "scrape_count"
            )
        )

        return {
            "total_jobs": total_jobs,
            "jobs_by_source": by_source,
            "recent_scrapes": recent_scrapes,
            "most_scraped": most_scraped,
        }

    def mark_job_inactive(self, url: str):
        """Mark a job as inactive"""
        ScrapedURL.objects.filter(url=url).update(is_active=False)

    def mark_job_closed(self, url: str, reason: Optional[str] = None):
        """Mark a job as closed/expired in both ScrapedURL and Job models"""
        try:
            ScrapedURL.objects.filter(url=url).update(is_active=False)
            Job.objects.filter(url=url).update(
                status="closed", last_checked=timezone.now()
            )
            logger.info(f"Marked job closed: {url} reason={reason}")
            return True
        except Exception as e:
            logger.error(f"Failed to mark job closed for {url}: {e}", exc_info=True)
            return False

    async def check_job_active(
        self, url: str, job_obj: Optional[Job] = None, use_playwright: bool = False
    ) -> tuple[bool, str]:
        """
        Check whether a job page is still active.
        Optimized to check date fields in raw_json before network requests.
        Returns (is_active, reason)
        """
        import asyncio
        import urllib.parse

        try:
            # 1. Smart Expiry Check: Check raw_json for explicit expiry dates first
            if job_obj and job_obj.raw_json:
                raw = job_obj.raw_json
                # List of common keys for expiry dates
                expiry_keys = [
                    "valid_through",
                    "validThrough",
                    "expiration_date",
                    "expiry_date",
                    "expires_at",
                    "closing_date",
                    "deadline",
                ]

                for key in expiry_keys:
                    val = raw.get(key)
                    if val:
                        try:
                            from dateutil import parser

                            exp_date = parser.parse(val).date()
                            if exp_date < timezone.now().date():
                                return False, f"data_expired:{key}:{val}"
                        except Exception:
                            continue

            # 2. Lightweight requests check with timeout
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }

            try:
                # Wrap in asyncio timeout for safety
                r = await asyncio.wait_for(
                    sync_to_async(curl_requests.get)(
                        url,
                        headers=headers,
                        timeout=15,  # Increased from 10 for slow sites
                        allow_redirects=True,
                        impersonate="chrome110",
                    ),
                    timeout=20,  # Overall timeout
                )
            except asyncio.TimeoutError:
                logger.warning(f"Timeout checking {url}")
                return True, "request_timeout"
            except Exception as e:
                logger.warning(f"Request failed for {url}: {e}")
                return True, "request_failed"

            status = r.status_code
            if status in (404, 410):
                return False, f"http_{status}"

            # Check redirects - improved logic
            if len(r.history) > 0:
                final_url = r.url
                parsed_final = urllib.parse.urlparse(final_url)
                parsed_original = urllib.parse.urlparse(url)

                # Check if redirected to homepage or generic careers page
                final_path = parsed_final.path.strip("/").lower()
                generic_paths = [
                    "",
                    "jobs",
                    "careers",
                    "opportunities",
                    "vacancies",
                    "positions",
                    "en-us",
                    "search-results",
                    "all-jobs",
                    "job-search",
                    "job-not-found",
                    "job-expired",
                    "application-closed",
                    "job-closed",
                ]
                if final_path in generic_paths:
                    return False, f"redirected_to_generic_page:{final_path}"

                # Check if domain changed (usually bad sign, unless it's a known SSO/Job board redirect)
                if parsed_final.netloc != parsed_original.netloc:
                    # Allow common subdomains like jobs.boeing.com or career.airbus.com
                    # Also common job board patterns
                    known_patterns = [
                        "jobs.",
                        "career.",
                        "careers.",
                        "recruitment.",
                        "hiring.",
                        "talent.",
                    ]
                    if not any(
                        known in parsed_final.netloc for known in known_patterns
                    ):
                        # Some companies redirect to a global portal, but generic ones are usually bad
                        if any(
                            generic in parsed_final.netloc
                            for generic in ["workday", "icims", "lever", "greenhouse"]
                        ):
                            # These are usually fine as they are ATS systems
                            pass
                        else:
                            return False, f"domain_changed:{parsed_final.netloc}"

            body = r.text or ""
            body_lower = body.lower()

            # Check for Workday invalid-url redirect pattern
            if (
                "community.workday.com/invalid-url" in body_lower
                or "window.location.href" in body_lower
                and "invalid" in body_lower
            ):
                return False, "workday_invalid_url_redirect"

            # Look for closed/expired keywords (removed overly broad "search results")
            closed_keywords = [
                # --- Filled / Selected ---
                "position has been filled",
                "position is filled",
                "role has been filled",
                "role is filled",
                "vacancy has been filled",
                "vacancy filled",
                "job has been filled",
                "job opening filled",
                "opening has been filled",
                # --- Specific Job Board / ATS Errors ---
                "the job that you were looking for either does not exist or is no longer open",
                "does not exist or is no longer open",
                "successfully filled",
                "has already been filled",
                "already filled",
                "candidate has been selected",
                "candidate selected",
                "we have hired",
                "position has been successfully filled",
                "role successfully filled",
                "hiring completed",
                "position filled internally",
                "position filled by internal candidate",
                "offer accepted",
                "position has been awarded",
                "this opportunity has been filled",
                # --- Closed / Expired ---
                "job is closed",
                "job has closed",
                "job closed",
                "position closed",
                "vacancy closed",
                "posting is closed",
                "posting has closed",
                "applications are closed",
                "applications have closed",
                "application closed",
                "job expired",
                "this job has expired",
                "this job posting has expired",
                "posting expired",
                "listing has expired",
                "the listing has expired",
                "role has closed",
                "this vacancy has closed",
                "this vacancy is closed",
                "position is no longer open",
                "this position is no longer open",
                "no longer open",
                "opportunity closed",
                "job opportunity closed",
                "recruitment closed",
                "hiring closed",
                # --- No Longer Available ---
                "this job is no longer available",
                "job no longer available",
                "position no longer available",
                "role no longer available",
                "vacancy is no longer available",
                "no longer available",
                "job unavailable",
                "position is unavailable",
                "role unavailable",
                "job posting unavailable",
                "listing unavailable",
                "opportunity no longer available",
                "job you are looking for is no longer available",
                "this posting is no longer active",
                "no longer active",
                "not active",
                "inactive job",
                "this role is no longer active",
                "position is inactive",
                # --- Not Accepting Applications ---
                "no longer accepting applications",
                "applications are no longer being accepted",
                "not accepting applications",
                "not accepting new applications",
                "we are no longer accepting applications",
                "no longer being accepted",
                "application deadline has passed",
                "application period has ended",
                "application window has closed",
                "deadline has passed",
                "past the application deadline",
                "applications closed for this role",
                "submission closed",
                "cannot accept applications",
                "applications disabled",
                "apply button disabled",
                # --- Removed / Cancelled / Paused ---
                "job has been removed",
                "posting has been removed",
                "listing has been removed",
                "job removed",
                "listing taken down",
                "job taken down",
                "position has been cancelled",
                "job has been cancelled",
                "vacancy cancelled",
                "requisition cancelled",
                "job cancelled",
                "position withdrawn",
                "job withdrawn",
                "hiring paused",
                "hiring for this role is paused",
                "role has been put on hold",
                "position on hold",
                "opening on hold",
                "recruitment on hold",
                "temporarily on hold",
                "job suspended",
                "posting suspended",
                # --- Requisition / ATS Specific ---
                "requisition is closed",
                "requisition has been closed",
                "job requisition closed",
                "job requisition has been closed",
                "job requisition is filled",
                "req has been closed",
                "req closed",
                "requisition filled",
                "requisition no longer active",
                "job id is closed",
                "job id not active",
                "job requisition expired",
                "position requisition closed",
                # --- Not Found / Invalid / Error ---
                "page not found",
                "404 not found",
                "404 error",
                "error 404",
                "404 page not found",
                "job not found",
                "job listing not found",
                "could not find the job",
                "job does not exist",
                "job no longer exists",
                "this page does not exist",
                "page does not exist",
                "invalid job id",
                "invalid job code",
                "invalid requisition",
                "invalid url",
                "the url you have provided is invalid",
                "this link is invalid",
                "broken link",
                "page cannot be found",
                "position cannot be found",
                "listing not found",
                "not found or has expired",
                # --- Portal / Board Removal ---
                "removed from the board",
                "removed by employer",
                "no longer being advertised",
                "ad has expired",
                "advert expired",
                "advert has closed",
                "job ad expired",
                "job ad closed",
                "posting no longer available",
                "advert no longer available",
                "job is offline",
                "posting offline",
                # --- Generic Fail States ---
                "position unavailable",
                "opportunity unavailable",
                "job is inactive",
                "posting inactive",
                "vacancy inactive",
                "career opportunity closed",
                "opportunity has ended",
                "opportunity expired",
                "opening expired",
                "opening closed",
                "no vacancies",
                "currently not hiring",
                "we are not hiring for this role anymore",
                "future opportunities only",
            ]

            # Limit search to first 100KB for efficiency
            search_body = body_lower[:100000]

            for kw in closed_keywords:
                # Hotfix for AviaNation: "job expired" matches incorrectly on active pages
                if "avianation.com" in url and kw == "job expired":
                    continue

                if kw in search_body:
                    return False, f"closed_keyword:{kw}"

            # 4. Check for dynamic/JS redirect snippets in body
            redirect_patterns = [
                r'window\.location\.replace\(["\'](.*?)["\']\)',
                r'window\.location\.href\s*=\s*["\'](.*?)["\']',
                r'meta\s+http-equiv=["\']refresh["\']\s+content=["\']\d+;url=(.*?)["\']',
            ]
            for pat in redirect_patterns:
                match = re.search(pat, body, re.IGNORECASE)
                if match:
                    redir_target = match.group(1)
                    if any(
                        x in redir_target.lower()
                        for x in ["login", "expired", "closed", "notfound"]
                    ):
                        return False, f"js_redirect_to_closure:{redir_target}"

            # JSON-LD date checks (also limited to first 100KB for consistency)
            json_ld_section = body[:100000]
            for match in re.findall(
                r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
                json_ld_section,
                re.DOTALL | re.IGNORECASE,
            ):
                try:
                    data = json.loads(match)
                except Exception:
                    continue
                items = data if isinstance(data, list) else [data]
                for item in items:
                    if isinstance(item, dict) and (
                        "JobPosting" in item.get("@type", "")
                        or item.get("@type") == "JobPosting"
                    ):
                        valid_through = item.get("validThrough") or item.get(
                            "valid_through"
                        )
                        if valid_through:
                            try:
                                from dateutil import parser

                                vt_date = parser.parse(valid_through).date()
                                if vt_date < timezone.now().date():
                                    return False, "validThrough_expired"
                            except Exception:
                                pass

            if use_playwright:
                try:
                    from playwright.async_api import async_playwright

                    async with async_playwright() as p:
                        browser = await p.chromium.launch(headless=True)
                        context = await browser.new_context(
                            user_agent=headers["User-Agent"]
                        )
                        page = await context.new_page()
                        try:
                            resp = await page.goto(
                                url, wait_until="domcontentloaded", timeout=20000
                            )
                            if not resp or resp.status in (404, 410):
                                return (
                                    False,
                                    f"pw_http_{resp.status if resp else 'no_resp'}",
                                )

                            # Final state check
                            final_url = page.url
                            if any(
                                x in final_url.lower()
                                for x in ["expired", "closed", "job-not-found"]
                            ):
                                return False, f"pw_url_closure:{final_url}"

                            # Check for text visibility
                            for kw in closed_keywords:
                                if await page.get_by_text(kw, exact=False).is_visible():
                                    return False, f"pw_keyword_visible:{kw}"

                        finally:
                            await browser.close()
                except Exception as e:
                    logger.warning(f"Playwright check failed for {url}: {e}")

            return True, "ok"

        except Exception as e:
            logger.debug(f"check_job_active error for {url}: {e}")
            return True, "check_error"

    async def verify_active_jobs(self, limit: int = 100):
        """
        Verify status of currently active jobs.
        Returns statistics of the check.
        """
        from jobs.models import Job

        active_jobs = Job.objects.filter(status="active").order_by("last_checked")[
            :limit
        ]

        stats = {"total": 0, "stayed_active": 0, "closed": 0, "errors": 0}

        for job in active_jobs:
            stats["total"] += 1
            is_active, reason = await self.check_job_active(job.url, job_obj=job)

            if not is_active:
                job.status = "closed"
                job.last_checked = timezone.now()
                job.save(update_fields=["status", "last_checked"])
                stats["closed"] += 1
                logger.info(
                    f"Marked job closed during verification: {job.title} ({reason})"
                )
            else:
                job.last_checked = timezone.now()
                job.save(update_fields=["last_checked"])
                stats["stayed_active"] += 1

        return stats

    def print_statistics(self):
        """Log database statistics"""
        stats = self.get_statistics()

        logger.info("=" * 70)
        logger.info("📊 DATABASE STATISTICS")
        logger.info("=" * 70)
        logger.info(f"Total Jobs in Database: {stats['total_jobs']}")

        logger.info("Jobs by Source:")
        for source, count in stats["jobs_by_source"].items():
            logger.info(f"  • {source}: {count} jobs")

        if stats["most_scraped"]:
            logger.info("Most Frequently Scraped Jobs:")
            for job in stats["most_scraped"]:
                logger.info(
                    f"  • {job['title']} at {job['company']} - {job['scrape_count']} times"
                )

        logger.info("=" * 70)
