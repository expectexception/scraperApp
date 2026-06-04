import asyncio
import logging
import requests

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

USAJOBS_API_URL = "https://data.usajobs.gov/api/search"
USAJOBS_HEADERS = {
    "Host": "data.usajobs.gov",
    "User-Agent": "aeroops-scraper@example.com",
    "Authorization-Key": "",  # Public endpoint works without key for basic queries
}

# Aviation-relevant occupation series
OCCUPATION_CODES = ["2151", "0086", "2181", "1601", "0301"]
KEYWORDS = [
    "dispatcher",
    "flight dispatcher",
    "operations controller",
    "OCC",
    "air traffic",
]


class UsajobsScraper(BaseScraper):
    """
    Scraper for USAJOBS (US Federal) via public REST API.
    Targets aviation dispatch / OCC roles (GS-2151, GS-0086).
    """

    def __init__(self, config, db_manager=None):
        super().__init__(config, site_key="usajobs", db_manager=db_manager)
        self.api_url = USAJOBS_API_URL
        self.company_name = "USAJOBS (Federal)"
        self.base_url = "https://www.usajobs.gov"

    async def fetch_jobs(self) -> list:
        jobs = []
        logger.info(f"[{self.site_key}] Fetching USAJOBS listings via public API...")

        for keyword in KEYWORDS:
            try:
                params = {
                    "Keyword": keyword,
                    "ResultsPerPage": 50,
                    "SortField": "OpenDate",
                    "SortDirection": "Desc",
                }
                resp = requests.get(
                    self.api_url,
                    params=params,
                    headers=USAJOBS_HEADERS,
                    timeout=30,
                )
                if resp.status_code != 200:
                    logger.warning(
                        f"[{self.site_key}] API returned {resp.status_code} for keyword={keyword}"
                    )
                    continue

                data = resp.json()
                items = data.get("SearchResult", {}).get("SearchResultItems", [])
                logger.info(
                    f"[{self.site_key}] keyword={keyword}: {len(items)} results"
                )

                for item in items:
                    if self.max_jobs and len(jobs) >= self.max_jobs:
                        break

                    mv = item.get("MatchedObjectDescriptor", {})
                    title = mv.get("PositionTitle", "").strip()
                    if not title:
                        continue

                    locations = mv.get("PositionLocation", [])
                    location_str = (
                        ", ".join(
                            f"{loc.get('CityName', '')}, {loc.get('CountryCode', 'US')}"
                            for loc in locations
                        )
                        if locations
                        else "United States"
                    )

                    apply_uri = mv.get("ApplyURI", [""])[0]
                    job_id = mv.get("PositionID", str(hash(apply_uri)))
                    org = mv.get("OrganizationName", "US Government")
                    posted = mv.get("PublicationStartDate", "")[:10]
                    salary_min = mv.get("PositionRemuneration", [{}])[0].get(
                        "MinimumRange", ""
                    )
                    salary_max = mv.get("PositionRemuneration", [{}])[0].get(
                        "MaximumRange", ""
                    )
                    salary = f"${salary_min}–${salary_max}" if salary_min else ""

                    job_url = f"{self.base_url}/job/{job_id}"

                    jobs.append(
                        {
                            "company": org,
                            "title": title,
                            "location": location_str,
                            "url": job_url,
                            "source_url": self.api_url,
                            "apply_url": apply_uri or job_url,
                            "job_seq_no": job_id,
                            "is_active": True,
                            "posted_date": posted or None,
                            "salary": salary,
                        }
                    )

            except Exception as e:
                logger.error(f"[{self.site_key}] Error fetching keyword={keyword}: {e}")

            await asyncio.sleep(1)

        # Deduplicate by job_id
        seen = set()
        unique = []
        for j in jobs:
            if j["job_seq_no"] not in seen:
                seen.add(j["job_seq_no"])
                unique.append(j)

        logger.info(f"[{self.site_key}] Found {len(unique)} unique jobs")
        return unique

    async def fetch_job_descriptions(self, jobs) -> list:
        # Descriptions fetched via detail API
        logger.info(f"[{self.site_key}] Fetching descriptions for {len(jobs)} jobs...")
        for job in jobs:
            try:
                job_id = job.get("job_seq_no", "")
                if not job_id:
                    continue
                requests.get(
                    "https://data.usajobs.gov/api/referencedata/v1/codelists/PositionOfferingType",
                    timeout=15,
                )
                # Use the job detail page text instead
                detail_resp = requests.get(
                    f"https://data.usajobs.gov/api/search?PositionID={job_id}",
                    headers=USAJOBS_HEADERS,
                    timeout=20,
                )
                if detail_resp.status_code == 200:
                    d = detail_resp.json()
                    items = d.get("SearchResult", {}).get("SearchResultItems", [])
                    if items:
                        mv = items[0].get("MatchedObjectDescriptor", {})
                        duties = (
                            mv.get("UserArea", {})
                            .get("Details", {})
                            .get("MajorDuties", [])
                        )
                        req = (
                            mv.get("UserArea", {})
                            .get("Details", {})
                            .get("Requirements", "")
                        )
                        job["description"] = "\n".join(duties) + "\n" + str(req)
            except Exception as e:
                logger.warning(
                    f"[{self.site_key}] Desc fetch failed for {job.get('job_seq_no')}: {e}"
                )
            await asyncio.sleep(0.5)
        return jobs

    async def run(self):
        self.print_header()
        jobs = await self.fetch_jobs()
        if not jobs:
            return []

        if self.use_filter and self.filter_manager:
            jobs, _, filter_stats = self.apply_title_filter(jobs)
            self.filter_manager.print_filter_stats(filter_stats)
            if not jobs:
                return []

        jobs, _ = await self.filter_new_jobs(jobs)
        if not jobs:
            return []

        jobs = await self.fetch_job_descriptions(jobs)
        await self.save_results(jobs)
        return jobs
