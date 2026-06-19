"""
Configuration for Aviation Job Scraper
Edit these settings to control scraper behavior for different sites
"""

# Auto-Schedule Configuration
AUTO_SCHEDULE = {
    "enabled": True,  # Enable/disable automatic scheduling
    "run_all_scrapers": {
        "enabled": True,
        "schedule": "0 */3 * * *",  # Cron: Every 3 hours (HH:00)
        "description": "Run all enabled scrapers",
        "max_jobs": None,  # None = use per-scraper limits
    },
    "run_priority_scrapers": {
        "enabled": True,
        "schedule": "0 */6 * * *",  # Every 6 hours
        "description": "Run high-priority scrapers (Signature, LinkedIn, AviationJobSearch)",
        "scrapers": ["signature"],
    },
    "run_specialty_scrapers": {
        "enabled": True,
        "schedule": "0 1 * * *",  # Daily at 01:00
        "description": "Run specialty airline scrapers (IndiGo, Air India, Cargolux)",
        "scrapers": ["indigo", "airindia", "cargolux"],
    },
    "cleanup_old_jobs": {
        "enabled": True,
        "schedule": "0 3 * * 0",  # Weekly on Sunday at 03:00
        "description": "Archive/cleanup jobs older than 90 days",
    },
    "generate_report": {
        "enabled": True,
        "schedule": "0 23 * * *",  # Daily at 23:00
        "description": "Generate daily scraper report",
    },
}

# Global Scraper Settings
SCRAPER_SETTINGS = {
    # Number of concurrent browser pages for description extraction
    "batch_size": 3,  # Reduced from 5 to be less aggressive
    # Output directory
    "output_dir": "output",
    # Anti-Detection Settings
    "stealth_mode": True,
    "request_delay_min": 2,  # Minimum delay between requests (seconds)
    "request_delay_max": 5,  # Maximum delay between requests (seconds)
    "page_load_delay": 3,  # Extra delay after page load (seconds)
    "random_scroll": True,  # Simulate human scrolling
    "random_mouse": True,  # Simulate mouse movements
    # Browser impersonation targets for TLS fingerprinting (curl_cffi)
    # Rotating these makes the scraper much harder to detect
    # Note: Only desktop browser impersonations are supported by curl_cffi
    "impersonate_list": ["chrome110", "chrome120", "edge101", "firefox"],
    "user_agents": [
        # --- Google Chrome (Windows) ---
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        # --- Google Chrome (macOS) ---
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        # --- Google Chrome (Linux) ---
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        # --- Mozilla Firefox (Windows) ---
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
        # --- Mozilla Firefox (macOS) ---
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:126.0) Gecko/20100101 Firefox/126.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) Gecko/20100101 Firefox/125.0",
        # --- Microsoft Edge (Windows) ---
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
        # --- Apple Safari (macOS) ---
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    ],
    # Proxy Settings (optional - add your proxies here)
    "proxy_list": [],  # Example: ['http://user:pass@proxy1.com:8080', 'http://proxy2.com:8080']
    "rotate_proxy": False,
    # Title Filtering Settings
    # ---------------------------
    # Global settings for the job filtering system (JobFilterManager).
    # - filter_file: JSON file containing categories and keywords.
    # - filter_before_scrape: Filter by title BEFORE fetching descriptions.
    #   (Saves significant time and resources).
    "filter_file": "filter_title.json",
    "filter_before_scrape": True,
    # Priority Levels for scrapers (higher = more priority)
    "priority_levels": {
        "absjets": "medium",
        "aegean": "medium",
        "aena": "medium",
        "airfrance": "medium",
        "airfrancehop": "medium",
        "airmalta": "medium",
        "airserbia": "medium",
        "alsieexpress": "medium",
        "amapolaflyg": "medium",
        "aslairlinesbelgium": "medium",
        "austrianairlines": "medium",
        "blueislands": "medium",
        "braathens": "medium",
        "bristow": "medium",
        "brusselsairlines": "medium",
        "buraqair": "medium",
        "buzz": "medium",
        "cabotaviation": "medium",
        "capitalairlines": "medium",
        "carpatair": "medium",
        "dat": "medium",
        "easternairways": "medium",
        "easyjet": "medium",
        "edelweiss": "medium",
        "egyptair": "medium",
        "elal": "medium",
        "ethiopian": "medium",
        "eurowings": "medium",
        "finnair": "medium",
        "flybe": "medium",
        "hahnair": "medium",
        "iberia": "medium",
        "iberiaexpress": "medium",
        "icelandair": "medium",
        "itaairways": "medium",
        "klm": "medium",
        "lufthansacityline": "medium",
        "norwegian": "medium",
        "olympicair": "medium",
        "ryanair": "medium",
        "sas": "medium",
        "smartwings": "medium",
        "swiss": "medium",
        "tap": "medium",
        "transavia": "medium",
        "tuiairways": "medium",
        "vueling": "medium",
        "aerlingus": "medium",
        "airbaltic": "medium",
        "airdolomiti": "medium",
        "airnostrum": "medium",
        "signature": "high",  # Always run - reliable source
        "aap": "medium",
        "cargolux": "medium",  # Airline-specific
        "airindia": "medium",  # Airline-specific
        "indigo": "medium",  # Airline-specific (fixed recently)
        "aisats": "medium",  # Ground handling
        "etihad": "medium",
        "flyadeal": "medium",
        "flynas": "medium",
        "gulfair": "medium",
        "jetfly": "medium",
        "kuwaitairways": "medium",
        "nesma": "medium",
        "omanair": "medium",
        "salamair": "medium",
        "saudia": "medium",
        "wmd": "medium",
        "flydubai": "medium",
        "ameriflight": "medium",
        "pacificaviation": "medium",
        "airarabia": "medium",
        "airarabia_auh": "medium",
        "royaljet": "medium",
        "dubairaw": "low",
        "falconaviation": "medium",
        "spirit": "high",
        "mesa": "medium",
        "delta": "high",
        "sun_country": "medium",
        "mountain_air_cargo": "medium",
        "air_wisconsin": "medium",
        "atsg": "medium",
        "nac": "medium",
        "omni_air": "medium",
        "kalitta_holdings": "medium",
        "jet_aviation": "medium",
        "riyadh_air": "medium",
        "global_jet": "medium",
        "global_jet": "medium",
        "fedex": "medium",
        "fedex_euro_dispatch": "medium",
        "kalitta_air": "medium",
        "envoy_air": "medium",
        "atlas_air": "medium",
        "atlantic_aviation": "medium",
        "netjets": "medium",
        "wheels_up": "medium",
        "flexjet": "medium",
        "amerijet": "medium",
        "cargojet": "medium",
        "canadian_north": "medium",
        "rtx": "medium",
        "jetblue": "medium",
        "qatar": "medium",
        "dnatabrasil": "medium",
        "emploitic": "medium",
        "swissport": "medium",
        "menzies": "medium",
        "united": "high",
        "lynn": "medium",
        "starlinkaviation": "medium",
        "sunairjets": "medium",
        "moncton_adp": "medium",
        "hyperion": "medium",
        "magma": "medium",
        "maersk": "medium",
        "hevenaerotech": "medium",
        "pngair": "medium",
        "flyalliance": "medium",
        "flyscoot": "medium",
        "flytropic": "medium",
        "flyflair": "medium",
        "jetex": "medium",
        "helinet": "medium",
        "nationalairlines": "medium",
        "flyafricaworld": "medium",
        "allegiantair": "medium",
        "dcaviation": "medium",
        "airasia": "medium",
        "bbnairlines": "medium",
        "maximusair": "medium",
        "volotea": "medium",
        "philippineairlines": "medium",
        "adp_fbb94cb3": "medium",
        "flyporter": "medium",
        "alexjets": "medium",
        "templerecruitment": "medium",
        "astonjet": "medium",
        "airx": "medium",
        "helvetic": "medium",
        "hadid": "medium",
        "singaporeair": "medium",
        "vistaglobal": "medium",
        "transavia_fr": "medium",
        "latestpilotjobs": "medium",
        "aviationcareers": "medium",
        "flyinggroup": "medium",
        "luxaviation": "medium",
        "twenty_one_air": "medium",
        "sterling": "medium",
        "uchealth": "medium",
        "usajet": "medium",
        "igoxair": "medium",
        "phoenix_air_group": "medium",
        "cutter": "medium",
        "ups": "medium",
        "havenasg": "medium",
        "contour": "medium",
        "breeze_airways": "medium",
        "westjet": "medium",
        "cmacgm": "medium",
        "neosair": "medium",
        "hifly": "medium",
        "airarabia": "medium",
        "cargolux": "medium",
        "platoon": "medium",
        "flexjet": "medium",
        "skyexpress": "medium",
    },
}

