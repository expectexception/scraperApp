import sys
import os
# Add the scraper_manager directory to path so it can find things
sys.path.append(os.path.join(os.getcwd(), 'scraper_manager'))

from filter_manager import JobFilterManager

# Initialize with explicit path to ensure it works
filter_manager = JobFilterManager("filter_title.json")
jobs = [
    {"title": "HR Manager"},
    {"title": "Human Resources Coordinator"},
    {"title": "Flight Operations Officer"},
    {"title": "HR Business Partner"},
    {"title": "Agent technique d'exploitation"}
]

matched, rejected, stats = filter_manager.filter_jobs(jobs)

print(f"Matched: {[j['title'] for j in matched]}")
print(f"Rejected: {[j['title'] for j in rejected]}")
