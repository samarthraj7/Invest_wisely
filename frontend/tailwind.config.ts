import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          50: "#f6f7f9",
          100: "#eceef2",
          400: "#8a94a6",
          600: "#4b5468",
          800: "#1f2733",
          900: "#141a23",
          950: "#0b0f15",
        },
        brand: {
          400: "#7c9cff",
          500: "#5b7cfa",
          600: "#4361ee",
          700: "#3147c4",
        },
      },
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
      },
      boxShadow: {
        soft: "0 1px 2px rgba(16,24,40,.04), 0 8px 24px rgba(16,24,40,.06)",
      },
    },
  },
  plugins: [],
};

export default config;
