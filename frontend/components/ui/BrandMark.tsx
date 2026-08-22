/** The one mark, in one file.
 *
 *  There were three, and which one you saw depended on where you happened to be: the
 *  supplied `pramaan-logo.png` lockup on the front door, the State Emblem at the head of the
 *  navigation rail, and a drawn cable-stayed bridge in the topbar — which is the one an
 *  applicant met first, because the rail is collapsed by default and the topbar mark stands
 *  in for it. Signing in therefore *changed the product's logo*, which reads as having
 *  landed somewhere else entirely.
 *
 *  So: the emblem, and nothing else. It is the element common to all three, it is the only
 *  one of them that is a mark rather than a lockup, and it carries no "Government of India"
 *  wording — which an unaffiliated prototype should not be printing above a footer that
 *  carefully disclaims exactly that authority.
 *
 *  Two tones, because the mark sits on two grounds and the artwork is black line art:
 *  `light` tints it gold for the navy chrome, `dark` leaves it as drawn for paper.
 */

/** Black line art → the gold of the identity strip. A filter rather than a second export:
 *  one asset that cannot drift beats two that can. */
const GOLD =
  "brightness(0) invert(1) sepia(1) saturate(3) hue-rotate(15deg) brightness(1.1)";

type Tone = "light" | "dark";
type Size = "sm" | "md" | "lg";

const EMBLEM: Record<Size, string> = {
  sm: "h-9 w-7",
  md: "h-11 w-9",
  lg: "h-12 w-10",
};

const WORD: Record<Size, string> = {
  sm: "text-[17px] tracking-[0.04em]",
  md: "text-[20px] tracking-[0.06em]",
  lg: "text-[22px] tracking-[0.06em]",
};

/** The State Emblem on its own — for the places that want the mark without the wordmark. */
export function Emblem({ tone = "light", className = "" }: {
  tone?: Tone; className?: string;
}) {
  return (
    // eslint-disable-next-line @next/next/no-img-element -- an SVG needs no optimisation,
    // and `next/image` would defeat the CSS tint the two tones depend on.
    <img src="/emblem.svg" alt="" aria-hidden
         className={`object-contain ${className}`}
         style={tone === "light" ? { filter: GOLD } : undefined} />
  );
}

/**
 * Emblem + wordmark. Used by the public header, the navigation rail, the topbar and the
 * sign-in card, so those four cannot disagree about what this product's logo is.
 *
 * `tagline` is off at `sm` on purpose: at topbar height the strapline sets below 9px, which
 * is decoration nobody can read rather than information.
 */
export function BrandMark({ tone = "light", size = "md", tagline = true, className = "" }: {
  tone?: Tone; size?: Size; tagline?: boolean; className?: string;
}) {
  const light = tone === "light";
  return (
    <span className={`flex items-center gap-3 leading-none ${className}`}>
      <span className="relative shrink-0">
        <Emblem tone={tone} className={EMBLEM[size]} />
        {light && (
          // A breath of warmth behind the line art, so the emblem does not read as a hole
          // punched in the navy bar.
          <span aria-hidden className="absolute inset-0 -z-10 scale-150 rounded-full
                                       bg-amber-300 opacity-20 blur-lg" />
        )}
      </span>
      <span className="flex flex-col gap-1">
        <span className={`font-bold ${WORD[size]} ${light ? "text-white" : "text-brand-deep"}`}>
          PRAMAAN
        </span>
        {tagline && size !== "sm" && (
          <span className={`text-[9px] font-medium uppercase leading-none tracking-[0.15em] ${
            light ? "text-amber-200/60" : "text-ink-faint"}`}>
            Smart DPR Appraisal
          </span>
        )}
      </span>
    </span>
  );
}
