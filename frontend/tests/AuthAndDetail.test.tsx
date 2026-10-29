import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";
const mocks = vi.hoisted(() => ({ useAnimeDetail: vi.fn(), useSimilar: vi.fn(), useAuth: vi.fn(), useProviders: vi.fn() }));
vi.mock("../src/api/hooks", () => ({ useAnimeDetail: mocks.useAnimeDetail, useSimilar: mocks.useSimilar, useProviders: mocks.useProviders }));
vi.mock("../src/auth/useAuth", () => ({ useAuth: mocks.useAuth }));
import { ApiError, api } from "../src/api/client";
import { ToastProvider } from "../src/components/ToastProvider";
import { LoginPage } from "../src/pages/AuthPages";
import { AnimeDetailPage } from "../src/pages/AnimeDetailPage";
describe("auth and detail states", () => {
  beforeEach(() => {
    mocks.useAuth.mockReturnValue({ mature: false, user: null, refresh: vi.fn().mockResolvedValue(undefined) });
    mocks.useProviders.mockReturnValue({ data: { google: false } });
  });
  it("shows the exact detail 404 message", () => {
    mocks.useAnimeDetail.mockReturnValue({ isLoading: false, isError: true, error: new ApiError("hidden", 404) });
    mocks.useSimilar.mockReturnValue({ isLoading: true });
    render(<MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }} initialEntries={["/anime/4"]}><Routes><Route path="/anime/:id" element={<AnimeDetailPage />} /></Routes></MemoryRouter>);
    expect(screen.getByText("Not found, or hidden by your content settings")).toBeInTheDocument();
  });
  it("submits the login form and hides Google when it is not configured", async () => {
    const login = vi.spyOn(api, "login").mockResolvedValue({ id: 1, email: "a@b.com", display_name: "A", show_mature: false, created_at: "today" });
    const queryClient = new QueryClient();
    render(<QueryClientProvider client={queryClient}><ToastProvider><MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}><Routes><Route path="*" element={<LoginPage />} /></Routes></MemoryRouter></ToastProvider></QueryClientProvider>);
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "a@b.com" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "secret" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
    await waitFor(() => expect(login).toHaveBeenCalledWith({ email: "a@b.com", password: "secret" }));
    expect(screen.queryByRole("link", { name: "Continue with Google" })).not.toBeInTheDocument();
  });
});
