import type { Recommendation } from "./api/types";

export const QUIZ_STORAGE_KEY = "animatch.phase5.v1";
export interface SavedQuiz { answers: Record<string, string>; results: Recommendation[]; includeMature: boolean }
let memoryFallback: SavedQuiz | null = null;
let storageUnavailable = false;

export function readSavedQuiz(): SavedQuiz | null {
  try {
    if (storageUnavailable) return memoryFallback;
    const raw = localStorage.getItem(QUIZ_STORAGE_KEY);
    if (!raw) return memoryFallback;
    const value: unknown = JSON.parse(raw);
    if (!value || typeof value !== "object") return memoryFallback;
    const saved = value as Partial<SavedQuiz>;
    if (!saved.answers || typeof saved.answers !== "object" || !Array.isArray(saved.results) || typeof saved.includeMature !== "boolean") return memoryFallback;
    return saved as SavedQuiz;
  } catch { return memoryFallback; }
}

export function saveQuiz(value: SavedQuiz): boolean {
  memoryFallback = value;
  try { localStorage.setItem(QUIZ_STORAGE_KEY, JSON.stringify(value)); storageUnavailable = false; return true; } catch { storageUnavailable = true; return false; }
}

export function clearSavedQuiz(): void { memoryFallback = null; storageUnavailable = false; try { localStorage.removeItem(QUIZ_STORAGE_KEY); } catch { storageUnavailable = true; /* Storage may be unavailable. */ } }
