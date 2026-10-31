export function safeNextPath(candidate: string | null, fallback = "/browse"): string {
  if (!candidate || !candidate.startsWith("/") || candidate.startsWith("//")) return fallback;
  try { return new URL(candidate, window.location.origin).origin === window.location.origin ? candidate : fallback; }
  catch { return fallback; }
}
