"use client";
import { useRouter } from "next/navigation";

import type { DprRow } from "@/lib/api";
import { Chip, DPR_STATUS, Empty, ScoreBadge, TableSkeleton } from "./bits";

export type { DprRow };

export function DprTable({ rows, hrefBase, loading }: {
  rows: DprRow[]; hrefBase: string; loading?: boolean;
}) {
  const router = useRouter();
  if (loading) return <TableSkeleton rows={5} cols={5} />;
  if (rows.length === 0) {
    return <Empty title="Nothing here yet"
                  hint="Reports appear here once they have been uploaded and processed." />;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-2xs uppercase tracking-wide text-ink-faint
                         border-b border-paper-edge">
            <th className="py-2.5 pr-4 font-semibold">Project</th>
            <th className="py-2.5 pr-4 font-semibold w-36">Status</th>
            <th className="py-2.5 pr-4 font-semibold w-20 text-right">Score</th>
            <th className="py-2.5 pr-4 font-semibold w-32 text-right">Findings</th>
            <th className="py-2.5 font-semibold w-28">Submitted</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id}
                onClick={() => router.push(`${hrefBase}/${r.id}`)}
                className="row-link border-b border-paper-edge/60 last:border-0">
              <td className="py-3 pr-4">
                <span className="text-brand font-medium hover:underline">{r.title}</span>
                {r.is_self_check && (
                  <span className="ml-2 chip bg-paper-deep text-ink-soft border-paper-edge">
                    private check
                  </span>
                )}
              </td>
              <td className="py-3 pr-4">
                <Chip meta={DPR_STATUS[r.status] ?? { label: r.status, cls: "bg-paper-deep text-ink-soft border-paper-edge" }} dot />
              </td>
              <td className="py-3 pr-4 text-right"><ScoreBadge score={r.overall_score} /></td>
              <td className="py-3 pr-4 text-right tabular-nums text-ink-soft">
                {r.finding_count ?? "—"}
                {!!r.critical_count && (
                  <span className="ml-2 chip bg-sev-critical-soft text-sev-critical
                                   border-sev-critical/25">
                    {r.critical_count} critical
                  </span>
                )}
              </td>
              <td className="py-3 text-ink-faint text-xs whitespace-nowrap">
                {new Date(r.created_at).toLocaleDateString("en-IN",
                  { day: "2-digit", month: "short", year: "numeric" })}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
