import os
import gzip
import json
import logging
from datetime import datetime
from pathlib import Path
from bson import json_util
from django.conf import settings
from pymongo import MongoClient

logger = logging.getLogger(__name__)

def get_mongo_client():
    mongodb_uri = os.environ.get("MONGODB_URI")
    if not mongodb_uri:
        raise ValueError("MONGODB_URI not found in environment")
    return MongoClient(mongodb_uri)

def get_db_name():
    return os.environ.get("MONGODB_NAME") or "aeroops_db"

def backup_collections(collection_names=None, backup_dir=None):
    """
    Backup specified collections to local storage.
    If collection_names is None, backup all collections in the database.
    """
    client = get_mongo_client()
    db_name = get_db_name()
    db = client[db_name]
    
    if not backup_dir:
        backup_dir = Path(settings.BASE_DIR) / "backups"
    
    backup_dir = Path(backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"backup_{timestamp}"
    backup_path.mkdir(parents=True, exist_ok=True)
    
    if not collection_names:
        collection_names = db.list_collection_names()
    
    results = []
    for coll_name in collection_names:
        try:
            coll = db[coll_name]
            file_path = backup_path / f"{coll_name}.json.gz"
            
            count = 0
            with gzip.open(file_path, 'wt', encoding='UTF-8') as f:
                for doc in coll.find():
                    f.write(json_util.dumps(doc) + '\n')
                    count += 1
            
            results.append({
                "collection": coll_name,
                "count": count,
                "file": str(file_path),
                "status": "success"
            })
        except Exception as e:
            logger.error(f"Failed to backup collection {coll_name}: {e}")
            results.append({
                "collection": coll_name,
                "error": str(e),
                "status": "failed"
            })
            
    return {
        "backup_id": f"backup_{timestamp}",
        "path": str(backup_path),
        "timestamp": timestamp,
        "results": results
    }

def restore_collection(file_path, collection_name=None, drop_existing=False):
    """
    Restore a collection from a gzipped JSON file.
    """
    client = get_mongo_client()
    db_name = get_db_name()
    db = client[db_name]
    
    file_path = Path(file_path)
    if not collection_name:
        collection_name = file_path.name.split('.')[0]
        
    coll = db[collection_name]
    
    if drop_existing:
        coll.drop()
        
    count = 0
    with gzip.open(file_path, 'rt', encoding='UTF-8') as f:
        batch = []
        for line in f:
            if line.strip():
                batch.append(json_util.loads(line))
                count += 1
                
                if len(batch) >= 1000:
                    coll.insert_many(batch)
                    batch = []
        
        if batch:
            coll.insert_many(batch)
            
    return {
        "collection": collection_name,
        "count": count,
        "status": "success"
    }

def list_local_backups(backup_dir=None):
    if not backup_dir:
        backup_dir = Path(settings.BASE_DIR) / "backups"
    
    backup_dir = Path(backup_dir)
    if not backup_dir.exists():
        return []
    
    backups = []
    for item in backup_dir.iterdir():
        if item.is_dir() and item.name.startswith("backup_"):
            # Calculate size
            total_size = sum(f.stat().st_size for f in item.glob('*.json.gz'))
            collections = [f.name.split('.')[0] for f in item.glob('*.json.gz')]
            
            backups.append({
                "id": item.name,
                "path": str(item),
                "timestamp": item.name.replace("backup_", ""),
                "size_bytes": total_size,
                "collections": collections
            })
            
    return sorted(backups, key=lambda x: x["timestamp"], reverse=True)
