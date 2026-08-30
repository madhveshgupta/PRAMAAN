"use client";
/**
 * The applicant's whole world: their reports, and the way to submit another.
 *
 *  The emotional arc here is upload → wait → *your report has findings*, and the third
 *  step is the one the design has to get right. The person reading these findings WROTE the
 *  report. So the language is help rather than judgement — "action required", not "failed";
 *  "what to fix", not "defects" — and the score is shown only for a private pre-submission
 *  check, which is the author's own rehearsal. A number attached to a live submission
 *  invites "we are at 84, get us to 90", and the cheapest route to 90 is padding chapters.
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { UploadDialog } from "@/components/applicant/UploadDialog";
import { AppShell, RailCard } from "@/components/layout/AppShell";
import type { Notice } from "@/components/layout/Topbar";
import { Empty } from "@/components/ui/bits";
import { Icon } from "@/components/ui/Icon";
import { Pagination } from "@/components/ui/Pagination";
import { ReportCard } from "@/components/ui/ReportCard";
import { Segmented } from "@/components/ui/Segmented";
import { StatStrip, type Stat } from "@/components/ui/StatStrip";
import { useReveal } from "@/lib/motion";
import { api, type DprRow } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth";

const PER_PAGE = 6;
type Tab = "checked" | "attention" | "drafts";

function Submissions() {
  const { session, ready } = useRequireAuth(["applicant", "ministry"]);
  const params = useSearchParams();
  const router = useRouter();

  const [rows, setRows] = useState<DprRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<Tab>("checked");
  const [page, setPage] = useState(1);
  const [uploading, setUploading] = useState(params.get("upload") === "1");

  const refresh = useCallback(async () => {
    try { setRows(await api<DprRow[]>("/dprs")); } finally { setLoading(false); }
  }, []);

  useEffect(() => { if (ready && session) void refresh(); }, [ready, session, refresh]);
  useEffect(() => { setUploading(params.get("upload") === "1"); }, [params]);
  useEffect(() => { setPage(1); }, [tab]);

  const buckets = useMemo(() => {
    const attention = rows.filter((r) => (r.critical_count ?? 0) > 0);
    const drafts = rows.filter((r) => r.status === "draft" || r.status === "processing");
    const checked = rows.filter(
      (r) => (r.critical_count ?? 0) === 0 && r.status !== "draft" && r.status !== "processing");
    return { attention, drafts, checked };
  }, [rows]);

  const shown = buckets[tab];
  const pages = Math.max(1, Math.ceil(shown.length / PER_PAGE));
  const slice = shown.slice((page - 1) * PER_PAGE, page * PER_PAGE);

  const reveal = useReveal<HTMLDivElement>({ immediate: true, deps: [tab, page, loading] });

  // The bell's contents, and they are real: reports of theirs that came back with something
  // to act on. Nothing is invented to make the icon look busy.
  const notices: Notice[] = buckets.attention.slice(0, 6).map((r) => ({
    id: r.id, title: r.title, href: `/review/${r.id}?view=findings`, tone: "attention",
    detail: `${r.critical_count} critical finding${r.critical_count === 1 ? "" : "s"} to look at`,
  }));

  const scored = rows.filter((r) => r.overall_score != null && r.is_self_check);
  const stats: Stat[] = [
    { key: "total", label: "Reports submitted", value: rows.length, icon: "doc", tone: "brand" },
    { key: "clean", label: "Checked, nothing critical", value: buckets.checked.length,
      icon: "check", tone: "ok" },
    { key: "att", label: "Needing action", value: buckets.attention.length,
      icon: "flag", tone: "attention" },
    { key: "self", label: "Mean score, private checks",
      value: scored.length
        ? Math.round(scored.reduce((s, r) => s + (r.overall_score ?? 0), 0) / scored.length)
        : null,
      suffix: scored.length ? "/100" : undefined, icon: "gauge", tone: "gold",
      basis: scored.length ? `across ${scored.length} private check${scored.length === 1 ? "" : "s"}`
                           : "run a private check to see this" },
  ];

  const closeUpload = () => {
    setUploading(false);
    if (params.get("upload")) router.replace("/submissions", { scroll: false });
  };

  if (!ready || !session) return null;

  const rail = (
    <>
      <RailCard tone="brand">
        <div className="flex items-start gap-3">
          <span aria-hidden className="grid h-11 w-11 shrink-0 place-items-center
                                       rounded-card bg-brand text-white">
            <Icon name="upload" className="w-5 h-5" />
          </span>
          <div className="min-w-0">
            <h2 className="display text-sm font-bold text-ink">Submit a new report</h2>
            <p className="mt-0.5 text-2xs leading-relaxed text-ink-soft">
              PDF up to 100 MB. Run it as a private check first and fix what it finds before
              the ministry ever sees it.
            </p>
          </div>
        </div>
        <button onClick={() => setUploading(true)} className="btn-gold mt-3 w-full">
          Upload now
          <Icon name="arrow" className="w-4 h-4" />
        </button>
      </RailCard>

      {/* No "Summary" card here. It listed the same four figures as the band at the foot
          of the page, in the same order, six inches apart — and a number shown twice on one
          screen is a number a reader has to check against itself. The band keeps them,
          because it is the one an eye lands on first. */}

      <RailCard title="Recent activity">
        {rows.length === 0 ? (
          <p className="text-2xs text-ink-faint">Nothing yet.</p>
        ) : (
          <ul className="space-y-2.5">
            {rows.slice(0, 5).map((r) => {
              const att = (r.critical_count ?? 0) > 0;
              return (
                <li key={r.id}>
                  <a href={`/review/${r.id}`}
                     className="group flex items-start gap-2.5 rounded p-1 transition-colors
                                hover:bg-brand-soft/60">
                    <Icon name={att ? "flag" : "check"}
                          className={`mt-0.5 w-4 h-4 shrink-0 ${att ? "text-sev-high" : "text-ok"}`} />
                    <span className="min-w-0">
                      <span className="block truncate text-2xs font-medium text-ink
                                       group-hover:text-brand">
                        {r.title}
                      </span>
                      <span className="mt-0.5 block text-2xs text-ink-faint">
                        {att ? "Action required" : "Checked"}
                        <span className="mx-1">·</span>
                        <span className="tabular-nums">
                          {new Date(r.created_at).toLocaleDateString("en-IN",
                            { day: "2-digit", month: "short", year: "numeric" })}
                        </span>
                      </span>
                    </span>
                  </a>
                </li>
              );
            })}
          </ul>
        )}
      </RailCard>
    </>
  );

  return (
    <AppShell title="My reports"
              subtitle="Track the status of your submitted reports and private checks."
              notices={notices}
              search={uploading ? "upload=1" : ""}
              rail={rail}
              actions={
                <button onClick={() => setUploading(true)}
                        className="btn btn-sm btn-primary hidden sm:inline-flex">
                  <Icon name="upload" className="w-3.5 h-3.5" />
                  Upload
                </button>
              }>
      <UploadDialog open={uploading} onClose={closeUpload} onDone={refresh} />

      <div className="flex flex-wrap items-center gap-3">
        <Segmented<Tab>
          label="Filter reports"
          value={tab} onChange={setTab}
          segments={[
            { value: "checked", label: "Submitted & checked", count: buckets.checked.length },
            { value: "attention", label: "Action required", count: buckets.attention.length },
            { value: "drafts", label: "Processing", count: buckets.drafts.length },
          ]} />
        <span className="ml-auto text-2xs tabular-nums text-ink-faint">
          {rows.length} report{rows.length === 1 ? "" : "s"} in total
        </span>
      </div>

      <div ref={reveal} className="mt-5">
        {loading ? (
          <div className="grid gap-4 sm:grid-cols-2">
            {[0, 1, 2, 3].map((i) => <div key={i} className="skeleton h-56 rounded-card" />)}
          </div>
        ) : rows.length === 0 ? (
          <div className="card px-6 py-14 text-center shadow-card">
            <Icon name="cloud" className="mx-auto w-10 h-10 text-ink-ghost" />
            <p className="mt-3 display text-lg font-bold text-ink">Nothing here yet</p>
            <p className="mx-auto mt-1.5 max-w-md text-xs leading-relaxed text-ink-soft">
              Upload a Detailed Project Report and it will appear here once it has been read.
              Start with a private check — it is scored against the same rubric the ministry
              uses, and nobody else sees it.
            </p>
            <button onClick={() => setUploading(true)} className="btn-gold mx-auto mt-5">
              <Icon name="upload" className="w-4 h-4" />
              Upload your first report
            </button>
          </div>
        ) : slice.length === 0 ? (
          <Empty title={tab === "attention"
                   ? "Nothing needs your action"
                   : tab === "drafts" ? "Nothing is processing"
                   : "No checked reports yet"}
                 hint={tab === "attention"
                   ? "None of your reports has a critical finding against it."
                   : "Reports move here once they have been read."} />
        ) : (
          <>
            <div className="grid gap-4 sm:grid-cols-2">
              {slice.map((r) => (
                <div key={r.id} data-reveal>
                  <ReportCard row={r} href={`/review/${r.id}`}
                              showScore={r.is_self_check}
                              footnote={r.is_self_check
                                ? "Private pre-submission check — not seen by the ministry"
                                : undefined} />
                </div>
              ))}
            </div>
            <div className="mt-5 flex justify-center">
              <Pagination page={page} pages={pages} onChange={setPage}
                          total={shown.length} />
            </div>
          </>
        )}
      </div>

      <div className="mt-6">
        <StatStrip stats={stats} />
      </div>

      <p className="mt-4 max-w-3xl text-2xs leading-relaxed text-ink-faint">
        Findings are advisory. Nothing here is a rejection — the system scores and flags, and
        a named officer decides. Where a finding cites a page, you can open the report at
        that page and read the exact text it is based on.
      </p>
    </AppShell>
  );
}

export default function Page() {
  return <Suspense fallback={null}><Submissions /></Suspense>;
}
