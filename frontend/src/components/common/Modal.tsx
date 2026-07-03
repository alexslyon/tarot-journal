import { createContext, useCallback, useContext, useEffect, useRef, useState, type ButtonHTMLAttributes, type ReactNode } from 'react';
import { registerDirty } from '../../utils/dirtyGuard';
import './Modal.css';

// Lets buttons rendered inside a Modal (e.g. a footer "Cancel") close it
// through the same guarded path as the X button / Escape / overlay click,
// so the unsaved-changes confirmation is never bypassed.
const ModalCloseContext = createContext<() => void>(() => {});

/** Guarded close for use inside a Modal: shows the unsaved-changes
 *  confirmation when the modal is dirty instead of closing outright.
 *  Always prefer this over calling the raw onClose prop directly.
 *  NOTE: only works in components rendered *inside* the Modal body
 *  (below the provider) — not in the component that renders <Modal>
 *  itself. For footer Cancel buttons, use <ModalCancelButton>. */
export function useModalClose(): () => void {
  return useContext(ModalCloseContext);
}

/** A footer "Cancel"/"Close" button that closes the enclosing Modal
 *  through the guarded path, so dirty modals still show the
 *  unsaved-changes confirmation. Drop-in replacement for
 *  `<button onClick={onClose}>Cancel</button>`. */
export function ModalCancelButton(
  props: ButtonHTMLAttributes<HTMLButtonElement>,
) {
  const attemptClose = useModalClose();
  return <button type="button" {...props} onClick={attemptClose} />;
}

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  width?: number;
  children: ReactNode;
  /** When true, shows a confirmation dialog before closing */
  isDirty?: boolean;
  /** Custom message for the confirmation dialog */
  confirmMessage?: string;
}

export default function Modal({
  open,
  onClose,
  title,
  width = 700,
  children,
  isDirty = false,
  confirmMessage = 'You have unsaved changes. Are you sure you want to close?',
}: ModalProps) {
  const overlayRef = useRef<HTMLDivElement>(null);
  const [showConfirm, setShowConfirm] = useState(false);

  // Reset confirm dialog when modal closes
  useEffect(() => {
    if (!open) setShowConfirm(false);
  }, [open]);

  // While this modal has unsaved changes, closing the whole app window
  // asks for confirmation too (see utils/dirtyGuard).
  useEffect(() => {
    if (open && isDirty) return registerDirty();
  }, [open, isDirty]);

  const attemptClose = useCallback(() => {
    if (isDirty) {
      setShowConfirm(true);
    } else {
      onClose();
    }
  }, [isDirty, onClose]);

  const confirmClose = () => {
    setShowConfirm(false);
    onClose();
  };

  const cancelClose = () => {
    setShowConfirm(false);
  };

  // Focus trap: keep Tab cycling within the modal
  const contentRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (showConfirm) {
          cancelClose();
        } else {
          attemptClose();
        }
      }
      // Trap focus within modal
      if (e.key === 'Tab' && contentRef.current) {
        const focusable = contentRef.current.querySelectorAll<HTMLElement>(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        if (focusable.length === 0) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (e.shiftKey) {
          if (document.activeElement === first) {
            e.preventDefault();
            last.focus();
          }
        } else {
          if (document.activeElement === last) {
            e.preventDefault();
            first.focus();
          }
        }
      }
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [open, onClose, isDirty, showConfirm]);

  // Auto-focus the modal when it opens
  useEffect(() => {
    if (open && contentRef.current) {
      const firstFocusable = contentRef.current.querySelector<HTMLElement>(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );
      firstFocusable?.focus();
    }
  }, [open]);

  if (!open) return null;

  return (
    <div
      className="modal-overlay"
      ref={overlayRef}
      onMouseDown={(e) => {
        // Only close if mousedown directly on overlay (not dragged from content)
        if (e.target === overlayRef.current) attemptClose();
      }}
    >
      <div
        className="modal-content"
        style={{ maxWidth: width }}
        ref={contentRef}
        role="dialog"
        aria-modal="true"
        aria-label={title || 'Dialog'}
      >
        {title && (
          <div className="modal-header">
            <h2 className="modal-title">{title}</h2>
            <button className="modal-close" onClick={attemptClose} aria-label="Close">&times;</button>
          </div>
        )}
        <div className="modal-body">
          <ModalCloseContext.Provider value={attemptClose}>
            {children}
          </ModalCloseContext.Provider>
        </div>
      </div>

      {/* Confirmation dialog */}
      {showConfirm && (
        <div className="modal-confirm-overlay" onClick={cancelClose}>
          <div className="modal-confirm" onClick={(e) => e.stopPropagation()}>
            <p className="modal-confirm__message">{confirmMessage}</p>
            <div className="modal-confirm__buttons">
              <button onClick={cancelClose}>Keep Editing</button>
              <button className="danger" onClick={confirmClose}>Discard Changes</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
