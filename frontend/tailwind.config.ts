import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        studio: {
          deep: "#0d0d1a",
          panel: "#1a1a2e",
          card: "#242440",
          hover: "#2d2d50",
          border: "#2a2a45",
        },
        accent: {
          warm: "#e2a03f",
          coral: "#ff6b6b",
          teal: "#4ecdc4",
          violet: "#9b59b6",
        },
        text: {
          primary: "#f0ece2",
          secondary: "#a0a0b0",
          dim: "#6a6a7a",
        },
      },
      fontFamily: {
        display: ['"Playfair Display"', 'Georgia', 'serif'],
        body: ['"Crimson Text"', 'Georgia', 'serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      animation: {
        "pulse-glow": "pulse-glow 2s ease-in-out infinite",
        "slide-up": "slide-up 0.6s ease-out forwards",
        "fade-in": "fade-in 0.4s ease-out forwards",
        "on-air": "on-air-blink 1.5s ease-in-out infinite",
      },
      keyframes: {
        "pulse-glow": {
          "0%, 100%": { boxShadow: "0 0 10px rgba(226, 160, 63, 0.2)" },
          "50%": { boxShadow: "0 0 20px rgba(226, 160, 63, 0.27), 0 0 40px rgba(226, 160, 63, 0.13)" },
        },
        "slide-up": {
          from: { opacity: "0", transform: "translateY(20px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        "fade-in": {
          from: { opacity: "0" },
          to: { opacity: "1" },
        },
        "on-air-blink": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.3" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
