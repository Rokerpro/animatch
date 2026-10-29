import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, useLocation } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { FilterBar } from "../src/components/FilterBar";
function LocationText() { const location = useLocation(); return <output>{location.search}</output>; }
describe("FilterBar", () => {
  it("sets URL filters and exposes removable chips and clear all", () => {
    render(<MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }} initialEntries={["/browse"]}><FilterBar options={{ genres: ["Action"], tags: ["Time Loop"] }} /><LocationText /></MemoryRouter>);
    fireEvent.change(screen.getByLabelText("Genre"), { target: { value: "Action" } });
    expect(screen.getByText("?genres=Action")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Action/ })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Clear all" }));
    expect(document.querySelector("output")?.textContent).toBe("");
  });
});
