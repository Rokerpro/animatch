import "@testing-library/jest-dom/vitest";
import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

const storageValues = new Map<string, string>();
Object.defineProperty(globalThis, "localStorage", { configurable: true, value: {
  getItem: (key: string) => storageValues.get(key) ?? null,
  setItem: (key: string, value: string) => { storageValues.set(key, String(value)); },
  removeItem: (key: string) => { storageValues.delete(key); },
  clear: () => storageValues.clear(),
} });

// Automatically cleanup DOM after each test
afterEach(() => {
  cleanup();
});
