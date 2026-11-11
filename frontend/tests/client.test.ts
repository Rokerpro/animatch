import { afterEach, describe, expect, it, vi } from "vitest";
import { api, apiDetailMessage, normalizeApiBaseUrl } from "../src/api/client";
afterEach(() => vi.restoreAllMocks());
describe("API client", () => {
  it("normalizes the configured /api proxy prefix without duplicating it", () => {
    expect(normalizeApiBaseUrl("/api")).toBe("");
    expect(normalizeApiBaseUrl("http://localhost:8000/api/")).toBe("http://localhost:8000");
  });
  it("formats string and validation-array details without exposing locations", () => {
    expect(apiDetailMessage("Invalid selection")).toBe("Invalid selection");
    expect(apiDetailMessage([
      { loc: ["body", "liked_ids", 5], msg: "At most 5 items", type: "too_long" },
      { loc: ["body", "limit"], msg: "Must be positive", type: "greater_than" },
    ])).toBe("At most 5 items; Must be positive");
    expect(apiDetailMessage([{ loc: ["body", "secret"], type: "error" }], "Request failed")).toBe("Request failed");
  });
  it("sends includeMature for catalog, recommendation, list, and batch status requests", async () => {
    const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async () => new Response("{}", { status: 200, headers: { "Content-Type": "application/json" } }));
    await api.anime({ includeMature: true });
    await api.filters(true);
    await api.detail(2, true);
    await api.similar(2, true);
    await api.myRecommendations(true);
    await api.list({ sort: "updated", page: 1, pageSize: 24, includeMature: true });
    await api.listStatuses([1, 2, 3], true);
    const urls = fetch.mock.calls.map(([input]) => String(input));
    expect(urls).toHaveLength(7);
    expect(urls.every((url) => new URL(url, "http://localhost").searchParams.get("includeMature") === "true")).toBe(true);
    expect(urls[4]).toContain("/api/recs/me?includeMature=true");
    expect(urls[5]).toContain("/api/list?");
    expect(new URL(urls[5], "http://localhost").searchParams.get("pageSize")).toBe("24");
    expect(urls[6]).toContain("/api/list/statuses?ids=1,2,3&includeMature=true");
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
  it("extracts messages from FastAPI validation details", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async () => new Response(JSON.stringify({ detail: [
      { loc: ["body", "liked_ids", 5], msg: "At most 5 items", type: "too_long" },
      { loc: ["body", "limit"], msg: "Must be positive", type: "greater_than" },
    ] }), { status: 422, headers: { "Content-Type": "application/json" } }));
    await expect(api.startRecommendations([1, 2, 3], false)).rejects.toMatchObject({
      message: "At most 5 items; Must be positive",
      status: 422,
    });
  });

  it("uses documented list paths, snake_case entry payloads, CSRF headers, and list casing", async () => {
    const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith("/api/auth/csrf")) return new Response(JSON.stringify({ csrf_token: "csrf-value" }), { status: 200, headers: { "Content-Type": "application/json" } });
      return new Response(JSON.stringify({ items: [] }), { status: 200, headers: { "Content-Type": "application/json" } });
    });
    await api.listStatuses([12, 34], false);
    await api.updateListEntry(12, { status: "completed", rating: 9 });
    await api.deleteListEntry(12);
    expect(String(fetch.mock.calls[0][0])).toBe("/api/list/statuses?ids=12,34&includeMature=false");
    const put = fetch.mock.calls.find(([, init]) => init?.method === "PUT");
    expect(String(put?.[0])).toBe("/api/list/12");
    expect(put?.[1]?.headers).toMatchObject({ "X-CSRF-Token": "csrf-value" });
    expect(JSON.parse(String(put?.[1]?.body))).toEqual({ status: "completed", rating: 9 });
    const deletion = fetch.mock.calls.find(([, init]) => init?.method === "DELETE");
    expect(String(deletion?.[0])).toBe("/api/list/12");
    expect(deletion?.[1]?.headers).toMatchObject({ "X-CSRF-Token": "csrf-value" });
  });
  it("uploads MAL export bytes raw with the CSRF header and binary content type", async () => {
    const file = new File(["<myanimelist />"], "list.xml", { type: "application/xml" });
    const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      if (String(input).endsWith("/api/auth/csrf")) return new Response(JSON.stringify({ csrf_token: "csrf-value" }), { status: 200, headers: { "Content-Type": "application/json" } });
      return new Response(JSON.stringify({ total_entries: 0, to_import: 0, skipped_existing: 0, unmatched_count: 0, unmatched: [] }), { status: 200, headers: { "Content-Type": "application/json" } });
    });
    await api.importMALList(file, true);
    const [url, init] = fetch.mock.calls.find(([input]) => String(input).includes("/api/list/import"))!;
    expect(String(url)).toBe("/api/list/import?dry_run=true");
    expect(init?.method).toBe("POST");
    expect(init?.body).toBe(file);
    expect(init?.headers).toMatchObject({ "X-CSRF-Token": "csrf-value", "Content-Type": "application/octet-stream" });
  });
  it("posts only quiz_answers to Find something new with a CSRF header", async () => {
    const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      if (String(input).endsWith("/api/auth/csrf")) return new Response(JSON.stringify({ csrf_token: "csrf-new" }), { status: 200, headers: { "Content-Type": "application/json" } });
      return new Response(JSON.stringify({ results: [], mode: "quiz_fallback" }), { status: 200, headers: { "Content-Type": "application/json" } });
    });
    await api.newRecommendations({ quiz_answers: { mood: "epic", era: "recent" } });
    const [url, init] = fetch.mock.calls.find(([input]) => String(input).endsWith("/api/recs/new"))!;
    expect(String(url)).toBe("/api/recs/new");
    expect(init?.method).toBe("POST");
    expect(init?.headers).toMatchObject({ "X-CSRF-Token": "csrf-new" });
    expect(JSON.parse(String(init?.body))).toEqual({ quiz_answers: { mood: "epic", era: "recent" } });
  });
});
