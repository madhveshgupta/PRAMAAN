"use client";
/** The ministry overview.
 *
 *  Everything here is computed from data the system already holds — workflow state,
 *  findings, checklist tallies, and peer-based cost ranges. Deliberately absent: physical
 *  progress, budget burn, and any schedule timeline. PRAMAAN appraises a report before the
 *  project starts, so it holds no milestone or expenditure data, and drawing one would be
 *  inventing the most important number on the page (invariant 13).
 *
 *  The same rule kills every "vs last month" on this screen. The system keeps no history of
 *  its own throughput, so a delta would be drawn from nothing. Where a figure needs
 *  context, it is given a stated BASIS instead — "across 24 assessed reports" — which is a
 *  fact rather than a trend.
 */
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { QualityRiskScatter, SeverityBars, StatusStack } from "@/components/charts/Figures";
import { AppShell, RailCard, RailStat } from "@/components/layout/AppShell";
import { Empty } from "@/components/ui/bits";
import { Icon } from "@/components/ui/Icon";
import { StatStrip, type Stat } from "@/components/ui/StatStrip";
import { useReveal } from "@/lib/motion";
import { api, type DprRow } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth";

interface PortfolioRow {
  id: string; title: string; status: string;
  quality_score: number | null; delay_probability: number | null;
  composite: number | null; critical_findings: number;
  p80_cost_cr: number | null; peer_count: number | null;
  /** Null for a report assessed before the checklist existed — not an empty tally. */
  check_tally: Record<string, number> | null;
}

function Panel({ title, hint, children, action, className = "" }: {
  title: string; hint?: string; children: React.ReactNode;
  action?: React.ReactNode; className?: string;
}) {
  return (
    <section data-reveal className={`card p-5 shadow-card ${className}`}>
      <div className="flex items-start gap-3">
        <div className="min-w-0">
          <h2 className="display text-sm font-bold text-ink">{title}</h2>
          {hint && (
            <p className="mt-0.5 max-w-prose text-2xs leading-relaxed text-ink-faint">{hint}</p>
          )}
        </div>
        {action && <div className="ml-auto shrink-0 no-print">{action}</div>}
      </div>
      <div className="mt-4">{children}</div>
    </section>
  );
}

