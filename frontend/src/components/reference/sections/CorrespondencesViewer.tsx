import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  getCorrespondenceSystems,
  getCorrespondenceSystem,
  compareCorrespondenceSystems,
} from '../../../api/correspondences';
import type { CorrespondenceSystem, CorrespondenceAssignment } from '../../../types';
import { CORRESPONDENCE_FIELDS, CORRESPONDENCE_FIELD_LABELS } from '../../../types';
import './CorrespondencesViewer.css';

interface GroupPattern {
  groupLabel: string;
  fieldName: string;
  fieldLabel: string;
  value: string;
}

/** Detect group-level patterns: values shared by all cards in a group. */
function detectGroupPatterns(
  assignments: CorrespondenceAssignment[],
): GroupPattern[] {
  // Build per-card field maps with card metadata
  const cards = new Map<number, {
    name: string;
    suit: string | null;
    card_type: string | null;
    fields: Map<string, string>;
  }>();

  for (const a of assignments) {
    if (!cards.has(a.archetype_id)) {
      cards.set(a.archetype_id, {
        name: a.archetype_name,
        suit: a.suit,
        card_type: a.card_type,
        fields: new Map(),
      });
    }
    cards.get(a.archetype_id)!.fields.set(a.field_name, a.field_value);
  }

  const allCards = [...cards.values()];
  const patterns: GroupPattern[] = [];

  // Define groups to check
  const groups: { label: string; filter: (c: typeof allCards[0]) => boolean }[] = [
    // Suits
    { label: 'Wands', filter: c => c.suit === 'Wands' },
    { label: 'Cups', filter: c => c.suit === 'Cups' },
    { label: 'Swords', filter: c => c.suit === 'Swords' },
    { label: 'Pentacles', filter: c => c.suit === 'Pentacles' },
    // Court ranks
    { label: 'Pages', filter: c => c.name.startsWith('Page of') },
    { label: 'Knights', filter: c => c.name.startsWith('Knight of') },
    { label: 'Queens', filter: c => c.name.startsWith('Queen of') },
    { label: 'Kings', filter: c => c.name.startsWith('King of') },
    // Pips
    { label: 'Aces', filter: c => c.name.startsWith('Ace of') },
    // Major Arcana as a whole
    { label: 'Major Arcana', filter: c => c.card_type === 'major' },
  ];

  for (const group of groups) {
    const members = allCards.filter(group.filter);
    if (members.length < 2) continue;

    for (const field of CORRESPONDENCE_FIELDS) {
      const values = members.map(m => m.fields.get(field)).filter(Boolean);
      if (values.length === members.length) {
        // Every member has this field set
        const unique = new Set(values);
        if (unique.size === 1) {
          patterns.push({
            groupLabel: group.label,
            fieldName: field,
            fieldLabel: CORRESPONDENCE_FIELD_LABELS[field],
            value: values[0]!,
          });
        }
      }
    }
  }

  return patterns;
}

type ViewMode = 'by-system' | 'compare';

interface CorrespondencesViewerProps {
  onEditCorrespondences?: (section: string) => void;
}

