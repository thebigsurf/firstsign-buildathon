import type { Config } from "tailwindcss";

const v = (name: string): string => `var(--${name})`;

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: v("bg"),
        surface: v("surface"),
        sunken: v("sunken"),
        text: v("text"),
        muted: v("muted"),
        border: v("border"),
        borderStrong: v("border-strong"),
        accent: v("accent"),
        accentFg: v("accent-fg"),
        accentSoft: v("accent-soft"),
        accentText: v("accent-text"),
        normal: v("normal"),
        normalBg: v("normal-bg"),
        watch: v("watch"),
        watchBg: v("watch-bg"),
        alert: v("alert"),
        alertBg: v("alert-bg"),
        onAlert: v("on-alert"),
        confHigh: v("conf-high"),
        confHighBg: v("conf-high-bg"),
        confUnc: v("conf-unc"),
        confUncBg: v("conf-unc-bg"),
        confUnk: v("conf-unk"),
        confUnkBg: v("conf-unk-bg"),
      },
      fontFamily: {
        display: v("font-display"),
        sans: v("font-body"),
        mono: v("font-mono"),
      },
      borderRadius: { md: "6px", lg: "10px", xl: "16px" },
      boxShadow: { 1: v("shadow-1"), 2: v("shadow-2"), 3: v("shadow-3") },
      fontSize: {
        display: ["3rem", { lineHeight: "1.1", fontWeight: "700" }],
        h1: ["2rem", { lineHeight: "1.2", fontWeight: "700" }],
        h2: ["1.5rem", { lineHeight: "1.25", fontWeight: "600" }],
        h3: ["1.125rem", { lineHeight: "1.35", fontWeight: "600" }],
        "num-lg": ["2.25rem", { lineHeight: "1", fontWeight: "600" }],
        asha: ["1.25rem", { lineHeight: "1.5", fontWeight: "500" }],
        "asha-h": ["1.75rem", { lineHeight: "1.3", fontWeight: "700" }],
      },
      keyframes: {
        pulseSoft: { "0%,100%": { opacity: "1" }, "50%": { opacity: "0.6" } },
        slideIn: { from: { opacity: "0", transform: "translateY(-8px)" }, to: { opacity: "1", transform: "none" } },
        ring: {
          "0%,100%": { boxShadow: "0 0 0 0 rgb(179 38 30 / 0.4)" },
          "50%": { boxShadow: "0 0 0 14px rgb(179 38 30 / 0)" },
        },
        draw: { to: { strokeDashoffset: "0" } },
      },
      animation: {
        skeleton: "pulseSoft 1.2s ease-in-out infinite",
        slideIn: "slideIn 200ms ease-out",
        ring: "ring 1.4s ease-in-out infinite",
        draw: "draw 300ms ease-out forwards",
      },
    },
  },
  plugins: [],
} satisfies Config;
