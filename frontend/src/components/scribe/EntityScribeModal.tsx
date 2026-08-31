/**
 * The Entity Scribe — imports source texts onto reference ENTITIES
 * (signs, planets, sephiroth, tree paths, chakras, numbers, suits,
 * ranks) rather than cards. A leaner sibling of the card Scribe,
 * sharing its services: server-side text extraction, the LLM chat
 * endpoint, the fenced-JSON reply protocol, and the batched apply.
 *
 * One entity kind per import (deliberate — a chapter on the suits, a
 * chapter on the sephiroth): pick the kind (and deck type for
 * suits/ranks), the reference source the texts belong to, add
 * material, review per-entity proposals, apply. Applied notes merge
 * into each entity's one note per source (append, never clobber).
 */
import { useMemo, useRef, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import Modal, { ModalCancelButton } from '../common/Modal';
import { useToast } from '../../context/ToastContext';
import { getReferenceSources } from '../../api/referenceSources';
import {
  getNumerologyReference,
  getRanksReference,
  getSuitsReference,
  type EntityKind,
} from '../../api/reference';
import { extractSourceText, applyScribeWrites, type ScribeWrite } from '../../api/scribe';
import { llmChat, type LlmMessage } from '../../api/llm';
import type { ReferenceSource } from '../../types';
import './EntityScribeModal.css';

interface EntityScribeModalProps {
  open: boolean;
  onClose: () => void;
  /** Preselected kind (the section the user launched from). */
  initialKind?: EntityKind;
  /** Preselected deck type, for suit/rank kinds. */
  initialType?: string | null;
}

const KIND_LABELS: Record<EntityKind, string> = {
  sign: 'Astrology — signs',
  planet: 'Astrology — planets',
  sephira: 'Kabbalah — sephiroth',
  path: 'Kabbalah — paths (by Hebrew letter)',
  chakra: 'Chakras',
  number: 'Numerology numbers',
  suit: 'Suits',
  rank: 'Ranks',
};

const TYPED_KINDS: EntityKind[] = ['suit', 'rank'];

// Static entity rosters (the dynamic kinds — numbers, suits, ranks —
// load from the reference endpoints instead).
const STATIC_ENTITIES: Partial<Record<EntityKind, string[]>> = {
  sign: ['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo', 'Libra',
    'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces'],
  planet: ['Sun', 'Moon', 'Mercury', 'Venus', 'Mars', 'Jupiter', 'Saturn',
    'Uranus', 'Neptune', 'Pluto'],
  sephira: ['Kether', 'Chokmah', 'Binah', 'Chesed', 'Geburah', 'Tiphareth',
    'Netzach', 'Hod', 'Yesod', 'Malkuth'],
  path: ['Aleph', 'Beth', 'Gimel', 'Daleth', 'Heh', 'Vav', 'Zayin', 'Cheth',
    'Teth', 'Yod', 'Kaph', 'Lamed', 'Mem', 'Nun', 'Samekh', 'Ayin', 'Peh',
    'Tzaddi', 'Qoph', 'Resh', 'Shin', 'Tav'],
  chakra: ['Root', 'Sacral', 'Solar Plexus', 'Heart', 'Throat', 'Third Eye',
    'Crown'],
};

// Alternate spellings folded into matching (mirrors the backend's
// alias tables).
const ALIASES: Record<string, string> = {
  alef: 'Aleph', bet: 'Beth', beit: 'Beth', gimmel: 'Gimel', dalet: 'Daleth',
  he: 'Heh', hey: 'Heh', vau: 'Vav', waw: 'Vav', zain: 'Zayin',
  chet: 'Cheth', het: 'Cheth', heth: 'Cheth', tet: 'Teth', yud: 'Yod',
  caph: 'Kaph', kaf: 'Kaph', lamedh: 'Lamed', samech: 'Samekh',
  pe: 'Peh', fe: 'Peh', tsade: 'Tzaddi', tzadi: 'Tzaddi', tsadi: 'Tzaddi',
  qof: 'Qoph', kof: 'Qoph', tau: 'Tav', taw: 'Tav',
  keter: 'Kether', chochmah: 'Chokmah', hokmah: 'Chokmah', chokma: 'Chokmah',
  hesed: 'Chesed', gevurah: 'Geburah', tiphereth: 'Tiphareth',
  tiferet: 'Tiphareth', tifereth: 'Tiphareth', netsach: 'Netzach',
  malchut: 'Malkuth', malkut: 'Malkuth',
  muladhara: 'Root', svadhisthana: 'Sacral', manipura: 'Solar Plexus',
  anahata: 'Heart', vishuddha: 'Throat', visuddha: 'Throat',
  ajna: 'Third Eye', sahasrara: 'Crown',
};

const norm = (s: string) =>
  s.normalize('NFD').replace(/[̀-ͯ]/g, '').trim().toLowerCase();

/** Plain text from the model → simple HTML for the rich-text viewer. */
function textToHtml(text: string): string {
  const esc = (s: string) => s
    .replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');
  return text
    .split(/\n\s*\n/)
    .map(p => p.trim())
    .filter(Boolean)
    .map(p => `<p>${esc(p).replaceAll('\n', '<br>')}</p>`)
    .join('');
}

interface EntityProposal {
  /** The name the model used (raw). */
  entry: string;
  content: string;
  flags?: string[];
  /** Resolved entity name from the roster ('' = unmatched). */
  resolved: string;
  checked: boolean;
}

const CHUNK_CHARS = 90_000;
const CHUNK_OVERLAP = 4_000;
let materialId = 1;

interface TextMaterial {
  id: number;
  label: string;
  text: string;
}

export default function EntityScribeModal({
  open,
  onClose,
  initialKind,
  initialType,
}: EntityScribeModalProps) {
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  // ── Setup ─────────────────────────────────────────────────
  const [kind, setKind] = useState<EntityKind>(initialKind ?? 'sign');
  const [deckType, setDeckType] = useState<string | null>(initialType ?? null);
  const [sourceId, setSourceId] = useState<number | ''>('');
  const [instructions, setInstructions] = useState('');
  const [materials, setMaterials] = useState<TextMaterial[]>([]);
  const [pasteText, setPasteText] = useState('');
  const [extracting, setExtracting] = useState(false);
  const [stage, setStage] = useState<'setup' | 'review'>('setup');

  const { data: sources = [] } = useQuery<ReferenceSource[]>({
    queryKey: ['reference-sources'],
    queryFn: () => getReferenceSources(),
    enabled: open,
  });

  // Entity roster for the chosen kind
  const typed = TYPED_KINDS.includes(kind);
  const { data: suitData } = useQuery({
    queryKey: ['reference-suits', typed ? deckType : null],
    queryFn: () => getSuitsReference(deckType),
    enabled: open && kind === 'suit',
  });
  const { data: rankData } = useQuery({
    queryKey: ['reference-ranks', typed ? deckType : null],
    queryFn: () => getRanksReference(deckType),
    enabled: open && kind === 'rank',
  });
  const { data: numberData } = useQuery({
    queryKey: ['reference-numerology'],
    queryFn: getNumerologyReference,
    enabled: open && kind === 'number',
  });

  const suitTypes = suitData?.types ?? rankData?.types ?? [];
  const resolvedType = kind === 'suit'
    ? suitData?.type ?? deckType
    : rankData?.type ?? deckType;
  const entities = useMemo<string[]>(() => {
    if (kind === 'suit') return (suitData?.suits ?? []).map(s => s.name);
    if (kind === 'rank') return (rankData?.ranks ?? []).map(r => r.rank);
    if (kind === 'number') return (numberData?.entries ?? []).map(e => e.number);
    return STATIC_ENTITIES[kind] ?? [];
  }, [kind, suitData, rankData, numberData]);

  const resolveEntity = (raw: string): string => {
    const n = norm(raw);
    const direct = entities.find(e => norm(e) === n);
    if (direct) return direct;
    const alias = ALIASES[n];
    if (alias && entities.includes(alias)) return alias;
    // 'Nine of Hearts'-style or 'the Kings' → try the leading word
    const first = norm(raw.split(/ of |,/)[0]).replace(/^the /, '').replace(/s$/, '');
    return entities.find(e => norm(e) === first || norm(e) === `${first}s`) ?? '';
  };

  // ── Review state ──────────────────────────────────────────
  const [messages, setMessages] = useState<LlmMessage[]>([]);
  const [display, setDisplay] = useState<{ role: string; text: string }[]>([]);
  const [chatInput, setChatInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [applying, setApplying] = useState(false);
  const [proposals, setProposals] = useState<EntityProposal[]>([]);
  const proposalsRef = useRef<EntityProposal[]>([]);
  const systemPromptRef = useRef('');

  const updateProposals = (fn: (cur: EntityProposal[]) => EntityProposal[]) => {
    proposalsRef.current = fn(proposalsRef.current);
    setProposals(proposalsRef.current);
  };

  // ── Materials ─────────────────────────────────────────────
  const addFiles = async (files: FileList | null) => {
    if (!files?.length) return;
    setExtracting(true);
    try {
      for (const file of Array.from(files)) {
        try {
          const result = await extractSourceText(file);
          if (result.text.trim()) {
            setMaterials(m => [...m, {
              id: materialId++, label: result.filename, text: result.text,
            }]);
          } else {
            showToast(`${file.name}: no text found (scanned/image files aren't supported here)`, 'error');
          }
          if (result.warning) showToast(result.warning, 'warning');
        } catch (e) {
          showToast(`${file.name}: ${e instanceof Error ? e.message : 'extraction failed'}`, 'error');
        }
      }
    } finally {
      setExtracting(false);
    }
  };

  const addPaste = () => {
    if (!pasteText.trim()) return;
    setMaterials(m => [...m, {
      id: materialId++,
      label: `Pasted text (${pasteText.trim().length.toLocaleString()} chars)`,
      text: pasteText.trim(),
    }]);
    setPasteText('');
  };

  // ── Prompt + extraction ───────────────────────────────────
  const buildSystemPrompt = () => {
    const sourceName = sources.find(s => s.id === sourceId)?.name ?? 'the source';
    const kindLabel = KIND_LABELS[kind] + (typed && resolvedType ? ` (${resolvedType})` : '');
    const extra = instructions.trim()
      ? `\n\nInstructions from the user for THIS import — follow them; the JSON output format is always required:\n${instructions.trim()}`
      : '';
    return `You are the Scribe, an assistant inside a personal tarot/cartomancy journal app. Your job is to transcribe reference text from source material into per-entry notes. You transcribe and organize — you never invent content.

This import covers ONE list of entries: ${kindLabel}.
The app's entries are, exactly: ${entities.join(', ')}
Source being imported: ${sourceName}

How to respond — these rules are strict, the app parses your output:
- Extracted content goes ONLY inside a fenced code block tagged json, one block per reply, in this exact shape:
\`\`\`json
{"proposals": [{"entry": "<entry name>", "content": "<text>", "flags": []}]}
\`\`\`
- Use the app's entry names exactly as listed whenever you are confident of the match (sources use variant spellings — Keter/Kether, Tsadi/Tzaddi, Mūlādhāra/Root — map them silently). If a passage matches no listed entry, keep the source's own name and add a flag explaining.
- The app MERGES each block into a running list keyed by entry: send only entries you are adding or changing in this reply, and always send an entry's COMPLETE text (the new block replaces the old for that entry).
- Content must be faithful to the source — no summarizing, paraphrasing, or embellishing. Fix obvious OCR artifacts and merged hyphenation; note significant repairs in flags. Plain text; separate paragraphs with a blank line.
- Material about other subjects (cards, spreads, other entry kinds) is out of scope for this import — mention in one sentence that you skipped it, and do not extract it.
- The source arrives in one or more parts. Extract each part immediately, no clarifying questions. If a part has nothing relevant, say so in one sentence — no JSON block.
- Outside the JSON block reply briefly; never put source text in prose, it is not saved.${extra}`;
  };

  const parseReply = (text: string) => {
    const match = text.match(/```json\s*([\s\S]*?)```/);
    if (!match) return;
    try {
      const parsed = JSON.parse(match[1]);
      const rows: { entry?: unknown; content?: unknown; flags?: unknown }[] =
        Array.isArray(parsed?.proposals) ? parsed.proposals : [];
      updateProposals(cur => {
        const next = [...cur];
        for (const row of rows) {
          const entry = String(row.entry ?? '').trim();
          const content = String(row.content ?? '').trim();
          if (!entry || !content) continue;
          const flags = Array.isArray(row.flags) ? row.flags.map(String) : [];
          const resolved = resolveEntity(entry);
          const i = next.findIndex(p => norm(p.entry) === norm(entry));
          if (i >= 0) {
            next[i] = { ...next[i], content, flags, resolved: next[i].resolved || resolved };
          } else {
            next.push({ entry, content, flags, resolved, checked: true });
          }
        }
        // Roster order first, unmatched rows at the end
        return next.sort((a, b) => {
          const ai = a.resolved ? entities.indexOf(a.resolved) : 999;
          const bi = b.resolved ? entities.indexOf(b.resolved) : 999;
          return ai - bi || a.entry.localeCompare(b.entry);
        });
      });
    } catch {
      showToast('A reply contained unparseable JSON — ask the model to re-send it.', 'error');
    }
  };

  const stripJson = (text: string) =>
    text.replace(/```json[\s\S]*?```/g, '(proposals updated)').trim();

  const startExtraction = async () => {
    const system = buildSystemPrompt();
    systemPromptRef.current = system;
    setStage('review');
    setBusy(true);
    try {
      // Chunk all materials into parts, then extract sequentially.
      const parts: { label: string; text: string }[] = [];
      for (const m of materials) {
        if (m.text.length <= CHUNK_CHARS) {
          parts.push({ label: m.label, text: m.text });
        } else {
          for (let i = 0, n = 1; i < m.text.length; i += CHUNK_CHARS - CHUNK_OVERLAP, n++) {
            parts.push({
              label: `${m.label} (part ${n})`,
              text: m.text.slice(i, i + CHUNK_CHARS),
            });
          }
        }
      }
      let history: LlmMessage[] = [];
      for (const part of parts) {
        const userMsg: LlmMessage = {
          role: 'user',
          content: `Source material — ${part.label}:\n\n${part.text}`,
        };
        setDisplay(d => [...d, { role: 'user', text: `📄 ${part.label}` }]);
        const reply = await llmChat({
          messages: [...history, userMsg],
          system,
          feature: 'scribe',
          max_tokens: 64000,
        });
        parseReply(reply.text);
        setDisplay(d => [...d, { role: 'assistant', text: stripJson(reply.text) }]);
        history = [...history, userMsg, { role: 'assistant', content: reply.text }];
        setMessages(history);
      }
    } catch (e) {
      showToast(e instanceof Error ? e.message : 'Extraction failed', 'error');
    } finally {
      setBusy(false);
    }
  };

  const sendChat = async () => {
    const text = chatInput.trim();
    if (!text || busy) return;
    setChatInput('');
    setBusy(true);
    const userMsg: LlmMessage = { role: 'user', content: text };
    setDisplay(d => [...d, { role: 'user', text }]);
    try {
      const reply = await llmChat({
        messages: [...messages, userMsg],
        system: systemPromptRef.current,
        feature: 'scribe',
        max_tokens: 64000,
        thinking: true,
      });
      parseReply(reply.text);
      setDisplay(d => [...d, { role: 'assistant', text: stripJson(reply.text) }]);
      setMessages(m => [...m, userMsg, { role: 'assistant', content: reply.text }]);
    } catch (e) {
      showToast(e instanceof Error ? e.message : 'Request failed', 'error');
    } finally {
      setBusy(false);
    }
  };

  // ── Apply ─────────────────────────────────────────────────
  const applyChecked = async () => {
    if (sourceId === '') return;
    const rows = proposalsRef.current.filter(p => p.checked && p.resolved);
    if (rows.length === 0) {
      showToast('Nothing checked (or nothing matched an entry).', 'error');
      return;
    }
    setApplying(true);
    try {
      const writes: ScribeWrite[] = rows.map(p => ({
        target: 'entity_note',
        kind,
        key: typed && resolvedType ? `${resolvedType}::${p.resolved}` : p.resolved,
        source_id: sourceId,
        content: textToHtml(p.content),
      }));
      const result = await applyScribeWrites(writes);
      queryClient.invalidateQueries({
        predicate: q => q.queryKey[0] === 'entity-notes',
      });
      const bits = [`${result.applied} applied`];
      if (result.skipped) bits.push(`${result.skipped} already present`);
      if (result.errors.length) bits.push(`${result.errors.length} failed`);
      showToast(`Source texts: ${bits.join(', ')}.`, result.errors.length ? 'error' : 'success');
    } catch (e) {
      showToast(e instanceof Error ? e.message : 'Apply failed', 'error');
    } finally {
      setApplying(false);
    }
  };

  const canStart = sourceId !== '' && materials.length > 0 &&
    entities.length > 0 && !extracting;

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Scribe — Reference Entries"
      width={stage === 'setup' ? 560 : 1100}
    >
      {stage === 'setup' && (
        <div className="entity-scribe__setup">
          <label className="entity-scribe__field">
            <span>What is this source about?</span>
            <select
              value={kind}
              onChange={(e) => setKind(e.target.value as EntityKind)}
            >
              {(Object.keys(KIND_LABELS) as EntityKind[]).map(k => (
                <option key={k} value={k}>{KIND_LABELS[k]}</option>
              ))}
            </select>
          </label>
          {typed && (
            <label className="entity-scribe__field">
              <span>Deck type</span>
              <select
                value={resolvedType ?? ''}
                onChange={(e) => setDeckType(e.target.value)}
              >
                {suitTypes.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </label>
          )}
          <label className="entity-scribe__field">
            <span>Reference source these texts belong to</span>
            <select
              value={sourceId === '' ? '' : String(sourceId)}
              onChange={(e) => setSourceId(e.target.value === '' ? '' : Number(e.target.value))}
            >
              <option value="">Choose a source…</option>
              {sources.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </label>

          <div className="entity-scribe__field">
            <span>Source material</span>
            {materials.map(m => (
              <div key={m.id} className="entity-scribe__material">
                <span>{m.label}</span>
                <button
                  type="button"
                  onClick={() => setMaterials(list => list.filter(x => x.id !== m.id))}
                >
                  Remove
                </button>
              </div>
            ))}
            <input
              type="file"
              multiple
              accept=".epub,.pdf,.mobi,.azw,.azw3,.txt,.md,.html,.rtf"
              onChange={(e) => { addFiles(e.target.files); e.target.value = ''; }}
            />
            <textarea
              value={pasteText}
              onChange={(e) => setPasteText(e.target.value)}
              placeholder="…or paste text here"
              rows={4}
            />
            {pasteText.trim() && (
              <button type="button" onClick={addPaste}>Add pasted text</button>
            )}
          </div>

          <label className="entity-scribe__field">
            <span>Instructions for this import (optional)</span>
            <textarea
              value={instructions}
              onChange={(e) => setInstructions(e.target.value)}
              placeholder="e.g. only chapters 3–4 are about the suits; keep the author's headings"
              rows={2}
            />
          </label>

          <div className="entity-scribe__actions">
            <ModalCancelButton>Cancel</ModalCancelButton>
            <button
              type="button"
              className="primary"
              disabled={!canStart}
              onClick={startExtraction}
            >
              {extracting ? 'Reading files…' : 'Start extraction'}
            </button>
          </div>
        </div>
      )}

      {stage === 'review' && (
        <div className="entity-scribe__review">
          <div className="entity-scribe__chat">
            <div className="entity-scribe__log">
              {display.map((m, i) => (
                <div key={i} className={`entity-scribe__msg entity-scribe__msg--${m.role}`}>
                  {m.text}
                </div>
              ))}
              {busy && <div className="entity-scribe__msg entity-scribe__msg--assistant">…</div>}
            </div>
            <div className="entity-scribe__chatbar">
              <input
                type="text"
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') sendChat(); }}
                placeholder="Refine: 'you merged Geburah into Chesed', 'keep the epigraphs'…"
                disabled={busy}
              />
              <button type="button" onClick={sendChat} disabled={busy || !chatInput.trim()}>
                Send
              </button>
            </div>
          </div>

          <div className="entity-scribe__panel">
            <div className="entity-scribe__panel-head">
              <strong>{proposals.length}</strong>&nbsp;proposals ·{' '}
              {entities.length - new Set(proposals.map(p => p.resolved).filter(Boolean)).size}{' '}
              entries uncovered
            </div>
            <div className="entity-scribe__rows">
              {proposals.map((p, i) => (
                <div key={`${p.entry}-${i}`} className="entity-scribe__row">
                  <div className="entity-scribe__row-head">
                    <input
                      type="checkbox"
                      checked={p.checked}
                      onChange={(e) => updateProposals(cur =>
                        cur.map((x, j) => (j === i ? { ...x, checked: e.target.checked } : x)))}
                    />
                    <select
                      value={p.resolved}
                      onChange={(e) => updateProposals(cur =>
                        cur.map((x, j) => (j === i ? { ...x, resolved: e.target.value } : x)))}
                    >
                      <option value="">— pick an entry —</option>
                      {entities.map(name => (
                        <option key={name} value={name}>{name}</option>
                      ))}
                    </select>
                    {p.resolved === '' && (
                      <span className="entity-scribe__unmatched">“{p.entry}”</span>
                    )}
                  </div>
                  {p.flags && p.flags.length > 0 && (
                    <div className="entity-scribe__flags">⚑ {p.flags.join(' · ')}</div>
                  )}
                  <textarea
                    value={p.content}
                    rows={Math.min(10, Math.max(3, Math.ceil(p.content.length / 90)))}
                    onChange={(e) => updateProposals(cur =>
                      cur.map((x, j) => (j === i ? { ...x, content: e.target.value } : x)))}
                  />
                </div>
              ))}
              {proposals.length === 0 && !busy && (
                <p className="entity-scribe__empty">No proposals yet.</p>
              )}
            </div>
            <div className="entity-scribe__actions">
              <ModalCancelButton>Close</ModalCancelButton>
              <button
                type="button"
                className="primary"
                disabled={applying || busy || proposals.every(p => !p.checked || !p.resolved)}
                onClick={applyChecked}
              >
                {applying ? 'Applying…' : 'Apply checked'}
              </button>
            </div>
          </div>
        </div>
      )}
    </Modal>
  );
}
