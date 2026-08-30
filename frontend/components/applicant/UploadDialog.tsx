"use client";
/**
 * Submitting a report, and watching it be read.
 *
 *  The wait is the design problem here, not the form. A 300-page DPR takes two to four
 *  minutes, and scanned pages take longer because each one has to be recognised — people
 *  tolerate a slow process they can watch and abandon a spinner. So the progress panel
 *  names the real stage the worker is in and counts real pages, and the stages are listed
 *  ahead of time so the reader knows how far through they are rather than only how fast.
 *
 *  The private pre-submission check is given equal weight to the submit button on purpose.
 *  It is the single feature that changes the relationship between the two sides of this
 *  system: an applicant who can rehearse against the same rubric the ministry will use
 *  fixes the missing annexure themselves, and the file never bounces.
 */
import { useEffect, useRef, useState } from "react";

import { Icon } from "@/components/ui/Icon";
import { api, getSession } from "@/lib/api";

interface Status { stage: string; detail: string; percent: number;
                   pages_done?: number; page_count?: number | null; error: string | null }

const STAGES = [
  ["queued", "Queued"],
  ["parsing", "Reading text and tables"],
  ["ocr", "Reading scanned pages"],
  ["indexing", "Indexing for evidence"],
  ["ready", "Ready"],
] as const;

