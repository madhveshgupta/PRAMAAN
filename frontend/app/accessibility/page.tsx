"use client";

import { PublicFrame } from "@/components/layout/PublicFrame";
import { useReveal } from "@/lib/motion";
import { Icon } from "@/components/ui/Icon";

const COMMITMENTS = [
  {
    title: "Nothing depends on colour alone",
    body: "Every severity and every status carries a word and a symbol as well as a colour, so the meaning still comes through in black and white, or for a reader who cannot distinguish colours.",
    icon: "shield",
  },
  {
    title: "Works with a keyboard",
    body: "In the review screen, j and k move between findings and [ and ] move between pieces of evidence. You can always see which item is selected — a 2px outline that is never switched off.",
    icon: "list",
  },
  {
    title: "Built for the monitor it will be used on",
    body: "High contrast, large type, and a layout that holds together at 125% browser zoom. Tested on an old office display, not a designer's.",
    icon: "gauge",
  },
  {
    title: "Prints clearly",
    body: "Menus and buttons are left out of printouts and card borders darken, so an appraisal note reads on paper the way it does on screen.",
    icon: "docCheck",
  },
  {
    title: "Text you can select",
    body: "Findings quote the real text from the report, not pictures of it. That means a screen reader can read the evidence itself.",
    icon: "doc",
  },
];

export default function Accessibility() {
  const reveal = useReveal<HTMLDivElement>({ immediate: true });

  return (
    <PublicFrame title="Accessibility"
                 subtitle="This is a prototype and it has not been through a formal WCAG audit. Below is what was deliberately built in, written plainly so you can check it rather than take it on trust.">
      <div ref={reveal} className="max-w-4xl space-y-12">
        <div className="grid gap-6 md:grid-cols-2">
          {COMMITMENTS.map((c) => (
            <div key={c.title} data-reveal
                 className="group relative overflow-hidden rounded-xl border border-paper-edge bg-paper p-6 
                            shadow-card transition-all duration-300 hover:-translate-y-1 hover:border-brand/30 
                            hover:shadow-pop">
              <div className="absolute inset-0 bg-gradient-to-br from-brand-soft/20 to-transparent opacity-0 transition-opacity duration-300 group-hover:opacity-100" />
              <div className="relative">
                <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-full bg-brand-soft text-brand shadow-sm ring-1 ring-brand/10 transition-transform duration-300 group-hover:scale-110">
                  <Icon name={c.icon as any} className="h-5 w-5" />
                </div>
                <h2 className="display text-base font-bold leading-snug text-ink transition-colors group-hover:text-brand-deep">{c.title}</h2>
                <p className="mt-2.5 text-[13px] leading-relaxed text-ink-soft">{c.body}</p>
              </div>
            </div>
          ))}
        </div>

        <section data-reveal className="relative max-w-3xl overflow-hidden rounded-xl border border-gold/30 bg-gradient-to-br from-gold/5 to-transparent p-8 shadow-sm">
          <div className="absolute left-0 top-0 h-full w-1.5 bg-gold" />
          <h2 className="display text-2xl font-bold text-ink flex items-center gap-2.5">
            <Icon name="ban" className="h-6 w-6 text-gold" />
            One known gap
          </h2>
          <p className="mt-4 text-sm leading-relaxed text-ink-soft">
            The report is displayed as an image, so a screen reader cannot read the page itself. 
            The quoted evidence beside every finding carries the same text, and that text can be 
            selected and read natively.
          </p>
        </section>
      </div>
    </PublicFrame>
  );
}
