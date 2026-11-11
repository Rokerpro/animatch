import { fireEvent, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api, apiDetailMessage } from "../src/api/client";
import { useAuth } from "../src/auth/useAuth";
import * as quizStorage from "../src/quizStorage";
import * as startStorage from "../src/startStorage";
import { ForYouPage } from "../src/pages/ForYouPage";
import { NewPage } from "../src/pages/NewPage";

vi.mock("../src/auth/useAuth", () => ({ useAuth: vi.fn() }));
vi.mock("../src/api/client", async (load) => {
  const actual = await load<typeof import("../src/api/client")>();
  return {
    ...actual,
    api: {
      ...actual.api,
      quiz: vi.fn(),
      newRecommendations: vi.fn(),
      saveTasteProfile: vi.fn(),
      myRecommendations: vi.fn(),
      listStatuses: vi.fn(),
      detail: vi.fn(),
    },
  };
});

const signedInUser = { id: 8, email: "new@example.com", display_name: "N", show_mature: false, created_at: "today" };
const questions = [
  { id: "mood", label: "What mood are you in?", answers: [{ id: "epic", label: "Epic / action-packed" }] },
  { id: "pacing", label: "How do you like your story paced?", answers: [{ id: "fast", label: "Fast-paced" }] },
  { id: "length", label: "How long a series are you looking for?", answers: [{ id: "short", label: "Short" }] },
  { id: "era", label: "Any era preference?", answers: [{ id: "classic", label: "Classic" }] },
];
const recommendation = {
  id: 22,
  title: "A New Direction",
  coverImage: "https://image.test/22.jpg",
  reason: "Matches your tense preference; a different direction with Mystery.",
  similarity: 0.8,
  score: 84,
  format: "TV",
  year: 2022,
  episodes: 12,
};
const result = { results: [recommendation], mode: "novelty" as const };

function CurrentLocation() {
  const location = useLocation();
  return <output data-testid="location">{location.pathname}{location.search}</output>;
}

function renderRoute(path = "/new") {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(<QueryClientProvider client={client}><MemoryRouter initialEntries={[path]}><CurrentLocation /><Routes>
    <Route path="/new" element={<NewPage />} />
    <Route path="/for-you" element={<ForYouPage />} />
    <Route path="/login" element={<p>Login page</p>} />
    <Route path="/import" element={<p>Import page</p>} />
    <Route path="/browse" element={<p>Browse page</p>} />
  </Routes></MemoryRouter></QueryClientProvider>);
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(useAuth).mockReturnValue({ user: signedInUser, mature: false, authLoading: false, refresh: vi.fn(), setMature: vi.fn(), signOut: vi.fn() });
  vi.mocked(api.quiz).mockResolvedValue(questions);
  vi.mocked(api.newRecommendations).mockResolvedValue(result);
  vi.mocked(api.myRecommendations).mockResolvedValue([]);
  vi.mocked(api.listStatuses).mockResolvedValue({ items: [] });
  vi.mocked(api.detail).mockResolvedValue({ id: 22, title: recommendation.title, coverImage: recommendation.coverImage });
});

afterEach(() => vi.restoreAllMocks());

