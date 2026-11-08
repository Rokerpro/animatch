import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, api } from "../src/api/client";
import { useContext } from "react";
import { AuthProvider } from "../src/auth/AuthContext";
import { AuthContext } from "../src/auth/context";
import { useAuth } from "../src/auth/useAuth";
import { ToastProvider } from "../src/components/ToastProvider";
import { Navbar } from "../src/components/Navbar";
import { ForYouPage } from "../src/pages/ForYouPage";
import { LoginPage, RegisterPage, SettingsPage } from "../src/pages/AuthPages";
import { readSavedQuiz, saveQuiz, clearSavedQuiz } from "../src/quizStorage";
import { readSavedStart, saveStart, clearSavedStart } from "../src/startStorage";

vi.mock("../src/auth/useAuth", () => ({ useAuth: vi.fn() }));
vi.mock("../src/api/hooks", () => ({ queryKeys: { me: ["me"] }, useProviders: () => ({ data: { google: false } }), useMe: () => ({ data: { id: 7, email: "person@example.com", display_name: "Person", show_mature: false, created_at: "2026-01-01" }, isLoading: false }), useListStatuses: () => ({ data: { items: [] }, isLoading: false }) }));

const user = { id: 7, email: "person@example.com", display_name: "Person", show_mature: false, created_at: "2026-01-01" };
const recommendation = { id: 3, title: "A title", reason: "Because it fits your answers" };
const taste = { quiz_answers: { mood: "cozy" }, liked_ids: [] };

function renderApp(element: React.ReactNode, initial = "/") {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}><ToastProvider><MemoryRouter initialEntries={[initial]}>{element}</MemoryRouter></ToastProvider></QueryClientProvider>);
}

beforeEach(() => {
  localStorage.clear(); clearSavedQuiz(); clearSavedStart(); vi.clearAllMocks();
  vi.mocked(useAuth).mockReturnValue({ user: null, authLoading: false, mature: false, refresh: vi.fn().mockResolvedValue(undefined), setMature: vi.fn().mockResolvedValue(undefined), signOut: vi.fn().mockResolvedValue(undefined) });
});

