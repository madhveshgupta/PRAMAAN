"use client";
/**
 * The evidence split — the product's signature gesture.
 *
 *  The claim and its proof are the same object, and this is the piece of the interface that
 *  has to say so. Reading a finding, you click its page reference; the reading column moves
 *  aside and the document arrives beside it, already on the right page with the right
 *  region lit. The shape is borrowed on purpose from the window snap every officer already
 *  has on their desktop — two panes, a seam you can drag, and presets — so the gesture
 *  needs no instruction.
 *
 *  What makes it a split and not a modal: the finding you were reading stays on screen,
 *  in place, at the same scroll position. A dialog over the top would answer "what does the
 *  page say" and lose "what was the claim" — which is the comparison the officer is here to
 *  make, and the one an RTI reply two years later has to be able to reconstruct.
 *
 *  Constraints held here rather than at the call sites:
 *    · the seam is ONE CSS variable, so the two panes can never disagree about where it is,
 *      and the closed layout is correct with no JavaScript at all (`--split-left: 100%`);
 *    · below `lg` there is no split — a 27rem-wide PDF page is unreadable, so the document
 *      arrives as a full sheet instead. Same state, different geometry;
 *    · when closed the document pane is `inert`, so it is not in the tab order and a
 *      keyboard user cannot land inside a pane they cannot see.
 */
import { useCallback, useEffect, useRef, useState } from "react";

import { Icon } from "@/components/ui/Icon";
import { exitToRight, enterFromRight, flashSnapGhost, prefersReduced, snapTo } from "@/lib/motion";

/** The presets, in the order the toolbar shows them. 62 rather than 50 is the default
 *  because the reading column carries prose and the document carries a page: prose at
 *  half a 1366px screen wraps at about nine words, which is where reading speed falls off. */
const PRESETS = [
  { pct: 100, icon: "close" as const,       label: "Close the document" },
  { pct: 62,  icon: "columns" as const,     label: "Split — reading wide" },
  { pct: 38,  icon: "expandRight" as const, label: "Split — document wide" },
  { pct: 6,   icon: "expandLeft" as const,  label: "Document almost full width" },
];

