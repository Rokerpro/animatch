import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, useLocation } from "react-router-dom";
import { LayoutGrid } from "lucide-react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useAuth } from "../src/auth/useAuth";
import { HeaderTabs } from "../src/components/HeaderTabs";

vi.mock("../src/auth/useAuth", () => ({ useAuth: vi.fn() }));

const titles: Record<number, { title: string; isAdult?: boolean }> = {
  7: { title: "Example" },
  9: { title: "Grown up", isAdult: true },
};
vi.mock("../src/api/hooks", () => ({
  useAnimeDetail: (id: number) => ({
    data: titles[id] && {
      id,
      coverImage: `https://img.test/${id}.jpg`,
      coverColor: "#223344",
      ...titles[id],
    },
  }),
}));

function Where() {
  return <output data-testid="path">{useLocation().pathname}</output>;
}

function renderTabs(path: string, mature = false, quiet = false) {
  vi.mocked(useAuth).mockReturnValue({
    user: null,
    mature,
    authLoading: false,
    refresh: vi.fn(),
    setMature: vi.fn(),
    signOut: vi.fn(),
  });
  return render(
    <MemoryRouter initialEntries={[path]}>
      <HeaderTabs
        quiet={quiet}
        pageLinks={[
          { to: "/browse", label: "Browse", className: "", Icon: LayoutGrid },
        ]}
      />
      <Where />
    </MemoryRouter>
  );
}

beforeEach(() => localStorage.clear());

describe("header tabs", () => {
  it("opens a tab for an anime page and keeps it across visits", () => {
    const { unmount } = renderTabs("/anime/7");
    expect(screen.getByRole("link", { name: "Example" })).toHaveAttribute(
      "aria-current",
      "page"
    );
    unmount();
    renderTabs("/similar/7");
    expect(screen.getByRole("link", { name: "Example" })).not.toHaveAttribute(
      "aria-current"
    );
    expect(screen.getByRole("link", { name: "Like Example" })).toHaveAttribute(
      "aria-current",
      "page"
    );
  });

  it("moves to a neighbour, then to Browse, when the active tab closes", () => {
    localStorage.setItem(
      "animatch.openTabs",
      JSON.stringify([
        { path: "/anime/7", kind: "anime", title: "Example" },
        { path: "/results", kind: "matches", title: "Your matches" },
      ])
    );
    renderTabs("/anime/7");
    fireEvent.click(screen.getByRole("button", { name: "Close Example" }));
    expect(screen.getByTestId("path")).toHaveTextContent("/results");
    fireEvent.click(screen.getByRole("button", { name: "Close Your matches" }));
    expect(screen.getByTestId("path")).toHaveTextContent("/browse");
  });

  it("hides adult tabs unless mature content is on", () => {
    const { unmount } = renderTabs("/anime/9");
    expect(
      screen.queryByRole("link", { name: "Grown up" })
    ).not.toBeInTheDocument();
    unmount();
    renderTabs("/browse", true);
    expect(screen.getByRole("link", { name: "Grown up" })).toBeVisible();
  });

  it("ignores saved tabs that do not point at a tab route", () => {
    localStorage.setItem(
      "animatch.openTabs",
      JSON.stringify([
        { path: "https://evil.test", kind: "anime", title: "Bad" },
        { path: "/anime/7", kind: "anime", title: "Example" },
      ])
    );
    renderTabs("/browse");
    expect(screen.queryByRole("link", { name: "Bad" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Example" })).toBeVisible();
  });

  it("folds the tabs into a Your tabs menu on the home page", () => {
    localStorage.setItem(
      "animatch.openTabs",
      JSON.stringify([{ path: "/anime/7", kind: "anime", title: "Example" }])
    );
    renderTabs("/", false, true);
    expect(
      screen.queryByRole("link", { name: "Browse" })
    ).not.toBeInTheDocument();
    const button = screen.getByRole("button", { name: /Your tabs/ });
    expect(button).toHaveTextContent("2");
    fireEvent.click(button);
    expect(screen.getByRole("menuitem", { name: "Browse" })).toHaveFocus();
    expect(screen.getByRole("menuitem", { name: "Example" })).toBeVisible();
    fireEvent.keyDown(screen.getByRole("menu"), { key: "Escape" });
    expect(button).toHaveFocus();
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
    fireEvent.click(button);
    fireEvent.click(screen.getByRole("menuitem", { name: "Example" }));
    expect(screen.getByTestId("path")).toHaveTextContent("/anime/7");
  });

  it("lists the page tabs in the Your tabs menu when nothing is open", () => {
    renderTabs("/", false, true);
    const button = screen.getByRole("button", { name: /Your tabs/ });
    expect(button).toHaveTextContent("1");
    fireEvent.click(button);
    expect(
      screen.getAllByRole("menuitem").map((item) => item.textContent)
    ).toEqual(["Browse"]);
  });
});
