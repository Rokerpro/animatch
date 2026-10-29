/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        surface: {
          base: "#0d0d11",
          raised: "#141419",
          overlay: "#1a1a22",
          border: "#202028",
        },
        accent: {
          ui: "#7c65c1",
          hover: "#6a56aa",
          text: "#9d8bdc",
          subtle: "rgba(124, 101, 193, 0.12)",
        },
        content: {
          primary: "#eeeeee",
          secondary: "#9494a0",
          muted: "#5e5e6e",
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
      transitionDuration: { DEFAULT: "200ms" },
    },
  },
  plugins: [],
};
