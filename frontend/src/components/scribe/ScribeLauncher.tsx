/**
 * The Scribe's single front door. Every Scribe entry point renders
 * this; the launch context decides what shows:
 *
 *  - {mode:'cards', source|deck}  → the card Scribe directly
 *  - {mode:'entities', kind?...}  → the entity Scribe directly
 *  - {} (no context, e.g. ⌘K)     → a chooser step: pick what to
 *    import (card meanings, or reference entries) and, for cards,
 *    which reference source or deck to import into — then the
 *    matching Scribe opens.
 *
 * Option-2 door: the modes are a registry, and the two pipelines'
 * reply protocols use disjoint JSON keys ("proposals"/"combinations"
 * vs "entries"). A future merged mode — one extraction run emitting
 * all three — would join the chooser as a third card and combine the
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
  | { mode: 'cards'; source?: ReferenceSource; deck?: Deck }
  | { mode: 'entities'; kind?: EntityKind; deckType?: string | null }
  | Record<string, never>;

interface ScribeLauncherProps {
  open: boolean;
  onClose: () => void;
  context?: ScribeContext;
}

type Chosen =
  | { mode: 'cards'; source?: ReferenceSource; deck?: Deck }
  | { mode: 'entities'; kind?: EntityKind; deckType?: string | null }
  | null;

export default function ScribeLauncher({ open, onClose, context }: ScribeLauncherProps) {
  const ctx = context ?? {};
  const [chosen, setChosen] = useState<Chosen>(null);
  // The chooser's second step for card mode: pick the import target.
  const [pickingCardTarget, setPickingCardTarget] = useState(false);

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

  // Chooser: no (complete) context supplied.
  return (
    <Modal open onClose={onClose} title="Scribe" width={520}>
      {!pickingCardTarget ? (
        <div className="scribe-launcher">
          <p className="scribe-launcher__hint">
            What are you importing from this source?
          </p>
          <button
            type="button"
            className="scribe-launcher__choice"
            onClick={() => setPickingCardTarget(true)}
          >
            <strong>Card meanings</strong>
            <span>
              Per-card texts into archetype notes or deck card fields,
              with combinations riding along.
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
          <p className="scribe-launcher__hint">
            Import card meanings into which source or deck?
          </p>
          <div className="scribe-launcher__list">
            {sources.map(s => (
              <button
                key={`s-${s.id}`}
                type="button"
                className="scribe-launcher__row"
                onClick={() => setChosen({ mode: 'cards', source: s })}
              >
                📖 {s.name}
                <span>{(s.cartomancy_types || []).join(', ')}</span>
              </button>
            ))}
            {decks.map(d => (
              <button
                key={`d-${d.id}`}
                type="button"
                className="scribe-launcher__row"
                onClick={() => setChosen({ mode: 'cards', deck: d })}
              >
                🃏 {d.name}
                <span>{(d.cartomancy_types || []).map(t => t.name).join(', ')}</span>
              </button>
            ))}
          </div>
          <div className="scribe-launcher__actions">
            <button type="button" onClick={() => setPickingCardTarget(false)}>
              Back
            </button>
            <ModalCancelButton>Cancel</ModalCancelButton>
          </div>
        </div>
      )}
    </Modal>
  );
}
