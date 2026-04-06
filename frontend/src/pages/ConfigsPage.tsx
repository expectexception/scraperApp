import React, { useState, useEffect } from 'react';
import { useConfigs, useSchedulerOverview, useScraperActions, useScrapers, useTitleFilters } from '../hooks/useScrapers';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { useAuth } from '../hooks/useAuth';
import {
    Settings,
    Save,
    ChevronRight,
    Sliders,
    Clock,
    Plus,
    Trash2,
    Search
} from 'lucide-react';
import type { ScraperConfig } from '../types';
import { motion } from 'framer-motion';
import { cn } from '../services/utils';

export const ConfigsPage: React.FC = () => {
    const { isLoggedIn } = useAuth();
    const { data: scrapers } = useScrapers();
    const { data: configs, isLoading } = useConfigs(isLoggedIn);
    const { data: schedulerOverview } = useSchedulerOverview(isLoggedIn);
    const { data: titleFilters } = useTitleFilters(isLoggedIn);
    const { updateConfig, updateTitleFilter } = useScraperActions();

    const [selectedScraper, setSelectedScraper] = useState<string>('');
    const [draft, setDraft] = useState<ScraperConfig | null>(null);
    const [newKeyword, setNewKeyword] = useState('');
    const [keywordSearch, setKeywordSearch] = useState('');
    const [targetFilterType, setTargetFilterType] = useState('');

    useEffect(() => {
        if (scrapers?.length && !selectedScraper) {
            setSelectedScraper(scrapers[0].name);
        }
    }, [scrapers]);

    useEffect(() => {
        if (selectedScraper && configs?.[selectedScraper]) {
            setDraft(configs[selectedScraper]);
        }
    }, [selectedScraper, configs]);

    const handleSave = () => {
        if (selectedScraper && draft) {
            updateConfig.mutate({ name: selectedScraper, config: draft });
        }
    };

    const handleAddKeyword = async () => {
        const keyword = newKeyword.trim();
        if (!keyword) return;
        await updateTitleFilter.mutateAsync({
            action: 'add',
            keyword,
            filterType: targetFilterType || undefined,
        });
        setNewKeyword('');
    };

    const handleRemoveKeyword = async (keyword: string) => {
        await updateTitleFilter.mutateAsync({
            action: 'remove',
            keyword,
        });
    };

    const filteredKeywords = (titleFilters?.keywords ?? []).filter((keyword) =>
        keyword.toLowerCase().includes(keywordSearch.toLowerCase())
    );

    if (isLoading) return <div className="p-8 text-secondary">Loading configurations...</div>;

    return (
        <div className="grid grid-cols-1 xl:grid-cols-4 gap-6 lg:gap-10">
            {/* Sidebar List */}
            <div className="xl:col-span-1 space-y-6">
                <Card className="p-0">
                    <div className="p-4 space-y-2">
                        <p className="text-[10px] font-black text-secondary uppercase tracking-[0.2em]">Scheduler</p>
                        <p className="text-lg font-black text-white">{schedulerOverview?.scheduled_scrapers ?? 0} scheduled</p>
                        <p className="text-xs text-secondary">{schedulerOverview?.celery_beat_available ? `${schedulerOverview.active_periodic_tasks} beat task(s) active` : 'Beat not available in this environment'}</p>
                    </div>
                </Card>
                <h3 className="text-[10px] font-black text-secondary uppercase tracking-[0.2em] px-4">Available Scrapers</h3>
                <div className="flex xl:flex-col gap-2 overflow-x-auto xl:overflow-visible pb-2 xl:pb-0">
                    {scrapers?.map(s => (
                        <button
                            key={s.name}
                            onClick={() => setSelectedScraper(s.name)}
                            className={cn(
                                "flex items-center justify-between px-5 py-4 rounded-2xl transition-all text-left group min-w-[240px] xl:min-w-0",
                                selectedScraper === s.name
                                    ? "bg-primary/10 text-primary border border-primary/30 shadow-glow-primary"
                                    : "text-secondary hover:bg-white/[0.03] border border-transparent"
                            )}
                        >
                            <div className="flex flex-col overflow-hidden">
                                <span className="text-sm font-black tracking-tight truncate uppercase">{s.display_name || s.name}</span>
                                <span className="text-[9px] opacity-40 font-black tracking-widest uppercase mt-1">SCRAPER_V1</span>
                            </div>
                            <ChevronRight className={cn("w-4 h-4 transition-transform duration-500", selectedScraper === s.name ? "rotate-90 translate-x-1" : "group-hover:translate-x-1")} />
                        </button>
                    ))}
                </div>
            </div>

            {/* Editor Area */}
            <div className="xl:col-span-3 xl:sticky xl:top-24 h-fit">
                {draft ? (
                    <motion.div
                        key={selectedScraper}
                        initial={{ opacity: 0, scale: 0.98 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{ duration: 0.4 }}
                        className="space-y-8"
                    >
                        <Card
                            title={`${selectedScraper} Settings`}
                            subtitle="Manage scraper boundaries and schedules"
                            footer={
                                <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                                    <p className="text-[10px] text-secondary font-bold uppercase tracking-[0.1em] opacity-50">State modified locally • Pending commit</p>
                                    <Button
                                        className="gap-3 px-6 sm:px-10 shadow-glow-primary w-full sm:w-auto"
                                        onClick={handleSave}
                                        isLoading={updateConfig.isPending}
                                    >
                                        <Save className="w-4 h-4" /> SAVE SETTINGS
                                    </Button>
                                </div>
                            }
                        >
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-8 lg:gap-10 p-1 sm:p-2">
                                {/* Left Column: Toggles & Numbers */}
                                <div className="space-y-8">
                                    <div className="p-6 rounded-3xl bg-white/[0.02] border border-white/[0.05] space-y-4">
                                        <div className="flex items-center justify-between">
                                            <div className="flex items-center gap-4">
                                                <div className="p-3 bg-primary/10 rounded-2xl text-primary shadow-inner"><Sliders className="w-5 h-5" /></div>
                                                <div>
                                                    <p className="text-sm font-black uppercase tracking-tight">Active Status</p>
                                                    <p className="text-[10px] text-secondary font-bold uppercase tracking-widest">Enable or disable scraper</p>
                                                </div>
                                            </div>
                                            <button
                                                onClick={() => setDraft({ ...draft, is_enabled: !draft.is_enabled })}
                                                className={cn(
                                                    "w-12 h-6 rounded-full transition-all relative",
                                                    draft.is_enabled ? "bg-primary" : "bg-white/10"
                                                )}
                                            >
                                                <div className={cn(
                                                    "absolute top-1 w-4 h-4 rounded-full bg-white transition-all shadow-lg",
                                                    draft.is_enabled ? "left-7" : "left-1"
                                                )} />
                                            </button>
                                        </div>
                                    </div>

                                    <div className="space-y-6">
                                        <div className="space-y-3">
                                            <label className="text-[10px] font-black text-secondary uppercase tracking-[0.2em] ml-2">Extraction Limit (ENTRIES)</label>
                                            <input
                                                type="number"
                                                value={draft.max_jobs ?? 0}
                                                onChange={e => setDraft({ ...draft, max_jobs: parseInt(e.target.value) || null })}
                                                className="glass-input w-full font-black text-white px-6"
                                            />
                                        </div>
                                        <div className="space-y-3">
                                            <label className="text-[10px] font-black text-secondary uppercase tracking-[0.2em] ml-2">Recursion Depth (PAGES)</label>
                                            <input
                                                type="number"
                                                value={draft.max_pages ?? 0}
                                                onChange={e => setDraft({ ...draft, max_pages: parseInt(e.target.value) || null })}
                                                className="glass-input w-full font-black text-white px-6"
                                            />
                                        </div>
                                        <div className="space-y-3">
                                            <label className="text-[10px] font-black text-secondary uppercase tracking-[0.2em] ml-2">Request Timeout (SECONDS)</label>
                                            <input
                                                type="number"
                                                min={1}
                                                value={draft.timeout}
                                                onChange={e => setDraft({ ...draft, timeout: parseInt(e.target.value) || 300 })}
                                                className="glass-input w-full font-black text-white px-6"
                                            />
                                        </div>
                                    </div>
                                </div>

                                {/* Right Column: Schedule & Details */}
                                <div className="space-y-8">
                                    <div className="p-6 rounded-3xl bg-white/[0.02] border border-white/[0.05] space-y-6">
                                        <div className="flex items-center justify-between">
                                            <div className="flex items-center gap-4">
                                                <div className="p-3 bg-info/10 rounded-2xl text-info shadow-inner"><Clock className="w-5 h-5" /></div>
                                                <div>
                                                    <p className="text-sm font-black uppercase tracking-tight">Cron Triggers</p>
                                                    <p className="text-[10px] text-secondary font-bold uppercase tracking-widest">Automated execution</p>
                                                </div>
                                            </div>
                                            <button
                                                onClick={() => setDraft({ ...draft, schedule_enabled: !draft.schedule_enabled })}
                                                className={cn(
                                                    "w-12 h-6 rounded-full transition-all relative",
                                                    draft.schedule_enabled ? "bg-info" : "bg-white/10"
                                                )}
                                            >
                                                <div className={cn(
                                                    "absolute top-1 w-4 h-4 rounded-full bg-white transition-all shadow-lg",
                                                    draft.schedule_enabled ? "left-7" : "left-1"
                                                )} />
                                            </button>
                                        </div>
                                        <div className="relative">
                                            <input
                                                placeholder="0 0 * * *"
                                                value={draft.schedule_cron}
                                                onChange={e => setDraft({ ...draft, schedule_cron: e.target.value })}
                                                disabled={!draft.schedule_enabled}
                                                className="glass-input w-full pl-6 pr-6 py-4 font-mono text-center text-xs tracking-[0.3em] disabled:opacity-20 transition-all"
                                            />
                                        </div>
                                        <p className="text-[10px] text-secondary uppercase tracking-[0.16em] font-black opacity-70">
                                            {schedulerOverview?.celery_beat_available ? 'Saved schedules sync into django_celery_beat tasks.' : 'Scheduling metadata can be saved, but beat is not available.'}
                                        </p>
                                    </div>

                                    <div className="space-y-3">
                                        <label className="text-[10px] font-black text-secondary uppercase tracking-[0.2em] ml-2">Retry Count</label>
                                        <input
                                            type="number"
                                            min={0}
                                            value={draft.retry_count}
                                            onChange={e => setDraft({ ...draft, retry_count: parseInt(e.target.value) || 0 })}
                                            className="glass-input w-full px-6 py-4 font-black text-white"
                                        />
                                    </div>

                                    <div className="space-y-3">
                                        <label className="text-[10px] font-black text-secondary uppercase tracking-[0.2em] ml-2">Notes</label>
                                        <textarea
                                            rows={5}
                                            value={draft.description || ''}
                                            onChange={e => setDraft({ ...draft, description: e.target.value })}
                                            className="glass-input w-full px-6 py-5 resize-none leading-relaxed text-[11px] font-bold uppercase tracking-wide h-[155px]"
                                            placeholder="ENTER SCRAPER NOTES AND TECHNICAL CONSTRAINTS..."
                                        />
                                    </div>
                                </div>
                            </div>
                        </Card>

                        <Card
                            title="Title Filter Keywords"
                            subtitle="Add or remove job title keywords used by filter_title.json"
                        >
                            <div className="space-y-5">
                                <div className="grid grid-cols-1 lg:grid-cols-[1.2fr_1fr_auto] gap-3">
                                    <div className="relative">
                                        <Search className="w-4 h-4 text-secondary absolute left-3 top-1/2 -translate-y-1/2" />
                                        <input
                                            value={newKeyword}
                                            onChange={(e) => setNewKeyword(e.target.value)}
                                            placeholder="Add keyword (e.g. Flight Dispatcher)"
                                            className="glass-input w-full pl-10"
                                        />
                                    </div>
                                    <select
                                        value={targetFilterType}
                                        onChange={(e) => setTargetFilterType(e.target.value)}
                                        className="glass-input w-full"
                                    >
                                        <option value="">Default group</option>
                                        {titleFilters?.groups.map((group) => (
                                            <option key={group.filter_type} value={group.filter_type}>
                                                {group.display_name} ({group.keyword_count})
                                            </option>
                                        ))}
                                    </select>
                                    <Button
                                        className="gap-2"
                                        onClick={handleAddKeyword}
                                        isLoading={updateTitleFilter.isPending}
                                        disabled={!newKeyword.trim()}
                                    >
                                        <Plus className="w-4 h-4" />
                                        Add
                                    </Button>
                                </div>

                                <div className="relative">
                                    <Search className="w-4 h-4 text-secondary absolute left-3 top-1/2 -translate-y-1/2" />
                                    <input
                                        value={keywordSearch}
                                        onChange={(e) => setKeywordSearch(e.target.value)}
                                        placeholder="Search existing keywords..."
                                        className="glass-input w-full pl-10"
                                    />
                                </div>

                                <div className="max-h-80 overflow-y-auto rounded-2xl border border-white/5 bg-white/[0.02] p-3 space-y-2">
                                    {filteredKeywords.slice(0, 200).map((keyword) => (
                                        <div key={keyword} className="flex items-center justify-between gap-3 rounded-xl border border-white/5 bg-white/[0.02] px-3 py-2">
                                            <span className="text-xs font-bold text-white">{keyword}</span>
                                            <Button
                                                variant="ghost"
                                                size="sm"
                                                className="h-8 px-3 text-danger hover:bg-danger/10 hover:text-danger"
                                                onClick={() => handleRemoveKeyword(keyword)}
                                                isLoading={updateTitleFilter.isPending}
                                            >
                                                <Trash2 className="w-3.5 h-3.5" />
                                            </Button>
                                        </div>
                                    ))}
                                    {!filteredKeywords.length && (
                                        <p className="text-xs text-secondary text-center py-6">No matching keywords found.</p>
                                    )}
                                </div>
                                <p className="text-[10px] text-secondary uppercase tracking-[0.16em] font-black">
                                    Showing {Math.min(filteredKeywords.length, 200)} of {titleFilters?.count ?? 0} keywords
                                </p>
                            </div>
                        </Card>
                    </motion.div>
                ) : (
                    <div className="h-[600px] flex flex-col items-center justify-center glass-card rounded-[40px] p-20 text-center">
                        <div className="p-8 bg-white/[0.03] rounded-[40px] mb-8 border border-white/[0.05] shadow-inner">
                            <Settings className="w-16 h-16 text-primary/20 animate-spin-slow" />
                        </div>
                        <h4 className="text-2xl font-black text-white/40 tracking-tighter uppercase mb-4">Select a Scraper</h4>
                        <p className="text-secondary/30 max-w-sm mx-auto font-bold uppercase tracking-[0.2em] text-[10px] leading-loose">
                            Select a scraper from the list to configure its settings and schedule.
                        </p>
                    </div>
                )}
            </div>
        </div>
    );
};
