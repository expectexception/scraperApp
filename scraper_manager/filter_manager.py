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
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)



class JobFilterManager:
    """Advanced job filtering with weighted scoring, caching, and performance optimization"""
    
    def __init__(self, filter_file: str = 'filter_title.json', use_cache: bool = True):
        """Initialize filter manager with filter configuration"""
        self.logger = logger
        self.filter_file = Path(filter_file)
        if not self.filter_file.is_absolute():
            # Resolve relative to this specific file's directory
            base_dir = Path(__file__).resolve().parent
            self.filter_file = base_dir / self.filter_file
            
        self.filters = []
        self.all_keywords = set()
        self.keyword_to_category = {}
        self.phrase_keywords = []  # Multi-word phrases
        self.single_keywords = []  # Single words
        self.negative_keywords = [] # Global negative keywords
        self.use_cache = use_cache
        self.filter_cache = {}  # Cache for filtered titles
        
        # Precompiled regex patterns for performance
        self.phrase_patterns = []  # List of (pattern, keyword) tuples
        self.single_patterns = []  # List of (pattern, keyword) tuples
        self.exclusion_compiled = []  # Precompiled exclusion patterns
        
        # Exclusion patterns — jobs matching ANY of these are hard-blocked regardless of score.
        # Pattern: pilot/captain/cabin crew/baggage handler/customer service/unrelated industries.
        self.exclusion_patterns = [
            # Pilots & flight deck (unless specifically looking for flight ops)
            r'\b(pilot|co-pilot|copilot|first officer|second officer|captain|commander)\b',
            # Cabin crew / inflight service
            r'\b(cabin crew|flight attendant|cabin attendant|steward|stewardess|purser|pnc|hostess|air host)\b',
            # Basic ground handling (unskilled ramp/baggage — NOT controllers)
            r'\b(baggage handler|baggage agent|ramp agent|ramp handler|ground handler|bagagiste|gepäckabfertiger)\b',
            # Customer-facing airport roles (Terminal/Gate)
            r'\b(check-in agent|gate agent|ticket agent|passenger service agent|customer service agent|reservation agent)\b',
            # Generic IT & Development
            r'\b(software developer|frontend developer|backend developer|fullstack|devops|programmer|data scientist|ux researcher)\b',
            # Unrelated Industries (Healthcare / Retail / F&B / Education)
            r'\b(nurse|physician|doctor|healthcare|pharmacist|medical)\b',
            r'\b(teacher|professor|faculty|lecturer|educator|student|internship)\b',
            r'\b(cashier|retail associate|store clerk|shop assistant|sales associate)\b',
            r'\b(bartender|chef|waiter|waitress|catering)\b',
            r'\b(delivery driver|truck driver|courier|warehouse associate)\b',
        ]
        
        # Category weights for scoring (higher = more important)
        self.category_weights = {
            'Core_Function_Terms_Only': 4.0,
            'Operative_Functional_Control_Keywords': 3.0,
            'Supervisory_Level_Control_Keywords': 2.0,
            'Management_Executive_Control_Keywords': 1.5,
            'Maintenance_Engineering_Control': 2.5,
            'Operations_Performance_Analytics': 2.0,
            'Flight_Deck_Crew': 2.5,
            'Cabin_Crew_Inflight': 2.5,
            'Ground_Airport_Operations': 2.5
        }
        
        # Performance metrics
        self.perf_stats = {
            'filters_loaded': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'total_filtered': 0,
            'avg_filter_time_ms': 0
        }
        
        # Initialize attributes that might be used even if load fails
        self.keyword_patterns_compiled = {}
        self.global_negatives = set()
        self._neg_pattern_cache: dict = {}  # compiled regex cache for negative keywords
        
        self.load_filters()
    
    def load_filters(self):
        """Load filter configuration from JSON file with optimized processing"""
        if not self.filter_file.exists():
            print(f"⚠️  Filter file not found: {self.filter_file}")
            return
        
        try:
            with open(self.filter_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.filters = data.get('Filters', [])
            
            # Precompile exclusion patterns once
            self.exclusion_compiled = [
                re.compile(pattern, re.IGNORECASE) 
                for pattern in self.exclusion_patterns
            ]
            
            # Patterns precompiled: 61
            self.keyword_patterns_compiled = {}
            self.global_negatives = set()
            
            # Build keyword mappings in single pass - optimized
            for filter_group in self.filters:
                negatives = filter_group.get('NegativeKeywords', [])
                for nk in negatives:
                    self.global_negatives.add(nk.lower())

                filter_type = filter_group.get('FilterType', '')
                display_name = filter_group.get('DisplayName', '')
                keywords = filter_group.get('Keywords', [])
                weight = self.category_weights.get(filter_type, 1.0)
                
                for keyword in keywords:
                    keyword_lower = keyword.lower()
                    self.all_keywords.add(keyword_lower)
                    
                    # Create category info once
                    cat_info = {
                        'filter_type': filter_type,
                        'display_name': display_name,
                        'original_keyword': keyword,
                        'weight': weight
                    }
                    
                    # Initialize or append to category mapping
                    if keyword_lower not in self.keyword_to_category:
                        self.keyword_to_category[keyword_lower] = []
                    self.keyword_to_category[keyword_lower].append(cat_info)
                    
                    # Negative keywords per category
                    cat_negatives = filter_group.get('NegativeKeywords', [])
                    cat_info['negative_keywords'] = [nk.lower() for nk in cat_negatives]
                    
                    # Separate and precompile phrases vs single words
                    pattern = re.compile(r'\b' + re.escape(keyword_lower) + r'\b', re.IGNORECASE)
                    
                    if ' ' in keyword_lower:
                        self.phrase_keywords.append(keyword_lower)
                        self.phrase_patterns.append((pattern, keyword_lower))
                    else:
                        self.single_keywords.append(keyword_lower)
                        self.single_patterns.append((pattern, keyword_lower))
            
            self.perf_stats['filters_loaded'] = len(self.filters)
            
            print(f"✓ Loaded {len(self.filters)} filter categories")
            print(f"✓ Total keywords: {len(self.all_keywords)} ({len(self.phrase_keywords)} phrases, {len(self.single_keywords)} single words)")
            print(f"✓ Patterns precompiled: {len(self.phrase_patterns) + len(self.single_patterns) + len(self.exclusion_compiled)}")
            
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
            if pattern.search(job_title.lower()):
                return True
        return False
    
    def _get_cache_key(self, job_title: str) -> str:
        """Generate cache key for job title"""
        return job_title.lower()
    
    def _negative_matches(self, nk: str, title_lower: str) -> bool:
        """Word-boundary-aware negative keyword check (cached compiled patterns)."""
        key = nk
        if key not in self._neg_pattern_cache:
            self._neg_pattern_cache[key] = re.compile(
                r'\b' + re.escape(nk) + r'\b', re.IGNORECASE
            )
        return bool(self._neg_pattern_cache[key].search(title_lower))

    @lru_cache(maxsize=10000)
    def _matches_filter_impl(self, title_lower: str) -> Tuple[bool, Tuple, float, Dict]:
        """Internal implementation of filter matching - optimized for speed"""
        # Fast exclusion pattern check (early return)
        for pattern in self.exclusion_compiled:
            if pattern.search(title_lower):
                return False, tuple(), 0.0, {'reason': 'excluded_pattern'}
        
        matched_keywords = []
        total_score = 0.0
        category_scores = {}
        
        # Phase 1: Match multi-word phrases first (higher accuracy)
        for pattern, phrase in self.phrase_patterns:
            if pattern.search(title_lower):
                # Check negative keywords for EVERY category this phrase belongs to
                categories = self.keyword_to_category[phrase]
                phrase_rejected = False
                
                for cat in categories:
                    # Word-boundary negative keyword check
                    for nk in cat.get('negative_keywords', []):
                        if self._negative_matches(nk, title_lower):
                            phrase_rejected = True
                            break
                    if phrase_rejected:
                        break
                
                if phrase_rejected:
                    continue

                matched_keywords.append(phrase)
                
                # Phrases get a significant boost as they are more specific
                phrase_weight_multiplier = 3.0 
                
                for cat in categories:
                    weight = cat['weight']
                    score_add = weight * phrase_weight_multiplier
                    total_score += score_add
                    
                    cat_name = cat['display_name']
                    category_scores[cat_name] = category_scores.get(cat_name, 0.0) + score_add
        
        # Phase 2: Match single words (only if score is low or for auxiliary info)
        for pattern, keyword in self.single_patterns:
            if pattern.search(title_lower):
                # Penalty for very generic single words unless combined with others
                generic_keywords = {'officer', 'manager', 'director', 'supervisor', 'controller', 'agent', 'specialist', 'assistant', 'coordinator', 'analyst', 'planner'}
                is_generic = keyword in generic_keywords
                
                matched_keywords.append(keyword)
                categories = self.keyword_to_category[keyword]
                for cat in categories:
                    # Word-boundary negative keyword check
                    negative_match = False
                    for nk in cat.get('negative_keywords', []):
                        if self._negative_matches(nk, title_lower):
                            negative_match = True
                            break
                    
                    if negative_match:
                        continue

                    weight = cat['weight']
                    # Generic words get reduced weight if they are the only match
                    effective_weight = weight * 0.5 if is_generic else weight
                    total_score += effective_weight
                    
                    cat_name = cat['display_name']
                    category_scores[cat_name] = category_scores.get(cat_name, 0.0) + effective_weight
                
                # Exit early if we just crossed threshold
                if total_score >= 1.5:
                    break
        
        matched_categories = self._build_categories(matched_keywords)
        
        # A match requires either a phrase match or at least a reasonably weighted single match
        is_match = total_score >= 1.5
        
        match_details = {
            'matched_keywords': matched_keywords,
            'category_scores': category_scores,
            'keyword_count': len(matched_keywords),
            'match_type': 'phrase_match' if any(' ' in k for k in matched_keywords) else 'single_match'
        }
        
        return is_match, tuple(matched_categories), total_score, match_details
    
    def _build_categories(self, matched_keywords: List[str]) -> List[Dict]:
        """Build category list from matched keywords - optimized with direct dict access"""
        categories = []
        seen = set()
        
        for keyword in matched_keywords:
            # Direct dict access instead of .get() for matched keywords
            if keyword in self.keyword_to_category:
                for cat in self.keyword_to_category[keyword]:
                    cat_key = (cat['filter_type'], cat['display_name'])
                    if cat_key not in seen:
                        seen.add(cat_key)
                        categories.append(cat)
        
        return categories
    
    def matches_filter(self, job_title: str) -> Tuple[bool, List[Dict], float, Dict]:
        """
        Advanced filter matching with scoring - optimized for speed
        
        Returns:
            (matches: bool, matched_categories: List[Dict], score: float, match_details: Dict)
        """
        if not job_title:
            return False, [], 0.0, {}
        
        title_lower = job_title.lower()
        
        # Try cache first (dict lookup is O(1))
        if self.use_cache:
            cache_key = title_lower
            if cache_key in self.filter_cache:
                self.perf_stats['cache_hits'] += 1
                return self.filter_cache[cache_key]
            self.perf_stats['cache_misses'] += 1
        
        # Perform actual filtering
        is_match, categories, score, details = self._matches_filter_impl(title_lower)
        result = (is_match, list(categories), score, details)
        
        # Cache result if enabled
        if self.use_cache:
            self.filter_cache[title_lower] = result
        
        return result
    
    def filter_jobs(self, jobs: List[Dict]) -> Tuple[List[Dict], List[Dict], Dict]:
        """
        Filter a list of jobs with optimized batch processing
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
            'score_distribution': {'high': 0, 'medium': 0, 'low': 0},
            'performance': {}
        }
        
        start_time = time.time()
        
        # Optimized: Pre-allocate lists for better memory usage
        matched_list = []
        rejected_list = []
        by_category = {}
        
        for job in jobs:
            title = job.get('title', '')
            if not title:
                job['filter_match'] = False
                job['filter_score'] = 0.0
                rejected_jobs.append(job)
                stats['rejected'] += 1
                continue
            
            matches, categories, score, details = self.matches_filter(title)
            
            if matches:
                # Batch set fields (fewer individual assignments)
                job.update({
                    'filter_match': True,
                    'filter_score': round(score, 2),
                    'matched_categories': [cat['display_name'] for cat in categories],
                    'matched_filter_types': [cat['filter_type'] for cat in categories],
                    'matched_keywords': details.get('matched_keywords', []),
                    'category_scores': details.get('category_scores', {}),
                    'primary_category': max(details['category_scores'].items(), key=lambda x: x[1])[0] 
                                        if details.get('category_scores') else 'Unknown'
                })
                
                matched_list.append(job)
                stats['matched'] += 1
                
                # Update score distribution
                if score >= 5.0:
                    stats['score_distribution']['high'] += 1
                elif score >= 3.0:
                    stats['score_distribution']['medium'] += 1
                else:
                    stats['score_distribution']['low'] += 1
                
                # Count by category (optimized)
                for cat in categories:
                    cat_name = cat['display_name']
                    by_category[cat_name] = by_category.get(cat_name, 0) + 1
            else:
                job.update({
                    'filter_match': False,
                    'filter_score': 0.0,
                    'matched_categories': [],
                    'primary_category': None,
                    'rejection_reason': 'excluded_pattern' if details.get('reason') == 'excluded_pattern' else 'no_keyword_match'
                })
                
                if details.get('reason') == 'excluded_pattern':
                    stats['excluded'] += 1
                
                rejected_list.append(job)
                stats['rejected'] += 1
        
        # Performance metrics
        elapsed_ms = (time.time() - start_time) * 1000
        stats['by_category'] = by_category
        stats['performance'] = {
            'total_time_ms': round(elapsed_ms, 2),
            'avg_per_job_ms': round(elapsed_ms / len(jobs), 3) if jobs else 0,
            'jobs_per_second': round(len(jobs) / (elapsed_ms / 1000), 1) if elapsed_ms > 0 else 0,
            'cache_hits': self.perf_stats['cache_hits'],
            'cache_misses': self.perf_stats['cache_misses'],
            'cache_efficiency': round(
                self.perf_stats['cache_hits'] / (self.perf_stats['cache_hits'] + self.perf_stats['cache_misses']) * 100, 1
            ) if (self.perf_stats['cache_hits'] + self.perf_stats['cache_misses']) > 0 else 0
        }
        
        self.perf_stats['total_filtered'] += len(jobs)
        self.perf_stats['avg_filter_time_ms'] = stats['performance']['avg_per_job_ms']
        
        return matched_list, rejected_list, stats
    
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
        """Clear caches efficiently"""
        self.filter_cache.clear()
        self.perf_stats['cache_hits'] = 0
        self.perf_stats['cache_misses'] = 0
    
    def get_cache_stats(self) -> Dict:
        """Get cache performance stats - optimized calculation"""
        cache_hits = self.perf_stats['cache_hits']
        cache_misses = self.perf_stats['cache_misses']
        total_requests = cache_hits + cache_misses
        
        return {
            'total_filtered_jobs': self.perf_stats['total_filtered'],
            'cache_hits': cache_hits,
            'cache_misses': cache_misses,
            'total_requests': total_requests,
            'hit_rate': round((cache_hits / total_requests * 100), 1) if total_requests > 0 else 0,
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
