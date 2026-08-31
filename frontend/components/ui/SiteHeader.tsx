"use client";
/** The one header. Every page uses it — landing, login and the signed-in screens.
 *
 *  It exists because there were three: `Shell`'s, a hand-rolled copy on the landing page
 *  that had drifted from it, and nothing at all on `/login`. Chrome that differs page to
 *  page reads as a site assembled by several people who never spoke, which is precisely the
 *  impression a government appraisal tool cannot afford.
 *
 *  It wears two faces, and the difference is the audience rather than the page: `public` is
 *  the front door — a mark, a centred menu and a way in — while `app` is the working chrome
 *  a signed-in officer sits under all day, where the identity strip and the person's own
 *  name matter more than a call to action. The nav list and every behaviour below are still
 *  written once.
 *
 *  The variant is passed in, never inferred from `session`: inferring it would flash the
 *  front-door header for one frame on every signed-in page while the token is still being
 *  read from storage, and `Shell` sizes `--chrome-h` against the app variant's exact
 *  height.
 */
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { BrandMark } from "@/components/ui/BrandMark";
import { SignInDialog } from "@/components/auth/SignInDialog";
import { useAuth } from "@/lib/auth";

type Item = { href: string; label: string };

// One source of truth for navigation. Public items are anchors on the landing page — one
// strong page beats three thin ones — except Data sources, which earns a URL because the
// MoSPI provenance is the credibility argument.
const PUBLIC_NAV: Item[] = [
  { href: "/#how-it-works", label: "How it works" },
  { href: "/#principles", label: "Principles" },
  { href: "/data-sources", label: "Data sources" },
];

const RESOURCES: Item[] = [
  { href: "/#faq", label: "Questions" },
  { href: "/#sectors", label: "Sectors covered" },
  { href: "/accessibility", label: "Accessibility" },
];

const NAV: Record<string, Item[]> = {
  applicant: [
    { href: "/submissions", label: "My reports" },
  ],
  ministry: [
    { href: "/dashboard", label: "Overview" },
    { href: "/queue", label: "Review queue" },
    { href: "/portfolio", label: "Portfolio" },
    { href: "/audit", label: "Audit" },
    { href: "/reports", label: "Reports" },
  ],
};

function Chevron({ open }: { open: boolean }) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden fill="none" stroke="currentColor" strokeWidth="2"
         strokeLinecap="round" strokeLinejoin="round"
         className={`w-3.5 h-3.5 transition-transform ${open ? "rotate-180" : ""}`}>
      <path d="m6 9 6 6 6-6" />
    </svg>
  );
}

function UserGlyph() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden fill="none" stroke="currentColor" strokeWidth="1.8"
         strokeLinecap="round" className="w-4 h-4">
      <circle cx="12" cy="8" r="3.4" />
      <path d="M5 20c0-3.6 3.1-6 7-6s7 2.4 7 6" />
    </svg>
  );
}

/** The Resources menu. Closes on Escape, on a click outside, and on navigation — a menu
 *  that survives the route change stays open over the page you just asked for. */
