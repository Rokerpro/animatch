import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, expect, it, vi } from "vitest";
import { AnimeCard } from "../src/components/AnimeCard";
vi.mock("../src/auth/useAuth", () => ({ useAuth: () => ({ mature: false, user: null }) }));
describe("AnimeCard", () => {
  it("shows similarity and a five-star rating separately with metadata", () => {
    const queryClient = new QueryClient();
    render(<QueryClientProvider client={queryClient}><MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}><AnimeCard anime={{ id: 7, title: "Example", coverImage: "https://img.test/7.jpg", score: 83, similarity: 0.72, year: 2024, format: "TV", episodes: 12 }} /></MemoryRouter></QueryClientProvider>);
    expect(screen.getAllByRole("link", { name: "Example" }).every((link) => link.getAttribute("href") === "/anime/7")).toBe(true);
    expect(screen.getByLabelText("Similarity: 72%")).toHaveTextContent("72% match");
    expect(screen.getByLabelText("Rating: 4.2 out of 5")).toHaveTextContent("4.2/5");
    const posterBadges = document.querySelector(".poster-badges");
    expect(posterBadges?.children[0]).toHaveTextContent("72% match");
    expect(posterBadges?.children[1]).toHaveTextContent("4.2/5");
    expect(screen.getByRole("button", { name: "Add Example to My list" }).closest(".anime-save-control"))
      .toBeInTheDocument();
    expect(screen.getByRole("link", { name: "AniList, Public domain, via Wikimedia Commons" }))
      .toHaveAttribute("href", "https://commons.wikimedia.org/wiki/File:AniList_logo.svg");
    expect(screen.getByText("TV · 2024 · 12 eps")).toBeInTheDocument();
  });
});