# Per-Site Scraper Limits
SCRAPERS = {
    "two_excel": {
        "enabled": True,
        "headless": True,
    },
    "ascent": {
        "enabled": True,
        "headless": True,
    },
    "aviasg": {
        "enabled": True,
        "headless": True,
    },
    "fedex": {
        "enabled": True,
        "headless": True,
    },
    "fedex_euro_dispatch": {
        "enabled": True,
        "headless": True,
    },
    "dlr": {
        "enabled": True,
        "headless": True,
    },
    "lar": {
        "enabled": True,
        "headless": True,
    },
    "virgin_australia": {
        "enabled": True,
        "headless": True,
    },
    "menzies": {
        "enabled": True,
        "headless": True,
        "max_pages": 3,
        "max_jobs": 50,
    },
    "menzies_ultipro": {
        "enabled": True,
        "headless": True,
        "max_pages": 3,
        "max_jobs": 50,
    },
    "gojet": {
        "enabled": True,
        "headless": True,
    },
    "aeroguard": {
        "enabled": True,
        "headless": True,
    },
    "flyexclusive": {
        "enabled": True,
        "headless": True,
        "max_pages": 3,
        "max_jobs": 50,
    },
    "air_canada": {
        "enabled": True,
        "headless": True,
    },
    "challenge_group": {
        "enabled": True,
        "headless": True,
    },
    "glock": {
        "enabled": True,
        "headless": True,
    },
    "amazon_air": {
        "enabled": True,
        "headless": True,
        "max_pages": 3,
    },
    "absjets": {
    },
    "aegean": {
    },
    "aena": {
    },
    "airfrance": {
    },
    "airfrancehop": {
    },
    "airmalta": {
    },
    "airserbia": {
    },
    "alsieexpress": {
    },
    "amapolaflyg": {
    },
    "aslairlinesbelgium": {
    },
    "austrianairlines": {
    },
    "blueislands": {
    },
    "braathens": {
    },
    "bristow": {
    },
    "brusselsairlines": {
    },
    "buraqair": {
    },
    "buzz": {
    },
    "cabotaviation": {
    },
    "capitalairlines": {
    },
    "carpatair": {
    },
    "dat": {
    },
    "easternairways": {
    },
    "easyjet": {
    },
    "edelweiss": {
    },
    "egyptair": {
        "headless": False,
    },
    "elal": {
        "headless": False,
    },
    "ethiopian": {
    },
    "eurowings": {
    },
    "finnair": {
    },
    "flybe": {
    },
    "hahnair": {
    },
    "iberia": {
        "headless": False,
    },
    "iberiaexpress": {
        "headless": False,
    },
    "icelandair": {
        "headless": False,
    },
    "itaairways": {
        "headless": False,
    },
    "klm": {
        "headless": False,
    },
    "lufthansacityline": {
    },
    "norwegian": {
    },
    "olympicair": {
    },
    "ryanair": {
    },
    "sas": {
    },
    "smartwings": {
        "headless": False,
    },
    "swiss": {
    },
    "tap": {
    },
    "transavia": {
        "headless": False,
    },
    "tuiairways": {
    },
    "vueling": {
    },
    "aerlingus": {
    },
    "airbaltic": {
    },
    "airdolomiti": {
    },
    "airnostrum": {
    },
    "signature": {  # None = extract all jobs
        # None = no page limit
    },
    "aap": {  # Limit for testing
    },
    "cargolux": {
    },
    "airindia": {
    },
    "emirates": {
        "search_queries": ["Operations", "Dispatcher", "Manager"],
    },
    "boeing": {
        "search_queries": ["Operations", "Dispatcher", "Manager"],
        "search_locations": [
            "Singapore",
            "Australia",
            "Brazil",
            "United Kingdom",
            "Germany",
            "France",
            "Canada",
            "Washington",
        ],
    },
    "airbus": { "search_queries": ["Dispatch", "Operations", "Manager"]},
    "aisats": {
    },
    "jmc": {
        "timeout": 60,
    },
    "iata": {
        "timeout": 60,
    },
    "avianation": {
        "timeout": 60,
    },
    "wizzair": {
        "timeout": 60,
        "search_queries": [
            "Operations",
            "Dispatcher",
            "Manager",
        ],  # Default to all, or user specific like "Pilot"
    },
    "cpr": {
        "timeout": 60,
    },
    "nbaa": {
        "timeout": 60,
    },
    "starair": {
    },
    "lufthansa": {
    },
    "southwest": {
    },
    "ba": {
    },
    "cathay": {
    },
    "germanairways": {
    },
    "aa": {
    },
    "etihad": {
    },
    "flydubai": {
    },
    "ameriflight": {
    },
    "pacificaviation": {
    },
    "airarabia": {
    },
    "airarabia_auh": {
    },
    "royaljet": {
    },
    "abudhabiaviation": {
    },
    "falconaviation": {
    },
    "wmd": {
    },
    "jetfly": {
    },
    "kuwaitairways": {
    },
    "flyadeal": {
    },
    "flynas": {
    },
    "saudia": {
    },
    "nesma": {
    },
    "gulfair": {
    },
    "omanair": {
    },
    "salamair": {
    },
    "spirit": {
    },
    "mesa": {
    },
    "delta": {
    },
    "sun_country": {
    },
    "mountain_air_cargo": {
    },
    "air_wisconsin": {
    },
    "atsg": {
    },
    "nac": {
    },
    "omni_air": {
    },
    "kalitta_holdings": {
    },
    "jet_aviation": {
    },
    "riyadh_air": {
    },
    "global_jet": {
    },
    "aar_corp": {
    },
    "kalitta_air": {
    },
    "envoy_air": {
    },
    "atlas_air": {
    },
    "atlantic_aviation": {
    },
    "netjets": {
    },
    "wheels_up": {
    },
    "flexjet": {
    },
    "amerijet": {
    },
    "cargojet": {
    },
    "canadian_north": {
    },
    "rtx": {
    },
    "jetblue": {
    },
    "qatar": {
    },
    "dnatabrasil": {
    },
    "emploitic": {
    },
    "swissport": {
    },
    "menzies": {
    },
    "united": {
    },
    "lynn": {
    },
    "starlinkaviation": {
    },
    "sunairjets": {
    },
    "moncton_adp": {
    },
    "hyperion": {
    },
    "magma": {
    },
    "maersk": {
    },
    "hevenaerotech": {
    },
    "pngair": {
    },
    "flyalliance": {
    },
    "flyscoot": {
    },
    "flytropic": {
    },
    "flyflair": {
    },
    "jetex": {
    },
    "helinet": {
    },
    "nationalairlines": {
    },
    "flyafricaworld": {
    },
    "allegiantair": {
    },
    "dcaviation": {
    },
    "airasia": {
    },
    "bbnairlines": {
    },
    "maximusair": {
    },
    "volotea": {
    },
    "philippineairlines": {
    },
    "adp_fbb94cb3": {
    },
    "flyporter": {
    },
    "alexjets": {
    },
    "templerecruitment": {
    },
    "astonjet": {
    },
    "airx": {
    },
    "helvetic": {
    },
    "hadid": {
    },
    "singaporeair": {
    },
    "vistaglobal": {
    },
    "transavia_fr": {
    },
    "latestpilotjobs": {
    },
    "aviationcareers": {
    },
    "flyinggroup": {
    },
    "luxaviation": {
    },
    "ups": {
    },
    "havenasg": {
    },
    "contour": {
    },
    "breeze_airways": {
    },
    "westjet": {
    },
    "cmacgm": {
    },
    "neosair": {
    },
    "hifly": {
    },
    "airarabia": {
    },
    "cargolux": {
    },
    "platoon": {
    },
    "flexjet": {
    },
    "skyexpress": {
    },
    "twenty_one_air": {
    },
    "sterling": {
    },
    "uchealth": {
        "headless": False,
    },
    "usajet": {
    },
    "igoxair": {
    },
    "phoenix_air_group": {
    },
    "cutter": {
    },
}

