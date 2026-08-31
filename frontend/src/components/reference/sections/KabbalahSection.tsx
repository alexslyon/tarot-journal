/**
 * Kabbalah reference: user-configured Tree of Life tabs. Each tab
 * pairs a correspondence system (whose hebrew_letter assignments put
 * the cards on the paths — so a Thoth-style tree shows its own
 * letter–trump swaps) with a deck for the card images. With no trees
 * configured yet, the canonical Golden Dawn tree shows with images
 * from the default Tarot deck.
 */
import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import Modal, { ModalCancelButton } from '../../common/Modal';
import QueryError from '../../common/QueryError';
import { confirmDialog } from '../../common/ConfirmDialog';
import {
  getKabbalahReference,
  getKabbalahTrees,
  setKabbalahTrees,
  type KabbalahTreeConfig,
} from '../../../api/reference';
import { getCorrespondenceSystems } from '../../../api/correspondences';
import { getDecks } from '../../../api/decks';
import type { CorrespondenceSystem, Deck } from '../../../types';
import { useCardPeek } from './referenceShared';
import TreeOfLife from './TreeOfLife';
import ScribeLauncher from '../../scribe/ScribeLauncher';
import '../ReferenceTab.css';
import './KabbalahSection.css';

interface TreeModalState {
  index: number | 'new';
  label: string;
  systemId: number | '';
  deckId: number | '';
}

