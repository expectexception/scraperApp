import subprocess
import concurrent.futures
import os

scrapers = [
    "absjets", "aegean", "airfrance", "airfrancehop", "aena", "aireuropaexpress", "airmalta", "airserbia", "alsieexpress", "amapolaflyg", "aslairlinesbelgium", "austrianairlines", "blueislands", "braathens", "bristow", "brusselsairlines", "buraqair", "buzz", "cabotaviation", "signature", "flygosh", "aviationindeed", "aap", "indigo", "aviationjobsearch", "goose", "linkedin", "cargolux", "airindia", "jsfirm", "allflyingjobs", "emirates", "boeing", "airbus", "pilots_global", "aviationcv", "zenon", "aaae", "aisats", "jmc", "iata", "avianation", "wizzair", "cpr", "nbaa", "starair", "lufthansa", "southwest", "ba", "capitalairlines", "carpatair", "dat", "edelweiss", "egyptair", "elal", "ethiopian", "eurowings", "finnair", "flybe", "hahnair", "iberia", "iberiaexpress", "icelandair", "itaairways", "klm", "lot", "lufthansacityline", "norwegian", "olympicair", "ryanair", "sas", "smartwings", "swiss", "tap", "transavia", "tuiairways", "vueling", "aerlingus", "airbaltic", "airdolomiti", "airnostrum", "easternairways", "easyjet", "cathay", "germanairways", "aa", "etihad", "flydubai", "airarabia", "airarabia_auh", "royaljet", "dubairaw", "abudhabiaviation", "falconaviation"
]

os.makedirs('scraper_logs', exist_ok=True)

def test_scraper(scraper):
    try:
        # Run the scraper, capturing output, with a timeout of 180 seconds to prevent hanging
        process = subprocess.run(
            ['python3', 'manage.py', 'run_scraper', scraper], 
            capture_output=True, 
            text=True, 
            timeout=180
        )
        
        with open(f"scraper_logs/{scraper}.log", "w") as f:
            f.write(process.stdout)
            f.write("\n--- STDERR ---\n")
            f.write(process.stderr)

        if process.returncode == 0:
            print(f"✓ {scraper} succeeded")
            return (scraper, "Success")
        else:
            # Check if there's a specific error in output
            if "Target page, context or browser has been closed" in process.stderr:
                return (scraper, "Failed (Browser Closed Early)")
            print(f"✗ {scraper} failed (Exit code {process.returncode})")
            return (scraper, "Failed")
            
    except subprocess.TimeoutExpired as e:
        print(f"⏱️ {scraper} timed out")
        with open(f"scraper_logs/{scraper}.log", "w") as f:
            f.write(e.stdout.decode('utf-8', errors='ignore') if e.stdout else "")
            f.write("\n--- TIMEOUT ---\n")
            f.write(e.stderr.decode('utf-8', errors='ignore') if e.stderr else "")
        return (scraper, "Timeout")
    except Exception as e:
        print(f"❌ {scraper} error: {e}")
        return (scraper, f"Error: {e}")

def main():
    print(f"Starting test of {len(scrapers)} scrapers...")
    results = []
    
    # Run scrapers in parallel to save time. 
    # Use 3 workers so we don't overwhelm playwright or the CPU, but still fast.
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        future_to_scraper = {executor.submit(test_scraper, s): s for s in scrapers}
        for future in concurrent.futures.as_completed(future_to_scraper):
            res = future.result()
            results.append(res)
            
    with open('scraper_test_results.md', 'w') as f:
        f.write("# Scraper Test Results\n\n")
        f.write("| Scraper | Status |\n|---|---|\n")
        # Sort results alphabetically
        results.sort(key=lambda x: x[0])
        for s, res in results:
            f.write(f"| {s} | {res} |\n")
            
    print("\nAll tests completed! Results saved to scraper_test_results.md")

if __name__ == '__main__':
    main()
