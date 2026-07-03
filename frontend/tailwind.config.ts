import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./src/**/*.{astro,html,js,jsx,md,mdx,svelte,ts,tsx,vue}'],
  theme: {
    extend: {
      borderRadius: {
        sm: '6px',
        md: '10px',
        lg: '12px'
      },
      boxShadow: {
        soft: '0 2px 8px rgba(0, 0, 0, 0.08)',
        medium: '0 4px 16px rgba(0, 0, 0, 0.1)',
        strong: '0 8px 24px rgba(0, 0, 0, 0.12)'
      },
      colors: {
        primary: {
          DEFAULT: '#2563eb',
          hover: '#1d4ed8',
          light: '#dbeafe'
        },
        background: '#f5f5f5',
        surface: '#ffffff',
        border: '#e5e5e5',
        text: {
          DEFAULT: '#171717',
          secondary: '#737373'
        }
      },
      animation: {
        'fade-in': 'fadeIn 0.2s ease-out',
        'slide-up': 'slideUp 0.2s ease-out',
        'slide-down': 'slideDown 0.2s ease-out'
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' }
        },
        slideUp: {
          '0%': { transform: 'translateY(10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' }
        },
        slideDown: {
          '0%': { transform: 'translateY(-10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' }
        }
      }
    }
  },
  plugins: [require('tailwindcss-animate')]
};

export default config;
