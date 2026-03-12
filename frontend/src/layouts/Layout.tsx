import React, { useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { useAuth } from '../hooks/useAuth';
import { useHealth } from '../hooks/useScrapers';
import {
    LayoutDashboard,
    History,
    Settings,
    Search,
    LogOut,
    Activity,
    Menu,
    Plane,
    Briefcase,
    Database,
} from 'lucide-react';
import { cn } from '../services/utils';
import type { View } from '../types';

interface LayoutProps {
    children: ReactNode;
    activeView: View;
    setActiveView: (view: View) => void;
}

const NavItem: React.FC<{
    icon: any;
    label: string;
    active: boolean;
    onClick: () => void;
}> = ({ icon: Icon, label, active, onClick }) => (
    <button
        onClick={onClick}
        className={cn(
            'w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all group',
            active
                ? 'bg-primary text-white shadow-lg shadow-primary/30'
                : 'text-secondary hover:text-white hover:bg-white/5'
        )}
    >
        <Icon className={cn('w-5 h-5 transition-transform group-hover:scale-110', active ? 'text-white' : 'text-secondary')} />
        <span className="font-medium text-sm">{label}</span>
    </button>
);

export const Layout: React.FC<LayoutProps> = ({ children, activeView, setActiveView }) => {
    const { logout, isLoggedIn, username } = useAuth();
    const { data: healthStatus } = useHealth();
    const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

    const viewTitle = useMemo(() => {
        switch (activeView) {
            case 'configs':
                return 'Parameters';
            case 'catalog':
                return 'Scrapers';
            case 'jobs':
                return 'Managed Jobs';
            case 'scraped':
                return 'Scraped Records';
            default:
                return activeView;
        }
    }, [activeView]);

    const renderNav = () => (
        <nav className="flex-1 flex flex-col gap-3 mt-4">
            <NavItem
                icon={LayoutDashboard}
                label="Dashboard"
                active={activeView === 'dashboard'}
                onClick={() => {
                    setActiveView('dashboard');
                    setIsMobileMenuOpen(false);
                }}
            />
            <NavItem
                icon={Search}
                label="Scrapers"
                active={activeView === 'catalog'}
                onClick={() => {
                    setActiveView('catalog');
                    setIsMobileMenuOpen(false);
                }}
            />
            <NavItem
                icon={Briefcase}
                label="Jobs"
                active={activeView === 'jobs'}
                onClick={() => {
                    setActiveView('jobs');
                    setIsMobileMenuOpen(false);
                }}
            />
            <NavItem
                icon={Database}
                label="Scraped"
                active={activeView === 'scraped'}
                onClick={() => {
                    setActiveView('scraped');
                    setIsMobileMenuOpen(false);
                }}
            />
            <NavItem
                icon={History}
                label="History"
                active={activeView === 'history'}
                onClick={() => {
                    setActiveView('history');
                    setIsMobileMenuOpen(false);
                }}
            />
            <NavItem
                icon={Settings}
                label="Configuration"
                active={activeView === 'configs'}
                onClick={() => {
                    setActiveView('configs');
                    setIsMobileMenuOpen(false);
                }}
            />
        </nav>
    );

    if (!isLoggedIn) return <>{children}</>;

    return (
        <div className="min-h-screen bg-background flex text-slate-200">
            {isMobileMenuOpen && (
                <button
                    aria-label="Close navigation"
                    className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
                    onClick={() => setIsMobileMenuOpen(false)}
                />
            )}

            {/* Sidebar */}
            <aside className={cn(
                "w-72 lg:w-64 glass-morphism flex flex-col p-6 gap-8 fixed inset-y-0 left-0 z-50 rounded-none border-y-0 border-l-0 shadow-none transition-transform duration-300",
                isMobileMenuOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
            )}>
                <div className="flex items-center gap-4 px-2">
                    <div className="h-12 w-12 rounded-2xl bg-primary/15 border border-primary/20 flex items-center justify-center text-primary shadow-glow-primary">
                        <Plane className="w-5 h-5 rotate-45" />
                    </div>
                    <div>
                        <h1 className="font-black text-xl tracking-tighter text-white">IFOA Scrapers</h1>
                        <p className="text-[10px] text-primary font-black uppercase tracking-[0.3em] -mt-1 leading-none">Dashboard</p>
                    </div>
                </div>

                {renderNav()}

                <div className="mt-auto pt-8 border-t border-white/[0.08] flex flex-col gap-6">
                    <div className="flex items-center justify-between px-3">
                        <div className="flex items-center gap-3">
                            <Activity className="w-4 h-4 text-secondary" />
                            <span className="text-xs text-secondary font-bold uppercase tracking-widest">Health</span>
                        </div>
                        <div className="flex items-center gap-2">
                            {healthStatus === 'ok' ? (
                                <>
                                    <div className="w-2 h-2 rounded-full bg-success animate-pulse shadow-glow-success" />
                                    <span className="text-[10px] font-black text-success uppercase tracking-widest">Online</span>
                                </>
                            ) : (
                                <>
                                    <div className="w-2 h-2 rounded-full bg-danger animate-pulse" />
                                    <span className="text-[10px] font-black text-danger uppercase tracking-widest">Offline</span>
                                </>
                            )}
                        </div>
                    </div>
                    <button
                        onClick={logout}
                        className="flex items-center gap-4 px-4 py-4 rounded-2xl text-secondary hover:text-white hover:bg-danger/10 hover:text-danger transition-all group font-bold"
                    >
                        <LogOut className="w-5 h-5 group-hover:-translate-x-1 transition-transform" />
                        <span className="text-xs uppercase tracking-[0.2em]">Sign Out</span>
                    </button>
                </div>
            </aside>

            {/* Main Content */}
            <main className="flex-1 min-h-screen transition-all lg:ml-64">
                <header className="min-h-24 flex items-center justify-between gap-4 px-4 sm:px-6 lg:px-12 py-4 sticky top-0 bg-background/80 backdrop-blur-2xl z-30 border-b border-white/[0.05]">
                    <div className="flex items-center gap-4 min-w-0">
                        <button
                            type="button"
                            className="lg:hidden h-11 w-11 rounded-2xl border border-white/10 bg-white/[0.03] flex items-center justify-center text-white"
                            onClick={() => setIsMobileMenuOpen(true)}
                            aria-label="Open navigation"
                        >
                            <Menu className="w-5 h-5" />
                        </button>
                        <div className="min-w-0">
                        <h2 className="text-xl sm:text-2xl font-black text-white uppercase tracking-tighter truncate">{viewTitle}</h2>
                        <div className="h-1 w-12 bg-primary rounded-full mt-1 shadow-glow-primary"></div>
                        </div>
                    </div>
                    <div className="flex items-center gap-3 sm:gap-6">
                        <div className="hidden sm:flex flex-col items-end">
                            <span className="text-sm font-black text-white uppercase tracking-widest">{username ?? 'Admin User'}</span>
                            <span className="text-[10px] text-secondary font-bold uppercase tracking-[0.2em] mt-0.5">Control Panel Access</span>
                        </div>
                        <div className="w-11 h-11 sm:w-12 sm:h-12 rounded-2xl bg-white/[0.03] border border-white/10 flex items-center justify-center text-primary font-black shadow-inner shrink-0">
                            {(username ?? 'AD').slice(0, 2).toUpperCase()}
                        </div>
                        <button
                            type="button"
                            className="lg:hidden h-11 w-11 rounded-2xl border border-white/10 bg-white/[0.03] flex items-center justify-center text-white"
                            onClick={logout}
                            aria-label="Sign out"
                        >
                            <LogOut className="w-5 h-5" />
                        </button>
                    </div>
                </header>
                <div className="p-4 sm:p-6 lg:p-12 max-w-[1400px] mx-auto">
                    {children}
                </div>
            </main>
        </div>
    );
};
