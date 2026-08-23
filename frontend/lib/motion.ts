"use client";
/**
 * The motion vocabulary, in one file.
 *
 * Every animation in this product has to answer "what did that tell the user?", so the
 * helpers here are named for the message rather than for the effect: `useReveal` says
 * *this section has arrived*, `useCountUp` says *this figure was computed, not typed*,
 * `snapTo` says *the claim and its proof are two halves of one object*.
 *
 * Three rules hold across all of it and are enforced here rather than at each call site:
 *
 *   1. `prefers-reduced-motion: reduce` produces a CORRECT, COMPLETE, STATIC page — never a
 *      page with invisible content because a reveal never fired. Every helper therefore
 *      applies its END state immediately and returns, rather than shortening a duration.
 *   2. Nothing is hidden in CSS waiting for JavaScript. The hidden state is applied by GSAP
 *      in a layout effect, so with scripting off the markup is simply visible and readable.
 *   3. Opacity and transform only. No animation may move a layout-affecting property on a
 *      scroll path, and none may delay first meaningful paint.
 */
import { gsap } from "gsap";
import { useEffect, useLayoutEffect, useRef, useState } from "react";

/** The house easing. Eased out, never bouncy: a control that springs is a control a tired
 *  officer waits for. */
export const EASE = "power3.out";
export const EASE_SNAP = "power4.out";

/** SSR-safe layout effect — the reveal must set its hidden state before the browser paints,
 *  but `useLayoutEffect` warns during server rendering. */
const useIsomorphicLayoutEffect =
  typeof window !== "undefined" ? useLayoutEffect : useEffect;

