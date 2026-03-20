import React, { useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import { useScrapedRecords, useScraperActions } from '../hooks/useScrapers';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Activity, Database, ExternalLink, Loader2, Search } from 'lucide-react';
import { formatDate } from '../services/utils';

export const ScrapedJobsPage: React.FC = () => {
    const { isLoggedIn } = useAuth();
    const [page, setPage] = useState(1);
    const [search, setSearch] = useState('');
    const [sourceFilter, setSourceFilter] = useState('');
    const { checkJobStatusBulk } = useScraperActions();
    const { data, isLoading } = useScrapedRecords(isLoggedIn, page, 20, search, sourceFilter);

    const handleBulkValidation = async () => {
        await checkJobStatusBulk.mutateAsync({
            q: search,
            source: sourceFilter,
            maxChecks: 250,
        });
    };

    return (
        <div className="space-y-8">
            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                <div>
                    <h2 className="text-3xl font-black text-white flex items-center gap-4 tracking-tighter uppercase">
                        <div className="p-2.5 bg-primary/10 rounded-2xl">
                            <Database className="text-primary w-8 h-8" />
                        </div>
                        Scraped Records
                    </h2>
                    <p className="text-secondary text-xs mt-2 font-bold uppercase tracking-[0.2em]">Track raw scraped entries and refresh cadence</p>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-[1.5fr_1fr] gap-3 w-full lg:w-[680px]">
                    <div className="relative group">
                        <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-secondary" />
                        <input
                            value={search}
                            onChange={(e) => {
                                setSearch(e.target.value);
                                setPage(1);
                            }}
                            className="glass-input w-full pl-12"
                            placeholder="Search title, company, source, URL..."
                        />
                    </div>
                    <select value={sourceFilter} onChange={(e) => { setSourceFilter(e.target.value); setPage(1); }} className="glass-input w-full">
                        <option value="">All sources</option>
                        {data?.sources.map((source) => <option key={source} value={source}>{source}</option>)}
                    </select>
                </div>
            </div>

            <Card
                title="Scraped Feed"
                subtitle="Raw records captured by scraper runs"
                footer={
                    <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                        <p className="text-[10px] text-secondary uppercase tracking-[0.18em] font-black">Page {data?.pagination.page ?? page} of {data?.pagination.pages ?? 1}</p>
                        <div className="flex gap-3 w-full sm:w-auto">
                            <Button variant="secondary" size="sm" disabled={page === 1} className="flex-1 sm:flex-none" onClick={() => setPage((current) => Math.max(1, current - 1))}>Prev</Button>
                            <Button variant="secondary" size="sm" disabled={!!data?.pagination && page >= data.pagination.pages} className="flex-1 sm:flex-none" onClick={() => setPage((current) => current + 1)}>Next</Button>
                        </div>
                    </div>
                }
            >
                <div className="mb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 rounded-2xl border border-white/5 bg-white/[0.02] px-4 py-3">
                    <p className="text-[10px] text-secondary font-black uppercase tracking-[0.2em]">
                        Bulk validation checks scraped records and always skips verified jobs.
                    </p>
                    <Button
                        variant="outline"
                        size="sm"
                        className="h-10 px-5 text-[10px] gap-2 border-white/10 hover:border-primary/40"
                        onClick={handleBulkValidation}
                        isLoading={checkJobStatusBulk.isPending}
                        disabled={isLoading || !data?.records.length}
                    >
                        <Activity className="w-3.5 h-3.5" />
                        Validate Scraped Records
                    </Button>
                </div>

                <div className="hidden xl:block overflow-x-auto">
                    <table className="w-full min-w-[980px]">
                        <thead>
                            <tr className="border-b border-white/5 text-left">
                                <th className="py-3 text-[10px] uppercase tracking-[0.18em] text-secondary">Title</th>
                                <th className="py-3 text-[10px] uppercase tracking-[0.18em] text-secondary">Company</th>
                                <th className="py-3 text-[10px] uppercase tracking-[0.18em] text-secondary">Source</th>
                                <th className="py-3 text-[10px] uppercase tracking-[0.18em] text-secondary">Scrapes</th>
                                <th className="py-3 text-[10px] uppercase tracking-[0.18em] text-secondary">State</th>
                                <th className="py-3 text-[10px] uppercase tracking-[0.18em] text-secondary">Last Seen</th>
                                <th className="py-3 text-[10px] uppercase tracking-[0.18em] text-secondary">Link</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-white/5">
                            {isLoading ? (
                                <tr><td colSpan={7} className="py-10 text-center"><Loader2 className="w-7 h-7 text-primary animate-spin mx-auto" /></td></tr>
                            ) : data?.records.map((record) => (
                                <tr key={record.id} className="hover:bg-white/[0.03] transition-colors">
                                    <td className="py-4 pr-4">
                                        <p className="text-sm font-bold text-white line-clamp-1">{record.title}</p>
                                        <p className="text-[10px] text-secondary uppercase tracking-[0.15em] mt-1">ID {record.job_id}</p>
                                    </td>
                                    <td className="py-4 pr-4 text-sm text-secondary">{record.company}</td>
                                    <td className="py-4 pr-4 text-xs text-secondary uppercase">{record.source}</td>
                                    <td className="py-4 pr-4 text-sm font-bold text-white">{record.scrape_count}</td>
                                    <td className="py-4 pr-4"><Badge variant={record.is_active ? 'success' : 'danger'}>{record.is_active ? 'active' : 'inactive'}</Badge></td>
                                    <td className="py-4 pr-4 text-xs text-secondary">{formatDate(record.last_scraped)}</td>
                                    <td className="py-4"><a href={record.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 text-primary text-xs font-black uppercase tracking-[0.16em] hover:underline">Open <ExternalLink className="w-3 h-3" /></a></td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>

                <div className="xl:hidden space-y-3">
                    {isLoading ? (
                        <div className="py-10 text-center"><Loader2 className="w-7 h-7 text-primary animate-spin mx-auto" /></div>
                    ) : data?.records.map((record) => (
                        <div key={record.id} className="rounded-3xl border border-white/5 bg-white/[0.02] p-4 space-y-3">
                            <div className="flex items-start justify-between gap-3">
                                <div>
                                    <h3 className="text-sm font-black text-white line-clamp-2">{record.title}</h3>
                                    <p className="text-xs text-secondary mt-1">{record.company}</p>
                                </div>
                                <Badge variant={record.is_active ? 'success' : 'danger'}>{record.is_active ? 'active' : 'inactive'}</Badge>
                            </div>
                            <div className="grid grid-cols-2 gap-3 text-[11px]">
                                <div className="rounded-2xl border border-white/5 bg-white/[0.02] p-3">
                                    <p className="text-[9px] uppercase tracking-[0.16em] text-secondary font-black">Source</p>
                                    <p className="text-white font-bold mt-1">{record.source}</p>
                                </div>
                                <div className="rounded-2xl border border-white/5 bg-white/[0.02] p-3">
                                    <p className="text-[9px] uppercase tracking-[0.16em] text-secondary font-black">Scrape Count</p>
                                    <p className="text-white font-bold mt-1">{record.scrape_count}</p>
                                </div>
                            </div>
                            <div className="flex items-center justify-between gap-3 text-[10px] uppercase tracking-[0.16em] text-secondary font-black">
                                <span>{formatDate(record.last_scraped)}</span>
                                <a href={record.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-primary hover:underline">Open <ExternalLink className="w-3 h-3" /></a>
                            </div>
                        </div>
                    ))}
                </div>
            </Card>
        </div>
    );
};
