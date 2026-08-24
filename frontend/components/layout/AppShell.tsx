"use client";
/**
 * The frame every signed-in screen wears.
 *
 *  The whole app is one viewport-height column: rail, header, and a main region that
 *  scrolls inside itself. That is worth stating because it removes the one number in the
 *  old layout that rotted silently — `--chrome-h`, a hand-maintained `11.75rem` that the
 *  review workspace subtracted from `100vh`. Get it wrong by 4px and the product's main
 *  screen grows a second scrollbar; get it wrong the other way and the PDF is clipped.
 *  A flex column measures itself, so the split view can simply say `flex-1 min-h-0` and be
 *  exactly right at any header height, any zoom, and any font size.
 *
 *  Two densities, because a screen you SCAN and a screen you FOCUS IN should not feel the
 *  same. `page` gives the queue and the dashboards air and an optional right rail; `focus`
 *  hands the whole region to the evidence workspace with no padding at all.
 */
import { useCallback, useEffect, useState } from "react";
import { usePathname } from "next/navigation";

import { Icon } from "@/components/ui/Icon";
import { Sidebar } from "./Sidebar";
import { Topbar, type Notice } from "./Topbar";
import { useAuth } from "@/lib/auth";

/** Remembered per browser, so an officer who opened the rail does not have to open it again
 *  on every page. Absent means collapsed — see the state comment below. */
const RAIL_KEY = "pramaan.rail.collapsed";

/**
 * `borrowRail` lets a screen hand the rail's width to its own content.
 *
 *  The evidence split needs this. On a 1366px monitor the rail, the reading column and the
 *  document cannot all have enough room at once, and the one of the three not being used
 *  while an officer checks a figure against a page is the navigation.
 *
 *  It is a prop rather than a context on purpose: `AppShell` owns the rail's state, so any
 *  provider it renders is BELOW the page that renders `AppShell`, and a page could never be
 *  a consumer of it. The first version of this was exactly that mistake — the hook returned
 *  the default no-op and the rail never moved.
 *
 *  Held apart from the stored preference, so an officer who had deliberately collapsed the
 *  rail still finds it collapsed afterwards, and one who had it open finds it open.
 */

