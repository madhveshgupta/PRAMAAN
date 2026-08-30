"use client";
/** The backdrop every sign-in appears on.
 *
 *  There used to be two: a polished dialog over the landing page, and a plain `/login`
 *  route you were dropped onto by signing out or by a session expiring. Same act, two
 *  different-looking portals, and the one you met by accident was the worse one. This is
 *  what both now render, so how you arrived stops being visible.
 */
export function LoginStage({ children, onDismiss }: {
  children: React.ReactNode;
  /** Supplied only by the dialog — the standalone page has nothing to dismiss to. */
  onDismiss?: () => void;
}) {
  return (
    <>
      <div onClick={onDismiss}
           className="absolute inset-0 bg-brand-ink/70 backdrop-blur-md animate-fade-in" />
      {/* The same cable geometry as the hero, quietened right down — the page behind is
          blurred away, and this keeps the sign-in from sitting on a flat rectangle. */}
      <svg aria-hidden viewBox="0 0 400 260" preserveAspectRatio="xMidYMid slice"
           className="absolute inset-0 h-full w-full text-gold opacity-[0.13] animate-fade-in">
        <g stroke="currentColor" fill="none">
          {Array.from({ length: 11 }, (_, i) => (
            <g key={i}>
              <line x1={200} y1={30 + i * 5} x2={200 - (i + 1) * 24} y2={200} strokeWidth={0.8} />
              <line x1={200} y1={30 + i * 5} x2={200 + (i + 1) * 24} y2={200} strokeWidth={0.8} />
            </g>
          ))}
          <line x1={200} y1={14} x2={200} y2={205} strokeWidth={2} />
          <line x1={0} y1={200} x2={400} y2={200} strokeWidth={1.4} />
        </g>
      </svg>

      <div className="relative animate-rise-in">{children}</div>
    </>
  );
}
