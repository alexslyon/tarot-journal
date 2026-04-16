import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { getCardCorrespondences, setCardOverrides } from '../../api/correspondences';
import type { ResolvedCorrespondence } from '../../types';
import { CORRESPONDENCE_FIELDS, CORRESPONDENCE_FIELD_LABELS } from '../../types';
import './CardCorrespondences.css';

interface CardCorrespondencesProps {
  cardId: number;
}

export default function CardCorrespondences({ cardId }: CardCorrespondencesProps) {
  const queryClient = useQueryClient();
  const [editingField, setEditingField] = useState<string | null>(null);
  const [editValue, setEditValue] = useState('');
  const [saving, setSaving] = useState(false);

  const { data: correspondences = [] } = useQuery<ResolvedCorrespondence[]>({
    queryKey: ['card-correspondences', cardId],
    queryFn: () => getCardCorrespondences(cardId),
  });

  // Build a lookup map
  const corrMap = new Map<string, ResolvedCorrespondence>();
  for (const c of correspondences) {
    corrMap.set(c.field_name, c);
  }

  const hasAnyValue = correspondences.some(c => c.value !== null);

  const startEdit = (fieldName: string) => {
    const corr = corrMap.get(fieldName);
    setEditingField(fieldName);
    setEditValue(corr?.value || '');
  };

  const cancelEdit = () => {
    setEditingField(null);
    setEditValue('');
  };

  const saveOverride = async (fieldName: string, value: string) => {
    setSaving(true);
    try {
      await setCardOverrides(cardId, [{ field_name: fieldName, field_value: value || null }]);
      queryClient.invalidateQueries({ queryKey: ['card-correspondences', cardId] });
      setEditingField(null);
      setEditValue('');
    } catch (err) {
      console.error('Failed to save override:', err);
    } finally {
      setSaving(false);
    }
  };

  const revertOverride = async (fieldName: string) => {
    setSaving(true);
    try {
      await setCardOverrides(cardId, [{ field_name: fieldName, field_value: null }]);
      queryClient.invalidateQueries({ queryKey: ['card-correspondences', cardId] });
    } catch (err) {
      console.error('Failed to revert override:', err);
    } finally {
      setSaving(false);
    }
  };

  if (!hasAnyValue && !editingField) {
    return (
      <div className="card-corr">
        <div className="card-corr__empty">
          No correspondences assigned.
          <button className="card-corr__add-btn" onClick={() => startEdit(CORRESPONDENCE_FIELDS[0])}>
            Add Override
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="card-corr">
      <div className="card-corr__grid">
        {CORRESPONDENCE_FIELDS.map(fieldName => {
          const corr = corrMap.get(fieldName);
          const isEditing = editingField === fieldName;
          const hasValue = corr && corr.value !== null;
          const isOverride = corr?.source === 'override';
          const isInherited = corr?.source === 'inherited';

          return (
            <div key={fieldName} className="card-corr__field">
              <label className="card-corr__label">
                {CORRESPONDENCE_FIELD_LABELS[fieldName]}
                {isOverride && <span className="card-corr__badge card-corr__badge--override">override</span>}
                {isInherited && <span className="card-corr__badge card-corr__badge--inherited">inherited</span>}
              </label>

              {isEditing ? (
                <div className="card-corr__edit-row">
                  <input
                    type="text"
                    value={editValue}
                    onChange={e => setEditValue(e.target.value)}
                    className="card-corr__input"
                    autoFocus
                    onKeyDown={e => {
                      if (e.key === 'Enter') saveOverride(fieldName, editValue);
                      if (e.key === 'Escape') cancelEdit();
                    }}
                  />
                  <button
                    className="card-corr__save-btn"
                    onClick={() => saveOverride(fieldName, editValue)}
                    disabled={saving}
                  >
                    Save
                  </button>
                  <button onClick={cancelEdit}>Cancel</button>
                </div>
              ) : (
                <div className="card-corr__value-row" onClick={() => startEdit(fieldName)}>
                  <span className={`card-corr__value ${isInherited ? 'card-corr__value--inherited' : ''} ${!hasValue ? 'card-corr__value--empty' : ''}`}>
                    {hasValue ? corr.value : '—'}
                  </span>
                  {isOverride && (
                    <button
                      className="card-corr__revert-btn"
                      onClick={(e) => { e.stopPropagation(); revertOverride(fieldName); }}
                      title="Revert to inherited value"
                      disabled={saving}
                    >
                      Revert
                    </button>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
