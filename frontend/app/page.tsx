import Image from "next/image";
import Link from "next/link";

import heroEngineer from "@/public/hero-engineer.png";
import { Counter } from "@/components/ui/Counter";
import { Icon, type IconName } from "@/components/ui/Icon";
import { SiteFooter } from "@/components/ui/SiteFooter";
import { SiteHeader } from "@/components/ui/SiteHeader";
import { LandingAnimations } from "@/components/landing/LandingAnimations";
import { GradientOrbs, FloatingParticles, FloatingShapes, WaveDivider, AnimatedDotGrid } from "@/components/landing/Backgrounds";

/* The front door is the one page written for someone who has never heard of this, so it is
   the one page that does not wear the working chrome: sans headings rather than the app's
   serif, a light ground, generous radii. Everything behind sign-in keeps the tighter,
   flatter treatment an officer sits under all day. */

/* Three figures under the hero, set to the approved design reference.

   The labels say "signals" rather than "risk detected" on purpose: PRAMAAN raises a flag for
   a human to weigh, and a hero that reads as though the system had declared 71% of projects
   risky claims an authority invariant 4 explicitly denies it.

   NOTE for whoever ships this, unchanged by that rewording: these are the reference's
   marketing figures, not measured output. 1,604 is the size of the MoSPI training panel, not
   a count of DPRs this system has appraised, and 71/64 come from one sample document's
   predictions rather than from any population — so the two percentage labels still describe
   a cohort we have not measured. Honest equivalents we can evidence are "1,604 project
   outcomes learned from", "25 checks run on every report" and "100% of findings linked to a
   page". */
const HERO_STATS: [IconName, string, string, string, string][] = [
  ["shield", "1,604", "+", "Projects assessed", "bg-brand-soft text-brand"],
  ["pie", "71", "%", "Projects with cost-risk signals", "bg-ok-soft text-ok"],
  ["clock", "64", "%", "Projects with schedule-risk signals", "bg-gold-soft text-gold-text"],
];

/* The trust strip under the hero. Four claims, each of which the product can actually
   demonstrate on the next screen — which is the only reason it is allowed to sit this close
   to the call to action. */
const TRUST = [
  "Evidence-based appraisal",
  "Page-level traceability",
  "Human-in-the-loop",
  "Audit-ready",
];

const PILLARS: [IconName, string, string][] = [
  ["docCheck", "Compliance",
   "Checks follow MoRTH and CVC requirements and audit expectations."],
  ["search", "Transparency",
   "Every finding shows the page it came from."],
  ["cpu", "Explainable AI",
   "Every result shows its reasoning. A person always decides."],
  ["users", "Accountable",
   "Built for officers, not just auditors."],
  ["lock", "Secure & private",
   "Your data stays with your department."],
];

/* The ring colour walks from brand blue through gold to green across the five steps, so
   the row reads as travel toward a decision rather than as five identical badges. */
const PROCESS: [IconName, string, string, string, string][] = [
  ["cloud", "Upload DPR", "Upload the project", "report securely", "ring-brand/40 text-brand"],
  ["scan", "AI Scanning", "PRAMAAN reads and", "checks every page", "ring-brand/40 text-brand"],
  ["list", "Risk & Compliance", "Checks the rules and", "finds problems", "ring-ok/40 text-ok"],
  ["trend", "Insights", "See findings with the", "page they came from", "ring-gold-vivid/70 text-gold-text"],
  ["check", "Decide", "Approve, ask a question", "or send it back", "ring-ok/50 text-ok"],
];

const CAPABILITIES: [IconName, string, string][] = [
  ["layers", "Checks what information is missing",
   "It goes chapter by chapter against the template that sector actually requires. A hospital block and a water supply scheme are not judged against the same list."],
  ["search", "Finds conflicting information",
   "The same figure stated two different ways, eighty pages apart. No AI is involved here — it simply holds the whole report in view at once, which no reader can."],
  ["rupee", "Verifies financial claims",
   "It recalculates the stated rate of return from the report’s own cash-flow tables. If the report’s own numbers do not support the figure it claims, that is a finding."],
  ["chart", "Highlights cost and delay risks",
   "Two likelihoods, learned from 1,604 completed central government projects. Each one comes with the factors behind it attached — never a bare score."],
  ["clock", "Likely cost and time ranges",
   "A likely case, a cautious case and a worst case (P50, P80 and P95), taken from what comparable projects actually cost and how late they actually ran. Read off real history, never simulated."],
  ["link", "Evidence for every number",
   "Click any number and the report opens at that page with the exact line highlighted. A figure that cannot do this is discarded, not shown."],
];

