"use client";
/** Page control. Present only when there is more than one page — a lone "1" in a box is a
 *  control that can never do anything, and every one of those an officer learns to ignore
 *  costs a little of the attention the real controls need. */
import { Icon } from "./Icon";

export function Pagination({ page, pages, onChange, total, unit = "reports" }: {
  page: number; pages: number; onChange: (p: number) => void;
  total?: number; unit?: string;
}) {
  if (pages <= 1) return null;

  // A window around the current page, with the ends always reachable. Ten pages of numbers
  // is not navigation, it is a wall.
  const nums: (number | "gap")[] = [];
  for (let i = 1; i <= pages; i++) {
    if (i === 1 || i === pages || Math.abs(i - page) <= 1) nums.push(i);
    else if (nums[nums.length - 1] !== "gap") nums.push("gap");
  }

  const Btn = ({ to, disabled, children, label }: {
    to: number; disabled: boolean; children: React.ReactNode; label: string;
  }) => (
    <button type="button" onClick={() => onChange(to)} disabled={disabled} aria-label={label}
            className="grid h-9 w-9 place-items-center rounded-full border border-paper-edge
                       bg-paper text-ink-soft transition-colors hover:border-brand/30
                       hover:bg-brand-soft hover:text-brand disabled:opacity-40
                       disabled:hover:border-paper-edge disabled:hover:bg-paper
                       disabled:hover:text-ink-soft">
      {children}
    </button>
  );

  return (
    <nav aria-label="Pagination" className="no-print flex flex-wrap items-center gap-2">
      <Btn to={page - 1} disabled={page <= 1} label="Previous page">
        <Icon name="chevronRight" className="w-4 h-4 rotate-180" />
      </Btn>
      {nums.map((n, i) =>
        n === "gap" ? (
          <span key={`g${i}`} aria-hidden className="px-1 text-ink-ghost">…</span>
        ) : (
          <button key={n} type="button" onClick={() => onChange(n)}
                  aria-current={n === page ? "page" : undefined}
                  className={`h-9 min-w-9 rounded-full px-3 text-sm tabular-nums transition-colors
                    ${n === page
                      ? "bg-brand-deep font-semibold text-white shadow-card"
                      : "border border-paper-edge bg-paper text-ink-soft hover:bg-brand-soft hover:text-brand"}`}>
            {n}
          </button>
        ))}
      <Btn to={page + 1} disabled={page >= pages} label="Next page">
        <Icon name="chevronRight" className="w-4 h-4" />
      </Btn>
      {total != null && (
        <span className="ml-2 text-2xs text-ink-faint tabular-nums">
          {total} {unit}
        </span>
      )}
    </nav>
  );
}
