/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        // Design token: base backgrounds (dark, sleek, minimal)
        surface: {
          base: "#09090b", // Deep near-black background
          raised: "#121217", // Elevated cards and search panels
          overlay: "#181820", // Modals and dropdown menus
          border: "#272732", // Subtle boundaries
        },
        // Design token: single restrained violet/indigo accent
        // WCAG AA compliant: contrast ratio > 6:1 against #09090b
        accent: {
          DEFAULT: "#8B7CF6",
          hover: "#7C3AED",
          light: "#A78BFA",
          muted: "rgba(139, 124, 246, 0.15)",
        },
        // Typography tokens
        content: {
          primary: "#F4F4F5", // High contrast crisp reading text
          secondary: "#A1A1AA", // Muted metadata, subtext
          muted: "#71717A", // Subtle labels
        },
      },
      fontFamily: {
        sans: [
          "Inter",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "Roboto",
          "sans-serif",
        ],
      },
      transitionDuration: {
        DEFAULT: "200ms", // 150-250ms subtle transitions as specified
      },
    },
  },
  plugins: [],
};
