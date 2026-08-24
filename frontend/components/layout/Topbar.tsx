"use client";
/** The page header: what this screen is, and who is looking at it.
 *
 *  It carries the title band the old `Shell` had, plus the two controls the reference puts
 *  top-right — the account menu and the notice bell. The bell shows a count only when there
 *  is something to count, and what it counts is real: reports of yours that came back
 *  needing attention. A bell with a permanent red dot is furniture.
 */
import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { BrandMark } from "@/components/ui/BrandMark";
import { Icon } from "@/components/ui/Icon";
import { Jaali } from "./Ornament";
import { useAuth } from "@/lib/auth";

export interface Notice { id: string; title: string; detail: string; href: string;
                          tone: "attention" | "done" }

function initials(name: string) {
  return name.split(/\s+/).filter(Boolean).slice(0, 2).map((p) => p[0]).join("").toUpperCase()
      || "—";
}

/** A menu that closes on Escape, on a click outside, and on navigation. A menu that
 *  survives the route change stays open over the page you just asked for. */
function useDismiss(open: boolean, close: () => void) {
  const wrap = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (!wrap.current?.contains(e.target as Node)) close();
    };
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") close(); };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open, close]);
  return wrap;
}

function NoticeBell({ notices }: { notices: Notice[] }) {
  const [open, setOpen] = useState(false);
  const wrap = useDismiss(open, () => setOpen(false));
  const n = notices.length;

  return (
    <div ref={wrap} className="relative">
      <button type="button" onClick={() => setOpen((v) => !v)}
              aria-expanded={open} aria-haspopup="menu"
              aria-label={n ? `Notices — ${n} needing attention` : "Notices — nothing new"}
              className="relative grid h-10 w-10 place-items-center rounded-full
                         text-ink-soft transition-colors hover:bg-paper-deep hover:text-ink">
        <Icon name="bell" className="w-[18px] h-[18px]" />
        {n > 0 && (
          <>
            <span aria-hidden className="absolute right-2 top-2 h-2 w-2 rounded-full
                                         bg-sev-high ring-2 ring-paper" />
            <span aria-hidden className="absolute right-2 top-2 h-2 w-2 rounded-full
                                         bg-sev-high animate-ping-once" />
          </>
        )}
      </button>

      {open && (
        <div role="menu"
             className="absolute right-0 top-full z-50 mt-2 w-80 overflow-hidden rounded-rail
                        border border-paper-edge bg-paper shadow-rail animate-rise-in">
          <p className="border-b border-paper-edge px-4 py-2.5 text-2xs font-semibold
                        uppercase tracking-wide text-ink-faint">
            Needs your attention
          </p>
          {n === 0 ? (
            <p className="px-4 py-6 text-center text-xs text-ink-faint">
              Nothing waiting on you.
            </p>
          ) : (
            <ul className="max-h-80 overflow-y-auto scroll-slim">
              {notices.map((x) => (
                <li key={x.id} className="border-b border-paper-edge/70 last:border-0">
                  <Link href={x.href} role="menuitem" onClick={() => setOpen(false)}
                        className="block px-4 py-3 transition-colors hover:bg-brand-soft/60">
                    <span className="flex items-start gap-2.5">
                      <Icon name={x.tone === "attention" ? "flag" : "check"}
                            className={`mt-0.5 w-4 h-4 shrink-0 ${
                              x.tone === "attention" ? "text-sev-high" : "text-ok"}`} />
                      <span className="min-w-0">
                        <span className="block truncate text-xs font-medium text-ink">
                          {x.title}
                        </span>
                        <span className="mt-0.5 block text-2xs leading-relaxed text-ink-faint">
                          {x.detail}
                        </span>
                      </span>
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

function AccountMenu() {
  const { session, signOut } = useAuth();
  const [open, setOpen] = useState(false);
  const wrap = useDismiss(open, () => setOpen(false));
  if (!session) return null;

  return (
    <div ref={wrap} className="relative">
      <button type="button" onClick={() => setOpen((v) => !v)}
              aria-expanded={open} aria-haspopup="menu"
              className="flex items-center gap-2.5 rounded-full border border-transparent
                         py-1 pl-1 pr-2.5 transition-colors hover:border-paper-edge
                         hover:bg-paper">
        <span aria-hidden
              className="grid h-9 w-9 place-items-center rounded-full bg-brand-soft
                         text-sm font-semibold text-brand-deep">
          {initials(session.full_name)}
        </span>
        <span className="hidden text-left leading-tight lg:block">
          <span className="block text-xs font-medium text-ink">{session.full_name}</span>
          <span className="block text-2xs text-ink-faint">
            {session.role === "applicant" ? "Applicant" : "Ministry"}
          </span>
        </span>
        <Icon name="chevronDown"
              className={`w-3.5 h-3.5 text-ink-faint transition-transform duration-200
                          ${open ? "rotate-180" : ""}`} />
      </button>

      {open && (
        <div role="menu"
             className="absolute right-0 top-full z-50 mt-2 w-64 overflow-hidden rounded-rail
                        border border-paper-edge bg-paper shadow-rail animate-rise-in">
          <div className="border-b border-paper-edge bg-paper-soft px-4 py-3">
            <p className="text-sm font-medium text-ink">{session.full_name}</p>
            <p className="mt-0.5 text-2xs text-ink-faint">
              {session.role === "applicant" ? "Submitting organisation" : "Appraisal officer"}
            </p>
            {/* The single most consequential fact about a MINISTRY account, stated where
                the account is rather than buried in a tooltip on a disabled button. It says
                nothing about an applicant, who never had sanctioning power to be told they
                lack — and "May recommend, not sanction" on a submitter's own menu reads as
                a permission they were refused. */}
            {session.role === "ministry" && (
              <p className={`mt-2 chip ${session.can_sanction
                ? "bg-ok-soft text-ok border-ok/25" : "bg-paper-deep text-ink-soft border-paper-edge"}`}>
                {session.can_sanction ? "✓ May record a sanction" : "⊘ May recommend, not sanction"}
              </p>
            )}
          </div>
          {/* The ministry's record of its own decision. An applicant has no appraisal to
              read, so offering them the shelf is offering a door that opens on nothing. */}
          {session.role === "ministry" && (
            <Link href="/reports" role="menuitem" onClick={() => setOpen(false)}
                  className="flex items-center gap-2.5 px-4 py-2.5 text-sm text-ink
                             transition-colors hover:bg-brand-soft hover:text-brand">
              <Icon name="docCheck" className="w-4 h-4" /> Appraisal notes
            </Link>
          )}
          <Link href="/accessibility" role="menuitem" onClick={() => setOpen(false)}
                className="flex items-center gap-2.5 px-4 py-2.5 text-sm text-ink
                           transition-colors hover:bg-brand-soft hover:text-brand">
            <Icon name="help" className="w-4 h-4" /> Accessibility
          </Link>
          <button role="menuitem" onClick={signOut}
                  className="flex w-full items-center gap-2.5 border-t border-paper-edge px-4
                             py-2.5 text-left text-sm text-ink transition-colors
                             hover:bg-sev-critical-soft hover:text-sev-critical">
            <Icon name="logout" className="w-4 h-4" /> Sign out
          </button>
        </div>
      )}
    </div>
  );
}

export function Topbar({ title, subtitle, crumb, actions, notices = [],
                        onOpenDrawer, onToggleRail, railCollapsed = false }: {
  title?: string;
  subtitle?: string;
  crumb?: { href: string; label: string }[];
  actions?: React.ReactNode;
  notices?: Notice[];
  /** Opens the overlay drawer, below `lg`. */
  onOpenDrawer?: () => void;
  /** Collapses or restores the standing rail, at `lg` and above. */
  onToggleRail?: () => void;
  railCollapsed?: boolean;
}) {
  return (
    <header className="no-print relative z-30 border-b border-paper-edge bg-paper">
      {/* The identity strip, kept: it is the convention on Indian government portals, and it
          is where the advisory disclaimer belongs — on every screen, not on a page people
          have to find. */}
      <div className="bg-brand-ink text-2xs text-white/75">
        <div className="flex h-7 items-center justify-between gap-4 px-5">
          <span className="truncate">Project Report Appraisal, Modelling and Analytics</span>
          <span className="hidden shrink-0 sm:inline">
            Advisory system — the final decision rests with the authorised officer
          </span>
        </div>
      </div>

      <div className="relative flex min-h-[4.5rem] items-center gap-4 px-5 py-3">
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <Jaali className="absolute -right-16 -top-32 h-72 w-72 text-brand/[0.055]" />
        </div>

        {/* Two controls, not one, because they do different things. Below `lg` the button
            opens an overlay; at `lg` and above it collapses a standing column, and the
            label has to say which — "Toggle navigation" on a desktop where the rail is
            already visible tells a screen-reader user nothing about what will happen. */}
        <button type="button" onClick={onOpenDrawer} aria-label="Open navigation"
                className="grid h-10 w-10 shrink-0 place-items-center rounded-full
                           text-ink-soft transition-colors hover:bg-paper-deep hover:text-ink
                           lg:hidden">
          <Icon name="menu" className="w-5 h-5" />
        </button>
        {/* The rail is collapsed by default, so while it is closed this button IS the
            navigation — the only route to it on a desktop. It therefore carries a border and
            a ground while closed, so it reads as a control, and drops back to a ghost once
            the rail is standing and the destinations are visible on their own. */}
        <button type="button" onClick={onToggleRail} aria-expanded={!railCollapsed}
                aria-label={railCollapsed ? "Show the navigation menu" : "Hide the navigation menu"}
                title={railCollapsed ? "Show the navigation menu" : "Hide the navigation menu"}
                className={`hidden h-10 w-10 shrink-0 place-items-center rounded-card
                            transition-colors lg:grid ${
                  railCollapsed
                    ? "border border-paper-edge bg-paper text-ink shadow-card hover:border-brand/40 hover:bg-brand-soft hover:text-brand"
                    : "border border-transparent text-ink-soft hover:bg-paper-deep hover:text-ink"}`}>
          <Icon name={railCollapsed ? "menu" : "expandLeft"} className="w-5 h-5" />
        </button>

        {/* The mark, which lives at the head of the rail and therefore vanishes with it.
            A signed-in officer should not have a screen with no indication of what product
            they are in, so it reappears here for exactly as long as the rail is away. */}
        {railCollapsed && (
          <Link href="/" aria-label="PRAMAAN — home"
                className="hidden shrink-0 lg:block">
            <BrandMark tone="dark" size="sm" />
          </Link>
        )}

        <div className="relative min-w-0 flex-1">
          {crumb && crumb.length > 0 && (
            <nav aria-label="Breadcrumb"
                 className="mb-0.5 flex items-center gap-1.5 text-2xs text-ink-faint">
              {crumb.map((c, i) => (
                <span key={c.href} className="flex items-center gap-1.5">
                  {i > 0 && <Icon name="chevronRight" className="w-3 h-3 text-ink-ghost" />}
                  <Link href={c.href} className="transition-colors hover:text-brand hover:underline">
                    {c.label}
                  </Link>
                </span>
              ))}
            </nav>
          )}
          {title && (
            <h1 className="display truncate text-[26px] font-bold leading-tight text-ink">
              {title}
            </h1>
          )}
          {subtitle && (
            <p className="mt-0.5 truncate text-xs text-ink-soft">{subtitle}</p>
          )}
          {title && <div className="rule-gold-stub mt-2" />}
        </div>

        <div className="relative ml-auto flex shrink-0 items-center gap-2">
          {actions}
          <NoticeBell notices={notices} />
          <AccountMenu />
        </div>
      </div>
    </header>
  );
}
