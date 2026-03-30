import { useState, useMemo } from 'react';
import './MappingsEditor.css';

interface MappingsEditorProps {
  /** card name → filename patterns */
  mappings: Record<string, string[]>;
  onChange: (mappings: Record<string, string[]>) => void;
  readOnly?: boolean;
}

export default function MappingsEditor({ mappings, onChange, readOnly }: MappingsEditorProps) {
  const [search, setSearch] = useState('');
  const [editingCard, setEditingCard] = useState<string | null>(null);
  const [editPatterns, setEditPatterns] = useState('');
  const [editCardName, setEditCardName] = useState('');
  const [addingNew, setAddingNew] = useState(false);
  const [newCardName, setNewCardName] = useState('');
  const [newPatterns, setNewPatterns] = useState('');

  // Sort card names and filter by search
  const cardNames = useMemo(() => {
    const names = Object.keys(mappings).sort();
    if (!search.trim()) return names;
    const q = search.toLowerCase();
    return names.filter(
      (name) =>
        name.toLowerCase().includes(q) ||
        mappings[name].some((p) => p.toLowerCase().includes(q))
    );
  }, [mappings, search]);

  const totalPatterns = useMemo(
    () => Object.values(mappings).reduce((sum, arr) => sum + arr.length, 0),
    [mappings]
  );

  const startEdit = (cardName: string) => {
    setEditingCard(cardName);
    setEditCardName(cardName);
    setEditPatterns(mappings[cardName].join(', '));
  };

  const saveEdit = () => {
    if (!editingCard || !editCardName.trim()) return;
    const patterns = editPatterns
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean);
    if (patterns.length === 0) return;

    const updated = { ...mappings };
    // If card name changed, remove old entry
    if (editCardName.trim() !== editingCard) {
      delete updated[editingCard];
    }
    updated[editCardName.trim()] = patterns;
    onChange(updated);
    setEditingCard(null);
  };

  const cancelEdit = () => {
    setEditingCard(null);
  };

  const deleteCard = (cardName: string) => {
    const updated = { ...mappings };
    delete updated[cardName];
    onChange(updated);
  };

  const addNew = () => {
    if (!newCardName.trim()) return;
    const patterns = newPatterns
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean);
    if (patterns.length === 0) return;

    const updated = { ...mappings };
    const existing = updated[newCardName.trim()] || [];
    updated[newCardName.trim()] = [...existing, ...patterns];
    onChange(updated);
    setNewCardName('');
    setNewPatterns('');
    setAddingNew(false);
  };

  return (
    <div className="mappings-editor">
      <div className="mappings-editor__header">
        <span className="mappings-editor__count">
          {Object.keys(mappings).length} cards, {totalPatterns} filename patterns
        </span>
        <input
          type="text"
          className="mappings-editor__search"
          placeholder="Search cards or patterns..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      <div className="mappings-editor__list">
        {cardNames.map((cardName) => (
          <div key={cardName} className="mappings-editor__row">
            {editingCard === cardName ? (
              <div className="mappings-editor__edit-form">
                <div className="mappings-editor__edit-field">
                  <label className="mappings-editor__edit-label">Card Name</label>
                  <input
                    type="text"
                    value={editCardName}
                    onChange={(e) => setEditCardName(e.target.value)}
                  />
                </div>
                <div className="mappings-editor__edit-field">
                  <label className="mappings-editor__edit-label">
                    Filename Patterns (comma-separated)
                  </label>
                  <input
                    type="text"
                    value={editPatterns}
                    onChange={(e) => setEditPatterns(e.target.value)}
                  />
                </div>
                <div className="mappings-editor__edit-actions">
                  <button onClick={cancelEdit}>Cancel</button>
                  <button className="mappings-editor__save-btn" onClick={saveEdit}>
                    Save
                  </button>
                </div>
              </div>
            ) : (
              <>
                <div className="mappings-editor__card-info">
                  <span className="mappings-editor__card-name">{cardName}</span>
                  <span className="mappings-editor__patterns">
                    {mappings[cardName].join(', ')}
                  </span>
                </div>
                {!readOnly && (
                  <div className="mappings-editor__row-actions">
                    <button
                      className="mappings-editor__row-btn"
                      onClick={() => startEdit(cardName)}
                    >
                      Edit
                    </button>
                    <button
                      className="mappings-editor__row-btn mappings-editor__row-btn--danger"
                      onClick={() => deleteCard(cardName)}
                    >
                      Delete
                    </button>
                  </div>
                )}
              </>
            )}
          </div>
        ))}

        {cardNames.length === 0 && (
          <div className="mappings-editor__empty">
            {search ? 'No matches found' : 'No card mappings defined'}
          </div>
        )}
      </div>

      {!readOnly && (
        <>
          {addingNew ? (
            <div className="mappings-editor__add-form">
              <div className="mappings-editor__edit-field">
                <label className="mappings-editor__edit-label">Card Name</label>
                <input
                  type="text"
                  value={newCardName}
                  onChange={(e) => setNewCardName(e.target.value)}
                  placeholder="e.g. The Fool"
                />
              </div>
              <div className="mappings-editor__edit-field">
                <label className="mappings-editor__edit-label">
                  Filename Patterns (comma-separated)
                </label>
                <input
                  type="text"
                  value={newPatterns}
                  onChange={(e) => setNewPatterns(e.target.value)}
                  placeholder="e.g. 00, 0, fool, thefool"
                />
              </div>
              <div className="mappings-editor__edit-actions">
                <button onClick={() => setAddingNew(false)}>Cancel</button>
                <button className="mappings-editor__save-btn" onClick={addNew}>
                  Add
                </button>
              </div>
            </div>
          ) : (
            <button
              className="mappings-editor__add-btn"
              onClick={() => setAddingNew(true)}
            >
              + Add Card Mapping
            </button>
          )}
        </>
      )}
    </div>
  );
}
