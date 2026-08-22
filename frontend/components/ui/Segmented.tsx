"use client";
/** The pill tab group.
 *
 *  The active state is a filled capsule that SLIDES between positions rather than
 *  appearing at the new one. That is the whole reason this is a component and not three
 *  buttons: a thumb that travels tells the reader the two states are one control with one
 *  value, where two independently-filling buttons read as two switches that happen to be
 *  adjacent.
 */
import { useEffect, useRef, useState } from "react";

export interface Segment<T extends string> { value: T; label: string; count?: number | null }

export function Segmented<T extends string>({ segments, value, onChange, label }: {
  segments: Segment<T>[];
  value: T;
  onChange: (v: T) => void;
  label: string;
}) {
  const wrap = useRef<HTMLDivElement>(null);
  const [thumb, setThumb] = useState<{ x: number; w: number } | null>(null);

  // Measured rather than computed from index: the segments have different label lengths, so
  // an equal-width assumption would put the capsule beside the word instead of under it.
  useEffect(() => {
    const root = wrap.current;
    if (!root) return;
    const move = () => {
      const active = root.querySelector<HTMLElement>('[aria-selected="true"]');
      if (!active) return;
      setThumb({ x: active.offsetLeft, w: active.offsetWidth });
    };
    move();
    const ro = new ResizeObserver(move);
    ro.observe(root);
    return () => ro.disconnect();
  }, [value, segments]);

  return (
    <div ref={wrap} role="tablist" aria-label={label} className="segmented">
      {thumb && (
        <span aria-hidden className="segmented-thumb"
              style={{ transform: `translateX(${thumb.x}px)`, width: thumb.w,
                       top: 4, bottom: 4 }} />
      )}
      {segments.map((s) => (
        <button key={s.value} role="tab" type="button"
                aria-selected={value === s.value}
                onClick={() => onChange(s.value)}>
          {s.label}
          {s.count != null && (
            <span className={`ml-2 rounded-full px-1.5 py-0.5 text-2xs font-semibold
                              tabular-nums transition-colors ${
              value === s.value ? "bg-white/20 text-white" : "bg-paper-deep text-ink-soft"}`}>
              {s.count}
            </span>
          )}
        </button>
      ))}
    </div>
  );
}
