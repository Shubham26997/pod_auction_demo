/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        gold: {
          DEFAULT: '#f0b429',
          light: '#f7d070',
          dark: '#c48d10',
        },
        metal: {
          bg: '#0d0f14',
          card: '#161920',
          border: '#1e2330',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      animation: {
        'pulse-subtle': 'pulse-subtle 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'bounce-dot': 'bounce-dot 1.4s infinite ease-in-out',
        'ticker': 'ticker 55s linear infinite',
        'scroll-up': 'scroll-up 22s linear infinite',
        'fade-in': 'fade-in 0.4s ease forwards',
        'fade-out': 'fade-out 0.4s ease forwards',
      },
      keyframes: {
        'pulse-subtle': {
          '0%, 100%': { opacity: 1 },
          '50%': { opacity: 0.4 },
        },
        'bounce-dot': {
          '0%, 80%, 100%': { transform: 'scale(0)', opacity: 0.3 },
          '40%': { transform: 'scale(1)', opacity: 1 },
        },
        'ticker': {
          '0%':   { transform: 'translateX(0)' },
          '100%': { transform: 'translateX(-50%)' },
        },
        'scroll-up': {
          '0%':   { transform: 'translateY(0)' },
          '100%': { transform: 'translateY(-50%)' },
        },
        'fade-in': {
          '0%':   { opacity: 0, transform: 'translateY(8px)' },
          '100%': { opacity: 1, transform: 'translateY(0)' },
        },
        'fade-out': {
          '0%':   { opacity: 1, transform: 'translateY(0)' },
          '100%': { opacity: 0, transform: 'translateY(-8px)' },
        },
      },
    },
  },
  plugins: [],
}
