import { useEffect, useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { api } from "../api/client";
import type { QuizQuestion } from "../api/types";
import { RecommendationCard } from "../components/RecommendationCard";
import { PosterGrid } from "../components/PosterGrid";
import { PosterSkeleton } from "../components/RequestStates";
import { useAuth } from "../auth/useAuth";
import { Check, CircleAlert, Clapperboard, ListChecks, Sparkles } from "lucide-react";
import { clearSavedQuiz, readSavedQuiz, saveQuiz } from "../quizStorage";

export function LandingPage() {
  const saved = readSavedQuiz();
  if (saved) return <Navigate to="/results" replace />;
  return <section className="landing-page">
    <div className="hero-badge"><Sparkles aria-hidden="true" size={14} /> Quiz-based recommendations</div>
    <h1 className="hero-title"><span>Ani</span><span className="wordmark-accent">Match</span></h1>
    <p>AniMatch recommends anime based on your quiz answers. The quiz takes about a minute.</p>
    <div className="hero-actions"><Link className="primary-action" to="/quiz">Start quiz</Link><Link className="secondary-action" to="/browse">Skip to Browse</Link></div>
    <div className="how-it-works" aria-label="How it works">
      <article className="how-step"><span className="how-step-icon"><ListChecks aria-hidden="true" size={17} /></span><div><h2>Take the quiz</h2><p>About a minute</p></div></article>
      <article className="how-step"><span className="how-step-icon"><Clapperboard aria-hidden="true" size={17} /></span><div><h2>Get matches</h2><p>Anime that fit your answers</p></div></article>
      <article className="how-step"><span className="how-step-icon"><Check aria-hidden="true" size={17} /></span><div><h2>See why</h2><p>Every match explains itself</p></div></article>
    </div>
  </section>;
}

export function QuizPage() {
  const [questions, setQuestions] = useState<QuizQuestion[] | null>(null);
  const [error, setError] = useState(false);
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [selectedMany, setSelectedMany] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(false);
  const { mature } = useAuth(); const navigate = useNavigate();
  useEffect(() => {
    const current = questions?.[step];
    const isMultiple = ["multi", "multiple", "multi-select", "multiselect"].includes(current?.type?.toLowerCase() ?? "");
    setSelectedMany(isMultiple && current ? (answers[current.id]?.split(",").filter(Boolean) ?? []) : []);
  }, [answers, questions, step]);
  async function load() { setError(false); try { setQuestions(await api.quiz()); } catch { setError(true); } }
  useEffect(() => { void load(); }, []);
  async function submit(currentAnswers = answers) {
    setSubmitting(true); setSubmitError(false);
    try {
      const response = await api.quizRecommendations(currentAnswers, mature);
      saveQuiz({ answers: currentAnswers, results: response.results, includeMature: mature });
      navigate("/results", { replace: true });
    } catch { setSubmitError(true); } finally { setSubmitting(false); }
  }
  if (error) return <section className="quiz-page"><h1>Quiz</h1><div className="status-box status-error" role="alert"><CircleAlert aria-hidden="true" /><p><strong>Could not load the quiz.</strong></p><button className="text-button" onClick={() => void load()}>Retry</button></div></section>;
  if (!questions) return <section className="quiz-page"><h1>Quiz</h1><p>Loading questions…</p></section>;
  if (!questions.length) return <section className="quiz-page"><h1>Quiz</h1><p>No quiz questions are available.</p></section>;
  const question = questions[step]; const multiple = ["multi", "multiple", "multi-select", "multiselect"].includes(question.type?.toLowerCase() ?? "");
  function choose(id: string) {
    if (multiple) { setSelectedMany((old) => old.includes(id) ? old.filter((answer) => answer !== id) : [...old, id]); return; }
    const updated = { ...answers, [question.id]: id }; setAnswers(updated);
    if (step < questions!.length - 1) setStep(step + 1); else void submit(updated);
  }
  function continueMany() {
    const updated = { ...answers, [question.id]: selectedMany.join(",") }; setAnswers(updated); setSelectedMany([]);
    if (step < questions!.length - 1) setStep(step + 1); else void submit(updated);
  }
  return <section className="quiz-page"><h1>Quiz</h1><div className="quiz-card"><p className="quiz-progress">Question {step + 1} of {questions.length}</p><div className="quiz-progress-track" role="progressbar" aria-valuenow={step + 1} aria-valuemin={1} aria-valuemax={questions.length}><span style={{ width: `${((step + 1) / questions.length) * 100}%` }} /></div><h2>{question.label}</h2>
    <fieldset className="quiz-options"><legend className="sr-only">{question.label}</legend>{question.answers.map((answer) => <label className="quiz-option" key={answer.id}><input type={multiple ? "checkbox" : "radio"} name={question.id} checked={multiple ? selectedMany.includes(answer.id) : answers[question.id] === answer.id} onChange={() => choose(answer.id)} /><span>{answer.label}</span></label>)}</fieldset>
    <div className="quiz-actions"><button className="text-button" disabled={step === 0 || submitting} onClick={() => { setStep(step - 1); setSelectedMany([]); }}>Back</button>{multiple && <button className="primary-action" disabled={!selectedMany.length || submitting} onClick={continueMany}>Continue</button>}</div>
    {submitting && <div className="quiz-loading" aria-live="polite"><p>Finding recommendations…</p><PosterSkeleton count={4} /></div>}
    {submitError && <div className="status-box status-error quiz-error" role="alert"><CircleAlert aria-hidden="true" /><p>Recommendations could not be loaded. Your answers are still here.</p><button className="text-button" onClick={() => void submit()}>Retry</button></div>}
  </div></section>;
}

export function ResultsPage() {
  const [saved, setSaved] = useState(readSavedQuiz);
  const [error, setError] = useState(false); const [refreshing, setRefreshing] = useState(false); const { mature } = useAuth();
  useEffect(() => {
    if (!saved?.answers || !saved.results) return;
    if (saved.includeMature === mature) return;
    let active = true; setError(false); setRefreshing(true);
    void api.quizRecommendations(saved.answers, mature).then((response) => {
      if (!active) return; const updated = { ...saved, results: response.results, includeMature: mature }; saveQuiz(updated); setSaved(updated);
    }).catch(() => { if (active) setError(true); }).finally(() => { if (active) setRefreshing(false); });
    return () => { active = false; };
  }, [mature, saved]);
  if (!saved) return <Navigate to="/quiz" replace />;
  function startOver() { clearSavedQuiz(); setSaved(null); }
  if (error) return <section className="browse-page"><h1 className="page-title">Recommendations</h1><div className="status-box status-error" role="alert"><CircleAlert aria-hidden="true" /><p>Could not update recommendations for this content setting.</p><button className="text-button" onClick={() => { setSaved({ ...saved, includeMature: !mature }); }}>Retry</button></div></section>;
  return <section className="browse-page results-page"><h1 className="page-title">Recommendations based on your answers</h1><div className="results-actions"><Link className="text-button" to="/quiz">Retake quiz</Link><Link className="quiet-link-button" to="/quiz" onClick={startOver}>Start over</Link></div>{refreshing ? <><p aria-live="polite">Updating recommendations…</p><PosterSkeleton count={4} /></> : <>{saved.results.length < 10 && <p className="result-count">Fewer recommendations were available for these answers.</p>}
    {!saved.results.length ? <p>No recommendations were found. Retake the quiz to try different answers.</p> : <PosterGrid label="Quiz recommendations">{saved.results.map((result) => <RecommendationCard key={result.id} recommendation={result} />)}</PosterGrid>}
    </>}<p className="results-account">Create an account to keep these. <Link to="/register?next=/results">Create an account</Link></p>
  </section>;
}
