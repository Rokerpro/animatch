import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "../src/api/client";
import { useAuth } from "../src/auth/useAuth";
import { ToastProvider } from "../src/components/ToastProvider";
import { ListPage } from "../src/pages/ListPage";

vi.mock("../src/auth/useAuth", () => ({ useAuth: vi.fn() }));
const user = { id: 1, email: "a@example.com", display_name: "A", show_mature: true, created_at: "today" };
function response(total = 0, last_page = 1, withItem = false) {
  return { items: withItem ? [{ id: 5, anime_id: 7, anime: { id: 7, title: "Example", coverImage: "https://img.test/7.jpg" }, status: "planning" as const, rating: null, source: "manual" as const, added_at: "today", updated_at: "today" }] : [], page_info: { total, current_page: 1, last_page, per_page: 24, has_next_page: last_page > 1 } };
}
function renderPage(initial = "/list") {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(<QueryClientProvider client={client}><ToastProvider><MemoryRouter initialEntries={[initial]}><Routes><Route path="/list" element={<ListPage />} /><Route path="/login" element={<p>Login screen</p>} /></Routes></MemoryRouter></ToastProvider></QueryClientProvider>);
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.spyOn(api, "list").mockResolvedValue(response());
  vi.mocked(useAuth).mockReturnValue({ user, mature: true, authLoading: false, refresh: vi.fn(), setMature: vi.fn(), signOut: vi.fn() });
});

describe("My list page", () => {
  it("redirects signed-out visitors to login without rendering list content", async () => {
    vi.mocked(useAuth).mockReturnValue({ user: null, mature: false, authLoading: false, refresh: vi.fn(), setMature: vi.fn(), signOut: vi.fn() });
    renderPage();
    expect(await screen.findByText("Login screen")).toBeInTheDocument();
    expect(api.list).not.toHaveBeenCalled();
  });

  it("shows the empty state, quiz link, and includes the mature setting in list requests", async () => {
    vi.spyOn(api, "list").mockResolvedValue(response());
    renderPage();
    expect(await screen.findByText(/Your list is empty/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Take the quiz" })).toHaveAttribute("href", "/quiz");
    expect(api.list).toHaveBeenCalledWith({ status: undefined, sort: "updated", page: 1, pageSize: 24, includeMature: true });
  });

  it("supports keyboard status tabs, sorting, numbered pagination, and total count", async () => {
    vi.spyOn(api, "list").mockResolvedValue(response(49, 3, true));
    renderPage("/list?page=2");
    expect(await screen.findByText("49 titles")).toBeInTheDocument();
    expect(api.list).toHaveBeenCalledWith({ status: undefined, sort: "updated", page: 2, pageSize: 24, includeMature: true });

    const allTab = screen.getByRole("tab", { name: "All" });
    allTab.focus(); fireEvent.keyDown(allTab, { key: "ArrowRight" });
    await waitFor(() => expect(api.list).toHaveBeenLastCalledWith({ status: "planning", sort: "updated", page: 1, pageSize: 24, includeMature: true }));
    expect(screen.getByRole("tab", { name: "Planning" })).toHaveFocus();

    fireEvent.change(screen.getByRole("combobox", { name: "Sort list" }), { target: { value: "rating" } });
    await waitFor(() => expect(api.list).toHaveBeenLastCalledWith({ status: "planning", sort: "rating", page: 1, pageSize: 24, includeMature: true }));
    fireEvent.click(screen.getByRole("button", { name: "Next" }));
    await waitFor(() => expect(api.list).toHaveBeenLastCalledWith({ status: "planning", sort: "rating", page: 2, pageSize: 24, includeMature: true }));
  });
});
