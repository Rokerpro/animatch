import {
  useCallback,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { CircleAlert, CircleCheck, Info } from "lucide-react";
import { ToastContext, type ToastKind, type ToastMessage } from "./ToastContext";

let nextToastId = 0;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const showToast = useCallback((message: string, kind: ToastKind = "info") => {
    const id = ++nextToastId;
    setToasts((current) => [...current, { id, message, kind }]);
    window.setTimeout(() => {
      setToasts((current) => current.filter((toast) => toast.id !== id));
    }, 3500);
  }, []);

  const value = useMemo(() => ({ showToast }), [showToast]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div aria-live="polite" className="toast-viewport">
        {toasts.map((toast) => (
          <div
            className={`toast toast-${toast.kind}`}
            key={toast.id}
            role={toast.kind === "error" ? "alert" : "status"}
          >
            <span aria-hidden="true" className="toast-icon">
              {toast.kind === "error" ? <CircleAlert size={17} /> : toast.kind === "success" ? <CircleCheck size={17} /> : <Info size={17} />}
            </span>
            {toast.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
