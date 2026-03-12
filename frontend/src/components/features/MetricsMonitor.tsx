import React from 'react';
import { useSystemMetrics } from '../../hooks/useScrapers';
import { Card } from '../ui/Card';
import { Activity, Cpu, Database, HardDrive } from 'lucide-react';
import { motion } from 'framer-motion';

export const MetricsMonitor: React.FC = () => {
    const { data: metrics, isLoading } = useSystemMetrics(true);

    const formatBytes = (bytes: number) => {
        if (!bytes) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    };

    const MetricRing = ({ percentage, color, icon: Icon, label, value }: any) => (
        <div className="flex flex-col items-center gap-3">
            <div className="relative w-24 h-24">
                <svg className="w-full h-full -rotate-90" viewBox="0 0 100 100">
                    <circle
                        className="text-white/5"
                        strokeWidth="8"
                        stroke="currentColor"
                        fill="transparent"
                        r="40"
                        cx="50"
                        cy="50"
                    />
                    <motion.circle
                        className={color}
                        strokeWidth="8"
                        strokeDasharray={251.2}
                        initial={{ strokeDashoffset: 251.2 }}
                        animate={{ strokeDashoffset: 251.2 - (251.2 * percentage) / 100 }}
                        transition={{ duration: 1, ease: "easeOut" }}
                        strokeLinecap="round"
                        stroke="currentColor"
                        fill="transparent"
                        r="40"
                        cx="50"
                        cy="50"
                    />
                </svg>
                <div className="absolute inset-0 flex items-center justify-center">
                    <Icon className="w-6 h-6 text-white/50" />
                </div>
            </div>
            <div className="text-center">
                <p className="text-[10px] font-bold text-secondary uppercase tracking-widest mb-1">{label}</p>
                <p className="text-sm font-black text-white">{value || '0%'}</p>
            </div>
        </div>
    );

    return (
        <Card className="h-full">
            <div className="flex items-center justify-between mb-8">
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-primary/10 rounded-lg">
                        <Activity className="w-4 h-4 text-primary" />
                    </div>
                    <h3 className="text-sm font-bold text-white uppercase tracking-wider">System Status</h3>
                </div>
                <div className="flex items-center gap-2">
                    <div className="w-1.5 h-1.5 rounded-full bg-success animate-pulse" />
                    <span className="text-[10px] font-bold text-success uppercase tracking-widest">Live</span>
                </div>
            </div>

            {isLoading ? (
                <div className="grid grid-cols-3 gap-4 animate-pulse">
                    {[1, 2, 3].map(i => <div key={i} className="h-32 bg-white/5 rounded-2xl" />)}
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                    <MetricRing
                        percentage={metrics?.cpu.percent}
                        color="text-primary"
                        icon={Cpu}
                        label="CPU Usage"
                        value={`${metrics?.cpu.percent.toFixed(1)}%`}
                    />
                    <MetricRing
                        percentage={metrics?.memory.percent}
                        color="text-info"
                        icon={Database}
                        label="Memory Usage"
                        value={formatBytes(metrics?.memory.used || 0)}
                    />
                    <MetricRing
                        percentage={metrics?.disk.percent}
                        color="text-secondary"
                        icon={HardDrive}
                        label="Storage Capacity"
                        value={`${metrics?.disk.percent.toFixed(1)}%`}
                    />
                </div>
            )}

            {!isLoading && (
                <div className="mt-8 pt-6 border-t border-white/[0.05] grid grid-cols-2 gap-4">
                    <div className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.05]">
                        <p className="text-[9px] font-bold text-secondary uppercase tracking-widest mb-1">Process Memory</p>
                        <p className="text-xs font-bold text-white">{formatBytes(metrics?.process.memory_info || 0)}</p>
                    </div>
                    <div className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.05]">
                        <p className="text-[9px] font-bold text-secondary uppercase tracking-widest mb-1">Active Threads</p>
                        <p className="text-xs font-bold text-white">{metrics?.process.threads} THREADS</p>
                    </div>
                </div>
            )}
        </Card>
    );
};
