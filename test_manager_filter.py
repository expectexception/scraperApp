import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'scraper_manager'))
from filter_manager import JobFilterManager

filter_manager = JobFilterManager("filter_title.json")
jobs = [
    {"title": "GENERAL MANAGER - PLANNING"},
    {"title": "GENERAL MANAGER/ VICE PRESIDENT, PROJECT MANAGEMEN"},
    {"title": "HIGH-LEVEL CONTROL MANAGER (BAGGAGE HANDLING SYSTE"},
    {"title": "ASSISTANT MANAGER/MANAGER, AIRPORT OPERATIONS DEVE"},
    {"title": "OCC Manager"}
]

matched, rejected, stats = filter_manager.filter_jobs(jobs)

print(f"Matched: {[j['title'] for j in matched]}")
print(f"Rejected: {[j['title'] for j in rejected]}")
