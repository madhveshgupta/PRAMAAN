"use client";
/** Contact.
 *
 *  No form. A form that posts nowhere is a worse answer than a page that says plainly there
 *  is no desk behind it — and there is no desk behind it, because this is a hackathon
 *  prototype rather than a service with a support function.
 */
import Link from "next/link";
import { PublicFrame } from "@/components/layout/PublicFrame";
import { Icon, type IconName } from "@/components/ui/Icon";
import { useReveal } from "@/lib/motion";

const ROUTES: { icon: IconName; heading: string; body: string;
                link?: [string, string] }[] = [
  {
    icon: "play",
    heading: "Try it first",
    body: "Three demonstration accounts are open on the sign-in card, password published " +
          "beside them. Six sample reports are already loaded — three sound, three with " +
          "known defects — so there is something to look at before anything is uploaded.",
    link: ["Sign in", "/?signin=1&demo=1"],
  },
  {
    icon: "layers",
    heading: "Where the numbers come from",
    body: "Most questions about a figure on this site are answered by the page that names " +
          "the source it was learned from, including the one check that is deliberately " +
          "not built.",
    link: ["Data sources", "/data-sources"],
  },
  {
    icon: "help",
    heading: "Using it with assistive technology",
    body: "What has been done for keyboard, screen reader and print, stated as commitments " +
          "rather than as a compliance badge.",
    link: ["Accessibility", "/accessibility"],
  },
];

export default function Contact() {
  const reveal = useReveal<HTMLDivElement>({ immediate: true });

  return (
    <PublicFrame title="Contact"
                 subtitle="What this is, and the honest answer about who is behind it.">
      <div ref={reveal} className="max-w-3xl space-y-6">
        <div data-reveal
             className="flex gap-3 rounded-xl border border-gold/30 bg-gold/5 p-5">
          <Icon name="users" className="mt-0.5 h-5 w-5 shrink-0 text-gold" />
          <p className="text-sm leading-relaxed text-ink">
            PRAMAAN is a student project built for the Smart India Hackathon. There is no
            support desk, no helpline and no department behind it — so rather than a contact
            form that posts nowhere, here is where the answers actually are.
          </p>
        </div>

        {ROUTES.map((r) => (
          <section key={r.heading} data-reveal
                   className="rounded-xl border border-paper-edge bg-paper p-6 shadow-sm">
            <h2 className="display flex items-center gap-2.5 text-lg font-bold text-ink">
              <span className="grid h-9 w-9 place-items-center rounded-full bg-brand-soft
                               text-brand ring-1 ring-brand/10">
                <Icon name={r.icon} className="h-4 w-4" />
              </span>
              {r.heading}
            </h2>
            <p className="mt-3 text-sm leading-relaxed text-ink-soft">{r.body}</p>
            {r.link && (
              <Link href={r.link[1]}
                    className="mt-4 inline-flex items-center gap-1.5 text-sm font-medium
                               text-brand underline-offset-4 hover:underline">
                {r.link[0]}
                <Icon name="arrow" className="h-3.5 w-3.5" />
              </Link>
            )}
          </section>
        ))}

        <section data-reveal
                 className="rounded-xl border border-paper-edge bg-paper-soft p-6">
          <h2 className="display text-lg font-bold text-ink">If you are evaluating it</h2>
          <p className="mt-2.5 text-sm leading-relaxed text-ink-soft">
            Reach the team through the Smart India Hackathon channel this entry was submitted
            under. That is the only route that reaches a person, and inventing an official
            address here would be exactly the sort of unsupported claim this product is built
            to catch.
          </p>
        </section>
      </div>
    </PublicFrame>
  );
}
