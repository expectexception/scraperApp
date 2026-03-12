import React from 'react';
import type { ReactNode } from 'react';
import { useAuth } from '../hooks/useAuth';
import { useHealth } from '../hooks/useScrapers';
import {
    LayoutDashboard,
    History,
    Settings,
    Search,
    LogOut,
    Activity
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
    const { logout, isLoggedIn } = useAuth();
    const { data: healthStatus } = useHealth();

    if (!isLoggedIn) return <>{children}</>;

    return (
        <div className="min-h-screen bg-background flex text-slate-200">
            {/* Sidebar */}
            <aside className="w-64 glass-morphism flex flex-col p-6 gap-8 fixed inset-y-0 z-50 rounded-none border-y-0 border-l-0 shadow-none">
                <div className="flex items-center gap-4 px-2">
                    <div>
                        <h1 className="font-black text-xl tracking-tighter text-white">IFOA Scrapers</h1>
                        <p className="text-[10px] text-primary font-black uppercase tracking-[0.3em] -mt-1 leading-none">Dashboard</p>
                    </div>
                </div>

                <nav className="flex-1 flex flex-col gap-3 mt-4">
                    <NavItem
                        icon={LayoutDashboard}
                        label="Dashboard"
                        active={activeView === 'dashboard'}
                        onClick={() => setActiveView('dashboard')}
                    />
                    <NavItem
                        icon={Search}
                        label="Scrapers"
                        active={activeView === 'catalog'}
                        onClick={() => setActiveView('catalog')}
                    />
                    <NavItem
                        icon={History}
                        label="History"
                        active={activeView === 'history'}
                        onClick={() => setActiveView('history')}
                    />
                    <NavItem
                        icon={Settings}
                        label="Configuration"
                        active={activeView === 'configs'}
                        onClick={() => setActiveView('configs')}
                    />
                </nav>

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
            <main className="flex-1 ml-64 min-h-screen transition-all">
                <header className="h-24 flex items-center justify-between px-12 sticky top-0 bg-background/60 backdrop-blur-2xl z-40 border-b border-white/[0.05]">
                    <div>
                        <h2 className="text-2xl font-black text-white uppercase tracking-tighter">{activeView === 'configs' ? 'Parameters' : activeView}</h2>
                        <div className="h-1 w-12 bg-primary rounded-full mt-1 shadow-glow-primary"></div>
                    </div>
                    <div className="flex items-center gap-6">
                        <div className="flex flex-col items-end">
                            <span className="text-sm font-black text-white uppercase tracking-widest">Admin User</span>
                            <span className="text-[10px] text-secondary font-bold uppercase tracking-[0.2em] mt-0.5">Control Panel Access</span>
                        </div>
                        <div className="w-12 h-12 rounded-2xl bg-white/[0.03] border border-white/10 flex items-center justify-center text-primary font-black shadow-inner">
                            AD
                        </div>
                    </div>
                </header>
                <div className="p-12 max-w-[1400px] mx-auto">
                    {children}
                </div>
            </main>
        </div>
    );
};
