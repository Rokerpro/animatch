import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";
const mocks = vi.hoisted(() => ({ useAnime: vi.fn(), useFilters: vi.fn(), useAuth: vi.fn() }));
vi.mock("../src/api/hooks", () => ({ useAnime: mocks.useAnime, useFilters: mocks.useFilters, useAnimeDetail: () => ({ data: undefined }), useListStatuses: () => ({ data: { items: [] }, isLoading: false }) }));
vi.mock("../src/auth/useAuth", () => ({ useAuth: mocks.useAuth }));
import { BrowsePage } from "../src/pages/BrowsePage";
function LocationText() { return <output>{useLocation().search}</output>; }
describe("BrowsePage URL state", () => {
  beforeEach(() => {
    mocks.useAuth.mockReturnValue({ mature: false });
    mocks.useFilters.mockReturnValue({ data: { genres: ["Action"], tags: [] } });
    mocks.useAnime.mockReturnValue({ isLoading: false, isError: false, data: { items: [{ id: 1, title: "Example" }], pageInfo: { total: 40, currentPage: 1, lastPage: 2, perPage: 24, hasNextPage: true } } });
  });
  it("reads filters and page from the URL and keeps filters when changing page", () => {
    render(<QueryClientProvider client={new QueryClient()}><MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }} initialEntries={["/browse?genres=Action&page=1"]}><Routes><Route path="/browse" element={<><BrowsePage /><LocationText /></>} /></Routes></MemoryRouter></QueryClientProvider>);
    expect(screen.getByText("40 anime")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "2" }));
    expect(screen.getByText("?genres=Action&page=2")).toBeInTheDocument();
  });
  it("keeps secondary filters collapsed and shows their active count on the toggle", () => {
    mocks.useFilters.mockReturnValue({ data: { genres: ["Action"], tags: ["Thriller"] } });
    render(<QueryClientProvider client={new QueryClient()}><MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }} initialEntries={["/browse?genres=Action&tags=Thriller&yearMin=2021&status=FINISHED"]}><Routes><Route path="/browse" element={<BrowsePage />} /></Routes></MemoryRouter></QueryClientProvider>);

    const toggle = screen.getByRole("button", { name: /More filters 4/ });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("group", { name: "Genre" })).not.toBeInTheDocument();

    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("group", { name: "Genre" })).toBeInTheDocument();
    expect(screen.getByRole("group", { name: "Tags" })).toBeInTheDocument();
    expect(screen.getByLabelText("Year from")).toHaveValue(2021);
    expect(screen.getByLabelText("Status")).toHaveValue("FINISHED");
  });
});
