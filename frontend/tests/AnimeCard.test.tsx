import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { AnimeCard } from "../src/components/AnimeCard";
describe("AnimeCard", () => {
  it("shows a poster link, neutral percentage score, and metadata", () => {
    render(<MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}><AnimeCard anime={{ id: 7, title: "Example", score: 83, year: 2024, format: "TV", episodes: 12 }} /></MemoryRouter>);
    expect(screen.getByRole("link", { name: "Example" })).toHaveAttribute("href", "/anime/7");
    expect(screen.getByLabelText("Score: 83%")).toHaveTextContent("83%");
    expect(screen.getByText("TV · 2024 · 12 eps")).toBeInTheDocument();
  });
});
