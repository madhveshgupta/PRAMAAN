"use client";
/**
 * One finding, elaborated (Checklist Timeline UI).
 */
import { useState } from "react";

import { Chip, SEVERITY_META, STATUS_META } from "@/components/ui/bits";
import { Icon } from "@/components/ui/Icon";
import { ConfidenceMeter } from "@/components/charts/Figures";
import { EvidenceRoute } from "./EvidenceRoute";
import { ACTOR_WORD, categoryMeta, SEVERITY_SENTENCE, STATUS_SENTENCE } from "./glossary";
import type { Finding } from "@/lib/api";

const RAIL_BORDER: Record<string, string> = {
  critical: "border-l-rose-600", high: "border-l-orange-500", medium: "border-l-amber-500",
  low: "border-l-blue-400", info: "border-l-slate-400",
};

const SEV_BG: Record<string, string> = {
  critical: "bg-rose-50 text-rose-600", high: "bg-orange-50 text-orange-600", medium: "bg-amber-50 text-amber-600",
  low: "bg-blue-50 text-blue-600", info: "bg-slate-50 text-slate-600",
};

function ReviewNote({ decision, onCancel, onSubmit }: {
  decision: "rejected" | "amended";
  onCancel: () => void;
  onSubmit: (note: string) => void;
}) {
  const [note, setNote] = useState("");
  const word = decision === "rejected" ? "setting aside" : "amending";
  return (
    <form onSubmit={(e) => { e.preventDefault(); if (note.trim()) onSubmit(note.trim()); }}
          className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4 shadow-sm animate-sweep-in">
      <label className="block text-xs font-bold uppercase tracking-wider text-slate-600">
        Why are you {word} this finding?
      </label>
      <p className="mt-1 text-[11px] leading-relaxed text-slate-500">
        Recorded against your name in the audit trail, and printed in the appraisal note
        beside the finding. It cannot be edited afterwards.
      </p>
      <textarea value={note} onChange={(e) => setNote(e.target.value)} rows={2} autoFocus
                className="w-full mt-3 rounded-lg border border-slate-300 p-2.5 text-[13px] focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none" placeholder="Reason (required)" />
      <div className="mt-3 flex gap-2">
        <button type="button" onClick={onCancel} className="px-3 py-1.5 rounded-lg text-xs font-semibold text-slate-600 hover:bg-slate-200 transition-colors">Cancel</button>
        <button type="submit" disabled={!note.trim()} className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-blue-600 text-white disabled:opacity-50 hover:bg-blue-700 transition-colors">
          Record
        </button>
      </div>
    </form>
  );
}