export function EvidenceSplit({
  open, onClose, reading, document: doc, documentTitle, hint,
}: {
  open: boolean;
  onClose: () => void;
  reading: React.ReactNode;
  document: React.ReactNode;
  documentTitle?: string;
  /** One line naming what is currently shown in the document pane. */
  hint?: React.ReactNode;
}) {
  const host = useRef<HTMLDivElement>(null);
  const pane = useRef<HTMLDivElement>(null);
  const [pct, setPct] = useState(100);
  const [dragging, setDragging] = useState(false);
  // Mounted on first open and kept mounted: closing must not throw away a 300-page document
  // that took four seconds to fetch, and reopening it must be instant.
  const [everOpened, setEverOpened] = useState(false);

  const applySplit = useCallback((next: number, ghost = false) => {
    setPct(next);
    if (ghost && next < 100) flashSnapGhost(host.current, next);
    snapTo(host.current, next);
  }, []);

  useEffect(() => {
    if (open) {
      setEverOpened(true);
      // One frame, so the pane exists before it is asked to move.
      requestAnimationFrame(() => {
        applySplit(62, true);
        enterFromRight(pane.current);
      });
    } else if (pct < 100) {
      exitToRight(pane.current, () => applySplit(100));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  /* --- drag the seam ---------------------------------------------------------------- */
  useEffect(() => {
    if (!dragging) return;
    const move = (e: PointerEvent) => {
      const box = host.current?.getBoundingClientRect();
      if (!box) return;
      // Clamped: neither pane may be squeezed to a sliver you cannot read or close.
      const next = Math.min(88, Math.max(18, ((e.clientX - box.left) / box.width) * 100));
      setPct(next);
      host.current?.style.setProperty("--split-left", `${next}%`);
    };
    const up = () => setDragging(false);
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
    return () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };
  }, [dragging]);

  /* --- keyboard --------------------------------------------------------------------- */
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const typing = /^(INPUT|TEXTAREA)$/.test((e.target as HTMLElement)?.tagName ?? "");
      if (typing) return;
      if (e.key === "Escape" && open) { e.preventDefault(); onClose(); return; }
      if (!open || !(e.metaKey || e.ctrlKey)) return;
      if (e.key === "\\") { e.preventDefault(); applySplit(pct === 62 ? 38 : 62, true); }
      if (e.key === "[")  { e.preventDefault(); applySplit(Math.max(18, pct - 12)); }
      if (e.key === "]")  { e.preventDefault(); applySplit(Math.min(88, pct + 12)); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, pct, onClose, applySplit]);

  const closed = !open;

  return (
    <div ref={host}
         className="split-grid relative min-h-0 flex-1"
         style={{ ["--split-left" as string]: prefersReduced() && open ? "62%" : "100%" }}>
      {/* --- the reading column ------------------------------------------------------ */}
      <div className="min-w-0 overflow-y-auto scroll-slim">{reading}</div>

      {/* --- the seam ---------------------------------------------------------------- */}
      {!closed && (
        <div role="separator" aria-orientation="vertical" tabIndex={0}
             aria-label="Resize the document pane. Left and right arrows adjust it."
             data-dragging={dragging}
             onPointerDown={(e) => { e.preventDefault(); setDragging(true); }}
             onDoubleClick={() => applySplit(62, true)}
             onKeyDown={(e) => {
               if (e.key === "ArrowLeft")  { e.preventDefault(); applySplit(Math.max(18, pct - 6)); }
               if (e.key === "ArrowRight") { e.preventDefault(); applySplit(Math.min(88, pct + 6)); }
             }}
             className="split-handle no-print absolute inset-y-0 z-20 hidden md:block"
             style={{ left: "var(--split-left)", marginLeft: -3 }}>
          <span aria-hidden
                className="absolute left-1/2 top-1/2 h-10 w-1 -translate-x-1/2 -translate-y-1/2
                           rounded-full bg-ink-ghost/50" />
        </div>
      )}

      {/* --- the document pane -------------------------------------------------------
          Below `md` this is a full sheet rather than a column: a document page squeezed
          into 38% of a phone is a picture of a page, not a page you can check a figure on. */}
      <div ref={pane}
           inert={closed}
           aria-hidden={closed}
           className={`no-print flex min-w-0 flex-col overflow-hidden border-l
                       border-paper-edge bg-paper-deep
                       max-md:fixed max-md:inset-0 max-md:z-50 max-md:border-l-0
                       ${closed ? "pointer-events-none max-md:hidden" : ""}`}>
        <div className="flex h-12 shrink-0 items-center gap-2 border-b border-paper-edge
                        bg-paper px-3">
          <Icon name="link" className="w-4 h-4 shrink-0 text-brand" />
          <div className="min-w-0 flex-1">
            <p className="truncate text-xs font-medium text-ink">
              {documentTitle ?? "Source document"}
            </p>
            {hint && <p className="truncate text-2xs text-ink-faint">{hint}</p>}
          </div>

          <div className="flex shrink-0 items-center gap-0.5">
            {PRESETS.map((p) => (
              <button key={p.pct} type="button" title={p.label} aria-label={p.label}
                      onClick={() => (p.pct === 100 ? onClose() : applySplit(p.pct, true))}
                      aria-pressed={p.pct !== 100 && Math.abs(pct - p.pct) < 2}
                      className={`hidden h-8 w-8 place-items-center rounded transition-colors
                                  md:grid ${
                        p.pct !== 100 && Math.abs(pct - p.pct) < 2
                          ? "bg-brand-soft text-brand"
                          : "text-ink-soft hover:bg-paper-deep hover:text-ink"}`}>
                <Icon name={p.icon} className="w-4 h-4" />
              </button>
            ))}
            <button type="button" onClick={onClose} aria-label="Close the document"
                    className="grid h-8 w-8 place-items-center rounded text-ink-soft
                               transition-colors hover:bg-sev-critical-soft
                               hover:text-sev-critical md:hidden">
              <Icon name="close" className="w-4 h-4" />
            </button>
          </div>
        </div>

        <div className="min-h-0 flex-1">{everOpened ? doc : null}</div>

        <p className="hidden shrink-0 border-t border-paper-edge bg-paper px-3 py-1.5
                      text-2xs text-ink-faint md:block">
          Drag the seam to resize · <kbd className="font-mono">Esc</kbd> closes ·{" "}
          <kbd className="font-mono">⌘\</kbd> swaps which side is wide
        </p>
      </div>
    </div>
  );
}
