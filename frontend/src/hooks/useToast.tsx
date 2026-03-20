import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { APP_TOAST_EVENT, type AppToastLevel, type AppToastPayload } from '../services/toast';

type ToastItem = {
    id: string;
    message: string;
    level: AppToastLevel;
};

type ToastContextValue = {
    showToast: (payload: AppToastPayload) => void;
};

const ToastContext = createContext<ToastContextValue | undefined>(undefined);

const levelStyles: Record<AppToastLevel, string> = {
    success: 'border-success/40 bg-success/10 text-success',
    error: 'border-danger/40 bg-danger/10 text-danger',
    info: 'border-info/40 bg-info/10 text-info',
};

export const ToastProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
    const [toasts, setToasts] = useState<ToastItem[]>([]);
    const timeoutsRef = useRef<Map<string, number>>(new Map());

    const removeToast = useCallback((id: string) => {
        setToasts((prev) => prev.filter((toast) => toast.id !== id));
        const timeoutId = timeoutsRef.current.get(id);
        if (timeoutId) {
            window.clearTimeout(timeoutId);
            timeoutsRef.current.delete(id);
        }
    }, []);

    const showToast = useCallback((payload: AppToastPayload) => {
        const id = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
        const level = payload.level ?? 'info';
        const durationMs = payload.durationMs ?? 3500;

        setToasts((prev) => [...prev, { id, message: payload.message, level }]);
        const timeoutId = window.setTimeout(() => removeToast(id), durationMs);
        timeoutsRef.current.set(id, timeoutId);
    }, [removeToast]);

    useEffect(() => {
        const handler = (event: Event) => {
            const customEvent = event as CustomEvent<AppToastPayload>;
            const payload = customEvent.detail;
            if (!payload?.message) return;
            showToast(payload);
        };

        window.addEventListener(APP_TOAST_EVENT, handler);
        return () => {
            window.removeEventListener(APP_TOAST_EVENT, handler);
            timeoutsRef.current.forEach((timeoutId) => window.clearTimeout(timeoutId));
            timeoutsRef.current.clear();
        };
    }, [showToast]);

    const value = useMemo(() => ({ showToast }), [showToast]);

    return (
        <ToastContext.Provider value={value}>
            {children}
            <div className="fixed top-4 right-4 z-[100] flex w-[min(92vw,420px)] flex-col gap-2">
                {toasts.map((toast) => (
                    <button
                        key={toast.id}
                        type="button"
                        onClick={() => removeToast(toast.id)}
                        className={`w-full rounded-2xl border px-4 py-3 text-left text-xs font-bold uppercase tracking-wider shadow-xl backdrop-blur ${levelStyles[toast.level]}`}
                        title="Click to dismiss"
                    >
                        {toast.message}
                    </button>
                ))}
            </div>
        </ToastContext.Provider>
    );
};

export const useToast = () => {
    const context = useContext(ToastContext);
    if (!context) {
        throw new Error('useToast must be used within a ToastProvider');
    }
    return context;
};
