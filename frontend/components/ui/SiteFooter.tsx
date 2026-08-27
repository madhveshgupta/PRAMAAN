import Link from "next/link";

import { Icon, type IconName } from "@/components/ui/Icon";

/**
 * The footer carries what a government site is expected to state plainly: what the system
 * is, what it explicitly does NOT do, where the data comes from, and who is accountable.
 * The advisory notice is repeated here on purpose — it should be visible on every screen,
 * not only where a score happens to appear.
 *
 * The two lists are exported because they are the product's plainest statement of scope,
 * and anything else that restates them should read them from here rather than retype them.
 *
 * It is built to a height budget: four columns, one advisory strip, one bottom bar, and
 * nothing that grows. Chrome is the last thing on the page and the least important thing
 * on it, so it is set at 11px and packed tightly — a footer that fills a screen is a footer
 * competing with the page it belongs to.
 */
export const DOES = [
  "Checks what information is missing",
  "Finds conflicting information",
  "Verifies financial claims",
  "Highlights cost and delay risks",
];

export const DOES_NOT = [
  "Does not make the final decision",
  "Does not approve or reject a project",
  "Does not report a finding without evidence",
  "Does not benchmark against information it does not have",
];

const BASIS = [
  "Learned from MoSPI PAIMANA outcomes for central projects of ₹150 crore and above",
  "Ranges come from similar completed projects, never simulated",
  "Checklists are versioned — a past assessment keeps the one it was scored against",
];

/** The three commitments, each with the glyph that already carries its meaning elsewhere in
 *  the product: `check` for what the system does and `ban` for what it refuses to do. Tones
 *  are picked for a navy ground rather than for paper — the greens that read on white are
 *  near-invisible here.
 *
 *  Note the deliberate absence of red on the refusals. This is an advisory tool, and a red
 *  list under "what it does not do" would read as four warnings nobody raised. */
const COLUMNS: ReadonlyArray<{
  heading: string;
  items: readonly string[];
  glyph: IconName;
  tone: string;
}> = [
  { heading: "What it does", items: DOES, glyph: "check", tone: "text-[#5cb98d]" },
  { heading: "What it does not do", items: DOES_NOT, glyph: "ban", tone: "text-gold-bright" },
  { heading: "Basis", items: BASIS, glyph: "layers", tone: "text-white/40" },
];

/** Every one of these resolves to a real route. A public service footer is expected to
 *  carry terms, privacy and contact, and a link in that bar that 404s is worse than no link
 *  at all — so the three of them say plainly what a prototype can honestly say. */
const BOTTOM_LINKS = [
  ["/#principles", "About"],
  ["/accessibility", "Accessibility"],
  ["/data-sources", "Data sources"],
  ["/terms", "Terms"],
  ["/privacy", "Privacy"],
  ["/contact", "Contact"],
] as const;

/** The ground: a cable-stayed span reduced to a deck line and one fan of stays, at the
 *  opacity of a watermark. Line art rather than an illustration, and tiled small rather
 *  than placed large, so it reads as the paper this kind of document is drawn on instead of
 *  as a picture the footer is sitting on top of.
 *
 *  The mask fades it out well before the advisory strip. At full strength across the whole
 *  footer the stays cross the smallest text on the page and read as scratches. */
