import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';
import type {
    Scraper,
    ActiveJob,
    Stats,
    HistoryResponse,
    RecentJob,
    ScraperConfig,
    SystemMetrics,
    HealthStatus,
    ManagedJobsResponse,
    ManagedJob,
    ScrapedRecordsResponse,
    SchedulerOverview,
} from '../types';

export const useSystemMetrics = (enabled: boolean) => {
    return useQuery({
        queryKey: ['systemMetrics'],
        queryFn: async () => {
            const { data } = await api.get('/metrics/');
            return data as SystemMetrics;
        },
        enabled,
        refetchInterval: 2000, // Frequent updates for real-time monitoring
    });
};

export const useScrapers = () => {
    return useQuery({
        queryKey: ['scrapers'],
        queryFn: async () => {
            const { data } = await api.get('/list/');
            return data.scrapers as Scraper[];
        },
    });
};

export const useHealth = () => {
    return useQuery({
        queryKey: ['health'],
        queryFn: async () => {
            const { data } = await api.get('/health/');
            return (data.status === 'healthy' ? 'ok' : 'unreachable') as HealthStatus;
        },
        refetchInterval: 30000,
    });
};

export const useActiveJobs = (enabled: boolean) => {
    return useQuery({
        queryKey: ['activeJobs'],
        queryFn: async () => {
            const { data } = await api.get('/active/');
            return data.active_jobs as ActiveJob[];
        },
        enabled,
        refetchInterval: 5000,
    });
};

export const useStats = (enabled: boolean) => {
    return useQuery({
        queryKey: ['stats'],
        queryFn: async () => {
            const { data } = await api.get('/stats/');
            return data as Stats;
        },
        enabled,
        refetchInterval: 10000,
    });
};

export const useHistory = (enabled: boolean, page = 1, limit = 20, search = '') => {
    return useQuery({
        queryKey: ['history', page, limit, search],
        queryFn: async () => {
            const params = new URLSearchParams({ page: String(page), limit: String(limit) });
            if (search.trim()) {
                params.set('q', search.trim());
            }
            const { data } = await api.get(`/history/?${params.toString()}`);
            return data as HistoryResponse;
        },
        enabled,
    });
};

export const useRecentJobs = (enabled: boolean, limit = 20) => {
    return useQuery({
        queryKey: ['recentJobs', limit],
        queryFn: async () => {
            const { data } = await api.get(`/recent-jobs/?limit=${limit}`);
            return data.jobs as RecentJob[];
        },
        enabled,
        refetchInterval: 15000,
    });
};

export const useConfigs = (enabled: boolean) => {
    return useQuery({
        queryKey: ['configs'],
        queryFn: async () => {
            const { data } = await api.get('/configs/');
            return data.configs as Record<string, ScraperConfig>;
        },
        enabled,
    });
};

export const useManagedJobs = (enabled: boolean, page = 1, limit = 20, search = '', status = '', source = '') => {
    return useQuery({
        queryKey: ['managedJobs', page, limit, search, status, source],
        queryFn: async () => {
            const params = new URLSearchParams({ page: String(page), limit: String(limit) });
            if (search.trim()) params.set('q', search.trim());
            if (status.trim()) params.set('status', status.trim());
            if (source.trim()) params.set('source', source.trim());
            const { data } = await api.get(`/jobs/?${params.toString()}`);
            return data as ManagedJobsResponse;
        },
        enabled,
    });
};

export const useScrapedRecords = (enabled: boolean, page = 1, limit = 20, search = '', source = '') => {
    return useQuery({
        queryKey: ['scrapedRecords', page, limit, search, source],
        queryFn: async () => {
            const params = new URLSearchParams({ page: String(page), limit: String(limit) });
            if (search.trim()) params.set('q', search.trim());
            if (source.trim()) params.set('source', source.trim());
            const { data } = await api.get(`/scraped-records/?${params.toString()}`);
            return data as ScrapedRecordsResponse;
        },
        enabled,
    });
};

export const useSchedulerOverview = (enabled: boolean) => {
    return useQuery({
        queryKey: ['schedulerOverview'],
        queryFn: async () => {
            const { data } = await api.get('/scheduler/overview/');
            return data as SchedulerOverview;
        },
        enabled,
        refetchInterval: 30000,
    });
};

export const useScraperActions = () => {
    const queryClient = useQueryClient();

    const startScraper = useMutation({
        mutationFn: async (scraperName: string) => {
            await api.post('/start/', { scraper_name: scraperName });
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['activeJobs'] });
            queryClient.invalidateQueries({ queryKey: ['stats'] });
            queryClient.invalidateQueries({ queryKey: ['history'] });
        },
    });

    const startAllScrapers = useMutation({
        mutationFn: async () => {
            await api.post('/start-all/');
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['activeJobs'] });
            queryClient.invalidateQueries({ queryKey: ['stats'] });
            queryClient.invalidateQueries({ queryKey: ['history'] });
        },
    });

    const cancelJob = useMutation({
        mutationFn: async (jobId: number) => {
            await api.delete(`/cancel/${jobId}/`);
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['activeJobs'] });
            queryClient.invalidateQueries({ queryKey: ['history'] });
            queryClient.invalidateQueries({ queryKey: ['stats'] });
        },
    });

    const updateConfig = useMutation({
        mutationFn: async ({ name, config }: { name: string; config: ScraperConfig }) => {
            await api.patch(`/config/${name}/update/`, config);
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['configs'] });
            queryClient.invalidateQueries({ queryKey: ['scrapers'] });
            queryClient.invalidateQueries({ queryKey: ['schedulerOverview'] });
        },
    });

    const updateManagedJob = useMutation({
        mutationFn: async ({ jobId, job }: { jobId: number; job: Partial<ManagedJob> }) => {
            const { data } = await api.patch(`/jobs/${jobId}/`, job);
            return data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['managedJobs'] });
            queryClient.invalidateQueries({ queryKey: ['recentJobs'] });
            queryClient.invalidateQueries({ queryKey: ['stats'] });
        },
    });

    const checkJobStatus = useMutation({
        mutationFn: async (jobId: number) => {
            const { data } = await api.post(`/jobs/${jobId}/check-status/`);
            return data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['managedJobs'] });
        },
    });

    return {
        startScraper,
        startAllScrapers,
        cancelJob,
        updateConfig,
        updateManagedJob,
        checkJobStatus,
    };
};
