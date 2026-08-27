"use client";
/**
 * The two standing information pages — data sources, accessibility — are read by both
 * audiences, and the chrome has to follow the reader rather than the URL.
 *
 *  A signed-in officer who clicks "Data sources" in the navigation rail and lands on a page
 *  with no rail has, as far as they can tell, left the application. So when there is a
 *  session the page wears the working chrome; when there is not, it wears the front door.
 *  One page, one copy of the content, two frames.
 */
import { AppShell } from "./AppShell";
import { SiteFooter } from "@/components/ui/SiteFooter";
import { SiteHeader } from "@/components/ui/SiteHeader";
import { useAuth } from "@/lib/auth";

export function PublicFrame({ title, subtitle, children }: {
  title: string; subtitle?: string; children: React.ReactNode;
}) {
  const { session, ready } = useAuth();

  // Nothing until the session is read, so a signed-in officer never sees one frame swap for
  // the other — a page that changes shape after it has loaded reads as a fault.
  if (!ready) return null;

  if (session) {
    return <AppShell title={title} subtitle={subtitle}>{children}</AppShell>;
  }

  return (
    <div className="flex min-h-screen flex-col bg-paper">
      <SiteHeader variant="public" />
      <main className="flex-1">
        <div className="mx-auto max-w-screen px-5 py-8">
          <h1 className="display text-[30px] font-bold leading-tight text-ink">{title}</h1>
          {subtitle && <p className="mt-1 text-sm text-ink-soft">{subtitle}</p>}
          <div className="rule-gold-stub mt-3" />
          <div className="mt-6">{children}</div>
        </div>
      </main>
      <SiteFooter />
    </div>
  );
}
