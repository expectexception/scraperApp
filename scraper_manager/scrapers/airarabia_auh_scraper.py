"""
Air Arabia Abu Dhabi Careers Scraper
Extracts aviation job listings for Air Arabia Abu Dhabi
"""

from .airarabia_scraper import AirArabiaScraper

class AirArabiaAuhScraper(AirArabiaScraper):
    """Scraper for Air Arabia Abu Dhabi Careers"""

    def __init__(self, config, db_manager=None):
        # Initialize the parent class with the is_auh flag
        super().__init__(config, db_manager=db_manager, is_auh=True)
