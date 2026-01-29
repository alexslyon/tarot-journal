import { useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getDecks } from '../../api/decks';
import { getCards } from '../../api/cards';
import { getSpreads, getSpread } from '../../api/spreads';
import { cardThumbnailUrl } from '../../api/images';
import type { Card, Spread, SpreadPosition } from '../../types';
import './ReadingEditor.css';

export interface ReadingData {
  spread_id: number | null;
  spread_name: string | null;
  deck_id: number | null;
  deck_name: string | null;
  cartomancy_type: string | null;
  cards: Array<{
    name: string;
    reversed: boolean;
    deck_id?: number;
    deck_name?: string;
    position_index?: number;
  }>;
}

interface ReadingEditorProps {
  value: ReadingData;
  onChange: (data: ReadingData) => void;
  onRemove: () => void;
  index: number;
}

export default function ReadingEditor({ value, onChange, onRemove, index }: ReadingEditorProps) {
  const { data: decks = [] } = useQuery({
    queryKey: ['decks'],
    queryFn: () => getDecks(),
  });

  const { data: spreads = [] } = useQuery<Spread[]>({
    queryKey: ['spreads'],
    queryFn: getSpreads,
  });

  const { data: spread } = useQuery<Spread>({
    queryKey: ['spread', value.spread_id],
    queryFn: () => getSpread(value.spread_id!),
    enabled: value.spread_id !== null && value.spread_id !== undefined,
  });

  const { data: deckCards = [] } = useQuery({
    queryKey: ['cards', value.deck_id],
    queryFn: () => getCards(value.deck_id!),
    enabled: value.deck_id !== null && value.deck_id !== undefined,
  });

  const positions: SpreadPosition[] =
    spread?.positions && Array.isArray(spread.positions) ? spread.positions : [];

  // When spread changes, resize cards array to match positions
  useEffect(() => {
    if (positions.length > 0 && value.cards.length !== positions.length) {
      const newCards = positions.map((_, idx) => {
        return value.cards[idx] || { name: '', reversed: false, position_index: idx };
      });
      onChange({ ...value, cards: newCards });
    }
  }, [positions.length]);

  const handleSpreadChange = (spreadId: number | null) => {
    const selectedSpread = spreads.find(s => s.id === spreadId);
    onChange({
      ...value,
      spread_id: spreadId,
      spread_name: selectedSpread?.name || null,
      cards: [],
    });
  };

  const handleDeckChange = (deckId: number | null) => {
    const selectedDeck = decks.find(d => d.id === deckId);
    onChange({
      ...value,
      deck_id: deckId,
      deck_name: selectedDeck?.name || null,
      cartomancy_type: selectedDeck?.cartomancy_type || null,
    });
  };

  const updateCard = (idx: number, field: string, val: string | boolean) => {
    const newCards = [...value.cards];
    newCards[idx] = { ...newCards[idx], [field]: val, position_index: idx };
    // When selecting a card by name, also store deck info
    if (field === 'name' && value.deck_id) {
      newCards[idx].deck_id = value.deck_id;
      newCards[idx].deck_name = value.deck_name || undefined;
    }
    onChange({ ...value, cards: newCards });
  };

  const addCard = () => {
    onChange({
      ...value,
      cards: [
        ...value.cards,
        {
          name: '',
          reversed: false,
          position_index: value.cards.length,
          deck_id: value.deck_id || undefined,
          deck_name: value.deck_name || undefined,
        },
      ],
    });
  };

  const removeCard = (idx: number) => {
    onChange({
      ...value,
      cards: value.cards.filter((_, i) => i !== idx),
    });
  };

  return (
    <div className="reading-editor">
      <div className="reading-editor__header">
        <span className="reading-editor__label">Reading {index + 1}</span>
        <button
          className="reading-editor__remove-btn"
          onClick={onRemove}
          title="Remove reading"
        >
          &times;
        </button>
      </div>

      <div className="reading-editor__row">
        <div className="reading-editor__field">
          <label className="reading-editor__field-label">Spread</label>
          <select
            value={value.spread_id ?? ''}
            onChange={(e) => handleSpreadChange(e.target.value ? Number(e.target.value) : null)}
          >
            <option value="">No Spread</option>
            {spreads.map((s) => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>
        </div>

        <div className="reading-editor__field">
          <label className="reading-editor__field-label">Deck</label>
          <select
            value={value.deck_id ?? ''}
            onChange={(e) => handleDeckChange(e.target.value ? Number(e.target.value) : null)}
          >
            <option value="">No Deck</option>
            {decks.map((d) => (
              <option key={d.id} value={d.id}>{d.name}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Card slots */}
      <div className="reading-editor__cards">
        {positions.length > 0 ? (
          // Spread with positions: show visual canvas layout
          <VisualSpreadEditor
            positions={positions}
            cards={value.cards}
            deckCards={deckCards}
            onUpdateCard={updateCard}
          />
        ) : (
          // No spread: free-form card list
          <>
            {value.cards.map((card, idx) => (
              <div key={idx} className="reading-editor__card-slot">
                {deckCards.length > 0 ? (
                  <select
                    className="reading-editor__card-select"
                    value={card.name}
                    onChange={(e) => updateCard(idx, 'name', e.target.value)}
                  >
                    <option value="">— select card —</option>
                    {deckCards.map((c) => (
                      <option key={c.id} value={c.name}>{c.name}</option>
                    ))}
                  </select>
                ) : (
                  <input
                    className="reading-editor__card-input"
                    type="text"
                    value={card.name}
                    onChange={(e) => updateCard(idx, 'name', e.target.value)}
                    placeholder="Card name"
                  />
                )}
                <label className="reading-editor__reversed">
                  <input
                    type="checkbox"
                    checked={card.reversed}
                    onChange={(e) => updateCard(idx, 'reversed', e.target.checked)}
                  />
                  <span>R</span>
                </label>
                <button
                  className="reading-editor__card-remove"
                  onClick={() => removeCard(idx)}
                  title="Remove card"
                >
                  &times;
                </button>
              </div>
            ))}
            <button className="reading-editor__add-card" onClick={addCard}>
              + Add Card
            </button>
          </>
        )}
      </div>
    </div>
  );
}

/** Visual canvas editor for spread positions */
function VisualSpreadEditor({
  positions,
  cards,
  deckCards,
  onUpdateCard,
}: {
  positions: SpreadPosition[];
  cards: ReadingData['cards'];
  deckCards: Card[];
  onUpdateCard: (idx: number, field: string, val: string | boolean) => void;
}) {
  // Calculate bounding box and scale to fit within a reasonable size
  const maxX = Math.max(...positions.map(p => (p.x || 0) + (p.width || 80)));
  const maxY = Math.max(...positions.map(p => (p.y || 0) + (p.height || 120)));
  // Scale to fit in ~450x350 area
  const scale = Math.min(1, 450 / maxX, 350 / maxY);

  // Find card_id for a given card name
  const getCardId = (name: string): number | undefined => {
    const found = deckCards.find(c => c.name === name);
    return found?.id;
  };

  return (
    <div className="reading-editor__visual">
      {/* Visual canvas showing card layout */}
      <div
        className="reading-editor__canvas"
        style={{
          width: maxX * scale + 16,
          height: maxY * scale + 16,
          position: 'relative',
        }}
      >
        {positions.map((pos, idx) => {
          const card = cards[idx];
          const cardId = card?.name ? getCardId(card.name) : undefined;
          const slotWidth = (pos.width || 80) * scale;
          const slotHeight = (pos.height || 120) * scale;

          return (
            <div
              key={idx}
              className={`reading-editor__visual-slot ${card?.reversed ? 'reading-editor__visual-slot--reversed' : ''}`}
              style={{
                position: 'absolute',
                left: (pos.x || 0) * scale + 8,
                top: (pos.y || 0) * scale + 8,
                width: slotWidth,
                height: slotHeight,
              }}
              title={`${pos.label || `Position ${idx + 1}`}${card?.name ? `: ${card.name}` : ''}`}
            >
              {cardId ? (
                <img
                  className="reading-editor__visual-img"
                  src={cardThumbnailUrl(cardId)}
                  alt={card.name}
                  style={card.reversed ? { transform: 'rotate(180deg)' } : undefined}
                />
              ) : (
                <div className="reading-editor__visual-placeholder">
                  <span className="reading-editor__visual-idx">{pos.key || idx + 1}</span>
                </div>
              )}
              {/* Small badge showing position key */}
              <span className="reading-editor__visual-badge">{pos.key || idx + 1}</span>
            </div>
          );
        })}
      </div>

      {/* Card selection list below canvas */}
      <div className="reading-editor__position-list">
        {positions.map((pos, idx) => {
          const card = cards[idx];
          return (
            <div key={idx} className="reading-editor__position-row">
              <span className="reading-editor__position-key">{pos.key || idx + 1}</span>
              <span className="reading-editor__position-label">{pos.label || `Position ${idx + 1}`}</span>
              <select
                className="reading-editor__card-select"
                value={card?.name || ''}
                onChange={(e) => onUpdateCard(idx, 'name', e.target.value)}
              >
                <option value="">— select card —</option>
                {deckCards.map((c) => (
                  <option key={c.id} value={c.name}>{c.name}</option>
                ))}
              </select>
              <label className="reading-editor__reversed">
                <input
                  type="checkbox"
                  checked={card?.reversed || false}
                  onChange={(e) => onUpdateCard(idx, 'reversed', e.target.checked)}
                />
                <span>R</span>
              </label>
            </div>
          );
        })}
      </div>
    </div>
  );
}
