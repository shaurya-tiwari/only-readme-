/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        surface: "#f9f9f6",
        "surface-container-low": "#f4f4f1",
        "surface-container": "#eeeeeb",
        "surface-container-high": "#e8e8e5",
        "surface-container-highest": "#e2e3e0",
        "surface-container-lowest": "#ffffff",
        primary: "#003535",
        "primary-container": "#0d4d4d",
        "on-primary": "#ffffff",
        "on-primary-container": "#85bdbc",
        secondary: "#48626e",
        "secondary-container": "#cbe7f5",
        tertiary: "#462800",
        "tertiary-container": "#643c00",
        "on-tertiary-container": "#f4a135",
        "on-surface": "#1a1c1b",
        "on-surface-variant": "#404848",
        error: "#ba1a1a",
        "error-container": "#ffdad6",
        "outline-variant": "#bfc8c8",
        ink: "#1a1c1b",
        mist: "#f9f9f6",
        forest: "#003535",
        storm: "#48626e",
        gold: "#f4a135",
      },
      boxShadow: {
        panel: "0 18px 50px rgba(26, 28, 27, 0.08)",
      },
      backgroundImage: {
        "mesh-paper":
          "radial-gradient(circle at top left, rgba(244,161,53,0.14), transparent 30%), radial-gradient(circle at top right, rgba(13,77,77,0.14), transparent 35%), linear-gradient(180deg, #f9f9f6 0%, #f4f4f1 100%)",
      },
      fontFamily: {
        headline: ["Plus Jakarta Sans", "sans-serif"],
        body: ["Inter", "sans-serif"],
        label: ["Inter", "sans-serif"],
      },
    },
  },
  plugins: [],
};
