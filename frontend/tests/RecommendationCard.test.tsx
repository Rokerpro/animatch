import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, expect, it, vi } from "vitest";
import { RecommendationCard } from "../src/components/RecommendationCard";
vi.mock("../src/auth/useAuth", () => ({ useAuth: () => ({ mature: false, user: null }) }));
function renderRecommendation(recommendation: React.ComponentProps<typeof RecommendationCard>["recommendation"]) {
  return render(<QueryClientProvider client={new QueryClient()}><MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}><RecommendationCard recommendation={recommendation} /></MemoryRouter></QueryClientProvider>);
}
describe("RecommendationCard", () => {
  it("renders the exact reason returned by the API", () => {
    renderRecommendation({ id: 9, title: "Similar", coverImage: "https://img.test/9.jpg", reason: "Shares a high-ranked theme" });
    expect(screen.getByText("Shares a high-ranked theme")).toBeInTheDocument();
  });
  it("does not invent explanation text when the reason is empty", () => {
    renderRecommendation({ id: 9, title: "Similar", coverImage: "https://img.test/9.jpg", reason: "" });
    expect(screen.queryByText("This recommendation is similar because…")).not.toBeInTheDocument();
  });
  it("shows a shortened reason with a More button that expands the full text", () => {
    const reason = "Matches Sci-fi / technology (Sci-Fi) and Epic / action-packed (Super Power, Adventure) and Fast-paced / action-focused (Action, Adventure).";
    renderRecommendation({ id: 9, title: "Similar", coverImage: "https://img.test/9.jpg", reason });
    expect(screen.getByText(/…/)).toBeInTheDocument();
    const more = screen.getByRole("button", { name: "More" });
    const reasonText = more.closest(".reason-text");
    expect(more).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(more);
    expect(reasonText).toHaveTextContent(reason);
    expect(screen.getByRole("button", { name: "Less" })).toHaveAttribute("aria-expanded", "true");
  });
});
