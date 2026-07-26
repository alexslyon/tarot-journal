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
  const systemPromptRef = useRef('');
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
    const system = buildSystemPrompt(ctype, archetypes, targetLabels, source.name);
    systemPromptRef.current = system;

    const parts: LlmMessagePart[] = [];
    let text = 'Here is the source material to extract from:\n\n';
    let truncated = false;
    for (const m of materials) {
      if (m.kind === 'text' && m.text) {
        let chunk = `--- ${m.filename} ---\n${m.text}\n\n`;
        if (text.length + chunk.length > MAX_SOURCE_CHARS) {
          chunk = chunk.slice(0, Math.max(0, MAX_SOURCE_CHARS - text.length));
          truncated = true;
        }
        text += chunk;
      }
    }
    text += '\nPlease extract the content for the target fields now.';
    parts.push({ type: 'text', text });
    for (const m of materials) {
      if (m.kind === 'image' && m.data) {
        parts.push({ type: 'image', media_type: m.mediaType, data: m.data });
      }
    }
    if (truncated) {
      showToast('The source text was very long and was truncated — consider importing in smaller pieces.');
    }

    const firstMessage: LlmMessage = { role: 'user', content: parts };
    setStage('chat');
    setDisplayMessages([{ role: 'user', text: `Sent ${materials.length} source file${materials.length === 1 ? '' : 's'} for extraction.` }]);
    await sendToModel([firstMessage]);
  };

  // ── Chat plumbing ──────────────────────────────────────────
  const sendToModel = async (history: LlmMessage[]) => {
    setBusy(true);
    try {
      const { text: reply, truncated } = await llmChat({
        messages: history,
        system: systemPromptRef.current,
        max_tokens: 64000,
      });
      const { visible, parsed } = splitReply(reply);
      setMessages([...history, { role: 'assistant', content: reply }]);
      if (parsed) {
        const resolved = resolveProposals(parsed, archetypes, deckCards, proposals);
        setProposals(resolved);
        setDisplayMessages(prev => [...prev, {
          role: 'assistant',
          text: visible || `Updated ${resolved.length} card proposal${resolved.length === 1 ? '' : 's'} — review them on the right.`,
        }]);
        if (truncated) {
          setDisplayMessages(prev => [...prev, {
            role: 'error',
            text: `The reply was cut off at the length limit — ${resolved.length} card${resolved.length === 1 ? '' : 's'} were recovered. Tell the model to continue with the remaining cards (it will re-send the full set), or target fewer fields per pass.`,
          }]);
        }
      } else {
        setDisplayMessages(prev => [...prev, { role: 'assistant', text: visible || reply }]);
        if (truncated) {
          setDisplayMessages(prev => [...prev, {
            role: 'error',
            text: 'The reply was cut off at the length limit before any proposals could be read. Try targeting fewer fields per pass, or ask the model to extract a smaller batch of cards first (e.g. "start with the Major Arcana only").',
          }]);
        }
      }
    } catch (err: unknown) {
      const e = err as { response?: { data?: { error?: string } } };
      setDisplayMessages(prev => [...prev, {
        role: 'error',
        text: e.response?.data?.error || 'The model request failed. You can try sending again.',
      }]);
      setMessages(history); // keep history so the user can retry
    } finally {
      setBusy(false);
    }
  };

  const handleSend = async () => {
    const text = chatInput.trim();
    if (!text || busy) return;
    setChatInput('');
    setDisplayMessages(prev => [...prev, { role: 'user', text }]);
    await sendToModel([...messages, { role: 'user', content: text }]);
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
- Start extracting immediately from the provided material. Do not ask for confirmation or clarification first; extract what you can and note open questions afterwards.
- Every reply that extracts or changes anything must include exactly ONE such block containing the COMPLETE current set of proposals (never a delta), in this exact shape:
\`\`\`json
{"proposals": [{"card": "<archetype name>", "fields": {"<field name>": "<content>"}, "flags": ["<optional short notes>"]}]}
\`\`\`
- If the source is long, work in cumulative batches: emit the complete set of cards you have finished so far (a valid, closed JSON block), state which cards remain, and continue when the user says to. Never let the JSON block get cut off mid-card — a smaller complete batch beats a larger broken one.
- Use the app's archetype names exactly as listed above whenever you are confident of the match (books often use variant names or other languages). If you cannot match a card confidently, keep the source's name and add a flag explaining the uncertainty.
- Field content must be faithful to the source text — do not summarize, paraphrase, or embellish. Light cleanup is encouraged: fix obvious OCR artifacts (garbled characters, broken headers, stray symbols like ¥), merge hyphenated line breaks, and remove accidentally duplicated passages, but note significant repairs in flags.
- If the material only covers some cards, only include those cards.
- Outside the JSON block, reply conversationally and briefly: what you found, what's uncertain or missing, answers to the user's questions.
- When the user requests changes, apply them and emit the complete updated JSON block again.`;
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

/** Attach archetype/card ids and carry over checkbox state. */
function resolveProposals(
  parsed: { card: string; fields: Record<string, string>; flags?: string[] }[],
  archetypes: Archetype[],
  deckCards: Card[],
  previous: Proposal[],
): Proposal[] {
  const archByName = new Map(archetypes.map(a => [a.name.toLowerCase(), a.id]));
  const prevChecked = new Map(previous.map(p => [p.card.toLowerCase(), p.checked]));
  return parsed
    .filter(p => p && typeof p.card === 'string' && p.fields && typeof p.fields === 'object')
    .map(p => {
      const key = p.card.toLowerCase();
      const archetypeId = archByName.get(key);
      const card = deckCards.find(c =>
        (c.archetype || '').toLowerCase() === key || c.name.toLowerCase() === key);
      const matched = archetypeId != null || card != null;
      return {
        card: p.card,
        fields: Object.fromEntries(
          Object.entries(p.fields).filter(([, v]) => typeof v === 'string')),
        flags: Array.isArray(p.flags) ? p.flags.filter(f => typeof f === 'string') : undefined,
        archetypeId,
        cardId: card?.id,
        checked: prevChecked.get(key) ?? matched,
      };
    });
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
