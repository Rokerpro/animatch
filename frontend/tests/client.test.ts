import { afterEach, describe, expect, it, vi } from "vitest";
import { api, normalizeApiBaseUrl } from "../src/api/client";
afterEach(() => vi.restoreAllMocks());
describe("API client", () => {
  it("normalizes the configured /api proxy prefix without duplicating it", () => {
    expect(normalizeApiBaseUrl("/api")).toBe("");
    expect(normalizeApiBaseUrl("http://localhost:8000/api/")).toBe("http://localhost:8000");
  });
  it("sends includeMature for each catalog and recommendation request", async () => {
    const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async () => new Response("{}", { status: 200, headers: { "Content-Type": "application/json" } }));
    await api.anime({ includeMature: true });
    await api.filters(true);
    await api.detail(2, true);
    await api.similar(2, true);
    const urls = fetch.mock.calls.map(([input]) => String(input));
    expect(urls).toHaveLength(4);
    expect(urls.every((url) => new URL(url).searchParams.get("includeMature") === "true")).toBe(true);
    expect(fetch.mock.calls.every(([, init]) => init?.credentials === "include")).toBe(true);
  });
});
