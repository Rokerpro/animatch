/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        graphite: "#101114",
        surface: "#191B21",
        line: "#2B2E37",
        paper: "#F2F1F6",
        muted: "#A3A4B0",
        lavender: "#A99BFF",
        danger: "#F07178",
      },
      fontFamily: {
        display: ['"Dela Gothic One"', "ui-sans-serif", "system-ui"],
        sans: ['"Zen Kaku Gothic New"', "ui-sans-serif", "system-ui"],
      },
    },
  },
  plugins: [],
};
