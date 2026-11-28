import {
  useEffect,
  useRef,
  useState,
  type FormEvent,
  type KeyboardEvent,
} from "react";
import { Link, Navigate } from "react-router-dom";
import { Sparkles } from "lucide-react";
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
const EXAMPLES = [
  "Something cozy to watch after work",
  "Like Frieren, but shorter",
  "A sports show for people who hate sports",
  "Dark fantasy with a good ending",
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
          <PageTitle lead="Describe what you want" />
        </header>
        <div className="ask-disabled">
          <p role="status">This feature is not enabled on this server.</p>
          <Link className="secondary-action" to="/new">
            Use Find something new
          </Link>
        </div>
      </section>
    );

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
  const answer = showResults ? ask.data : undefined;
  return (
    <section className="browse-page ask-page">
      <header className="page-header">
        <div>
          <PageTitle lead="Describe what you want" />
          <p className="page-subtitle">
            Say it the way you would to a friend. Mention a mood or a few titles
            you enjoy.
          </p>
        </div>
      </header>
      <div className="ask-layout">
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
                  : "Get recommendations"}
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
        <aside className="ask-side">
          <section aria-labelledby="ask-examples-heading">
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
                    {example}
                  </button>
                </li>
              ))}
            </ul>
          </section>
          <section aria-labelledby="ask-tips-heading" className="ask-tips">
            <h2 className="ask-side-heading" id="ask-tips-heading">
              Tips
            </h2>
            <p>
              Name titles you liked and what you liked about them. Length and
              era help too.
            </p>
          </section>
        </aside>
      </div>
      {answer && (
        <section
          aria-labelledby="ask-understood-heading"
          className="ask-results"
        >
          <div className="ask-results-head">
            <div className="ask-understood">
              <h2
                className="ask-understood-heading"
                id="ask-understood-heading"
                ref={resultsHeadingRef}
                tabIndex={-1}
              >
                What we understood
              </h2>
              {answer.understood.quiz_answers.length > 0 && (
                <ul className="ask-chips" aria-label="Interpreted preferences">
                  {answer.understood.quiz_answers.map((item) => (
                    <li
                      className="ask-chip"
                      key={`${item.question_id}-${item.answer_id}`}
                    >
                      {item.question_label}: {item.answer_label}
                    </li>
                  ))}
                </ul>
              )}
              {answer.understood.matched_seed_titles.length > 0 && (
                <ul className="ask-chips" aria-label="Matched titles">
                  {answer.understood.matched_seed_titles.map((seed) => (
                    <li key={seed.id}>
                      <Link className="ask-chip" to={`/anime/${seed.id}`}>
                        {seed.title}
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
              {answer.understood.unmatched_seed_titles.length > 0 && (
                <p className="ask-unmatched">
                  Couldn't find:{" "}
                  {answer.understood.unmatched_seed_titles.join(", ")}
                </p>
              )}
            </div>
            <button
              className="secondary-action"
              onClick={editRequest}
              type="button"
            >
              Edit request
            </button>
          </div>
          {answer.results.length > 0 ? (
            <PosterGrid
              animeIds={answer.results.map((result) => result.id)}
              label="Recommendations from your request"
              wide
            >
              {answer.results.map((result) => (
                <RecommendationCard key={result.id} recommendation={result} />
              ))}
            </PosterGrid>
          ) : (
            <div
              aria-live="polite"
              className="empty-recommendations ask-empty-results"
            >
              <p>
                {answer.message ||
                  "I couldn’t find recommendations for that request."}
              </p>
              <p>Try mentioning a mood or a few titles you enjoy.</p>
            </div>
          )}
          <p className="ask-footnote">
            Not quite right? <Link to="/new">Try the normal quiz</Link>.
          </p>
        </section>
      )}
    </section>
  );
}
