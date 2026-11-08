import { useEffect, useRef, useState, type FormEvent } from "react";
import { Link, Navigate, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { ApiError, api, getErrorMessage } from "../api/client";
import type { QuizQuestion } from "../api/types";
import type { AnimeCardData } from "../api/types";
import { RecommendationCard } from "../components/RecommendationCard";
import { PosterGrid } from "../components/PosterGrid";
import { PosterSkeleton } from "../components/RequestStates";
import { TitleAutocomplete } from "../components/TitleAutocomplete";
import { useAuth } from "../auth/useAuth";
import { Check, CircleAlert, Clapperboard, ListChecks, Sparkles, X } from "lucide-react";
import { clearQuizDraft, clearSavedQuiz, markQuizProfileSaved, readQuizDraft, readSavedQuiz, saveQuiz, saveQuizDraft } from "../quizStorage";
import { clearSavedStart, markStartProfileSaved, readSavedStart, saveStart } from "../startStorage";
import { useOptionalToast } from "../components/useToast";
import { StartResultsPage } from "./StartResultsPage";

const FRANCHISE_VALIDATION_MESSAGE =
  "These titles include multiple seasons from the same series. Choose titles from at least 3 different series.";

function startRequestErrorMessage(error: unknown): string {
  if (!(error instanceof ApiError)) {
    return "Could not get recommendations. Try again.";
  }
  if (
    error.status === 422 &&
    /different franchises?.*share a franchise|share a franchise.*different franchises?/i.test(
      error.message,
    )
  ) {
    return FRANCHISE_VALIDATION_MESSAGE;
  }
  return getErrorMessage(error, "Could not get recommendations. Try again.");
}

export function LandingPage() {
  const location = useLocation();
  const saved = readSavedQuiz() || readSavedStart();
  if (saved && !location.state?.showHome) return <Navigate to="/results" replace />;
  return <section className="landing-page">
    <div className="hero-badge"><Sparkles aria-hidden="true" size={14} /> Anime recommendations</div>
    <h1 className="hero-title"><span>Ani</span><span className="wordmark-accent">Match</span></h1>
    <p>Tell AniMatch what you enjoy in anime. It finds titles that fit your taste and explains why each one is a match.</p>
    <div className="hero-actions"><Link className="primary-action" to="/quiz">Find my anime</Link></div>
    <div className="how-it-works" aria-label="How it works">
      <article className="how-step"><span className="how-step-icon"><ListChecks aria-hidden="true" size={17} /></span><div><h2>Tell us what you like</h2><p>Take a quick quiz or name titles you enjoy</p></div></article>
      <article className="how-step"><span className="how-step-icon"><Clapperboard aria-hidden="true" size={17} /></span><div><h2>Get matches</h2><p>Anime that fit your answers</p></div></article>
      <article className="how-step"><span className="how-step-icon"><Check aria-hidden="true" size={17} /></span><div><h2>See why</h2><p>Every match explains itself</p></div></article>
    </div>
  </section>;
}

export function QuizPage() {
  const [questions, setQuestions] = useState<QuizQuestion[] | null>(null);
  const [error, setError] = useState(false);
  const [quizLoadMessage, setQuizLoadMessage] = useState("");
  const [draft] = useState(readQuizDraft);
  const [step, setStep] = useState(draft?.step ?? 0);
  const [answers, setAnswers] = useState<Record<string, string>>(draft?.answers ?? {});
  const [selectedMany, setSelectedMany] = useState<string[]>(draft?.selectedMany ?? []);
  const [pickedTitles, setPickedTitles] = useState<AnimeCardData[]>(draft?.pickedTitles ?? []);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(false);
  const [startError, setStartError] = useState("");
  const [startSubmitting, setStartSubmitting] = useState(false);
  const [searchParams, setSearchParams] = useSearchParams();
  const titleMode = searchParams.get("mode") === "titles";
  const { mature, user } = useAuth(); const navigate = useNavigate(); const { showToast } = useOptionalToast();
  const viewHeadingRef = useRef<HTMLHeadingElement>(null);
  const mountedViewRef = useRef(false);
  const [announcement, setAnnouncement] = useState("");
  useEffect(() => {
    saveQuizDraft({ answers, step, selectedMany, pickedTitles });
  }, [answers, step, selectedMany, pickedTitles]);
  useEffect(() => {
    const current = questions?.[step];
    const isMultiple = ["multi", "multiple", "multi-select", "multiselect"].includes(current?.type?.toLowerCase() ?? "");
    if (!isMultiple) {
      setSelectedMany([]);
      return;
    }
    const stored = current ? (answers[current.id]?.split(",").filter(Boolean) ?? []) : [];
    if (stored.length) setSelectedMany(stored);
  }, [answers, questions, step]);
  useEffect(() => {
    const initial = !mountedViewRef.current;
    mountedViewRef.current = true;
    if (initial && !titleMode) return;
    viewHeadingRef.current?.focus({ preventScroll: true });
    setAnnouncement(titleMode ? "Anime title picker opened." : "Quiz opened.");
  }, [titleMode]);
  function switchView(toTitles: boolean) {
    setSearchParams(toTitles ? { mode: "titles" } : {}, { replace: true });
  }
  async function load() {
    setError(false); setQuizLoadMessage("");
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 10_000);
    try { setQuestions(await api.quiz(controller.signal)); }
    catch (reason) {
      setError(true);
      setQuizLoadMessage(reason instanceof DOMException && reason.name === "AbortError"
        ? "The quiz request timed out. Check that the backend is running, then retry."
        : "Could not load the quiz. Check that the backend is running, then retry.");
    } finally { window.clearTimeout(timeout); }
  }
  useEffect(() => { void load(); }, []);
  async function submit(currentAnswers = answers) {
    setSubmitting(true); setSubmitError(false);
    try {
      const response = await api.quizRecommendations(currentAnswers, mature);
      clearSavedStart();
      saveQuiz({ answers: currentAnswers, results: response.results, includeMature: mature });
      if (user) {
        try { await api.saveTasteProfile({ quiz_answers: currentAnswers, liked_ids: [] }); markQuizProfileSaved(user.id); showToast("Saved your answers", "success"); }
        catch (reason) { showToast(getErrorMessage(reason, "Could not save your profile"), "error"); }
      }
      navigate("/results", { replace: true });
    } catch { setSubmitError(true); } finally { setSubmitting(false); }
  }
  async function getTitleRecommendations(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pickedTitles.length < 3 || pickedTitles.length > 5 || startSubmitting) return;
    setStartSubmitting(true);
    setStartError("");
    try {
      const likedIds = pickedTitles.map((anime) => anime.id);
      const results = await api.startRecommendations(likedIds, mature);
      saveStart({ liked_ids: likedIds, results, include_mature: mature });
      clearSavedQuiz();
      clearQuizDraft();
      if (user) {
        try { await api.saveTasteProfile({ quiz_answers: null, liked_ids: likedIds }); markStartProfileSaved(user.id); showToast("Saved your answers", "success"); }
        catch (reason) { showToast(getErrorMessage(reason, "Could not save your profile"), "error"); }
      }
      navigate("/results", { replace: true });
    } catch (reason: unknown) {
      setStartError(startRequestErrorMessage(reason));
    } finally {
      setStartSubmitting(false);
    }
  }
  function addTitle(anime: AnimeCardData) {
    setPickedTitles((current) => current.length < 5 && !current.some((item) => item.id === anime.id) ? [...current, anime] : current);
    setStartError("");
  }
  function removeTitle(id: number) {
    setPickedTitles((current) => current.filter((anime) => anime.id !== id));
    setStartError("");
  }
  if (error) return <section className="quiz-page"><h1>Quiz</h1><div className="status-box status-error" role="alert"><CircleAlert aria-hidden="true" /><p>{quizLoadMessage}</p><button className="text-button" onClick={() => void load()}>Retry</button></div></section>;
  if (!questions) return <section className="quiz-page"><h1>Quiz</h1><p>Loading questions…</p></section>;
  if (!questions.length) return <section className="quiz-page"><h1>Quiz</h1><p>No quiz questions are available.</p></section>;
  const question = questions[Math.min(step, questions.length - 1)]; const multiple = ["multi", "multiple", "multi-select", "multiselect"].includes(question.type?.toLowerCase() ?? "");
  function choose(id: string) {
    if (multiple) { setSelectedMany((old) => old.includes(id) ? old.filter((answer) => answer !== id) : [...old, id]); return; }
    const updated = { ...answers, [question.id]: id }; setAnswers(updated);
    if (step < questions!.length - 1) setStep(step + 1); else void submit(updated);
  }
  function continueMany() {
    const updated = { ...answers, [question.id]: selectedMany.join(",") }; setAnswers(updated); setSelectedMany([]);
    if (step < questions!.length - 1) setStep(step + 1); else void submit(updated);
  }
  return <section className="quiz-page">
    {!titleMode && <h1>Quiz</h1>}
    <p aria-live="polite" className="sr-only">{announcement}</p>
    {titleMode ? (
      <div className="quiz-card title-picker-view">
        <h1 className="title-picker-heading" ref={viewHeadingRef} tabIndex={-1}>Name anime you like</h1>
        <p className="title-picker-intro">Choose 3 to 5 titles you enjoy and we’ll find similar matches.</p>
        <form className="title-picker-form" onSubmit={getTitleRecommendations}>
          <TitleAutocomplete disabled={pickedTitles.length >= 5 || startSubmitting} includeMature={mature} onSelect={addTitle} selected={pickedTitles} />
          <div className="picked-title-header"><span>Picked titles</span><span aria-live="polite">{pickedTitles.length} of 3 minimum, 5 maximum</span></div>
          {pickedTitles.length ? <ul aria-label="Picked anime" className="picked-title-queue">{pickedTitles.map((anime) => <li className="picked-title-row" key={anime.id}>
            {anime.coverImage ? <img alt="" src={anime.coverImage} /> : <span aria-hidden="true" className="picked-title-cover-placeholder" />}
            <span className="picked-title-name">{anime.title}</span><button aria-label={`Remove ${anime.title}`} disabled={startSubmitting} onClick={() => removeTitle(anime.id)} type="button"><X aria-hidden="true" size={14} /></button>
          </li>)}</ul> : <p className="picked-title-empty">Your selected titles will appear here.</p>}
          {startError && <p className="start-submit-error" role="alert">{startError}</p>}
          <button className="primary-action get-recommendations-button" disabled={pickedTitles.length < 3 || startSubmitting} type="submit">{startSubmitting ? "Getting recommendations…" : "Get recommendations"}</button>
        </form>
        <button className="text-button take-quiz-instead" onClick={() => switchView(false)} type="button">Take the quiz instead</button>
      </div>
    ) : (
      <div className="quiz-card">
        <p className="quiz-progress">Question {step + 1} of {questions.length}</p>
        <div className="quiz-progress-track" role="progressbar" aria-valuenow={step + 1} aria-valuemin={1} aria-valuemax={questions.length}><span style={{ width: `${((step + 1) / questions.length) * 100}%` }} /></div>
        <h2 className="quiz-question-heading" ref={viewHeadingRef} tabIndex={-1}>{question.label}</h2>
        <fieldset className="quiz-options"><legend className="sr-only">{question.label}</legend>{question.answers.map((answer) => <label className="quiz-option" key={answer.id}><input type={multiple ? "checkbox" : "radio"} name={question.id} checked={multiple ? selectedMany.includes(answer.id) : answers[question.id] === answer.id} onChange={() => choose(answer.id)} /><span>{answer.label}</span></label>)}</fieldset>
        {step === 0 && <>
          <div aria-label="Or choose another way to get recommendations" className="quiz-alternative" role="separator"><span>or</span></div>
          <button className="secondary-action quiz-picker-switch" onClick={() => switchView(true)} type="button">Name anime you like instead</button>
        </>}
        <div className="quiz-actions">{step > 0 && <button className="text-button" disabled={submitting} onClick={() => {
          const previousStep = step - 1;
          const previousQuestion = questions[previousStep];
          const previousIsMultiple = ["multi", "multiple", "multi-select", "multiselect"].includes(previousQuestion?.type?.toLowerCase() ?? "");
          setSelectedMany(previousIsMultiple && previousQuestion ? (answers[previousQuestion.id]?.split(",").filter(Boolean) ?? []) : []);
          setStep(previousStep);
        }}>Back</button>}{multiple && <button className="primary-action" disabled={!selectedMany.length || submitting} onClick={continueMany}>Continue</button>}</div>
        {submitting && <div className="quiz-loading" aria-live="polite"><p>Finding recommendations…</p><PosterSkeleton count={4} /></div>}
        {submitError && <div className="status-box status-error quiz-error" role="alert"><CircleAlert aria-hidden="true" /><p>Recommendations could not be loaded. Your answers are still here.</p><button className="text-button" onClick={() => void submit()}>Retry</button></div>}
      </div>
    )}
  </section>;
}