# Site Configurations
SITES = {
    "two_excel": {
        "name": "2Excel",
        "base_url": "https://2excel.talosats-careers.com",
        "jobs_url": "https://2excel.talosats-careers.com/view-all-vacancies?what=&where=&iso=gb&radius=30&custom=-1-_-1-#vacancies-section-filters",
        "description": "2Excel Careers",
    },
    "ascent": {
        "name": "Ascent Flight Training",
        "base_url": "https://ascentflighttraining.com",
        "jobs_url": "https://ascentflighttraining.com/careers/",
        "description": "Ascent Flight Training Careers",
    },
    "aviasg": {
        "name": "Avia Solutions Group",
        "base_url": "https://careers.aviasg.com",
        "jobs_url": "https://careers.aviasg.com/en/search?keyword=&country=&businessSegment=&company=&category=",
        "description": "Avia Solutions Group Careers",
    },
    "dlr": {
        "name": "DLR",
        "base_url": "https://jobs.dlr.de",
        "jobs_url": "https://jobs.dlr.de/go/All-Jobs/9291501/",
        "description": "DLR Careers",
    },
    "lar": {
        "name": "LAR Careers",
        "base_url": "https://lar.careers",
        "jobs_url": "https://lar.careers/board/62729feb4cdf6e3a3a8dc30d",
        "description": "LAR Careers Careers",
    },
    "virgin_australia": {
        "name": "Virgin Australia",
        "base_url": "https://careers.virginaustralia.com",
        "jobs_url": "https://careers.virginaustralia.com/jobs/search",
        "description": "Virgin Australia Careers",
        "class": "VirginAustraliaScraper",
        "module": "scraper_manager.scrapers.virginaustralia_scraper",
    },
    "usajobs": {
        "name": "USAJOBS",
        "enabled": True,
        "base_url": "https://www.usajobs.gov",
        "jobs_url": "https://www.usajobs.gov/Search/Results",
        "description": "Primary federal hub. Use series code GS-2151 for Dispatching and GS-0086 for Emergency/Security dispatch",
    },
    "usajobs_api": {
        "name": "USAJOBS Developer Portal",
        "enabled": True,
        "base_url": "https://developer.usajobs.gov",
        "jobs_url": "https://developer.usajobs.gov",
        "description": "The official endpoint to request a client API token to query and extract active job listings in mass JSON format",
    },
    "canada_gc": {
        "name": "Government of Canada Jobs",
        "enabled": True,
        "base_url": "https://www.canada.ca",
        "jobs_url": "https://www.canada.ca/en/services/jobs/opportunities/government.html",
        "description": "The central GC Jobs network covering the Public Service Commission, transit, and RCMP emergency dispatch pipelines",
    },
    "findajob_uk": {
        "name": "Find a Job (UK)",
        "enabled": True,
        "base_url": "https://findajob.dwp.gov.uk",
        "jobs_url": "https://findajob.dwp.gov.uk/",
        "description": "The national civil service board aggregating regional emergency logistics and dispatch frameworks",
    },
    "apsjobs_au": {
        "name": "APS Jobs (Australia)",
        "enabled": True,
        "base_url": "https://www.apsjobs.gov.au",
        "jobs_url": "https://www.apsjobs.gov.au/",
        "description": "Australian Public Service clearinghouse for territorial border force and emergency management networks",
    },
    "ncs_india": {
        "name": "National Career Service (India)",
        "enabled": True,
        "base_url": "https://www.ncs.gov.in",
        "jobs_url": "https://www.ncs.gov.in/",
        "description": "National Career Service portal by the Ministry of Labour and Employment, aggregating central, state, and public sector undertaking openings",
    },
    "governmentjobs": {
        "name": "GovernmentJobs Portal",
        "enabled": True,
        "base_url": "https://www.governmentjobs.com",
        "jobs_url": "https://www.governmentjobs.com/",
        "description": "The vendor hosting direct enterprise hiring software for thousands of US municipal, county, and state police/fire departments",
    },
    "naspe": {
        "name": "NASPE",
        "enabled": True,
        "base_url": "https://www.naspe.net",
        "jobs_url": "https://www.naspe.net/",
        "description": "Provides a directory architecture mapping directly to the official, dedicated state employee hiring portals for all 50 states",
    },
    "faa": {
        "name": "Federal Aviation Administration (FAA)",
        "enabled": True,
        "base_url": "https://www.faa.gov",
        "jobs_url": "https://www.faa.gov/jobs",
        "description": "Direct hiring information page for regional and federal aviation safety inspectors specializing in dispatch oversight",
    },
    "eurocontrol": {
        "name": "EUROCONTROL Careers",
        "enabled": True,
        "base_url": "https://jobs.eurocontrol.int",
        "jobs_url": "https://jobs.eurocontrol.int/",
        "description": "Centralized control body managing European airspace; standard platform for mass Network Management and Flight Planning Trainee roles",
    },
    "caa_uk": {
        "name": "UK Civil Aviation Authority",
        "enabled": True,
        "base_url": "https://careers.caa.co.uk",
        "jobs_url": "https://careers.caa.co.uk/",
        "description": "Official regulatory talent network for safety management and airspace coordination",
    },
    "dgca_india": {
        "name": "DGCA India",
        "enabled": True,
        "base_url": "https://www.dgca.gov.in",
        "jobs_url": "https://www.dgca.gov.in/",
        "description": "Official vacancies panel for flight operation oversight and regulatory dispatch inspection",
    },
    "iag": {
        "name": "International Airlines Group (IAG)",
        "enabled": True,
        "base_url": "https://careers.iagportal.com",
        "jobs_url": "https://careers.iagportal.com/",
        "description": "Consolidated control network operations engine for British Airways, Aer Lingus, Iberia, and Vueling",
    },
    "lufthansa_group": {
        "name": "Lufthansa Group Careers",
        "enabled": True,
        "base_url": "https://career.be-lufthansa.com",
        "jobs_url": "https://career.be-lufthansa.com/",
        "description": "Mass operational and flight dispatch clearinghouse for Lufthansa, Swiss, Austrian, and Brussels Airlines",
    },
    "american_airlines": {
        "name": "American Airlines Careers",
        "enabled": True,
        "base_url": "https://jobs.aa.com",
        "jobs_url": "https://jobs.aa.com/",
        "description": "Aggregates direct mainline dispatch opportunities along with regional lines like Envoy and Piedmont",
    },
    "qatar": {
        "name": "Qatar Airways",
        "enabled": True,
        "base_url": "https://careers.qatarairways.com",
        "jobs_url": "https://careers.qatarairways.com/global/SearchJobs?7330=57893&listFilterMode=1",
        "description": "Qatar Airways careers",
    },
    "dnatabrasil": {
        "name": "dnata Brasil",
        "enabled": True,
        "base_url": "https://dnatabrasil.gupy.io",
        "jobs_url": "https://dnatabrasil.gupy.io/",
        "description": "dnata Brasil careers (Gupy)",
    },
    "emploitic": {
        "name": "Emploitic",
        "enabled": True,
        "base_url": "https://emploitic.com",
        "jobs_url": "https://emploitic.com/offres-d-emploi",
        "description": "Emploitic job portal (Algeria)",
    },
    "swissport": {
        "name": "Swissport",
        "enabled": True,
        "base_url": "https://careers.swissport.com",
        "jobs_url": "https://careers.swissport.com/jobs?country=United%20States",
        "description": "Swissport careers (iCIMS)",
    },
    "menzies": {
        "name": "Menzies Aviation",
        "category": "service_provider",
        "base_url": "https://careers.jmenzies.com",
        "jobs_url": "https://careers.jmenzies.com/aviation/vacancy/find/results/",
        "description": "Menzies Aviation careers (Oleeo)",
        "class": "MenziesScraper",
        "module": "scraper_manager.scrapers.menzies_scraper",
    },
    "menzies_ultipro": {
        "name": "Menzies Aviation (UltiPro)",
        "category": "service_provider",
        "base_url": "https://recruiting2.ultipro.com",
        "jobs_url": "https://recruiting2.ultipro.com/MEN1002MENZI/JobBoard/c62dfe4d-64ad-4642-8cd0-17a30715a697/?q=&o=postedDateDesc",
        "description": "Menzies Aviation UltiPro Job Board",
    },
    "united": {
        "name": "United Airlines",
        "enabled": True,
        "base_url": "https://careers.united.com",
        "jobs_url": "https://careers.united.com/us/en/operations-search-results-page",
        "description": "United Airlines Careers",
    },
    "lynn": {
        "name": "Lynn",
        "enabled": True,
        "base_url": "https://lynn.wd5.myworkdayjobs.com/Careers",
        "jobs_url": "https://lynn.wd5.myworkdayjobs.com/Careers",
        "description": "Lynn Careers (Workday)",
    },
    "starlinkaviation": {
        "name": "Starlink Aviation",
        "enabled": True,
        "base_url": "https://starlinkaviation.com/careers/job-openings/",
        "jobs_url": "https://starlinkaviation.com/careers/job-openings/",
        "description": "Starlink Aviation Careers",
    },
    "sunairjets": {
        "name": "Sun Air Jets",
        "enabled": True,
        "base_url": "https://www.sunairjets.com/careers/",
        "jobs_url": "https://www.sunairjets.com/careers/",
        "description": "Sun Air Jets Careers",
    },
    "moncton_adp": {
        "name": "Moncton Aviation (ADP)",
        "enabled": True,
        "base_url": "https://workforcenow.adp.com",
        "jobs_url": "https://workforcenow.adp.com/mascsr/default/mdf/recruitment/recruitment.html?cid=06351502-0666-4c6f-9a0b-165c5faeab35&ccId=9200784035909_2&lang=en_CA",
        "description": "Moncton Aviation ADP Job Board",
    },
    "hyperion": {
        "name": "Hyperion Aviation",
        "enabled": True,
        "base_url": "https://hyperion.aero/job-openings/",
        "jobs_url": "https://hyperion.aero/job-openings/",
        "description": "Hyperion Aviation Careers",
    },
    "magma": {
        "name": "Magma Aviation",
        "enabled": True,
        "base_url": "https://magma.aero/careers/",
        "jobs_url": "https://magma.aero/careers/",
        "description": "Magma Aviation Careers",
    },
    "maersk": {
        "name": "Maersk Air Freight",
        "enabled": True,
        "base_url": "https://www.maersk.com/careers/",
        "jobs_url": "https://www.maersk.com/careers/vacancies?continent=&category=Air+Freight&country=&searchText=&limit=24",
        "description": "Maersk Air Freight Jobs",
    },
    "hevenaerotech": {
        "name": "Heven Aerotech",
        "enabled": True,
        "base_url": "https://job-boards.greenhouse.io/hevenaerotech",
        "jobs_url": "https://boards-api.greenhouse.io/v1/boards/hevenaerotech/jobs",
        "description": "Heven Aerotech Jobs (Greenhouse)",
    },
    "pngair": {
        "name": "PNG Air",
        "enabled": True,
        "base_url": "https://www.pngworkforce.com/jobs/view-company/2787/png-air",
        "jobs_url": "https://www.pngworkforce.com/jobs/view-company/2787/png-air",
        "description": "PNG Air Careers",
    },
    "flyalliance": {
        "name": "Fly Alliance",
        "enabled": True,
        "base_url": "https://flyalliance.com/careers/",
        "jobs_url": "https://flyalliance.com/careers/",
        "description": "Fly Alliance Careers",
    },
    "flyscoot": {
        "name": "Scoot",
        "enabled": True,
        "base_url": "https://careers.flyscoot.com/jobs-board?department=flight%20operations",
        "jobs_url": "https://careers.flyscoot.com/jobs-board?department=flight%20operations",
        "description": "Scoot Jobs",
    },
    "flytropic": {
        "name": "Tropic Ocean Airways",
        "enabled": True,
        "base_url": "https://flytropic.com/careers-full-description-and-applications/",
        "jobs_url": "https://flytropic.com/careers-full-description-and-applications/",
        "description": "Tropic Ocean Airways Jobs",
    },
    "flyflair": {
        "name": "Flair Airlines",
        "enabled": True,
        "base_url": "https://career.flyflair.com/jobs",
        "jobs_url": "https://career.flyflair.com/jobs?search=&trk=public_post_reshare-text",
        "description": "Flair Airlines Careers",
    },
    "jetex": {
        "name": "Jetex",
        "enabled": True,
        "base_url": "https://careers.jetex.com/",
        "jobs_url": "https://careers.jetex.com/",
        "description": "Jetex Careers",
    },
    "helinet": {
        "name": "Helinet",
        "enabled": True,
        "base_url": "https://helinet.com/careers/",
        "jobs_url": "https://helinet.com/careers/#see-careers",
        "description": "Helinet Careers",
    },
    "nationalairlines": {
        "name": "National Airlines",
        "enabled": True,
        "base_url": "https://www.nationalairlines.com/careers/",
        "jobs_url": "https://www.nationalairlines.com/careers/",
        "description": "National Airlines Careers",
    },
    "flyafricaworld": {
        "name": "Africa World Airlines",
        "enabled": True,
        "base_url": "https://recruitment.apps-flyafricaworld.com/",
        "jobs_url": "https://recruitment.apps-flyafricaworld.com/",
        "description": "Africa World Airlines Careers",
    },
    "allegiantair": {
        "name": "Allegiant Air",
        "enabled": True,
        "base_url": "https://www.allegiantair.jobs/see-all-jobs/",
        "jobs_url": "https://www.allegiantair.jobs/see-all-jobs/",
        "description": "Allegiant Air Careers",
    },
    "dcaviation": {
        "name": "DC Aviation",
        "enabled": True,
        "base_url": "https://dcaviationgmbh.recruitee.com/l/en/",
        "jobs_url": "https://dcaviationgmbh.recruitee.com/l/en/",
        "description": "DC Aviation Careers",
    },
    "airasia": {
        "name": "AirAsia",
        "enabled": True,
        "base_url": "https://mycareer.airasia.com/gb/en/search-results",
        "jobs_url": "https://mycareer.airasia.com/gb/en/search-results",
        "description": "AirAsia Careers",
    },
    "bbnairlines": {
        "name": "BBN Airlines",
        "enabled": True,
        "base_url": "https://bbnairlines.aero/careers/",
        "jobs_url": "https://bbnairlines.aero/careers/",
        "description": "BBN Airlines Careers",
    },
    "maximusair": {
        "name": "Maximus Air",
        "enabled": True,
        "base_url": "https://www.maximus-air.com/careers",
        "jobs_url": "https://www.maximus-air.com/careers",
        "description": "Maximus Air Careers",
    },
    "volotea": {
        "name": "Volotea",
        "enabled": True,
        "base_url": "https://jobs.volotea.com/hq/",
        "jobs_url": "https://jobs.volotea.com/hq/",
        "description": "Volotea Careers",
    },
    "philippineairlines": {
        "name": "Philippine Airlines",
        "enabled": True,
        "base_url": "https://careers.philippineairlines.com/go/Ground-And-Admin-Employees/734744/",
        "jobs_url": "https://careers.philippineairlines.com/go/Ground-And-Admin-Employees/734744/",
        "description": "Philippine Airlines Careers",
    },
    "adp_fbb94cb3": {
        "name": "Aviation Charter Broker (ADP)",
        "enabled": True,
        "base_url": "https://workforcenow.adp.com",
        "jobs_url": "https://workforcenow.adp.com/mascsr/default/mdf/recruitment/recruitment.html?cid=fbb94cb3-cbb5-4d4b-8225-770829b92d51&ccId=19000101_000001&lang=en_US",
        "description": "ADP Company fbb94cb3 Careers",
    },
    "flyporter": {
        "name": "Porter Airlines",
        "enabled": True,
        "base_url": "https://careers.flyporter.com/jobs",
        "jobs_url": "https://careers.flyporter.com/jobs",
        "description": "Porter Airlines Careers",
    },
    "alexjets": {
        "name": "Alex Jets",
        "enabled": True,
        "base_url": "https://alexjets.com/modern/career",
        "jobs_url": "https://alexjets.com/modern/career",
        "description": "Alex Jets Careers",
    },
    "templerecruitment": {
        "name": "Temple Recruitment",
        "enabled": True,
        "base_url": "https://templerecruitment.ie/jobs/",
        "jobs_url": "https://templerecruitment.ie/jobs/",
        "description": "Temple Recruitment Careers",
    },
    "astonjet": {
        "name": "Astonjet",
        "enabled": True,
        "base_url": "https://astonjet.com/careers/",
        "jobs_url": "https://astonjet.recruitee.com/",
        "description": "Astonjet Careers",
    },
    "airx": {
        "name": "AirX",
        "enabled": True,
        "base_url": "https://www.airx.aero/careers/",
        "jobs_url": "https://www.airx.aero/careers/",
        "description": "AirX Careers",
    },
    "helvetic": {
        "name": "Helvetic Airways",
        "enabled": True,
        "base_url": "https://career.helvetic.com/vacancies",
        "jobs_url": "https://career.helvetic.com/vacancies",
        "description": "Helvetic Airways Careers",
    },
    "hadid": {
        "name": "Hadid Aviation",
        "enabled": True,
        "base_url": "https://hadid.aero/job-vacancies/list",
        "jobs_url": "https://hadid.aero/job-vacancies/list",
        "description": "Hadid Aviation Careers",
    },
    "singaporeair": {
        "name": "Singapore Airlines",
        "enabled": True,
        "base_url": "https://careers.singaporeair.com/sia/go/Ground-Professionals/689144/",
        "jobs_url": "https://careers.singaporeair.com/sia/go/Ground-Professionals/689144/",
        "description": "Singapore Airlines Careers",
    },
    "vistaglobal": {
        "name": "Vista Global",
        "enabled": True,
        "base_url": "https://hub-vistaglobal.icims.com/jobs/search?ss=1&in_iframe=1",
        "jobs_url": "https://hub-vistaglobal.icims.com/jobs/search?ss=1&searchCategory=109470&searchCategory=17882&searchCategory=17912&searchCategory=17886&searchCategory=8748&searchCategory=17898&searchCategory=54473&searchCategory=57874&mobile=false&width=1296&height=500&bga=true&needsRedirect=false&jan1offset=330&jun1offset=330",
        "description": "Vista Global Careers",
    },
    "transavia_fr": {
        "name": "Transavia France",
        "enabled": True,
        "base_url": "https://recrutement.transavia.com/fr/annonces",
        "jobs_url": "https://recrutement.transavia.com/fr/annonces",
        "description": "Transavia France Careers",
    },
    "latestpilotjobs": {
        "name": "Latest Pilot Jobs",
        "enabled": True,
        "base_url": "https://www.latestpilotjobs.com",
        "jobs_url": "https://www.latestpilotjobs.com/jobs/category/id/ground_crew_jobs.html",
        "description": "LatestPilotJobs Ground Crew listings",
    },
    "aviationcareers": {
        "name": "Aviation Careers CA",
        "enabled": True,
        "base_url": "https://aviationcareers.ca",
        "jobs_url": "https://aviationcareers.ca/careersection/2/jobsearch.ftl?lang=en",
        "description": "Aviation Careers Canada (Taleo)",
    },
    "flyinggroup": {
        "name": "FLYINGGROUP",
        "enabled": True,
        "base_url": "https://www.flyinggroup.aero",
        "jobs_url": "https://www.flyinggroup.aero/jobs/",
        "description": "FLYINGGROUP Careers",
    },
    "luxaviation": {
        "name": "Luxaviation",
        "enabled": True,
        "base_url": "https://luxaviation.bamboohr.com",
        "jobs_url": "https://luxaviation.bamboohr.com/careers",
        "description": "Luxaviation Careers (BambooHR)",
    },
    "gojet": {
        "name": "GoJet Airlines",
        "category": "airline",
        "base_url": "https://workforcenow.adp.com",
        "jobs_url": "https://workforcenow.adp.com/mascsr/default/mdf/recruitment/recruitment.html?cid=a7828c0b-d30d-40a2-a3ee-61c80628985c&ccId=19000101_000001&lang=en_US",
        "description": "GoJet Airlines ADP Job Board",
    },
    "aeroguard": {
        "name": "AeroGuard Flight Training Center",
        "category": "service_provider",
        "base_url": "https://recruitingbypaycor.com",
        "jobs_url": "https://recruitingbypaycor.com/career/CareerHome.action?clientId=8a7883d088e0b78e0189415b377122db",
        "description": "AeroGuard Flight Training Center Paycor Job Board",
    },
    "flyexclusive": {
        "name": "FlyExclusive",
        "category": "operator",
        "base_url": "https://www.paycomonline.net",
        "jobs_url": "https://www.paycomonline.net/v4/ats/web.php/jobs?clientkey=91989CEA70627F35DBDEA57AC03E0A2B",
        "description": "FlyExclusive Paycom Careers",
    },
    "air_canada": {
        "name": "Air Canada",
        "category": "airline",
        "base_url": "https://careers.aircanada.com",
        "jobs_url": "https://careers.aircanada.com/ca/en",
        "description": "Air Canada Phenom People Job Board",
    },
    "challenge_group": {
        "name": "Challenge Group",
        "category": "airline",
        "base_url": "https://career.challenge-group.com",
        "jobs_url": "https://career.challenge-group.com/search/?q=&locationsearch=&searchResultView=LIST&pageNumber=0&facetFilters=%7B%7D&sortBy=&markerViewed=&carouselIndex=",
        "description": "Challenge Group SuccessFactors Job Board",
    },
    "glock": {
        "name": "Glock",
        "category": "operator",
        "base_url": "https://jobs.glock.at",
        "jobs_url": "https://jobs.glock.at/programme/onlinebewerbung_uebersicht.php",
        "description": "Glock Aviation & Corporate Jobs",
    },
    "amazon_air": {
        "name": "Amazon Air",
        "category": "airline",
        "base_url": "https://amazon.jobs",
        "jobs_url": "https://amazon.jobs/content/en/teams/transportation-shipping-logistics/air#jobs-search",
        "description": "Amazon Air Global Careers",
    },
    "united": {
        "name": "United Airlines",
        "enabled": True,
        "base_url": "https://careers.united.com",
        "jobs_url": "https://careers.united.com/us/en/search-results",
        "description": "United Airlines careers (Workday/Phenom)",
    },
    "ups": {
        "name": "UPS Airlines",
        "enabled": True,
        "base_url": "https://www.jobs-ups.com",
        "jobs_url": "https://www.jobs-ups.com/search-jobs",
        "description": "UPS Airlines careers (Taleo/Phenom)",
    },
    "jetblue": {
        "name": "JetBlue Airways",
        "enabled": True,
        "base_url": "https://careers.jetblue.com",
        "jobs_url": "https://careers.jetblue.com/search/?createNewAlert=false&q=&locationsearch=",
        "description": "JetBlue Airways careers (SuccessFactors)",
    },
    "absjets": {
        "name": "ABS Jets",
        "enabled": True,
        "base_url": "https://www.absjets.com",
        "jobs_url": "https://www.absjets.com/careers-109",
        "description": "ABS Jets careers page",
    },
    "aegean": {
        "name": "Aegean Airlines",
        "enabled": True,
        "base_url": "https://jobs.aegeanair.com",
        "jobs_url": "https://jobs.aegeanair.com/search/?createNewAlert=false&q=",
        "description": "Aegean Airlines careers",
        "class": "AegeanScraper",
        "module": "scraper_manager.scrapers.aegean_scraper",
    },
    "aena": {
        "name": "Aena",
        "enabled": True,
        "base_url": "https://empleo.aena.es",
        "jobs_url": "https://empleo.aena.es/empleo/SessSrv?accion=seleccionar&leng=EN&SEDE=0",
        "description": "Aena careers",
    },
    "airfrance": {
        "name": "Air France",
        "enabled": True,
        "base_url": "https://recrutement.airfrance.com",
        "jobs_url": "https://recrutement.airfrance.com/homepage.aspx?LCID=2057",
        "description": "Air France recruitment",
    },
    "airfrancehop": {
        "name": "Air France HOP",
        "enabled": True,
        "base_url": "https://www.hop.fr",
        "jobs_url": "https://www.hop.fr/en/carriere/",
        "description": "Air France HOP careers",
    },
    "airmalta": {
        "name": "Air Malta (KM Malta Airlines)",
        "enabled": True,
        "base_url": "https://kmmaltairlines.com",
        "jobs_url": "https://kmmaltairlines.com/en/careers",
        "description": "KM Malta Airlines careers",
    },
    "airserbia": {
        "name": "Air Serbia",
        "enabled": True,
        "base_url": "https://career.airserbia.com",
        "jobs_url": "https://career.airserbia.com/",
        "description": "Air Serbia careers",
    },
    "alsieexpress": {
        "name": "Alsie Express",
        "enabled": True,
        "base_url": "https://www.alsie.com",
        "jobs_url": "https://candidate.hr-manager.net/vacancies/list.aspx?customer=alsie_tr&nocookie=true&uiculture=en",
        "description": "Alsie Express (HR Manager)",
    },
    "amapolaflyg": {
        "name": "Amapola Flyg",
        "enabled": True,
        "base_url": "https://amapola.nu",
        "jobs_url": "https://amapola.nu/about-us/careers/",
        "description": "Amapola Flyg careers",
    },
    "aslairlinesbelgium": {
        "name": "ASL Airlines Belgium",
        "enabled": True,
        "base_url": "https://aslairlines.be",
        "jobs_url": "https://aslairlines.be/asljobs/",
        "description": "ASL Airlines Belgium careers",
    },
    "austrianairlines": {
        "name": "Austrian Airlines",
        "enabled": True,
        "base_url": "https://careers.austrian.com",
        "jobs_url": "https://careers.austrian.com/en/",
        "description": "Austrian Airlines careers",
    },
    "blueislands": {
        "name": "Blue Islands",
        "enabled": False,
        "base_url": "https://www.airlinestaffrates.com",
        "jobs_url": "https://www.airlinestaffrates.com/blue-islands-is-hiring-cabin-crew-channel-islands/",
        "description": "Blue Islands proxy careers",
    },
    "braathens": {
        "name": "Braathens Regional Airlines",
        "enabled": True,
        "base_url": "https://www.braathens.com",
        "jobs_url": "https://www.braathens.com/career/",
        "description": "Braathens Regional Airlines",
    },
    "bristow": {
        "name": "Bristow Helicopters",
        "enabled": True,
        "base_url": "https://www.linkedin.com/company/bristow-group-inc/jobs",
        "jobs_url": "https://www.linkedin.com/company/bristow-group-inc/jobs",
        "description": "Bristow Helicopters LinkedIn proxy",
    },
    "brusselsairlines": {
        "name": "Brussels Airlines",
        "enabled": True,
        "base_url": "https://www.lufthansagroup.careers/en/brussels-airlines/",
        "jobs_url": "https://www.lufthansagroup.careers/en/brussels-airlines/",
        "description": "Brussels Airlines careers",
    },
    "buraqair": {
        "name": "Buraq Air",
        "enabled": True,
        "base_url": "https://buraq.aero",
        "jobs_url": "https://buraq.aero/careers/",
        "description": "Buraq Air careers",
    },
    "buzz": {
        "name": "Buzz (Ryanair Group)",
        "enabled": True,
        "base_url": "https://careers.ryanair.com",
        "jobs_url": "https://careers.ryanair.com/search/#job/search",
        "description": "Buzz / Ryanair Group careers",
    },
    "cabotaviation": {
        "name": "Cabot Aviation",
        "enabled": False,
        "base_url": "https://cabotaviation.com",
        "jobs_url": "https://cabotaviation.com/",
        "description": "Cabot Aviation (disabled for official-employer-only runs)",
    },
    "capitalairlines": {
        "name": "Beijing Capital Airlines",
        "enabled": True,
        "base_url": "https://jdair.net",
        "jobs_url": "https://jdair.net",
        "description": "Beijing Capital Airlines fallback",
    },
    "southwest": {
        "name": "Southwest Airlines",
        "enabled": True,
        "base_url": "https://careers.southwestair.com",
        "jobs_url": "https://careers.southwestair.com/us/en/c/corporate-careers-jobs",
        "description": "Southwest Airlines careers (Phenom People)",
        "class": "SouthwestScraper",
        "module": "scraper_manager.scrapers.southwest_scraper",
    },
    "carpatair": {
        "name": "Carpatair",
        "enabled": True,
        "base_url": "https://www.carpatair.com",
        "jobs_url": "https://www.carpatair.com/careers/",
        "description": "Carpatair careers",
    },
    "dat": {
        "name": "DAT (Danish Air Transport)",
        "enabled": True,
        "base_url": "https://dat.dk",
        "jobs_url": "https://dat.dk/corporate/careers",
        "description": "DAT careers",
    },
    "easternairways": {
        "name": "Eastern Airways",
        "enabled": True,
        "base_url": "https://www.easternairways.com",
        "jobs_url": "https://www.easternairways.com/careers",
        "description": "Eastern Airways careers fallback",
    },
    "wmd": {
        "class": "WmdScraper",
        "module": "scraper_manager.scrapers.wmd_scraper",
        "enabled": True,
    },
    "royaljet": {
        "name": "Royal Jet",
        "enabled": True,
        "base_url": "https://careerroyaljet.talentera.com",
        "jobs_url": "https://careerroyaljet.talentera.com/en/job-search-results/",
        "description": "Royal Jet careers portal (Talentera)",
        "class": "RoyalJetScraper",
        "module": "scraper_manager.scrapers.royaljet_scraper",
    },
    "jetfly": {
        "name": "Jetfly",
        "enabled": True,
        "base_url": "https://jetfly.com",
        "jobs_url": "https://jetfly.com/careers",
        "description": "Jetfly careers page",
        "class": "JetflyScraper",
        "module": "scraper_manager.scrapers.jetfly_scraper",
    },
    "easyjet": {
        "name": "easyJet",
        "enabled": True,
        "base_url": "https://careers.easyjet.com",
        "jobs_url": "https://easyjet.taleo.net/careersection/2/jobsearch.ftl?f=JOB_FIELD(30305011999,34305011999,34405011999,9570751484,10670751484,28205011999,36405011999,8670751484,16170701859,34205011999,8770751484,34705011999,34105011999,30205011999,32805011999,34905011999,16270701859,8270751484,10370751484,10070751484,8970751484,24105011999,24205011999,24405011999,26105011999,24305011999,32705011999,10270751484,35005011999,9970751484,10570751484,36305011999,9370751484,32605011999,34505011999,9470751484,32505011999,8370751484,9070751484,9870751484,9670751484,34805011999,32105011999,8470751484,18270701859)&ignoreSavedQuery&ej_consent_marketing=false&ej_consent_perf=false#",
        "description": "easyJet careers",
        "class": "EasyJetScraper",
        "module": "scraper_manager.scrapers.easyjet_scraper",
    },
    "edelweiss": {
        "name": "Edelweiss Air",
        "enabled": True,
        "base_url": "https://www.lufthansagroup.careers/en/edelweiss",
        "jobs_url": "https://www.lufthansagroup.careers/en/edelweiss",
        "description": "Edelweiss Air careers",
    },
    "egyptair": {
        "name": "Egyptair",
        "enabled": True,
        "base_url": "https://hr.egyptair.com",
        "jobs_url": "https://hr.egyptair.com",
        "description": "Egyptair careers fallback",
    },
    "elal": {
        "name": "El Al",
        "enabled": True,
        "base_url": "https://www.elal.com/eng/about/careers",
        "jobs_url": "https://www.elal.com/eng/about/careers",
        "description": "El Al careers fallback",
    },
    "ethiopian": {
        "name": "Ethiopian Airlines",
        "enabled": True,
        "base_url": "https://corporate.ethiopianairlines.com/AboutEthiopian/careers/vacancies",
        "jobs_url": "https://corporate.ethiopianairlines.com/AboutEthiopian/careers/vacancies",
        "description": "Ethiopian Airlines careers",
    },
    "eurowings": {
        "name": "Eurowings",
        "enabled": True,
        "base_url": "https://www.lufthansagroup.careers/en/eurowings",
        "jobs_url": "https://www.lufthansagroup.careers/en/eurowings",
        "description": "Eurowings careers",
    },
    "finnair": {
        "name": "Finnair",
        "enabled": True,
        "base_url": "https://company.finnair.com",
        "jobs_url": "https://company.finnair.com/en/careers",
        "description": "Finnair careers",
    },
    "flybe": {
        "name": "Flybe",
        "enabled": False,
        "base_url": "https://flybe.com",
        "jobs_url": "https://flybe.com",
        "description": "Flybe careers (Ceased operations, returning 0)",
    },
    "hahnair": {
        "name": "Hahn Air Lines",
        "enabled": True,
        "base_url": "https://www.hahnair.com",
        "jobs_url": "https://www.hahnair.com/en/career/career",
        "description": "Hahn Air Lines careers",
    },
    "iberia": {
        "name": "Iberia",
        "enabled": True,
        "base_url": "https://www.iberia.com",
        "jobs_url": "https://trabajaconnosotros.iberia.es/search/?createNewAlert=false&q=",
        "description": "Iberia careers",
    },
    "spirit": {
        "name": "Spirit Airlines",
        "enabled": True,
        "base_url": "https://careers.spirit.com",
        "jobs_url": "https://careers.spirit.com/careers-home/jobs",
        "description": "Spirit Airlines careers (API)",
        "class": "SpiritScraper",
        "module": "scraper_manager.scrapers.spirit_scraper",
    },
    "aar_corp": {
        "name": "AAR Corp",
        "enabled": True,
        "base_url": "https://aarcorp.taleo.net",
        "jobs_url": "https://aarcorp.taleo.net/careersection/2/jobsearch.ftl?lang=en",
        "description": "AAR Corp careers (Taleo)",
    },
    "fedex": {
        "name": "FedEx",
        "category": "service_provider",
        "base_url": "https://careers.fedex.com",
        "jobs_url": "https://careers.fedex.com/jobs",
        "description": "FedEx careers (Phenom People)",
        "class": "FedexScraper",
        "module": "scraper_manager.scrapers.fedex_scraper",
    },
    "fedex_euro_dispatch": {
        "name": "FedEx European Operations",
        "category": "service_provider",
        "base_url": "https://careers.fedex.com",
        "jobs_url": "https://careers.fedex.com/international/european-operations/jobs?keyword=dispatch",
        "description": "FedEx European Operations Dispatch",
    },
    "kalitta_air": {
        "name": "Kalitta Air",
        "enabled": True,
        "base_url": "https://workforcenow.adp.com",
        "jobs_url": "https://workforcenow.adp.com/mascsr/default/mdf/recruitment/recruitment.html?ccId=19000101_000001&cid=17b87f3e-11d6-434a-b3df-0d83d72f832b&lang=en_US&type=MP",
        "description": "Kalitta Air careers (ADP Workforce Now)",
    },
    "envoy_air": {
        "name": "Envoy Air",
        "enabled": True,
        "base_url": "https://careers-envoyair.icims.com",
        "jobs_url": "https://careers-envoyair.icims.com/jobs/search?in_iframe=1",
        "description": "Envoy Air careers (iCIMS)",
    },
    "atlas_air": {
        "name": "Atlas Air Worldwide",
        "enabled": True,
        "base_url": "https://www.atlasairworldwide.com",
        "jobs_url": "https://boards-api.greenhouse.io/v1/boards/atlasair/jobs",
        "description": "Atlas Air Worldwide careers (Greenhouse API)",
    },
    "atlantic_aviation": {
        "name": "Atlantic Aviation",
        "enabled": True,
        "base_url": "https://atlanticaviationcareers.com",
        "jobs_url": "https://atlanticaviationcareers.com/#jobs",
        "description": "Atlantic Aviation careers (Talentcare/WordPress)",
    },
    "netjets": {
        "name": "NetJets",
        "enabled": True,
        "base_url": "https://netjets.jobs.hr.cloud.sap",
        "jobs_url": "https://netjets.jobs.hr.cloud.sap/us/search/",
        "description": "NetJets careers (SuccessFactors)",
    },
    "wheels_up": {
        "name": "Wheels Up",
        "enabled": True,
        "base_url": "https://careers-wheelsup.icims.com",
        "jobs_url": "https://careers-wheelsup.icims.com/jobs/search?in_iframe=1",
        "description": "Wheels Up careers (iCIMS)",
    },
    "flexjet": {
        "name": "Flexjet",
        "enabled": True,
        "base_url": "https://careers.flexjet.com",
        "jobs_url": "https://careers.flexjet.com/us/en/eu-all-categories",
        "description": "Flexjet careers (Phenom People)",
    },
    "amerijet": {
        "name": "Amerijet",
        "enabled": True,
        "base_url": "https://workforcenow.adp.com",
        "jobs_url": "https://workforcenow.adp.com/mascsr/default/mdf/recruitment/recruitment.html?cid=b84c1100-8ca6-49d3-8a35-f06ad8084d26&ccId=19000101_000001&lang=en_US",
        "description": "Amerijet careers (ADP Workforce Now)",
    },
    "cargojet": {
        "name": "Cargojet",
        "enabled": True,
        "base_url": "https://recruiting.ultipro.ca",
        "jobs_url": "https://recruiting.ultipro.ca/CAR5000CJT/JobBoard/3bdb0a52-04dc-4fa4-91cd-d80afd88843d/",
        "description": "Cargojet careers (UltiPro)",
    },
    "canadian_north": {
        "name": "Canadian North",
        "enabled": True,
        "base_url": "https://recruiting.ultipro.ca",
        "jobs_url": "https://recruiting.ultipro.ca/BRA50007F/JobBoard/2ea5e84a-bfc4-4167-88ba-20d03547d410/",
        "description": "Canadian North careers (UltiPro)",
        "class": "CanadianNorthScraper",
        "module": "scraper_manager.scrapers.canadian_north_scraper",
    },
    "rtx": {
        "name": "RTX",
        "enabled": True,
        "base_url": "https://careers.rtx.com",
        "jobs_url": "https://careers.rtx.com/global/en/search-results",
        "description": "RTX / Collins / Pratt & Whitney careers (Phenom People)",
        "class": "RtxScraper",
        "module": "scraper_manager.scrapers.rtx_scraper",
    },
    "mesa": {
        "name": "Mesa Airlines",
        "enabled": True,
        "base_url": "https://myjobs.adp.com",
        "jobs_url": "https://myjobs.adp.com/mesaexternal/cx/job-listing",
        "description": "Mesa Airlines careers (ADP)",
        "class": "MesaAirlinesScraper",
        "module": "scraper_manager.scrapers.mesa_airlines_scraper",
    },
    "delta": {
        "name": "Delta Airlines",
        "enabled": True,
        "base_url": "https://delta.avature.net",
        "jobs_url": "https://delta.avature.net/en_US/careers/SearchJobs/?listFilterMode=1#/",
        "description": "Delta Airlines careers (Avature)",
        "class": "DeltaScraper",
        "module": "scraper_manager.scrapers.delta_scraper",
    },
    "iberiaexpress": {
        "name": "Iberia Express",
        "enabled": True,
        "base_url": "https://iberiaexpress.com",
        "jobs_url": "https://trabajaconnosotros.iberia.es/search/?createNewAlert=false&q=Express",
        "description": "Iberia Express careers (Custom Portal)",
    },
    "icelandair": {
        "name": "Icelandair",
        "enabled": True,
        "base_url": "https://www.icelandair.com/about/job-vacancies/",
        "jobs_url": "https://jobs.50skills.com/icelandair/en",
        "description": "Icelandair careers (50skills)",
    },
    "itaairways": {
        "name": "ITA Airways",
        "enabled": True,
        "base_url": "https://career.ita-airways.com/",
        "jobs_url": "https://career.ita-airways.com/search/",
        "description": "ITA Airways careers (SuccessFactors)",
    },
    "klm": {
        "name": "KLM Royal Dutch Airlines",
        "enabled": True,
        "base_url": "https://careers.klm.com/en/jobs/",
        "jobs_url": "https://careers.klm.com/en/jobs/",
        "description": "KLM careers (Fallback, WAF protected)",
    },
    "lufthansacityline": {
        "name": "Lufthansa CityLine",
        "enabled": True,
        "base_url": "https://www.lufthansagroup.careers/en/lufthansa-cityline",
        "jobs_url": "https://www.lufthansagroup.careers/en/lufthansa-cityline",
        "description": "Lufthansa CityLine careers",
    },
    "norwegian": {
        "name": "Norwegian Air Shuttle",
        "enabled": True,
        "base_url": "https://careers.norwegian.com",
        "jobs_url": "https://careers.norwegian.com/search/",
        "description": "Norwegian Air Shuttle careers (SuccessFactors)",
    },
    "olympicair": {
        "name": "Olympic Air",
        "enabled": True,
        "base_url": "https://jobs.aegeanair.com",
        "jobs_url": "https://jobs.aegeanair.com/",
        "description": "Olympic Air careers (Aegean proxy)",
    },
    "ryanair": {
        "name": "Ryanair",
        "enabled": True,
        "base_url": "https://careers.ryanair.com",
        "jobs_url": "https://careers.ryanair.com/search/",
        "description": "Ryanair careers",
    },
    "sas": {
        "name": "SAS Scandinavian Airlines",
        "enabled": True,
        "base_url": "https://careers.sasgroup.net",
        "jobs_url": "https://careers.sasgroup.net/go/All-SAS-Jobs/4164001/",
        "description": "SAS Scandinavian Airlines careers",
    },
    "smartwings": {
        "name": "SmartWings",
        "enabled": True,
        "base_url": "https://www.smartwings.com/en/career/",
        "jobs_url": "https://www.smartwings.com/en/career/",
        "description": "SmartWings careers (Fallback, WAF protected)",
    },
    "swiss": {
        "name": "Swiss International Air Lines",
        "enabled": True,
        "base_url": "https://apply.lufthansagroup.careers/index.php?ac=search_result&search_criterion_activity_level%5B%5D=107",
        "jobs_url": "https://apply.lufthansagroup.careers/index.php?ac=search_result&search_criterion_activity_level%5B%5D=107",
        "description": "Swiss International Air Lines careers (Lufthansa Proxy)",
    },
    "tap": {
        "name": "TAP Air Portugal",
        "enabled": True,
        "base_url": "https://careers.flytap.com/",
        "jobs_url": "https://careers.flytap.com/",
        "description": "TAP Air Portugal careers",
    },
    "tuiairways": {
        "name": "TUI Airways",
        "enabled": True,
        "base_url": "https://careers.tuigroup.com/en",
        "jobs_url": "https://careers.tuigroup.com/en/search-jobs?acm=32141888,32173952&alrpm=ALL&ascf=[%7B%22key%22:%22custom_fields.subcategories%22,%22value%22:%22Engineering+%26+Maintenance%22%7D,%7B%22key%22:%22custom_fields.subcategories%22,%22value%22:%22Airline+Engineering%22%7D,%7B%22key%22:%22custom_fields.subcategories%22,%22value%22:%22Engineering+Apprentice%22%7D,%7B%22key%22:%22custom_fields.subcategories%22,%22value%22:%22Ground+Ops%22%7D,%7B%22key%22:%22custom_fields.subcategories%22,%22value%22:%22Aviation%22%7D]",
        "description": "TUI Airways careers",
        "class": "TuiAirwaysScraper",
        "module": "scraper_manager.scrapers.tuiairways_scraper",
    },
    "vueling": {
        "name": "Vueling",
        "enabled": True,
        "base_url": "https://careers.vueling.com/",
        "jobs_url": "https://careers.vueling.com/",
        "description": "Vueling careers",
    },
    "aerlingus": {
        "name": "Aer Lingus",
        "enabled": True,
        "base_url": "https://aerlingus.wd3.myworkdayjobs.com/en-US/AerLingus",
        "jobs_url": "https://aerlingus.wd3.myworkdayjobs.com/en-US/AerLingus",
        "description": "Aer Lingus careers (Workday)",
    },
    "airbaltic": {
        "name": "Air Baltic",
        "enabled": True,
        "base_url": "https://careers.airbaltic.com/en/jobs",
        "jobs_url": "https://careers.airbaltic.com/en/jobs",
        "description": "Air Baltic careers",
    },
    "airdolomiti": {
        "name": "Air Dolomiti",
        "enabled": True,
        "base_url": "https://airdolomiti.altamiraweb.com/",
        "jobs_url": "https://airdolomiti.altamiraweb.com/default/",
        "description": "Air Dolomiti careers",
    },
    "airnostrum": {
        "name": "Air Nostrum",
        "enabled": True,
        "base_url": "https://jobs.airnostrum.es/?locale=en_US",
        "jobs_url": "https://jobs.airnostrum.es/?locale=en_US",
        "description": "Air Nostrum careers",
    },
    "signature": {
        "name": "Signature Aviation",
        "enabled": True,
        "api_url": "https://hdbt.fa.us2.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions",
        "site_number": "CX_1",
        "base_url": "https://jobs.signatureaviation.com",
        "description": "Oracle Cloud HCM-based job board",
    },
    # NOT WORKING YET - CEIPAL iframe requires special handling
    "aviationindeed": {
        "name": "Aviation Indeed",
        "enabled": False,  # Site has loading issues - needs investigation
        "base_url": "https://www.aviationindeed.com",
        "ceipal_url": "https://www.aviationindeed.com/ceipal/",
        "description": "CEIPAL iframe-based job board",
    },
    "aap": {
        "name": "AAP Aviation",
        "enabled": False,
        "base_url": "https://jobs.aapaviation.com",
        "jobs_url": "https://jobs.aapaviation.com/jobs",
        "description": "AAP Aviation job board (disabled for official-employer-only runs)",
    },
    "indigo": {
        "name": "IndiGo Airlines",
        "enabled": True,  # Temporarily enabled for debugging and fixes
        "base_url": "https://www.goindigo.in",
        "jobs_url": "https://www.goindigo.in/careers/job-search.html?type=&location=&department=",
        "description": "IndiGo Airlines careers page (currently under development)",
    },
    "cargolux": {
        "name": "Cargolux Careers (PeopleClick)",
        "enabled": True,
        "base_url": "https://careers.peopleclick.eu.com",
        "jobs_url": "https://careers.peopleclick.eu.com/careerscp/client_cargolux/external/results/searchResult.html",
        "description": "Cargolux careers site (PeopleClick implementation)",
    },
    "airindia": {
        "name": "Air India Careers",
        "enabled": True,
        "base_url": "https://careers.airindia.com",
        "jobs_url": "https://careers.airindia.com/sfcareer/search",
        "description": "Air India careers site (SuccessFactors implementation)",
    },
    "emirates": {
        "name": "Emirates Group Careers",
        "enabled": True,
        "base_url": "https://www.emiratesgroupcareers.com",
        "jobs_url": "https://www.emiratesgroupcareers.com/search-and-apply/#all",
        "description": "Official career site for Emirates Group",
        "class": "EmiratesScraper",
        "module": "scraper_manager.scrapers.emirates_scraper",
    },
    "boeing": {
        "name": "Boeing Careers",
        "enabled": True,
        "base_url": "https://jobs.boeing.com",
        "description": "Boeing Career Site",
    },
    "airbus": {
        "name": "Airbus Careers",
        "enabled": True,
        "base_url": "https://ag.wd3.myworkdayjobs.com/Airbus",
        "api_url": "https://ag.wd3.myworkdayjobs.com/wday/cxs/ag/Airbus/jobs",
        "description": "Airbus Workday Career Site",
    },
    "aisats": {
        "name": "AISATS (Air India SATS)",
        "enabled": True,
        "base_url": "https://www.aisats.in",
        "jobs_url": "https://www.aisats.in/careers",
        "description": "Air India SATS Airport Services career page",
    },
    "jmc": {
        "name": "JMC Aviation",
        "enabled": False,
        "base_url": "https://www.jmc-aviation.com",
        "jobs_url": "https://www.jmc-aviation.com/jobs/",
        "description": "Aviation recruitment specialist (disabled for official-employer-only runs)",
    },
    "iata": {
        "name": "IATA",
        "enabled": False,
        "base_url": "https://iata.csod.com",
        "jobs_url": "https://iata.csod.com/ux/ats/careersite/1/home?c=iata",
        "description": "International Air Transport Association (disabled for official-employer-only runs)",
    },
    "avianation": {
        "name": "AviaNation",
        "enabled": False,
        "base_url": "https://www.avianation.com",
        "jobs_url": "https://www.avianation.com/",
        "description": "Aviation jobs portal (disabled for official-employer-only runs)",
    },
    "wizzair": {
        "name": "Wizz Air",
        "enabled": True,
        "base_url": "https://careers.wizzair.com",
        "jobs_url": "https://careers.wizzair.com/search/",
        "description": "Wizz Air Careers",
    },
    "cpr": {
        "name": "CPKC (Canadian Pacific)",
        "enabled": True,
        "base_url": "https://careers.cpr.ca",
        "jobs_url": "https://careers.cpr.ca/search/?q=&locationsearch=&skillsSearch=false&sortBy=date&pageNumber=0",
        "description": "Canadian Pacific Kansas City Careers",
    },
    "nbaa": {
        "name": "NBAA (National Business Aviation Association)",
        "enabled": False,
        "base_url": "https://jobs.nbaa.org",
        "jobs_url": "https://jobs.nbaa.org/jobs/",
        "description": "NBAA Jobs (disabled for official-employer-only runs)",
    },
    "starair": {
        "name": "Star Air",
        "enabled": True,
        "base_url": "https://www.starair.in",
        "jobs_url": "https://www.starair.in/careers",
        "description": "Star Air careers page",
    },
    "lufthansa": {
        "name": "Lufthansa Group",
        "enabled": True,
        "base_url": "https://apply.lufthansagroup.careers",
        "jobs_url": "https://apply.lufthansagroup.careers/index.php?ac=search_result&search_criterion_channel%5B%5D=12&language=2&pk_vid=65d4beac5e416cfb178150183991a939",
        "description": "Lufthansa Group careers portal",
        "class": "LufthansagroupScraper",
        "module": "scraper_manager.scrapers.lufthansagroup_scraper",
    },
    "ba": {
        "name": "British Airways",
        "enabled": True,
        "base_url": "https://careers.ba.com",
        "jobs_url": "https://careers.ba.com/search-jobs",
        "description": "British Airways careers portal",
        "class": "BritishAirwaysScraper",
        "module": "scraper_manager.scrapers.ba_scraper",
    },
    "cathay": {
        "name": "Cathay Pacific",
        "enabled": True,
        "base_url": "https://careers.cathaypacific.com",
        "jobs_url": "https://careers.cathaypacific.com/en/careers/jobs",
        "description": "Cathay Pacific careers page",
    },
    "germanairways": {
        "name": "German Airways",
        "enabled": True,
        "base_url": "https://german-airways.jobs.personio.de",
        "description": "German Airways (Personio) job board",
    },
    "aa": {
        "name": "American Airlines",
        "enabled": True,  # Blocked by WAF
        "base_url": "https://jobs.aa.com",
        "jobs_url": "https://jobs.aa.com/search/",
        "description": "American Airlines careers (Blocked by WAF)",
    },
    "etihad": {
        "name": "Etihad Airways",
        "enabled": True,
        "base_url": "https://careers.smartrecruiters.com/EtihadAirways5",
        "jobs_url": "https://careers.smartrecruiters.com/EtihadAirways5",
        "description": "Etihad Airways careers (SmartRecruiters)",
        "class": "SmartRecruitersScraper",
        "module": "scraper_manager.scrapers.smartrecruiters_scraper",
    },
    "bombardier": {
        "name": "Bombardier",
        "enabled": True,
        "base_url": "https://jobs.bombardier.com",
        "jobs_url": "https://jobs.bombardier.com/search/?q=&locationsearch=&searchResultView=LIST&pageNumber=1&facetFilters=%7B%7D&sortBy=&markerViewed=&carouselIndex=",
        "description": "Bombardier careers portal",
        "class": "BombardierScraper",
        "module": "scraper_manager.scrapers.bombardier_scraper",
    },
    "flydubai": {
        "name": "Flydubai",
        "enabled": True,
        "base_url": "https://careers.flydubai.com",
        "jobs_url": "https://careers.flydubai.com/jobs?page=1&categories=Behind%20the%20Scenes",
        "description": "Flydubai careers portal",
    },
    "ameriflight": {
        "name": "Ameriflight",
        "enabled": True,
        "base_url": "https://recruiting.paylocity.com",
        "jobs_url": "https://recruiting.paylocity.com/recruiting/jobs/All/ffb2b81c-27ab-41d2-959e-56f9349360aa/Ameriflight-LLC",
        "description": "Ameriflight careers (Paylocity)",
    },
    "pacificaviation": {
        "name": "Pacific Aviation",
        "enabled": True,
        "base_url": "https://apply.workable.com",
        "jobs_url": "https://apply.workable.com/pacificaviation/?lng=en",
        "description": "Pacific Aviation careers (Workable)",
    },
    "airarabia": {
        "name": "Air Arabia",
        "enabled": True,
        "base_url": "https://jobs.airarabiagroupcareers.com",
        "jobs_url": "https://jobs.airarabiagroupcareers.com/search/",
        "description": "Air Arabia Group careers portal",
    },
    "airarabia_auh": {
        "name": "Air Arabia Abu Dhabi",
        "enabled": True,
        "base_url": "https://jobs.airarabiagroupcareers.com",
        # NOTE: location= parameter is silently ignored by this site.
        # Using q= keyword search for Abu Dhabi instead (verified via live browser test).
        "jobs_url": "https://jobs.airarabiagroupcareers.com/search/?q=Abu+Dhabi",
        "description": "Air Arabia Abu Dhabi roles (keyword search filter)",
    },
    "dubairaw": {
        "name": "Dubai Royal Air Wing",
        "enabled": True,
        "base_url": "https://careers.dubaiairports.ae",
        "jobs_url": "https://careers.dubaiairports.ae/search-jobs",
        "description": "Dubai Royal Air Wing (Recruitment via Dubai Airports)",
    },
    "abudhabiaviation": {
        "name": "Abu Dhabi Aviation",
        "enabled": True,
        "base_url": "https://ada.ae",
        "jobs_url": "https://ada.ae/general-application/",
        "description": "Abu Dhabi Aviation general application",
    },
    "falconaviation": {
        "name": "Falcon Aviation Services",
        "enabled": True,
        "base_url": "https://falconaviation.ae",
        "jobs_url": "https://falconaviation.ae/careers",
        "description": "Falcon Aviation Services careers",
    },
    "transavia": {
        "name": "Transavia",
        "enabled": True,
        "base_url": "https://werkenbijtransavia.com",
        "jobs_url": "https://werkenbijtransavia.com/l/en/vacatures",
        "description": "Transavia vacancy portal",
    },
    "sun_country": {
        "name": "Sun Country Airlines",
        "enabled": True,
        "base_url": "https://recruiting2.ultipro.com/SUN1000SUNCO/JobBoard/5882c1c5-18e3-8740-5e61-37d8f7574d64/",
        "description": "Sun Country Airlines careers (UKG Pro)",
        "class": "SunCountryScraper",
        "module": "scraper_manager.scrapers.sun_country_scraper",
    },
    "mountain_air_cargo": {
        "name": "Mountain Air Cargo",
        "enabled": True,
        "base_url": "https://mountainaircargo.hrmdirect.com",
        "jobs_url": "https://mountainaircargo.hrmdirect.com/employment/job-openings.php?search=true&&cust_sort1=170262",
        "description": "Mountain Air Cargo careers (hrmdirect)",
        "class": "MountainAirCargoScraper",
        "module": "scraper_manager.scrapers.mountain_air_cargo_scraper",
    },
    "air_wisconsin": {
        "name": "Air Wisconsin",
        "enabled": True,
        "base_url": "https://recruiting2.ultipro.com/AIR1002AIRWI/JobBoard/74c69cd1-e0aa-4364-8c31-c93dc910998d/",
        "description": "Air Wisconsin careers (UKG Pro)",
        "class": "AirWisconsinScraper",
        "module": "scraper_manager.scrapers.air_wisconsin_scraper",
    },
    "atsg": {
        "name": "Air Transport Services Group (ATSG)",
        "enabled": True,
        "base_url": "https://recruiting.ultipro.com/AIR1013ATSG/JobBoard/7f7953dc-22ab-4b56-ad7a-2fe1ad00de22/",
        "description": "ATSG careers (UKG Pro)",
        "class": "ATSGScraper",
        "module": "scraper_manager.scrapers.atsg_scraper",
    },
    "nac": {
        "name": "Northern Air Cargo",
        "enabled": True,
        "base_url": "https://recruiting.ultipro.com/NOR1020NAIRC/JobBoard/be7c5458-8e9f-482c-b6a2-37175c50020d/",
        "description": "Northern Air Cargo careers (UKG Pro)",
        "class": "NACScraper",
        "module": "scraper_manager.scrapers.nac_scraper",
    },
    "omni_air": {
        "name": "Omni Air International",
        "enabled": True,
        "base_url": "https://workforcenow.adp.com",
        "jobs_url": "https://workforcenow.adp.com/mascsr/default/mdf/recruitment/recruitment.html?cid=a7828c0b-d30d-40a2-a3ee-61c80628985c&ccId=19000101_000001&lang=en_US&selectedMenuKey=CurrentOpenings",
        "description": "Omni Air International careers (ADP)",
        "class": "OmniAirScraper",
        "module": "scraper_manager.scrapers.omni_air_scraper",
    },
    "kalitta_holdings": {
        "name": "Kalitta Holdings",
        "enabled": True,
        "base_url": "https://recruiting.paylocity.com",
        "jobs_url": "https://recruiting.paylocity.com/recruiting/jobs/All/a34be4ee-9763-456a-beb1-0a06243c36f2/Doug-Kalitta-Holdings",
        "description": "Kalitta Holdings careers (Paylocity)",
        "class": "KalittaHoldingsScraper",
        "module": "scraper_manager.scrapers.kalitta_holdings_scraper",
    },
    "jet_aviation": {
        "name": "Jet Aviation",
        "enabled": True,
        "base_url": "https://jobs.jetaviation.com",
        "jobs_url": "https://jobs.jetaviation.com/go/Europe/8766702/?q=&q2=&alertId=&title=dispatch&location=&facility=&date=#searchresults",
        "description": "Jet Aviation careers (SuccessFactors)",
        "class": "JetAviationScraper",
        "module": "scraper_manager.scrapers.jet_aviation_scraper",
    },
    "riyadh_air": {
        "name": "Riyadh Air",
        "enabled": True,
        "base_url": "https://globalcareerhub-riyadhair.icims.com",
        "jobs_url": "https://globalcareerhub-riyadhair.icims.com/jobs/search?hashed=-625885971&mobile=false&width=1492&height=500&bga=true&needsRedirect=false&jan1offset=330&jun1offset=330",
        "description": "Riyadh Air careers (iCIMS)",
        "class": "RiyadhAirScraper",
        "module": "scraper_manager.scrapers.riyadh_air_scraper",
    },
    "global_jet": {
        "name": "Global Jet",
        "enabled": True,
        "base_url": "https://globaljet.aero",
        "jobs_url": "https://globaljet.aero/en/careers",
        "description": "Global Jet careers (Custom SPA)",
        "class": "GlobalJetScraper",
        "module": "scraper_manager.scrapers.global_jet_scraper",
    },
    "alaska": {
        "name": "Alaska Airlines",
        "enabled": True,
        "base_url": "https://careers.alaskaair.com",
        "jobs_url": "https://careers.alaskaair.com/jobs/search?in_iframe=1",
        "description": "Alaska Airlines careers (iCIMS)",
    },
    "skywest": {
        "name": "SkyWest Airlines",
        "enabled": True,
        "base_url": "https://www.skywest.com",
        "jobs_url": "https://skywest-airlines.icims.com/jobs/search?in_iframe=1",
        "description": "SkyWest Airlines careers (iCIMS)",
    },
    "republic": {
        "name": "Republic Airways",
        "enabled": True,
        "base_url": "https://rjet.com/careers",
        "jobs_url": "https://rjet.com/careers",
        "description": "Republic Airways careers (iCIMS)",
    },
    "endeavor": {
        "name": "Endeavor Air",
        "enabled": True,
        "base_url": "https://www.endeavorair.com",
        "jobs_url": "https://www.endeavorair.com/careers",
        "description": "Endeavor Air careers (iCIMS)",
    },
    "frontier": {
        "name": "Frontier Airlines",
        "enabled": True,
        "base_url": "https://recruiting2.ultipro.com",
        "jobs_url": "https://recruiting2.ultipro.com/FRO1003FTAIR/JobBoard/1efcf859-1b48-4a31-b014-ef62bdcab988/?q=&o=postedDateDesc",
        "description": "Frontier Airlines careers (UKG Pro)",
        "class": "FrontierScraper",
        "module": "scraper_manager.scrapers.frontier_scraper",
    },
    "dhl": {
        "name": "DHL Aviation",
        "enabled": True,
        "base_url": "https://careers.dhl.com",
        "jobs_url": "https://careers.dhl.com/global/en/c/operations-jobs",
        "description": "DHL Aviation careers (SmartRecruiters)",
    },
    "cae": {
        "name": "CAE",
        "enabled": True,
        "base_url": "https://cae.wd3.myworkdayjobs.com/en-US/career/",
        "jobs_url": "https://cae.wd3.myworkdayjobs.com/wday/cxs/cae/career/jobs",
        "description": "CAE careers (Workday API)",
    },
    "globeair": {
        "name": "GlobeAir",
        "enabled": True,
        "base_url": "https://www.globeair.com",
        "jobs_url": "https://www.globeair.com/career",
        "description": "GlobeAir Careers",
    },
    "norse": {
        "name": "Norse Atlantic Airways",
        "enabled": True,
        "base_url": "https://careers.flynorse.com",
        "jobs_url": "https://careers.flynorse.com/jobs",
        "description": "Norse Atlantic Airways Careers",
    },
    "perimeter": {
        "name": "Perimeter Aviation",
        "enabled": True,
        "base_url": "https://jobs.dayforcehcm.com",
        "jobs_url": "https://jobs.dayforcehcm.com/perimeteravi/All-Jobs",
        "description": "Perimeter Aviation careers (Dayforce)",
        "class": "DayforceScraper",
        "module": "scraper_manager.scrapers.dayforce_scraper",
    },
    "westjet": {
        "name": "WestJet",
        "enabled": True,
        "base_url": "https://jobs.dayforcehcm.com",
        "jobs_url": "https://jobs.dayforcehcm.com/en-CA/WestJet/OPSCONTROLCENTRE",
        "description": "WestJet careers (Dayforce)",
        "class": "DayforceScraper",
        "module": "scraper_manager.scrapers.dayforce_scraper",
    },
    "cevalogistics": {
        "name": "CEVA Logistics",
        "enabled": True,
        "base_url": "https://jobs.cmacgm-group.com",
        "jobs_url": "https://jobs.cmacgm-group.com/CEVALogistics/search/?createNewAlert=false&q=&locationsearch=&optionsFacetsDD_shifttype=",
        "description": "CEVA Logistics careers portal (SuccessFactors)",
        "class": "CevaLogisticsScraper",
        "module": "scraper_manager.scrapers.cevalogistics_scraper",
    },
    "jpmc": {
        "name": "JPMorgan Chase",
        "enabled": True,
        "base_url": "https://jpmc.fa.oraclecloud.com",
        "jobs_url": "https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/jobs",
        "api_url": "https://jpmc.fa.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions",
        "site_number": "CX_1001",
        "description": "JPMorgan Chase careers portal (Oracle Cloud HCM)",
        "class": "JpmcScraper",
        "module": "scraper_manager.scrapers.jpmc_scraper",
    },
    "fai": {
        "name": "FAI Aviation Group",
        "enabled": True,
        "base_url": "https://www.fai.ag",
        "jobs_url": "https://www.fai.ag/career/job-offers",
        "description": "FAI AG Careers",
    },
    "aireuropa": {
        "name": "Air Europa",
        "enabled": True,
        "base_url": "https://vacantes.aireuropa.com",
        "jobs_url": "https://vacantes.aireuropa.com/jobs",
        "description": "Air Europa Careers",
    },
    "skyexpress": {
        "name": "Sky Express",
        "enabled": True,
        "base_url": "https://www.skyexpress.gr",
        "jobs_url": "https://www.skyexpress.gr/en/company/careers",
        "description": "Sky Express Careers",
    },
    "glock": {
        "name": "Glock Aviation",
        "enabled": True,
        "base_url": "https://jobs.glock.at",
        "jobs_url": "https://jobs.glock.at/programme/onlinebewerbung_uebersicht.php",
        "description": "Glock Aviation Careers",
    },
    "maltairport": {
        "name": "Malta Airport",
        "enabled": True,
        "base_url": "https://maltairport.com",
        "jobs_url": "https://maltairport.com/corporate/careers/join-our-team/",
        "description": "Malta Airport Careers",
    },
    "marabu": {
        "name": "Marabu Airlines",
        "enabled": True,
        "base_url": "https://apply.workable.com/marabu/",
        "jobs_url": "https://apply.workable.com/api/v3/accounts/marabu/jobs",
        "description": "Marabu Airlines Careers (Workable)",
    },
    "jost": {
        "name": "Jost Group",
        "enabled": True,
        "base_url": "https://jostgroup.com",
        "jobs_url": "https://jostgroup.com/en/jobs",
        "description": "Jost Group Careers",
    },
    "faktor": {
        "name": "Faktor",
        "enabled": True,
        "base_url": "https://www.wearefaktor.com",
        "jobs_url": "https://www.wearefaktor.com/jobs",
        "description": "Faktor Recruitment",
    },
    "challenge": {
        "name": "Challenge Group",
        "enabled": True,
        "base_url": "https://career.challenge-group.com",
        "jobs_url": "https://career.challenge-group.com/search/",
        "description": "Challenge Group Careers",
    },
    "flix": {
        "name": "Flix",
        "enabled": True,
        "base_url": "https://flix.careers",
        "jobs_url": "https://flix.careers/de/standorte/berlin/#berlinjobs",
        "description": "Flix Careers",
    },
    "tradewind": {
        "name": "Tradewind",
        "enabled": True,
        "base_url": "https://recruiting.paylocity.com/recruiting/jobs/All/508f4046-d9bb-45f4-bd05-bdeaa7c8aa3c/Tradewind",
        "jobs_url": "https://recruiting.paylocity.com/recruiting/jobs/All/508f4046-d9bb-45f4-bd05-bdeaa7c8aa3c/Tradewind",
        "description": "Tradewind Aviation Careers",
    },
    "psa": {
        "name": "PSA Airlines",
        "enabled": True,
        "base_url": "https://careers-psaairlines.icims.com",
        "jobs_url": "https://careers-psaairlines.icims.com/jobs/search?in_iframe=1",
        "description": "PSA Airlines Careers",
    },
    "gridiron": {
        "name": "Gridiron Air",
        "enabled": True,
        "base_url": "https://recruiting2.ultipro.com/ARI1001CARD/JobBoard/952474da-aa04-4760-90e6-cdacf1e0cc13",
        "jobs_url": "https://recruiting2.ultipro.com/ARI1001CARD/JobBoard/952474da-aa04-4760-90e6-cdacf1e0cc13/?q=&o=postedDateDesc",
        "description": "Gridiron Air Careers",
    },
    "amentum": {
        "name": "Amentum",
        "enabled": True,
        "base_url": "https://www.amentumcareers.com",
        "jobs_url": "https://www.amentumcareers.com/jobs/search?query=",
        "description": "Amentum Careers",
        "class": "AmentumScraper",
        "module": "scraper_manager.scrapers.amentum_scraper",
    },
    "flyexclusive": {
        "name": "flyExclusive",
        "enabled": True,
        "base_url": "https://www.paycomonline.net",
        "jobs_url": "https://www.paycomonline.net/v4/ats/web.php/portal/91989CEA70627F35DBDEA57AC03E0A2B/career-page",
        "description": "flyExclusive Careers (Paycom)",
        "class": "FlyExclusiveScraper",
        "module": "scraper_manager.scrapers.flyexclusive_scraper",
    },
    "havenasg": {
        "name": "Haven ASG",
        "enabled": True,
        "base_url": "https://www.havenasg.com",
        "jobs_url": "https://www.havenasg.com/careers#roles",
        "description": "Haven Aviation Services Group Careers",
    },
    "contour": {
        "name": "Contour Aviation",
        "enabled": True,
        "base_url": "https://www.paycomonline.net/v4/ats/web.php/portal/4E8FCB0F31AC88147F0DB7B85238B354/career-page",
        "jobs_url": "https://www.paycomonline.net/v4/ats/web.php/portal/4E8FCB0F31AC88147F0DB7B85238B354/career-page",
        "description": "Contour Aviation Careers",
    },
    "cmacgm": {
        "name": "CMA CGM",
        "enabled": True,
        "base_url": "https://jobs.cmacgm-group.com",
        "jobs_url": "https://jobs.cmacgm-group.com/go/Air-Freight-2/9716801/",
        "description": "CMA CGM careers (SuccessFactors)",
        "class": "CmacgmScraper",
        "module": "scraper_manager.scrapers.cmacgm_scraper",
    },
    "neosair": {
        "name": "Neos Air",
        "enabled": True,
        "base_url": "https://www.neosair.com",
        "jobs_url": "https://www.neosair.com/en/work-with-us/open-positions",
        "description": "Neos Air careers",
        "class": "NeosAirScraper",
        "module": "scraper_manager.scrapers.neosair_scraper",
    },
    "hifly": {
        "name": "Hi Fly",
        "enabled": True,
        "base_url": "https://hifly.aero",
        "jobs_url": "https://hifly.aero/careers/",
        "description": "Hi Fly careers",
        "class": "HiFlyScraper",
        "module": "scraper_manager.scrapers.hifly_scraper",
    },
    "airarabia": {
        "name": "Air Arabia",
        "enabled": True,
        "base_url": "https://www.airarabiagroupcareers.com",
        "jobs_url": "https://www.airarabiagroupcareers.com/gb/en/flight-operations",
        "description": "Air Arabia Careers",
        "class": "AirArabiaScraper",
        "module": "scraper_manager.scrapers.airarabia_scraper",
    },
    "cargolux": {
        "name": "Cargolux",
        "enabled": True,
        "base_url": "https://cargolux-iajigs.fa.ocs.oraclecloud.com",
        "jobs_url": "https://cargolux-iajigs.fa.ocs.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CargoluxGroundStaff/jobs",
        "description": "Cargolux Ground Staff Careers",
        "class": "CargoluxScraper",
        "module": "scraper_manager.scrapers.cargolux_scraper",
    },
    "platoon": {
        "name": "Platoon Aviation",
        "enabled": True,
        "base_url": "https://platoon-aviation.jobs.personio.de/",
        "jobs_url": "https://platoon-aviation.jobs.personio.de/",
        "description": "Platoon Aviation Personio",
        "class": "PlatoonScraper",
        "module": "scraper_manager.scrapers.platoon_scraper",
    },
    "flexjet": {
        "name": "Flexjet",
        "enabled": True,
        "base_url": "https://careers.flexjet.com",
        "jobs_url": "https://careers.flexjet.com/us/en/eu-all-categories",
        "description": "Flexjet Careers",
        "class": "FlexjetScraper",
        "module": "scraper_manager.scrapers.flexjet_scraper",
    },
    "skyexpress": {
        "name": "Sky Express",
        "enabled": True,
        "base_url": "https://www.skyexpress.gr/en/company/careers",
        "jobs_url": "https://www.skyexpress.gr/en/company/careers",
        "description": "Sky Express Careers",
        "class": "SkyExpressScraper",
        "module": "scraper_manager.scrapers.skyexpress_scraper",
    },
    "breeze_airways": {
        "name": "Breeze Airways",
        "enabled": True,
        "base_url": "https://job-boards.greenhouse.io/breezeairways",
        "jobs_url": "https://boards-api.greenhouse.io/v1/boards/breezeairways/jobs",
        "class": "BreezeAirwaysScraper",
        "module": "scraper_manager.scrapers.breeze_airways_scraper",
        "description": "Breeze Airways Careers",
    },
    "vistajetcn": {
        "name": "VistaJet CN",
        "enabled": True,
        "base_url": "https://www.vistajet.cn/en/careers/",
        "jobs_url": "https://careers-vistajet.icims.com/jobs/search?ss=1&in_iframe=1",
        "description": "VistaJet CN Careers",
        "class": "VistajetcnScraper",
        "module": "scraper_manager.scrapers.vistajetcn_scraper",
    },
    "flylevel": {
        "name": "Fly LEVEL",
        "enabled": True,
        "base_url": "https://careers.flylevel.com",
        "jobs_url": "https://careers.flylevel.com/jobs",
        "description": "Fly LEVEL Careers",
        "class": "FlylevelScraper",
        "module": "scraper_manager.scrapers.flylevel_scraper",
    },
    "aeroitalia": {
        "name": "Aeroitalia",
        "enabled": True,
        "base_url": "https://www.aeroitalia.com/en",
        "jobs_url": "https://www.aeroitalia.com/en/company/work-with-us",
        "description": "Aeroitalia Careers",
        "class": "AeroitaliaScraper",
        "module": "scraper_manager.scrapers.aeroitalia_scraper",
    },
    "twenty_one_air": {
        "name": "21 Air",
        "enabled": True,
        "base_url": "https://recruiting.paylocity.com/recruiting/jobs/All/bf3ab0f0-77a0-4342-8ff8-83069b83bd23/21-AIR-LLC",
        "jobs_url": "https://recruiting.paylocity.com/recruiting/jobs/All/bf3ab0f0-77a0-4342-8ff8-83069b83bd23/21-AIR-LLC",
        "description": "21 Air Careers",
        "class": "TwentyOneAirScraper",
        "module": "scraper_manager.scrapers.twenty_one_air_scraper",
    },
    "sterling": {
        "name": "Sterling Airways",
        "enabled": True,
        "base_url": "https://flysterling.com/careers/",
        "jobs_url": "https://flysterling.com/careers/",
        "description": "Sterling Airways Careers",
        "class": "SterlingScraper",
        "module": "scraper_manager.scrapers.sterling_scraper",
    },
    "uchealth": {
        "name": "UCHealth",
        "enabled": True,
        "base_url": "https://careers.uchealth.org/search/jobs",
        "jobs_url": "https://careers.uchealth.org/search/jobs",
        "description": "UCHealth Careers",
        "class": "UCHealthScraper",
        "module": "scraper_manager.scrapers.uchealth_scraper",
    },
    "usajet": {
        "name": "USA Jet",
        "enabled": True,
        "base_url": "https://usajet.aero/flight-operations/",
        "jobs_url": "https://ascentgl.wd1.myworkdayjobs.com/USJ",
        "description": "USA Jet Careers",
        "class": "USAJetScraper",
        "module": "scraper_manager.scrapers.usajet_scraper",
    },
    "igoxair": {
        "name": "iGox Air",
        "enabled": True,
        "base_url": "https://www.igoxair.com/opportunities",
        "jobs_url": "https://www.igoxair.com/opportunities",
        "description": "iGox Air Careers",
        "class": "IGoxAirScraper",
        "module": "scraper_manager.scrapers.igoxair_scraper",
    },
    "phoenix_air_group": {
        "name": "Phoenix Air Group",
        "enabled": True,
        "base_url": "https://workforcenow.adp.com/mascsr/default/mdf/recruitment/recruitment.html?cid=0e1b54aa-e5af-4e0b-90d1-e04e6d0be023&ccId=19000101_000001&lang=en_US",
        "jobs_url": "https://workforcenow.adp.com/mascsr/default/careercenter/public/events/staffing/v1/job-requisitions?cid=0e1b54aa-e5af-4e0b-90d1-e04e6d0be023&ccId=19000101_000001&lang=en_US",
        "description": "Phoenix Air Group Careers",
        "class": "PhoenixAirGroupScraper",
        "module": "scraper_manager.scrapers.phoenix_air_group_scraper",
    },
    "cutter": {
        "name": "Cutter Aviation",
        "enabled": True,
        "base_url": "https://cutteraviation.com/careers/",
        "jobs_url": "https://recruiting.paylocity.com/recruiting/v2/api/feed/jobs/e31122d0-2189-4eb9-8b32-a8dd1dafea6c",
        "description": "Cutter Aviation Careers",
        "class": "CutterScraper",
        "module": "scraper_manager.scrapers.cutter_scraper",
    },
}


# Build complete config (used by scrapers)
CONFIG = {
    "scraper_settings": SCRAPER_SETTINGS,
    "scrapers": SCRAPERS,
    "sites": SITES,
}
