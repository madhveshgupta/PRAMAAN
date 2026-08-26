import type { EvidenceAnchor } from "@/lib/api";

/** How every panel asks for the document.
 *
 *  One signature for findings, checklist rows and extracted values alike, because all three
 *  carry the same `evidence[]` and all three drive the same viewer. `key` identifies the
 *  row so the panel can show which of its own rows is currently open in the document —
 *  without it, opening evidence from the checklist would leave the checklist unable to say
 *  which line the reader is looking at.
 */
export type OpenEvidence = (
  evidence: EvidenceAnchor[],
  severity: string,
  index?: number,
  key?: string,
) => void;

export interface ViewProps {
  onOpen: OpenEvidence;
  /** The row currently driving the document pane, if it belongs to this panel. */
  activeKey?: string | null;
  activeIndex?: number;
  ministry: boolean;
}
