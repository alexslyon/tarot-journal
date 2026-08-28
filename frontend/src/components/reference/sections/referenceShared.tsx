/**
 * Shared plumbing for the content reference sections (Astrology,
 * Kabbalah, Numerology, Chakras):
 *
 * - useReferenceSystem: which correspondence system feeds the
 *   "in your correspondences" cross-references (persisted locally).
 * - useCardPeek: click a card tile anywhere in these sections to open
 *   the full card viewer.
 * - RefTile / AssignedCards: the small building blocks each section
 *   renders its cards and cross-refs with.
 */
import { useMemo, useState, type ReactNode } from 'react';
import { useQuery } from '@tanstack/react-query';
import { CardTile } from '../../profiles/BirthCardsModal';
import CardViewModal from '../../library/CardViewModal';
import { getCorrespondenceSystems } from '../../../api/correspondences';
import type { CorrespondenceSystem } from '../../../types';
import type { AssignedRef } from '../../../api/reference';
import './ReferenceContent.css';

const SYSTEM_STORAGE_KEY = 'tj-reference-system';

/** The correspondence system used for cross-references, remembered
 *  across sessions. Defaults to the first Tarot system. */
export function useReferenceSystem() {
  const { data: systems = [] } = useQuery<CorrespondenceSystem[]>({
    queryKey: ['correspondence-systems'],
    queryFn: getCorrespondenceSystems,
  });
  const [stored, setStored] = useState<string | null>(() => {
    try {
      return localStorage.getItem(SYSTEM_STORAGE_KEY);
    } catch {
      return null;
    }
  });

  // 'none' is an explicit choice; an unknown/absent id falls back to
  // the first Tarot system (deleted systems degrade gracefully).
  const systemId = useMemo(() => {
    if (stored === 'none') return null;
    const id = stored ? Number(stored) : NaN;
    if (systems.some(s => s.id === id)) return id;
    return systems.find(s => s.cartomancy_type === 'Tarot')?.id
      ?? systems[0]?.id ?? null;
  }, [stored, systems]);

  const setSystemId = (id: number | null) => {
    const value = id === null ? 'none' : String(id);
    setStored(value);
    try {
      localStorage.setItem(SYSTEM_STORAGE_KEY, value);
    } catch { /* per-viewer convenience only */ }
  };

  return { systems, systemId, setSystemId };
}

export function ReferenceSystemPicker({ systems, systemId, onChange }: {
  systems: CorrespondenceSystem[];
  systemId: number | null;
  onChange: (id: number | null) => void;
}) {
  if (systems.length === 0) return null;
  return (
    <label className="ref-system-picker">
      <span>Cross-references from</span>
      <select
        value={systemId === null ? 'none' : String(systemId)}
        onChange={(e) => onChange(e.target.value === 'none' ? null : Number(e.target.value))}
      >
        <option value="none">No system</option>
        {systems.map(s => (
          <option key={s.id} value={s.id}>
            {s.name} ({s.cartomancy_type})
          </option>
        ))}
      </select>
    </label>
  );
}

/** Card-viewer modal on demand: call openCard(cardId) from any tile,
 *  render cardModal once at the section root. */
export function useCardPeek() {
  const [cardId, setCardId] = useState<number | null>(null);
  const cardModal: ReactNode = cardId !== null ? (
    <CardViewModal
      cardId={cardId}
      cardIds={[cardId]}
      onClose={() => setCardId(null)}
      onNavigate={setCardId}
    />
  ) : null;
  return { openCard: setCardId, cardModal };
}

/** A birth-cards-style tile that opens the card viewer when the
 *  default Tarot deck has an image for it. */
export function RefTile({ card, caption, onOpen }: {
  card: { name: string; card_id: number | null };
  caption?: string;
  onOpen: (cardId: number) => void;
}) {
  const clickable = card.card_id != null;
  return (
    <div
      className={`ref-tile ${clickable ? 'ref-tile--clickable' : ''}`}
      role={clickable ? 'button' : undefined}
      tabIndex={clickable ? 0 : undefined}
      onClick={() => { if (card.card_id != null) onOpen(card.card_id); }}
      onKeyDown={(e) => {
        if (clickable && (e.key === 'Enter' || e.key === ' ')) {
          e.preventDefault();
          onOpen(card.card_id as number);
        }
      }}
    >
      <CardTile card={card} caption={caption} small />
    </div>
  );
}

/** "In your correspondences" chips — the archetypes the chosen system
 *  assigns to the entity being viewed. */
export function AssignedCards({ refs, onOpenArchetype }: {
  refs: AssignedRef[];
  onOpenArchetype?: (id: number, cartomancyType: string) => void;
}) {
  if (refs.length === 0) return null;
  return (
    <div className="ref-assigned">
      <span className="ref-assigned__label">In your correspondences:</span>
      <div className="ref-assigned__chips">
        {refs.map(ref => (
          <button
            key={ref.archetype_id}
            type="button"
            className="ref-assigned__chip"
            title={ref.cartomancy_type}
            onClick={() => onOpenArchetype?.(ref.archetype_id, ref.cartomancy_type)}
            disabled={!onOpenArchetype}
          >
            {ref.name}
          </button>
        ))}
      </div>
    </div>
  );
}
