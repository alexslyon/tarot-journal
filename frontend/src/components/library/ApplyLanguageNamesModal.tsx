/**
 * Card Names from Language — rename a whole deck's cards using the
 * localized names stored in Archetype Languages.
 *
 * Pick a language and every card whose archetype has a name in it gets
 * that name proposed; a preview table shows current → proposed with a
 * dropdown wherever a card has several options (Le Mat / Le Fou) or
 * the user wants to keep the current name. "Canonical" renames back to
 * the archetype names, making the whole operation reversible. Nothing
 * is written until Apply.
 *
 * Card names change; archetype links don't — so search-by-archetype,
 * journal matching, and Anki export keep working exactly as before.
 */
import { useMemo, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import Modal, { ModalCancelButton } from '../common/Modal';
import { useToast } from '../../context/ToastContext';
import { getCards } from '../../api/cards';
import { renameDeckCards } from '../../api/decks';
import {
  getArchetypeLanguages,
  getArchetypeNamesForType,
} from '../../api/archetypeLanguages';
import type { Deck, ArchetypeLanguage, ArchetypeLanguageName, Card } from '../../types';
import './ApplyLanguageNamesModal.css';

interface ApplyLanguageNamesModalProps {
  deck: Deck;
  open: boolean;
  onClose: () => void;
}

const CANONICAL = 'canonical' as const;
/** Sentinel for "keep this card's current name". */
const KEEP = '';

export default function ApplyLanguageNamesModal({ deck, open, onClose }: ApplyLanguageNamesModalProps) {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const [languageId, setLanguageId] = useState<number | typeof CANONICAL | ''>('');
  const [overrides, setOverrides] = useState<Record<number, string>>({});
  const [applying, setApplying] = useState(false);

  const typeNames = useMemo(
    () => (deck.cartomancy_types || []).map(t => t.name),
    [deck.cartomancy_types],
  );

  const { data: languages = [] } = useQuery<ArchetypeLanguage[]>({
    queryKey: ['archetype-languages'],
    queryFn: getArchetypeLanguages,
    enabled: open,
  });
  const { data: cards = [] } = useQuery<Card[]>({
    queryKey: ['cards', deck.id],
    queryFn: () => getCards(deck.id),
    enabled: open,
  });
  const { data: allNames = [] } = useQuery<ArchetypeLanguageName[]>({
    queryKey: ['archetype-names-for-types', typeNames],
    queryFn: async () => {
      const perType = await Promise.all(typeNames.map(getArchetypeNamesForType));
      return perType.flat();
    },
    enabled: open && typeNames.length > 0,
  });

  // Only offer languages that actually have names for this deck's types
  const usableLanguages = useMemo(() => {
    const withNames = new Set(allNames.map(n => n.language_id));
    return languages.filter(l => withNames.has(l.id));
  }, [languages, allNames]);

  // archetype name (lowercased) → candidate names in the chosen language
  const candidatesByArchetype = useMemo(() => {
    const map = new Map<string, string[]>();
    if (languageId === '' || languageId === CANONICAL) return map;
    for (const n of allNames) {
      if (n.language_id !== languageId || !n.archetype_name) continue;
      const key = n.archetype_name.toLowerCase();
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(n.name);
    }
    return map;
  }, [allNames, languageId]);

  interface PreviewRow {
    card: Card;
    candidates: string[];
    chosen: string; // KEEP = keep current
    /** Why a row has nothing to rename (or 'renamable' when it does):
     *  'already' = the card ALREADY carries this language's name. */
    status: 'renamable' | 'already' | 'no-name' | 'no-archetype';
  }

  const rows: PreviewRow[] = useMemo(() => {
    if (languageId === '') return [];
    return cards.map(card => {
      let candidates: string[] = [];
      if (languageId === CANONICAL) {
        candidates = card.archetype ? [card.archetype] : [];
      } else if (card.archetype) {
        candidates = candidatesByArchetype.get(card.archetype.toLowerCase()) ?? [];
      }
      // Renaming to the name it already has is a no-op — treat as keep
      const meaningful = candidates.filter(c => c !== card.name);
      let status: PreviewRow['status'];
      if (!card.archetype) {
        status = 'no-archetype';
      } else if (candidates.length === 0) {
        status = 'no-name';
      } else if (meaningful.length === 0) {
        // Had candidates, but every one matches the current name.
        status = 'already';
      } else {
        status = 'renamable';
      }
      const fallback = meaningful.length ? meaningful[0] : KEEP;
      const chosen = overrides[card.id] !== undefined ? overrides[card.id] : fallback;
      return { card, candidates: meaningful, chosen, status };
    });
  }, [cards, languageId, candidatesByArchetype, overrides]);

  const renameCount = rows.filter(r => r.chosen !== KEEP).length;
  const alreadyCount = rows.filter(r => r.status === 'already').length;
  const unmappedCount = rows.filter(r => r.status === 'no-name' || r.status === 'no-archetype').length;

  const handleLanguageChange = (value: string) => {
    setOverrides({});
    setLanguageId(value === '' ? '' : value === CANONICAL ? CANONICAL : Number(value));
  };

  const handleApply = async () => {
    const renames = rows
      .filter(r => r.chosen !== KEEP)
      .map(r => ({ card_id: r.card.id, name: r.chosen }));
    if (!renames.length) return;
    setApplying(true);
    try {
      const result = await renameDeckCards(deck.id, renames);
      queryClient.invalidateQueries({ queryKey: ['cards'] });
      queryClient.invalidateQueries({ queryKey: ['card-search'] });
      if (result.errors.length) {
        showToast(`Renamed ${result.applied} of ${renames.length} cards — ${result.errors.length} failed.`);
      } else {
        showToast(`Renamed ${result.applied} cards.`, 'success');
        onClose();
      }
    } catch {
      showToast('Failed to rename the cards.');
    } finally {
      setApplying(false);
    }
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={`Card Names from Language — ${deck.name}`}
      width={640}
    >
      <div className="lang-names__body">
        <div className="lang-names__picker">
          <label>Rename this deck's cards to</label>
          <select value={String(languageId)} onChange={e => handleLanguageChange(e.target.value)}>
            <option value="">Choose a language…</option>
            {usableLanguages.map(l => (
              <option key={l.id} value={l.id}>{l.name}</option>
            ))}
            <option value={CANONICAL}>Canonical (archetype names)</option>
          </select>
        </div>

        {languageId !== '' && (
          <>
            <p className="lang-names__summary">
              {renameCount} of {cards.length} cards will be renamed.
              {alreadyCount > 0 && (languageId === CANONICAL
                ? ` ${alreadyCount} already carry their canonical name.`
                : ` ${alreadyCount} are already named in this language.`)}
              {unmappedCount > 0 && ` ${unmappedCount} have no name in this language (or no archetype) and keep their current name.`}
              {' '}Card archetypes aren't touched, so search and journal matching keep working.
            </p>
            <div className="lang-names__list">
              {rows.map(({ card, candidates, chosen, status }) => (
                <div key={card.id} className="lang-names__row">
                  <span className="lang-names__current" title={card.archetype || undefined}>
                    {card.name}
                  </span>
                  <span className="lang-names__arrow">→</span>
                  {candidates.length === 0 ? (
                    <span className={status === 'already' ? 'lang-names__already' : 'lang-names__keep'}>
                      {status === 'already'
                        ? (languageId === CANONICAL
                          ? 'already the canonical name ✓'
                          : 'already named in this language ✓')
                        : status === 'no-name'
                          ? 'no name in this language — keeps current'
                          : 'no archetype — keeps current'}
                    </span>
                  ) : (
                    <select
                      value={chosen}
                      onChange={e => setOverrides(prev => ({ ...prev, [card.id]: e.target.value }))}
                    >
                      {candidates.map(c => <option key={c} value={c}>{c}</option>)}
                      <option value={KEEP}>Keep current name</option>
                    </select>
                  )}
                </div>
              ))}
            </div>
          </>
        )}

        <div className="lang-names__actions">
          <button
            className="primary"
            onClick={handleApply}
            disabled={applying || renameCount === 0}
          >
            {applying ? 'Renaming…' : `Rename ${renameCount} card${renameCount === 1 ? '' : 's'}`}
          </button>
          <ModalCancelButton>Cancel</ModalCancelButton>
        </div>
      </div>
    </Modal>
  );
}
