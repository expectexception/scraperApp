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
    Hash
} from 'lucide-react';
import { formatDate, formatDuration } from '../services/utils';

export const HistoryPage: React.FC = () => {
    const { isLoggedIn } = useAuth();
    const [page, setPage] = useState(1);
    const { data: history, isLoading } = useHistory(isLoggedIn, page);

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
                        className="glass-input w-full md:w-80 pl-12 pr-6 uppercase text-[11px] font-black tracking-widest placeholder:text-secondary/30"
                    />
                </div>
            </div>

            <Card className="p-0 overflow-hidden bg-white/[0.01]">
                <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse">
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
                            ) : history?.map(row => (
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

                {/* Pagination */}
                <div className="px-8 py-6 bg-white/[0.02] border-t border-white/[0.05] flex items-center justify-between">
                    <p className="text-[10px] text-secondary font-black uppercase tracking-[0.2em]">
                        Showing runs <span className="text-white">{(page - 1) * 20 + 1} — {page * 20}</span> of historical data
                    </p>
                    <div className="flex gap-4">
                        <Button
                            variant="secondary"
                            size="sm"
                            disabled={page === 1}
                            onClick={() => setPage(p => Math.max(1, p - 1))}
                            className="gap-2 px-6 uppercase text-[9px] font-black tracking-widest"
                        >
                            <ChevronLeft className="w-4 h-4" /> REVISE
                        </Button>
                        <Button
                            variant="secondary"
                            size="sm"
                            onClick={() => setPage(p => p + 1)}
                            className="gap-2 px-6 uppercase text-[9px] font-black tracking-widest"
                        >
                            ADVANCE <ChevronRight className="w-4 h-4" />
                        </Button>
                    </div>
                </div>
            </Card>
        </div>
    );
};