export function ResultsPage() {
  if (readSavedStart()) return <StartResultsPage />;
  return <QuizResultsPage />;
}

function QuizResultsPage() {
  const [saved, setSaved] = useState(readSavedQuiz); const coverRefreshAttempted = useRef(false);
  const [error, setError] = useState(false); const [refreshing, setRefreshing] = useState(false); const { mature } = useAuth();
  useEffect(() => {
    if (!saved?.answers || !saved.results) return;
    const hasMissingCovers = saved.results.some((result) => !result.coverImage);
    if (saved.includeMature === mature && (!hasMissingCovers || coverRefreshAttempted.current)) return;
    let active = true; setError(false); setRefreshing(true);
    void api.quizRecommendations(saved.answers, mature).then((response) => {
      if (!active) return;
      if (hasMissingCovers) coverRefreshAttempted.current = true;
      const updated = { ...saved, results: response.results, includeMature: mature };
      saveQuiz(updated); setSaved(updated); setRefreshing(false);
    }).catch(() => {
      if (!active) return;
      if (hasMissingCovers) coverRefreshAttempted.current = true;
      setError(true); setRefreshing(false);
    });
    return () => { active = false; };
  }, [mature, saved]);
  if (!saved) return <Navigate to="/quiz" replace />;
  if (error) return <section className="browse-page"><h1 className="page-title">Recommendations</h1><div className="status-box status-error" role="alert"><CircleAlert aria-hidden="true" /><p>Could not update recommendations for this content setting.</p><button className="text-button" onClick={() => { setSaved({ ...saved, includeMature: !mature }); }}>Retry</button></div></section>;
  return <section className="browse-page results-page"><h1 className="page-title">Recommendations based on your answers</h1>{refreshing ? <><p aria-live="polite">Updating recommendations…</p><PosterSkeleton count={4} /></> : <>{saved.results.length < 10 && <p className="result-count">Fewer recommendations were available for these answers.</p>}
    {!saved.results.length ? <p>No recommendations were found. Retake the quiz to try different answers.</p> : <PosterGrid animeIds={saved.results.map((result) => result.id)} label="Quiz recommendations">{saved.results.map((result) => <RecommendationCard key={result.id} recommendation={result} />)}</PosterGrid>}
    </>}<p className="results-account">Create an account to keep these. <Link to="/register?next=/results">Create an account</Link></p>
  </section>;
}
