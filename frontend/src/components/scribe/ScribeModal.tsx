/**
 * The Scribe — imports book/photo content into reference data with an
 * AI assistant, while keeping the user in charge of what gets written.
 *
 * Flow (all inside one modal):
 *   1. Setup — pick cartomancy type, which source fields to fill,
 *      optionally a deck + card custom fields, and add source material
 *      (EPUB/PDF/MOBI/text extracted server-side; photos read locally).
 *   2. Chat + review — the model extracts per-card proposals; they
 *      render in a review table beside the chat. The user refines by
 *      chatting ("split the keywords into their own field", "you
 *      garbled the Queen of Cups") and the model re-emits proposals.
 *   3. Apply — checked rows are written in one batch: source fields
 *      go to archetype notes, card fields to the deck's cards.
 *
 * The model returns proposals as a fenced ```json block in each
 * message; the block is parsed out and never shown raw in the chat.
 */
import { useEffect, useMemo, useRef, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import Modal, { ModalCancelButton } from '../common/Modal';
import { useToast } from '../../context/ToastContext';
import { getSourceFields, getSourceEntries } from '../../api/referenceSources';
import { getArchetypes, type Archetype } from '../../api/correspondences';
import { getDecks, getDeckCustomFields } from '../../api/decks';
import { getCards } from '../../api/cards';
import { extractSourceText, applyScribeWrites, type ScribeWrite } from '../../api/scribe';
import { llmChat, getLlmConfig, type LlmMessage, type LlmMessagePart } from '../../api/llm';
import type { ReferenceSource, SourceField, Card, Deck, DeckCustomField } from '../../types';
import './ScribeModal.css';

/** Launched from a reference source (fills its archetype-note fields,
 *  optionally card fields on a deck too) or directly from a deck
 *  (fills that deck's card custom fields only). Exactly one of
 *  source/deck must be provided. */
interface ScribeModalProps {
  source?: ReferenceSource;
  deck?: Deck;
  open: boolean;
  onClose: () => void;
}

/** One extraction request: a chunk of book text, or a group of page
 *  photos. Each unit is sent as its own message in the conversation.
 *  text/images keep the raw material so a unit whose reply overflows
 *  the output limit can be split in half and re-queued. */
interface ExtractionUnit {
  label: string;
  parts: LlmMessagePart[];
  text?: string;
  images?: Material[];
}

// ── Source material the user has added ───────────────────────
interface Material {
  id: number;
  filename: string;
  kind: 'text' | 'image';
  text?: string;       // extracted text (ebooks)
  data?: string;       // base64 (images)
  mediaType?: string;
  charCount?: number;
  warning?: string | null;
}

// ── One proposal row parsed from the model's JSON ────────────
interface Proposal {
  card: string;                    // the name the model used
  fields: Record<string, string>;  // field label → content
  flags?: string[];
  // resolved locally:
  archetypeId?: number;
  cardId?: number;
  checked: boolean;
}

// Ceiling on total source text per session. Extraction itself has no
// real limit (each part is its own small request); this guards the
// refinement chat, whose stitched conversation holds the whole book
// and must fit the big models' 1M-token context. ~3M chars ≈ 750k
// tokens, leaving room for the extraction replies alongside it.
const MAX_SOURCE_CHARS = 3_000_000;
// The APP drives batching, not the model: long books are cut into
// parts of this size and each part is one small, fast request. Sized
// so even a part that is wall-to-wall card text produces a reply
// under the 64k output limit; a part that still overflows gets split
// in half and re-queued automatically.
const CHUNK_CHARS = 90_000;
const IMAGES_PER_UNIT = 8;
// Parts are independent, so several can extract at once — wall-clock
// time divides accordingly. Kept modest to stay under API rate limits.
const CONCURRENT_PARTS = 3;
// Chunks overlap so a card cut at one part's end appears whole at the
// next part's start; the merge keeps whichever version is longer.
// Sized for books with long per-card essays (several pages ≈ 8k chars);
// anything longer still gets caught by the automatic completion pass.
const CHUNK_OVERLAP = 8_000;
// Flags the model uses when a card's text was cut off at a boundary —
// these trigger the automatic completion pass after extraction.
const INCOMPLETE_FLAG = /cut\s*off|incomplete|truncat|continu/i;
// Attempts per part before it lands on the Resume list: transient
// failures (empty replies, overloads) usually clear on the second try.
const UNIT_ATTEMPTS = 2;
const RETRY_DELAY_MS = 3_000;
// Downscale photos so a stack of LWB pages doesn't blow request limits.
const IMAGE_MAX_EDGE = 2000;

let materialIdCounter = 1;

export default function ScribeModal({ source, deck, open, onClose }: ScribeModalProps) {
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  // Which cartomancy types this import can cover, and what to call it
  const availableTypes = useMemo(
    () => source
      ? source.cartomancy_types
      : (deck?.cartomancy_types || []).map(t => t.name),
    [source, deck],
  );
  const displayName = source?.name ?? deck?.name ?? '';

  // ── Setup state ────────────────────────────────────────────
  const [ctype, setCtype] = useState(availableTypes[0] || 'Tarot');
  const [selectedFieldIds, setSelectedFieldIds] = useState<number[]>([]);
  const [deckId, setDeckId] = useState<number | ''>(deck?.id ?? '');
  // Card fields: definitions ticked from the deck + free-typed extras
  const [selectedCardFields, setSelectedCardFields] = useState<string[]>([]);
  const [cardFieldsText, setCardFieldsText] = useState('');
  const [materials, setMaterials] = useState<Material[]>([]);
  const [extracting, setExtracting] = useState(false);
  const [stage, setStage] = useState<'setup' | 'chat'>('setup');

  // ── Chat state ─────────────────────────────────────────────
  const [messages, setMessages] = useState<LlmMessage[]>([]);
  const [displayMessages, setDisplayMessages] = useState<{ role: string; text: string }[]>([]);
  const [chatInput, setChatInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [proposals, setProposals] = useState<Proposal[]>([]);
  const [applying, setApplying] = useState(false);
  // Parts of the book still waiting to be sent (nonempty after a
  // mid-extraction failure — powers the Resume button).
  const [pendingUnits, setPendingUnits] = useState<ExtractionUnit[]>([]);
  const systemPromptRef = useRef('');
  // Source of truth for proposal logic. React state is only its render
  // mirror — EVERY change must go through updateProposals below, so
  // async merges and user checkbox clicks can never diverge (a merge
  // building on a stale copy would visually revert the panel).
  const proposalsRef = useRef<Proposal[]>([]);
  const chatEndRef = useRef<HTMLDivElement>(null);

  const updateProposals = (fn: (current: Proposal[]) => Proposal[]): Proposal[] => {
    const next = fn(proposalsRef.current);
    proposalsRef.current = next;
    setProposals(next);
    return next;
  };

  // Mirrors for async code (same rationale as proposalsRef): user
  // events and worker loops need current values, not render-time ones.
  const busyRef = useRef(false);
  const messagesRef = useRef<LlmMessage[]>([]);
  // Messages typed while the model is working: they steer the parts
  // not yet sent, then get a real reply once the workers go quiet.
  const steeringNotesRef = useRef<string[]>([]);

  const setBusyTracked = (b: boolean) => { busyRef.current = b; setBusy(b); };
  const setMessagesTracked = (m: LlmMessage[]) => { messagesRef.current = m; setMessages(m); };

  const { data: llmConfig } = useQuery({ queryKey: ['llm-config'], queryFn: getLlmConfig, enabled: open });
  const { data: fields = [] } = useQuery<SourceField[]>({
    queryKey: ['source-fields', source?.id, ctype],
    queryFn: () => getSourceFields(source!.id, ctype),
    enabled: open && !!source,
  });
  const { data: archetypes = [] } = useQuery<Archetype[]>({
    queryKey: ['archetypes', ctype],
    queryFn: () => getArchetypes(ctype),
    enabled: open,
  });
  const { data: decks = [] } = useQuery<Deck[]>({
    queryKey: ['decks'],
    queryFn: () => getDecks(),
    enabled: open,
  });
  const { data: deckCards = [] } = useQuery<Card[]>({
    queryKey: ['cards', deckId],
    queryFn: () => getCards(deckId as number),
    enabled: open && deckId !== '',
  });
  const { data: existingEntries = [] } = useQuery({
    queryKey: ['source-entries', source?.id, ctype],
    queryFn: () => getSourceEntries(source!.id, ctype),
    enabled: open && !!source,
  });
  const { data: deckFieldDefs = [] } = useQuery<DeckCustomField[]>({
    queryKey: ['deck-custom-fields', deckId],
    queryFn: () => getDeckCustomFields(deckId as number),
    enabled: open && deckId !== '',
  });

  // Default: all source fields selected
  useEffect(() => {
    setSelectedFieldIds(fields.map(f => f.id));
  }, [fields]);

  // Deck mode: preselect the deck's existing field definitions
  useEffect(() => {
    if (deck) setSelectedCardFields(deckFieldDefs.map(f => f.field_name));
  }, [deck, deckFieldDefs]);

  // Reset everything when the modal opens fresh
  useEffect(() => {
    if (!open) return;
    setStage('setup');
    setMaterials([]);
    setMessagesTracked([]);
    setDisplayMessages([]);
    updateProposals(() => []);
    setPendingUnits([]);
    steeringNotesRef.current = [];
    setChatInput('');
    setCtype(availableTypes[0] || 'Tarot');
    setDeckId(deck?.id ?? '');
    setSelectedCardFields([]);
    setCardFieldsText('');
  }, [open, source?.id, deck?.id, availableTypes]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [displayMessages, busy]);

  const decksForType = useMemo(
    () => decks.filter(d => (d.cartomancy_types || []).some(t => t.name === ctype)),
    [decks, ctype],
  );

  const cardFieldNames = useMemo(() => {
    const typed = cardFieldsText.split(/[,;\n]/).map(s => s.trim()).filter(Boolean);
    const all = [...selectedCardFields, ...typed];
    // De-dupe case-insensitively, first occurrence wins
    const seen = new Set<string>();
    return all.filter(n => {
      const k = n.toLowerCase();
      if (seen.has(k)) return false;
      seen.add(k);
      return true;
    });
  }, [selectedCardFields, cardFieldsText]);

  const selectedFields = fields.filter(f => selectedFieldIds.includes(f.id));
  const totalChars = materials.reduce((n, m) => n + (m.charCount || 0), 0);

  // What kinds of writes this session can actually perform. A row is
  // only truly "matched" if it can reach at least one write target —
  // e.g. in a deck-only import, matching an archetype that has no card
  // in the deck still means nothing can be written.
  const hasArchetypeTargets = !!source && selectedFields.length > 0;
  const hasCardTargets = deckId !== '' && cardFieldNames.length > 0;
  const isWritable = (p: Proposal) =>
    (p.archetypeId != null && hasArchetypeTargets) ||
    (p.cardId != null && hasCardTargets);

  // Existing archetype content, for overwrite badges: "archetypeId:fieldId"
  const existingKeys = useMemo(() => {
    const set = new Set<string>();
    for (const e of existingEntries) set.add(`${e.archetype_id}:${e.field_id}`);
    return set;
  }, [existingEntries]);

  // Per-field coverage: how many of this type's archetypes already
  // have content, straight from the data behind the overwrite badges.
  // Drives the "(12 of 78 filled)" hints and the gaps-only shortcut.
  const fieldCoverage = useMemo(() => {
    const map = new Map<number, number>();
    for (const f of fields) {
      map.set(f.id, new Set(
        existingEntries.filter(e => e.field_id === f.id).map(e => e.archetype_id),
      ).size);
    }
    return map;
  }, [fields, existingEntries]);

  const fieldsWithGaps = fields.filter(f =>
    (fieldCoverage.get(f.id) ?? 0) < archetypes.length);

  // ── File intake ────────────────────────────────────────────
  const handleAddFiles = async (files: FileList | null) => {
    if (!files?.length) return;
    setExtracting(true);
    for (const file of Array.from(files)) {
      try {
        if (file.type.startsWith('image/')) {
          const { data, mediaType } = await readImageDownscaled(file);
          setMaterials(prev => [...prev, {
            id: materialIdCounter++, filename: file.name, kind: 'image',
            data, mediaType,
          }]);
        } else {
          const result = await extractSourceText(file);
          setMaterials(prev => [...prev, {
            id: materialIdCounter++, filename: result.filename, kind: 'text',
            text: result.text, charCount: result.char_count,
            warning: result.warning,
          }]);
        }
      } catch (err: unknown) {
        const e = err as { response?: { data?: { error?: string } } };
        showToast(e.response?.data?.error || `Couldn't read ${file.name}.`);
      }
    }
    setExtracting(false);
  };

  // ── Start extraction ───────────────────────────────────────
  const targetLabels = [
    ...selectedFields.map(f => f.name),
    ...(deckId !== '' ? cardFieldNames : []),
  ];

  const canStart = materials.length > 0 && targetLabels.length > 0 && !extracting;

  const handleStart = async () => {
    systemPromptRef.current = buildSystemPrompt(ctype, archetypes, targetLabels, displayName);

    const totalText = materials.reduce((n, m) => n + (m.text?.length || 0), 0);
    if (totalText > MAX_SOURCE_CHARS) {
      showToast(`This source is over ${Math.round(MAX_SOURCE_CHARS / 1_000_000)} million characters — only the first ${Math.round(MAX_SOURCE_CHARS / 1000)}k could be included. Import it as separate smaller files (e.g. split by chapters).`);
    }
    const units = buildUnits(materials);
    if (!units.length) return;

    setMessagesTracked([]);
    updateProposals(() => []);
    setDisplayMessages([]);
    setStage('chat');
    await runExtraction(units, []);
  };

  /** Extract every part, several at a time. Each part is its own
   *  independent request (system prompt + that part only), so they can
   *  run concurrently; results merge into the running list as they
   *  land. Afterwards the (part, reply) pairs are stitched into one
   *  conversation in book order so refinement chat has full context.
   *  Failed parts are collected for the Resume button. */
  const runExtraction = async (units: ExtractionUnit[], startHistory: LlmMessage[]) => {
    setBusyTracked(true);
    // Local copy — split-on-overflow appends sub-units while workers
    // are still draining the queue.
    const queue = [...units];
    const results: ({ userMsg: LlmMessage; reply: string } | null | undefined)[] = [];
    // Units whose overflowing reply was replaced by two queued halves —
    // not failures, so they don't go to the Resume list.
    const splitAway = new Set<number>();
    let nextIdx = 0;

    // One request with automatic retry: transient failures (an empty
    // reply, a momentary overload, a rate-limit blip) get a second
    // attempt after a pause before the part is declared failed.
    // Returns the userMsg actually sent — mid-import guidance from the
    // user is attached to parts not yet dispatched, and the stitched
    // history must reflect what the model really saw.
    const requestUnit = async (unit: ExtractionUnit) => {
      for (let attempt = 1; ; attempt++) {
        const notes = steeringNotesRef.current;
        const userMsg: LlmMessage = {
          role: 'user',
          content: notes.length
            ? [...unit.parts, {
                type: 'text' as const,
                text: `Guidance the user sent while this import is running — apply it to this part's extraction:\n- ${notes.join('\n- ')}`,
              }]
            : unit.parts,
        };
        try {
          const result = await llmChat({
            feature: 'scribe',
            messages: [...startHistory, userMsg],
            system: systemPromptRef.current,
            max_tokens: 64000,
            // One-shot: this part's content is never re-sent, so don't
            // pay the cache-write surcharge on it. (The stitched
            // conversation used for follow-ups and refinement IS
            // cached — that's where re-reading happens.)
            cache: false,
          });
          return { ...result, userMsg };
        } catch (err: unknown) {
          if (attempt >= UNIT_ATTEMPTS) throw err;
          const e = err as { response?: { data?: { error?: string } } };
          setDisplayMessages(prev => [...prev, {
            role: 'user',
            text: `[${unit.label}] ${e.response?.data?.error || 'The request failed.'} Retrying…`,
          }]);
          await new Promise(resolve => setTimeout(resolve, RETRY_DELAY_MS));
        }
      }
    };

    const worker = async () => {
      while (nextIdx < queue.length) {
        const i = nextIdx++;
        const unit = queue[i];
        setDisplayMessages(prev => [...prev, { role: 'user', text: `Reading ${unit.label}…` }]);
        try {
          const { text: reply, truncated, userMsg } = await requestUnit(unit);
          const { visible, parsed } = splitReply(reply);
          if (parsed) {
            const merged = updateProposals(current =>
              mergeProposals(current, parsed, archetypes, deckCards, true));
            const summary = `${parsed.length} card${parsed.length === 1 ? '' : 's'} (${merged.length} total): ${summarizeCards(parsed)}`;
            setDisplayMessages(prev => [...prev, {
              role: 'assistant',
              text: `[${unit.label}] ${trimProse(visible) ? `${trimProse(visible)}\n— ${summary}` : summary}`,
            }]);
          } else {
            setDisplayMessages(prev => [...prev, {
              role: 'assistant',
              text: `[${unit.label}] ${trimProse(visible || reply)}`,
            }]);
          }
          if (truncated) {
            const subUnits = splitUnit(unit);
            if (subUnits) {
              splitAway.add(i);
              queue.push(...subUnits);
              setDisplayMessages(prev => [...prev, {
                role: 'user',
                text: `[${unit.label}] The reply hit the length limit — re-reading this part in ${subUnits.length} smaller pieces (cards already extracted are kept; complete versions win).`,
              }]);
              continue; // don't stitch the overflowed round into history
            }
            setDisplayMessages(prev => [...prev, {
              role: 'error',
              text: `[${unit.label}] This reply was cut off at the length limit and the part can't be split further — some of its cards may be missing. Ask the model to re-check this part afterwards.`,
            }]);
          }
          results[i] = { userMsg, reply };
        } catch (err: unknown) {
          const e = err as { response?: { data?: { error?: string } } };
          setDisplayMessages(prev => [...prev, {
            role: 'error',
            text: `[${unit.label}] ${e.response?.data?.error || 'The model request failed.'} (retried ${UNIT_ATTEMPTS - 1}×)`,
          }]);
        }
      }
    };

    await Promise.all(
      Array.from({ length: Math.min(CONCURRENT_PARTS, queue.length) }, worker),
    );

    // Stitch successful rounds into one conversation, in book order,
    // so refinement questions can reference any part of the source.
    let history = startHistory;
    const failedUnits: ExtractionUnit[] = [];
    queue.forEach((unit, i) => {
      if (splitAway.has(i)) return;
      const r = results[i];
      if (r) history = [...history, r.userMsg, { role: 'assistant', content: r.reply }];
      else failedUnits.push(unit);
    });
    setMessagesTracked(history);
    setPendingUnits(failedUnits);
    if (failedUnits.length) {
      setDisplayMessages(prev => [...prev, {
        role: 'error',
        text: `${failedUnits.length} part${failedUnits.length === 1 ? '' : 's'} failed — cards already extracted are safe. "Resume extraction" retries just the failed parts.`,
      }]);
    }
    setBusyTracked(false);
    // With every part in, run the automatic follow-ups: complete
    // boundary-straddling cards, then audit field coverage. Both ride
    // the stitched conversation — the only place all parts are visible
    // at once. (After a Resume run finishes the missing parts, these
    // fire then instead.)
    if (!failedUnits.length) {
      const afterRepair = await completeFlaggedCards(history);
      await auditFieldCoverage(afterRepair ?? history);
      // Notes typed during the run steered the remaining parts as they
      // went out; now that the full material is stitched, give them a
      // proper full-context turn. (With failed parts pending, notes
      // stay queued so they also steer the Resume run.)
      await flushQueuedNotes();
    }
  };

  /** Deliver mid-run messages as a real conversation turn once the
   *  workers are quiet. Loops because the user may keep typing while
   *  the flush turn itself is generating. */
  const flushQueuedNotes = async () => {
    while (steeringNotesRef.current.length && !busyRef.current) {
      const notes = steeringNotesRef.current;
      steeringNotesRef.current = [];
      const combined = notes.length === 1
        ? notes[0]
        : `While the import ran, I sent these notes:\n- ${notes.join('\n- ')}`;
      setDisplayMessages(prev => [...prev, {
        role: 'user',
        text: `Following up on the note${notes.length === 1 ? '' : 's'} sent during extraction…`,
      }]);
      await callModel([...messagesRef.current, {
        role: 'user',
        content:
          `${combined}\n\n(Sent while extraction was still running — later parts already saw it as guidance. ` +
          'Now that all material is above, apply anything still needed to the proposals — re-send only ' +
          'changed cards — and answer any questions.)',
      }]);
    }
  };

  /** One-shot follow-up: re-request full content for any card the
   *  model flagged as cut off at a part boundary. Returns the extended
   *  history, or null if there was nothing to repair. */
  const completeFlaggedCards = async (history: LlmMessage[]): Promise<LlmMessage[] | null> => {
    const flagged = proposalsRef.current.filter(p =>
      p.flags?.some(f => INCOMPLETE_FLAG.test(f)));
    if (!flagged.length) return null;
    const names = flagged.map(p => p.card).join(', ');
    setDisplayMessages(prev => [...prev, {
      role: 'user',
      text: `Auto-completing ${flagged.length} card${flagged.length === 1 ? '' : 's'} flagged as cut off: ${names}`,
    }]);
    return callModel([...history, {
      role: 'user',
      content:
        `These cards were flagged as incomplete or cut off at a part boundary: ${names}. ` +
        'All source parts are above in this conversation, and neighbouring parts overlap, ' +
        'so the complete text for each card should be visible across them. Re-send each of ' +
        'these cards with its complete field content assembled from all relevant parts. ' +
        'For every card you resolve, include "flags": [] (or a flag stating what is genuinely ' +
        'missing from the source, if the text truly ends mid-sentence in the book itself).',
    }]);
  };

  /** One-shot follow-up: when some target fields were filled for far
   *  fewer cards than others, ask the model to re-scan for them — the
   *  usual cause is the model economizing on dense parts, or a book
   *  keeping a field's content in its own section (all keywords in an
   *  appendix, say) that got extracted under the wrong name. */
  const auditFieldCoverage = async (history: LlmMessage[]) => {
    const props = proposalsRef.current;
    if (props.length < 5 || targetLabels.length < 2) return;
    const counts = targetLabels.map(label => ({
      label,
      count: props.filter(p =>
        Object.entries(p.fields).some(([k, v]) =>
          k.toLowerCase() === label.toLowerCase() && v?.trim())).length,
    }));
    const maxCount = Math.max(...counts.map(c => c.count));
    if (maxCount === 0) return;
    const sparse = counts.filter(c => c.count < maxCount * 0.5);
    if (!sparse.length) return;
    const description = sparse
      .map(c => `"${c.label}" (${c.count} of ${props.length} cards)`)
      .join(', ');
    setDisplayMessages(prev => [...prev, {
      role: 'user',
      text: `Auto-check: some target fields were rarely filled — ${description}. Asking the model to re-scan the source…`,
    }]);
    await callModel([...history, {
      role: 'user',
      content:
        `Field-coverage check: these target fields were filled for few or no cards: ${description}. ` +
        'Re-scan the source parts above for content belonging to these fields — it may sit in its own ' +
        'section (an appendix of keywords, a separate reversed-meanings chapter) or have been extracted ' +
        'under a different field name. If the source has the content, re-send the affected cards with ' +
        'those fields added, using the exact target field names (only changed cards, as usual). ' +
        'If the source genuinely does not provide this information, say so briefly — never invent content.',
    }]);
  };

  // ── Chat plumbing ──────────────────────────────────────────

  /** One model round-trip: send history, show the reply, merge any
   *  proposals. Returns the new history, or null on failure. */
  const callModel = async (history: LlmMessage[]): Promise<LlmMessage[] | null> => {
    setBusyTracked(true);
    try {
      const { text: reply, truncated } = await llmChat({
        feature: 'scribe',
        messages: history,
        system: systemPromptRef.current,
        max_tokens: 64000,
      });
      const { visible, parsed } = splitReply(reply);
      const newHistory: LlmMessage[] = [...history, { role: 'assistant', content: reply }];
      setMessagesTracked(newHistory);
      if (parsed) {
        const merged = updateProposals(current =>
          mergeProposals(current, parsed, archetypes, deckCards));
        const summary = `Updated ${parsed.length} card${parsed.length === 1 ? '' : 's'} (${merged.length} total): ${summarizeCards(parsed)}`;
        setDisplayMessages(prev => [...prev, {
          role: 'assistant',
          text: visible ? `${visible}\n— ${summary}` : summary,
        }]);
      } else {
        setDisplayMessages(prev => [...prev, { role: 'assistant', text: visible || reply }]);
      }
      if (truncated) {
        setDisplayMessages(prev => [...prev, {
          role: 'error',
          text: 'This reply was cut off at the length limit, so some cards from this part may be missing. Once extraction finishes, ask the model to re-check this part.',
        }]);
      }
      return newHistory;
    } catch (err: unknown) {
      const e = err as { response?: { data?: { error?: string } } };
      setDisplayMessages(prev => [...prev, {
        role: 'error',
        text: e.response?.data?.error || 'The model request failed. You can try sending again.',
      }]);
      return null;
    } finally {
      setBusyTracked(false);
    }
  };

  const handleSend = async () => {
    const text = chatInput.trim();
    if (!text) return;
    setChatInput('');
    if (busyRef.current) {
      // Model's mid-work: queue it. It steers parts not yet sent and
      // gets a full-context reply when the current work finishes.
      steeringNotesRef.current = [...steeringNotesRef.current, text];
      setDisplayMessages(prev => [...prev,
        { role: 'user', text },
        { role: 'note', text: 'Noted — this will guide the remaining parts and get a reply when the current work finishes.' },
      ]);
      return;
    }
    setDisplayMessages(prev => [...prev, { role: 'user', text }]);
    await callModel([...messagesRef.current, { role: 'user', content: text }]);
    // Anything typed while that reply generated gets its turn now.
    await flushQueuedNotes();
  };

  // ── Apply ──────────────────────────────────────────────────
  // Only writable rows count — a checked row with no reachable target
  // must not inflate the Apply button's promise.
  const checkedProposals = proposals.filter(p => p.checked && isWritable(p));
  const fieldByName = useMemo(() => {
    const map = new Map<string, SourceField>();
    for (const f of selectedFields) map.set(f.name.toLowerCase(), f);
    return map;
  }, [selectedFields]);

  const handleApply = async () => {
    const writes: ScribeWrite[] = [];
    // Everything skipped is surfaced with its actual reason — never silent.
    const unknownLabels = new Set<string>();
    const cardsWithoutDeckCard = new Set<string>();
    for (const p of checkedProposals) {
      for (const [label, content] of Object.entries(p.fields)) {
        if (!content?.trim()) continue;
        const sourceField = fieldByName.get(label.toLowerCase());
        const isCardField = cardFieldNames.some(n => n.toLowerCase() === label.toLowerCase());
        if (sourceField && p.archetypeId) {
          writes.push({
            target: 'archetype',
            archetype_id: p.archetypeId,
            field_id: sourceField.id,
            content,
          });
        } else if (isCardField && p.cardId) {
          writes.push({
            target: 'card',
            card_id: p.cardId,
            field_name: label,
            content,
          });
        } else if (isCardField && !p.cardId) {
          cardsWithoutDeckCard.add(p.card);
        } else if (!sourceField) {
          unknownLabels.add(label);
        }
      }
    }
    if (unknownLabels.size) {
      showToast(
        `Heads up: ${[...unknownLabels].map(l => `"${l}"`).join(', ')} ` +
        `${unknownLabels.size === 1 ? 'is' : 'are'} not among your target fields and won't be written. ` +
        'Ask the model to move that content into a target field, or add it as a field first.',
      );
    }
    if (cardsWithoutDeckCard.size) {
      showToast(
        `${[...cardsWithoutDeckCard].join(', ')}: no matching card in the deck, so their ` +
        'card fields can\'t be written. Use "Assign to card…" on those rows first.',
      );
    }
    if (!writes.length) {
      showToast('Nothing to apply — the checked cards have no writable fields.');
      return;
    }
    setApplying(true);
    try {
      const result = await applyScribeWrites(writes);
      queryClient.invalidateQueries({ queryKey: ['archetype-source-entries'] });
      queryClient.invalidateQueries({ queryKey: ['source-entries'] });
      queryClient.invalidateQueries({ queryKey: ['cards'] });
      queryClient.invalidateQueries({ queryKey: ['deck-custom-fields'] });
      if (result.errors.length) {
        showToast(`Applied ${result.applied} of ${writes.length} — ${result.errors.length} failed.`);
      } else {
        showToast(`Imported ${result.applied} entries from ${displayName}.`, 'success');
        onClose();
      }
    } catch {
      showToast('Failed to apply the import.');
    } finally {
      setApplying(false);
    }
  };

  const dirty = stage === 'chat' && proposals.length > 0;

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={`Import with AI — ${displayName}`}
      width={stage === 'chat' ? 1100 : 640}
      isDirty={dirty}
      confirmMessage="Close the import? Unapplied proposals will be lost."
    >
      {llmConfig && !llmConfig.model && (
        <p className="scribe__warning">
          No AI model is configured yet — set one up in Settings → AI Assistant first.
        </p>
      )}

      {stage === 'setup' && (
        <div className="scribe__setup">
          {availableTypes.length > 1 && (
            <div className="scribe__field">
              <label>Cartomancy type</label>
              <select value={ctype} onChange={e => setCtype(e.target.value)}>
                {availableTypes.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
          )}

          {source && (
          <div className="scribe__field">
            <label>Fill these {source.name} fields ({ctype})</label>
            {fields.length === 0 && (
              <p className="scribe__hint">
                This source has no {ctype} fields yet — add them in the source's
                field list first, or target only deck card fields below.
              </p>
            )}
            {fields.map(f => {
              const filled = fieldCoverage.get(f.id) ?? 0;
              const total = archetypes.length;
              return (
                <label key={f.id} className="scribe__check">
                  <input
                    type="checkbox"
                    checked={selectedFieldIds.includes(f.id)}
                    onChange={e => setSelectedFieldIds(prev =>
                      e.target.checked ? [...prev, f.id] : prev.filter(id => id !== f.id))}
                  />
                  {f.name}
                  <span className={`scribe__coverage ${filled >= total && total > 0 ? 'scribe__coverage--full' : ''}`}>
                    {total > 0
                      ? filled === 0 ? '(empty)' : `(${filled} of ${total} filled)`
                      : ''}
                  </span>
                </label>
              );
            })}
            {fields.length > 1 && fieldsWithGaps.length > 0 && fieldsWithGaps.length < fields.length && (
              <button
                className="scribe__gaps-btn"
                onClick={() => setSelectedFieldIds(fieldsWithGaps.map(f => f.id))}
              >
                Select only fields with gaps ({fieldsWithGaps.length})
              </button>
            )}
          </div>
          )}

          <div className="scribe__field">
            {deck ? (
              <label>Fill card fields on {deck.name} ({ctype})</label>
            ) : (
              <>
                <label>Also fill card fields on a deck (optional)</label>
                <select
                  value={deckId}
                  onChange={e => setDeckId(e.target.value ? Number(e.target.value) : '')}
                >
                  <option value="">No deck — reference fields only</option>
                  {decksForType.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
                </select>
              </>
            )}
            {deckId !== '' && (
              <>
                {deckFieldDefs.map(f => (
                  <label key={f.id} className="scribe__check">
                    <input
                      type="checkbox"
                      checked={selectedCardFields.some(n => n.toLowerCase() === f.field_name.toLowerCase())}
                      onChange={e => setSelectedCardFields(prev =>
                        e.target.checked
                          ? [...prev, f.field_name]
                          : prev.filter(n => n.toLowerCase() !== f.field_name.toLowerCase()))}
                    />
                    {f.field_name}
                  </label>
                ))}
                <input
                  type="text"
                  placeholder={deckFieldDefs.length
                    ? 'Additional new field names, comma-separated'
                    : 'Card field names, comma-separated (e.g. Keywords, Book Meaning)'}
                  value={cardFieldsText}
                  onChange={e => setCardFieldsText(e.target.value)}
                />
                <p className="scribe__hint">
                  These become custom fields on each card of the deck,
                  matched to cards through their archetypes.
                  {deck && !cardFieldNames.length && ' Pick at least one field (or type a new one) to import into.'}
                </p>
              </>
            )}
          </div>

          <div className="scribe__field">
            <label>Source material</label>
            <div className="scribe__materials">
              {materials.map(m => (
                <div key={m.id} className="scribe__material">
                  <span className="scribe__material-name">
                    {m.kind === 'image' ? '🖼 ' : '📄 '}{m.filename}
                  </span>
                  {m.charCount != null && (
                    <span className="scribe__material-meta">
                      {Math.round(m.charCount / 1000)}k characters
                    </span>
                  )}
                  <button
                    className="scribe__material-remove"
                    onClick={() => setMaterials(prev => prev.filter(x => x.id !== m.id))}
                    aria-label={`Remove ${m.filename}`}
                  >×</button>
                  {m.warning && <div className="scribe__warning">{m.warning}</div>}
                </div>
              ))}
            </div>
            <label className="scribe__file-btn">
              {extracting ? 'Reading…' : '+ Add files'}
              <input
                type="file"
                multiple
                accept=".epub,.pdf,.mobi,.azw,.azw3,.txt,.md,.html,.htm,image/*"
                onChange={e => { handleAddFiles(e.target.files); e.target.value = ''; }}
                disabled={extracting}
                hidden
              />
            </label>
            <p className="scribe__hint">
              Books: EPUB, PDF, MOBI/AZW, or plain text. Photos of book
              pages work too (needs a vision-capable model).
              {totalChars > 0 && ` Loaded ${Math.round(totalChars / 1000)}k characters.`}
            </p>
          </div>

          <div className="scribe__actions">
            <button className="primary" onClick={handleStart} disabled={!canStart || !llmConfig?.model}>
              Start extraction
            </button>
            <ModalCancelButton>Cancel</ModalCancelButton>
          </div>
        </div>
      )}

      {stage === 'chat' && (
        <div className="scribe__workspace">
          <div className="scribe__chat">
            <div className="scribe__chat-log">
              {displayMessages.map((m, i) => (
                <div key={i} className={`scribe__msg scribe__msg--${m.role}`}>
                  {m.text}
                </div>
              ))}
              {busy && <div className="scribe__msg scribe__msg--assistant scribe__msg--busy">Working…</div>}
              {pendingUnits.length > 0 && !busy && (
                <button
                  className="scribe__resume"
                  onClick={() => runExtraction(pendingUnits, messages)}
                >
                  Resume extraction ({pendingUnits.length} part{pendingUnits.length === 1 ? '' : 's'} left)
                </button>
              )}
              <div ref={chatEndRef} />
            </div>
            <div className="scribe__chat-input">
              <textarea
                value={chatInput}
                placeholder={busy
                  ? 'Still working — messages sent now will guide the remaining parts…'
                  : 'Ask for corrections or changes… (Enter to send, Shift+Enter for a new line)'}
                onChange={e => setChatInput(e.target.value)}
                onKeyDown={e => {
                  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
                }}
                rows={2}
              />
              <button onClick={handleSend} disabled={!chatInput.trim()}>Send</button>
            </div>
          </div>

          <div className="scribe__review">
            <div className="scribe__review-head">
              <strong>{proposals.length} card{proposals.length === 1 ? '' : 's'} proposed</strong>
              {proposals.length > 0 && (
                <span className="scribe__review-bulk">
                  <button onClick={() => updateProposals(p => p.map(x => ({ ...x, checked: true })))}>All</button>
                  <button onClick={() => updateProposals(p => p.map(x => ({ ...x, checked: false })))}>None</button>
                </span>
              )}
            </div>
            <div className="scribe__review-list">
              {proposals.length === 0 && !busy && (
                <p className="scribe__hint">
                  Proposals will appear here once the model has read the material.
                </p>
              )}
              {proposals.map((p, i) => (
                <ProposalRow
                  key={`${p.card}-${i}`}
                  proposal={p}
                  selectedFields={selectedFields}
                  cardFieldNames={deckId !== '' ? cardFieldNames : []}
                  existingKeys={existingKeys}
                  writable={isWritable(p)}
                  // Assigning goes through whatever this session can
                  // write to: archetypes when reference fields are
                  // targeted, otherwise the deck's actual cards.
                  assignOptions={hasArchetypeTargets
                    ? archetypes.map(a => ({ id: a.id, label: a.name }))
                    : deckCards.map(c => ({ id: c.id, label: c.name }))}
                  resolvedName={
                    archetypes.find(a => a.id === p.archetypeId)?.name
                    ?? deckCards.find(c => c.id === p.cardId)?.name}
                  onToggle={() => updateProposals(prev =>
                    prev.map((x, j) => j === i ? { ...x, checked: !x.checked } : x))}
                  onAssign={(id) => {
                    if (hasArchetypeTargets) {
                      const arch = archetypes.find(a => a.id === id);
                      const key = (arch?.name || '').toLowerCase();
                      const card = deckCards.find(c =>
                        (c.archetype || '').toLowerCase() === key || c.name.toLowerCase() === key);
                      updateProposals(prev => prev.map((x, j) => j === i
                        ? { ...x, archetypeId: id, cardId: card?.id ?? x.cardId, checked: true }
                        : x));
                    } else {
                      const card = deckCards.find(c => c.id === id);
                      const key = (card?.archetype || card?.name || '').toLowerCase();
                      const archetypeId = archetypes.find(a => a.name.toLowerCase() === key)?.id;
                      updateProposals(prev => prev.map((x, j) => j === i
                        ? { ...x, cardId: id, archetypeId: archetypeId ?? x.archetypeId, checked: true }
                        : x));
                    }
                  }}
                  onEditField={(label, value) => updateProposals(prev =>
                    prev.map((x, j) => j === i
                      ? { ...x, fields: { ...x.fields, [label]: value } }
                      : x))}
                />
              ))}
            </div>
            <div className="scribe__actions">
              <button
                className="primary"
                onClick={handleApply}
                disabled={applying || checkedProposals.length === 0}
              >
                {applying ? 'Applying…' : `Apply ${checkedProposals.length} card${checkedProposals.length === 1 ? '' : 's'}`}
              </button>
              <button onClick={() => setStage('setup')} disabled={busy}>Back to setup</button>
              <ModalCancelButton>Close</ModalCancelButton>
            </div>
          </div>
        </div>
      )}
    </Modal>
  );
}

// ── One proposal row ─────────────────────────────────────────

function ProposalRow({
  proposal, selectedFields, cardFieldNames, existingKeys, writable,
  assignOptions, resolvedName, onToggle, onAssign, onEditField,
}: {
  proposal: Proposal;
  selectedFields: SourceField[];
  cardFieldNames: string[];
  existingKeys: Set<string>;
  /** Whether this row can reach at least one write target as-is. */
  writable: boolean;
  /** What "Assign to card…" offers: archetypes when reference fields
   *  are targeted, the deck's cards in a deck-only import. */
  assignOptions: { id: number; label: string }[];
  /** The app card/archetype this row resolved to, when it differs
   *  from the name the book used. */
  resolvedName?: string;
  onToggle: () => void;
  onAssign: (id: number) => void;
  onEditField: (label: string, value: string) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const [editingField, setEditingField] = useState<string | null>(null);
  const [draft, setDraft] = useState('');
  const p = proposal;
  const unmatched = !writable;

  const overwrites = selectedFields.some(f =>
    p.archetypeId &&
    p.fields[f.name] != null &&
    existingKeys.has(`${p.archetypeId}:${f.id}`));

  return (
    <div className={`scribe__proposal ${unmatched ? 'scribe__proposal--unmatched' : ''}`}>
      <div className="scribe__proposal-head">
        <label>
          <input type="checkbox" checked={p.checked} onChange={onToggle} disabled={unmatched} />
          <strong>{p.card}</strong>
        </label>
        {resolvedName && resolvedName.toLowerCase() !== p.card.toLowerCase() && (
          <span className="scribe__resolved">→ {resolvedName}</span>
        )}
        {unmatched && (
          <>
            <span className="scribe__badge scribe__badge--warn">
              {p.archetypeId || p.cardId ? 'no card on this deck' : 'no matching card'}
            </span>
            <select
              className="scribe__assign"
              value=""
              onChange={e => { if (e.target.value) onAssign(Number(e.target.value)); }}
              title="Pick which of the app's cards this proposal belongs to"
            >
              <option value="">Assign to card…</option>
              {assignOptions.map(o => (
                <option key={o.id} value={o.id}>{o.label}</option>
              ))}
            </select>
          </>
        )}
        {overwrites && <span className="scribe__badge">overwrites existing</span>}
        {(p.flags || []).map((f, i) => (
          <span key={i} className="scribe__badge scribe__badge--flag">{f}</span>
        ))}
        <button className="scribe__expand" onClick={() => setExpanded(e => !e)}>
          {expanded ? 'Hide' : 'Show'}
        </button>
      </div>
      {expanded && (
        <div className="scribe__proposal-fields">
          {Object.entries(p.fields).map(([label, content]) => (
            <div key={label} className="scribe__proposal-field">
              <span className="scribe__proposal-field-name">
                {label}
                {cardFieldNames.some(n => n.toLowerCase() === label.toLowerCase()) && ' (card field)'}
                {!selectedFields.some(f => f.name.toLowerCase() === label.toLowerCase()) &&
                  !cardFieldNames.some(n => n.toLowerCase() === label.toLowerCase()) && (
                  <span className="scribe__badge scribe__badge--warn">
                    not a target field — won't be applied
                  </span>
                )}
                {editingField !== label && (
                  <button
                    className="scribe__field-edit-btn"
                    onClick={() => { setEditingField(label); setDraft(content); }}
                  >
                    Edit
                  </button>
                )}
              </span>
              {editingField === label ? (
                <div className="scribe__field-edit">
                  <textarea
                    value={draft}
                    onChange={e => setDraft(e.target.value)}
                    rows={Math.min(12, Math.max(4, draft.split('\n').length + 1))}
                    autoFocus
                  />
                  <div className="scribe__field-edit-actions">
                    <button
                      className="primary"
                      onClick={() => { onEditField(label, draft); setEditingField(null); }}
                    >
                      Save
                    </button>
                    <button onClick={() => setEditingField(null)}>Cancel</button>
                  </div>
                </div>
              ) : (
                <div className="scribe__proposal-field-text">{content}</div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Prompt + parsing helpers ─────────────────────────────────

function buildSystemPrompt(
  ctype: string,
  archetypes: Archetype[],
  targetLabels: string[],
  sourceName: string,
): string {
  const names = archetypes.map(a => a.name).join(', ');
  return `You are the Scribe, an assistant inside a personal tarot/cartomancy journal app. Your job is to transcribe card meanings and related content from source material (book text or photographed pages) into structured per-card fields. You transcribe and organize — you never invent card meanings.

Cartomancy type: ${ctype}
Source being imported: ${sourceName}
The app's ${ctype} card archetypes are: ${names}

Target fields to fill for each card: ${targetLabels.map(l => `"${l}"`).join(', ')}
Use these field names exactly, character for character — the app matches them literally and silently discards anything else.

How to respond — these rules are strict, the app parses your output:
- Extracted card content goes ONLY inside a fenced code block tagged json. NEVER put card meanings, keywords, or field content in the prose part of your reply — the app cannot read prose, and content outside the JSON block is lost.
- The source material arrives in one or more parts, each in its own message. When a part arrives, immediately extract the card content found in THAT part — no confirmation or clarification questions first.
- The app keeps a running list of proposals and MERGES each JSON block you send into it. So each block contains ONLY the cards you are adding or changing in this reply — never re-send cards that haven't changed. One block per reply, in this exact shape:
\`\`\`json
{"proposals": [{"card": "<archetype name>", "fields": {"<field name>": "<content>"}, "flags": ["<optional short notes>"]}]}
\`\`\`
- Use the app's archetype names exactly as listed above whenever you are confident of the match (books often use variant names or other languages). If you cannot match a card confidently, keep the source's name and add a flag explaining the uncertainty.
- For every card, fill EVERY target field the source provides content for — never skip secondary fields (keywords, reversed meanings, correspondences) to save space, even in dense parts. If the source truly has no content for a field on a card, simply omit that field; never invent content to fill one.
- Parts overlap, so a card whose text is cut off at the end of one part usually appears complete in another; always extract the complete version you can see. If a card's text still looks cut off, extract what's there and add a flag containing the words "cut off" — the app uses that flag to request completion automatically.
- Field content must be faithful to the source text — do not summarize, paraphrase, or embellish. Light cleanup is encouraged: fix obvious OCR artifacts (garbled characters, broken headers, stray symbols like ¥), merge hyphenated line breaks, and remove accidentally duplicated passages, but note significant repairs in flags.
- If a part contains no card content (front matter, essays, spreads), say so in one sentence — no JSON block needed.
- Outside the JSON block, reply conversationally and BRIEFLY — a few short sentences at most: what you found, what's uncertain or missing, answers to the user's questions. NEVER quote card text or extended source passages in prose; that content belongs only in the JSON block, and prose is never saved anywhere.
- When the user requests changes, emit only the affected cards (each with all of its fields, not just the changed one) in the JSON block.`;
}

type RawProposal = { card: string; fields: Record<string, string>; flags?: string[] };

/** Extraction-phase prose should be a short status note. When the
 *  model rambles (or quotes book text despite instructions), trim the
 *  chat display — the content that matters is in the review panel,
 *  and nothing in the chat is ever written to the database. */
function trimProse(text: string, max = 700): string {
  if (text.length <= max) return text;
  return text.slice(0, max).trimEnd() +
    `\n\n[…trimmed ${text.length - max} characters of extra prose. Extracted card content lives in the review panel on the right — if something you saw here is missing from a card there, ask the model to re-send that card.]`;
}

/** "The Fool, The Magician, … (+12 more)" — every chat round names the
 *  cards it touched, so anything odd is traceable to specific rows. */
function summarizeCards(cards: { card: string }[], max = 12): string {
  const names = cards.map(c => c.card);
  if (names.length <= max) return names.join(', ');
  return `${names.slice(0, max).join(', ')} (+${names.length - max} more)`;
}

/** Split a model reply into visible prose and the parsed proposals.
 *
 *  Deliberately forgiving about the block format: models sometimes tag
 *  the fence differently (```JSON, bare ```), skip the fence entirely,
 *  or get cut off at the reply-length limit mid-JSON. A truncated
 *  proposals array is salvaged up to its last complete card so a long
 *  extraction degrades to "most cards + a warning" instead of nothing. */
function splitReply(reply: string): { visible: string; parsed: RawProposal[] | null } {
  const candidates: string[] = [];
  // Closed fences, any tag casing, last one wins
  for (const m of reply.matchAll(/```[a-zA-Z]*\s*([\s\S]*?)```/g)) {
    if (m[1].includes('"proposals"')) candidates.push(m[1]);
  }
  // Unterminated final fence (typical of a truncated reply)
  if (!candidates.length) {
    const open = reply.match(/```[a-zA-Z]*\s*([\s\S]*)$/);
    if (open && open[1].includes('"proposals"')) candidates.push(open[1]);
  }
  // No fence at all — bare JSON object somewhere in the reply
  if (!candidates.length) {
    const idx = reply.search(/\{\s*"proposals"/);
    if (idx !== -1) candidates.push(reply.slice(idx));
  }

  let parsed: RawProposal[] | null = null;
  for (let i = candidates.length - 1; i >= 0 && !parsed; i--) {
    parsed = parseProposals(candidates[i]);
  }

  // Prose = the reply minus fenced blocks (terminated or not) and any
  // bare proposals JSON we managed to parse.
  let visible = reply.replace(/```[\s\S]*?(```|$)/g, '');
  if (parsed) visible = visible.replace(/\{\s*"proposals"[\s\S]*$/, '');
  visible = visible.replace(/\n{3,}/g, '\n\n').trim();
  return { visible, parsed };
}

/** Parse a proposals JSON string; on failure, salvage every complete
 *  card object from a truncated array. */
function parseProposals(jsonText: string): RawProposal[] | null {
  try {
    const obj = JSON.parse(jsonText);
    if (Array.isArray(obj?.proposals)) return obj.proposals;
    return null;
  } catch { /* fall through to salvage */ }

  const keyIdx = jsonText.indexOf('"proposals"');
  if (keyIdx === -1) return null;
  const arrStart = jsonText.indexOf('[', keyIdx);
  if (arrStart === -1) return null;

  // Walk the array tracking strings/escapes/nesting; remember where
  // each complete top-level object ends, then rebuild a closed array.
  let depth = 0;
  let inString = false;
  let escaped = false;
  let lastComplete = -1;
  for (let i = arrStart; i < jsonText.length; i++) {
    const ch = jsonText[i];
    if (escaped) { escaped = false; continue; }
    if (inString) {
      if (ch === '\\') escaped = true;
      else if (ch === '"') inString = false;
      continue;
    }
    if (ch === '"') inString = true;
    else if (ch === '{' || ch === '[') depth++;
    else if (ch === '}' || ch === ']') {
      depth--;
      if (depth === 1) lastComplete = i; // back at array level: object done
      if (depth === 0) break;            // array itself closed
    }
  }
  if (lastComplete === -1) return null;
  try {
    const arr = JSON.parse(jsonText.slice(arrStart, lastComplete + 1) + ']');
    return Array.isArray(arr) && arr.length ? arr : null;
  } catch {
    return null;
  }
}

/** Merge a JSON block's cards into the running proposal list.
 *
 *  Keyed by card name (case-insensitive): a re-sent card updates its
 *  existing row field-by-field and keeps its checkbox state; a new
 *  card is appended. Nothing is ever dropped — the model only sends
 *  additions and changes, never the full set.
 *
 *  preferLonger is used during extraction, where overlapping parts can
 *  finish in any order: a complete version of a boundary-straddling
 *  card must not be clobbered by the cut-off version arriving later.
 *  Refinement merges leave it off so "shorten this field" works. */
function mergeProposals(
  previous: Proposal[],
  incoming: RawProposal[],
  archetypes: Archetype[],
  deckCards: Card[],
  preferLonger = false,
): Proposal[] {
  const archByName = new Map(archetypes.map(a => [a.name.toLowerCase(), a.id]));
  const result = [...previous];
  const indexByKey = new Map(result.map((p, i) => [p.card.toLowerCase(), i] as const));

  for (const raw of incoming) {
    if (!raw || typeof raw.card !== 'string' || !raw.fields || typeof raw.fields !== 'object') continue;
    const key = raw.card.toLowerCase();
    const archetypeId = archByName.get(key);
    const card = deckCards.find(c =>
      (c.archetype || '').toLowerCase() === key || c.name.toLowerCase() === key);
    const fields = Object.fromEntries(
      Object.entries(raw.fields).filter(([, v]) => typeof v === 'string')) as Record<string, string>;
    const flags = Array.isArray(raw.flags) ? raw.flags.filter(f => typeof f === 'string') : undefined;

    const existingIdx = indexByKey.get(key);
    if (existingIdx != null) {
      const existing = result[existingIdx];
      const mergedFields = { ...existing.fields };
      let accepted = 0;
      for (const [k, v] of Object.entries(fields)) {
        const current = mergedFields[k];
        if (preferLonger && typeof current === 'string' && current.length > v.length) continue;
        mergedFields[k] = v;
        accepted++;
      }
      // Flags follow the content decision. When this round's version
      // of the card won (or it's a refinement), its flags replace the
      // old ones — including replacing them with nothing, so a card
      // completed by a later part sheds its stale "cut off" flag. A
      // losing fragment's flags never overwrite the winner's.
      const nextFlags = (!preferLonger || accepted > 0) ? flags : existing.flags;
      result[existingIdx] = {
        ...existing,
        fields: mergedFields,
        flags: nextFlags?.length ? nextFlags : undefined,
        archetypeId: existing.archetypeId ?? archetypeId,
        cardId: existing.cardId ?? card?.id,
      };
    } else {
      result.push({
        card: raw.card,
        fields,
        flags,
        archetypeId,
        cardId: card?.id,
        checked: archetypeId != null || card != null,
      });
      indexByKey.set(key, result.length - 1);
    }
  }
  return result;
}

function makeTextUnit(label: string, text: string): ExtractionUnit {
  return {
    label,
    text,
    parts: [{
      type: 'text',
      text: `Source material — ${label}. Extract the card content found in this part now:\n\n${text}`,
    }],
  };
}

function makeImageUnit(label: string, group: Material[]): ExtractionUnit {
  return {
    label,
    images: group,
    parts: [
      {
        type: 'text',
        text: `Source material — ${label}. Extract the card content found in these page photos now:`,
      },
      ...group.map(m => ({
        type: 'image' as const,
        media_type: m.mediaType,
        data: m.data,
      })),
    ],
  };
}

/** Cut the source material into extraction units: text files split at
 *  paragraph boundaries into CHUNK_CHARS pieces, photos in groups. */
function buildUnits(materials: Material[]): ExtractionUnit[] {
  const units: ExtractionUnit[] = [];
  let used = 0;
  for (const m of materials) {
    if (m.kind !== 'text' || !m.text) continue;
    let text = m.text;
    if (used + text.length > MAX_SOURCE_CHARS) {
      text = text.slice(0, Math.max(0, MAX_SOURCE_CHARS - used));
    }
    used += text.length;
    if (!text) continue;
    const chunks = splitIntoChunks(text);
    chunks.forEach((chunk, i) => {
      const label = chunks.length > 1
        ? `${m.filename} (part ${i + 1} of ${chunks.length})`
        : m.filename;
      units.push(makeTextUnit(label, chunk));
    });
  }
  const images = materials.filter(m => m.kind === 'image' && m.data);
  for (let i = 0; i < images.length; i += IMAGES_PER_UNIT) {
    const group = images.slice(i, i + IMAGES_PER_UNIT);
    const label = images.length > IMAGES_PER_UNIT
      ? `photos ${i + 1}–${i + group.length} of ${images.length}`
      : `${group.length} photo${group.length === 1 ? '' : 's'}`;
    units.push(makeImageUnit(label, group));
  }
  return units;
}

/** Halve a unit whose reply overflowed the output limit, so each half
 *  yields a reply that fits. Returns null when it can't be split
 *  smaller (tiny text, single photo). */
function splitUnit(unit: ExtractionUnit): ExtractionUnit[] | null {
  if (unit.text && unit.text.length > 20_000) {
    const halves = splitIntoChunks(
      unit.text, Math.ceil(unit.text.length / 2) + CHUNK_OVERLAP);
    if (halves.length < 2) return null;
    return halves.map((h, i) =>
      makeTextUnit(`${unit.label} · piece ${i + 1} of ${halves.length}`, h));
  }
  if (unit.images && unit.images.length > 1) {
    const mid = Math.ceil(unit.images.length / 2);
    return [unit.images.slice(0, mid), unit.images.slice(mid)].map((g, i) =>
      makeImageUnit(`${unit.label} · piece ${i + 1} of 2`, g));
  }
  return null;
}

function splitIntoChunks(text: string, max = CHUNK_CHARS): string[] {
  if (text.length <= max) return [text];
  const chunks: string[] = [];
  let pos = 0;
  for (;;) {
    let end = Math.min(pos + max, text.length);
    if (end < text.length) {
      // Prefer breaking at a paragraph gap so cards aren't split
      // mid-sentence more than necessary.
      const gap = text.lastIndexOf('\n\n', end);
      if (gap > pos + max * 0.5) end = gap;
    }
    chunks.push(text.slice(pos, end));
    if (end >= text.length) break;
    // Step back so the next chunk re-covers the boundary region.
    pos = Math.max(end - CHUNK_OVERLAP, pos + 1);
  }
  return chunks;
}

// ── Image reading (downscale in-browser) ─────────────────────

async function readImageDownscaled(file: File): Promise<{ data: string; mediaType: string }> {
  const url = URL.createObjectURL(file);
  try {
    const img = await new Promise<HTMLImageElement>((resolve, reject) => {
      const el = new Image();
      el.onload = () => resolve(el);
      el.onerror = () => reject(new Error('unreadable image'));
      el.src = url;
    });
    const scale = Math.min(1, IMAGE_MAX_EDGE / Math.max(img.width, img.height));
    if (scale === 1 && (file.type === 'image/jpeg' || file.type === 'image/png')) {
      const data = await fileToBase64(file);
      return { data, mediaType: file.type };
    }
    const canvas = document.createElement('canvas');
    canvas.width = Math.round(img.width * scale);
    canvas.height = Math.round(img.height * scale);
    canvas.getContext('2d')!.drawImage(img, 0, 0, canvas.width, canvas.height);
    const dataUrl = canvas.toDataURL('image/jpeg', 0.85);
    return { data: dataUrl.split(',')[1], mediaType: 'image/jpeg' };
  } finally {
    URL.revokeObjectURL(url);
  }
}

function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve((reader.result as string).split(',')[1]);
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
}
