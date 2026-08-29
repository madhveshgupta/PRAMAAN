"use client";
/**
 * PDF.js viewer with the highlight overlay.
 *
 * Only the visible page is rendered — a 300-page document must never put 300 canvases in
 * memory. The neighbouring pages are pre-fetched so stepping through a multi-anchor
 * finding does not stall.
 *
 * Highlight geometry is the whole point of the product. Boxes arrive normalised to 0–1
 * against page size, so drawing one is a multiplication against whatever size the page was
 * rendered at — which is what makes it land correctly at every zoom level with no per-zoom
 * bookkeeping at all.
 */
import { useCallback, useEffect, useRef, useState } from "react";

import { prefersReduced } from "@/lib/motion";
import { getSession, type EvidenceAnchor } from "@/lib/api";

const FILL: Record<string, string> = {
  critical: "rgba(196, 62, 74, 0.38)",
  high: "rgba(214, 130, 40, 0.38)",
  medium: "rgba(196, 165, 52, 0.40)",
  low: "rgba(130, 143, 156, 0.34)",
  info: "rgba(52, 118, 176, 0.34)",
};

export interface ViewerTarget {
  page: number;
  anchors: EvidenceAnchor[];
  severity: string;
  nonce: number;
}

export function PdfViewer({ documentId, target }: {
  documentId: string; target: ViewerTarget | null;
}) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const pdfRef = useRef<any>(null);
  const taskRef = useRef<any>(null);

  const [pageCount, setPageCount] = useState(0);
  const [page, setPage] = useState(1);
  const [pageInput, setPageInput] = useState("1");
  const [zoom, setZoom] = useState(1.2);
  const [fitWidth, setFitWidth] = useState(true);
  const [size, setSize] = useState({ w: 0, h: 0 });
  const [loading, setLoading] = useState(true);
  const [rendering, setRendering] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => { setPageInput(String(page)); }, [page]);

  // --- load once -------------------------------------------------------------------
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const pdfjs = await import("pdfjs-dist");
        pdfjs.GlobalWorkerOptions.workerSrc = "/pdf.worker.min.mjs";

        // PDF.js fetches the file itself and knows nothing about the API helper, so the
        // bearer token has to be handed to it explicitly — the document endpoint is
        // access-scoped like everything else.
        const token = getSession()?.access_token;
        if (!token) throw new Error("Not signed in");

        const doc = await pdfjs.getDocument({
          url: `/api/v1/documents/${documentId}/pdf`,
          httpHeaders: { Authorization: `Bearer ${token}` },
          withCredentials: false,
        }).promise;
        if (cancelled) return;
        pdfRef.current = doc;
        setPageCount(doc.numPages);
        setLoading(false);
      } catch (e: any) {
        if (cancelled) return;
        const msg = String(e?.message ?? "");
        setError(msg.includes("401")
          ? "Your session expired while the document was loading. Sign in again."
          : msg || "Could not open the document");
        setLoading(false);
      }
    })();
    return () => { cancelled = true; taskRef.current?.cancel(); };
  }, [documentId]);

  // --- render current page ---------------------------------------------------------
  const render = useCallback(async () => {
    const doc = pdfRef.current, canvas = canvasRef.current, wrap = wrapRef.current;
    if (!doc || !canvas || !wrap) return;

    // Cancel any in-flight render: stepping quickly otherwise throws "Cannot use the same
    // canvas during multiple render() operations".
    taskRef.current?.cancel();
    setRendering(true);

    // Fit-to-width needs a laid-out container. Measured at 0 — which happens on the very
    // first paint — the clamp below would silently render the page at 40% and leave a
    // sliver. Bail instead; the ResizeObserver fires as soon as the width is real.
    if (fitWidth && wrap.clientWidth < 100) { setRendering(false); return; }

    const p = await doc.getPage(page);
    const base = p.getViewport({ scale: 1 });
    const scale = fitWidth
      ? Math.max(0.4, (wrap.clientWidth - 56) / base.width)
      : zoom;
    const viewport = p.getViewport({ scale });

    const ratio = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.floor(viewport.width * ratio);
    canvas.height = Math.floor(viewport.height * ratio);
    canvas.style.width = `${viewport.width}px`;
    canvas.style.height = `${viewport.height}px`;
    setSize({ w: viewport.width, h: viewport.height });

    const ctx = canvas.getContext("2d")!;
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    const task = p.render({ canvasContext: ctx, viewport, canvas });
    taskRef.current = task;
    try { await task.promise; }
    catch (e: any) { if (e?.name !== "RenderingCancelledException") throw e; }
    finally { setRendering(false); }

    // warm the neighbours so stepping evidence does not stall
    for (const n of [page + 1, page - 1]) {
      if (n >= 1 && n <= doc.numPages) doc.getPage(n).catch(() => {});
    }
  }, [page, zoom, fitWidth]);

  // `loading` and `error` are dependencies, not decoration. The canvas is only in the DOM
  // once both are false, so the first run of this effect finds `canvasRef.current === null`
  // and returns early — and nothing re-triggers it, because `render` only changes with
  // page/zoom/fitWidth. The first page was therefore drawn only when the ResizeObserver
  // happened to fire after the canvas mounted, which is why it failed intermittently and
  // left a blank sheet behind.
  useEffect(() => {
    if (loading || error) return;
    void render();
  }, [loading, error, render]);

  // Trailing-edge only. The evidence split animates this pane's width for ~440ms, which
  // fires the observer on every frame; re-rasterising a page 26 times to land on the same
  // size makes the snap stutter on exactly the machines this is built for. Render once the
  // width has stopped changing.
  useEffect(() => {
    if (!fitWidth) return;
    let t: number | undefined;
    const ro = new ResizeObserver(() => {
      window.clearTimeout(t);
      t = window.setTimeout(() => void render(), 90);
    });
    if (wrapRef.current) ro.observe(wrapRef.current);
    return () => { ro.disconnect(); window.clearTimeout(t); };
  }, [fitWidth, render]);

  // The arrival. Moving to the right page is not enough on a dense A4 sheet — the reader
  // still has to find the region. Scroll so the FIRST anchor sits a third of the way down
  // the pane, which is where the eye goes, rather than to the top of the page.
  useEffect(() => {
    if (!target) return;
    setPage(target.page);
    const wrap = wrapRef.current;
    if (!wrap) return;
    const first = target.anchors[0];
    const settle = window.setTimeout(() => {
      const top = first && size.h
        ? Math.max(0, first.bbox[1] * size.h - wrap.clientHeight * 0.32)
        : 0;
      wrap.scrollTo({ top, behavior: prefersReduced() ? "auto" : "smooth" });
    }, 60);
    return () => window.clearTimeout(settle);
  }, [target, size.h]);

  const anchors = target?.anchors.filter((a) => a.page === page) ?? [];
  const go = (n: number) => setPage(Math.min(Math.max(1, n), pageCount || 1));

  return (
    <div className="flex flex-col h-full">
      <div className="no-print flex items-center gap-1.5 px-3 h-11 border-b
                      border-paper-edge bg-paper text-sm shrink-0">
        <button onClick={() => go(page - 1)} disabled={page <= 1} aria-label="Previous page"
                className="btn btn-sm btn-ghost px-2">←</button>
        <div className="flex items-center gap-1.5 text-xs text-ink-soft">
          <input value={pageInput} aria-label="Page number"
                 onChange={(e) => setPageInput(e.target.value)}
                 onBlur={() => go(Number(pageInput) || page)}
                 onKeyDown={(e) => e.key === "Enter" && go(Number(pageInput) || page)}
                 className="w-14 border border-paper-edge rounded px-1.5 py-1
                            text-center tabular-nums" />
          <span className="tabular-nums whitespace-nowrap">of {pageCount || "…"}</span>
        </div>
        <button onClick={() => go(page + 1)} disabled={page >= pageCount}
                aria-label="Next page" className="btn btn-sm btn-ghost px-2">→</button>

        {rendering && <span className="text-2xs text-ink-ghost ml-1">rendering…</span>}

        <div className="ml-auto flex items-center gap-1">
          <button onClick={() => setFitWidth(true)}
                  className={`btn btn-sm ${fitWidth ? "bg-brand-soft text-brand border border-brand/25" : "btn-ghost"}`}>
            Fit
          </button>
          <button onClick={() => { setFitWidth(false); setZoom((z) => Math.max(0.5, +(z - 0.25).toFixed(2))); }}
                  aria-label="Zoom out" className="btn btn-sm btn-ghost px-2">−</button>
          <span className="tabular-nums w-11 text-center text-xs text-ink-soft">
            {fitWidth ? "auto" : `${Math.round(zoom * 100)}%`}
          </span>
          <button onClick={() => { setFitWidth(false); setZoom((z) => Math.min(3, +(z + 0.25).toFixed(2))); }}
                  aria-label="Zoom in" className="btn btn-sm btn-ghost px-2">+</button>
        </div>
      </div>

      <div ref={wrapRef} className="flex-1 overflow-auto p-6 min-h-0">
        {loading && (
          <div className="mx-auto max-w-2xl">
            <div className="skeleton h-[70vh] w-full" />
            <p className="mt-3 text-center text-xs text-ink-faint">
              Opening document — large reports take a moment to load.
            </p>
          </div>
        )}
        {error && (
          <p role="alert" className="mx-auto max-w-lg text-sm text-sev-critical
                                     bg-sev-critical-soft border border-sev-critical/20
                                     rounded px-4 py-3">{error}</p>
        )}
        {!loading && !error && (
          <div className="relative mx-auto shadow-pop bg-white rounded-[2px] overflow-hidden"
               style={{ width: size.w || undefined }}>
            <canvas ref={canvasRef} className="block" />
            {anchors.map((a, i) => {
              const box = {
                left: a.bbox[0] * size.w,
                top: a.bbox[1] * size.h,
                width: Math.max(4, (a.bbox[2] - a.bbox[0]) * size.w),
                height: Math.max(4, (a.bbox[3] - a.bbox[1]) * size.h),
              };
              return (
                <div key={`${target!.nonce}-${i}`}>
                  <div className="pramaan-highlight pramaan-highlight--pulse"
                       style={{ ...box, background: FILL[target!.severity] ?? FILL.info }} />
                  {/* One ring, drawn 4px outside the fill, that says WHERE on the sheet the
                      claim landed before the reader starts reading. It does not loop —
                      a loop is progress, and this is arrival. */}
                  <div className="pramaan-arrival animate-ping-once"
                       style={{ left: box.left - 4, top: box.top - 4,
                                width: box.width + 8, height: box.height + 8 }} />
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
