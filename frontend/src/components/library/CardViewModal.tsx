import { useEffect, useMemo, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { getCard, deleteCard } from '../../api/cards';
import { getCardCorrespondences } from '../../api/correspondences';
import { getArchetypeSourceEntries } from '../../api/referenceSources';
import { getArchetypes, type Archetype } from '../../api/correspondences';
import { cardPreviewUrl } from '../../api/images';
import { useToast } from '../../context/ToastContext';
import type { Card, Tag, CardGroup, ResolvedCorrespondence, ArchetypeSourceEntry } from '../../types';
import { CORRESPONDENCE_FIELDS, CORRESPONDENCE_FIELD_LABELS } from '../../types';
import Modal from '../common/Modal';
import RichTextViewer from '../common/RichTextViewer';
import './CardViewModal.css';
import { confirmDialog } from '../common/ConfirmDialog';

interface CardViewModalProps {
  cardId: number | null;
  cardIds: number[];
  onClose: () => void;
  onNavigate: (cardId: number) => void;
  onEdit?: (cardId: number) => void;
  onDeleted?: () => void;
  /** Jump to the Journal tab filtered to entries containing this card */
  onFindInJournal?: (cardName: string) => void;
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

export default function CardViewModal({ cardId, cardIds, onClose, onNavigate, onEdit, onDeleted, onFindInJournal }: CardViewModalProps) {
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

  // Details / Archetype Notes tabs. Back to Details when the card
  // changes via Prev/Next — the notes tab choice shouldn't stick to a
  // different card... actually it SHOULD stick: browsing notes across
  // cards is the whole point of arrow navigation. It resets only when
  // the modal closes (cardId null unmounts us).
  const [tab, setTab] = useState<'details' | 'archetype'>('details');

  // Cards store their archetype by NAME; the notes live under the
  // archetype's id — resolve through the type's archetype list.
  const { data: archetypes = [] } = useQuery<Archetype[]>({
    queryKey: ['archetypes', card?.cartomancy_type_name],
    queryFn: () => getArchetypes(card!.cartomancy_type_name!),
    enabled: cardId !== null && !!card?.cartomancy_type_name && !!card?.archetype,
  });
  const archetypeId = useMemo(() => {
    const name = card?.archetype?.trim().toLowerCase();
    if (!name) return null;
    return archetypes.find(a => a.name.trim().toLowerCase() === name)?.id ?? null;
  }, [archetypes, card?.archetype]);

  const { data: archetypeEntries = [] } = useQuery<ArchetypeSourceEntry[]>({
    queryKey: ['archetype-source-entries', archetypeId, card?.cartomancy_type_name],
    queryFn: () => getArchetypeSourceEntries(archetypeId!, card!.cartomancy_type_name),
    enabled: cardId !== null && archetypeId != null,
  });

  // Group notes by source (server order: source name, field order).
  const noteGroups = useMemo(() => {
    const bySource = new Map<number, { sourceName: string; fields: ArchetypeSourceEntry[] }>();
    for (const e of archetypeEntries) {
      if (!e.content || !e.content.replace(/<[^>]*>/g, '').trim()) continue;
      let bucket = bySource.get(e.source_id);
      if (!bucket) {
        bucket = { sourceName: e.source_name, fields: [] };
        bySource.set(e.source_id, bucket);
      }
      bucket.fields.push(e);
    }
    return [...bySource.values()];
  }, [archetypeEntries]);

  // Only show correspondence fields that resolved to a value
  const populatedCorrespondences = CORRESPONDENCE_FIELDS
    .map(f => correspondences.find(c => c.field_name === f))
    .filter((c): c is ResolvedCorrespondence => !!c && c.values.length > 0);

  // Arrow keys flip between cards — the natural way to browse a deck.
  // Ignored while the user is typing in a field.
  useEffect(() => {
    if (cardId === null) return;
    const onKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      if (target && (
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.tagName === 'SELECT' ||
        target.isContentEditable
      )) return;
      const idx = cardIds.indexOf(cardId);
      if (e.key === 'ArrowLeft' && idx > 0) {
        e.preventDefault();
        onNavigate(cardIds[idx - 1]);
      } else if (e.key === 'ArrowRight' && idx >= 0 && idx < cardIds.length - 1) {
        e.preventDefault();
        onNavigate(cardIds[idx + 1]);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [cardId, cardIds, onNavigate]);

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

            {archetypeId != null && (
              <div className="card-view__tabs" role="tablist">
                <button
                  role="tab"
                  aria-selected={tab === 'details'}
                  className={`card-view__tab ${tab === 'details' ? 'card-view__tab--active' : ''}`}
                  onClick={() => setTab('details')}
                >
                  Details
                </button>
                <button
                  role="tab"
                  aria-selected={tab === 'archetype'}
                  className={`card-view__tab ${tab === 'archetype' ? 'card-view__tab--active' : ''}`}
                  onClick={() => setTab('archetype')}
                >
                  Archetype Notes
                  {noteGroups.length > 0 && (
                    <span className="card-view__tab-count">{noteGroups.length}</span>
                  )}
                </button>
              </div>
            )}

            {tab === 'archetype' && archetypeId != null ? (
              <ArchetypeNotesPane groups={noteGroups} archetypeName={card.archetype || card.name} />
            ) : (
            <>
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
            </>
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
          {onFindInJournal && card && (
            <button
              onClick={() => {
                onFindInJournal(card.name);
                onClose();
              }}
              title="Show journal entries containing this card"
            >
              Find in Journal
            </button>
          )}
          <button
            className="danger"
            onClick={async () => {
              if (!(await confirmDialog({ message: `Delete "${card?.name}"? This cannot be undone.`, title: 'Delete Card', confirmLabel: 'Delete' }))) return;
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

/** The card's authored reference notes, grouped by source. Sources
 *  collapse individually; a single source starts open, several start
 *  closed (long book imports would otherwise fill the modal). */
function ArchetypeNotesPane({
  groups,
  archetypeName,
}: {
  groups: { sourceName: string; fields: ArchetypeSourceEntry[] }[];
  archetypeName: string;
}) {
  const [openSources, setOpenSources] = useState<Set<string>>(
    () => new Set(groups.length === 1 ? [groups[0].sourceName] : []),
  );
  const toggle = (name: string) => {
    setOpenSources(prev => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  };

  if (groups.length === 0) {
    return (
      <p className="card-view__notes-empty">
        No archetype notes for {archetypeName} yet. Author them in
        Settings → Archetype Notes, or import a book with the Scribe.
      </p>
    );
  }
  return (
    <div className="card-view__archetype-notes">
      {groups.map(g => {
        const open = openSources.has(g.sourceName);
        return (
          <section key={g.sourceName} className="card-view__note-source">
            <button
              className="card-view__note-source-toggle"
              aria-expanded={open}
              onClick={() => toggle(g.sourceName)}
            >
              <span className={`card-view__note-chevron ${open ? 'card-view__note-chevron--open' : ''}`} aria-hidden="true">▸</span>
              {g.sourceName}
              <span className="card-view__note-count">{g.fields.length} field{g.fields.length === 1 ? '' : 's'}</span>
            </button>
            {open && g.fields.map(f => (
              <div key={f.field_id} className="card-view__note-field">
                <h4 className="card-view__note-field-name">{f.field_name}</h4>
                <RichTextViewer content={f.content} />
              </div>
            ))}
          </section>
        );
      })}
    </div>
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
