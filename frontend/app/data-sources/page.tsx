"use client";

import { PublicFrame } from "@/components/layout/PublicFrame";
import { useReveal } from "@/lib/motion";
import { Icon } from "@/components/ui/Icon";

/** Where the numbers come from — including the one place we have no data and therefore
 *  do not score. That last section is the reason this page exists. */
const SOURCES = [
  {
    name: "MoSPI PAIMANA Flash Report, June 2026",
    what: "The government’s own record of every central project of ₹150 crore and above, comparing approved cost with revised cost, and the original completion date with the revised one.",
    use: "1,604 usable project records. This is the only thing the risk model and the cost and time ranges are built from. Nothing is simulated.",
    icon: "trend",
  },
  {
    name: "KIIFB — Template for Preparation of a DPR (Bridges)",
    what: "A published government template: 17 numbered chapters, 27 salient-feature entries and 7 annexures. Survey requirements follow the IRC:SP:19 standard.",
    use: "The infrastructure checklist, item by item. Every check can be traced to a chapter that a real template requires.",
    icon: "docCheck",
  },
  {
    name: "KIIFB — DPR template (Buildings)",
    what: "Chapters 1–18, for building and social-infrastructure projects.",
    use: "The building checklist — 18 checks.",
    icon: "doc",
  },
  {
    name: "KIIFB — Guidelines for preparing a DPR (general)",
    what: "Chapters 1–18, used where no template exists for that sector. It adds an Environmental and Sustainability chapter that the Buildings template does not have.",
    use: "The public-works checklist — 19 checks. Where the templates differ, that difference is kept rather than flattened.",
    icon: "list",
  },
];

export default function DataSources() {
  const reveal = useReveal<HTMLDivElement>({ immediate: true });

  return (
    <PublicFrame title="Data sources"
                 subtitle="A risk figure is only as good as the data it was learned from, and a check is only as good as the rulebook behind it. Both are named here.">
      <div ref={reveal} className="max-w-5xl space-y-14">
          <div className="grid gap-6 md:grid-cols-2">
            {SOURCES.map((s) => (
              <div key={s.name} data-reveal
                   className="group relative overflow-hidden rounded-xl border border-paper-edge bg-paper p-6 
                              shadow-card transition-all duration-300 hover:-translate-y-1 hover:border-brand/30 
                              hover:shadow-pop">
                <div className="absolute inset-0 bg-gradient-to-br from-brand-soft/20 to-transparent opacity-0 transition-opacity duration-300 group-hover:opacity-100" />
                <div className="relative">
                  <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-full bg-brand-soft text-brand shadow-sm ring-1 ring-brand/10 transition-transform duration-300 group-hover:scale-110">
                    <Icon name={s.icon as any} className="h-5 w-5" />
                  </div>
                  <h2 className="display text-base font-bold leading-snug text-ink transition-colors group-hover:text-brand-deep">{s.name}</h2>
                  <p className="mt-2.5 text-[13px] leading-relaxed text-ink-soft">{s.what}</p>
                  
                  <div className="mt-5 rounded-lg bg-paper-soft p-4 ring-1 ring-paper-edge/50 transition-colors group-hover:bg-brand-soft/40">
                    <p className="text-[13px] leading-relaxed text-ink">
                      <b className="mb-1.5 flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-brand">
                        <Icon name="check" className="h-3.5 w-3.5" /> How it is used
                      </b>
                      {s.use}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>

          <section data-reveal className="relative max-w-3xl overflow-hidden rounded-xl border border-gold/30 bg-gradient-to-br from-gold/5 to-transparent p-8 shadow-sm">
            <div className="absolute left-0 top-0 h-full w-1.5 bg-gold" />
            <h2 className="display text-2xl font-bold text-ink flex items-center gap-2.5">
              <Icon name="ban" className="h-6 w-6 text-gold" />
              What we do not have
            </h2>
            <div className="mt-4 space-y-4 text-sm leading-relaxed text-ink-soft">
              <p>
                PRAMAAN does <b className="text-ink">not</b> compare unit rates against a Schedule of Rates — the
                official price list for construction work — because no published version of it
                was available. The check is designed but deliberately not built: comparing
                against invented rates would produce confident findings with nothing behind
                them, which is worse than reporting nothing.
              </p>
              <p>
                So it is absent from the score rather than sitting inside it as a component
                that could never be filled in. The quality score is made up only of what
                PRAMAAN can evidence from the document in front of it — nothing in it is a
                placeholder.
              </p>
            </div>
          </section>

          <section data-reveal className="max-w-3xl rounded-xl border border-paper-edge bg-paper p-8 shadow-sm">
            <h2 className="display text-2xl font-bold text-ink">The sample reports</h2>
            <p className="mt-4 text-sm leading-relaxed text-ink-soft">
              The six reports in the demo are made up, and labelled as such. No real
              completed DPR was available, and to test whether a problem is caught you have to
              know the problem is there. What is not invented is their shape: every chapter
              exists because one of the published templates above requires it, in that
              template&rsquo;s own numbering and wording.
            </p>
          </section>
      </div>
    </PublicFrame>
  );
}
