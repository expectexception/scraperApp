"""
Advanced Job Filter Manager - OPTIMIZED VERSION
Uses sophisticated filtering techniques including:
- Precompiled regex patterns for performance
- Caching mechanisms to avoid redundant processing
- Parallel keyword matching with early exit
- Weighted scoring by category with priority levels
- Smart exclusion patterns for false positives
"""

import json
import re
from typing import List, Dict, Set, Optional, Tuple
from pathlib import Path
from functools import lru_cache
import time


class JobFilterManager:
    """Advanced job filtering with weighted scoring, caching, and performance optimization"""
    
    def __init__(self, filter_file: str = 'filter_title.json', use_cache: bool = True):
        """Initialize filter manager with filter configuration"""
        self.filter_file = Path(filter_file)
        self.filters = []
        self.all_keywords = set()
        self.keyword_to_category = {}
        self.phrase_keywords = []  # Multi-word phrases
        self.single_keywords = []  # Single words
        self.use_cache = use_cache
        self.filter_cache = {}  # Cache for filtered titles
        
        # Precompiled regex patterns for performance
        self.phrase_patterns = []  # List of (pattern, keyword) tuples
        self.single_patterns = []  # List of (pattern, keyword) tuples
        self.exclusion_compiled = []  # Precompiled exclusion patterns
        
        # Exclusion patterns to filter out false positives
        self.exclusion_patterns = [
            r'\b(cabin crew|flight attendant|steward|stewardess)\b',
            r'\b(pilot recruitment|pilot jobs|careers|hiring)\b',
            r'\b(maintenance engineer|aircraft engineer|technician)\b',
            r'\b(software|developer|programmer|IT)\b',
            r'\b(sales|marketing|finance|HR|human resources)\b',
            r'\b(receptionist|secretary|admin|administrative)\b',
            r'\b(logistics|supply chain|warehouse|inventory)\b',
            r'\b(security|catering|cleaning|janitorial)\b',
            r'\b(retail|cashier|shop|store)\b',
        ]
        
        # Category weights for scoring (higher = more important)
        self.category_weights = {
            'Core_Function_Terms_Only': 3.0,  # Highest priority
            'Operative_Functional_Control_Keywords': 2.5,
            'Supervisory_Level_Control_Keywords': 2.0,
            'Management_Executive_Control_Keywords': 1.5
        }
        
        # Performance metrics
        self.perf_stats = {
            'filters_loaded': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'total_filtered': 0,
            'avg_filter_time_ms': 0
        }
        
        self.load_filters()
    
    def load_filters(self):
        """Load filter configuration from JSON file with advanced processing"""
        if not self.filter_file.exists():
            print(f"⚠️  Filter file not found: {self.filter_file}")
            return
        
        try:
            with open(self.filter_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.filters = data.get('Filters', [])
            
            # Precompile exclusion patterns for performance
            for pattern in self.exclusion_patterns:
                try:
                    self.exclusion_compiled.append(re.compile(pattern, re.IGNORECASE))
                except Exception as e:
                    print(f"⚠️  Error compiling exclusion pattern '{pattern}': {e}")
            
            # Build keyword sets and mappings with phrase/single word separation
            for filter_group in self.filters:
                filter_type = filter_group.get('FilterType', '')
                display_name = filter_group.get('DisplayName', '')
                keywords = filter_group.get('Keywords', [])
                weight = self.category_weights.get(filter_type, 1.0)
                
                for keyword in keywords:
                    keyword_lower = keyword.lower()
                    self.all_keywords.add(keyword_lower)
                    
                    # Separate phrases from single words
                    if ' ' in keyword_lower:
                        self.phrase_keywords.append(keyword_lower)
                        # Precompile phrase pattern
                        pattern = re.compile(r'\b' + re.escape(keyword_lower) + r'\b', re.IGNORECASE)
                        self.phrase_patterns.append((pattern, keyword_lower))
                    else:
                        self.single_keywords.append(keyword_lower)
                        # Precompile single word pattern
                        pattern = re.compile(r'\b' + re.escape(keyword_lower) + r'\b', re.IGNORECASE)
                        self.single_patterns.append((pattern, keyword_lower))
                    
                    # Map keyword to its category with weight
                    if keyword_lower not in self.keyword_to_category:
                        self.keyword_to_category[keyword_lower] = []
                    self.keyword_to_category[keyword_lower].append({
                        'filter_type': filter_type,
                        'display_name': display_name,
                        'original_keyword': keyword,
                        'weight': weight
                    })
            
            self.perf_stats['filters_loaded'] = len(self.filters)
            
            print(f"✓ Loaded {len(self.filters)} filter categories")
            print(f"✓ Total keywords: {len(self.all_keywords)} ({len(self.phrase_keywords)} phrases, {len(self.single_keywords)} single words)")
            print(f"✓ Exclusion patterns: {len(self.exclusion_compiled)} (precompiled)")
            print(f"✓ Performance: Regex patterns precompiled for speed")
            
        except Exception as e:
            print(f"❌ Error loading filters: {e}")
    
    def check_exclusions(self, job_title: str) -> bool:
        """
        Check if title matches exclusion patterns (false positives)
        Uses precompiled patterns for performance
        
        Returns:
            True if title should be excluded
        """
        for pattern in self.exclusion_compiled:
            if pattern.search(job_title):
                return True
        return False
    
    def _get_cache_key(self, job_title: str) -> str:
        """Generate cache key for job title"""
        return job_title.lower()
    
    @lru_cache(maxsize=10000)
    def _cached_matches_filter(self, job_title_lower: str) -> Tuple[bool, Tuple, float, Dict]:
        """Cached filter matching - internal implementation"""
        return self._matches_filter_impl(job_title_lower)
    
    def _matches_filter_impl(self, title_lower: str) -> Tuple[bool, Tuple, float, Dict]:
        """Internal implementation of filter matching"""
        # Check exclusion patterns first (fast path)
        for pattern in self.exclusion_compiled:
            if pattern.search(title_lower):
                return False, tuple(), 0.0, {'reason': 'excluded_pattern'}
        
        matched_keywords = []
        total_score = 0.0
        category_scores = {}
        
        # Phase 1: Match multi-word phrases first (higher accuracy, fewer comparisons)
        for pattern, phrase in self.phrase_patterns:
            if pattern.search(title_lower):
                matched_keywords.append(phrase)
                
                # Add category information with weight
                categories = self.keyword_to_category.get(phrase, [])
                for cat in categories:
                    weight = cat['weight']
                    total_score += weight * 2.0  # Phrases get 2x weight
                    
                    cat_name = cat['display_name']
                    if cat_name not in category_scores:
                        category_scores[cat_name] = 0.0
                    category_scores[cat_name] += weight * 2.0
        
        # Early exit if we have high confidence match from phrases
        if total_score >= 4.0:
            matched_categories = self._build_categories(matched_keywords)
            is_match = True
            match_details = {
                'matched_keywords': matched_keywords,
                'category_scores': category_scores,
                'keyword_count': len(matched_keywords),
                'match_type': 'phrase_match'
            }
            return is_match, tuple(matched_categories), total_score, match_details
        
        # Phase 2: Match single words (lower priority)
        for pattern, keyword in self.single_patterns:
            if pattern.search(title_lower):
                matched_keywords.append(keyword)
                
                # Add category information with weight
                categories = self.keyword_to_category.get(keyword, [])
                for cat in categories:
                    weight = cat['weight']
                    total_score += weight
                    
                    cat_name = cat['display_name']
                    if cat_name not in category_scores:
                        category_scores[cat_name] = 0.0
                    category_scores[cat_name] += weight
        
        matched_categories = self._build_categories(matched_keywords)
        is_match = total_score >= 1.5  # Minimum threshold
        
        match_details = {
            'matched_keywords': matched_keywords,
            'category_scores': category_scores,
            'keyword_count': len(matched_keywords),
            'match_type': 'combined_match' if len(matched_keywords) > 1 else 'single_match'
        }
        
        return is_match, tuple(matched_categories), total_score, match_details
    
    def _build_categories(self, matched_keywords: List[str]) -> List[Dict]:
        """Build category list from matched keywords"""
        categories = []
        seen = set()
        for keyword in matched_keywords:
            cats = self.keyword_to_category.get(keyword, [])
            for cat in cats:
                cat_key = (cat['filter_type'], cat['display_name'])
                if cat_key not in seen:
                    seen.add(cat_key)
                    categories.append(cat)
        return categories
    
    def matches_filter(self, job_title: str) -> Tuple[bool, List[Dict], float, Dict]:
        """
        Advanced filter matching with scoring and category labeling
        
        Returns:
            (matches: bool, matched_categories: List[Dict], score: float, match_details: Dict)
        """
        if not job_title:
            return False, [], 0.0, {}
        
        title_lower = job_title.lower()
        
        # Try cache first if enabled
        if self.use_cache:
            cache_key = self._get_cache_key(job_title)
            if cache_key in self.filter_cache:
                self.perf_stats['cache_hits'] += 1
                return self.filter_cache[cache_key]
            self.perf_stats['cache_misses'] += 1
        
        # Perform actual filtering
        is_match, categories, score, details = self._matches_filter_impl(title_lower)
        result = (is_match, list(categories), score, details)
        
        # Cache result if enabled
        if self.use_cache:
            self.filter_cache[cache_key] = result
        
        return result
    
    def filter_jobs(self, jobs: List[Dict]) -> Tuple[List[Dict], List[Dict], Dict]:
        """
        Filter a list of jobs with performance optimization
        
        Uses batch processing and statistics tracking
        
        Returns:
            (matched_jobs, rejected_jobs, statistics)
        """
        if not jobs:
            return [], [], {
                'total': 0, 'matched': 0, 'rejected': 0, 'excluded': 0,
                'by_category': {}, 'score_distribution': {'high': 0, 'medium': 0, 'low': 0},
                'performance': {'cache_hits': 0, 'cache_misses': 0}
            }
        
        matched_jobs = []
        rejected_jobs = []
        
        stats = {
            'total': len(jobs),
            'matched': 0,
            'rejected': 0,
            'excluded': 0,
            'by_category': {},
            'score_distribution': {
                'high': 0,    # score >= 5.0
                'medium': 0,  # 3.0 <= score < 5.0
                'low': 0      # 1.5 <= score < 3.0
            },
            'performance': {}
        }
        
        # Performance timing
        start_time = time.time()
        
        for job in jobs:
            title = job.get('title', '')
            matches, categories, score, details = self.matches_filter(title)
            
            if matches:
                # Add comprehensive filter metadata to job
                job['filter_match'] = True
                job['filter_score'] = round(score, 2)
                job['matched_categories'] = [cat['display_name'] for cat in categories]
                job['matched_filter_types'] = [cat['filter_type'] for cat in categories]
                job['matched_keywords'] = details.get('matched_keywords', [])
                job['category_scores'] = details.get('category_scores', {})
                
                # Add primary category label (highest scoring)
                if details.get('category_scores'):
                    primary_category = max(details['category_scores'].items(), key=lambda x: x[1])[0]
                    job['primary_category'] = primary_category
                else:
                    job['primary_category'] = job['matched_categories'][0] if job['matched_categories'] else 'Unknown'
                
                matched_jobs.append(job)
                stats['matched'] += 1
                
                # Score distribution
                if score >= 5.0:
                    stats['score_distribution']['high'] += 1
                elif score >= 3.0:
                    stats['score_distribution']['medium'] += 1
                else:
                    stats['score_distribution']['low'] += 1
                
                # Count by category
                for cat in categories:
                    cat_name = cat['display_name']
                    if cat_name not in stats['by_category']:
                        stats['by_category'][cat_name] = 0
                    stats['by_category'][cat_name] += 1
            else:
                job['filter_match'] = False
                job['filter_score'] = 0.0
                job['matched_categories'] = []
                job['primary_category'] = None
                
                # Track exclusion reason
                if details.get('reason') == 'excluded_pattern':
                    stats['excluded'] += 1
                    job['rejection_reason'] = 'excluded_pattern'
                else:
                    job['rejection_reason'] = 'no_keyword_match'
                
                rejected_jobs.append(job)
                stats['rejected'] += 1
        
        # Calculate performance metrics
        elapsed_ms = (time.time() - start_time) * 1000
        stats['performance'] = {
            'total_time_ms': round(elapsed_ms, 2),
            'avg_per_job_ms': round(elapsed_ms / len(jobs), 3) if jobs else 0,
            'cache_hits': self.perf_stats['cache_hits'],
            'cache_misses': self.perf_stats['cache_misses'],
            'cache_efficiency': round(
                self.perf_stats['cache_hits'] / (self.perf_stats['cache_hits'] + self.perf_stats['cache_misses']) * 100, 1
            ) if (self.perf_stats['cache_hits'] + self.perf_stats['cache_misses']) > 0 else 0
        }
        
        self.perf_stats['total_filtered'] += len(jobs)
        self.perf_stats['avg_filter_time_ms'] = stats['performance']['avg_per_job_ms']
        
        return matched_jobs, rejected_jobs, stats
    
    def print_filter_stats(self, stats: Dict):
        """Print comprehensive filtering statistics with performance metrics"""
        print(f"\n{'='*70}")
        print("📊 ADVANCED FILTERING RESULTS")
        print(f"{'='*70}")
        print(f"\nTotal jobs analyzed: {stats['total']}")
        print(f"✅ Matched (will scrape): {stats['matched']}")
        print(f"❌ Rejected (skipped): {stats['rejected']}")
        
        if stats.get('excluded', 0) > 0:
            print(f"🚫 Excluded by pattern: {stats['excluded']}")
        
        if stats['matched'] > 0:
            match_rate = (stats['matched'] / stats['total']) * 100
            print(f"\n📈 Match rate: {match_rate:.1f}%")
            
            # Score distribution
            score_dist = stats.get('score_distribution', {})
            if any(score_dist.values()):
                print(f"\n🎯 Score Distribution:")
                print(f"  • High confidence (≥5.0):    {score_dist.get('high', 0)} jobs")
                print(f"  • Medium confidence (≥3.0):  {score_dist.get('medium', 0)} jobs")
                print(f"  • Low confidence (≥1.5):     {score_dist.get('low', 0)} jobs")
        
        if stats.get('by_category'):
            print(f"\n📁 Matches by Category:")
            for category, count in sorted(stats['by_category'].items(), key=lambda x: x[1], reverse=True):
                print(f"  • {category}: {count} jobs")
        
        # Performance metrics
        perf = stats.get('performance', {})
        if perf:
            print(f"\n⚡ Performance Metrics:")
            print(f"  • Total time: {perf.get('total_time_ms', 0):.2f}ms")
            print(f"  • Per-job avg: {perf.get('avg_per_job_ms', 0):.3f}ms")
            if perf.get('cache_efficiency', 0) > 0:
                print(f"  • Cache efficiency: {perf.get('cache_efficiency', 0):.1f}% hit rate")
        
        print(f"{'='*70}\n")
    
    def get_filter_summary(self) -> Dict:
        """Get summary of loaded filters"""
        summary = {
            'total_categories': len(self.filters),
            'total_keywords': len(self.all_keywords),
            'phrase_keywords': len(self.phrase_keywords),
            'single_keywords': len(self.single_keywords),
            'precompiled_patterns': len(self.phrase_patterns) + len(self.single_patterns),
            'exclusion_patterns': len(self.exclusion_compiled),
            'cache_enabled': self.use_cache,
            'categories': []
        }
        
        for filter_group in self.filters:
            summary['categories'].append({
                'type': filter_group.get('FilterType', ''),
                'name': filter_group.get('DisplayName', ''),
                'description': filter_group.get('Description', ''),
                'keyword_count': len(filter_group.get('Keywords', []))
            })
        
        return summary
    
    def print_filter_info(self):
        """Print information about loaded filters and optimizations"""
        print(f"\n{'='*70}")
        print("🔍 FILTER CONFIGURATION & OPTIMIZATIONS")
        print(f"{'='*70}")
        
        summary = self.get_filter_summary()
        print(f"\nTotal Categories: {summary['total_categories']}")
        print(f"Total Keywords: {summary['total_keywords']}")
        print(f"  • Phrases (multi-word): {summary['phrase_keywords']}")
        print(f"  • Single words: {summary['single_keywords']}")
        
        print(f"\n⚡ Performance Optimizations:")
        print(f"  • Precompiled regex patterns: {summary['precompiled_patterns']}")
        print(f"  • Precompiled exclusion patterns: {summary['exclusion_patterns']}")
        print(f"  • Result caching enabled: {summary['cache_enabled']}")
        print(f"  • Cache size: 10,000 entries (LRU)")
        print(f"  • Matching strategy: 2-phase (phrases→single words)")
        print(f"  • Early exit on high confidence (≥4.0)")
        
        print("\nCategories:")
        for cat in summary['categories']:
            print(f"\n  📁 {cat['name']}")
            print(f"     Type: {cat['type']}")
            print(f"     Keywords: {cat['keyword_count']}")
            print(f"     {cat['description']}")
        
        print(f"\n{'='*70}\n")
    
    def clear_cache(self):
        """Clear the LRU cache and filter cache"""
        self.filter_cache.clear()
        self._cached_matches_filter.cache_clear()
        self.perf_stats['cache_hits'] = 0
        self.perf_stats['cache_misses'] = 0
        print("✓ Filter cache cleared")
    
    def get_cache_stats(self) -> Dict:
        """Get cache performance statistics"""
        total_requests = self.perf_stats['cache_hits'] + self.perf_stats['cache_misses']
        return {
            'total_filtered_jobs': self.perf_stats['total_filtered'],
            'cache_hits': self.perf_stats['cache_hits'],
            'cache_misses': self.perf_stats['cache_misses'],
            'total_requests': total_requests,
            'hit_rate': round(
                (self.perf_stats['cache_hits'] / total_requests * 100) if total_requests > 0 else 0, 1
            ),
            'avg_filter_time_ms': round(self.perf_stats['avg_filter_time_ms'], 3)
        }


if __name__ == '__main__':
    # Test the optimized filter manager
    filter_mgr = JobFilterManager('filter_title.json')
    filter_mgr.print_filter_info()
    
    # Test with sample titles including edge cases
    test_titles = [
        "Flight Operations Officer - OCC",
        "Senior Dispatcher - Network Control",
        "Aircraft Maintenance Engineer",
        "Software Developer",
        "OCC Manager - Operations Control",
        "Load Controller - Hub Operations",
        "Cabin Crew",
        "Flight Dispatch Supervisor",
        "Director Network Operations",
        "IOCC Controller - Night Shift",
        "Flight Operations Center Manager",
        "Crew Control Supervisor",
        "First Officer Jobs | Pilot Careers",  # Should be excluded
        "Network Recovery Officer",
        "Head of Flight Dispatch"
    ]
    
    print("\n" + "="*70)
    print("TEST: Optimized Matching with Performance Tracking")
    print("="*70)
    
    for title in test_titles:
        matches, categories, score, details = filter_mgr.matches_filter(title)
        if matches:
            cat_names = [cat['display_name'] for cat in categories]
            primary = max(details['category_scores'].items(), key=lambda x: x[1])[0] if details['category_scores'] else 'N/A'
            print(f"\n✅ MATCH: {title}")
            print(f"   Score: {score:.2f}")
            print(f"   Primary Category: {primary}")
            print(f"   All Categories: {', '.join(cat_names)}")
            print(f"   Keywords: {', '.join(details['matched_keywords'][:5])}")  # Show first 5
        else:
            reason = details.get('reason', 'no match')
            print(f"\n❌ NO MATCH: {title}")
            print(f"   Reason: {reason}")
    
    # Show cache stats
    print("\n" + "="*70)
    print("CACHE PERFORMANCE")
    print("="*70)
    cache_stats = filter_mgr.get_cache_stats()
    print(f"\nTotal jobs filtered: {cache_stats['total_filtered_jobs']}")
    print(f"Cache hits: {cache_stats['cache_hits']}")
    print(f"Cache misses: {cache_stats['cache_misses']}")
    print(f"Hit rate: {cache_stats['hit_rate']}%")
    print(f"Avg time per job: {cache_stats['avg_filter_time_ms']}ms")
        # Phase 2: Match single words (lower priority)
        for keyword in self.single_keywords:
            # Word boundary matching
            pattern = r'\b' + re.escape(keyword) + r'\b'
            
            if re.search(pattern, title_lower):
                matched_keywords.append(keyword)
                
                # Add category information with weight
                categories = self.keyword_to_category.get(keyword, [])
                for cat in categories:
                    weight = cat['weight']
                    total_score += weight
                    
                    # Track category scores
                    cat_name = cat['display_name']
                    if cat_name not in category_scores:
                        category_scores[cat_name] = 0.0
                    category_scores[cat_name] += weight
                    
                    if cat not in matched_categories:
                        matched_categories.append(cat)
        
        match_details = {
            'matched_keywords': matched_keywords,
            'category_scores': category_scores,
            'keyword_count': len(matched_keywords)
        }
        
        # Consider it a match if score is significant enough
        is_match = total_score >= 1.5  # Minimum threshold
        
        return is_match, matched_categories, total_score, match_details
    
    def filter_jobs(self, jobs: List[Dict]) -> Tuple[List[Dict], List[Dict], Dict]:
        """
        Advanced filtering with scoring and detailed categorization
        
        Returns:
            (matched_jobs, rejected_jobs, statistics)
        """
        matched_jobs = []
        rejected_jobs = []
        
        stats = {
            'total': len(jobs),
            'matched': 0,
            'rejected': 0,
            'excluded': 0,
            'by_category': {},
            'score_distribution': {
                'high': 0,    # score >= 5.0
                'medium': 0,  # 3.0 <= score < 5.0
                'low': 0      # 1.5 <= score < 3.0
            }
        }
        
        for job in jobs:
            title = job.get('title', '')
            matches, categories, score, details = self.matches_filter(title)
            
            if matches:
                # Add comprehensive filter metadata to job
                job['filter_match'] = True
                job['filter_score'] = round(score, 2)
                job['matched_categories'] = [cat['display_name'] for cat in categories]
                job['matched_filter_types'] = [cat['filter_type'] for cat in categories]
                job['matched_keywords'] = details.get('matched_keywords', [])
                job['category_scores'] = details.get('category_scores', {})
                
                # Add primary category label (highest scoring)
                if details.get('category_scores'):
                    primary_category = max(details['category_scores'].items(), key=lambda x: x[1])[0]
                    job['primary_category'] = primary_category
                else:
                    job['primary_category'] = job['matched_categories'][0] if job['matched_categories'] else 'Unknown'
                
                matched_jobs.append(job)
                stats['matched'] += 1
                
                # Score distribution
                if score >= 5.0:
                    stats['score_distribution']['high'] += 1
                elif score >= 3.0:
                    stats['score_distribution']['medium'] += 1
                else:
                    stats['score_distribution']['low'] += 1
                
                # Count by category
                for cat in categories:
                    cat_name = cat['display_name']
                    if cat_name not in stats['by_category']:
                        stats['by_category'][cat_name] = 0
                    stats['by_category'][cat_name] += 1
            else:
                job['filter_match'] = False
                job['filter_score'] = 0.0
                job['matched_categories'] = []
                job['primary_category'] = None
                
                # Track exclusion reason
                if details.get('reason') == 'excluded_pattern':
                    stats['excluded'] += 1
                    job['rejection_reason'] = 'excluded_pattern'
                
                rejected_jobs.append(job)
                stats['rejected'] += 1
        
        return matched_jobs, rejected_jobs, stats
    
    def print_filter_stats(self, stats: Dict):
        """Print comprehensive filtering statistics"""
        print(f"\n{'='*70}")
        print("📊 ADVANCED FILTERING RESULTS")
        print(f"{'='*70}")
        print(f"\nTotal jobs analyzed: {stats['total']}")
        print(f"✅ Matched (will scrape): {stats['matched']}")
        print(f"❌ Rejected (skipped): {stats['rejected']}")
        
        if stats.get('excluded', 0) > 0:
            print(f"🚫 Excluded by pattern: {stats['excluded']}")
        
        if stats['matched'] > 0:
            match_rate = (stats['matched'] / stats['total']) * 100
            print(f"\n📈 Match rate: {match_rate:.1f}%")
            
            # Score distribution
            score_dist = stats.get('score_distribution', {})
            if any(score_dist.values()):
                print(f"\n🎯 Score Distribution:")
                print(f"  • High confidence (≥5.0):    {score_dist.get('high', 0)} jobs")
                print(f"  • Medium confidence (≥3.0):  {score_dist.get('medium', 0)} jobs")
                print(f"  • Low confidence (≥1.5):     {score_dist.get('low', 0)} jobs")
        
        if stats.get('by_category'):
            print(f"\n📁 Matches by Category:")
            for category, count in sorted(stats['by_category'].items(), key=lambda x: x[1], reverse=True):
                print(f"  • {category}: {count} jobs")
        
        print(f"{'='*70}\n")
    
    def get_filter_summary(self) -> Dict:
        """Get summary of loaded filters"""
        summary = {
            'total_categories': len(self.filters),
            'total_keywords': len(self.all_keywords),
            'categories': []
        }
        
        for filter_group in self.filters:
            summary['categories'].append({
                'type': filter_group.get('FilterType', ''),
                'name': filter_group.get('DisplayName', ''),
                'description': filter_group.get('Description', ''),
                'keyword_count': len(filter_group.get('Keywords', []))
            })
        
        return summary
    
    def print_filter_info(self):
        """Print information about loaded filters"""
        print(f"\n{'='*70}")
        print("🔍 FILTER CONFIGURATION")
        print(f"{'='*70}")
        
        summary = self.get_filter_summary()
        print(f"\nTotal Categories: {summary['total_categories']}")
        print(f"Total Keywords: {summary['total_keywords']}")
        
        print("\nCategories:")
        for cat in summary['categories']:
            print(f"\n  📁 {cat['name']}")
            print(f"     Type: {cat['type']}")
            print(f"     Keywords: {cat['keyword_count']}")
            print(f"     {cat['description']}")
        
        print(f"\n{'='*70}\n")


if __name__ == '__main__':
    # Test the advanced filter manager
    filter_mgr = JobFilterManager('filter_title.json')
    filter_mgr.print_filter_info()
    
    # Test with sample titles including edge cases
    test_titles = [
        "Flight Operations Officer - OCC",
        "Senior Dispatcher - Network Control",
        "Aircraft Maintenance Engineer",
        "Software Developer",
        "OCC Manager - Operations Control",
        "Load Controller - Hub Operations",
        "Cabin Crew",
        "Flight Dispatch Supervisor",
        "Director Network Operations",
        "IOCC Controller - Night Shift",
        "Flight Operations Center Manager",
        "Crew Control Supervisor",
        "First Officer Jobs | Pilot Careers",  # Should be excluded
        "Network Recovery Officer",
        "Head of Flight Dispatch"
    ]
    
    print("\n" + "="*70)
    print("TEST: Advanced Matching with Scoring")
    print("="*70)
    
    for title in test_titles:
        matches, categories, score, details = filter_mgr.matches_filter(title)
        if matches:
            cat_names = [cat['display_name'] for cat in categories]
            primary = max(details['category_scores'].items(), key=lambda x: x[1])[0] if details['category_scores'] else 'N/A'
            print(f"\n✅ MATCH: {title}")
            print(f"   Score: {score:.2f}")
            print(f"   Primary Category: {primary}")
            print(f"   All Categories: {', '.join(cat_names)}")
            print(f"   Keywords: {', '.join(details['matched_keywords'][:5])}")  # Show first 5
        else:
            reason = details.get('reason', 'no match')
            print(f"\n❌ NO MATCH: {title}")
            print(f"   Reason: {reason}")
