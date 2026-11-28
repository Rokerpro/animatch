import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, expect, it, vi } from "vitest";
import { AnimeCard } from "../src/components/AnimeCard";
vi.mock("../src/auth/useAuth", () => ({
  useAuth: () => ({ mature: false, user: null }),
}));
describe("AnimeCard", () => {
  it("shows the match, its bar and the score out of five under the poster", () => {
    const queryClient = new QueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <AnimeCard
            anime={{
              id: 7,
              title: "Example",
              coverImage: "https://img.test/7.jpg",
              score: 83,
              similarity: 0.72,
              year: 2024,
              format: "TV",
              episodes: 12,
            }}
          />
        </MemoryRouter>
      </QueryClientProvider>
    );
    expect(
      screen
        .getAllByRole("link", { name: "Example" })
        .every((link) => link.getAttribute("href") === "/anime/7")
    ).toBe(true);
    expect(screen.getByLabelText("Similarity: 72%")).toHaveTextContent(
      "72% match"
    );
    expect(screen.getByLabelText("Rating: 4.2 out of 5")).toHaveTextContent(
      "4.2"
    );
    // Match and score sit under the poster, above a bar filled to the match.
    const matchRow = document.querySelector(".card-match-row");
    expect(matchRow?.children[0]).toHaveTextContent("72% match");
    expect(matchRow?.children[1]).toHaveTextContent("4.2");
    expect(
      document.querySelector<HTMLElement>(".card-match-track > span")?.style
        .width
    ).toBe("72%");
    expect(
      screen
        .getByRole("button", { name: "Add Example to My list" })
        .closest(".anime-save-control")
    ).toBeInTheDocument();
    expect(screen.getByText("TV, 2024, 12 eps")).toBeInTheDocument();
  });
});
