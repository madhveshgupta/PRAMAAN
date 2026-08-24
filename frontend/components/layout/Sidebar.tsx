"use client";
/**
 * The standing navigation rail (Dark Premium Theme).
 */
import Link from "next/link";
import { usePathname } from "next/navigation";
import { BrandMark, Emblem } from "@/components/ui/BrandMark";
import { Icon, type IconName } from "@/components/ui/Icon";
import type { Session } from "@/lib/api";

export interface NavItem {
  href: string; label: string; icon: IconName;
  badge?: number | null;
  hint?: string;
}

export function navFor(session: Session | null): { group: string; items: NavItem[] }[] {
  if (session?.role === "applicant") {
    return [
      { group: "Reports", items: [
        { href: "/submissions", label: "My Reports", icon: "doc" },
        { href: "/submissions?upload=1", label: "Upload New Report", icon: "upload" },
      ]},
      { group: "About", items: [
        { href: "/data-sources", label: "Data Sources", icon: "layers" },
        { href: "/accessibility", label: "Accessibility", icon: "help" },
      ]},
    ];
  }
  return [
    { group: "Appraisal", items: [
      { href: "/queue", label: "Review Queue", icon: "list" },
      { href: "/dashboard", label: "Overview", icon: "grid" },
      { href: "/portfolio", label: "Portfolio", icon: "trend" },
    ]},
    { group: "Record", items: [
      { href: "/reports", label: "Appraisal Notes", icon: "docCheck" },
      { href: "/audit", label: "Audit Trail", icon: "history" },
    ]},
    { group: "About", items: [
      { href: "/data-sources", label: "Data Sources", icon: "layers" },
      { href: "/accessibility", label: "Accessibility", icon: "help" },
    ]},
  ];
}

function isActive(path: string, href: string, search: string) {
  const [base, query] = href.split("?");
  if (path !== base) return false;
  if (query) return search.includes(query);
  return !search.includes("upload=1");
}

export function SidebarNav({ session, search = "", onNavigate }: {
  session: Session | null; search?: string; onNavigate?: () => void;
}) {
  const path = usePathname();
  const groups = navFor(session);

  return (
    <nav aria-label="Main" className="relative z-10 flex-1 overflow-y-auto scroll-slim px-4 py-5">
      {groups.map((g, gi) => (
        <div key={g.group} className={gi ? "mt-7" : ""}>
          <p className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-amber-200/50">
            {g.group}
          </p>
          <ul className="space-y-0.5">
            {g.items.map((i) => {
              const active = isActive(path, i.href, search);
              return (
                <li key={i.href}>
                  <Link href={i.href} onClick={onNavigate}
                        aria-current={active ? "page" : undefined}
                        className={`group flex items-center gap-3.5 rounded-xl px-4 py-2.5 text-[13.5px] transition-all duration-300 ${
                          active 
                            ? "bg-[rgba(30,80,130,0.45)] text-white font-medium border border-cyan-400/30 shadow-[0_0_20px_rgba(34,211,238,0.12),inset_0_1px_0_rgba(255,255,255,0.06)]" 
                            : "text-[#8a9bb5] border border-transparent hover:bg-white/[0.04] hover:text-[#c4d2e8] hover:border-white/[0.06]"
                        }`}>
                    <Icon name={i.icon}
                          className={`w-[18px] h-[18px] transition-all duration-200 ${
                            active ? "text-cyan-300 drop-shadow-[0_0_6px_rgba(34,211,238,0.5)]" : "text-[#5a7a9e] group-hover:scale-110 group-hover:text-[#7a9cc0]"
                          }`} />
                    <span className="truncate">{i.label}</span>
                    {i.badge != null && i.badge > 0 && (
                      <span className={`ml-auto shrink-0 rounded-full px-2 py-0.5 text-[10px]
                                        font-bold tabular-nums ${active
                        ? "bg-cyan-400/20 text-cyan-300 border border-cyan-400/30" : "bg-white/5 text-blue-300/70"}`}>
                        {i.badge}
                      </span>
                    )}
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </nav>
  );
}

export function Sidebar({ session, search = "", onNavigate }: {
  session: Session | null; search?: string; onNavigate?: () => void;
}) {
  return (
    <div className="flex h-full flex-col bg-[#061e33] text-slate-300 border-r border-[#0d3050] relative overflow-hidden">
      
      {/* Decorative Floating Orbs */}
      <div className="absolute inset-0 pointer-events-none z-0 overflow-hidden">
        {/* Large warm orb - bottom left */}
        <div className="absolute -bottom-16 -left-16 w-72 h-72 rounded-full opacity-40"
             style={{ background: 'radial-gradient(circle, rgba(59,130,246,0.2) 0%, rgba(30,64,175,0.08) 50%, transparent 70%)' }} />
        {/* Accent orb - top right */}
        <div className="absolute -top-10 -right-10 w-48 h-48 rounded-full opacity-30"
             style={{ background: 'radial-gradient(circle, rgba(34,211,238,0.15) 0%, transparent 60%)' }} />
        {/* Mid orb */}
        <div className="absolute top-[45%] right-[-2rem] w-40 h-40 rounded-full opacity-25"
             style={{ background: 'radial-gradient(circle, rgba(99,102,241,0.2) 0%, transparent 60%)' }} />
             
        {/* Subtle noise/grain texture */}
        <div className="absolute inset-0 opacity-[0.03]" 
             style={{ backgroundImage: 'url("data:image/svg+xml,%3Csvg viewBox=\'0 0 256 256\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cfilter id=\'n\'%3E%3CfeTurbulence type=\'fractalNoise\' baseFrequency=\'0.9\' numOctaves=\'4\' stitchTiles=\'stitch\'/%3E%3C/filter%3E%3Crect width=\'100%25\' height=\'100%25\' filter=\'url(%23n)\' opacity=\'0.5\'/%3E%3C/svg%3E")' }} />
      </div>

      {/* Header — the same mark the front door and the topbar wear. */}
      <Link href="/" onClick={onNavigate} aria-label="PRAMAAN — home"
            className="relative z-10 flex shrink-0 items-center px-5 py-5 border-b border-white/[0.06]">
        <BrandMark tone="light" size="md" />
      </Link>

      <SidebarNav session={session} search={search} onNavigate={onNavigate} />

      {/* Footer */}
      <div className="relative z-10 shrink-0 border-t border-white/[0.06] px-5 py-5">
        {/* Emblem watermark in footer */}
        <div className="absolute right-3 bottom-3 w-16 h-16 opacity-[0.03] pointer-events-none">
          <Emblem tone="dark" className="w-full h-full invert" />
        </div>
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg border border-cyan-400/15 flex items-center justify-center bg-[rgba(30,80,130,0.3)] shrink-0">
            <Icon name="shield" className="w-4 h-4 text-cyan-400/70" />
          </div>
          <div>
            <p className="text-[9px] font-semibold tracking-[0.18em] text-white/60 uppercase mb-1">
              Verify. <span className="text-cyan-400/80">Trust.</span> Transform.
            </p>
            <p className="text-[9.5px] leading-[1.5] text-white/25">
              For internal use by authorized officers only.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
