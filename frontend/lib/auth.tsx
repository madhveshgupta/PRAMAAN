"use client";
/**
 * Client-side session state. The server enforces access; this only decides what to draw.
 *
 * Sign-in goes through this context rather than calling the API module directly. Writing
 * the session to localStorage is not enough: the provider mounts once in the root layout
 * and does not re-read on client navigation, so a page that redirected immediately after
 * login would see a null session and bounce straight back to /login — a redirect loop.
 */
import { useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useState } from "react";

import { getSession, homeFor, login as apiLogin, setSession, type Session } from "./api";

interface AuthValue {
  session: Session | null;
  ready: boolean;
  signIn: (email: string, password: string) => Promise<Session>;
  signOut: () => void;
}

const Ctx = createContext<AuthValue>({
  session: null,
  ready: false,
  signIn: async () => {
    throw new Error("AuthProvider missing");
  },
  signOut: () => {},
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [session, setS] = useState<Session | null>(null);
  const [ready, setReady] = useState(false);
  const router = useRouter();

  useEffect(() => {
    setS(getSession());
    setReady(true);
  }, []);

  const signIn = useCallback(async (email: string, password: string) => {
    const s = await apiLogin(email, password);
    setS(s);                       // keep context and storage in step
    return s;
  }, []);

  const signOut = useCallback(() => {
    setSession(null);
    setS(null);
    router.push("/?signin=1");
  }, [router]);

  return (
    <Ctx.Provider value={{ session, ready, signIn, signOut }}>{children}</Ctx.Provider>
  );
}

export const useAuth = () => useContext(Ctx);

/** Send the user where they belong. Renders nothing until `ready` so there is no flash of
 *  the wrong portal while localStorage is read. */
export function useRequireAuth(allow?: Session["role"][]) {
  const { session, ready } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!ready) return;
    if (!session) router.replace("/?signin=1");
    else if (allow && !allow.includes(session.role)) router.replace(homeFor(session.role));
  }, [ready, session, allow, router]);

  return { session, ready };
}
