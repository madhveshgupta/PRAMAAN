"use client";
/**
 * The review workspace — the product.
 *
 *  The old shape was a document on the left and a 27rem tabbed rail on the right, always
 *  both, forever. That is the right shape only if the document is the subject; here the
 *  FINDINGS are the subject and the document is the proof, so the default is the reading
 *  column at full width, with the document arriving beside it the moment a claim is
 *  challenged. See `EvidenceSplit` for the gesture itself.
 *
 *  Findings and their anchors arrive in the initial payload, so the jump from clicking a
 *  finding to seeing the highlight costs no network round-trip. That is the difference
 *  between an instrument and a website, and it is why the split can be instant.
 */
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useMemo, useState } from "react";

import { EvidenceSplit } from "@/components/evidence/EvidenceSplit";
import { AppShell } from "@/components/layout/AppShell";
import { ChecklistView } from "@/components/review/ChecklistView";
import { DecisionPanel } from "@/components/review/DecisionPanel";
import { FindingsView } from "@/components/review/FindingsView";
import { OverviewView } from "@/components/review/OverviewView";
import { RiskView, type RiskPayload } from "@/components/review/RiskView";
import { ValuesView } from "@/components/review/ValuesView";
import { Icon, type IconName } from "@/components/ui/Icon";
import { api, type Assessment, type Checklist, type DecisionPayload, type DprRow,
         type EvidenceAnchor, type Extraction, type Finding } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth";
import { prefersReduced } from "@/lib/motion";
import { PdfViewer, type ViewerTarget } from "@/components/viewer/PdfViewer";

interface Status {
  document_id?: string;
  is_self_check?: boolean;
  ocr_pages?: number; stage: string; detail: string; percent: number;
  page_count: number | null; spans: number; error: string | null;
}

type View = "overview" | "findings" | "checklist" | "values" | "risk" | "decision";

/** What the reading column is currently pointing at. One piece of state for findings,
 *  checklist rows and extracted values alike — three separate selections is how the old
 *  page ended up unable to say which row the document was showing. */
interface Selection {
  key: string;
  evidence: EvidenceAnchor[];
  severity: string;
  index: number;
  nonce: number;
}

