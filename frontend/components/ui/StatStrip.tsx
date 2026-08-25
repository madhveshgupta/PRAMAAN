"use client";
/** The band of figures along the foot of a list screen.
 *
 *  Every tile here is computed from rows already on the page. There is deliberately no
 *  "vs last month" on any of them: the system holds no history of its own throughput, and a
 *  delta drawn from nothing is the one kind of number this product must never show
 *  (invariant 13 — never invent a statistical parameter). Where a comparison genuinely
 *  exists it is passed in as `against` and named.
 */
import { useCountUp } from "@/lib/motion";
import { Icon, type IconName } from "./Icon";

export interface Stat {
  key: string;
  label: string;
  value: number | null;
  suffix?: string;
  icon: IconName;
  tone?: "brand" | "ok" | "attention" | "gold";
  /** A stated basis, not a trend: "across 24 assessed reports". */
  basis?: string;
}

const TONE: Record<string, { chip: string; text: string }> = {
  brand:     { chip: "bg-brand-soft text-brand",           text: "text-ink" },
  ok:        { chip: "bg-ok-soft text-ok",                 text: "text-ok" },
  attention: { chip: "bg-sev-high-soft text-sev-high",     text: "text-sev-high" },
  gold:      { chip: "bg-gold-soft text-gold-deep",        text: "text-ink" },
};

function Tile({ stat }: { stat: Stat }) {
  const { ref, shown } = useCountUp(stat.value);
  const tone = TONE[stat.tone ?? "brand"];
  return (
    <div data-reveal className="flex items-start gap-3.5 px-4 py-3.5">
      <span aria-hidden className={`grid h-11 w-11 shrink-0 place-items-center rounded-card
                                    ${tone.chip}`}>
        <Icon name={stat.icon} className="w-5 h-5" />
      </span>
      <div className="min-w-0">
        {/* Wraps to a second line rather than truncating. A tile label is three or four
            words and it is the only thing that says what the number IS — "CHECKED, NOTHING
            CRI…" above a green 2 is a tile that has thrown away its own meaning to save
            18px. */}
        <p className="text-2xs uppercase leading-tight tracking-wide text-ink-faint">
          {stat.label}
        </p>
        <p className={`display text-2xl font-bold leading-tight tabular-nums ${tone.text}`}>
          <span ref={ref}>{stat.value == null ? "—" : Math.round(shown ?? 0)}</span>
          {stat.suffix && (
            <span className="ml-0.5 text-sm font-normal text-ink-faint">{stat.suffix}</span>
          )}
        </p>
        {stat.basis && (
          <p className="mt-0.5 text-2xs leading-tight text-ink-faint">{stat.basis}</p>
        )}
      </div>
    </div>
  );
}

export function StatStrip({ stats }: { stats: Stat[] }) {
  return (
    <div className="grid divide-y divide-paper-edge overflow-hidden rounded-card border
                    border-paper-edge bg-paper shadow-card
                    sm:grid-cols-2 sm:divide-y-0 lg:grid-cols-4
                    sm:[&>*:not(:first-child)]:border-l sm:[&>*]:border-paper-edge">
      {stats.map((s) => <Tile key={s.key} stat={s} />)}
    </div>
  );
}
