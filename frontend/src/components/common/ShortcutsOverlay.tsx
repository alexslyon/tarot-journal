/**
 * The "?" keyboard-shortcuts cheat sheet: a small modal listing every
 * shortcut the app actually has, grouped by where it works. Opened
 * from App's global key handler; closes on Escape via the shared
 * Modal (or by pressing ? again).
 */
import Modal from './Modal';
import './ShortcutsOverlay.css';

const IS_MAC = navigator.platform.toUpperCase().includes('MAC');
const MOD = IS_MAC ? '⌘' : 'Ctrl';

interface ShortcutsOverlayProps {
  open: boolean;
  onClose: () => void;
}

const GROUPS: { title: string; rows: [string, string][] }[] = [
  {
    title: 'Anywhere',
    rows: [
      [`${MOD} K`, 'Open the command palette'],
      [`${MOD} N`, 'New journal entry'],
      [`${MOD} [`, 'Back (navigation history)'],
      [`${MOD} ]`, 'Forward'],
      ['?', 'Show this cheat sheet'],
      ['Esc', 'Close dialogs'],
    ],
  },
  {
    title: 'Journal',
    rows: [
      ['← →', 'Newer / older entry'],
      [`${MOD} ↵`, 'Save the entry being edited'],
    ],
  },
  {
    title: 'Library',
    rows: [
      ['← →', 'Previous / next card in the card viewer'],
    ],
  },
  {
    title: 'Spread designer',
    rows: [
      ['Arrows', 'Nudge the selected position one grid step'],
      ['Shift Arrows', 'Nudge by a hair (1px)'],
      [`${MOD} D`, 'Duplicate the selected position'],
    ],
  },
];

export default function ShortcutsOverlay({ open, onClose }: ShortcutsOverlayProps) {
  return (
    <Modal open={open} onClose={onClose} title="Keyboard Shortcuts" width={440}>
      <div className="shortcuts-overlay">
        {GROUPS.map(group => (
          <section key={group.title} className="shortcuts-overlay__group">
            <h3 className="shortcuts-overlay__kicker">{group.title}</h3>
            {group.rows.map(([keys, what]) => (
              <div key={keys + what} className="shortcuts-overlay__row">
                <span className="shortcuts-overlay__keys">
                  {keys.split(' ').map(k => (
                    <kbd key={k} className="shortcuts-overlay__kbd">{k}</kbd>
                  ))}
                </span>
                <span className="shortcuts-overlay__what">{what}</span>
              </div>
            ))}
          </section>
        ))}
      </div>
    </Modal>
  );
}
