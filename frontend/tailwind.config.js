// frontend/tailwind.config.js
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#fff1f1',
          100: '#ffe1e1',
          200: '#ffc7c7',
          300: '#ffa0a0',
          400: '#ff6969',
          500: '#e6000f',  // Main Swisson brand color
          600: '#c70010',  // Hover state
          700: '#a80011',  // Active/pressed state
          800: '#8a0012',  // Dark variant
          900: '#6b0013',  // Darkest variant
        },
      },
    },
  },
  plugins: [],
}