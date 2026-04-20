import { useState, useMemo } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  getCorrespondenceSystems,
  getCorrespondenceSystem,
  createCorrespondenceSystem,
  updateCorrespondenceSystem,
  deleteCorrespondenceSystem,
  cloneCorrespondenceSystem,
  deleteAssignment,
  getArchetypes,
  getFieldOptions,
  expandElementalZodiac,
  setAssignmentValues,
  type Archetype,
  type FieldOption,
} from '../../../api/correspondences';
import MultiValueSelect from '../../common/MultiValueSelect';
import type {
  CorrespondenceSystem,
  CorrespondenceAssignment,
} from '../../../types';
import {
  CORRESPONDENCE_FIELDS,
  CORRESPONDENCE_FIELD_LABELS,
} from '../../../types';
import { detectGroupPatterns, patternsByCategory, type PatternCategorySection } from '../../../utils/correspondencePatterns';
import { displayArchetypeName, archetypeSortKey, displayGroupLabel } from '../../../utils/tarotNaming';
import FieldOptionsEditor from './FieldOptionsEditor';
import '../SettingsTab.css';
import './CorrespondencesSection.css';

export default function CorrespondencesSection() {
  const queryClient = useQueryClient();
  const [selectedSystemId, setSelectedSystemId] = useState<number | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null);
  const [newName, setNewName] = useState('');
  const [newDesc, setNewDesc] = useState('');
  const [newCartomancyType, setNewCartomancyType] = useState('Tarot');
  const [newNamingStyle, setNewNamingStyle] = useState('RWS');
  const [newSourceId, setNewSourceId] = useState<number | ''>('');
  const [creating, setCreating] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [editingName, setEditingName] = useState<string | null>(null);
  const [editingDesc, setEditingDesc] = useState<string | null>(null);
  const [cloneName, setCloneName] = useState('');
  const [showClone, setShowClone] = useState(false);
  const [filterText, setFilterText] = useState('');
  const [bulkGroup, setBulkGroup] = useState('');
  const [bulkField, setBulkField] = useState(CORRESPONDENCE_FIELDS[0] as string);
  const [bulkValues, setBulkValues] = useState<string[]>([]);
  const [bulkApplying, setBulkApplying] = useState(false);
  const [showBulk, setShowBulk] = useState(false);
  const [showOptionsEditor, setShowOptionsEditor] = useState(false);

  const { data: systems = [] } = useQuery<CorrespondenceSystem[]>({
    queryKey: ['correspondence-systems'],
    queryFn: getCorrespondenceSystems,
  });

  const { data: systemDetail } = useQuery({
    queryKey: ['correspondence-system', selectedSystemId],
    queryFn: () => getCorrespondenceSystem(selectedSystemId!),
    enabled: selectedSystemId !== null,
  });

  // Which cartomancy type's archetypes to show depends on the selected
  // system's type (falls back to Tarot for backwards compat and for the
  // create-form archetype preview).
  const activeCartomancyType = systemDetail?.cartomancy_type || 'Tarot';

  const { data: allArchetypes = [] } = useQuery<Archetype[]>({
    queryKey: ['archetypes', activeCartomancyType],
    queryFn: () => getArchetypes(activeCartomancyType),
  });

  const { data: allFieldOptions = [] } = useQuery<FieldOption[]>({
    queryKey: ['field-options', 'all'],
    queryFn: () => getFieldOptions(),
  });

  // Group options by field_name
  const optionsByField = new Map<string, FieldOption[]>();
  for (const opt of allFieldOptions) {
    if (!optionsByField.has(opt.field_name)) optionsByField.set(opt.field_name, []);
    optionsByField.get(opt.field_name)!.push(opt);
  }

  const showMsg = (text: string, type: 'success' | 'error') => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 4000);
  };

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['correspondence-systems'] });
    if (selectedSystemId) {
      queryClient.invalidateQueries({ queryKey: ['correspondence-system', selectedSystemId] });
    }
  };

  const handleCreate = async () => {
    if (!newName.trim()) return;
    setCreating(true);
    try {
      let newId: number;
      if (newSourceId) {
        // Clone existing system
        const cloneResult = await cloneCorrespondenceSystem(newSourceId, newName.trim());
        newId = cloneResult.id;
        // Update description separately if provided
        if (newDesc.trim()) {
          await updateCorrespondenceSystem(newId, { description: newDesc.trim() });
        }
        showMsg('System cloned', 'success');
      } else {
        const result = await createCorrespondenceSystem({
          name: newName.trim(),
          description: newDesc.trim() || undefined,
          cartomancy_type: newCartomancyType,
          naming_style: newCartomancyType === 'Tarot' ? newNamingStyle : undefined,
        });
        newId = result.id;
        showMsg('System created', 'success');
      }
      invalidate();
      setSelectedSystemId(newId);
      setNewName('');
      setNewDesc('');
      setNewCartomancyType('Tarot');
      setNewNamingStyle('RWS');
      setNewSourceId('');
      setShowCreate(false);
    } catch {
      showMsg('Failed to create system (name may already exist)', 'error');
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (system: CorrespondenceSystem) => {
    if (!window.confirm(`Delete "${system.name}"? This will remove all its assignments.`)) return;
    try {
      await deleteCorrespondenceSystem(system.id);
      if (selectedSystemId === system.id) setSelectedSystemId(null);
      invalidate();
      showMsg('System deleted', 'success');
    } catch {
      showMsg('Failed to delete system', 'error');
    }
  };

  const handleClone = async () => {
    if (!selectedSystemId || !cloneName.trim()) return;
    try {
      const result = await cloneCorrespondenceSystem(selectedSystemId, cloneName.trim());
      invalidate();
      setSelectedSystemId(result.id);
      setCloneName('');
      setShowClone(false);
      showMsg('System cloned', 'success');
    } catch {
      showMsg('Failed to clone system', 'error');
    }
  };

  const handleSaveMeta = async () => {
    if (!selectedSystemId) return;
    try {
      await updateCorrespondenceSystem(selectedSystemId, {
        name: editingName ?? undefined,
        description: editingDesc ?? undefined,
      });
      invalidate();
      setEditingName(null);
      setEditingDesc(null);
      showMsg('System updated', 'success');
    } catch {
      showMsg('Failed to update system', 'error');
    }
  };

  const handleSetCellValues = async (archetypeId: number, fieldName: string, values: string[]) => {
    if (!selectedSystemId) return;
    try {
      if (values.length === 0) {
        // Empty: clear all sources for this cell (including bulk/group contributions)
        await deleteAssignment(selectedSystemId, archetypeId, fieldName, { all: true });
      } else {
        // Manual multi-value edit: replaces the NULL-sourced rows for this cell
        // (plus clears any non-NULL sources since the user just took ownership)
        await deleteAssignment(selectedSystemId, archetypeId, fieldName, { all: true });
        await setAssignmentValues(selectedSystemId, archetypeId, fieldName, values);
      }
      queryClient.invalidateQueries({ queryKey: ['correspondence-system', selectedSystemId] });
    } catch {
      showMsg('Failed to update assignment', 'error');
    }
  };

  // Group assignments by archetype — each cell may have multiple values from different source groups
  const assignmentsByArchetype = new Map<number, Map<string, string[]>>();

  if (systemDetail?.assignments) {
    for (const a of systemDetail.assignments as CorrespondenceAssignment[]) {
      if (!assignmentsByArchetype.has(a.archetype_id)) {
        assignmentsByArchetype.set(a.archetype_id, new Map());
      }
      const fieldMap = assignmentsByArchetype.get(a.archetype_id)!;
      if (!fieldMap.has(a.field_name)) fieldMap.set(a.field_name, []);
      const values = fieldMap.get(a.field_name)!;
      if (!values.includes(a.field_value)) values.push(a.field_value);
    }
  }

  // Detect group-level patterns (same as Reference view), grouped by category
  const patternSections = useMemo<PatternCategorySection[]>(() => {
    if (!systemDetail?.assignments) return [];
    const patterns = detectGroupPatterns(systemDetail.assignments as CorrespondenceAssignment[]);
    return patternsByCategory(patterns);
  }, [systemDetail]);

  // === Bulk assign groups ===
  // Groups are defined per cartomancy type so the dropdown matches the
  // selected system's deck — Lenormand doesn't have suits or courts, etc.
  type BulkGroup = { label: string; category: string; filter: (a: Archetype) => boolean };

  const TAROT_BULK_GROUPS: BulkGroup[] = [
    { label: 'Major Arcana', category: 'Card Type', filter: a => a.card_type === 'major' },
    { label: 'Minor Arcana', category: 'Card Type', filter: a => a.card_type === 'minor' },
    { label: 'Wands', category: 'Suits', filter: a => a.suit === 'Wands' },
    { label: 'Cups', category: 'Suits', filter: a => a.suit === 'Cups' },
    { label: 'Swords', category: 'Suits', filter: a => a.suit === 'Swords' },
    { label: 'Pentacles', category: 'Suits', filter: a => a.suit === 'Pentacles' },
    { label: 'Pages', category: 'Court Ranks', filter: a => a.name.startsWith('Page of') },
    { label: 'Knights', category: 'Court Ranks', filter: a => a.name.startsWith('Knight of') },
    { label: 'Queens', category: 'Court Ranks', filter: a => a.name.startsWith('Queen of') },
    { label: 'Kings', category: 'Court Ranks', filter: a => a.name.startsWith('King of') },
    { label: 'Court Cards', category: 'Court Ranks', filter: a => {
      if (a.card_type !== 'minor') return false;
      const rankNum = parseInt(a.rank?.slice(-2) || '0');
      return rankNum >= 11 && rankNum <= 14;
    }},
    { label: 'Aces', category: 'Pip Numbers', filter: a => a.name.startsWith('Ace of') },
    { label: 'Twos', category: 'Pip Numbers', filter: a => a.name.startsWith('Two of') },
    { label: 'Threes', category: 'Pip Numbers', filter: a => a.name.startsWith('Three of') },
    { label: 'Fours', category: 'Pip Numbers', filter: a => a.name.startsWith('Four of') },
    { label: 'Fives', category: 'Pip Numbers', filter: a => a.name.startsWith('Five of') },
    { label: 'Sixes', category: 'Pip Numbers', filter: a => a.name.startsWith('Six of') },
    { label: 'Sevens', category: 'Pip Numbers', filter: a => a.name.startsWith('Seven of') },
    { label: 'Eights', category: 'Pip Numbers', filter: a => a.name.startsWith('Eight of') },
    { label: 'Nines', category: 'Pip Numbers', filter: a => a.name.startsWith('Nine of') },
    { label: 'Tens', category: 'Pip Numbers', filter: a => a.name.startsWith('Ten of') },
    { label: 'Pips (Ace-10)', category: 'Pip Numbers', filter: a => {
      if (a.card_type !== 'minor') return false;
      const rankNum = parseInt(a.rank?.slice(-2) || '0');
      return rankNum >= 1 && rankNum <= 10;
    }},
  ];

  const PLAYING_CARDS_BULK_GROUPS: BulkGroup[] = [
    { label: 'Hearts', category: 'Suits', filter: a => a.suit === 'Hearts' },
    { label: 'Diamonds', category: 'Suits', filter: a => a.suit === 'Diamonds' },
    { label: 'Clubs', category: 'Suits', filter: a => a.suit === 'Clubs' },
    { label: 'Spades', category: 'Suits', filter: a => a.suit === 'Spades' },
    { label: 'Aces', category: 'Ranks', filter: a => a.rank === 'Ace' },
    { label: 'Twos', category: 'Ranks', filter: a => a.rank === 'Two' },
    { label: 'Threes', category: 'Ranks', filter: a => a.rank === 'Three' },
    { label: 'Fours', category: 'Ranks', filter: a => a.rank === 'Four' },
    { label: 'Fives', category: 'Ranks', filter: a => a.rank === 'Five' },
    { label: 'Sixes', category: 'Ranks', filter: a => a.rank === 'Six' },
    { label: 'Sevens', category: 'Ranks', filter: a => a.rank === 'Seven' },
    { label: 'Eights', category: 'Ranks', filter: a => a.rank === 'Eight' },
    { label: 'Nines', category: 'Ranks', filter: a => a.rank === 'Nine' },
    { label: 'Tens', category: 'Ranks', filter: a => a.rank === 'Ten' },
    { label: 'Jacks', category: 'Ranks', filter: a => a.rank === 'Jack' },
    { label: 'Queens', category: 'Ranks', filter: a => a.rank === 'Queen' },
    { label: 'Kings', category: 'Ranks', filter: a => a.rank === 'King' },
    { label: 'Jokers', category: 'Ranks', filter: a => a.rank === 'Joker' },
  ];

  // Lenormand cards each have a traditional playing-card inset. Group by
  // that inset's suit and rank so "Aces" in Lenormand = Ring/Man/Woman/Sun, etc.
  const LENORMAND_PLAYING_CARD: Record<string, { suit: string; rank: string }> = {
    'Rider':      { suit: 'Hearts',   rank: 'Nine' },
    'Clover':     { suit: 'Diamonds', rank: 'Six' },
    'Ship':       { suit: 'Spades',   rank: 'Ten' },
    'House':      { suit: 'Hearts',   rank: 'King' },
    'Tree':       { suit: 'Hearts',   rank: 'Seven' },
    'Clouds':     { suit: 'Clubs',    rank: 'King' },
    'Snake':      { suit: 'Clubs',    rank: 'Queen' },
    'Coffin':     { suit: 'Diamonds', rank: 'Nine' },
    'Bouquet':    { suit: 'Spades',   rank: 'Queen' },
    'Scythe':     { suit: 'Diamonds', rank: 'Jack' },
    'Whip':       { suit: 'Clubs',    rank: 'Jack' },
    'Birds':      { suit: 'Diamonds', rank: 'Seven' },
    'Child':      { suit: 'Spades',   rank: 'Jack' },
    'Fox':        { suit: 'Clubs',    rank: 'Nine' },
    'Bear':       { suit: 'Clubs',    rank: 'Ten' },
    'Stars':      { suit: 'Hearts',   rank: 'Six' },
    'Stork':      { suit: 'Hearts',   rank: 'Queen' },
    'Dog':        { suit: 'Hearts',   rank: 'Ten' },
    'Tower':      { suit: 'Spades',   rank: 'Six' },
    'Garden':     { suit: 'Spades',   rank: 'Eight' },
    'Mountain':   { suit: 'Clubs',    rank: 'Eight' },
    'Crossroads': { suit: 'Diamonds', rank: 'Queen' },
    'Mice':       { suit: 'Clubs',    rank: 'Seven' },
    'Heart':      { suit: 'Hearts',   rank: 'Jack' },
    'Ring':       { suit: 'Clubs',    rank: 'Ace' },
    'Book':       { suit: 'Diamonds', rank: 'Ten' },
    'Letter':     { suit: 'Spades',   rank: 'Seven' },
    'Man':        { suit: 'Hearts',   rank: 'Ace' },
    'Woman':      { suit: 'Spades',   rank: 'Ace' },
    'Lily':       { suit: 'Spades',   rank: 'King' },
    'Sun':        { suit: 'Diamonds', rank: 'Ace' },
    'Moon':       { suit: 'Hearts',   rank: 'Eight' },
    'Key':        { suit: 'Diamonds', rank: 'Eight' },
    'Fish':       { suit: 'Diamonds', rank: 'King' },
    'Anchor':     { suit: 'Spades',   rank: 'Nine' },
    'Cross':      { suit: 'Clubs',    rank: 'Six' },
  };

  const LENORMAND_BULK_GROUPS: BulkGroup[] = [
    { label: 'Hearts', category: 'Suits',
      filter: a => LENORMAND_PLAYING_CARD[a.name]?.suit === 'Hearts' },
    { label: 'Diamonds', category: 'Suits',
      filter: a => LENORMAND_PLAYING_CARD[a.name]?.suit === 'Diamonds' },
    { label: 'Clubs', category: 'Suits',
      filter: a => LENORMAND_PLAYING_CARD[a.name]?.suit === 'Clubs' },
    { label: 'Spades', category: 'Suits',
      filter: a => LENORMAND_PLAYING_CARD[a.name]?.suit === 'Spades' },
    { label: 'Aces', category: 'Ranks',
      filter: a => LENORMAND_PLAYING_CARD[a.name]?.rank === 'Ace' },
    { label: 'Sixes', category: 'Ranks',
      filter: a => LENORMAND_PLAYING_CARD[a.name]?.rank === 'Six' },
    { label: 'Sevens', category: 'Ranks',
      filter: a => LENORMAND_PLAYING_CARD[a.name]?.rank === 'Seven' },
    { label: 'Eights', category: 'Ranks',
      filter: a => LENORMAND_PLAYING_CARD[a.name]?.rank === 'Eight' },
    { label: 'Nines', category: 'Ranks',
      filter: a => LENORMAND_PLAYING_CARD[a.name]?.rank === 'Nine' },
    { label: 'Tens', category: 'Ranks',
      filter: a => LENORMAND_PLAYING_CARD[a.name]?.rank === 'Ten' },
    { label: 'Jacks', category: 'Ranks',
      filter: a => LENORMAND_PLAYING_CARD[a.name]?.rank === 'Jack' },
    { label: 'Queens', category: 'Ranks',
      filter: a => LENORMAND_PLAYING_CARD[a.name]?.rank === 'Queen' },
    { label: 'Kings', category: 'Ranks',
      filter: a => LENORMAND_PLAYING_CARD[a.name]?.rank === 'King' },
  ];

  const GROUPS_BY_TYPE: Record<string, BulkGroup[]> = {
    'Tarot': TAROT_BULK_GROUPS,
    'Playing Cards': PLAYING_CARDS_BULK_GROUPS,
    'Lenormand': LENORMAND_BULK_GROUPS,
  };

  const BULK_GROUPS = GROUPS_BY_TYPE[activeCartomancyType] || [];

  // Build ordered category list from BULK_GROUPS
  const BULK_CATEGORIES: string[] = [];
  for (const g of BULK_GROUPS) {
    if (!BULK_CATEGORIES.includes(g.category)) BULK_CATEGORIES.push(g.category);
  }

  const getGroupArchetypes = (groupLabel: string): Archetype[] => {
    const group = BULK_GROUPS.find(g => g.label === groupLabel);
    if (!group) return [];
    return allArchetypes.filter(group.filter);
  };

  const handleBulkApply = async () => {
    if (!selectedSystemId || !bulkGroup || !bulkField || bulkValues.length === 0) return;
    const archetypes = getGroupArchetypes(bulkGroup);
    if (archetypes.length === 0) return;

    setBulkApplying(true);
    try {
      for (const a of archetypes) {
        await setAssignmentValues(selectedSystemId, a.id, bulkField, bulkValues, bulkGroup);
      }

      // Optimistic cache update so the table reflects the change immediately
      const affectedIds = new Set(archetypes.map(a => a.id));
      queryClient.setQueryData<{ assignments: CorrespondenceAssignment[] } & Record<string, unknown>>(
        ['correspondence-system', selectedSystemId],
        (old) => {
          if (!old) return old;
          // Remove any prior rows for this group/field and the affected archetypes,
          // then append the new value rows.
          const kept = old.assignments.filter(a => !(
            a.source_group === bulkGroup && a.field_name === bulkField && affectedIds.has(a.archetype_id)
          ));
          const added: CorrespondenceAssignment[] = [];
          for (const a of archetypes) {
            for (const v of bulkValues) {
              added.push({
                id: -1, // placeholder; backend id will arrive on refetch
                system_id: selectedSystemId,
                archetype_id: a.id,
                archetype_name: a.name,
                cartomancy_type: a.cartomancy_type,
                rank: a.rank,
                suit: a.suit,
                card_type: a.card_type,
                field_name: bulkField,
                field_value: v,
                source_group: bulkGroup,
              });
            }
          }
          return { ...old, assignments: [...kept, ...added] };
        },
      );
      queryClient.invalidateQueries({ queryKey: ['correspondence-system', selectedSystemId] });

      const label = CORRESPONDENCE_FIELD_LABELS[bulkField];
      const valueDesc = bulkValues.length === 1 ? bulkValues[0] : `[${bulkValues.join(', ')}]`;
      showMsg(`Set ${label} = ${valueDesc} for ${archetypes.length} cards`, 'success');
      setBulkValues([]);
    } catch {
      showMsg('Failed to apply bulk assignment', 'error');
    } finally {
      setBulkApplying(false);
    }
  };

  const handleExpandElemental = async () => {
    if (!selectedSystemId || !bulkGroup) return;
    const archetypes = getGroupArchetypes(bulkGroup);
    if (archetypes.length === 0) return;

    setBulkApplying(true);
    try {
      await expandElementalZodiac(
        selectedSystemId,
        archetypes.map(a => a.id),
        bulkGroup,
      );
      queryClient.invalidateQueries({ queryKey: ['correspondence-system', selectedSystemId] });
      showMsg(`Assigned elemental zodiac signs to ${archetypes.length} cards in "${displayGroupLabel(bulkGroup, activeNamingStyle)}"`, 'success');
    } catch {
      showMsg('Failed to expand elemental zodiac', 'error');
    } finally {
      setBulkApplying(false);
    }
  };

  const handleBulkClear = async () => {
    if (!selectedSystemId || !bulkGroup || !bulkField) return;
    const archetypes = getGroupArchetypes(bulkGroup);
    if (archetypes.length === 0) return;

    if (!window.confirm(
      `Clear the "${displayGroupLabel(bulkGroup, activeNamingStyle)}" group's ${CORRESPONDENCE_FIELD_LABELS[bulkField]} values for all ${archetypes.length} cards?\n\nOther contributions (manual edits or other groups) are not affected.`
    )) return;

    setBulkApplying(true);
    try {
      // Run deletes sequentially so the DB's internal lock doesn't starve
      // under parallel load, and any auto-derived cleanup (e.g. modality
      // zodiac refresh) runs cleanly between deletes.
      for (const a of archetypes) {
        await deleteAssignment(selectedSystemId, a.id, bulkField, { sourceGroup: bulkGroup });
      }

      // Optimistically update the cached systemDetail so the UI reflects the
      // removal immediately. React Query's invalidate+refetch can lag enough
      // that the table doesn't visibly update until the user navigates away.
      const affectedIds = new Set(archetypes.map(a => a.id));
      const isAutoDerivedClear = bulkField === 'modality'; // modality clear also wipes auto:modality zodiac
      queryClient.setQueryData<{ assignments: CorrespondenceAssignment[] } & Record<string, unknown>>(
        ['correspondence-system', selectedSystemId],
        (old) => {
          if (!old) return old;
          const filtered = old.assignments.filter(a => {
            if (a.source_group === bulkGroup && a.field_name === bulkField && affectedIds.has(a.archetype_id)) {
              return false;
            }
            if (isAutoDerivedClear && a.source_group === 'auto:modality' && a.field_name === 'zodiac_sign' && affectedIds.has(a.archetype_id)) {
              return false;
            }
            return true;
          });
          return { ...old, assignments: filtered };
        },
      );

      // Still invalidate so we'll eventually reconcile with the authoritative backend data
      queryClient.invalidateQueries({
        queryKey: ['correspondence-system', selectedSystemId],
      });
      showMsg(`Cleared "${displayGroupLabel(bulkGroup, activeNamingStyle)}" ${CORRESPONDENCE_FIELD_LABELS[bulkField]} for ${archetypes.length} cards`, 'success');
    } catch {
      showMsg('Failed to clear bulk assignment', 'error');
    } finally {
      setBulkApplying(false);
    }
  };

  // Get all archetypes that have at least one assignment, filtered
  // Show every archetype from the deck type so a newly-created (empty) system
  // still lets the user assign values. Sort by the naming-style-aware rank so
  // e.g. Marseille swaps Strength (8 ↔ 11) with Justice.
  const activeNamingStyle = systemDetail?.naming_style || null;
  const sortedArchetypes = [...allArchetypes].sort((a, b) =>
    archetypeSortKey(a.name, a.rank, activeNamingStyle)
      - archetypeSortKey(b.name, b.rank, activeNamingStyle)
  );
  const visibleArchetypes = sortedArchetypes.filter(a => {
    if (!filterText) return true;
    const display = displayArchetypeName(a.name, activeNamingStyle).toLowerCase();
    return a.name.toLowerCase().includes(filterText.toLowerCase())
      || display.includes(filterText.toLowerCase());
  });

  return (
    <div className="settings-tab__scroll">
      <h2 className="settings-tab__title">Correspondence Systems</h2>

      {message && (
        <div className={`settings-tab__message settings-tab__message--${message.type}`}>
          {message.text}
        </div>
      )}

      {/* System List */}
      <section className="settings-tab__section">
        <p className="settings-tab__hint">
          Correspondence systems define canonical element, planet, zodiac, and other
          assignments for card archetypes. Decks can select a system to inherit these values.
        </p>

        <div className="corr-systems__list">
          {systems.map(sys => (
            <div
              key={sys.id}
              className={`corr-systems__item ${selectedSystemId === sys.id ? 'corr-systems__item--selected' : ''}`}
              onClick={() => setSelectedSystemId(sys.id)}
            >
              <div className="corr-systems__item-info">
                <span className="corr-systems__item-name">
                  {sys.name}
                  {!!sys.is_builtin && <span className="settings-tab__import-preset-badge">built-in</span>}
                </span>
                <span className="corr-systems__item-stats">
                  {sys.archetype_count} archetypes · {sys.assignment_count} assignments
                </span>
              </div>
              <div className="corr-systems__item-actions">
                <button
                  className="settings-tab__import-preset-btn settings-tab__import-preset-btn--danger"
                  onClick={(e) => { e.stopPropagation(); handleDelete(sys); }}
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>

        <div style={{ display: 'flex', gap: 16, alignItems: 'center', marginBottom: 8 }}>
          <button
            className="settings-tab__customize-btn"
            onClick={() => setShowOptionsEditor(!showOptionsEditor)}
          >
            {showOptionsEditor ? 'Hide Field Options' : 'Edit Field Options...'}
          </button>
          <span className="settings-tab__hint" style={{ margin: 0 }}>
            Manage the values available in correspondence dropdowns (global, applies to all systems).
          </span>
        </div>

        {showOptionsEditor && (
          <div style={{ marginBottom: 12 }}>
            <FieldOptionsEditor onClose={() => setShowOptionsEditor(false)} />
          </div>
        )}

        {!showCreate ? (
          <button className="settings-tab__add-preset-btn" onClick={() => setShowCreate(true)}>
            + New System
          </button>
        ) : (
          <div className="corr-systems__create-form">
            <div className="settings-tab__field">
              <label className="settings-tab__label">Name</label>
              <input
                type="text"
                value={newName}
                onChange={e => setNewName(e.target.value)}
                placeholder="e.g. Thoth, Golden Dawn"
              />
            </div>
            {!newSourceId && (
              <>
                <div className="settings-tab__field">
                  <label className="settings-tab__label">Deck Type</label>
                  <select
                    value={newCartomancyType}
                    onChange={e => setNewCartomancyType(e.target.value)}
                  >
                    <option value="Tarot">Tarot</option>
                    <option value="Lenormand">Lenormand</option>
                    <option value="Playing Cards">Playing Cards</option>
                    <option value="Oracle">Oracle</option>
                    <option value="I Ching">I Ching</option>
                    <option value="Kipper">Kipper</option>
                  </select>
                </div>
                {newCartomancyType === 'Tarot' && (
                  <div className="settings-tab__field">
                    <label className="settings-tab__label">Naming &amp; Ordering</label>
                    <select
                      value={newNamingStyle}
                      onChange={e => setNewNamingStyle(e.target.value)}
                    >
                      <option value="RWS">Rider-Waite-Smith (Page, Knight, Queen, King)</option>
                      <option value="Thoth">Thoth (Princess, Prince, Queen, Knight; Adjustment/Lust)</option>
                      <option value="Marseille">Marseille / Pre-Golden Dawn (Justice=8, Strength=11)</option>
                    </select>
                    <p className="settings-tab__hint" style={{ marginTop: 4, marginBottom: 0 }}>
                      Changes card labels shown in this system. Card data is shared across styles.
                    </p>
                  </div>
                )}
              </>
            )}
            <div className="settings-tab__field">
              <label className="settings-tab__label">Base on</label>
              <select
                value={newSourceId}
                onChange={e => setNewSourceId(e.target.value ? Number(e.target.value) : '')}
              >
                <option value="">Empty (no assignments)</option>
                {systems.map(sys => (
                  <option key={sys.id} value={sys.id}>Clone: {sys.name}</option>
                ))}
              </select>
              {newSourceId && (
                <p className="settings-tab__hint" style={{ marginTop: 4, marginBottom: 0 }}>
                  All assignments from the source system will be copied, including its deck type and naming style.
                </p>
              )}
            </div>
            <div className="settings-tab__field">
              <label className="settings-tab__label">Description</label>
              <input
                type="text"
                value={newDesc}
                onChange={e => setNewDesc(e.target.value)}
                placeholder="Optional description"
              />
            </div>
            <div className="corr-systems__create-actions">
              <button onClick={() => {
                setShowCreate(false);
                setNewName('');
                setNewDesc('');
                setNewCartomancyType('Tarot');
                setNewNamingStyle('RWS');
                setNewSourceId('');
              }}>Cancel</button>
              <button
                className="settings-tab__save-btn"
                onClick={handleCreate}
                disabled={creating || !newName.trim()}
              >
                {creating ? (newSourceId ? 'Cloning...' : 'Creating...') : (newSourceId ? 'Clone' : 'Create')}
              </button>
            </div>
          </div>
        )}
      </section>

      {/* System Detail / Assignment Editor */}
      {systemDetail && (
        <section className="settings-tab__section">
          <div className="corr-systems__detail-header">
            {editingName !== null ? (
              <div className="corr-systems__edit-meta">
                <input
                  type="text"
                  value={editingName}
                  onChange={e => setEditingName(e.target.value)}
                  placeholder="System name"
                />
                <input
                  type="text"
                  value={editingDesc ?? ''}
                  onChange={e => setEditingDesc(e.target.value)}
                  placeholder="Description"
                />
                <div className="corr-systems__create-actions">
                  <button onClick={() => { setEditingName(null); setEditingDesc(null); }}>Cancel</button>
                  <button className="settings-tab__save-btn" onClick={handleSaveMeta}>Save</button>
                </div>
              </div>
            ) : (
              <>
                <div>
                  <h3 className="settings-tab__section-title" style={{ marginBottom: 2 }}>
                    {systemDetail.name}
                    <span style={{ marginLeft: 8, fontSize: 'var(--font-size-small)', color: 'var(--text-dim)', fontWeight: 'normal' }}>
                      {activeCartomancyType}
                      {activeCartomancyType === 'Tarot' && activeNamingStyle && activeNamingStyle !== 'RWS' ? ` · ${activeNamingStyle}` : ''}
                    </span>
                  </h3>
                  {systemDetail.description && (
                    <p className="settings-tab__hint" style={{ margin: 0 }}>
                      {systemDetail.description}
                    </p>
                  )}
                </div>
                <div className="corr-systems__detail-actions">
                  <button onClick={() => {
                    setEditingName(systemDetail.name);
                    setEditingDesc(systemDetail.description || '');
                  }}>
                    Rename
                  </button>
                  {!showClone ? (
                    <button onClick={() => setShowClone(true)}>Clone</button>
                  ) : (
                    <div className="corr-systems__clone-inline">
                      <input
                        type="text"
                        value={cloneName}
                        onChange={e => setCloneName(e.target.value)}
                        placeholder="New name"
                        style={{ width: 150 }}
                      />
                      <button className="settings-tab__save-btn" onClick={handleClone} disabled={!cloneName.trim()}>
                        Clone
                      </button>
                      <button onClick={() => { setShowClone(false); setCloneName(''); }}>
                        Cancel
                      </button>
                    </div>
                  )}
                </div>
              </>
            )}
          </div>

          {/* Group-level patterns summary (same as Reference view) */}
          {patternSections.length > 0 && (
            <div className="corr-viewer__group-summary">
              <h4 className="corr-viewer__group-title">Group Patterns</h4>
              {patternSections.map(section => (
                <div key={section.category} className="corr-viewer__group-category">
                  <div className="corr-viewer__group-category-heading">{section.category}</div>
                  {section.groups.map(({ groupLabel, patterns }) => (
                    <div key={groupLabel} className="corr-viewer__group-row">
                      <span className="corr-viewer__group-field">{displayGroupLabel(groupLabel, activeNamingStyle)}</span>
                      <div className="corr-viewer__group-values">
                        {patterns.map(p => (
                          <span key={p.fieldLabel} className="corr-viewer__group-tag">
                            <span className="corr-viewer__group-name">{p.fieldLabel}</span>
                            <span className="corr-viewer__group-eq">=</span>
                            <span className="corr-viewer__group-val">{p.value}</span>
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              ))}
            </div>
          )}

          {/* Bulk Assign */}
          <div className="corr-bulk">
            <button
              className="settings-tab__customize-btn"
              onClick={() => setShowBulk(!showBulk)}
            >
              {showBulk ? 'Hide Bulk Assign' : 'Bulk Assign by Group...'}
            </button>

            {showBulk && (
              <div className="corr-bulk__panel">
                <div className="corr-bulk__row">
                  <div className="corr-bulk__field">
                    <label className="settings-tab__label">Group</label>
                    <select
                      value={bulkGroup}
                      onChange={e => setBulkGroup(e.target.value)}
                      disabled={BULK_GROUPS.length === 0}
                    >
                      <option value="">
                        {BULK_GROUPS.length === 0
                          ? `No preset groups for ${activeCartomancyType}`
                          : 'Select a group...'}
                      </option>
                      {BULK_CATEGORIES.map(cat => (
                        <optgroup key={cat} label={cat}>
                          {BULK_GROUPS.filter(g => g.category === cat).map(g => (
                            <option key={g.label} value={g.label}>
                              {displayGroupLabel(g.label, activeNamingStyle)}
                            </option>
                          ))}
                        </optgroup>
                      ))}
                    </select>
                  </div>

                  <div className="corr-bulk__field">
                    <label className="settings-tab__label">Field</label>
                    <select value={bulkField} onChange={e => setBulkField(e.target.value)}>
                      {CORRESPONDENCE_FIELDS.map(f => (
                        <option key={f} value={f}>{CORRESPONDENCE_FIELD_LABELS[f]}</option>
                      ))}
                    </select>
                  </div>

                  <div className="corr-bulk__field" style={{ flex: 1 }}>
                    <label className="settings-tab__label">Value(s)</label>
                    <MultiValueSelect
                      values={bulkValues}
                      options={(optionsByField.get(bulkField) || []).map(o => o.option_value)}
                      onCommit={setBulkValues}
                      placeholder="Select value(s)..."
                    />
                  </div>

                  <div className="corr-bulk__field corr-bulk__actions" style={{ alignSelf: 'flex-end' }}>
                    <button
                      className="settings-tab__save-btn"
                      onClick={handleBulkApply}
                      disabled={bulkApplying || !bulkGroup || bulkValues.length === 0}
                    >
                      {bulkApplying ? 'Working...' : `Apply${bulkGroup ? ` (${getGroupArchetypes(bulkGroup).length})` : ''}`}
                    </button>
                    <button
                      className="corr-bulk__clear-btn"
                      onClick={handleBulkClear}
                      disabled={bulkApplying || !bulkGroup}
                      title="Remove the assignment for every card in this group"
                    >
                      Clear
                    </button>
                  </div>
                </div>

                {bulkGroup && (
                  <p className="settings-tab__hint" style={{ marginTop: 4 }}>
                    Targets {getGroupArchetypes(bulkGroup).length} cards: {getGroupArchetypes(bulkGroup).slice(0, 4).map(a => a.name).join(', ')}{getGroupArchetypes(bulkGroup).length > 4 ? ', ...' : ''}
                    <br />
                    <strong>Apply</strong> sets {CORRESPONDENCE_FIELD_LABELS[bulkField]} = "{bulkValues.join(', ') || '...'}" for these cards. <strong>Clear</strong> removes {CORRESPONDENCE_FIELD_LABELS[bulkField]} entirely (card-level overrides are not affected).
                  </p>
                )}

                {bulkField === 'zodiac_sign' && activeCartomancyType === 'Tarot' && (
                  <div style={{ marginTop: 12, paddingTop: 12, borderTop: '1px solid var(--border)' }}>
                    <button
                      className="settings-tab__save-btn"
                      onClick={handleExpandElemental}
                      disabled={bulkApplying || !bulkGroup}
                      style={{ marginRight: 8 }}
                    >
                      {bulkApplying ? 'Working...' : 'Expand to Elemental Signs'}
                    </button>
                    <span className="settings-tab__hint">
                      Assigns all 3 zodiac signs of each card's suit element (Wands→Aries/Leo/Sagittarius, etc). Common for Aces representing the "root" of an element.
                    </span>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Filter */}
          <div className="corr-systems__filter">
            <input
              type="text"
              value={filterText}
              onChange={e => setFilterText(e.target.value)}
              placeholder="Filter cards..."
              className="corr-systems__filter-input"
            />
          </div>

          {/* Assignment Table */}
          <div className="corr-systems__table-wrap">
            <table className="corr-systems__table">
              <thead>
                <tr>
                  <th className="corr-systems__th--card">Card</th>
                  {CORRESPONDENCE_FIELDS.map(f => (
                    <th key={f}>{CORRESPONDENCE_FIELD_LABELS[f]}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {visibleArchetypes.map(arch => {
                  const fields = assignmentsByArchetype.get(arch.id);
                  const displayName = displayArchetypeName(arch.name, activeNamingStyle);
                  return (
                    <tr key={arch.id}>
                      <td className="corr-systems__td--card">
                        <span className="corr-systems__card-name">{displayName}</span>
                      </td>
                      {CORRESPONDENCE_FIELDS.map(f => (
                        <td key={f}>
                          <MultiValueSelect
                            values={fields?.get(f) || []}
                            options={(optionsByField.get(f) || []).map(o => o.option_value)}
                            onCommit={vals => handleSetCellValues(arch.id, f, vals)}
                            compact
                          />
                        </td>
                      ))}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {visibleArchetypes.length === 0 && (
            <p className="settings-tab__hint" style={{ textAlign: 'center', padding: 20 }}>
              {filterText ? 'No cards match your filter.' : 'Loading archetypes...'}
            </p>
          )}
        </section>
      )}
    </div>
  );
}
