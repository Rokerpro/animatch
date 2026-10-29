import { createContext } from "react";

export type ToastKind = "success" | "error" | "info";
export type ToastMessage = { id: number; message: string; kind: ToastKind };
export type ToastContextValue = {
  showToast: (message: string, kind?: ToastKind) => void;
};

export const ToastContext = createContext<ToastContextValue | null>(null);
