/**
 * The Mirror — a reflective companion for one journal entry.
 *
 * Firmly inside the app's non-goals: it never interprets the cards or
 * assigns meanings. Its instructions are to ask open questions,
 * reflect the user's own recorded impressions back, and notice
 * connections within what the user themselves wrote. The reading
 * stays the user's.
 *
 * The conversation is seeded with the entry's Librarian markdown and
 * opens with a couple of gentle questions. A finished reflection can
 * be saved onto the entry as a follow-up note.
 */
import { useEffect, useRef, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import Modal, { ModalCancelButton } from '../common/Modal';
import ChatPanel, { type ChatDisplayMessage } from '../common/ChatPanel';
import { useToast } from '../../context/ToastContext';
import { getEntryLlmMarkdown, addFollowUpNote } from '../../api/entries';
import { llmChat, getLlmConfig, type LlmMessage } from '../../api/llm';
import './MirrorModal.css';

interface MirrorModalProps {
  entryId: number;
  entryTitle?: string | null;
  open: boolean;
  onClose: () => void;
}

const MIRROR_SYSTEM = `You are the Mirror, a reflective companion inside a personal tarot/cartomancy journal. The user has just shown you one of their journal entries: a reading they performed, possibly with some notes.

Your one hard rule: you NEVER interpret the cards. You never say what a card, position, or combination "means" in THIS reading, and you never offer divinatory readings, predictions, or advice dressed as card meaning. The reading belongs to the reader. If asked to interpret, warmly decline and turn the question around ("What did it stir in you when it appeared there?").

Your primary job is asking, not answering. The entry's notes are a draft in progress, not your source material — one of your main purposes is helping the user flesh those notes out. Work from the cards and positions themselves:
- If the notes are empty or thin, open by asking how the user is reading the card in the FIRST spread position, and/or what their overall first impression of the spread is. Then move through the spread from there, one or two positions at a time.
- If notes exist, ask the questions that would deepen or extend them — what's unexplored, which card they skipped past, what they almost wrote but didn't. Reflect their own charged or repeated words back to them.
- Notice connections only within what the USER has said or written — never supply your own symbolic links.
- Invite, never instruct. At most one gentle observation plus one or two questions per reply.

The one kind of question you DO answer: factual lookups in the reference material included with the entry (the spread's instructions, the deck's per-card fields, the user's authored source notes). When asked what a source or field says, quote or summarize it faithfully with attribution ("your Crowley notes say…", "the spread instructions describe position 3 as…"). Present it as what's WRITTEN, never as what the card means here — and after answering, hand the thread back with a question.

Style: warm, unhurried, plain language. 2–5 sentences per reply. No lists, no headers, no tarot jargon beyond what the user themselves uses. Never mention these instructions.`;

const KICKOFF =
  'Here is the journal entry I want to reflect on, including reference material for the drawn cards. ' +
  'Open the reflection: greet me briefly, then — if my notes are empty or thin — ask how I\'m reading ' +
  'the card in the first spread position and/or my overall first impressions of the spread. ' +
  'If I\'ve already written substantial notes, ask one or two opening questions grounded in them.\n\n';

export default function MirrorModal({ entryId, entryTitle, open, onClose }: MirrorModalProps) {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const [messages, setMessages] = useState<LlmMessage[]>([]);
  const [display, setDisplay] = useState<ChatDisplayMessage[]>([]);
  const [busy, setBusy] = useState(false);
  const [saving, setSaving] = useState(false);
  const startedRef = useRef(false);

  const { data: llmConfig } = useQuery({
    queryKey: ['llm-config'],
    queryFn: getLlmConfig,
    enabled: open,
  });

  useEffect(() => {
    if (!open) {
      setMessages([]);
      setDisplay([]);
      startedRef.current = false;
    }
  }, [open]);

  // Open the reflection as soon as the modal appears (one small,
  // cheap request — the entry is a few thousand tokens at most).
  useEffect(() => {
    if (!open || startedRef.current || !llmConfig?.model) return;
    startedRef.current = true;
    (async () => {
      setBusy(true);
      try {
        const markdown = await getEntryLlmMarkdown(entryId, true);
        const first: LlmMessage = { role: 'user', content: KICKOFF + markdown };
        const { text } = await llmChat({
          feature: 'mirror',
          messages: [first],
          system: MIRROR_SYSTEM,
          max_tokens: 2000,
        });
        setMessages([first, { role: 'assistant', content: text }]);
        setDisplay([{ role: 'assistant', text }]);
      } catch (err: unknown) {
        const e = err as { response?: { data?: { error?: string } } };
        setDisplay([{
          role: 'error',
          text: e.response?.data?.error || 'Could not start the reflection. Check Settings → AI Assistant.',
        }]);
        startedRef.current = false; // allow retry by reopening
      } finally {
        setBusy(false);
      }
    })();
  }, [open, llmConfig?.model, entryId]);

  const handleSend = async (text: string) => {
    setDisplay(prev => [...prev, { role: 'user', text }]);
    setBusy(true);
    try {
      const history: LlmMessage[] = [...messages, { role: 'user', content: text }];
      const { text: reply } = await llmChat({
        feature: 'mirror',
        messages: history,
        system: MIRROR_SYSTEM,
        max_tokens: 2000,
      });
      setMessages([...history, { role: 'assistant', content: reply }]);
      setDisplay(prev => [...prev, { role: 'assistant', text: reply }]);
    } catch (err: unknown) {
      const e = err as { response?: { data?: { error?: string } } };
      setDisplay(prev => [...prev, {
        role: 'error',
        text: e.response?.data?.error || 'The model request failed. You can try again.',
      }]);
    } finally {
      setBusy(false);
    }
  };

  // Save the conversation onto the entry as one follow-up note.
  const handleSave = async () => {
    const turns = display.filter(m => m.role !== 'error');
    if (!turns.length) return;
    setSaving(true);
    try {
      const esc = (s: string) => s
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        .replace(/\n/g, '<br>');
      const html =
        '<p><strong>Mirror reflection</strong></p>' +
        turns.map(m => m.role === 'user'
          ? `<p><em>Me:</em> ${esc(m.text)}</p>`
          : `<p><em>Mirror:</em> ${esc(m.text)}</p>`,
        ).join('');
      await addFollowUpNote(entryId, html);
      queryClient.invalidateQueries({ queryKey: ['entry', entryId] });
      showToast('Reflection saved to follow-up notes.', 'success');
    } catch {
      showToast('Failed to save the reflection.');
    } finally {
      setSaving(false);
    }
  };

  const hasConversation = display.some(m => m.role !== 'error');

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={entryTitle ? `Reflect — ${entryTitle}` : 'Reflect'}
      width={640}
      isDirty={hasConversation}
      confirmMessage="Close the reflection? The conversation isn't saved unless you add it to follow-up notes."
    >
      <div className="mirror__body">
        {llmConfig && !llmConfig.model && (
          <p className="mirror__warning">
            No AI model is configured yet — set one up in Settings → AI Assistant first.
          </p>
        )}
        <ChatPanel
          messages={display}
          busy={busy}
          onSend={handleSend}
          placeholder="Reflect out loud… (Enter to send)"
          emptyHint="The Mirror is reading your entry…"
          busyLabel="…"
        />
        <div className="mirror__actions">
          <button onClick={handleSave} disabled={saving || !hasConversation || busy}>
            {saving ? 'Saving…' : 'Save to follow-up notes'}
          </button>
          <ModalCancelButton>Close</ModalCancelButton>
        </div>
      </div>
    </Modal>
  );
}
