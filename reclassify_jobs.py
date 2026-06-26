import os
from pymongo import MongoClient
from scraper_manager.category_taxonomy import infer_job_category

mongo_uri = "mongodb+srv://ifoa:rajatrathee@ifoa.figv3ri.mongodb.net/"
client = MongoClient(mongo_uri)

for db_name in ["aeroops_db", "aeroops_test_db"]:
    print(f"\n==================================================")
    print(f"Processing Database: {db_name}")
    print(f"==================================================")
    
    db = client[db_name]
    jobs_col = db["jobs"]
    scraped_col = db["scraper_manager_scrapedurl"]
    
    # 1. Delete Sales Manager jobs
    deleted_jobs = jobs_col.delete_many({"title": {"$regex": "Sales Manager", "$options": "i"}})
    deleted_scraped = scraped_col.delete_many({"title": {"$regex": "Sales Manager", "$options": "i"}})
    print(f"Deleted {deleted_jobs.deleted_count} jobs and {deleted_scraped.deleted_count} scraped URLs containing 'Sales Manager'")
    
    # 2. Reclassify remaining jobs
    jobs = list(jobs_col.find({}))
    print(f"Loaded {len(jobs)} jobs for reclassification.")
    reclassified_count = 0
    
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
            print(f"Job: '{job.get('title')}' | Company: '{job.get('company')}'")
            print(f"  Old: {old_cat} -> New: {new_cat}")
            jobs_col.update_one(
                {"_id": job["_id"]},
                {"$set": {"job_category": new_cat, "category": new_cat}}
            )
            # Also update the scraped url model if it exists
            scraped_col.update_many(
                {"title": job.get("title"), "company": job.get("company")},
                {"$set": {"job_category": new_cat, "category": new_cat}}
            )
            reclassified_count += 1
            
    print(f"Reclassification complete for {db_name}! Total reclassified: {reclassified_count}")
