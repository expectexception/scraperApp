import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';
import type { Scraper, ActiveJob, Stats, HistoryJob, RecentJob, ScraperConfig, SystemMetrics } from '../types';

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
            return data.status as string;
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

export const useHistory = (enabled: boolean, page = 1, limit = 20) => {
    return useQuery({
        queryKey: ['history', page, limit],
        queryFn: async () => {
            const { data } = await api.get(`/history/?page=${page}&limit=${limit}`);
            return data.jobs as HistoryJob[];
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

export const useScraperActions = () => {
    const queryClient = useQueryClient();

    const startScraper = useMutation({
        mutationFn: async (scraperName: string) => {
            await api.post('/start/', { scraper_name: scraperName });
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['activeJobs'] });
        },
    });

    const startAllScrapers = useMutation({
        mutationFn: async () => {
            await api.post('/start-all/');
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['activeJobs'] });
        },
    });

    const cancelJob = useMutation({
        mutationFn: async (jobId: number) => {
            await api.delete(`/cancel/${jobId}/`);
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['activeJobs'] });
        },
    });

    const updateConfig = useMutation({
        mutationFn: async ({ name, config }: { name: string; config: ScraperConfig }) => {
            await api.patch(`/config/${name}/update/`, config);
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['configs'] });
        },
    });

    return {
        startScraper,
        startAllScrapers,
        cancelJob,
        updateConfig,
    };
};
