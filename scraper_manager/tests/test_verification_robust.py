import io
import unittest.mock as mock
from django.test import TestCase
from django.core.management import call_command
from django.utils import timezone
from datetime import timedelta
from asgiref.sync import async_to_sync

from jobs.models import Job
from django.contrib.auth.models import User
from scraper_manager.db_manager import DjangoDBManager


class JobVerificationRobustTests(TestCase):
    def setUp(self):
        self.db_manager = DjangoDBManager()
        self.admin_user = User.objects.create_user(
            username="admin_tester", password="pass"
        )

    def test_keyword_closure_detection(self):
        """Test that various closed keywords are correctly identified"""
        test_cases = [
            (
                "This position has been filled",
                False,
                "closed_keyword:position has been filled",
            ),
            (
                "The role has already been filled",
                False,
                "closed_keyword:has already been filled",
            ),
            (
                "This vacancy is no longer being advertised",
                False,
                "closed_keyword:is no longer being advertised",
            ),
            (
                "This job is no longer available",
                False,
                "closed_keyword:this job is no longer available",
            ),
            ("404 Error: Page Not Found", False, "closed_keyword:page not found"),
            ("This is an active and exciting job listing!", True, "ok"),
        ]

        for body, expected_active, reason_snippet in test_cases:
            mock_resp = mock.Mock()
            mock_resp.status_code = 200
            mock_resp.text = body
            mock_resp.content = body.encode("utf-8")
            mock_resp.url = "http://example.com/job"
            mock_resp.history = []

            with mock.patch("curl_cffi.requests.get", return_value=mock_resp):
                is_active, reason = async_to_sync(self.db_manager.check_job_active)(
                    "http://example.com/job"
                )
                self.assertEqual(
                    is_active, expected_active, f"Failed for body: {body[:30]}..."
                )
                if not expected_active:
                    self.assertIn(reason_snippet, reason)

    def test_management_command_checks_all_jobs(self):
        """Test that verify_job_active command checks all active jobs"""
        # 1. Create a recruiter-posted job
        recruiter_job = Job.objects.create(
            title="Recruiter Job",
            company="Test Co",
            url="http://example.com/recruiter",
            status="active",
            posted_by=self.admin_user,
            last_checked=timezone.now() - timedelta(days=10),
            source="manual",
        )

        # 2. Create a scraped job
        scraped_job = Job.objects.create(
            title="Scraped Job",
            company="Scraped Co",
            url="http://example.com/scraped",
            status="active",
            posted_by=None,
            last_checked=timezone.now() - timedelta(days=10),
            source="aviation",
        )

        out = io.StringIO()
        # Mocking check_job_active to return closed for everything it processes
        with mock.patch(
            "scraper_manager.db_manager.DjangoDBManager.check_job_active",
            return_value=(False, "mock_closed"),
        ):
            call_command("verify_job_active", age_days=5, dry_run=False, stdout=out)

        # Refresh from DB
        recruiter_job.refresh_from_db()
        scraped_job.refresh_from_db()

        # Both jobs should be closed since we check all active/new jobs now
        self.assertEqual(recruiter_job.status, "closed")
        self.assertEqual(scraped_job.status, "closed")