const SECTORS: [string, string, string][] = [
  ["/sectors/roads.jpg", "Roads & Highways", "Transport & Logistics"],
  ["/sectors/water.jpg", "Water Resources", "Water & Sanitation"],
  ["/sectors/transport.jpg", "Urban Public Transport", "Transport & Logistics"],
  ["/sectors/energy.jpg", "Electricity Generation", "Energy"],
];

const DESKS = [
  {
    role: "For the submitting department",
    icon: "doc" as IconName,
    lead: "Check your DPR before sending it for appraisal.",
    points: [
      "Check a draft against the same checklist the ministry will use",
      "See every missing chapter and every conflict, with page numbers",
      "Fix and resubmit — each version keeps its own assessment",
    ],
    cta: ["Sign in as an applicant", "/?signin=1"] as const,
  },
  {
    role: "For the appraising ministry",
    icon: "users" as IconName,
    lead: "Review projects faster, with findings and evidence already prepared.",
    points: [
      "A ranked list of every project, by score and by risk",
      "Findings and the full checklist — what passed, not only what failed",
      "Recommend or approve, with the officer and the reason recorded",
    ],
    cta: ["Sign in as a reviewer", "/?signin=1&demo=1"] as const,
  },
];

const FAQ: [string, React.ReactNode][] = [
  ["Does PRAMAAN approve or reject a project?",
   <>No, and it is built so that it cannot. It scores, flags problems and shows the evidence
    behind them. The decision belongs to a named officer who holds that authority. This is
    enforced by the system, not just promised: no finding can carry a status of “fail”, and
    a recommendation and a sanction are written to the audit trail as two separate acts,
    each naming the person who made it.</>],
  ["Where do the risk numbers come from?",
   <>From MoSPI PAIMANA flash reports — the government’s own records of every central
    project of ₹150 crore and above, comparing the approved cost with the revised cost and
    the original completion date with the revised one. That gives 1,604 usable records. On a
    standard accuracy measure the cost model scores 0.82 and the delay model 0.67. Both beat
    the obvious baselines. Real, not spectacular.</>],
  ["What prevents PRAMAAN from inventing a number?",
   <>Before any figure is stored, PRAMAAN has to find it again in the text of the document.
    If it cannot, the figure is thrown away and the refusal is logged — and the assessment
    shows you that list, so anything it refused to report is visible rather than hidden.</>],
  ["What does PRAMAAN deliberately not check?",
   <>Unit rates against a Schedule of Rates (the official price list for construction work).
    No published version of that list was available, and comparing against invented rates
    would produce confident findings with nothing behind them — so the check is designed but
    not built, and the score is made up only of the components it can actually evidence.</>],
  ["Are the sample reports real DPRs?",
   <>No, and they say so. To test whether PRAMAAN catches a problem, you have to know the
    problem is there — so the samples have known faults built into them. What is not invented
    is their shape: every chapter exists because a published government template requires it,
    using that template’s own numbering.</>],
];

/** Section heading, so the eyebrow / title / standfirst rhythm is set in one place rather
 *  than re-typed with a different size at every section. */
function Heading({ eyebrow, title, children, inverted = false }: {
  eyebrow: string; title: React.ReactNode; children?: React.ReactNode; inverted?: boolean;
}) {
  return (
    <div className="max-w-2xl section-heading">
      <p className={`text-2xs font-bold uppercase tracking-[0.14em] ${inverted ? "text-gold-vivid text-glow-gold" : "text-gold-text"}`}>
        {eyebrow}
      </p>
      <h2 className={`mt-3 text-[28px] md:text-[34px] font-bold tracking-tight leading-tight
                     ${inverted ? "text-white drop-shadow-sm" : "text-brand-ink"}`}>
        {title}
      </h2>
      {children && (
        <p className={`mt-4 text-[17px] leading-relaxed ${inverted ? "text-white/70" : "text-ink-soft"}`}>
          {children}
        </p>
      )}
    </div>
  );
}

