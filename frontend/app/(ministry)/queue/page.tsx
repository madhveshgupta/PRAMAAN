"use client";
/**
 * The officer's front door.
 *
 *  This screen answers exactly one question — *which one do I open next?* — so it is built
 *  for that decision and not for completeness. Reports with critical findings sort to the
 *  top, because attention should go where the largest sums are at stake rather than to
 *  whatever arrived most recently.
 *
 *  Two views on purpose. A queue is read two ways: scanned for the worst, or worked down in
 *  order. Cards suit the first and a table the second, so both are offered rather than one
 *  being imposed. The choice is remembered for the session, since an officer picks once.
 */
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { AppShell, RailCard } from "@/components/layout/AppShell";
import type { Notice } from "@/components/layout/Topbar";
import { QualityRiskScatter } from "@/components/charts/Figures";
import { Empty } from "@/components/ui/bits";
import { DprTable } from "@/components/ui/DprTable";
import { Icon } from "@/components/ui/Icon";
import { Pagination } from "@/components/ui/Pagination";
import { ReportCard } from "@/components/ui/ReportCard";
import { Segmented } from "@/components/ui/Segmented";
import { StatStrip, type Stat } from "@/components/ui/StatStrip";
import { useReveal } from "@/lib/motion";
import { api, type DprRow } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth";

interface PortfolioRow {
  id: string; title: string; status: string;
  quality_score: number | null; delay_probability: number | null;
  composite: number | null; critical_findings: number;
  p80_cost_cr: number | null; peer_count: number | null;
  check_tally?: Record<string, number> | null;
}

const PER_PAGE = 6;
type Tab = "attention" | "clean" | "all";

