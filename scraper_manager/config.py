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
        "max_jobs": 100,
    },
    "run_specialty_scrapers": {
        "enabled": True,
        "schedule": "0 1 * * *",  # Daily at 01:00
        "description": "Run specialty airline scrapers (IndiGo, Air India, Cargolux)",
        "scrapers": ["indigo", "airindia", "cargolux"],
        "max_jobs": 50,
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
        "aar_corp": "medium",
        "fedex": "medium",
        "kalitta_air": "medium",
        "envoy_air": "medium",
        "atlas_air": "medium",
        "atlantic_aviation": "medium",
        "netjets": "medium",
        "wheels_up": "medium",
        "flexjet": "medium",
        "amerijet": "medium",
        "cargojet": "medium",
        "jetblue": "medium",
        "qatar": "medium",
        "dnatabrasil": "medium",
        "emploitic": "medium",
        "swissport": "medium",
        "menzies": "medium",
        "united": "high",
        "ups": "medium",
        "havenasg": "medium",
        "contour": "medium",
        "breeze_airways": "medium",
    },
}

# Per-Site Scraper Limits
SCRAPERS = {
    "absjets": {
        "max_jobs": 50,
    },
    "aegean": {
        "max_jobs": 50,
    },
    "aena": {
        "max_jobs": 50,
    },
    "airfrance": {
        "max_jobs": 50,
    },
    "airfrancehop": {
        "max_jobs": 50,
    },
    "airmalta": {
        "max_jobs": 50,
    },
    "airserbia": {
        "max_jobs": 50,
    },
    "alsieexpress": {
        "max_jobs": 50,
    },
    "amapolaflyg": {
        "max_jobs": 50,
    },
    "aslairlinesbelgium": {
        "max_jobs": 50,
    },
    "austrianairlines": {
        "max_jobs": 50,
    },
    "blueislands": {
        "max_jobs": 50,
    },
    "braathens": {
        "max_jobs": 50,
    },
    "bristow": {
        "max_jobs": 50,
    },
    "brusselsairlines": {
        "max_jobs": 50,
    },
    "buraqair": {
        "max_jobs": 50,
    },
    "buzz": {
        "max_jobs": 50,
    },
    "cabotaviation": {
        "max_jobs": 50,
    },
    "capitalairlines": {
        "max_jobs": 50,
    },
    "carpatair": {
        "max_jobs": 50,
    },
    "dat": {
        "max_jobs": 50,
    },
    "easternairways": {
        "max_jobs": 50,
    },
    "easyjet": {
        "max_jobs": 100,
    },
    "edelweiss": {
        "max_jobs": 50,
    },
    "egyptair": {
        "max_jobs": 50,
        "headless": False,
    },
    "elal": {
        "max_jobs": 50,
        "headless": False,
    },
    "ethiopian": {
        "max_jobs": 50,
    },
    "eurowings": {
        "max_jobs": 50,
    },
    "finnair": {
        "max_jobs": 50,
    },
    "flybe": {
        "max_jobs": 50,
    },
    "hahnair": {
        "max_jobs": 50,
    },
    "iberia": {
        "max_jobs": 50,
        "headless": False,
    },
    "iberiaexpress": {
        "max_jobs": 50,
        "headless": False,
    },
    "icelandair": {
        "max_jobs": 50,
        "headless": False,
    },
    "itaairways": {
        "max_jobs": 50,
        "headless": False,
    },
    "klm": {
        "max_jobs": 50,
        "headless": False,
    },
    "lufthansacityline": {
        "max_jobs": 50,
    },
    "norwegian": {
        "max_jobs": 50,
    },
    "olympicair": {
        "max_jobs": 50,
    },
    "ryanair": {
        "max_jobs": 50,
    },
    "sas": {
        "max_jobs": 50,
    },
    "smartwings": {
        "max_jobs": 50,
        "headless": False,
    },
    "swiss": {
        "max_jobs": 50,
    },
    "tap": {
        "max_jobs": 50,
    },
    "transavia": {
        "max_jobs": 50,
        "headless": False,
    },
    "tuiairways": {
        "max_jobs": 50,
    },
    "vueling": {
        "max_jobs": 50,
    },
    "aerlingus": {
        "max_jobs": 50,
    },
    "airbaltic": {
        "max_jobs": 50,
    },
    "airdolomiti": {
        "max_jobs": 50,
    },
    "airnostrum": {
        "max_jobs": 50,
    },
    "signature": {
        "max_jobs": 50,  # None = extract all jobs
        # None = no page limit
    },
    "aap": {
        "max_jobs": 50,  # Limit for testing
    },
    "cargolux": {
        "max_jobs": 50,
    },
    "airindia": {
        "max_jobs": 50,
    },
    "emirates": {
        "max_jobs": 50,
        "search_queries": ["Operations", "Dispatcher", "Manager"],
    },
    "boeing": {
        "max_jobs": 50,
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
    "airbus": {"max_jobs": 50, "search_queries": ["Dispatch", "Operations", "Manager"]},
    "aisats": {
        "max_jobs": 5,
    },
    "jmc": {
        "max_jobs": 50,
        "timeout": 60,
    },
    "iata": {
        "max_jobs": 50,
        "timeout": 60,
    },
    "avianation": {
        "max_jobs": 50,
        "timeout": 60,
    },
    "wizzair": {
        "max_jobs": 50,
        "timeout": 60,
        "search_queries": [
            "Operations",
            "Dispatcher",
            "Manager",
        ],  # Default to all, or user specific like "Pilot"
    },
    "cpr": {
        "max_jobs": 50,
        "timeout": 60,
    },
    "nbaa": {
        "max_jobs": 50,
        "timeout": 60,
    },
    "starair": {
        "max_jobs": 50,
    },
    "lufthansa": {
        "max_jobs": 50,
    },
    "southwest": {
        "max_jobs": 50,
    },
    "ba": {
        "max_jobs": 50,
    },
    "cathay": {
        "max_jobs": 50,
    },
    "germanairways": {
        "max_jobs": 50,
    },
    "aa": {
        "max_jobs": 50,
    },
    "etihad": {
        "max_jobs": 50,
    },
    "flydubai": {
        "max_jobs": 50,
    },
    "airarabia": {
        "max_jobs": 50,
    },
    "airarabia_auh": {
        "max_jobs": 50,
    },
    "royaljet": {
        "max_jobs": 50,
    },
    "dubairaw": {
        "max_jobs": 50,
    },
    "abudhabiaviation": {
        "max_jobs": 50,
    },
    "falconaviation": {
        "max_jobs": 50,
    },
    "wmd": {
        "max_jobs": 50,
    },
    "jetfly": {
        "max_jobs": 50,
    },
    "kuwaitairways": {
        "max_jobs": 50,
    },
    "flyadeal": {
        "max_jobs": 50,
    },
    "flynas": {
        "max_jobs": 50,
    },
    "saudia": {
        "max_jobs": 50,
    },
    "nesma": {
        "max_jobs": 50,
    },
    "gulfair": {
        "max_jobs": 50,
    },
    "omanair": {
        "max_jobs": 50,
    },
    "salamair": {
        "max_jobs": 50,
    },
    "spirit": {
        "max_jobs": 50,
    },
    "mesa": {
        "max_jobs": 50,
    },
    "delta": {
        "max_jobs": 50,
    },
    "sun_country": {
        "max_jobs": 50,
    },
    "mountain_air_cargo": {
        "max_jobs": 50,
    },
    "air_wisconsin": {
        "max_jobs": 50,
    },
    "atsg": {
        "max_jobs": 50,
    },
    "nac": {
        "max_jobs": 50,
    },
    "omni_air": {
        "max_jobs": 50,
    },
    "kalitta_holdings": {
        "max_jobs": 50,
    },
    "jet_aviation": {
        "max_jobs": 50,
    },
    "riyadh_air": {
        "max_jobs": 50,
    },
    "global_jet": {
        "max_jobs": 50,
    },
    "aar_corp": {
        "max_jobs": 50,
    },
    "fedex": {
        "max_jobs": 50,
    },
    "kalitta_air": {
        "max_jobs": 50,
    },
    "envoy_air": {
        "max_jobs": 50,
    },
    "atlas_air": {
        "max_jobs": 50,
    },
    "atlantic_aviation": {
        "max_jobs": 50,
    },
    "netjets": {
        "max_jobs": 50,
    },
    "wheels_up": {
        "max_jobs": 50,
    },
    "flexjet": {
        "max_jobs": 50,
    },
    "amerijet": {
        "max_jobs": 50,
    },
    "cargojet": {
        "max_jobs": 50,
    },
    "jetblue": {
        "max_jobs": 50,
    },
    "qatar": {
        "max_jobs": 50,
    },
    "dnatabrasil": {
        "max_jobs": 50,
    },
    "emploitic": {
        "max_jobs": 50,
    },
    "swissport": {
        "max_jobs": 50,
    },
    "menzies": {
        "max_jobs": 50,
    },
    "united": {
        "max_jobs": 50,
    },
    "ups": {
        "max_jobs": 50,
    },
    "havenasg": {
        "max_jobs": 50,
    },
    "contour": {
        "max_jobs": 150,
    },
    "breeze_airways": {
        "max_jobs": 50,
    },
}

# Site Configurations
SITES = {
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
        "jobs_url": "https://careers.qatarairways.com/global/SearchJobs/?jobRecordsPerPage=6&jobOffset=0",
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
        "enabled": True,
        "base_url": "https://careers.jmenzies.com",
        "jobs_url": "https://careers.jmenzies.com/aviation/vacancy/find/results/",
        "description": "Menzies Aviation careers (Oleeo)",
        "class": "MenziesScraper",
        "module": "scraper_manager.scrapers.menzies_scraper",
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
        "jobs_url": "https://jobs.aegeanair.com/",
        "description": "Aegean Airlines careers",
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
        "jobs_url": "https://careers.southwestair.com/us/en/search-results",
        "description": "Southwest Airlines careers (Phenom People)",
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
        "jobs_url": "https://jetfly.com/apply-for-a-job",
        "description": "Jetfly careers page",
        "class": "JetflyScraper",
        "module": "scraper_manager.scrapers.jetfly_scraper",
    },
    "easyjet": {
        "name": "easyJet",
        "enabled": True,
        "base_url": "https://careers.easyjet.com",
        "jobs_url": "https://careers.easyjet.com/en",
        "description": "easyJet careers",
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
        "jobs_url": "https://portal.iberia.es/portal/site/Iberia/menuitem.944252622416f0ce3f0ce310f2108a0c/",
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
        "enabled": True,
        "base_url": "https://careers.fedex.com",
        "jobs_url": "https://careers.fedex.com/jobs",
        "description": "FedEx careers (Phenom People)",
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
        "jobs_url": "https://careers.flexjet.com/us/en/search-results",
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
        "jobs_url": "https://portalempleo.iberiaexpress.com/",
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
        "jobs_url": "https://careers.sasgroup.net/",
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
        "jobs_url": "https://careers.tuigroup.com/en/search-jobs",
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
        "description": "Official career site for Emirates Group",
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
        "description": "Lufthansa Group careers portal",
    },
    "ba": {
        "name": "British Airways",
        "enabled": True,
        "base_url": "https://careers.ba.com",
        "jobs_url": "https://careers.ba.com/search-jobs",
        "description": "British Airways careers portal",
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
        "jobs_url": "https://careers.flydubai.com/jobs",
        "description": "Flydubai careers portal",
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
        "jobs_url": "https://careers.dhl.com",
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
    "perimeter": {
        "name": "Perimeter Aviation",
        "enabled": True,
        "base_url": "https://jobs.dayforcehcm.com",
        "jobs_url": "https://jobs.dayforcehcm.com/perimeteravi/All-Jobs",
        "description": "Perimeter Aviation careers (Dayforce)",
        "class": "DayforceScraper",
        "module": "scraper_manager.scrapers.dayforce_scraper",
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
    "breeze_airways": {
        "name": "Breeze Airways",
        "enabled": True,
        "base_url": "https://job-boards.greenhouse.io/breezeairways",
        "jobs_url": "https://boards-api.greenhouse.io/v1/boards/breezeairways/jobs",
        "class": "BreezeAirwaysScraper",
        "module": "scraper_manager.scrapers.breeze_airways_scraper",
        "description": "Breeze Airways Careers",
    },
}

# Build complete config (used by scrapers)
CONFIG = {
    "scraper_settings": SCRAPER_SETTINGS,
    "scrapers": SCRAPERS,
    "sites": SITES,
}
