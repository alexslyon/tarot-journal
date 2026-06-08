import { useQuery, useQueryClient } from '@tanstack/react-query';
import { getCard, deleteCard } from '../../api/cards';
import { getCardCorrespondences } from '../../api/correspondences';
import { cardPreviewUrl } from '../../api/images';
import { useToast } from '../../context/ToastContext';
import type { Card, Tag, CardGroup, ResolvedCorrespondence } from '../../types';
import { CORRESPONDENCE_FIELDS, CORRESPONDENCE_FIELD_LABELS } from '../../types';
import Modal from '../common/Modal';
import RichTextViewer from '../common/RichTextViewer';
import './CardViewModal.css';

interface CardViewModalProps {
  cardId: number | null;
  cardIds: number[];
  onClose: () => void;
  onNavigate: (cardId: number) => void;
  onEdit?: (cardId: number) => void;
  onDeleted?: () => void;
}

interface CardDetail extends Card {
  deck_name?: string;
  cartomancy_type_name?: string;
  own_tags?: Tag[];
  inherited_tags?: Tag[];
  groups?: CardGroup[];
  card_custom_fields?: Array<{
    field_name: string;
    field_value: string | null;
    field_type: string;
  }>;
}

export default function CardViewModal({ cardId, cardIds, onClose, onNavigate, onEdit, onDeleted }: CardViewModalProps) {
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  const { data: card, isLoading } = useQuery<CardDetail>({
    queryKey: ['card-detail', cardId],
    queryFn: () => getCard(cardId!),
    enabled: cardId !== null,
  });

  const { data: correspondences = [] } = useQuery<ResolvedCorrespondence[]>({
    queryKey: ['card-correspondences', cardId],
    queryFn: () => getCardCorrespondences(cardId!),
    enabled: cardId !== null,
  });

  // Only show correspondence fields that resolved to a value
  const populatedCorrespondences = CORRESPONDENCE_FIELDS
    .map(f => correspondences.find(c => c.field_name === f))
    .filter((c): c is ResolvedCorrespondence => !!c && c.values.length > 0);

  if (cardId === null) return null;

  const currentIndex = cardIds.indexOf(cardId);
  const hasPrev = currentIndex > 0;
  const hasNext = currentIndex < cardIds.length - 1;

  const isIChing = card?.cartomancy_type_name === 'I Ching';

  // Parse old custom_fields JSON blob (legacy storage)
  let customFields: Record<string, string> = {};
  if (card?.custom_fields) {
    try {
      customFields = JSON.parse(card.custom_fields);
    } catch { /* ignore */ }
  }

  // Fields shown elsewhere (I Ching fields displayed in Classification section)
  const iChingFieldKeys = ['traditional_chinese', 'simplified_chinese'];

  // Check if a field value has actual content (not empty or just empty HTML tags)
  const hasContent = (value: string | null | undefined): boolean => {
    if (!value) return false;
    // Strip HTML tags and check if anything remains
    const textContent = value.replace(/<[^>]*>/g, '').trim();
    return textContent.length > 0;
  };

  // Convert old JSON entries to display format, excluding I Ching fields and empty values
  const legacyFields = Object.entries(customFields)
    .filter(([key, value]) => !iChingFieldKeys.includes(key) && hasContent(value))
    .map(([key, value]) => ({ field_name: key, field_value: value }));

  // Combine with new table-based custom fields, excluding empty values
  const tableFields = (card?.card_custom_fields || [])
    .filter(f => !iChingFieldKeys.includes(f.field_name) && hasContent(f.field_value))
    .map(f => ({ field_name: f.field_name, field_value: f.field_value || '' }));

  // Some cards have a field in both stores after the old-to-new
  // migration: the legacy JSON blob isn't cleared when an entry is
  // re-saved through the new card_custom_fields table. Hide any
  // legacy entry whose name also exists in the table (case-
  // insensitive), so the same field doesn't render twice.
  const tableNamesLower = new Set(tableFields.map(f => f.field_name.toLowerCase()));
  const dedupedLegacy = legacyFields.filter(
    f => !tableNamesLower.has(f.field_name.toLowerCase()),
  );
  const displayCustomFields = [...dedupedLegacy, ...tableFields];

  return (
    <Modal open={true} onClose={onClose} width={750}>
      {isLoading ? (
        <div className="card-view__loading">Loading...</div>
      ) : card ? (
        <div className="card-view">
          <div className="card-view__image-panel">
            {card.image_path ? (
              <img
                className="card-view__image"
                src={cardPreviewUrl(card.id)}
                alt={card.name}
              />
            ) : (
              <div className="card-view__no-image">No Image</div>
            )}
          </div>

          <div className="card-view__info-panel">
            <h2 className="card-view__name">{card.name}</h2>
            <p className="card-view__deck">Deck: {card.deck_name}</p>

            <div className="card-view__section">
              <h3 className="card-view__section-title">Classification</h3>
              {card.archetype && (
                <InfoRow label="Archetype" value={card.archetype} />
              )}
              {card.rank && (
                <InfoRow
                  label={isIChing ? 'Hexagram Number' : 'Rank'}
                  value={card.rank}
                />
              )}
              {card.suit && (
                <InfoRow
                  label={isIChing ? 'Pinyin' : 'Suit'}
                  value={card.suit}
                />
              )}
              {isIChing && customFields.traditional_chinese && (
                <InfoRow label="Traditional Chinese" value={customFields.traditional_chinese} />
              )}
              {isIChing && customFields.simplified_chinese && (
                <InfoRow label="Simplified Chinese" value={customFields.simplified_chinese} />
              )}
              <InfoRow label="Sort Order" value={String(card.card_order)} />
            </div>

            {populatedCorrespondences.length > 0 && (
              <div className="card-view__section">
                <h3 className="card-view__section-title">Correspondences</h3>
                {populatedCorrespondences.map(c => (
                  <InfoRow
                    key={c.field_name}
                    label={CORRESPONDENCE_FIELD_LABELS[c.field_name] || c.field_name}
                    value={c.values.join(', ')}
                  />
                ))}
              </div>
            )}

            {card.notes && (
              <div className="card-view__section">
                <h3 className="card-view__section-title">Notes</h3>
                <p className="card-view__notes">{card.notes}</p>
              </div>
            )}

            {displayCustomFields.length > 0 && (
              <div className="card-view__section">
                <h3 className="card-view__section-title">Custom Fields</h3>
                {displayCustomFields.map((f, i) => (
                  <div key={i} className="card-view__custom-field">
                    <span className="card-view__cf-label">{f.field_name}</span>
                    <RichTextViewer
                      content={f.field_value || ''}
                      className="card-view__cf-content"
                    />
                  </div>
                ))}
              </div>
            )}

            {((card.inherited_tags && card.inherited_tags.length > 0) ||
              (card.own_tags && card.own_tags.length > 0)) && (
              <div className="card-view__section">
                <h3 className="card-view__section-title">Tags</h3>
                {card.inherited_tags && card.inherited_tags.length > 0 && (
                  <InfoRow
                    label="Deck Tags"
                    value={card.inherited_tags.map(t => t.name).join(', ')}
                  />
                )}
                {card.own_tags && card.own_tags.length > 0 && (
                  <InfoRow
                    label="Card Tags"
                    value={card.own_tags.map(t => t.name).join(', ')}
                  />
                )}
              </div>
            )}

            {card.groups && card.groups.length > 0 && (
              <div className="card-view__section">
                <h3 className="card-view__section-title">Groups</h3>
                <InfoRow
                  label="Member of"
                  value={card.groups.map(g => g.name).join(', ')}
                />
              </div>
            )}
          </div>
        </div>
      ) : null}

      <div className="card-view__footer">
        <div className="card-view__nav">
          <button
            disabled={!hasPrev}
            onClick={() => hasPrev && onNavigate(cardIds[currentIndex - 1])}
          >
            &lsaquo; Prev
          </button>
          <span className="card-view__position">
            {currentIndex + 1} / {cardIds.length}
          </span>
          <button
            disabled={!hasNext}
            onClick={() => hasNext && onNavigate(cardIds[currentIndex + 1])}
          >
            Next &rsaquo;
          </button>
        </div>
        <div className="card-view__actions">
          {onEdit && (
            <button onClick={() => onEdit(cardId)}>Edit</button>
          )}
          <button
            className="danger"
            onClick={async () => {
              if (!window.confirm(`Delete "${card?.name}"? This cannot be undone.`)) return;
              try {
                await deleteCard(cardId);
                queryClient.invalidateQueries({ queryKey: ['cards'] });
                queryClient.invalidateQueries({ queryKey: ['card-search'] });
                queryClient.invalidateQueries({ queryKey: ['decks'] });
                onDeleted?.();
                onClose();
              } catch (err) {
                console.error('Failed to delete card:', err);
                showToast('Failed to delete card.');
              }
            }}
          >
            Delete
          </button>
          <button onClick={onClose}>Close</button>
        </div>
      </div>
    </Modal>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="card-view__row">
      <span className="card-view__label">{label}:</span>
      <span className="card-view__value">{value}</span>
    </div>
  );
}
