import type { Recommendation } from "./api/types";

export const START_STORAGE_KEY = "animatch.start.v1";

export interface SavedStart {
  liked_ids: number[];
  results: Recommendation[];
  include_mature: boolean;
  profile_saved_for?: number;
}

let memoryFallback: SavedStart | null = null;
let storageUnavailable = false;

export function readSavedStart(): SavedStart | null {
  try {
    if (storageUnavailable) return memoryFallback;
    const raw = localStorage.getItem(START_STORAGE_KEY);
    if (!raw) return memoryFallback;
    const value: unknown = JSON.parse(raw);
    if (!value || typeof value !== "object") return memoryFallback;
    const saved = value as Partial<SavedStart>;
    if (
      !Array.isArray(saved.liked_ids) ||
      !saved.liked_ids.every((id) => Number.isInteger(id)) ||
      !Array.isArray(saved.results) ||
      typeof saved.include_mature !== "boolean"
    ) {
      return memoryFallback;
    }
    return saved as SavedStart;
  } catch {
    return memoryFallback;
  }
}

export function saveStart(value: SavedStart): boolean {
  memoryFallback = value;
  try {
    localStorage.setItem(START_STORAGE_KEY, JSON.stringify(value));
    storageUnavailable = false;
    return true;
  } catch {
    storageUnavailable = true;
    return false;
  }
}

export function markStartProfileSaved(userId: number): void {
  const saved = readSavedStart();
  if (saved) saveStart({ ...saved, profile_saved_for: userId });
}

export function clearSavedStart(): void {
  memoryFallback = null;
  storageUnavailable = false;
  try {
    localStorage.removeItem(START_STORAGE_KEY);
  } catch {
    storageUnavailable = true;
  }
}
