import { beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { api } from "../src/api/client";
import type { AnimeCardData } from "../src/api/types";
import { Navbar } from "../src/components/Navbar";
import { LandingPage, QuizPage, ResultsPage } from "../src/pages/QuizPages";
import { clearSavedQuiz, readQuizDraft, readSavedQuiz, saveQuiz, saveQuizDraft, QUIZ_STORAGE_KEY } from "../src/quizStorage";
import { safeNextPath } from "../src/auth/nextPath";

vi.mock("../src/api/client", () => ({ api: { anime: vi.fn(), quiz: vi.fn(), quizRecommendations: vi.fn(), startRecommendations: vi.fn() } }));
const authState = vi.hoisted(() => ({ mature: false }));
vi.mock("../src/auth/useAuth", () => ({ useAuth: () => ({ mature: authState.mature }) }));
const questions = [
  { id: "mood", label: "What mood?", answers: [{ id: "cozy", label: "Cozy" }, { id: "epic", label: "Epic" }] },
  { id: "tone", label: "Which tone?", answers: [{ id: "dark", label: "Dark" }, { id: "hopeful", label: "Hopeful" }] },
];
const rec = { id: 3, title: "Test Anime", coverImage: "https://img.test/cover.jpg", format: "TV", year: 2024, score: 80, reason: "Because of your quiz answers" };
const animePick: AnimeCardData = { id: 8, title: "Picked Anime", coverImage: "https://img.test/picked.jpg", format: "TV", year: 2023 };
function LocationDisplay() { const location = useLocation(); return <output data-testid="current-location">{location.pathname}{location.search}</output>; }
function HistoryBackButton() { const navigate = useNavigate(); return <button onClick={() => navigate(-1)}>History back</button>; }
function renderRoutes(path: string, start: React.ReactNode) {
  return render(<MemoryRouter initialEntries={[path]}><Navbar /><LocationDisplay /><Routes><Route path="/" element={<LandingPage />} /><Route path="/quiz" element={<QuizPage />} /><Route path="/results" element={<ResultsPage />} /><Route path="*" element={start} /></Routes></MemoryRouter>);
}
async function selectAnimeTitle() {
  const input = screen.getByRole("combobox", { name: "Search anime titles" });
  fireEvent.focus(input);
  fireEvent.change(input, { target: { value: "Picked" } });
  fireEvent.click(await screen.findByRole("option", { name: /Picked Anime/ }));
}
describe("Phase 5 quiz flow", () => {
  beforeEach(() => { authState.mature = false; localStorage.clear(); clearSavedQuiz(); vi.clearAllMocks(); vi.mocked(api.anime).mockResolvedValue({ items: [animePick], pageInfo: { total: 1, currentPage: 1, lastPage: 1, perPage: 6, hasNextPage: false } }); vi.mocked(api.quiz).mockResolvedValue(questions); vi.mocked(api.quizRecommendations).mockResolvedValue({ results: [rec], quizVecStored: false }); vi.mocked(api.startRecommendations).mockResolvedValue([rec]); });
  it("places the home CTA above the steps and sends new visitors to the quiz", async () => {
    const view = renderRoutes("/", <QuizPage />);
    expect(screen.getByRole("link", { name: "Find my anime" })).toBeTruthy();
    expect(view.container.querySelector(".recommendation-card")).toBeNull();
    fireEvent.click(screen.getByRole("link", { name: "Find my anime" }));
    expect(await screen.findByRole("heading", { name: "What mood?" })).toBeTruthy();
  });
  it("shows the title alternative on question one and preserves both choices when switching", async () => {
    renderRoutes("/quiz", <QuizPage />);
    expect(await screen.findByRole("heading", { name: "What mood?" })).toBeTruthy();
    expect(screen.getByRole("separator", { name: "Or choose another way to get recommendations" })).toHaveTextContent("or");
    expect(screen.getByRole("button", { name: "Name anime you like instead" })).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Back" })).toBeNull();
    fireEvent.click(screen.getByLabelText("Cozy"));
    expect(await screen.findByRole("heading", { name: "Which tone?" })).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Name anime you like instead" })).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Back" }));
    expect(await screen.findByRole("heading", { name: "What mood?" })).toBeTruthy();
    expect((screen.getByLabelText("Cozy") as HTMLInputElement).checked).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: "Name anime you like instead" }));
    expect(screen.getByTestId("current-location")).toHaveTextContent("/quiz?mode=titles");
    const pickerHeading = screen.getByRole("heading", { name: "Name anime you like" });
    expect(screen.queryByRole("heading", { name: "Quiz" })).toBeNull();
    expect(document.activeElement).toBe(pickerHeading);
    expect(screen.getByRole("button", { name: "Take the quiz instead" })).toBeTruthy();
    await selectAnimeTitle();
    expect(screen.getByText("Picked Anime")).toBeTruthy();

    expect(screen.queryByRole("link", { name: "Retake the quiz" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Take the quiz instead" }));
    expect(screen.getByTestId("current-location")).toHaveTextContent("/quiz");
    expect(screen.getByRole("heading", { name: "What mood?" })).toBeTruthy();
    expect((screen.getByLabelText("Cozy") as HTMLInputElement).checked).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: "Name anime you like instead" }));
    expect(screen.getByText("Picked Anime")).toBeTruthy();
  });
  it("restores title mode and picks from storage on direct load; history Back returns home", async () => {
    saveQuizDraft({ answers: { mood: "epic" }, step: 0, selectedMany: [], pickedTitles: [animePick] });
    render(<MemoryRouter initialEntries={["/", "/quiz?mode=titles"]} initialIndex={1}>
      <Navbar /><LocationDisplay /><HistoryBackButton />
      <Routes><Route path="/" element={<LandingPage />} /><Route path="/quiz" element={<QuizPage />} /></Routes>
    </MemoryRouter>);
    expect(await screen.findByRole("heading", { name: "Name anime you like" })).toBeTruthy();
    expect(screen.getByText("Picked Anime")).toBeTruthy();
    expect(screen.getByTestId("current-location")).toHaveTextContent("/quiz?mode=titles");
    expect(readQuizDraft()?.answers).toEqual({ mood: "epic" });
    fireEvent.click(screen.getByRole("button", { name: "History back" }));
    expect(await screen.findByRole("link", { name: "Find my anime" })).toBeTruthy();
  });
  it("submits selected answers and advances; Back returns to prior answer", async () => {
    renderRoutes("/quiz", <QuizPage />);
    expect(await screen.findByRole("heading", { name: "What mood?" })).toBeTruthy();
    fireEvent.click(screen.getByLabelText("Cozy"));
    expect(await screen.findByRole("heading", { name: "Which tone?" })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Back" }));
    expect(await screen.findByRole("heading", { name: "What mood?" })).toBeTruthy();
    expect((screen.getByLabelText("Cozy") as HTMLInputElement).checked).toBe(true);
    fireEvent.click(screen.getByLabelText("Epic")); fireEvent.click(screen.getByLabelText("Dark"));
    await waitFor(() => expect(api.quizRecommendations).toHaveBeenCalledWith({ mood: "epic", tone: "dark" }, false));
    expect(readSavedQuiz()?.answers).toEqual({ mood: "epic", tone: "dark" });
  });
  it("renders API reason text and retries without losing selected answers", async () => {
    vi.mocked(api.quizRecommendations).mockRejectedValueOnce(new Error("offline"));
    renderRoutes("/quiz", <QuizPage />);
    fireEvent.click(await screen.findByLabelText("Cozy")); fireEvent.click(await screen.findByLabelText("Dark"));
    fireEvent.click(await screen.findByRole("button", { name: "Retry" }));
    await waitFor(() => expect(api.quizRecommendations).toHaveBeenLastCalledWith({ mood: "cozy", tone: "dark" }, false));
    saveQuiz({ answers: { mood: "cozy" }, results: [rec], includeMature: false });
    cleanup();
    renderRoutes("/results", <ResultsPage />);
    expect(await screen.findByText("Because of your quiz answers")).toBeTruthy();
  });
  it("refreshes saved recommendations once when legacy results have no covers", async () => {
    vi.mocked(api.quizRecommendations).mockReset().mockResolvedValue({ results: [rec], quizVecStored: false });
    saveQuiz({ answers: { mood: "cozy" }, results: [{ ...rec, coverImage: null }], includeMature: false });
    renderRoutes("/results", <QuizPage />);
    await waitFor(() => expect(api.quizRecommendations).toHaveBeenCalledWith({ mood: "cozy" }, false));
    const poster = await screen.findByAltText("Test Anime", {}, { timeout: 5000 });
    await waitFor(() => expect(poster).toHaveAttribute("src", "https://img.test/cover.jpg"));
    expect(api.quizRecommendations).toHaveBeenCalledTimes(1);
  });
  it("redirects / to results for saved results and /results to quiz without saved answers", async () => {
    saveQuiz({ answers: { mood: "cozy" }, results: [rec], includeMature: false });
    renderRoutes("/", <p>Elsewhere</p>);
    expect(await screen.findByText("Recommendations based on your answers")).toBeTruthy();
    clearSavedQuiz();
    renderRoutes("/results", <p>Quiz route</p>);
    expect(await screen.findByRole("heading", { name: "What mood?" })).toBeTruthy();
  });
  it("logo navigates home even when results are saved", async () => {
    saveQuiz({ answers: { mood: "cozy" }, results: [rec], includeMature: false });
    renderRoutes("/results", <p>Elsewhere</p>);
    fireEvent.click(screen.getByRole("link", { name: "AniMatch home" }));
    expect(screen.getByRole("link", { name: "Find my anime" })).toBeTruthy();
  });
  it("shows the similar-anime search in the results header and opens similar results for the selected anime", async () => {
    saveQuiz({ answers: { mood: "cozy" }, results: [rec], includeMature: false });
    renderRoutes("/results", <p>Anime detail destination</p>);
    const input = screen.getByRole("combobox", { name: "Search anime similar to" });
    expect(input).toHaveAttribute("placeholder", "Search anime similar to…");
    fireEvent.focus(input);
    fireEvent.change(input, { target: { value: "Picked" } });
    expect(await screen.findByRole("option", { name: /Picked Anime/ })).toBeTruthy();
    expect(api.anime).toHaveBeenLastCalledWith(
      { q: "Picked", page: 1, pageSize: 6, includeMature: false },
      expect.any(AbortSignal),
    );
    fireEvent.click(screen.getByRole("option", { name: /Picked Anime/ }));
    expect(screen.getByTestId("current-location")).toHaveTextContent("/similar/8");
  });
  it("reruns recommendations if the mature setting changes on results and has no start over link", async () => {
    saveQuiz({ answers: { mood: "cozy" }, results: [rec], includeMature: false });
    const route = (mature: boolean) => <MemoryRouter initialEntries={["/results"]}><ResultsPage key={String(mature)} /></MemoryRouter>;
    const view = render(route(false));
    authState.mature = true; view.rerender(route(true));
    await waitFor(() => expect(api.quizRecommendations).toHaveBeenCalledWith({ mood: "cozy" }, true));
    expect(screen.queryByRole("link", { name: "Start over" })).toBeNull();
    expect(readSavedQuiz()?.answers).toEqual({ mood: "cozy" });
  });
  it("sends current includeMature on each recommendation request", async () => {
    renderRoutes("/quiz", <QuizPage />);
    fireEvent.click(await screen.findByLabelText("Cozy")); fireEvent.click(await screen.findByLabelText("Dark"));
    await waitFor(() => expect(api.quizRecommendations).toHaveBeenCalledWith({ mood: "cozy", tone: "dark" }, false));
  });
});

describe("saved quiz storage and redirects", () => {
  beforeEach(() => { localStorage.clear(); clearSavedQuiz(); });
  it("saves/restores versioned state and falls back when storage throws", () => {
    const saved = { answers: { mood: "cozy" }, results: [rec], includeMature: true };
    expect(saveQuiz(saved)).toBe(true); expect(localStorage.getItem(QUIZ_STORAGE_KEY)).toBeTruthy(); expect(readSavedQuiz()).toEqual(saved);
    const get = vi.spyOn(localStorage, "getItem").mockImplementation(() => { throw new Error("blocked"); });
    expect(readSavedQuiz()).toEqual(saved); get.mockRestore();
    const set = vi.spyOn(localStorage, "setItem").mockImplementation(() => { throw new Error("blocked"); });
    expect(saveQuiz(saved)).toBe(false); set.mockRestore(); expect(readSavedQuiz()).toEqual(saved); clearSavedQuiz();
  });
  it("rejects absolute and protocol-relative next values", () => {
    expect(safeNextPath("/results")).toBe("/results");
    expect(safeNextPath("https://evil.test/")).toBe("/browse");
    expect(safeNextPath("//evil.test/")).toBe("/browse");
  });
});
