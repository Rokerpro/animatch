import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { Link, Navigate } from "react-router-dom";
import { ApiError, getErrorMessage } from "../api/client";
import { useAskRecommendations } from "../api/useAskRecommendations";
import { useFeatures } from "../api/useFeatures";
import { useAuth } from "../auth/useAuth";
import { PosterGrid } from "../components/PosterGrid";
import { RecommendationCard } from "../components/RecommendationCard";

// Mirrors backend/app/recs/natural_language.py:NL_MAX_CHARS default.
const NL_MAX_CHARS = 300;
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
    if (ask.error instanceof ApiError && ask.error.code === "natural_language_unavailable") {
      void refreshFeatures();
    }
  }, [ask.error, refreshFeatures]);

  if (authLoading) return <section className="browse-page ask-page"><p>Checking your account…</p></section>;
  if (!user) return <Navigate replace to={`/login?next=${encodeURIComponent("/ask")}`} />;

  function editRequest() {
    ask.reset();
    setShowResults(false);
    window.requestAnimationFrame(() => textareaRef.current?.focus());
  }

  async function submit(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault();
    const trimmed = text.trim();
    if (!trimmed || trimmed.length > NL_MAX_CHARS || ask.isPending || !features.data?.natural_language) return;
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

  if (features.isPending) return <section className="browse-page ask-page"><p aria-live="polite">Checking assistant availability…</p></section>;
  if (features.isError || !features.data?.natural_language) return <section className="browse-page ask-page">
    <h1 className="page-title">Describe what you want</h1>
    <p role="status">This feature is not enabled on this server.</p>
    <Link to="/new">Use Find something new</Link>
  </section>;

  if (showResults && ask.data) {
    const { results, understood, message } = ask.data;
    return <section className="browse-page ask-page ask-results">
      <header className="ask-page-heading">
        <p className="eyebrow">A recommendation conversation</p>
        <h1 className="page-title" ref={resultsHeadingRef} tabIndex={-1}>Here’s what I found</h1>
        <button className="text-button" onClick={editRequest} type="button">Edit request</button>
      </header>
      <section aria-labelledby="ask-understood-heading" className="ask-understood">
        <h2 id="ask-understood-heading">How I read your request</h2>
        {understood.quiz_answers.length > 0 && <ul className="ask-chips" aria-label="Interpreted preferences">
          {understood.quiz_answers.map((answer) => <li key={`${answer.question_id}-${answer.answer_id}`}>{answer.question_label}: {answer.answer_label}</li>)}
        </ul>}
        {understood.matched_seed_titles.length > 0 && <ul className="ask-chips" aria-label="Matched titles">
          {understood.matched_seed_titles.map((seed) => <li key={seed.id}><Link to={`/anime/${seed.id}`}>{seed.title}</Link></li>)}
        </ul>}
        {understood.unmatched_seed_titles.length > 0 && <p className="ask-unmatched">Couldn't find: {understood.unmatched_seed_titles.join(", ")}</p>}
      </section>
      {results.length > 0 ? <PosterGrid animeIds={results.map((result) => result.id)} label="Recommendations from your request">
        {results.map((result) => <RecommendationCard key={result.id} recommendation={result} />)}
      </PosterGrid> : <div aria-live="polite" className="empty-recommendations ask-empty-results">
        <p>{message || "I couldn’t find recommendations for that request."}</p>
        <p>Try mentioning a mood or a few titles you enjoy.</p>
      </div>}
    </section>;
  }

  const error = ask.error;
  const isAssistantUnavailable = error instanceof ApiError && error.status === 503;
  const inlineError = error instanceof ApiError && error.code === "natural_language_unavailable"
    ? "This feature is not enabled on this server."
    : isAssistantUnavailable
      ? "The assistant is unavailable right now. You can use the normal quiz instead."
      : error ? getErrorMessage(error, "Could not process your request. Please try again.") : "";

  return <section className="browse-page ask-page">
    <header className="ask-page-heading">
      <p className="eyebrow">Recommendations in your own words</p>
      <h1 className="page-title">Describe what you want</h1>
      <p>Share a mood, a few details, or titles you already enjoy.</p>
    </header>
    <form className="ask-form" onSubmit={(event) => void submit(event)}>
      <label htmlFor="ask-request">What are you in the mood to watch?</label>
      <textarea
        id="ask-request"
        ref={textareaRef}
        maxLength={undefined}
        onChange={(event) => setText(event.currentTarget.value)}
        onKeyDown={handleKeyDown}
        value={text}
        rows={5}
        aria-describedby="ask-counter ask-privacy"
      />
      <p aria-live="polite" className={`ask-counter${text.length > NL_MAX_CHARS ? " is-over-limit" : ""}`} id="ask-counter">{text.length} / {NL_MAX_CHARS} characters</p>
      <p className="ask-privacy" id="ask-privacy">Your text is sent to Google’s Gemini API to be interpreted.</p>
      <div className="ask-examples" aria-label="Example requests">
        {EXAMPLES.map((example) => <button className="ask-example" key={example} onClick={() => setText(example)} type="button">{example}</button>)}
      </div>
      {error && <div aria-live="assertive" className="ask-error" role="alert">
        <p>{inlineError}</p>
        {isAssistantUnavailable && <Link to="/new">Try the normal quiz</Link>}
        {error instanceof ApiError && error.code === "natural_language_unavailable" && <button className="text-button" onClick={() => void features.refetch()} type="button">Refresh availability</button>}
      </div>}
      <div aria-live="polite" className="sr-only">{ask.isPending ? "Getting recommendations…" : ""}</div>
      <button className="primary-action" disabled={!text.trim() || text.trim().length > NL_MAX_CHARS || ask.isPending} type="submit">
        {ask.isPending ? "Finding recommendations…" : "Get recommendations"}
      </button>
    </form>
  </section>;
}
