import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { ApiError, api } from "../src/api/client";
import type { AnimeCardData, Recommendation } from "../src/api/types";
import { TitleAutocomplete } from "../src/components/TitleAutocomplete";
import { LandingPage, QuizPage, ResultsPage } from "../src/pages/QuizPages";
import { clearSavedQuiz } from "../src/quizStorage";
import {
  clearSavedStart,
  readSavedStart,
  saveStart,
  START_STORAGE_KEY,
} from "../src/startStorage";

vi.mock("../src/api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../src/api/client")>();
  return {
    ...actual,
    api: {
      ...actual.api,
      anime: vi.fn(),
      quiz: vi.fn(),
      startRecommendations: vi.fn(),
    },
  };
});

const authState = vi.hoisted(() => ({ mature: false }));
vi.mock("../src/auth/useAuth", () => ({
  useAuth: () => ({ mature: authState.mature }),
}));

const anime: AnimeCardData[] = Array.from({ length: 6 }, (_, index) => ({
  id: index + 1,
  title: `Anime ${index + 1}`,
  titleRomaji: null,
  coverImage: `https://images.test/${index + 1}.jpg`,
  format: "TV",
  year: 2024,
}));
const recommendation: Recommendation = {
  id: 90,
  title: "Recommended Anime",
  coverImage: "https://images.test/recommendation.jpg",
  format: "TV",
  year: 2024,
  episodes: 12,
  score: 82,
  reason: "Because of your picks",
};

function animeResponse(items: AnimeCardData[]) {
  return {
    items,
    pageInfo: {
      total: items.length,
      currentPage: 1,
      lastPage: 1,
      perPage: 6,
      hasNextPage: false,
    },
  };
}

function routeElement(path = "/") {
  return (
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/results" element={<ResultsPage />} />
        <Route path="/quiz" element={<QuizPage />} />
        <Route path="/anime/:id" element={<p>Anime detail</p>} />
      </Routes>
    </MemoryRouter>
  );
}

function renderRoutes(path = "/") {
  return render(routeElement(path));
}

async function advanceSearchDebounce() {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(300);
  });
}

async function pickTitle(title: string) {
  const input = screen.getByRole("combobox");
  fireEvent.focus(input);
  fireEvent.change(input, {
    target: { value: title },
  });
  await advanceSearchDebounce();
  fireEvent.click(screen.getByRole("option", { name: new RegExp(title) }));
}

beforeEach(() => {
  vi.useFakeTimers();
  authState.mature = false;
  localStorage.clear();
  clearSavedQuiz();
  clearSavedStart();
  vi.mocked(api.anime).mockReset().mockResolvedValue(animeResponse(anime));
  vi.mocked(api.quiz).mockReset().mockResolvedValue([
    { id: "mood", label: "What mood?", answers: [{ id: "cozy", label: "Cozy" }] },
  ]);
  vi.mocked(api.startRecommendations).mockReset().mockResolvedValue([recommendation]);
});

afterEach(() => {
  vi.useRealTimers();
});

