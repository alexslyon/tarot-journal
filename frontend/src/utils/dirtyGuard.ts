import { confirmDialog } from '../components/common/ConfirmDialog';

/** Tracks whether any editor currently holds unsaved changes, and
 *  intercepts window close (Cmd+Q, the traffic-light button, Cmd+R
 *  reload) while one does. The in-app dialogs guard stray clicks, but
 *  without this, quitting the app silently discarded a half-written
 *  entry. */

let dirtyCount = 0;
let allowClose = false;

/** Register a dirty editor. Returns an unregister function — call it
 *  when the editor saves, closes, or becomes clean again. */
export function registerDirty(): () => void {
  dirtyCount++;
  let active = true;
  return () => {
    if (active) {
      active = false;
      dirtyCount--;
    }
  };
}

/** Install the beforeunload interceptor. Call once at startup. */
export function installQuitGuard() {
  window.addEventListener('beforeunload', (e) => {
    if (dirtyCount === 0 || allowClose) return;
    // In Electron, preventing the unload blocks the close silently
    // (no browser-style prompt), so we show our own dialog after.
    e.preventDefault();
    e.returnValue = '';
    confirmDialog({
      title: 'Unsaved Changes',
      message: 'You have unsaved changes. Quit and discard them?',
      confirmLabel: 'Discard & Quit',
    }).then((discard) => {
      if (discard) {
        allowClose = true;
        window.close();
        // If the close is somehow blocked, don't leave a stale bypass
        // that would let a later quit skip the guard.
        setTimeout(() => {
          allowClose = false;
        }, 1000);
      }
    });
  });
}
