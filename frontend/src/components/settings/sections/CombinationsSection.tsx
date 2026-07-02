import { useState, useEffect } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  getCombinationMeanings,
  createCombinationMeaning,
  updateCombinationMeaning,
  deleteCombinationMeaning,
  reorderCombinationMeanings,
} from '../../../api/combinations';
import { getReferenceSources } from '../../../api/referenceSources';
import { cardPreviewUrl } from '../../../api/images';
import RichTextEditor from '../../common/RichTextEditor';
import RichTextViewer from '../../common/RichTextViewer';
import { useToast } from '../../../context/ToastContext';
import {
  useArchetypeCardList,
  type ArchetypeCardEntry,
} from '../../../utils/useArchetypeCardList';
import type { ReferenceSource, CombinationMeaning } from '../../../types';
import '../SettingsTab.css';
import './CombinationsSection.css';

/** Cartomancy types the Combinations feature supports. */
export const SUPPORTED_COMBINATION_TYPES = [
  'Tarot',
  'Lenormand',
  'Playing Cards',
  'Kipper',
  'Vera Sibilla Italiana / Sibilla della Zingara', 'Sibylle des Salons / Sibilla Indovina',
] as const;

export type CombinationCartomancyType =
  (typeof SUPPORTED_COMBINATION_TYPES)[number];

interface CombinationsSectionProps {
  /** When non-null, pre-select these archetypes (used by the Reference deep-link). */
  initialCombination?: {
    cartomancy_type: string;
    archetype_1_id: number;
    archetype_2_id: number;
  };
  /** Called once after initial selection has been applied. */
  onInitialApplied?: () => void;
}

