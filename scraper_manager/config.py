"""
Configuration for Aviation Job Scraper
Edit these settings to control scraper behavior for different sites
"""

# Auto-Schedule Configuration
AUTO_SCHEDULE = {
    'enabled': True,  # Enable/disable automatic scheduling
    'run_all_scrapers': {
        'enabled': True,
        'schedule': '0 */3 * * *',  # Cron: Every 3 hours (HH:00)
        'description': 'Run all enabled scrapers',
        'max_jobs': None,  # None = use per-scraper limits

    },
    'run_priority_scrapers': {
        'enabled': True,
        'schedule': '0 */6 * * *',  # Every 6 hours
        'description': 'Run high-priority scrapers (Signature, LinkedIn, AviationJobSearch)',
        'scrapers': ['signature',  'aviationjobsearch'],
        'max_jobs': 100,
    },
    'run_specialty_scrapers': {
        'enabled': True,
        'schedule': '0 1 * * *',  # Daily at 01:00
        'description': 'Run specialty airline scrapers (IndiGo, Air India, Cargolux)',
        'scrapers': ['indigo', 'airindia', 'cargolux'],
        'max_jobs': 50,
    },
    'cleanup_old_jobs': {
        'enabled': True,
        'schedule': '0 3 * * 0',  # Weekly on Sunday at 03:00
        'description': 'Archive/cleanup jobs older than 90 days',
    },
    'generate_report': {
        'enabled': True,
        'schedule': '0 23 * * *',  # Daily at 23:00
        'description': 'Generate daily scraper report',
    },
}

# Global Scraper Settings
SCRAPER_SETTINGS = {
    # Number of concurrent browser pages for description extraction
    'batch_size': 3,  # Reduced from 5 to be less aggressive
    
    # Output directory
    'output_dir': 'output',
    
    # Anti-Detection Settings
    'stealth_mode': True,
    'request_delay_min': 2,  # Minimum delay between requests (seconds)
    'request_delay_max': 5,  # Maximum delay between requests (seconds)
    'page_load_delay': 3,    # Extra delay after page load (seconds)
    'random_scroll': True,   # Simulate human scrolling
    'random_mouse': True,    # Simulate mouse movements
    
    # Browser impersonation targets for TLS fingerprinting (curl_cffi)
    # Rotating these makes the scraper much harder to detect
    # Note: Only desktop browser impersonations are supported by curl_cffi
    'impersonate_list': [
        'chrome110', 
        'chrome120', 
        'edge101',
        'firefox'
    ],
    'user_agents': [
    # --- Google Chrome (Windows) ---
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
    
    # --- Google Chrome (macOS) ---
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    
    # --- Google Chrome (Linux) ---
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    
    # --- Mozilla Firefox (Windows) ---
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0',
    
    # --- Mozilla Firefox (macOS) ---
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:126.0) Gecko/20100101 Firefox/126.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) Gecko/20100101 Firefox/125.0',
    
    # --- Microsoft Edge (Windows) ---
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0',
    
    # --- Apple Safari (macOS) ---
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15',
    ],
    
    # Proxy Settings (optional - add your proxies here)
    'proxy_list': [],  # Example: ['http://user:pass@proxy1.com:8080', 'http://proxy2.com:8080']
    'rotate_proxy': False,
    
    # Title Filtering Settings
    # ---------------------------
    # Global settings for the job filtering system (JobFilterManager).
    # - filter_file: JSON file containing categories and keywords.
    # - filter_before_scrape: Filter by title BEFORE fetching descriptions.
    #   (Saves significant time and resources).
    'filter_file': 'filter_title.json',
    'filter_before_scrape': True,
    
    # Priority Levels for scrapers (higher = more priority)
    'priority_levels': {
        'absjets': 'medium',
        'aegean': 'medium',
        'aena': 'medium',
        'aireuropaexpress': 'medium',
        'airfrance': 'medium',
        'airfrancehop': 'medium',
        'airmalta': 'medium',
        'airserbia': 'medium',
        'alsieexpress': 'medium',
        'amapolaflyg': 'medium',
        'aslairlinesbelgium': 'medium',
        'austrianairlines': 'medium',
        'blueislands': 'medium',
        'braathens': 'medium',
        'bristow': 'medium',
        'brusselsairlines': 'medium',
        'buraqair': 'medium',
        'buzz': 'medium',
        'cabotaviation': 'medium',
        'capitalairlines': 'medium',
        'carpatair': 'medium',
        'dat': 'medium',
        'easternairways': 'medium',
        'easyjet': 'medium',
        'edelweiss': 'medium',
        'egyptair': 'medium',
        'elal': 'medium',
        'ethiopian': 'medium',
        'eurowings': 'medium',
        'finnair': 'medium',
        'flybe': 'medium',
        'hahnair': 'medium',
        'iberia': 'medium',
        'iberiaexpress': 'medium',
        'icelandair': 'medium',
        'itaairways': 'medium',
        'klm': 'medium',
        'lot': 'medium',
        'lufthansacityline': 'medium',
        'norwegian': 'medium',
        'olympicair': 'medium',
        'ryanair': 'medium',
        'sas': 'medium',
        'smartwings': 'medium',
        'swiss': 'medium',
        'tap': 'medium',
        'transavia': 'medium',
        'tuiairways': 'medium',
        'vueling': 'medium',
        'aerlingus': 'medium',
        'airbaltic': 'medium',
        'airdolomiti': 'medium',
        'airnostrum': 'medium',
        'signature': 'high',          # Always run - reliable source
        'linkedin': 'low',           # Large job database
        'aviationjobsearch': 'high',  # Specialized aviation jobs
        'flygosh': 'medium',
        'aap': 'medium',
        'goose': 'medium',
        'cargolux': 'medium',         # Airline-specific
        'airindia': 'medium',         # Airline-specific
        'indigo': 'medium',           # Airline-specific (fixed recently)
        'aisats': 'medium',           # Ground handling
        'aviationindeed': 'high',      # Currently disabled
        'etihad': 'medium',
        'flydubai': 'medium',
        'airarabia': 'medium',
        'airarabia_auh': 'medium',
        'royaljet': 'medium',
        'dubairaw': 'low',
        'abudhabiaviation': 'medium',
        'falconaviation': 'medium',
    }
}

