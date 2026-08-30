"use client";
/** Privacy.
 *
 *  Written from what the code actually does rather than from a template — the one section
 *  worth reading is the one naming the third party a document is sent to, because the
 *  landing page's "sits on your desk" copy is about the deployment this is designed for,
 *  not about the hosted demo you are currently looking at.
 */
import { PublicFrame } from "@/components/layout/PublicFrame";
import { Icon } from "@/components/ui/Icon";
import { useReveal } from "@/lib/motion";

const HELD: [string, string][] = [
  ["The PDF you upload",
   "Stored so it can be read, rasterised for the page viewer, and cited by a finding."],
  ["Text extracted from it",
   "Page by page, so a finding can point at the exact line it came from."],
  ["Your account",
   "Email address, display name, role and organisation. No other personal data is asked for."],
  ["What you did",
   "Every appraisal, decision and export is written to an audit trail against your name. " +
   "That is the point of the audit trail and it cannot be switched off."],
];

export default function Privacy() {
  const reveal = useReveal<HTMLDivElement>({ immediate: true });

  return (
    <PublicFrame title="Privacy"
                 subtitle="What this prototype stores, where it goes, and the one place it leaves the building.">
      <div ref={reveal} className="max-w-3xl space-y-6">
        <section data-reveal
                 className="rounded-xl border border-paper-edge bg-paper p-6 shadow-sm">
          <h2 className="display text-lg font-bold text-ink">What is held</h2>
          <ul className="mt-4 space-y-3">
            {HELD.map(([what, why]) => (
              <li key={what} className="flex gap-3">
                <Icon name="doc" className="mt-0.5 h-4 w-4 shrink-0 text-brand" />
                <p className="text-sm leading-relaxed text-ink-soft">
                  <b className="text-ink">{what}.</b> {why}
                </p>
              </li>
            ))}
          </ul>
        </section>

        {/* The section that matters. A privacy page that omits this is worse than none. */}
        <section data-reveal
                 className="relative overflow-hidden rounded-xl border border-gold/30
                            bg-gradient-to-br from-gold/5 to-transparent p-6 shadow-sm">
          <div className="absolute left-0 top-0 h-full w-1.5 bg-gold" />
          <h2 className="display flex items-center gap-2.5 text-lg font-bold text-ink">
            <Icon name="cloud" className="h-5 w-5 text-gold" />
            Where a document leaves the building
          </h2>
          <div className="mt-3 space-y-3 text-sm leading-relaxed text-ink-soft">
            <p>
              Field extraction calls a cloud language model — Google Gemini — so passages of
              an uploaded document are sent to Google in the course of an assessment. That is
              true of this hosted demonstration.
            </p>
            <p>
              It is not an unavoidable property of the system. Every model call goes through
              a single provider module, and the deployment this is designed for runs the
              model on the department&rsquo;s own hardware with nothing leaving the network.
              But on the demo you are looking at, it leaves — so{" "}
              <b className="text-ink">do not upload a real, unpublished government
              document</b>.
            </p>
          </div>
        </section>

        <section data-reveal
                 className="rounded-xl border border-paper-edge bg-paper p-6 shadow-sm">
          <h2 className="display text-lg font-bold text-ink">How long it is kept</h2>
          <p className="mt-2.5 text-sm leading-relaxed text-ink-soft">
            The demo runs on free hosting with no persistent disk. Uploaded PDFs and page
            images are erased on every restart and every deploy; the database rows describing
            them outlive the files. Nothing here is a record, and nothing should be relied on
            to still be here tomorrow.
          </p>
        </section>

        <section data-reveal
                 className="rounded-xl border border-paper-edge bg-paper p-6 shadow-sm">
          <h2 className="display text-lg font-bold text-ink">No tracking</h2>
          <p className="mt-2.5 text-sm leading-relaxed text-ink-soft">
            There are no analytics, no advertising and no third-party trackers on this site.
            Browser storage is used for two things only: the session token that keeps you
            signed in, and whether you left the navigation rail open.
          </p>
        </section>

        <p data-reveal className="text-2xs text-ink-faint">
          Last reviewed 4 September 2026.
        </p>
      </div>
    </PublicFrame>
  );
}