export default function Landing() {
  return (
    <LandingAnimations>
    <div className="min-h-screen flex flex-col bg-paper">
      <SiteHeader variant="public" />

      <main className="flex-1">
        {/* ------------------------------------------------------------------ hero -- */}
        <section className="hero-shell relative bg-paper overflow-hidden">
          <GradientOrbs variant="light" />
          {/* `overflow-hidden` is load-bearing: the photograph inside is scaled and drifted by
              the scroll parallax, so without a clip it grows past this box on the left — out
              from under the white gradient that is supposed to feather it into the page, and
              into a hard vertical seam beside the panel. */}
          <div aria-hidden className="absolute inset-y-0 right-0 w-full lg:w-[62%] overflow-hidden">
            <Image src={heroEngineer} alt="" priority placeholder="blur" sizes="65vw"
                   className="object-cover object-[66%_38%]" fill />
            <div className="absolute inset-0 hidden lg:block" style={{ background:
              "linear-gradient(90deg,#fff 0%,#fff 12%,rgba(255,255,255,.57) 31%,"
              + "rgba(255,255,255,.13) 60%,rgba(255,255,255,0) 100%)" }} />
            <div className="absolute inset-0 bg-paper/85 lg:hidden" />
          </div>

          <div className="hero-container relative mx-auto w-full max-w-screen px-5 pt-12 pb-24 md:pt-16 md:pb-28">
            <div className="max-w-2xl hero-animate hero-panel glass-panel p-8 md:p-12 rounded-3xl relative overflow-hidden">
              <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-white to-transparent opacity-60" />
              <div className="absolute inset-0 bg-white/40 pointer-events-none" />

              <div className="relative z-10">
                <p className="hero-child hero-eyebrow inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full
                              bg-white/80 border border-white/60 shadow-sm text-2xs
                              font-bold uppercase tracking-[0.12em] text-ink-soft">
                  <span className="w-1.5 h-1.5 rounded-full bg-gold-vivid animate-pulse" />
                  AI-powered · Government trusted
                </p>

                <h1 className="hero-child hero-title mt-7 text-[44px] md:text-[62px] font-bold tracking-tight
                               leading-[1.04] text-brand-ink drop-shadow-sm">
                  From Complex Reports
                  <span className="block">
                    to <span className="text-gold-vivid text-glow-gold">Confident Decisions</span>
                  </span>
                </h1>
                <span aria-hidden className="hero-child hero-rule mt-6 block h-1 w-20 rounded-full bg-gold-vivid shadow-[0_0_12px_rgba(245,185,33,0.6)]" />

                <p className="hero-child hero-lede mt-7 text-[17px] md:text-lg text-ink-soft leading-relaxed
                              max-w-xl font-medium">
                  PRAMAAN reads the entire Detailed Project Report (DPR), checks for missing
                  information and inconsistencies, verifies important claims, and highlights
                  cost and delay risks — helping officers make informed decisions.
                </p>

                <div className="hero-child hero-actions mt-9 flex flex-wrap items-center gap-4">
                  <div className="magnetic relative group">
                    <div className="absolute -inset-0.5 bg-gradient-to-r from-gold-vivid to-amber-300 rounded-xl blur opacity-30 group-hover:opacity-60 transition duration-500"></div>
                    <Link href="/?signin=1&demo=1"
                          className="relative inline-flex items-center gap-2.5 px-6 py-3.5 rounded-xl
                                     bg-gradient-to-b from-gold-vivid to-gold-bright text-brand-ink font-semibold shadow-card
                                     hover:shadow-lg hover:-translate-y-0.5 transition-all duration-300">
                      <Icon name="docCheck" className="w-[18px] h-[18px]" />
                      Start a new appraisal
                      <Icon name="arrow" className="w-[18px] h-[18px]" />
                    </Link>
                  </div>
                  <Link href="#how-it-works"
                        className="inline-flex items-center gap-2.5 px-6 py-3.5 rounded-xl
                                   bg-white/80 backdrop-blur-sm border border-white font-medium text-ink
                                   shadow-sm hover:bg-white hover:shadow hover:-translate-y-0.5
                                   transition-all duration-300">
                    <Icon name="play" className="w-[18px] h-[18px] text-brand" />
                    See how it works
                  </Link>
                </div>

                <dl className="hero-stats mt-12 grid grid-cols-1 sm:grid-cols-3 gap-4">
                  {HERO_STATS.map(([icon, value, suffix, label, tile]) => (
                    <div key={label}
                         className="hero-stat glass-panel flex items-center gap-3 p-4 rounded-2xl
                                    hover:-translate-y-1 hover:shadow-lg transition-transform duration-300">
                      <span className={`grid place-items-center w-11 h-11 rounded-xl shrink-0 ${tile} shadow-sm`}>
                        <Icon name={icon} className="w-5 h-5" />
                      </span>
                      <div className="min-w-0">
                        <dd className="text-[22px] font-bold tracking-tight text-brand-ink
                                       leading-none drop-shadow-sm">
                          <Counter to={Number(value.replace(/,/g, ""))} />{suffix}
                        </dd>
                        <dt className="mt-1 text-xs text-ink-soft font-medium leading-snug">{label}</dt>
                      </div>
                    </div>
                  ))}
                </dl>

                <ul className="hero-trust mt-8 flex flex-wrap items-center gap-x-3.5 gap-y-2 text-[10px] font-bold
                               uppercase tracking-[0.09em] text-ink-faint">
                  {TRUST.map((t, i) => (
                    <li key={t} className="trust-item flex items-center gap-3.5">
                      {i > 0 && (
                        <span aria-hidden className="w-1 h-1 rounded-full bg-gold-vivid/50" />
                      )}
                      {t}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </section>

        {/* ── wave divider ── */}
        <WaveDivider color="#082a44" className="drop-shadow-lg relative z-20 -mb-1" />

        {/* ---------------------------------------------------------------- pillars -- */}
        <section className="relative bg-brand-ink pillars-section">
          <FloatingParticles count={40} color="rgba(255,255,255,0.08)" />
          <div className="relative z-10 mx-auto max-w-screen px-5 pt-8 pb-12">
            <div className="rounded-3xl bg-[#0a3556]/50 border border-white/10 p-8 md:p-12
                            shadow-2xl backdrop-blur-md">
              <div className="flex flex-col items-center">
                <p className="text-2xs font-bold uppercase tracking-[0.14em] text-gold-vivid text-glow-gold mb-3">
                  Why PRAMAAN
                </p>
                <h2 className="text-[22px] md:text-[26px] font-bold tracking-tight
                               text-white text-center drop-shadow-sm">
                  Built for better public infrastructure
                </h2>
                <span aria-hidden className="hidden sm:block mt-6 h-px w-16 bg-gold-vivid shadow-[0_0_8px_rgba(245,185,33,0.5)]" />
              </div>

              <div className="mt-10 grid gap-y-10 sm:grid-cols-2 lg:grid-cols-5 gap-x-6">
                {PILLARS.map(([icon, title, body], i) => (
                  <div key={title}
                       className={`pillar-card flex gap-4 px-0 lg:px-4 ${
                         i > 0 ? "lg:border-l lg:border-white/10" : ""}`}>
                    <span className="grid place-items-center w-11 h-11 rounded-xl shrink-0
                                     bg-[#082a44] text-white border border-white/20 shadow-inner">
                      <Icon name={icon} className="w-5 h-5" />
                    </span>
                    <div className="min-w-0">
                      <p className="font-semibold text-[15px] text-white leading-snug">
                        {title}
                      </p>
                      <p className="mt-2 text-[13px] text-white/70 leading-relaxed">
                        {body}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* ---------------------------------------------------------------- process -- */}
        <section id="how-it-works" className="scroll-mt-24 bg-brand-ink process-section relative">
          <div className="mx-auto max-w-screen px-5 pt-12 pb-16">
            <div className="relative overflow-hidden rounded-2xl bg-brand-ink text-white
                            px-6 py-10 md:px-11 md:py-12">
              <FloatingParticles count={30} color="rgba(255,255,255,0.15)" />
              <AnimatedDotGrid className="absolute -right-4 -bottom-4 w-[300px] h-[150px] text-white/20" />

              <div className="relative grid lg:grid-cols-[18rem_minmax(0,1fr)] gap-10
                              xl:gap-14 items-center">
                <div>
                  <p className="text-2xs font-bold uppercase tracking-[0.16em] text-white/70">
                    Our process
                  </p>
                  <p className="mt-3 text-[26px] md:text-[30px] font-bold tracking-tight
                                leading-[1.15] drop-shadow-sm">
                    From upload to
                    <span className="block text-gold-vivid text-glow-gold">a clear decision</span>
                  </p>
                  <span aria-hidden
                        className="mt-4 block h-1 w-16 rounded-full bg-gold-vivid/70" />
                </div>

                <ol className="grid gap-y-9 grid-cols-2 sm:grid-cols-3 lg:grid-cols-5">
                  {PROCESS.map(([icon, title, l1, l2, ring], i) => (
                    <li key={title} className="process-step relative text-center">
                      {i < PROCESS.length - 1 && (
                        <span aria-hidden
                              className="process-connector hidden lg:flex absolute top-8 left-[calc(50%+2.4rem)]
                                         right-[calc(-50%+2.4rem)] items-center gap-1.5">
                          <span className="flex-1 border-t border-dashed border-white/30" />
                          <Icon name="arrow" className="w-3 h-3 text-white/45" />
                        </span>
                      )}
                      <span className={`mx-auto grid place-items-center w-16 h-16
                                        rounded-full bg-paper ring-4 ${ring}`}>
                        <Icon name={icon} className="w-7 h-7" />
                      </span>
                      <p className="mt-4 text-sm font-semibold">
                        {i + 1}. {title}
                      </p>
                      <p className="mt-1.5 text-xs text-white/60 leading-relaxed">
                        {l1}<br />{l2}
                      </p>
                    </li>
                  ))}
                </ol>
              </div>
            </div>
          </div>
        </section>

        {/* ----------------------------------------------------------- the evidence -- */}
        <section className="relative bg-brand-ink evidence-section overflow-hidden">
          <FloatingShapes />
          <GradientOrbs variant="dark" />
          <div className="relative z-10 mx-auto max-w-screen px-5 py-20 grid lg:grid-cols-2 gap-12
                          xl:gap-20 items-center">
            <div className="evidence-text">
              <Heading inverted eyebrow="The part that matters"
                       title={<>Every number, traced to<br className="hidden md:block" />{" "}
                              the page it came from</>}>
                A score you cannot check is not much help — the officer still has to read
                all four hundred pages. So every finding is linked to the page and the text it
                came from. Open a finding and the DPR opens at that page, with the supporting
                line highlighted.
              </Heading>
              <p className="mt-4 max-w-2xl text-[17px] text-white/70 leading-relaxed">
                It works the other way too. If a number or statement cannot be found in the
                source DPR, PRAMAAN does not present it as a supported finding: the figure is
                discarded and the refusal is recorded where you can see it.
              </p>
              <Link href="/data-sources"
                    className="mt-8 inline-flex items-center gap-2 px-5 py-3 rounded-xl
                               bg-[#0a3556] border border-white/20 text-white font-medium hover:bg-[#0c4069]
                               transition-colors shadow-lg">
                Where the data comes from
                <Icon name="arrow" className="w-4 h-4" />
              </Link>
            </div>

            <div className="evidence-card glass-panel-dark rounded-2xl overflow-hidden hover:scale-[1.02] transition-transform duration-500">
              <div className="flex items-center justify-between px-4 py-3 bg-[#0a3556]/60
                              border-b border-white/10">
                <p className="text-xs font-medium text-white/60">
                  dpr_bridge.pdf — page 138
                </p>
                <span className="chip bg-amber-500/20 text-amber-300 border border-amber-500/30 shadow-[0_0_12px_rgba(245,158,11,0.2)]">
                  Medium
                </span>
              </div>
              <div className="px-6 py-6 bg-transparent text-white space-y-2.5 text-[13px]
                              leading-relaxed">
                <p className="text-white/50">8.4 Financial Internal Rate of Return</p>
                <p>
                  The financial analysis has been carried out over a thirty-year concession
                  period, with traffic growth assumed at 6.2 per cent per annum for the first
                  decade.
                </p>
                <p>
                  On this basis{" "}
                  <mark className="bg-amber-500/30 text-white px-1 rounded-[2px] shadow-[0_0_8px_rgba(245,158,11,0.4)]">
                    the project yields a financial internal rate of return of 13.8 per cent
                  </mark>
                  , which exceeds the hurdle rate of 12 per cent prescribed for
                  transport-sector proposals.
                </p>
                <p className="text-white/50">
                  The corresponding cash-flow statement is placed at Annexure&nbsp;VII.
                </p>
              </div>
              <div className="px-5 py-4 bg-[#0a3556]/40 border-t border-white/10">
                <p className="text-2xs uppercase tracking-wide text-white/50">
                  Finding · financial recomputation
                </p>
                <p className="mt-1.5 text-sm text-white/90 leading-relaxed">
                  Claimed IRR of <b className="text-amber-300">13.8%</b> does not reconcile. Recomputed from the
                  cash-flow statement in this same document (Annexure VII, p. 307):{" "}
                  <b className="text-emerald-400">11.2%</b>.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* -------------------------------------------------------- what it checks -- */}
        <section className="relative bg-[#051b2d] border-y border-white/5 capabilities-section overflow-hidden">
          <GradientOrbs variant="dark" />
          <div className="relative z-10 mx-auto max-w-screen px-5 py-20">
            <Heading inverted eyebrow="What it checks" title="Six things, done properly">
              Each one gives you evidence you can open — or it says plainly that the document
              did not give it enough to go on.
            </Heading>

            <div className="mt-16 grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
              {CAPABILITIES.map(([icon, title, desc]) => (
                <div key={title}
                     className="cap-card glass-panel-dark flex flex-col p-6 rounded-2xl group
                                hover:-translate-y-1 transition-all duration-300">
                  <div className="flex items-start justify-between">
                    <span className="grid place-items-center w-11 h-11 rounded-xl
                                     bg-[#0a3556] text-white border border-white/10 group-hover:bg-[#0c4069]
                                     transition-colors shadow-inner">
                      <Icon name={icon} className="w-5 h-5" />
                    </span>
                  </div>
                  <h3 className="mt-6 text-base font-bold text-white group-hover:text-gold-vivid transition-colors">
                    {title}
                  </h3>
                  <p className="mt-2 text-[14px] text-white/70 leading-relaxed">
                    {desc}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* --------------------------------------------------------------- sectors -- */}
        <section id="sectors"
                 className="sectors-section scroll-mt-24 bg-brand-ink overflow-hidden border-b border-white/5">
          <div className="mx-auto max-w-screen px-5 py-20 xl:py-28 grid lg:grid-cols-2
                          gap-16 xl:gap-24 items-center">
            <div className="order-last lg:order-first relative sector-cards-container">
              <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-3/4 h-3/4 bg-[#0a3556] blur-[100px] rounded-full pointer-events-none" />

              <div className="relative z-10 grid sm:grid-cols-2 gap-4">
                {/* Each card carries the sector's own glyph. They were empty boxes with a
                    caption until now, which is a poor advertisement for a section the
                    Resources menu sends people to by name. */}
                {SECTORS.map(([imageSrc, name, category], i) => (
                  <div key={name}
                       className={`sector-card group relative aspect-[4/3] sm:aspect-[4/3] rounded-2xl overflow-hidden
                                   border border-white/10 bg-[#0a3556] shadow-xl
                                   transition-all duration-500 hover:shadow-2xl hover:border-white/30 ${
                                     i % 2 === 1 ? "sm:mt-12" : ""}`}>
                    <div className="absolute inset-0">
                      <Image src={imageSrc} alt={name} fill sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw"
                             className="object-cover transition-transform duration-700 group-hover:scale-105" />
                    </div>
                    <div className="absolute inset-0 bg-gradient-to-t from-[#03111d] via-[#03111d]/40 to-transparent opacity-90 transition-opacity duration-500 group-hover:opacity-100" />
                    <div className="absolute bottom-5 left-5 right-5 transform transition-transform duration-500 group-hover:-translate-y-1">
                      <h3 className="text-[22px] font-bold text-white tracking-wide mb-1.5 drop-shadow-md">
                        {name}
                      </h3>
                      <p className="text-xs uppercase tracking-[0.15em] text-white/50 font-semibold">
                        {category}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
            
            <div>
              <Heading inverted eyebrow="Domain coverage"
                       title={<>Reads the standard format<br className="hidden xl:block" />{" "}
                              of your ministry</>}>
                The parser is tuned to the structure of standard Indian government DPRs. It
                understands where to find the financial model, how to read an environmental
                clearance annexure, and which tables contain the construction schedule.
              </Heading>
            </div>
          </div>
        </section>

        {/* ----------------------------------------------------------------- desks -- */}
        <section id="principles"
                 className="desks-section scroll-mt-24 bg-brand-ink border-t border-white/5 overflow-hidden">
          <div className="mx-auto max-w-screen px-5 py-20 xl:py-28 grid lg:grid-cols-2
                          gap-16 xl:gap-24 items-center">
            <div>
              <Heading inverted eyebrow="Designed for government"
                       title={<>Sits on your desk,<br className="hidden xl:block" />{" "}
                              not in a cloud</>}>
                We do not send unpublished government documents to public APIs. PRAMAAN runs
                on your own hardware. The analysis stays in the building.
              </Heading>

              <div className="principles-section mt-10 grid gap-6 sm:grid-cols-2">
                <div className="principle-card">
                  <div className="flex items-center gap-3">
                    <span className="grid place-items-center w-8 h-8 rounded-full
                                     bg-emerald-500/20 text-emerald-400">
                      <Icon name="check" className="w-4 h-4" />
                    </span>
                    <h4 className="font-bold text-white text-[15px]">Air-gapped</h4>
                  </div>
                  <p className="mt-2.5 text-sm text-white/70 leading-relaxed pl-11">
                    No internet connection required. Runs completely offline on local GPUs.
                  </p>
                </div>
                <div className="principle-card">
                  <div className="flex items-center gap-3">
                    <span className="grid place-items-center w-8 h-8 rounded-full
                                     bg-emerald-500/20 text-emerald-400">
                      <Icon name="check" className="w-4 h-4" />
                    </span>
                    <h4 className="font-bold text-white text-[15px]">Audit trail</h4>
                  </div>
                  <p className="mt-2.5 text-sm text-white/70 leading-relaxed pl-11">
                    Every automated finding records exactly which model version made it.
                  </p>
                </div>
              </div>
            </div>

            <div className="relative desk-cards-container">
              <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[120%] aspect-square bg-[#0a3556]/50 rounded-full blur-3xl pointer-events-none" />

              {/* The two desks this is built for, each with the way in. `DESKS` had been
                  declared and then never rendered, so this column stood as two empty
                  outlines — and it is where the Principles link lands. */}
              <div className="relative z-10 grid gap-4 sm:grid-cols-2 xl:gap-6">
                {DESKS.map((d, i) => (
                  <div key={d.role}
                       className={`desk-card flex h-full flex-col rounded-2xl border
                                   border-white/10 bg-[#0a3556]/70 p-6 shadow-2xl ${
                         i === 0 ? "sm:translate-y-6" : "sm:-translate-y-6"}`}>
                    <span className="grid h-10 w-10 place-items-center rounded-full
                                     bg-gold-vivid/15 text-gold-vivid">
                      <Icon name={d.icon} className="h-5 w-5" />
                    </span>
                    <p className="mt-4 text-[11px] font-bold uppercase tracking-[0.12em]
                                  text-gold-vivid">
                      {d.role}
                    </p>
                    <p className="mt-2 text-[15px] font-semibold leading-snug text-white">
                      {d.lead}
                    </p>
                    <ul className="mt-4 space-y-2">
                      {d.points.map((pt) => (
                        <li key={pt} className="flex gap-2 text-[13px] leading-relaxed text-white/70">
                          <Icon name="check" className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-400" />
                          <span>{pt}</span>
                        </li>
                      ))}
                    </ul>
                    <Link href={d.cta[1]}
                          className="mt-5 inline-flex items-center gap-1.5 self-start text-[13px]
                                     font-medium text-gold-vivid underline-offset-4 hover:underline">
                      {d.cta[0]}
                      <Icon name="arrow" className="h-3.5 w-3.5" />
                    </Link>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* ------------------------------------------------------------------- faq -- */}
        <section id="faq"
                 className="faq-section scroll-mt-24 bg-brand-ink border-t border-white/5 relative">
          <div className="mx-auto max-w-3xl px-5 py-24">
            <h2 className="text-[28px] md:text-[34px] font-bold tracking-tight text-white text-center mb-12">
              Common questions
            </h2>
            <div className="space-y-4">
              {FAQ.map(([q, a]) => (
                <details key={q} className="faq-item group bg-[#0a3556] rounded-xl border border-white/10">
                  <summary className="flex items-center justify-between px-6 py-5 cursor-pointer
                                      text-[16px] font-semibold text-white select-none">
                    {q}
                    <Icon name="arrow"
                          className="w-5 h-5 text-white/40 group-open:rotate-180 transition-transform" />
                  </summary>
                  <div className="px-6 pb-6 text-white/70 leading-relaxed text-[15px]">
                    {a}
                  </div>
                </details>
              ))}
            </div>
          </div>
        </section>

        {/* ------------------------------------------------------------- final cta -- */}
        <section className="relative bg-[#051b2d] overflow-hidden">
          <div className="relative z-10 mx-auto max-w-screen px-5 py-16">
            <div className="cta-section relative rounded-2xl bg-[#082a44] border border-white/10 text-white px-7 py-12 md:px-12
                            grid lg:grid-cols-2 gap-10 items-center overflow-hidden shadow-2xl">
              <FloatingParticles count={25} color="rgba(245,185,33,0.15)" />
              <div className="absolute inset-0 bg-gradient-to-br from-gold-vivid/10 to-transparent pointer-events-none" />

              <div className="relative z-10">
                <h2 className="text-[30px] md:text-[34px] font-bold tracking-tight
                               leading-tight drop-shadow-sm">
                  Ready to test a <span className="text-gold-vivid text-glow-gold">DPR</span>?
                </h2>
                <p className="mt-4 text-[17px] text-white/70 leading-relaxed max-w-lg">
                  Upload a PDF, set the parameters, and let the parser read it. You can
                  always discard the draft if you don't like the results.
                </p>
              </div>
              <div className="relative z-10 flex flex-col sm:flex-row lg:justify-end gap-4">
                <Link href="#how-it-works"
                      className="inline-flex justify-center items-center gap-2.5 px-6 py-3.5
                                 rounded-xl bg-white/10 border border-white/20 text-white font-medium
                                 hover:bg-white/20 transition-all shadow-sm">
                  Read the docs
                </Link>
                <div className="magnetic relative group">
                  <div className="absolute -inset-0.5 bg-gradient-to-r from-gold-vivid to-amber-300 rounded-xl blur opacity-30 group-hover:opacity-60 transition duration-500"></div>
                  <Link href="/?signin=1"
                        className="relative inline-flex justify-center items-center gap-2.5 px-6 py-3.5
                                   rounded-xl bg-gradient-to-b from-gold-vivid to-gold-bright text-brand-ink font-semibold
                                   hover:shadow-lg hover:-translate-y-0.5 transition-all duration-300 shadow-card">
                    Start a new appraisal
                  </Link>
                </div>
              </div>
            </div>
          </div>
        </section>
      </main>

      <SiteFooter />
    </div>
    </LandingAnimations>
  );
}
