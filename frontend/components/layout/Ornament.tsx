/** Decoration, drawn rather than imported.
 *
 *  Two reasons it is inline SVG and not an image file. The obvious one is that §7 of the
 *  brief forbids external assets and a government intranet is exactly where a CDN image
 *  fails silently. The better one is that every mark here inherits `currentColor`, so one
 *  drawing works on the navy rail, on white paper and in a greyscale print of the page —
 *  three exports of the same PNG would drift within a fortnight.
 */

/** The jaali watermark. A radial screen, the ornament on the stone screens of the buildings
 *  these reports are written in. It sits behind a page title at very low opacity, where it
 *  gives a large empty header a centre without adding anything that has to be read. */
export function Jaali({ className = "", petals = 16 }: {
  className?: string; petals?: number;
}) {
  const ring = (r: number, n: number, len: number, w: number) =>
    Array.from({ length: n }).map((_, i) => {
      const a = (i / n) * Math.PI * 2;
      return (
        <line key={`${r}-${i}`}
              x1={100 + Math.cos(a) * r} y1={100 + Math.sin(a) * r}
              x2={100 + Math.cos(a) * (r + len)} y2={100 + Math.sin(a) * (r + len)}
              strokeWidth={w} strokeLinecap="round" />
      );
    });

  return (
    <svg viewBox="0 0 200 200" aria-hidden className={className}
         fill="none" stroke="currentColor">
      <circle cx="100" cy="100" r="26" strokeWidth="1.2" />
      <circle cx="100" cy="100" r="44" strokeWidth="0.9" />
      <circle cx="100" cy="100" r="70" strokeWidth="0.9" />
      <circle cx="100" cy="100" r="92" strokeWidth="1.2" />
      {ring(26, petals / 2, 18, 1)}
      {ring(44, petals, 26, 0.9)}
      {ring(70, petals * 1.5, 22, 0.7)}
      {Array.from({ length: petals }).map((_, i) => {
        const a = (i / petals) * Math.PI * 2;
        const a2 = ((i + 0.5) / petals) * Math.PI * 2;
        return (
          <path key={i} strokeWidth="0.85"
                d={`M${100 + Math.cos(a) * 44} ${100 + Math.sin(a) * 44}
                    Q${100 + Math.cos(a2) * 82} ${100 + Math.sin(a2) * 82}
                     ${100 + Math.cos((i + 1) / petals * Math.PI * 2) * 44}
                     ${100 + Math.sin((i + 1) / petals * Math.PI * 2) * 44}`} />
        );
      })}
    </svg>
  );
}

/** The secretariat silhouette that anchors the foot of the navigation rail — the same
 *  gesture as the reference, drawn as one flat shape so it stays quiet. */
export function Secretariat({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 240 96" aria-hidden className={className} fill="currentColor">
      <path opacity=".5" d="M0 96V78c14-2 22-8 34-8s18 6 32 6 20-7 34-7 22 8 36 8 24-9 40-9 34 6 44 8v20z" />
      <g opacity=".85">
        <path d="M112 34a8 8 0 0 1 16 0v4h-16z" />
        <path d="M118 18h4v14h-4z" />
        <path d="M104 44h32c4 12 8 20 8 30h-48c0-10 4-18 8-30z" />
        <rect x="96" y="74" width="48" height="22" />
        <rect x="72" y="60" width="20" height="36" />
        <rect x="148" y="60" width="20" height="36" />
        <rect x="52" y="72" width="16" height="24" />
        <rect x="172" y="72" width="16" height="24" />
        <rect x="34" y="80" width="14" height="16" opacity=".7" />
        <rect x="192" y="80" width="14" height="16" opacity=".7" />
      </g>
      <g opacity=".35">
        {[58, 76, 80, 84, 88, 154, 158, 162, 166, 184].map((x) => (
          <rect key={x} x={x} y="66" width="3" height="8" fill="#fff" />
        ))}
      </g>
      {/* The flag, the one place the mark is allowed a second colour. */}
      <path d="M120 8h1v12h-1z" />
      <path d="M121 8h14v7h-14z" opacity=".7" />
    </svg>
  );
}

/* --------------------------------------------------------------- project thumbnails -- */

export type Sector = "roads" | "irrigation" | "water" | "waste" | "health" | "transit"
                   | "power" | "generic";

/** Guess the sector from the report's own title.
 *
 *  A guess, and labelled as decoration only: the thumbnail is never the source of any
 *  claim, so a wrong guess costs a slightly odd picture and nothing else. Nothing in the
 *  appraisal reads this. */
export function sectorOf(title: string): Sector {
  const t = title.toLowerCase();
  if (/road|highway|bridge|connectivity|pmgsy/.test(t)) return "roads";
  if (/irrigat|canal|dam|command area|minor lift/.test(t)) return "irrigation";
  if (/water supply|drinking|jal|pipe|phed|tube ?well/.test(t)) return "water";
  if (/waste|sanitat|sewer|swm|landfill|drainage/.test(t)) return "waste";
  if (/health|hospital|phc|chc|medical|wellness/.test(t)) return "health";
  if (/metro|transit|bus|rail|terminal|transport/.test(t)) return "transit";
  if (/power|solar|grid|substation|transmission|electri/.test(t)) return "power";
  return "generic";
}

export const SECTOR_LABEL: Record<Sector, string> = {
  roads: "Rural roads & bridges", irrigation: "Irrigation", water: "Water supply",
  waste: "Solid waste & sanitation", health: "Health infrastructure",
  transit: "Urban transport", power: "Power & transmission", generic: "Infrastructure",
};

/**
 * A flat illustrated thumbnail per sector.
 *
 * These are the one purely ornamental element in the working screens, and they are here
 * because a queue of twelve near-identical government project titles is genuinely hard to
 * scan — "Rural Road Connectivity Improvement Project, Phase II" and "Rural Road
 * Connectivity Improvement Project, Phase III" differ by one character in the middle of a
 * long line. A picture gives the eye a second, faster handle on the row. It never carries
 * information the text does not.
 */
export function SectorArt({ sector, className = "" }: { sector: Sector; className?: string }) {
  const ext = ["health", "transit", "power", "generic"].includes(sector) ? "jpg" : "png";
  
  return (
    <div className={`overflow-hidden rounded-xl border border-paper-edge shadow-sm bg-white ${className}`}>
      <img src={`/icons/${sector}.${ext}`} 
           alt={`${sector} sector icon`} 
           className="w-full h-full object-cover" 
           aria-hidden="true" />
    </div>
  );
}
