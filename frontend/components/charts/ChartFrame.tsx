"use client";
/** The container every chart in the product sits in.
 *
 *  It exists because the charts were previously bare SVGs dropped into cards: no consistent
 *  title, no legend rule, and — the accessibility gap that mattered — no way to read the
 *  numbers if you could not read the picture. Every chart here ships a table of its own
 *  data behind a toggle, which is also what an officer copies into an appraisal note.
 */
import { useId, useState } from "react";

export interface Datum { key: string; label: string; value: number | null; color?: string;
                         note?: string }

export function ChartFrame({
  title, hint, footnote, legend, data, unit, children, dense = false, action,
}: {
  title?: string;
  hint?: string;
  footnote?: string;
  /** Legend entries. Present whenever the chart carries two or more series — identity is
   *  never colour alone. Omitted for a single series, where the title names it. */
  legend?: Datum[];
  /** Powers the table view. Supply it and the toggle appears; omit it and it does not. */
  data?: Datum[];
  unit?: string;
  children: React.ReactNode;
  dense?: boolean;
  action?: React.ReactNode;
}) {
  const [asTable, setAsTable] = useState(false);
  const id = useId();

  return (
    <figure className="m-0">
      {(title || action) && (
        <div className="flex items-start gap-3">
          {title && (
            <div className="min-w-0">
              <h3 className="display text-sm font-bold text-ink">{title}</h3>
              {hint && (
                <p className="mt-0.5 text-2xs text-ink-faint leading-relaxed max-w-prose">
                  {hint}
                </p>
              )}
            </div>
          )}
          <div className="ml-auto flex items-center gap-1 shrink-0 no-print">
            {action}
            {data && data.length > 0 && (
              <button type="button" onClick={() => setAsTable((v) => !v)}
                      aria-pressed={asTable} aria-controls={id}
                      className="btn btn-sm btn-quiet text-2xs">
                {asTable ? "Chart" : "Table"}
              </button>
            )}
          </div>
        </div>
      )}

      <div id={id} className={dense ? "mt-2" : "mt-3"}>
        {asTable && data ? (
          <table className="w-full text-xs">
            <thead>
              <tr className="text-left text-2xs uppercase tracking-wide text-ink-faint
                             border-b border-paper-edge">
                <th className="py-1.5 pr-3 font-semibold">Item</th>
                <th className="py-1.5 font-semibold text-right">
                  {unit ?? "Value"}
                </th>
              </tr>
            </thead>
            <tbody>
              {data.map((d) => (
                <tr key={d.key} className="border-b border-paper-edge/60 last:border-0">
                  <td className="py-1.5 pr-3 text-ink-soft">
                    <span className="inline-flex items-center gap-2">
                      {d.color && (
                        <span aria-hidden className="w-2.5 h-2.5 rounded-[2px] shrink-0"
                              style={{ background: d.color }} />
                      )}
                      {d.label}
                    </span>
                  </td>
                  <td className="py-1.5 text-right tabular-nums font-medium text-ink">
                    {d.value == null ? "not measured" : d.value.toLocaleString("en-IN")}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          children
        )}
      </div>

      {legend && legend.length > 1 && !asTable && (
        <ul className="mt-3 flex flex-wrap gap-x-4 gap-y-1.5">
          {legend.map((d) => (
            <li key={d.key} className="flex items-center gap-1.5 text-2xs text-ink-soft">
              <span aria-hidden className="w-2.5 h-2.5 rounded-[2px] shrink-0"
                    style={{ background: d.color }} />
              {d.value != null && (
                <span className="tabular-nums font-semibold text-ink">{d.value}</span>
              )}
              {d.label}
            </li>
          ))}
        </ul>
      )}

      {footnote && (
        <figcaption className="mt-2.5 text-2xs text-ink-faint leading-relaxed max-w-prose">
          {footnote}
        </figcaption>
      )}
    </figure>
  );
}

/** A hover readout that follows the cursor inside a chart. Positioned against the chart's
 *  own box rather than the viewport, so it cannot be clipped by a scrolling rail. */
export function useHoverReadout<T>() {
  const [hover, setHover] = useState<{ x: number; y: number; datum: T } | null>(null);
  const show = (e: React.MouseEvent, datum: T) => {
    const box = (e.currentTarget as HTMLElement).closest("[data-chart]") as HTMLElement | null;
    if (!box) return;
    const r = box.getBoundingClientRect();
    setHover({ x: e.clientX - r.left, y: e.clientY - r.top, datum });
  };
  const hide = () => setHover(null);
  return { hover, show, hide };
}

export function Readout({ x, y, children }: {
  x: number; y: number; children: React.ReactNode;
}) {
  return (
    <div role="status"
         className="pointer-events-none absolute z-20 -translate-x-1/2 -translate-y-[calc(100%+10px)]
                    rounded bg-brand-ink px-2.5 py-1.5 text-2xs leading-snug text-white
                    shadow-pop whitespace-nowrap animate-fade-in"
         style={{ left: x, top: y }}>
      {children}
    </div>
  );
}
