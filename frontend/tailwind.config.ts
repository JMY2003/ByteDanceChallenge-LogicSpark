import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}"
  ],
  theme: {
    extend: {
      colors: {
        ink: "#1d1d1f",
        steel: "#6e6e73",
        panel: "#f5f5f7",
        line: "#d2d2d7",
        signal: "#0071e3",
        warn: "#bf5b00",
        danger: "#d70015"
      },
      boxShadow: {
        soft: "0 18px 44px rgba(0, 0, 0, 0.07)",
        hairline: "0 1px 2px rgba(0, 0, 0, 0.04)"
      }
    }
  },
  plugins: []
};

export default config;
