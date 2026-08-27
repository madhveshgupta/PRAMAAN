"use client";
/**
 * Decorative animated backgrounds for the landing page.
 * All purely visual — pointer-events: none, aria-hidden, z-0.
 */
import React, { useEffect, useRef } from "react";
import { gsap } from "gsap";
import { prefersReduced } from "@/lib/motion";

/* ── Floating Particles ──────────────────────────────────────────────────
   A field of small dots that drift slowly, giving depth to dark sections. */
export function FloatingParticles({
  count = 40,
  color = "rgba(59,130,246,0.25)",
  className = "",
}: {
  count?: number;
  color?: string;
  className?: string;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    if (prefersReduced()) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animId: number;
    const dpr = window.devicePixelRatio || 1;

    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      canvas.width = rect.width * dpr;
      canvas.height = rect.height * dpr;
      ctx.scale(dpr, dpr);
    };
    resize();
    window.addEventListener("resize", resize);

    type Particle = { x: number; y: number; r: number; vx: number; vy: number; opacity: number };
    const particles: Particle[] = [];
    const rect = canvas.getBoundingClientRect();

    for (let i = 0; i < count; i++) {
      particles.push({
        x: Math.random() * rect.width,
        y: Math.random() * rect.height,
        r: Math.random() * 2 + 0.5,
        vx: (Math.random() - 0.5) * 0.3,
        vy: (Math.random() - 0.5) * 0.2 - 0.1,
        opacity: Math.random() * 0.6 + 0.2,
      });
    }

    const draw = () => {
      const r = canvas.getBoundingClientRect();
      ctx.clearRect(0, 0, r.width, r.height);

      for (const p of particles) {
        p.x += p.vx;
        p.y += p.vy;
        if (p.x < -10) p.x = r.width + 10;
        if (p.x > r.width + 10) p.x = -10;
        if (p.y < -10) p.y = r.height + 10;
        if (p.y > r.height + 10) p.y = -10;

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = color.replace(/[\d.]+\)$/, `${p.opacity})`);
        ctx.fill();
      }

      animId = requestAnimationFrame(draw);
    };
    draw();

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener("resize", resize);
    };
  }, [count, color]);

  return (
    <canvas
      ref={canvasRef}
      aria-hidden
      className={`absolute inset-0 w-full h-full pointer-events-none z-0 ${className}`}
    />
  );
}

/* ── Animated Gradient Orbs ──────────────────────────────────────────────
   Soft blurred circles that slowly drift around, creating a living gradient mesh. */
export function GradientOrbs({ variant = "light" }: { variant?: "light" | "dark" }) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (prefersReduced()) return;
    const el = containerRef.current;
    if (!el) return;
    const orbs = el.querySelectorAll<HTMLDivElement>(".gradient-orb");

    const ctx = gsap.context(() => {
      orbs.forEach((orb, i) => {
        gsap.to(orb, {
          x: `random(-80, 80)`,
          y: `random(-60, 60)`,
          duration: `random(12, 20)`,
          ease: "sine.inOut",
          repeat: -1,
          yoyo: true,
          delay: i * 2,
        });
        // Gentle pulse
        gsap.to(orb, {
          scale: `random(0.85, 1.15)`,
          opacity: `random(0.15, 0.4)`,
          duration: `random(6, 10)`,
          ease: "sine.inOut",
          repeat: -1,
          yoyo: true,
          delay: i * 1.5,
        });
      });
    }, el);

    return () => ctx.revert();
  }, []);

  const isLight = variant === "light";

  return (
    <div ref={containerRef} aria-hidden className="absolute inset-0 overflow-hidden pointer-events-none z-0">
      <div className={`gradient-orb absolute w-[500px] h-[500px] rounded-full blur-[120px] ${
        isLight ? "bg-blue-400/10 top-[-10%] left-[-8%]" : "bg-blue-500/20 top-[-10%] left-[-8%]"
      }`} />
      <div className={`gradient-orb absolute w-[400px] h-[400px] rounded-full blur-[100px] ${
        isLight ? "bg-amber-300/8 top-[30%] right-[-5%]" : "bg-cyan-400/15 top-[30%] right-[-5%]"
      }`} />
      <div className={`gradient-orb absolute w-[350px] h-[350px] rounded-full blur-[90px] ${
        isLight ? "bg-emerald-300/8 bottom-[-5%] left-[20%]" : "bg-indigo-500/15 bottom-[-5%] left-[20%]"
      }`} />
    </div>
  );
}

