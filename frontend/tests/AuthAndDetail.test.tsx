import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useContext } from "react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";
const mocks = vi.hoisted(() => ({ useAnimeDetail: vi.fn(), useSimilar: vi.fn(), useListStatuses: vi.fn(), useAuth: vi.fn(), useProviders: vi.fn(), useMe: vi.fn() }));
vi.mock("../src/api/hooks", () => ({ useAnimeDetail: mocks.useAnimeDetail, useSimilar: mocks.useSimilar, useListStatuses: mocks.useListStatuses, useProviders: mocks.useProviders, useMe: mocks.useMe }));
vi.mock("../src/auth/useAuth", () => ({ useAuth: mocks.useAuth }));
vi.mock("../src/api/useListMutation", () => ({ useListMutation: () => ({ mutate: vi.fn(), isPending: false }) }));
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
    mocks.useAuth.mockReturnValue({ mature: false, user: null, refresh: vi.fn().mockResolvedValue(undefined) });
    mocks.useProviders.mockReturnValue({ data: { google: false } });
    mocks.useMe.mockReturnValue({ data: undefined });
  });
  it("shows the exact detail 404 message", () => {
    mocks.useAnimeDetail.mockReturnValue({ isLoading: false, isError: true, error: new ApiError("hidden", 404) });
    mocks.useSimilar.mockReturnValue({ isLoading: true });
    mocks.useListStatuses.mockReturnValue({ data: { items: [] }, isLoading: false });
    render(<MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }} initialEntries={["/anime/4"]}><Routes><Route path="/anime/:id" element={<AnimeDetailPage />} /></Routes></MemoryRouter>);
    expect(screen.getByText("Not found, or hidden by your content settings")).toBeInTheDocument();
  });
  it("asks guests to sign in from Add to list or rating and shows the rating out of ten", () => {
    mocks.useAnimeDetail.mockReturnValue({ isLoading: false, isError: false, data: { id: 4, title: "Test Anime", coverImage: "https://img.test/cover.jpg", format: "TV", score: 84 } });
    mocks.useSimilar.mockReturnValue({ isLoading: false, isError: false, data: [] });
    mocks.useListStatuses.mockReturnValue({ data: { items: [] }, isLoading: false });
    render(<MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }} initialEntries={["/anime/4"]}><Routes><Route path="/anime/:id" element={<AnimeDetailPage />} /></Routes></MemoryRouter>);

    const sidebar = screen.getByRole("complementary", { name: "Anime controls" });
    expect(sidebar).toContainElement(screen.getByText("AniList score"));
    expect(sidebar).toContainElement(screen.getByRole("button", { name: "Add Test Anime to My list" }));
    expect(sidebar).toContainElement(screen.getByRole("combobox", { name: "Your rating for Test Anime" }));
    expect(screen.getByRole("heading", { name: "Test Anime" }).closest(".detail-main")).not.toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Add Test Anime to My list" }));
    expect(screen.getByRole("dialog", { name: "Sign in to save anime" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Sign in" })).toHaveAttribute("href", "/login?next=%2Fanime%2F4");
    expect(screen.getByRole("link", { name: "Create account" })).toHaveAttribute("href", "/register?next=%2Fanime%2F4");

    fireEvent.click(screen.getByRole("button", { name: "Close sign-in prompt" }));
    fireEvent.change(screen.getByRole("combobox", { name: "Your rating for Test Anime" }), { target: { value: "7" } });
    expect(screen.getByRole("dialog", { name: "Sign in to save anime" })).toBeInTheDocument();
  });
  it("shows similar recommendations for the selected anime without rendering its full details", () => {
    mocks.useAnimeDetail.mockReturnValue({ isLoading: false, isError: false, data: { id: 4, title: "Seed Anime", coverImage: "https://img.test/seed.jpg", format: "TV", year: 2024 } });
    mocks.useSimilar.mockReturnValue({ isLoading: false, isError: false, data: [{ id: 9, title: "Similar Anime", coverImage: "https://img.test/similar.jpg", format: "TV", year: 2023, similarity: 0.8, reason: "Shares genres" }] });
    render(<MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }} initialEntries={["/similar/4"]}><Routes><Route path="/similar/:id" element={<SimilarAnimePage />} /></Routes></MemoryRouter>);
    expect(screen.getByRole("heading", { name: "Anime similar to Seed Anime" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Seed Anime" })).toHaveAttribute("href", "/anime/4");
    expect(screen.getByText("Similar Anime")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Synopsis" })).not.toBeInTheDocument();
  });
  it("shows the similar-anime search on similar and anime detail pages", () => {
    render(<MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }} initialEntries={["/similar/4"]}><Navbar /></MemoryRouter>);
    expect(screen.getByRole("combobox", { name: "Search anime similar to" })).toBeInTheDocument();
    cleanup();
    render(<MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }} initialEntries={["/anime/4"]}><Navbar /></MemoryRouter>);
    expect(screen.getByRole("combobox", { name: "Search anime similar to" })).toBeInTheDocument();
  });
  it("requires guests to sign in before toggling mature anime", () => {
    const setMature = vi.fn().mockResolvedValue(undefined);
    mocks.useAuth.mockReturnValue({ mature: false, user: null, setMature, refresh: vi.fn() });
    render(<MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }} initialEntries={["/quiz"]}><Navbar /></MemoryRouter>);
    fireEvent.click(screen.getByRole("button", { name: "Include mature anime" }));
    expect(screen.getByRole("dialog", { name: "Sign in to view 18+ content" })).toBeInTheDocument();
    expect(setMature).not.toHaveBeenCalled();

    cleanup();
    mocks.useAuth.mockReturnValue({ mature: false, user: { id: 1 }, setMature, refresh: vi.fn() });
    render(<MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }} initialEntries={["/quiz"]}><Navbar /></MemoryRouter>);
    fireEvent.click(screen.getByRole("button", { name: "Include mature anime" }));
    expect(setMature).toHaveBeenCalledWith(true);
  });
  it("keeps mature content off for guests even if an old local preference is enabled", async () => {
    localStorage.setItem("animatch.includeMature", "true");
    function MatureProbe() {
      const auth = useContext(AuthContext);
      if (!auth) throw new Error("AuthProvider is required");
      const { mature, setMature } = auth;
      return <button aria-pressed={mature} onClick={() => void setMature(true)}>{mature ? "On" : "Off"}</button>;
    }
    const updateMe = vi.spyOn(api, "updateMe");
    render(<QueryClientProvider client={new QueryClient()}><ToastProvider><AuthProvider><MatureProbe /></AuthProvider></ToastProvider></QueryClientProvider>);
    const toggle = screen.getByRole("button", { name: "Off" });
    expect(toggle).toHaveAttribute("aria-pressed", "false");
    fireEvent.click(toggle);
    await waitFor(() => expect(screen.getByRole("button", { name: "Off" })).toHaveAttribute("aria-pressed", "false"));
    expect(updateMe).not.toHaveBeenCalled();
  });
  it("submits the login form and hides Google when it is not configured", async () => {
    const login = vi.spyOn(api, "login").mockResolvedValue({ id: 1, email: "a@b.com", display_name: "A", show_mature: false, created_at: "today" });
    const queryClient = new QueryClient();
    render(<QueryClientProvider client={queryClient}><ToastProvider><MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}><Routes><Route path="*" element={<LoginPage />} /></Routes></MemoryRouter></ToastProvider></QueryClientProvider>);
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "a@b.com" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "secret" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
    await waitFor(() => expect(login).toHaveBeenCalledWith({ email: "a@b.com", password: "secret" }));
    expect(screen.queryByRole("link", { name: "Continue with Google" })).not.toBeInTheDocument();
  });
});