export default function CorrespondencesViewer({ onEditCorrespondences }: CorrespondencesViewerProps) {
  const [viewMode, setViewMode] = useState<ViewMode>('by-system');
  const [selectedSystemId, setSelectedSystemId] = useState<number | null>(null);
  const [compareIds, setCompareIds] = useState<number[]>([]);
  const [filterText, setFilterText] = useState('');

  const { data: systems = [] } = useQuery<CorrespondenceSystem[]>({
    queryKey: ['correspondence-systems'],
    queryFn: getCorrespondenceSystems,
  });

  // Auto-select first system
  if (systems.length > 0 && selectedSystemId === null) {
    setSelectedSystemId(systems[0].id);
  }

  const { data: systemDetail } = useQuery({
    queryKey: ['correspondence-system', selectedSystemId],
    queryFn: () => getCorrespondenceSystem(selectedSystemId!),
    enabled: selectedSystemId !== null && viewMode === 'by-system',
  });

  const { data: compareData = [] } = useQuery<CorrespondenceAssignment[]>({
    queryKey: ['correspondence-compare', compareIds],
    queryFn: () => compareCorrespondenceSystems(compareIds),
    enabled: compareIds.length >= 2 && viewMode === 'compare',
  });

  const toggleCompareId = (id: number) => {
    setCompareIds(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    );
  };

  // Build table data for by-system view
  const bySystemRows = new Map<number, { name: string; fields: Map<string, string> }>();
  if (systemDetail?.assignments) {
    for (const a of systemDetail.assignments as CorrespondenceAssignment[]) {
      if (!bySystemRows.has(a.archetype_id)) {
        bySystemRows.set(a.archetype_id, { name: a.archetype_name, fields: new Map() });
      }
      bySystemRows.get(a.archetype_id)!.fields.set(a.field_name, a.field_value);
    }
  }

  // Detect group-level patterns
  const groupPatterns = useMemo(() => {
    if (!systemDetail?.assignments) return [];
    return detectGroupPatterns(systemDetail.assignments as CorrespondenceAssignment[]);
  }, [systemDetail]);

  // Group the patterns by field for display
  const patternsByField = useMemo(() => {
    const map = new Map<string, GroupPattern[]>();
    for (const p of groupPatterns) {
      if (!map.has(p.fieldLabel)) map.set(p.fieldLabel, []);
      map.get(p.fieldLabel)!.push(p);
    }
    return map;
  }, [groupPatterns]);

  const filteredArchetypeIds = [...bySystemRows.keys()].filter(id => {
    if (!filterText) return true;
    return bySystemRows.get(id)!.name.toLowerCase().includes(filterText.toLowerCase());
  });

  // Build compare table data — grouped by archetype, then by system
  const compareRows = new Map<string, Map<string, Map<string, string>>>();
  const compareSystemNames = new Map<number, string>();
  for (const a of compareData) {
    if (!compareRows.has(a.archetype_name)) {
      compareRows.set(a.archetype_name, new Map());
    }
    const systemName = (a as CorrespondenceAssignment & { system_name?: string }).system_name || String(a.system_id);
    compareSystemNames.set(a.system_id, systemName);
    if (!compareRows.get(a.archetype_name)!.has(systemName)) {
      compareRows.get(a.archetype_name)!.set(systemName, new Map());
    }
    compareRows.get(a.archetype_name)!.get(systemName)!.set(a.field_name, a.field_value);
  }

  const compareSystemList = [...compareSystemNames.entries()].sort((a, b) => a[1].localeCompare(b[1]));

  return (
    <div className="reference-section">
      <div className="corr-viewer__header">
        <h2 className="reference-section__title">Correspondences</h2>
        {onEditCorrespondences && (
          <button
            className="corr-viewer__edit-btn"
            onClick={() => onEditCorrespondences('correspondences')}
          >
            Edit Correspondences
          </button>
        )}
      </div>

      {/* View mode tabs */}
      <div className="corr-viewer__mode-tabs">
        <button
          className={`corr-viewer__mode-tab ${viewMode === 'by-system' ? 'corr-viewer__mode-tab--active' : ''}`}
          onClick={() => setViewMode('by-system')}
        >
          By System
        </button>
        <button
          className={`corr-viewer__mode-tab ${viewMode === 'compare' ? 'corr-viewer__mode-tab--active' : ''}`}
          onClick={() => setViewMode('compare')}
        >
          Compare Systems
        </button>
      </div>

      {/* By System view */}
      {viewMode === 'by-system' && (
        <div className="reference-section__card">
          <div className="corr-viewer__controls">
            <select
              value={selectedSystemId ?? ''}
              onChange={e => setSelectedSystemId(Number(e.target.value))}
              className="corr-viewer__system-select"
            >
              {systems.map(sys => (
                <option key={sys.id} value={sys.id}>{sys.name}</option>
              ))}
            </select>
            <input
              type="text"
              value={filterText}
              onChange={e => setFilterText(e.target.value)}
              placeholder="Filter cards..."
              className="corr-viewer__filter"
            />
          </div>

          {/* Group-level patterns summary */}
          {patternsByField.size > 0 && (
            <div className="corr-viewer__group-summary">
              <h4 className="corr-viewer__group-title">Group Patterns</h4>
              {[...patternsByField.entries()].map(([fieldLabel, patterns]) => (
                <div key={fieldLabel} className="corr-viewer__group-row">
                  <span className="corr-viewer__group-field">{fieldLabel}</span>
                  <div className="corr-viewer__group-values">
                    {patterns.map(p => (
                      <span key={p.groupLabel} className="corr-viewer__group-tag">
                        <span className="corr-viewer__group-name">{p.groupLabel}</span>
                        <span className="corr-viewer__group-eq">=</span>
                        <span className="corr-viewer__group-val">{p.value}</span>
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}

          <div className="corr-viewer__table-wrap">
            <table className="corr-viewer__table">
              <thead>
                <tr>
                  <th className="corr-viewer__th--card">Card</th>
                  {CORRESPONDENCE_FIELDS.map(f => (
                    <th key={f}>{CORRESPONDENCE_FIELD_LABELS[f]}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filteredArchetypeIds.map(archId => {
                  const row = bySystemRows.get(archId)!;
                  return (
                    <tr key={archId}>
                      <td className="corr-viewer__td--card">{row.name}</td>
                      {CORRESPONDENCE_FIELDS.map(f => (
                        <td key={f} className="corr-viewer__td--value">
                          {row.fields.get(f) || ''}
                        </td>
                      ))}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {filteredArchetypeIds.length === 0 && (
            <p className="reference-section__hint" style={{ textAlign: 'center', padding: 20 }}>
              {filterText ? 'No cards match your filter.' : 'No assignments in this system.'}
            </p>
          )}
        </div>
      )}

      {/* Compare view */}
      {viewMode === 'compare' && (
        <div className="reference-section__card">
          <p className="reference-section__hint">Select two or more systems to compare.</p>
          <div className="corr-viewer__compare-select">
            {systems.map(sys => (
              <label key={sys.id} className="corr-viewer__compare-check">
                <input
                  type="checkbox"
                  checked={compareIds.includes(sys.id)}
                  onChange={() => toggleCompareId(sys.id)}
                />
                <span>{sys.name}</span>
              </label>
            ))}
          </div>

          {compareIds.length >= 2 && compareRows.size > 0 && (
            <div className="corr-viewer__table-wrap">
              <table className="corr-viewer__table">
                <thead>
                  <tr>
                    <th className="corr-viewer__th--card">Card</th>
                    <th>Field</th>
                    {compareSystemList.map(([id, name]) => (
                      <th key={id}>{name}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {[...compareRows.entries()].map(([archName, systemMap]) => {
                    // Find fields that differ across systems
                    const allFields = new Set<string>();
                    for (const fields of systemMap.values()) {
                      for (const f of fields.keys()) allFields.add(f);
                    }

                    return [...allFields].map((fieldName, fi) => (
                      <tr key={`${archName}-${fieldName}`}>
                        {fi === 0 ? (
                          <td className="corr-viewer__td--card" rowSpan={allFields.size}>
                            {archName}
                          </td>
                        ) : null}
                        <td className="corr-viewer__td--field">
                          {CORRESPONDENCE_FIELD_LABELS[fieldName] || fieldName}
                        </td>
                        {compareSystemList.map(([, sysName]) => {
                          const val = systemMap.get(sysName)?.get(fieldName) || '';
                          return <td key={sysName} className="corr-viewer__td--value">{val}</td>;
                        })}
                      </tr>
                    ));
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
