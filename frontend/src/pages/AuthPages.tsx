import { useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import { useProviders } from "../api/hooks";
import { useAuth } from "../auth/useAuth";
import { useToast } from "../components/useToast";
import { safeNextPath } from "../auth/nextPath";
import { CircleAlert } from "lucide-react";
function AuthForm({ mode }: { mode: "login" | "register" }) {
  const [email, setEmail] = useState(""); const [password, setPassword] = useState(""); const [name, setName] = useState(""); const [error, setError] = useState("");
  const providers = useProviders(); const { user, refresh } = useAuth(); const nav = useNavigate(); const [search] = useSearchParams(); const queryClient = useQueryClient(); const { showToast } = useToast();
  const next = safeNextPath(search.get("next"));
  if (user) return <Navigate to={next} replace />;
  async function submit(event: FormEvent) {
    event.preventDefault(); setError("");
    try {
      if (mode === "login") await api.login({ email, password });
      else await api.register({ email, password, display_name: name || undefined });
      await refresh(); await queryClient.invalidateQueries(); nav(next); showToast("You’re signed in", "success");
    } catch (e) { const message = e instanceof Error ? e.message : "Unable to sign in"; setError(message); }
  }
  return <section className="auth-page"><h1>{mode === "login" ? "Sign in" : "Create an account"}</h1>
    <form className="auth-form" onSubmit={submit}>
    {mode === "register" && <label>Display name<input value={name} onChange={(e) => setName(e.target.value)} autoComplete="nickname" /></label>}
      <label>Email<input type="email" required autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} /></label>
      <label>Password<input type="password" required minLength={mode === "register" ? 10 : 1} autoComplete={mode === "login" ? "current-password" : "new-password"} value={password} onChange={(e) => setPassword(e.target.value)} /></label>
      {error && <div className="status-box status-error auth-error" role="alert"><CircleAlert aria-hidden="true" /><p>{error}</p></div>}<button type="submit">{mode === "login" ? "Sign in" : "Register"}</button>
    </form>
    {providers.data?.google && <a className="google-button" href={api.googleLogin()}>Continue with Google</a>}
    <p>{mode === "login" ? <>New here? <Link to="/register">Create an account</Link></> : <>Already registered? <Link to="/login">Sign in</Link></>}</p>
  </section>;
}
export function LoginPage() { return <AuthForm mode="login" />; }
export function RegisterPage() { return <AuthForm mode="register" />; }
export function SettingsPage() {
  const { user, mature, setMature } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  return <section className="auth-page"><h1>Settings</h1><p>{user.email}</p><label className="setting-toggle"><input type="checkbox" checked={mature} onChange={(e) => void setMature(e.target.checked)} /> Include mature anime</label></section>;
}
