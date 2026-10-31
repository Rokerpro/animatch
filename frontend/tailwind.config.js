/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        surface: {
          base: "#0b0b0f",
          raised: "#121216",
          overlay: "#1a1a22",
          border: "#292832",
          backdrop: "rgba(0, 0, 0, 0.67)",
        },
        accent: {
          DEFAULT: "#7c65c1",
          ui: "#7c65c1",
          hover: "#6a56aa",
          text: "#9d8bdc",
          gradientStart: "#9d8bdc",
          gradientEnd: "#7c65c1",
          subtle: "rgba(124, 101, 193, 0.14)",
          glow: "rgba(124, 101, 193, 0.17)",
        },
        content: {
          primary: "#eeeeee",
          secondary: "#9494a0",
          muted: "#9494a0",
        },
        score: { high: "#4ade80", mid: "#facc15", low: "#f87171" },
        status: {
          error: "#f87171",
          errorSurface: "rgba(248, 113, 113, 0.10)",
          success: "#4ade80",
          successSurface: "rgba(74, 222, 128, 0.10)",
        },
      },
      borderRadius: { xl: "12px", "2xl": "16px" },
      boxShadow: {
        focus: "0 0 0 3px rgba(124, 101, 193, 0.22)",
        panel: "0 8px 24px rgba(0, 0, 0, 0.16)",
        toast: "0 10px 24px rgba(0, 0, 0, 0.24)",
        menu: "0 14px 32px rgba(0, 0, 0, 0.28)",
        drawer: "0 -18px 48px rgba(0, 0, 0, 0.34)",
      },
      fontFamily: { sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"] },
      transitionDuration: { DEFAULT: "180ms" },
    },
  },
  plugins: [],
};
