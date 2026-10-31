import { beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { api } from "../src/api/client";
import { LandingPage, QuizPage, ResultsPage } from "../src/pages/QuizPages";
import { clearSavedQuiz, readSavedQuiz, saveQuiz, QUIZ_STORAGE_KEY } from "../src/quizStorage";
import { safeNextPath } from "../src/auth/nextPath";

vi.mock("../src/api/client", () => ({ api: { quiz: vi.fn(), quizRecommendations: vi.fn() } }));
const authState = vi.hoisted(() => ({ mature: false }));
vi.mock("../src/auth/useAuth", () => ({ useAuth: () => ({ mature: authState.mature }) }));
const questions = [
  { id: "mood", label: "What mood?", answers: [{ id: "cozy", label: "Cozy" }, { id: "epic", label: "Epic" }] },
  { id: "tone", label: "Which tone?", answers: [{ id: "dark", label: "Dark" }, { id: "hopeful", label: "Hopeful" }] },
];
const rec = { id: 3, title: "Test Anime", coverImage: "https://img.test/cover.jpg", format: "TV", year: 2024, score: 80, reason: "Because of your quiz answers" };
function renderRoutes(path: string, start: React.ReactNode) {
  return render(<MemoryRouter initialEntries={[path]}><Routes><Route path="/" element={<LandingPage />} /><Route path="/quiz" element={<QuizPage />} /><Route path="/results" element={<ResultsPage />} /><Route path="*" element={start} /></Routes></MemoryRouter>);
}
describe("Phase 5 quiz flow", () => {
  beforeEach(() => { authState.mature = false; localStorage.clear(); clearSavedQuiz(); vi.clearAllMocks(); vi.mocked(api.quiz).mockResolvedValue(questions); vi.mocked(api.quizRecommendations).mockResolvedValue({ results: [rec], quizVecStored: false }); });
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
  it("redirects / to results for saved results and /results to quiz without saved answers", async () => {
    saveQuiz({ answers: { mood: "cozy" }, results: [rec], includeMature: false });
    renderRoutes("/", <p>Elsewhere</p>);
    expect(await screen.findByText("Recommendations based on your answers")).toBeTruthy();
    clearSavedQuiz();
    renderRoutes("/results", <p>Quiz route</p>);
    expect(await screen.findByRole("heading", { name: "What mood?" })).toBeTruthy();
  });
  it("reruns recommendations if the mature setting changes on results and Start over clears saved state", async () => {
    saveQuiz({ answers: { mood: "cozy" }, results: [rec], includeMature: false });
    const route = (mature: boolean) => <MemoryRouter initialEntries={["/results"]}><ResultsPage key={String(mature)} /></MemoryRouter>;
    const view = render(route(false));
    authState.mature = true; view.rerender(route(true));
    await waitFor(() => expect(api.quizRecommendations).toHaveBeenCalledWith({ mood: "cozy" }, true));
    fireEvent.click(screen.getByRole("link", { name: "Start over" }));
    expect(readSavedQuiz()).toBeNull();
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
