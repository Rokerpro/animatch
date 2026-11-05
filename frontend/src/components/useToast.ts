import { useContext } from "react";
import { ToastContext } from "./ToastContext";

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used inside ToastProvider");
  }
  return context;
}

export function useOptionalToast() {
  return useContext(ToastContext) ?? { showToast: () => undefined };
}
