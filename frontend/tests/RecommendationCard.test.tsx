import { render, screen } from "@testing-library/react";
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
});
