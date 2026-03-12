import React, { useState } from 'react';
import { useHistory } from '../hooks/useScrapers';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { useAuth } from '../hooks/useAuth';
import {
    History as HistoryIcon,
    ChevronLeft,
    ChevronRight,
    Search,
    Calendar,
    Clock,
    CheckCircle2,
    XCircle,
    Hash,
    Loader2
} from 'lucide-react';
import { formatDate, formatDuration } from '../services/utils';

export const HistoryPage: React.FC = () => {
    const { isLoggedIn } = useAuth();
    const [page, setPage] = useState(1);
    const [search, setSearch] = useState('');
    const { data: historyResponse, isLoading } = useHistory(isLoggedIn, page, 20, search);
    const history = historyResponse?.jobs ?? [];
    const pagination = historyResponse?.pagination;
    const startIndex = pagination?.total ? (pagination.page - 1) * pagination.page_size + 1 : 0;
    const endIndex = pagination?.total ? Math.min(pagination.page * pagination.page_size, pagination.total) : 0;

    return (
        <div className="space-y-10">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
                <div>
                    <h2 className="text-3xl font-black text-white flex items-center gap-4 tracking-tighter uppercase">
                        <div className="p-2.5 bg-primary/10 rounded-2xl">
                            <HistoryIcon className="text-primary w-8 h-8" />
                        </div>
                        Scraper History
                    </h2>
                    <p className="text-secondary text-xs mt-2 font-bold uppercase tracking-[0.2em]">History of all scraper runs</p>
                </div>
                <div className="relative group">
                    <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-secondary group-focus-within:text-primary transition-colors" />
                    <input
                        placeholder="SEARCH RUNS..."
                        value={search}
                        onChange={(e) => {
                            setSearch(e.target.value);
                            setPage(1);
                        }}
                        className="glass-input w-full md:w-80 pl-12 pr-6 uppercase text-[11px] font-black tracking-widest placeholder:text-secondary/30"
                    />
                </div>
            </div>

            <Card className="p-0 overflow-hidden bg-white/[0.01]">
                <div className="hidden lg:block overflow-x-auto">
                    <table className="w-full min-w-[900px] text-left border-collapse">
                        <thead>
                            <tr className="bg-white/[0.03] border-b border-white/[0.05]">
                                <th className="py-6 px-8 text-[10px] font-black text-secondary uppercase tracking-[0.2em]">
                                    <div className="flex items-center gap-3">
                                        <Hash className="w-3.5 h-3.5 text-primary" /> RUN_ID
                                    </div>
                                </th>
                                <th className="py-6 px-8 text-[10px] font-black text-secondary uppercase tracking-[0.2em]">Scraper Name</th>
                                <th className="py-6 px-8 text-[10px] font-black text-secondary uppercase tracking-[0.2em]">Outcome</th>
                                <th className="py-6 px-8 text-[10px] font-black text-secondary uppercase tracking-[0.2em]">
                                    <div className="flex items-center gap-3">
                                        <Calendar className="w-3.5 h-3.5 text-primary" /> Timestamp
                                    </div>
                                </th>
                                <th className="py-6 px-8 text-[10px] font-black text-secondary uppercase tracking-[0.2em]">
                                    <div className="flex items-center gap-3">
                                        <Clock className="w-3.5 h-3.5 text-primary" /> Duration
                                    </div>
                                </th>
                                <th className="py-6 px-8 text-[10px] font-black text-secondary uppercase tracking-[0.2em] text-right">Payload Metrics</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-white/[0.03]">
                            {isLoading ? (
                                [...Array(10)].map((_, i) => (
                                    <tr key={i} className="animate-pulse">
                                        <td colSpan={6} className="py-8 px-8"><div className="h-4 bg-white/[0.03] rounded-full w-full"></div></td>
                                    </tr>
                                ))
                            ) : history.map(row => (
                                <tr key={row.id} className="hover:bg-primary/[0.02] transition-all duration-500 group">
                                    <td className="py-6 px-8 text-xs font-black text-secondary/40 group-hover:text-primary transition-colors tracking-widest font-mono">#{row.id.toString().padStart(4, '0')}</td>
                                    <td className="py-6 px-8">
                                        <div className="font-black text-sm text-white group-hover:text-primary transition-colors cursor-pointer tracking-tight uppercase">{row.scraper_name}</div>
                                    </td>
                                    <td className="py-6 px-8">
                                        <div className="flex items-center">
                                            <Badge variant={row.status === 'completed' ? 'success' : row.status === 'failed' ? 'danger' : 'warning'}>
                                                <span className="flex items-center gap-2 font-black tracking-[0.15em] text-[9px] whitespace-nowrap">
                                                    {row.status === 'completed' ? <CheckCircle2 className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
                                                    {row.status.toUpperCase()}
                                                </span>
                                            </Badge>
                                        </div>
                                    </td>
                                    <td className="py-6 px-8 text-[11px] font-bold text-secondary uppercase tracking-wider">{formatDate(row.started_at)}</td>
                                    <td className="py-6 px-8 text-[11px] font-bold text-secondary uppercase tracking-wider">{formatDuration(row.execution_time)}</td>
                                    <td className="py-6 px-8 text-right">
                                        <div className="flex flex-col items-end gap-1.5">
                                            <span className="text-xs font-black text-white tracking-widest uppercase">{row.jobs_new} NEW</span>
                                            <span className="text-[10px] text-secondary font-black opacity-30 tracking-[0.2em] uppercase">{row.jobs_found} TOTAL</span>
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>

                <div className="lg:hidden divide-y divide-white/[0.04]">
                    {isLoading ? (
                        <div className="py-14 flex justify-center">
                            <Loader2 className="w-8 h-8 animate-spin text-primary" />
                        </div>
                    ) : history.length ? (
                        history.map((row) => (
                            <div key={row.id} className="p-5 space-y-4">
                                <div className="flex items-start justify-between gap-3">
                                    <div>
                                        <p className="text-[10px] font-black text-secondary uppercase tracking-[0.18em]">Run #{row.id.toString().padStart(4, '0')}</p>
                                        <h3 className="text-base font-black text-white uppercase tracking-tight mt-1">{row.scraper_name}</h3>
                                    </div>
                                    <Badge variant={row.status === 'completed' ? 'success' : row.status === 'failed' ? 'danger' : 'warning'}>
                                        {row.status}
                                    </Badge>
                                </div>
                                <div className="grid grid-cols-2 gap-3 text-[11px]">
                                    <div className="rounded-2xl border border-white/[0.05] bg-white/[0.02] p-3">
                                        <p className="text-secondary uppercase tracking-wider text-[9px] font-black mb-1">Started</p>
                                        <p className="font-bold text-white">{formatDate(row.started_at)}</p>
                                    </div>
                                    <div className="rounded-2xl border border-white/[0.05] bg-white/[0.02] p-3">
                                        <p className="text-secondary uppercase tracking-wider text-[9px] font-black mb-1">Duration</p>
                                        <p className="font-bold text-white">{formatDuration(row.execution_time)}</p>
                                    </div>
                                    <div className="rounded-2xl border border-white/[0.05] bg-white/[0.02] p-3">
                                        <p className="text-secondary uppercase tracking-wider text-[9px] font-black mb-1">New Jobs</p>
                                        <p className="font-bold text-white">{row.jobs_new}</p>
                                    </div>
                                    <div className="rounded-2xl border border-white/[0.05] bg-white/[0.02] p-3">
                                        <p className="text-secondary uppercase tracking-wider text-[9px] font-black mb-1">Total Found</p>
                                        <p className="font-bold text-white">{row.jobs_found}</p>
                                    </div>
                                </div>
                            </div>
                        ))
                    ) : (
                        <div className="py-12 text-center text-secondary text-sm">No history found for the current filter.</div>
                    )}
                </div>

                {/* Pagination */}
                <div className="px-4 sm:px-8 py-6 bg-white/[0.02] border-t border-white/[0.05] flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                    <p className="text-[10px] text-secondary font-black uppercase tracking-[0.2em]">
                        Showing runs <span className="text-white">{startIndex || 0} — {endIndex || 0}</span> of {pagination?.total ?? 0}
                    </p>
                    <div className="flex gap-3 w-full sm:w-auto">
                        <Button
                            variant="secondary"
                            size="sm"
                            disabled={page === 1}
                            onClick={() => setPage(p => Math.max(1, p - 1))}
                            className="gap-2 px-4 sm:px-6 uppercase text-[9px] font-black tracking-widest flex-1 sm:flex-none"
                        >
                            <ChevronLeft className="w-4 h-4" /> REVISE
                        </Button>
                        <Button
                            variant="secondary"
                            size="sm"
                            disabled={!!pagination && page >= pagination.pages}
                            onClick={() => setPage(p => p + 1)}
                            className="gap-2 px-4 sm:px-6 uppercase text-[9px] font-black tracking-widest flex-1 sm:flex-none"
                        >
                            ADVANCE <ChevronRight className="w-4 h-4" />
                        </Button>
                    </div>
                </div>
            </Card>
        </div>
    );
};
