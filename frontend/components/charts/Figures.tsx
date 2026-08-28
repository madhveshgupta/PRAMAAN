"use client";
/** The chart forms this product needs, hand-built.
 *
 *  Hand-built rather than Recharts for one reason that is not taste: every chart here has
 *  to carry a glyph, a word and a number beside its colour, and has to survive a greyscale
 *  print. Reaching that through a chart library's render props costs more code than the
 *  SVG does, and the SVG is the thing an auditor eventually looks at.
 *
 *  Rules held throughout, from the project's own colour work:
 *    · severity is ORDINAL and gets a sequential ramp, never five categorical hues;
 *    · signed values diverge on blue↔orange, never red↔green;
 *    · a value we did not measure is HATCHED, never drawn as zero;
 *    · every fill is direct-laballed or legended — colour is the third cue, never the only.
 */
import { useDrawTo } from "@/lib/motion";
import { ChartFrame, Readout, useHoverReadout, type Datum } from "./ChartFrame";
import { AXIS, CONFIDENCE_RAMP, DIVERGING, GRID, HATCH_ID, INK_MUTED, SEVERITY_RAMP,
         STATUS_FILL, hatchDefs } from "./palette";

const STATUS_LABEL: Record<string, string> = {
  pass: "confirmed", partial: "weak", insufficient_evidence: "no evidence",
  flagged: "flagged", not_run: "not checked",
};
const STATUS_GLYPH: Record<string, string> = {
  pass: "✓", partial: "–", insufficient_evidence: "✗", flagged: "⚑", not_run: "⊘",
};
const STATUS_ORDER = ["pass", "partial", "insufficient_evidence", "flagged", "not_run"];

/* ------------------------------------------------------------------ checklist tally -- */

/**
 * What was examined, as one bar.
 *
 * A 2px paper gap sits between segments so two adjacent fills never touch — that gap is
 * what stops "confirmed" and "weak" reading as one block at a glance, and it does the job
 * in greyscale too.
 */
export function StatusStack({ tally, title, hint, footnote }: {
  tally: Record<string, number>;
  title?: string; hint?: string; footnote?: string;
}) {
  const parts = STATUS_ORDER.filter((k) => (tally[k] ?? 0) > 0);
  const total = parts.reduce((s, k) => s + (tally[k] ?? 0), 0);
  const { hover, show, hide } = useHoverReadout<{ k: string; n: number }>();

  if (!total) {
    return <p className="text-2xs text-ink-faint">No checks have been recorded yet.</p>;
  }

  const legend: Datum[] = parts.map((k) => ({
    key: k, label: STATUS_LABEL[k], value: tally[k], color: STATUS_FILL[k],
  }));

  return (
    <ChartFrame title={title} hint={hint} footnote={footnote} legend={legend} data={legend}
                unit="Checks">
      <div data-chart className="relative">
        <div className="flex h-7 gap-[2px] rounded overflow-hidden bg-paper" role="img"
             aria-label={parts.map((k) => `${tally[k]} ${STATUS_LABEL[k]}`).join(", ")}>
          {parts.map((k) => {
            const w = ((tally[k] ?? 0) / total) * 100;
            return (
              <div key={k}
                   onMouseMove={(e) => show(e, { k, n: tally[k] ?? 0 })}
                   onMouseLeave={hide}
                   className="relative grid place-items-center transition-[filter] hover:brightness-110"
                   style={{ width: `${w}%`, background: STATUS_FILL[k] }}>
                {/* Direct label inside the segment when it is wide enough to hold one —
                    the contrast warning on the grey and the amber is relieved by this, and
                    by the legend below, not waived. */}
                {w > 9 && (
                  <span className="text-2xs font-semibold tabular-nums text-white/95">
                    {tally[k]}
                  </span>
                )}
              </div>
            );
          })}
        </div>
        {hover && (
          <Readout x={hover.x} y={hover.y}>
            <span aria-hidden className="mr-1">{STATUS_GLYPH[hover.datum.k]}</span>
            {hover.datum.n} {STATUS_LABEL[hover.datum.k]}
            <span className="text-white/60"> · {Math.round((hover.datum.n / total) * 100)}%</span>
          </Readout>
        )}
      </div>
    </ChartFrame>
  );
}