function Workspace() {
  const { session, ready } = useRequireAuth(["ministry", "applicant"]);
  const { id } = useParams<{ id: string }>();
  const params = useSearchParams();
  const router = useRouter();

  const [dpr, setDpr] = useState<DprRow | null>(null);
  const [status, setStatus] = useState<Status | null>(null);
  const [assessment, setAssessment] = useState<Assessment | null>(null);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [checklist, setChecklist] = useState<Checklist | null>(null);
  const [extraction, setExtraction] = useState<Extraction | null>(null);
  const [risk, setRisk] = useState<RiskPayload | null>(null);
  const [decision, setDecision] = useState<DecisionPayload | null>(null);

  const [view, setView] = useState<View>((params.get("view") as View) ?? "overview");
  const [sel, setSel] = useState<Selection | null>(null);
  const [splitOpen, setSplitOpen] = useState(false);
  // Whether the navigation rail is currently lent to the split. Measured once on open
  // rather than read on every render, so a resize mid-review does not yank the layout.
  const [borrowRail, setBorrowRail] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // The whole applicant/ministry split hangs off this. The server already refuses the
  // ministry-only endpoints, so this decides what is OFFERED, not what is protected.
  const ministry = session?.role === "ministry";

  useEffect(() => {
    if (!ready || !session) return;
    void (async () => {
      try {
        const [st, fs, rows] = await Promise.all([
          api<Status>(`/dprs/${id}/status`),
          api<Finding[]>(`/dprs/${id}/findings`),
          api<DprRow[]>("/dprs").catch(() => [] as DprRow[]),
        ]);
        setStatus(st);
        setFindings(fs);
        setDpr(rows.find((r) => r.id === id) ?? null);

        // Each of these is optional: a report can be readable before it is assessed, and a
        // missing assessment must not blank the screen that shows the document.
        try { setAssessment(await api<Assessment>(`/dprs/${id}/assessment`)); } catch {}
        try { setChecklist(await api<Checklist>(`/dprs/${id}/checklist`)); } catch {}
        if (session.role === "ministry") {
          // Both of these are ministry-only on the server. Asking for them as an applicant
          // is a guaranteed 403 on every page load — caught and discarded, but still two
          // failing requests in the network log of the screen an officer is most likely to
          // be shown when something is being debugged.
          try { setExtraction(await api<Extraction>(`/dprs/${id}/extraction`)); } catch {}
          try { setRisk(await api<RiskPayload>(`/dprs/${id}/risk`)); } catch {}
        } else {
          try { setDecision(await api<DecisionPayload>(`/dprs/${id}/decision`)); } catch {}
        }
      } catch (e) {
        setError((e as Error).message ?? "Could not load this report");
      } finally { setLoading(false); }
    })();
  }, [id, ready, session]);

  /* --- opening the document -------------------------------------------------------- */

  const open = useCallback((evidence: EvidenceAnchor[], severity: string,
                            index = 0, key = "") => {
    if (!evidence?.length) return;
    setSel((prev) => ({
      key, evidence, severity, index,
      nonce: (prev?.nonce ?? 0) + 1,   // re-fires the highlight even on the same anchor
    }));
    setSplitOpen(true);

    // Bring the row that was just opened to the top of the reading column. Without this the
    // reading column keeps whatever scroll position it had, so on a 1366px screen the claim
    // whose proof just arrived is frequently the one thing scrolled off the top — the two
    // halves of the comparison end up on screen at different times.
    if (!key) return;
    requestAnimationFrame(() => {
      const el = document.getElementById(`finding-${key}`) ?? document.getElementById(`row-${key}`);
      el?.scrollIntoView({ block: "nearest", behavior: prefersReduced() ? "auto" : "smooth" });
    });
  }, []);

  const target: ViewerTarget | null = useMemo(() => {
    if (!sel || !sel.evidence || !sel.evidence[sel.index]) return null;
    const a = sel.evidence[Math.min(sel.index, sel.evidence.length - 1)];
    if (!a) return null;
    return {
      page: a.page,
      anchors: sel.evidence.filter((e) => e.page === a.page),
      severity: sel.severity,
      nonce: sel.nonce,
    };
  }, [sel]);

  /* --- the rail's width, while two panes need it ------------------------------------
     Only below 1600px: on a wide monitor all three fit, and taking the navigation away
     there would be solving a problem that screen does not have. */
  useEffect(() => {
    if (!splitOpen) { setBorrowRail(false); return; }
    setBorrowRail(window.innerWidth < 1600);
  }, [splitOpen]);

  /* --- the URL carries the view and the selection, so a link is shareable ----------- */
  useEffect(() => {
    const q = new URLSearchParams({ view });
    if (sel?.key) { q.set("row", sel.key); q.set("anchor", String(sel.index)); }
    router.replace(`?${q}`, { scroll: false });
  }, [view, sel?.key, sel?.index, router]);

  /* --- keyboard: work the list without the mouse ------------------------------------ */
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (/^(INPUT|TEXTAREA)$/.test((e.target as HTMLElement)?.tagName ?? "")) return;
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      if (view !== "findings" || !findings.length) return;

      const i = findings.findIndex((f) => f.id === sel?.key);
      const go = (n: number) => {
        const f = findings[Math.max(0, Math.min(findings.length - 1, n))];
        if (!f) return;
        e.preventDefault();
        open(f.evidence, f.severity, 0, f.id);
        document.getElementById(`finding-${f.id}`)
          ?.scrollIntoView({ block: "center", behavior: "smooth" });
      };
      if (e.key === "j" || e.key === "ArrowDown") go(i + 1);
      else if (e.key === "k" || e.key === "ArrowUp") go(i < 0 ? 0 : i - 1);
      else if (e.key === "]" && sel) {
        e.preventDefault();
        setSel({ ...sel, index: Math.min(sel.evidence.length - 1, sel.index + 1),
                 nonce: sel.nonce + 1 });
      } else if (e.key === "[" && sel) {
        e.preventDefault();
        setSel({ ...sel, index: Math.max(0, sel.index - 1), nonce: sel.nonce + 1 });
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [findings, sel, view, open]);

  const review = useCallback(
    async (f: Finding, d: "accepted" | "rejected" | "amended", note?: string) => {
      const q = new URLSearchParams({ decision: d, ...(note ? { note } : {}) });
      await api(`/findings/${f.id}/review?${q}`, { method: "POST" });
      setFindings(await api<Finding[]>(`/dprs/${id}/findings`));
    }, [id]);

  // Above the auth guard: hooks may not sit behind an early return, and `session` resolving
  // one render later is exactly the case that would change the hook count between renders.
  const claimedCostCr = useMemo(() => {
    const f = extraction?.fields.find(
      (x) => /total_cost|project_cost|capital_cost/.test(x.field_key));
    const n = f?.value ? Number(String(f.value).replace(/[^\d.]/g, "")) : NaN;
    return Number.isFinite(n) && n > 0 ? n : null;
  }, [extraction]);

  if (!ready || !session) return null;

  const showScore = Boolean(ministry || status?.is_self_check);

  const TABS: { key: View; label: string; icon: IconName; count?: number | null }[] = [
    { key: "overview",  label: "Overview",  icon: "gauge" },
    { key: "findings",  label: "Findings",  icon: "flag", count: findings.length },
    { key: "checklist", label: "Checklist", icon: "list",
      count: checklist && !checklist.stale ? checklist.tally.total : null },
    ...(ministry ? [
      { key: "values" as View, label: "Values & refusals", icon: "shield" as IconName,
        count: extraction ? extraction.fields.length : null },
      { key: "risk" as View, label: "Risk", icon: "trend" as IconName },
    ] : []),
    { key: "decision",  label: "Decision",  icon: "docCheck" },
  ];

  const reading = (
    <div className="mx-auto max-w-4xl px-5 py-5">
      {error && (
        <p role="alert" className="mb-4 rounded-card border border-sev-critical/20
                                   bg-sev-critical-soft px-4 py-3 text-sm text-sev-critical">
          {error}
        </p>
      )}

      {view === "overview" && (
        <OverviewView assessment={assessment} findings={findings}
                      tally={checklist && !checklist.stale ? checklist.tally : null}
                      ministry={ministry} showScore={showScore}
                      ocrPages={status?.ocr_pages} pageCount={status?.page_count}
                      onGoto={(v) => setView(v)} />
      )}

      {view === "findings" && (
        <FindingsView findings={findings} loading={loading} ministry={ministry}
                      onOpen={open} activeKey={sel?.key} activeIndex={sel?.index ?? 0}
                      canReview={ministry} onReview={review} />
      )}

      {view === "checklist" && (
        <ChecklistView checklist={checklist} ministry={ministry}
                       onOpen={open} activeKey={sel?.key} />
      )}

      {view === "values" && (
        <ValuesView extraction={extraction} ministry={ministry}
                    onOpen={open} activeKey={sel?.key} />
      )}

      {view === "risk" && <RiskView risk={risk} claimedCostCr={claimedCostCr} />}

      {view === "decision" && (
        <DecisionPanel dprId={id} session={session} assessment={assessment}
                       decision={decision} onDone={() => { /* audit is append-only */ }} />
      )}
    </div>
  );

  return (
    <AppShell
      variant="focus"
      borrowRail={borrowRail}
      title={dpr?.title ?? (loading ? "Opening report…" : "Report")}
      // Every field here is optional on purpose. A DPR whose document row was never written
      // — an upload that failed early — returns a status with no page count and no span
      // count, and reading `.toLocaleString()` off the missing one crashed the whole screen
      // rather than showing the document that is genuinely not there.
      subtitle={status
        ? [
            status.page_count != null ? `${status.page_count} pages` : null,
            status.spans ? `${status.spans.toLocaleString("en-IN")} text spans indexed` : null,
            status.ocr_pages ? `${status.ocr_pages} read by OCR` : null,
          ].filter(Boolean).join(" · ") || status.detail
        : undefined}
      crumb={[{ href: ministry ? "/queue" : "/submissions",
                label: ministry ? "Review queue" : "My reports" }]}
      actions={ministry ? (
        <button onClick={() => {
          import("@/lib/api").then(({ downloadFile }) => {
            downloadFile(`/dprs/${id}/report.pdf`, `Appraisal Note.pdf`)
              .catch(e => alert(e.message));
          });
        }}
           className="btn btn-sm btn-ghost">
          <Icon name="download" className="w-4 h-4" />
          <span className="hidden sm:inline">Appraisal note</span>
        </button>
      ) : undefined}
    >
      {/* --- section nav. Buttons, not tabs in a rail: these are pages of one report. --- */}
      <div className="no-print flex shrink-0 items-center gap-1 overflow-x-auto border-b
                      border-paper-edge bg-paper px-4">
        {TABS.map((t) => (
          <button key={t.key} onClick={() => setView(t.key)}
                  aria-current={view === t.key ? "page" : undefined}
                  className={`flex shrink-0 items-center gap-1.5 border-b-2 px-3 py-2.5
                              text-xs font-medium transition-colors ${
                    view === t.key
                      ? "border-brand text-brand"
                      : "border-transparent text-ink-soft hover:text-ink"}`}>
            <Icon name={t.icon} className="w-4 h-4" />
            {t.label}
            {t.count != null && (
              <span className={`rounded-full px-1.5 py-0.5 text-2xs tabular-nums ${
                view === t.key ? "bg-brand-soft text-brand" : "bg-paper-deep text-ink-faint"}`}>
                {t.count}
              </span>
            )}
          </button>
        ))}

        <button onClick={() => (splitOpen ? setSplitOpen(false)
                                          : sel ? setSplitOpen(true)
                                          : findings[0] && open(findings[0].evidence,
                                                                findings[0].severity, 0,
                                                                findings[0].id))}
                disabled={!status?.document_id}
                aria-pressed={splitOpen}
                className={`ml-auto flex shrink-0 items-center gap-1.5 rounded px-2.5 py-1.5
                            text-2xs font-medium transition-colors disabled:opacity-40 ${
                  splitOpen ? "bg-brand text-white" : "text-brand hover:bg-brand-soft"}`}>
          <Icon name="columns" className="w-4 h-4" />
          {splitOpen ? "Close document" : "Open document"}
        </button>
      </div>

      <EvidenceSplit
        open={splitOpen && Boolean(status?.document_id)}
        onClose={() => setSplitOpen(false)}
        documentTitle={dpr?.title ?? "Source document"}
        hint={target
          ? <>page {target.page} · {target.anchors.length} region
              {target.anchors.length === 1 ? "" : "s"} highlighted</>
          : "no region selected"}
        reading={reading}
        document={status?.document_id
          ? <PdfViewer documentId={status.document_id} target={target} />
          : (
            <div className="grid h-full place-items-center p-8 text-center">
              <p className="text-sm text-ink-faint">
                {status?.error ?? "This report has no readable document attached."}
              </p>
            </div>
          )}
      />
    </AppShell>
  );
}

export default function ReviewPage() {
  return <Suspense fallback={null}><Workspace /></Suspense>;
}