export function FindingCard({
  finding, index, active, anchorIndex, onSelect, onOpenEvidence, onReview, canReview, expanded,
}: {
  finding: Finding;
  index: number;
  active: boolean;
  anchorIndex: number;
  onSelect: () => void;
  onOpenEvidence: (index: number) => void;
  onReview: (decision: "accepted" | "rejected" | "amended", note?: string) => void;
  canReview: boolean;
  expanded?: boolean;
}) {
  const [why, setWhy] = useState(Boolean(expanded));
  const [noting, setNoting] = useState<"rejected" | "amended" | null>(null);

  const sev = SEVERITY_META[finding.severity] ?? SEVERITY_META.info;
  const status = STATUS_META[finding.status];
  const cat = categoryMeta(finding.category);
  const isDataQuality = finding.category === "data_quality";
  const borderClass = RAIL_BORDER[finding.severity] || "border-l-slate-400";
  const bgClass = SEV_BG[finding.severity] || "bg-slate-50 text-slate-600";

  return (
    <div id={`finding-${finding.id}`} className="relative flex items-start gap-3 sm:gap-4 z-10 group mb-1">
      {/* Timeline Circle */}
      <div className={`mt-5 w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm shadow-sm ring-1 ring-slate-200 z-10 shrink-0 transition-colors ${
        active ? 'bg-blue-500 text-white border-blue-500' : 'bg-white text-slate-400 group-hover:text-slate-600'
      }`}>
        {index}
      </div>

      <article className={`flex-1 bg-white border border-slate-200 border-l-[4px] rounded-xl p-4 sm:p-5 shadow-[0_2px_10px_rgb(0,0,0,0.02)] flex flex-col transition-all duration-300 ${borderClass} ${
        active ? 'ring-2 ring-blue-500/20 shadow-md' : 'hover:shadow-md'
      }`}>
        <button onClick={onSelect} aria-pressed={active} className="block w-full text-left focus:outline-none">
          <div className="flex flex-wrap items-center gap-2 mb-3">
            <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded ${bgClass}`}>
              {sev.label}
            </span>
            {status && (
              <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200">
                {status.label}
              </span>
            )}
            <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200">
              {cat.label}
            </span>
            {isDataQuality && (
              <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-amber-50 text-amber-700 border border-amber-200" title="This is about our reading of the document, not a defect in the project">
                ⊘ our reading, not a defect
              </span>
            )}
            {finding.match_status === "auto" && finding.match_confidence !== null && (
              <span className="ml-auto flex items-center gap-1.5 text-[10px] font-bold text-blue-600 bg-blue-50 px-2 py-0.5 rounded border border-blue-100">
                <Icon name="shield" className="w-3 h-3" /> Auto Match
              </span>
            )}
          </div>

          <h3 className="font-bold text-slate-800 text-[16px] leading-snug">
            {finding.title}
          </h3>

          <p className="mt-2 text-[14px] leading-relaxed text-slate-600 max-w-4xl">
            {finding.message}
          </p>

          <p className="mt-2 text-[11px] font-medium text-slate-400 flex items-center gap-1.5">
            <Icon name="help" className="w-3.5 h-3.5" />
            {/* Two different statements, and running them together produced "Look at this
                before the file moves. Something was found that an officer should look at
                directly." — the same sentence twice. The severity says how much attention
                this deserves; the status is only worth adding when it says something the
                severity does not. */}
            {SEVERITY_SENTENCE[finding.severity]}
            {finding.status === "insufficient_evidence" && (
              <span className="block mt-0.5">{STATUS_SENTENCE.insufficient_evidence}</span>
            )}
          </p>
        </button>

        {/* Why it matters */}
        <div className="mt-4 border-t border-slate-100 pt-3">
          <button type="button" onClick={() => setWhy((v) => !v)} aria-expanded={why}
                  className="flex items-center gap-1.5 rounded py-1 text-[11px] font-semibold text-blue-600 transition-colors hover:text-blue-700">
            <Icon name="chevronDown"
                  className={`w-3.5 h-3.5 transition-transform duration-200 ${why ? "rotate-180" : ""}`} />
            {why ? "Hide Details" : "What is this check, and who acts on it?"}
          </button>

          {why && (
            <div className="mt-3 grid gap-3 rounded-xl border border-slate-100 bg-slate-50/50 p-4 animate-sweep-in sm:grid-cols-2">
              <div>
                <dt className="text-[10px] font-bold uppercase tracking-wider text-slate-500">What this looks for</dt>
                <dd className="mt-1 text-[12px] leading-relaxed text-slate-700">{cat.what}</dd>
              </div>
              <div>
                <dt className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Why an appraisal cares</dt>
                <dd className="mt-1 text-[12px] leading-relaxed text-slate-700">{cat.why}</dd>
              </div>
              <div className="col-span-1 sm:col-span-2 flex items-center gap-2 border-t border-slate-200/60 pt-3 mt-1">
                <Icon name={cat.actor === "system" ? "cpu" : cat.actor === "ministry" ? "shield" : "users"}
                      className="w-4 h-4 shrink-0 text-slate-400" />
                <span className="text-[12px] font-bold text-slate-600">{ACTOR_WORD[cat.actor]}</span>
                <span className="ml-auto font-mono text-[10px] bg-white border border-slate-200 px-2 py-0.5 rounded text-slate-400">
                  {finding.rule_id}
                </span>
              </div>
            </div>
          )}
        </div>

        {/* What to do */}
        {finding.suggested_action && (
          <div className="mt-3 flex gap-3 rounded-xl border border-blue-100 bg-blue-50/50 px-4 py-3">
            <Icon name="arrow" className="mt-0.5 w-4 h-4 shrink-0 text-blue-500" />
            <p className="text-[13px] leading-relaxed text-blue-900">
              <span className="font-bold">Suggested Action — </span>
              {finding.suggested_action}
            </p>
          </div>
        )}

        {/* Evidence Link */}
        <div className="mt-4 bg-slate-50 rounded-xl p-2 border border-slate-100">
          <EvidenceRoute evidence={finding.evidence}
                         activeIndex={active ? anchorIndex : null}
                         onOpen={onOpenEvidence} />
        </div>

        {/* Officer's mark */}
        {(canReview || finding.review) && (
          <div className="mt-4 pt-4 border-t border-slate-200 flex flex-wrap items-center justify-between gap-4">
            {finding.review ? (
              <div className="flex items-start gap-2.5 bg-emerald-50 text-emerald-800 px-4 py-2.5 rounded-xl border border-emerald-100 w-full sm:w-auto">
                <Icon name="check" className="mt-0.5 w-4 h-4 shrink-0 text-emerald-600" />
                <span className="text-[12px] leading-snug">
                  <b className="capitalize font-bold">{finding.review.decision}</b> by the reviewing officer
                  {finding.review.note && <> — “<span className="italic">{finding.review.note}</span>”</>}
                  <span className="block mt-1 text-[10px] font-semibold text-emerald-600/70 uppercase tracking-wide">
                    {new Date(finding.review.at).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" })}
                  </span>
                </span>
              </div>
            ) : noting ? (
              <div className="w-full">
                <ReviewNote decision={noting} onCancel={() => setNoting(null)}
                            onSubmit={(note) => { onReview(noting, note); setNoting(null); }} />
              </div>
            ) : (
              <div className="flex flex-wrap items-center gap-2 w-full">
                <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider mr-2">Your Review:</span>
                <button onClick={() => onReview("accepted")}
                        className="px-4 py-1.5 rounded-lg text-[12px] font-bold bg-white border border-emerald-200 text-emerald-600 hover:bg-emerald-50 transition-colors shadow-sm">
                  Accept
                </button>
                <button onClick={() => setNoting("amended")}
                        className="px-4 py-1.5 rounded-lg text-[12px] font-bold bg-white border border-amber-200 text-amber-600 hover:bg-amber-50 transition-colors shadow-sm">
                  Amend
                </button>
                <button onClick={() => setNoting("rejected")}
                        className="px-4 py-1.5 rounded-lg text-[12px] font-bold bg-white border border-rose-200 text-rose-600 hover:bg-rose-50 transition-colors shadow-sm">
                  Set Aside
                </button>
              </div>
            )}
          </div>
        )}
      </article>
    </div>
  );
}
