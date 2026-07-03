import { useEffect, useRef, useState } from 'react';
import './ConfirmDialog.css';

export interface ConfirmOptions {
  message: string;
  title?: string;
  /** Label for the confirming button (default "OK") */
  confirmLabel?: string;
  cancelLabel?: string;
  /** Style the confirm button as destructive (default true — most
   *  confirmations in this app guard deletions) */
  danger?: boolean;
}

type Resolver = (result: boolean) => void;
let hostListener: ((opts: ConfirmOptions, resolve: Resolver) => void) | null = null;

/** Themed drop-in replacement for window.confirm().
 *
 *  Usage: `if (!(await confirmDialog('Delete this entry?'))) return;`
 *
 *  Renders through the ConfirmDialogHost mounted in App, so it matches
 *  the app's theme instead of the OS-native popup. Falls back to
 *  window.confirm if the host isn't mounted (never in practice). */
export function confirmDialog(opts: ConfirmOptions | string): Promise<boolean> {
  const normalized: ConfirmOptions = typeof opts === 'string' ? { message: opts } : opts;
  return new Promise((resolve) => {
    if (hostListener) hostListener(normalized, resolve);
    else resolve(window.confirm(normalized.message));
  });
}

/** Mount exactly once (in App). Renders the active confirmation. */
export function ConfirmDialogHost() {
  const [options, setOptions] = useState<ConfirmOptions | null>(null);
  const resolverRef = useRef<Resolver | null>(null);
  const cancelBtnRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    hostListener = (opts, resolve) => {
      // A second confirm while one is open cancels the first.
      resolverRef.current?.(false);
      resolverRef.current = resolve;
      setOptions(opts);
    };
    return () => {
      hostListener = null;
    };
  }, []);

  const settle = (result: boolean) => {
    resolverRef.current?.(result);
    resolverRef.current = null;
    setOptions(null);
  };

  // Capture-phase Escape handler so it beats any underlying Modal's
  // window listener — Escape dismisses the confirmation only, not the
  // modal beneath it.
  useEffect(() => {
    if (!options) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        e.stopImmediatePropagation();
        settle(false);
      }
    };
    window.addEventListener('keydown', onKey, true);
    return () => window.removeEventListener('keydown', onKey, true);
  }, [options]);

  // Focus lands on Cancel so a stray Enter never confirms a deletion.
  useEffect(() => {
    if (options) cancelBtnRef.current?.focus();
  }, [options]);

  if (!options) return null;

  return (
    <div
      className="confirm-dialog__overlay"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) settle(false);
      }}
    >
      <div className="confirm-dialog" role="alertdialog" aria-modal="true"
           aria-label={options.title || 'Confirm'}>
        {options.title && <h3 className="confirm-dialog__title">{options.title}</h3>}
        <p className="confirm-dialog__message">{options.message}</p>
        <div className="confirm-dialog__buttons">
          <button ref={cancelBtnRef} onClick={() => settle(false)}>
            {options.cancelLabel ?? 'Cancel'}
          </button>
          <button
            className={options.danger === false ? 'primary' : 'danger'}
            onClick={() => settle(true)}
          >
            {options.confirmLabel ?? 'OK'}
          </button>
        </div>
      </div>
    </div>
  );
}
