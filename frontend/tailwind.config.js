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
        conformance: {
          bg: '#080b11',
          sidebar: '#07090e',
          card: '#0e131d',
          cardHover: '#131a27',
          cardInner: '#0a0e17',
          border: '#182030',
          borderLight: '#222d42',
          lime: '#a3e635',
          limeDark: '#4d7c0f',
          red: '#f87171',
          amber: '#fbbf24',
          cyan: '#38bdf8',
          blue: '#60a5fa',
          purple: '#c084fc',
          emerald: '#34d399',
          textMuted: '#8b9bb4',
          textSub: '#5d6d85'
        }
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'Menlo', 'monospace']
      }
    },
  },
  plugins: [],
}
