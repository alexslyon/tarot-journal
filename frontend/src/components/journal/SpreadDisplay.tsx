import { useQuery } from '@tanstack/react-query';
import { getSpread } from '../../api/spreads';
import { cardThumbnailUrl } from '../../api/images';
import type { EntryReadingParsed, Spread, SpreadPosition } from '../../types';
import './SpreadDisplay.css';

interface SpreadDisplayProps {
  reading: EntryReadingParsed;
}

export default function SpreadDisplay({ reading }: SpreadDisplayProps) {
  const { data: spread } = useQuery<Spread>({
    queryKey: ['spread', reading.spread_id],
    queryFn: () => getSpread(reading.spread_id!),
    enabled: reading.spread_id !== null && reading.spread_id !== undefined,
  });

  const cards = reading.cards_used || [];

  // If we have a spread with parsed positions, use positioned layout
  const positions: SpreadPosition[] =
    spread?.positions && Array.isArray(spread.positions) ? spread.positions : [];

  if (positions.length > 0 && cards.length > 0) {
    return <PositionedLayout cards={cards} positions={positions} spreadName={reading.spread_name} />;
  }

  // Fallback: simple card row
  return <SimpleCardRow cards={cards} spreadName={reading.spread_name} deckName={reading.deck_name} />;
}

function PositionedLayout({
  cards,
  positions,
  spreadName,
}: {
  cards: EntryReadingParsed['cards_used'];
  positions: SpreadPosition[];
  spreadName: string | null;
}) {
  // Calculate bounding box from positions to set container size
  const maxX = Math.max(...positions.map(p => (p.x || 0) + (p.width || 80)));
  const maxY = Math.max(...positions.map(p => (p.y || 0) + (p.height || 120)));
  // Scale down to fit a reasonable display area
  const scale = Math.min(1, 400 / maxX, 350 / maxY);

  return (
    <div className="spread-display">
      {spreadName && <div className="spread-display__name">{spreadName}</div>}
      <div
        className="spread-display__canvas"
        style={{
          width: maxX * scale,
          height: maxY * scale,
          position: 'relative',
        }}
      >
        {positions.map((pos, idx) => {
          const card = cards.find(c => c.position_index === idx) || cards[idx];
          return (
            <div
              key={idx}
              className="spread-display__slot"
              style={{
                position: 'absolute',
                left: (pos.x || 0) * scale,
                top: (pos.y || 0) * scale,
                width: (pos.width || 80) * scale,
                height: (pos.height || 120) * scale,
              }}
              title={pos.label || `Position ${idx + 1}`}
            >
              {card ? (
                <CardSlot card={card} />
              ) : (
                <div className="spread-display__empty-slot">
                  <span className="spread-display__slot-label">{pos.label || idx + 1}</span>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function SimpleCardRow({
  cards,
  spreadName,
  deckName,
}: {
  cards: EntryReadingParsed['cards_used'];
  spreadName: string | null;
  deckName: string | null;
}) {
  return (
    <div className="spread-display">
      <div className="spread-display__header-row">
        {spreadName && <span className="spread-display__name">{spreadName}</span>}
        {deckName && <span className="spread-display__deck">{deckName}</span>}
      </div>
      {cards.length > 0 ? (
        <div className="spread-display__card-row">
          {cards.map((card, idx) => (
            <div key={idx} className="spread-display__card-item">
              <CardSlot card={card} />
            </div>
          ))}
        </div>
      ) : (
        <div className="spread-display__no-cards">No cards recorded</div>
      )}
    </div>
  );
}

function CardSlot({ card }: { card: { name: string; reversed?: boolean; card_id?: number } }) {
  return (
    <div className={`spread-display__card ${card.reversed ? 'spread-display__card--reversed' : ''}`}>
      {card.card_id ? (
        <img
          className="spread-display__card-img"
          src={cardThumbnailUrl(card.card_id)}
          alt={card.name}
          style={card.reversed ? { transform: 'rotate(180deg)' } : undefined}
        />
      ) : (
        <div className="spread-display__card-placeholder" />
      )}
      <div className="spread-display__card-name">
        {card.name}
        {card.reversed && <span className="spread-display__reversed-badge"> R</span>}
      </div>
    </div>
  );
}