describe("TitleAutocomplete", () => {
  it("debounces search and supports arrows, enter, and escape with the combobox pattern", async () => {
    authState.mature = true;
    const onSelect = vi.fn();
    render(
      <TitleAutocomplete
        includeMature={authState.mature}
        onSelect={onSelect}
        selected={[]}
      />,
    );
    const input = screen.getByRole("combobox", { name: "Search anime titles" });
    fireEvent.focus(input);
    fireEvent.change(input, { target: { value: "anime" } });
    expect(api.anime).not.toHaveBeenCalled();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(299);
    });
    expect(api.anime).not.toHaveBeenCalled();
    await advanceSearchDebounce();
    await act(async () => { await Promise.resolve(); });
    expect(api.anime).toHaveBeenCalledWith(
      { q: "anime", page: 1, pageSize: 6, includeMature: true },
      expect.any(AbortSignal),
    );
    expect(screen.getAllByRole("option")).toHaveLength(6);
    expect(input).toHaveAttribute("aria-expanded", "true");

    fireEvent.keyDown(input, { key: "ArrowDown" });
    const firstOptionId = input.getAttribute("aria-activedescendant");
    expect(firstOptionId).toBeTruthy();
    fireEvent.keyDown(input, { key: "ArrowDown" });
    expect(input.getAttribute("aria-activedescendant")).not.toBe(firstOptionId);
    fireEvent.keyDown(input, { key: "ArrowUp" });
    expect(input.getAttribute("aria-activedescendant")).toBe(firstOptionId);
    fireEvent.keyDown(input, { key: "Escape" });
    expect(input).toHaveAttribute("aria-expanded", "false");

    fireEvent.change(input, { target: { value: "anime again" } });
    await advanceSearchDebounce();
    fireEvent.keyDown(input, { key: "ArrowDown" });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onSelect).toHaveBeenCalledWith(anime[0]);
  });

  it("aborts the prior request when the query changes", async () => {
    let resolveStale: (response: ReturnType<typeof animeResponse>) => void = () => undefined;
    vi.mocked(api.anime)
      .mockReturnValueOnce(
        new Promise((resolve) => {
          resolveStale = resolve;
        }),
      )
      .mockResolvedValueOnce(animeResponse([anime[1]]));
    render(
      <TitleAutocomplete includeMature={false} onSelect={vi.fn()} selected={[]} />,
    );
    const input = screen.getByRole("combobox", { name: "Search anime titles" });
    fireEvent.focus(input);
    fireEvent.change(input, { target: { value: "stale" } });
    await advanceSearchDebounce();
    const staleSignal = vi.mocked(api.anime).mock.calls[0][1];
    expect(staleSignal?.aborted).toBe(false);

    fireEvent.change(input, { target: { value: "current" } });
    expect(staleSignal?.aborted).toBe(true);
    await advanceSearchDebounce();
    await act(async () => Promise.resolve());
    resolveStale(animeResponse([anime[0]]));
    await act(async () => Promise.resolve());
    expect(screen.getAllByRole("option")).toHaveLength(1);
    expect(screen.getByRole("option")).toHaveTextContent("Anime 2");
  });

  it("shows the empty state and offers retry after a network error", async () => {
    const onSelect = vi.fn();
    vi.mocked(api.anime)
      .mockResolvedValueOnce(animeResponse([]))
      .mockRejectedValueOnce(new Error("offline"))
      .mockResolvedValue(animeResponse(anime));
    render(
      <TitleAutocomplete includeMature={false} onSelect={onSelect} selected={[]} />,
    );
    const input = screen.getByRole("combobox", { name: "Search anime titles" });
    fireEvent.focus(input);
    fireEvent.change(input, { target: { value: "missing" } });
    await advanceSearchDebounce();
    expect(screen.getByRole("status")).toHaveTextContent("No anime found");

    fireEvent.change(input, { target: { value: "network" } });
    await advanceSearchDebounce();
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Could not load anime. Try again.",
    );
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    await act(async () => Promise.resolve());
    expect(screen.getAllByRole("option")).toHaveLength(6);
  });
});

describe("home page", () => {
  it("does not show the similar-anime search outside the results header", () => {
    renderRoutes("/");
    expect(screen.queryByRole("combobox", { name: "Search anime similar to" })).toBeNull();
  });
});

