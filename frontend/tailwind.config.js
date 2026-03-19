/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    darkMode: 'class',
    theme: {
        extend: {
            colors: {
                background: '#030712',
                surface: '#0F172A',
                primary: {
                    DEFAULT: '#1E40AF', // Deep Blue 800
                    dark: '#1E3A8A',    // Deep Blue 900
                    glow: 'rgba(30, 64, 175, 0.5)',
                },
                secondary: '#94A3B8',
                success: '#10B981',
                warning: '#F59E0B',
                danger: '#EF4444',
                info: '#3B82F6',
            },
            fontFamily: {
                sans: ['Inter', 'system-ui', 'sans-serif'],
                mono: ['Fira Code', 'monospace'],
            },
            animation: {
                'scan': 'scan 3s linear infinite',
                'float': 'float 6s ease-in-out infinite',
            },
            keyframes: {
                scan: {
                    '0%': { transform: 'translateY(-100%)' },
                    '100%': { transform: 'translateY(100%)' },
                },
                float: {
                    '0%, 100%': { transform: 'translateY(0)' },
                    '50%': { transform: 'translateY(-10px)' },
                }
            },
            boxShadow: {
                'glow-primary': '0 0 20px rgba(30, 64, 175, 0.4)',
                'glow-blue': '0 0 25px rgba(30, 64, 175, 0.25)',
                'glow-success': '0 0 15px rgba(16, 185, 129, 0.3)',
            }
        },
    },
    plugins: [],
}
