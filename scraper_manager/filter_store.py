"""Mongo-backed store for the job title filter configuration.

The web admin edits scrape filter categories (keywords, negative keywords and an
on/off flag) and saves them into the shared Mongo collection
``admin_scrape_filter_configs`` (written by the main backend). The scraper reads
that collection here so admin changes take effect on the next run, falling back
to ``filter_title.json`` when Mongo has no config yet.
"""

import os
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

SCRAPE_FILTER_KEY = "scrape_filter_config"
_COLLECTION = "admin_scrape_filter_configs"


def _get_mongo_db():
    uri = os.environ.get("MONGODB_URI") or os.environ.get("MONGO_URI")
    name = os.environ.get("MONGODB_NAME") or os.environ.get("DB_NAME") or "aeroops_db"
    if not uri:
        return None
    try:
        from pymongo import MongoClient

        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        return client[name]
    except Exception as exc:  # pragma: no cover - network/driver issues
        logger.warning("Mongo filter store unavailable: %s", exc)
        return None


def load_filter_config_from_mongo() -> Optional[Dict[str, Any]]:
    """Return the admin-managed filter config dict, or None if unavailable/empty."""
    db = _get_mongo_db()
    if db is None:
        return None
    try:
        doc = db[_COLLECTION].find_one({"key": SCRAPE_FILTER_KEY})
    except Exception as exc:  # pragma: no cover
        logger.warning("Failed reading scrape filter config from Mongo: %s", exc)
        return None
    if not doc or not doc.get("config"):
        return None
    return doc["config"]


def seed_filter_config_to_mongo(config: Dict[str, Any]) -> bool:
    """Insert the config if none exists yet. Never overwrites admin edits."""
    db = _get_mongo_db()
    if db is None:
        return False
    try:
        now = datetime.now(timezone.utc)
        db[_COLLECTION].update_one(
            {"key": SCRAPE_FILTER_KEY},
            {
                "$setOnInsert": {
                    "key": SCRAPE_FILTER_KEY,
                    "config": config,
                    "version": 1,
                    "created_at": now,
                    "updated_at": now,
                    "updated_by": {"id": "system", "username": "scraper-seed"},
                }
            },
            upsert=True,
        )
        return True
    except Exception as exc:  # pragma: no cover
        logger.warning("Failed seeding scrape filter config to Mongo: %s", exc)
        return False
