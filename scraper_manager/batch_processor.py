"""
Batch Processing Utilities for Scraper Manager
Optimizes database operations using bulk_create, bulk_update, etc.
"""

import logging
from typing import List, Dict, Tuple, Any
from django.db import transaction
from django.utils import timezone
from .models import ScrapedURL
from jobs.models import Job, CompanyMapping

logger = logging.getLogger(__name__)


class BatchProcessor:
    """Handles batch database operations efficiently"""
    
    def __init__(self, batch_size: int = 100):
        """
        Initialize batch processor
        
        Args:
            batch_size: Number of items to process in each batch
        """
        self.batch_size = batch_size
        self.scraped_urls_buffer = []
        self.jobs_buffer = []
        self.stats = {
            'urls_created': 0,
            'urls_updated': 0,
            'jobs_created': 0,
            'jobs_updated': 0,
            'errors': 0
        }
    
    def add_scraped_url(self, url: str, job_id: str, source: str, 
                        title: str, company: str, job_data: Dict):
        """Add a scraped URL to buffer"""
        self.scraped_urls_buffer.append({
            'url': url,
            'job_id': job_id,
            'source': source,
            'title': title,
            'company': company,
            'job_data': job_data,
            'is_active': True,
        })
        
        if len(self.scraped_urls_buffer) >= self.batch_size:
            self.flush_scraped_urls()
    
    def add_job(self, job_data: Dict, source: str):
        """Add a job to buffer"""
        self.jobs_buffer.append({
            'job_data': job_data,
            'source': source,
        })
        
        if len(self.jobs_buffer) >= self.batch_size:
            self.flush_jobs()
    
    @transaction.atomic
    def flush_scraped_urls(self) -> Tuple[int, int]:
        """Flush buffered scraped URLs to database"""
        if not self.scraped_urls_buffer:
            return 0, 0
        
        created_count = 0
        updated_count = 0
        
        try:
            # Prepare data for bulk operations
            urls_to_create = []
            urls_to_update = []
            existing_urls = set(
                ScrapedURL.objects.filter(
                    url__in=[item['url'] for item in self.scraped_urls_buffer]
                ).values_list('url', flat=True)
            )
            
            for item in self.scraped_urls_buffer:
                url_obj = ScrapedURL(
                    url=item['url'],
                    job_id=item['job_id'],
                    source=item['source'],
                    title=item['title'],
                    company=item['company'],
                    job_data=item['job_data'],
                    is_active=item['is_active'],
                )
                
                if item['url'] in existing_urls:
                    urls_to_update.append(item['url'])
                else:
                    urls_to_create.append(url_obj)
            
            # Bulk create new URLs
            if urls_to_create:
                ScrapedURL.objects.bulk_create(urls_to_create, batch_size=self.batch_size)
                created_count = len(urls_to_create)
                self.stats['urls_created'] += created_count
                logger.debug(f"Bulk created {created_count} scraped URLs")
            
            # Bulk update existing URLs (increment scrape_count)
            if urls_to_update:
                ScrapedURL.objects.filter(
                    url__in=urls_to_update
                ).update(
                    scrape_count=ScrapedURL.objects.filter(url__in=urls_to_update).values('scrape_count')[0]['scrape_count'] + 1,
                    last_scraped=timezone.now()
                )
                updated_count = len(urls_to_update)
                self.stats['urls_updated'] += updated_count
                logger.debug(f"Bulk updated {updated_count} scraped URLs")
            
        except Exception as e:
            logger.error(f"Error flushing scraped URLs: {e}", exc_info=True)
            self.stats['errors'] += 1
        
        finally:
            self.scraped_urls_buffer = []
        
        return created_count, updated_count
    
    @transaction.atomic
    def flush_jobs(self) -> Tuple[int, int]:
        """Flush buffered jobs to database"""
        if not self.jobs_buffer:
            return 0, 0
        
        created_count = 0
        updated_count = 0
        
        try:
            urls_batch = [item['job_data'].get('url', '').strip() for item in self.jobs_buffer]
            
            # Get existing URLs
            existing_jobs = set(
                Job.objects.filter(url__in=urls_batch)
                .values_list('url', flat=True)
            )
            
            jobs_to_create = []
            jobs_to_update = []
            
            for item in self.jobs_buffer:
                job_data = item['job_data']
                url = job_data.get('url', '').strip()
                
                if not url:
                    logger.warning(f"Skipping job without URL: {job_data.get('title')}")
                    continue
                
                defaults = self._prepare_job_defaults(job_data, item['source'])
                
                if url in existing_jobs:
                    jobs_to_update.append((url, defaults))
                else:
                    defaults['url'] = url
                    jobs_to_create.append(Job(**defaults))
            
            # Bulk create new jobs
            if jobs_to_create:
                Job.objects.bulk_create(jobs_to_create, batch_size=self.batch_size)
                created_count = len(jobs_to_create)
                self.stats['jobs_created'] += created_count
                logger.debug(f"Bulk created {created_count} jobs")
            
            # Bulk update existing jobs
            if jobs_to_update:
                # For bulk update with different values, we need to update each
                for url, defaults in jobs_to_update:
                    Job.objects.filter(url=url).update(
                        **{k: v for k, v in defaults.items() if v is not None}
                    )
                updated_count = len(jobs_to_update)
                self.stats['jobs_updated'] += updated_count
                logger.debug(f"Bulk updated {updated_count} jobs")
            
        except Exception as e:
            logger.error(f"Error flushing jobs: {e}", exc_info=True)
            self.stats['errors'] += 1
        
        finally:
            self.jobs_buffer = []
        
        return created_count, updated_count
    
    def flush_all(self) -> Dict[str, int]:
        """Flush all buffers"""
        self.flush_scraped_urls()
        self.flush_jobs()
        return self.stats
    
    def _prepare_job_defaults(self, job_data: Dict, source: str) -> Dict:
        """Prepare job defaults for database insertion"""
        from dateutil import parser
        
        title = job_data.get('title', 'No Title').strip()
        company = job_data.get('company', 'Unknown').strip()
        location = job_data.get('location', '').strip()
        description = job_data.get('description', '').strip()[:10000]  # Limit description
        
        # Parse posted_date
        posted_date = None
        date_str = job_data.get('posted_date')
        if date_str:
            try:
                posted_date = parser.parse(date_str).date()
            except Exception as e:
                logger.debug(f"Could not parse date '{date_str}': {e}")
        
        return {
            'title': title or 'No Title',
            'company': company or 'Unknown Company',
            'location': location,
            'description': description,
            'source': source,
            'country_code': self._extract_country_code(location, company),
            'operation_type': self._infer_operation_type(title, company, description),
            'raw_json': job_data,
            'retrieved_date': timezone.now(),
            'posted_date': posted_date,
            'status': 'active',
        }
    
    def _extract_country_code(self, location: str, company: str = '') -> str:
        """Extract country code from location"""
        if not location:
            return None
        
        location_lower = location.lower()
        country_map = {
            'india': 'IN', 'united states': 'US', 'usa': 'US', 'america': 'US',
            'united kingdom': 'GB', 'uk': 'GB', 'england': 'GB', 'scotland': 'GB',
            'united arab emirates': 'AE', 'uae': 'AE', 'dubai': 'AE', 'abu dhabi': 'AE',
            'singapore': 'SG', 'hong kong': 'HK', 'china': 'CN', 'australia': 'AU',
            'canada': 'CA', 'germany': 'DE', 'france': 'FR', 'netherlands': 'NL',
        }
        
        for pattern, code in country_map.items():
            if pattern in location_lower:
                return code
        
        return None
    
    def _infer_operation_type(self, title: str, company: str, description: str) -> str:
        """Infer operation type from job details"""
        keywords = {
            'flight_ops': ['flight operation', 'flight ops', 'flight crew', 'pilot', 'captain', 'first officer'],
            'ground_ops': ['ground operation', 'ground handling', 'cargo', 'ramp', 'loader'],
            'maintenance': ['maintenance', 'engineer', 'technician', 'mro'],
            'customer_service': ['customer service', 'call center', 'service', 'support'],
        }
        
        combined_text = f"{title} {company} {description}".lower()
        
        for op_type, terms in keywords.items():
            if any(term in combined_text for term in terms):
                return op_type
        
        return 'general'
    
    def get_stats(self) -> Dict[str, int]:
        """Get processing statistics"""
        return self.stats.copy()
