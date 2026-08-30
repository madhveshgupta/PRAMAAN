"use client";
/** Terms of use.
 *
 *  The footer has always linked here and there has never been a page — the link 404'd. What
 *  it says is deliberately short and deliberately unflattering: this is a hackathon
 *  prototype, and terms that borrow the tone of a live government service would be the one
 *  claim on the site nothing behind it supports.
 */
import { PublicFrame } from "@/components/layout/PublicFrame";
import { Icon } from "@/components/ui/Icon";
import { useReveal } from "@/lib/motion";

const TERMS: [string, string][] = [
  ["What this is",
   "PRAMAAN is a prototype built for the Smart India Hackathon. It is not an official " +
   "Government of India service, it is not affiliated with any ministry or department, and " +
   "nothing it produces carries statutory weight."],
  ["Advisory only",
   "Every score, finding and range is advice for a person to weigh. The system does not " +
   "approve or reject a project, and it is built so that it cannot. The decision belongs to " +
   "the authorised officer, and is recorded in their name."],
  ["No warranty",
   "The software is provided as it stands, without warranty of any kind. A finding may be " +
   "wrong and a check may miss something. Do not rely on it as the sole basis for a " +
   "decision that commits public money."],
  ["The demonstration accounts",
   "The three demo logins are public and their password is published on the sign-in card. " +
   "Anything uploaded through them should be treated as visible to anyone. Do not put a " +
   "real, unpublished government document into this demo."],
  ["Your documents",
   "A file you upload is stored so it can be assessed and so a finding can point back at " +
   "the page it came from. On the free hosting tier that storage is erased whenever the " +
   "service restarts, so nothing here should be treated as a record of anything."],
];

export default function Terms() {
  const reveal = useReveal<HTMLDivElement>({ immediate: true });

  return (
    <PublicFrame title="Terms of use"
                 subtitle="Short, because a prototype should not read like a service that exists.">
      <div ref={reveal} className="max-w-3xl space-y-6">
        <div data-reveal
             className="flex gap-3 rounded-xl border border-gold/30 bg-gold/5 p-5">
          <Icon name="shield" className="mt-0.5 h-5 w-5 shrink-0 text-gold" />
          <p className="text-sm leading-relaxed text-ink">
            <b>This is a Smart India Hackathon prototype, not a government service.</b> Using
            it implies you accept the five points below.
          </p>
        </div>

        {TERMS.map(([heading, body]) => (
          <section key={heading} data-reveal
                   className="rounded-xl border border-paper-edge bg-paper p-6 shadow-sm">
            <h2 className="display text-lg font-bold text-ink">{heading}</h2>
            <p className="mt-2.5 text-sm leading-relaxed text-ink-soft">{body}</p>
          </section>
        ))}

        <p data-reveal className="text-2xs text-ink-faint">
          Last reviewed 4 September 2026.
        </p>
      </div>
    </PublicFrame>
  );
}
