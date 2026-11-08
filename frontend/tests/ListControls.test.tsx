import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, api } from "../src/api/client";
import { useAuth } from "../src/auth/useAuth";
import { ToastProvider } from "../src/components/ToastProvider";
import { ListControl, ListRatingControl } from "../src/components/ListControls";
import { ListStatusContext } from "../src/components/listStatus";
import { PosterGrid } from "../src/components/PosterGrid";
import { AnimeCard } from "../src/components/AnimeCard";

vi.mock("../src/auth/useAuth", () => ({ useAuth: vi.fn() }));

const user = { id: 1, email: "a@example.com", display_name: "A", show_mature: false, created_at: "today" };
const anime = { id: 7, title: "Example", coverImage: "https://img.test/7.jpg" };
function renderWithProviders(node: React.ReactNode, initial = "/anime/7") {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return { client, ...render(<QueryClientProvider client={client}><ToastProvider><MemoryRouter initialEntries={[initial]}>{node}</MemoryRouter></ToastProvider></QueryClientProvider>) };
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(useAuth).mockReturnValue({ user, mature: false, authLoading: false, refresh: vi.fn(), setMature: vi.fn(), signOut: vi.fn() });
});

describe("list controls", () => {
  it("optimistically changes status and rolls it back with the server error message", async () => {
    let rejectUpdate: ((reason: Error) => void) | undefined;
    vi.spyOn(api, "updateListEntry").mockImplementation(() => new Promise((_resolve, reject) => { rejectUpdate = reject; }));
    const { client } = renderWithProviders(<ListStatusContext.Provider value={{ entries: new Map([[7, { status: "planning", rating: 8 }]]), loading: false }}><ListControl anime={anime} status="planning" rating={8} /></ListStatusContext.Provider>);
    const invalidate = vi.spyOn(client, "invalidateQueries");
    client.setQueryData(["list-statuses", false, [7]], { items: [{ animeId: 7, status: "planning", rating: 8 }] });
    fireEvent.click(screen.getByRole("button", { name: /Change list status for Example/ }));
    fireEvent.click(screen.getByRole("menuitemradio", { name: "Watching" }));
    await waitFor(() => expect(client.getQueryData(["list-statuses", false, [7]])).toEqual({ items: [{ animeId: 7, status: "watching", rating: 8 }] }));
    rejectUpdate?.(new Error("The server rejected this status."));
    expect(await screen.findByRole("alert")).toHaveTextContent("The server rejected this status.");
    await waitFor(() => expect(client.getQueryData(["list-statuses", false, [7]])).toEqual({ items: [{ animeId: 7, status: "planning", rating: 8 }] }));
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["list"] });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["list-statuses"] });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["my-recommendations"] });
  });

  it("creates an unlisted title as completed when it is rated", async () => {
    const update = vi.spyOn(api, "updateListEntry").mockResolvedValue({ id: 4, anime_id: 7, anime, status: "completed", rating: 8, source: "manual", added_at: "today", updated_at: "today" });
    renderWithProviders(<ListRatingControl anime={anime} status={null} rating={null} />);
    const select = screen.getByRole("combobox", { name: "Your rating for Example" });
    expect(Array.from((select as HTMLSelectElement).options).map((option) => option.value)).toEqual(["", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]);
    fireEvent.change(select, { target: { value: "8" } });
    await waitFor(() => expect(update).toHaveBeenCalledWith(7, { status: "completed", rating: 8 }));
  });

  it("shows the content settings message when adding a hidden title returns 404", async () => {
    vi.spyOn(api, "updateListEntry").mockRejectedValue(new ApiError("Not found", 404));
    renderWithProviders(<ListControl anime={anime} status={null} rating={null} />);
    fireEvent.click(screen.getByRole("button", { name: "Add Example to My list" }));
    fireEvent.click(screen.getByRole("menuitemradio", { name: "Watching" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("This title is hidden by your content settings");
  });

  it("clears an existing rating by sending null", async () => {
    const update = vi.spyOn(api, "updateListEntry").mockResolvedValue({ id: 4, anime_id: 7, anime, status: "watching", rating: null, source: "manual", added_at: "today", updated_at: "today" });
    renderWithProviders(<ListRatingControl anime={anime} status="watching" rating={8} />);
    fireEvent.change(screen.getByRole("combobox", { name: "Your rating for Example" }), { target: { value: "" } });
    await waitFor(() => expect(update).toHaveBeenCalledWith(7, { rating: null }));
  });

  it("opens a sign-in prompt whose return path is validated and relative", () => {
    vi.mocked(useAuth).mockReturnValue({ user: null, mature: false, authLoading: false, refresh: vi.fn(), setMature: vi.fn(), signOut: vi.fn() });
    renderWithProviders(<ListControl anime={anime} status={null} rating={null} />, "/anime/7?from=%2Ffor-you");
    fireEvent.click(screen.getByRole("button", { name: "Add Example to My list" }));
    expect(screen.getByRole("link", { name: "Sign in" })).toHaveAttribute("href", "/login?next=%2Fanime%2F7%3Ffrom%3D%252Ffor-you");
  });

  it("loads list state in one batch for the whole result grid and exposes the filled status", async () => {
    const lookup = vi.spyOn(api, "listStatuses").mockResolvedValue({ items: [{ animeId: 7, status: "watching", rating: 6 }] });
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<QueryClientProvider client={client}><ToastProvider><MemoryRouter initialEntries={["/results"]}><PosterGrid animeIds={[7, 8]}>
      <AnimeCard anime={{ id: 7, title: "Example", coverImage: "https://img.test/7.jpg" }} />
      <AnimeCard anime={{ id: 8, title: "Another", coverImage: "https://img.test/8.jpg" }} />
    </PosterGrid></MemoryRouter></ToastProvider></QueryClientProvider>);
    expect(await screen.findByRole("button", { name: /Change list status for Example, Watching/ })).toBeInTheDocument();
    expect(lookup).toHaveBeenCalledTimes(1);
    expect(lookup).toHaveBeenCalledWith([7, 8], false);
  });

  it("closes the status menu on Escape and restores focus to its trigger", () => {
    renderWithProviders(<ListControl anime={anime} status="watching" rating={null} />);
    const trigger = screen.getByRole("button", { name: /Change list status for Example, Watching/ });
    fireEvent.click(trigger);
    const menu = screen.getByRole("menu", { name: "List status for Example" });
    fireEvent.keyDown(menu, { key: "Escape" });
    expect(trigger).toHaveFocus();
    expect(trigger).toHaveAttribute("aria-expanded", "false");
  });
});
