"use client";
/**
 * Every figure the system took out of the document — and every figure it refused to.
 *
 *  The refusal list is the point of this page. The guarantee this product makes is not
 *  "the model does not hallucinate", which nobody can promise; it is that a value the model
 *  could not locate inside its own cited evidence never becomes an output. That is only a
 *  guarantee anyone can believe if the refusals are visible, so they are shown at the same
 *  size as the accepted values rather than logged somewhere an officer will never look.
 *
 *  The diagram at the top exists because the guard has two steps and almost everyone
 *  assumes it has one. Locating the quotation is not enough: a model can quote a real
 *  sentence from the report and attach a fabricated number to it, and span-only
 *  verification accepts that. The value has to appear INSIDE the span that was found.
 */
import { useMemo, useState } from "react";

import { ConfidenceMeter } from "@/components/charts/Figures";
import { Chip, Empty } from "@/components/ui/bits";
import { Icon } from "@/components/ui/Icon";
import { useReveal } from "@/lib/motion";
import { EvidenceRoute } from "./EvidenceRoute";
import type { ViewProps } from "./types";
import type { Extraction, ExtractedFieldRow } from "@/lib/api";

const STATUS: Record<string, { label: string; cls: string }> = {
  found: { label: "✓ Located in the document", cls: "bg-ok-soft text-ok border-ok/25" },
  not_found: { label: "Not found", cls: "bg-paper-deep text-ink-soft border-paper-edge" },
  not_extracted: { label: "Not extracted", cls: "bg-paper-deep text-ink-soft border-paper-edge" },
  needs_human_verification: {
    label: "⚑ Needs an officer's eye",
    cls: "bg-sev-medium-soft text-sev-medium border-sev-medium/25" },
};

