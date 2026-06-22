"""Audit reachability of every ENABLED scraper's URL.

Checks jobs_url, falling back to api_url then base_url. Uses curl_cffi with
TLS impersonation + a hard timeout so a hung host can't stall the run.
Writes a report to audit_url_report.txt and prints a summary.
"""
import concurrent.futures as cf
import importlib.util
import time

from curl_cffi import requests as cr

TIMEOUT = 20
WORKERS = 16
IMPERSONATE = "chrome120"

spec = importlib.util.spec_from_file_location("cfg", "scraper_manager/config.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
CONFIG = m.CONFIG
sites = CONFIG["sites"]
scrapers = CONFIG["scrapers"]

enabled = []
for name in sorted(set(list(sites) + list(scrapers))):
    sc = scrapers.get(name, {})
    si = sites.get(name, {})
    if sc.get("enabled", si.get("enabled", False)):
        enabled.append(name)


def pick_url(name):
    si = sites.get(name, {})
    return si.get("jobs_url") or si.get("api_url") or si.get("base_url"), (
        "jobs_url" if si.get("jobs_url") else "api_url" if si.get("api_url") else "base_url"
    )


def check(name):
    url, kind = pick_url(name)
    if not url:
        return name, kind, None, "NO_URL", None
    t0 = time.time()
    try:
        r = cr.get(url, timeout=TIMEOUT, impersonate=IMPERSONATE, allow_redirects=True)
        dt = time.time() - t0
        return name, kind, r.status_code, "OK" if r.status_code < 400 else "HTTP_ERR", round(dt, 1)
    except Exception as e:
        return name, kind, None, type(e).__name__, round(time.time() - t0, 1)


def main():
    rows = []
    with cf.ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for res in ex.map(check, enabled):
            rows.append(res)
            name, kind, code, verdict, dt = res
            print(f"{verdict:14} {str(code):4} {name:32} {kind:8} {dt}")

    bad = [r for r in rows if r[3] not in ("OK",)]
    lines = []
    lines.append(f"ENABLED scrapers checked: {len(rows)}")
    lines.append(f"OK: {len(rows) - len(bad)}   PROBLEM: {len(bad)}\n")
    lines.append("=== PROBLEMS (need attention) ===")
    for name, kind, code, verdict, dt in sorted(bad, key=lambda x: x[3]):
        url, _ = pick_url(name)
        lines.append(f"{verdict:16} code={code} {name}  [{kind}] {url}")
    report = "\n".join(lines)
    with open("audit_url_report.txt", "w") as f:
        f.write(report + "\n")
    print("\n" + report)


if __name__ == "__main__":
    main()
