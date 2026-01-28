import { useState } from 'react';
import type { Tag } from '../../types';
import './TagSection.css';

interface TagSectionProps {
  title: string;
  tags: Tag[];
  loading: boolean;
  onAdd: (name: string, color: string) => Promise<void>;
  onUpdate: (tagId: number, name: string, color: string) => Promise<void>;
  onDelete: (tagId: number) => Promise<void>;
}

export default function TagSection({
  title,
  tags,
  loading,
  onAdd,
  onUpdate,
  onDelete,
}: TagSectionProps) {
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editName, setEditName] = useState('');
  const [editColor, setEditColor] = useState('#6B5B95');
  const [isAdding, setIsAdding] = useState(false);
  const [saving, setSaving] = useState(false);

  const startAdd = () => {
    setIsAdding(true);
    setEditingId(null);
    setEditName('');
    setEditColor('#6B5B95');
  };

  const startEdit = (tag: Tag) => {
    setEditingId(tag.id);
    setIsAdding(false);
    setEditName(tag.name);
    setEditColor(tag.color);
  };

  const cancel = () => {
    setEditingId(null);
    setIsAdding(false);
  };

  const handleSave = async () => {
    if (!editName.trim()) return;
    setSaving(true);
    try {
      if (isAdding) {
        await onAdd(editName.trim(), editColor);
        setIsAdding(false);
      } else if (editingId !== null) {
        await onUpdate(editingId, editName.trim(), editColor);
        setEditingId(null);
      }
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (tagId: number, tagName: string) => {
    if (!window.confirm(`Delete tag "${tagName}"? This will remove it from all assignments.`)) return;
    await onDelete(tagId);
  };

  return (
    <div className="tag-section">
      <div className="tag-section__header">
        <h3 className="tag-section__title">{title}</h3>
        <button className="tag-section__add-btn" onClick={startAdd} disabled={isAdding}>
          + Add
        </button>
      </div>

      {/* Add/Edit inline form */}
      {(isAdding || editingId !== null) && (
        <div className="tag-section__edit-row">
          <input
            className="tag-section__edit-name"
            type="text"
            value={editName}
            onChange={(e) => setEditName(e.target.value)}
            placeholder="Tag name"
            onKeyDown={(e) => e.key === 'Enter' && handleSave()}
            autoFocus
          />
          <input
            className="tag-section__edit-color"
            type="color"
            value={editColor}
            onChange={(e) => setEditColor(e.target.value)}
            title="Tag color"
          />
          <button
            className="tag-section__save-btn"
            onClick={handleSave}
            disabled={saving || !editName.trim()}
          >
            {saving ? '...' : 'Save'}
          </button>
          <button className="tag-section__cancel-btn" onClick={cancel}>
            Cancel
          </button>
        </div>
      )}

      {/* Tag list */}
      <div className="tag-section__list">
        {loading && <div className="tag-section__empty">Loading...</div>}
        {!loading && tags.length === 0 && (
          <div className="tag-section__empty">No tags defined.</div>
        )}
        {tags.map((tag) => (
          <div
            key={tag.id}
            className={`tag-section__item ${editingId === tag.id ? 'tag-section__item--editing' : ''}`}
          >
            <span
              className="tag-section__badge"
              style={{ backgroundColor: tag.color }}
            >
              {tag.name}
            </span>
            <div className="tag-section__item-actions">
              <button
                className="tag-section__edit-btn"
                onClick={() => startEdit(tag)}
                title="Edit"
              >
                &#9998;
              </button>
              <button
                className="tag-section__delete-btn"
                onClick={() => handleDelete(tag.id, tag.name)}
                title="Delete"
              >
                &times;
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
