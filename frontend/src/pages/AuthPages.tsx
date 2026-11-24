import { useState, type FormEvent } from "react";
import "../styles/account.css";
import { Link, Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { api, getErrorMessage } from "../api/client";
import { queryKeys, useProviders } from "../api/hooks";
import { useAuth } from "../auth/useAuth";
import { useToast } from "../components/useToast";
import { safeNextPath } from "../auth/nextPath";
import { CircleAlert } from "lucide-react";
import { PageTitle } from "../components/PageTitle";
import { PosterStack } from "../components/PosterStack";
import {
  clearSavedQuiz,
  markQuizProfileSaved,
  readSavedQuiz,
} from "../quizStorage";
import {
  clearSavedStart,
  markStartProfileSaved,
  readSavedStart,
} from "../startStorage";
function AuthForm({ mode }: { mode: "login" | "register" }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const providers = useProviders();
  const { user } = useAuth();
  const nav = useNavigate();
  const [search] = useSearchParams();
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const next = safeNextPath(search.get("next"));
  if (user) return <Navigate to={next} replace />;
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (submitting) return;
    setSubmitting(true);
    setError("");
    try {
      const authenticatedUser =
        mode === "login"
          ? await api.login({ email, password })
          : await api.register({
              email,
              password,
              display_name: name || undefined,
            });
      queryClient.setQueryData(queryKeys.me, authenticatedUser);
      const quiz = readSavedQuiz();
      const start = readSavedStart();
      const localProfile = {
        quiz_answers: quiz?.answers ?? null,
        liked_ids: start?.liked_ids ?? [],
      };
      const hasLocalData = Boolean(quiz || start);
      const needsProfileSave = Boolean(
        (quiz && quiz.profileSavedFor !== authenticatedUser.id) ||
        (start && start.profile_saved_for !== authenticatedUser.id)
      );
      if (
        (mode === "login" && hasLocalData) ||
        (mode === "register" && needsProfileSave)
      ) {
        void (async () => {
          try {
            if (mode === "login") {
              const profile = await api.tasteProfile();
              const hasProfile =
                Boolean(
                  profile.quiz_answers &&
                  Object.keys(profile.quiz_answers).length
                ) || profile.liked_ids.length > 0;
              if (hasProfile) {
                if (quiz) markQuizProfileSaved(authenticatedUser.id);
                if (start) markStartProfileSaved(authenticatedUser.id);
                showToast("Your saved profile was kept", "info");
              } else if (needsProfileSave) {
                await api.saveTasteProfile(localProfile);
                if (quiz) markQuizProfileSaved(authenticatedUser.id);
                if (start) markStartProfileSaved(authenticatedUser.id);
                showToast("Saved your answers", "success");
              }
            } else {
              await api.saveTasteProfile(localProfile);
              if (quiz) markQuizProfileSaved(authenticatedUser.id);
              if (start) markStartProfileSaved(authenticatedUser.id);
              showToast("Saved your answers", "success");
            }
          } catch (reason) {
            showToast(
              getErrorMessage(reason, "Could not save your profile"),
              "error"
            );
          }
        })();
      }
      nav(next);
      showToast("You’re signed in", "success");
    } catch (e) {
      const message = e instanceof Error ? e.message : "Unable to sign in";
      setError(message);
    } finally {
      setSubmitting(false);
    }
  }
  const isLogin = mode === "login";
  return (
    <section className="auth-page">
      <div className="auth-main">
        <PageTitle
          lead={isLogin ? "Sign" : "Create an"}
          accent={isLogin ? "In" : "Account"}
        />
        <p className="page-subtitle">
          {isLogin
            ? "Pick up your list and recommendations where you left off."
            : "Save your list and get picks that learn from it."}
        </p>
        <form className="auth-form" onSubmit={submit}>
          {!isLogin && (
            <label className="field">
              <span>Display name</span>
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                autoComplete="nickname"
                placeholder="What should we call you?"
              />
            </label>
          )}
          <label className="field">
            <span>Email</span>
            <input
              type="email"
              required
              autoComplete="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </label>
          <div className="field">
            <label className="field" htmlFor="auth-password">
              <span>Password</span>
              <input
                id="auth-password"
                type="password"
                required
                minLength={isLogin ? 1 : 10}
                autoComplete={isLogin ? "current-password" : "new-password"}
                aria-describedby={isLogin ? undefined : "password-hint"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </label>
            {!isLogin && (
              <p className="field-hint" id="password-hint">
                At least 10 characters.
              </p>
            )}
          </div>
          {error && (
            <div className="status-box status-error auth-error" role="alert">
              <CircleAlert aria-hidden="true" />
              <p>{error}</p>
            </div>
          )}
          <button disabled={submitting} type="submit">
            {submitting
              ? isLogin
                ? "Signing in…"
                : "Creating account…"
              : isLogin
                ? "Sign in"
                : "Create account"}
          </button>
        </form>
        {providers.data?.google && (
          <a className="google-button" href={api.googleLogin()}>
            <GoogleMark />
            {isLogin ? "Sign in with Google" : "Sign up with Google"}
          </a>
        )}
        <p className="auth-switch">
          {isLogin ? (
            <>
              New here? <Link to="/register">Create an account</Link>
            </>
          ) : (
            <>
              Already registered? <Link to="/login">Sign in</Link>
            </>
          )}
        </p>
      </div>
      <aside className="auth-aside panel">
        <PosterStack />
        <div className="auth-aside-copy">
          <h2>Your list follows you.</h2>
          <p>
            Saved titles, For You picks and quiz results stay with your account,
            on any device.
          </p>
        </div>
      </aside>
    </section>
  );
}
function GoogleMark() {
  return (
    <svg aria-hidden="true" height="18" viewBox="0 0 48 48" width="18">
      <path
        d="M43.6 20.5H42V20H24v8h11.3C33.7 32.7 29.2 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34 6.1 29.3 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.3-.1-2.4-.4-3.5z"
        fill="#FFC107"
      />
      <path
        d="M6.3 14.7l6.6 4.8C14.7 15.1 19 12 24 12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34 6.1 29.3 4 24 4 16.3 4 9.7 8.3 6.3 14.7z"
        fill="#FF3D00"
      />
      <path
        d="M24 44c5.2 0 9.9-2 13.4-5.2l-6.2-5.2C29.2 35.1 26.7 36 24 36c-5.2 0-9.6-3.3-11.3-8l-6.5 5C9.5 39.6 16.2 44 24 44z"
        fill="#4CAF50"
      />
      <path
        d="M43.6 20.5H42V20H24v8h11.3c-.8 2.2-2.2 4.2-4.1 5.6l6.2 5.2C37 39.2 44 34 44 24c0-1.3-.1-2.4-.4-3.5z"
        fill="#1976D2"
      />
    </svg>
  );
}
export function LoginPage() {
  return <AuthForm mode="login" />;
}
export function RegisterPage() {
  return <AuthForm mode="register" />;
}
const SETTINGS_SECTIONS = [
  { id: "profile", label: "Profile" },
  { id: "preferences", label: "Preferences" },
  { id: "delete-account", label: "Delete account" },
];
export function SettingsPage() {
  const { user, mature, setMature, signOut, refresh } = useAuth();
  const nav = useNavigate();
  const { showToast } = useToast();
  const [displayName, setDisplayName] = useState(user?.display_name ?? "");
  const [nameError, setNameError] = useState("");
  const [savingName, setSavingName] = useState(false);
  const [confirmation, setConfirmation] = useState("");
  const [deleteError, setDeleteError] = useState("");
  const [deleting, setDeleting] = useState(false);
  const [activeSection, setActiveSection] = useState("profile");
  async function saveName(event: FormEvent) {
    event.preventDefault();
    setNameError("");
    setSavingName(true);
    try {
      await api.updateMe({ display_name: displayName.trim() });
      await refresh();
      showToast("Display name saved", "success");
    } catch (reason) {
      setNameError(getErrorMessage(reason, "Could not save display name"));
    } finally {
      setSavingName(false);
    }
  }
  async function deleteAccount() {
    if (confirmation !== "DELETE" || deleting) return;
    setDeleting(true);
    setDeleteError("");
    try {
      await api.deleteMe();
      clearSavedQuiz();
      clearSavedStart();
      try {
        await signOut();
      } catch {
        /* Delete already cleared the server session. */
      }
      nav("/", { replace: true, state: { showHome: true } });
      showToast("Account deleted", "success");
    } catch (reason) {
      setDeleteError(getErrorMessage(reason, "Could not delete account"));
    } finally {
      setDeleting(false);
    }
  }
  async function handleSignOut() {
    try {
      await signOut();
    } catch {
      /* Local state is cleared even if the server session expired. */
    }
    nav("/", { replace: true, state: { showHome: true } });
    showToast("You’re signed out", "success");
  }
  if (!user) return <Navigate to="/login" replace />;
  const initial = (user.display_name || user.email).trim().charAt(0);
  return (
    <section className="settings-page">
      <header className="page-header">
        <div>
          <PageTitle lead="Account" accent="Settings" />
          <p className="page-subtitle">
            Manage your profile, preferences and account.
          </p>
        </div>
      </header>
      <div className="settings-layout">
        <nav aria-label="Settings sections" className="settings-nav">
          {SETTINGS_SECTIONS.map((section) => (
            <a
              aria-current={activeSection === section.id ? "true" : undefined}
              className={activeSection === section.id ? "active" : undefined}
              href={`#${section.id}`}
              key={section.id}
              onClick={() => setActiveSection(section.id)}
            >
              {section.label}
            </a>
          ))}
          <hr />
          <button
            className="settings-signout"
            onClick={() => void handleSignOut()}
            type="button"
          >
            Sign out
          </button>
        </nav>
        <div className="settings-content">
          <section aria-labelledby="profile-title" id="profile">
            <h2 className="settings-heading" id="profile-title">
              Profile
            </h2>
            <div className="settings-panel">
              <div className="settings-row settings-identity">
                <span aria-hidden="true" className="settings-avatar">
                  {initial.toUpperCase()}
                </span>
                <div>
                  <p className="settings-name">
                    {user.display_name || "No display name"}
                  </p>
                  <p className="muted">{user.email}</p>
                </div>
              </div>
              <form
                className="settings-row"
                onSubmit={(event) => void saveName(event)}
              >
                <div className="settings-row-copy">
                  <label htmlFor="settings-display-name">Display name</label>
                  <p className="muted">
                    Shown on your list and in your recommendations.
                  </p>
                  {nameError && (
                    <p className="settings-error" role="alert">
                      {nameError}
                    </p>
                  )}
                </div>
                <div className="settings-row-control">
                  <input
                    autoComplete="nickname"
                    id="settings-display-name"
                    maxLength={100}
                    value={displayName}
                    onChange={(event) => setDisplayName(event.target.value)}
                  />
                  <button
                    aria-label="Save display name"
                    className="primary-action"
                    disabled={savingName || !displayName.trim()}
                    type="submit"
                  >
                    {savingName ? "Saving…" : "Save"}
                  </button>
                </div>
              </form>
              <div className="settings-row">
                <div className="settings-row-copy">
                  <p className="settings-label">Email</p>
                  <p className="muted">The address you sign in with.</p>
                </div>
                <p className="settings-value">{user.email}</p>
              </div>
            </div>
          </section>
          <section aria-labelledby="preferences-title" id="preferences">
            <h2 className="settings-heading" id="preferences-title">
              Preferences
            </h2>
            <div className="settings-panel">
              <div className="settings-row">
                <div className="settings-row-copy">
                  <label htmlFor="settings-mature">
                    Include mature anime (18+)
                  </label>
                  <p className="muted" id="settings-mature-hint">
                    Adult titles stay hidden everywhere until you turn this on.
                  </p>
                </div>
                <input
                  aria-describedby="settings-mature-hint"
                  checked={mature}
                  className="switch"
                  id="settings-mature"
                  onChange={(event) => void setMature(event.target.checked)}
                  role="switch"
                  type="checkbox"
                />
              </div>
              <div className="settings-row">
                <div className="settings-row-copy">
                  <p className="settings-label">Quiz answers</p>
                  <p className="muted">
                    Retake the quiz to refresh your For You picks.
                  </p>
                </div>
                <Link className="secondary-action" to="/quiz">
                  Retake quiz
                </Link>
              </div>
            </div>
          </section>
          <section aria-labelledby="delete-account-title" id="delete-account">
            <h2 className="settings-heading" id="delete-account-title">
              Delete account
            </h2>
            <div className="settings-panel danger-panel">
              <div className="settings-row">
                <div className="settings-row-copy">
                  <label htmlFor="settings-delete-confirm">
                    Type DELETE to confirm
                  </label>
                  <p className="muted" id="delete-account-warning">
                    Permanently removes your account and your list. This cannot
                    be undone.
                  </p>
                  {deleteError && (
                    <p className="settings-error" role="alert">
                      {deleteError}
                    </p>
                  )}
                </div>
                <div className="settings-row-control">
                  <input
                    aria-describedby="delete-account-warning"
                    autoComplete="off"
                    id="settings-delete-confirm"
                    onChange={(event) => {
                      setConfirmation(event.target.value);
                      setDeleteError("");
                    }}
                    placeholder="DELETE"
                    value={confirmation}
                  />
                  <button
                    className="delete-account-button"
                    disabled={confirmation !== "DELETE" || deleting}
                    onClick={() => void deleteAccount()}
                    type="button"
                  >
                    {deleting ? "Deleting account…" : "Delete account"}
                  </button>
                </div>
              </div>
            </div>
          </section>
        </div>
      </div>
    </section>
  );
}