describe("title recommendation entry", () => {
  it("requires three picks, prevents duplicates, caps at five, sends mature setting, saves, and navigates", async () => {
    authState.mature = true;
    renderRoutes("/quiz?mode=titles");
    await act(async () => Promise.resolve());
    expect(screen.getByRole("heading", { name: "Name anime you like" })).toBeInTheDocument();
    const submit = screen.getByRole("button", { name: "Get recommendations" });
    const search = screen.getByRole("combobox", { name: "Search anime titles" });
    expect(submit).toBeDisabled();
    expect(screen.getByText("0 of 3 minimum, 5 maximum")).toBeInTheDocument();

    await pickTitle("Anime 1");
    expect(screen.getByText("1 of 3 minimum, 5 maximum")).toBeInTheDocument();
    expect(screen.getByRole("list", { name: "Picked anime" }).querySelector("img"))
      .toHaveAttribute("src", anime[0].coverImage);
    await pickTitle("Anime 1");
    expect(screen.getByText("1 of 3 minimum, 5 maximum")).toBeInTheDocument();
    await pickTitle("Anime 2");
    expect(submit).toBeDisabled();
    await pickTitle("Anime 3");
    expect(submit).toBeEnabled();
    await pickTitle("Anime 4");
    await pickTitle("Anime 5");

    expect(screen.getByText("5 of 3 minimum, 5 maximum")).toBeInTheDocument();
    expect(search).toBeDisabled();
    expect(screen.getByText("Maximum of 5 titles selected.")).toBeInTheDocument();
    expect(screen.queryByText(/different franchises/i)).not.toBeInTheDocument();
    expect(api.anime).toHaveBeenCalled();
    for (const [params] of vi.mocked(api.anime).mock.calls) {
      expect(params.includeMature).toBe(true);
    }

    fireEvent.click(submit);
    await act(async () => Promise.resolve());
    expect(screen.getByRole("heading", { name: "Recommendations based on your picks" })).toBeInTheDocument();
    expect(api.startRecommendations).toHaveBeenCalledWith([1, 2, 3, 4, 5], true);
    expect(readSavedStart()).toMatchObject({
      liked_ids: [1, 2, 3, 4, 5],
      results: [recommendation],
      include_mature: true,
    });
  }, 15000);

  it("rewrites the franchise 422 beside the picked titles in clearer language", async () => {
    vi.mocked(api.startRecommendations).mockRejectedValueOnce(
      new ApiError(
        "liked_ids must cover at least 3 different franchises; some selected titles share a franchise.",
        422,
      ),
    );
    renderRoutes("/quiz?mode=titles");
    await act(async () => Promise.resolve());
    await pickTitle("Anime 1");
    await pickTitle("Anime 2");
    await pickTitle("Anime 3");
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Get recommendations" }));
      await Promise.resolve();
    });
    expect(screen.getByRole("alert")).toHaveTextContent(
      "These titles include multiple seasons from the same series. Choose titles from at least 3 different series.",
    );
    expect(screen.getByRole("alert")).not.toHaveTextContent("liked_ids");
    expect(readSavedStart()).toBeNull();
  }, 10000);

  it("shows a loading label and disables submission while the request is pending", async () => {
    let resolveRequest: (results: Recommendation[]) => void = () => undefined;
    vi.mocked(api.startRecommendations).mockReturnValueOnce(
      new Promise((resolve) => {
        resolveRequest = resolve;
      }),
    );
    renderRoutes("/quiz?mode=titles");
    await act(async () => Promise.resolve());
    await pickTitle("Anime 1");
    await pickTitle("Anime 2");
    await pickTitle("Anime 3");
    fireEvent.click(screen.getByRole("button", { name: "Get recommendations" }));
    expect(screen.getByRole("button", { name: "Getting recommendations…" })).toBeDisabled();
    await act(async () => resolveRequest([recommendation]));
    expect(screen.getByRole("heading", { name: "Recommendations based on your picks" })).toBeInTheDocument();
  }, 10000);

  it("retries with stored IDs when mature content changes and has no start over button", async () => {
    saveStart({
      liked_ids: [2, 4, 6],
      results: [recommendation],
      include_mature: false,
    });
    const view = renderRoutes("/results");
    expect(screen.getByRole("heading", { name: "Recommendations based on your picks" })).toBeInTheDocument();

    authState.mature = true;
    view.rerender(routeElement("/results"));
    await act(async () => Promise.resolve());
    expect(api.startRecommendations).toHaveBeenCalledWith([2, 4, 6], true);
    expect(readSavedStart()?.include_mature).toBe(true);
    expect(screen.queryByRole("button", { name: "Start over" })).toBeNull();
    expect(readSavedStart()?.liked_ids).toEqual([2, 4, 6]);
  });
});

describe("title recommendation storage", () => {
  it("uses the versioned key and falls back to memory when localStorage throws", () => {
    const saved = {
      liked_ids: [1, 2, 3],
      results: [recommendation],
      include_mature: false,
    };
    const set = vi.spyOn(localStorage, "setItem").mockImplementation(() => {
      throw new Error("storage blocked");
    });
    expect(saveStart(saved)).toBe(false);
    expect(readSavedStart()).toEqual(saved);
    set.mockRestore();
    expect(START_STORAGE_KEY).toBe("animatch.start.v1");
    clearSavedStart();
    expect(readSavedStart()).toBeNull();
  });
});
