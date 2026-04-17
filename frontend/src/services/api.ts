import axios from 'axios';
import { emitAppToast } from './toast';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8008/api/scrapers';
const DB_API_BASE = 'http://localhost:8008/api/db';

const createApiInstance = (baseURL: string) => {
    const instance = axios.create({
        baseURL,
        headers: {
            'Content-Type': 'application/json',
        },
    });

    instance.interceptors.request.use((config) => {
        const token = localStorage.getItem('aeroops_token');
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    });

    instance.interceptors.response.use(
        (response) => response,
        (error) => {
            const requestUrl = String(error.config?.url ?? '');
            const isLoginRequest = requestUrl.includes('/auth/login/');
            const hasStoredToken = !!localStorage.getItem('aeroops_token');

            if (error.response?.status === 401 && !isLoginRequest && hasStoredToken) {
                emitAppToast({
                    level: 'error',
                    message: 'Session expired. Please log in again.',
                    durationMs: 1800,
                });
                localStorage.removeItem('aeroops_token');
                localStorage.removeItem('aeroops_username');
                window.setTimeout(() => {
                    window.location.reload();
                }, 1200);
            }
            return Promise.reject(error);
        }
    );

    return instance;
};

const api = createApiInstance(API_BASE);
export const dbApi = createApiInstance(DB_API_BASE);

export default api;
