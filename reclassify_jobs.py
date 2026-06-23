import os
from pymongo import MongoClient
from scraper_manager.category_taxonomy import infer_job_category

mongo_uri = "mongodb+srv://ifoa:rajatrathee@ifoa.figv3ri.mongodb.net/"
client = MongoClient(mongo_uri)
db = client["aeroops_db"]
jobs_col = db["jobs"]

print("Reclassifying jobs in database with correct metadata...")
reclassified_count = 0

jobs = list(jobs_col.find({}))
print(f"Loaded {len(jobs)} jobs.")

for job in jobs:
    old_cat = job.get("job_category") or job.get("category")
    job_data = job.get("job_data", {})
    if not isinstance(job_data, dict):
        job_data = {}
    
    new_cat = infer_job_category(
        title=job.get("title", ""),
        description=job.get("description", ""),
        primary_category=job_data.get("primary_category"),
        matched_categories=job_data.get("matched_categories"),
        matched_filter_types=job_data.get("matched_filter_types"),
        existing_category=job_data.get("job_category"),
        source=job.get("source", ""),
        company=job.get("company", "")
    )
    
    if old_cat != new_cat:
        print(f"Job: '{job.get('title')}' | Company: '{job.get('company')}' | Source: '{job.get('source')}'")
        print(f"  Old: {old_cat} -> New: {new_cat}")
        jobs_col.update_one(
            {"_id": job["_id"]},
            {"$set": {"job_category": new_cat, "category": new_cat}}
        )
        reclassified_count += 1

print(f"Reclassification complete! Total reclassified: {reclassified_count}")
