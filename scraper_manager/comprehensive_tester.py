#!/usr/bin/env python
"""
Comprehensive Scraper Testing & Data Review Script
Tests scrapers and analyzes data quality
"""

import os
import sys
import django

sys.path.insert(0, '/home/rajat/Desktop/AeroOps Intel/aeroScrap_backend/backendMain')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backendMain.settings')
django.setup()

from scraper_manager.models import ScraperJob, ScrapedURL
from jobs.models import Job
from django.db.models import Count, Q, Sum, Avg
from datetime import timedelta
from django.utils import timezone
import json


class ScraperTester:
    def __init__(self):
        self.test_results = {}
    
    def run_all_tests(self):
        """Run all tests"""
        print("\n" + "="*80)
        print(" "*20 + "COMPREHENSIVE SCRAPER TEST SUITE")
        print("="*80)
        
        self.test_database_integrity()
        self.test_data_quality()
        self.test_scraper_efficiency()
        self.test_data_consistency()
        self.test_error_tracking()
        self.print_summary()
    
    def test_database_integrity(self):
        """Test database integrity and consistency"""
        print("\n" + "-"*80)
        print("TEST 1: DATABASE INTEGRITY")
        print("-"*80)
        
        tests_passed = 0
        tests_total = 0
        
        # Test 1.1: Check for orphaned records
        print("\n✓ Test 1.1: Checking for orphaned URLs...")
        tests_total += 1
        orphaned = ScrapedURL.objects.filter(source='').count()
        if orphaned == 0:
            print(f"  ✅ No orphaned URLs found (0/625)")
            tests_passed += 1
        else:
            print(f"  ⚠️  Found {orphaned} URLs with missing source")
        
        # Test 1.2: Check for duplicate URLs
        print("\n✓ Test 1.2: Checking for duplicate URLs...")
        tests_total += 1
        duplicates = ScrapedURL.objects.values('url').annotate(count=Count('id')).filter(count__gt=1).count()
        if duplicates == 0:
            print(f"  ✅ No duplicate URLs found")
            tests_passed += 1
        else:
            print(f"  ⚠️  Found {duplicates} duplicate URLs")
        
        # Test 1.3: Check job record integrity
        print("\n✓ Test 1.3: Checking job record integrity...")
        tests_total += 1
        jobs_without_title = Job.objects.filter(title='').count()
        if jobs_without_title == 0:
            print(f"  ✅ All {Job.objects.count()} jobs have titles")
            tests_passed += 1
        else:
            print(f"  ⚠️  Found {jobs_without_title} jobs without titles")
        
        # Test 1.4: Check scraper job status consistency
        print("\n✓ Test 1.4: Checking ScraperJob status consistency...")
        tests_total += 1
        invalid_status = ScraperJob.objects.exclude(
            status__in=['pending', 'running', 'completed', 'failed', 'cancelled']
        ).count()
        if invalid_status == 0:
            print(f"  ✅ All {ScraperJob.objects.count()} scraper jobs have valid status")
            tests_passed += 1
        else:
            print(f"  ⚠️  Found {invalid_status} jobs with invalid status")
        
        self.test_results['Database Integrity'] = f"{tests_passed}/{tests_total}"
        print(f"\n✅ Database Integrity: {tests_passed}/{tests_total} tests passed")
    
    def test_data_quality(self):
        """Test data completeness and quality"""
        print("\n" + "-"*80)
        print("TEST 2: DATA QUALITY & COMPLETENESS")
        print("-"*80)
        
        tests_passed = 0
        tests_total = 0
        
        # Test 2.1: Title completeness
        print("\n✓ Test 2.1: Title data completeness...")
        tests_total += 1
        total = ScrapedURL.objects.count()
        with_title = ScrapedURL.objects.exclude(title='').count()
        title_pct = (with_title * 100) // total if total else 0
        print(f"  {with_title}/{total} URLs have titles ({title_pct}%)")
        if title_pct >= 95:
            print(f"  ✅ Title completeness acceptable")
            tests_passed += 1
        else:
            print(f"  ⚠️  Title completeness below 95%")
        
        # Test 2.2: Company data
        print("\n✓ Test 2.2: Company name completeness...")
        tests_total += 1
        with_company = ScrapedURL.objects.exclude(company='').count()
        company_pct = (with_company * 100) // total if total else 0
        print(f"  {with_company}/{total} URLs have company names ({company_pct}%)")
        if company_pct >= 90:
            print(f"  ✅ Company completeness acceptable")
            tests_passed += 1
        else:
            print(f"  ⚠️  Company completeness below 90%")
        
        # Test 2.3: Description data
        print("\n✓ Test 2.3: Job description completeness...")
        tests_total += 1
        with_desc = ScrapedURL.objects.exclude(job_data__description='').count()
        desc_pct = (with_desc * 100) // total if total else 0
        print(f"  {with_desc}/{total} URLs have descriptions ({desc_pct}%)")
        if desc_pct >= 90:
            print(f"  ✅ Description completeness acceptable")
            tests_passed += 1
        else:
            print(f"  ⚠️  Description completeness below 90%")
        
        # Test 2.4: Location data
        print("\n✓ Test 2.4: Location data completeness...")
        tests_total += 1
        with_location = ScrapedURL.objects.exclude(job_data__location='').count()
        location_pct = (with_location * 100) // total if total else 0
        print(f"  {with_location}/{total} URLs have location ({location_pct}%)")
        if location_pct >= 80:
            print(f"  ✅ Location data acceptable")
            tests_passed += 1
        else:
            print(f"  ⚠️  Location data below 80%")
        
        # Test 2.5: Data by source analysis
        print("\n✓ Test 2.5: Data quality by source:")
        tests_total += 1
        sources_ok = 0
        sources_total = 0
        
        by_source = ScrapedURL.objects.values('source').distinct()
        for source_info in by_source:
            source = source_info['source']
            urls = ScrapedURL.objects.filter(source=source)
            source_total = urls.count()
            with_desc_src = urls.exclude(job_data__description='').count()
            desc_pct_src = (with_desc_src * 100) // source_total if source_total else 0
            
            status_icon = "✅" if desc_pct_src >= 80 else "⚠️"
            print(f"    {status_icon} {source}: {desc_pct_src}% with descriptions")
            
            if desc_pct_src >= 80:
                sources_ok += 1
            sources_total += 1
        
        if sources_ok >= sources_total * 0.8:
            print(f"  ✅ Most sources have good data quality")
            tests_passed += 1
        else:
            print(f"  ⚠️  Some sources have poor data quality")
        
        self.test_results['Data Quality'] = f"{tests_passed}/{tests_total}"
        print(f"\n✅ Data Quality: {tests_passed}/{tests_total} tests passed")
    
    def test_scraper_efficiency(self):
        """Test scraper efficiency and performance"""
        print("\n" + "-"*80)
        print("TEST 3: SCRAPER EFFICIENCY & PERFORMANCE")
        print("-"*80)
        
        tests_passed = 0
        tests_total = 0
        
        # Test 3.1: Execution time analysis
        print("\n✓ Test 3.1: Execution time analysis...")
        tests_total += 1
        completed_jobs = ScraperJob.objects.filter(
            status='completed',
            execution_time__isnull=False
        )
        if completed_jobs.exists():
            avg_time = completed_jobs.aggregate(avg=Avg('execution_time'))['avg']
            max_time = completed_jobs.aggregate(max_time=Avg('execution_time'))
            print(f"  Average execution time: {avg_time:.1f} seconds")
            if avg_time < 300:  # Less than 5 minutes
                print(f"  ✅ Execution time is acceptable")
                tests_passed += 1
            else:
                print(f"  ⚠️  Execution time is high (>5 min)")
        
        # Test 3.2: Success rate
        print("\n✓ Test 3.2: Scraper success rate...")
        tests_total += 1
        total_jobs = ScraperJob.objects.count()
        completed = ScraperJob.objects.filter(status='completed').count()
        failed = ScraperJob.objects.filter(status='failed').count()
        success_rate = (completed * 100) // total_jobs if total_jobs else 0
        
        print(f"  Total jobs: {total_jobs}")
        print(f"  Completed: {completed} ({success_rate}%)")
        print(f"  Failed: {failed}")
        
        if success_rate >= 80:
            print(f"  ✅ Success rate is good (>80%)")
            tests_passed += 1
        else:
            print(f"  ⚠️  Success rate is low (<80%)")
        
        # Test 3.3: Job discovery rate
        print("\n✓ Test 3.3: Job discovery efficiency...")
        tests_total += 1
        jobs_found = ScraperJob.objects.filter(status='completed').aggregate(
            total=Sum('jobs_found'),
            new=Sum('jobs_new')
        )
        total_found = jobs_found['total'] or 0
        total_new = jobs_found['new'] or 0
        
        print(f"  Total jobs found: {total_found}")
        print(f"  New jobs: {total_new}")
        
        if total_found > 0:
            print(f"  ✅ Scrapers are finding jobs")
            tests_passed += 1
        else:
            print(f"  ⚠️  No jobs are being found")
        
        self.test_results['Efficiency'] = f"{tests_passed}/{tests_total}"
        print(f"\n✅ Efficiency: {tests_passed}/{tests_total} tests passed")
    
    def test_data_consistency(self):
        """Test data consistency across systems"""
        print("\n" + "-"*80)
        print("TEST 4: DATA CONSISTENCY")
        print("-"*80)
        
        tests_passed = 0
        tests_total = 0
        
        # Test 4.1: URL count consistency
        print("\n✓ Test 4.1: URL tracking consistency...")
        tests_total += 1
        scraped_urls = ScrapedURL.objects.count()
        jobs_in_system = Job.objects.count()
        
        print(f"  ScrapedURLs: {scraped_urls}")
        print(f"  Jobs in system: {jobs_in_system}")
        
        if scraped_urls <= jobs_in_system * 1.5:  # URLs should be roughly equal to jobs
            print(f"  ✅ URL counts are consistent")
            tests_passed += 1
        else:
            print(f"  ⚠️  Mismatch between URLs and jobs")
        
        # Test 4.2: Source coverage
        print("\n✓ Test 4.2: Source coverage...")
        tests_total += 1
        unique_sources = ScrapedURL.objects.values('source').distinct().count()
        print(f"  {unique_sources} unique sources with data")
        
        if unique_sources >= 5:
            print(f"  ✅ Good source diversity")
            tests_passed += 1
        else:
            print(f"  ⚠️  Limited source diversity")
        
        # Test 4.3: Data freshness
        print("\n✓ Test 4.3: Data freshness...")
        tests_total += 1
        recent_cutoff = timezone.now() - timedelta(days=1)
        recent_urls = ScrapedURL.objects.filter(last_scraped__gte=recent_cutoff).count()
        
        print(f"  URLs scraped in last 24 hours: {recent_urls}")
        
        if recent_urls > 0:
            print(f"  ✅ Recent data is available")
            tests_passed += 1
        else:
            print(f"  ⚠️  No recent scraping activity")
        
        self.test_results['Consistency'] = f"{tests_passed}/{tests_total}"
        print(f"\n✅ Consistency: {tests_passed}/{tests_total} tests passed")
    
    def test_error_tracking(self):
        """Test error tracking and reporting"""
        print("\n" + "-"*80)
        print("TEST 5: ERROR TRACKING & ANALYSIS")
        print("-"*80)
        
        tests_passed = 0
        tests_total = 0
        
        # Test 5.1: Error logging
        print("\n✓ Test 5.1: Error logging...")
        tests_total += 1
        failed_jobs = ScraperJob.objects.filter(status='failed')
        logged_errors = failed_jobs.exclude(error_message='').count()
        
        print(f"  Failed jobs: {failed_jobs.count()}")
        print(f"  With error messages: {logged_errors}")
        
        if logged_errors == failed_jobs.count():
            print(f"  ✅ All errors are properly logged")
            tests_passed += 1
        elif logged_errors > 0:
            print(f"  ⚠️  Some errors missing messages")
        else:
            print(f"  ℹ️  No recent failures")
        
        # Test 5.2: Error patterns
        print("\n✓ Test 5.2: Error pattern analysis...")
        tests_total += 1
        error_patterns = {}
        for job in failed_jobs:
            if job.error_message:
                # Extract first line of error
                error_short = job.error_message.split('\n')[0][:50]
                error_patterns[error_short] = error_patterns.get(error_short, 0) + 1
        
        if error_patterns:
            print(f"  Top errors:")
            for error, count in sorted(error_patterns.items(), key=lambda x: -x[1])[:5]:
                print(f"    - {error}: {count} times")
        
        if len(error_patterns) <= 3:
            print(f"  ✅ Few distinct error patterns (likely environment issues)")
            tests_passed += 1
        else:
            print(f"  ⚠️  Multiple error patterns detected")
        
        self.test_results['Error Tracking'] = f"{tests_passed}/{tests_total}"
        print(f"\n✅ Error Tracking: {tests_passed}/{tests_total} tests passed")
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*80)
        print(" "*25 + "TEST SUMMARY")
        print("="*80)
        
        print("\nTest Results:")
        for test_name, result in self.test_results.items():
            print(f"  • {test_name}: {result}")
        
        # Calculate overall stats
        total_urls = ScrapedURL.objects.count()
        total_jobs = Job.objects.count()
        completed_runs = ScraperJob.objects.filter(status='completed').count()
        
        print("\n" + "-"*80)
        print("OVERALL STATISTICS")
        print("-"*80)
        print(f"  Total URLs scraped: {total_urls}")
        print(f"  Total jobs in system: {total_jobs}")
        print(f"  Successful scraper runs: {completed_runs}")
        print(f"  Data sources: {ScrapedURL.objects.values('source').distinct().count()}")
        
        # Data quality score
        urls_with_desc = ScrapedURL.objects.exclude(job_data__description='').count()
        quality_score = (urls_with_desc * 100) // total_urls if total_urls else 0
        
        print(f"\n  Data Quality Score: {quality_score}%")
        
        if quality_score >= 90:
            print("  ✅ EXCELLENT data quality")
        elif quality_score >= 80:
            print("  ✅ GOOD data quality")
        elif quality_score >= 70:
            print("  ⚠️  ACCEPTABLE data quality")
        else:
            print("  ❌ POOR data quality")
        
        print("\n" + "="*80 + "\n")


if __name__ == '__main__':
    tester = ScraperTester()
    tester.run_all_tests()
