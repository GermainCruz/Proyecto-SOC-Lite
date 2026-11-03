/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bank: {
          blue: "#2D60FF",
          "blue-dark": "#1814F3",
          "blue-subtle": "#EDF2FF",
          navy: "#343C6A",
          muted: "#718EBF",
          "muted-light": "#8BA3CB",
          bg: "#F5F7FA",
          card: "#FFFFFF",
          border: "#E6EFF5",
          teal: "#16DBCC",
          coral: "#FE5C73",
          pink: "#FF82AC",
          amber: "#FFBB38",
          purple: "#7B61FF",
        },
        soc: {
          navy: "#343C6A",
          steel: "#2D60FF",
          mist: "#EDF2FF",
          ink: "#232323",
          critical: "#FE5C73",
          high: "#FEAA09",
          medium: "#FFBB38",
          low: "#16DBCC",
          info: "#718EBF",
        },
      },
      fontFamily: {
        sans: ["Inter", "Segoe UI", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "Consolas", "monospace"],
      },
      borderRadius: {
        "2xl": "16px",
        "3xl": "24px",
      },
      boxShadow: {
        card: "0 4px 20px rgba(223, 230, 242, 0.45)",
        "card-hover": "0 8px 30px rgba(223, 230, 242, 0.7)",
        primary: "0 4px 14px rgba(45, 96, 255, 0.35)",
      },
    },
  },
  plugins: [],
};
