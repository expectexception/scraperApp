import React from 'react';
import { Card } from '../ui/Card';
import { cn } from '../../services/utils';
import type { LucideIcon } from 'lucide-react';

interface StatTileProps {
    label: string;
    value: string | number;
    icon: LucideIcon;
    isLoading?: boolean;
    trend?: {
        value: number;
        isPositive: boolean;
    };
    className?: string;
}

export const StatTile: React.FC<StatTileProps> = ({ label, value, icon: Icon, isLoading, trend, className }) => {
    return (
        <Card className={cn('p-0', className)}>
            <div className="p-5 flex items-start justify-between">
                <div>
                    <p className="text-[10px] font-black text-secondary uppercase tracking-[0.15em] mb-1">{label}</p>
                    <div className="flex items-baseline gap-2 mt-1">
                        {isLoading ? (
                            <div className="h-8 w-20 bg-white/5 animate-pulse rounded" />
                        ) : (
                            <h2 className="text-2xl font-bold text-white tracking-tight">{value}</h2>
                        )}
                        {trend && (
                            <span className={cn('text-[10px] font-bold px-1 rounded', trend.isPositive ? 'text-success bg-success/10' : 'text-danger bg-danger/10')}>
                                {trend.isPositive ? '+' : ''}{trend.value}%
                            </span>
                        )}
                    </div>
                </div>
                <div className="p-2.5 bg-primary/10 rounded-lg text-primary">
                    <Icon className="w-5 h-5" />
                </div>
            </div>
        </Card>
    );
};
