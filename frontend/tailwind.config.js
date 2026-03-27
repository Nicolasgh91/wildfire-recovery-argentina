import { fontFamily } from "tailwindcss/defaultTheme"
import tailwindcssAnimate from "tailwindcss-animate"

/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        nav: {
          DEFAULT: "hsl(var(--nav) / <alpha-value>)",
          foreground: "hsl(var(--nav-foreground) / <alpha-value>)",
          hover: "hsl(var(--nav-hover) / <alpha-value>)",
        },
        footer: {
          DEFAULT: "hsl(var(--footer) / <alpha-value>)",
          foreground: "hsl(var(--footer-foreground) / <alpha-value>)",
          muted: "hsl(var(--footer-muted) / <alpha-value>)",
        },
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        "auth-page": "hsl(var(--auth-page-background))",
        "auth-form-container": "hsl(var(--auth-form-container-bg))",
        "history-page-bg": "hsl(var(--history-page-bg))",
        "table-border": "hsl(var(--table-border))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        chart: {
          1: "hsl(var(--chart-1))",
          2: "hsl(var(--chart-2))",
          3: "hsl(var(--chart-3))",
          4: "hsl(var(--chart-4))",
          5: "hsl(var(--chart-5))",
        },
        sidebar: {
          DEFAULT: "hsl(var(--sidebar))",
          foreground: "hsl(var(--sidebar-foreground))",
          primary: "hsl(var(--sidebar-primary))",
          "primary-foreground": "hsl(var(--sidebar-primary-foreground))",
          accent: "hsl(var(--sidebar-accent))",
          "accent-foreground": "hsl(var(--sidebar-accent-foreground))",
          border: "hsl(var(--sidebar-border))",
          ring: "hsl(var(--sidebar-ring))",
        },
        "mobile-nav": {
          DEFAULT: "hsl(var(--mobile-nav-bg) / <alpha-value>)",
          foreground: "hsl(var(--mobile-nav-foreground) / <alpha-value>)",
          muted: "hsl(var(--mobile-nav-muted) / <alpha-value>)",
          "muted-foreground": "hsl(var(--mobile-nav-muted-foreground) / <alpha-value>)",
          primary: "hsl(var(--mobile-nav-primary) / <alpha-value>)",
          "primary-foreground": "hsl(var(--mobile-nav-primary-foreground) / <alpha-value>)",
          border: "hsl(var(--mobile-nav-border))",
          "section-heading": "hsl(var(--mobile-nav-section-heading))",
        },
        "critical-dialog": {
          DEFAULT: "hsl(var(--critical-dialog-bg) / <alpha-value>)",
          foreground: "hsl(var(--critical-dialog-foreground) / <alpha-value>)",
          muted: "hsl(var(--critical-dialog-muted))",
        },
      },
      borderRadius: {
        xl: "calc(var(--radius) + 4px)",
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      fontFamily: {
        sans: ["Inter Variable", "Inter", "system-ui", "-apple-system", "BlinkMacSystemFont", "Segoe UI", ...fontFamily.sans],
        mono: ["var(--font-mono)", ...fontFamily.mono],
      },
      keyframes: {
        "accordion-down": {
          from: { height: "0" },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: "0" },
        },
        "collapsible-down": {
          from: { height: "0" },
          to: { height: "var(--radix-collapsible-content-height)" },
        },
        "collapsible-up": {
          from: { height: "var(--radix-collapsible-content-height)" },
          to: { height: "0" },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
        "collapsible-down": "collapsible-down 0.2s ease-out",
        "collapsible-up": "collapsible-up 0.2s ease-out",
      },
    },
  },
  plugins: [tailwindcssAnimate],
}
