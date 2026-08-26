"use client";
/**
 * The checklist — what was examined, not only what went wrong.
 */
import { useMemo, useState } from "react";
import { STATUS_FILL } from "@/components/charts/palette";
import { Empty } from "@/components/ui/bits";
import { Icon, type IconName } from "@/components/ui/Icon";
import { useReveal } from "@/lib/motion";
import { EvidenceLink } from "./EvidenceRoute";
import type { ViewProps } from "./types";
import type { OpenEvidence } from "./types";
import type { CheckRow, Checklist } from "@/lib/api";

/** Per-status presentation. FIVE statuses, not two.
 *
 *  This row used to compute `isPass = status === "pass"` and render everything else as
 *  "Weak evidence" in amber. That collapsed three genuinely different statements into one
 *  wrong one:
 *
 *    · `insufficient_evidence` means we looked and found nothing — which is NOT evidence
 *      that the requirement was unmet, and must never be shown as a weakness in the report;
 *    · `not_run` means WE did not run the check — a gap in our coverage, and showing it as
 *      a defect in the submission blames the applicant for our own limitation;
 *    · `flagged` means an officer should look directly, which is not "weak" either.
 *
 *  Colour is never the only cue: each carries a glyph and a word.
 */
const ROW_STATE: Record<string, {
  word: string; glyph: string; rail: string; dot: string; chip: string;
}> = {
  pass: {
    word: "Evidence found", glyph: "\u2713", rail: "border-l-emerald-500",
    dot: "bg-emerald-500 text-white", chip: "bg-emerald-50 text-emerald-700",
  },
  partial: {
    word: "Weak evidence", glyph: "\u2013", rail: "border-l-amber-500",
    dot: "bg-amber-500 text-white", chip: "bg-amber-50 text-amber-700",
  },
  insufficient_evidence: {
    word: "No evidence found", glyph: "\u2717", rail: "border-l-slate-300",
    dot: "bg-slate-400 text-white", chip: "bg-slate-100 text-slate-600",
  },
  flagged: {
    word: "Flagged for you", glyph: "\u2691", rail: "border-l-orange-500",
    dot: "bg-orange-500 text-white", chip: "bg-orange-50 text-orange-700",
  },
  not_run: {
    word: "Not checked", glyph: "\u2298", rail: "border-l-blue-400",
    dot: "bg-blue-500 text-white", chip: "bg-blue-50 text-blue-700",
  },
};

/** How the anchor was found, in words an officer can repeat. */
const METHOD_WORD: Record<string, string> = {
  exact: "exact text match", span: "matched against the parsed text",
  fuzzy: "close text match", table: "read from a table cell",
  ocr: "read by character recognition", regex: "matched by rule",
  llm_verified: "model-proposed, then located in the text",
};

