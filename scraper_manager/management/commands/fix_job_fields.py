"""
Management command to fix missing fields in existing jobs
"""
from django.core.management.base import BaseCommand
from django.db.models import Q
from jobs.models import Job
from scraper_manager.db_manager import DjangoDBManager


class Command(BaseCommand):
    help = 'Fix missing country_code, operation_type, and status fields in existing jobs'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limit number of jobs to process',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        limit = options['limit']
        
        self.stdout.write(self.style.SUCCESS('Starting job field fix...'))
        
        # Initialize db_manager for helper methods
        db_manager = DjangoDBManager()
        
        # Find jobs with missing fields or wrong status
        jobs_to_fix = Job.objects.filter(
            Q(country_code__isnull=True) | 
            Q(operation_type__isnull=True) |
            Q(status='new')
        ).select_related()
        
        if limit:
            jobs_to_fix = jobs_to_fix[:limit]
        
        total = jobs_to_fix.count()
        self.stdout.write(f'Found {total} jobs to fix')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        stats = {
            'status_fixed': 0,
            'country_added': 0,
            'operation_added': 0,
            'no_changes': 0,
        }
        
        for i, job in enumerate(jobs_to_fix, 1):
            changed = False
            changes = []
            
            # Fix status
            if job.status == 'new':
                if not dry_run:
                    job.status = 'active'
                changed = True
                changes.append('status: new→active')
                stats['status_fixed'] += 1
            
            # Extract country code if missing
            if not job.country_code and job.location:
                country_code = db_manager._extract_country_code(job.location, job.company)
                if country_code:
                    if not dry_run:
                        job.country_code = country_code
                    changed = True
                    changes.append(f'country: {country_code}')
                    stats['country_added'] += 1
            
            # Infer operation type if missing
            if not job.operation_type:
                operation_type = db_manager._infer_operation_type(
                    job.title,
                    job.company,
                    job.description or ''
                )
                if operation_type:
                    if not dry_run:
                        job.operation_type = operation_type
                    changed = True
                    changes.append(f'operation: {operation_type}')
                    stats['operation_added'] += 1
            
            if changed:
                if not dry_run:
                    job.save(update_fields=['status', 'country_code', 'operation_type'])
                
                if i % 100 == 0 or i <= 10:
                    self.stdout.write(
                        f'  [{i}/{total}] {job.id}: {job.title[:40]} | {", ".join(changes)}'
                    )
            else:
                stats['no_changes'] += 1
        
        # Print summary
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('Summary:'))
        self.stdout.write(f'  Total jobs processed: {total}')
        self.stdout.write(f'  Status fixed (new→active): {stats["status_fixed"]}')
        self.stdout.write(f'  Country code added: {stats["country_added"]}')
        self.stdout.write(f'  Operation type added: {stats["operation_added"]}')
        self.stdout.write(f'  No changes needed: {stats["no_changes"]}')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\nDRY RUN - Run without --dry-run to apply changes'))
        else:
            self.stdout.write(self.style.SUCCESS('\n✓ All changes applied successfully!'))