/* --------------------------------------------------------------------- severity bars -- */

/** Ordered magnitude — a sequential ramp, one hue, dark = most severe. */
export function SeverityBars({ counts, title, hint, onPick, active }: {
  counts: Record<string, number>;
  title?: string; hint?: string;
  onPick?: (severity: string) => void;
  active?: string | null;
}) {
  const order = ["critical", "high", "medium", "low", "info"];
  const label: Record<string, string> = {
    critical: "Critical", high: "High", medium: "Medium", low: "Low", info: "Note",
  };
  const rows = order.map((k) => [k, counts[k] ?? 0] as const).filter(([, n]) => n > 0);
  const max = Math.max(1, ...rows.map(([, n]) => n));

  if (!rows.length) {
    return (
      <p className="text-2xs text-ink-faint">
        No findings were raised — which is a statement about this document, not about how
        much was checked. The checklist shows the rest.
      </p>
    );
  }

  const data: Datum[] = rows.map(([k, n]) => ({
    key: k, label: label[k], value: n, color: SEVERITY_RAMP[k],
  }));

  return (
    <ChartFrame title={title} hint={hint} data={data} unit="Findings">
      <ul className="space-y-1.5">
        {rows.map(([k, n]) => {
          const Row = onPick ? "button" : "div";
          return (
            <li key={k}>
              <Row
                {...(onPick ? { onClick: () => onPick(k), "aria-pressed": active === k } : {})}
                className={`group flex w-full items-center gap-3 rounded px-1.5 py-1
                            text-left transition-colors
                            ${onPick ? "hover:bg-brand-soft/60 cursor-pointer" : ""}
                            ${active === k ? "bg-brand-soft" : ""}`}>
                <span className="w-16 shrink-0 text-2xs font-medium text-ink-soft">
                  {label[k]}
                </span>
                <span className="flex-1 h-3.5 rounded-[3px]" style={{ background: GRID }}>
                  <span className="block h-full rounded-[3px] transition-[width] duration-500"
                        style={{ width: `${(n / max) * 100}%`, background: SEVERITY_RAMP[k] }} />
                </span>
                <span className="w-7 text-right text-2xs tabular-nums font-semibold text-ink">
                  {n}
                </span>
              </Row>
            </li>
          );
        })}
      </ul>
    </ChartFrame>
  );
}

/* ---------------------------------------------------------------- risk probability --- */

/**
 * A probability, placed on a scale rather than pointed at by a needle.
 *
 * A gauge with a needle in a red zone is a verdict, and this system does not return
 * verdicts (§ the tone is advisory). A marker on a labelled 0–100% track says the same
 * number without the theatre, and leaves room to draw the comparison that actually helps:
 * where comparable projects landed.
 */
