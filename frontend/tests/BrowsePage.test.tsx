import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
const mocks = vi.hoisted(() => ({ useAnime: vi.fn(), useFilters: vi.fn(), useAuth: vi.fn() }));
vi.mock("../src/api/hooks", () => ({ useAnime: mocks.useAnime, useFilters: mocks.useFilters }));
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
    render(<MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }} initialEntries={["/browse?genres=Action&page=1"]}><Routes><Route path="/browse" element={<><BrowsePage /><LocationText /></>} /></Routes></MemoryRouter>);
    expect(screen.getByText("40 anime")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "2" }));
    expect(screen.getByText("?genres=Action&page=2")).toBeInTheDocument();
  });
});
