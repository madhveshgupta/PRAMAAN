"use client";
/** Where the appraisal notes live. Ministry only.
 *
 *  Each note is a PDF carrying a SHA-256 of its own content, which is why it is worth a
 *  shelf of its own rather than one link buried in the review workspace: the hash is the
 *  thing that lets an auditor confirm, years later, that the note in the file is the note
 *  that was issued.
 *
 *  An applicant was allowed in here and should not have been. The note is the record of the
 *  ministry's appraisal — an applicant has none to read, and the shelf they were shown
 *  listed their own private self-checks under a heading describing a decision nobody had
 *  taken. `useRequireAuth` now sends them back to their own reports, and both routes in
 *  (the rail and the account menu) have been withdrawn for that role.
 */
import { useEffect, useState } from "react";

import { AppShell, RailCard } from "@/components/layout/AppShell";
import { Chip, DPR_STATUS, Empty, TableSkeleton } from "@/components/ui/bits";
import { Icon } from "@/components/ui/Icon";
import { ScoreArc } from "@/components/ui/Score";
import { useReveal } from "@/lib/motion";
import { api, type DprRow } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth";

export default function ReportsPage() {
  const { session, ready } = useRequireAuth(["ministry"]);
  const [rows, setRows] = useState<DprRow[]>([]);
  const [loading, setLoading] = useState(true);
  const reveal = useReveal<HTMLUListElement>({ immediate: true, deps: [loading] });

  useEffect(() => {
    if (!ready || !session) return;
    void (async () => {
      try { setRows(await api<DprRow[]>("/dprs")); } finally { setLoading(false); }
    })();
  }, [ready, session]);

  if (!ready || !session) return null;
  const available = rows.filter((r) => r.overall_score != null);

  const rail = (
    <RailCard title="What is in a note">
      <ul className="space-y-2 text-2xs leading-relaxed text-ink-soft">
        <li className="flex gap-2">
          <Icon name="gauge" className="mt-px w-3.5 h-3.5 shrink-0 text-brand" />
          The quality score and the components it is made of.
        </li>
        <li className="flex gap-2">
          <Icon name="flag" className="mt-px w-3.5 h-3.5 shrink-0 text-brand" />
          Every finding, with the page each one cites.
        </li>
        <li className="flex gap-2">
          <Icon name="list" className="mt-px w-3.5 h-3.5 shrink-0 text-brand" />
          The full checklist — including the rules that were not run.
        </li>
        <li className="flex gap-2">
          <Icon name="lock" className="mt-px w-3.5 h-3.5 shrink-0 text-brand" />
          A SHA-256 of the note's own content, in the
          {" "}<code className="font-mono">X-Content-SHA256</code> header.
        </li>
      </ul>
    </RailCard>
  );

  return (
    <AppShell title="Appraisal notes"
              subtitle="A signed note for each assessed report — the score, the findings, and the pages they cite."
              rail={rail}>
      {loading ? (
        <div className="card p-4 shadow-card"><TableSkeleton rows={5} cols={4} /></div>
      ) : available.length === 0 ? (
        <Empty title="No appraisal notes yet"
               hint="A note becomes available once a report has been assessed." />
      ) : (
        <ul ref={reveal} className="grid gap-4 sm:grid-cols-2">
          {available.map((r) => (
            <li key={r.id} data-reveal
                className="card card-hover flex items-center gap-4 p-4 shadow-card">
              <div className="w-[62px] shrink-0 flex items-center justify-center">
                <ScoreArc score={r.overall_score ?? null} size={62} label={false} />
              </div>
              <div className="min-w-0 flex-1">
                <p className="display truncate text-sm font-bold text-ink">{r.title}</p>
                <div className="mt-1.5 flex flex-wrap items-center gap-2">
                  <Chip meta={DPR_STATUS[r.status] ?? DPR_STATUS.draft} />
                  <span className="text-2xs tabular-nums text-ink-faint">
                    {new Date(r.created_at).toLocaleDateString("en-IN",
                      { day: "2-digit", month: "short", year: "numeric" })}
                  </span>
                </div>
              </div>
              <button onClick={() => {
                import("@/lib/api").then(({ downloadFile }) => {
                  downloadFile(`/dprs/${r.id}/report.pdf`, `${r.title} - Appraisal Note.pdf`)
                    .catch(e => alert(e.message));
                });
              }}
                 className="btn btn-sm btn-ghost shrink-0">
                <Icon name="download" className="w-3.5 h-3.5" />
                PDF
              </button>
            </li>
          ))}
        </ul>
      )}
    </AppShell>
  );
}
