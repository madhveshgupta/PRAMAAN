"use client";
/** Small shared pieces. Severity and status never rely on colour alone — each carries a
 *  glyph and a word, so the meaning survives greyscale printing and colour blindness. */

export const SEVERITY_META: Record<string, { label: string; cls: string; dot: string }> = {
  critical: { label: "Critical", cls: "bg-sev-critical-soft text-sev-critical border-sev-critical/25", dot: "bg-sev-critical" },
  high:     { label: "High",     cls: "bg-sev-high-soft text-sev-high border-sev-high/25",             dot: "bg-sev-high" },
  medium:   { label: "Medium",   cls: "bg-sev-medium-soft text-sev-medium border-sev-medium/25",       dot: "bg-sev-medium" },
  low:      { label: "Low",      cls: "bg-sev-low-soft text-sev-low border-sev-low/25",                dot: "bg-sev-low" },
  info:     { label: "Note",     cls: "bg-sev-info-soft text-sev-info border-sev-info/25",             dot: "bg-sev-info" },
};

export const STATUS_META: Record<string, { label: string; cls: string }> = {
  pass:                  { label: "Evidence found",  cls: "bg-ok-soft text-ok border-ok/25" },
  partial:               { label: "Weak evidence",   cls: "bg-sev-medium-soft text-sev-medium border-sev-medium/25" },
  insufficient_evidence: { label: "No evidence found", cls: "bg-paper-deep text-ink-soft border-paper-edge" },
  flagged:               { label: "Flagged",         cls: "bg-sev-high-soft text-sev-high border-sev-high/25" },
  // "We did not check this" must not look like "we checked and found nothing" — the first
  // is a statement about us, the second about the document.
  not_run:               { label: "Not checked",     cls: "bg-sev-info-soft text-sev-info border-sev-info/25" },
};

/** Glyph per status. Paired with the word, never used alone — see the note above. */
export const STATUS_GLYPH: Record<string, string> = {
  pass: "\u2713", partial: "\u2013", insufficient_evidence: "\u2717",
  flagged: "\u2691", not_run: "\u2298",
};

export const DPR_STATUS: Record<string, { label: string; cls: string }> = {
  draft:        { label: "Draft",          cls: "bg-paper-deep text-ink-soft border-paper-edge" },
  processing:   { label: "Processing",     cls: "bg-brand-soft text-brand border-brand/20" },
  assessed:     { label: "Assessed",       cls: "bg-ok-soft text-ok border-ok/25" },
  under_review: { label: "Under review",   cls: "bg-brand-soft text-brand border-brand/20" },
  approved:     { label: "Approved",       cls: "bg-ok-soft text-ok border-ok/25" },
  returned:     { label: "Needs attention",cls: "bg-sev-high-soft text-sev-high border-sev-high/25" },
  rejected:     { label: "Rejected",       cls: "bg-sev-critical-soft text-sev-critical border-sev-critical/25" },
};

export function Chip({ meta, dot = false }: { meta: { label: string; cls: string }; dot?: boolean }) {
  return (
    <span className={`chip ${meta.cls}`}>
      {dot && <span className="w-1.5 h-1.5 rounded-full bg-current opacity-70" />}
      {meta.label}
    </span>
  );
}

export function ScoreBadge({ score }: { score: number | null | undefined }) {
  if (score == null) return <span className="text-ink-ghost tabular-nums">—</span>;
  const tone =
    score >= 80 ? "text-ok" : score >= 60 ? "text-sev-medium" : "text-sev-critical";
  return (
    <span className={`tabular-nums font-semibold ${tone}`}>{Math.round(score)}</span>
  );
}

export function Empty({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="py-14 text-center">
      <p className="text-sm font-medium text-ink-soft">{title}</p>
      {hint && <p className="mt-1.5 text-xs text-ink-faint max-w-md mx-auto leading-relaxed">{hint}</p>}
    </div>
  );
}

export function TableSkeleton({ rows = 5, cols = 5 }: { rows?: number; cols?: number }) {
  return (
    <div className="py-2" aria-busy="true" aria-label="Loading">
      {Array.from({ length: rows }).map((_, r) => (
        <div key={r} className="flex gap-4 py-3 border-b border-paper-edge/50">
          {Array.from({ length: cols }).map((_, c) => (
            <div key={c} className="skeleton h-3" style={{ width: c === 0 ? "38%" : "12%" }} />
          ))}
        </div>
      ))}
    </div>
  );
}
