import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50:  "#ecfeff",
          100: "#cffafe",
          200: "#a5f3fc",
          300: "#67e8f9",
          400: "#22d3ee",
          500: "#06b6d4",
          600: "#0891b2",
          700: "#0e7490",
          800: "#155e75",
          900: "#164e63",
        },
        surface: {
          DEFAULT: "#06101f",
          2: "#081320",
          3: "#0d1b2f",
        },
      },
      boxShadow: {
        "glow-cyan":   "0 0 20px rgba(34,211,238,0.15), 0 0 40px rgba(34,211,238,0.05)",
        "glow-red":    "0 0 20px rgba(239,68,68,0.20),  0 0 40px rgba(239,68,68,0.05)",
        "glow-orange": "0 0 16px rgba(249,115,22,0.15)",
        "glow-green":  "0 0 16px rgba(34,197,94,0.15)",
        "glow-indigo": "0 0 20px rgba(99,102,241,0.20)",
      },
      keyframes: {
        "slide-in-from-right-5": {
          from: { transform: "translateX(20px)", opacity: "0" },
          to:   { transform: "translateX(0)",    opacity: "1" },
        },
        "fade-in": {
          from: { opacity: "0" },
          to:   { opacity: "1" },
        },
        "glow-pulse": {
          "0%, 100%": { boxShadow: "0 0 20px rgba(34,211,238,0.15)" },
          "50%":      { boxShadow: "0 0 32px rgba(34,211,238,0.30)" },
        },
        float: {
          "0%, 100%": { transform: "translateY(0)" },
          "50%":      { transform: "translateY(-6px)" },
        },
      },
      animation: {
        "in":         "slide-in-from-right-5 0.2s ease-out, fade-in 0.15s ease-out",
        "glow-pulse": "glow-pulse 2.5s ease-in-out infinite",
        "float":      "float 4s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;
