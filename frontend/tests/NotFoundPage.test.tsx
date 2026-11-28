import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { NotFoundPage } from "../src/pages/NotFoundPage";

vi.mock("../src/api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../src/api/client")>();
  return {
    ...actual,
    api: {
      ...actual.api,
      anime: vi.fn().mockResolvedValue({ items: [], pageInfo: {} }),
    },
  };
});

describe("not found page", () => {
  it("explains the dead link and offers a way back", () => {
    render(
      <QueryClientProvider client={new QueryClient()}>
        <MemoryRouter>
          <NotFoundPage />
        </MemoryRouter>
      </QueryClientProvider>
    );
    expect(
      screen.getByRole("heading", { name: "Page not found" })
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Go home" })).toHaveAttribute(
      "href",
      "/"
    );
    expect(screen.getByRole("link", { name: "Browse anime" })).toHaveAttribute(
      "href",
      "/browse"
    );
    expect(screen.getByRole("link", { name: "Take the quiz" })).toHaveAttribute(
      "href",
      "/quiz"
    );
  });
});
