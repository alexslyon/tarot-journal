import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  getCorrespondenceSystems,
  getCorrespondenceSystem,
  createCorrespondenceSystem,
  updateCorrespondenceSystem,
  deleteCorrespondenceSystem,
  cloneCorrespondenceSystem,
  setAssignment,
  deleteAssignment,
  bulkSetAssignments,
  getArchetypes,
  type Archetype,
} from '../../../api/correspondences';
import type {
  CorrespondenceSystem,
  CorrespondenceAssignment,
} from '../../../types';
import {
  CORRESPONDENCE_FIELDS,
  CORRESPONDENCE_FIELD_LABELS,
} from '../../../types';
import '../SettingsTab.css';
import './CorrespondencesSection.css';

export default function CorrespondencesSection() {
  const queryClient = useQueryClient();
  const [selectedSystemId, setSelectedSystemId] = useState<number | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null);
  const [newName, setNewName] = useState('');
  const [newDesc, setNewDesc] = useState('');
  const [creating, setCreating] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [editingName, setEditingName] = useState<string | null>(null);
  const [editingDesc, setEditingDesc] = useState<string | null>(null);
  const [cloneName, setCloneName] = useState('');
  const [showClone, setShowClone] = useState(false);
  const [filterText, setFilterText] = useState('');
  const [bulkGroup, setBulkGroup] = useState('');
  const [bulkField, setBulkField] = useState(CORRESPONDENCE_FIELDS[0] as string);
  const [bulkValue, setBulkValue] = useState('');
  const [bulkApplying, setBulkApplying] = useState(false);
  const [showBulk, setShowBulk] = useState(false);

  const { data: systems = [] } = useQuery<CorrespondenceSystem[]>({
    queryKey: ['correspondence-systems'],
    queryFn: getCorrespondenceSystems,
  });

  const { data: systemDetail } = useQuery({
    queryKey: ['correspondence-system', selectedSystemId],
    queryFn: () => getCorrespondenceSystem(selectedSystemId!),
    enabled: selectedSystemId !== null,
  });

  const { data: allArchetypes = [] } = useQuery<Archetype[]>({
    queryKey: ['archetypes', 'Tarot'],
    queryFn: () => getArchetypes('Tarot'),
  });

  const showMsg = (text: string, type: 'success' | 'error') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['correspondence-systems'] });
    if (selectedSystemId) {
      queryClient.invalidateQueries({ queryKey: ['correspondence-system', selectedSystemId] });
    }
  };

  const handleCreate = async () => {
    if (!newName.trim()) return;
    setCreating(true);
    try {
      const result = await createCorrespondenceSystem({ name: newName.trim(), description: newDesc.trim() || undefined });
      invalidate();
      setSelectedSystemId(result.id);
      setNewName('');
      setNewDesc('');
      setShowCreate(false);
      showMsg('System created', 'success');
    } catch {
      showMsg('Failed to create system (name may already exist)', 'error');
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (system: CorrespondenceSystem) => {
    if (!window.confirm(`Delete "${system.name}"? This will remove all its assignments.`)) return;
    try {
      await deleteCorrespondenceSystem(system.id);
      if (selectedSystemId === system.id) setSelectedSystemId(null);
      invalidate();
      showMsg('System deleted', 'success');
    } catch {
      showMsg('Failed to delete system', 'error');
    }
  };

  const handleClone = async () => {
    if (!selectedSystemId || !cloneName.trim()) return;
    try {
      const result = await cloneCorrespondenceSystem(selectedSystemId, cloneName.trim());
      invalidate();
      setSelectedSystemId(result.id);
      setCloneName('');
      setShowClone(false);
      showMsg('System cloned', 'success');
    } catch {
      showMsg('Failed to clone system', 'error');
    }
  };

  const handleSaveMeta = async () => {
    if (!selectedSystemId) return;
    try {
      await updateCorrespondenceSystem(selectedSystemId, {
        name: editingName ?? undefined,
        description: editingDesc ?? undefined,
      });
      invalidate();
      setEditingName(null);
      setEditingDesc(null);
      showMsg('System updated', 'success');
    } catch {
      showMsg('Failed to update system', 'error');
    }
  };

  const handleSetAssignment = async (archetypeId: number, fieldName: string, value: string) => {
    if (!selectedSystemId) return;
    try {
      if (value.trim()) {
        await setAssignment(selectedSystemId, archetypeId, fieldName, value.trim());
      } else {
        await deleteAssignment(selectedSystemId, archetypeId, fieldName);
      }
      queryClient.invalidateQueries({ queryKey: ['correspondence-system', selectedSystemId] });
    } catch {
      showMsg('Failed to update assignment', 'error');
    }
  };

  // Group assignments by archetype for table display
  const assignmentsByArchetype = new Map<number, Map<string, string>>();
  const archetypeInfo = new Map<number, { name: string; cartomancy_type: string; card_type: string | null }>();

  if (systemDetail?.assignments) {
    for (const a of systemDetail.assignments as CorrespondenceAssignment[]) {
      if (!assignmentsByArchetype.has(a.archetype_id)) {
        assignmentsByArchetype.set(a.archetype_id, new Map());
        archetypeInfo.set(a.archetype_id, {
          name: a.archetype_name,
          cartomancy_type: a.cartomancy_type,
          card_type: a.card_type,
        });
      }
      assignmentsByArchetype.get(a.archetype_id)!.set(a.field_name, a.field_value);
    }
  }

  // === Bulk assign groups ===
  const BULK_GROUPS: { label: string; filter: (a: Archetype) => boolean }[] = [
    { label: 'Major Arcana', filter: a => a.card_type === 'major' },
    { label: 'All Minor Arcana', filter: a => a.card_type === 'minor' },
    // Suits
    { label: 'Wands', filter: a => a.suit === 'Wands' },
    { label: 'Cups', filter: a => a.suit === 'Cups' },
    { label: 'Swords', filter: a => a.suit === 'Swords' },
    { label: 'Pentacles', filter: a => a.suit === 'Pentacles' },
    // Court ranks
    { label: 'All Pages', filter: a => a.name.startsWith('Page of') },
    { label: 'All Knights', filter: a => a.name.startsWith('Knight of') },
    { label: 'All Queens', filter: a => a.name.startsWith('Queen of') },
    { label: 'All Kings', filter: a => a.name.startsWith('King of') },
    // Pip numbers
    { label: 'All Aces', filter: a => a.name.startsWith('Ace of') },
    { label: 'All Twos', filter: a => a.name.startsWith('Two of') },
    { label: 'All Threes', filter: a => a.name.startsWith('Three of') },
    { label: 'All Fours', filter: a => a.name.startsWith('Four of') },
    { label: 'All Fives', filter: a => a.name.startsWith('Five of') },
    { label: 'All Sixes', filter: a => a.name.startsWith('Six of') },
    { label: 'All Sevens', filter: a => a.name.startsWith('Seven of') },
    { label: 'All Eights', filter: a => a.name.startsWith('Eight of') },
    { label: 'All Nines', filter: a => a.name.startsWith('Nine of') },
    { label: 'All Tens', filter: a => a.name.startsWith('Ten of') },
    // All pips (non-court minor)
    { label: 'All Pips (Ace-10)', filter: a => {
      if (a.card_type !== 'minor') return false;
      const rankNum = parseInt(a.rank?.slice(-2) || '0');
      return rankNum >= 1 && rankNum <= 10;
    }},
    // All court cards
    { label: 'All Court Cards', filter: a => {
      if (a.card_type !== 'minor') return false;
      const rankNum = parseInt(a.rank?.slice(-2) || '0');
      return rankNum >= 11 && rankNum <= 14;
    }},
  ];

  const getGroupArchetypes = (groupLabel: string): Archetype[] => {
    const group = BULK_GROUPS.find(g => g.label === groupLabel);
    if (!group) return [];
    return allArchetypes.filter(group.filter);
  };

  const handleBulkApply = async () => {
    if (!selectedSystemId || !bulkGroup || !bulkField || !bulkValue.trim()) return;
    const archetypes = getGroupArchetypes(bulkGroup);
    if (archetypes.length === 0) return;

    setBulkApplying(true);
    try {
      const assignments = archetypes.map(a => ({
        archetype_id: a.id,
        field_name: bulkField,
        field_value: bulkValue.trim(),
      }));
      await bulkSetAssignments(selectedSystemId, assignments);
      queryClient.invalidateQueries({ queryKey: ['correspondence-system', selectedSystemId] });
      showMsg(`Set ${CORRESPONDENCE_FIELD_LABELS[bulkField]} = "${bulkValue.trim()}" for ${archetypes.length} cards`, 'success');
      setBulkValue('');
    } catch {
      showMsg('Failed to apply bulk assignment', 'error');
    } finally {
      setBulkApplying(false);
    }
  };

  // Get all archetypes that have at least one assignment, filtered
  const archetypeIds = [...assignmentsByArchetype.keys()].filter(id => {
    if (!filterText) return true;
    const info = archetypeInfo.get(id);
    return info?.name.toLowerCase().includes(filterText.toLowerCase());
  });

  return (
    <div className="settings-tab__scroll">
      <h2 className="settings-tab__title">Correspondence Systems</h2>

      {message && (
        <div className={`settings-tab__message settings-tab__message--${message.type}`}>
          {message.text}
        </div>
      )}

      {/* System List */}
      <section className="settings-tab__section">
        <p className="settings-tab__hint">
          Correspondence systems define canonical element, planet, zodiac, and other
          assignments for card archetypes. Decks can select a system to inherit these values.
        </p>

        <div className="corr-systems__list">
          {systems.map(sys => (
            <div
              key={sys.id}
              className={`corr-systems__item ${selectedSystemId === sys.id ? 'corr-systems__item--selected' : ''}`}
              onClick={() => setSelectedSystemId(sys.id)}
            >
              <div className="corr-systems__item-info">
                <span className="corr-systems__item-name">
                  {sys.name}
                  {sys.is_builtin && <span className="settings-tab__import-preset-badge">built-in</span>}
                </span>
                <span className="corr-systems__item-stats">
                  {sys.archetype_count} archetypes · {sys.assignment_count} assignments
                </span>
              </div>
              <div className="corr-systems__item-actions">
                <button
                  className="settings-tab__import-preset-btn settings-tab__import-preset-btn--danger"
                  onClick={(e) => { e.stopPropagation(); handleDelete(sys); }}
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>

        {!showCreate ? (
          <button className="settings-tab__add-preset-btn" onClick={() => setShowCreate(true)}>
            + New System
          </button>
        ) : (
          <div className="corr-systems__create-form">
            <div className="settings-tab__field">
              <label className="settings-tab__label">Name</label>
              <input
                type="text"
                value={newName}
                onChange={e => setNewName(e.target.value)}
                placeholder="e.g. Thoth, Golden Dawn"
              />
            </div>
            <div className="settings-tab__field">
              <label className="settings-tab__label">Description</label>
              <input
                type="text"
                value={newDesc}
                onChange={e => setNewDesc(e.target.value)}
                placeholder="Optional description"
              />
            </div>
            <div className="corr-systems__create-actions">
              <button onClick={() => setShowCreate(false)}>Cancel</button>
              <button
                className="settings-tab__save-btn"
                onClick={handleCreate}
                disabled={creating || !newName.trim()}
              >
                {creating ? 'Creating...' : 'Create'}
              </button>
            </div>
          </div>
        )}
      </section>

      {/* System Detail / Assignment Editor */}
      {systemDetail && (
        <section className="settings-tab__section">
          <div className="corr-systems__detail-header">
            {editingName !== null ? (
              <div className="corr-systems__edit-meta">
                <input
                  type="text"
                  value={editingName}
                  onChange={e => setEditingName(e.target.value)}
                  placeholder="System name"
                />
                <input
                  type="text"
                  value={editingDesc ?? ''}
                  onChange={e => setEditingDesc(e.target.value)}
                  placeholder="Description"
                />
                <div className="corr-systems__create-actions">
                  <button onClick={() => { setEditingName(null); setEditingDesc(null); }}>Cancel</button>
                  <button className="settings-tab__save-btn" onClick={handleSaveMeta}>Save</button>
                </div>
              </div>
            ) : (
              <>
                <div>
                  <h3 className="settings-tab__section-title" style={{ marginBottom: 2 }}>
                    {systemDetail.name}
                  </h3>
                  {systemDetail.description && (
                    <p className="settings-tab__hint" style={{ margin: 0 }}>
                      {systemDetail.description}
                    </p>
                  )}
                </div>
                <div className="corr-systems__detail-actions">
                  <button onClick={() => {
                    setEditingName(systemDetail.name);
                    setEditingDesc(systemDetail.description || '');
                  }}>
                    Rename
                  </button>
                  {!showClone ? (
                    <button onClick={() => setShowClone(true)}>Clone</button>
                  ) : (
                    <div className="corr-systems__clone-inline">
                      <input
                        type="text"
                        value={cloneName}
                        onChange={e => setCloneName(e.target.value)}
                        placeholder="New name"
                        style={{ width: 150 }}
                      />
                      <button className="settings-tab__save-btn" onClick={handleClone} disabled={!cloneName.trim()}>
                        Clone
                      </button>
                      <button onClick={() => { setShowClone(false); setCloneName(''); }}>
                        Cancel
                      </button>
                    </div>
                  )}
                </div>
              </>
            )}
          </div>

          {/* Bulk Assign */}
          <div className="corr-bulk">
            <button
              className="settings-tab__customize-btn"
              onClick={() => setShowBulk(!showBulk)}
            >
              {showBulk ? 'Hide Bulk Assign' : 'Bulk Assign by Group...'}
            </button>

            {showBulk && (
              <div className="corr-bulk__panel">
                <div className="corr-bulk__row">
                  <div className="corr-bulk__field">
                    <label className="settings-tab__label">Group</label>
                    <select value={bulkGroup} onChange={e => setBulkGroup(e.target.value)}>
                      <option value="">Select a group...</option>
                      <optgroup label="Card Type">
                        {BULK_GROUPS.filter((_, i) => i < 2).map(g => (
                          <option key={g.label} value={g.label}>{g.label}</option>
                        ))}
                      </optgroup>
                      <optgroup label="Suits">
                        {BULK_GROUPS.filter((_, i) => i >= 2 && i < 6).map(g => (
                          <option key={g.label} value={g.label}>{g.label}</option>
                        ))}
                      </optgroup>
                      <optgroup label="Court Ranks">
                        {BULK_GROUPS.filter((_, i) => i >= 6 && i < 10).map(g => (
                          <option key={g.label} value={g.label}>{g.label}</option>
                        ))}
                      </optgroup>
                      <optgroup label="Pip Numbers">
                        {BULK_GROUPS.filter((_, i) => i >= 10 && i < 20).map(g => (
                          <option key={g.label} value={g.label}>{g.label}</option>
                        ))}
                      </optgroup>
                      <optgroup label="Combined">
                        {BULK_GROUPS.filter((_, i) => i >= 20).map(g => (
                          <option key={g.label} value={g.label}>{g.label}</option>
                        ))}
                      </optgroup>
                    </select>
                  </div>

                  <div className="corr-bulk__field">
                    <label className="settings-tab__label">Field</label>
                    <select value={bulkField} onChange={e => setBulkField(e.target.value)}>
                      {CORRESPONDENCE_FIELDS.map(f => (
                        <option key={f} value={f}>{CORRESPONDENCE_FIELD_LABELS[f]}</option>
                      ))}
                    </select>
                  </div>

                  <div className="corr-bulk__field" style={{ flex: 1 }}>
                    <label className="settings-tab__label">Value</label>
                    <input
                      type="text"
                      value={bulkValue}
                      onChange={e => setBulkValue(e.target.value)}
                      placeholder="e.g. Fire, Water, Air..."
                    />
                  </div>

                  <div className="corr-bulk__field" style={{ alignSelf: 'flex-end' }}>
                    <button
                      className="settings-tab__save-btn"
                      onClick={handleBulkApply}
                      disabled={bulkApplying || !bulkGroup || !bulkValue.trim()}
                    >
                      {bulkApplying ? 'Applying...' : `Apply${bulkGroup ? ` (${getGroupArchetypes(bulkGroup).length})` : ''}`}
                    </button>
                  </div>
                </div>

                {bulkGroup && (
                  <p className="settings-tab__hint" style={{ marginTop: 4 }}>
                    Will set {CORRESPONDENCE_FIELD_LABELS[bulkField]} to "{bulkValue || '...'}" for {getGroupArchetypes(bulkGroup).length} cards: {getGroupArchetypes(bulkGroup).slice(0, 4).map(a => a.name).join(', ')}{getGroupArchetypes(bulkGroup).length > 4 ? ', ...' : ''}
                  </p>
                )}
              </div>
            )}
          </div>

          {/* Filter */}
          <div className="corr-systems__filter">
            <input
              type="text"
              value={filterText}
              onChange={e => setFilterText(e.target.value)}
              placeholder="Filter cards..."
              className="corr-systems__filter-input"
            />
          </div>

          {/* Assignment Table */}
          <div className="corr-systems__table-wrap">
            <table className="corr-systems__table">
              <thead>
                <tr>
                  <th className="corr-systems__th--card">Card</th>
                  {CORRESPONDENCE_FIELDS.map(f => (
                    <th key={f}>{CORRESPONDENCE_FIELD_LABELS[f]}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {archetypeIds.map(archId => {
                  const info = archetypeInfo.get(archId)!;
                  const fields = assignmentsByArchetype.get(archId)!;
                  return (
                    <tr key={archId}>
                      <td className="corr-systems__td--card">
                        <span className="corr-systems__card-name">{info.name}</span>
                      </td>
                      {CORRESPONDENCE_FIELDS.map(f => (
                        <td key={f}>
                          <input
                            type="text"
                            className="corr-systems__cell-input"
                            defaultValue={fields.get(f) || ''}
                            onBlur={e => {
                              const newVal = e.target.value;
                              const oldVal = fields.get(f) || '';
                              if (newVal !== oldVal) {
                                handleSetAssignment(archId, f, newVal);
                              }
                            }}
                          />
                        </td>
                      ))}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {archetypeIds.length === 0 && (
            <p className="settings-tab__hint" style={{ textAlign: 'center', padding: 20 }}>
              {filterText ? 'No cards match your filter.' : 'No assignments yet. Edit cells to add correspondences.'}
            </p>
          )}
        </section>
      )}
    </div>
  );
}
