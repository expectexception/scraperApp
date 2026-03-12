export type Scraper = {
    name: string
    display_name: string
    description: string
    enabled: boolean
}

export type ActiveJob = {
    id: number
    scraper_name: string
    status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
    started_at: string
    triggered_by?: string
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
    id: number
    scraper_name: string
    status: string
    started_at: string
    completed_at: string | null
    execution_time: number | null
    jobs_found: number
    jobs_new: number
}

export type RecentJob = {
    id: number
    title: string
    company: string
    source: string
    url: string
    last_scraped: string
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

export type View = 'dashboard' | 'history' | 'configs' | 'catalog'