export function AppShell({
  children, title, subtitle, crumb, actions, rail, notices, variant = "page", search = "",
  borrowRail = false,
}: {
  children: React.ReactNode;
  title?: string;
  subtitle?: string;
  crumb?: { href: string; label: string }[];
  actions?: React.ReactNode;
  /** The standing right-hand column. Optional — a screen with nothing standing to say
   *  should not grow an empty 20rem gutter to prove it has one. */
  rail?: React.ReactNode;
  notices?: Notice[];
  variant?: "page" | "focus";
  search?: string;
  /** Temporarily hide the rail without touching the officer's stored preference. */
  borrowRail?: boolean;
}) {
  const { session } = useAuth();
  // Two different things wear the same word "open", and collapsing them into one state is
  // what once hid the navigation with no way to tell it had happened. They stay separate:
  //
  //   `drawer`    — the < lg overlay. Starts closed, because it covers the page.
  //   `collapsed` — the ≥ lg rail. Starts CLOSED, so every screen opens at full width and
  //                 the reading column, the tables and the evidence split get the whole
  //                 monitor by default. Opening it is a deliberate act, and it is
  //                 remembered, so an officer who wants the rail standing gets it standing
  //                 on every page until they say otherwise.
  //
  // The toggle that governs it lives in the topbar and is labelled in both directions, so
  // a collapsed rail is a state the officer can see and undo rather than a missing feature.
  const [drawer, setDrawer] = useState(false);
  const [collapsed, setCollapsed] = useState(true);
  const path = usePathname();

  // Read after mount, never during render: the server has no localStorage, and reading it
  // in the initial state would make the first client paint disagree with the server's.
  //
  // Compared against "0" rather than "1" because CLOSED is the default: an unset key, a
  // private window and a browser blocking site data must all land on the default, and only
  // an explicit "0" — written when the officer opened it — reopens the rail.
  useEffect(() => {
    try { setCollapsed(localStorage.getItem(RAIL_KEY) !== "0"); } catch { /* blocked storage */ }
  }, []);

  const toggleRail = useCallback(() => {
    setCollapsed((v) => {
      const next = !v;
      try { localStorage.setItem(RAIL_KEY, next ? "1" : "0"); } catch { /* blocked storage */ }
      return next;
    });
  }, []);

  useEffect(() => setDrawer(false), [path]);
  useEffect(() => {
    if (!drawer) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setDrawer(false); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [drawer]);

  const hidden = collapsed || borrowRail;

  return (
    <div className="app-shell flex h-screen overflow-hidden bg-paper-soft">
      {/* The standing rail, ≥lg. `aria-hidden`/`inert` follow the width: a 0px-wide column
          is still in the tab order, so a keyboard user would otherwise tab through eight
          invisible destinations before reaching the page. */}
      <aside aria-label="Main navigation"
             aria-hidden={hidden}
             // A BOOLEAN, not the empty string. React 19 treats `inert` as a real boolean
             // attribute, so `inert=""` is read as false and the attribute is dropped — the
             // collapsed rail stayed fully tab-reachable, and a keyboard user tabbed through
             // eight invisible destinations before reaching the page. That matters more now
             // that collapsed is the default state rather than the exception.
             inert={hidden}
             className={`no-print hidden shrink-0 overflow-hidden transition-[width]
                         duration-300 ease-[cubic-bezier(.16,.84,.44,1)] lg:block ${
               hidden ? "w-0" : "w-sidebar"}`}>
        <div className="h-full w-sidebar">
          <Sidebar session={session} search={search} />
        </div>
      </aside>

      {drawer && (
        <div className="no-print fixed inset-0 z-50 lg:hidden">
          <div onClick={() => setDrawer(false)}
               className="absolute inset-0 bg-brand-ink/50 backdrop-blur-sm animate-fade-in" />
          <div className="absolute inset-y-0 left-0 w-[17rem] shadow-rail
                          animate-slide-in-right">
            <Sidebar session={session} search={search} onNavigate={() => setDrawer(false)} />
          </div>
          <button onClick={() => setDrawer(false)} aria-label="Close navigation"
                  className="absolute right-4 top-4 grid h-10 w-10 place-items-center
                             rounded-full bg-paper text-ink shadow-pop">
            <Icon name="close" className="w-5 h-5" />
          </button>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar title={title} subtitle={subtitle} crumb={crumb} actions={actions}
                notices={notices}
                onOpenDrawer={() => setDrawer(true)}
                onToggleRail={toggleRail}
                railCollapsed={hidden} />

        <main className={`app-main min-h-0 flex-1 ${
          variant === "focus" ? "flex flex-col" : "overflow-y-auto scroll-slim"}`}>
          {variant === "focus" ? children : (
            <div className={rail
              ? "mx-auto grid max-w-screen gap-6 px-5 py-6 xl:grid-cols-[minmax(0,1fr)_20rem]"
              : "mx-auto max-w-screen px-5 py-6"}>
              <div className="min-w-0">{children}</div>
              {rail && (
                <div className="no-print min-w-0 space-y-4 xl:sticky xl:top-0">{rail}</div>
              )}
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------- the rail's parts -- */

export function RailCard({ title, action, children, tone = "plain" }: {
  title?: string; action?: React.ReactNode; children: React.ReactNode;
  tone?: "plain" | "brand";
}) {
  return (
    <section className={`overflow-hidden rounded-card border shadow-card ${
      tone === "brand"
        ? "border-brand/15 bg-gradient-to-br from-brand-soft to-paper"
        : "border-paper-edge bg-paper"}`}>
      {title && (
        <div className="flex items-center gap-2 px-4 pt-4">
          <h2 className="display text-sm font-bold text-ink">{title}</h2>
          {action && <div className="ml-auto">{action}</div>}
        </div>
      )}
      <div className={title ? "px-4 pb-4 pt-3" : "p-4"}>{children}</div>
    </section>
  );
}

/** A definition row for the rail's summary card. Kept as a component because there are
 *  four of these on three screens and they had drifted into three shapes. */
export function RailStat({ icon, label, value, tone }: {
  icon: React.ComponentProps<typeof Icon>["name"];
  label: string; value: string | number;
  tone?: "ok" | "attention" | "muted";
}) {
  const colour = tone === "ok" ? "text-ok"
               : tone === "attention" ? "text-sev-high"
               : tone === "muted" ? "text-ink-faint" : "text-ink";
  return (
    <div className="flex items-center gap-2.5 py-1.5">
      <Icon name={icon} className={`w-4 h-4 shrink-0 ${colour}`} />
      <span className="min-w-0 truncate text-xs text-ink-soft">{label}</span>
      <span className={`ml-auto shrink-0 text-sm font-semibold tabular-nums ${colour}`}>
        {value}
      </span>
    </div>
  );
}
