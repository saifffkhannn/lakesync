import { useEffect, useState } from "react";
import { CheckCircle, XCircle, Info, X } from "lucide-react";

export interface ToastData {
  id: string;
  message: string;
  type: "success" | "error" | "info";
}

// Global toast state
let toastListeners: ((toasts: ToastData[]) => void)[] = [];
let toasts: ToastData[] = [];

const setToasts = (newToasts: ToastData[]) => {
  toasts = newToasts;
  toastListeners.forEach((listener) => listener(toasts));
};

export const showToast = (message: string, type: ToastData["type"] = "success") => {
  const id = Date.now().toString() + Math.random().toString(36).slice(2);
  const newToast: ToastData = { id, message, type };
  setToasts([...toasts, newToast]);

  // Auto-dismiss after 4 seconds
  setTimeout(() => {
    setToasts(toasts.filter((t) => t.id !== id));
  }, 4000);
};

const iconMap = {
  success: <CheckCircle className="w-5 h-5 text-emerald-400" />,
  error: <XCircle className="w-5 h-5 text-red-400" />,
  info: <Info className="w-5 h-5 text-blue-400" />,
};

const bgMap = {
  success: "bg-emerald-50 dark:bg-emerald-900/30 border-emerald-200 dark:border-emerald-800",
  error: "bg-red-50 dark:bg-red-900/30 border-red-200 dark:border-red-800",
  info: "bg-blue-50 dark:bg-blue-900/30 border-blue-200 dark:border-blue-800",
};

const ToastContainer = () => {
  const [currentToasts, setCurrentToasts] = useState<ToastData[]>([]);

  useEffect(() => {
    const listener = (t: ToastData[]) => setCurrentToasts([...t]);
    toastListeners.push(listener);
    return () => {
      toastListeners = toastListeners.filter((l) => l !== listener);
    };
  }, []);

  const dismiss = (id: string) => {
    setToasts(toasts.filter((t) => t.id !== id));
  };

  if (currentToasts.length === 0) return null;

  return (
    <div className="fixed top-4 right-4 z-[9999] flex flex-col gap-3 max-w-sm">
      {currentToasts.map((toast) => (
        <div
          key={toast.id}
          className={`flex items-center gap-3 px-4 py-3 rounded-xl border shadow-lg backdrop-blur-sm
            animate-slideIn ${bgMap[toast.type]}`}
        >
          {iconMap[toast.type]}
          <span className="text-sm font-medium text-gray-800 dark:text-gray-100 flex-1">
            {toast.message}
          </span>
          <button
            onClick={() => dismiss(toast.id)}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      ))}
    </div>
  );
};

export default ToastContainer;
