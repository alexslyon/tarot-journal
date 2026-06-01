import { useState, useEffect } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  getLenormandMeanings,
  createLenormandMeaning,
  updateLenormandMeaning,
  deleteLenormandMeaning,
  reorderLenormandMeanings,
} from '../../../api/lenormandCombinations';
import { getReferenceSources } from '../../../api/referenceSources';
import { cardPreviewUrl } from '../../../api/images';
import RichTextEditor from '../../common/RichTextEditor';
import RichTextViewer from '../../common/RichTextViewer';
import { useToast } from '../../../context/ToastContext';
import { useLenormandCardList, type LenormandCardEntry } from '../../../utils/useLenormandCardList';
import type { ReferenceSource, LenormandMeaning } from '../../../types';
import '../SettingsTab.css';
import './LenormandCombinationsSection.css';

interface LenormandCombinationsSectionProps {
  /** When non-null, pre-select these card numbers (used by the Reference deep-link). */
  initialCards?: { card_1: number; card_2: number };
  /** Called once after initial card selection has been applied. */
  onInitialApplied?: () => void;
}

export default function LenormandCombinationsSection({
  initialCards,
  onInitialApplied,
}: LenormandCombinationsSectionProps) {
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  const { cardList, defaultDeckId: lenormandDeckId } = useLenormandCardList();

  // === Two-card selection ===
  const [card1, setCard1] = useState<number | null>(null);
  const [card2, setCard2] = useState<number | null>(null);

  // Apply deep-link selection once when it arrives
  useEffect(() => {
    if (initialCards) {
      setCard1(initialCards.card_1);
      setCard2(initialCards.card_2);
      onInitialApplied?.();
    }
  }, [initialCards, onInitialApplied]);

  // === Sources (read-only here; managed in the Reference Sources section) ===
  const { data: sources = [] } = useQuery<ReferenceSource[]>({
    queryKey: ['reference-sources'],
    queryFn: () => getReferenceSources(),
  });

  // === Meanings for the selected combination ===
  const meaningsKey = ['lenormand-meanings', card1, card2];
  const { data: meanings = [] } = useQuery<LenormandMeaning[]>({
    queryKey: meaningsKey,
    queryFn: () => getLenormandMeanings(card1!, card2!),
    enabled: card1 != null && card2 != null && card1 !== card2,
  });
  const invalidateMeanings = () =>
    queryClient.invalidateQueries({ queryKey: ['lenormand-meanings', card1, card2] });

  return (
    <div className="settings-tab__scroll">
      <h2 className="settings-tab__title">Lenormand Combinations</h2>
      <p className="settings-tab__hint">
        Reference meanings for any ordered pair of Lenormand cards. The order
        matters — Dog + Ring is different from Ring + Dog.
      </p>

      <p className="settings-tab__hint">
        Sources are managed in <strong>Reference Sources</strong>. Pick from
        them when adding a meaning below.
      </p>

      <section className="settings-tab__section">
        <h3 className="settings-tab__section-title">Combinations</h3>

        {lenormandDeckId == null && (
          <p className="lenormand-comb__warn">
            No default Lenormand deck is set. Card names and images are pulled
            from the default deck — set one in <strong>General</strong> settings
            to see them here.
          </p>
        )}

        <div className="lenormand-comb__pickers">
          <CardPicker
            label="First card"
            value={card1}
            onChange={setCard1}
            cardList={cardList}
            excludeNum={card2}
          />
          <CardPicker
            label="Second card"
            value={card2}
            onChange={setCard2}
            cardList={cardList}
            excludeNum={card1}
          />
        </div>

        {card1 != null && card2 != null && card1 !== card2 && (
          <MeaningsEditor
            card1={card1}
            card2={card2}
            meanings={meanings}
            sources={sources}
            onChanged={invalidateMeanings}
            showToast={showToast}
          />
        )}
      </section>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Card picker (shared between editor and viewer)
// ---------------------------------------------------------------------------

function CardPicker({
  label,
  value,
  onChange,
  cardList,
  excludeNum,
}: {
  label: string;
  value: number | null;
  onChange: (n: number | null) => void;
  cardList: LenormandCardEntry[];
  excludeNum: number | null;
}) {
  const selected = value != null ? cardList.find(c => c.num === value) : null;
  return (
    <div className="lenormand-comb__picker">
      <label className="settings-tab__label">{label}</label>
      <select
        value={value ?? ''}
        onChange={e => onChange(e.target.value ? Number(e.target.value) : null)}
      >
        <option value="">Choose card...</option>
        {cardList.map(c => (
          <option key={c.num} value={c.num} disabled={c.num === excludeNum}>
            {c.num} · {c.name}
          </option>
        ))}
      </select>
      <div className="lenormand-comb__picker-image">
        {selected?.cardId ? (
          <img src={cardPreviewUrl(selected.cardId)} alt={selected.name} />
        ) : selected ? (
          <div className="lenormand-comb__placeholder">{selected.name}</div>
        ) : (
          <div className="lenormand-comb__placeholder">No selection</div>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Meanings editor (for the selected combination)
// ---------------------------------------------------------------------------

function MeaningsEditor({
  card1,
  card2,
  meanings,
  sources,
  onChanged,
  showToast,
}: {
  card1: number;
  card2: number;
  meanings: LenormandMeaning[];
  sources: ReferenceSource[];
  onChanged: () => void;
  showToast: (msg: string) => void;
}) {
  const [draftMeaning, setDraftMeaning] = useState('');
  const [draftSourceId, setDraftSourceId] = useState<number | ''>('');
  const [adding, setAdding] = useState(false);

  // Drag-to-reorder
  const [draggedId, setDraggedId] = useState<number | null>(null);
  const [dragOverId, setDragOverId] = useState<number | null>(null);

  const handleAdd = async () => {
    if (!draftMeaning.trim()) return;
    try {
      await createLenormandMeaning(
        card1,
        card2,
        draftMeaning,
        draftSourceId === '' ? null : draftSourceId,
      );
      setDraftMeaning('');
      setDraftSourceId('');
      setAdding(false);
      onChanged();
    } catch {
      showToast('Could not add meaning.');
    }
  };

  const handleDrop = async (targetId: number) => {
    if (draggedId == null || draggedId === targetId) {
      setDraggedId(null);
      setDragOverId(null);
      return;
    }
    const ids = meanings.map(m => m.id);
    const fromIdx = ids.indexOf(draggedId);
    const toIdx = ids.indexOf(targetId);
    if (fromIdx === -1 || toIdx === -1) {
      setDraggedId(null);
      setDragOverId(null);
      return;
    }
    ids.splice(fromIdx, 1);
    ids.splice(toIdx, 0, draggedId);
    const combinationId = meanings[0]?.combination_id;
    if (combinationId == null) return;
    try {
      await reorderLenormandMeanings(combinationId, ids);
      onChanged();
    } catch {
      showToast('Could not reorder meanings.');
    }
    setDraggedId(null);
    setDragOverId(null);
  };

  return (
    <div className="lenormand-comb__editor">
      {meanings.length === 0 && !adding && (
        <p className="lenormand-comb__empty">
          No meanings yet for this combination.
        </p>
      )}

      <ul className="lenormand-comb__meanings">
        {meanings.map(m => (
          <MeaningRow
            key={m.id}
            meaning={m}
            sources={sources}
            onChanged={onChanged}
            showToast={showToast}
            draggedId={draggedId}
            dragOverId={dragOverId}
            onDragStart={setDraggedId}
            onDragOver={setDragOverId}
            onDrop={handleDrop}
            onDragEnd={() => { setDraggedId(null); setDragOverId(null); }}
          />
        ))}
      </ul>

      {adding ? (
        <div className="lenormand-comb__meaning-add">
          <RichTextEditor
            content={draftMeaning}
            onChange={setDraftMeaning}
            placeholder="Meaning..."
            minHeight={80}
          />
          <select
            value={draftSourceId}
            onChange={e => setDraftSourceId(e.target.value ? Number(e.target.value) : '')}
            className="lenormand-comb__source-select"
          >
            <option value="">— No source —</option>
            {sources.map(s => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>
          <div className="lenormand-comb__meaning-add-actions">
            <button onClick={() => { setAdding(false); setDraftMeaning(''); setDraftSourceId(''); }}>
              Cancel
            </button>
            <button
              onClick={handleAdd}
              disabled={!plainTextHasContent(draftMeaning)}
              className="lenormand-comb__save-btn"
            >
              Add Meaning
            </button>
          </div>
        </div>
      ) : (
        <button onClick={() => setAdding(true)} className="lenormand-comb__add-meaning-btn">
          + Add Meaning
        </button>
      )}
    </div>
  );
}

function MeaningRow({
  meaning,
  sources,
  onChanged,
  showToast,
  draggedId,
  dragOverId,
  onDragStart,
  onDragOver,
  onDrop,
  onDragEnd,
}: {
  meaning: LenormandMeaning;
  sources: ReferenceSource[];
  onChanged: () => void;
  showToast: (msg: string) => void;
  draggedId: number | null;
  dragOverId: number | null;
  onDragStart: (id: number) => void;
  onDragOver: (id: number) => void;
  onDrop: (id: number) => void;
  onDragEnd: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(meaning.meaning);
  const [draftSourceId, setDraftSourceId] = useState<number | ''>(
    meaning.source_id ?? '',
  );

  // Reset draft when the underlying record changes (e.g. from optimistic refresh)
  useEffect(() => {
    if (!editing) {
      setDraft(meaning.meaning);
      setDraftSourceId(meaning.source_id ?? '');
    }
  }, [meaning.meaning, meaning.source_id, editing]);

  const handleSave = async () => {
    try {
      await updateLenormandMeaning(meaning.id, {
        meaning: draft,
        source_id: draftSourceId === '' ? null : draftSourceId,
      });
      setEditing(false);
      onChanged();
    } catch {
      showToast('Could not update meaning.');
    }
  };

  const handleDelete = async () => {
    if (!window.confirm('Delete this meaning?')) return;
    try {
      await deleteLenormandMeaning(meaning.id);
      onChanged();
    } catch {
      showToast('Could not delete meaning.');
    }
  };

  const rowClass = [
    'lenormand-comb__meaning-row',
    draggedId === meaning.id ? 'lenormand-comb__meaning-row--dragging' : '',
    dragOverId === meaning.id ? 'lenormand-comb__meaning-row--drag-over' : '',
  ].filter(Boolean).join(' ');

  return (
    <li
      className={rowClass}
      draggable={!editing}
      onDragStart={() => onDragStart(meaning.id)}
      onDragOver={e => {
        if (draggedId == null || draggedId === meaning.id) return;
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
        if (dragOverId !== meaning.id) onDragOver(meaning.id);
      }}
      onDrop={e => { e.preventDefault(); onDrop(meaning.id); }}
      onDragEnd={onDragEnd}
    >
      <span className="lenormand-comb__drag-handle" title="Drag to reorder">⋮⋮</span>
      {editing ? (
        <div className="lenormand-comb__meaning-edit">
          <RichTextEditor
            content={draft}
            onChange={setDraft}
            minHeight={80}
          />
          <select
            value={draftSourceId}
            onChange={e => setDraftSourceId(e.target.value ? Number(e.target.value) : '')}
            className="lenormand-comb__source-select"
          >
            <option value="">— No source —</option>
            {sources.map(s => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>
          <div className="lenormand-comb__meaning-edit-actions">
            <button onClick={() => { setEditing(false); setDraft(meaning.meaning); setDraftSourceId(meaning.source_id ?? ''); }}>
              Cancel
            </button>
            <button onClick={handleSave} className="lenormand-comb__save-btn">
              Save
            </button>
          </div>
        </div>
      ) : (
        <div className="lenormand-comb__meaning-content">
          <RichTextViewer content={meaning.meaning} />
          <div className="lenormand-comb__meaning-meta">
            <span className="lenormand-comb__meaning-source">
              {meaning.source_name || 'Unsourced'}
            </span>
            <button onClick={() => setEditing(true)}>Edit</button>
            <button onClick={handleDelete} className="danger">Delete</button>
          </div>
        </div>
      )}
    </li>
  );
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function plainTextHasContent(html: string): boolean {
  return html.replace(/<[^>]*>/g, '').trim().length > 0;
}