export function ProbabilityScale({ value, label, peerValue, peerLabel, caveat }: {
  value: number | null;
  label: string;
  /** The base rate among comparable projects, if we have one. A 42% that sits below a 61%
   *  cohort rate means something quite different from a 42% that sits above a 12% one. */
  peerValue?: number | null;
  peerLabel?: string;
  caveat?: string | null;
}) {
  const { ref, t } = useDrawTo<HTMLDivElement>(value);
  if (value == null) {
    return <p className="text-2xs text-ink-faint">Not predicted for this report.</p>;
  }
  const x = value * 100 * t;

  // Drawn in HTML rather than SVG, and that is a correctness decision rather than a taste
  // one. A full-width SVG needs `preserveAspectRatio="none"` to stretch its viewBox, and
  // that scales x and y by different factors — which turns every circle into an ellipse,
  // every stroke width into a different number horizontally and vertically, and every dash
  // pattern into something that depends on the container's width. The marker on this scale
  // was rendering as a 20px-wide pill. Positioned divs cannot have that bug.
  return (
    <figure className="m-0">
      <div className="flex items-baseline gap-2">
        <span className="display text-[34px] font-bold leading-none tabular-nums text-ink">
          {Math.round(value * 100 * t)}
          <span className="text-lg font-normal text-ink-faint">%</span>
        </span>
        <span className="text-xs leading-snug text-ink-soft">{label}</span>
      </div>

      {/* The observer's anchor: `useDrawTo` watches this to start the draw when the
           chart scrolls into view. */}
      <div ref={ref} className="h-0" aria-hidden />

      <div className="relative mt-3 h-4" role="img"
           aria-label={`${label}: ${Math.round(value * 100)} percent`}>
        <div className="absolute inset-x-0 top-1/2 h-1 -translate-y-1/2 rounded-full"
             style={{ background: GRID }} />
        <div className="absolute left-0 top-1/2 h-1 -translate-y-1/2 rounded-full"
             style={{ width: `${x}%`, background: DIVERGING.lowers }} />

        {peerValue != null && (
          <div className="absolute top-0 bottom-0 w-px border-l border-dashed"
               style={{ left: `${peerValue * 100}%`, borderColor: INK_MUTED }} />
        )}

        <div className="absolute top-1/2 h-4 w-4 -translate-x-1/2 -translate-y-1/2
                        rounded-full border-2 border-white shadow-card"
             style={{ left: `${x}%`, background: DIVERGING.lowers }} />
      </div>

      <div className="mt-1 flex justify-between text-2xs tabular-nums text-ink-faint">
        <span>0%</span>
        {peerValue != null && (
          <span className="text-ink-soft">
            {peerLabel ?? "comparable projects"} {Math.round(peerValue * 100)}%
          </span>
        )}
        <span>100%</span>
      </div>

      {caveat && (
        <figcaption className="mt-2.5 border-t border-paper-edge pt-2 text-2xs
                               leading-relaxed text-ink-faint">
          {caveat}
        </figcaption>
      )}
    </figure>
  );
}

/* ----------------------------------------------------------------- outcome forecast -- */

/**
 * The P50 / P80 / P95 band, drawn as a range against the figure the report itself claims.
 *
 * Percentile numbers in a column tell an officer nothing about the shape of the risk. The
 * distance between P50 and P95 is the whole message — a tight band is a well-understood
 * class of project, a wide one is not — and only a drawn range shows it.
 */
