import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { Link, Navigate } from "react-router-dom";
import { getErrorMessage } from "../api/client";
import { useNewRecommendationQuiz, useNewRecommendations } from "../api/useNewRecommendations";
import type { QuizQuestion } from "../api/types";
import { useAuth } from "../auth/useAuth";
import { PosterGrid } from "../components/PosterGrid";
import { RecommendationCard } from "../components/RecommendationCard";

// Keep in sync with backend/app/recs/quiz.py:NEW_QUIZ_QUESTION_IDS.
const NEW_QUIZ_QUESTION_IDS = ["mood", "length", "era"] as const;

export function NewPage() {
  const { user, authLoading } = useAuth();
  const quiz = useNewRecommendationQuiz(Boolean(user) && !authLoading);
  const recommendationMutation = useNewRecommendations();
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [resultsStep, setResultsStep] = useState(false);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const questions = useMemo(() => {
    const available = new Map((quiz.data ?? []).map((question) => [question.id, question]));
    return NEW_QUIZ_QUESTION_IDS.map((id) => available.get(id)).filter(
      (question): question is QuizQuestion => Boolean(question),
    );
  }, [quiz.data]);

  useEffect(() => {
    if (!authLoading && user) headingRef.current?.focus({ preventScroll: true });
  }, [authLoading, resultsStep, user]);

  if (authLoading) return <section className="quiz-page"><p>Checking your account…</p></section>;
  if (!user) return <Navigate replace to={`/login?next=${encodeURIComponent("/new")}`} />;

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!Object.keys(answers).length || recommendationMutation.isPending) return;
    try {
      await recommendationMutation.mutateAsync({ quiz_answers: answers });
      setResultsStep(true);
    } catch {
      // The shared API client has already normalized both FastAPI detail shapes.
    }
  }

  function startOver() {
    setAnswers({});
    recommendationMutation.reset();
    setResultsStep(false);
  }

  if (resultsStep && recommendationMutation.data) {
    const { mode, results } = recommendationMutation.data;
    return <section className="browse-page new-results-page">
      <header className="new-page-heading">
        <p className="eyebrow">Your next watch</p>
        <h1 className="page-title" ref={headingRef} tabIndex={-1}>Find something new</h1>
        {mode === "novelty" ? <p className="new-mode-message">These picks sit outside your usual taste.</p> : <div className="new-fallback-notice">
          <p>Your list is still empty, so these picks come from the normal quiz.</p>
          <p><Link to="/import">Import from MyAnimeList</Link> or <Link to="/browse">browse the catalog</Link>.</p>
        </div>}
        <button className="text-button" onClick={startOver} type="button">Start over</button>
      </header>
      {results.length ? <PosterGrid animeIds={results.map((result) => result.id)} label="Find something new recommendations">
        {results.map((result) => <RecommendationCard key={result.id} recommendation={result} />)}
      </PosterGrid> : <div aria-live="polite" className="empty-recommendations">
        <p>No recommendations matched those answers.</p>
        <button className="primary-action" onClick={startOver} type="button">Try different answers</button>
      </div>}
    </section>;
  }

  const selectedCount = Object.keys(answers).length;
  const error = recommendationMutation.error;
  return <section className="quiz-page new-page">
    <h1 className="page-title" ref={headingRef} tabIndex={-1}>Find something new</h1>
    <div className="quiz-card">
      <p className="new-page-intro">Choose any of these questions. You can skip the ones you do not have an answer for.</p>
      {quiz.isPending && <p aria-live="polite">Loading questions…</p>}
      {quiz.isError && <div aria-live="assertive" className="status-box status-error" role="alert">
        <p>{getErrorMessage(quiz.error, "Could not load the quiz questions.")}</p>
        <button className="text-button" onClick={() => void quiz.refetch()} type="button">Retry</button>
      </div>}
      {!quiz.isPending && !quiz.isError && <form className="new-quiz-form" onSubmit={(event) => void submit(event)}>
        {questions.map((question) => <NewQuizQuestion
          key={question.id}
          question={question}
          selected={answers[question.id] ?? ""}
          onSelect={(answer) => setAnswers((current) => ({ ...current, [question.id]: answer }))}
        />)}
        {!questions.length && <p>No discovery questions are available.</p>}
        {error && <p aria-live="assertive" className="new-quiz-error" role="alert">{getErrorMessage(error, "Could not find recommendations. Please try again.")}</p>}
        <div aria-live="polite" className="sr-only">{recommendationMutation.isPending ? "Finding recommendations…" : ""}</div>
        <button className="primary-action" disabled={selectedCount === 0 || recommendationMutation.isPending || !questions.length} type="submit">
          {recommendationMutation.isPending ? "Finding recommendations…" : "Find recommendations"}
        </button>
      </form>}
    </div>
  </section>;
}

function NewQuizQuestion({ question, selected, onSelect }: {
  question: QuizQuestion;
  selected: string;
  onSelect: (answerId: string) => void;
}) {
  return <fieldset className="new-quiz-question">
    <legend>{question.label}</legend>
    <div className="quiz-options">
      {question.answers.map((answer) => <label className="quiz-option" key={answer.id}>
        <input checked={selected === answer.id} name={`new-${question.id}`} onChange={() => onSelect(answer.id)} type="radio" />
        <span>{answer.label}</span>
      </label>)}
    </div>
  </fieldset>;
}