describe("stage 1 account flows", () => {
  it("saves local quiz data once after registration and marks it saved", async () => {
    saveQuiz({ answers: { mood: "cozy" }, results: [recommendation], includeMature: false });
    vi.spyOn(api, "register").mockResolvedValue(user);
    const save = vi.spyOn(api, "saveTasteProfile").mockResolvedValue(taste);
    renderApp(<Routes><Route path="/register" element={<RegisterPage />} /><Route path="/results" element={<p>Results</p>} /></Routes>, "/register?next=/results");
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: user.email } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "longpassword" } });
    fireEvent.click(screen.getByRole("button", { name: "Register" }));
    await waitFor(() => expect(save).toHaveBeenCalledWith({ quiz_answers: { mood: "cozy" }, liked_ids: [] }));
    expect(await screen.findByText("Results")).toBeInTheDocument();
    expect(readSavedQuiz()?.profileSavedFor).toBe(user.id);
  });

  it("keeps an existing login profile and never overwrites it", async () => {
    saveStart({ liked_ids: [4], results: [recommendation], include_mature: false });
    vi.spyOn(api, "login").mockResolvedValue(user);
    vi.spyOn(api, "tasteProfile").mockResolvedValue(taste);
    const save = vi.spyOn(api, "saveTasteProfile");
    renderApp(<Routes><Route path="/login" element={<LoginPage />} /><Route path="/results" element={<p>Results</p>} /></Routes>, "/login?next=/results");
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: user.email } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "longpassword" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByText("Results")).toBeInTheDocument();
    expect(await screen.findByText("Your saved profile was kept")).toBeInTheDocument();
    expect(save).not.toHaveBeenCalled();
    expect(readSavedStart()?.profile_saved_for).toBe(user.id);
  });

  it("continues to results after a profile save error and preserves local data", async () => {
    saveQuiz({ answers: { mood: "cozy" }, results: [recommendation], includeMature: false });
    vi.spyOn(api, "register").mockResolvedValue(user);
    vi.spyOn(api, "saveTasteProfile").mockRejectedValue(new Error("Profile unavailable"));
    renderApp(<Routes><Route path="/register" element={<RegisterPage />} /><Route path="/results" element={<p>Results</p>} /></Routes>, "/register?next=/results");
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: user.email } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "longpassword" } });
    fireEvent.click(screen.getByRole("button", { name: "Register" }));
    expect(await screen.findByText("Results")).toBeInTheDocument();
    expect(await screen.findByText("Profile unavailable")).toBeInTheDocument();
    expect(readSavedQuiz()?.profileSavedFor).not.toBe(user.id);
  });

  it("redirects signed-out visitors to login and shows the empty recommendation state", async () => {
    vi.mocked(useAuth).mockReturnValue({ user: null, authLoading: false, mature: false, refresh: vi.fn(), setMature: vi.fn(), signOut: vi.fn() });
    renderApp(<Routes><Route path="/for-you" element={<ForYouPage />} /><Route path="/login" element={<p>Login page</p>} /></Routes>, "/for-you");
    expect(await screen.findByText("Login page")).toBeInTheDocument();

    vi.mocked(useAuth).mockReturnValue({ user, authLoading: false, mature: false, refresh: vi.fn(), setMature: vi.fn(), signOut: vi.fn() });
    vi.spyOn(api, "myRecommendations").mockResolvedValue([]);
    renderApp(<Routes><Route path="/for-you" element={<ForYouPage />} /></Routes>, "/for-you");
    expect(await screen.findByText(/No recommendations yet/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Take the quiz" })).toHaveAttribute("href", "/quiz");
  });

  it("redirects to login if the personalised request returns 401", async () => {
    vi.mocked(useAuth).mockReturnValue({ user, authLoading: false, mature: false, refresh: vi.fn(), setMature: vi.fn(), signOut: vi.fn() });
    vi.spyOn(api, "myRecommendations").mockRejectedValue(new ApiError("Unauthorized", 401));
    renderApp(<Routes><Route path="/for-you" element={<ForYouPage />} /><Route path="/login" element={<p>Login page</p>} /></Routes>, "/for-you");
    expect(await screen.findByText("Login page")).toBeInTheDocument();
  });

  it("shows My list but no Browse link and exposes a keyboard account menu", async () => {
    vi.mocked(useAuth).mockReturnValue({ user, authLoading: false, mature: false, refresh: vi.fn(), setMature: vi.fn(), signOut: vi.fn() });
    renderApp(<Navbar />, "/");
    expect(screen.getByRole("link", { name: "My list" })).toHaveAttribute("href", "/list");
    expect(screen.queryByRole("link", { name: "Browse" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Account menu" }));
    expect(screen.getByRole("menuitem", { name: "Settings" })).toBeInTheDocument();
    fireEvent.keyDown(screen.getByRole("menu"), { key: "Escape" });
    expect(screen.getByRole("button", { name: "Account menu" })).toHaveFocus();
  });

  it("shows only Get started and Sign in while signed out", () => {
    renderApp(<Navbar />, "/");
    expect(screen.getByRole("link", { name: "Get started" })).toHaveAttribute("href", "/quiz");
    expect(screen.getByRole("link", { name: "Sign in" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "For you" })).not.toBeInTheDocument();
  });

  it("does not refetch or resave local data already marked saved", async () => {
    saveQuiz({ answers: { mood: "cozy" }, results: [recommendation], includeMature: false, profileSavedFor: user.id });
    vi.spyOn(api, "login").mockResolvedValue(user);
    const getProfile = vi.spyOn(api, "tasteProfile");
    const saveProfile = vi.spyOn(api, "saveTasteProfile");
    renderApp(<Routes><Route path="/login" element={<LoginPage />} /><Route path="/results" element={<p>Results</p>} /></Routes>, "/login?next=/results");
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: user.email } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "longpassword" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByText("Results")).toBeInTheDocument();
    expect(getProfile).toHaveBeenCalledTimes(1);
    expect(saveProfile).not.toHaveBeenCalled();
  });

  it("requires DELETE before enabling account deletion", async () => {
    vi.mocked(useAuth).mockReturnValue({ user, authLoading: false, mature: false, refresh: vi.fn(), setMature: vi.fn(), signOut: vi.fn() });
    renderApp(<SettingsPage />);
    const button = screen.getByRole("button", { name: "Delete account" });
    expect(button).toBeDisabled();
    fireEvent.change(screen.getByLabelText("Type DELETE to confirm"), { target: { value: "DELETE" } });
    expect(button).toBeEnabled();
    expect(screen.getByLabelText("Type DELETE to confirm")).toHaveAttribute("aria-describedby", "delete-account-warning");
  });

  it("clears local results after account deletion", async () => {
    const signOut = vi.fn().mockResolvedValue(undefined);
    vi.mocked(useAuth).mockReturnValue({ user, authLoading: false, mature: false, refresh: vi.fn(), setMature: vi.fn(), signOut });
    saveQuiz({ answers: { mood: "cozy" }, results: [recommendation], includeMature: false });
    saveStart({ liked_ids: [3], results: [recommendation], include_mature: false });
    vi.spyOn(api, "deleteMe").mockResolvedValue({ message: "ok" });
    renderApp(<SettingsPage />);
    fireEvent.change(screen.getByLabelText("Type DELETE to confirm"), { target: { value: "DELETE" } });
    fireEvent.click(screen.getByRole("button", { name: "Delete account" }));
    await waitFor(() => expect(readSavedQuiz()).toBeNull());
    expect(readSavedStart()).toBeNull();
    expect(signOut).toHaveBeenCalled();
  });

  it("clears both saved result types when signing out", async () => {
    saveQuiz({ answers: { mood: "cozy" }, results: [recommendation], includeMature: false });
    saveStart({ liked_ids: [3], results: [recommendation], include_mature: false });
    vi.spyOn(api, "logout").mockResolvedValue({ message: "ok" });
    function SignOutProbe() {
      const auth = useContext(AuthContext);
      return <button onClick={() => void auth?.signOut()}>Sign out</button>;
    }
    renderApp(<AuthProvider><SignOutProbe /></AuthProvider>);
    fireEvent.click(screen.getByRole("button", { name: "Sign out" }));
    await waitFor(() => expect(readSavedQuiz()).toBeNull());
    expect(readSavedStart()).toBeNull();
  });

  it("trims display names and routes the 18+ control through the shared mutation", async () => {
    const setMature = vi.fn().mockResolvedValue(undefined);
    vi.mocked(useAuth).mockReturnValue({ user, authLoading: false, mature: false, refresh: vi.fn(), setMature, signOut: vi.fn() });
    const update = vi.spyOn(api, "updateMe").mockResolvedValue(user);
    renderApp(<SettingsPage />);
    fireEvent.change(screen.getByLabelText("Display name"), { target: { value: "  New name  " } });
    fireEvent.click(screen.getByRole("button", { name: "Save display name" }));
    await waitFor(() => expect(update).toHaveBeenCalledWith({ display_name: "New name" }));
    fireEvent.click(screen.getByLabelText("Include mature anime (18+)"));
    expect(setMature).toHaveBeenCalledWith(true);
  });
});
