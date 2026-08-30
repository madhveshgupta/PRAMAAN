"use client";
/** The record of who did what. Read-only for everyone, ministry included.
 *
 *  Drawn as a timeline rather than a table, because that is what it is: an ordered record
 *  of acts, where the gap between two of them is itself information. A table of four
 *  columns hides that a report sat untouched for nine days between being opened and being
 *  decided, which is exactly the question an audit asks.
 */
import { useEffect, useMemo, useState } from "react";

import { AppShell, RailCard } from "@/components/layout/AppShell";
import { Empty, TableSkeleton } from "@/components/ui/bits";
import { Icon, type IconName } from "@/components/ui/Icon";
import { useReveal } from "@/lib/motion";
import { api, type AuditEvent } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth";

// Dotted, because that is what the backend writes — `dpr.uploaded`, not `dpr_uploaded`.
const ACTION: Record<string, { label: string; icon: IconName; tone: string }> = {
  "dpr.uploaded":   { label: "Report uploaded",  icon: "upload",   tone: "text-brand" },
  "dpr.viewed":     { label: "Report opened",    icon: "search",   tone: "text-ink-faint" },
  "dpr.appraised":  { label: "Appraisal recommendation recorded", icon: "docCheck",
                      tone: "text-brand" },
  "dpr.decided":    { label: "Sanction decision recorded", icon: "shield", tone: "text-ok" },
  "finding.reviewed": { label: "Finding reviewed", icon: "flag", tone: "text-sev-medium" },
  "report.exported":  { label: "Appraisal note exported", icon: "download",
                        tone: "text-ink-faint" },
};

function meta(action: string) {
  return ACTION[action] ?? {
    label: action.replace(/[._]/g, " "), icon: "history" as IconName, tone: "text-ink-faint",
  };
}

