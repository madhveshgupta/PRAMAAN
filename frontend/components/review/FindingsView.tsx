"use client";
/**
 * Findings, as a page rather than as a rail (Checklist Timeline UI).
 */
import { useMemo, useState } from "react";

import { SeverityBars } from "@/components/charts/Figures";
import { Empty } from "@/components/ui/bits";
import { Icon } from "@/components/ui/Icon";
import { useReveal } from "@/lib/motion";
import { FindingCard } from "./FindingCard";
import { categoryMeta } from "./glossary";
import type { ViewProps } from "./types";
import type { Finding } from "@/lib/api";

const ORDER = ["critical", "high", "medium", "low", "info"];
const LABEL: Record<string, string> = {
  critical: "Critical", high: "High", medium: "Medium", low: "Low", info: "Note",
};

function SeverityBlock({ severity, list, onOpen, activeKey, activeIndex, onReview, canReview }: {
  severity: string;
  list: Finding[];
  onOpen: (ev: any, sev: string, idx: number, id: string) => void;
  activeKey?: string | null;
  activeIndex?: number;
  onReview: (f: Finding, decision: "accepted" | "rejected" | "amended", note?: string) => void;
  canReview: boolean;
}) {
  const isCritical = severity === "critical" || severity === "high";
  const done = list.filter((f) => f.review).length;
  const total = list.length;
  const pct = Math.round((total > 0 ? done / total : 0) * 100);

  const colorClass = severity === "critical" ? "text-rose-500 bg-rose-50" : severity === "high" ? "text-orange-500 bg-orange-50" : severity === "medium" ? "text-amber-500 bg-amber-50" : "text-blue-500 bg-blue-50";
  const barClass = severity === "critical" ? "bg-rose-500" : severity === "high" ? "bg-orange-500" : severity === "medium" ? "bg-amber-500" : "bg-blue-500";
  const barBgClass = severity === "critical" ? "bg-rose-100" : severity === "high" ? "bg-orange-100" : severity === "medium" ? "bg-amber-100" : "bg-blue-100";

  return (
    <div className="mb-10 relative" data-reveal>
      <div className="bg-white rounded-[24px] shadow-sm border border-slate-200 p-6 mb-6">
        <div className="flex flex-col xl:flex-row items-start xl:items-center justify-between gap-6">
          
          <div className="flex items-center gap-5">
            <div className={`w-20 h-20 rounded-full flex items-center justify-center shrink-0 ${colorClass}`}>
              <Icon name={isCritical ? "flag" : "list"} className="w-10 h-10" />
            </div>
            <div>
              <h2 className="text-[22px] font-bold text-slate-800 tracking-tight leading-tight">{LABEL[severity]} Priority</h2>
              <p className="text-slate-500 font-bold mt-1 text-sm">{total} items require attention</p>
            </div>
          </div>

          <div className="flex items-center gap-3 flex-wrap">
            <div className="bg-slate-50/80 rounded-2xl p-3 border border-slate-100 flex items-center gap-3 min-w-[140px]">
              <div className="bg-white p-2 rounded-xl shadow-sm border border-slate-100"><Icon name="trend" className="w-5 h-5 text-blue-500" /></div>
              <div>
                <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Reviewed</div>
                <div className="text-lg font-black text-blue-600 leading-none mt-1">{pct}%</div>
              </div>
            </div>
            
            <div className="bg-slate-50/80 rounded-2xl p-3 border border-slate-100 flex items-center gap-3 min-w-[140px]">
              <div className="bg-white p-2 rounded-xl shadow-sm border border-slate-100"><Icon name="docCheck" className="w-5 h-5 text-emerald-500" /></div>
              <div>
                <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Completed</div>
                <div className="text-lg font-black text-emerald-600 leading-none mt-1">{done} <span className="text-sm text-slate-400 font-semibold">/ {total}</span></div>
              </div>
            </div>
          </div>
        </div>

        <div className="mt-6 flex items-center gap-4">
          <div className={`flex-1 h-2.5 rounded-full overflow-hidden ${barBgClass}`}>
            <div className={`h-full rounded-full transition-all duration-1000 ease-out ${barClass}`} style={{ width: `${pct}%` }}></div>
          </div>
          <span className="font-bold text-slate-700 text-sm tracking-tight">{pct}%</span>
        </div>
      </div>

      <div className="relative pl-0 sm:pl-6 pb-2">
        <div className="hidden sm:block absolute left-[39px] top-6 bottom-4 w-[2px] bg-slate-200 z-0" />
        <div className="flex flex-col gap-4">
          {list.map((f, idx) => (
             <FindingCard key={f.id} finding={f} index={idx + 1}
                          active={activeKey === f.id}
                          anchorIndex={activeKey === f.id ? (activeIndex || 0) : 0}
                          onSelect={() => onOpen(f.evidence, f.severity, 0, f.id)}
                          onOpenEvidence={(i) => onOpen(f.evidence, f.severity, i, f.id)}
                          onReview={(d, note) => onReview(f, d, note)}
                          canReview={canReview} />
          ))}
        </div>
      </div>
    </div>
  );
}

