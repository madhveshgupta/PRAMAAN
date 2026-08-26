"use client";
/**
 * The report at a glance — the screen an officer opens first and returns to last.
 */
import Link from "next/link";
import { SEVERITY_RAMP, STATUS_FILL } from "@/components/charts/palette";
import { Icon } from "@/components/ui/Icon";
import { ComponentBars, ScoreArc } from "@/components/ui/Score";
import { useReveal } from "@/lib/motion";
import type { Assessment, CheckTally, Finding } from "@/lib/api";

/** The validated fills, not hand-picked ones.
 *
 *  These were locally hardcoded as #059669 / #d97706 / #dc2626 / #2563eb, which is the exact
 *  pair `charts/palette.tsx` documents as failing: "confirmed" green against "weak" amber
 *  measured ΔE 5.5 under protanopia as adjacent segments of a stacked bar — the two states an
 *  officer most needs to separate were the two that collided. The palette module holds the
 *  re-stepped set that passes, and holds it in one place so a chart cannot drift from it. */
const STATUS_COLORS = STATUS_FILL;

const STATUS_LABELS: Record<string, string> = {
  pass: "confirmed",
  partial: "weak",
  insufficient_evidence: "no evidence",
  flagged: "flagged",
  not_run: "not checked",
};

export function OverviewView({
  assessment, findings, tally, ministry, showScore, onGoto, ocrPages, pageCount,
}: {
  assessment: Assessment | null;
  findings: Finding[];
  tally: CheckTally | null;
  ministry: boolean;
  showScore: boolean;
  onGoto: (view: "findings" | "checklist" | "values" | "risk") => void;
  ocrPages?: number;
  pageCount?: number | null;
}) {
  const reveal = useReveal<HTMLDivElement>({ immediate: true, deps: [assessment?.dpr_id, findings.length] });

  const counts = findings.reduce<Record<string, number>>((a, f) => {
    a[f.severity] = (a[f.severity] ?? 0) + 1; return a;
  }, {});
  const critical = counts.critical ?? 0;
  const high = counts.high ?? 0;

  const anchored = findings.filter((f) => f.anchor_count > 0).length;
  const coverage = findings.length ? anchored / findings.length : 1;

  const top = [...findings]
    .sort((a, b) => ["critical", "high", "medium", "low", "info"].indexOf(a.severity)
                  - ["critical", "high", "medium", "low", "info"].indexOf(b.severity))
    .slice(0, 3);

  const totalChecks = tally?.total || 0;

  // Every severity present, not just the top two. This panel used to draw a hardcoded
  // "Critical" and "High" row, so on a report with 3 critical, 2 high, 2 medium, 1 low and
  // 1 info it showed 5 of 9 findings and silently dropped the rest — under a heading that
  // says "What was found".
  const SEVERITIES = ["critical", "high", "medium", "low", "info"] as const;
  const SEVERITY_LABEL: Record<string, string> = {
    critical: "Critical", high: "High", medium: "Medium", low: "Low", info: "Note",
  };
  const severityRows = SEVERITIES
    .map((k) => [k, counts[k] ?? 0] as const)
    .filter(([, n]) => n > 0);
  const maxFindings = Math.max(1, ...severityRows.map(([, n]) => n));

  return (
    <div ref={reveal} className="space-y-6">
      
      {/* 1. Critical Banner */}
      {critical > 0 && (
        <div data-reveal className="bg-rose-50 border border-rose-200 rounded-[20px] p-5 flex items-center justify-between gap-5 relative overflow-hidden shadow-sm">
          <div className="flex items-center gap-5 relative z-10">
            <div className="w-14 h-14 rounded-full bg-rose-100 flex items-center justify-center shrink-0 border border-rose-200">
              <Icon name="flag" className="w-6 h-6 text-rose-500" />
            </div>
            <div>
              <h3 className="text-[16px] font-bold text-rose-800">{critical} critical finding{critical > 1 ? "s" : ""} on this report.</h3>
              <p className="text-[13px] text-rose-700/90 mt-1 max-w-2xl">Critical means <b>look at this before the file moves</b> — it is not a rejection, and nothing here has been rejected.</p>
            </div>
          </div>
          <button onClick={() => onGoto("findings")} className="z-10 flex items-center gap-2 font-bold text-rose-600 hover:text-rose-700 transition-colors text-sm px-4 py-2 hover:bg-rose-100 rounded-xl shrink-0">
            Open them <Icon name="chevronRight" className="w-4 h-4" />
          </button>
          
          <Icon name="flag" className="absolute right-10 -bottom-10 w-48 h-48 text-rose-600 opacity-5 pointer-events-none" />
        </div>
      )}

      {/* 2. The score, and what it is made of.
             Restored: this panel had been dropped, so the Overview showed how much was
             examined and what was found but not the headline the whole assessment exists to
             produce — and `showScore` was still being accepted as a prop and then ignored,
             which meant an applicant's private check silently rendered the same screen as a
             live submission. */}
      {showScore && assessment && (
        <div data-reveal className="bg-white rounded-[24px] shadow-sm border border-slate-200
                                    p-6 flex flex-col sm:flex-row items-center gap-8">
          <div className="shrink-0 text-center">
            <ScoreArc score={assessment.overall_score ?? null} size={132}
                      sublabel={assessment.rubric_version
                        ? `rubric ${assessment.rubric_version}` : undefined} />
          </div>

          <div className="min-w-0 flex-1 self-stretch">
            <h2 className="text-[17px] font-bold text-slate-800">Quality score</h2>
            <p className="text-[12px] text-slate-500 mt-1 max-w-lg leading-relaxed">
              How well the report evidences what it is required to contain — not whether the
              project is worth funding. Advisory: nothing here decides anything.
            </p>
            <div className="mt-5">
              {/* Cost realism is filtered out for the applicant because it never runs: it is
                  our note about a gap in our own coverage, not something its author can act
                  on. */}
              <ComponentBars
                components={assessment.components.filter(
                  (c) => ministry || c.key !== "cost_realism")}
                onPick={() => onGoto("checklist")} />
            </div>
          </div>
        </div>
      )}

      {/* 2. Row 1 - Left and Right Cards */}
      <div className="grid gap-6 lg:grid-cols-2">
         {/* Left Card: How much was examined */}
         <div data-reveal className="bg-white rounded-[24px] shadow-sm border border-slate-200 p-6 flex flex-col h-full relative overflow-hidden">
            <div className="flex justify-between items-start mb-8">
              <div className="flex gap-4">
                <div className="w-12 h-12 rounded-full bg-emerald-50 flex items-center justify-center shrink-0 border border-emerald-100">
                  <Icon name="list" className="w-6 h-6 text-emerald-500" />
                </div>
                <div>
                  <h2 className="text-[17px] font-bold text-slate-800">How much was examined</h2>
                  <p className="text-[12px] text-slate-500 mt-1 max-w-sm">The audit trail of the assessment — every statutory rule that ran, whether or not it raised a finding.</p>
                </div>
              </div>
              {totalChecks > 0 && (
                <button onClick={() => onGoto("checklist")} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-emerald-200 text-emerald-600 text-[12px] font-bold hover:bg-emerald-50 transition-colors shrink-0">
                  Open <Icon name="chevronRight" className="w-3 h-3" />
                </button>
              )}
            </div>

            {totalChecks > 0 ? (
              <>
                {/* Custom Stacked Bar */}
                <div className="w-full h-8 rounded-full overflow-hidden flex mb-4 relative shadow-inner">
                  {["pass", "partial", "insufficient_evidence", "flagged", "not_run"].map(k => {
                    const n = (tally as any)[k] || 0;
                    if (n === 0) return null;
                    const w = (n / totalChecks) * 100;
                    return (
                      <div key={k} className="h-full flex items-center justify-center border-r border-white/20 last:border-0" style={{width: `${w}%`, backgroundColor: STATUS_COLORS[k]}}>
                        {w > 10 && <span className="text-white text-[11px] font-bold">{n}</span>}
                      </div>
                    );
                  })}
                </div>

                {/* Custom Legend */}
                <div className="flex flex-wrap gap-x-4 gap-y-2 mb-8">
                  {["pass", "partial", "insufficient_evidence", "flagged", "not_run"].map(k => {
                    const n = (tally as any)[k] || 0;
                    if (n === 0) return null;
                    return (
                      <div key={k} className="flex items-center gap-1.5 text-[11px] font-bold text-slate-600">
                        <span className="w-2 h-2 rounded-sm" style={{backgroundColor: STATUS_COLORS[k]}}></span>
                        {n} {STATUS_LABELS[k]}
                      </div>
                    );
                  })}
                </div>

                <div className="mt-auto border-t border-slate-100 pt-5">
                  <p className="text-[13px] text-slate-600 leading-relaxed">
                    <b className="text-slate-800">{tally?.pass} of {totalChecks}</b> checks were confirmed against a page you can open.<br/>
                    {tally?.not_run} were not run — a gap in our coverage, not in the report.
                  </p>
                </div>
              </>
            ) : (
              <p className="text-sm text-slate-500 mt-auto">No checklist recorded.</p>
            )}
         </div>

         {/* Right Card: What was found */}
         <div data-reveal className="bg-white rounded-[24px] shadow-sm border border-slate-200 p-6 flex flex-col h-full">
            <div className="flex justify-between items-start mb-8">
              <div className="flex gap-4">
                <div className="w-12 h-12 rounded-full bg-emerald-50 flex items-center justify-center shrink-0 border border-emerald-100">
                  <Icon name="docCheck" className="w-6 h-6 text-emerald-500" />
                </div>
                <div>
                  <h2 className="text-[17px] font-bold text-slate-800">What was found</h2>
                  <p className="text-[12px] text-slate-500 mt-1 max-w-sm">Ordered by how much attention each deserves.</p>
                </div>
              </div>
              {findings.length > 0 && (
                <button onClick={() => onGoto("findings")} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-emerald-200 text-emerald-600 text-[12px] font-bold hover:bg-emerald-50 transition-colors shrink-0">
                  Open <Icon name="chevronRight" className="w-3 h-3" />
                </button>
              )}
            </div>

            {findings.length > 0 ? (
              <>
                {/* Severity is ORDINAL, so it is one hue deepening rather than a red bar
                    against a blue one — five unrelated colours would claim these are five
                    kinds of thing rather than one scale. The word beside each bar carries
                    the meaning; the colour is the third cue. */}
                <div className="space-y-3.5 mb-8">
                  {severityRows.map(([k, n]) => (
                    <div key={k} className="flex items-center gap-4">
                      <span className="w-16 text-[12px] font-bold text-slate-700">
                        {SEVERITY_LABEL[k]}
                      </span>
                      <div className="flex-1 h-3.5 bg-slate-100 rounded-full overflow-hidden">
                        <div className="h-full rounded-full transition-[width] duration-500"
                             style={{ width: `${(n / maxFindings) * 100}%`,
                                      background: SEVERITY_RAMP[k] }} />
                      </div>
                      <span className="w-4 text-right text-[12px] font-bold tabular-nums
                                       text-slate-800">{n}</span>
                    </div>
                  ))}
                </div>

                <ul className="mt-auto border-t border-slate-100 pt-5 space-y-3">
                  {top.map(f => (
                    <li key={f.id} className="flex items-center gap-3 text-[12px]">
                      <span aria-hidden className="w-1.5 h-1.5 rounded-full shrink-0"
                            style={{ background: SEVERITY_RAMP[f.severity] ?? SEVERITY_RAMP.info }} />
                      <span className="truncate flex-1 font-semibold text-slate-600">{f.title}</span>
                      <span className="font-bold text-emerald-600 shrink-0">
                        {f.evidence[0] ? `p.${f.evidence[0].page}` : '-'}
                      </span>
                    </li>
                  ))}
                </ul>
              </>
            ) : (
              <p className="text-sm text-slate-500 mt-auto">No findings recorded.</p>
            )}
         </div>
      </div>

      {/* 3. Row 2 - How much of this you can check yourself */}
      <div data-reveal className="bg-white rounded-[24px] shadow-sm border border-slate-200 p-6 sm:p-8 flex flex-col md:flex-row items-center justify-between gap-8 relative overflow-hidden">
         
         {/* Background graphics like the screenshot */}
         <div className="absolute right-0 bottom-0 pointer-events-none opacity-5">
            <Icon name="building" className="w-80 h-80 text-emerald-900 translate-y-16 translate-x-16" />
         </div>
         <div className="absolute right-1/4 top-0 pointer-events-none opacity-[0.03]">
            <Icon name="grid" className="w-48 h-48 text-emerald-900 -translate-y-8" />
         </div>

         <div className="flex gap-5 relative z-10 max-w-2xl">
            <div className="w-16 h-16 rounded-2xl bg-emerald-50 flex items-center justify-center shrink-0 border border-emerald-100 shadow-sm">
               <Icon name="shield" className="w-8 h-8 text-emerald-500" />
            </div>
            <div>
               <h2 className="text-[20px] font-bold text-slate-800">How much of this you can check yourself</h2>
               <p className="text-[13px] text-slate-600 mt-2 leading-relaxed">
                 <b className="text-slate-800">{anchored} of {findings.length} findings</b> carry at least one place in the document you can open and read.<br/>
                 A finding with no evidence anchor is a bug in this system, not a fact about the report — if you see one, it should be reported.
               </p>
            </div>
         </div>

         <div className="relative z-10 shrink-0 md:mr-10">
            <div className="w-28 h-28 rounded-full relative flex items-center justify-center">
               <svg className="absolute inset-0 w-full h-full -rotate-90">
                 {/* Track */}
                 <circle cx="56" cy="56" r="50" fill="none" stroke="#f1f5f9" strokeWidth="6" />
                 {/* Fill */}
                 <circle cx="56" cy="56" r="50" fill="none" stroke="#059669" strokeWidth="6" strokeDasharray="314" strokeDashoffset={314 - (314 * coverage)} className="transition-all duration-1000 ease-out drop-shadow-sm" strokeLinecap="round" />
               </svg>
               <div className="text-center mt-1">
                 <div className="text-2xl font-black text-slate-800 leading-none">{Math.round(coverage * 100)}%</div>
                 <div className="text-[10px] font-bold text-slate-400 uppercase mt-1">Traceable</div>
               </div>
            </div>
         </div>
      </div>
      
      {/* Footer text */}
      {assessment && (
        <div data-reveal className="flex items-center gap-2 text-2xs leading-relaxed text-slate-400 font-medium">
          <Icon name="help" className="w-3.5 h-3.5" />
          {assessment.advisory_notice}
          {ministry && assessment.engine_version && (
            <span> · Rubric {assessment.rubric_version} · engine {assessment.engine_version}.</span>
          )}
          <Link href="/data-sources" className="text-emerald-600 hover:underline font-bold ml-1">
            Where this comes from
          </Link>
        </div>
      )}
    </div>
  );
}
