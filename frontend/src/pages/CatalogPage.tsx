import React, { useState, useMemo } from 'react';
import { useScrapers, useScraperActions } from '../hooks/useScrapers';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { cn } from '../services/utils';
import {
    Search,
    Database,
    Globe,
    Tag,
    Rocket,
    Info
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export const CatalogPage: React.FC = () => {
    const { data: scrapers, isLoading } = useScrapers();
    const { startScraper } = useScraperActions();
    const [filter, setFilter] = useState('');

    const filteredScrapers = useMemo(() => {
        if (!scrapers) return [];
        const term = filter.toLowerCase();
        return scrapers.filter(s =>
            s.name.toLowerCase().includes(term) ||
            s.display_name.toLowerCase().includes(term) ||
            s.description.toLowerCase().includes(term)
        );
    }, [scrapers, filter]);

    return (
        <div className="space-y-10">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
                <div>
                    <h2 className="text-3xl font-black text-white flex items-center gap-4 tracking-tighter uppercase">
                        <div className="p-2.5 bg-primary/10 rounded-2xl">
                            <Database className="text-primary w-8 h-8" />
                        </div>
                        Scraper List
                    </h2>
                    <p className="text-secondary text-xs mt-2 font-bold uppercase tracking-[0.2em]">Manage and run available scrapers</p>
                </div>
                <div className="relative group">
                    <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-secondary group-focus-within:text-primary transition-colors" />
                    <input
                        placeholder="SEARCH SCRAPERS BY NAME OR TAG..."
                        value={filter}
                        onChange={(e) => setFilter(e.target.value)}
                        className="glass-input w-full md:w-96 pl-12 pr-6 uppercase text-[11px] font-black tracking-widest placeholder:text-secondary/30"
                    />
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 2xl:grid-cols-3 gap-8">
                <AnimatePresence mode="popLayout">
                    {isLoading ? (
                        [...Array(6)].map((_, i) => (
                            <div key={i} className="h-72 glass-card animate-pulse" />
                        ))
                    ) : filteredScrapers.map((scraper, index) => (
                        <motion.div
                            key={scraper.name}
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: index * 0.05, duration: 0.5 }}
                            layout
                        >
                            <Card
                                className="h-full group"
                                footer={
                                    <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 bg-transparent">
                                        <div className="flex items-center gap-3">
                                            <div className={cn("w-2.5 h-2.5 rounded-full shadow-lg", scraper.enabled ? "bg-success shadow-glow-success animate-pulse" : "bg-secondary/30")} />
                                            <span className="text-[10px] font-black text-secondary uppercase tracking-[0.2em]">{scraper.enabled ? 'ACTIVE' : 'DISABLED'}</span>
                                        </div>
                                        <Button
                                            size="sm"
                                            onClick={() => startScraper.mutate(scraper.name)}
                                            disabled={!scraper.enabled}
                                            isLoading={startScraper.isPending && startScraper.variables === scraper.name}
                                            className="gap-2 px-8 uppercase text-[10px] w-full sm:w-auto"
                                        >
                                            <Rocket className="w-3.5 h-3.5" />
                                            {scraper.enabled ? 'RUN' : 'DISABLED'}
                                        </Button>
                                    </div>
                                }
                            >
                                <div className="flex items-start justify-between mb-6">
                                    <div className="p-4 bg-white/[0.03] border border-white/10 rounded-2xl group-hover:border-primary/50 transition-all duration-500 group-hover:bg-primary/[0.05] group-hover:shadow-glow-primary">
                                        <Globe className="w-8 h-8 text-secondary group-hover:text-primary transition-all duration-500" />
                                    </div>
                                    <Badge variant="neutral">MODEL.V1</Badge>
                                </div>

                                <h3 className="text-xl font-black text-white mb-3 group-hover:text-primary transition-colors tracking-tight">
                                    {scraper.display_name || scraper.name}
                                </h3>
                                <p className="text-secondary text-[11px] leading-relaxed line-clamp-3 mb-8 font-bold uppercase tracking-wide opacity-70">
                                    {scraper.description || 'Enterprise-grade scraping logic for aviation portal data extraction and pre-filtering.'}
                                </p>

                                <div className="flex flex-wrap gap-3 mt-auto">
                                    <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white/[0.02] border border-white/[0.05] text-[9px] font-black text-secondary uppercase tracking-[0.15em] transition-all group-hover:border-white/20">
                                        <Tag className="w-2.5 h-2.5" /> Aviation
                                    </div>
                                    <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white/[0.02] border border-white/[0.05] text-[9px] font-black text-secondary uppercase tracking-[0.15em] transition-all group-hover:border-white/20">
                                        <Tag className="w-2.5 h-2.5" /> Intel
                                    </div>
                                    {scraper.active_jobs ? (
                                        <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-primary/10 border border-primary/20 text-[9px] font-black text-primary uppercase tracking-[0.15em]">
                                            <Tag className="w-2.5 h-2.5" /> {scraper.active_jobs} Active Job{scraper.active_jobs > 1 ? 's' : ''}
                                        </div>
                                    ) : null}
                                    {scraper.schedule?.schedule_enabled ? (
                                        <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-info/10 border border-info/20 text-[9px] font-black text-info uppercase tracking-[0.15em]">
                                            <Tag className="w-2.5 h-2.5" /> {scraper.schedule.schedule_cron}
                                        </div>
                                    ) : null}
                                </div>
                            </Card>
                        </motion.div>
                    ))}
                </AnimatePresence>
            </div>

            {!isLoading && filteredScrapers.length === 0 && (
                <div className="py-20 text-center">
                    <Info className="w-12 h-12 text-secondary/20 mx-auto mb-4" />
                    <p className="text-secondary font-medium">No scrapers matching your criteria were found.</p>
                </div>
            )}
        </div>
    );
};