function label(key: string) {
  return key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

/* ------------------------------------------------------------------- the guard, drawn -- */

const STEPS = [
  { n: 1, icon: "cpu" as const, title: "The model proposes",
    body: "It returns a value and quotes the sentence it says the value came from." },
  { n: 2, icon: "search" as const, title: "The quote must exist",
    body: "That sentence is looked for in the text parsed from the PDF. If it is not there, the value is refused." },
  { n: 3, icon: "target" as const, title: "The value must be inside it",
    body: "The number itself must appear within the located sentence. A real quote with an invented figure attached fails here." },
  { n: 4, icon: "lock" as const, title: "Only then is it stored",
    body: "Stored with the page and the box on it. Anything that failed is recorded as refused and never shown as a value." },
];

function GuardDiagram({ stored, refused, llmRan }: {
  stored: number; refused: number; llmRan: boolean;
}) {
  const [open, setOpen] = useState(false);
  return (
    <section className="overflow-hidden rounded-card border border-brand/20
                        bg-gradient-to-br from-brand-soft/70 to-paper shadow-card">
      <div className="flex flex-wrap items-center gap-3 px-4 py-3">
        <span aria-hidden className="grid h-10 w-10 shrink-0 place-items-center rounded-card
                                     bg-brand text-white">
          <Icon name="shield" className="w-5 h-5" />
        </span>
        <div className="min-w-0 flex-1">
          <h2 className="display text-sm font-bold text-ink">
            How a number gets into this system
          </h2>
          <p className="mt-0.5 text-2xs leading-relaxed text-ink-soft">
            No value is stored unless it can be found inside the evidence cited for it.
            {" "}
            <b className="tabular-nums text-ink">{stored} stored</b>
            {refused > 0 && (
              <> · <b className="tabular-nums text-sev-high">{refused} refused</b></>
            )}
            {" "}on this report.
          </p>
        </div>
        <button onClick={() => setOpen((v) => !v)} aria-expanded={open}
                className="btn btn-sm btn-ghost shrink-0">
          <Icon name="chevronDown"
                className={`w-3.5 h-3.5 transition-transform duration-200 ${open ? "rotate-180" : ""}`} />
          {open ? "Hide" : "Show the four steps"}
        </button>
      </div>

      {open && (
        <div className="border-t border-brand/15 bg-paper/70 px-4 py-4 animate-sweep-in">
          <ol className="grid gap-3 lg:grid-cols-4">
            {STEPS.map((s, i) => (
              <li key={s.n} className="relative">
                {/* The connector, drawn only between steps and only where they sit in a row.
                    An arrow that wraps to the next line points at nothing. */}
                {i < STEPS.length - 1 && (
                  <span aria-hidden
                        className="absolute right-[-14px] top-6 hidden text-brand/40 lg:block">
                    <Icon name="arrow" className="w-5 h-5" />
                  </span>
                )}
                <div className="h-full rounded-card border border-paper-edge bg-paper p-3">
                  <div className="flex items-center gap-2">
                    <span aria-hidden className="grid h-7 w-7 place-items-center rounded-full
                                                 bg-brand-soft text-brand">
                      <Icon name={s.icon} className="w-3.5 h-3.5" />
                    </span>
                    <span className="text-2xs font-semibold tabular-nums text-ink-ghost">
                      Step {s.n}
                    </span>
                  </div>
                  <p className="mt-2 text-xs font-semibold text-ink">{s.title}</p>
                  <p className="mt-1 text-2xs leading-relaxed text-ink-soft">{s.body}</p>
                </div>
              </li>
            ))}
          </ol>

          <p className="mt-3 flex gap-2 rounded border-l-2 border-gold px-3 py-2 text-2xs
                        leading-relaxed text-ink-soft">
            <Icon name="flag" className="mt-px w-3.5 h-3.5 shrink-0 text-gold-deep" />
            <span>
              Step 3 is the one that is usually missing. Proving the quotation exists is not
              enough — a model can quote a real sentence from the report and attach a figure
              that is not in it. Verifying the span alone accepts that; requiring the value
              to sit inside the span does not.
            </span>
          </p>

          {!llmRan && (
            <p className="mt-2 flex gap-2 rounded bg-paper-soft px-3 py-2 text-2xs
                          leading-relaxed text-ink-soft">
              <Icon name="cpu" className="mt-px w-3.5 h-3.5 shrink-0 text-ink-faint" />
              <span>
                For this report no model extraction ran — every value below came from rules.
                The guard therefore had nothing to check, which is <b>not</b> the same as
                having checked and found nothing.
              </span>
            </p>
          )}
        </div>
      )}
    </section>
  );
}

/* ---------------------------------------------------------------------------- the page -- */

export function ValuesView({ extraction, onOpen, activeKey }: ViewProps & {
  extraction: Extraction | null;
}) {
  const [q, setQ] = useState("");
  const reveal = useReveal<HTMLDivElement>({ immediate: true, deps: [extraction?.fields.length] });

  const fields = useMemo(() => {
    const list = extraction?.fields ?? [];
    if (!q.trim()) return list;
    const n = q.toLowerCase();
    return list.filter((f) =>
      f.field_key.toLowerCase().includes(n) || (f.value ?? "").toLowerCase().includes(n));
  }, [extraction, q]);

  if (!extraction) {
    return <Empty title="Nothing extracted yet"
                  hint="Values appear once the document has been read." />;
  }

  const blocked = extraction.blocked_values;
  const llmRan = (extraction.llm_fields ?? 0) > 0;

  return (
    <div ref={reveal} className="space-y-4">
      <div data-reveal>
        <GuardDiagram stored={extraction.fields.length} refused={blocked.length}
                      llmRan={llmRan} />
      </div>

      {/* --- refused first. It is the shorter list and the more important one. --------- */}
      <section data-reveal>
        <h2 className="mb-2 flex items-center gap-2 text-2xs font-semibold uppercase
                       tracking-wide text-ink-faint">
          Refused
          <span className="tabular-nums">· {blocked.length}</span>
          <span className="h-px flex-1 bg-paper-edge" />
        </h2>

        {blocked.length === 0 ? (
          <p className="card px-4 py-3 text-2xs leading-relaxed text-ink-soft shadow-card">
            {llmRan
              ? "Nothing was blocked for this document. Every value the model stated was found inside the evidence it cited."
              : "No model extraction ran for this document, so the guard had nothing to check. Every value below came from rules applied directly to the parsed text."}
          </p>
        ) : (
          <ul className="overflow-hidden rounded-card border border-sev-high/25
                         bg-sev-high-soft/30 shadow-card">
            {blocked.map((b, i) => (
              <li key={i} className="border-b border-sev-high/15 px-4 py-3 last:border-0">
                <div className="flex flex-wrap items-baseline gap-2">
                  <span className="text-xs font-semibold text-ink">{label(b.field_key)}</span>
                  <span className="chip border-sev-high/25 bg-paper text-sev-high">
                    ✗ not stored
                  </span>
                </div>
                <p className="mt-1 text-sm tabular-nums text-sev-high line-through">
                  {b.claimed_value ?? "—"}
                </p>
                <p className="mt-1 text-2xs leading-relaxed text-ink-soft">{b.reason}</p>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* --- what was kept ------------------------------------------------------------ */}
      <section data-reveal>
        <div className="mb-2 flex flex-wrap items-center gap-2">
          <h2 className="flex items-center gap-2 text-2xs font-semibold uppercase
                         tracking-wide text-ink-faint">
            Stored, with the page it came from
            <span className="tabular-nums">· {extraction.fields.length}</span>
          </h2>
          <div className="no-print relative ml-auto w-48">
            <Icon name="search"
                  className="pointer-events-none absolute left-2.5 top-1/2 w-3.5 h-3.5
                             -translate-y-1/2 text-ink-ghost" />
            <input value={q} onChange={(e) => setQ(e.target.value)}
                   aria-label="Search extracted values" placeholder="Search values"
                   className="field py-1 pl-8 text-2xs" />
          </div>
        </div>

        {fields.length === 0 ? (
          <Empty title="No values match that search" />
        ) : (
          <ul className="space-y-2.5">
            {fields.map((f: ExtractedFieldRow, i) => {
              const key = `${f.field_key}-${i}`;
              return (
                <li key={key}
                    className={`card overflow-hidden p-3.5 shadow-card transition-colors ${
                      activeKey === key ? "border-brand/50 ring-1 ring-brand/25" : ""}`}>
                  <div className="flex flex-wrap items-baseline gap-2">
                    <span className="text-xs font-semibold text-ink">
                      {label(f.field_key)}
                    </span>
                    <Chip meta={STATUS[f.status] ?? STATUS.not_extracted} />
                    {f.needs_verification && (
                      <span className="chip border-sev-medium/25 bg-sev-medium-soft text-sev-medium">
                        confirm against the page
                      </span>
                    )}
                    <span className="ml-auto">
                      <ConfidenceMeter value={f.confidence} label="confidence" />
                    </span>
                  </div>

                  <p className="mt-1.5 display text-xl font-bold tabular-nums text-ink">
                    {f.value ?? <span className="text-base font-normal text-ink-ghost">not found</span>}
                    {f.unit && (
                      <span className="ml-1.5 text-xs font-normal text-ink-faint">{f.unit}</span>
                    )}
                  </p>

                  {f.evidence.length > 0 && (
                    <div className="mt-2.5">
                      <EvidenceRoute evidence={f.evidence} dense
                                     heading="Where this number is written"
                                     activeIndex={activeKey === key ? 0 : null}
                                     onOpen={(idx) => onOpen(f.evidence, "info", idx, key)} />
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </div>
  );
}
