/**
 * The Scribe's single front door. Every Scribe entry point renders
 * this; the launch context decides what shows:
 *
 *  - {mode:'cards', source|deck}  → the card Scribe directly
 *  - {mode:'entities', kind?...}  → the entity Scribe directly
 *  - {} (no context, e.g. ⌘K)     → a chooser: what are you importing
 *    — deck information (pick a deck), card archetype information
 *    (pick a reference source), combinations (pick the source they're
 *    attributed to), or reference entries. Target lists are filtered
 *    per destination and searchable.
 *
 * Option-2 door: the destinations are a registry, and the pipelines'
 * reply protocols use disjoint JSON keys ("proposals"/"combinations"
 * vs "entries"). A future merged mode — one extraction run emitting
 * all three — would join the chooser as another card and combine the
 * prompts, without reshaping this component.
 */
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import Modal, { ModalCancelButton } from '../common/Modal';
import ScribeModal from './ScribeModal';
import EntityScribeModal from './EntityScribeModal';
import { getReferenceSources } from '../../api/referenceSources';
import { getDecks } from '../../api/decks';
import type { Deck, ReferenceSource } from '../../types';
import type { EntityKind } from '../../api/reference';
import './ScribeLauncher.css';

export type ScribeContext =
  | { mode: 'cards'; source?: ReferenceSource; deck?: Deck; combinationsOnly?: boolean }
  | { mode: 'entities'; kind?: EntityKind; deckType?: string | null }
  | Record<string, never>;

interface ScribeLauncherProps {
  open: boolean;
  onClose: () => void;
  context?: ScribeContext;
}

type Chosen =
  | { mode: 'cards'; source?: ReferenceSource; deck?: Deck; combinationsOnly?: boolean }
  | { mode: 'entities'; kind?: EntityKind; deckType?: string | null }
  | null;

/** Which second-step target list is open. */
type Picking = 'deck' | 'source' | 'combo-source' | null;

export default function ScribeLauncher({ open, onClose, context }: ScribeLauncherProps) {
  const ctx = context ?? {};
  const [chosen, setChosen] = useState<Chosen>(null);
  const [picking, setPicking] = useState<Picking>(null);
  const [filter, setFilter] = useState('');

  const active: Chosen =
    'mode' in ctx && ctx.mode ? (ctx as Chosen) : chosen;

  const { data: sources = [] } = useQuery<ReferenceSource[]>({
    queryKey: ['reference-sources'],
    queryFn: () => getReferenceSources(),
    enabled: open && !active,
  });
  const { data: decks = [] } = useQuery<Deck[]>({
    queryKey: ['decks'],
    queryFn: () => getDecks(),
    enabled: open && !active,
  });

  if (!open) return null;

  if (active?.mode === 'cards' && (active.source || active.deck)) {
    return (
      <ScribeModal
        source={active.source}
        deck={active.deck}
        combinationsOnly={active.combinationsOnly}
        open
        onClose={onClose}
      />
    );
  }
  if (active?.mode === 'entities') {
    return (
      <EntityScribeModal
        open
        onClose={onClose}
        initialKind={active.kind}
        initialType={active.deckType ?? null}
      />
    );
  }

  const q = filter.trim().toLowerCase();
  const matches = (name: string) => !q || name.toLowerCase().includes(q);
  const openPicker = (p: Picking) => { setPicking(p); setFilter(''); };

  const pickerTitle = picking === 'deck'
    ? 'Import deck information into which deck?'
    : picking === 'source'
      ? 'Import card archetype information into which reference source?'
      : 'Attribute the combinations to which reference source?';

  return (
    <Modal open onClose={onClose} title="Scribe" width={520}>
      {picking === null ? (
        <div className="scribe-launcher">
          <p className="scribe-launcher__hint">
            What are you importing from this source?
          </p>
          <button
            type="button"
            className="scribe-launcher__choice"
            onClick={() => openPicker('deck')}
          >
            <strong>Deck information</strong>
            <span>Per-card texts into one deck's card fields.</span>
          </button>
          <button
            type="button"
            className="scribe-launcher__choice"
            onClick={() => openPicker('source')}
          >
            <strong>Card archetype information</strong>
            <span>
              Card meanings into a reference source's archetype note
              fields (shared across decks).
            </span>
          </button>
          <button
            type="button"
            className="scribe-launcher__choice"
            onClick={() => openPicker('combo-source')}
          >
            <strong>Combinations</strong>
            <span>
              Pair and triad meanings ("Rider + Clover: …") into the
              Combinations reference.
            </span>
          </button>
          <button
            type="button"
            className="scribe-launcher__choice"
            onClick={() => setChosen({ mode: 'entities' })}
          >
            <strong>Reference entries</strong>
            <span>
              Texts about signs, planets, sephiroth, paths, chakras,
              numbers, suits, or ranks — into the Reference sections.
            </span>
          </button>
          <div className="scribe-launcher__actions">
            <ModalCancelButton>Cancel</ModalCancelButton>
          </div>
        </div>
      ) : (
        <div className="scribe-launcher">
          <p className="scribe-launcher__hint">{pickerTitle}</p>
          <input
            autoFocus
            type="text"
            className="scribe-launcher__filter"
            placeholder="Type to filter…"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          />
          <div className="scribe-launcher__list">
            {picking === 'deck'
              ? decks.filter(d => matches(d.name)).map(d => (
                <button
                  key={d.id}
                  type="button"
                  className="scribe-launcher__row"
                  onClick={() => setChosen({ mode: 'cards', deck: d })}
                >
                  🃏 {d.name}
                  <span>{(d.cartomancy_types || []).map(t => t.name).join(', ')}</span>
                </button>
              ))
              : sources.filter(s => matches(s.name)).map(s => (
                <button
                  key={s.id}
                  type="button"
                  className="scribe-launcher__row"
                  onClick={() => setChosen({
                    mode: 'cards',
                    source: s,
                    combinationsOnly: picking === 'combo-source',
                  })}
                >
                  📖 {s.name}
                  <span>{(s.cartomancy_types || []).join(', ')}</span>
                </button>
              ))}
            {((picking === 'deck' && decks.every(d => !matches(d.name)))
              || (picking !== 'deck' && sources.every(s => !matches(s.name)))) && (
              <p className="scribe-launcher__hint">Nothing matches.</p>
            )}
          </div>
          <div className="scribe-launcher__actions">
            <button type="button" onClick={() => setPicking(null)}>
              Back
            </button>
            <ModalCancelButton>Cancel</ModalCancelButton>
          </div>
        </div>
      )}
    </Modal>
  );
}
