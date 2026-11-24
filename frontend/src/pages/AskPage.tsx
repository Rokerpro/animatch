import {
  useEffect,
  useRef,
  useState,
  type FormEvent,
  type KeyboardEvent,
} from "react";
import { Link, Navigate } from "react-router-dom";
import { Search, Sparkles } from "lucide-react";
import { ApiError, getErrorMessage } from "../api/client";
import { useAskRecommendations } from "../api/useAskRecommendations";
import { useFeatures } from "../api/useFeatures";
import { useAuth } from "../auth/useAuth";
import { PosterGrid } from "../components/PosterGrid";
import { RecommendationCard } from "../components/RecommendationCard";
import { PageTitle } from "../components/PageTitle";
import "../styles/ask.css";

// Mirrors backend/app/recs/natural_language.py:NL_MAX_CHARS default.
const NL_MAX_CHARS = 300;
const TIPS = [
  { title: "A mood or feeling", body: "Cozy, bittersweet, tense, funny." },
  { title: "Titles you liked", body: "“Like Mushishi, but with a story arc.”" },
  { title: "Limits", body: "Short series, finished airing, recent." },
];
const EXAMPLES = [
  "I want a cozy fantasy with a hopeful ending.",
  "Something tense and clever, but not too long.",
  "I liked Frieren and Fullmetal Alchemist; what else might I enjoy?",
];

