import React from 'react';
import { cn } from '../../services/utils';

interface CardProps {
    children: React.ReactNode;
    className?: string;
    title?: React.ReactNode;
    subtitle?: string;
    footer?: React.ReactNode;
}

export const Card: React.FC<CardProps> = ({ children, className, title, subtitle, footer }) => {
    return (
        <div className={cn('glass-card flex flex-col', className)}>
            {title && (
                <div className="px-6 py-5 border-b border-white/[0.08]">
                    {typeof title === 'string' ? (
                        <h3 className="text-lg font-bold text-white tracking-tight">{title}</h3>
                    ) : (
                        title
                    )}
                    {subtitle && <p className="text-xs text-secondary mt-1 font-medium">{subtitle}</p>}
                </div>
            )}
            <div className="p-6 flex-1">{children}</div>
            {footer && <div className="px-6 py-4 bg-white/[0.02] border-t border-white/[0.08] backdrop-blur-md">{footer}</div>}
        </div>
    );
};
