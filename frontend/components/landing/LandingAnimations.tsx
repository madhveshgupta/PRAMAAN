"use client";
/**
 * Landing page scroll animations.
 *
 * This component wraps the landing page and wires up GSAP ScrollTrigger for
 * every section. It runs entirely on the client and applies effects
 * progressively — with JS off, every section is simply visible.
 *
 * Two rules borrowed from `lib/motion.ts`, because they matter more here than anywhere:
 *
 *   1. Nothing is hidden in CSS waiting for JavaScript. Every hidden state is applied by
 *      GSAP, so a failed bundle leaves a readable page rather than a blank one.
 *   2. `prefers-reduced-motion` returns before a single `set()` runs, which leaves the page
 *      in its finished state instead of its starting one.
 *
 * The vocabulary is deliberately split in two. Entrances fire `once` and then let go — a
 * section that re-announces itself on every scroll-back is noise. Scroll-*linked* motion
 * (parallax, the progress rail, the headline sweep) is `scrub`bed instead, so it belongs to
 * the reader's own movement and never plays at them on a timer they did not start.
 */
import { useEffect, useRef } from "react";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { prefersReduced } from "@/lib/motion";

gsap.registerPlugin(ScrollTrigger);

export function LandingAnimations({ children }: { children: React.ReactNode }) {
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (prefersReduced()) return;
    const root = rootRef.current;
    if (!root) return;

    /* Pointer-driven flourishes are wired only for a real pointer. On touch there is no
       hover state to leave, so a tilted card stays tilted. */
    const finePointer = window.matchMedia("(pointer: fine)").matches;

    /* `gsap.context().revert()` undoes tweens and ScrollTriggers, but it knows nothing about
       listeners we attached by hand — those have to be collected and removed explicitly, or
       they outlive the component and keep every card node alive with them. */
    const cleanups: Array<() => void> = [];

    const ctx = gsap.context(() => {
      /* Every entrance shares one shape so the page reads as one system: rise, settle, stop.
         Only the distance and the stagger change with the weight of the thing arriving. */
      const enter = (
        targets: gsap.TweenTarget,
        trigger: Element,
        opts?: { y?: number; scale?: number; start?: string; stagger?: number;
                 duration?: number; ease?: string; delay?: number },
      ) => {
        const { y = 40, scale = 1, start = "top 82%", stagger = 0.09,
                duration = 0.7, ease = "power3.out", delay = 0 } = opts ?? {};
        gsap.set(targets, { opacity: 0, y, scale });
        ScrollTrigger.create({
          trigger, start, once: true,
          onEnter: () => gsap.to(targets, {
            opacity: 1, y: 0, scale: 1, duration, ease, stagger, delay,
          }),
        });
      };

      /* Parallax: the element drifts against the scroll instead of riding with it. `scrub`
         ties it to scroll position rather than to a clock, so it reverses cleanly when the
         reader scrolls back up. Distances stay small — this is depth, not a ride. */
      const parallax = (el: Element | null, distance: number) => {
        if (!el) return;
        gsap.fromTo(el, { y: distance }, {
          y: -distance, ease: "none",
          scrollTrigger: { trigger: el, start: "top bottom", end: "bottom top", scrub: 0.6 },
        });
      };

      // ── Scroll progress rail ──────────────────────────────────────────
      const rail = root.querySelector(".scroll-rail-fill");
      if (rail) {
        gsap.set(rail, { scaleX: 0, transformOrigin: "left center" });
        gsap.to(rail, {
          scaleX: 1, ease: "none",
          scrollTrigger: { start: 0, end: () => document.body.scrollHeight - window.innerHeight,
                           scrub: 0.25, invalidateOnRefresh: true },
        });
      }

      // ── Hero ──────────────────────────────────────────────────────────
      const heroContent = root.querySelector(".hero-animate");
      if (heroContent) {
        const heroChildren = heroContent.querySelectorAll(".hero-child");
        gsap.set(heroChildren, { opacity: 0, y: 40 });
        gsap.to(heroChildren, {
          opacity: 1, y: 0, duration: 0.8, ease: "power3.out", stagger: 0.12, delay: 0.2,
        });
      }

      const heroStats = root.querySelectorAll(".hero-stat");
      gsap.set(heroStats, { opacity: 0, y: 30, scale: 0.95 });
      gsap.to(heroStats, {
        opacity: 1, y: 0, scale: 1, duration: 0.6, ease: "back.out(1.4)",
        stagger: 0.15, delay: 0.8,
      });

      const trustItems = root.querySelectorAll(".trust-item");
      gsap.set(trustItems, { opacity: 0, x: -15 });
      gsap.to(trustItems, {
        opacity: 1, x: 0, duration: 0.5, ease: "power2.out", stagger: 0.1, delay: 1.3,
      });

      /* Leaving the hero: the panel lifts and dissolves a little ahead of the fold while the
         photograph behind it drifts the other way. Two speeds across one gesture is what
         reads as depth — and it hands the next section a stage rather than a hard cut.
         Capped well short of invisible, so a reader who stops mid-scroll is never looking at
         a half-erased headline — and capped short in distance too, because the panel lifting
         off its own baseline is white paper opening underneath it, which reads as a hole in
         the page rather than as depth once it passes about forty pixels. */
      const heroShell = root.querySelector(".hero-shell");
      if (heroShell && heroContent) {
        gsap.to(heroContent, {
          y: -36, opacity: 0.35, ease: "none",
          scrollTrigger: { trigger: heroShell, start: "top top", end: "bottom top", scrub: 0.5 },
        });
        const heroPhoto = heroShell.querySelector("img");
        if (heroPhoto) {
          gsap.to(heroPhoto, {
            y: 70, scale: 1.06, ease: "none",
            scrollTrigger: { trigger: heroShell, start: "top top", end: "bottom top", scrub: 0.5 },
          });
        }
      }

      // ── Pillars ───────────────────────────────────────────────────────
      const pillarsContainer = root.querySelector(".pillars-section");
      if (pillarsContainer) {
        enter(pillarsContainer.querySelectorAll(".pillar-card"), pillarsContainer,
              { y: 50, scale: 0.9, start: "top 80%", stagger: 0.08,
                duration: 0.65, ease: "back.out(1.2)" });
      }

      // ── Process ───────────────────────────────────────────────────────
      const processSection = root.querySelector(".process-section");
      if (processSection) {
        const processSteps = processSection.querySelectorAll(".process-step");
        enter(processSteps, processSection,
              { y: 40, scale: 0.85, start: "top 75%", stagger: 0.12,
                duration: 0.7, ease: "back.out(1.5)" });

        /* The connectors draw left-to-right after the steps have landed, so the row reads as
           a sequence being traced rather than five badges appearing at once. */
        const connectors = processSection.querySelectorAll(".process-connector");
        gsap.set(connectors, { scaleX: 0, transformOrigin: "left center" });
        ScrollTrigger.create({
          trigger: processSection, start: "top 70%", once: true,
          onEnter: () => gsap.to(connectors, {
            scaleX: 1, duration: 0.6, ease: "power2.out", stagger: 0.15, delay: 0.5,
          }),
        });
      }

      // ── Evidence ──────────────────────────────────────────────────────
      const evidenceSection = root.querySelector(".evidence-section");
      if (evidenceSection) {
        const evidenceText = evidenceSection.querySelector(".evidence-text");
        const evidenceCard = evidenceSection.querySelector(".evidence-card");

        if (evidenceText) {
          gsap.set(evidenceText, { opacity: 0, x: -60 });
          ScrollTrigger.create({
            trigger: evidenceSection, start: "top 75%", once: true,
            onEnter: () => gsap.to(evidenceText, {
              opacity: 1, x: 0, duration: 0.8, ease: "power3.out",
            }),
          });
        }

        if (evidenceCard) {
          gsap.set(evidenceCard, { opacity: 0, x: 60, rotationY: 5 });
          ScrollTrigger.create({
            trigger: evidenceSection, start: "top 70%", once: true,
            onEnter: () => gsap.to(evidenceCard, {
              opacity: 1, x: 0, rotationY: 0, duration: 0.9, ease: "power3.out", delay: 0.2,
            }),
          });
          /* Once it has arrived, the card keeps drifting a little slower than the column
             beside it. The claim and its proof stay visibly on two planes. */
          gsap.to(evidenceCard, {
            y: -40, ease: "none",
            scrollTrigger: { trigger: evidenceSection, start: "top 60%",
                             end: "bottom top", scrub: 0.7 },
          });
        }
      }

      // ── Capabilities ──────────────────────────────────────────────────
      /* Was querying `.capability-card`, which is not a class this page has ever rendered —
         the six tiles were the only grid on the page that never animated. The markup calls
         them `cap-card`, which is also what the tilt handler below already used. */
      const capsSection = root.querySelector(".capabilities-section");
      if (capsSection) {
        const cards = capsSection.querySelectorAll<HTMLElement>(".cap-card");
        cards.forEach((card, i) => {
          gsap.set(card, { opacity: 0, y: 60 });
          ScrollTrigger.create({
            trigger: card, start: "top 88%", once: true,
            /* Delay by column, not by index: on a three-up grid this makes each ROW sweep
               left to right, where a flat index stagger would trail diagonally. */
            onEnter: () => gsap.to(card, {
              opacity: 1, y: 0, duration: 0.65, ease: "power3.out", delay: (i % 3) * 0.1,
            }),
          });
        });
      }

      // ── Sectors ───────────────────────────────────────────────────────
      /* This section, `desks` and `principles` below were all querying wrappers that did not
         exist in the markup, so three of the page's last four sections arrived with no
         motion at all. The hooks are now on the sections; these run for the first time. */
      const sectorsSection = root.querySelector(".sectors-section");
      if (sectorsSection) {
        enter(sectorsSection.querySelectorAll(".sector-card"), sectorsSection,
              { y: 40, scale: 0.92, start: "top 80%", stagger: 0.1,
                duration: 0.6, ease: "back.out(1.3)" });
        parallax(sectorsSection.querySelector(".sector-cards-container"), 26);
      }

      // ── Desks ─────────────────────────────────────────────────────────
      const desksSection = root.querySelector(".desks-section");
      if (desksSection) {
        const deskCards = desksSection.querySelectorAll<HTMLElement>(".desk-card");
        deskCards.forEach((card, i) => {
          /* Animate the INNER panel, never `.desk-card` itself. The card carries its
             staggered offset as a Tailwind `translate-y-8` class, and a GSAP transform on
             the same element writes an inline `transform` that silently discards it —
             flattening the two columns the layout deliberately steps apart. */
          const inner = card.firstElementChild;
          if (!inner) return;
          gsap.set(inner, { opacity: 0, x: i === 0 ? -60 : 60 });
          ScrollTrigger.create({
            trigger: desksSection, start: "top 75%", once: true,
            onEnter: () => gsap.to(inner, {
              opacity: 1, x: 0, duration: 0.8, ease: "power3.out", delay: i * 0.15,
            }),
          });
        });
        parallax(desksSection.querySelector(".desk-cards-container"), 22);
      }

      // ── Principles ────────────────────────────────────────────────────
      const principlesSection = root.querySelector(".principles-section");
      if (principlesSection) {
        const prinCards = principlesSection.querySelectorAll(".principle-card");
        enter(prinCards, principlesSection,
              { y: 50, start: "top 85%", stagger: 0.15, duration: 0.7 });
      }

      // ── FAQ ───────────────────────────────────────────────────────────
      const faqSection = root.querySelector(".faq-section");
      if (faqSection) {
        faqSection.querySelectorAll(".faq-item").forEach((item) => {
          gsap.set(item, { opacity: 0, y: 30, x: -20 });
          ScrollTrigger.create({
            trigger: item, start: "top 88%", once: true,
            onEnter: () => gsap.to(item, {
              opacity: 1, y: 0, x: 0, duration: 0.55, ease: "power3.out",
            }),
          });
        });
      }

      // ── CTA ───────────────────────────────────────────────────────────
      const ctaSection = root.querySelector(".cta-section");
      if (ctaSection) {
        gsap.set(ctaSection, { opacity: 0, y: 50, scale: 0.96 });
        ScrollTrigger.create({
          trigger: ctaSection, start: "top 80%", once: true,
          onEnter: () => gsap.to(ctaSection, {
            opacity: 1, y: 0, scale: 1, duration: 0.8, ease: "power3.out",
          }),
        });
      }

      // ── Section headings ──────────────────────────────────────────────
      /* The heading rises and un-masks at the same time: `clipPath` sweeps the block open
         from its own baseline, so the words look uncovered rather than faded up. The mask is
         released to `none` on completion — a live clip-path on a text block keeps it on its
         own layer and clips any focus ring a keyboard user lands inside it. */
      root.querySelectorAll(".section-heading").forEach((heading) => {
        gsap.set(heading, { opacity: 0, y: 35, clipPath: "inset(0% 0% 100% 0%)" });
        ScrollTrigger.create({
          trigger: heading, start: "top 85%", once: true,
          onEnter: () => gsap.to(heading, {
            opacity: 1, y: 0, clipPath: "inset(0% 0% 0% 0%)",
            duration: 0.85, ease: "power3.out",
            onComplete: () => gsap.set(heading, { clearProps: "clipPath" }),
          }),
        });
      });

      /* No `.parallax-slow` hook on the blurred blobs, tempting as they are: both centre
         themselves with Tailwind's `-translate-x-1/2 -translate-y-1/2`, and a GSAP `y` on the
         same node rewrites `transform` wholesale and drops them a quarter-width off centre.
         The two image containers above carry no transform class, which is why the depth is
         hung on them instead. */

      if (!finePointer) return;

      // ── 3D tilt on hover ──────────────────────────────────────────────
      const tiltCards = root.querySelectorAll<HTMLElement>(
        ".cap-card, .pillar-card, .evidence-card, .sector-card");
      tiltCards.forEach((card) => {
        gsap.set(card, { transformPerspective: 1000 });

        const onMove = (e: MouseEvent) => {
          const rect = card.getBoundingClientRect();
          const rotateX = ((e.clientY - rect.top - rect.height / 2) / (rect.height / 2)) * -5;
          const rotateY = ((e.clientX - rect.left - rect.width / 2) / (rect.width / 2)) * 5;
          gsap.to(card, { rotationX: rotateX, rotationY: rotateY,
                          duration: 0.4, ease: "power2.out" });
        };
        const onLeave = () => gsap.to(card, {
          rotationX: 0, rotationY: 0, duration: 0.7, ease: "elastic.out(1, 0.5)" });

        card.addEventListener("mousemove", onMove);
        card.addEventListener("mouseleave", onLeave);
        cleanups.push(() => {
          card.removeEventListener("mousemove", onMove);
          card.removeEventListener("mouseleave", onLeave);
        });
      });

      // ── Magnetic call-to-action ───────────────────────────────────────
      /* The primary buttons lean toward the cursor as it approaches. The pull is capped at a
         few pixels and the element never leaves its hit box, so the button that gets clicked
         is always the button that was aimed at. */
      root.querySelectorAll<HTMLElement>(".magnetic").forEach((el) => {
        const onMove = (e: MouseEvent) => {
          const rect = el.getBoundingClientRect();
          gsap.to(el, {
            x: ((e.clientX - rect.left) / rect.width - 0.5) * 12,
            y: ((e.clientY - rect.top) / rect.height - 0.5) * 8,
            duration: 0.4, ease: "power2.out",
          });
        };
        const onLeave = () => gsap.to(el, {
          x: 0, y: 0, duration: 0.6, ease: "elastic.out(1, 0.4)" });

        el.addEventListener("mousemove", onMove);
        el.addEventListener("mouseleave", onLeave);
        cleanups.push(() => {
          el.removeEventListener("mousemove", onMove);
          el.removeEventListener("mouseleave", onLeave);
        });
      });
    }, root);

    return () => {
      cleanups.forEach((fn) => fn());
      ctx.revert();
    };
  }, []);

  return (
    <div ref={rootRef}>
      {/* The progress rail ships collapsed and is opened only by the scrub below. Gating it
          on state instead would render it a paint too late for the effect's `querySelector`,
          leaving an un-animated full-width gold bar pinned across the top of the page — and
          the same inline `scaleX(0)` is what correctly hides it under reduced motion and with
          no JavaScript at all, where a scroll indicator that cannot track scroll has nothing
          to say. */}
      <div aria-hidden
           className="no-print fixed top-0 left-0 right-0 z-50 h-[3px] pointer-events-none">
        <div className="scroll-rail-fill h-full w-full bg-gradient-to-r
                        from-gold-vivid via-amber-300 to-gold-vivid
                        shadow-[0_0_10px_rgba(245,185,33,0.6)]"
             style={{ transform: "scaleX(0)", transformOrigin: "left center" }} />
      </div>
      {children}
    </div>
  );
}
