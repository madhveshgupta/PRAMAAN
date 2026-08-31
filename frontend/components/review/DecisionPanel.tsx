"use client";
/** Appraisal and sanction, as two visibly separate acts.
 */
import { useState } from "react";

import { Chip, DPR_STATUS } from "@/components/ui/bits";
import { Icon } from "@/components/ui/Icon";
import { api, type Assessment, type DecisionPayload, type Session } from "@/lib/api";

const RECOMMENDATIONS = [
  ["recommend", "Recommend"],
  ["recommend_with_conditions", "Recommend with conditions"],
  ["return", "Return for revision"],
] as const;

const DECISIONS = [
  ["approved", "Approve"],
  ["approved_with_conditions", "Approve with conditions"],
  ["returned", "Return for revision"],
  ["rejected", "Reject"],
] as const;

function ConfirmSanction({ label, value, note, score, onCancel, onConfirm, busy }: {
  label: string; value: string; note: string; score: number | null;
  onCancel: () => void; onConfirm: () => void; busy: boolean;
}) {
  const destructive = value === "rejected" || value === "returned";
  return (
    <div className="fixed inset-0 z-50 grid place-items-center px-4 py-8 overflow-y-auto">
      <div onClick={onCancel}
           className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm animate-fade-in" />
      <div role="dialog" aria-modal="true" aria-label={label}
           className="relative w-full max-w-lg bg-white rounded-[24px] shadow-xl border border-slate-200 overflow-hidden animate-rise-in">
        <div className={`h-2 w-full ${destructive ? 'bg-rose-500' : 'bg-emerald-500'}`} />
        <div className="p-6 sm:p-8">
          <p className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Final sanction decision</p>
          <h3 className="mt-1 text-[24px] font-black text-slate-800">{label}</h3>

          <div className="mt-6 flex items-center gap-5 rounded-2xl border border-slate-200 bg-slate-50 p-5 shadow-sm">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Score</p>
              <p className="text-3xl font-black text-slate-800 tabular-nums leading-none mt-1">
                {score === null ? "—" : Math.round(score)}<span
                  className="text-base text-slate-400 font-bold">/100</span>
              </p>
            </div>
            <p className="text-[12px] text-slate-500 leading-relaxed border-l border-slate-200 pl-5">
              Advisory. The score measures how well the report evidences what it must
              contain — not whether the project is worth funding.
            </p>
          </div>

          <p className="mt-6 text-[11px] font-bold uppercase tracking-wider text-slate-400">Reason to be recorded</p>
          <p className="mt-1 text-[14px] text-slate-700 leading-relaxed whitespace-pre-wrap max-h-32 overflow-y-auto bg-white border border-slate-100 rounded-xl p-3 shadow-inner">
            {note}
          </p>

          <p className="mt-6 text-[11px] text-slate-500 leading-relaxed bg-slate-50 border border-slate-100 rounded-lg p-3">
            Sanctioning authority rests with the competent authority, and every decision
            recorded here names the officer who made it. The audit trail is append-only —
            this cannot be edited or withdrawn afterwards.
          </p>

          <div className="mt-8 flex gap-3">
            <button onClick={onCancel} disabled={busy}
                    className="flex-1 px-4 py-3 rounded-xl font-bold text-[14px] bg-white border border-slate-200 text-slate-600 hover:bg-slate-50 transition-colors">Cancel</button>
            <button onClick={onConfirm} disabled={busy}
                    className={`flex-1 px-4 py-3 rounded-xl font-bold text-[14px] text-white transition-colors shadow-md ${destructive
                      ? "bg-rose-600 hover:bg-rose-700" : "bg-emerald-600 hover:bg-emerald-700"}`}>
              {busy ? "Recording…" : `Confirm — ${label}`}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export function DecisionPanel({ dprId, session, assessment, decision, onDone }: {
  dprId: string; session: Session; assessment: Assessment | null;
  decision?: DecisionPayload | null; onDone: () => void;
}) {
  const [pending, setPending] = useState<{ value: string; label: string } | null>(null);
  const [recNote, setRecNote] = useState("");
  const [decNote, setDecNote] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  const ministry = session.role === "ministry";

  async function post(path: string, params: Record<string, string>, kind: string) {
    setBusy(kind); setMsg(null);
    try {
      await api(`${path}?${new URLSearchParams(params)}`, { method: "POST" });
      setMsg({ ok: true, text: "Recorded. This is now part of the audit trail." });
      onDone();
    } catch (e) {
      setMsg({ ok: false, text: (e as Error).message || "That was not accepted." });
    } finally {
      setBusy(null);
    }
  }

  if (!ministry) {
    const d = decision?.decision;
    return (
      <div className="bg-white rounded-[24px] shadow-sm border border-slate-200 p-6 sm:p-8">
        {!d ? (
          <div className="flex flex-col items-center justify-center text-center py-10">
            <div className="w-16 h-16 rounded-full bg-slate-50 flex items-center justify-center border border-slate-100 mb-4">
               <Icon name="clock" className="w-8 h-8 text-slate-400" />
            </div>
            <h3 className="text-[20px] font-bold text-slate-800">Not yet decided</h3>
            <p className="mt-2 text-[14px] text-slate-500 leading-relaxed max-w-md">
              Your report is with the ministry. When a decision is recorded it will appear
              here, together with the reason and the officer who made it.
            </p>
          </div>
        ) : (
          <div>
            <div className="flex flex-wrap items-center gap-3">
              <Chip meta={DPR_STATUS[decision!.status] ?? DPR_STATUS.draft} />
              <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider px-3 py-1.5 rounded-lg bg-slate-50 border border-slate-100">
                {new Date(d.at).toLocaleDateString("en-IN",
                  { day: "2-digit", month: "short", year: "numeric" })}
              </span>
            </div>
            {d.by && (
              <p className="mt-6 text-[12px] text-slate-500">
                Recorded by <span className="text-slate-800 font-bold bg-slate-50 px-2 py-0.5 rounded border border-slate-200">{d.by}</span>, ministry
              </p>
            )}
            <div className="mt-6 border-t border-slate-100 pt-6">
              <p className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Recorded Reason</p>
              <div className="mt-3 text-[14px] text-slate-700 leading-relaxed whitespace-pre-wrap bg-slate-50 border border-slate-100 rounded-xl p-4 shadow-inner">
                {d.reason}
              </div>
            </div>
            <p className="mt-6 text-[11px] font-bold text-slate-400 leading-relaxed flex items-center gap-2">
              <Icon name="lock" className="w-3.5 h-3.5" />
              Every decision names the officer who made it and carries a recorded reason. This record cannot be edited or withdrawn.
            </p>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {pending && (
        <ConfirmSanction
          label={pending.label} value={pending.value} note={decNote}
          score={assessment?.overall_score ?? null} busy={busy !== null}
          onCancel={() => setPending(null)}
          onConfirm={() => {
            const p = pending;
            setPending(null);
            void post(`/dprs/${dprId}/decision`, { decision: p.value, note: decNote }, p.value);
          }} />
      )}

      {msg && (
        <div role="status"
             className={`flex items-center gap-3 px-4 py-3 rounded-xl font-bold text-[13px] border shadow-sm ${msg.ok
               ? "bg-emerald-50 text-emerald-700 border-emerald-200"
               : "bg-rose-50 text-rose-700 border-rose-200"}`}>
          <Icon name={msg.ok ? "check" : "ban"} className={`w-5 h-5 ${msg.ok ? "text-emerald-500" : "text-rose-500"}`} />
          {msg.text}
        </div>
      )}

      {/* 1 — appraisal */}
      <section className="bg-white rounded-[24px] shadow-sm border border-slate-200 p-6 sm:p-8 relative overflow-hidden">
        <div className="flex items-start gap-4">
           <div className="w-12 h-12 rounded-2xl bg-blue-50 border border-blue-100 flex items-center justify-center shrink-0">
             <span className="text-blue-500 font-black text-xl">1</span>
           </div>
           <div>
              <h3 className="text-[18px] font-bold text-slate-800 mt-1">Appraisal recommendation</h3>
              <p className="mt-1 text-[13px] text-slate-500 leading-relaxed">
                Your professional view on the report, recorded separately from the sanction below — appraising and deciding are different acts.
              </p>
           </div>
        </div>
        <div className="mt-6 pl-0 sm:pl-16">
          <textarea value={recNote} onChange={(e) => setRecNote(e.target.value)}
                    rows={3} placeholder="Reasoning (optional)"
                    className="w-full rounded-xl border border-slate-300 p-4 text-[14px] text-slate-700 focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none transition-all shadow-sm resize-y" />
          <div className="mt-4 flex flex-wrap gap-3">
            {RECOMMENDATIONS.map(([value, label]) => (
              <button key={value} disabled={busy !== null}
                      onClick={() => post(`/dprs/${dprId}/recommendation`,
                        { recommendation: value, ...(recNote ? { note: recNote } : {}) },
                        value)}
                      className="px-4 py-2 rounded-xl text-[13px] font-bold bg-white border border-slate-200 text-slate-600 hover:bg-slate-50 hover:text-blue-600 hover:border-blue-200 transition-all shadow-sm disabled:opacity-50">
                {busy === value ? "Recording…" : label}
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* 2 — sanction */}
      <section className="bg-white rounded-[24px] shadow-sm border border-slate-200 p-6 sm:p-8 relative overflow-hidden">
        <div className="flex items-start gap-4">
           <div className="w-12 h-12 rounded-2xl bg-indigo-50 border border-indigo-100 flex items-center justify-center shrink-0">
             <span className="text-indigo-500 font-black text-xl">2</span>
           </div>
           <div>
              <h3 className="text-[18px] font-bold text-slate-800 mt-1">Sanction decision</h3>
              <p className="mt-1 text-[13px] text-slate-500 leading-relaxed">
                The binding act. A recorded reason is required, and the decision names you in the audit trail permanently.
              </p>
           </div>
        </div>

        <div className="mt-6 pl-0 sm:pl-16">
          <textarea value={decNote} onChange={(e) => setDecNote(e.target.value)}
                    rows={3} required
                    placeholder="Recorded reason (required)"
                    className="w-full rounded-xl border border-slate-300 p-4 text-[14px] text-slate-700 focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none transition-all shadow-sm resize-y" />
          <div className="mt-4 flex flex-wrap gap-3">
            {DECISIONS.map(([value, label]) => (
              <button key={value}
                      disabled={!decNote.trim() || busy !== null}
                      onClick={() => setPending({ value, label })}
                      className={`px-4 py-2 rounded-xl text-[13px] font-bold transition-all shadow-sm disabled:opacity-50 ${value === "rejected"
                        ? "bg-white border border-rose-200 text-rose-600 hover:bg-rose-50 hover:border-rose-300"
                        : "bg-white border border-slate-200 text-slate-600 hover:bg-slate-50 hover:border-indigo-200 hover:text-indigo-600"}`}>
                {busy === value ? "Recording…" : label}
              </button>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