export default function KabbalahSection() {
  const queryClient = useQueryClient();
  const { openCard, cardModal } = useCardPeek();
  const [scribeOpen, setScribeOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const [modal, setModal] = useState<TreeModalState | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);

  const { data: treesData } = useQuery({
    queryKey: ['kabbalah-trees'],
    queryFn: getKabbalahTrees,
  });
  const trees = treesData?.trees ?? [];
  const current: KabbalahTreeConfig | null =
    trees.length > 0 ? trees[Math.min(activeIndex, trees.length - 1)] : null;

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['reference-kabbalah', current?.system_id ?? null, current?.deck_id ?? null],
    queryFn: () => getKabbalahReference(current?.system_id, current?.deck_id),
    enabled: treesData !== undefined,
  });

  // Pickers for the config modal (fetched only while it's open)
  const { data: systems = [] } = useQuery<CorrespondenceSystem[]>({
    queryKey: ['correspondence-systems'],
    queryFn: getCorrespondenceSystems,
    enabled: modal !== null,
  });
  const { data: decks = [] } = useQuery<Deck[]>({
    queryKey: ['decks'],
    queryFn: () => getDecks(),
    enabled: modal !== null,
  });

  const saveTrees = async (next: KabbalahTreeConfig[]) => {
    await setKabbalahTrees(next);
    queryClient.invalidateQueries({ queryKey: ['kabbalah-trees'] });
  };

  const submitModal = async () => {
    if (!modal || !modal.label.trim() || modal.systemId === '' || modal.deckId === '') {
      setSaveError('A name, correspondence system, and deck are all needed.');
      return;
    }
    const entry: KabbalahTreeConfig = {
      label: modal.label.trim(),
      system_id: modal.systemId,
      deck_id: modal.deckId,
    };
    const next = modal.index === 'new'
      ? [...trees, entry]
      : trees.map((t, i) => (i === modal.index ? entry : t));
    try {
      await saveTrees(next);
      setActiveIndex(modal.index === 'new' ? next.length - 1 : modal.index);
      setModal(null);
      setSaveError(null);
    } catch {
      setSaveError('Saving failed — is the app online?');
    }
  };

  const removeCurrent = async () => {
    if (current === null) return;
    const ok = await confirmDialog({
      title: 'Remove Tree',
      message: `Remove the "${current.label}" tree tab? The correspondence system and deck themselves are untouched.`,
      confirmLabel: 'Remove',
    });
    if (!ok) return;
    const idx = trees.indexOf(current);
    await saveTrees(trees.filter((_, i) => i !== idx));
    setActiveIndex(0);
  };

  const openEdit = () => {
    if (current === null) return;
    setSaveError(null);
    setModal({
      index: trees.indexOf(current),
      label: current.label,
      systemId: current.system_id,
      deckId: current.deck_id,
    });
  };

  return (
    <div className="reference-section">
      <div className="ref-section-head">
        <h2 className="reference-section__title">Kabbalah</h2>
        <button type="button" className="ref-scribe-btn" onClick={() => setScribeOpen(true)}>
          Import from source (Scribe)
        </button>
      </div>
      <p className="reference-section__hint">
        The Tree of Life: ten sephiroth joined by twenty-two paths, one
        Hebrew letter per path. Each tab builds the tree from one of
        your correspondence systems, with images from its deck.
      </p>

      <div className="ref-subtabs kabbalah__tabs">
        {trees.map((tree, i) => (
          <button
            key={`${tree.label}-${i}`}
            type="button"
            className={`ref-subtabs__tab ${current === tree ? 'ref-subtabs__tab--active' : ''}`}
            onClick={() => setActiveIndex(i)}
          >
            {tree.label}
          </button>
        ))}
        <button
          type="button"
          className="ref-subtabs__tab kabbalah__tab-action"
          onClick={() => {
            setSaveError(null);
            setModal({ index: 'new', label: '', systemId: '', deckId: '' });
          }}
        >
          + Add tree
        </button>
        {current !== null && (
          <>
            <button
              type="button"
              className="ref-subtabs__tab kabbalah__tab-action"
              onClick={openEdit}
            >
              Edit
            </button>
            <button
              type="button"
              className="ref-subtabs__tab kabbalah__tab-action"
              onClick={removeCurrent}
            >
              Remove
            </button>
          </>
        )}
      </div>
      {trees.length === 0 && treesData !== undefined && (
        <p className="reference-section__hint">
          Showing the canonical Golden Dawn tree. Add a tree to build a
          version from one of your correspondence systems — its
          Hebrew-letter assignments place the cards on the paths.
        </p>
      )}

      {isLoading && <p className="reference-section__hint">Loading…</p>}
      {isError && <QueryError what="Kabbalah reference" onRetry={() => refetch()} />}

      {data && <TreeOfLife data={data} openCard={openCard} />}

      {cardModal}
      {scribeOpen && (
        <ScribeLauncher open onClose={() => setScribeOpen(false)} context={{ mode: 'entities', kind: 'sephira' }} />
      )}

      {modal && (
        <Modal
          open
          onClose={() => setModal(null)}
          title={modal.index === 'new' ? 'Add Tree' : 'Edit Tree'}
          width={440}
        >
          <div className="kabbalah__form">
            <label className="kabbalah__form-field">
              <span>Name</span>
              <input
                type="text"
                value={modal.label}
                placeholder="e.g. Golden Dawn, Thoth, Continental"
                onChange={(e) => setModal({ ...modal, label: e.target.value })}
              />
            </label>
            <label className="kabbalah__form-field">
              <span>Correspondence system</span>
              <select
                value={modal.systemId === '' ? '' : String(modal.systemId)}
                onChange={(e) => setModal({
                  ...modal,
                  systemId: e.target.value === '' ? '' : Number(e.target.value),
                })}
              >
                <option value="">Choose a system…</option>
                {systems.map(s => (
                  <option key={s.id} value={s.id}>
                    {s.name} ({s.cartomancy_type})
                  </option>
                ))}
              </select>
            </label>
            <label className="kabbalah__form-field">
              <span>Deck for card images</span>
              <select
                value={modal.deckId === '' ? '' : String(modal.deckId)}
                onChange={(e) => setModal({
                  ...modal,
                  deckId: e.target.value === '' ? '' : Number(e.target.value),
                })}
              >
                <option value="">Choose a deck…</option>
                {decks.map(d => (
                  <option key={d.id} value={d.id}>{d.name}</option>
                ))}
              </select>
            </label>
            {saveError && <p className="kabbalah__form-error">{saveError}</p>}
            <div className="kabbalah__form-actions">
              <ModalCancelButton>Cancel</ModalCancelButton>
              <button type="button" className="primary" onClick={submitModal}>
                {modal.index === 'new' ? 'Add' : 'Save'}
              </button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}
