import os
import subprocess
import sys
import json
import re
import argparse
from datetime import datetime

# Adjust paths
PROJECT_ROOT = "/home/rajat/Desktop/AeroOps Intel/scraper-standalone"
PYTHON_BIN = "/home/rajat/Desktop/AeroOps Intel/.venv/bin/python3"
BRAIN_DIR = "/home/rajat/.gemini/antigravity/brain/5c3b8d65-cfee-40a3-8ebc-1213b705bf58"
REPORT_FILE = os.path.join(BRAIN_DIR, "scraper_test_results.md")
JSON_RESULTS = os.path.join(BRAIN_DIR, "scraper_test_results.json")

def get_enabled_scrapers():
    """Extract enabled scrapers from config.py using regex to avoid Django dependency here"""
    config_path = os.path.join(PROJECT_ROOT, "scraper_manager/config.py")
    with open(config_path, 'r') as f:
        content = f.read()
    
    sites = {}
    matches = re.finditer(r"'([a-zA-Z0-9_]+)':\s*\{", content)
    for match in matches:
        key = match.group(1)
        start = match.end()
        end = content.find('},', start)
        if end == -1: end = len(content)
        
        block = content[start:end]
        if "'enabled': True" in block:
            sites[key] = True
            
    scrapers = sorted(list(sites.keys()))
    excluded_keys = {'run_all_scrapers', 'run_priority_scrapers', 'run_specialty_scrapers', 'cleanup_old_jobs', 'generate_report'}
    return [s for s in scrapers if s not in excluded_keys]

def run_test(scraper_name):
    print(f"Testing {scraper_name}...")
    try:
        cmd = [
            PYTHON_BIN, "manage.py", "run_scraper", scraper_name, 
            "--no-db", "--max-jobs", "20"
        ]
        result = subprocess.run(
            cmd, cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=120
        )
        
        output = result.stdout + result.stderr
        
        # Parse output for stats
        # SuccessFactors/Advanced Filtering style: Matched (will scrape): 5
        matchedMatch = re.search(r"Matched \(will scrape\):\s+(\d+)", output)
        
        # Summary style: Jobs found: 10
        foundMatch = re.search(r"Jobs found:\s+(\d+)", output)
        
        matched = int(matchedMatch.group(1)) if matchedMatch else 0
        found = int(foundMatch.group(1)) if foundMatch else 0
        
        # In no-db mode, found is the final result.
        # If matched > 0, we definitely found something.
        
        status = "Success" if result.returncode == 0 else "Failed"
        error = "" if result.returncode == 0 else output[-500:].strip()
        
        if "Access Denied" in output or "Attention Required" in output:
             status = "Blocked"
             
        return {
            "name": scraper_name,
            "status": status,
            "found": found,
            "matched": matched,
            "error": error
        }
    except subprocess.TimeoutExpired:
        return {
            "name": scraper_name,
            "status": "Timeout",
            "found": 0,
            "matched": 0,
            "error": "Timed out after 120s"
        }
    except Exception as e:
        return {
            "name": scraper_name,
            "status": "Error",
            "found": 0,
            "matched": 0,
            "error": str(e)
        }

def generate_report(results):
    with open(REPORT_FILE, 'w') as f:
        f.write("# Scraper Test Results (Consolidated)\n\n")
        f.write(f"Total enabled scrapers: {len(get_enabled_scrapers())}\n")
        f.write(f"Tested so far: {len(results)}\n\n")
        f.write("| Scraper | Status | Found | Matched | Notes |\n")
        f.write("|---------|--------|-------|---------|-------|\n")
        for r in sorted(results, key=lambda x: x['name']):
            notes = r['error'].replace('\n', ' ')[:50] if r['status'] not in ["Success", "Blocked"] else ""
            if r['status'] == "Blocked": notes = "WAF Blocked"
            f.write(f"| {r['name']} | {r['status']} | {r['found']} | {r['matched']} | {notes} |\n")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--end", type=int, default=10)
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()

    scrapers = get_enabled_scrapers()
    
    # Load existing results
    all_results = []
    if os.path.exists(JSON_RESULTS):
        with open(JSON_RESULTS, 'r') as f:
            all_results = json.load(f)
    
    existing_names = {r['name'] for r in all_results}
    
    if args.all:
        target_scrapers = scrapers
    else:
        target_scrapers = scrapers[args.start:args.end]
        
    print(f"Testing {len(target_scrapers)} scrapers from index {args.start} to {args.end}...")
    
    for i, name in enumerate(target_scrapers):
        print(f"[{i+1}/{len(target_scrapers)}] testing {name}...")
        res = run_test(name)
        
        # Update or add
        updated = False
        for j, existing in enumerate(all_results):
            if existing['name'] == name:
                all_results[j] = res
                updated = True
                break
        if not updated:
            all_results.append(res)
            
        # Save JSON after each test to avoid loss
        with open(JSON_RESULTS, 'w') as f:
            json.dump(all_results, f, indent=2)
            
    generate_report(all_results)
    print(f"Report updated at {REPORT_FILE}")

if __name__ == "__main__":
    main()
