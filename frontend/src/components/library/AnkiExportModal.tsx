import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
  useSortable,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import api from '../../api/client';
import Modal from '../common/Modal';
import './AnkiExportModal.css';

interface FieldOption {
  key: string;
  label: string;
  always?: boolean;
  populated?: boolean;
}

interface AnkiExportModalProps {
  deckId: number;
  deckName: string;
  onClose: () => void;
}

function SortableField({
  field,
  checked,
  onToggle,
}: {
  field: FieldOption;
  checked: boolean;
  onToggle: () => void;
}) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: field.key });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div ref={setNodeRef} style={style} className="anki-export__field-row">
      <span className="anki-export__drag-handle" {...attributes} {...listeners}>
        ⠿
      </span>
      <label className="anki-export__field-label">
        <input
          type="checkbox"
          checked={checked}
          onChange={onToggle}
          disabled={field.always}
        />
        <span>{field.label}</span>
        {field.populated && <span className="anki-export__badge">has data</span>}
        {field.always && <span className="anki-export__badge anki-export__badge--required">required</span>}
      </label>
    </div>
  );
}

export default function AnkiExportModal({ deckId, deckName, onClose }: AnkiExportModalProps) {
  const [orderedFields, setOrderedFields] = useState<FieldOption[]>([]);
  const [selectedKeys, setSelectedKeys] = useState<Set<string>>(new Set());
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState('');

  const { data: availableFields = [], isLoading } = useQuery<FieldOption[]>({
    queryKey: ['anki-fields', deckId],
    queryFn: async () => {
      const res = await api.get(`/api/decks/${deckId}/anki-fields`);
      return res.data;
    },
  });

  // Initialize field order and selection when data loads
  useEffect(() => {
    if (availableFields.length > 0 && orderedFields.length === 0) {
      setOrderedFields(availableFields);
      // Select always-required fields plus any populated ones
      const initial = new Set<string>();
      for (const f of availableFields) {
        if (f.always || f.populated) {
          initial.add(f.key);
        }
      }
      setSelectedKeys(initial);
    }
  }, [availableFields, orderedFields.length]);

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (over && active.id !== over.id) {
      setOrderedFields(prev => {
        const oldIndex = prev.findIndex(f => f.key === active.id);
        const newIndex = prev.findIndex(f => f.key === over.id);
        return arrayMove(prev, oldIndex, newIndex);
      });
    }
  };

  const toggleField = (key: string) => {
    setSelectedKeys(prev => {
      const next = new Set(prev);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  };

  const handleExport = async () => {
    const fields = orderedFields
      .filter(f => selectedKeys.has(f.key))
      .map(f => f.key);

    if (fields.length === 0) {
      setError('Select at least one field.');
      return;
    }

    setExporting(true);
    setError('');
    try {
      const res = await api.post(
        `/api/decks/${deckId}/anki-export`,
        { fields },
        { responseType: 'blob' },
      );
      // Trigger download
      const url = URL.createObjectURL(res.data);
      const a = document.createElement('a');
      a.href = url;
      const safeName = deckName.replace(/[^a-zA-Z0-9 _-]/g, '').trim();
      a.download = `${safeName}_anki.zip`;
      a.click();
      URL.revokeObjectURL(url);
      onClose();
    } catch {
      setError('Export failed. Please try again.');
    } finally {
      setExporting(false);
    }
  };

  const selectedCount = orderedFields.filter(f => selectedKeys.has(f.key)).length;

  return (
    <Modal onClose={onClose} isDirty={false}>
      <div className="anki-export">
        <h2 className="anki-export__title">Export for Anki</h2>
        <p className="anki-export__hint">
          Select and reorder fields for the Anki export. Drag to reorder — column
          order in the export matches this order. The exported zip contains a
          tab-separated text file and card images.
        </p>

        {error && (
          <div className="anki-export__error">{error}</div>
        )}

        {isLoading ? (
          <div className="anki-export__loading">Loading fields...</div>
        ) : (
          <>
            <div className="anki-export__field-list">
              <DndContext
                sensors={sensors}
                collisionDetection={closestCenter}
                onDragEnd={handleDragEnd}
              >
                <SortableContext
                  items={orderedFields.map(f => f.key)}
                  strategy={verticalListSortingStrategy}
                >
                  {orderedFields.map(field => (
                    <SortableField
                      key={field.key}
                      field={field}
                      checked={selectedKeys.has(field.key)}
                      onToggle={() => toggleField(field.key)}
                    />
                  ))}
                </SortableContext>
              </DndContext>
            </div>

            <div className="anki-export__footer">
              <span className="anki-export__count">
                {selectedCount} field{selectedCount !== 1 ? 's' : ''} selected
              </span>
              <div className="anki-export__actions">
                <button onClick={onClose}>Cancel</button>
                <button
                  className="anki-export__export-btn"
                  onClick={handleExport}
                  disabled={exporting || selectedCount === 0}
                >
                  {exporting ? 'Exporting...' : 'Export'}
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </Modal>
  );
}
