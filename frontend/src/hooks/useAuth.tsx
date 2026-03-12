import React, { createContext, useContext, useState, useCallback } from 'react';
import type { ReactNode } from 'react';
import api from '../services/api';

interface AuthContextType {
    token: string | null;
    username: string | null;
    isLoggedIn: boolean;
    login: (username: string, password: string) => Promise<void>;
    logout: () => void;
    error: string | null;
    isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
    const [token, setToken] = useState<string | null>(localStorage.getItem('aeroops_token'));
    const [username, setUsername] = useState<string | null>(localStorage.getItem('aeroops_username'));
    const [error, setError] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(false);

    const login = useCallback(async (username: string, password: string) => {
        setIsLoading(true);
        setError(null);
        try {
            const { data } = await api.post('/auth/login/', { username, password });
            localStorage.setItem('aeroops_token', data.token);
            localStorage.setItem('aeroops_username', data.username ?? username);
            setToken(data.token);
            setUsername(data.username ?? username);
        } catch (err: any) {
            setError(err.response?.data?.error || 'Login failed');
            throw err;
        } finally {
            setIsLoading(false);
        }
    }, []);

    const logout = useCallback(() => {
        localStorage.removeItem('aeroops_token');
        localStorage.removeItem('aeroops_username');
        setToken(null);
        setUsername(null);
        setError(null);
    }, []);

    return (
        <AuthContext.Provider
            value={{
                token,
                username,
                isLoggedIn: !!token,
                login,
                logout,
                error,
                isLoading,
            }}
        >
            {children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
};
