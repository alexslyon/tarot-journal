import { useMemo, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { getCartomancyTypes, getDecks } from '../../../api/decks';
import { getArchetypes, type Archetype } from '../../../api/correspondences';
import {
  addCartomancyType,
  renameCartomancyType,
  deleteCartomancyType,
  addArchetype,
  bulkAddArchetypes,
  seedArchetypesFromDeck,
  updateArchetype,
  deleteArchetype,
} from '../../../api/deckTypes';
import { useToast } from '../../../context/ToastContext';
import { confirmDialog } from '../../common/ConfirmDialog';
import QueryError from '../../common/QueryError';
import type { CartomancyType, Deck } from '../../../types';
import './DeckTypesSection.css';

/** Settings → Deck Types: add custom cartomancy types and author
 *  their archetypes (the per-type card identities that reference
 *  notes, combinations, languages, and correspondences hang off).
 *  Built-in types are re-seeded on startup, so they can gain
 *  archetypes here but never be renamed or deleted. */
export default function DeckTypesSection() {
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [newTypeName, setNewTypeName] = useState('');
  const [renameText, setRenameText] = useState('');
  const [newArch, setNewArch] = useState({ name: '', rank: '', suit: '' });
  const [bulkText, setBulkText] = useState('');
  const [bulkOpen, setBulkOpen] = useState(false);
  const [seedDeckId, setSeedDeckId] = useState<number | ''>('');
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editText, setEditText] = useState('');

  const { data: types = [], isError: typesError, refetch: refetchTypes } =
    useQuery<CartomancyType[]>({
      queryKey: ['cartomancy-types'],
      queryFn: getCartomancyTypes,
    });
  const { data: decks = [] } = useQuery<Deck[]>({
    queryKey: ['decks'],
    queryFn: () => getDecks(),
  });

  const selected = types.find(t => t.id === selectedId) ?? null;

  const { data: archetypes = [] } = useQuery<Archetype[]>({
    queryKey: ['archetypes', selected?.name],
    queryFn: () => getArchetypes(selected!.name),
    enabled: selected != null,
  });

  const deckCounts = useMemo(() => {
    const counts = new Map<string, number>();
    for (const d of decks) {
      for (const t of d.cartomancy_types ?? []) {
        counts.set(t.name, (counts.get(t.name) ?? 0) + 1);
      }
    }
    return counts;
  }, [decks]);

  const typeDecks = selected
    ? decks.filter(d => (d.cartomancy_types ?? []).some(t => t.name === selected.name))
    : [];

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['cartomancy-types'] });
    queryClient.invalidateQueries({ queryKey: ['archetypes'] });
  };

  const handleAddType = async () => {
    const name = newTypeName.trim();
    if (!name) return;
    try {
      const { id } = await addCartomancyType(name);
      setNewTypeName('');
      invalidate();
      setSelectedId(id);
      setRenameText(name);
    } catch (err) {
      showToast(apiError(err, 'Could not add the type.'));
    }
  };

  const handleRename = async () => {
    if (!selected || !renameText.trim() || renameText.trim() === selected.name) return;
    try {
      await renameCartomancyType(selected.id, renameText.trim());
      invalidate();
      // Nearly everything keys off the type name string — refresh broadly.
      queryClient.invalidateQueries();
      showToast('Type renamed everywhere.', 'success');
    } catch (err) {
      showToast(apiError(err, 'Rename failed.'));
    }
  };

  const handleDeleteType = async () => {
    if (!selected) return;
    const ok = await confirmDialog({
      title: 'Delete Deck Type',
      message: `Delete "${selected.name}"? Its ${archetypes.length} archetype${archetypes.length === 1 ? '' : 's'} — including any reference notes, combinations, languages, and correspondences attached to them — will be permanently removed.`,
      confirmLabel: 'Delete',
    });
    if (!ok) return;
    try {
      await deleteCartomancyType(selected.id);
      setSelectedId(null);
      invalidate();
      queryClient.invalidateQueries();
    } catch (err) {
      showToast(apiError(err, 'Delete failed.'));
    }
  };

  const handleAddArchetype = async () => {
    if (!selected || !newArch.name.trim()) return;
    try {
      await addArchetype({
        cartomancy_type: selected.name,
        name: newArch.name,
        rank: newArch.rank || undefined,
        suit: newArch.suit || undefined,
      });
      setNewArch({ name: '', rank: '', suit: '' });
      queryClient.invalidateQueries({ queryKey: ['archetypes'] });
    } catch (err) {
      showToast(apiError(err, 'Could not add the archetype.'));
    }
  };

  const handleBulkAdd = async () => {
    if (!selected) return;
    // One per line: "Name" or "Name | rank | suit"
    const rows = bulkText.split('\n')
      .map(line => {
        const [name, rank, suit] = line.split('|').map(s => s.trim());
        return { name: name || '', rank: rank || undefined, suit: suit || undefined };
      })
      .filter(r => r.name);
    if (!rows.length) return;
    try {
      const result = await bulkAddArchetypes(selected.name, rows);
      setBulkText('');
      setBulkOpen(false);
      queryClient.invalidateQueries({ queryKey: ['archetypes'] });
      showToast(
        `Added ${result.created} archetype${result.created === 1 ? '' : 's'}`
        + (result.skipped ? ` (${result.skipped} already existed)` : '') + '.',
        'success',
      );
    } catch (err) {
      showToast(apiError(err, 'Bulk add failed.'));
    }
  };

  const handleSeed = async () => {
    if (!selected || seedDeckId === '') return;
    try {
      const result = await seedArchetypesFromDeck(seedDeckId as number, selected.name);
      queryClient.invalidateQueries({ queryKey: ['archetypes'] });
      queryClient.invalidateQueries({ queryKey: ['cards'] });
      showToast(`Created ${result.created} archetype${result.created === 1 ? '' : 's'} from the deck's cards.`, 'success');
    } catch (err) {
      showToast(apiError(err, 'Seeding failed.'));
    }
  };

  const handleRenameArchetype = async (a: Archetype) => {
    const name = editText.trim();
    setEditingId(null);
    if (!name || name === a.name) return;
    try {
      await updateArchetype(a.id, { name });
      queryClient.invalidateQueries({ queryKey: ['archetypes'] });
      queryClient.invalidateQueries({ queryKey: ['cards'] });
    } catch (err) {
      showToast(apiError(err, 'Rename failed.'));
    }
  };

  const handleDeleteArchetype = async (a: Archetype) => {
    const ok = await confirmDialog({
      title: 'Delete Archetype',
      message: `Delete "${a.name}"? Reference notes, combinations, language names, and correspondences attached to it will be removed.`,
      confirmLabel: 'Delete',
    });
    if (!ok) return;
    try {
      await deleteArchetype(a.id);
      queryClient.invalidateQueries({ queryKey: ['archetypes'] });
    } catch (err) {
      showToast(apiError(err, 'Delete failed.'));
    }
  };

  if (typesError) return <QueryError what="deck types" onRetry={() => refetchTypes()} />;

  return (
    <div className="deck-types">
      <div className="deck-types__list">
        <h3 className="deck-types__heading">Deck Types</h3>
        {types.map(t => (
          <button
            key={t.id}
            className={`deck-types__row ${t.id === selectedId ? 'deck-types__row--active' : ''}`}
            onClick={() => { setSelectedId(t.id); setRenameText(t.name); setSeedDeckId(''); }}
          >
            <span className="deck-types__row-name">{t.name}</span>
            <span className="deck-types__row-meta">
              {t.builtin ? 'built-in' : `${deckCounts.get(t.name) ?? 0} deck${(deckCounts.get(t.name) ?? 0) === 1 ? '' : 's'}`}
            </span>
          </button>
        ))}
        <div className="deck-types__add">
          <input
            type="text"
            value={newTypeName}
            placeholder="New type name"
            onChange={e => setNewTypeName(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') handleAddType(); }}
          />
          <button onClick={handleAddType} disabled={!newTypeName.trim()}>Add</button>
        </div>
      </div>

      <div className="deck-types__detail">
        {!selected ? (
          <p className="deck-types__hint">
            Select a type, or add a new one. Custom types need archetypes —
            the per-type card identities that reference notes, combinations,
            and correspondences attach to. The quickest start: create the
            type, import a deck of it, then use “Create archetypes from a
            deck” below.
          </p>
        ) : (
          <>
            <div className="deck-types__detail-head">
              {selected.builtin ? (
                <>
                  <h3 className="deck-types__heading">{selected.name}</h3>
                  <span className="deck-types__badge">
                    built-in — can’t be renamed or deleted; adding archetypes is fine
                  </span>
                </>
              ) : (
                <>
                  <input
                    type="text"
                    className="deck-types__rename"
                    value={renameText}
                    onChange={e => setRenameText(e.target.value)}
                    onKeyDown={e => { if (e.key === 'Enter') handleRename(); }}
                  />
                  <button onClick={handleRename}
                          disabled={!renameText.trim() || renameText.trim() === selected.name}>
                    Rename
                  </button>
                  <button className="danger" onClick={handleDeleteType}>Delete type</button>
                </>
              )}
            </div>

            <h4 className="deck-types__subheading">
              Archetypes ({archetypes.length})
            </h4>
            <div className="deck-types__archetypes">
              {archetypes.map(a => (
                <div key={a.id} className="deck-types__arch-row">
                  {editingId === a.id ? (
                    <input
                      autoFocus
                      type="text"
                      value={editText}
                      onChange={e => setEditText(e.target.value)}
                      onBlur={() => handleRenameArchetype(a)}
                      onKeyDown={e => {
                        if (e.key === 'Enter') handleRenameArchetype(a);
                        if (e.key === 'Escape') setEditingId(null);
                      }}
                    />
                  ) : (
                    <span className="deck-types__arch-name">{a.name}</span>
                  )}
                  <span className="deck-types__arch-meta">
                    {[a.rank, a.suit].filter(Boolean).join(' · ')}
                  </span>
                  {!selected.builtin && editingId !== a.id && (
                    <span className="deck-types__arch-actions">
                      <button onClick={() => { setEditingId(a.id); setEditText(a.name); }}>
                        Rename
                      </button>
                      <button onClick={() => handleDeleteArchetype(a)}>×</button>
                    </span>
                  )}
                </div>
              ))}
              {archetypes.length === 0 && (
                <p className="deck-types__hint">
                  No archetypes yet — add them below, paste a list, or create
                  them from a deck’s cards.
                </p>
              )}
            </div>

            <div className="deck-types__tools">
              <div className="deck-types__tool-row">
                <input
                  type="text"
                  placeholder="Archetype name"
                  value={newArch.name}
                  onChange={e => setNewArch({ ...newArch, name: e.target.value })}
                  onKeyDown={e => { if (e.key === 'Enter') handleAddArchetype(); }}
                />
                <input
                  type="text"
                  className="deck-types__narrow"
                  placeholder="Rank"
                  value={newArch.rank}
                  onChange={e => setNewArch({ ...newArch, rank: e.target.value })}
                />
                <input
                  type="text"
                  className="deck-types__narrow"
                  placeholder="Suit"
                  value={newArch.suit}
                  onChange={e => setNewArch({ ...newArch, suit: e.target.value })}
                />
                <button onClick={handleAddArchetype} disabled={!newArch.name.trim()}>
                  Add archetype
                </button>
              </div>

              {!bulkOpen ? (
                <button className="deck-types__link-btn" onClick={() => setBulkOpen(true)}>
                  + Paste a list…
                </button>
              ) : (
                <div className="deck-types__bulk">
                  <textarea
                    rows={6}
                    value={bulkText}
                    onChange={e => setBulkText(e.target.value)}
                    placeholder={'One archetype per line — optionally with rank and suit:\nFehu | 1 | Freyr’s Aett\nUruz | 2 | Freyr’s Aett'}
                  />
                  <div className="deck-types__tool-row">
                    <button onClick={handleBulkAdd} disabled={!bulkText.trim()}>Add all</button>
                    <button onClick={() => setBulkOpen(false)}>Cancel</button>
                  </div>
                </div>
              )}

              <div className="deck-types__tool-row">
                <select
                  value={seedDeckId}
                  onChange={e => setSeedDeckId(e.target.value ? Number(e.target.value) : '')}
                >
                  <option value="">Create archetypes from a deck…</option>
                  {typeDecks.map(d => (
                    <option key={d.id} value={d.id}>{d.name}</option>
                  ))}
                </select>
                <button onClick={handleSeed} disabled={seedDeckId === ''}>
                  Create from cards
                </button>
              </div>
              {typeDecks.length === 0 && (
                <p className="deck-types__hint">
                  No decks of this type yet — once one is imported, its card
                  names can seed the archetype list in one click.
                </p>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function apiError(err: unknown, fallback: string): string {
  return (err as { response?: { data?: { error?: string } } })
    ?.response?.data?.error ?? fallback;
}
