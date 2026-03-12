import React, { useMemo, useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import { useManagedJobs, useScraperActions } from '../hooks/useScrapers';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import type { ManagedJob } from '../types';
import { Briefcase, CheckCircle2, Search, ShieldCheck, ExternalLink, Loader2 } from 'lucide-react';
import { formatDate } from '../services/utils';

const statusVariant = (status: string) => {
    switch (status) {
        case 'new':
            return 'info';
        case 'active':
            return 'success';
        case 'closed':
            return 'danger';
        default:
            return 'neutral';
    }
};

export const JobsPage: React.FC = () => {
    const { isLoggedIn } = useAuth();
    const { updateManagedJob } = useScraperActions();
    const [page, setPage] = useState(1);
    const [search, setSearch] = useState('');
    const [statusFilter, setStatusFilter] = useState('');
    const [sourceFilter, setSourceFilter] = useState('');
    const { data, isLoading } = useManagedJobs(isLoggedIn, page, 20, search, statusFilter, sourceFilter);
    const [selectedJobId, setSelectedJobId] = useState<number | null>(null);
    const effectiveSelectedJobId = selectedJobId ?? data?.jobs?.[0]?.id ?? null;
    const selectedJob = useMemo(() => data?.jobs.find((job) => job.id === effectiveSelectedJobId) ?? null, [data?.jobs, effectiveSelectedJobId]);
    const [draft, setDraft] = useState<ManagedJob | null>(null);
    const editorJob = draft ?? selectedJob;

    const handleSelectJob = (job: ManagedJob) => {
        setSelectedJobId(job.id);
        setDraft(job);
    };

    const handleSave = async () => {
        if (!editorJob) return;
        await updateManagedJob.mutateAsync({
            jobId: editorJob.id,
            job: {
                title: editorJob.title,
                company: editorJob.company,
                location: editorJob.location,
                status: editorJob.status,
                operation_type: editorJob.operation_type,
                job_category: editorJob.job_category,
                sub_role: editorJob.sub_role,
                country_code: editorJob.country_code,
                is_verified: editorJob.is_verified,
                is_remote: editorJob.is_remote,
                description: editorJob.description,
            },
        });
    };

    const pagination = data?.pagination;
    const summary = data?.summary;

    return (
        <div className="space-y-8">
            <div className="flex flex-col xl:flex-row xl:items-center justify-between gap-4">
                <div>
                    <h2 className="text-3xl font-black text-white flex items-center gap-4 tracking-tighter uppercase">
                        <div className="p-2.5 bg-primary/10 rounded-2xl">
                            <Briefcase className="text-primary w-8 h-8" />
                        </div>
                        Managed Jobs
                    </h2>
                    <p className="text-secondary text-xs mt-2 font-bold uppercase tracking-[0.2em]">Review, verify, and update scraped jobs</p>
                </div>
                <div className="grid grid-cols-2 md:grid-cols-5 gap-3 w-full xl:w-auto">
                    <Card className="p-0"><div className="p-4"><p className="text-[10px] text-secondary uppercase font-black tracking-[0.2em]">Total</p><p className="text-2xl font-black text-white mt-2">{summary?.total ?? 0}</p></div></Card>
                    <Card className="p-0"><div className="p-4"><p className="text-[10px] text-secondary uppercase font-black tracking-[0.2em]">New</p><p className="text-2xl font-black text-info mt-2">{summary?.new ?? 0}</p></div></Card>
                    <Card className="p-0"><div className="p-4"><p className="text-[10px] text-secondary uppercase font-black tracking-[0.2em]">Active</p><p className="text-2xl font-black text-success mt-2">{summary?.active ?? 0}</p></div></Card>
                    <Card className="p-0"><div className="p-4"><p className="text-[10px] text-secondary uppercase font-black tracking-[0.2em]">Closed</p><p className="text-2xl font-black text-danger mt-2">{summary?.closed ?? 0}</p></div></Card>
                    <Card className="p-0"><div className="p-4"><p className="text-[10px] text-secondary uppercase font-black tracking-[0.2em]">Verified</p><p className="text-2xl font-black text-primary mt-2">{summary?.verified ?? 0}</p></div></Card>
                </div>
            </div>

            <div className="grid grid-cols-1 2xl:grid-cols-[1.4fr_0.9fr] gap-8">
                <Card
                    title="Job Inventory"
                    subtitle="Search, filter, and inspect imported jobs"
                    footer={
                        <div className="flex flex-col sm:flex-row justify-between gap-4 items-start sm:items-center">
                            <p className="text-[10px] text-secondary font-black uppercase tracking-[0.18em]">
                                Page {pagination?.page ?? page} of {pagination?.pages ?? 1}
                            </p>
                            <div className="flex gap-3 w-full sm:w-auto">
                                <Button variant="secondary" size="sm" disabled={page === 1} className="flex-1 sm:flex-none" onClick={() => setPage((current) => Math.max(1, current - 1))}>Prev</Button>
                                <Button variant="secondary" size="sm" disabled={!!pagination && page >= pagination.pages} className="flex-1 sm:flex-none" onClick={() => setPage((current) => current + 1)}>Next</Button>
                            </div>
                        </div>
                    }
                >
                    <div className="space-y-4">
                        <div className="grid grid-cols-1 md:grid-cols-[1.5fr_1fr_1fr] gap-3">
                            <div className="relative group">
                                <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-secondary" />
                                <input
                                    value={search}
                                    onChange={(e) => {
                                        setSearch(e.target.value);
                                        setPage(1);
                                    }}
                                    className="glass-input w-full pl-12"
                                    placeholder="Search title, company, source..."
                                />
                            </div>
                            <select value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }} className="glass-input w-full">
                                <option value="">All statuses</option>
                                <option value="new">New</option>
                                <option value="active">Active</option>
                                <option value="closed">Closed</option>
                            </select>
                            <select value={sourceFilter} onChange={(e) => { setSourceFilter(e.target.value); setPage(1); }} className="glass-input w-full">
                                <option value="">All sources</option>
                                {data?.sources.map((source) => <option key={source} value={source}>{source}</option>)}
                            </select>
                        </div>

                        <div className="hidden xl:block overflow-x-auto">
                            <table className="w-full min-w-[900px]">
                                <thead>
                                    <tr className="border-b border-white/5 text-left">
                                        <th className="py-3 text-[10px] uppercase tracking-[0.18em] text-secondary">Title</th>
                                        <th className="py-3 text-[10px] uppercase tracking-[0.18em] text-secondary">Company</th>
                                        <th className="py-3 text-[10px] uppercase tracking-[0.18em] text-secondary">Source</th>
                                        <th className="py-3 text-[10px] uppercase tracking-[0.18em] text-secondary">Status</th>
                                        <th className="py-3 text-[10px] uppercase tracking-[0.18em] text-secondary">Verified</th>
                                        <th className="py-3 text-[10px] uppercase tracking-[0.18em] text-secondary">Retrieved</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-white/5">
                                    {isLoading ? (
                                        <tr><td colSpan={6} className="py-10 text-center"><Loader2 className="w-7 h-7 text-primary animate-spin mx-auto" /></td></tr>
                                    ) : data?.jobs.map((job) => (
                                        <tr key={job.id} className={`cursor-pointer transition-colors hover:bg-white/[0.03] ${effectiveSelectedJobId === job.id ? 'bg-primary/5' : ''}`} onClick={() => handleSelectJob(job)}>
                                            <td className="py-4 pr-4">
                                                <p className="text-sm font-bold text-white line-clamp-1">{job.title}</p>
                                                <p className="text-[10px] text-secondary uppercase tracking-[0.15em] mt-1">{job.location || 'No location'}</p>
                                            </td>
                                            <td className="py-4 pr-4 text-sm text-secondary">{job.company}</td>
                                            <td className="py-4 pr-4 text-xs text-secondary uppercase">{job.source || '-'}</td>
                                            <td className="py-4 pr-4"><Badge variant={statusVariant(job.status)}>{job.status}</Badge></td>
                                            <td className="py-4 pr-4">{job.is_verified ? <ShieldCheck className="w-4 h-4 text-success" /> : <span className="text-secondary">-</span>}</td>
                                            <td className="py-4 text-xs text-secondary">{formatDate(job.retrieved_date)}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>

                        <div className="xl:hidden space-y-3">
                            {isLoading ? (
                                <div className="py-10 text-center"><Loader2 className="w-7 h-7 text-primary animate-spin mx-auto" /></div>
                            ) : data?.jobs.map((job) => (
                                <button key={job.id} onClick={() => handleSelectJob(job)} className={`w-full text-left rounded-3xl border p-4 transition-all ${effectiveSelectedJobId === job.id ? 'border-primary/40 bg-primary/5' : 'border-white/5 bg-white/[0.02]'}`}>
                                    <div className="flex justify-between gap-3">
                                        <div>
                                            <h3 className="text-sm font-black text-white line-clamp-2">{job.title}</h3>
                                            <p className="text-xs text-secondary mt-1">{job.company}</p>
                                        </div>
                                        <Badge variant={statusVariant(job.status)}>{job.status}</Badge>
                                    </div>
                                    <div className="flex flex-wrap gap-2 mt-3 text-[10px] uppercase tracking-[0.14em] text-secondary">
                                        <span>{job.source || 'Unknown source'}</span>
                                        <span>•</span>
                                        <span>{job.location || 'No location'}</span>
                                    </div>
                                </button>
                            ))}
                        </div>
                    </div>
                </Card>

                <Card
                    title={editorJob ? 'Edit Job' : 'Job Details'}
                    subtitle={editorJob ? 'Update metadata, verification, and status' : 'Select a job to review'}
                    footer={editorJob ? (
                        <div className="flex flex-col sm:flex-row gap-3 justify-between items-start sm:items-center">
                            <div className="text-[10px] text-secondary uppercase tracking-[0.18em] font-black">
                                Last checked {editorJob.last_checked ? formatDate(editorJob.last_checked) : 'not yet'}
                            </div>
                            <div className="flex gap-3 w-full sm:w-auto">
                                <Button variant="secondary" className="flex-1 sm:flex-none" onClick={() => setDraft(selectedJob)}>Reset</Button>
                                <Button className="flex-1 sm:flex-none" onClick={handleSave} isLoading={updateManagedJob.isPending}>Save Job</Button>
                            </div>
                        </div>
                    ) : undefined}
                >
                    {editorJob ? (
                        <div className="space-y-5">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <label className="text-[10px] font-black text-secondary uppercase tracking-[0.2em]">Title</label>
                                    <input className="glass-input w-full" value={editorJob.title} onChange={(e) => setDraft({ ...editorJob, title: e.target.value })} />
                                </div>
                                <div className="space-y-2">
                                    <label className="text-[10px] font-black text-secondary uppercase tracking-[0.2em]">Company</label>
                                    <input className="glass-input w-full" value={editorJob.company} onChange={(e) => setDraft({ ...editorJob, company: e.target.value })} />
                                </div>
                                <div className="space-y-2">
                                    <label className="text-[10px] font-black text-secondary uppercase tracking-[0.2em]">Location</label>
                                    <input className="glass-input w-full" value={editorJob.location ?? ''} onChange={(e) => setDraft({ ...editorJob, location: e.target.value })} />
                                </div>
                                <div className="space-y-2">
                                    <label className="text-[10px] font-black text-secondary uppercase tracking-[0.2em]">Status</label>
                                    <select className="glass-input w-full" value={editorJob.status} onChange={(e) => setDraft({ ...editorJob, status: e.target.value })}>
                                        <option value="new">New</option>
                                        <option value="active">Active</option>
                                        <option value="closed">Closed</option>
                                    </select>
                                </div>
                                <div className="space-y-2">
                                    <label className="text-[10px] font-black text-secondary uppercase tracking-[0.2em]">Operation Type</label>
                                    <input className="glass-input w-full" value={editorJob.operation_type ?? ''} onChange={(e) => setDraft({ ...editorJob, operation_type: e.target.value })} />
                                </div>
                                <div className="space-y-2">
                                    <label className="text-[10px] font-black text-secondary uppercase tracking-[0.2em]">Category</label>
                                    <input className="glass-input w-full" value={editorJob.job_category ?? ''} onChange={(e) => setDraft({ ...editorJob, job_category: e.target.value })} />
                                </div>
                                <div className="space-y-2">
                                    <label className="text-[10px] font-black text-secondary uppercase tracking-[0.2em]">Sub Role</label>
                                    <input className="glass-input w-full" value={editorJob.sub_role ?? ''} onChange={(e) => setDraft({ ...editorJob, sub_role: e.target.value })} />
                                </div>
                                <div className="space-y-2">
                                    <label className="text-[10px] font-black text-secondary uppercase tracking-[0.2em]">Country Code</label>
                                    <input className="glass-input w-full" value={editorJob.country_code ?? ''} onChange={(e) => setDraft({ ...editorJob, country_code: e.target.value.toUpperCase() })} />
                                </div>
                            </div>

                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                <button onClick={() => setDraft({ ...editorJob, is_verified: !editorJob.is_verified })} className={`rounded-2xl border p-4 text-left transition-all ${editorJob.is_verified ? 'border-success/30 bg-success/10 text-success' : 'border-white/10 bg-white/[0.02] text-secondary'}`}>
                                    <p className="text-[10px] uppercase tracking-[0.18em] font-black">Verification</p>
                                    <p className="text-sm font-black mt-2">{editorJob.is_verified ? 'Verified' : 'Needs review'}</p>
                                </button>
                                <button onClick={() => setDraft({ ...editorJob, is_remote: !editorJob.is_remote })} className={`rounded-2xl border p-4 text-left transition-all ${editorJob.is_remote ? 'border-info/30 bg-info/10 text-info' : 'border-white/10 bg-white/[0.02] text-secondary'}`}>
                                    <p className="text-[10px] uppercase tracking-[0.18em] font-black">Remote</p>
                                    <p className="text-sm font-black mt-2">{editorJob.is_remote ? 'Remote eligible' : 'On-site / unknown'}</p>
                                </button>
                            </div>

                            <div className="space-y-2">
                                <label className="text-[10px] font-black text-secondary uppercase tracking-[0.2em]">Description</label>
                                <textarea className="glass-input w-full min-h-[160px] resize-y" value={editorJob.description ?? ''} onChange={(e) => setDraft({ ...editorJob, description: e.target.value })} />
                            </div>

                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-4">
                                    <p className="text-[10px] uppercase tracking-[0.18em] text-secondary font-black">Source</p>
                                    <p className="text-sm font-bold text-white mt-2">{editorJob.source || '-'}</p>
                                </div>
                                <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-4">
                                    <p className="text-[10px] uppercase tracking-[0.18em] text-secondary font-black">Posted</p>
                                    <p className="text-sm font-bold text-white mt-2">{editorJob.posted_date ? formatDate(editorJob.posted_date) : '-'}</p>
                                </div>
                            </div>

                            <a href={editorJob.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 text-primary text-xs font-black uppercase tracking-[0.18em] hover:underline">
                                Open source posting <ExternalLink className="w-4 h-4" />
                            </a>
                        </div>
                    ) : (
                        <div className="h-full min-h-[320px] flex items-center justify-center text-center text-secondary">
                            <div>
                                <CheckCircle2 className="w-10 h-10 mx-auto mb-4 text-secondary/40" />
                                <p className="font-bold uppercase tracking-[0.18em] text-[11px]">Select a job to edit its metadata</p>
                            </div>
                        </div>
                    )}
                </Card>
            </div>
        </div>
    );
};
