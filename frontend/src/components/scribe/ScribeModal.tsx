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
import { getDecks } from '../../api/decks';
import { getCards } from '../../api/cards';
import { extractSourceText, applyScribeWrites, type ScribeWrite } from '../../api/scribe';
import { llmChat, getLlmConfig, type LlmMessage, type LlmMessagePart } from '../../api/llm';
import type { ReferenceSource, SourceField, Card, Deck } from '../../types';
import './ScribeModal.css';

interface ScribeModalProps {
  source: ReferenceSource;
  open: boolean;
  onClose: () => void;
}

/** One extraction request: a chunk of book text, or a group of page
 *  photos. Each unit is sent as its own message in the conversation. */
interface ExtractionUnit {
  label: string;
  parts: LlmMessagePart[];
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

// Keep prompts under control: ~200k tokens of book text is plenty for
// one import session and stays inside big-model context windows.
const MAX_SOURCE_CHARS = 800_000;
// The APP drives batching, not the model: long books are cut into
// parts of this size and each part is one small, fast request. Replies
// stay far below output limits and timeouts no matter the book length.
const CHUNK_CHARS = 120_000;
const IMAGES_PER_UNIT = 8;
// Parts are independent, so several can extract at once — wall-clock
// time divides accordingly. Kept modest to stay under API rate limits.
const CONCURRENT_PARTS = 3;
// Chunks overlap so a card cut at one part's end appears whole at the
// next part's start; the merge keeps whichever version is longer.
const CHUNK_OVERLAP = 3_000;
// Downscale photos so a stack of LWB pages doesn't blow request limits.
const IMAGE_MAX_EDGE = 2000;

let materialIdCounter = 1;

export default function ScribeModal({ source, open, onClose }: ScribeModalProps) {
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  // ── Setup state ────────────────────────────────────────────
  const [ctype, setCtype] = useState(source.cartomancy_types[0] || 'Tarot');
  const [selectedFieldIds, setSelectedFieldIds] = useState<number[]>([]);
  const [deckId, setDeckId] = useState<number | ''>('');
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
  // Mirror of `proposals` that async loops can read without stale
  // closures (several merges can land within one render cycle).
  const proposalsRef = useRef<Proposal[]>([]);
  const chatEndRef = useRef<HTMLDivElement>(null);

  const { data: llmConfig } = useQuery({ queryKey: ['llm-config'], queryFn: getLlmConfig, enabled: open });
  const { data: fields = [] } = useQuery<SourceField[]>({
    queryKey: ['source-fields', source.id, ctype],
    queryFn: () => getSourceFields(source.id, ctype),
    enabled: open,
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
    queryKey: ['source-entries', source.id, ctype],
    queryFn: () => getSourceEntries(source.id, ctype),
    enabled: open,
  });

  // Default: all source fields selected
  useEffect(() => {
    setSelectedFieldIds(fields.map(f => f.id));
  }, [fields]);

  // Reset everything when the modal opens fresh
  useEffect(() => {
    if (!open) return;
    setStage('setup');
    setMaterials([]);
    setMessages([]);
    setDisplayMessages([]);
    setProposals([]);
    proposalsRef.current = [];
    setPendingUnits([]);
    setChatInput('');
    setCtype(source.cartomancy_types[0] || 'Tarot');
    setDeckId('');
    setCardFieldsText('');
  }, [open, source.id, source.cartomancy_types]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [displayMessages, busy]);

  const decksForType = useMemo(
    () => decks.filter(d => (d.cartomancy_types || []).some(t => t.name === ctype)),
    [decks, ctype],
  );

  const cardFieldNames = useMemo(
    () => cardFieldsText.split(/[,;\n]/).map(s => s.trim()).filter(Boolean),
    [cardFieldsText],
  );

  const selectedFields = fields.filter(f => selectedFieldIds.includes(f.id));
  const totalChars = materials.reduce((n, m) => n + (m.charCount || 0), 0);

  // Existing archetype content, for overwrite badges: "archetypeId:fieldId"
  const existingKeys = useMemo(() => {
    const set = new Set<string>();
    for (const e of existingEntries) set.add(`${e.archetype_id}:${e.field_id}`);
    return set;
  }, [existingEntries]);

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
    systemPromptRef.current = buildSystemPrompt(ctype, archetypes, targetLabels, source.name);

    const totalText = materials.reduce((n, m) => n + (m.text?.length || 0), 0);
    if (totalText > MAX_SOURCE_CHARS) {
      showToast('The source text was very long and was truncated — consider importing in smaller pieces.');
    }
    const units = buildUnits(materials);
    if (!units.length) return;

    setMessages([]);
    setProposals([]);
    proposalsRef.current = [];
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
    setBusy(true);
    const results: ({ userMsg: LlmMessage; reply: string } | null)[] =
      new Array(units.length).fill(null);
    let nextIdx = 0;

    const worker = async () => {
      while (nextIdx < units.length) {
        const i = nextIdx++;
        const unit = units[i];
        setDisplayMessages(prev => [...prev, { role: 'user', text: `Reading ${unit.label}…` }]);
        const userMsg: LlmMessage = { role: 'user', content: unit.parts };
        try {
          const { text: reply, truncated } = await llmChat({
            messages: [...startHistory, userMsg],
            system: systemPromptRef.current,
            max_tokens: 64000,
          });
          const { visible, parsed } = splitReply(reply);
          if (parsed) {
            const merged = mergeProposals(
              proposalsRef.current, parsed, archetypes, deckCards, true);
            proposalsRef.current = merged;
            setProposals(merged);
            setDisplayMessages(prev => [...prev, {
              role: 'assistant',
              text: `[${unit.label}] ${visible || `${parsed.length} card${parsed.length === 1 ? '' : 's'} extracted (${merged.length} total).`}`,
            }]);
          } else {
            setDisplayMessages(prev => [...prev, {
              role: 'assistant',
              text: `[${unit.label}] ${visible || reply}`,
            }]);
          }
          if (truncated) {
            setDisplayMessages(prev => [...prev, {
              role: 'error',
              text: `[${unit.label}] This reply was cut off at the length limit — some of its cards may be missing. Ask the model to re-check this part afterwards.`,
            }]);
          }
          results[i] = { userMsg, reply };
        } catch (err: unknown) {
          const e = err as { response?: { data?: { error?: string } } };
          setDisplayMessages(prev => [...prev, {
            role: 'error',
            text: `[${unit.label}] ${e.response?.data?.error || 'The model request failed.'}`,
          }]);
        }
      }
    };

    await Promise.all(
      Array.from({ length: Math.min(CONCURRENT_PARTS, units.length) }, worker),
    );

    // Stitch successful rounds into one conversation, in book order,
    // so refinement questions can reference any part of the source.
    let history = startHistory;
    const failedUnits: ExtractionUnit[] = [];
    units.forEach((unit, i) => {
      const r = results[i];
      if (r) history = [...history, r.userMsg, { role: 'assistant', content: r.reply }];
      else failedUnits.push(unit);
    });
    setMessages(history);
    setPendingUnits(failedUnits);
    if (failedUnits.length) {
      setDisplayMessages(prev => [...prev, {
        role: 'error',
        text: `${failedUnits.length} part${failedUnits.length === 1 ? '' : 's'} failed — cards already extracted are safe. "Resume extraction" retries just the failed parts.`,
      }]);
    }
    setBusy(false);
  };