# Per-Site Scraper Limits
SCRAPERS = {
    'absjets': {
        'max_jobs': 50,
    },
    'aegean': {
        'max_jobs': 50,
    },
    'aena': {
        'max_jobs': 50,
    },
    'aireuropaexpress': {
        'max_jobs': 50,
    },
    'airfrance': {
        'max_jobs': 50,
    },
    'airfrancehop': {
        'max_jobs': 50,
    },
    'airmalta': {
        'max_jobs': 50,
    },
    'airserbia': {
        'max_jobs': 50,
    },
    'alsieexpress': {
        'max_jobs': 50,
    },
    'amapolaflyg': {
        'max_jobs': 50,
    },
    'aslairlinesbelgium': {
        'max_jobs': 50,
    },
    'austrianairlines': {
        'max_jobs': 50,
    },
    'blueislands': {
        'max_jobs': 50,
    },
    'braathens': {
        'max_jobs': 50,
    },
    'bristow': {
        'max_jobs': 50,
    },
    'brusselsairlines': {
        'max_jobs': 50,
    },
    'buraqair': {
        'max_jobs': 50,
    },
    'buzz': {
        'max_jobs': 50,
    },
    'cabotaviation': {
        'max_jobs': 50,
    },
    'capitalairlines': {
        'max_jobs': 50,
    },
    'carpatair': {
        'max_jobs': 50,
    },
    'dat': {
        'max_jobs': 50,
    },
    'easternairways': {
        'max_jobs': 50,
    },
    'easyjet': {
        'max_jobs': 100,
    },
    'edelweiss': {
        'max_jobs': 50,
    },
    'egyptair': {
        'max_jobs': 50,
        'headless': False,
    },
    'elal': {
        'max_jobs': 50,
        'headless': False,
    },
    'ethiopian': {
        'max_jobs': 50,
    },
    'eurowings': {
        'max_jobs': 50,
    },
    'finnair': {
        'max_jobs': 50,
    },
    'flybe': {
        'max_jobs': 50,
    },
    'hahnair': {
        'max_jobs': 50,
    },
    'iberia': {
        'max_jobs': 50,
        'headless': False,
    },
    'iberiaexpress': {
        'max_jobs': 50,
        'headless': False,
    },
    'icelandair': {
        'max_jobs': 50,
        'headless': False,
    },
    'itaairways': {
        'max_jobs': 50,
        'headless': False,
    },
    'klm': {
        'max_jobs': 50,
        'headless': False,
    },
    'lot': {
        'max_jobs': 50,
    },
    'lufthansacityline': {
        'max_jobs': 50,
    },
    'norwegian': {
        'max_jobs': 50,
    },
    'olympicair': {
        'max_jobs': 50,
    },
    'ryanair': {
        'max_jobs': 50,
    },
    'sas': {
        'max_jobs': 50,
    },
    'smartwings': {
        'max_jobs': 50,
        'headless': False,
    },
    'swiss': {
        'max_jobs': 50,
    },
    'tap': {
        'max_jobs': 50,
    },
    'transavia': {
        'max_jobs': 50,
        'headless': False,
    },
    'tuiairways': {
        'max_jobs': 50,
    },
    'vueling': {
        'max_jobs': 50,
    },
    'aerlingus': {
        'max_jobs': 50,
    },
    'airbaltic': {
        'max_jobs': 50,
    },
    'airdolomiti': {
        'max_jobs': 50,
    },
    'airnostrum': {
        'max_jobs': 50,
    },
    'signature': {
        'max_jobs': 50,  # None = extract all jobs
  # None = no page limit
    },
    'flygosh': {
        'max_jobs': 50,   # Set to 50 to limit to 50 jobs
  # Not applicable for listing-based scrapers
    },
    'aviationindeed': {
        'max_jobs': 50,   # Limit for testing

    },
    'aap': {
        'max_jobs': 50,   # Limit for testing

    },
    'indigo': {
        'max_jobs': 40,   # Limit for testing

    },
    'aviationjobsearch': {
        'max_jobs': 50,   # Increased to find matching jobs

    },
    'goose': {
        'max_jobs': 50,   # Limit for testing

    },
    'linkedin': {
        'max_jobs': 50,   # Limit for LinkedIn scraping

    },
    'cargolux': {
        'max_jobs': 50,

    },
    'airindia': {
        'max_jobs': 50,

    },
    'jsfirm': {
        'max_jobs': 50,
        'search_locations': ['Singapore','Australia','Brazil','United Kingdom','Germany','France','Canada']
    },
    'allflyingjobs': {
        'max_jobs': 50,
        'search_queries': ['Dispatcher','Operations','Manager']
    },
    'emirates': {
        'max_jobs': 50,
        'search_queries': ['Operations', 'Dispatcher', 'Manager']
    },
    'boeing': {
        'max_jobs': 50,
        'search_queries': ['Operations','Dispatcher','Manager'],
        'search_locations': ['Singapore','Australia','Brazil','United Kingdom','Germany','France','Canada','Washington']
    },
    'airbus': {
        'max_jobs': 50,
        'search_queries': ['Dispatch' ,'Operations','Manager']
    },
    'pilots_global': {
        'max_jobs': 50
    },
    'aviationcv': {
        'max_jobs': 50,
    },
    'zenon': {
        'max_jobs': 50,
    },
    'aaae': {
        'max_jobs': 50,
    },
    'aisats': {
        'max_jobs': 5,
    },
    'jmc': {
        'max_jobs': 50,
        'timeout': 60,
    },
    'iata': {
        'max_jobs': 50,
        'timeout': 60,
    },
    'avianation': {
        'max_jobs': 50,
        'timeout': 60,
    },
    'wizzair': {
        'max_jobs': 50,
        'timeout': 60,
        'search_queries': ['Operations','Dispatcher','Manager'], # Default to all, or user specific like "Pilot"
    },
    'cpr': {
        'max_jobs': 50,
        'timeout': 60,
    },
    'nbaa': {
        'max_jobs': 50,
        'timeout': 60,
    },
    'starair': {
        'max_jobs': 50,
    },
    'lufthansa': {
        'max_jobs': 50,
    },
    'southwest': {
        'max_jobs': 50,
    },
    'ba': {
        'max_jobs': 50,
    },
    'cathay': {
        'max_jobs': 50,
    },
    'germanairways': {
        'max_jobs': 50,
    },
    'aa': {
        'max_jobs': 50,
    },
    'etihad': {
        'max_jobs': 50,
    },
    'flydubai': {
        'max_jobs': 50,
    },
    'airarabia': {
        'max_jobs': 50,
    },
    'airarabia_auh': {
        'max_jobs': 50,
    },
    'royaljet': {
        'max_jobs': 50,
    },
    'dubairaw': {
        'max_jobs': 50,
    },
    'abudhabiaviation': {
        'max_jobs': 50,
    },
    'falconaviation': {
        'max_jobs': 50,
    },
}

