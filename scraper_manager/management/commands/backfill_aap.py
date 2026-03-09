from django.core.management.base import BaseCommand
from django.db import transaction
from django.db import models
from jobs.models import Job
from scraper_manager.scrapers.aap_aviation_scraper import AAPAviationScraper
import asyncio
import logging
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Backfill missing location and posted_date for AAP jobs by re-fetching job pages'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=0, help='Limit number of jobs to process (0 = all)')
        parser.add_argument('--dry-run', action='store_true', help='Do not save changes, just report')

    def handle(self, *args, **options):
        limit = options.get('limit', 0)
        dry = options.get('dry_run', False)

        # Get AAP jobs that need updating (missing location or posted_date)
        qs = Job.objects.filter(source='aap')

        # Filter for jobs that need updates
        jobs_needing_update = []
        for job in qs:
            needs_update = (
                not job.location or
                job.location == '' or
                job.location == 'Unknown' or
                not job.posted_date
            )
            if needs_update:
                jobs_needing_update.append(job)

        if limit and limit > 0:
            jobs_needing_update = jobs_needing_update[:limit]

        jobs = jobs_needing_update
        total = len(jobs)

        if not jobs:
            self.stdout.write(self.style.SUCCESS('No AAP jobs need backfilling.'))
            return

        self.stdout.write(f'Processing {total} AAP jobs (dry_run={dry})...')

        # Create scraper instance
        from scraper_manager.config import SCRAPER_SETTINGS
        config = {
            'sites': {
                'aap': {
                    'name': 'AAP Aviation',
                    'base_url': 'https://jobs.aapaviation.com',
                    'jobs_url': 'https://jobs.aapaviation.com/jobs',
                    'description': 'AAP Aviation careers site'
                }
            },
            **SCRAPER_SETTINGS
        }

        scraper = AAPAviationScraper(config)

        async def process_jobs():
            updated_count = 0
            error_count = 0

            for i, job in enumerate(jobs):
                try:
                    self.stdout.write(f'[{i+1}/{total}] Processing: {job.title[:50]}...')

                    # Create job dict for processing
                    job_dict = {
                        'job_id': f"aap_{job.id}",
                        'title': job.title,
                        'company': job.company,
                        'source': job.source,
                        'url': job.url,
                        'apply_url': job.url,
                        'location': job.location or '',
                        'job_type': job.operation_type or '',
                        'department': '',
                        'posted_date': str(job.posted_date) if job.posted_date else '',
                        'closing_date': '',
                        'timestamp': job.created_at.isoformat(),
                        'description': job.description or '',
                        'requirements': '',
                        'qualifications': '',
                    }

                    # Extract description and additional fields
                    jobs_with_updates = await scraper.fetch_job_descriptions([job_dict])

                    if jobs_with_updates and len(jobs_with_updates) > 0:
                        updated_job = jobs_with_updates[0]

                        # Check what changed
                        changes = []
                        if updated_job.get('location') and updated_job['location'] != job.location:
                            changes.append(f"location: '{job.location}' -> '{updated_job['location']}'")
                        if updated_job.get('posted_date') and str(updated_job['posted_date']) != str(job.posted_date):
                            changes.append(f"posted_date: '{job.posted_date}' -> '{updated_job['posted_date']}'")
                        if updated_job.get('description') and len(updated_job['description']) > len(job.description or ''):
                            changes.append(f"description: {len(job.description or '')} -> {len(updated_job['description'])} chars")

                        if changes:
                            self.stdout.write(f'  ✓ Updated: {", ".join(changes)}')

                            if not dry:
                                # Update the job in database (async-safe)
                                await sync_to_async(self._update_job)(job, updated_job)
                                updated_count += 1
                        else:
                            self.stdout.write('  - No changes needed')
                    else:
                        self.stdout.write('  ✗ Failed to fetch updates')
                        error_count += 1

                except Exception as e:
                    self.stdout.write(f'  ✗ Error: {e}')
                    error_count += 1
                    continue

            return updated_count, error_count

        # Run the async processing
        try:
            updated, errors = asyncio.run(process_jobs())

            if dry:
                self.stdout.write(self.style.SUCCESS(f'DRY RUN: Would update {updated} jobs, {errors} errors'))
            else:
                self.stdout.write(self.style.SUCCESS(f'Updated {updated} AAP jobs, {errors} errors'))

        except Exception as e:
            self.stderr.write(f'Error during processing: {e}')

    def _update_job(self, job, updated_job):
        """Update job in database (sync function)"""
        job.location = updated_job.get('location') or job.location
        job.posted_date = updated_job.get('posted_date') or job.posted_date
        if updated_job.get('description') and len(updated_job['description']) > len(job.description or ''):
            job.description = updated_job['description']
        job.save()