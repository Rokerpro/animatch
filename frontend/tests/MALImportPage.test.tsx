import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "../src/api/client";
import { useAuth } from "../src/auth/useAuth";
import { MALImportPage } from "../src/pages/MALImportPage";
import { QuizPage } from "../src/pages/QuizPages";

vi.mock("../src/auth/useAuth", () => ({ useAuth: vi.fn() }));
vi.mock("../src/api/client", async (load) => {
  const actual = await load<typeof import("../src/api/client")>();
  return { ...actual, api: { ...actual.api, quiz: vi.fn(), importMALList: vi.fn(), csrf: vi.fn() } };
});
const user = { id: 1, email: "a@example.com", display_name: "A", show_mature: false, created_at: "today" };
const preview = { total_entries: 4, to_import: 2, skipped_existing: 1, unmatched_count: 1, unmatched: [{ title: "Unknown Show" }] };
function renderPage(client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } }), path = "/import") {
  return { ...render(<QueryClientProvider client={client}><MemoryRouter initialEntries={[path]}><Routes><Route path="/import" element={<MALImportPage />} /><Route path="/login" element={<p>Login screen</p>} /><Route path="/quiz" element={<QuizPage />} /><Route path="/list" element={<p>List</p>} /><Route path="/for-you" element={<p>For you</p>} /></Routes></MemoryRouter></QueryClientProvider>), client };
}
beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(useAuth).mockReturnValue({ user, mature: false, authLoading: false, refresh: vi.fn(), setMature: vi.fn(), signOut: vi.fn() });
  vi.mocked(api.csrf).mockResolvedValue({ csrf_token: "csrf" });
  vi.mocked(api.importMALList).mockResolvedValue(preview);
  vi.mocked(api.quiz).mockResolvedValue([{ id: "mood", label: "What mood?", answers: [{ id: "cozy", label: "Cozy" }] }]);
});

describe("MyAnimeList import", () => {
  it("redirects guests to login with the import destination", async () => {
    vi.mocked(useAuth).mockReturnValue({ user: null, mature: false, authLoading: false, refresh: vi.fn(), setMature: vi.fn(), signOut: vi.fn() });
    renderPage();
    expect(await screen.findByText("Login screen")).toBeInTheDocument();
  });
  it("rejects oversized and unsupported files before requesting", () => {
    renderPage();
    const input = screen.getByLabelText("MyAnimeList export file");
    fireEvent.change(input, { target: { files: [new File([new Uint8Array(5 * 1024 * 1024 + 1)], "large.xml")] } });
    expect(screen.getByRole("alert")).toHaveTextContent("larger than 5 MB");
    fireEvent.change(input, { target: { files: [new File(["bad"], "list.json")] } });
    expect(screen.getByRole("alert")).toHaveTextContent("Choose a MyAnimeList export file");
    expect(api.importMALList).not.toHaveBeenCalled();
  });
  it("previews and confirms, shows results, and invalidates list and recommendation queries", async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
    const invalidate = vi.spyOn(client, "invalidateQueries");
    renderPage(client);
    fireEvent.change(screen.getByLabelText("MyAnimeList export file"), { target: { files: [new File(["xml"], "list.xml")] } });
    fireEvent.click(screen.getByRole("button", { name: "Preview import" }));
    expect(await screen.findByText("Unknown Show")).toBeInTheDocument();
    expect(api.importMALList).toHaveBeenCalledWith(expect.any(File), true);
    fireEvent.click(screen.getByRole("button", { name: "Confirm import" }));
    await screen.findByRole("heading", { name: "Import complete" });
    expect(api.importMALList).toHaveBeenLastCalledWith(expect.any(File), false);
    expect(screen.getByRole("link", { name: "My list" })).toHaveAttribute("href", "/list");
    expect(screen.getByRole("link", { name: "For you" })).toHaveAttribute("href", "/for-you");
    await waitFor(() => expect(invalidate).toHaveBeenCalledWith({ queryKey: ["list"] }));
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["list-statuses"] });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["my-recommendations"] });
  });
  it("shows API errors in either supported detail shape", async () => {
    renderPage();
    const input = screen.getByLabelText("MyAnimeList export file");
    fireEvent.change(input, { target: { files: [new File(["xml"], "list.xml")] } });
    vi.mocked(api.importMALList).mockRejectedValueOnce(new Error("String detail"));
    fireEvent.click(screen.getByRole("button", { name: "Preview import" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("String detail");
    vi.mocked(api.importMALList).mockRejectedValueOnce(new Error("First issue; second issue"));
    fireEvent.click(screen.getByRole("button", { name: "Preview import" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("First issue; second issue");
  });
  it("offers import from the quiz and prompts guests with the correct destination", async () => {
    vi.mocked(useAuth).mockReturnValue({ user: null, mature: false, authLoading: false, refresh: vi.fn(), setMature: vi.fn(), signOut: vi.fn() });
    renderPage(undefined, "/quiz");
    fireEvent.click(await screen.findByRole("button", { name: "Import a file" }));
    expect(screen.getByRole("link", { name: "Sign in" })).toHaveAttribute("href", "/login?next=%2Fimport");
    expect(screen.getByRole("link", { name: "Create account" })).toHaveAttribute("href", "/register?next=%2Fimport");
  });
});
