"use client";
/**
 * The route from a claim to its proof.
 *
 *  This is the loudest affordance in the product and it is supposed to be. Everything else
 *  on a finding card — the severity, the wording, the suggested action — is the system's
 *  opinion. This strip is the only part that is checkable, and the test the whole design is
 *  judged against is whether a stranger can find it in under three seconds.
 *
 *  So it is not a small blue "p.12" at the end of a sentence, which is what it used to be.
 *  It is a bordered block with its own heading, one row per place in the document, each row
 *  carrying the page, the sentence that was actually found there, how it was found, and how
 *  confident the match is. Clicking a row opens the document beside this one at that page.
 *
 *  The wording matters as much as the layout: "3 places in the document" rather than
 *  "3 anchors". An officer writing an appraisal note has to be able to repeat this sentence
 *  in it.
 */
import { useRef } from "react";

import { ConfidenceMeter } from "@/components/charts/Figures";
import { Icon } from "@/components/ui/Icon";
import { handOff } from "@/lib/motion";
import type { EvidenceAnchor } from "@/lib/api";

const METHOD_WORD: Record<string, string> = {
  exact: "exact text match",
  span: "matched against the parsed text",
  fuzzy: "close text match",
  table: "read from a table cell",
  ocr: "read by character recognition",
  regex: "matched by rule",
  llm_verified: "model-proposed, then located in the text",
};

function methodWord(m: string) {
  return METHOD_WORD[m] ?? m.replace(/_/g, " ");
}

export function EvidenceRoute({
  evidence, activeIndex, onOpen, dense = false, heading,
}: {
  evidence: EvidenceAnchor[];
  /** Which anchor the document pane is currently showing, if this row drives it. */
  activeIndex?: number | null;
  onOpen: (index: number) => void;
  dense?: boolean;
  heading?: string;
}) {
  const first = useRef<HTMLButtonElement>(null);

  if (!evidence?.length) {
    // The honest empty state. "No evidence found" is a statement about the document; it is
    // never dressed up as a pass, and it is never silently omitted.
    return (
      <p className="flex items-start gap-2 rounded border border-dashed border-paper-edge
                    bg-paper-soft px-3 py-2.5 text-2xs leading-relaxed text-ink-soft">
        <Icon name="ban" className="mt-px w-3.5 h-3.5 shrink-0 text-ink-ghost" />
        <span>
          <b className="text-ink">No page to cite.</b> Nothing in this document could be
          located to support or contradict this — which is not the same as the requirement
          having been missed.
        </span>
      </p>
    );
  }

  const pages = Array.from(new Set(evidence.map((e) => e.page)));

  return (
    <div className="overflow-hidden rounded border border-brand/20 bg-brand-soft/40">
      <div className="flex items-center gap-2 border-b border-brand/15 px-3 py-1.5">
        <Icon name="link" className="w-3.5 h-3.5 shrink-0 text-brand" />
        <p className="text-2xs font-semibold uppercase tracking-wide text-brand">
          {heading ?? "Evidence"}
        </p>
        <p className="ml-auto text-2xs text-ink-soft">
          {evidence.length} place{evidence.length === 1 ? "" : "s"} in the document
          {pages.length > 1 && (
            <span className="text-ink-faint"> · pages {pages.join(", ")}</span>
          )}
        </p>
      </div>

      <ul className="divide-y divide-brand/10">
        {evidence.slice(0, dense ? 2 : evidence.length).map((a, i) => {
          const active = activeIndex === i;
          return (
            <li key={`${a.page}-${i}`}>
              <button ref={i === 0 ? first : undefined}
                      type="button"
                      onClick={(e) => { handOff(e.currentTarget); onOpen(i); }}
                      aria-pressed={active}
                      aria-label={`Open page ${a.page} with this region highlighted`}
                      className={`group flex w-full items-start gap-2.5 px-3 py-2.5 text-left
                                  transition-colors ${
                        active ? "bg-brand-soft" : "hover:bg-brand-soft/70"}`}>
                <span className={`mt-px shrink-0 rounded px-1.5 py-0.5 text-2xs font-semibold
                                  tabular-nums transition-colors ${
                  active ? "bg-brand text-white" : "bg-paper text-brand ring-1 ring-brand/25"}`}>
                  p.{a.page}
                </span>

                <span className="min-w-0 flex-1">
                  {a.snippet && (
                    <span className="block text-2xs italic leading-relaxed text-ink">
                      “{a.snippet.length > 220 ? `${a.snippet.slice(0, 220)}…` : a.snippet}”
                    </span>
                  )}
                  <span className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1">
                    <ConfidenceMeter value={a.confidence} />
                    <span className="text-2xs text-ink-faint">{methodWord(a.method)}</span>
                    {a.source && (
                      <span className="text-2xs text-ink-faint">· {a.source}</span>
                    )}
                  </span>
                </span>

                <span aria-hidden
                      className="mt-0.5 flex shrink-0 items-center gap-1 text-2xs font-medium
                                 text-brand opacity-0 transition-opacity
                                 group-hover:opacity-100 group-focus-visible:opacity-100">
                  Open
                  <Icon name="arrow" className="w-3.5 h-3.5" />
                </span>
              </button>
            </li>
          );
        })}
      </ul>

      {dense && evidence.length > 2 && (
        <button type="button" onClick={() => onOpen(0)}
                className="w-full border-t border-brand/10 px-3 py-1.5 text-2xs font-medium
                           text-brand transition-colors hover:bg-brand-soft">
          + {evidence.length - 2} more place{evidence.length - 2 === 1 ? "" : "s"} in the document
        </button>
      )}
    </div>
  );
}

/** The one-line form, for a table row or a dense list where a full strip would not fit.
 *  Still a real button with a real label — never a bare "p.12" you have to guess is live. */
export function EvidenceLink({ evidence, onOpen, active }: {
  evidence: EvidenceAnchor[]; onOpen: () => void; active?: boolean;
}) {
  if (!evidence?.length) {
    return <span className="text-2xs text-ink-ghost">no page to cite</span>;
  }
  const pages = Array.from(new Set(evidence.map((e) => e.page)));
  return (
    <button type="button" onClick={(e) => { handOff(e.currentTarget); onOpen(); }}
            aria-pressed={active}
            aria-label={`Open page ${pages[0]} with the supporting region highlighted`}
            className={`inline-flex shrink-0 items-center gap-1 rounded px-1.5 py-0.5 text-2xs
                        font-semibold tabular-nums transition-colors ${
              active ? "bg-brand text-white"
                     : "bg-brand-soft text-brand ring-1 ring-brand/20 hover:bg-brand hover:text-white"}`}>
      <Icon name="link" className="w-3 h-3" />
      p.{pages[0]}{pages.length > 1 && ` +${pages.length - 1}`}
    </button>
  );
}
