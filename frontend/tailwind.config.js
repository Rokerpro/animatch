/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        surface: {
          base: "#101014",
          raised: "#17171d",
          overlay: "#1b1a22",
          border: "#302e38",
        },
        accent: {
          DEFAULT: "#9682df",
          soft: "#b2a3ef",
          subtle: "rgba(150, 130, 223, 0.14)",
        },
        content: {
          primary: "#eeedf3",
          secondary: "#aaa7b3",
          muted: "#777482",
        },
      },
      fontFamily: { sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"] },
      transitionDuration: { DEFAULT: "200ms" },
    },
  },
  plugins: [],
};
