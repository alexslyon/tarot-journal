import { useState, useEffect, useMemo, useRef, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { setEntryBreakdownSettings } from '../../api/entries';
import { useEntryBreakdown, renderBreakdownValue } from '../../utils/readingBreakdown';
import type { JournalEntryFull, BreakdownSettings } from '../../types';
import './ReadingBreakdown.css';

interface Props {
  entry: JournalEntryFull;
}

function parseInitialSettings(raw: string | null): BreakdownSettings {
  const fallback: BreakdownSettings = { open: false, last_tab: 'all', visible: {} };
  if (!raw) return fallback;
  try {
    const parsed = JSON.parse(raw);
    return {
      open: typeof parsed.open === 'boolean' ? parsed.open : fallback.open,
      last_tab:
        parsed.last_tab === 'all' || typeof parsed.last_tab === 'number'
          ? parsed.last_tab
          : fallback.last_tab,
      visible: parsed.visible && typeof parsed.visible === 'object' ? parsed.visible : {},
    };
  } catch {
    return fallback;
  }
}

export default function ReadingBreakdown({ entry }: Props) {
  const queryClient = useQueryClient();
  // Hydrate once from the loaded entry. If the entry's persisted settings
  // change server-side later in the session we don't re-sync — local edits
  // win until the entry is reloaded.
  const initial = useMemo(
    () => parseInitialSettings(entry.breakdown_settings),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [entry.id],
  );
  const [open, setOpen] = useState(initial.open);
  const [lastTab, setLastTab] = useState<'all' | number>(initial.last_tab);
  const [visible, setVisible] = useState<Record<string, boolean>>(initial.visible);
  const [filterOpen, setFilterOpen] = useState(false);

  const data = useEntryBreakdown(entry);

  // Resolve the active tab against the entry's current tabs — the saved
  // last_tab might point at a reading that's since been deleted.
  const activeTabId = data.tabs.some(t => t.id === lastTab)
    ? lastTab
    : data.tabs[0]?.id ?? 'all';
  const activeTab = data.tabs.find(t => t.id === activeTabId);

  // ── Debounced autosave ────────────────────────────────────
  // Skip the very first render — we just hydrated, no need to round-trip.
  const firstRunRef = useRef(true);
  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const flushSave = useCallback(
    (settings: BreakdownSettings) => {
      setEntryBreakdownSettings(entry.id, settings as unknown as Record<string, unknown>)
        .then(() => {
          // Keep the entry query cache in sync so reopening the entry within
          // staleTime shows the just-saved values.
          queryClient.setQueryData<JournalEntryFull>(['entry', entry.id], prev =>
            prev ? { ...prev, breakdown_settings: JSON.stringify(settings) } : prev,
          );
        })
        .catch(err => {
          console.error('Failed to save breakdown settings:', err);
        });
    },
    [entry.id, queryClient],
  );

  useEffect(() => {
    if (firstRunRef.current) {
      firstRunRef.current = false;
      return;
    }
    if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
    const settings: BreakdownSettings = { open, last_tab: lastTab, visible };
    saveTimerRef.current = setTimeout(() => flushSave(settings), 600);
    return () => {
      if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
    };
  }, [open, lastTab, visible, flushSave]);

  // ── Click-outside handler for the filter popover ─────────
  const filterRef = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    if (!filterOpen) return;
    function onMouseDown(e: MouseEvent) {
      if (filterRef.current && !filterRef.current.contains(e.target as Node)) {
        setFilterOpen(false);
      }
    }
    document.addEventListener('mousedown', onMouseDown);
    return () => document.removeEventListener('mousedown', onMouseDown);
  }, [filterOpen]);

  // ── Don't render at all if the entry has no readings with cards ──
  if (data.tabs.length === 0) return null;

  const presentFields = data.presentCorrespondenceFields;
  const hasFilterableFields = presentFields.length > 0;

  function setAllVisible(value: boolean) {
    const next: Record<string, boolean> = {};
    for (const f of presentFields) next[f] = value;
    setVisible(next);
  }

  function isFieldVisible(field: string): boolean {
    return visible[field] !== false; // missing key = visible
  }

  return (
    <div className="reading-breakdown">
      <button
        className="reading-breakdown__header"
        onClick={() => setOpen(o => !o)}
        aria-expanded={open}
      >
        <span className={`reading-breakdown__chevron ${open ? 'reading-breakdown__chevron--open' : ''}`}>
          ▸
        </span>
        <span className="reading-breakdown__title">Reading Breakdown</span>
      </button>

      {open && (
        <div className="reading-breakdown__body">
          {/* Tabs (per-reading + aggregate). Hidden when only one reading. */}
          {data.tabs.length > 1 && (
            <nav className="reading-breakdown__tabs" role="tablist">
              {data.tabs.map(tab => (
                <button
                  key={String(tab.id)}
                  role="tab"
                  aria-selected={tab.id === activeTabId}
                  className={`reading-breakdown__tab ${
                    tab.id === activeTabId ? 'reading-breakdown__tab--active' : ''
                  }`}
                  onClick={() => setLastTab(tab.id)}
                >
                  {tab.label}
                  <span className="reading-breakdown__tab-count">{tab.cardCount}</span>
                </button>
              ))}
            </nav>
          )}

          {/* Filter popover trigger */}
          {hasFilterableFields && (
            <div className="reading-breakdown__filter" ref={filterRef}>
              <button
                className="reading-breakdown__filter-trigger"
                onClick={() => setFilterOpen(o => !o)}
                aria-expanded={filterOpen}
                aria-label="Filter correspondence rows"
                title="Filter correspondence rows"
              >
                ⚙ Filter
              </button>
              {filterOpen && (
                <div className="reading-breakdown__filter-popover" role="dialog">
                  <div className="reading-breakdown__filter-bulk">
                    <button onClick={() => setAllVisible(true)}>All</button>
                    <button onClick={() => setAllVisible(false)}>None</button>
                  </div>
                  <ul className="reading-breakdown__filter-list">
                    {presentFields.map(field => {
                      const row = data.tabs.find(t => t.id === 'all')?.rows.find(r => r.key === field)
                        ?? activeTab?.rows.find(r => r.key === field);
                      const label = row?.label || field;
                      return (
                        <li key={field} className="reading-breakdown__filter-item">
                          <label>
                            <input
                              type="checkbox"
                              checked={isFieldVisible(field)}
                              onChange={e =>
                                setVisible(v => ({ ...v, [field]: e.target.checked }))
                              }
                            />
                            <span>{label}</span>
                          </label>
                        </li>
                      );
                    })}
                  </ul>
                </div>
              )}
            </div>
          )}

          {/* Table */}
          {data.isLoading && (
            <div className="reading-breakdown__loading">Loading…</div>
          )}
          {!data.isLoading && activeTab && (
            <div className="reading-breakdown__table">
              {activeTab.rows
                .filter(row => {
                  if (row.key === 'suit' || row.key === 'rank') return true;
                  return isFieldVisible(row.key);
                })
                .map(row => (
                  <div key={row.key} className="reading-breakdown__row">
                    <div className="reading-breakdown__row-label">{row.label}</div>
                    <div className="reading-breakdown__row-chips">
                      {row.columns.map(col => (
                        <span key={col.value} className="reading-breakdown__chip">
                          <span className="reading-breakdown__chip-value">
                            {renderBreakdownValue(row.key, col.value)}
                          </span>
                          <span className="reading-breakdown__chip-count">{col.count}</span>
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
