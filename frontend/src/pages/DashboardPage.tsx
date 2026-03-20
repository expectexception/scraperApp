import React from 'react';
import { useStats, useActiveJobs, useRecentJobs, useScraperActions } from '../hooks/useScrapers';
import { StatTile } from '../components/features/StatTile';
import { MetricsMonitor } from '../components/features/MetricsMonitor';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { useAuth } from '../hooks/useAuth';
import {
    PlayCircle,
    RotateCcw,
    Zap,
    CheckCircle2,
    XCircle,
    Timer,
    Clock,
    ExternalLink,
    Loader2
} from 'lucide-react';
import { formatDate, formatDuration } from '../services/utils';

export const DashboardPage: React.FC = () => {
    const { isLoggedIn } = useAuth();
    const { data: stats, isLoading: statsLoading } = useStats(isLoggedIn);
    const { data: activeJobs, isLoading: jobsLoading } = useActiveJobs(isLoggedIn);
    const { data: recentJobs, isLoading: recentLoading } = useRecentJobs(isLoggedIn, 5);
    const { startAllScrapers, cancelJob } = useScraperActions();

    return (
        <div className="space-y-8">
            {/* Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-6">
                <StatTile
                    label="Total Runs"
                    value={stats?.total_runs ?? 0}
                    icon={RotateCcw}
                    isLoading={statsLoading}
                />
                <StatTile
                    label="Completed"
                    value={stats?.completed_runs ?? 0}
                    icon={CheckCircle2}
                    isLoading={statsLoading}
                    className="border-success/20"
                />
                <StatTile
                    label="Failed"
                    value={stats?.failed_runs ?? 0}
                    icon={XCircle}
                    isLoading={statsLoading}
                    className="border-danger/20"
                />
                <StatTile
                    label="Success Rate"
                    value={`${(stats?.success_rate ?? 0).toFixed(1)}%`}
                    icon={Zap}
                />
                <StatTile
                    label="Jobs Scraped"
                    value={stats?.total_jobs_scraped ?? 0}
                    icon={RotateCcw}
                />
                <StatTile
                    label="Avg Runtime"
                    value={formatDuration(stats?.avg_execution_time ?? 0)}
                    icon={Timer}
                />
            </div>

            <div className="grid grid-cols-1 xl:grid-cols-2 gap-8 mb-8">
                <MetricsMonitor />
                <Card
                    title="Scraper Statistics"
                    subtitle="Real-time performance and system health"
                >
                    <div className="grid grid-cols-2 gap-4 h-full">
                        <div className="p-5 rounded-3xl bg-white/[0.02] border border-white/[0.05] flex flex-col justify-center">
                            <p className="text-[10px] font-black text-secondary uppercase tracking-[0.2em] mb-2">Success Rate</p>
                            <p className="text-3xl font-black text-white">{(stats?.success_rate ?? 0).toFixed(1)}%</p>
                            <div className="mt-4 w-full bg-white/5 h-1 rounded-full overflow-hidden">
                                <div
                                    className="bg-success h-full transition-all duration-1000"
                                    style={{ width: `${stats?.success_rate ?? 0}%` }}
                                />
                            </div>
                        </div>
                        <div className="p-5 rounded-3xl bg-white/[0.02] border border-white/[0.05] flex flex-col justify-center">
                            <p className="text-[10px] font-black text-secondary uppercase tracking-[0.2em] mb-2">Total Jobs Found</p>
                            <p className="text-3xl font-black text-white">{stats?.total_jobs_scraped ?? 0}</p>
                            <p className="text-[9px] text-secondary mt-2 font-bold uppercase">Total indexed entries</p>
                        </div>
                    </div>
                </Card>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Active Jobs Section */}
                <Card
                    className="lg:col-span-2"
                    title={`Active Scrapers (${activeJobs?.length ?? 0})`}
                    subtitle="Live scraper status and management"
                    footer={
                        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 w-full">
                            <p className="text-xs text-secondary italic">Auto-refreshing every 5 seconds</p>
                            <Button
                                size="sm"
                                className="gap-2 w-full sm:w-auto"
                                onClick={() => startAllScrapers.mutate()}
                                isLoading={startAllScrapers.isPending}
                            >
                                <PlayCircle className="w-4 h-4" />
                                Run All Scrapers
                            </Button>
                        </div>
                    }
                >
                    <div className="overflow-x-auto">
                        <table className="w-full min-w-[720px] text-left border-collapse">
                            <thead>
                                <tr className="border-b border-white/5">
                                    <th className="py-4 px-6 text-[10px] font-bold text-secondary uppercase tracking-widest">ID</th>
                                    <th className="py-4 px-6 text-[10px] font-bold text-secondary uppercase tracking-widest">Scraper</th>
                                    <th className="py-4 px-6 text-[10px] font-bold text-secondary uppercase tracking-widest">Status</th>
                                    <th className="py-4 px-6 text-[10px] font-bold text-secondary uppercase tracking-widest">Started</th>
                                    <th className="py-4 px-6 text-[10px] font-bold text-secondary uppercase tracking-widest text-right">Actions</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-white/5">
                                {!activeJobs?.length && !jobsLoading ? (
                                    <tr>
                                        <td colSpan={5} className="py-12 text-center text-secondary text-sm">
                                            No active scrapers. Ready to run.
                                        </td>
                                    </tr>
                                ) : activeJobs?.map(job => (
                                    <tr key={job.id} className="group hover:bg-white/[0.02] transition-colors">
                                        <td className="py-4 px-6 text-xs font-mono text-secondary">#{job.id}</td>
                                        <td className="py-4 px-6 font-semibold text-sm">{job.scraper_name}</td>
                                        <td className="py-4 px-6">
                                            <Badge variant={job.status === 'running' ? 'info' : 'warning'}>
                                                {job.status === 'running' && <Loader2 className="w-3 h-3 animate-spin" />}
                                                {job.status}
                                            </Badge>
                                        </td>
                                        <td className="py-4 px-6 text-xs text-secondary flex items-center gap-2">
                                            <Clock className="w-3.5 h-3.5" />
                                            {formatDate(job.started_at)}
                                        </td>
                                        <td className="py-4 px-6 text-right">
                                            {job.status === 'running' || job.status === 'pending' ? (
                                                <Button
                                                    variant="danger"
                                                    size="sm"
                                                    className="px-4 font-black transition-all hover:scale-105 active:scale-95 shadow-glow-danger"
                                                    onClick={() => cancelJob.mutate(job.id)}
                                                    isLoading={cancelJob.isPending && String(cancelJob.variables) === String(job.id)}
                                                >
                                                    Abort
                                                </Button>
                                            ) : '-'}
                                        </td>
                                    </tr>
                                ))}
                                {jobsLoading && (
                                    <tr>
                                        <td colSpan={5} className="py-12 text-center">
                                            <Loader2 className="w-8 h-8 animate-spin text-primary mx-auto" />
                                        </td>
                                    </tr>
                                )}
                            </tbody>
                        </table>
                    </div>
                </Card>

                {/* Recent Findings Section */}
                <div className="space-y-6">
                    <Card
                        title="Recent Activity"
                        subtitle="Latest jobs scraped across sources"
                    >
                        <div className="space-y-4">
                            {recentLoading ? (
                                <div className="py-12 flex justify-center">
                                    <Loader2 className="w-6 h-6 animate-spin text-primary" />
                                </div>
                            ) : recentJobs?.map(job => (
                                <div key={job.id} className="p-4 rounded-xl bg-white/[0.02] border border-white/5 hover:border-primary/20 transition-all hover:bg-white/[0.05] group">
                                    <div className="flex justify-between items-start mb-2">
                                        <Badge variant="neutral">{job.source}</Badge>
                                        <span className="text-[10px] text-secondary font-medium">{formatDate(job.last_scraped)}</span>
                                    </div>
                                    <h4 className="font-bold text-sm text-white line-clamp-1 mb-1">{job.title}</h4>
                                    <p className="text-xs text-secondary mb-3">{job.company}</p>
                                    <a
                                        href={job.url}
                                        target="_blank"
                                        rel="noreferrer"
                                        className="text-[10px] font-bold text-primary flex items-center gap-1 hover:underline"
                                    >
                                        VIEW SOURCE <ExternalLink className="w-3 h-3" />
                                    </a>
                                </div>
                            ))}
                            {!recentJobs?.length && !recentLoading && (
                                <p className="text-sm text-secondary text-center py-8 italic">No scraper activity data available.</p>
                            )}
                        </div>
                        <Button variant="ghost" className="w-full mt-6 text-xs font-bold tracking-widest uppercase">
                            View Detailed Log
                        </Button>
                    </Card>
                </div>
            </div>
        </div>
    );
};