describe("Find something new", () => {
  it("redirects guests to login with next=/new and does not load quiz questions", async () => {
    vi.mocked(useAuth).mockReturnValue({ user: null, mature: false, authLoading: false, refresh: vi.fn(), setMature: vi.fn(), signOut: vi.fn() });
    renderRoute();
    expect(await screen.findByText("Login page")).toBeInTheDocument();
    expect(screen.getByTestId("location")).toHaveTextContent("/login?next=%2Fnew");
    expect(api.quiz).not.toHaveBeenCalled();
  });

  it("shows only mood, length, and era, with submit disabled until an answer is selected", async () => {
    renderRoute();
    expect(await screen.findByText("What mood are you in?")).toBeInTheDocument();
    expect(screen.queryByText("How do you like your story paced?")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Find recommendations" })).toBeDisabled();
    fireEvent.click(screen.getByLabelText("Epic / action-packed"));
    expect(screen.getByRole("button", { name: "Find recommendations" })).toBeEnabled();
  });

  it("sends exactly the selected answers and renders reasons with the existing card controls", async () => {
    renderRoute();
    await screen.findByText("What mood are you in?");
    fireEvent.click(screen.getByLabelText("Epic / action-packed"));
    fireEvent.click(screen.getByLabelText("Short"));
    fireEvent.click(screen.getByRole("button", { name: "Find recommendations" }));
    expect(await screen.findByText(recommendation.reason)).toBeInTheDocument();
    expect(api.newRecommendations).toHaveBeenCalledTimes(1);
    expect(api.newRecommendations).toHaveBeenCalledWith({
      quiz_answers: { mood: "epic", length: "short" },
    });
    expect(screen.getByRole("button", { name: "Add A New Direction to My list" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Start over" })).toBeInTheDocument();
  });

  it("shows the fallback notice and its import and browse links", async () => {
    vi.mocked(api.newRecommendations).mockResolvedValueOnce({ ...result, mode: "quiz_fallback" });
    renderRoute();
    await screen.findByText("What mood are you in?");
    fireEvent.click(screen.getByLabelText("Epic / action-packed"));
    fireEvent.click(screen.getByRole("button", { name: "Find recommendations" }));
    expect(await screen.findByText(/Your list is still empty/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Import from MyAnimeList" })).toHaveAttribute("href", "/import");
    expect(screen.getByRole("link", { name: "browse the catalog" })).toHaveAttribute("href", "/browse");
  });

  it("shows the novelty subtitle and empty result retry action", async () => {
    vi.mocked(api.newRecommendations).mockResolvedValueOnce({ results: [], mode: "novelty" });
    renderRoute();
    await screen.findByText("What mood are you in?");
    fireEvent.click(screen.getByLabelText("Epic / action-packed"));
    fireEvent.click(screen.getByRole("button", { name: "Find recommendations" }));
    expect(await screen.findByText("These picks sit outside your usual taste.")).toBeInTheDocument();
    expect(screen.getByText("No recommendations matched those answers.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Try different answers" }));
    expect(await screen.findByText("What mood are you in?")).toBeInTheDocument();
  });

  it.each([
    ["string detail", "A server validation message"],
    [
      "list detail",
      apiDetailMessage([{ loc: ["body", "quiz_answers"], msg: "Choose another answer", type: "value_error" }]),
    ],
  ])("shows inline errors from %s", async (_shape, message) => {
    vi.mocked(api.newRecommendations).mockRejectedValueOnce(new Error(message));
    renderRoute();
    await screen.findByText("What mood are you in?");
    fireEvent.click(screen.getByLabelText("Epic / action-packed"));
    fireEvent.click(screen.getByRole("button", { name: "Find recommendations" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(message);
  });

  it("never uses saved quiz storage or saves answers to the taste profile", async () => {
    const quizStorageSpies = [
      vi.spyOn(quizStorage, "readQuizDraft"), vi.spyOn(quizStorage, "saveQuizDraft"),
      vi.spyOn(quizStorage, "clearQuizDraft"), vi.spyOn(quizStorage, "readSavedQuiz"),
      vi.spyOn(quizStorage, "saveQuiz"), vi.spyOn(quizStorage, "clearSavedQuiz"),
    ];
    const startStorageSpies = [
      vi.spyOn(startStorage, "readSavedStart"), vi.spyOn(startStorage, "saveStart"),
      vi.spyOn(startStorage, "clearSavedStart"),
    ];
    renderRoute();
    await screen.findByText("What mood are you in?");
    fireEvent.click(screen.getByLabelText("Epic / action-packed"));
    fireEvent.click(screen.getByRole("button", { name: "Find recommendations" }));
    await screen.findByText(recommendation.reason);
    expect(quizStorageSpies.every((spy) => spy.mock.calls.length === 0)).toBe(true);
    expect(startStorageSpies.every((spy) => spy.mock.calls.length === 0)).toBe(true);
    expect(api.saveTasteProfile).not.toHaveBeenCalled();
  });

  it("shows Find something new in the For you header and empty state", async () => {
    renderRoute("/for-you");
    expect(await screen.findByText(/No recommendations yet/)).toBeInTheDocument();
    const links = screen.getAllByRole("link", { name: "Find something new" });
    expect(links).toHaveLength(2);
    expect(links.every((link) => link.getAttribute("href") === "/new")).toBe(true);
  });
});