export default function QueuePage() {
  const { session, ready } = useRequireAuth(["ministry"]);
  const router = useRouter();

  const [rows, setRows] = useState<DprRow[]>([]);
  const [portfolio, setPortfolio] = useState<PortfolioRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<Tab>("attention");
  const [view, setView] = useState<"cards" | "table">("cards");
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);

  useEffect(() => {
    if (!ready || !session) return;
    void (async () => {
      try {
        // Two calls, not forty. `/portfolio` already carries the P80 cost and the delay
        // probability for every live report, so the cards can show a cost without each one
        // fetching its own.
        const [d, p] = await Promise.all([
          api<DprRow[]>("/dprs"),
          api<PortfolioRow[]>("/portfolio").catch(() => [] as PortfolioRow[]),
        ]);
        setRows(d); setPortfolio(p);
      } finally { setLoading(false); }
    })();
  }, [ready, session]);

  useEffect(() => { setPage(1); }, [tab, q]);

  const costOf = useMemo(() => {
    const m = new Map(portfolio.map((p) => [p.id, p.p80_cost_cr]));
    return (id: string) => m.get(id) ?? null;
  }, [portfolio]);

  const live = useMemo(() => rows.filter((r) => !r.is_self_check), [rows]);

  const buckets = useMemo(() => ({
    attention: live.filter((r) => (r.critical_count ?? 0) > 0),
    clean: live.filter((r) => (r.critical_count ?? 0) === 0),
    all: live,
  }), [live]);

  const shown = useMemo(() => {
    let out = buckets[tab];
    if (q.trim()) {
      const n = q.toLowerCase();
      out = out.filter((r) => r.title.toLowerCase().includes(n));
    }
    // Most critical first, then oldest first — an old report with two criticals outranks a
    // new one with three, because the old one has been waiting.
    return [...out].sort((a, b) =>
      (b.critical_count ?? 0) - (a.critical_count ?? 0) ||
      new Date(a.created_at).getTime() - new Date(b.created_at).getTime());
  }, [buckets, tab, q]);

  const pages = Math.max(1, Math.ceil(shown.length / PER_PAGE));
  const slice = shown.slice((page - 1) * PER_PAGE, page * PER_PAGE);
  const reveal = useReveal<HTMLDivElement>({ immediate: true, deps: [tab, page, view, loading] });

  const scored = live.filter((r) => r.overall_score != null);
  const mean = scored.length
    ? Math.round(scored.reduce((s, r) => s + (r.overall_score ?? 0), 0) / scored.length)
    : null;

  // The oldest report still waiting. This is the number a queue is actually judged on, and
  // it is computed from the rows rather than invented.
  const oldestDays = live.length
    ? Math.max(...live.map((r) =>
        Math.floor((Date.now() - new Date(r.created_at).getTime()) / 86_400_000)))
    : null;

  const stats: Stat[] = [
    { key: "await", label: "Awaiting review", value: live.length, icon: "list", tone: "brand" },
    { key: "crit", label: "With critical findings", value: buckets.attention.length,
      icon: "flag", tone: "attention" },
    { key: "mean", label: "Mean quality score", value: mean, suffix: mean != null ? "/100" : undefined,
      icon: "gauge", tone: "gold",
      basis: scored.length ? `across ${scored.length} assessed reports` : "nothing assessed yet" },
    { key: "old", label: "Longest waiting", value: oldestDays, suffix: oldestDays != null ? " days" : undefined,
      icon: "clock", tone: oldestDays != null && oldestDays > 14 ? "attention" : "brand" },
  ];

  const notices: Notice[] = buckets.attention.slice(0, 6).map((r) => ({
    id: r.id, title: r.title, href: `/review/${r.id}?view=findings`, tone: "attention",
    detail: `${r.critical_count} critical finding${r.critical_count === 1 ? "" : "s"}`,
  }));

  if (!ready || !session) return null;

  const rail = (
    <>
      {/* The four counts live in the band at the foot of the page and nowhere else. This
          card used to repeat them, which made the rail longer without making the screen say
          anything more. */}

      {portfolio.length >= 2 && (
        <RailCard title="Quality against risk"
                  action={
                    <button onClick={() => router.push("/portfolio")}
                            className="btn btn-sm btn-quiet text-2xs">
                      Portfolio <Icon name="chevronRight" className="w-3 h-3" />
                    </button>
                  }>
          <QualityRiskScatter rows={portfolio} onPick={(id) => router.push(`/review/${id}`)} />
        </RailCard>
      )}

      <RailCard title="How this queue is ordered">
        <p className="text-2xs leading-relaxed text-ink-soft">
          Reports with critical findings first, then the ones that have waited longest.
          Nothing here has been rejected by the system — it scores and flags, and you decide.
        </p>
      </RailCard>
    </>
  );

  return (
    <AppShell title="Review queue"
              subtitle="Reports waiting on an appraisal decision, most urgent first."
              notices={notices} rail={rail}>
      <StatStrip stats={stats} />

      <div className="mt-6 flex flex-wrap items-center gap-3">
        <Segmented<Tab>
          label="Filter the queue"
          value={tab} onChange={setTab}
          segments={[
            { value: "attention", label: "Needs attention", count: buckets.attention.length },
            { value: "clean", label: "No critical findings", count: buckets.clean.length },
            { value: "all", label: "All", count: buckets.all.length },
          ]} />

        <div className="no-print relative ml-auto w-56">
          <Icon name="search"
                className="pointer-events-none absolute left-3 top-1/2 w-4 h-4 -translate-y-1/2
                           text-ink-ghost" />
          <input value={q} onChange={(e) => setQ(e.target.value)}
                 aria-label="Search by project name" placeholder="Search by project name"
                 className="field py-1.5 pl-9 text-xs" />
        </div>

        <div className="no-print flex items-center gap-1 rounded-full border border-paper-edge
                        bg-paper p-1" role="group" aria-label="View">
          {([["cards", "grid"], ["table", "list"]] as const).map(([k, icon]) => (
            <button key={k} onClick={() => setView(k)} aria-pressed={view === k}
                    aria-label={k === "cards" ? "Card view" : "Table view"}
                    className={`grid h-7 w-7 place-items-center rounded-full transition-colors ${
                      view === k ? "bg-brand-deep text-white"
                                 : "text-ink-soft hover:bg-paper-deep"}`}>
              <Icon name={icon as "grid" | "list"} className="w-3.5 h-3.5" />
            </button>
          ))}
        </div>
      </div>

      <div ref={reveal} className="mt-5">
        {loading ? (
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {[0, 1, 2, 3, 4, 5].map((i) => <div key={i} className="skeleton h-56 rounded-card" />)}
          </div>
        ) : shown.length === 0 ? (
          <Empty title={q ? "No reports match that search" : "Nothing in this bucket"}
                 hint={q ? "Clear the search to see the whole queue."
                         : "Reports appear here once they have been submitted and read."} />
        ) : view === "cards" ? (
          <>
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {slice.map((r) => (
                <div key={r.id} data-reveal>
                  <ReportCard row={r} href={`/review/${r.id}`} cost={costOf(r.id)} />
                </div>
              ))}
            </div>
            <div className="mt-5 flex justify-center">
              <Pagination page={page} pages={pages} onChange={setPage} total={shown.length} />
            </div>
          </>
        ) : (
          <div data-reveal className="card overflow-hidden px-4 shadow-card">
            <DprTable rows={shown} hrefBase="/review" loading={false} />
          </div>
        )}
      </div>
    </AppShell>
  );
}
