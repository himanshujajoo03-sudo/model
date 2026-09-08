/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Pure White Canvas & Neutral Scale
        'bg-base': '#FFFFFF',
        'bg-surface': '#FFFFFF',
        'bg-elevated': '#F8FAFC',
        'bg-raised': '#F1F5F9',
        'bg-border': '#E2E8F0',
        'bg-strong-border': '#CBD5E1',

        // Typography Tokens
        'text-primary': '#0F172A',
        'text-secondary': '#475569',
        'text-muted': '#94A3B8',

        // Indian-Inspired Sophisticated Palette
        'brand-blue': {
          50: '#EFF6FF',
          100: '#DBEAFE',
          500: '#2563EB',
          600: '#1D4ED8',
          700: '#1E3A8A',
        },
        'brand-saffron': {
          50: '#FFF7ED',
          100: '#FFEDD5',
          500: '#F97316',
          600: '#EA580C',
          700: '#C2410C',
        },
        'brand-emerald': {
          50: '#ECFDF5',
          100: '#D1FAE5',
          500: '#10B981',
          600: '#059669',
          700: '#047857',
        },
        'brand-teal': {
          50: '#F0FDFA',
          100: '#CCFBF1',
          500: '#14B8A6',
          600: '#0D9488',
          700: '#0F766E',
        },
        'brand-cyan': {
          50: '#ECFEFF',
          100: '#CFFAFE',
          500: '#06B6D4',
          600: '#0284C7',
          700: '#0369A1',
        },

        // Status Colors
        'accent': '#EA580C',
        'steel': '#2563EB',
        'steel-light': '#EFF6FF',
        'success': '#059669',
        'success-light': '#ECFDF5',
        'warning': '#D97706',
        'warning-light': '#FEF3C7',
        'critical': '#DC2626',
        'critical-light': '#FEE2E2',
      },
      fontFamily: {
        'sans': ['"Plus Jakarta Sans"', '"Inter"', 'system-ui', 'sans-serif'],
        'display': ['"Plus Jakarta Sans"', 'sans-serif'],
        'mono': ['"IBM Plex Mono"', 'ui-monospace', 'monospace'],
      },
      borderRadius: {
        'panel': '12px',
        'card': '10px',
      },
      boxShadow: {
        'xs': '0 1px 2px 0 rgba(0, 0, 0, 0.04)',
        'sm': '0 1px 3px 0 rgba(0, 0, 0, 0.06), 0 1px 2px -1px rgba(0, 0, 0, 0.04)',
        'card': '0 1px 3px rgba(15, 23, 42, 0.06), 0 1px 2px rgba(15, 23, 42, 0.04)',
        'card-hover': '0 8px 20px -4px rgba(15, 23, 42, 0.08), 0 4px 8px -2px rgba(15, 23, 42, 0.04)',
        'dropdown': '0 10px 25px -5px rgba(15, 23, 42, 0.1), 0 8px 10px -6px rgba(15, 23, 42, 0.06)',
      },
    },
  },
  plugins: [],
}
