import React from 'react';
import { cn } from '../../services/utils';

interface BadgeProps {
    children: React.ReactNode;
    variant?: 'success' | 'warning' | 'danger' | 'info' | 'neutral';
    className?: string;
}

export const Badge: React.FC<BadgeProps> = ({ children, variant = 'neutral', className }) => {
    const variants = {
        success: 'bg-success/10 text-success border-success/30 shadow-[0_0_8px_rgba(16,185,129,0.1)]',
        warning: 'bg-warning/10 text-warning border-warning/30 shadow-[0_0_8px_rgba(245,158,11,0.1)]',
        danger: 'bg-danger/10 text-danger border-danger/30 shadow-[0_0_8px_rgba(239,68,68,0.1)]',
        info: 'bg-info/10 text-info border-info/30 shadow-[0_0_8px_rgba(59,130,246,0.1)]',
        neutral: 'bg-white/5 text-secondary border-white/20',
    };

    return (
        <span
            className={cn(
                'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[9px] font-black uppercase tracking-widest border backdrop-blur-sm',
                variants[variant],
                className
            )}
        >
            {children}
        </span>
    );
};
