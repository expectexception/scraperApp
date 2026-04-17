export type ScraperJobStatus = 'pending' | 'queued' | 'running' | 'retrying' | 'cancelling' | 'completed' | 'failed' | 'cancelled'

export type Scraper = {
    name: string
    display_name: string
    description: string
    enabled: boolean
    base_url?: string
    max_jobs?: number | null
    max_pages?: number | null
    timeout?: number
    retry_count?: number
    active_jobs?: number
    schedule?: SchedulerSchedule
}

export type ActiveJob = {
    id: number | string
    scraper_name: string
    status: ScraperJobStatus
    started_at: string
    triggered_by?: string
    task_id?: string
    worker_name?: string
    progress?: number
    progress_message?: string
    heartbeat_at?: string | null
    cancel_requested_at?: string | null
    completed_at?: string | null
    execution_time?: number | null
    jobs_found?: number
    jobs_new?: number
    jobs_updated?: number
    jobs_duplicate?: number
    liveness?: {
        is_stale: boolean
        task_state?: string | null
        pid_alive?: boolean | null
        last_seen_at?: string | null
        heartbeat_age_seconds?: number | null
        stale_timeout_seconds?: number
    }
}

export type RealtimeEvent = {
    type: string
    event?: string
    timestamp: string
    job?: ActiveJob
    extra?: Record<string, unknown>
}

export type ActiveMonitorResponse = {
    active_jobs: ActiveJob[]
    recently_finished: ActiveJob[]
    count: number
}

export type Stats = {
    total_runs: number
    completed_runs: number
    failed_runs: number
    success_rate: number
    total_jobs_scraped: number
    total_new_jobs: number
    avg_execution_time?: number
}

export type HistoryJob = {
    id: number | string
    scraper_name: string
    status: string
    started_at: string
    completed_at: string | null
    execution_time: number | null
    jobs_found: number
    jobs_new: number
    jobs_updated?: number
    jobs_duplicate?: number
    triggered_by?: string
}

export type PaginationMeta = {
    page: number
    page_size: number
    total: number
    pages: number
}

export type HistoryResponse = {
    jobs: HistoryJob[]
    pagination: PaginationMeta
}

export type RecentJob = {
    id: number | string
    job_id?: string
    title: string
    company: string
    source: string
    url: string
    last_scraped: string
    scrape_count?: number
}

export type ManagedJob = {
    id: number | string
    title: string
    company: string
    location: string | null
    source: string | null
    status: string
    url: string
    operation_type: string | null
    job_category: string | null
    sub_role: string | null
    country_code: string | null
    is_verified: boolean
    posted_date: string | null
    retrieved_date: string
    description: string | null
    salary_currency: string
    is_remote: boolean
    last_checked: string | null
}

export type ManagedJobsResponse = {
    jobs: ManagedJob[]
    pagination: PaginationMeta
    summary: {
        total: number
        new: number
        active: number
        closed: number
        verified: number
    }
    sources: string[]
}

export type BulkJobStatusCheckResponse = {
    message: string
    task_id?: string
    queued?: boolean
    filters: {
        q: string
        status: string
        source: string
        only_scraped: boolean
        skip_verified: boolean
        max_checks: number
    }
    results?: {
        checked: number
        skipped_verified: number
        skipped_no_url: number
        failed_requests: number
        status_changed: number
        closed_detected: number
        total_candidates: number
    }
}

export type TitleFilterGroup = {
    filter_type: string
    display_name: string
    keyword_count: number
}

export type TitleFiltersResponse = {
    filter_name: string
    description: string
    file_path: string
    groups: TitleFilterGroup[]
    keywords: string[]
    count: number
}

export type ScrapedRecord = {
    id: number | string
    job_id: string
    url: string
    source: string
    title: string
    company: string
    scrape_count: number
    is_active: boolean
    first_scraped: string
    last_scraped: string
}

export type ScrapedRecordsResponse = {
    records: ScrapedRecord[]
    pagination: PaginationMeta
    sources: string[]
}

export type ScraperConfig = {
    scraper_name: string
    is_enabled: boolean
    max_jobs: number | null
    max_pages: number | null
    timeout: number
    retry_count: number
    schedule_enabled: boolean
    schedule_cron: string
    description: string
}

export type SchedulerSchedule = {
    scraper_name: string
    schedule_enabled: boolean
    schedule_cron: string
    task_name?: string
    celery_beat_available: boolean
    periodic_task_enabled: boolean
    periodic_task_exists: boolean
    last_run?: string | null
}

export type SchedulerOverview = {
    celery_beat_available: boolean
    configured_scrapers: number
    scheduled_scrapers: number
    active_periodic_tasks: number
    schedules: SchedulerSchedule[]
}

export type SystemMetrics = {
    cpu: {
        percent: number
        count: number
        freq: number
    }
    memory: {
        total: number
        available: number
        percent: number
        used: number
    }
    disk: {
        total: number
        used: number
        free: number
        percent: number
    }
    process: {
        memory_info: number
        threads: number
    }
    timestamp: string
}

export type HealthStatus = 'ok' | 'checking' | 'unreachable'

export type View = 'dashboard' | 'jobs' | 'scraped' | 'history' | 'configs' | 'catalog' | 'database'
