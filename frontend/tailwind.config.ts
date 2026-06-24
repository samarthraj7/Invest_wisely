import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          50: "#f7f8fa",
          100: "#eef0f4",
          200: "#e1e5ec",
          300: "#cbd2dd",
          400: "#8b94a7",
          500: "#5f6982",
          600: "#444d63",
          700: "#2d3447",
          800: "#1b2130",
          900: "#10141f",
          950: "#080b12",
        },
        brand: {
          50: "#eef2ff",
          100: "#e0e7ff",
          400: "#818cf8",
          500: "#6366f1",
          600: "#4f46e5",
          700: "#4338ca",
        },
        violet: {
          400: "#a78bfa",
          500: "#8b5cf6",
          600: "#7c3aed",
        },
      },
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
      },
      boxShadow: {
        soft: "0 1px 2px rgba(16,24,40,.04), 0 12px 32px rgba(16,24,40,.08)",
        glow: "0 8px 40px rgba(99,102,241,.28)",
        card: "0 1px 0 rgba(16,24,40,.02), 0 6px 24px rgba(16,24,40,.06)",
      },
      keyframes: {
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        shimmer: {
          "100%": { transform: "translateX(100%)" },
        },
        pulseRing: {
          "0%,100%": { opacity: "1" },
          "50%": { opacity: ".35" },
        },
      },
      animation: {
        "fade-up": "fade-up .4s ease both",
        shimmer: "shimmer 1.6s infinite",
        "pulse-ring": "pulseRing 1.4s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;
