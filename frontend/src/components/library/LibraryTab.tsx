import { useState, useCallback, useEffect } from 'react';
import { useQuery, keepPreviousData } from '@tanstack/react-query';
import { Panel, Group, Separator } from 'react-resizable-panels';
import DeckList from './DeckList';
import CardGrid from './CardGrid';
import CardViewModal from './CardViewModal';
import CardEditModal from './CardEditModal';
import CardSearchBar, { type SearchFilters } from './CardSearchBar';
import DeckEditModal from './DeckEditModal';
import BatchEditModal from './BatchEditModal';
import ImportDeckModal from './ImportDeckModal';
import AddCardsModal from './AddCardsModal';
import { getCards, searchCards } from '../../api/cards';
import { getDeck } from '../../api/decks';
import { synonymAlternatives } from '../../utils/cardSynonyms';
import type { Deck, Card } from '../../types';
import './LibraryTab.css';

interface LibraryTabProps {
  /** Jump to the Journal tab filtered to entries containing a card */
  onFindCardInJournal?: (cardName: string) => void;
  /** Deck to select on mount (set by the command palette) */
  pendingDeckId?: number | null;
  onPendingDeckHandled?: () => void;
}

export default function LibraryTab({
  onFindCardInJournal,
  pendingDeckId,
  onPendingDeckHandled,
}: LibraryTabProps) {
  const [selectedDeck, setSelectedDeck] = useState<Deck | null>(null);

  // Command-palette deep link: select the requested deck once loaded.
  useEffect(() => {
    if (pendingDeckId == null) return;
    let cancelled = false;
    getDeck(pendingDeckId)
      .then(deck => { if (!cancelled) setSelectedDeck(deck); })
      .catch(() => {})
      .finally(() => onPendingDeckHandled?.());
    return () => { cancelled = true; };
  }, [pendingDeckId, onPendingDeckHandled]);
  const [viewingCardId, setViewingCardId] = useState<number | null>(null);
  const [editingCardId, setEditingCardId] = useState<number | null>(null);
  const [editingDeckId, setEditingDeckId] = useState<number | null>(null);
  const [activeSearch, setActiveSearch] = useState<SearchFilters | null>(null);
  const [selectedCardIds, setSelectedCardIds] = useState<Set<number>>(new Set());
  const [showBatchEdit, setShowBatchEdit] = useState(false);
  const [showImport, setShowImport] = useState(false);
  const [showAddCards, setShowAddCards] = useState(false);

  const deckId = selectedDeck?.id ?? null;

  // Deck cards query (used when not searching)
  const { data: deckCards = [] } = useQuery({
    queryKey: ['cards', deckId],
    queryFn: () => getCards(deckId!),
    enabled: deckId !== null && activeSearch === null,
  });

  // Search query (used when search is active)
  const searchParams = activeSearch ? {
    ...activeSearch,
    ...(deckId ? { deck_id: deckId } : {}),
  } : null;

  const { data: searchResults, isLoading: searchLoading } = useQuery({
    queryKey: ['card-search', searchParams],
    queryFn: () => searchCards(searchParams as Record<string, string | number | boolean>),
    enabled: searchParams !== null,
    // Live search: keep showing the previous results while the next
    // keystroke's query runs so the grid doesn't flash empty.
    placeholderData: keepPreviousData,
  });

  // Synonym fallback: when the search finds nothing, retry with
  // card-world equivalents (Coins ↔ Pentacles, Papess ↔ High
  // Priestess, …) and say so, instead of a bare "no results".
  const primaryCameUpEmpty =
    searchParams !== null
    && searchResults !== undefined
    && searchResults.length === 0
    && !!activeSearch?.query?.trim();
  const { data: synonymHit } = useQuery({
    queryKey: ['card-search-synonyms', searchParams],
    queryFn: async () => {
      for (const alt of synonymAlternatives(activeSearch!.query)) {
        const cards = await searchCards({
          ...(searchParams as Record<string, string | number | boolean>),
          query: alt,
        });
        if (cards.length > 0) return { term: alt, cards };
      }
      return null;
    },
    enabled: primaryCameUpEmpty,
  });

  // Card IDs for modal navigation come from whichever list is active
  const synonymCards = primaryCameUpEmpty ? synonymHit?.cards : undefined;
  const displayedCards = activeSearch
    ? (synonymCards ?? searchResults ?? [])
    : deckCards;
  const cardIds = displayedCards.map((c: Card) => c.id);

  const handleSearch = useCallback((filters: SearchFilters | null) => {
    setActiveSearch(filters);
  }, []);

  return (
    <div className="library-tab">
      <Group orientation="horizontal" style={{ width: '100%', height: '100%' }}>
        <Panel defaultSize="30%" minSize="20%">
          <DeckList
            selectedDeckId={deckId}
            onSelectDeck={setSelectedDeck}
            onEditDeck={setEditingDeckId}
            onImport={() => setShowImport(true)}
          />
        </Panel>
        <Separator className="resize-handle" />
        <Panel minSize="20%">
          <div className="library-tab__right-panel">
            <CardSearchBar deckId={deckId} onSearch={handleSearch} />
            <CardGrid
              deckId={deckId}
              deckName={selectedDeck?.name ?? ''}
              onCardClick={(card) => setViewingCardId(card.id)}
              searchResults={activeSearch ? (synonymCards ?? searchResults ?? []) : undefined}
              searchLoading={searchLoading}
              searchNote={
                synonymCards && activeSearch
                  ? `No matches for “${activeSearch.query}” — showing “${synonymHit!.term}” instead.`
                  : undefined
              }
              selectedIds={selectedCardIds}
              onSelectionChange={setSelectedCardIds}
              onBatchEdit={() => setShowBatchEdit(true)}
              onAddCard={deckId ? () => setShowAddCards(true) : undefined}
            />
          </div>
        </Panel>
      </Group>

      <CardViewModal
        cardId={viewingCardId}
        cardIds={cardIds}
        onClose={() => setViewingCardId(null)}
        onNavigate={setViewingCardId}
        onEdit={(id) => {
          setViewingCardId(null);
          setEditingCardId(id);
        }}
        onFindInJournal={onFindCardInJournal}
        onDeleted={() => setSelectedCardIds(new Set())}
      />

      <CardEditModal
        cardId={editingCardId}
        deckId={deckId}
        cardIds={cardIds}
        onClose={() => {
          const id = editingCardId;
          setEditingCardId(null);
          if (id) setViewingCardId(id);
        }}
        onSaved={() => {}}
        onNavigate={setEditingCardId}
      />

      <DeckEditModal
        deckId={editingDeckId}
        onClose={() => setEditingDeckId(null)}
        onSaved={() => {}}
        onDeleted={() => setSelectedDeck(null)}
      />

      {showBatchEdit && (
        <BatchEditModal
          cardIds={Array.from(selectedCardIds)}
          deckId={deckId}
          onClose={() => setShowBatchEdit(false)}
          onSaved={() => setSelectedCardIds(new Set())}
        />
      )}

      {showImport && (
        <ImportDeckModal
          onClose={() => setShowImport(false)}
          onImported={async (deckId) => {
            const deck = await getDeck(deckId);
            setSelectedDeck(deck);
          }}
        />
      )}

      {showAddCards && deckId && (
        <AddCardsModal
          deckId={deckId}
          deckName={selectedDeck?.name ?? ''}
          onClose={() => setShowAddCards(false)}
          onImported={() => {}}
        />
      )}
    </div>
  );
}