/* ── Animated Dot Grid ───────────────────────────────────────────────────
   A field of dots with a subtle wave animation — like a data matrix coming alive. */
export function AnimatedDotGrid({ className = "" }: { className?: string }) {
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    if (prefersReduced()) return;
    const svg = svgRef.current;
    if (!svg) return;
    const dots = svg.querySelectorAll("circle");

    const ctx = gsap.context(() => {
      dots.forEach((dot, i) => {
        const row = Math.floor(i / 20);
        const col = i % 20;
        const delay = (row + col) * 0.08;

        gsap.to(dot, {
          opacity: 0.6,
          r: 1.8,
          duration: 1.5,
          ease: "sine.inOut",
          repeat: -1,
          yoyo: true,
          delay,
        });
      });
    }, svg);

    return () => ctx.revert();
  }, []);

  // Generate 20x10 grid of dots
  const dots: React.JSX.Element[] = [];
  for (let row = 0; row < 10; row++) {
    for (let col = 0; col < 20; col++) {
      dots.push(
        <circle
          key={`${row}-${col}`}
          cx={col * 18 + 9}
          cy={row * 18 + 9}
          r={1.2}
          fill="currentColor"
          opacity={0.2}
        />
      );
    }
  }

  return (
    <svg
      ref={svgRef}
      aria-hidden
      viewBox="0 0 360 180"
      className={`pointer-events-none ${className}`}
    >
      {dots}
    </svg>
  );
}

/* ── Wave Divider ────────────────────────────────────────────────────────
   A smooth SVG wave separating two sections. */
export function WaveDivider({
  flip = false,
  color = "#f7f5f1",
  className = "",
}: {
  flip?: boolean;
  color?: string;
  className?: string;
}) {
  return (
    <div
      aria-hidden
      className={`w-full overflow-hidden leading-[0] pointer-events-none ${
        flip ? "rotate-180" : ""
      } ${className}`}
    >
      <svg
        viewBox="0 0 1440 80"
        preserveAspectRatio="none"
        className="w-full h-[40px] md:h-[60px]"
      >
        <path
          d="M0,40 C360,80 720,0 1080,40 C1260,60 1380,20 1440,40 L1440,80 L0,80 Z"
          fill={color}
        />
      </svg>
    </div>
  );
}

/* ── Geometric Float ─────────────────────────────────────────────────────
   Slowly rotating geometric shapes for visual interest. */
export function FloatingShapes() {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (prefersReduced()) return;
    const el = containerRef.current;
    if (!el) return;
    const shapes = el.querySelectorAll<HTMLDivElement>(".float-shape");

    const ctx = gsap.context(() => {
      shapes.forEach((shape, i) => {
        gsap.to(shape, {
          rotation: 360,
          duration: 30 + i * 10,
          ease: "none",
          repeat: -1,
        });
        gsap.to(shape, {
          y: `random(-30, 30)`,
          x: `random(-20, 20)`,
          duration: `random(8, 15)`,
          ease: "sine.inOut",
          repeat: -1,
          yoyo: true,
          delay: i * 2,
        });
      });
    }, el);

    return () => ctx.revert();
  }, []);

  return (
    <div ref={containerRef} aria-hidden className="absolute inset-0 overflow-hidden pointer-events-none z-0">
      {/* Hollow ring */}
      <div className="float-shape absolute top-[15%] right-[12%] w-20 h-20 rounded-full border-2 border-brand/10 opacity-40" />
      {/* Small square */}
      <div className="float-shape absolute bottom-[25%] left-[8%] w-10 h-10 rounded-lg border border-gold-vivid/15 opacity-30 rotate-45" />
      {/* Diamond */}
      <div className="float-shape absolute top-[55%] right-[25%] w-6 h-6 rounded-sm bg-brand/5 opacity-40 rotate-45" />
      {/* Larger ring */}
      <div className="float-shape absolute bottom-[10%] right-[40%] w-32 h-32 rounded-full border border-emerald-400/8 opacity-30" />
      {/* Tiny dot cluster */}
      <div className="float-shape absolute top-[35%] left-[30%] w-3 h-3 rounded-full bg-gold-vivid/15" />
    </div>
  );
}
