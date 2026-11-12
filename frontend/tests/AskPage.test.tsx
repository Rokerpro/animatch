import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api, ApiError, apiDetailMessage } from "../src/api/client";
import { useAuth } from "../src/auth/useAuth";
import { AskPage } from "../src/pages/AskPage";
import { ForYouPage } from "../src/pages/ForYouPage";
import * as quizStorage from "../src/quizStorage";
import * as startStorage from "../src/startStorage";

vi.mock("../src/auth/useAuth", () => ({ useAuth: vi.fn() }));
vi.mock("../src/api/client", async (load) => {
  const actual = await load<typeof import("../src/api/client")>();
  return {
    ...actual,
    api: {
      ...actual.api,
      features: vi.fn(), askRecommendations: vi.fn(), myRecommendations: vi.fn(),
      listStatuses: vi.fn(), detail: vi.fn(), saveTasteProfile: vi.fn(),
    },
  };
});

const user = { id: 1, email: "ask@example.com", display_name: "A", show_mature: false, created_at: "today" };
const response = {
  results: [{ id: 20, title: "Found Anime", coverImage: "https://image.test/20.jpg", reason: "Because of mystery." }],
  understood: {
    quiz_answers: [{ question_id: "mood", question_label: "Mood", answer_id: "cozy", answer_label: "Cozy" }],
    matched_seed_titles: [{ id: 21, title: "Seed Anime" }],
    unmatched_seed_titles: ["Missing Anime"],
  },
  message: null,
};

function Location() {
  const location = useLocation();
  return <output data-testid="location">{location.pathname}{location.search}</output>;
}

function renderAt(path = "/ask") {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return { client, ...render(<QueryClientProvider client={client}><MemoryRouter initialEntries={[path]}><Location /><Routes>
    <Route path="/ask" element={<AskPage />} /><Route path="/for-you" element={<ForYouPage />} />
    <Route path="/login" element={<p>Login screen</p>} /><Route path="/new" element={<p>New quiz</p>} />
    <Route path="/anime/:id" element={<p>Anime detail</p>} />
  </Routes></MemoryRouter></QueryClientProvider>) };
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(useAuth).mockReturnValue({ user, mature: false, authLoading: false, refresh: vi.fn(), setMature: vi.fn(), signOut: vi.fn() });
  vi.mocked(api.features).mockResolvedValue({ natural_language: true });
  vi.mocked(api.askRecommendations).mockResolvedValue(response);
  vi.mocked(api.myRecommendations).mockResolvedValue([]);
  vi.mocked(api.listStatuses).mockResolvedValue({ items: [] });
  vi.mocked(api.detail).mockResolvedValue({ id: 20, title: "Found Anime", coverImage: "https://image.test/20.jpg" });
});