function Row({ check, index, active, onOpen }: {
  check: CheckRow; index: number; active: boolean; onOpen: () => void;
}) {
  const clickable = Boolean(check.evidence && check.evidence.length > 0);
  const st = ROW_STATE[check.status] ?? ROW_STATE.flagged;
  const first = check.evidence?.[0];

  return (
    <div className="relative z-10 mb-1 flex items-center gap-3 sm:gap-4 group">
      <div className="z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-full
                      bg-slate-50 text-sm font-bold text-slate-500 shadow-sm
                      ring-1 ring-slate-200/60">
        {index}
      </div>

      <div className={`flex flex-1 flex-col justify-between gap-4 rounded-xl border
                       border-l-[4px] border-slate-200 bg-white p-4 shadow-[0_2px_10px_rgb(0,0,0,0.02)]
                       transition-all duration-300 md:flex-row md:items-center sm:p-5
                       ${st.rail} ${active ? "ring-2 ring-brand/20 shadow-md" : "hover:shadow-md"}`}>

        <div className="flex min-w-0 flex-1 items-start gap-4">
          <div className={`mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full
                           text-[12px] font-bold shadow-sm ${st.dot}`}
               aria-hidden>
            {st.glyph}
          </div>

          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-3">
              <h3 className="text-[15px] font-bold text-slate-800">{check.label}</h3>
              <span className={`rounded px-2 py-0.5 text-[10px] font-bold uppercase ${st.chip}`}>
                {st.word}
              </span>
            </div>
            {check.detail && (
              <p className="mt-1.5 max-w-3xl text-[13px] leading-relaxed text-slate-500">
                {check.detail}
              </p>
            )}

            {/* Facts about THIS row, read off the row. Three fixed chips used to sit here —
                "Report evidence", "Data validated", "Auto checked" — rendered identically on
                every check, including ones with no anchor at all. A row that says nothing
                could be located while claiming "Data validated" beside it is the one kind of
                mistake this product cannot make. */}
            <div className="mt-3 flex flex-wrap items-center gap-2">
              {clickable ? (
                <>
                  <span className="flex items-center gap-1.5 rounded-md border border-slate-100
                                   bg-slate-50 px-2.5 py-1 text-[11px] font-semibold text-slate-600">
                    <Icon name="doc" className="w-3.5 h-3.5 text-blue-500" />
                    {check.anchor_count} place{check.anchor_count === 1 ? "" : "s"} cited
                  </span>
                  {first?.method && (
                    <span className="flex items-center gap-1.5 rounded-md border border-slate-100
                                     bg-slate-50 px-2.5 py-1 text-[11px] font-semibold text-slate-600">
                      <Icon name="link" className="w-3.5 h-3.5 text-purple-500" />
                      {METHOD_WORD[first.method] ?? first.method.replace(/_/g, " ")}
                    </span>
                  )}
                </>
              ) : (
                <span className="flex items-center gap-1.5 rounded-md border border-slate-100
                                 bg-slate-50 px-2.5 py-1 text-[11px] font-semibold text-slate-500">
                  <Icon name="ban" className="w-3.5 h-3.5 text-slate-400" />
                  nothing in the document to cite
                </span>
              )}
              {check.finding_ids?.length > 0 && (
                <span className="flex items-center gap-1.5 rounded-md border border-slate-100
                                 bg-slate-50 px-2.5 py-1 text-[11px] font-semibold text-slate-600">
                  <Icon name="flag" className="w-3.5 h-3.5 text-amber-500" />
                  raised {check.finding_ids.length} finding
                  {check.finding_ids.length === 1 ? "" : "s"}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* One control, and it does something. There were two more beside it — a chevron and
            a menu — that were wired to nothing on every row of a 35-row list. */}
        <div className="flex shrink-0 items-center gap-2 self-end md:self-auto">
          {clickable ? (
            <EvidenceLink evidence={check.evidence} onOpen={onOpen} active={active} />
          ) : (
            <span className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white
                             px-3 py-1.5 text-xs font-semibold text-slate-400">
              No page to cite <Icon name="ban" className="w-3.5 h-3.5" />
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

interface Family { key: string; label: string; checks: CheckRow[]; visible: CheckRow[] }

function FamilyBlock({ fam, activeKey, onOpen }: {
  fam: Family; activeKey: string | null | undefined; onOpen: OpenEvidence;
}) {
  const done = fam.checks.filter((c) => c.status === "pass").length;
  const total = fam.checks.length;
  const pct = Math.round((total > 0 ? done / total : 0) * 100);

  // How many of this family's checks cite a page you can open. This tile used to read
  // "Confidence: High / Medium / Low", derived from the pass percentage and then labelled
  // with a word that means something else entirely — an invented statistic, which is the one
  // thing this system is not allowed to produce. Cited-page count is the same reassurance,
  // and it is a fact we hold.
  const cited = fam.checks.filter((c) => c.anchor_count > 0).length;
  const notRun = fam.checks.filter((c) => c.status === "not_run").length;

  const t = pct === 100 ? {
    iconBg: "bg-emerald-50", iconText: "text-emerald-500",
    badgeBg: "bg-emerald-500", badgeText: "text-white", badgeIcon: "check",
    titleText: "text-emerald-700",
    msgText: "text-emerald-600",
    barBg: "bg-emerald-100", barFill: "bg-emerald-500",
    msg: "Every check in this group found its evidence",
    msgIcon: "check"
  } : pct >= 50 ? {
    iconBg: "bg-amber-50", iconText: "text-amber-500",
    badgeBg: "bg-amber-500", badgeText: "text-white", badgeIcon: "clock",
    titleText: "text-amber-700",
    msgText: "text-amber-600",
    barBg: "bg-amber-100", barFill: "bg-amber-500",
    msg: "Some checks in this group found no evidence",
    msgIcon: "clock"
  } : {
    iconBg: "bg-rose-50", iconText: "text-rose-500",
    badgeBg: "bg-rose-500", badgeText: "text-white", badgeIcon: "clock",
    titleText: "text-rose-700",
    msgText: "text-rose-600",
    barBg: "bg-rose-100", barFill: "bg-rose-500",
    msg: "Most checks in this group found no evidence",
    msgIcon: "clock"
  };

  const confT = pct === 100 ? { icon: "text-emerald-500", text: "text-emerald-600" } 
              : pct >= 50 ? { icon: "text-amber-500", text: "text-amber-600" }
              : { icon: "text-rose-500", text: "text-rose-600" };

  return (
    <div className="mb-10 relative">
      <div className="bg-white rounded-[24px] shadow-sm border border-slate-200 p-6 mb-6">
        <div className="flex flex-col xl:flex-row items-start xl:items-center justify-between gap-6">
          
          <div className="flex items-center gap-5">
            <div className={`w-20 h-20 ${t.iconBg} rounded-full flex items-center justify-center relative shrink-0`}>
              <Icon name="list" className={`w-10 h-10 ${t.iconText}`} />
              <div className={`absolute -bottom-1 -right-1 ${t.badgeBg} rounded-full p-1 border-[3px] border-white shadow-sm`}>
                 <Icon name={t.badgeIcon as IconName} className={`w-4 h-4 ${t.badgeText}`} />
              </div>
            </div>
            <div>
              <h2 className="text-[22px] font-bold text-slate-800 tracking-tight leading-tight">{fam.label}</h2>
              <p className={`${t.titleText} font-bold mt-1 text-sm`}>{done} <span className="text-slate-500 font-medium">of {total} confirmed</span></p>
              <div className={`${t.msgText} text-[13px] mt-1.5 flex items-center gap-1.5 font-medium`}>
                <div className={`${t.badgeBg} rounded-full p-0.5`}><Icon name={t.msgIcon as IconName} className={`w-2.5 h-2.5 ${t.badgeText}`} /></div> 
                {t.msg}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3 flex-wrap">
            <div className="bg-slate-50/80 rounded-2xl p-3 border border-slate-100 flex items-center gap-3 min-w-[140px]">
              <div className="bg-white p-2 rounded-xl shadow-sm border border-slate-100"><Icon name="trend" className={`w-5 h-5 ${t.iconText}`} /></div>
              <div>
                <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Progress</div>
                <div className={`text-lg font-black ${t.msgText} leading-none mt-1`}>{pct}%</div>
              </div>
            </div>
            
            <div className="bg-slate-50/80 rounded-2xl p-3 border border-slate-100 flex items-center gap-3 min-w-[140px]">
              <div className="bg-white p-2 rounded-xl shadow-sm border border-slate-100"><Icon name="shield" className="w-5 h-5 text-blue-500" /></div>
              <div>
                <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Checks Passed</div>
                <div className="text-lg font-black text-blue-600 leading-none mt-1">{done} <span className="text-sm text-slate-400 font-semibold">/ {total}</span></div>
              </div>
            </div>
            
            <div className="bg-slate-50/80 rounded-2xl p-3 border border-slate-100 flex items-center gap-3 min-w-[140px]">
              <div className="bg-white p-2 rounded-xl shadow-sm border border-slate-100"><Icon name="docCheck" className={`w-5 h-5 ${confT.icon}`} /></div>
              <div>
                <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                  Cite a page
                </div>
                <div className={`mt-1 text-lg font-black leading-none ${confT.text}`}>
                  {cited} <span className="text-sm font-semibold text-slate-400">/ {total}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="mt-6 flex items-center gap-4">
          <div className={`flex-1 h-2.5 ${t.barBg} rounded-full overflow-hidden`}>
            <div className={`h-full ${t.barFill} rounded-full transition-all duration-1000 ease-out`} style={{ width: `${pct}%` }}></div>
          </div>
          <span className="font-bold text-slate-700 text-sm tracking-tight">{pct}%</span>
        </div>
      </div>

      <div className="relative pl-0 sm:pl-6 pb-2">
        <div className="hidden sm:block absolute left-[39px] top-6 bottom-4 w-[2px] bg-slate-200 z-0" />
        <div className="flex flex-col gap-4">
          {fam.visible.map((c, idx) => (
            <Row key={c.check_id} check={c} index={idx + 1} active={activeKey === c.check_id} onOpen={() => onOpen(c.evidence, c.severity, 0, c.check_id)} />
          ))}
        </div>
      </div>
      
      {pct === 100 && (
        <div className="bg-gradient-to-r from-emerald-50 to-emerald-100/50 border border-emerald-200/50 rounded-xl p-5 flex items-center gap-4 mt-4 relative overflow-hidden">
          <div className="w-10 h-10 bg-white rounded-full flex items-center justify-center shadow-sm border border-emerald-100 shrink-0 z-10">
            <Icon name="shield" className="w-5 h-5 text-emerald-600" />
          </div>
          <div className="z-10">
            {/* Advisory, not congratulatory, and not addressed to "your DPR": this screen is
                read by the appraising officer as often as by the submitter, and the system
                does not hand out verdicts or confidence levels it has not measured. */}
            <h4 className="text-[14px] font-bold text-emerald-900">
              All {total} checks in this group found their evidence in the document.
            </h4>
            <p className="mt-0.5 text-xs font-medium text-emerald-700/80">
              {cited} of them cite a page you can open and read for yourself.
              {notRun > 0 && ` ${notRun} were not run at all.`}
            </p>
          </div>
          <div className="absolute right-4 -bottom-4 opacity-30 z-0">
            <Icon name="shield" className="w-24 h-24 text-emerald-600" />
          </div>
        </div>
      )}
    </div>
  );
}

export function ChecklistView({ checklist, onOpen, activeKey, ministry }: ViewProps & {
  checklist: Checklist | null;
}) {
  const [only, setOnly] = useState<string | null>(null);
  const reveal = useReveal<HTMLDivElement>({ immediate: true, deps: [checklist?.dpr_id] });

  const families = useMemo(() => {
    if (!checklist) return [];
    return checklist.families
      .filter((f) => ministry || f.key !== "cost_realism")
      .map((f) => ({
        ...f,
        visible: only ? f.checks.filter((c) => c.status === only) : f.checks,
      }))
      .filter((f) => f.visible.length > 0);
  }, [checklist, only, ministry]);

  if (!checklist) {
    return <Empty title="No checklist yet"
                  hint="This report has not been assessed. The checklist is written as the
                        assessment runs, so it appears together with the score." />;
  }
  if (checklist.stale) {
    return <Empty title="Assessed before the checklist existed"
                  hint="This report was scored by an earlier engine that did not record which
                        checks it ran. Re-run the assessment to record every check this
                        document passed — the score itself is unaffected." />;
  }

  const t = checklist.tally;
  const STATUSES = ["pass", "partial", "insufficient_evidence", "flagged", "not_run"] as const;
  const counts = t as unknown as Record<string, number>;

  return (
    <div ref={reveal}>
      {/* The whole-document summary, restored. Without it the page opened straight into the
          first family, so an officer could read every group and still never be told how many
          checks ran in total, which rubric was applied, or — the one that matters — how many
          were not run at all. A checklist that only shows the groups it did examine is the
          black box this screen exists to replace. */}
      <div data-reveal className="mb-8 rounded-[24px] border border-slate-200 bg-white p-6
                                  shadow-sm">
        <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
          <h2 className="text-[18px] font-bold text-slate-800">
            {t.total} checks were run against this document
          </h2>
          <span className="text-[13px] text-slate-500">
            {t.pass} confirmed against a page you can open
          </span>
        </div>

        <div className="mt-4 flex h-7 gap-[2px] overflow-hidden rounded-lg" role="img"
             aria-label={STATUSES.filter((k) => counts[k] > 0)
               .map((k) => `${counts[k]} ${ROW_STATE[k].word}`).join(", ")}>
          {STATUSES.filter((k) => counts[k] > 0).map((k) => (
            <div key={k} className="grid place-items-center"
                 style={{ width: `${(counts[k] / (t.total || 1)) * 100}%`,
                          background: STATUS_FILL[k] }}>
              {(counts[k] / (t.total || 1)) * 100 > 9 && (
                <span className="text-[11px] font-bold tabular-nums text-white/95">
                  {counts[k]}
                </span>
              )}
            </div>
          ))}
        </div>

        {/* Filter chips. `only` was already wired into the family filter but nothing on the
            page could set it, so the state — and the empty state below that depends on it —
            were both unreachable. */}
        <div className="mt-4 flex flex-wrap items-center gap-2 no-print">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
            Show only
          </span>
          {STATUSES.filter((k) => counts[k] > 0).map((k) => (
            <button key={k} onClick={() => setOnly(only === k ? null : k)}
                    aria-pressed={only === k}
                    className={`flex items-center gap-1.5 rounded-lg border px-2.5 py-1
                                text-[11px] font-semibold transition-colors ${
                      only === k
                        ? "border-transparent bg-slate-800 text-white"
                        : "border-slate-200 bg-slate-50 text-slate-600 hover:border-slate-300"}`}>
              <span aria-hidden>{ROW_STATE[k].glyph}</span>
              {ROW_STATE[k].word}
              <span className="tabular-nums opacity-70">{counts[k]}</span>
            </button>
          ))}
          {only && (
            <button onClick={() => setOnly(null)}
                    className="flex items-center gap-1 rounded-lg px-2 py-1 text-[11px]
                               font-semibold text-slate-500 hover:text-slate-800">
              <Icon name="close" className="w-3 h-3" /> Clear
            </button>
          )}
        </div>

        {checklist.profile.label && (
          <p className="mt-4 border-t border-slate-100 pt-3 text-[12px] leading-relaxed
                        text-slate-500">
            Rubric applied: <b className="text-slate-700">{checklist.profile.label}</b>
            {checklist.profile.provenance && ` — ${checklist.profile.provenance}`}
          </p>
        )}

        {t.not_run > 0 && (
          <p className="mt-3 flex gap-2 rounded-xl border border-blue-100 bg-blue-50 px-3 py-2
                        text-[12px] leading-relaxed text-slate-600">
            <Icon name="cpu" className="mt-px w-3.5 h-3.5 shrink-0 text-blue-500" />
            <span>
              <b className="text-slate-800">{t.not_run} checks were not run.</b> That is a gap
              in our coverage, not in the report, and it must not count against the
              submission. The rows say which, and why.
            </span>
          </p>
        )}
      </div>

      {families.length === 0 ? (
        <Empty title="No checks match that filter"
               hint="Clear the filter to see every check that ran." />
      ) : (
        families.map((fam) => (
          <FamilyBlock key={fam.key} fam={fam} activeKey={activeKey || ""} onOpen={onOpen} />
        ))
      )}

      <p className="px-2 mt-8 text-center text-[11px] font-medium uppercase tracking-widest text-slate-400">
        {checklist.advisory_notice}
      </p>
    </div>
  );
}