export function FindingsView({
  findings, loading, onOpen, activeKey, activeIndex = 0, canReview, onReview,
}: ViewProps & {
  findings: Finding[];
  loading: boolean;
  canReview: boolean;
  onReview: (f: Finding, decision: "accepted" | "rejected" | "amended", note?: string) => void;
}) {
  const [sev, setSev] = useState<string | null>(null);
  const [cat, setCat] = useState<string | null>(null);
  const [q, setQ] = useState("");
  const [openOnly, setOpenOnly] = useState(false);

  const counts = useMemo(() => {
    const by: Record<string, number> = {};
    for (const f of findings) by[f.severity] = (by[f.severity] ?? 0) + 1;
    return by;
  }, [findings]);

  const categories = useMemo(() => {
    const by: Record<string, number> = {};
    for (const f of findings) by[f.category] = (by[f.category] ?? 0) + 1;
    return Object.entries(by).sort((a, b) => b[1] - a[1]);
  }, [findings]);

  const shown = useMemo(() => {
    let out = findings;
    if (sev) out = out.filter((f) => f.severity === sev);
    if (cat) out = out.filter((f) => f.category === cat);
    if (openOnly) out = out.filter((f) => !f.review);
    if (q.trim()) {
      const needle = q.toLowerCase();
      out = out.filter((f) =>
        f.title.toLowerCase().includes(needle) || f.message.toLowerCase().includes(needle));
    }
    return [...out].sort(
      (a, b) => ORDER.indexOf(a.severity) - ORDER.indexOf(b.severity));
  }, [findings, sev, cat, q, openOnly]);

  const grouped = useMemo(() => {
    const by: Record<string, Finding[]> = {};
    for (const f of shown) (by[f.severity] ??= []).push(f);
    return ORDER.filter((s) => by[s]?.length).map((s) => [s, by[s]] as const);
  }, [shown]);

  const reveal = useReveal<HTMLDivElement>({ immediate: true, deps: [loading, shown.length] });
  const filtered = Boolean(sev || cat || q.trim() || openOnly);
  const reviewed = findings.filter((f) => f.review).length;

  if (loading) {
    return (
      <div className="space-y-3">
        {[0, 1, 2, 3].map((i) => <div key={i} className="skeleton h-40 rounded-card" />)}
      </div>
    );
  }

  if (findings.length === 0) {
    return (
      <Empty title="No findings were raised"
             hint="That is a statement about this document, not about how much was checked —
                   the checklist shows every rule that ran, including the ones this report
                   satisfied. If the report has only just been uploaded, it may not have
                   finished processing." />
    );
  }

  return (
    <div ref={reveal} className="space-y-4">
      {/* --- the shape of the findings, before the list of them ---------------------- */}
      <section data-reveal className="bg-white rounded-[20px] shadow-sm border border-slate-200 p-5 sm:p-6 mb-8">
        <div className="grid gap-6 sm:grid-cols-[minmax(0,16rem)_minmax(0,1fr)]">
          <SeverityBars counts={counts} onPick={(s) => setSev(sev === s ? null : s)}
                        active={sev}
                        title="Findings by severity"
                        hint="Click a band to filter the list. Severity is an ordering of how
                              much attention a finding deserves — never a ruling." />
          <div className="space-y-3 border-t border-slate-100 pt-5 sm:border-l sm:border-t-0 sm:pl-6 sm:pt-0">
            <p className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
              By check family
            </p>
            <ul className="flex flex-wrap gap-2">
              {categories.map(([k, n]) => (
                <li key={k}>
                  <button onClick={() => setCat(cat === k ? null : k)}
                          aria-pressed={cat === k}
                          title={categoryMeta(k).what}
                          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12px] font-bold transition-colors ${cat === k
                            ? "border-transparent bg-blue-600 text-white shadow-sm"
                            : "border border-slate-200 bg-slate-50 text-slate-600 hover:border-blue-300 hover:text-blue-600"}`}>
                    {categoryMeta(k).label}
                    <span className={`px-1.5 py-0.5 rounded-md text-[10px] ${cat === k ? "bg-white/20 text-white" : "bg-slate-200 text-slate-500"}`}>{n}</span>
                  </button>
                </li>
              ))}
            </ul>
            {canReview && (
              <p className="pt-2 text-[12px] leading-relaxed text-slate-500 max-w-xl">
                <b className="text-slate-700 font-bold tabular-nums">{reviewed} of {findings.length}</b>{" "}
                carry your view. Accepting a finding records that you agree with it; setting
                one aside records that you do not, and why.
              </p>
            )}
          </div>
        </div>
      </section>

      {/* --- filters ----------------------------------------------------------------- */}
      <div data-reveal className="no-print flex flex-wrap items-center gap-3 mb-6">
        <div className="relative min-w-[14rem] flex-1 max-w-sm">
          <Icon name="search"
                className="pointer-events-none absolute left-3.5 top-1/2 w-4 h-4 -translate-y-1/2
                           text-slate-400" />
          <input value={q} onChange={(e) => setQ(e.target.value)}
                 aria-label="Search findings"
                 placeholder="Search these findings..."
                 className="w-full bg-white border border-slate-200 rounded-xl py-2 pl-10 pr-4 text-[13px] font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all shadow-sm" />
        </div>
        {canReview && (
          <button onClick={() => setOpenOnly((v) => !v)} aria-pressed={openOnly}
                  className={`flex items-center gap-2 px-3 py-2 rounded-xl text-[12px] font-bold transition-all shadow-sm ${openOnly
                    ? "border-transparent bg-blue-50 text-blue-600 ring-1 ring-blue-500/30" 
                    : "border border-slate-200 bg-white text-slate-600 hover:bg-slate-50"}`}>
            <Icon name="filter" className="w-4 h-4" />
            Needs Review
          </button>
        )}
        {filtered && (
          <button onClick={() => { setSev(null); setCat(null); setQ(""); setOpenOnly(false); }}
                  className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-[12px] font-bold text-slate-500 hover:text-slate-700 hover:bg-slate-100 transition-colors">
            <Icon name="close" className="w-4 h-4" /> Clear
          </button>
        )}
        <span className="ml-auto text-[11px] font-bold uppercase tracking-wider tabular-nums text-slate-400 bg-slate-100 px-3 py-1.5 rounded-lg border border-slate-200">
          Showing {shown.length} / {findings.length}
        </span>
      </div>

      {/* --- the list ---------------------------------------------------------------- */}
      {shown.length === 0 ? (
        <Empty title="Nothing matches these filters"
               hint="Clear the filters to see all findings for this report." />
      ) : (
        grouped.map(([s, list]) => (
          <SeverityBlock key={s} severity={s} list={list} onOpen={onOpen} activeKey={activeKey} activeIndex={activeIndex} onReview={onReview} canReview={canReview} />
        ))
      )}
    </div>
  );
}