# Site Configurations
SITES = {
    'absjets': {
        'name': 'ABS Jets',
        'enabled': True,
        'base_url': 'https://www.absjets.com',
        'jobs_url': 'https://www.absjets.com/careers-109',
        'description': 'ABS Jets careers page',
    },
    'aegean': {
        'name': 'Aegean Airlines',
        'enabled': True,
        'base_url': 'https://jobs.aegeanair.com',
        'jobs_url': 'https://jobs.aegeanair.com/',
        'description': 'Aegean Airlines careers',
    },
    'aena': {
        'name': 'Aena',
        'enabled': True,
        'base_url': 'https://empleo.aena.es',
        'jobs_url': 'https://empleo.aena.es/empleo/SessSrv?accion=seleccionar&leng=EN&SEDE=0',
        'description': 'Aena careers',
    },
    'aireuropaexpress': {
        'name': 'Air Europa Express',
        'enabled': False,
        'base_url': 'https://www.airlinestaffrates.com',
        'jobs_url': 'https://www.airlinestaffrates.com/air-europa-express-is-hiring-flight-attendants-with-cabin-crew-certification-for/',
        'description': 'Air Europa Express proxy careers',
    },
    'airfrance': {
        'name': 'Air France',
        'enabled': True,
        'base_url': 'https://recrutement.airfrance.com',
        'jobs_url': 'https://recrutement.airfrance.com/homepage.aspx?LCID=2057',
        'description': 'Air France recruitment',
    },
    'airfrancehop': {
        'name': 'Air France HOP',
        'enabled': True,
        'base_url': 'https://www.hop.fr',
        'jobs_url': 'https://www.hop.fr/en/carriere/',
        'description': 'Air France HOP careers',
    },
    'airmalta': {
        'name': 'Air Malta (KM Malta Airlines)',
        'enabled': True,
        'base_url': 'https://kmmaltairlines.com',
        'jobs_url': 'https://kmmaltairlines.com/en/careers',
        'description': 'KM Malta Airlines careers',
    },
    'airserbia': {
        'name': 'Air Serbia',
        'enabled': True,
        'base_url': 'https://career.airserbia.com',
        'jobs_url': 'https://career.airserbia.com/',
        'description': 'Air Serbia careers',
    },
    'alsieexpress': {
        'name': 'Alsie Express',
        'enabled': True,
        'base_url': 'https://www.alsie.com',
        'jobs_url': 'https://candidate.hr-manager.net/vacancies/list.aspx?customer=alsie_tr&nocookie=true&uiculture=en',
        'description': 'Alsie Express (HR Manager)',
    },
    'amapolaflyg': {
        'name': 'Amapola Flyg',
        'enabled': True,
        'base_url': 'https://amapola.nu',
        'jobs_url': 'https://amapola.nu/about-us/careers/',
        'description': 'Amapola Flyg careers',
    },
    'aslairlinesbelgium': {
        'name': 'ASL Airlines Belgium',
        'enabled': True,
        'base_url': 'https://aslairlines.be',
        'jobs_url': 'https://aslairlines.be/asljobs/',
        'description': 'ASL Airlines Belgium careers',
    },
    'austrianairlines': {
        'name': 'Austrian Airlines',
        'enabled': True,
        'base_url': 'https://careers.austrian.com',
        'jobs_url': 'https://careers.austrian.com/en/',
        'description': 'Austrian Airlines careers',
    },
    'blueislands': {
        'name': 'Blue Islands',
        'enabled': True,
        'base_url': 'https://www.airlinestaffrates.com',
        'jobs_url': 'https://www.airlinestaffrates.com/blue-islands-is-hiring-cabin-crew-channel-islands/',
        'description': 'Blue Islands proxy careers',
    },
    'braathens': {
        'name': 'Braathens Regional Airlines',
        'enabled': True,
        'base_url': 'https://www.braathens.com',
        'jobs_url': 'https://www.braathens.com/career/',
        'description': 'Braathens Regional Airlines',
    },
    'bristow': {
        'name': 'Bristow Helicopters',
        'enabled': True,
        'base_url': 'https://www.linkedin.com/company/bristow-group-inc/jobs',
        'jobs_url': 'https://www.linkedin.com/company/bristow-group-inc/jobs',
        'description': 'Bristow Helicopters LinkedIn proxy',
    },
    'brusselsairlines': {
        'name': 'Brussels Airlines',
        'enabled': True,
        'base_url': 'https://www.lufthansagroup.careers/en/brussels-airlines/',
        'jobs_url': 'https://www.lufthansagroup.careers/en/brussels-airlines/',
        'description': 'Brussels Airlines careers',
    },
    'buraqair': {
        'name': 'Buraq Air',
        'enabled': True,
        'base_url': 'https://buraq.aero',
        'jobs_url': 'https://buraq.aero/careers/',
        'description': 'Buraq Air careers',
    },
    'buzz': {
        'name': 'Buzz (Ryanair Group)',
        'enabled': True,
        'base_url': 'https://careers.ryanair.com',
        'jobs_url': 'https://careers.ryanair.com/search/#job/search',
        'description': 'Buzz / Ryanair Group careers',
    },
    'cabotaviation': {
        'name': 'Cabot Aviation',
        'enabled': True,
        'base_url': 'https://cabotaviation.com',
        'jobs_url': 'https://cabotaviation.com/',
        'description': 'Cabot Aviation',
    },
    'capitalairlines': {
        'name': 'Beijing Capital Airlines',
        'enabled': True,
        'base_url': 'https://jdair.net',
        'jobs_url': 'https://jdair.net',
        'description': 'Beijing Capital Airlines fallback',
    },
    'southwest': {
        'name': 'Southwest Airlines',
        'enabled': True,
        'base_url': 'https://careers.southwestair.com',
        'jobs_url': 'https://careers.southwestair.com/us/en/search-results',
        'description': 'Southwest Airlines careers (Phenom People)',
    },
    'carpatair': {
        'name': 'Carpatair',
        'enabled': True,
        'base_url': 'https://www.carpatair.com',
        'jobs_url': 'https://www.carpatair.com/careers/',
        'description': 'Carpatair careers',
    },
    'dat': {
        'name': 'DAT (Danish Air Transport)',
        'enabled': True,
        'base_url': 'https://dat.dk',
        'jobs_url': 'https://dat.dk/corporate/careers',
        'description': 'DAT careers',
    },
    'easternairways': {
        'name': 'Eastern Airways',
        'enabled': True,
        'base_url': 'https://www.easternairways.com',
        'jobs_url': 'https://www.easternairways.com/careers',
        'description': 'Eastern Airways careers fallback',
    },
    'easyjet': {
        'name': 'easyJet',
        'enabled': True,
        'base_url': 'https://careers.easyjet.com',
        'jobs_url': 'https://careers.easyjet.com/en',
        'description': 'easyJet careers',
    },
    'edelweiss': {
        'name': 'Edelweiss Air',
        'enabled': True,
        'base_url': 'https://www.lufthansagroup.careers/en/edelweiss',
        'jobs_url': 'https://www.lufthansagroup.careers/en/edelweiss',
        'description': 'Edelweiss Air careers',
    },
    'egyptair': {
        'name': 'Egyptair',
        'enabled': True,
        'base_url': 'https://hr.egyptair.com',
        'jobs_url': 'https://hr.egyptair.com',
        'description': 'Egyptair careers fallback',
    },
    'elal': {
        'name': 'El Al',
        'enabled': True,
        'base_url': 'https://www.elal.com/eng/about/careers',
        'jobs_url': 'https://www.elal.com/eng/about/careers',
        'description': 'El Al careers fallback',
    },
    'ethiopian': {
        'name': 'Ethiopian Airlines',
        'enabled': True,
        'base_url': 'https://corporate.ethiopianairlines.com/AboutEthiopian/careers/vacancies',
        'jobs_url': 'https://corporate.ethiopianairlines.com/AboutEthiopian/careers/vacancies',
        'description': 'Ethiopian Airlines careers',
    },
    'eurowings': {
        'name': 'Eurowings',
        'enabled': True,
        'base_url': 'https://www.lufthansagroup.careers/en/eurowings',
        'jobs_url': 'https://www.lufthansagroup.careers/en/eurowings',
        'description': 'Eurowings careers',
    },
    'finnair': {
        'name': 'Finnair',
        'enabled': True,
        'base_url': 'https://company.finnair.com',
        'jobs_url': 'https://company.finnair.com/en/careers',
        'description': 'Finnair careers',
    },
    'flybe': {
        'name': 'Flybe',
        'enabled': True,
        'base_url': 'https://flybe.com',
        'jobs_url': 'https://flybe.com',
        'description': 'Flybe careers (Ceased operations, returning 0)',
    },
    'hahnair': {
        'name': 'Hahn Air Lines',
        'enabled': True,
        'base_url': 'https://www.hahnair.com',
        'jobs_url': 'https://www.hahnair.com/en/career/career',
        'description': 'Hahn Air Lines careers',
    },
    'iberia': {
        'name': 'Iberia',
        'enabled': True,
        'base_url': 'https://www.iberia.com/gb/careers/',
        'jobs_url': 'https://trabajaconnosotros.iberia.es/',
        'description': 'Iberia careers (SAP SuccessFactors)',
    },
    'iberiaexpress': {
        'name': 'Iberia Express',
        'enabled': True,
        'base_url': 'https://iberiaexpress.com',
        'jobs_url': 'https://portalempleo.iberiaexpress.com/',
        'description': 'Iberia Express careers (Custom Portal)',
    },
    'icelandair': {
        'name': 'Icelandair',
        'enabled': True,
        'base_url': 'https://www.icelandair.com/about/job-vacancies/',
        'jobs_url': 'https://jobs.50skills.com/icelandair/en',
        'description': 'Icelandair careers (50skills)',
    },
    'itaairways': {
        'name': 'ITA Airways',
        'enabled': True,
        'base_url': 'https://career.ita-airways.com/',
        'jobs_url': 'https://career.ita-airways.com/search/',
        'description': 'ITA Airways careers (SuccessFactors)',
    },
    'klm': {
        'name': 'KLM Royal Dutch Airlines',
        'enabled': True,
        'base_url': 'https://careers.klm.com/en/jobs/',
        'jobs_url': 'https://careers.klm.com/en/jobs/',
        'description': 'KLM careers (Fallback, WAF protected)',
    },
    'lot': {
        'name': 'LOT Polish Airlines',
        'enabled': True,
        'base_url': 'https://www.lot.com/',
        'jobs_url': 'https://www.lot.com/pl/pl/kariera',
        'description': 'LOT Polish Airlines careers',
    },
    'lufthansacityline': {
        'name': 'Lufthansa CityLine',
        'enabled': True,
        'base_url': 'https://www.lufthansagroup.careers/en/lufthansa-cityline',
        'jobs_url': 'https://www.lufthansagroup.careers/en/lufthansa-cityline',
        'description': 'Lufthansa CityLine careers',
    },
    'norwegian': {
        'name': 'Norwegian Air Shuttle',
        'enabled': True,
        'base_url': 'https://careers.norwegian.com',
        'jobs_url': 'https://careers.norwegian.com/search/',
        'description': 'Norwegian Air Shuttle careers (SuccessFactors)',
    },
    'olympicair': {
        'name': 'Olympic Air',
        'enabled': True,
        'base_url': 'https://jobs.aegeanair.com',
        'jobs_url': 'https://jobs.aegeanair.com/',
        'description': 'Olympic Air careers (Aegean proxy)',
    },
    'ryanair': {
        'name': 'Ryanair',
        'enabled': True,
        'base_url': 'https://careers.ryanair.com',
        'jobs_url': 'https://careers.ryanair.com/search/',
        'description': 'Ryanair careers',
    },
    'sas': {
        'name': 'SAS Scandinavian Airlines',
        'enabled': True,
        'base_url': 'https://careers.sasgroup.net',
        'jobs_url': 'https://careers.sasgroup.net/',
        'description': 'SAS Scandinavian Airlines careers',
    },
    'smartwings': {
        'name': 'SmartWings',
        'enabled': True,
        'base_url': 'https://www.smartwings.com/en/career/',
        'jobs_url': 'https://www.smartwings.com/en/career/',
        'description': 'SmartWings careers (Fallback, WAF protected)',
    },
    'swiss': {
        'name': 'Swiss International Air Lines',
        'enabled': True,
        'base_url': 'https://apply.lufthansagroup.careers/index.php?ac=search_result&search_criterion_activity_level%5B%5D=107',
        'jobs_url': 'https://apply.lufthansagroup.careers/index.php?ac=search_result&search_criterion_activity_level%5B%5D=107',
        'description': 'Swiss International Air Lines careers (Lufthansa Proxy)',
    },
    'tap': {
        'name': 'TAP Air Portugal',
        'enabled': True,
        'base_url': 'https://careers.flytap.com/',
        'jobs_url': 'https://careers.flytap.com/',
        'description': 'TAP Air Portugal careers',
    },
    'tuiairways': {
        'name': 'TUI Airways',
        'enabled': True,
        'base_url': 'https://careers.tuigroup.com/en/airline',
        'jobs_url': 'https://careers.tuigroup.com/en/airline',
        'description': 'TUI Airways careers',
    },
    'vueling': {
        'name': 'Vueling',
        'enabled': True,
        'base_url': 'https://careers.vueling.com/',
        'jobs_url': 'https://careers.vueling.com/',
        'description': 'Vueling careers',
    },
    'aerlingus': {
        'name': 'Aer Lingus',
        'enabled': True,
        'base_url': 'https://aerlingus.wd3.myworkdayjobs.com/en-US/AerLingus',
        'jobs_url': 'https://aerlingus.wd3.myworkdayjobs.com/en-US/AerLingus',
        'description': 'Aer Lingus careers (Workday)',
    },
    'airbaltic': {
        'name': 'Air Baltic',
        'enabled': True,
        'base_url': 'https://careers.airbaltic.com/en/jobs',
        'jobs_url': 'https://careers.airbaltic.com/en/jobs',
        'description': 'Air Baltic careers',
    },
    'airdolomiti': {
        'name': 'Air Dolomiti',
        'enabled': True,
        'base_url': 'https://airdolomiti.altamiraweb.com/',
        'jobs_url': 'https://airdolomiti.altamiraweb.com/default/',
        'description': 'Air Dolomiti careers',
    },
    'airnostrum': {
        'name': 'Air Nostrum',
        'enabled': True,
        'base_url': 'https://jobs.airnostrum.es/?locale=en_US',
        'jobs_url': 'https://jobs.airnostrum.es/?locale=en_US',
        'description': 'Air Nostrum careers',
    },
    'aaae': {
        'name': 'AAAE Career Center',
        'enabled': True,
        'base_url': 'https://careercenter.aaae.org',
        'jobs_url': 'https://careercenter.aaae.org/jobs',
        'description': 'American Association of Airport Executives - Career Center',
    },
    'signature': {
        'name': 'Signature Aviation',
        'enabled': True,
        'api_url': 'https://hdbt.fa.us2.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions',
        'site_number': 'CX_1',
        'base_url': 'https://jobs.signatureaviation.com',
        'description': 'Oracle Cloud HCM-based job board',
    },
    'flygosh': {
        'name': 'Flygosh Jobs',
        'enabled': True,
        'base_url': 'https://flygoshjobs.com',
        'jobs_url': 'https://flygoshjobs.com/jobs/all/all-region/',
        'description': 'Aviation jobs listing page',
    },
    # NOT WORKING YET - CEIPAL iframe requires special handling 
    'aviationindeed': {
        'name': 'Aviation Indeed',
        'enabled': True, # Site has loading issues - needs investigation
        'base_url': 'https://www.aviationindeed.com',
        'ceipal_url': 'https://www.aviationindeed.com/ceipal/',
        'description': 'CEIPAL iframe-based job board',
    },
    'aap': {
        'name': 'AAP Aviation',
        'enabled': True,
        'base_url': 'https://jobs.aapaviation.com',
        'jobs_url': 'https://jobs.aapaviation.com/jobs',
        'description': 'AAP Aviation job board',
    },
    'indigo': {
        'name': 'IndiGo Airlines',
        'enabled': True,  # Temporarily enabled for debugging and fixes
        'base_url': 'https://www.goindigo.in',
        'jobs_url': 'https://www.goindigo.in/careers/job-search.html?type=&location=&department=',
        'description': 'IndiGo Airlines careers page (currently under development)',
    },
    'aviationjobsearch': {
        'name': 'Aviation Job Search',
        'enabled': True,
        'base_url': 'https://www.aviationjobsearch.com',
        'jobs_url': 'https://www.aviationjobsearch.com/en-GB/jobs',
        'description': 'Aviation Job Search - comprehensive aviation job listings',
    },
    'goose': {
        'name': 'GOOSE Recruitment',
        'enabled': True,
        'base_url': 'https://www.goose-recruitment.com',
        'jobs_url': 'https://www.goose-recruitment.com/jobs',
        'description': 'GOOSE Recruitment - aviation and aerospace jobs',
    },
    # NOT WORKING YET - LinkedIn requires special handling and Ligin -- Have to configure scraper again to handle login credintials and cookies
    'linkedin': {
        'name': 'LinkedIn Jobs',
        'enabled': False,
        'base_url': 'https://www.linkedin.com',
        'search_url': 'https://www.linkedin.com/jobs/search/',
        # Multiple search terms and locations supported
        'default_post': ['flight dispatcher'],  # Can be string or list
        'default_location': ['Singapore','Australia','Brazil','United Kingdom','Germany','France','Canada'], # "'United States', 'United Arab Emirates', 'Qatar', 'Japan',"Top aviation hubs only - add more as needed
        'max_jobs_total': 100,  # Total jobs across all search combinations (optional)
        'description': 'LinkedIn job search - comprehensive job listings with multiple search terms',
    },
    'cargolux': {
        'name': 'Cargolux Careers (PeopleClick)',
        'enabled': True,
        'base_url': 'https://careers.peopleclick.eu.com',
        'jobs_url': 'https://careers.peopleclick.eu.com/careerscp/client_cargolux/external/results/searchResult.html',
        'description': 'Cargolux careers site (PeopleClick implementation)',
    },
    'airindia': {
        'name': 'Air India Careers',
        'enabled': True,
        'base_url': 'https://careers.airindia.com',
        'jobs_url': 'https://careers.airindia.com/sfcareer/search',
        'description': 'Air India careers site (SuccessFactors implementation)',
    },
    'jsfirm': {
        'name': 'JSFirm',
        'enabled': True,
        'base_url': 'https://www.jsfirm.com/',
        'jobs_url': 'https://www.jsfirm.com/jobs', # Assuming a jobs URL
        'description': 'JSFirm - Aviation jobs board',
    },
    'allflyingjobs': {
        'name': 'AllFlyingJobs',
        'enabled': True,
        'base_url': 'https://www.allflyingjobs.com',
        'jobs_url': 'https://www.allflyingjobs.com', 
        'description': 'AllFlyingJobs - Global aviation jobs search',
    },
    'aviationcv': {
        'name': 'AviationCV',
        'enabled': True,
        'base_url': 'https://www.aviationcv.com',
        'jobs_url': 'https://www.aviationcv.com/jobs',
        'description': 'AviationCV - Global aviation job board',
    },
    'emirates': {
        'name': 'Emirates Group Careers',
        'enabled': True,
        'base_url': 'https://www.emiratesgroupcareers.com',
        'description': 'Official career site for Emirates Group'
    },
    'boeing': {
        'name': 'Boeing Careers',
        'enabled': True,
        'base_url': 'https://jobs.boeing.com',
        'description': 'Boeing Career Site'
    },
    'airbus': {
        'name': 'Airbus Careers',
        'enabled': True,
        'base_url': 'https://ag.wd3.myworkdayjobs.com/Airbus',
        'api_url': 'https://ag.wd3.myworkdayjobs.com/wday/cxs/ag/Airbus/jobs',
        'description': 'Airbus Workday Career Site'
    },
    'pilots_global': {
        'name': 'PilotsGlobal',
        'enabled': True,
        'base_url': 'https://pilotsglobal.com',
        'description': 'PilotsGlobal Job Board'
    },
    'aisats': {
        'name': 'AISATS (Air India SATS)',
        'enabled': True,
        'base_url': 'https://www.aisats.in',
        'jobs_url': 'https://www.aisats.in/careers',
        'description': 'Air India SATS Airport Services career page'
    },
    'jmc': {
        'name': 'JMC Aviation',
        'enabled': True,
        'base_url': 'https://www.jmc-aviation.com',
        'jobs_url': 'https://www.jmc-aviation.com/jobs/',
        'description': 'Aviation recruitment specialist'
    },
    'iata': {
        'name': 'IATA',
        'enabled': True,
        'base_url': 'https://iata.csod.com',
        'jobs_url': 'https://iata.csod.com/ux/ats/careersite/1/home?c=iata',
        'description': 'International Air Transport Association'
    },
    'avianation': {
        'name': 'AviaNation',
        'enabled': True,
        'base_url': 'https://www.avianation.com',
        'jobs_url': 'https://www.avianation.com/',
        'description': 'Aviation jobs portal'
    },
    'wizzair': {
        'name': 'Wizz Air',
        'enabled': True,
        'base_url': 'https://careers.wizzair.com',
        'jobs_url': 'https://careers.wizzair.com/search/',
        'description': 'Wizz Air Careers'
    },
    'cpr': {
        'name': 'CPKC (Canadian Pacific)',
        'enabled': True,
        'base_url': 'https://careers.cpr.ca',
        'jobs_url': 'https://careers.cpr.ca/search/?q=&locationsearch=&skillsSearch=false&sortBy=date&pageNumber=0',
        'description': 'Canadian Pacific Kansas City Careers'
    },
    'nbaa': {
        'name': 'NBAA (National Business Aviation Association)',
        'enabled': True,
        'base_url': 'https://jobs.nbaa.org',
        'jobs_url': 'https://jobs.nbaa.org/jobs/',
        'description': 'NBAA Jobs'
    },
    'starair': {
        'name': 'Star Air',
        'enabled': True,
        'base_url': 'https://www.starair.in',
        'jobs_url': 'https://www.starair.in/careers',
        'description': 'Star Air careers page',
    },
    'lufthansa': {
        'name': 'Lufthansa Group',
        'enabled': True,
        'base_url': 'https://apply.lufthansagroup.careers',
        'description': 'Lufthansa Group careers portal',
    },
    'southwest': {
        'name': 'Southwest Airlines',
        'enabled': True,
        'base_url': 'https://careers.southwestair.com',
        'jobs_url': 'https://careers.southwestair.com/us/en/search-results',
        'description': 'Southwest Airlines careers (Phenom People)',
    },
    'ba': {
        'name': 'British Airways',
        'enabled': True,
        'base_url': 'https://careers.ba.com',
        'jobs_url': 'https://careers.ba.com/search-jobs',
        'description': 'British Airways careers portal',
    },
    'cathay': {
        'name': 'Cathay Pacific',
        'enabled': True,
        'base_url': 'https://careers.cathaypacific.com',
        'jobs_url': 'https://careers.cathaypacific.com/en/careers/jobs',
        'description': 'Cathay Pacific careers page',
    },
    'germanairways': {
        'name': 'German Airways',
        'enabled': True,
        'base_url': 'https://german-airways.jobs.personio.de',
        'description': 'German Airways (Personio) job board',
    },
    'aa': {
        'name': 'American Airlines',
        'enabled': False,  # Blocked by WAF
        'base_url': 'https://jobs.aa.com',
        'jobs_url': 'https://jobs.aa.com/search/',
        'description': 'American Airlines careers (Blocked by WAF)',
    },
    'etihad': {
        'name': 'Etihad Airways',
        'enabled': True,
        'base_url': 'https://careers.etihad.com',
        'jobs_url': 'https://careers.etihad.com/search/',
        'description': 'Etihad Airways careers portal',
    },
    'flydubai': {
        'name': 'Flydubai',
        'enabled': True,
        'base_url': 'https://careers.flydubai.com',
        'jobs_url': 'https://careers.flydubai.com/jobs',
        'description': 'Flydubai careers portal',
    },
    'airarabia': {
        'name': 'Air Arabia',
        'enabled': True,
        'base_url': 'https://jobs.airarabiagroupcareers.com',
        'jobs_url': 'https://jobs.airarabiagroupcareers.com/search/',
        'description': 'Air Arabia Group careers portal',
    },
    'airarabia_auh': {
        'name': 'Air Arabia Abu Dhabi',
        'enabled': True,
        'base_url': 'https://jobs.airarabiagroupcareers.com',
        # NOTE: location= parameter is silently ignored by this site.
        # Using q= keyword search for Abu Dhabi instead (verified via live browser test).
        'jobs_url': 'https://jobs.airarabiagroupcareers.com/search/?q=Abu+Dhabi',
        'description': 'Air Arabia Abu Dhabi roles (keyword search filter)',
    },
    'royaljet': {
        'name': 'Royal Jet',
        'enabled': True,
        'base_url': 'https://careerroyaljet.talentera.com',
        'jobs_url': 'https://careerroyaljet.talentera.com/en/job-search-results/',
        'description': 'Royal Jet careers portal (Talentera)',
    },
    'dubairaw': {
        'name': 'Dubai Royal Air Wing',
        'enabled': True,
        'base_url': 'https://careers.dubaiairports.ae',
        'jobs_url': 'https://careers.dubaiairports.ae/search-jobs',
        'description': 'Dubai Royal Air Wing (Recruitment via Dubai Airports)',
    },
    'abudhabiaviation': {
        'name': 'Abu Dhabi Aviation',
        'enabled': True,
        'base_url': 'https://ada.ae',
        'jobs_url': 'https://ada.ae/general-application/',
        'description': 'Abu Dhabi Aviation general application',
    },
    'falconaviation': {
        'name': 'Falcon Aviation Services',
        'enabled': True,
        'base_url': 'https://falconaviation.ae',
        'jobs_url': 'https://falconaviation.ae/careers',
        'description': 'Falcon Aviation Services careers',
    },
    'transavia': {
        'name': 'Transavia',
        'enabled': True,
        'base_url': 'https://werkenbijtransavia.com',
        'jobs_url': 'https://werkenbijtransavia.com/l/en/vacatures',
        'description': 'Transavia vacancy portal',
    },
    'zenon': {
        'name': 'Zenon Aviation Recruitment',
        'enabled': True,
        'base_url': 'https://www.zenon.aero',
        'jobs_url': 'https://www.zenon.aero/candidates/',
        'description': 'Zenon Aviation agency jobs',
    },
}

# Build complete config (used by scrapers)
CONFIG = {
    'scraper_settings': SCRAPER_SETTINGS,
    'scrapers': SCRAPERS,
    'sites': SITES,
}