describe("natural language recommendations", () => {
  it("redirects guests to login with next=/ask", async () => {
    vi.mocked(useAuth).mockReturnValue({ user: null, mature: false, authLoading: false, refresh: vi.fn(), setMature: vi.fn(), signOut: vi.fn() });
    renderAt();
    expect(await screen.findByText("Login screen")).toBeInTheDocument();
    expect(screen.getByTestId("location")).toHaveTextContent("/login?next=%2Fask");
  });

  it.each(["false", "failure"])('hides the For you entry and shows disabled page when features are %s', async (setting) => {
    if (setting === "false") vi.mocked(api.features).mockResolvedValue({ natural_language: false });
    else vi.mocked(api.features).mockRejectedValue(new Error("offline"));
    const view = renderAt("/for-you");
    await screen.findByText(/No recommendations yet/);
    expect(screen.queryByRole("link", { name: "Describe what you want" })).not.toBeInTheDocument();
    view.unmount();
    renderAt("/ask");
    expect(await screen.findByText("This feature is not enabled on this server.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Use Find something new" })).toHaveAttribute("href", "/new");
  });

  it("shows the For you entry when enabled", async () => {
    renderAt("/for-you");
    const links = await screen.findAllByRole("link", { name: "Describe what you want" });
    expect(links).toHaveLength(2);
    expect(links.every((link) => link.getAttribute("href") === "/ask")).toBe(true);
  });

  it("shows the live counter, disables invalid input, supports shortcut, and examples only fill", async () => {
    renderAt();
    const input = await screen.findByRole("textbox", { name: "What are you in the mood to watch?" });
    const submit = screen.getByRole("button", { name: "Get recommendations" });
    expect(screen.getByText("0 / 300 characters")).toBeInTheDocument();
    expect(submit).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: /cozy fantasy/ }));
    expect(input).toHaveValue("I want a cozy fantasy with a hopeful ending.");
    expect(api.askRecommendations).not.toHaveBeenCalled();
    fireEvent.change(input, { target: { value: "x".repeat(301) } });
    expect(screen.getByText("301 / 300 characters")).toBeInTheDocument();
    expect(submit).toBeDisabled();
    fireEvent.change(input, { target: { value: "  a thoughtful mystery  " } });
    fireEvent.keyDown(input, { key: "Enter", ctrlKey: true });
    expect(await screen.findByRole("heading", { name: "Here’s what I found" })).toBeInTheDocument();
    expect(api.askRecommendations).toHaveBeenCalledWith({ text: "a thoughtful mystery" }, expect.any(AbortSignal));
  });

  it("submits exactly trimmed text and renders results, understood chips, and edit keeps the request", async () => {
    renderAt();
    const input = await screen.findByRole("textbox", { name: "What are you in the mood to watch?" });
    fireEvent.change(input, { target: { value: "  cozy adventure  " } });
    fireEvent.click(screen.getByRole("button", { name: "Get recommendations" }));
    expect(await screen.findByText("Because of mystery.")).toBeInTheDocument();
    expect(screen.getByText("Mood: Cozy")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Seed Anime" })).toHaveAttribute("href", "/anime/21");
    expect(screen.getByText("Couldn't find: Missing Anime")).toBeInTheDocument();
    expect(api.askRecommendations).toHaveBeenCalledWith({ text: "cozy adventure" }, expect.any(AbortSignal));
    fireEvent.click(screen.getByRole("button", { name: "Edit request" }));
    expect(await screen.findByRole("textbox", { name: "What are you in the mood to watch?" })).toHaveValue("  cozy adventure  ");
  });

  it("shows the API message and tip for empty results", async () => {
    vi.mocked(api.askRecommendations).mockResolvedValueOnce({ ...response, results: [], message: "No matches this time." });
    renderAt();
    fireEvent.change(await screen.findByRole("textbox"), { target: { value: "quiet mood" } });
    fireEvent.click(screen.getByRole("button", { name: "Get recommendations" }));
    expect(await screen.findByText("No matches this time.")).toBeInTheDocument();
    expect(screen.getByText(/mentioning a mood or a few titles/)).toBeInTheDocument();
  });

  it.each([
    [429, "Daily request limit reached", undefined, "string"],
    [429, "Daily request limit reached", undefined, "list"],
    [503, "The assistant is unavailable right now. You can use the normal quiz instead.", "normal quiz", "string"],
    [503, "The assistant is unavailable right now. You can use the normal quiz instead.", "normal quiz", "list"],
    [401, "Please sign in", undefined, "string"],
    [401, "Please sign in", undefined, "list"],
    [422, "Unsupported request", undefined, "string"],
    [422, "Unsupported request", undefined, "list"],
  ])("shows inline status %s %s detail errors", async (status, message, linkText, shape) => {
    const detail = shape === "list" ? [{ loc: ["body", "text"], msg: String(message), type: "value_error" }] : message;
    vi.mocked(api.askRecommendations).mockRejectedValueOnce(new ApiError(apiDetailMessage(detail), status));
    renderAt();
    fireEvent.change(await screen.findByRole("textbox"), { target: { value: "some request" } });
    fireEvent.click(screen.getByRole("button", { name: "Get recommendations" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(message as string);
    if (linkText) expect(screen.getByRole("link", { name: "Try the normal quiz" })).toHaveAttribute("href", "/new");
  });

  it("refreshes features for an unconfigured server", async () => {
    vi.mocked(api.askRecommendations).mockRejectedValueOnce(new ApiError("Natural language is not configured", 503, "natural_language_unavailable"));
    renderAt();
    fireEvent.change(await screen.findByRole("textbox"), { target: { value: "a" } });
    fireEvent.click(screen.getByRole("button", { name: "Get recommendations" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("not enabled");
    expect(screen.getByRole("button", { name: "Refresh availability" })).toBeInTheDocument();
  });

  it("does not write request text to storage, the URL, console, saved quiz, or taste profile", async () => {
    const text = "private text unique phrase";
    const spies = [
      vi.spyOn(quizStorage, "readQuizDraft"), vi.spyOn(quizStorage, "saveQuizDraft"), vi.spyOn(quizStorage, "clearQuizDraft"),
      vi.spyOn(quizStorage, "readSavedQuiz"), vi.spyOn(quizStorage, "saveQuiz"), vi.spyOn(quizStorage, "clearSavedQuiz"),
      vi.spyOn(startStorage, "readSavedStart"), vi.spyOn(startStorage, "saveStart"), vi.spyOn(startStorage, "clearSavedStart"),
      vi.spyOn(console, "log"), vi.spyOn(console, "info"), vi.spyOn(console, "warn"), vi.spyOn(console, "error"),
    ];
    renderAt();
    fireEvent.change(await screen.findByRole("textbox"), { target: { value: text } });
    fireEvent.click(screen.getByRole("button", { name: "Get recommendations" }));
    await screen.findByText("Because of mystery.");
    await waitFor(() => expect(screen.getByTestId("location")).toHaveTextContent("/ask"));
    expect(spies.every((spy) => spy.mock.calls.length === 0)).toBe(true);
    expect(api.saveTasteProfile).not.toHaveBeenCalled();
    expect(window.location.href).not.toContain(encodeURIComponent(text));
  });
});
