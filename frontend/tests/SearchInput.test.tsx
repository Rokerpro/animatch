import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, useLocation } from "react-router-dom";
import { SearchInput } from "@/components/SearchInput";

function LocationProbe() {
  const location = useLocation();
  return (
    <output data-testid="location">
      {location.pathname}
      {location.search}
    </output>
  );
}

describe("SearchInput", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("debounces navigation to the browse query URL", async () => {
    render(
      <MemoryRouter
        future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
        initialEntries={["/"]}
      >
        <SearchInput />
        <LocationProbe />
      </MemoryRouter>
    );

    fireEvent.change(screen.getByRole("searchbox", { name: "Search titles" }), {
      target: { value: "Frieren" },
    });

    await act(async () => vi.advanceTimersByTime(299));
    expect(screen.getByTestId("location")).toHaveTextContent("/");

    await act(async () => vi.advanceTimersByTime(1));
    expect(screen.getByTestId("location")).toHaveTextContent(
      "/browse?q=Frieren"
    );
  });
});
