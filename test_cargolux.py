import asyncio
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scraper_service.settings')
django.setup()

try:
    from scraper_manager.scrapers.cargolux_scraper import CargoluxScraper
    from scraper_manager.config import CONFIG
    from scraper_manager.db_manager import DjangoDBManager

    async def main():
        db = DjangoDBManager()
        scraper = CargoluxScraper(CONFIG, db_manager=db)
        jobs = await scraper.run()
        
        print(f"\nTotal jobs extracted: {len(jobs)}")
        for j in jobs[:5]:
            print(f"- {j.get('title')} ({j.get('location')}) - {j.get('url')}")

    if __name__ == "__main__":
        asyncio.run(main())
except ImportError:
    print("cargolux_scraper.py not found.")