export function ForecastBand({ p50, p80, p95, claimed, peerCount, unit = "Cr" }: {
  p50: number | null; p80: number | null; p95: number | null;
  /** What the DPR asks for, if we extracted it — the comparison that makes the band land. */
  claimed?: number | null;
  peerCount?: number | null;
  unit?: string;
}) {
  const { ref, t } = useDrawTo<HTMLDivElement>(p95 ?? p80 ?? p50);
  const pts = [p50, p80, p95, claimed].filter((v): v is number => v != null);
  if (!pts.length) return <p className="text-2xs text-ink-faint">No comparable projects found.</p>;

  const lo = Math.min(...pts) * 0.92;
  const hi = Math.max(...pts) * 1.06;
  const X = (v: number) => ((v - lo) / (hi - lo)) * 100;
  const money = (v: number) => `\u20b9${v.toLocaleString("en-IN")} ${unit}`;

  const marks: [string, number | null, string][] = [
    ["P50", p50, "half of comparable projects finished at or below this"],
    ["P80", p80, "four in five finished at or below this"],
    ["P95", p95, "all but one in twenty finished at or below this"],
  ];

  // HTML, not a stretched SVG. A `preserveAspectRatio="none"` viewBox scales x and y by
  // different factors, so a 1.6-unit dashed rule became a ~8px-wide column of blocks and
  // the "what the report asks for" marker — the single most important mark on this chart —
  // read as a smudge. Positioned divs are measured in real pixels in both directions.
  return (
    <figure className="m-0">
      {/* The observer's anchor: `useDrawTo` watches this to start the draw when the
           chart scrolls into view. */}
      <div ref={ref} className="h-0" aria-hidden />

      <div className="relative h-[74px]" role="img"
           aria-label={`Cost outcome range from ${peerCount ?? "comparable"} projects`}>
        {/* The band from P50 out to P95: the spread IS the message. */}
        {p50 != null && p95 != null && (
          <div className="absolute top-[35%] h-[22%] rounded-[3px]"
               style={{ left: `${X(p50)}%`,
                        width: `${Math.max(0.5, (X(p95) - X(p50)) * t)}%`,
                        background: DIVERGING.lowers, opacity: 0.18 }} />
        )}
        <div className="absolute inset-x-0 top-1/2 h-px" style={{ background: AXIS }} />

        {marks.map(([k, v]) =>
          v == null ? null : (
            <div key={k}
                 className="absolute top-[26%] bottom-[26%] -translate-x-1/2 rounded-full"
                 style={{ left: `${X(v)}%`, width: k === "P80" ? 3 : 2,
                          background: DIVERGING.lowers, opacity: t }} />
          ))}

        {claimed != null && (
          <div className="absolute top-[14%] bottom-[14%] -translate-x-1/2 border-l-2
                          border-dashed"
               style={{ left: `${X(claimed)}%`, borderColor: DIVERGING.raises, opacity: t }} />
        )}
      </div>

      <div className="relative h-9">
        {marks.map(([k, v]) =>
          v == null ? null : (
            <div key={k} className="absolute -translate-x-1/2 text-center"
                 style={{ left: `${X(v)}%` }}>
              <p className="text-2xs font-semibold text-ink">{k}</p>
              <p className="whitespace-nowrap text-2xs tabular-nums text-ink-soft">
                {money(v)}
              </p>
            </div>
          ))}
      </div>

      <ul className="mt-2 space-y-1">
        {marks.map(([k, v, meaning]) =>
          v == null ? null : (
            <li key={k} className="flex gap-2 text-2xs leading-relaxed text-ink-soft">
              <span className="w-8 shrink-0 font-semibold tabular-nums text-ink">{k}</span>
              <span>{meaning}.</span>
            </li>
          ))}
        {claimed != null && (
          <li className="flex gap-2 text-2xs leading-relaxed">
            <span aria-hidden className="w-8 shrink-0 text-center font-semibold"
                  style={{ color: DIVERGING.raises }}>┆</span>
            <span className="text-ink-soft">
              The report itself asks for{" "}
              <b className="tabular-nums text-ink">{money(claimed)}</b>
              {p80 != null && (claimed < p80
                ? " \u2014 below what four in five comparable projects actually cost."
                : " \u2014 at or above the P80 of comparable projects.")}
            </span>
          </li>
        )}
      </ul>

      {peerCount != null && (
        <figcaption className="mt-2.5 border-t border-paper-edge pt-2 text-2xs
                               leading-relaxed text-ink-faint">
          Read from the actual outcomes of{" "}
          <b className="tabular-nums text-ink-soft">{peerCount} comparable projects</b>. Not
          a simulation — every figure above is a project that really finished. A range over
          38 projects means less than one over 342, which is why the count is never hidden.
        </figcaption>
      )}
    </figure>
  );
}

/* ------------------------------------------------------------------ peer histogram --- */

/** Where comparable projects actually landed. Shown when the backend supplies the
 *  distribution, so the percentiles above stop being three numbers from nowhere. */
export function PeerHistogram({ bins }: { bins: { label: string; count: number }[] }) {
  const { hover, show, hide } = useHoverReadout<{ label: string; count: number }>();
  if (!bins?.length) return null;
  const max = Math.max(...bins.map((b) => b.count)) || 1;
  return (
    <div data-chart className="relative">
      <div className="flex items-end gap-[3px] h-24">
        {bins.map((b, i) => (
          <div key={i} onMouseMove={(e) => show(e, b)} onMouseLeave={hide}
               className="flex-1 rounded-t-[3px] transition-[filter] hover:brightness-110"
               style={{ height: `${Math.max(3, (b.count / max) * 100)}%`,
                        background: CONFIDENCE_RAMP[2] }} />
        ))}
      </div>
      <div className="mt-1.5 flex justify-between text-2xs text-ink-faint">
        <span>{bins[0]?.label}</span>
        <span>{bins[bins.length - 1]?.label}</span>
      </div>
      {hover && (
        <Readout x={hover.x} y={hover.y}>
          {hover.datum.count} project{hover.datum.count === 1 ? "" : "s"} · {hover.datum.label}
        </Readout>
      )}
    </div>
  );
}

