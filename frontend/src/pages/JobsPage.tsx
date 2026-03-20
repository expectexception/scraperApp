import React, { useMemo, useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import { useManagedJobs, useScraperActions } from '../hooks/useScrapers';
import { useToast } from '../hooks/useToast';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import type { ManagedJob } from '../types';
import { 
    Briefcase, 
    Search, 
    ShieldCheck, 
    ExternalLink, 
    Loader2, 
    Edit3, 
    Activity,
    X,
    Check
} from 'lucide-react';
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
    const { showToast } = useToast();
    const { updateManagedJob, checkJobStatus, checkJobStatusBulk } = useScraperActions();
    const [page, setPage] = useState(1);
    const [search, setSearch] = useState('');
    const [statusFilter, setStatusFilter] = useState('');
    const [sourceFilter, setSourceFilter] = useState('');
    const [verifiedFilter, setVerifiedFilter] = useState<'all' | 'unverified' | 'verified'>('all');
    const { data, isLoading } = useManagedJobs(isLoggedIn, page, 20, search, statusFilter, sourceFilter, verifiedFilter);
    
    // UI State
    const [selectedJobId, setSelectedJobId] = useState<number | string | null>(null);
    const [draft, setDraft] = useState<ManagedJob | null>(null);
    const [isEditModalOpen, setIsEditModalOpen] = useState(false);
    
    const selectedJob = useMemo(() => {
        if (selectedJobId == null) return null;
        return data?.jobs.find((job) => String(job.id) === String(selectedJobId)) ?? null;
    }, [data?.jobs, selectedJobId]);
    const editorJob = draft ?? selectedJob;
    const closeEditModal = () => {
        setIsEditModalOpen(false);
        setDraft(null);
        setSelectedJobId(null);
    };

    const hasUnsavedChanges = useMemo(() => {
        if (!editorJob || !selectedJob) return false;
        const normalize = (job: ManagedJob) => ({
            title: job.title?.trim() ?? '',
            company: job.company?.trim() ?? '',
            location: job.location ?? '',
            status: job.status ?? '',
            operation_type: job.operation_type ?? '',
            job_category: job.job_category ?? '',
            sub_role: job.sub_role ?? '',
            country_code: (job.country_code ?? '').toUpperCase().slice(0, 3),
            is_verified: !!job.is_verified,
            is_remote: !!job.is_remote,
            description: job.description ?? '',
        });
        return JSON.stringify(normalize(editorJob)) !== JSON.stringify(normalize(selectedJob));
    }, [editorJob, selectedJob]);

    const handleEditClick = (job: ManagedJob) => {
        setSelectedJobId(job.id);
        setDraft(job);
        setIsEditModalOpen(true);
    };

    const handleCheckStatus = async (jobId: number | string) => {
        try {
            await checkJobStatus.mutateAsync(jobId);
        } catch {
            // Error toast is handled centrally in the mutation hook.
        }
    };

    const handleSave = async () => {
        if (!editorJob) return;
        const title = editorJob.title?.trim() ?? '';
        const company = editorJob.company?.trim() ?? '';
        if (!title || !company) {
            showToast({
                level: 'error',
                message: 'Title and company are required.',
            });
            return;
        }

        await updateManagedJob.mutateAsync({
            jobId: editorJob.id,
            job: {
                title,
                company,
                location: editorJob.location?.trim() || null,
                status: editorJob.status,
                operation_type: editorJob.operation_type?.trim() || null,
                job_category: editorJob.job_category?.trim() || null,
                sub_role: editorJob.sub_role?.trim() || null,
                country_code: editorJob.country_code?.toUpperCase().slice(0, 3) || null,
                is_verified: editorJob.is_verified,
                is_remote: editorJob.is_remote,
                description: editorJob.description?.trim() || null,
            },
        });
        closeEditModal();
    };

    const handleBulkValidation = async () => {
        await checkJobStatusBulk.mutateAsync({
            q: search,
            status: statusFilter,
            source: sourceFilter,
            maxChecks: 250,
        });
    };

    const pagination = data?.pagination;
    const summary = data?.summary;

    return (
        <div className="space-y-8">
            <div className="flex flex-col xl:flex-row xl:items-center justify-between gap-6">
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
                    <Card className="p-0 border-white/5 bg-white/[0.02]"><div className="p-4"><p className="text-[10px] text-secondary uppercase font-black tracking-[0.2em]">Total</p><p className="text-2xl font-black text-white mt-2">{summary?.total ?? 0}</p></div></Card>
                    <Card className="p-0 border-white/5 bg-white/[0.02]"><div className="p-4"><p className="text-[10px] text-secondary uppercase font-black tracking-[0.2em]">New</p><p className="text-2xl font-black text-info mt-2">{summary?.new ?? 0}</p></div></Card>
                    <Card className="p-0 border-white/5 bg-white/[0.02]"><div className="p-4"><p className="text-[10px] text-secondary uppercase font-black tracking-[0.2em]">Active</p><p className="text-2xl font-black text-success mt-2">{summary?.active ?? 0}</p></div></Card>
                    <Card className="p-0 border-white/5 bg-white/[0.02]"><div className="p-4"><p className="text-[10px] text-secondary uppercase font-black tracking-[0.2em]">Closed</p><p className="text-2xl font-black text-danger mt-2">{summary?.closed ?? 0}</p></div></Card>
                    <Card className="p-0 border-white/5 bg-white/[0.02]"><div className="p-4"><p className="text-[10px] text-secondary uppercase font-black tracking-[0.2em]">Verified</p><p className="text-2xl font-black text-primary mt-2">{summary?.verified ?? 0}</p></div></Card>
                </div>
            </div>

            <div className="w-full">
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
                    <div className="space-y-6">
                        <div className="grid grid-cols-1 lg:grid-cols-[1.5fr_1fr_1fr_1fr] gap-4">
                            <div className="relative group">
                                <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-secondary" />
                                <input
                                    value={search}
                                    onChange={(e) => {
                                        setSearch(e.target.value);
                                        setPage(1);
                                    }}
                                    className="glass-input w-full pl-12 h-12"
                                    placeholder="Search title, company, source..."
                                />
                            </div>
                            <select value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }} className="glass-input w-full h-12">
                                <option value="">All statuses</option>
                                <option value="new">New</option>
                                <option value="active">Active</option>
                                <option value="closed">Closed</option>
                            </select>
                            <select value={sourceFilter} onChange={(e) => { setSourceFilter(e.target.value); setPage(1); }} className="glass-input w-full h-12">
                                <option value="">All sources</option>
                                {data?.sources.map((source) => <option key={source} value={source}>{source}</option>)}
                            </select>
                            <select
                                value={verifiedFilter}
                                onChange={(e) => { setVerifiedFilter(e.target.value as 'all' | 'unverified' | 'verified'); setPage(1); }}
                                className="glass-input w-full h-12"
                            >
                                <option value="all">All verification states</option>
                                <option value="unverified">Hide verified jobs</option>
                                <option value="verified">Show only verified</option>
                            </select>
                        </div>

                        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 rounded-2xl border border-white/5 bg-white/[0.02] px-4 py-3">
                            <p className="text-[10px] text-secondary font-black uppercase tracking-[0.2em]">
                                Bulk check validates scraped records only and skips verified jobs automatically.
                            </p>
                            <Button
                                variant="outline"
                                size="sm"
                                className="h-10 px-5 text-[10px] gap-2 border-white/10 hover:border-primary/40"
                                onClick={handleBulkValidation}
                                isLoading={checkJobStatusBulk.isPending}
                                disabled={isLoading || !data?.jobs.length}
                            >
                                <Activity className="w-3.5 h-3.5" />
                                Validate Matching Unverified
                            </Button>
                        </div>

                        <div className="hidden xl:block overflow-x-auto rounded-2xl border border-white/5 bg-white/[0.01]">
                            <table className="w-full min-w-[1200px]">
                                <thead>
                                    <tr className="bg-white/5 text-left">
                                        <th className="py-5 px-6 text-[10px] uppercase tracking-[0.2em] text-secondary font-black">Job Details</th>
                                        <th className="py-5 px-6 text-[10px] uppercase tracking-[0.2em] text-secondary font-black">Source</th>
                                        <th className="py-5 px-6 text-[10px] uppercase tracking-[0.2em] text-secondary font-black">Status</th>
                                        <th className="py-5 px-6 text-[10px] uppercase tracking-[0.2em] text-secondary font-black text-center">Verified</th>
                                        <th className="py-5 px-6 text-[10px] uppercase tracking-[0.2em] text-secondary font-black">Live Validation</th>
                                        <th className="py-5 px-6 text-[10px] uppercase tracking-[0.2em] text-secondary font-black text-right">Actions</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-white/5">
                                    {isLoading ? (
                                        <tr><td colSpan={6} className="py-20 text-center"><Loader2 className="w-8 h-8 text-primary animate-spin mx-auto" /></td></tr>
                                    ) : data?.jobs.map((job) => (
                                        <tr key={job.id} className="transition-colors hover:bg-white/[0.03]">
                                            <td className="py-5 px-6">
                                                <div className="flex flex-col">
                                                    <span className="text-sm font-black text-white truncate max-w-[300px] leading-tight">{job.title}</span>
                                                    <div className="flex items-center gap-2 mt-1.5 min-w-0">
                                                        <span className="text-xs text-primary font-bold">{job.company}</span>
                                                        <span className="text-[10px] text-white/20">•</span>
                                                        <span className="text-[10px] text-secondary uppercase tracking-widest truncate">{job.location || 'Remote/Unknown'}</span>
                                                    </div>
                                                </div>
                                            </td>
                                            <td className="py-5 px-6">
                                                <span className="text-[10px] font-black text-secondary uppercase tracking-[0.15em] py-1 px-2.5 bg-white/5 rounded-lg border border-white/5">{job.source || '-'}</span>
                                            </td>
                                            <td className="py-5 px-6">
                                                <Badge variant={statusVariant(job.status)} className="font-black uppercase text-[9px] tracking-widest">{job.status}</Badge>
                                            </td>
                                            <td className="py-5 px-6 text-center">
                                                {job.is_verified ? (
                                                    <div className="p-1.5 bg-success/15 rounded-full inline-flex border border-success/20">
                                                        <ShieldCheck className="w-3.5 h-3.5 text-success" />
                                                    </div>
                                                ) : <span className="text-white/10">-</span>}
                                            </td>
                                            <td className="py-5 px-6">
                                                <div className="flex flex-col gap-1.5">
                                                    <Button 
                                                        variant="outline" 
                                                        size="sm" 
                                                        disabled={job.is_verified || (checkJobStatus.isPending && selectedJobId === job.id)}
                                                        onClick={() => {
                                                            setSelectedJobId(job.id);
                                                            handleCheckStatus(job.id);
                                                        }}
                                                        className="h-8 text-[9px] uppercase tracking-widest font-black gap-2 border-white/10 hover:border-primary/50"
                                                    >
                                                        {checkJobStatus.isPending && selectedJobId === job.id ? (
                                                            <Loader2 className="w-3 h-3 animate-spin" />
                                                        ) : (
                                                            <Activity className="w-3 h-3 text-primary" />
                                                        )}
                                                        {job.is_verified ? 'Verified' : 'Check Live'}
                                                    </Button>
                                                    {job.last_checked && (
                                                        <span className="text-[9px] text-secondary font-bold uppercase tracking-tighter">
                                                            Last: {formatDate(job.last_checked)}
                                                        </span>
                                                    )}
                                                </div>
                                            </td>
                                            <td className="py-5 px-6 text-right">
                                                <div className="flex items-center justify-end gap-2">
                                                    <button 
                                                        onClick={() => handleEditClick(job)}
                                                        className="p-2.5 rounded-xl bg-primary/10 text-primary border border-primary/20 hover:bg-primary hover:text-white transition-all shadow-glow-primary/20"
                                                        title="Edit Job"
                                                    >
                                                        <Edit3 className="w-4 h-4" />
                                                    </button>
                                                    <a 
                                                        href={job.url} 
                                                        target="_blank" 
                                                        rel="noreferrer" 
                                                        className="p-2.5 rounded-xl bg-white/5 text-secondary border border-white/10 hover:bg-white/10 hover:text-white transition-all"
                                                        title="Open Source"
                                                    >
                                                        <ExternalLink className="w-4 h-4" />
                                                    </a>
                                                </div>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>

                        <div className="xl:hidden space-y-4">
                            {isLoading ? (
                                <div className="py-20 text-center"><Loader2 className="w-8 h-8 text-primary animate-spin mx-auto" /></div>
                            ) : data?.jobs.map((job) => (
                                <div key={job.id} className="rounded-3xl border border-white/5 bg-white/[0.02] p-5 space-y-4">
                                    <div className="flex justify-between items-start gap-4">
                                        <div className="min-w-0">
                                            <h3 className="text-sm font-black text-white line-clamp-2 leading-tight">{job.title}</h3>
                                            <p className="text-xs text-primary font-bold mt-1.5">{job.company}</p>
                                        </div>
                                        <Badge variant={statusVariant(job.status)} className="font-black uppercase text-[9px] tracking-widest">{job.status}</Badge>
                                    </div>
                                    <div className="flex flex-wrap gap-2 text-[10px] uppercase tracking-[0.14em] text-secondary font-bold">
                                        <span className="py-1 px-2.5 bg-white/5 rounded-lg border border-white/5">{job.source || '-'}</span>
                                        <span className="py-1 px-2.5 bg-white/5 rounded-lg border border-white/5">{job.location || 'Remote'}</span>
                                    </div>
                                    <div className="flex gap-3 pt-2 border-t border-white/5">
                                        <Button 
                                            size="sm" 
                                            className="flex-1 h-10 text-[10px] uppercase tracking-widest font-black gap-2"
                                            onClick={() => handleEditClick(job)}
                                        >
                                            <Edit3 className="w-3.5 h-3.5" />
                                            Edit
                                        </Button>
                                        <Button 
                                            variant="secondary" 
                                            size="sm" 
                                            className="flex-1 h-10 text-[10px] uppercase tracking-widest font-black gap-2"
                                            onClick={() => handleCheckStatus(job.id)}
                                            disabled={job.is_verified || checkJobStatus.isPending}
                                        >
                                            <Activity className="w-3.5 h-3.5" />
                                            {job.is_verified ? 'Verified' : 'Check'}
                                        </Button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </Card>
            </div>

            {/* Edit Job Modal */}
            {isEditModalOpen && editorJob && (
                <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 sm:p-6 lg:p-8">
                    <div 
                        className="absolute inset-0 bg-background/60 backdrop-blur-md animate-in fade-in duration-300" 
                        onClick={closeEditModal} 
                    />
                    <div className="relative w-full max-w-4xl max-h-[90vh] overflow-hidden animate-in zoom-in-95 duration-300">
                        <Card
                            className="h-full flex flex-col p-0 overflow-hidden border-white/10 shadow-2xl"
                            title={
                                <div className="flex items-center justify-between w-full pr-4">
                                    <div className="flex items-center gap-4">
                                        <div className="p-2 bg-primary/10 rounded-xl">
                                            <Edit3 className="w-5 h-5 text-primary" />
                                        </div>
                                        <div>
                                            <h3 className="text-xl font-black text-white tracking-tighter uppercase">Edit Job Metadata</h3>
                                            <p className="text-[10px] text-secondary font-bold uppercase tracking-widest mt-0.5">ID: {editorJob.id}</p>
                                        </div>
                                    </div>
                                    <button 
                                        onClick={closeEditModal}
                                        className="p-2 rounded-xl border border-white/5 hover:bg-white/5 text-secondary hover:text-white transition-all"
                                    >
                                        <X className="w-5 h-5" />
                                    </button>
                                </div>
                            }
                        >
                            <div className="flex-1 overflow-y-auto p-6 lg:p-8 space-y-8 scrollbar-thin scrollbar-thumb-white/10">
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                    <div className="space-y-2">
                                        <label className="text-[10px] font-black text-secondary uppercase tracking-[0.2em]">Job Title</label>
                                        <input className="glass-input w-full h-11" value={editorJob.title} onChange={(e) => setDraft({ ...editorJob, title: e.target.value })} />
                                    </div>
                                    <div className="space-y-2">
                                        <label className="text-[10px] font-black text-secondary uppercase tracking-[0.2em]">Company Name</label>
                                        <input className="glass-input w-full h-11" value={editorJob.company} onChange={(e) => setDraft({ ...editorJob, company: e.target.value })} />
                                    </div>
                                    <div className="space-y-2">
                                        <label className="text-[10px] font-black text-secondary uppercase tracking-[0.2em]">Location</label>
                                        <input className="glass-input w-full h-11" value={editorJob.location ?? ''} onChange={(e) => setDraft({ ...editorJob, location: e.target.value })} />
                                    </div>
                                    <div className="space-y-2">
                                        <label className="text-[10px] font-black text-secondary uppercase tracking-[0.2em]">Current Status</label>
                                        <select className="glass-input w-full h-11" value={editorJob.status} onChange={(e) => setDraft({ ...editorJob, status: e.target.value })}>
                                            <option value="new">New</option>
                                            <option value="active">Active</option>
                                            <option value="closed">Closed</option>
                                        </select>
                                    </div>
                                    <div className="space-y-2">
                                        <label className="text-[10px] font-black text-secondary uppercase tracking-[0.2em]">Operation Type</label>
                                        <input className="glass-input w-full h-11" value={editorJob.operation_type ?? ''} onChange={(e) => setDraft({ ...editorJob, operation_type: e.target.value })} />
                                    </div>
                                    <div className="space-y-2">
                                        <label className="text-[10px] font-black text-secondary uppercase tracking-[0.2em]">Job Category</label>
                                        <input className="glass-input w-full h-11" value={editorJob.job_category ?? ''} onChange={(e) => setDraft({ ...editorJob, job_category: e.target.value })} />
                                    </div>
                                    <div className="space-y-2">
                                        <label className="text-[10px] font-black text-secondary uppercase tracking-[0.2em]">Sub Role</label>
                                        <input className="glass-input w-full h-11" value={editorJob.sub_role ?? ''} onChange={(e) => setDraft({ ...editorJob, sub_role: e.target.value })} />
                                    </div>
                                    <div className="space-y-2">
                                        <label className="text-[10px] font-black text-secondary uppercase tracking-[0.2em]">Country Code</label>
                                        <input className="glass-input w-full h-11" value={editorJob.country_code ?? ''} onChange={(e) => setDraft({ ...editorJob, country_code: e.target.value.toUpperCase() })} />
                                    </div>
                                </div>

                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                    <button 
                                        onClick={() => setDraft({ ...editorJob, is_verified: !editorJob.is_verified })} 
                                        className={`rounded-2xl border p-4 text-left transition-all flex items-center justify-between group ${editorJob.is_verified ? 'border-success/30 bg-success/10 text-success' : 'border-white/10 bg-white/[0.02] text-secondary'}`}
                                    >
                                        <div>
                                            <p className="text-[10px] uppercase tracking-[0.18em] font-black">Verification Status</p>
                                            <p className="text-sm font-black mt-1">{editorJob.is_verified ? 'Verified Successfully' : 'Needs Verification'}</p>
                                        </div>
                                        <div className={`w-8 h-8 rounded-full flex items-center justify-center transition-all ${editorJob.is_verified ? 'bg-success text-white shadow-glow-success/30' : 'bg-white/5 text-secondary group-hover:text-white'}`}>
                                            {editorJob.is_verified ? <Check className="w-4 h-4" /> : <ShieldCheck className="w-4 h-4" />}
                                        </div>
                                    </button>
                                    <button 
                                        onClick={() => setDraft({ ...editorJob, is_remote: !editorJob.is_remote })} 
                                        className={`rounded-2xl border p-4 text-left transition-all flex items-center justify-between group ${editorJob.is_remote ? 'border-info/30 bg-info/10 text-info' : 'border-white/10 bg-white/[0.02] text-secondary'}`}
                                    >
                                        <div>
                                            <p className="text-[10px] uppercase tracking-[0.18em] font-black">Remote Eligibility</p>
                                            <p className="text-sm font-black mt-1">{editorJob.is_remote ? 'Remote / Hybrid' : 'On-site Office'}</p>
                                        </div>
                                        <div className={`w-8 h-8 rounded-full flex items-center justify-center transition-all ${editorJob.is_remote ? 'bg-info text-white shadow-glow-info/30' : 'bg-white/5 text-secondary group-hover:text-white'}`}>
                                            <Activity className="w-4 h-4" />
                                        </div>
                                    </button>
                                </div>

                                <div className="space-y-4">
                                    <label className="text-[10px] font-black text-secondary uppercase tracking-[0.2em]">Job Description Overview</label>
                                    <textarea className="glass-input w-full min-h-[160px] resize-y p-5 leading-relaxed" value={editorJob.description ?? ''} onChange={(e) => setDraft({ ...editorJob, description: e.target.value })} />
                                </div>

                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                    <div className="rounded-2xl border border-white/5 bg-white/[0.02] p-5">
                                        <p className="text-[10px] uppercase tracking-[0.2em] text-secondary font-black">Data Source</p>
                                        <p className="text-sm font-bold text-white mt-1.5">{editorJob.source || '-'}</p>
                                    </div>
                                    <div className="rounded-2xl border border-white/5 bg-white/[0.02] p-5">
                                        <p className="text-[10px] uppercase tracking-[0.2em] text-secondary font-black">Original Post Date</p>
                                        <p className="text-sm font-bold text-white mt-1.5">{editorJob.posted_date ? formatDate(editorJob.posted_date) : '-'}</p>
                                    </div>
                                </div>
                            </div>
                            <div className="p-6 lg:p-8 bg-white/[0.02] border-t border-white/5 flex flex-col sm:flex-row gap-4 justify-between items-center">
                                <div className="flex items-center gap-3">
                                    <a href={editorJob.url} target="_blank" rel="noreferrer" className="flex items-center gap-2 py-2.5 px-5 rounded-xl bg-white/5 text-[10px] font-black text-secondary uppercase tracking-widest hover:bg-white/10 hover:text-white transition-all border border-white/5">
                                        Source URL <ExternalLink className="w-3.5 h-3.5" />
                                    </a>
                                    {editorJob.last_checked && (
                                        <span className="text-[9px] text-white/20 font-bold uppercase tracking-widest">
                                            Last Validated: {formatDate(editorJob.last_checked)}
                                        </span>
                                    )}
                                </div>
                                <div className="flex gap-3 w-full sm:w-auto">
                                    <Button variant="secondary" className="flex-1 sm:flex-none h-12 px-8 uppercase tracking-widest" onClick={closeEditModal}>Cancel</Button>
                                    <Button className="flex-1 sm:flex-none h-12 px-8 uppercase tracking-widest" onClick={handleSave} isLoading={updateManagedJob.isPending} disabled={!hasUnsavedChanges}>Submit Changes</Button>
                                </div>
                            </div>
                        </Card>
                    </div>
                </div>
            )}
        </div>
    );
};
