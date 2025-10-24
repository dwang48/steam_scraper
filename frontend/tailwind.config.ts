import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          DEFAULT: "#0B0B0C",
          subtle: "#1F1F24",
          softer: "#2A2A32"
        },
        mist: {
          DEFAULT: "#F5F5F7",
          subtle: "#E5E5EA"
        },
        accent: {
          DEFAULT: "#0A84FF",
          soft: "rgba(10,132,255,0.12)"
        }
      },
      fontFamily: {
        sans: [
          "-apple-system",
          "BlinkMacSystemFont",
          "\"SF Pro Display\"",
          "\"Segoe UI\"",
          "Roboto",
          "Helvetica",
          "Arial",
          "sans-serif"
        ]
      },
      boxShadow: {
        "glass": "0 30px 60px -30px rgba(15, 23, 42, 0.45)"
      }
    }
  },
  plugins: []
} satisfies Config;