export default function CombinationsSection({
  initialCombination,
  onInitialApplied,
}: CombinationsSectionProps) {
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  const [cartomancyType, setCartomancyType] =
    useState<CombinationCartomancyType>('Lenormand');
  const [card1Id, setCard1Id] = useState<number | null>(null);
  const [card2Id, setCard2Id] = useState<number | null>(null);

  // Clear the pair whenever the type changes — archetype ids don't
  // carry over across cartomancy types.
  useEffect(() => {
    setCard1Id(null);
    setCard2Id(null);
  }, [cartomancyType]);

  // Apply deep-link selection once when it arrives.
  useEffect(() => {
    if (initialCombination) {
      setCartomancyType(initialCombination.cartomancy_type as CombinationCartomancyType);
      setCard1Id(initialCombination.archetype_1_id);
      setCard2Id(initialCombination.archetype_2_id);
      onInitialApplied?.();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialCombination]);

  const { cardList, defaultDeckId } = useArchetypeCardList(cartomancyType);

  const { data: sources = [] } = useQuery<ReferenceSource[]>({
    queryKey: ['reference-sources'],
    queryFn: () => getReferenceSources(),
  });

  const meaningsKey = ['combination-meanings', cartomancyType, card1Id, card2Id];
  const { data: meanings = [] } = useQuery<CombinationMeaning[]>({
    queryKey: meaningsKey,
    queryFn: () => getCombinationMeanings(cartomancyType, card1Id!, card2Id!),
    enabled: card1Id != null && card2Id != null && card1Id !== card2Id,
  });
  const invalidateMeanings = () =>
    queryClient.invalidateQueries({ queryKey: meaningsKey });

  return (
    <div className="settings-tab__scroll">
      <h2 className="settings-tab__title">Combinations</h2>
      <p className="settings-tab__hint">
        Reference meanings for any ordered pair of cards. The order matters —
        in Lenormand, for instance, Dog + Ring reads differently from Ring + Dog.
      </p>
      <p className="settings-tab__hint">
        Sources are managed in <strong>Reference Sources</strong>. Pick from
        them when adding a meaning below.
      </p>

      <section className="settings-tab__section">
        <h3 className="settings-tab__section-title">Combinations</h3>

        <div className="combinations__type-row">
          <label className="settings-tab__label">Cartomancy type</label>
          <select
            value={cartomancyType}
            onChange={e => setCartomancyType(e.target.value as CombinationCartomancyType)}
          >
            {SUPPORTED_COMBINATION_TYPES.map(t => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </div>

        {defaultDeckId == null && (
          <p className="combinations__warn">
            No default {cartomancyType} deck is set. Card thumbnails come from
            the default deck — set one in <strong>General</strong> settings
            to see them here.
          </p>
        )}

        <div className="combinations__pickers">
          <CardPicker
            label="First card"
            value={card1Id}
            onChange={setCard1Id}
            cardList={cardList}
            excludeId={card2Id}
          />
          <CardPicker
            label="Second card"
            value={card2Id}
            onChange={setCard2Id}
            cardList={cardList}
            excludeId={card1Id}
          />
        </div>

        {card1Id != null && card2Id != null && card1Id !== card2Id && (
          <MeaningsEditor
            cartomancyType={cartomancyType}
            card1Id={card1Id}
            card2Id={card2Id}
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
// Card picker
// ---------------------------------------------------------------------------

function CardPicker({
  label,
  value,
  onChange,
  cardList,
  excludeId,
}: {
  label: string;
  value: number | null;
  onChange: (id: number | null) => void;
  cardList: ArchetypeCardEntry[];
  excludeId: number | null;
}) {
  const selected = value != null ? cardList.find(c => c.archetypeId === value) : null;
  return (
    <div className="combinations__picker">
      <label className="settings-tab__label">{label}</label>
      <select
        value={value ?? ''}
        onChange={e => onChange(e.target.value ? Number(e.target.value) : null)}
      >
        <option value="">Choose card...</option>
        {cardList.map(c => (
          <option
            key={c.archetypeId}
            value={c.archetypeId}
            disabled={c.archetypeId === excludeId}
          >
            {c.rank ? `${c.rank} · ${c.name}` : c.name}
          </option>
        ))}
      </select>
      <div className="combinations__picker-image">
        {selected?.cardId ? (
          <img src={cardPreviewUrl(selected.cardId)} alt={selected.name} />
        ) : selected ? (
          <div className="combinations__placeholder">{selected.name}</div>
        ) : (
          <div className="combinations__placeholder">No selection</div>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Meanings editor
// ---------------------------------------------------------------------------

function MeaningsEditor({
  cartomancyType,
  card1Id,
  card2Id,
  meanings,
  sources,
  onChanged,
  showToast,
}: {
  cartomancyType: string;
  card1Id: number;
  card2Id: number;
  meanings: CombinationMeaning[];
  sources: ReferenceSource[];
  onChanged: () => void;
  showToast: (msg: string) => void;
}) {
  const [draftMeaning, setDraftMeaning] = useState('');
  const [draftSourceId, setDraftSourceId] = useState<number | ''>('');
  const [adding, setAdding] = useState(false);

  const [draggedId, setDraggedId] = useState<number | null>(null);
  const [dragOverId, setDragOverId] = useState<number | null>(null);

  const handleAdd = async () => {
    if (!draftMeaning.trim()) return;
    try {
      await createCombinationMeaning(
        cartomancyType,
        card1Id,
        card2Id,
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
      await reorderCombinationMeanings(combinationId, ids);
      onChanged();
    } catch {
      showToast('Could not reorder meanings.');
    }
    setDraggedId(null);
    setDragOverId(null);
  };

  return (
    <div className="combinations__editor">
      {meanings.length === 0 && !adding && (
        <p className="combinations__empty">
          No meanings yet for this combination.
        </p>
      )}

      <ul className="combinations__meanings">
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
        <div className="combinations__meaning-add">
          <RichTextEditor
            content={draftMeaning}
            onChange={setDraftMeaning}
            placeholder="Meaning..."
            minHeight={80}
          />
          <select
            value={draftSourceId}
            onChange={e => setDraftSourceId(e.target.value ? Number(e.target.value) : '')}
            className="combinations__source-select"
          >
            <option value="">— No source —</option>
            {sources.map(s => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>
          <div className="combinations__meaning-add-actions">
            <button onClick={() => { setAdding(false); setDraftMeaning(''); setDraftSourceId(''); }}>
              Cancel
            </button>
            <button
              onClick={handleAdd}
              disabled={!plainTextHasContent(draftMeaning)}
              className="combinations__save-btn"
            >
              Add Meaning
            </button>
          </div>
        </div>
      ) : (
        <button onClick={() => setAdding(true)} className="combinations__add-meaning-btn">
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
  meaning: CombinationMeaning;
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

  useEffect(() => {
    if (!editing) {
      setDraft(meaning.meaning);
      setDraftSourceId(meaning.source_id ?? '');
    }
  }, [meaning.meaning, meaning.source_id, editing]);

  const handleSave = async () => {
    try {
      await updateCombinationMeaning(meaning.id, {
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
      await deleteCombinationMeaning(meaning.id);
      onChanged();
    } catch {
      showToast('Could not delete meaning.');
    }
  };

  const rowClass = [
    'combinations__meaning-row',
    draggedId === meaning.id ? 'combinations__meaning-row--dragging' : '',
    dragOverId === meaning.id ? 'combinations__meaning-row--drag-over' : '',
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
      <span className="combinations__drag-handle" title="Drag to reorder">⋮⋮</span>
      {editing ? (
        <div className="combinations__meaning-edit">
          <RichTextEditor
            content={draft}
            onChange={setDraft}
            minHeight={80}
          />
          <select
            value={draftSourceId}
            onChange={e => setDraftSourceId(e.target.value ? Number(e.target.value) : '')}
            className="combinations__source-select"
          >
            <option value="">— No source —</option>
            {sources.map(s => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>
          <div className="combinations__meaning-edit-actions">
            <button onClick={() => { setEditing(false); setDraft(meaning.meaning); setDraftSourceId(meaning.source_id ?? ''); }}>
              Cancel
            </button>
            <button onClick={handleSave} className="combinations__save-btn">
              Save
            </button>
          </div>
        </div>
      ) : (
        <div className="combinations__meaning-content">
          <RichTextViewer content={meaning.meaning} />
          <div className="combinations__meaning-meta">
            <span className="combinations__meaning-source">
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

function plainTextHasContent(html: string): boolean {
  return html.replace(/<[^>]*>/g, '').trim().length > 0;
}
