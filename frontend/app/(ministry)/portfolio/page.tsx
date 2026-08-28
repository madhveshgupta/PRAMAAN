"use client";
/** Cross-project analytics — the screen that argues this is worth having at scale.
 *
 *  A ministry with forty proposals and a fixed budget does not need forty scores, it needs
 *  an order. So the table is ranked, and every column that feeds the ranking is shown
 *  beside it: an order you cannot decompose is an order nobody will defend in a meeting.
 */
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { QualityRiskScatter } from "@/components/charts/Figures";
import { SEVERITY_RAMP } from "@/components/charts/palette";
import { AppShell, RailCard } from "@/components/layout/AppShell";
import { Empty, ScoreBadge, TableSkeleton } from "@/components/ui/bits";
import { Icon } from "@/components/ui/Icon";
import { useReveal } from "@/lib/motion";
import { api } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth";

interface Row {
  id: string; title: string; status: string;
  quality_score: number | null; delay_probability: number | null;
  composite: number | null; critical_findings: number;
  p80_cost_cr: number | null; peer_count: number | null;
  check_tally?: Record<string, number> | null;
}

type SortKey = "composite" | "quality_score" | "delay_probability" | "critical_findings"
             | "p80_cost_cr";

export default function PortfolioPage() {
  const { session, ready } = useRequireAuth(["ministry"]);
  const router = useRouter();
  const [rows, setRows] = useState<Row[]>([]);
  const [loading, setLoading] = useState(true);
  const [sort, setSort] = useState<SortKey>("composite");
  const [desc, setDesc] = useState(false);
  const reveal = useReveal<HTMLDivElement>({ immediate: true, deps: [loading] });

  useEffect(() => {
    if (!ready || !session) return;
    api<Row[]>("/portfolio").then((r) => { setRows(r); setLoading(false); })
                            .catch(() => setLoading(false));
  }, [ready, session]);

  const sorted = useMemo(() => {
    const dir = desc ? -1 : 1;
    return [...rows].sort((a, b) => {
      const x = a[sort], y = b[sort];
      // Nulls always sink, whichever way the column is pointing: a project we could not
      // measure is not the best one and it is not the worst one either.
      if (x == null && y == null) return 0;
      if (x == null) return 1;
      if (y == null) return -1;
      return (x - y) * dir;
    });
  }, [rows, sort, desc]);

  const totalP80 = rows.reduce((s, r) => s + (r.p80_cost_cr ?? 0), 0);
  const withRange = rows.filter((r) => r.p80_cost_cr != null).length;

  if (!ready || !session) return null;

  const head = (key: SortKey, label: string, hint?: string) => (
    <th className={`py-2.5 pr-4 text-right font-semibold ${
      sort === key ? "text-brand" : ""}`}>
      <button onClick={() => { sort === key ? setDesc((d) => !d) : setSort(key); }}
              title={hint}
              className="inline-flex items-center gap-1 transition-colors hover:text-brand">
        {label}
        <Icon name="chevronDown"
              className={`w-3 h-3 transition-transform ${
                sort !== key ? "opacity-25" : desc ? "" : "rotate-180"}`} />
      </button>
    </th>
  );

  const rail = (
    <>
      <RailCard title="Reading this ranking">
        <p className="text-2xs leading-relaxed text-ink-soft">
          Composite is <b className="text-ink">50% quality and 50% inverse delay risk</b>.
          That weighting is configurable and currently unjustified beyond being an even
          split — treat the ordering as a starting point for a discussion, not as an
          allocation.
        </p>
        <p className="mt-2.5 border-t border-paper-edge pt-2.5 text-2xs leading-relaxed
                      text-ink-soft">
          Projected costs are read from what actually happened to comparable completed
          projects. Every one is shown with the number of projects it rests on, because a
          range over 38 projects means less than one over 342.
        </p>
      </RailCard>

      {withRange > 0 && (
        <RailCard title="Committed at P80">
          <p className="display text-2xl font-bold tabular-nums text-ink">
            ₹{totalP80.toLocaleString("en-IN", { maximumFractionDigits: 0 })}
            <span className="ml-1 text-sm font-normal text-ink-faint">Cr</span>
          </p>
          <p className="mt-1 text-2xs leading-relaxed text-ink-faint">
            The sum of the P80 outcome for the {withRange} report{withRange === 1 ? "" : "s"}
            {" "}that have a comparable-project range. It is the figure four in five similar
            projects came in at or below — not a budget, and not the sum of what was asked for.
          </p>
        </RailCard>
      )}

      {rows.length >= 2 && (
        <RailCard title="Quality against risk">
          <QualityRiskScatter rows={rows} onPick={(id) => router.push(`/review/${id}`)} />
        </RailCard>
      )}
    </>
  );

  return (
    <AppShell title="Portfolio"
              subtitle="Every live report, ranked by quality-adjusted risk."
              rail={rail}>
      <div ref={reveal} data-reveal className="card overflow-hidden shadow-card">
        {loading ? (
          <div className="p-4"><TableSkeleton rows={6} cols={7} /></div>
        ) : rows.length === 0 ? (
          <Empty title="No reports to rank yet"
                 hint="A report joins the ranking once it has been assessed." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-paper-edge text-left text-2xs uppercase
                               tracking-wide text-ink-faint">
                  <th className="w-10 py-2.5 pl-4 pr-3 font-semibold">#</th>
                  <th className="py-2.5 pr-4 font-semibold">Project</th>
                  {head("composite", "Composite", "50% quality, 50% inverse delay risk")}
                  {head("quality_score", "Quality")}
                  {head("delay_probability", "Delay risk")}
                  {head("critical_findings", "Critical")}
                  {head("p80_cost_cr", "P80 outcome")}
                </tr>
              </thead>
              <tbody>
                {sorted.map((r, i) => (
                  <tr key={r.id} onClick={() => router.push(`/review/${r.id}`)}
                      className="row-link group border-b border-paper-edge/60 last:border-0">
                    <td className="py-3 pl-4 pr-3 tabular-nums text-ink-ghost">{i + 1}</td>
                    <td className="py-3 pr-4">
                      <span className="font-medium text-brand group-hover:underline">
                        {r.title}
                      </span>
                    </td>
                    <td className="py-3 pr-4 text-right">
                      {r.composite == null ? <span className="text-ink-ghost">—</span> : (
                        <span className="inline-flex items-center gap-2">
                          <span aria-hidden className="h-1.5 w-10 overflow-hidden rounded-full
                                                       bg-paper-edge">
                            <span className="block h-full rounded-full"
                                  style={{ width: `${r.composite}%`,
                                           background: SEVERITY_RAMP.high }} />
                          </span>
                          <span className="tabular-nums font-semibold">{r.composite}</span>
                        </span>
                      )}
                    </td>
                    <td className="py-3 pr-4 text-right">
                      <ScoreBadge score={r.quality_score} />
                    </td>
                    <td className="py-3 pr-4 text-right tabular-nums text-ink-soft">
                      {r.delay_probability == null
                        ? "—" : `${Math.round(r.delay_probability * 100)}%`}
                    </td>
                    <td className="py-3 pr-4 text-right tabular-nums">
                      {r.critical_findings > 0
                        ? <span className="font-semibold text-sev-critical">
                            {r.critical_findings}
                          </span>
                        : <span className="text-ink-ghost">0</span>}
                    </td>
                    <td className="py-3 pr-4 text-right tabular-nums">
                      {r.p80_cost_cr == null ? <span className="text-ink-ghost">—</span> : (
                        <>
                          <span className="font-medium">
                            ₹{r.p80_cost_cr.toLocaleString("en-IN")} Cr
                          </span>
                          <span className="block text-2xs text-ink-faint">
                            80% of {r.peer_count} comparable projects
                          </span>
                        </>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </AppShell>
  );
}
