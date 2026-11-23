import { useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { api, getErrorMessage } from "../api/client";
import { queryKeys, useProviders } from "../api/hooks";
import { useAuth } from "../auth/useAuth";
import { useToast } from "../components/useToast";
import { safeNextPath } from "../auth/nextPath";
import { CircleAlert } from "lucide-react";
import { clearSavedQuiz, markQuizProfileSaved, readSavedQuiz } from "../quizStorage";
import { clearSavedStart, markStartProfileSaved, readSavedStart } from "../startStorage";
function AuthForm({ mode }: { mode: "login" | "register" }) {
  const [email, setEmail] = useState(""); const [password, setPassword] = useState(""); const [name, setName] = useState(""); const [error, setError] = useState(""); const [submitting, setSubmitting] = useState(false);
  const providers = useProviders(); const { user } = useAuth(); const nav = useNavigate(); const [search] = useSearchParams(); const queryClient = useQueryClient(); const { showToast } = useToast();
  const next = safeNextPath(search.get("next"));
  if (user) return <Navigate to={next} replace />;
  async function submit(event: FormEvent) {
    event.preventDefault(); if (submitting) return; setSubmitting(true); setError("");
    try {
      const authenticatedUser = mode === "login"
        ? await api.login({ email, password })
        : await api.register({ email, password, display_name: name || undefined });
      queryClient.setQueryData(queryKeys.me, authenticatedUser);
      const quiz = readSavedQuiz(); const start = readSavedStart();
      const localProfile = { quiz_answers: quiz?.answers ?? null, liked_ids: start?.liked_ids ?? [] };
      const hasLocalData = Boolean(quiz || start);
      const needsProfileSave = Boolean((quiz && quiz.profileSavedFor !== authenticatedUser.id) || (start && start.profile_saved_for !== authenticatedUser.id));
      if ((mode === "login" && hasLocalData) || (mode === "register" && needsProfileSave)) {
        void (async () => {
          try {
            if (mode === "login") {
              const profile = await api.tasteProfile();
              const hasProfile = Boolean(profile.quiz_answers && Object.keys(profile.quiz_answers).length) || profile.liked_ids.length > 0;
              if (hasProfile) {
                if (quiz) markQuizProfileSaved(authenticatedUser.id); if (start) markStartProfileSaved(authenticatedUser.id);
                showToast("Your saved profile was kept", "info");
              } else if (needsProfileSave) {
                await api.saveTasteProfile(localProfile);
                if (quiz) markQuizProfileSaved(authenticatedUser.id); if (start) markStartProfileSaved(authenticatedUser.id);
                showToast("Saved your answers", "success");
              }
            } else {
              await api.saveTasteProfile(localProfile);
              if (quiz) markQuizProfileSaved(authenticatedUser.id); if (start) markStartProfileSaved(authenticatedUser.id);
              showToast("Saved your answers", "success");
            }
          } catch (reason) { showToast(getErrorMessage(reason, "Could not save your profile"), "error"); }
        })();
      }
      nav(next); showToast("You’re signed in", "success");
    } catch (e) { const message = e instanceof Error ? e.message : "Unable to sign in"; setError(message); }
    finally { setSubmitting(false); }
  }
  return <section className="auth-page"><h1>{mode === "login" ? "Sign in" : "Create an account"}</h1>
    <form className="auth-form" onSubmit={submit}>
    {mode === "register" && <label>Display name<input value={name} onChange={(e) => setName(e.target.value)} autoComplete="nickname" /></label>}
      <label>Email<input type="email" required autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} /></label>
      <label>Password<input type="password" required minLength={mode === "register" ? 10 : 1} autoComplete={mode === "login" ? "current-password" : "new-password"} value={password} onChange={(e) => setPassword(e.target.value)} /></label>
      {error && <div className="status-box status-error auth-error" role="alert"><CircleAlert aria-hidden="true" /><p>{error}</p></div>}<button disabled={submitting} type="submit">{submitting ? mode === "login" ? "Signing in…" : "Creating account…" : mode === "login" ? "Sign in" : "Register"}</button>
    </form>
    {providers.data?.google && <a className="google-button" href={api.googleLogin()}>Continue with Google</a>}
    <p>{mode === "login" ? <>New here? <Link to="/register">Create an account</Link></> : <>Already registered? <Link to="/login">Sign in</Link></>}</p>
  </section>;
}
export function LoginPage() { return <AuthForm mode="login" />; }
export function RegisterPage() { return <AuthForm mode="register" />; }
export function SettingsPage() {
  const { user, mature, setMature, signOut, refresh } = useAuth();
  const nav = useNavigate(); const { showToast } = useToast();
  const [displayName, setDisplayName] = useState(user?.display_name ?? "");
  const [nameError, setNameError] = useState(""); const [savingName, setSavingName] = useState(false);
  const [confirmation, setConfirmation] = useState(""); const [deleteError, setDeleteError] = useState(""); const [deleting, setDeleting] = useState(false);
  async function saveName(event: FormEvent) {
    event.preventDefault(); setNameError(""); setSavingName(true);
    try { await api.updateMe({ display_name: displayName.trim() }); await refresh(); showToast("Display name saved", "success"); }
    catch (reason) { setNameError(getErrorMessage(reason, "Could not save display name")); }
    finally { setSavingName(false); }
  }
  async function deleteAccount() {
    if (confirmation !== "DELETE" || deleting) return;
    setDeleting(true); setDeleteError("");
    try {
      await api.deleteMe(); clearSavedQuiz(); clearSavedStart();
      try { await signOut(); } catch { /* Delete already cleared the server session. */ }
      nav("/", { replace: true, state: { showHome: true } }); showToast("Account deleted", "success");
    } catch (reason) { setDeleteError(getErrorMessage(reason, "Could not delete account")); }
    finally { setDeleting(false); }
  }
  if (!user) return <Navigate to="/login" replace />;
  return <section className="settings-page">
    <h1>Settings</h1><p className="settings-email">{user.email}</p>
    <form className="settings-section" onSubmit={(event) => void saveName(event)}>
      <h2>Account</h2><label>Display name<input autoComplete="nickname" maxLength={100} value={displayName} onChange={(event) => setDisplayName(event.target.value)} /></label>
      {nameError && <p className="settings-error" role="alert">{nameError}</p>}
      <button className="primary-action" disabled={savingName || !displayName.trim()} type="submit">{savingName ? "Saving…" : "Save display name"}</button>
      <label className="setting-toggle"><input type="checkbox" checked={mature} onChange={(event) => void setMature(event.target.checked)} /> Include mature anime (18+)</label>
      <Link className="settings-link" to="/quiz">Retake quiz</Link>
    </form>
    <section aria-labelledby="delete-account-title" className="settings-section danger-section">
      <h2 id="delete-account-title">Delete account</h2>
      <p id="delete-account-warning">This permanently deletes your account and its list. Type DELETE to confirm. This action cannot be undone.</p>
      <label>Type DELETE to confirm<input aria-describedby="delete-account-warning" autoComplete="off" onChange={(event) => { setConfirmation(event.target.value); setDeleteError(""); }} value={confirmation} /></label>
      {deleteError && <p className="settings-error" role="alert">{deleteError}</p>}
      <button className="delete-account-button" disabled={confirmation !== "DELETE" || deleting} onClick={() => void deleteAccount()} type="button">{deleting ? "Deleting account…" : "Delete account"}</button>
    </section>
  </section>;
}
