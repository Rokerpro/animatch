import { useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import { X } from "lucide-react";

export function AuthPrompt({ nextPath, onClose }: { nextPath: string; onClose: () => void }) {
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    closeButtonRef.current?.focus();
    function onKeyDown(event: KeyboardEvent) { if (event.key === "Escape") onClose(); }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose]);
  const next = encodeURIComponent(nextPath);
  return <div className="auth-prompt-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
    <section aria-labelledby="auth-prompt-title" aria-modal="true" className="auth-prompt" role="dialog">
      <button aria-label="Close sign-in prompt" className="auth-prompt-close" onClick={onClose} ref={closeButtonRef} type="button"><X aria-hidden="true" size={16} strokeWidth={2} /></button>
      <h2 id="auth-prompt-title">Sign in to save anime</h2>
      <p>Create an account or sign in to add titles to your list and save ratings.</p>
      <div className="auth-prompt-actions">
        <Link className="primary-action" to={`/login?next=${next}`}>Sign in</Link>
        <Link className="secondary-action" to={`/register?next=${next}`}>Create account</Link>
      </div>
    </section>
  </div>;
}
