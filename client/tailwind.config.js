/** @type {import("tailwindcss").Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        surface: "#080a0f",
        panel:   "#0e1117",
        border:  "#1a1f2e",
        muted:   "#2a3045",
        text:    "#c8d0e0",
        dim:     "#5a6480",
        green:   { DEFAULT: "#00e5a0", dim: "#00b37e", glow: "#00e5a033" },
        red:     { DEFAULT: "#ff4545", dim: "#cc3636", glow: "#ff454533" },
        purple:  { DEFAULT: "#7b61ff", dim: "#5a44d4", glow: "#7b61ff33" },
        amber:   { DEFAULT: "#ffb020", dim: "#cc8c1a", glow: "#ffb02033" },
        blue:    { DEFAULT: "#00b4ff", dim: "#0090cc", glow: "#00b4ff33" },
      },
      fontFamily: {
        mono:    ["\"JetBrains Mono\"", "monospace"],
        display: ["\"Syne\"", "sans-serif"],
        body:    ["\"DM Sans\"", "sans-serif"],
      },
      animation: {
        "fade-up":   "fadeUp 0.4s ease forwards",
        "pulse-slow":"pulse 3s ease-in-out infinite",
      },
      keyframes: {
        fadeUp: {
          from: { opacity: "0", transform: "translateY(12px)" },
          to:   { opacity: "1", transform: "translateY(0)"    },
        },
      },
      boxShadow: {
        "glow-green" : "0 0 16px 2px #00e5a033",
        "glow-red"   : "0 0 16px 2px #ff454533",
        "glow-purple": "0 0 16px 2px #7b61ff33",
        "glow-amber" : "0 0 16px 2px #ffb02033",
      },
    },
  },
  plugins: [],
};
