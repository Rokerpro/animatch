import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { RecommendationCard } from "../src/components/RecommendationCard";
describe("RecommendationCard", () => {
  it("renders the exact reason returned by the API", () => {
    render(<MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}><RecommendationCard recommendation={{ id: 9, title: "Similar", reason: "Shares a high-ranked theme" }} /></MemoryRouter>);
    expect(screen.getByText("Shares a high-ranked theme")).toBeInTheDocument();
  });
  it("does not invent explanation text when the reason is empty", () => {
    render(<MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}><RecommendationCard recommendation={{ id: 9, title: "Similar", reason: "" }} /></MemoryRouter>);
    expect(screen.queryByText("This recommendation is similar because…")).not.toBeInTheDocument();
  });
  it("shows a shortened reason with a More button that expands the full text", () => {
    const reason = "Matches Sci-fi / technology (Sci-Fi) and Epic / action-packed (Super Power, Adventure) and Fast-paced / action-focused (Action, Adventure).";
    render(<MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}><RecommendationCard recommendation={{ id: 9, title: "Similar", reason }} /></MemoryRouter>);
    expect(screen.getByText(/…/)).toBeInTheDocument();
    const more = screen.getByRole("button", { name: "More" });
    const reasonText = more.closest(".reason-text");
    expect(more).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(more);
    expect(reasonText).toHaveTextContent(reason);
    expect(screen.getByRole("button", { name: "Less" })).toHaveAttribute("aria-expanded", "true");
  });
});
