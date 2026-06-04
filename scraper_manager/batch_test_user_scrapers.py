import subprocess
import concurrent.futures
import re

scrapers = [
    "united",
    "aa",
    "delta",
    "southwest",
    "atlas_air",
    "fedex",
    "ups",
    "lufthansa",
    "ryanair",
    "ba",
    "easyjet",
    "airfrance",
    "klm",
]


def run_scraper(name):
    print(f"Testing {name}...")
    cmd = ["python3", "manage.py", "run_scraper", name, "--no-db", "--max-jobs", "3"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        output = result.stdout + result.stderr

        status = "Failed"
        if result.returncode == 0:
            status = "Success"
        if "Access Denied" in output or "WAF" in output or "blocked" in output.lower():
            status = "Blocked by WAF"

        # Parse output for stats
        # Look for "[name] Found X jobs on current page" or similar
        foundMatch = re.search(r"Found (\d+) jobs on current page", output)
        if not foundMatch:
            foundMatch = re.search(r"Found (\d+) jobs", output)

        matchedMatch = re.search(r"Matched \(will scrape\):\s+(\d+)", output)

        found = int(foundMatch.group(1)) if foundMatch else 0
        matched = int(matchedMatch.group(1)) if matchedMatch else 0

        if found == 0:
            if "Timeout" in output:
                status += " (Timeout/Blocked)"
            else:
                status += " (No Initial Jobs - LAYOUT LIKELY BROKEN)"
        else:
            status += f" (Layout OK! Found: {found}, Matched Filter: {matched})"

        return (
            f"{name}: {status}\nRAW OUTPUT EXTRACT:\n"
            + "\n".join(output.split("\n")[-20:])
            + "\n"
            + "=" * 40
        )
    except Exception as e:
        return f"{name}: Error - {e}"


results = []
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    futures = [executor.submit(run_scraper, name) for name in scrapers]
    for future in concurrent.futures.as_completed(futures):
        results.append(future.result())
        print(future.result())

with open("batch_test_results2.txt", "w") as f:
    f.write("\n".join(results))