export default function DashboardPage() {
  const { session, ready } = useRequireAuth(["ministry"]);
  const router = useRouter();
  const [rows, setRows] = useState<PortfolioRow[]>([]);
  const [dprs, setDprs] = useState<DprRow[]>([]);
  const [tally, setTally] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);
  const reveal = useReveal<HTMLDivElement>({ immediate: true, deps: [loading] });

  useEffect(() => {
    if (!ready || !session) return;
    void (async () => {
      try {
        const [p, d] = await Promise.all([
          api<PortfolioRow[]>("/portfolio"), api<DprRow[]>("/dprs"),
        ]);
        setRows(p); setDprs(d);

        // Summed from the portfolio payload, which now carries each report's tally. This
        // used to fan out one `/checklist` request per report from the browser — forty
        // reports, forty requests, each one rebuilding a full checklist server-side to have
        // five integers read off it.
        //
        // Reports with no tally are SKIPPED rather than counted as zero: a report assessed
        // before the checklist existed is one we have no record for, not one that passed
        // nothing.
        const totals: Record<string, number> = {};
        for (const r of p) {
          if (!r.check_tally) continue;
          for (const [k, v] of Object.entries(r.check_tally)) {
            if (k !== "total") totals[k] = (totals[k] ?? 0) + v;
          }
        }
        setTally(totals);
      } finally { setLoading(false); }
    })();
  }, [ready, session]);

  if (!ready || !session) return null;

  const scored = dprs.filter((d) => d.overall_score !== null);
  const mean = scored.length
    ? Math.round(scored.reduce((s, d) => s + (d.overall_score ?? 0), 0) / scored.length)
    : null;
  const critical = dprs.reduce((s, d) => s + (d.critical_count ?? 0), 0);
  const totalFindings = dprs.reduce((s, d) => s + (d.finding_count ?? 0), 0);
  const byStatus = dprs.reduce<Record<string, number>>((a, d) => {
    a[d.status] = (a[d.status] ?? 0) + 1; return a;
  }, {});
  const checksRun = Object.values(tally).reduce((s, n) => s + n, 0);

  const stats: Stat[] = [
    { key: "held", label: "Reports held", value: dprs.length, icon: "doc", tone: "brand" },
    { key: "rev", label: "Under review", value: byStatus["under_review"] ?? 0,
      icon: "search", tone: "brand" },
    { key: "crit", label: "Critical findings", value: critical, icon: "flag",
      tone: "attention", basis: `out of ${totalFindings} findings in total` },
    { key: "mean", label: "Mean quality", value: mean,
      suffix: mean != null ? "/100" : undefined, icon: "gauge", tone: "gold",
      basis: scored.length ? `across ${scored.length} assessed reports` : "nothing assessed yet" },
  ];

  const rail = (
    <>
      <RailCard title="Workflow">
        {(["processing", "assessed", "under_review", "approved", "returned"] as const)
          .filter((k) => byStatus[k])
          .map((k) => (
            <RailStat key={k}
                      icon={k === "approved" ? "check" : k === "returned" ? "flag" : "clock"}
                      label={k.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase())}
                      value={byStatus[k]}
                      tone={k === "approved" ? "ok" : k === "returned" ? "attention" : undefined} />
          ))}
        {Object.keys(byStatus).length === 0 && (
          <p className="text-2xs text-ink-faint">No reports in the system yet.</p>
        )}
      </RailCard>

      <RailCard title="Cost outcomes"
                action={<button onClick={() => router.push("/portfolio")}
                                className="btn btn-sm btn-quiet text-2xs">
                          All <Icon name="chevronRight" className="w-3 h-3" />
                        </button>}>
        {rows.filter((r) => r.p80_cost_cr !== null).length === 0 ? (
          <p className="text-2xs text-ink-faint">
            No comparable-project ranges yet. A range needs peers in the historical data.
          </p>
        ) : (
          <ul className="space-y-2.5">
            {rows.filter((r) => r.p80_cost_cr !== null).slice(0, 5).map((r) => (
              <li key={r.id}>
                <button onClick={() => router.push(`/review/${r.id}?view=risk`)}
                        className="group w-full text-left">
                  <span className="flex items-baseline gap-2">
                    <span className="min-w-0 flex-1 truncate text-2xs text-ink-soft
                                     group-hover:text-brand">
                      {r.title}
                    </span>
                    <span className="shrink-0 text-2xs font-semibold tabular-nums text-ink">
                      ₹{r.p80_cost_cr?.toFixed(2)} Cr
                    </span>
                  </span>
                  <span className="mt-0.5 block text-2xs text-ink-faint">
                    80% of {r.peer_count} comparable projects finished at or below this
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </RailCard>
    </>
  );

  return (
    <AppShell title="Ministry overview"
              subtitle="Where each report sits, and what the engine found across all of them."
              rail={rail}>
      {loading ? (
        <div className="space-y-4">
          <div className="skeleton h-24 rounded-card" />
          <div className="grid gap-4 lg:grid-cols-2">
            {[0, 1, 2, 3].map((i) => <div key={i} className="skeleton h-56 rounded-card" />)}
          </div>
        </div>
      ) : dprs.length === 0 ? (
        <Empty title="No reports yet"
               hint="Submitted reports appear here once they have been processed." />
      ) : (
        <div ref={reveal} className="space-y-4">
          <div data-reveal><StatStrip stats={stats} /></div>

          <div className="grid gap-4 lg:grid-cols-2">
            <Panel title="What was checked, across every report"
                   hint={`${checksRun.toLocaleString("en-IN")} individual checks were run. This
                          is the whole rubric, not only the rules that raised something —
                          a tool that shows you only its complaints cannot be audited.`}>
              {checksRun > 0
                ? <StatusStack tally={tally} />
                : <p className="text-2xs text-ink-faint">
                    No checklist rows recorded yet. Reports assessed by an earlier engine do
                    not carry one.
                  </p>}
            </Panel>

            <Panel title="Findings by severity"
                   hint="Severity is ordinal, so it is drawn as one hue deepening rather than
                         five competing colours. Click a band to open the queue filtered to it."
                   action={<button onClick={() => router.push("/queue")}
                                   className="btn btn-sm btn-quiet text-2xs">
                             Queue <Icon name="chevronRight" className="w-3 h-3" />
                           </button>}>
              <SeverityBars
                counts={dprs.reduce<Record<string, number>>((a, d) => {
                  a.critical = (a.critical ?? 0) + (d.critical_count ?? 0);
                  a.high = (a.high ?? 0) +
                    Math.max(0, (d.finding_count ?? 0) - (d.critical_count ?? 0));
                  return a;
                }, {})}
                onPick={() => router.push("/queue")} />
              <p className="mt-3 border-t border-paper-edge pt-2.5 text-2xs leading-relaxed
                            text-ink-faint">
                The list endpoint returns a critical count and a total, so the bar below
                critical is every other severity together. Open a report to see its own
                breakdown — this view does not guess at one.
              </p>
            </Panel>

            <Panel title="Quality against predicted risk"
                   hint="A report can be well written and still describe a risky project.
                         These are separate measurements and the chart keeps them apart.
                         Click a point to open that report."
                   className="lg:col-span-2">
              <QualityRiskScatter rows={rows} onPick={(id) => router.push(`/review/${id}`)} />
            </Panel>
          </div>

          <p data-reveal className="max-w-3xl text-2xs leading-relaxed text-ink-faint">
            This page shows appraisal progress — where each report sits in the review
            workflow and what the engine found in it. It does not show construction or
            expenditure progress: a DPR is appraised before the work starts, so the system
            holds no milestone or spend data, and a chart of it would be invented.
          </p>
        </div>
      )}
    </AppShell>
  );
}
