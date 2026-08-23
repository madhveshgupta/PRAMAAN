/**
 * The single door to the backend.
 *
 * Every call goes through here so the auth header, the 401 refresh dance and error shapes
 * live in one place rather than being re-implemented per screen.
 */
export const API = "/api/v1";

export type Role = "applicant" | "ministry";

export interface Session {
  access_token: string;
  refresh_token: string;
  role: Role;
  can_sanction: boolean;
  full_name: string;
}

export interface EvidenceAnchor {
  page: number;
  bbox: [number, number, number, number]; // normalised 0-1, top-left origin
  snippet: string;
  confidence: number;
  method: string;
  source?: string | null;
}

export interface Finding {
  id: string;
  severity: "critical" | "high" | "medium" | "low" | "info";
  category: string;
  status: "pass" | "partial" | "insufficient_evidence" | "flagged";
  rule_id: string;
  title: string;
  message: string;
  suggested_action: string | null;
  evidence: EvidenceAnchor[];
  anchor_count: number;
  match_confidence: number | null;
  match_status: "auto" | "confirmed" | "rejected";
  review: { decision: string; note: string | null; at: string } | null;
}

export interface CheckRow {
  check_id: string;
  label: string;
  severity: "critical" | "high" | "medium" | "low" | "info";
  /** `not_run` means we cannot run this check for any document; `insufficient_evidence`
   *  means we ran it and this document did not give it what it needed. */
  status: "pass" | "partial" | "insufficient_evidence" | "flagged" | "not_run";
  detail: string;
  evidence: EvidenceAnchor[];
  anchor_count: number;
  evidence_score: number | null;
  finding_ids: string[];
}

export interface CheckTally {
  pass: number; partial: number; insufficient_evidence: number;
  flagged: number; not_run: number; total: number;
}

export interface RubricProfile {
  key: string | null; label: string | null;
  confidence: number | null; provenance: string | null;
}

export interface Checklist {
  dpr_id: string;
  rubric_version: string | null;
  profile: RubricProfile;
  tally: CheckTally;
  families: { key: string; label: string; checks: CheckRow[] }[];
  /** An assessment predating the checklist has no rows; say so rather than showing zero. */
  stale: boolean;
  advisory_notice: string;
}

export interface ExtractedFieldRow {
  field_key: string;
  value: string | null;
  unit: string | null;
  status: string;
  confidence: number;
  method: string | null;
  evidence: EvidenceAnchor[];
  needs_verification: boolean;
}

/** A value the model stated and the system refused to store, because it could not be
 *  located inside its own cited evidence. Shown as a reliability feature, not an error log. */
export interface BlockedValue {
  field_key: string;
  claimed_value: string | null;
  reason: string;
}

export interface Extraction {
  fields: ExtractedFieldRow[];
  blocked_values: BlockedValue[];
  /** 0 means no model ran — not that nothing was blocked. */
  llm_fields?: number;
}

/** A report as the list endpoint returns it. Lives here rather than beside the table that
 *  first rendered it: three screens and two cards consume this shape, and only one of them
 *  is a table. */
export interface DprRow {
  id: string;
  title: string;
  status: string;
  is_self_check: boolean;
  created_at: string;
  overall_score?: number | null;
  finding_count?: number;
  critical_count?: number;
}

export interface AuditEvent {
  id: string;
  at: string;
  action: string;
  actor_role: string | null;
  actor_id: string | null;
  dpr_id: string | null;
  /** The report's title if it is still held, `null` if the event has outlived it. The
   *  trail keeps events forever; the reports they describe can be removed. */
  dpr_title: string | null;
  detail: Record<string, unknown> | null;
}

/** The decision on a report, as the submitting organisation sees it.
 *  Deliberately carries no score — that stays with the ministry. */
export interface DecisionPayload {
  dpr_id: string;
  status: string;
  decision: {
    outcome: string; reason: string; at: string;
    by: string | null; by_role: string;
  } | null;
}

export interface Component {
  key: string;
  label: string;
  score: number | null;
  unavailable_reason: string | null;
}

export interface Assessment {
  dpr_id: string;
  overall_score: number | null;
  components: Component[];
  rubric_version: string | null;
  engine_version: string | null;
  advisory_notice: string;
  profile?: RubricProfile;
  check_tally?: CheckTally;
}

const KEY = "pramaan.session";

export function getSession(): Session | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as Session) : null;
  } catch {
    return null; // private window, cleared storage, or a browser blocking site data
  }
}

export function setSession(s: Session | null) {
  try {
    if (s) window.localStorage.setItem(KEY, JSON.stringify(s));
    else window.localStorage.removeItem(KEY);
  } catch {
    /* storage unavailable — the session simply won't persist across reloads */
  }
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function raw(path: string, init: RequestInit = {}, token?: string) {
  const headers = new Headers(init.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init.body && !(init.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  return fetch(`${API}${path}`, { ...init, headers });
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const s = getSession();
  let res = await raw(path, init, s?.access_token);

  // One transparent refresh attempt before giving up — a token expiring mid-review
  // should not throw the user back to the login screen.
  if (res.status === 401 && s?.refresh_token) {
    const r = await raw("/auth/refresh", {
      method: "POST",
      body: JSON.stringify({ refresh_token: s.refresh_token }),
    });
    if (r.ok) {
      const next = (await r.json()) as Session;
      setSession(next);
      res = await raw(path, init, next.access_token);
    } else {
      setSession(null);
    }
  }

  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch { /* non-JSON error body */ }
    throw new ApiError(res.status, detail);
  }
  return res.status === 204 ? (undefined as T) : ((await res.json()) as T);
}

export async function login(email: string, password: string): Promise<Session> {
  const res = await raw("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw new ApiError(res.status, "Invalid credentials");
  const s = (await res.json()) as Session;
  setSession(s);
  return s;
}

export async function downloadFile(path: string, filename: string) {
  const s = getSession();
  let res = await raw(path, {}, s?.access_token);

  if (res.status === 401 && s?.refresh_token) {
    const r = await raw("/auth/refresh", {
      method: "POST",
      body: JSON.stringify({ refresh_token: s.refresh_token }),
    });
    if (r.ok) {
      const next = (await r.json()) as Session;
      setSession(next);
      res = await raw(path, {}, next.access_token);
    } else {
      setSession(null);
    }
  }

  if (!res.ok) {
    let detail = res.statusText;
    try { detail = (await res.json()).detail ?? detail; } catch { /* ignore */ }
    throw new ApiError(res.status, detail);
  }

  const blob = await res.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  window.URL.revokeObjectURL(url);
}

export function homeFor(role: Role): string {
  return role === "applicant" ? "/submissions" : "/queue";
}
