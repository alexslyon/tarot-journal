import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  getArchetypeNames,
  getArchetypeNamesForType,
} from '../../../../api/archetypeLanguages';
import type { Archetype } from '../../../../api/correspondences';
import type { ArchetypeLanguageName } from '../../../../types';
import './ArchetypeLanguagesTab.css';

interface Props {
  archetype: Archetype;
  cartomancyType: string;
  archetypes: Archetype[];
  onNavigateToSettings?: (
    section: string,
    payload?: { archetypeId?: number; fieldId?: number },
  ) => void;
}

type Mode = 'card' | 'table';

const STORAGE_KEY = 'archetypes-viewer.languages.mode';

export default function ArchetypeLanguagesTab({
  archetype,
  cartomancyType,
  archetypes,
  onNavigateToSettings,
}: Props) {
  const [mode, setMode] = useState<Mode>(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    return saved === 'table' ? 'table' : 'card';
  });
  const switchMode = (m: Mode) => {
    setMode(m);
    localStorage.setItem(STORAGE_KEY, m);
  };

  return (
    <div className="archetype-langs">
      <div className="archetype-langs__header">
        <div className="archetype-langs__mode-toggle">
          <button
            className={`archetype-langs__mode-btn ${mode === 'card' ? 'archetype-langs__mode-btn--active' : ''}`}
            onClick={() => switchMode('card')}
          >
            Card mode
          </button>
          <button
            className={`archetype-langs__mode-btn ${mode === 'table' ? 'archetype-langs__mode-btn--active' : ''}`}
            onClick={() => switchMode('table')}
          >
            Table mode
          </button>
        </div>
        {onNavigateToSettings && (
          <button
            className="archetype-langs__edit-link"
            onClick={() =>
              onNavigateToSettings('archetype-languages', { archetypeId: archetype.id })
            }
          >
            Edit in Settings →
          </button>
        )}
      </div>

      {mode === 'card' ? (
        <CardModeView archetype={archetype} />
      ) : (
        <TableModeView
          cartomancyType={cartomancyType}
          archetypes={archetypes}
          activeArchetypeId={archetype.id}
        />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Card mode — names for one archetype, grouped by language
// ---------------------------------------------------------------------------

function CardModeView({ archetype }: { archetype: Archetype }) {
  const { data: names = [] } = useQuery<ArchetypeLanguageName[]>({
    queryKey: ['archetype-language-names', archetype.id],
    queryFn: () => getArchetypeNames(archetype.id),
  });

  // Group by language id, preserving the language sort order embedded in the
  // joined query result.
  const groups = useMemo(() => {
    const m = new Map<number, { name: string; sort: number; entries: ArchetypeLanguageName[] }>();
    for (const n of names) {
      if (!m.has(n.language_id)) {
        m.set(n.language_id, {
          name: n.language_name,
          sort: n.language_sort_order,
          entries: [],
        });
      }
      m.get(n.language_id)!.entries.push(n);
    }
    return [...m.entries()]
      .sort((a, b) => a[1].sort - b[1].sort)
      .map(([id, g]) => ({ id, ...g }));
  }, [names]);

  if (groups.length === 0) {
    return (
      <p className="archetype-langs__empty">
        No translations for {archetype.name} yet.
      </p>
    );
  }

  return (
    <div className="archetype-langs__card-mode">
      {groups.map(g => (
        <section key={g.id} className="archetype-langs__lang-block">
          <h4 className="archetype-langs__lang-name">{g.name}</h4>
          <ul className="archetype-langs__name-list">
            {g.entries.map(n => (
              <li key={n.id} className="archetype-langs__name-row">
                <span className="archetype-langs__name-text">{n.name}</span>
                {(n.romanization || n.ipa) && (
                  <div className="archetype-langs__name-meta">
                    {n.romanization && (
                      <span className="archetype-langs__romanization">{n.romanization}</span>
                    )}
                    {n.ipa && (
                      <span className="archetype-langs__ipa">/{n.ipa}/</span>
                    )}
                  </div>
                )}
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Table mode — rows = archetypes, columns = languages
// ---------------------------------------------------------------------------

function TableModeView({
  cartomancyType,
  archetypes,
  activeArchetypeId,
}: {
  cartomancyType: string;
  archetypes: Archetype[];
  activeArchetypeId: number;
}) {
  const { data: allNames = [] } = useQuery<ArchetypeLanguageName[]>({
    queryKey: ['archetype-language-names-by-type', cartomancyType],
    queryFn: () => getArchetypeNamesForType(cartomancyType),
  });

  const [expandedCell, setExpandedCell] = useState<{
    archetypeId: number;
    languageId: number;
  } | null>(null);

  // Build language list (in sort order) from the names data — only languages
  // that have at least one entry are visible.
  const languages = useMemo(() => {
    const m = new Map<number, { name: string; sort: number }>();
    for (const n of allNames) {
      if (!m.has(n.language_id)) {
        m.set(n.language_id, { name: n.language_name, sort: n.language_sort_order });
      }
    }
    return [...m.entries()]
      .sort((a, b) => a[1].sort - b[1].sort)
      .map(([id, info]) => ({ id, ...info }));
  }, [allNames]);

  // Index names by (archetype, language) for cell lookup.
  const cellIndex = useMemo(() => {
    const m = new Map<string, ArchetypeLanguageName[]>();
    for (const n of allNames) {
      const key = `${n.archetype_id}:${n.language_id}`;
      if (!m.has(key)) m.set(key, []);
      m.get(key)!.push(n);
    }
    return m;
  }, [allNames]);

  if (languages.length === 0) {
    return (
      <p className="archetype-langs__empty">
        No languages with entries yet. Add languages and names in Settings.
      </p>
    );
  }

  return (
    <div className="archetype-langs__table-wrap">
      <table className="archetype-langs__table">
        <thead>
          <tr>
            <th className="archetype-langs__th-card">Card</th>
            {languages.map(l => (
              <th key={l.id}>{l.name}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {archetypes.map(a => (
            <tr
              key={a.id}
              className={a.id === activeArchetypeId ? 'archetype-langs__row--active' : ''}
            >
              <td className="archetype-langs__td-card">{a.name}</td>
              {languages.map(l => {
                const cellNames = cellIndex.get(`${a.id}:${l.id}`) || [];
                const isExpanded =
                  expandedCell?.archetypeId === a.id &&
                  expandedCell?.languageId === l.id;
                return (
                  <td
                    key={l.id}
                    className="archetype-langs__cell"
                    onClick={() => {
                      if (cellNames.length === 0) return;
                      setExpandedCell(
                        isExpanded ? null : { archetypeId: a.id, languageId: l.id },
                      );
                    }}
                  >
                    {cellNames.length === 0 ? (
                      <span className="archetype-langs__cell-empty">—</span>
                    ) : (
                      <div className="archetype-langs__cell-stack">
                        {cellNames.map(n => (
                          <div key={n.id} className="archetype-langs__cell-name">
                            {n.name}
                            {isExpanded && (n.romanization || n.ipa) && (
                              <div className="archetype-langs__cell-meta">
                                {n.romanization && <span>{n.romanization}</span>}
                                {n.ipa && <span>/{n.ipa}/</span>}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
