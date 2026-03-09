#!/usr/bin/env python
"""
Test script for Scraper Manager API endpoints
Run with: python test_api.py
"""

import requests
import json
import time
from typing import Dict, Any

# Configuration
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/scrapers/"

# Test credentials (update with your credentials)
USERNAME = "admin"  # Change this
PASSWORD = "admin"  # Change this


class ScraperAPITester:
    def __init__(self):
        self.token = None
        self.session = requests.Session()
    
    def get_auth_token(self) -> bool:
        """Get JWT authentication token"""
        print("\n🔐 Getting authentication token...")
        try:
            response = self.session.post(
                f"{BASE_URL}/api/token/",
                json={"username": USERNAME, "password": PASSWORD}
            )
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get('access')
                self.session.headers.update({
                    'Authorization': f'Bearer {self.token}'
                })
                print("✅ Authentication successful")
                return True
            else:
                print(f"❌ Authentication failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    
    def test_health_check(self):
        """Test health check endpoint"""
        print("\n📊 Testing Health Check...")
        try:
            response = requests.get(f"{API_BASE}health/")
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(json.dumps(data, indent=2))
                print("✅ Health check passed")
            else:
                print(f"❌ Failed: {response.text}")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    def test_list_scrapers(self):
        """Test list scrapers endpoint"""
        print("\n📋 Testing List Scrapers...")
        try:
            response = self.session.get(f"{API_BASE}list/")
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"Found {len(data['scrapers'])} scrapers:")
                for scraper in data['scrapers']:
                    status = "✅ Enabled" if scraper['enabled'] else "❌ Disabled"
                    print(f"  • {scraper['display_name']} ({scraper['name']}) - {status}")
                print("✅ List scrapers test passed")
                return data['scrapers']
            else:
                print(f"❌ Failed: {response.text}")
        except Exception as e:
            print(f"❌ Error: {e}")
        return []
    
    def test_start_scraper(self, scraper_name: str = "signature"):
        """Test starting a scraper"""
        print(f"\n🚀 Testing Start Scraper ({scraper_name})...")
        try:
            response = self.session.post(
                f"{API_BASE}start/",
                json={
                    "scraper_name": scraper_name,
                    "max_jobs": 3
                }
            )
            print(f"Status: {response.status_code}")
            if response.status_code in [200, 202]:
                data = response.json()
                print(json.dumps(data, indent=2))
                print("✅ Scraper started successfully")
                return data.get('job_id')
            else:
                print(f"❌ Failed: {response.text}")
        except Exception as e:
            print(f"❌ Error: {e}")
        return None
    
    def test_job_status(self, job_id: int):
        """Test checking job status"""
        print(f"\n📈 Testing Job Status (ID: {job_id})...")
        try:
            response = self.session.get(f"{API_BASE}status/{job_id}/")
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"Job Status: {data['status']}")
                print(f"Jobs Found: {data['jobs_found']}")
                print(f"Jobs New: {data['jobs_new']}")
                print(f"Execution Time: {data['execution_time']}s")
                print("✅ Job status test passed")
                return data
            else:
                print(f"❌ Failed: {response.text}")
        except Exception as e:
            print(f"❌ Error: {e}")
        return None
    
    def test_get_stats(self):
        """Test getting statistics"""
        print("\n📊 Testing Statistics...")
        try:
            response = self.session.get(f"{API_BASE}stats/")
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"Total Runs: {data['total_runs']}")
                print(f"Success Rate: {data['success_rate']:.1f}%")
                print(f"Total Jobs Scraped: {data['total_jobs_scraped']}")
                print(f"Avg Execution Time: {data['avg_execution_time']:.1f}s")
                print("Jobs by Source:")
                for source, count in data['jobs_by_source'].items():
                    print(f"  • {source}: {count}")
                print("✅ Statistics test passed")
            else:
                print(f"❌ Failed: {response.text}")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    def test_get_history(self, scraper_name: str = None):
        """Test getting history"""
        print("\n📜 Testing History...")
        try:
            url = f"{API_BASE}history/"
            if scraper_name:
                url += f"?scraper={scraper_name}&limit=5"
            
            response = self.session.get(url)
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"Found {len(data['jobs'])} jobs in history")
                for job in data['jobs'][:3]:
                    print(f"  • {job['scraper_name']} - {job['status']} - {job['jobs_found']} jobs")
                print("✅ History test passed")
            else:
                print(f"❌ Failed: {response.text}")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    def test_active_jobs(self):
        """Test getting active jobs"""
        print("\n⚡ Testing Active Jobs...")
        try:
            response = self.session.get(f"{API_BASE}active/")
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"Active Jobs: {data['count']}")
                for job in data['active_jobs']:
                    print(f"  • Job {job['id']}: {job['scraper_name']} - {job['status']}")
                print("✅ Active jobs test passed")
            else:
                print(f"❌ Failed: {response.text}")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    def test_scraper_config(self, scraper_name: str = "signature"):
        """Test getting scraper config"""
        print(f"\n⚙️  Testing Scraper Config ({scraper_name})...")
        try:
            response = self.session.get(f"{API_BASE}config/{scraper_name}/")
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(json.dumps(data, indent=2))
                print("✅ Config test passed")
            else:
                print(f"❌ Failed: {response.text}")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    def run_all_tests(self):
        """Run all API tests"""
        print("=" * 60)
        print("🧪 SCRAPER MANAGER API TEST SUITE")
        print("=" * 60)
        
        # Test health (no auth required)
        self.test_health_check()
        
        # Get authentication token
        if not self.get_auth_token():
            print("\n❌ Cannot proceed without authentication")
            return
        
        # Test all endpoints
        self.test_list_scrapers()
        self.test_get_stats()
        self.test_get_history()
        self.test_active_jobs()
        self.test_scraper_config()
        
        # Test starting a scraper
        job_id = self.test_start_scraper("signature")
        
        if job_id:
            print("\n⏳ Waiting for job to complete...")
            time.sleep(5)
            self.test_job_status(job_id)
        
        print("\n" + "=" * 60)
        print("✅ API TESTS COMPLETED")
        print("=" * 60)


def main():
    """Main function"""
    print("""
╔════════════════════════════════════════════════════════════╗
║     SCRAPER MANAGER API TESTER                             ║
╚════════════════════════════════════════════════════════════╝

Make sure:
1. Django server is running (python manage.py runserver)
2. Update USERNAME and PASSWORD in this script
3. Database is migrated and has data

    """)
    
    tester = ScraperAPITester()
    
    try:
        tester.run_all_tests()
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")


if __name__ == "__main__":
    main()
