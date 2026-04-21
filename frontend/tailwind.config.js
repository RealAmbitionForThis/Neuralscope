/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,jsx}",
    "./components/**/*.{js,jsx}",
    "./hooks/**/*.{js,jsx}",
    "./lib/**/*.{js,jsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: "#0a0a0f",
        card: "#111118",
        panel: "#15151f",
        border: "#222230",
        muted: "#6b6b80",
        text: "#e6e6f0",
        accent: "#00f0ff",
        warn: "#ff9d00",
        danger: "#ff3333",
        ok: "#00ff88",
      },
      fontFamily: {
        sans: ["Geist", "Instrument Sans", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "IBM Plex Mono", "monospace"],
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(0, 240, 255, 0.25), 0 0 20px rgba(0, 240, 255, 0.15)",
      },
    },
  },
  plugins: [],
};