export function prefersReduced(): boolean {
  if (typeof window === "undefined" || !window.matchMedia) return false;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/**
 * Entrance for a section: its direct children rise into place, staggered, once.
 *
 * Fires when the section is scrolled into view and then disconnects — a reveal that
 * re-fires on scroll-back is a section that keeps announcing itself, which is noise after
 * the first time.
 */
export function useReveal<T extends HTMLElement = HTMLDivElement>(options?: {
  /** Children to stagger. Defaults to `[data-reveal]` inside the container. */
  selector?: string;
  stagger?: number;
  y?: number;
  /** Skip the IntersectionObserver and play on mount — for content already above the fold. */
  immediate?: boolean;
  /** Re-run when this changes, so a list that loads after mount still animates in. */
  deps?: unknown[];
}) {
  const ref = useRef<T>(null);
  const { selector = "[data-reveal]", stagger = 0.055, y = 14,
          immediate = false, deps = [] } = options ?? {};

  useIsomorphicLayoutEffect(() => {
    const root = ref.current;
    if (!root) return;
    const targets = Array.from(root.querySelectorAll<HTMLElement>(selector));
    if (!targets.length) return;

    // Reduced motion: the page is already in its end state. Touch nothing.
    if (prefersReduced()) return;

    const ctx = gsap.context(() => {
      gsap.set(targets, { opacity: 0, y });
      const play = () =>
        gsap.to(targets, { opacity: 1, y: 0, duration: 0.42, ease: EASE, stagger });

      if (immediate || typeof IntersectionObserver === "undefined") { play(); return; }

      const io = new IntersectionObserver(([entry]) => {
        if (!entry.isIntersecting) return;
        io.disconnect();
        play();
      }, { threshold: 0.08, rootMargin: "0px 0px -40px 0px" });
      io.observe(root);
      return () => io.disconnect();
    }, root);

    return () => ctx.revert();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return ref;
}

/**
 * A figure that counts up to its value.
 *
 * The DOM already holds the final number — this only winds it back and climbs, and only
 * once the tile is on screen. A number that animated off-screen animated for nobody.
 */
export function useCountUp(to: number | null, opts?: { duration?: number; decimals?: number }) {
  const ref = useRef<HTMLSpanElement>(null);
  const [shown, setShown] = useState<number | null>(to);
  const { duration = 0.9, decimals = 0 } = opts ?? {};

  useEffect(() => {
    setShown(to);
    const node = ref.current;
    if (node == null || to == null) return;
    if (prefersReduced() || typeof IntersectionObserver === "undefined") return;

    const proxy = { v: 0 };
    let tween: gsap.core.Tween | null = null;
    const io = new IntersectionObserver(([entry]) => {
      if (!entry.isIntersecting) return;
      io.disconnect();
      tween = gsap.to(proxy, {
        v: to, duration, ease: EASE,
        onUpdate: () => setShown(+proxy.v.toFixed(decimals)),
        onComplete: () => setShown(to),
      });
    }, { threshold: 0.35 });
    io.observe(node);
    return () => { io.disconnect(); tween?.kill(); };
  }, [to, duration, decimals]);

  return { ref, shown };
}

/** An arc, bar or ring that draws itself to its value once, so the reader sees the figure
 *  being *measured* rather than asserted. Returns the animated 0→1 fraction. */
export function useDrawTo<T extends Element = HTMLElement>(
  value: number | null, duration = 0.85,
) {
  const ref = useRef<T>(null);
  const [t, setT] = useState(value == null ? 0 : 1);

  useEffect(() => {
    if (value == null) { setT(0); return; }
    const node = ref.current;
    if (!node) { setT(1); return; }
    if (prefersReduced() || typeof IntersectionObserver === "undefined") { setT(1); return; }

    const proxy = { v: 0 };
    let tween: gsap.core.Tween | null = null;
    const io = new IntersectionObserver(([e]) => {
      if (!e.isIntersecting) return;
      io.disconnect();
      tween = gsap.to(proxy, { v: 1, duration, ease: EASE, onUpdate: () => setT(proxy.v) });
    }, { threshold: 0.3 });
    io.observe(node);
    return () => { io.disconnect(); tween?.kill(); };
  }, [value, duration]);

  return { ref, t };
}

/* ------------------------------------------------------------------ the evidence snap -- */

/**
 * Drive the split's left-column width.
 *
 * One CSS variable carries the whole gesture — the open, the snap presets and the drag —
 * so the panes cannot disagree about where the seam is, and so the closed layout is
 * correct with no JavaScript at all (`--split-left: 100%`).
 */
export function snapTo(el: HTMLElement | null, pct: number, opts?: {
  instant?: boolean;
  onUpdate?: () => void;
  onComplete?: () => void;
}) {
  if (!el) return;
  const { instant = false, onUpdate, onComplete } = opts ?? {};
  const current = parseFloat(getComputedStyle(el).getPropertyValue("--split-left")) || 100;

  if (instant || prefersReduced()) {
    el.style.setProperty("--split-left", `${pct}%`);
    onUpdate?.();
    onComplete?.();
    return;
  }

  const proxy = { v: current };
  gsap.to(proxy, {
    v: pct,
    duration: 0.44,
    ease: EASE_SNAP,
    onUpdate: () => {
      el.style.setProperty("--split-left", `${proxy.v}%`);
      onUpdate?.();
    },
    onComplete,
  });
}

/** The evidence panel arriving: it comes in from the right edge as the column makes room,
 *  so the two read as one movement rather than as a panel appearing over a page that
 *  happened to shrink. */
export function enterFromRight(el: HTMLElement | null) {
  if (!el || prefersReduced()) return;
  gsap.fromTo(el,
    { opacity: 0, xPercent: 12 },
    { opacity: 1, xPercent: 0, duration: 0.44, ease: EASE_SNAP });
}

export function exitToRight(el: HTMLElement | null, done: () => void) {
  if (!el || prefersReduced()) { done(); return; }
  gsap.to(el, { opacity: 0, xPercent: 14, duration: 0.24, ease: "power2.in", onComplete: done });
}

/**
 * The Windows-snap preview: two translucent zones flash once where the panes are about to
 * land. It is the only decorative motion in the app, and it earns its place by naming the
 * gesture — people know this shape from their own desktop, so the split needs no label.
 */
export function flashSnapGhost(host: HTMLElement | null, leftPct: number) {
  if (!host || prefersReduced()) return;
  const make = (leftCss: string, widthCss: string) => {
    const g = document.createElement("div");
    g.className = "snap-ghost";
    Object.assign(g.style, {
      left: leftCss, width: widthCss, top: "8px", bottom: "8px", zIndex: "30",
    } as CSSStyleDeclaration);
    host.appendChild(g);
    window.setTimeout(() => g.remove(), 520);
  };
  make("8px", `calc(${leftPct}% - 14px)`);
  make(`calc(${leftPct}% + 6px)`, `calc(${100 - leftPct}% - 14px)`);
}

/** The chip that was clicked flicks toward the document, so the click has a direction and
 *  the reader's eye is handed across the seam rather than left behind. */
export function handOff(el: HTMLElement | null) {
  if (!el || prefersReduced()) return;
  gsap.fromTo(el, { x: 0 }, { x: 6, duration: 0.14, ease: "power2.out", yoyo: true, repeat: 1 });
}

export { gsap };