function Blueprint() {
  return (
    <svg aria-hidden preserveAspectRatio="xMidYMid slice"
         className="pointer-events-none absolute inset-0 h-full w-full
                    [mask-image:linear-gradient(to_bottom,#000,#000_45%,transparent_78%)]">
      <defs>
        <pattern id="pramaan-span" width="300" height="150" patternUnits="userSpaceOnUse">
          <g fill="none" stroke="#fff" strokeLinecap="round">
            <path d="M90 22v100" strokeWidth="1.1" opacity=".055" />
            <path d="m90 30 84 92M90 30l50 96M90 30l-50 94M90 30 8 118"
                  strokeWidth="1" opacity=".03" />
            <path d="M0 126h300" strokeWidth="1.1" opacity=".045" />
          </g>
        </pattern>
      </defs>
      <rect width="100%" height="100%" fill="url(#pramaan-span)" />
    </svg>
  );
}

export function SiteFooter() {
  return (
    <footer className="no-print mt-auto">
      <div className="rule-gold" />

      <div className="relative overflow-hidden bg-brand-ink text-white/70">
        <Blueprint />

        <div className="relative mx-auto max-w-screen px-5 pt-10 pb-7">
          {/* `divide-x` supplies the 1px separators, so the rules cannot fall out of step
              with the columns the way four hand-placed borders eventually do. It is applied
              only from `lg`, where the four columns actually sit side by side — a vertical
              rule between stacked blocks is a rule pointing the wrong way. */}
          <div className="grid gap-y-9 lg:grid-cols-4 lg:gap-y-0 lg:divide-x
                          lg:divide-white/10">
            {/* ------------------------------------------------------------ identity -- */}
            <div className="lg:pr-8">
              <span aria-hidden className="flex h-[3px] w-12 overflow-hidden rounded-full">
                <span className="flex-1 bg-[#FF9933]" />
                <span className="flex-1 bg-white" />
                <span className="flex-1 bg-[#138808]" />
              </span>
              <p className="display mt-3 text-[22px] font-bold leading-none tracking-tight
                            text-white">
                PRAMAAN
              </p>
              <p className="mt-1.5 text-2xs text-white/45">
                प्रमाण — <i>evidence</i>
              </p>
              <p className="mt-3 max-w-[30ch] text-2xs leading-relaxed">
                We check Detailed Project Reports (DPRs). Every figure PRAMAAN reports can
                be traced back to the page it came from.
              </p>
            </div>

            {/* --------------------------------------------------------- commitments -- */}
            {COLUMNS.map(({ heading, items, glyph, tone }) => (
              <div key={heading} className="lg:px-8 lg:last:pr-0">
                <p className="text-2xs font-bold uppercase tracking-[0.13em] text-gold-vivid">
                  {heading}
                </p>
                <ul className="mt-3 space-y-1.5">
                  {items.map((t) => (
                    <li key={t} className="flex gap-2 text-2xs leading-[1.45] text-white/70">
                      <Icon name={glyph} className={`mt-px h-3.5 w-3.5 shrink-0 ${tone}`} />
                      <span>{t}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>

          {/* ---------------------------------------------------------------- advisory -- */}
          {/* One line at desktop width. The full sentence is kept rather than trimmed to fit:
              the clause naming the deciding officer is the accountability half of the
              notice, and a disclaimer that drops it says something weaker than the product
              actually promises. */}
          <div className="mt-6 flex items-center gap-3 border-l-2 border-gold-vivid
                          bg-white/[0.035] px-4 py-2.5">
            <Icon name="shield" className="h-4 w-4 shrink-0 text-gold-vivid" />
            <p className="text-2xs leading-relaxed">
              <b className="text-white">Advisory only.</b> PRAMAAN scores, flags problems and
              shows the evidence. The final decision rests with the authorised officer, and is
              recorded in their name.
            </p>
            <span className="ml-auto hidden shrink-0 items-center gap-2 xl:flex">
              {/* Honest labels only. This is an unaffiliated prototype, and a row of
                  invented compliance badges under a government masthead is precisely the
                  claim this footer exists to avoid making. */}
              {["Evidence-linked findings", "Versioned checklists"].map((t) => (
                <span key={t}
                      className="border border-white/15 px-2 py-1 text-[10px] uppercase
                                 tracking-[0.1em] text-white/50">
                  {t}
                </span>
              ))}
            </span>
          </div>

          {/* -------------------------------------------------------------- bottom bar -- */}
          <div className="mt-4 flex flex-wrap items-center gap-x-6 gap-y-2 border-t
                          border-white/10 pt-4">
            <p className="text-2xs text-white/40">
              © 2026 PRAMAAN · Smart India Hackathon prototype — not an official Government
              of India service
            </p>
            <nav className="flex flex-wrap gap-x-5 gap-y-2 text-2xs lg:ml-auto">
              {BOTTOM_LINKS.map(([href, label]) => (
                <Link key={href} href={href}
                      className="text-gold underline-offset-4 transition-colors
                                 hover:text-gold-bright hover:underline">
                  {label}
                </Link>
              ))}
            </nav>
          </div>
        </div>
      </div>
    </footer>
  );
}
