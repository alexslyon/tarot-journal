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
  // Calculate the actual bounding box of content (trimming empty space)
  const minX = Math.min(...positions.map(p => p.x || 0));
  const minY = Math.min(...positions.map(p => p.y || 0));
  const maxX = Math.max(...positions.map(p => (p.x || 0) + (p.width || 80)));
  const maxY = Math.max(...positions.map(p => (p.y || 0) + (p.height || 120)));

  // Content dimensions after trimming empty space
  const contentWidth = maxX - minX;
  const contentHeight = maxY - minY;

  // Use CSS to scale - we'll set a max-width and let the container handle sizing
  // The aspect ratio is maintained via the height calculation
  const aspectRatio = contentHeight / contentWidth;

  return (
    <div className="spread-display spread-display--positioned">
      {spreadName && <div className="spread-display__name">{spreadName}</div>}
      <div
        className="spread-display__canvas"
        style={{
          width: '100%',
          paddingBottom: `${aspectRatio * 100}%`,
          position: 'relative',
        }}
      >
        <div className="spread-display__canvas-inner">
          {positions.map((pos, idx) => {
            const card = cards.find(c => c.position_index === idx) || cards[idx];
            // Calculate position as percentage of content area (offset by minX/minY)
            const leftPct = ((pos.x || 0) - minX) / contentWidth * 100;
            const topPct = ((pos.y || 0) - minY) / contentHeight * 100;
            const widthPct = (pos.width || 80) / contentWidth * 100;
            const heightPct = (pos.height || 120) / contentHeight * 100;

            return (
              <div
                key={idx}
                className={`spread-display__slot ${card?.reversed ? 'spread-display__slot--reversed' : ''}`}
                style={{
                  position: 'absolute',
                  left: `${leftPct}%`,
                  top: `${topPct}%`,
                  width: `${widthPct}%`,
                  height: `${heightPct}%`,
                }}
                title={`${pos.label || `Position ${idx + 1}`}${card ? `: ${card.name}${card.reversed ? ' (R)' : ''}` : ''}`}
              >
                {/* Position badge */}
                <span className="spread-display__slot-badge">{pos.key || idx + 1}</span>
                {card ? (
                  <CardSlot card={card} hideLabel />
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

      {/* Legend showing position labels and card names */}
      <div className="spread-display__legend">
        {positions.map((pos, idx) => {
          const card = cards.find(c => c.position_index === idx) || cards[idx];
          return (
            <div key={idx} className="spread-display__legend-item">
              <span className="spread-display__legend-key">{pos.key || idx + 1}</span>
              <span className="spread-display__legend-label">{pos.label || `Position ${idx + 1}`}:</span>
              <span className={`spread-display__legend-card ${card?.reversed ? 'spread-display__legend-card--reversed' : ''}`}>
                {card?.name || '—'}
                {card?.reversed && <span className="spread-display__reversed-badge"> R</span>}
              </span>
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

function CardSlot({ card, hideLabel }: { card: { name: string; reversed?: boolean; card_id?: number }; hideLabel?: boolean }) {
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
      {!hideLabel && (
        <div className="spread-display__card-name">
          {card.name}
          {card.reversed && <span className="spread-display__reversed-badge"> R</span>}
        </div>
      )}
    </div>
  );
}
