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
        ink: "#17202a",
        steel: "#667085",
        panel: "#f7f9fc",
        line: "#d7dde5",
        signal: "#0f766e",
        warn: "#b45309",
        danger: "#b42318"
      },
      boxShadow: {
        soft: "0 18px 45px rgba(16, 24, 40, 0.08)"
      }
    }
  },
  plugins: []
};

export default config;