  // ── Chat plumbing ──────────────────────────────────────────

  /** One model round-trip: send history, show the reply, merge any
   *  proposals. Returns the new history, or null on failure. */
  const callModel = async (history: LlmMessage[]): Promise<LlmMessage[] | null> => {
    setBusy(true);
    try {
      const { text: reply, truncated } = await llmChat({
        messages: history,
        system: systemPromptRef.current,
        max_tokens: 64000,
      });
      const { visible, parsed } = splitReply(reply);
      const newHistory: LlmMessage[] = [...history, { role: 'assistant', content: reply }];
      setMessages(newHistory);
      if (parsed) {
        const merged = mergeProposals(proposalsRef.current, parsed, archetypes, deckCards);
        proposalsRef.current = merged;
        setProposals(merged);
        setDisplayMessages(prev => [...prev, {
          role: 'assistant',
          text: visible || `Updated ${parsed.length} card${parsed.length === 1 ? '' : 's'} (${merged.length} total) — review on the right.`,
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
      setBusy(false);
    }
  };

  const handleSend = async () => {
    const text = chatInput.trim();
    if (!text || busy) return;
    setChatInput('');
    setDisplayMessages(prev => [...prev, { role: 'user', text }]);
    await callModel([...messages, { role: 'user', content: text }]);
  };

  // ── Apply ──────────────────────────────────────────────────
  const checkedProposals = proposals.filter(p => p.checked);
  const fieldByName = useMemo(() => {
    const map = new Map<string, SourceField>();
    for (const f of selectedFields) map.set(f.name.toLowerCase(), f);
    return map;
  }, [selectedFields]);

  const handleApply = async () => {
    const writes: ScribeWrite[] = [];
    for (const p of checkedProposals) {
      for (const [label, content] of Object.entries(p.fields)) {
        if (!content?.trim()) continue;
        const sourceField = fieldByName.get(label.toLowerCase());
        if (sourceField && p.archetypeId) {
          writes.push({
            target: 'archetype',
            archetype_id: p.archetypeId,
            field_id: sourceField.id,
            content,
          });
        } else if (p.cardId && cardFieldNames.some(n => n.toLowerCase() === label.toLowerCase())) {
          writes.push({
            target: 'card',
            card_id: p.cardId,
            field_name: label,
            content,
          });
        }
      }
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
      if (result.errors.length) {
        showToast(`Applied ${result.applied} of ${writes.length} — ${result.errors.length} failed.`);
      } else {
        showToast(`Imported ${result.applied} entries from ${source.name}.`, 'success');
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
      title={`Import with AI — ${source.name}`}
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
          {source.cartomancy_types.length > 1 && (
            <div className="scribe__field">
              <label>Cartomancy type</label>
              <select value={ctype} onChange={e => setCtype(e.target.value)}>
                {source.cartomancy_types.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
          )}

          <div className="scribe__field">
            <label>Fill these {source.name} fields ({ctype})</label>
            {fields.length === 0 && (
              <p className="scribe__hint">
                This source has no {ctype} fields yet — add them in the source's
                field list first, or target only deck card fields below.
              </p>
            )}
            {fields.map(f => (
              <label key={f.id} className="scribe__check">
                <input
                  type="checkbox"
                  checked={selectedFieldIds.includes(f.id)}
                  onChange={e => setSelectedFieldIds(prev =>
                    e.target.checked ? [...prev, f.id] : prev.filter(id => id !== f.id))}
                />
                {f.name}
              </label>
            ))}
          </div>

          <div className="scribe__field">
            <label>Also fill card fields on a deck (optional)</label>
            <select
              value={deckId}
              onChange={e => setDeckId(e.target.value ? Number(e.target.value) : '')}
            >
              <option value="">No deck — reference fields only</option>
              {decksForType.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
            </select>
            {deckId !== '' && (
              <>
                <input
                  type="text"
                  placeholder="Card field names, comma-separated (e.g. Keywords, Book Meaning)"
                  value={cardFieldsText}
                  onChange={e => setCardFieldsText(e.target.value)}
                />
                <p className="scribe__hint">
                  These become custom fields on each card of the deck,
                  matched to cards through their archetypes.
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
                placeholder="Ask for corrections or changes… (Enter to send, Shift+Enter for a new line)"
                onChange={e => setChatInput(e.target.value)}
                onKeyDown={e => {
                  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
                }}
                rows={2}
                disabled={busy}
              />
              <button onClick={handleSend} disabled={busy || !chatInput.trim()}>Send</button>
            </div>
          </div>

          <div className="scribe__review">
            <div className="scribe__review-head">
              <strong>{proposals.length} card{proposals.length === 1 ? '' : 's'} proposed</strong>
              {proposals.length > 0 && (
                <span className="scribe__review-bulk">
                  <button onClick={() => setProposals(p => p.map(x => ({ ...x, checked: true })))}>All</button>
                  <button onClick={() => setProposals(p => p.map(x => ({ ...x, checked: false })))}>None</button>
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
                  onToggle={() => setProposals(prev =>
                    prev.map((x, j) => j === i ? { ...x, checked: !x.checked } : x))}
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
  proposal, selectedFields, cardFieldNames, existingKeys, onToggle,
}: {
  proposal: Proposal;
  selectedFields: SourceField[];
  cardFieldNames: string[];
  existingKeys: Set<string>;
  onToggle: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const p = proposal;
  const unmatched = !p.archetypeId && !p.cardId;

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
        {unmatched && <span className="scribe__badge scribe__badge--warn">no matching card</span>}
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
              </span>
              <div className="scribe__proposal-field-text">{content}</div>
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

How to respond — these rules are strict, the app parses your output:
- Extracted card content goes ONLY inside a fenced code block tagged json. NEVER put card meanings, keywords, or field content in the prose part of your reply — the app cannot read prose, and content outside the JSON block is lost.
- The source material arrives in one or more parts, each in its own message. When a part arrives, immediately extract the card content found in THAT part — no confirmation or clarification questions first.
- The app keeps a running list of proposals and MERGES each JSON block you send into it. So each block contains ONLY the cards you are adding or changing in this reply — never re-send cards that haven't changed. One block per reply, in this exact shape:
\`\`\`json
{"proposals": [{"card": "<archetype name>", "fields": {"<field name>": "<content>"}, "flags": ["<optional short notes>"]}]}
\`\`\`
- Use the app's archetype names exactly as listed above whenever you are confident of the match (books often use variant names or other languages). If you cannot match a card confidently, keep the source's name and add a flag explaining the uncertainty.
- Parts overlap slightly, so a card whose text is cut off at the end of one part usually appears complete in another; always extract the complete version you can see. If a card's text still looks cut off, extract what's there and add a flag ("text appears cut off").
- Field content must be faithful to the source text — do not summarize, paraphrase, or embellish. Light cleanup is encouraged: fix obvious OCR artifacts (garbled characters, broken headers, stray symbols like ¥), merge hyphenated line breaks, and remove accidentally duplicated passages, but note significant repairs in flags.
- If a part contains no card content (front matter, essays, spreads), say so in one sentence — no JSON block needed.
- Outside the JSON block, reply conversationally and briefly: what you found, what's uncertain or missing, answers to the user's questions.
- When the user requests changes, emit only the affected cards (each with all of its fields, not just the changed one) in the JSON block.`;
}

type RawProposal = { card: string; fields: Record<string, string>; flags?: string[] };

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
      for (const [k, v] of Object.entries(fields)) {
        const current = mergedFields[k];
        if (preferLonger && typeof current === 'string' && current.length > v.length) continue;
        mergedFields[k] = v;
      }
      result[existingIdx] = {
        ...existing,
        fields: mergedFields,
        flags: flags ?? existing.flags,
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
      units.push({
        label,
        parts: [{
          type: 'text',
          text: `Source material — ${label}. Extract the card content found in this part now:\n\n${chunk}`,
        }],
      });
    });
  }
  const images = materials.filter(m => m.kind === 'image' && m.data);
  for (let i = 0; i < images.length; i += IMAGES_PER_UNIT) {
    const group = images.slice(i, i + IMAGES_PER_UNIT);
    const label = images.length > IMAGES_PER_UNIT
      ? `photos ${i + 1}–${i + group.length} of ${images.length}`
      : `${group.length} photo${group.length === 1 ? '' : 's'}`;
    units.push({
      label,
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
    });
  }
  return units;
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
