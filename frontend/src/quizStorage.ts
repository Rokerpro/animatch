import type { AnimeCardData, Recommendation } from "./api/types";

export const QUIZ_STORAGE_KEY = "animatch.phase5.v1";
export interface SavedQuiz { answers: Record<string, string>; results: Recommendation[]; includeMature: boolean; profileSavedFor?: number }
export interface QuizDraft {
  answers: Record<string, string>;
  step: number;
  selectedMany: string[];
  pickedTitles: AnimeCardData[];
}
let memoryFallback: SavedQuiz | null = null;
let draftMemoryFallback: QuizDraft | null = null;
let storageUnavailable = false;

function readStorageValue(): Record<string, unknown> {
  try {
    const value: unknown = JSON.parse(localStorage.getItem(QUIZ_STORAGE_KEY) ?? "{}");
    return value && typeof value === "object" ? value as Record<string, unknown> : {};
  } catch {
    return {};
  }
}

export function readQuizDraft(): QuizDraft | null {
  try {
    if (storageUnavailable) return draftMemoryFallback;
    const draft = readStorageValue().draft as Partial<QuizDraft> | undefined;
    if (
      !draft ||
      !draft.answers || typeof draft.answers !== "object" ||
      !Number.isInteger(draft.step) || (draft.step ?? -1) < 0 ||
      !Array.isArray(draft.selectedMany) || !draft.selectedMany.every((item) => typeof item === "string") ||
      !Array.isArray(draft.pickedTitles) || !draft.pickedTitles.every((item) => item && Number.isInteger(item.id) && typeof item.title === "string")
    ) return draftMemoryFallback;
    return draft as QuizDraft;
  } catch {
    return draftMemoryFallback;
  }
}

export function saveQuizDraft(draft: QuizDraft): boolean {
  draftMemoryFallback = draft;
  try {
    localStorage.setItem(QUIZ_STORAGE_KEY, JSON.stringify({ ...readStorageValue(), draft }));
    storageUnavailable = false;
    return true;
  } catch {
    storageUnavailable = true;
    return false;
  }
}

export function clearQuizDraft(): void {
  draftMemoryFallback = null;
  try {
    const saved = readStorageValue();
    delete saved.draft;
    if (Object.keys(saved).length) localStorage.setItem(QUIZ_STORAGE_KEY, JSON.stringify(saved));
    else localStorage.removeItem(QUIZ_STORAGE_KEY);
  } catch {
    storageUnavailable = true;
  }
}

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
  draftMemoryFallback = null;
  try { localStorage.setItem(QUIZ_STORAGE_KEY, JSON.stringify(value)); storageUnavailable = false; return true; } catch { storageUnavailable = true; return false; }
}

export function markQuizProfileSaved(userId: number): void {
  const saved = readSavedQuiz();
  if (saved) saveQuiz({ ...saved, profileSavedFor: userId });
}

export function clearSavedQuiz(): void { memoryFallback = null; draftMemoryFallback = null; storageUnavailable = false; try { localStorage.removeItem(QUIZ_STORAGE_KEY); } catch { storageUnavailable = true; /* Storage may be unavailable. */ } }
