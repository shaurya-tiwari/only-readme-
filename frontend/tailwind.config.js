/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#121621",
        mist: "#f4efe7",
        sand: "#e6d7c8",
        ember: "#c55432",
        forest: "#2a5d4d",
        storm: "#274d75",
        gold: "#e0a931",
      },
      boxShadow: {
        panel: "0 18px 50px rgba(18, 22, 33, 0.08)",
      },
      backgroundImage: {
        "mesh-paper":
          "radial-gradient(circle at top left, rgba(224,169,49,0.18), transparent 30%), radial-gradient(circle at top right, rgba(39,77,117,0.18), transparent 35%), linear-gradient(180deg, #f9f5ef 0%, #f2ebe1 100%)",
      },
    },
  },
  plugins: [],
};
