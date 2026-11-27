import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { useContext } from "react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";
const mocks = vi.hoisted(() => ({
  useAnimeDetail: vi.fn(),
  useSimilar: vi.fn(),
  useSeasons: vi.fn(),
  useListStatuses: vi.fn(),
  useAuth: vi.fn(),
  useProviders: vi.fn(),
  useMe: vi.fn(),
}));
vi.mock("../src/api/hooks", () => ({
  useAnimeDetail: mocks.useAnimeDetail,
  useSimilar: mocks.useSimilar,
  useSeasons: mocks.useSeasons,
  useListStatuses: mocks.useListStatuses,
  useProviders: mocks.useProviders,
  useMe: mocks.useMe,
}));
vi.mock("../src/auth/useAuth", () => ({ useAuth: mocks.useAuth }));
vi.mock("../src/api/useListMutation", () => ({
  useListMutation: () => ({ mutate: vi.fn(), isPending: false }),
}));
import { ApiError, api } from "../src/api/client";
import { ToastProvider } from "../src/components/ToastProvider";
import { LoginPage } from "../src/pages/AuthPages";
import { AnimeDetailPage } from "../src/pages/AnimeDetailPage";
import { SimilarAnimePage } from "../src/pages/SimilarAnimePage";
import { Navbar } from "../src/components/Navbar";
import { AuthProvider } from "../src/auth/AuthContext";
import { AuthContext } from "../src/auth/context";
describe("auth and detail states", () => {
  beforeEach(() => {
    mocks.useAuth.mockReturnValue({
      mature: false,
      user: null,
      refresh: vi.fn().mockResolvedValue(undefined),
    });
    mocks.useProviders.mockReturnValue({ data: { google: false } });
    mocks.useMe.mockReturnValue({ data: undefined });
    mocks.useSeasons.mockReturnValue({ data: undefined });
  });
  it("shows the exact detail 404 message", () => {
    mocks.useAnimeDetail.mockReturnValue({
      isLoading: false,
      isError: true,
      error: new ApiError("hidden", 404),
    });
    mocks.useSimilar.mockReturnValue({ isLoading: true });
    mocks.useListStatuses.mockReturnValue({
      data: { items: [] },
      isLoading: false,
    });
    render(
      <MemoryRouter
        future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
        initialEntries={["/anime/4"]}
      >
        <Routes>
          <Route path="/anime/:id" element={<AnimeDetailPage />} />
        </Routes>
      </MemoryRouter>
    );
    expect(
      screen.getByText("Not found, or hidden by your content settings")
    ).toBeInTheDocument();
  });
  it("asks guests to sign in from Add to list or rating and shows the score out of five", () => {
    mocks.useAnimeDetail.mockReturnValue({
      isLoading: false,
      isError: false,
      data: {
        id: 4,
        title: "Test Anime",
        coverImage: "https://img.test/cover.jpg",
        format: "TV",
        score: 84,
      },
    });
    mocks.useSimilar.mockReturnValue({
      isLoading: false,
      isError: false,
      data: [],
    });
    mocks.useListStatuses.mockReturnValue({
      data: { items: [] },
      isLoading: false,
    });
    render(
      <MemoryRouter
        future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
        initialEntries={["/anime/4"]}
      >
        <Routes>
          <Route path="/anime/:id" element={<AnimeDetailPage />} />
        </Routes>
      </MemoryRouter>
    );

    const score = screen.getByText("AniList score").closest("div");
    expect(score).toHaveTextContent("AniList score4.2 / 5");
    const hero = screen
      .getByRole("heading", { level: 1, name: "Test Anime" })
      .closest("header");
    expect(hero).toContainElement(
      screen.getByRole("button", { name: "Add Test Anime to My list" })
    );
    expect(hero).toContainElement(
      screen.getByRole("combobox", { name: "Your rating for Test Anime" })
    );
    expect(screen.getByRole("list", { name: "Overview" })).toHaveTextContent(
      "TV"
    );
    fireEvent.click(
      screen.getByRole("button", { name: "Add Test Anime to My list" })
    );
    expect(
      screen.getByRole("dialog", { name: "Sign in to save anime" })
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Sign in" })).toHaveAttribute(
      "href",
      "/login?next=%2Fanime%2F4"
    );
    expect(
      screen.getByRole("link", { name: "Create account" })
    ).toHaveAttribute("href", "/register?next=%2Fanime%2F4");

    fireEvent.click(
      screen.getByRole("button", { name: "Close sign-in prompt" })
    );
    fireEvent.change(
      screen.getByRole("combobox", { name: "Your rating for Test Anime" }),
      { target: { value: "7" } }
    );
    expect(
      screen.getByRole("dialog", { name: "Sign in to save anime" })
    ).toBeInTheDocument();
  });
  it("lists the main story with the current entry and the optional extras", () => {
    mocks.useAnimeDetail.mockReturnValue({
      isLoading: false,
      isError: false,
      data: { id: 2, title: "Season Two", format: "TV" },
    });
    mocks.useSimilar.mockReturnValue({ isLoading: false, data: [] });
    mocks.useListStatuses.mockReturnValue({ data: { items: [] } });
    const item = { coverImage: null, coverColor: null, format: "TV" };
    mocks.useSeasons.mockReturnValue({
      data: {
        main: [
          {
            ...item,
            id: 1,
            title: "Season One",
            year: 2013,
            episodes: 25,
            position: 1,
            isCurrent: false,
          },
          {
            ...item,
            id: 2,
            title: "Season Two",
            year: 2017,
            episodes: 12,
            position: 2,
            isCurrent: true,
          },
        ],
        extras: [
          {
            ...item,
            id: 5,
            title: "Lost Girls",
            format: "OVA",
            year: 2017,
            episodes: 2,
            relation: "SIDE_STORY",
          },
          {
            ...item,
            id: 6,
            title: "Recap",
            format: "MOVIE",
            year: 2014,
            episodes: 1,
            relation: "SUMMARY",
          },
        ],
      },
    });
    render(
      <MemoryRouter
        future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
        initialEntries={["/anime/2"]}
      >
        <Routes>
          <Route path="/anime/:id" element={<AnimeDetailPage />} />
        </Routes>
      </MemoryRouter>
    );
    expect(
      screen.getByText("2 entries in the main story, in release order")
    ).toBeInTheDocument();
    const current = document.querySelector("[aria-current='page']");
    expect(current).toHaveTextContent("Season Two");
    expect(current).toHaveTextContent("You're here");
    expect(screen.getByRole("link", { name: /Season One/ })).toHaveAttribute(
      "href",
      "/anime/1"
    );
    expect(screen.getByRole("link", { name: /Lost Girls/ })).toHaveTextContent(
      "OVA, 2 episodes, 2017"
    );
    expect(screen.getByRole("link", { name: /Recap/ })).toHaveTextContent(
      "Recap film, 2014"
    );
  });
  it("shows similar recommendations for the selected anime without rendering its full details", () => {
    mocks.useAnimeDetail.mockReturnValue({
      isLoading: false,
      isError: false,
      data: {
        id: 4,
        title: "Seed Anime",
        coverImage: "https://img.test/seed.jpg",
        format: "TV",
        year: 2024,
      },
    });
    mocks.useSimilar.mockReturnValue({
      isLoading: false,
      isError: false,
      data: [
        {
          id: 9,
          title: "Similar Anime",
          coverImage: "https://img.test/similar.jpg",
          format: "TV",
          year: 2023,
          similarity: 0.8,
          reason: "Shares genres",
        },
      ],
    });
    render(
      <MemoryRouter
        future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
        initialEntries={["/similar/4"]}
      >
        <Routes>
          <Route path="/similar/:id" element={<SimilarAnimePage />} />
        </Routes>
      </MemoryRouter>
    );
    expect(
      screen.getByRole("heading", { name: "Anime Similar to Seed Anime" })
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Seed Anime" })).toHaveAttribute(
      "href",
      "/anime/4"
    );
    expect(screen.getByText("Similar Anime")).toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: "Synopsis" })
    ).not.toBeInTheDocument();
  });
  it("shows the similar-anime search on similar and anime detail pages", () => {
    render(
      <MemoryRouter
        future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
        initialEntries={["/similar/4"]}
      >
        <Navbar />
      </MemoryRouter>
    );
    expect(
      screen.getByRole("combobox", { name: "Search anime similar to" })
    ).toBeInTheDocument();
    cleanup();
    render(
      <MemoryRouter
        future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
        initialEntries={["/anime/4"]}
      >
        <Navbar />
      </MemoryRouter>
    );
    expect(
      screen.getByRole("combobox", { name: "Search anime similar to" })
    ).toBeInTheDocument();
  });
  it("requires guests to sign in before toggling mature anime", () => {
    const setMature = vi.fn().mockResolvedValue(undefined);
    mocks.useAuth.mockReturnValue({
      mature: false,
      user: null,
      setMature,
      refresh: vi.fn(),
    });
    render(
      <MemoryRouter
        future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
        initialEntries={["/quiz"]}
      >
        <Navbar />
      </MemoryRouter>
    );
    fireEvent.click(
      screen.getByRole("button", { name: "Include mature anime" })
    );
    expect(
      screen.getByRole("dialog", { name: "Sign in to view 18+ content" })
    ).toBeInTheDocument();
    expect(setMature).not.toHaveBeenCalled();

    cleanup();
    mocks.useAuth.mockReturnValue({
      mature: false,
      user: { id: 1 },
      setMature,
      refresh: vi.fn(),
    });
    render(
      <MemoryRouter
        future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
        initialEntries={["/quiz"]}
      >
        <Navbar />
      </MemoryRouter>
    );
    fireEvent.click(
      screen.getByRole("button", { name: "Include mature anime" })
    );
    expect(setMature).toHaveBeenCalledWith(true);
  });
  it("keeps mature content off for guests even if an old local preference is enabled", async () => {
    localStorage.setItem("animatch.includeMature", "true");
    function MatureProbe() {
      const auth = useContext(AuthContext);
      if (!auth) throw new Error("AuthProvider is required");
      const { mature, setMature } = auth;
      return (
        <button aria-pressed={mature} onClick={() => void setMature(true)}>
          {mature ? "On" : "Off"}
        </button>
      );
    }
    const updateMe = vi.spyOn(api, "updateMe");
    render(
      <QueryClientProvider client={new QueryClient()}>
        <ToastProvider>
          <AuthProvider>
            <MatureProbe />
          </AuthProvider>
        </ToastProvider>
      </QueryClientProvider>
    );
    const toggle = screen.getByRole("button", { name: "Off" });
    expect(toggle).toHaveAttribute("aria-pressed", "false");
    fireEvent.click(toggle);
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Off" })).toHaveAttribute(
        "aria-pressed",
        "false"
      )
    );
    expect(updateMe).not.toHaveBeenCalled();
  });
  it("submits the login form and hides Google when it is not configured", async () => {
    const login = vi.spyOn(api, "login").mockResolvedValue({
      id: 1,
      email: "a@b.com",
      display_name: "A",
      show_mature: false,
      created_at: "today",
    });
    const queryClient = new QueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <ToastProvider>
          <MemoryRouter
            future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
          >
            <Routes>
              <Route path="*" element={<LoginPage />} />
            </Routes>
          </MemoryRouter>
        </ToastProvider>
      </QueryClientProvider>
    );
    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "a@b.com" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "secret" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
    await waitFor(() =>
      expect(login).toHaveBeenCalledWith({
        email: "a@b.com",
        password: "secret",
      })
    );
    expect(
      screen.queryByRole("link", { name: "Sign in with Google" })
    ).not.toBeInTheDocument();
  });
});
