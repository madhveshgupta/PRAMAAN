"use client";
/** The quality score, and the components it is made of.
 *
 *  Drawn as an OPEN ARC rather than a closed ring, and that is a content decision as much
 *  as a visual one. A closed ring reads as a proportion of something complete — a verdict
 *  delivered. An arc with a visible gap reads as a position on a scale, which is what this
 *  number actually is: an advisory measurement of how well a report evidences what it must
 *  contain, not a ruling on whether the project deserves money.
 */
import { useCountUp, useDrawTo } from "@/lib/motion";
import type { Component } from "@/lib/api";

/** Bands, stated once. The tone is never the only cue — the caption names the band in
 *  words directly beneath the figure. */
function band(v: number) {
  if (v >= 80) return { tone: "#1d6b45", word: "Well evidenced" };
  if (v >= 60) return { tone: "#7d6212", word: "Partly evidenced" };
  return { tone: "#9d1c28", word: "Thinly evidenced" };
}

export function ScoreArc({ score, size = 108, label = true, sublabel, animate }: {
  score: number | null;
  size?: number;
  label?: boolean;
  sublabel?: string;
  /** Count the figure up and draw the arc. Defaults to ON for the full component and OFF
   *  for the caption-less form, which is the one used inside cards.
   *
   *  A queue of twelve cards animating twelve dials at once is not twelve pieces of
   *  feedback, it is a flicker — and for the second it runs, every score on the screen is
   *  WRONG. The motion says "this figure was measured", which is worth saying once, on the
   *  screen about one report, and not worth saying twelve times on a screen about a list. */
  animate?: boolean;
}) {
  const moving = animate ?? label;
  const { ref, t: drawT } = useDrawTo<SVGSVGElement>(moving ? score : null);
  const { ref: numRef, shown } = useCountUp(moving ? score : null);
  const t = moving ? drawT : 1;
  const value = moving ? shown : score;
  const v = score ?? 0;
  const { tone, word } = band(v);

  // 260° of arc, opening at the bottom. Geometry derived rather than hardcoded so the
  // component takes any size without a second set of magic numbers.
  const sweep = 260;
  const r = size * 0.375;
  const cx = size / 2;
  const cy = size / 2;
  const stroke = size * 0.105;
  const arcLen = (sweep / 360) * 2 * Math.PI * r;

  return (
    <div className="inline-flex flex-col items-center">
      <div className="relative" style={{ width: size, height: size * 0.86 }}>
        <svg ref={ref} width={size} height={size} viewBox={`0 0 ${size} ${size}`}
             className="block" role="img"
             aria-label={score === null
               ? "Not scored yet"
               : `Quality score ${Math.round(v)} out of 100 — ${word}`}>
          <g transform={`rotate(140 ${cx} ${cy})`}>
            <circle cx={cx} cy={cy} r={r} fill="none" stroke="#e7edf2"
                    strokeWidth={stroke} strokeLinecap="round"
                    strokeDasharray={`${arcLen} ${2 * Math.PI * r}`} />
            {score !== null && (
              <circle cx={cx} cy={cy} r={r} fill="none" stroke={tone}
                      strokeWidth={stroke} strokeLinecap="round"
                      strokeDasharray={`${arcLen * (v / 100) * t} ${2 * Math.PI * r}`} />
            )}
          </g>
        </svg>
        <div className="absolute top-0 left-0 right-0 flex flex-col items-center justify-center
                        pointer-events-none" style={{ height: size }}>
          <span ref={numRef} className="display font-bold tabular-nums leading-none text-ink"
                style={{ fontSize: size * 0.3 }}>
            {score === null ? "—" : Math.round(value ?? 0)}
          </span>
          {score !== null && (
            <span className="tabular-nums leading-none mt-0.5 text-ink-faint"
                  style={{ fontSize: size * 0.14 }}>
              /100
            </span>
          )}
        </div>
      </div>

      {label && (
        <div className="mt-1 text-center">
          <p className="text-2xs font-semibold uppercase tracking-wide"
             style={{ color: score === null ? "#6f7d89" : tone }}>
            {score === null ? "Not scored" : word}
          </p>
          {sublabel && <p className="mt-0.5 text-2xs text-ink-faint">{sublabel}</p>}
        </div>
      )}
    </div>
  );
}

/** Kept under its old name so nothing that imported it has to change; `compact` now means
 *  "no caption", which is what every caller used it for. */
export function ScoreDial({ score, size = 96, compact = false }: {
  score: number | null; size?: number; compact?: boolean;
}) {
  if (compact) return <ScoreArc score={score} size={size} label={false} />;
  return (
    <div className="flex items-center gap-4">
      <ScoreArc score={score} size={size} />
      <div>
        <p className="text-sm font-semibold">Quality score</p>
        <p className="text-2xs text-ink-faint mt-1 max-w-[16rem] leading-relaxed">
          Advisory. Measures how well the report evidences what it is required to contain —
          not whether the project is worth funding.
        </p>
      </div>
    </div>
  );
}

export function ComponentBars({ components, onPick }: {
  components: Component[];
  /** Each component is made of specific checks; clicking one should be able to take the
   *  reader to them. Optional so the applicant's read-only view can omit the affordance. */
  onPick?: (key: string) => void;
}) {
  return (
    <ul className="space-y-3">
      {components.map((c) => {
        const missing = c.score === null;
        const Row = onPick && !missing ? "button" : "div";
        return (
          <li key={c.key}>
            <Row {...(onPick && !missing ? { onClick: () => onPick(c.key), type: "button" as const } : {})}
                 className={`block w-full text-left group ${
                   onPick && !missing ? "cursor-pointer" : ""}`}>
              <div className="flex justify-between items-baseline text-xs">
                <span className={`text-ink-soft ${onPick && !missing
                  ? "group-hover:text-brand transition-colors" : ""}`}>
                  {c.label}
                </span>
                <span className="tabular-nums font-semibold">
                  {missing
                    ? <span className="text-ink-ghost font-normal">not scored</span>
                    : Math.round(c.score!)}
                </span>
              </div>
              <div className="mt-1.5 h-2 rounded-full bg-paper-edge overflow-hidden">
                {missing ? (
                  /* Hatched, never zero — an unavailable component is unknown, not bad, and
                     drawing it as an empty bar would read as a failing score. */
                  <div className="h-full w-full bg-[repeating-linear-gradient(45deg,#dbe2e8_0_4px,#f0f3f6_4px_8px)]" />
                ) : (
                  <div className="h-full rounded-full bg-brand transition-[width] duration-700
                                  ease-[cubic-bezier(.16,.84,.44,1)]"
                       style={{ width: `${c.score}%` }} />
                )}
              </div>
            </Row>
          </li>
        );
      })}
    </ul>
  );
}
