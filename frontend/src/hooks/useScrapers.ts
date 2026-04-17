import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { AxiosError } from 'axios';
import api, { dbApi } from '../services/api';
import { useToast } from './useToast';
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
    BulkJobStatusCheckResponse,
    ActiveMonitorResponse,
    TitleFiltersResponse,
} from '../types';

type ApiErrorPayload = {
    error?: string
    message?: string
};

const extractApiError = (error: unknown, fallback: string) => {
    const axiosError = error as AxiosError<ApiErrorPayload> | undefined;
    return String(
        axiosError?.response?.data?.error
        ?? axiosError?.response?.data?.message
        ?? (error as Error | undefined)?.message
        ?? fallback
    );
};

export const useSystemMetrics = (enabled: boolean) => {
    return useQuery({
        queryKey: ['systemMetrics'],
        queryFn: async () => {
            const { data } = await api.get('/metrics/');
            return data as SystemMetrics;
        },
        enabled,
        refetchInterval: 5000,
    });
};

export const useScrapers = () => {
    return useQuery({
        queryKey: ['scrapers'],
        queryFn: async () => {
            const { data } = await api.get('/list/');
            return data.scrapers as Scraper[];
        },
        refetchInterval: 60000,
        refetchIntervalInBackground: true,
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
        refetchInterval: 15000,
        refetchIntervalInBackground: true,
    });
};

