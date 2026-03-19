import React from 'react';
import { useSystemMetrics } from '../../hooks/useScrapers';
import { Card } from '../ui/Card';
import { Activity, Cpu, Database, HardDrive } from 'lucide-react';
import { motion } from 'framer-motion';

const formatBytes = (bytes: number) => {
    if (!bytes) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
};

const MetricRing = ({ percentage, color, icon: Icon, label, value }: any) => {
    const [displayPercentage, setDisplayPercentage] = React.useState(percentage || 0);
    const isFirstMount = React.useRef(true);

    React.useEffect(() => {
        if (typeof percentage === 'number') {
            setDisplayPercentage(percentage);
        }
    }, [percentage]);

    React.useEffect(() => {
        isFirstMount.current = false;
    }, []);

    return (
        <div className="flex flex-col items-center group">
            <div className="relative w-28 h-28 mb-4 transition-transform group-hover:scale-105 duration-500">
                <svg className="w-full h-full -rotate-90 filter drop-shadow-[0_0_12px_rgba(255,255,255,0.02)]" viewBox="0 0 100 100">
                    <circle
                        className="text-white/5"
                        strokeWidth="7"
                        stroke="currentColor"
                        fill="transparent"
                        r="42"
                        cx="50"
                        cy="50"
                    />
                    <motion.circle
                        className={color}
                        strokeWidth="7"
                        strokeDasharray={263.89}
                        initial={isFirstMount.current ? { strokeDashoffset: 263.89 } : false}
                        animate={{ strokeDashoffset: 263.89 - (263.89 * (displayPercentage)) / 100 }}
                        transition={{ duration: 1.5, ease: "circOut" }}
                        strokeLinecap="round"
                        stroke="currentColor"
                        fill="transparent"
                        r="42"
                        cx="50"
                        cy="50"
                    />
                </svg>
                <div className="absolute inset-0 flex items-center justify-center">
                    <div className="p-3 rounded-full bg-white/[0.03] border border-white/5 shadow-inner">
                        <Icon className="w-5 h-5 text-white/70" />
                    </div>
                </div>
            </div>
            <div className="text-center space-y-1">
                <p className="text-[10px] font-black text-secondary uppercase tracking-[0.2em]">{label}</p>
                <p className="text-lg font-black text-white tracking-tight">{value || '0%'}</p>
            </div>
        </div>
    );
};

export const MetricsMonitor: React.FC = () => {
    const { data: metrics, isLoading } = useSystemMetrics(true);

    // Only show skeleton on first load. Subsequent background refreshes keep the UI interactive.
    if (isLoading && !metrics) {
        return (
            <Card className="h-full" title="System Status" subtitle="Real-time infrastructure health monitor">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 animate-pulse py-4 items-center justify-items-center">
                    {[1, 2, 3].map(i => (
                        <div key={i} className="flex flex-col items-center gap-4">
                            <div className="w-28 h-28 rounded-full bg-white/5 border border-white/10" />
                            <div className="h-4 w-20 bg-white/5 rounded" />
                            <div className="h-6 w-16 bg-white/5 rounded" />
                        </div>
                    ))}
                </div>
            </Card>
        );
    }

    return (
        <Card className="h-full" title="System Status" subtitle="Real-time infrastructure health monitor">
            <div className="py-2">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-8 items-center justify-items-center">
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
                        color="text-success"
                        icon={HardDrive}
                        label="Storage"
                        value={`${metrics?.disk.percent.toFixed(1)}%`}
                    />
                </div>

                <div className="mt-10 pt-8 border-t border-white/[0.05] grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div className="p-4 rounded-2xl bg-white/[0.02] border border-white/[0.05] flex items-center justify-between group hover:bg-white/[0.04] transition-colors">
                        <div>
                            <p className="text-[9px] font-black text-secondary uppercase tracking-[0.25em] mb-1">Process Memory</p>
                            <p className="text-sm font-black text-white">{formatBytes(metrics?.process.memory_info || 0)}</p>
                        </div>
                        <div className="w-8 h-8 rounded-lg bg-info/10 flex items-center justify-center">
                            <Activity className="w-4 h-4 text-info" />
                        </div>
                    </div>
                    <div className="p-4 rounded-2xl bg-white/[0.02] border border-white/[0.05] flex items-center justify-between group hover:bg-white/[0.04] transition-colors">
                        <div>
                            <p className="text-[9px] font-black text-secondary uppercase tracking-[0.25em] mb-1">Active Threads</p>
                            <p className="text-sm font-black text-white">{metrics?.process.threads} UNITS</p>
                        </div>
                        <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
                            <Activity className="w-4 h-4 text-primary" />
                        </div>
                    </div>
                </div>
            </div>
        </Card>
    );
};
