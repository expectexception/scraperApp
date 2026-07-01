# Running Scrapers Guide

Guide for running the newly added and fixed aviation job scrapers.

---

## 1. Commands to Run Scrapers

### **Run a Single Scraper**
Use the Django management command followed by the scraper name:
```bash
python manage.py run_scraper <scraper_name>
```

**Example:**
```bash
python manage.py run_scraper qantas
```

### **Run All Scrapers**
To run all registered scrapers sequentially:
```bash
python manage.py run_scraper all
```

---

## 2. List of Supported Scraper Names

Here are the exact names for the newly added and fixed scrapers:

| Scraper Name | Company Name | Description |
| :--- | :--- | :--- |
| `aaregional` | American Airlines Regional | Workday API |
| `transairhawaii` | Transair Hawaii | HTML scraping |
| `chevron` | Chevron | HTML scraping with fallback location |
| `virgingalactic` | Virgin Galactic | Phenom People API |
| `gmr` | Global Medical Response | iCIMS API |
| `magnificaair` | Magnifica Air | Oasis Recruiting HTML |
| `qantas` | Qantas | Playwright Firefox |
| `flyairshare` | FlyAirshare | Paycom API |
| `adp_fbb94cb3` | Surf Air Mobility | ADP WorkforceNow API |
| `mountain_air_cargo`| Mountain Air Cargo | HRMDirect HTML |
| `skywest` | SkyWest Airlines | HTML |
| `endeavor` | Endeavor Air | iCIMS Frame Scraping |
| `ameriflight` | Ameriflight | Paylocity HTML |
| `nationalairlines` | National Airlines | Paylocity HTML |
| `maersk` | Maersk | Workday API (WAF bypass) |
| `marabu` | Marabu Airlines | Workable API |

---

## 3. Filters and Exclusions

### **Auto-applied Filters**
All scrapers automatically load filters from the database/Mongo (or fallback to `filter_title.json`). Only jobs matching the operational keywords will be saved.

### **Logistics Hard-Block**
We have added a strict global exclusion pattern. Any job title containing the word **`logistics`** will be automatically skipped and rejected across all scrapers (e.g., *Logistics Operations Controller* is blocked).

---

## 4. Run Without Database (Testing Mode)
To test a scraper without saving results to the database, use the `--no-db` flag:
```bash
python manage.py run_scraper <scraper_name> --no-db
```
