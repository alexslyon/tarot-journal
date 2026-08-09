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
import { useActivePrompt } from '../../utils/assistantPrompts';
import './MirrorModal.css';

interface MirrorModalProps {
  entryId: number;
  entryTitle?: string | null;
  open: boolean;
  onClose: () => void;
}

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
  const { prompt: mirrorSystem, ready: promptReady } = useActivePrompt('mirror', open);

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
    if (!open || startedRef.current || !llmConfig?.model || !promptReady) return;
    startedRef.current = true;
    (async () => {
      setBusy(true);
      try {
        const markdown = await getEntryLlmMarkdown(entryId, true);
        const first: LlmMessage = { role: 'user', content: KICKOFF + markdown };
        const { text } = await llmChat({
          feature: 'mirror',
          messages: [first],
          system: mirrorSystem,
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
  }, [open, llmConfig?.model, entryId, promptReady, mirrorSystem]);

  const handleSend = async (text: string) => {
    setDisplay(prev => [...prev, { role: 'user', text }]);
    setBusy(true);
    try {
      const history: LlmMessage[] = [...messages, { role: 'user', content: text }];
      const { text: reply } = await llmChat({
        feature: 'mirror',
        messages: history,
        system: mirrorSystem,
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
