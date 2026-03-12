import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8008/api/scrapers';

const api = axios.create({
    baseURL: API_BASE,
    headers: {
        'Content-Type': 'application/json',
    },
});

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
        if (error.response?.status === 401) {
            localStorage.removeItem('aeroops_token');
            window.location.reload(); // Simple way to force logout/redirect to login page
        }
        return Promise.reject(error);
    }
);

export default api;
