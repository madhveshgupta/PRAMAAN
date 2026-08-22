"use client";
/** Count-up for the stats band.
 *
 *  The server renders the final figure, so the number is correct with JavaScript disabled
 *  and correct for a screen reader that reads the DOM before any effect runs. Only after
 *  mount, and only when the band is actually scrolled into view, does it wind back to zero
 *  and climb — a number that animated while off-screen has animated for nobody.
 *
 *  `prefers-reduced-motion` skips the whole thing rather than shortening it: a figure
 *  ticking upward is exactly the kind of movement that setting exists to stop.
 */
import { useEffect, useRef, useState } from "react";

const DURATION = 1100;

export function Counter({ to, decimals = 0, prefix = "", suffix = "" }: {
  to: number; decimals?: number; prefix?: string; suffix?: string;
}) {
  const el = useRef<HTMLSpanElement>(null);
  const [shown, setShown] = useState(to);

  useEffect(() => {
    const node = el.current;
    if (!node) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    if (typeof IntersectionObserver === "undefined") return;

    let frame = 0;
    const io = new IntersectionObserver(([entry]) => {
      if (!entry.isIntersecting) return;
      io.disconnect();
      const start = performance.now();
      const tick = (now: number) => {
        const t = Math.min(1, (now - start) / DURATION);
        // Ease-out cubic: fast enough to feel responsive, settling rather than stopping.
        setShown(to * (1 - Math.pow(1 - t, 3)));
        if (t < 1) frame = requestAnimationFrame(tick);
      };
      setShown(0);
      frame = requestAnimationFrame(tick);
    }, { threshold: 0.4 });

    io.observe(node);
    return () => { io.disconnect(); cancelAnimationFrame(frame); };
  }, [to]);

  return (
    <span ref={el} className="tabular-nums">
      {prefix}{shown.toLocaleString("en-IN", {
        minimumFractionDigits: decimals, maximumFractionDigits: decimals,
      })}{suffix}
    </span>
  );
}
