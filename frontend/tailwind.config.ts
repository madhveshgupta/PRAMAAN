import type { Config } from "tailwindcss";

/**
 * Restrained and government-appropriate. The palette is a deep institutional blue with a
 * near-neutral paper ground — legible on a ten-year-old monitor, at 125% zoom, and when
 * printed in greyscale. Severity colours are muted deliberately: this is an advisory tool,
 * and a wall of alarming red would misrepresent what a finding means.
 *
 * RADIUS — one vocabulary, resolved. The product used to speak five: `--radius` at 3px in
 * the app, and 12–16px on the landing page, which read as two products wearing the same
 * header. The app now adopts the soft language, because the working screens are built from
 * cards and rails rather than from spreadsheet rules, and a 3px card at 125% zoom reads as
 * an unfinished div rather than as a considered surface. Everything derives from the scale
 * below; nothing hardcodes a pixel radius.
 */
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink:   { DEFAULT: "#11181f", soft: "#44515c", faint: "#6f7d89", ghost: "#95a2ad" },
        paper: { DEFAULT: "#ffffff", soft: "#f7f5f1", edge: "#e4dfd8", deep: "#eee9e3" },
        brand: { DEFAULT: "#12507e", soft: "#e9f1f8", deep: "#0c3c60", ink: "#082a44" },
        accent:{ DEFAULT: "#0f6b52", soft: "#e6f3ef" },
        sev: {
          critical: "#9d1c28", "critical-soft": "#fbeced",
          high:     "#a75a0c", "high-soft":     "#fdf1e4",
          medium:   "#7d6212", "medium-soft":   "#fbf5e3",
          low:      "#465360", "low-soft":      "#eff2f5",
          info:     "#12507e", "info-soft":     "#e9f1f8",
        },
        ok: { DEFAULT: "#1d6b45", soft: "#e6f2ec" },
        // Decoration only — rules, the hero button, the stats band, the active-nav
        // underline. Never a status chip: `sev.medium` (#7d6212) is an olive that a reader
        // already knows means "look at this", and a gold chip beside it would be read as a
        // warning that nobody raised. Deliberately brighter and more saturated than either
        // severity tone so the two are not confusable at a glance.
        // `vivid` is the marketing gold — it only ever appears as a FILL (the Get started
        // button, a process node, the underline under a headline), never as text on paper,
        // where it measures 1.9:1 and is unreadable. `text` is the gold for words on white:
        // 3.65:1, which clears AA for the display sizes it is used at and nothing smaller.
        gold: { DEFAULT: "#c9a227", bright: "#d9b44a", deep: "#8a6d14", soft: "#faf3dc",
                vivid: "#f5b921", text: "#b8790a" },
      },
      fontFamily: {
        // Headings only. Data, tables and money stay sans — a serif numeral column would
        // undo the tabular alignment `tnum` exists to guarantee.
        serif: ["var(--font-serif)", "Georgia", "Cambria", "serif"],
        sans:  ["var(--font-sans)", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      fontSize: {
        "2xs": ["11px", "15px"],
      },
      // One radius system for the whole product. `DEFAULT` is what `rounded` and the legacy
      // `rounded-[--radius]` call sites resolve to, so softening the app was one edit rather
      // than two hundred.
      borderRadius: {
        DEFAULT: "var(--radius)",   // 10px — chips, fields, buttons, small surfaces
        card:    "var(--radius-card)",  // 14px — every card and panel
        rail:    "var(--radius-rail)",  // 18px — rails, dialogs, the sidebar's active pill
      },
      boxShadow: {
        // A four-step elevation, so "raised" is a decision rather than an accident.
        card:  "0 1px 2px rgb(17 24 31 / 0.04), 0 1px 1px rgb(17 24 31 / 0.03)",
        lift:  "0 2px 6px rgb(17 24 31 / 0.06), 0 8px 20px -8px rgb(17 24 31 / 0.10)",
        pop:   "0 4px 16px rgb(17 24 31 / 0.10)",
        rail:  "0 10px 40px -12px rgb(8 42 68 / 0.18)",
        inset: "inset 0 1px 0 rgb(255 255 255 / 0.6)",
      },
      maxWidth: { screen: "1680px" },
      spacing: {
        sidebar: "16.5rem",
        "sidebar-collapsed": "4.5rem",
        rail: "20rem",
      },
      // Short, and eased out rather than bouncing. A sign-in panel that springs is a sign-in
      // panel a tired officer waits for. globals.css disables all of it under
      // prefers-reduced-motion.
      keyframes: {
        "fade-in": { from: { opacity: "0" }, to: { opacity: "1" } },
        "rise-in": {
          from: { opacity: "0", transform: "translateY(12px) scale(.985)" },
          to:   { opacity: "1", transform: "translateY(0) scale(1)" },
        },
        "sweep-in": {
          from: { opacity: "0", transform: "translateY(6px)" },
          to:   { opacity: "1", transform: "translateY(0)" },
        },
        // The evidence panel arriving from the right edge, and the content column making
        // room for it. Both are also driven by GSAP where the two must stay in step; these
        // are the CSS fallbacks for the cases that need no coordination.
        "slide-in-right": {
          from: { opacity: "0", transform: "translateX(24px)" },
          to:   { opacity: "1", transform: "translateX(0)" },
        },
        // A one-shot ring that draws attention to where a claim landed, then stops. Loops
        // are for progress, not for emphasis.
        "ping-once": {
          "0%":   { transform: "scale(.9)", opacity: ".55" },
          "100%": { transform: "scale(1.5)", opacity: "0" },
        },
        "shimmer": {
          "100%": { transform: "translateX(100%)" },
        },
      },
      animation: {
        "fade-in":  "fade-in .22s ease-out both",
        "rise-in":  "rise-in .3s cubic-bezier(.16,.84,.44,1) both",
        "sweep-in": "sweep-in .35s cubic-bezier(.16,.84,.44,1) both",
        "slide-in-right": "slide-in-right .34s cubic-bezier(.16,.84,.44,1) both",
        "ping-once": "ping-once .9s cubic-bezier(.16,.84,.44,1) 1 both",
        "shimmer": "shimmer 1.6s infinite",
      },
    },
  },
  plugins: [],
};
export default config;
