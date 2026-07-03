import { createContext, useCallback, useContext, useState, type ReactNode } from 'react';
import './Toast.css';

type ToastType = 'error' | 'success' | 'warning';

interface Toast {
  id: number;
  message: string;
  type: ToastType;
}

interface ToastContextValue {
  showToast: (message: string, type?: ToastType) => void;
}

const ToastContext = createContext<ToastContextValue>({
  showToast: () => {},
});

let nextId = 0;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const showToast = useCallback((message: string, type: ToastType = 'error') => {
    const id = nextId++;
    setToasts(prev => [...prev, { id, message, type }]);
    // Success/warning notices expire on their own; errors and warnings
    // about failures stay until dismissed — if a save failed while the
    // user glanced away, the evidence must still be there.
    if (type === 'success') {
      setTimeout(() => {
        setToasts(prev => prev.filter(t => t.id !== id));
      }, 5000);
    }
  }, []);

  const dismiss = useCallback((id: number) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      {toasts.length > 0 && (
        // aria-live lets screen readers announce toasts when they appear
        <div className="toast-container" role="status" aria-live="polite">
          {toasts.map(toast => (
            <div key={toast.id} className={`toast toast--${toast.type}`}>
              <span className="toast__message">{toast.message}</span>
              <button className="toast__dismiss" onClick={() => dismiss(toast.id)} aria-label="Dismiss">
                &times;
              </button>
            </div>
          ))}
        </div>
      )}
    </ToastContext.Provider>
  );
}

export function useToast() {
  return useContext(ToastContext);
}
