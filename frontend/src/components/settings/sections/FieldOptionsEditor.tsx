import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  getFieldOptions,
  addFieldOption,
  updateFieldOption,
  deleteFieldOption,
  reorderFieldOptions,
  type FieldOption,
} from '../../../api/correspondences';
import { CORRESPONDENCE_FIELDS, CORRESPONDENCE_FIELD_LABELS } from '../../../types';

interface FieldOptionsEditorProps {
  onClose: () => void;
}

export default function FieldOptionsEditor({ onClose }: FieldOptionsEditorProps) {
  const queryClient = useQueryClient();
  const [activeField, setActiveField] = useState<string>(CORRESPONDENCE_FIELDS[0]);
  const [newValue, setNewValue] = useState('');
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editingValue, setEditingValue] = useState('');

  const { data: options = [] } = useQuery<FieldOption[]>({
    queryKey: ['field-options', activeField],
    queryFn: () => getFieldOptions(activeField),
  });

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['field-options'] });
    // Renames cascade to correspondence_assignments + card_correspondence_overrides,
    // so refresh any cached views of that data too.
    queryClient.invalidateQueries({ queryKey: ['correspondence-system'] });
    queryClient.invalidateQueries({ queryKey: ['correspondence-systems'] });
    queryClient.invalidateQueries({ queryKey: ['card-correspondences'] });
    queryClient.invalidateQueries({ queryKey: ['correspondence-compare'] });
  };

  const handleAdd = async () => {
    const v = newValue.trim();
    if (!v) return;
    try {
      await addFieldOption(activeField, v);
      invalidate();
      setNewValue('');
    } catch {
      // ignore (likely duplicate)
    }
  };

  const handleDelete = async (opt: FieldOption) => {
    if (!window.confirm(`Remove "${opt.option_value}" from ${CORRESPONDENCE_FIELD_LABELS[activeField]} options?\n\nExisting assignments using this value will be preserved.`)) return;
    await deleteFieldOption(opt.id);
    invalidate();
  };

  const handleStartEdit = (opt: FieldOption) => {
    setEditingId(opt.id);
    setEditingValue(opt.option_value);
  };

  const handleSaveEdit = async () => {
    if (editingId == null || !editingValue.trim()) return;
    await updateFieldOption(editingId, { option_value: editingValue.trim() });
    invalidate();
    setEditingId(null);
    setEditingValue('');
  };

  const move = async (index: number, delta: number) => {
    const next = index + delta;
    if (next < 0 || next >= options.length) return;
    const reordered = [...options];
    [reordered[index], reordered[next]] = [reordered[next], reordered[index]];
    await reorderFieldOptions(activeField, reordered.map(o => o.id));
    invalidate();
  };

  return (
    <div className="field-options">
      <div className="field-options__header">
        <h3 className="settings-tab__section-title" style={{ margin: 0 }}>Field Options</h3>
        <button onClick={onClose}>Close</button>
      </div>

      <p className="settings-tab__hint">
        These are the values available in the dropdowns when editing correspondences.
        Changes apply across all correspondence systems.
      </p>

      {/* Field tabs */}
      <div className="field-options__tabs">
        {CORRESPONDENCE_FIELDS.map(f => (
          <button
            key={f}
            className={`field-options__tab ${activeField === f ? 'field-options__tab--active' : ''}`}
            onClick={() => setActiveField(f)}
          >
            {CORRESPONDENCE_FIELD_LABELS[f]}
          </button>
        ))}
      </div>

      {/* Options list */}
      <div className="field-options__list">
        {options.map((opt, i) => (
          <div key={opt.id} className="field-options__row">
            {editingId === opt.id ? (
              <>
                <input
                  type="text"
                  value={editingValue}
                  onChange={e => setEditingValue(e.target.value)}
                  onKeyDown={e => {
                    if (e.key === 'Enter') handleSaveEdit();
                    if (e.key === 'Escape') { setEditingId(null); setEditingValue(''); }
                  }}
                  autoFocus
                  className="field-options__input"
                />
                <button className="settings-tab__save-btn" onClick={handleSaveEdit}>Save</button>
                <button onClick={() => { setEditingId(null); setEditingValue(''); }}>Cancel</button>
              </>
            ) : (
              <>
                <span className="field-options__value">{opt.option_value}</span>
                <button onClick={() => move(i, -1)} disabled={i === 0} title="Move up">↑</button>
                <button onClick={() => move(i, 1)} disabled={i === options.length - 1} title="Move down">↓</button>
                <button onClick={() => handleStartEdit(opt)}>Edit</button>
                <button
                  className="settings-tab__import-preset-btn settings-tab__import-preset-btn--danger"
                  onClick={() => handleDelete(opt)}
                >
                  Delete
                </button>
              </>
            )}
          </div>
        ))}

        {options.length === 0 && (
          <p className="settings-tab__hint" style={{ textAlign: 'center', padding: 12 }}>
            No options yet. Add one below.
          </p>
        )}
      </div>

      {/* Add new */}
      <div className="field-options__add-row">
        <input
          type="text"
          value={newValue}
          onChange={e => setNewValue(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter') handleAdd(); }}
          placeholder={`New ${CORRESPONDENCE_FIELD_LABELS[activeField]} option...`}
          className="field-options__input"
        />
        <button className="settings-tab__save-btn" onClick={handleAdd} disabled={!newValue.trim()}>
          Add
        </button>
      </div>
    </div>
  );
}
