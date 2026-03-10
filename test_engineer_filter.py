import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'scraper_manager'))
from filter_manager import JobFilterManager

filter_manager = JobFilterManager("filter_title.json")
jobs = [
    {"title": "Aerospace Manufacturing Engineer"},
    {"title": "HR Manager"},
    {"title": "Maintenance Control Engineer"},
    {"title": "Flight Operations Officer"}
]

matched, rejected, stats = filter_manager.filter_jobs(jobs)

print(f"Matched: {[j['title'] for j in matched]}")
print(f"Rejected: {[j['title'] for j in rejected]}")
