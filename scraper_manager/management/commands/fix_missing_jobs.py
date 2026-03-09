"""
Fix missing jobs - sync ScrapedURL to Job table
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from scraper_manager.models import ScrapedURL
from scraper_manager.db_manager import DjangoDBManager
from jobs.models import Job


class Command(BaseCommand):
    help = 'Sync all ScrapedURL records to Job table (fix missing jobs)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without actually doing it',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        self.stdout.write("\n" + "="*70)
        self.stdout.write(self.style.SUCCESS("🔧 FIXING MISSING JOBS"))
        self.stdout.write("="*70 + "\n")
        
        # Find URLs only in ScrapedURL
        scraped_urls = set(ScrapedURL.objects.values_list('url', flat=True))
        job_urls = set(Job.objects.values_list('url', flat=True))
        missing_urls = scraped_urls - job_urls
        
        self.stdout.write(f"📊 Status:")
        self.stdout.write(f"   - ScrapedURL records: {len(scraped_urls)}")
        self.stdout.write(f"   - Job records: {len(job_urls)}")
        self.stdout.write(f"   - Missing in Job table: {len(missing_urls)}")
        
        if not missing_urls:
            self.stdout.write(self.style.SUCCESS("\n✅ No missing jobs - everything is in sync!"))
            return
        
        if dry_run:
            self.stdout.write(self.style.WARNING(f"\n🔍 DRY RUN MODE - showing first 10 missing jobs:"))
            for url in list(missing_urls)[:10]:
                scraped = ScrapedURL.objects.get(url=url)
                self.stdout.write(f"\n   📋 {scraped.title[:60]}")
                self.stdout.write(f"      Company: {scraped.company or 'Unknown'}")
                self.stdout.write(f"      Source: {scraped.source}")
            
            self.stdout.write(f"\n💡 Run without --dry-run to fix these {len(missing_urls)} jobs")
            return
        
        # Fix missing jobs
        self.stdout.write(f"\n🔄 Syncing {len(missing_urls)} missing jobs to Job table...")
        
        db_manager = DjangoDBManager()
        success_count = 0
        error_count = 0
        
        for url in missing_urls:
            try:
                scraped = ScrapedURL.objects.get(url=url)
                
                with transaction.atomic():
                    job, created = db_manager._save_to_jobs_model(
                        scraped.job_data, 
                        scraped.source
                    )
                    
                    if job:
                        success_count += 1
                        if success_count <= 5:  # Show first 5
                            self.stdout.write(
                                f"   ✅ {scraped.title[:50]} - {scraped.company or 'Unknown'}"
                            )
                    else:
                        error_count += 1
                        self.stdout.write(
                            self.style.ERROR(f"   ❌ Failed: {scraped.title[:50]}")
                        )
                        
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f"   ❌ Error processing {url[:50]}: {e}")
                )
        
        # Summary
        self.stdout.write("\n" + "="*70)
        self.stdout.write("📊 SYNC COMPLETE")
        self.stdout.write("="*70)
        self.stdout.write(f"   ✅ Successfully synced: {success_count}")
        self.stdout.write(f"   ❌ Errors: {error_count}")
        
        # Verify
        scraped_urls_after = set(ScrapedURL.objects.values_list('url', flat=True))
        job_urls_after = set(Job.objects.values_list('url', flat=True))
        still_missing = scraped_urls_after - job_urls_after
        
        if len(still_missing) == 0:
            self.stdout.write(self.style.SUCCESS("\n🎉 ALL JOBS SYNCED SUCCESSFULLY!"))
        else:
            self.stdout.write(
                self.style.WARNING(f"\n⚠️  {len(still_missing)} jobs still missing (errors occurred)")
            )
        
        self.stdout.write("="*70 + "\n")
