"use client";
/** Sign-in as a dialog over the landing page, blurring what is behind it.
 *
 *  Keyboard handling is not decoration here: a government portal is worked by keyboard more
 *  than most, and a dialog that traps nothing is worse than a page. Escape closes, Tab
 *  cycles inside, and focus returns to whatever opened it.
 */
import { useCallback, useEffect, useRef } from "react";

import { LoginCard } from "./LoginCard";
import { LoginStage } from "./LoginStage";

export function SignInDialog({ open, demo = false, onClose }: {
  open: boolean; demo?: boolean; onClose: () => void;
}) {
  const panel = useRef<HTMLDivElement>(null);
  const opener = useRef<Element | null>(null);

  const focusables = useCallback(
    () => Array.from(panel.current?.querySelectorAll<HTMLElement>(
      'a[href], button:not([disabled]), input, select, textarea') ?? []), []);

  useEffect(() => {
    if (!open) return;
    opener.current = document.activeElement;
    const { overflow } = document.body.style;
    document.body.style.overflow = "hidden";

    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") { onClose(); return; }
      if (e.key !== "Tab") return;
      const items = focusables();
      if (!items.length) return;
      const first = items[0], last = items[items.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    }

    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = overflow;
      (opener.current as HTMLElement | null)?.focus?.();
    };
  }, [open, onClose, focusables]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 grid place-items-center px-4 py-8 overflow-y-auto">
      <div onClick={onClose}
           className="fixed inset-0 bg-brand-ink/55 backdrop-blur-sm animate-none" />
      <div ref={panel} role="dialog" aria-modal="true" aria-label="Sign in"
           className="relative">
        <LoginCard demo={demo} autoFocus />
        <button onClick={onClose}
                className="mt-4 mx-auto block text-xs text-white/70 hover:text-white
                           underline-offset-4 hover:underline">
          Cancel
        </button>
      </div>
    </div>
  );
}
