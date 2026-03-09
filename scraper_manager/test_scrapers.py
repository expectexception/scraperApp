#!/usr/bin/env python
"""
Quick Test Script for Scraper Manager
Tests all scrapers to verify bug fixes
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, '/home/rajat/Desktop/AeroOps Intel/aeroScrap_backend/backendMain')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backendMain.settings')
django.setup()

from scraper_manager.config import CONFIG
from scraper_manager.scrapers import list_scrapers, get_scraper
from scraper_manager.db_manager import DjangoDBManager
import asyncio


async def test_scraper(scraper_name, max_jobs=5):
    """Test a single scraper"""
    print(f"\n{'='*70}")
    print(f"TESTING: {scraper_name}")
    print(f"{'='*70}\n")
    
    try:
        # Override max jobs for testing
        CONFIG['scrapers'][scraper_name]['max_jobs'] = max_jobs
        
        # Create DB manager
        db_manager = DjangoDBManager()
        
        # Get scraper instance
        scraper = get_scraper(scraper_name, CONFIG, db_manager=db_manager)
        
        # Run scraper
        jobs = await scraper.run()
        
        print(f"\n✅ {scraper_name} test PASSED")
        print(f"   Found {len(jobs)} jobs")
        
        if jobs:
            print(f"   Sample job: {jobs[0].get('title', 'N/A')}")
            if jobs[0].get('filter_match'):
                print(f"   Filter score: {jobs[0].get('filter_score', 0)}")
                print(f"   Category: {jobs[0].get('primary_category', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ {scraper_name} test FAILED")
        print(f"   Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_all_scrapers():
    """Test all enabled scrapers"""
    print("\n" + "="*70)
    print("SCRAPER MANAGER TEST SUITE")
    print("="*70)
    
    # Get enabled scrapers
    enabled_scrapers = [
        name for name, site in CONFIG['sites'].items()
        if site.get('enabled', False)
    ]
    
    print(f"\nTesting {len(enabled_scrapers)} enabled scrapers:")
    for name in enabled_scrapers:
        print(f"  • {name}")
    
    results = {}
    
    for scraper_name in enabled_scrapers:
        result = await test_scraper(scraper_name, max_jobs=5)
        results[scraper_name] = result
    
    # Summary
    print("\n" + "="*70)
    print("TEST RESULTS SUMMARY")
    print("="*70 + "\n")
    
    passed = sum(1 for r in results.values() if r)
    failed = len(results) - passed
    
    for scraper_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {scraper_name}")
    
    print(f"\nTotal: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("\n🎉 All tests passed!")
    else:
        print(f"\n⚠️  {failed} test(s) failed - check logs above")


async def test_filter_manager():
    """Test filter manager"""
    print("\n" + "="*70)
    print("TESTING FILTER MANAGER")
    print("="*70 + "\n")
    
    try:
        from scraper_manager.filter_manager import JobFilterManager
        
        filter_mgr = JobFilterManager('scraper_manager/filter_title.json')
        
        print(f"✅ Filter loaded successfully")
        print(f"   Total keywords: {len(filter_mgr.all_keywords)}")
        print(f"   Phrase keywords: {len(filter_mgr.phrase_keywords)}")
        print(f"   Single keywords: {len(filter_mgr.single_keywords)}")
        print(f"   Categories: {len(filter_mgr.filters)}")
        
        # Test with sample title
        test_title = "Flight Operations Officer - OCC"
        matches, categories, score, details = filter_mgr.matches_filter(test_title)
        
        print(f"\n   Test title: {test_title}")
        print(f"   Matches: {matches}")
        print(f"   Score: {score}")
        if matches:
            print(f"   Keywords: {', '.join(details.get('matched_keywords', []))}")
        
        return True
        
    except Exception as e:
        print(f"❌ Filter test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_database_integration():
    """Test database manager"""
    print("\n" + "="*70)
    print("TESTING DATABASE INTEGRATION")
    print("="*70 + "\n")
    
    try:
        from scraper_manager.db_manager import DjangoDBManager
        
        db_mgr = DjangoDBManager()
        
        # Test URL checking
        test_url = "https://example.com/test-job-123"
        is_scraped = await db_mgr.is_url_scraped(test_url)
        
        print(f"✅ Database manager initialized")
        print(f"   Test URL scraped check: {is_scraped}")
        
        # Test getting scraped URLs
        scraped_urls = await db_mgr.get_scraped_urls(source='linkedin')
        print(f"   LinkedIn scraped URLs: {len(scraped_urls)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Database test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main test runner"""
    print("\n🚀 Starting Scraper Manager Tests\n")
    
    # Test 1: Filter Manager
    filter_ok = await test_filter_manager()
    
    # Test 2: Database Integration
    db_ok = await test_database_integration()
    
    # Test 3: All Scrapers (only if user confirms)
    print("\n" + "="*70)
    response = input("Run full scraper tests? (y/n): ")
    if response.lower() == 'y':
        await test_all_scrapers()
    else:
        print("Skipping scraper tests")
    
    print("\n✅ Test suite completed\n")


if __name__ == '__main__':
    asyncio.run(main())