function ResourcesMenu() {
  const [open, setOpen] = useState(false);
  const wrap = useRef<HTMLDivElement>(null);
  const path = usePathname();

  useEffect(() => setOpen(false), [path]);

  useEffect(() => {
    if (!open) return;
    function onDown(e: MouseEvent) {
      if (!wrap.current?.contains(e.target as Node)) setOpen(false);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div ref={wrap} className="relative">
      <button type="button" onClick={() => setOpen((v) => !v)}
              aria-expanded={open} aria-haspopup="menu"
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-white/85
                         hover:text-white hover:bg-white/10 transition-colors">
        Resources
        <Chevron open={open} />
      </button>
      {open && (
        <div role="menu"
             className="absolute left-0 top-full mt-2 w-56 py-1.5 rounded-xl bg-paper
                        border border-paper-edge shadow-pop animate-fade-in z-50">
          {RESOURCES.map((r) => (
            <Link key={r.href} href={r.href} role="menuitem"
                  className="block px-4 py-2 text-sm text-ink hover:bg-brand-soft
                             hover:text-brand transition-colors">
              {r.label}
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

export function SiteHeader({ variant = "app" }: { variant?: "app" | "public" }) {
  const { session, signOut } = useAuth();
  const path = usePathname();
  const [signingIn, setSigningIn] = useState(false);
  const [demo, setDemo] = useState(false);
  const [menu, setMenu] = useState(false);
  const items = session ? NAV[session.role] : PUBLIC_NAV;

  // `/login` redirects here with ?signin=1 — from signing out, from a session expiring, or
  // from a direct link. Read straight off the URL rather than via useSearchParams so this
  // needs no Suspense boundary in the server pages that render the header.
  useEffect(() => {
    const q = new URLSearchParams(window.location.search);
    if (q.get("signin") !== "1") return;
    setDemo(q.get("demo") === "1");
    setSigningIn(true);
    window.history.replaceState({}, "", window.location.pathname);
  }, [path]);

  useEffect(() => setMenu(false), [path]);

  const dialog = (
    <SignInDialog open={signingIn} demo={demo}
                  onClose={() => { setSigningIn(false); setDemo(false); }} />
  );

  /* ------------------------------------------------------------------- the front door -- */
  if (variant === "public" && !session) {
    return (
      // The dialog is a sibling of the bar, not a child of it: `backdrop-blur` makes this
      // header a containing block for `position: fixed` descendants, so a dialog rendered
      // inside it would be trapped in a 72px-tall strip instead of covering the viewport.
      <>
      <div className="no-print sticky top-0 z-40 bg-brand-ink/95 backdrop-blur
                      border-b border-white/10">
        <div className="mx-auto max-w-screen px-5 h-[78px] flex items-center gap-8">
          <Link href="/" aria-label="PRAMAAN — home" className="shrink-0">
            <BrandMark tone="light" size="lg" />
          </Link>

          <nav className="hidden lg:flex items-center gap-1 text-sm mx-auto">
            {PUBLIC_NAV.map((i) => (
              <Link key={i.href} href={i.href}
                    className="px-3 py-2 rounded-lg text-white/85 hover:text-white
                               hover:bg-white/10 transition-colors">
                {i.label}
              </Link>
            ))}
            <ResourcesMenu />
          </nav>

          <div className="ml-auto lg:ml-0 flex items-center gap-3 shrink-0">
            <button onClick={() => setSigningIn(true)}
                    className="hidden sm:flex items-center gap-2 px-4 py-2 rounded-lg text-sm
                               text-white border border-white/25 hover:bg-white/10
                               transition-colors">
              <UserGlyph />
              Sign in
            </button>
            <Link href="/?signin=1&demo=1"
                  className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold
                             bg-gold-vivid text-brand-ink hover:bg-gold-bright
                             transition-colors">
              Get started
              <svg viewBox="0 0 24 24" aria-hidden fill="none" stroke="currentColor"
                   strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
                   className="w-4 h-4">
                <path d="M5 12h14M13 6l6 6-6 6" />
              </svg>
            </Link>
            <button onClick={() => setMenu((v) => !v)} aria-expanded={menu}
                    aria-label="Menu"
                    className="lg:hidden p-2 rounded-lg text-white hover:bg-white/10">
              <svg viewBox="0 0 24 24" aria-hidden fill="none" stroke="currentColor"
                   strokeWidth="2" strokeLinecap="round" className="w-5 h-5">
                <path d="M4 7h16M4 12h16M4 17h16" />
              </svg>
            </button>
          </div>
        </div>

        {menu && (
          <nav className="lg:hidden border-t border-white/10 px-5 py-3 space-y-1
                          animate-fade-in">
            {[...PUBLIC_NAV, ...RESOURCES].map((i) => (
              <Link key={i.href} href={i.href}
                    className="block px-3 py-2 rounded-lg text-sm text-white/85
                               hover:bg-white/10">
                {i.label}
              </Link>
            ))}
          </nav>
        )}
      </div>
      {dialog}
      </>
    );
  }

  /* ------------------------------------------------------------- the working chrome -- */
  return (
    <div className="no-print">
      {/* Thin identity strip — the convention on Indian government portals. */}
      <div className="bg-brand-ink text-white/80 text-2xs">
        <div className="mx-auto max-w-screen px-5 h-7 flex items-center justify-between">
          <span>Project Report Appraisal, Modelling and Analytics</span>
          <span className="hidden sm:inline">
            Advisory system — the final decision rests with the authorised officer
          </span>
        </div>
      </div>

      <header className="bg-brand-deep text-white">
        <div className="mx-auto max-w-screen px-5 h-16 flex items-center gap-7">
          <Link href="/" aria-label="PRAMAAN — home" className="shrink-0">
            <BrandMark tone="light" size="sm" />
          </Link>

          {/* Honest about what this is. The mockup carried a "Govt. of India" badge, which
              does not belong on an unaffiliated prototype sitting above a footer that
              carefully disclaims exactly that authority — hence this pill instead. */}
          <span className="pill bg-white/10 text-white/70 hidden lg:inline-flex shrink-0">
            Smart India Hackathon · Prototype
          </span>

          <nav className="hidden md:flex items-stretch gap-1 text-sm h-full">
            {items.map((i) => {
              // Anchors share the landing path, so only real routes light up.
              const active = !i.href.includes("#") && path.startsWith(i.href);
              return (
                <Link key={i.href} href={i.href}
                      aria-current={active ? "page" : undefined}
                      className={`px-3 flex items-center border-b-[3px] transition-colors ${
                        active ? "border-gold text-white font-medium"
                               : "border-transparent text-white/80 hover:text-white"}`}>
                  {i.label}
                </Link>
              );
            })}
          </nav>

          <div className="ml-auto flex items-center gap-4 text-sm shrink-0">
            {session ? (
              <>
                <div className="text-right leading-tight hidden sm:block">
                  <p className="text-white/95">{session.full_name}</p>
                  <p className="text-2xs text-white/55">
                    {session.role === "applicant" ? "Applicant" : "Ministry"}
                  </p>
                </div>
                <button onClick={signOut}
                        className="text-white/80 hover:text-white underline-offset-4
                                   hover:underline">
                  Sign out
                </button>
              </>
            ) : (
              <button onClick={() => setSigningIn(true)}
                      className="text-white/90 hover:text-white underline-offset-4
                                 hover:underline">
                Sign in
              </button>
            )}
          </div>
        </div>
      </header>
      <div className="rule-gold" />
      {dialog}
    </div>
  );
}