export default function AuditPage() {
  const { session, ready } = useRequireAuth(["ministry"]);
  const [rows, setRows] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string | null>(null);
  const reveal = useReveal<HTMLDivElement>({ immediate: true, deps: [loading, filter] });

  useEffect(() => {
    if (!ready || !session) return;
    void (async () => {
      try { setRows(await api<AuditEvent[]>("/audit")); } finally { setLoading(false); }
    })();
  }, [ready, session]);

  const kinds = useMemo(() => {
    const by: Record<string, number> = {};
    for (const r of rows) by[r.action] = (by[r.action] ?? 0) + 1;
    return Object.entries(by).sort((a, b) => b[1] - a[1]);
  }, [rows]);

  const shown = filter ? rows.filter((r) => r.action === filter) : rows;

  // Grouped by day. An audit trail read as one undifferentiated stream loses the shape of
  // the work — which days were busy, and which reports moved together.
  const days = useMemo(() => {
    const out: { day: string; items: AuditEvent[] }[] = [];
    for (const e of shown) {
      const day = new Date(e.at).toLocaleDateString("en-IN",
        { weekday: "short", day: "2-digit", month: "short", year: "numeric" });
      if (out[out.length - 1]?.day !== day) out.push({ day, items: [] });
      out[out.length - 1].items.push(e);
    }
    return out;
  }, [shown]);

  if (!ready || !session) return null;

  const rail = (
    <>
      <RailCard title="Why this is worth having">
        <p className="text-2xs leading-relaxed text-ink-soft">
          The record is append-only <b className="text-ink">for everyone, ministry
          included</b> — the database rejects UPDATE and DELETE on this table outright,
          rather than checking a role. A log that a privileged account can edit proves
          nothing at all, which is the whole reason this one is enforced in the schema and
          not in the application.
        </p>
      </RailCard>

      {kinds.length > 0 && (
        <RailCard title="By kind">
          <ul className="space-y-1">
            {kinds.map(([k, n]) => (
              <li key={k}>
                <button onClick={() => setFilter(filter === k ? null : k)}
                        aria-pressed={filter === k}
                        className={`flex w-full items-center gap-2 rounded px-2 py-1.5
                                    text-left transition-colors ${
                          filter === k ? "bg-brand-soft text-brand" : "hover:bg-paper-soft"}`}>
                  <Icon name={meta(k).icon} className={`w-3.5 h-3.5 shrink-0 ${meta(k).tone}`} />
                  <span className="min-w-0 flex-1 truncate text-2xs text-ink-soft">
                    {meta(k).label}
                  </span>
                  <span className="shrink-0 text-2xs font-semibold tabular-nums text-ink">
                    {n}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </RailCard>
      )}
    </>
  );

  return (
    <AppShell title="Audit trail"
              subtitle="Every appraisal, decision and export, in the order it happened."
              rail={rail}
              actions={filter ? (
                <button onClick={() => setFilter(null)} className="btn btn-sm btn-quiet">
                  <Icon name="close" className="w-3.5 h-3.5" /> Clear filter
                </button>
              ) : undefined}>
      {loading ? (
        <div className="card p-4 shadow-card"><TableSkeleton rows={6} cols={4} /></div>
      ) : shown.length === 0 ? (
        <Empty title={filter ? "No events of that kind" : "No events yet"}
               hint="Actions are recorded here as reports are appraised and decided." />
      ) : (
        <div ref={reveal} className="space-y-5">
          {days.map(({ day, items }) => (
            <section key={day} data-reveal>
              <h2 className="mb-2 flex items-center gap-2 text-2xs font-semibold uppercase
                             tracking-wide text-ink-faint">
                {day}
                <span className="tabular-nums">· {items.length}</span>
                <span className="h-px flex-1 bg-paper-edge" />
              </h2>
              <ol className="card overflow-hidden shadow-card">
                {items.map((e) => {
                  const m = meta(e.action);
                  return (
                    <li key={e.id} className="flex gap-3 border-b border-paper-edge px-4 py-3
                                              last:border-0">
                      <span aria-hidden className="mt-0.5 grid h-7 w-7 shrink-0 place-items-center
                                                   rounded-full bg-paper-soft">
                        <Icon name={m.icon} className={`w-3.5 h-3.5 ${m.tone}`} />
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className="flex flex-wrap items-baseline gap-x-2 text-xs">
                          <span className="font-medium text-ink">{m.label}</span>
                          <span className="capitalize text-ink-faint">
                            by {e.actor_role ?? "the system"}
                          </span>
                          <span className="ml-auto shrink-0 tabular-nums text-2xs text-ink-faint">
                            {new Date(e.at).toLocaleTimeString("en-IN",
                              { hour: "2-digit", minute: "2-digit" })}
                          </span>
                        </p>
                        {e.detail && Object.keys(e.detail).length > 0 && (
                          <dl className="mt-1 flex flex-wrap gap-x-4 gap-y-0.5">
                            {Object.entries(e.detail).slice(0, 5).map(([k, v]) => (
                              <div key={k} className="flex gap-1 text-2xs">
                                <dt className="text-ink-ghost">{k.replace(/_/g, " ")}:</dt>
                                <dd className="text-ink-soft">{String(v)}</dd>
                              </div>
                            ))}
                          </dl>
                        )}
                        {/* An event outlives the report it describes, so `dpr_id` alone
                            was not enough to offer a link — a removed report gave an
                            "Open the report" that landed on an empty review screen. The
                            title comes back only while the report is still held, so it is
                            the thing that decides. */}
                        {e.dpr_id && (e.dpr_title ? (
                          <a href={`/review/${e.dpr_id}`}
                             className="mt-1 inline-flex items-center gap-1 text-2xs text-brand
                                        hover:underline">
                            Open {e.dpr_title}
                            <Icon name="chevronRight" className="w-3 h-3" />
                          </a>
                        ) : (
                          <p className="mt-1 inline-flex items-center gap-1 text-2xs text-ink-ghost">
                            <Icon name="ban" className="w-3 h-3" />
                            The report is no longer held — the event stays on the record
                          </p>
                        ))}
                      </div>
                    </li>
                  );
                })}
              </ol>
            </section>
          ))}
        </div>
      )}
    </AppShell>
  );
}