/* -------------------------------------------------------------------- attribution ---- */

export interface Driver {
  feature: string; value: string; shap: number;
  direction: string; plain_english: string;
}

/**
 * What moved a risk score, and by how much.
 *
 * Diverges on blue↔orange, not red/green — the red/green pair measures ΔE 6.1 under
 * protanopia and is the classic trap. Every bar still carries its arrow and its sentence,
 * so colour is the third cue and never the only one.
 */
export function Tornado({ drivers, caption }: { drivers: Driver[]; caption?: string }) {
  const shown = [...(drivers ?? [])]
    .sort((a, b) => Math.abs(b.shap) - Math.abs(a.shap)).slice(0, 6);
  if (!shown.length) return null;
  const max = Math.max(...shown.map((d) => Math.abs(d.shap))) || 1;

  return (
    <figure className="m-0">
      {/* The axis, drawn ONCE for the whole set rather than as a hairline inside each row.
          It used to be a 0.7-unit line in a stretched viewBox, which rendered at well under
          a pixel and left six bars floating with no visible zero — and a diverging chart
          with no visible midpoint is just six bars of unequal length. */}
      <div className="relative">
        <div aria-hidden
             className="pointer-events-none absolute left-1/2 top-0 bottom-5 w-px
                        -translate-x-1/2"
             style={{ background: DIVERGING.midpoint }} />

        <ul className="space-y-2.5">
          {shown.map((d) => {
            const raises = d.direction === "raises risk";
            const pct = (Math.abs(d.shap) / max) * 50;
            const tone = raises ? DIVERGING.raises : DIVERGING.lowers;
            return (
              <li key={d.feature}>
                <div className="flex items-baseline gap-1.5 text-2xs">
                  <span aria-hidden style={{ color: tone }}>{raises ? "\u25b2" : "\u25bc"}</span>
                  <span className="leading-snug text-ink">{d.plain_english}</span>
                  <span className="ml-auto shrink-0 font-medium tabular-nums"
                        style={{ color: tone }}>
                    {raises ? "raises" : "lowers"}
                  </span>
                </div>
                {/* Positioned divs, not a stretched SVG: the bar has to start exactly on the
                    shared midpoint above, and a viewBox scaled independently in x and y
                    cannot promise that at every container width. */}
                <div className="relative mt-1 h-1.5"
                     role="img" aria-label={`${d.plain_english} \u2014 ${d.direction}`}>
                  <div className="absolute top-0 h-full rounded-[2px]
                                  transition-[width] duration-500"
                       style={{
                         left: raises ? "50%" : `${50 - pct}%`,
                         width: `${Math.max(pct, 0.4)}%`,
                         background: tone,
                       }} />
                </div>
              </li>
            );
          })}
        </ul>

        <div className="mt-1.5 flex items-center justify-between text-2xs text-ink-faint">
          <span>← lowers the risk</span>
          <span>raises the risk →</span>
        </div>
      </div>

      {caption && (
        <figcaption className="mt-3 border-t border-paper-edge pt-2 text-2xs leading-relaxed
                               text-ink-faint">
          {caption}
        </figcaption>
      )}
    </figure>
  );
}

/* ------------------------------------------------------------------- small meters ---- */

/** Confidence as five steps, because a continuous bar invites reading a precision off it
 *  that the underlying number does not carry. */
export function ConfidenceMeter({ value, label = "match confidence" }: {
  value: number | null; label?: string;
}) {
  if (value == null) return null;
  const steps = Math.max(1, Math.min(5, Math.ceil(value * 5)));
  return (
    <span className="inline-flex items-center gap-1.5" title={`${label}: ${Math.round(value * 100)}%`}>
      <span className="flex gap-[2px]" aria-hidden>
        {[0, 1, 2, 3, 4].map((i) => (
          <span key={i} className="w-1.5 h-3 rounded-[1px]"
                style={{ background: i < steps ? CONFIDENCE_RAMP[Math.min(4, steps)] : GRID }} />
        ))}
      </span>
      <span className="text-2xs tabular-nums text-ink-faint">
        {Math.round(value * 100)}% {label}
      </span>
    </span>
  );
}

