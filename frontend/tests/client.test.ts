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
  it("sends the exact snake_case start body and preserves the server validation message", async () => {
    const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async () => new Response("[]", { status: 200, headers: { "Content-Type": "application/json" } }));
    await api.startRecommendations([11, 22, 33], true);
    const [url, init] = fetch.mock.calls[0];
    expect(String(url)).toContain("/api/recs/start");
    expect(init?.method).toBe("POST");
    expect(JSON.parse(String(init?.body))).toEqual({ liked_ids: [11, 22, 33], include_mature: true });

    fetch.mockImplementationOnce(async () => new Response(JSON.stringify({ detail: "Liked titles share a franchise." }), { status: 422, headers: { "Content-Type": "application/json" } }));
    await expect(api.startRecommendations([11, 22, 33], false)).rejects.toMatchObject({
      message: "Liked titles share a franchise.",
      status: 422,
    });
  });
});
