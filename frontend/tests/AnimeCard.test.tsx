import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { AnimeCard } from "../src/components/AnimeCard";
describe("AnimeCard", () => {
  it("shows similarity and a five-star rating separately with metadata", () => {
    render(<MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}><AnimeCard anime={{ id: 7, title: "Example", score: 83, similarity: 0.72, year: 2024, format: "TV", episodes: 12 }} /></MemoryRouter>);
    expect(screen.getAllByRole("link", { name: "Example" }).every((link) => link.getAttribute("href") === "/anime/7")).toBe(true);
    expect(screen.getByLabelText("Similarity: 72%")).toHaveTextContent("72% match");
    expect(screen.getByLabelText("Rating: 4.2 out of 5")).toHaveTextContent("4.2/5");
    expect(screen.getByRole("link", { name: "AniList, Public domain, via Wikimedia Commons" }))
      .toHaveAttribute("href", "https://commons.wikimedia.org/wiki/File:AniList_logo.svg");
    expect(screen.getByText("TV · 2024 · 12 eps")).toBeInTheDocument();
  });
});