export const useActiveMonitor = (enabled: boolean) => {
    return useQuery({
        queryKey: ['activeMonitor'],
        queryFn: async () => {
            const { data } = await api.get('/active/');
            return data as ActiveMonitorResponse;
        },
        enabled,
        refetchInterval: 15000,
        refetchIntervalInBackground: true,
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
        refetchInterval: 60000,
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
        refetchInterval: 60000,
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

export const useTitleFilters = (enabled: boolean) => {
    return useQuery({
        queryKey: ['titleFilters'],
        queryFn: async () => {
            const { data } = await api.get('/title-filters/');
            return data as TitleFiltersResponse;
        },
        enabled,
    });
};

export const useManagedJobs = (enabled: boolean, page = 1, limit = 20, search = '', status = '', source = '', verified = 'all') => {
    return useQuery({
        queryKey: ['managedJobs', page, limit, search, status, source, verified],
        queryFn: async () => {
            const params = new URLSearchParams({ page: String(page), limit: String(limit) });
            if (search.trim()) params.set('q', search.trim());
            if (status.trim()) params.set('status', status.trim());
            if (source.trim()) params.set('source', source.trim());
            if (verified.trim() && verified !== 'all') params.set('verified', verified.trim());
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
        refetchInterval: 60000,
    });
};

export const useScraperActions = () => {
    const queryClient = useQueryClient();
    const { showToast } = useToast();

    const startScraper = useMutation({
        mutationFn: async (scraperName: string) => {
            await api.post('/start/', { scraper_name: scraperName });
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['scrapers'] });
            queryClient.invalidateQueries({ queryKey: ['activeJobs'] });
            queryClient.invalidateQueries({ queryKey: ['stats'] });
            queryClient.invalidateQueries({ queryKey: ['history'] });
        },
        onError: (error: unknown) => {
            const status = (error as AxiosError | undefined)?.response?.status;
            if (status === 409) {
                showToast({
                    level: 'info',
                    message: extractApiError(error, 'Scraper is already running.'),
                });
                return;
            }
            showToast({
                level: 'error',
                message: extractApiError(error, 'Failed to start scraper.'),
            });
        },
    });

    const startAllScrapers = useMutation({
        mutationFn: async () => {
            const { data } = await api.post('/start-all/');
            return data as { queued_count?: number; message?: string };
        },
        onSuccess: (data) => {
            queryClient.invalidateQueries({ queryKey: ['scrapers'] });
            queryClient.invalidateQueries({ queryKey: ['activeJobs'] });
            queryClient.invalidateQueries({ queryKey: ['activeMonitor'] });
            queryClient.invalidateQueries({ queryKey: ['stats'] });
            queryClient.invalidateQueries({ queryKey: ['history'] });
            showToast({
                level: 'success',
                message: data?.queued_count ? `Queued a sequential run for ${data.queued_count} scraper(s).` : (data?.message || 'Sequential scraper run queued.'),
            });
        },
        onError: (error: unknown) => {
            showToast({
                level: 'error',
                message: extractApiError(error, 'Failed to start all scrapers.'),
            });
        },
    });

    const cancelJob = useMutation({
        mutationFn: async (jobId: number | string) => {
            await api.delete(`/cancel/${jobId}/`);
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['scrapers'] });
            queryClient.invalidateQueries({ queryKey: ['activeJobs'] });
            queryClient.invalidateQueries({ queryKey: ['history'] });
            queryClient.invalidateQueries({ queryKey: ['stats'] });
        },
        onError: (error: unknown) => {
            showToast({
                level: 'error',
                message: extractApiError(error, 'Failed to cancel scraper job.'),
            });
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

    const updateTitleFilter = useMutation({
        mutationFn: async ({ action, keyword, filterType }: { action: 'add' | 'remove'; keyword: string; filterType?: string }) => {
            const { data } = await api.put('/title-filters/', {
                action,
                keyword,
                filter_type: filterType || '',
            });
            return data as { changed?: boolean; message?: string };
        },
        onSuccess: (data, variables) => {
            queryClient.invalidateQueries({ queryKey: ['titleFilters'] });
            showToast({
                level: 'success',
                message: data?.message || `Keyword ${variables.action} operation completed.`,
            });
        },
        onError: (error: unknown) => {
            showToast({
                level: 'error',
                message: extractApiError(error, 'Failed to update title filters.'),
            });
        },
    });

    const updateManagedJob = useMutation({
        mutationFn: async ({ jobId, job }: { jobId: number | string; job: Partial<ManagedJob> }) => {
            const { data } = await api.patch(`/jobs/${jobId}/`, job);
            return data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['managedJobs'] });
            queryClient.invalidateQueries({ queryKey: ['recentJobs'] });
            queryClient.invalidateQueries({ queryKey: ['stats'] });
            showToast({
                level: 'success',
                message: 'Job metadata updated successfully.',
            });
        },
        onError: (error: unknown) => {
            showToast({
                level: 'error',
                message: extractApiError(error, 'Failed to update job metadata.'),
            });
        },
    });

    const checkJobStatus = useMutation({
        mutationFn: async (jobId: number | string) => {
            const { data } = await api.post(`/jobs/${jobId}/check-status/`);
            return data;
        },
        onSuccess: (data: { result?: string } | undefined) => {
            queryClient.invalidateQueries({ queryKey: ['managedJobs'] });
            if (data?.result === 'skipped_verified') {
                showToast({
                    level: 'info',
                    message: 'Verified jobs are excluded from automated checks.',
                });
                return;
            }
            showToast({
                level: 'success',
                message: 'Live status check completed.',
            });
        },
        onError: (error: unknown) => {
            showToast({
                level: 'error',
                message: extractApiError(error, 'Live status check failed.'),
            });
        },
    });

    const checkJobStatusBulk = useMutation({
        mutationFn: async ({
            q = '',
            status = '',
            source = '',
            maxChecks = 200,
        }: {
            q?: string
            status?: string
            source?: string
            maxChecks?: number
        }) => {
            const { data } = await api.post('/jobs/check-status/bulk/', {
                q,
                status,
                source,
                max_checks: maxChecks,
            });
            return data as BulkJobStatusCheckResponse;
        },
        onSuccess: (data) => {
            queryClient.invalidateQueries({ queryKey: ['managedJobs'] });
            queryClient.invalidateQueries({ queryKey: ['scrapedRecords'] });
            queryClient.invalidateQueries({ queryKey: ['recentJobs'] });
            if (data.results) {
                const summary = data.results;
                showToast({
                    level: 'success',
                    message: `Checked ${summary.checked}. Closed ${summary.closed_detected}. Skipped verified ${summary.skipped_verified}.`,
                    durationMs: 5000,
                });
                return;
            }

            showToast({
                level: 'success',
                message: data.message || 'Bulk validation queued in the background.',
                durationMs: 4000,
            });
        },
        onError: (error: unknown) => {
            showToast({
                level: 'error',
                message: extractApiError(error, 'Bulk validation failed.'),
            });
        },
    });

    return {
        startScraper,
        startAllScrapers,
        cancelJob,
        updateConfig,
        updateTitleFilter,
        updateManagedJob,
        checkJobStatus,
        checkJobStatusBulk,
    };
};

export const useDatabase = (enabled: boolean) => {
    const queryClient = useQueryClient();
    const { showToast } = useToast();

    const collections = useQuery({
        queryKey: ['dbCollections'],
        queryFn: async () => {
            const { data } = await dbApi.get('/collections/');
            return data.collections as string[];
        },
        enabled,
    });

    const backups = useQuery({
        queryKey: ['dbBackups'],
        queryFn: async () => {
            const { data } = await dbApi.get('/backups/');
            return data.backups as any[];
        },
        enabled,
        refetchInterval: 10000,
    });

    const createBackup = useMutation({
        mutationFn: async (selectedCollections?: string[]) => {
            const { data } = await dbApi.post('/backup/', { collections: selectedCollections });
            return data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['dbBackups'] });
            showToast({
                level: 'success',
                message: 'Backup created successfully.',
            });
        },
        onError: (error: unknown) => {
            showToast({
                level: 'error',
                message: extractApiError(error, 'Failed to create backup.'),
            });
        },
    });

    const restoreBackup = useMutation({
        mutationFn: async ({ backupId, collection, dropExisting }: { backupId: string; collection?: string; dropExisting: boolean }) => {
            const { data } = await dbApi.post('/restore/', { 
                backup_id: backupId, 
                collection, 
                drop_existing: dropExisting 
            });
            return data;
        },
        onSuccess: () => {
            showToast({
                level: 'success',
                message: 'Database restoration completed.',
            });
            // We might want to invalidate everything if a full restore happened
            queryClient.invalidateQueries();
        },
        onError: (error: unknown) => {
            showToast({
                level: 'error',
                message: extractApiError(error, 'Restoration failed.'),
            });
        },
    });

    const deleteBackup = useMutation({
        mutationFn: async (backupId: string) => {
            await dbApi.delete(`/backups/${backupId}/`);
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['dbBackups'] });
            showToast({
                level: 'success',
                message: 'Backup deleted.',
            });
        },
        onError: (error: unknown) => {
            showToast({
                level: 'error',
                message: extractApiError(error, 'Failed to delete backup.'),
            });
        },
    });

    return {
        collections,
        backups,
        createBackup,
        restoreBackup,
        deleteBackup,
    };
};

