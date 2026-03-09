"""
Test scraper database integration
Verifies that scraped jobs appear in both ScrapedURL and Job models
"""
from django.core.management.base import BaseCommand
from django.db.models import Count
from scraper_manager.models import ScrapedURL, ScraperJob
from jobs.models import Job


class Command(BaseCommand):
    help = 'Test and verify scraper database integration'

    def handle(self, *args, **options):
        self.stdout.write("\n" + "="*70)
        self.stdout.write(self.style.SUCCESS("🔍 SCRAPER DATABASE INTEGRATION TEST"))
        self.stdout.write("="*70 + "\n")
        
        # Check ScrapedURL table
        scraped_count = ScrapedURL.objects.count()
        self.stdout.write(f"📋 ScrapedURL table: {scraped_count} records")
        
        if scraped_count > 0:
            by_source = ScrapedURL.objects.values('source').annotate(count=Count('id'))
            self.stdout.write("   Sources:")
            for item in by_source:
                self.stdout.write(f"   - {item['source']}: {item['count']} URLs")
        
        # Check Job table
        job_count = Job.objects.count()
        self.stdout.write(f"\n💼 Job table (main): {job_count} records")
        
        if job_count > 0:
            by_source = Job.objects.values('source').annotate(count=Count('id'))
            self.stdout.write("   Sources:")
            for item in by_source:
                source = item['source'] or 'Unknown'
                self.stdout.write(f"   - {source}: {item['count']} jobs")
        
        # Check ScraperJob executions
        scraper_jobs = ScraperJob.objects.count()
        self.stdout.write(f"\n🤖 ScraperJob executions: {scraper_jobs} total")
        
        if scraper_jobs > 0:
            completed = ScraperJob.objects.filter(status='completed').count()
            running = ScraperJob.objects.filter(status='running').count()
            failed = ScraperJob.objects.filter(status='failed').count()
            
            self.stdout.write(f"   ✅ Completed: {completed}")
            self.stdout.write(f"   ▶️  Running: {running}")
            self.stdout.write(f"   ❌ Failed: {failed}")
        
        # Verify linkage
        self.stdout.write("\n" + "="*70)
        self.stdout.write("🔗 LINKAGE VERIFICATION")
        self.stdout.write("="*70)
        
        # Check if URLs in ScrapedURL also exist in Job
        scraped_urls = set(ScrapedURL.objects.values_list('url', flat=True))
        job_urls = set(Job.objects.values_list('url', flat=True))
        
        in_both = scraped_urls & job_urls
        only_scraped = scraped_urls - job_urls
        only_jobs = job_urls - scraped_urls
        
        self.stdout.write(f"\n📊 URL Linkage:")
        self.stdout.write(f"   ✅ URLs in both tables: {len(in_both)}")
        self.stdout.write(f"   ⚠️  URLs only in ScrapedURL: {len(only_scraped)}")
        self.stdout.write(f"   ℹ️  URLs only in Job: {len(only_jobs)}")
        
        if only_scraped:
            self.stdout.write(f"\n   ⚠️  WARNING: {len(only_scraped)} scraped URLs not saved to Job table!")
            self.stdout.write("   This indicates the db_manager._save_to_jobs_model may have errors.")
            
            # Show sample
            sample = list(only_scraped)[:3]
            self.stdout.write("\n   Sample URLs not in Job table:")
            for url in sample:
                scraped = ScrapedURL.objects.filter(url=url).first()
                if scraped:
                    self.stdout.write(f"   - {scraped.title[:60]} ({scraped.source})")
        
        # Show recent jobs
        self.stdout.write("\n" + "="*70)
        self.stdout.write("📝 RECENT JOBS (Last 5)")
        self.stdout.write("="*70 + "\n")
        
        recent_jobs = Job.objects.order_by('-created_at')[:5]
        for job in recent_jobs:
            self.stdout.write(f"✈️  {job.title}")
            self.stdout.write(f"   Company: {job.company}")
            self.stdout.write(f"   Source: {job.source or 'Unknown'}")
            self.stdout.write(f"   Status: {job.status}")
            self.stdout.write(f"   Created: {job.created_at.strftime('%Y-%m-%d %H:%M')}")
            self.stdout.write("")
        
        # Summary
        self.stdout.write("="*70)
        if len(only_scraped) == 0 and scraped_count > 0:
            self.stdout.write(self.style.SUCCESS("✅ ALL SYSTEMS OPERATIONAL"))
            self.stdout.write(self.style.SUCCESS("   All scraped jobs are properly saved to Job table!"))
        elif scraped_count == 0:
            self.stdout.write(self.style.WARNING("⚠️  NO DATA YET"))
            self.stdout.write("   Run a scraper to test the integration.")
        else:
            self.stdout.write(self.style.ERROR("❌ INTEGRATION ISSUE DETECTED"))
            self.stdout.write("   Some scraped jobs are not appearing in the Job table.")
            self.stdout.write("   Check db_manager._save_to_jobs_model for errors.")
        
        self.stdout.write("="*70 + "\n")
