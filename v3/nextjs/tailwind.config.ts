import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./src/**/*.{js,ts,jsx,tsx,mdx}'],
  theme: {
    extend: {
      colors: {
        root: '#fafaf7',
        surface: '#f3f2ed',
        data: '#f5f4ee',
        accent: {
          DEFAULT: '#c8842a',
          glow: 'rgba(200, 132, 42, 0.08)',
          hover: '#d4953e',
        },
        cool: '#5b7a8c',
        'text-primary': '#1c1c1a',
        'text-secondary': '#6b6a63',
        'text-data': '#2a2820',
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
      },
      spacing: {
        1: '8px', // 8px baseline grid
        2: '16px',
        3: '24px',
        4: '32px',
        6: '48px',
        8: '64px',
      },
    },
  },
  plugins: [],
};

export default config;
