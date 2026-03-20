import axios from 'axios';
import { emitAppToast } from './toast';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8008/api/scrapers';

const api = axios.create({
    baseURL: API_BASE,
    headers: {
        'Content-Type': 'application/json',
    },
});

let authExpiryHandled = false;

api.interceptors.request.use((config) => {
    const token = localStorage.getItem('aeroops_token');
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

api.interceptors.response.use(
    (response) => response,
    (error) => {
        const requestUrl = String(error.config?.url ?? '');
        const isLoginRequest = requestUrl.includes('/auth/login/');
        const hasStoredToken = !!localStorage.getItem('aeroops_token');

        if (error.response?.status === 401 && !isLoginRequest && hasStoredToken && !authExpiryHandled) {
            authExpiryHandled = true;
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

export default api;
