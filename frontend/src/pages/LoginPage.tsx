import React, { useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { Plane, Lock, User, AlertCircle } from 'lucide-react';
import { motion } from 'framer-motion';

export const LoginPage: React.FC = () => {
    const [username, setUsername] = useState('admin');
    const [password, setPassword] = useState('');
    const { login, isLoading, error } = useAuth();

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            await login(username, password);
        } catch (err) {
            // Error handled by hook
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center bg-background px-4 relative overflow-hidden text-slate-200">
            {/* Background Decor */}
            <div className="absolute top-[-10%] right-[-10%] w-[50%] h-[50%] bg-primary/20 blur-[150px] rounded-full animate-float" />
            <div className="absolute bottom-[-10%] left-[-10%] w-[40%] h-[40%] bg-indigo-500/10 blur-[120px] rounded-full animate-float" style={{ animationDelay: '1s' }} />

            <motion.div
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.8, ease: "easeOut" }}
                className="w-full max-w-md relative z-10"
            >
                <div className="text-center mb-12">
                    <motion.div
                        initial={{ scale: 0.8, opacity: 0 }}
                        animate={{ scale: 1, opacity: 1 }}
                        transition={{ delay: 0.2, duration: 0.5 }}
                        className="w-20 h-20 bg-primary rounded-3xl flex items-center justify-center shadow-glow-primary mx-auto mb-8"
                    >
                        <Plane className="text-white w-10 h-10 rotate-45" />
                    </motion.div>
                    <h1 className="text-4xl font-black tracking-tighter text-white mb-3 text-transparent bg-clip-text bg-gradient-to-br from-white to-white/40">AEROOPS INTEL</h1>
                    <p className="text-xs font-black text-primary uppercase tracking-[0.4em]">Control Center</p>
                </div>

                <Card className="p-10 border-white/5 bg-white/[0.02] backdrop-blur-3xl shadow-none">
                    <form onSubmit={handleSubmit} className="space-y-8">
                        <div className="space-y-3">
                            <label className="text-[10px] font-black text-secondary uppercase tracking-[0.2em] ml-1">Username</label>
                            <div className="relative group">
                                <User className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-secondary group-focus-within:text-primary transition-colors" />
                                <input
                                    type="text"
                                    value={username}
                                    onChange={(e) => setUsername(e.target.value)}
                                    className="glass-input w-full pl-12 pr-4"
                                    placeholder="OPERATOR_CODE"
                                    required
                                />
                            </div>
                        </div>

                        <div className="space-y-3">
                            <label className="text-[10px] font-black text-secondary uppercase tracking-[0.2em] ml-1">Password</label>
                            <div className="relative group">
                                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-secondary group-focus-within:text-primary transition-colors" />
                                <input
                                    type="password"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    className="glass-input w-full pl-12 pr-4"
                                    placeholder="••••••••"
                                    required
                                />
                            </div>
                        </div>

                        {error && (
                            <motion.div
                                initial={{ opacity: 0, x: -10 }}
                                animate={{ opacity: 1, x: 0 }}
                                className="flex items-center gap-3 p-4 rounded-2xl bg-danger/10 border border-danger/20 text-danger text-[11px] font-bold uppercase tracking-wider"
                            >
                                <AlertCircle className="w-4 h-4 shrink-0" />
                                {error}
                            </motion.div>
                        )}

                        <Button
                            type="submit"
                            className="w-full py-5 rounded-2xl text-xs font-black tracking-[0.2em] shadow-glow-primary"
                            isLoading={isLoading}
                        >
                            LOGIN
                        </Button>
                    </form>
                </Card>

                <div className="flex items-center justify-center gap-8 mt-12 opacity-30 select-none">
                    <div className="h-px bg-white/20 flex-1" />
                    <p className="text-[10px] font-black text-white uppercase tracking-[0.5em] whitespace-nowrap">Secure Login</p>
                    <div className="h-px bg-white/20 flex-1" />
                </div>

                <p className="text-center mt-8 text-[10px] text-secondary font-black uppercase tracking-[0.2em]">
                    Secure management interface. Unauthorized access is logged.
                </p>
            </motion.div>
        </div>
    );
};
