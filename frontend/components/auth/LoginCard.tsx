"use client";
/** The sign-in form, extracted so every way into the product shows the same thing.
 *
 *  There is no `/login` route any more: `useRequireAuth` and `signOut` both send you to
 *  `/?signin=1`, which the header reads off the URL and opens this in a dialog over the
 *  landing page. One form, one appearance, however you arrived at it.
 */
import { useRouter } from "next/navigation";
import { useState } from "react";

import { BrandMark } from "@/components/ui/BrandMark";
import { homeFor } from "@/lib/api";
import { useAuth } from "@/lib/auth";

const DEMO = [
  ["ministry@demo.gov.in", "Ministry", "reviews, ranks and sanctions"],
  ["applicant@demo.gov.in", "Applicant", "submits and self-checks"],
];

export function LoginCard({ demo = false, autoFocus = false }: {
  demo?: boolean; autoFocus?: boolean;
}) {
  const router = useRouter();
  const { signIn } = useAuth();

  const [email, setEmail] = useState(demo ? "ministry@demo.gov.in" : "");
  const [password, setPassword] = useState(demo ? "pramaan" : "");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const s = await signIn(email, password);
      router.replace(homeFor(s.role));
    } catch {
      setError("Those credentials were not accepted.");
      setBusy(false);
    }
  }

  return (
    <div className="w-full max-w-[26rem] card shadow-pop overflow-hidden">
      <div className="rule-gold" />
      <form onSubmit={submit} className="px-7 pt-7 pb-6">
        <div className="animate-sweep-in flex flex-col items-center">
          <BrandMark tone="dark" size="md" />
          <span className="mt-2 text-2xs text-ink-faint">
            प्रमाण — <i className="text-gold-deep not-italic font-medium">evidence</i>
          </span>
        </div>

        <h1 className="mt-6 display text-xl font-bold text-center">Sign in</h1>
        <p className="mt-1 text-xs text-ink-faint text-center">
          Use your official credentials.
        </p>
        <div className="mx-auto mt-4 h-px w-12 bg-gold/50" />

        <label className="block mt-6 text-sm font-medium">
          Email address
          <input type="email" required autoComplete="username" value={email}
                 autoFocus={autoFocus} placeholder="Enter your email"
                 onChange={(e) => setEmail(e.target.value)}
                 className="field mt-1.5 font-normal" />
        </label>

        <label className="block mt-4 text-sm font-medium">
          Password
          <input type="password" required autoComplete="current-password"
                 value={password} placeholder="Enter your password"
                 onChange={(e) => setPassword(e.target.value)}
                 className="field mt-1.5 font-normal" />
        </label>

        {error && (
          <p role="alert"
             className="mt-4 text-sm text-sev-critical bg-sev-critical-soft animate-sweep-in
                        border border-sev-critical/20 rounded-[--radius] px-3 py-2">
            {error}
          </p>
        )}

        <button disabled={busy} className="btn-primary w-full mt-6 py-2.5 uppercase
                                           tracking-wide font-semibold
                                           transition-transform active:scale-[.99]">
          {busy ? "Signing in…" : "Sign in"}
        </button>
      </form>

      <div className="border-t border-paper-edge bg-paper-soft px-7 py-5">
        <p className="text-xs font-semibold text-ink text-center">Demonstration accounts</p>
        <p className="text-2xs text-ink-faint mt-0.5 text-center">
          Password for both: <code className="font-mono">pramaan</code>
        </p>
        <ul className="mt-3 space-y-2">
          {DEMO.map(([mail, role, note]) => (
            <li key={mail}>
              <button type="button"
                      onClick={() => { setEmail(mail); setPassword("pramaan"); }}
                      className="text-xs text-brand hover:underline font-medium">
                {mail}
              </button>
              <p className="text-2xs text-ink-faint">{role} — {note}</p>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
