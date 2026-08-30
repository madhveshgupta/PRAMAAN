"use client";
/** One report, at a glance — the same tile on the applicant's list and the ministry's queue.
 *
 *  Shared rather than duplicated: two lookalike cards drift within a week, and a score that
 *  renders differently for the two people discussing it is its own small bug.
 *
 *  The card is ONE hover target. Every part of it moves together — the surface lifts, the
 *  edge takes colour, the arrow slides — because a row that reacts in three places reads as
 *  three things sitting near each other rather than one thing you can open.
 */
import { useRouter } from "next/navigation";

import { SectorArt, SECTOR_LABEL, sectorOf } from "@/components/layout/Ornament";
import { Chip, DPR_STATUS } from "./bits";
import { type DprRow } from "./DprTable";
import { Icon } from "./Icon";
import { ScoreArc } from "./Score";

/** A figure in the card's foot.
 *
 *  Labels here are set at full length and NEVER truncated. The first cut of this card ran
 *  four labelled columns across a 380px tile and produced "FIN…", "CR…", "P8…" — three
 *  headings that say nothing, above the three numbers an officer is choosing between. A
 *  card that cannot fit a column drops the column; it does not keep a stub of it.
 */
function Metric({ label, children, className = "" }: {
  label: string; children: React.ReactNode; className?: string;
}) {
  return (
    <div className={`min-w-0 ${className}`}>
      <p className="text-2xs font-semibold uppercase tracking-wide text-ink-faint">{label}</p>
      <p className="mt-0.5 whitespace-nowrap text-base font-semibold leading-none tabular-nums">
        {children}
      </p>
    </div>
  );
}

export function ReportCard({ row, href, footnote, showScore = true, cost }: {
  row: DprRow;
  href: string;
  /** Small line under the title — the applicant's self-check marker, or funding category. */
  footnote?: string;
  /** The score is the ministry's judgement. The submitting organisation sees counts
   *  instead — same information, and nothing to optimise toward. A number invites "we are
   *  at 84, get us to 90", and the cheapest route to 90 is padding chapters. */
  showScore?: boolean;
  /** The P80 outcome in Rs Cr, when the caller already holds it. Never fetched per card —
   *  a queue of forty cards must not cost forty requests. */
  cost?: number | null;
}) {
  const router = useRouter();
  const critical = row.critical_count ?? 0;
  const findings = row.finding_count ?? 0;
  const status = DPR_STATUS[row.status] ?? DPR_STATUS.draft;
  const attention = critical > 0;
  const processing = row.status === "processing" || row.status === "draft";
  const sector = sectorOf(row.title);
  const edge = attention ? "bg-sev-high" : processing ? "bg-brand" : "bg-ok";

  return (
    <article className="group card card-hover relative flex overflow-hidden shadow-card">
      {/* The status edge. Colour, and never only colour — the chip beside it says the same
          thing in a word and a glyph. */}
      <span aria-hidden className={`w-1.5 shrink-0 ${edge}`} />

      <div className="flex min-w-0 flex-1 flex-col">
        <button onClick={() => router.push(href)}
                className="flex-1 px-4 pb-3 pt-3.5 text-left">
          {/* The state chip gets its own line ABOVE the title. It used to sit beside it,
              competing for the same row, which left a long government project name about
              eleven characters to render itself in. */}
          <div className="flex items-center gap-2">
            <span className={`chip ${attention
              ? "border-sev-high/25 bg-sev-high-soft text-sev-high"
              : processing ? "border-brand/20 bg-brand-soft text-brand"
              : "border-ok/25 bg-ok-soft text-ok"}`}>
              {attention ? "\u2691 Action required" : processing ? "\u25f7 Processing" : "\u2713 Checked"}
            </span>
            {row.is_self_check && (
              <span className="chip border-paper-edge bg-paper-deep text-ink-soft">
                private check
              </span>
            )}
            <span className="ml-auto shrink-0 text-2xs tabular-nums text-ink-faint">
              {new Date(row.created_at).toLocaleDateString("en-IN",
                { day: "2-digit", month: "short", year: "numeric" })}
            </span>
          </div>

          <div className="mt-2.5 flex items-start gap-3">
            <SectorArt sector={sector}
                       className="h-12 w-12 shrink-0 transition-transform duration-300
                                  group-hover:scale-[1.05]" />
            <div className="min-w-0 flex-1">
              <h3 className="display line-clamp-2 text-[15px] font-bold leading-snug text-ink
                             transition-colors group-hover:text-brand-deep">
                {row.title}
              </h3>
              <p className="mt-1 truncate text-2xs text-ink-faint">{SECTOR_LABEL[sector]}</p>
              {footnote && (
                <p className="mt-0.5 line-clamp-2 text-2xs text-ink-faint">{footnote}</p>
              )}
            </div>
          </div>
        </button>

        <div className="flex items-center gap-3 border-t border-paper-edge bg-paper-soft/60
                        px-4 py-2.5">
          {showScore && (
            <div className="shrink-0 text-center">
              <p className="mb-0.5 text-2xs font-semibold uppercase tracking-wide text-ink-faint">
                AI score
              </p>
              <ScoreArc score={row.overall_score ?? null} size={50} label={false} />
            </div>
          )}

          {/* Findings and criticals read as ONE line rather than two columns: they are the
              same measurement at two thresholds, and an officer reads them together. */}
          <div className="min-w-0 flex-1">
            <Metric label="Findings">
              <span className="text-ink">{findings}</span>
              <span className="mx-1.5 text-paper-edge">/</span>
              <span className={critical ? "text-sev-critical" : "text-ink-ghost"}>{critical}</span>
              <span className="ml-1 text-2xs font-normal text-ink-faint">critical</span>
            </Metric>
            {cost != null && (
              <p className="mt-1 truncate text-2xs text-ink-faint">
                P80 outcome{" "}
                <b className="tabular-nums text-ink-soft">
                  ₹{cost.toLocaleString("en-IN")} Cr
                </b>
              </p>
            )}
          </div>

          <button onClick={() => router.push(href)}
                  aria-label={`Open ${row.title}`}
                  className="grid h-10 w-10 shrink-0 place-items-center rounded-card border
                             border-paper-edge bg-paper text-ink-soft transition-all
                             duration-200 group-hover:translate-x-0.5
                             group-hover:border-brand/30 group-hover:bg-brand
                             group-hover:text-white">
            <Icon name="arrow" className="w-4 h-4" />
          </button>
        </div>

        <div className="flex items-center gap-2 border-t border-paper-edge px-4 py-2">
          <Chip meta={status} />
        </div>
      </div>
    </article>
  );
}