/** Quality against predicted delay risk. Each point is hoverable and the whole set has a
 *  table view — identity never rests on position alone. */
export function QualityRiskScatter({ rows, onPick }: {
  rows: { id: string; title: string; quality_score: number | null;
          delay_probability: number | null; critical_findings: number }[];
  onPick?: (id: string) => void;
}) {
  const pts = rows.filter((r) => r.quality_score !== null && r.delay_probability !== null);
  const { hover, show, hide } = useHoverReadout<(typeof pts)[number]>();

  if (pts.length < 2) {
    return <p className="text-2xs text-ink-faint">
      Not enough scored reports yet to compare quality against risk.
    </p>;
  }

  const data: Datum[] = pts.map((r) => ({
    key: r.id, label: r.title, value: r.quality_score,
    color: r.critical_findings > 0 ? DIVERGING.raises : DIVERGING.lowers,
  }));

  return (
    <ChartFrame
      data={data} unit="Quality"
      legend={[
        { key: "c", label: "has a critical finding", value: null, color: DIVERGING.raises },
        { key: "n", label: "no critical finding", value: null, color: DIVERGING.lowers },
      ]}
      footnote="Vertical axis is report quality out of 100. A report can be well written and
                still describe a risky project — these are separate measurements and the
                chart keeps them apart. Risk is a relative ordering, not a literal
                likelihood.">
      <div data-chart className="relative">
        <svg viewBox="0 0 320 190" className="w-full" role="img"
             aria-label="Report quality plotted against predicted schedule-delay risk">
          <line x1="34" y1="160" x2="312" y2="160" stroke={AXIS} strokeWidth="1" />
          <line x1="34" y1="14" x2="34" y2="160" stroke={AXIS} strokeWidth="1" />
          {[0, 25, 50, 75, 100].map((q) => (
            <g key={q}>
              <text x="30" y={164 - (q / 100) * 146} textAnchor="end" fontSize="7"
                    fill={INK_MUTED}>{q}</text>
              <line x1="34" y1={160 - (q / 100) * 146} x2="312" y2={160 - (q / 100) * 146}
                    stroke={GRID} strokeWidth="0.6" />
            </g>
          ))}
          {pts.map((r) => {
            const x = 34 + (r.delay_probability as number) * 278;
            const y = 160 - ((r.quality_score as number) / 100) * 146;
            return (
              <g key={r.id} onMouseMove={(e) => show(e as never, r)} onMouseLeave={hide}
                 onClick={() => onPick?.(r.id)}
                 className={onPick ? "cursor-pointer" : undefined}>
                {/* A 9px invisible target over a 4px mark — the hit area is the affordance,
                    not the dot. */}
                <circle cx={x} cy={y} r="9" fill="transparent" />
                <circle cx={x} cy={y} r="5.4" fill="#fff" />
                <circle cx={x} cy={y} r="4"
                        fill={r.critical_findings > 0 ? DIVERGING.raises : DIVERGING.lowers} />
              </g>
            );
          })}
          <text x="173" y="182" textAnchor="middle" fontSize="7.5" fill={INK_MUTED}>
            predicted schedule-delay risk →
          </text>
        </svg>
        {hover && (
          <Readout x={hover.x} y={hover.y}>
            <b>{hover.datum.title}</b>
            <span className="block text-white/70">
              quality {hover.datum.quality_score} ·
              risk {Math.round((hover.datum.delay_probability ?? 0) * 100)}%
              {hover.datum.critical_findings > 0 &&
                ` · ${hover.datum.critical_findings} critical`}
            </span>
          </Readout>
        )}
      </div>
    </ChartFrame>
  );
}

export { hatchDefs, HATCH_ID };
