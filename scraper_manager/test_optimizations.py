"""
Comprehensive Test Suite for Scraper Manager
Tests all optimizations and improvements
"""

import sys
import os
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backendMain.settings')
django.setup()

import asyncio
import logging
from django.test import TestCase
from django.utils import timezone
from scraper_manager.models import ScraperJob, ScraperConfig, ScrapedURL
from scraper_manager.db_manager import DjangoDBManager
from jobs.models import Job

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ScraperManagerTests:
    """Test suite for scraper manager functionality"""
    
    def __init__(self):
        self.db_manager = DjangoDBManager()
        self.test_source = 'test_scraper'
        self.test_job_data = {
            'job_id': 'TEST123',
            'title': 'Test Aviation Job',
            'company': 'Test Airlines',
            'url': 'https://example.com/job/TEST123',
            'location': 'Test City',
            'description': 'This is a test job description',
            'source': self.test_source,
        }
    
    def cleanup(self):
        """Clean up test data"""
        logger.info("Cleaning up test data...")
        ScrapedURL.objects.filter(source=self.test_source).delete()
        Job.objects.filter(source=self.test_source).delete()
        ScraperJob.objects.filter(scraper_name=self.test_source).delete()
        logger.info("✓ Cleanup complete")
    
    async def test_url_deduplication(self):
        """Test 1: URL deduplication works correctly"""
        logger.info("\n" + "="*60)
        logger.info("TEST 1: URL Deduplication")
        logger.info("="*60)
        
        url = self.test_job_data['url']
        
        # First check - should not be scraped
        is_scraped_1 = await self.db_manager.is_url_scraped(url)
        assert not is_scraped_1, "URL should not be scraped initially"
        logger.info("✓ URL not in database initially")
        
        # Add job
        is_new, msg = self.db_manager.add_or_update_job(self.test_job_data, self.test_source)
        assert is_new, "First add should be new"
        logger.info("✓ Job added successfully")
        
        # Second check - should be scraped
        is_scraped_2 = await self.db_manager.is_url_scraped(url)
        assert is_scraped_2, "URL should be in database after adding"
        logger.info("✓ URL found in database after adding")
        
        # Try adding again
        is_new_2, msg_2 = self.db_manager.add_or_update_job(self.test_job_data, self.test_source)
        assert not is_new_2, "Second add should be update, not new"
        logger.info("✓ Duplicate correctly identified")
        
        # Check scrape count
        scraped_url = ScrapedURL.objects.get(url=url)
        assert scraped_url.scrape_count == 2, "Scrape count should be 2"
        logger.info(f"✓ Scrape count correctly incremented: {scraped_url.scrape_count}")
        
        logger.info("\n✅ TEST 1 PASSED: URL Deduplication works correctly\n")
    
    async def test_batch_operations(self):
        """Test 2: Batch job operations"""
        logger.info("\n" + "="*60)
        logger.info("TEST 2: Batch Operations")
        logger.info("="*60)
        
        # Create batch of jobs
        jobs = []
        for i in range(5):
            job = self.test_job_data.copy()
            job['job_id'] = f'TEST{i}'
            job['url'] = f'https://example.com/job/TEST{i}'
            job['title'] = f'Test Job {i}'
            jobs.append(job)
        
        logger.info(f"Created {len(jobs)} test jobs")
        
        # Add batch
        stats = await self.db_manager.add_jobs_batch(jobs, self.test_source)
        
        assert stats['total'] == 5, "Total should be 5"
        assert stats['new'] == 5, "All 5 should be new"
        assert stats['errors'] == 0, "No errors expected"
        logger.info(f"✓ Batch added: {stats}")
        
        # Add same batch again (should all be updates)
        stats_2 = await self.db_manager.add_jobs_batch(jobs, self.test_source)
        
        assert stats_2['new'] == 0, "None should be new"
        assert stats_2['updated'] == 5, "All 5 should be updates"
        logger.info(f"✓ Duplicate batch handled: {stats_2}")
        
        logger.info("\n✅ TEST 2 PASSED: Batch operations work correctly\n")
    
    def test_scraper_job_tracking(self):
        """Test 3: ScraperJob tracking"""
        logger.info("\n" + "="*60)
        logger.info("TEST 3: ScraperJob Tracking")
        logger.info("="*60)
        
        # Create job
        job = ScraperJob.objects.create(
            scraper_name=self.test_source,
            status='running',
            started_at=timezone.now(),
            triggered_by='test_script'
        )
        logger.info(f"✓ Created ScraperJob: {job.id}")
        
        # Update job
        job.status = 'completed'
        job.completed_at = timezone.now()
        job.jobs_found = 10
        job.jobs_new = 8
        job.jobs_updated = 2
        job.execution_time = 15.5
        job.save()
        logger.info(f"✓ Updated ScraperJob status to completed")
        
        # Verify duration calculation
        duration = job.duration
        assert duration is not None, "Duration should be calculated"
        logger.info(f"✓ Duration calculated: {duration:.2f}s")
        
        # Verify string representation
        str_repr = str(job)
        assert self.test_source in str_repr, "String repr should contain scraper name"
        logger.info(f"✓ String representation: {str_repr}")
        
        logger.info("\n✅ TEST 3 PASSED: ScraperJob tracking works correctly\n")
    
    def test_scraper_config(self):
        """Test 4: ScraperConfig functionality"""
        logger.info("\n" + "="*60)
        logger.info("TEST 4: ScraperConfig")
        logger.info("="*60)
        
        # Create or get config
        config, created = ScraperConfig.objects.get_or_create(
            scraper_name=self.test_source,
            defaults={
                'is_enabled': True,
                'max_jobs': 50,
                'max_pages': 10,
            }
        )
        logger.info(f"✓ ScraperConfig {'created' if created else 'retrieved'}: {config}")
        
        # Test update_stats
        initial_runs = config.total_runs
        config.update_stats(success=True)
        assert config.total_runs == initial_runs + 1, "Total runs should increment"
        assert config.successful_runs > 0, "Successful runs should increment"
        logger.info(f"✓ Stats updated: total={config.total_runs}, success={config.successful_runs}")
        
        # Test failure
        config.update_stats(success=False)
        assert config.failed_runs > 0, "Failed runs should increment"
        logger.info(f"✓ Failed run recorded: failed={config.failed_runs}")
        
        logger.info("\n✅ TEST 4 PASSED: ScraperConfig works correctly\n")
    
    async def test_filter_new_jobs(self):
        """Test 5: Filter new jobs functionality"""
        logger.info("\n" + "="*60)
        logger.info("TEST 5: Filter New Jobs")
        logger.info("="*60)
        
        # Add some jobs to database
        existing_jobs = []
        for i in range(3):
            job = self.test_job_data.copy()
            job['job_id'] = f'EXISTING{i}'
            job['url'] = f'https://example.com/job/EXISTING{i}'
            existing_jobs.append(job)
        
        await self.db_manager.add_jobs_batch(existing_jobs, self.test_source)
        logger.info(f"✓ Added {len(existing_jobs)} existing jobs to database")
        
        # Create mixed batch (some new, some existing)
        mixed_jobs = existing_jobs.copy()
        for i in range(3):
            job = self.test_job_data.copy()
            job['job_id'] = f'NEW{i}'
            job['url'] = f'https://example.com/job/NEW{i}'
            mixed_jobs.append(job)
        
        logger.info(f"Created mixed batch: {len(existing_jobs)} existing, 3 new")
        
        # Get scraped URLs
        scraped_urls = await self.db_manager.get_scraped_urls(source=self.test_source)
        logger.info(f"✓ Retrieved {len(scraped_urls)} scraped URLs from database")
        
        # Filter
        new_jobs = [job for job in mixed_jobs if job['url'] not in scraped_urls]
        duplicate_count = len(mixed_jobs) - len(new_jobs)
        
        assert len(new_jobs) == 3, "Should have 3 new jobs"
        assert duplicate_count == 3, "Should have 3 duplicates"
        logger.info(f"✓ Filtered correctly: {len(new_jobs)} new, {duplicate_count} duplicates")
        
        logger.info("\n✅ TEST 5 PASSED: Filter new jobs works correctly\n")
    
    def test_database_statistics(self):
        """Test 6: Database statistics"""
        logger.info("\n" + "="*60)
        logger.info("TEST 6: Database Statistics")
        logger.info("="*60)
        
        stats = self.db_manager.get_statistics()
        
        assert 'total_jobs' in stats, "Stats should have total_jobs"
        assert 'jobs_by_source' in stats, "Stats should have jobs_by_source"
        assert isinstance(stats['total_jobs'], int), "total_jobs should be int"
        
        logger.info(f"✓ Total jobs in database: {stats['total_jobs']}")
        logger.info(f"✓ Jobs by source: {stats['jobs_by_source']}")
        logger.info(f"✓ Recent scrapes: {len(stats['recent_scrapes'])}")
        
        logger.info("\n✅ TEST 6 PASSED: Database statistics work correctly\n")
    
    async def run_all_tests(self):
        """Run all tests"""
        logger.info("\n" + "="*60)
        logger.info("STARTING SCRAPER MANAGER TEST SUITE")
        logger.info("="*60 + "\n")
        
        try:
            # Clean up before tests
            self.cleanup()
            
            # Run tests
            await self.test_url_deduplication()
            await self.test_batch_operations()
            self.test_scraper_job_tracking()
            self.test_scraper_config()
            await self.test_filter_new_jobs()
            self.test_database_statistics()
            
            # Summary
            logger.info("\n" + "="*60)
            logger.info("🎉 ALL TESTS PASSED! 🎉")
            logger.info("="*60)
            logger.info("\nSummary:")
            logger.info("  ✅ URL Deduplication")
            logger.info("  ✅ Batch Operations")
            logger.info("  ✅ ScraperJob Tracking")
            logger.info("  ✅ ScraperConfig")
            logger.info("  ✅ Filter New Jobs")
            logger.info("  ✅ Database Statistics")
            logger.info("\nAll scraper manager optimizations verified!")
            
        except AssertionError as e:
            logger.error(f"\n❌ TEST FAILED: {e}")
            raise
        except Exception as e:
            logger.error(f"\n❌ UNEXPECTED ERROR: {e}", exc_info=True)
            raise
        finally:
            # Clean up after tests
            logger.info("\nCleaning up test data...")
            self.cleanup()
            logger.info("Done!")


def main():
    """Main entry point"""
    tests = ScraperManagerTests()
    asyncio.run(tests.run_all_tests())


if __name__ == '__main__':
    main()