export function AskPage() {
  const { user, authLoading } = useAuth();
  const features = useFeatures();
  const refreshFeatures = features.refetch;
  const ask = useAskRecommendations();
  const [text, setText] = useState("");
  const [showResults, setShowResults] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const resultsHeadingRef = useRef<HTMLHeadingElement>(null);

  useEffect(() => {
    if (showResults && ask.data) resultsHeadingRef.current?.focus();
  }, [ask.data, showResults]);

  useEffect(() => {
    if (
      ask.error instanceof ApiError &&
      ask.error.code === "natural_language_unavailable"
    ) {
      void refreshFeatures();
    }
  }, [ask.error, refreshFeatures]);

  if (authLoading)
    return (
      <section className="browse-page ask-page">
        <p>Checking your account…</p>
      </section>
    );
  if (!user)
    return (
      <Navigate replace to={`/login?next=${encodeURIComponent("/ask")}`} />
    );

  function editRequest() {
    ask.reset();
    setShowResults(false);
    window.requestAnimationFrame(() => textareaRef.current?.focus());
  }

  async function submit(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault();
    const trimmed = text.trim();
    if (
      !trimmed ||
      trimmed.length > NL_MAX_CHARS ||
      ask.isPending ||
      !features.data?.natural_language
    )
      return;
    try {
      await ask.mutateAsync({ text: trimmed });
      setShowResults(true);
    } catch {
      // Errors are normalized by the shared API client and shown inline below.
    }
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
      event.preventDefault();
      void submit();
    }
  }

  if (features.isPending)
    return (
      <section className="browse-page ask-page">
        <p aria-live="polite">Checking assistant availability…</p>
      </section>
    );
  if (features.isError || !features.data?.natural_language)
    return (
      <section className="browse-page ask-page">
        <header className="page-header">
          <PageTitle lead="Describe" accent="What You Want" />
        </header>
        <div className="ask-disabled panel">
          <p role="status">This feature is not enabled on this server.</p>
          <Link className="secondary-action" to="/new">
            Use Find something new
          </Link>
        </div>
      </section>
    );

  if (showResults && ask.data) {
    const { results, understood, message } = ask.data;
    return (
      <section className="browse-page ask-page ask-results">
        <header className="page-header">
          <PageTitle
            accent="I Found"
            focusable
            lead="Here’s What"
            ref={resultsHeadingRef}
          />
          <div className="page-header-aside">
            <button
              className="secondary-action"
              onClick={editRequest}
              type="button"
            >
              Edit request
            </button>
          </div>
        </header>
        <section
          aria-labelledby="ask-understood-heading"
          className="ask-understood"
        >
          <h2 className="subheading" id="ask-understood-heading">
            How I read your request
          </h2>
          {understood.quiz_answers.length > 0 && (
            <ul className="ask-chips" aria-label="Interpreted preferences">
              {understood.quiz_answers.map((answer) => (
                <li
                  className="chip"
                  key={`${answer.question_id}-${answer.answer_id}`}
                >
                  {answer.question_label}: {answer.answer_label}
                </li>
              ))}
            </ul>
          )}
          {understood.matched_seed_titles.length > 0 && (
            <ul className="ask-chips" aria-label="Matched titles">
              {understood.matched_seed_titles.map((seed) => (
                <li key={seed.id}>
                  <Link className="chip" to={`/anime/${seed.id}`}>
                    {seed.title}
                  </Link>
                </li>
              ))}
            </ul>
          )}
          {understood.unmatched_seed_titles.length > 0 && (
            <p className="ask-unmatched muted">
              Couldn't find: {understood.unmatched_seed_titles.join(", ")}
            </p>
          )}
        </section>
        {results.length > 0 ? (
          <PosterGrid
            animeIds={results.map((result) => result.id)}
            label="Recommendations from your request"
            wide
          >
            {results.map((result) => (
              <RecommendationCard key={result.id} recommendation={result} />
            ))}
          </PosterGrid>
        ) : (
          <div
            aria-live="polite"
            className="empty-recommendations ask-empty-results"
          >
            <p>
              {message || "I couldn’t find recommendations for that request."}
            </p>
            <p>Try mentioning a mood or a few titles you enjoy.</p>
          </div>
        )}
      </section>
    );
  }

  const error = ask.error;
  const isAssistantUnavailable =
    error instanceof ApiError && error.status === 503;
  const inlineError =
    error instanceof ApiError && error.code === "natural_language_unavailable"
      ? "This feature is not enabled on this server."
      : isAssistantUnavailable
        ? "The assistant is unavailable right now. You can use the normal quiz instead."
        : error
          ? getErrorMessage(
              error,
              "Could not process your request. Please try again."
            )
          : "";

  const overLimit = text.length > NL_MAX_CHARS;
  return (
    <section className="browse-page ask-page">
      <header className="page-header">
        <div>
          <PageTitle lead="Describe" accent="What You Want" />
          <p className="page-subtitle">
            Describe what you’re looking for and we’ll find titles that fit.
          </p>
        </div>
      </header>
      <div className="ask-layout">
        <div className="ask-main">
          <form className="ask-form" onSubmit={(event) => void submit(event)}>
            <div className="ask-composer">
              <label className="sr-only" htmlFor="ask-request">
                What are you in the mood to watch?
              </label>
              <textarea
                aria-describedby="ask-counter ask-privacy"
                id="ask-request"
                onChange={(event) => setText(event.currentTarget.value)}
                onKeyDown={handleKeyDown}
                placeholder="A clever mystery with a small cast and a twist at the end, under 13 episodes."
                ref={textareaRef}
                rows={3}
                value={text}
              />
              <div className="ask-toolbar">
                <p className="ask-model-note">
                  <Sparkles aria-hidden="true" size={16} strokeWidth={1.6} />
                  Interpreted by Gemini
                </p>
                <p
                  aria-live="polite"
                  className={`ask-counter${overLimit ? " is-over-limit" : ""}`}
                  id="ask-counter"
                >
                  {text.length} / {NL_MAX_CHARS}
                </p>
                <button
                  className="primary-action"
                  disabled={!text.trim() || overLimit || ask.isPending}
                  type="submit"
                >
                  {ask.isPending
                    ? "Finding recommendations…"
                    : "Find recommendations"}
                </button>
              </div>
            </div>
            <p className="ask-privacy" id="ask-privacy">
              Your request is sent to Google’s Gemini API to be interpreted. It
              isn’t saved to your account.
            </p>
            {error && (
              <div aria-live="assertive" className="ask-error" role="alert">
                <p>{inlineError}</p>
                {isAssistantUnavailable && (
                  <Link to="/new">Try the normal quiz</Link>
                )}
                {error instanceof ApiError &&
                  error.code === "natural_language_unavailable" && (
                    <button
                      className="text-button"
                      onClick={() => void features.refetch()}
                      type="button"
                    >
                      Refresh availability
                    </button>
                  )}
              </div>
            )}
            <div aria-live="polite" className="sr-only">
              {ask.isPending ? "Getting recommendations…" : ""}
            </div>
          </form>
          <section
            aria-labelledby="ask-examples-heading"
            className="ask-examples"
          >
            <h2 className="ask-side-heading" id="ask-examples-heading">
              Examples
            </h2>
            <ul className="ask-example-list">
              {EXAMPLES.map((example) => (
                <li key={example}>
                  <button
                    className="ask-example"
                    onClick={() => {
                      setText(example);
                      textareaRef.current?.focus();
                    }}
                    type="button"
                  >
                    <Search aria-hidden="true" size={16} strokeWidth={1.8} />
                    {example}
                  </button>
                </li>
              ))}
            </ul>
          </section>
        </div>
        <aside aria-labelledby="ask-tips-heading" className="ask-tips">
          <h2 className="ask-side-heading" id="ask-tips-heading">
            What to include
          </h2>
          <dl>
            {TIPS.map((tip) => (
              <div key={tip.title}>
                <dt>{tip.title}</dt>
                <dd>{tip.body}</dd>
              </div>
            ))}
          </dl>
        </aside>
      </div>
    </section>
  );
}
