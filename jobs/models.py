from django.db import models
from django.utils import timezone


class Job(models.Model):
    title = models.CharField(max_length=500, db_index=True)
    normalized_title = models.CharField(max_length=500, null=True, blank=True, db_index=True)
    company = models.CharField(max_length=200, db_index=True)
    company_id = models.IntegerField(null=True, blank=True, db_index=True)

    country_code = models.CharField(max_length=3, null=True, blank=True, db_index=True)
    location = models.CharField(max_length=200, null=True, blank=True)
    operation_type = models.CharField(max_length=20, null=True, blank=True, db_index=True)
    job_category = models.CharField(max_length=50, null=True, blank=True, db_index=True)
    sub_role = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    is_verified = models.BooleanField(default=False, db_index=True)
    status = models.CharField(max_length=20, default="new", db_index=True)
    source = models.CharField(max_length=50, null=True, blank=True, db_index=True)

    senior_flag = models.BooleanField(default=False, db_index=True)
    senior_override = models.BooleanField(null=True, blank=True, db_index=True)
    is_senior_position = models.BooleanField(default=False, db_index=True)

    posted_date = models.DateField(null=True, blank=True, db_index=True)
    expiration_date = models.DateField(null=True, blank=True, db_index=True)
    retrieved_date = models.DateTimeField(default=timezone.now)
    last_checked = models.DateTimeField(null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)

    url = models.URLField(max_length=1000, unique=True, db_index=True)
    description = models.TextField(null=True, blank=True)
    raw_json = models.JSONField(null=True, blank=True)

    salary_min = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    salary_max = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    salary_currency = models.CharField(max_length=3, default="USD")
    is_remote = models.BooleanField(default=False)
    salary_visible = models.BooleanField(default=True)
    license_required = models.BooleanField(default=False)
    training_required = models.BooleanField(default=False)
    on_job_training = models.BooleanField(default=False)

    # Keep FK shape compatible with backend jobs table usage.
    posted_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="scraper_posted_jobs",
    )

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "jobs"
        managed = True


class CompanyMapping(models.Model):
    company_name = models.CharField(max_length=200, db_index=True)
    normalized_name = models.CharField(max_length=200, unique=True, db_index=True)
    operation_type = models.CharField(max_length=20, null=True, blank=True, db_index=True)
    country_code = models.CharField(max_length=3, null=True, blank=True, db_index=True)
    notes = models.TextField(null=True, blank=True)

    auto_created = models.BooleanField(default=False, db_index=True)
    needs_review = models.BooleanField(default=True, db_index=True)
    reviewed_by = models.CharField(max_length=100, null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    total_jobs = models.IntegerField(default=0)
    active_jobs = models.IntegerField(default=0)
    last_job_date = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "company_mapping"
        managed = True
