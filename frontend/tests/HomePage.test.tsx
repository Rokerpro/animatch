import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { HomePage } from "@/pages/HomePage";

describe("HomePage Component", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
        },
      },
    });
    vi.restoreAllMocks();
  });

  const renderWithProviders = (ui: React.ReactElement) => {
    return render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter
          future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
        >
          {ui}
        </BrowserRouter>
      </QueryClientProvider>
    );
  };

  it("renders the hero title and loading state initially", () => {
    // Mock fetch that hangs or returns a promise
    globalThis.fetch = vi.fn().mockImplementation(() => new Promise(() => {}));

    renderWithProviders(<HomePage />);

    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
      /AniMatch/i
    );
    expect(screen.getByTestId("health-loading")).toBeInTheDocument();
  });

  it("fetches and renders the health status from the backend successfully", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        status: "ok",
        version: "0.1.0",
        environment: "development",
        database: "connected",
      }),
    } as Response);

    renderWithProviders(<HomePage />);

    await waitFor(() => {
      expect(screen.getByTestId("health-success")).toBeInTheDocument();
    });

    expect(screen.getByText("v0.1.0")).toBeInTheDocument();
    expect(screen.getByText("connected")).toBeInTheDocument();
  });

  it("renders the error alert when backend health check fails", async () => {
    globalThis.fetch = vi.fn().mockRejectedValue(new Error("Network Error"));

    renderWithProviders(<HomePage />);

    await waitFor(() => {
      expect(screen.getByTestId("health-error")).toBeInTheDocument();
    });

    expect(screen.getByText(/Connection Failed/i)).toBeInTheDocument();
    expect(screen.getByText(/Network Error/i)).toBeInTheDocument();
  });
});
