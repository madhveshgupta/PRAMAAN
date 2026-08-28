/** Chart colours, and why these ones.
 *
 *  Every value here was checked with the dataviz validator rather than chosen by eye
 *  (`node scripts/validate_palette.js "<hex,…>" --mode light`). Four results worth
 *  recording, because all four contradict what looks reasonable:
 *
 *  1. The `sev` chip scale FAILS as a chart palette — `sev.high` and `sev.medium` sit
 *     ΔE 0.7 apart under protanopia, i.e. identical. They are fine as chips, where a glyph
 *     and a word carry the meaning, and unusable as adjacent fills. Severity is therefore
 *     drawn as a SEQUENTIAL ramp, which is the honest form anyway: critical→info is an
 *     ordered scale, not five unrelated identities.
 *
 *  2. The first ramp was too tight at the dark end: `#0c3c60`↔`#12507e` measured ΔE 7.5 to
 *     NORMAL vision — critical and high were indistinguishable in the one chart whose whole
 *     job is telling them apart. Re-stepped below to widen the lightness interval. Five
 *     steps of one hue cannot all clear the categorical ΔE 15 floor and are not asked to:
 *     a sequential ramp is judged on lightness monotonicity, which this one holds, and every
 *     bar is direct-labelled with its word and its count.
 *
 *  3. Red/green for "raises risk / lowers risk" measured ΔE 6.1 under protanopia — the
 *     classic trap. Blue↔orange measures 21.6 and passes every check, so the tornado
 *     diverges on that axis instead.
 *
 *  4. The status fills failed outright as adjacent segments: "confirmed" green and "weak"
 *     olive measured ΔE 11.7 to normal vision and 5.5 under protanopia, so the two states an
 *     officer most needs to separate were the two that collided. Re-stepped below to
 *     ΔE 16.6 normal / 10.3 protan. The chip colours are deliberately NOT changed — a chip
 *     is text on a soft ground with a border, a word and a glyph, and it was never the
 *     failing case.
 */

/** Diverging, for signed values. Validated: ΔE 21.6 protan, 24.5 tritan, both ≥3:1. */
export const DIVERGING = { raises: "#b5651d", lowers: "#1f6fb2", midpoint: "#dbe2e8" };

/** Sequential, one hue light→dark. Severity is ordinal, so it gets a ramp.
 *  Lightness is monotonic: 0.32 → 0.45 → 0.60 → 0.74 → 0.86. */
export const SEVERITY_RAMP: Record<string, string> = {
  critical: "#0a3557",
  high:     "#14608f",
  medium:   "#4790c2",
  low:      "#86b4d4",
  info:     "#bcd6e8",
};

/** Status fills, for charts only. Validated as a categorical set in the order they are
 *  stacked: lightness band PASS, CVD separation PASS (worst adjacent ΔE 10.3 protan),
 *  normal-vision floor PASS (worst adjacent ΔE 16.6).
 *
 *  `insufficient_evidence` is a deliberate grey — it is the "we found nothing" slot, and a
 *  chromatic hue there would claim a finding that was never made. Grey fails the chroma
 *  floor by design and is drawn with a hatch so it is distinguishable in greyscale and in
 *  forced-colours mode. */
export const STATUS_FILL: Record<string, string> = {
  pass: "#1e8055",
  partial: "#b8890d",
  insufficient_evidence: "#9aa7b2",
  flagged: "#c0561f",
  not_run: "#3577ad",
};

/** The chip palette, unchanged, for the small number of places a chart legend must match a
 *  chip exactly. Never used as an adjacent fill — see note 1. */
export const CHIP_TONE: Record<string, string> = {
  critical: "#9d1c28", high: "#a75a0c", medium: "#7d6212", low: "#465360", info: "#12507e",
};

/** Confidence, drawn as one hue deepening. Confidence is a magnitude, not an identity. */
export const CONFIDENCE_RAMP = ["#dbe7f1", "#a8c6de", "#5b93bf", "#1f6fb2", "#0c3c60"];

export const AXIS = "#dbe2e8";
export const GRID = "#eef2f5";
export const INK = "#11181f";
export const INK_MUTED = "#6f7d89";
export const SURFACE = "#ffffff";

/** A 45° hatch for the "unknown / not measured" case. Never a fill that means a value —
 *  a hatched bar is the chart saying "we did not measure this", which an empty bar would
 *  misreport as zero. */
export const HATCH_ID = "pramaan-hatch";

export function hatchDefs(color = "#c3ced8") {
  return (
    <defs>
      <pattern id={HATCH_ID} width="6" height="6" patternUnits="userSpaceOnUse"
               patternTransform="rotate(45)">
        <rect width="6" height="6" fill="#f2f5f8" />
        <line x1="0" y1="0" x2="0" y2="6" stroke={color} strokeWidth="2.4" />
      </pattern>
    </defs>
  );
}

/** Round a fraction to a whole percent for display. Percentages in an appraisal note are
 *  read aloud in meetings; a decimal place implies a precision the model does not have. */
export function pct(v: number | null | undefined): string {
  return v == null ? "—" : `${Math.round(v * 100)}%`;
}