export function UploadDialog({ open, onClose, onDone }: {
  open: boolean; onClose: () => void; onDone: () => void;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [selfCheck, setSelfCheck] = useState(true);
  const [busy, setBusy] = useState(false);
  const [drag, setDrag] = useState(false);
  const [progress, setProgress] = useState<Status | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const pollRef = useRef<number | undefined>(undefined);

  useEffect(() => {
    if (open) return;
    // Reset on close, but never mid-upload: closing the dialog must not orphan a poll.
    if (!busy) { setFile(null); setError(null); setProgress(null); }
  }, [open, busy]);

  useEffect(() => () => window.clearInterval(pollRef.current), []);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape" && !busy) onClose(); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, busy, onClose]);

  if (!open) return null;

  function pick(f: File | undefined | null) {
    if (!f) return;
    if (f.type !== "application/pdf") {
      setError("That is not a PDF. A DPR has to be submitted as a PDF so its pages can be cited.");
      return;
    }
    setError(null);
    setFile(f);
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    setBusy(true); setError(null);

    const body = new FormData();
    body.append("file", file);
    body.append("title", file.name.replace(/\.pdf$/i, ""));
    body.append("self_check", String(selfCheck));

    try {
      const res = await fetch("/api/v1/dprs", {
        method: "POST",
        headers: { Authorization: `Bearer ${getSession()!.access_token}` },
        body,
      });
      if (!res.ok) throw new Error((await res.json()).detail ?? "Upload failed");
      const { dpr_id } = await res.json();

      pollRef.current = window.setInterval(async () => {
        try {
          const s = await api<Status>(`/dprs/${dpr_id}/status`);
          setProgress(s);
          if (s.stage === "ready" || s.stage === "failed") {
            window.clearInterval(pollRef.current);
            setBusy(false);
            if (s.stage === "failed") {
              setError(s.error ?? "This document could not be processed.");
              setProgress(null);
            } else {
              onDone();
              onClose();
            }
          }
        } catch {
          window.clearInterval(pollRef.current);
          setBusy(false);
          setError("Lost contact while the report was being read. It may still be processing —"
                 + " reload the list in a minute.");
        }
      }, 1200);
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  }

  const stageIndex = STAGES.findIndex(([k]) => k === progress?.stage);

  return (
    <div className="fixed inset-0 z-50 grid place-items-center overflow-y-auto px-4 py-8">
      <div onClick={() => !busy && onClose()}
           className="fixed inset-0 bg-brand-ink/60 backdrop-blur-md animate-fade-in" />

      <form onSubmit={submit} role="dialog" aria-modal="true"
            aria-label="Submit a Detailed Project Report"
            className="card relative w-full max-w-xl overflow-hidden shadow-rail
                       animate-rise-in">
        <div className="rule-gold" />
        <div className="flex items-start gap-3 border-b border-paper-edge px-6 pb-4 pt-5">
          <span aria-hidden className="grid h-11 w-11 shrink-0 place-items-center
                                       rounded-card bg-brand-soft text-brand">
            <Icon name="upload" className="w-5 h-5" />
          </span>
          <div className="min-w-0 flex-1">
            <h2 className="display text-lg font-bold text-ink">
              Submit a Detailed Project Report
            </h2>
            <p className="mt-0.5 text-2xs leading-relaxed text-ink-soft">
              PDF, up to 100 MB. Every figure the system reports can be traced back to the
              page it came from.
            </p>
          </div>
          {!busy && (
            <button type="button" onClick={onClose} aria-label="Close"
                    className="grid h-8 w-8 shrink-0 place-items-center rounded-full
                               text-ink-faint transition-colors hover:bg-paper-deep hover:text-ink">
              <Icon name="close" className="w-4 h-4" />
            </button>
          )}
        </div>

        <div className="px-6 py-5">
          {!busy && (
            <>
              <label
                onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
                onDragLeave={() => setDrag(false)}
                onDrop={(e) => { e.preventDefault(); setDrag(false); pick(e.dataTransfer.files?.[0]); }}
                className={`flex cursor-pointer flex-col items-center rounded-card border-2
                            border-dashed px-6 py-8 text-center transition-colors ${
                  drag ? "border-brand bg-brand-soft"
                       : file ? "border-ok/40 bg-ok-soft/50"
                       : "border-paper-edge bg-paper-soft hover:border-brand/40"}`}>
                <input ref={inputRef} type="file" accept="application/pdf" className="sr-only"
                       onChange={(e) => pick(e.target.files?.[0])} />
                <Icon name={file ? "docCheck" : "cloud"}
                      className={`w-9 h-9 ${file ? "text-ok" : "text-ink-ghost"}`} />
                <p className="mt-2.5 text-sm font-medium text-ink">
                  {file ? file.name : "Drop the PDF here, or choose a file"}
                </p>
                <p className="mt-1 text-2xs tabular-nums text-ink-faint">
                  {file ? `${(file.size / 1_048_576).toFixed(1)} MB`
                        : "A 300-page report takes two to four minutes to read"}
                </p>
              </label>

              <label className="mt-4 flex cursor-pointer items-start gap-2.5 rounded-card
                                border border-paper-edge bg-paper-soft px-3.5 py-3">
                <input type="checkbox" checked={selfCheck} className="mt-0.5"
                       onChange={(e) => setSelfCheck(e.target.checked)} />
                <span>
                  <span className="text-sm font-medium text-ink">
                    Private pre-submission check
                  </span>
                  <span className="mt-0.5 block text-2xs leading-relaxed text-ink-soft">
                    Scored for you alone, against the same rubric the ministry uses. It does
                    not enter the ministry queue and is not recorded as a submission — so you
                    can fix what it finds first.
                  </span>
                </span>
              </label>
            </>
          )}

          {busy && (
            <div aria-live="polite">
              <ol className="space-y-2">
                {STAGES.map(([k, label], i) => {
                  const done = stageIndex > i;
                  const now = stageIndex === i;
                  return (
                    <li key={k} className="flex items-center gap-3">
                      <span aria-hidden className={`grid h-6 w-6 shrink-0 place-items-center
                                                    rounded-full text-2xs ${
                        done ? "bg-ok text-white"
                             : now ? "bg-brand text-white" : "bg-paper-deep text-ink-ghost"}`}>
                        {done ? "✓" : i + 1}
                      </span>
                      <span className={`text-sm ${now ? "font-medium text-ink"
                                                      : done ? "text-ink-soft" : "text-ink-ghost"}`}>
                        {label}
                      </span>
                      {now && (
                        <span className="ml-auto text-2xs tabular-nums text-ink-faint">
                          {progress?.page_count
                            ? `page ${progress.pages_done ?? 0} of ${progress.page_count}`
                            : progress?.detail}
                        </span>
                      )}
                    </li>
                  );
                })}
              </ol>

              <div className="mt-4 h-2 overflow-hidden rounded-full bg-paper-edge">
                <div className="h-full rounded-full bg-brand transition-[width] duration-500
                                ease-[cubic-bezier(.16,.84,.44,1)]"
                     style={{ width: `${progress?.percent ?? 4}%` }} />
              </div>
              <p className="mt-2 text-2xs leading-relaxed text-ink-faint">
                You can leave this page — the report keeps processing and will appear in your
                list when it is done.
              </p>
            </div>
          )}

          {error && (
            <p role="alert" className="mt-4 rounded border border-sev-critical/20
                                       bg-sev-critical-soft px-3 py-2 text-xs text-sev-critical">
              {error}
            </p>
          )}
        </div>

        <div className="flex gap-3 border-t border-paper-edge bg-paper-soft/60 px-6 py-4">
          <button type="button" onClick={onClose} disabled={busy}
                  className="btn btn-ghost flex-1">
            {busy ? "Processing…" : "Cancel"}
          </button>
          <button type="submit" disabled={!file || busy} className="btn-gold flex-1">
            {busy ? "Reading…" : selfCheck ? "Run private check" : "Submit to the ministry"}
          </button>
        </div>
      </form>
    </div>
  );
}
