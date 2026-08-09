/**
 * The Analyst — pattern retrospectives across many journal entries.
 *
 * Scope = whatever the journal list currently shows: the user narrows
 * with the existing filters (search, querent, dates, card), then opens
 * the Analyst on that set. The backend bundles those entries into one
 * chronological document topped with app-computed statistics, so
 * counting is done by code — the model's job is noticing patterns and
 * themes, always grounded in the provided entries.
 *
 * Like everything in the app, it does not interpret: no card meanings,
 * no predictions. It describes what's there.
 */
import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import Modal, { ModalCancelButton } from '../common/Modal';
import ChatPanel, { type ChatDisplayMessage } from '../common/ChatPanel';
import { getBulkLlmMarkdown } from '../../api/entries';
import { llmChat, getLlmConfig, type LlmMessage } from '../../api/llm';
import { useActivePrompt } from '../../utils/assistantPrompts';
import './AnalystModal.css';

interface AnalystModalProps {
  /** Entries currently shown in the journal list (newest first). */
  entryIds: number[];
  open: boolean;
  onClose: () => void;
}

// Beyond this, a question re-reads too much text to be worth it —
// the user should narrow the list filters instead.
const MAX_BUNDLE_CHARS = 900_000;

const KICKOFF =
  'Here is the journal excerpt. Start with a brief overview (under 200 words) of what stands out: ' +
  'reading rhythm over time, the most frequent cards, and any themes that recur in my own notes. ' +
  'Then I\'ll ask questions.\n\n';

export default function AnalystModal({ entryIds, open, onClose }: AnalystModalProps) {
  const [stage, setStage] = useState<'intro' | 'chat'>('intro');
  const [messages, setMessages] = useState<LlmMessage[]>([]);
  const [display, setDisplay] = useState<ChatDisplayMessage[]>([]);
  const [busy, setBusy] = useState(false);
  const [introError, setIntroError] = useState('');

  const { data: llmConfig } = useQuery({
    queryKey: ['llm-config'],
    queryFn: getLlmConfig,
    enabled: open,
  });
  const { prompt: analystSystem } = useActivePrompt('analyst', open);

  useEffect(() => {
    if (!open) {
      setStage('intro');
      setMessages([]);
      setDisplay([]);
      setIntroError('');
    }
  }, [open]);

  const callModel = async (history: LlmMessage[]) => {
    setBusy(true);
    try {
      const { text: reply } = await llmChat({
        feature: 'analyst',
        messages: history,
        system: analystSystem,
        max_tokens: 4000,
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

  const handleBegin = async () => {
    setIntroError('');
    setBusy(true);
    try {
      const bundle = await getBulkLlmMarkdown(entryIds);
      if (bundle.char_count > MAX_BUNDLE_CHARS) {
        setIntroError(
          `These ${bundle.entry_count} entries add up to ${Math.round(bundle.char_count / 1000)}k characters — ` +
          'too much to analyze at once. Narrow the journal list first (date range, querent, or a search).',
        );
        setBusy(false);
        return;
      }
      setStage('chat');
      await callModel([{ role: 'user', content: KICKOFF + bundle.markdown }]);
    } catch (err: unknown) {
      const e = err as { response?: { data?: { error?: string } } };
      setIntroError(e.response?.data?.error || 'Could not assemble the journal excerpt.');
      setBusy(false);
    }
  };

  const handleSend = async (text: string) => {
    setDisplay(prev => [...prev, { role: 'user', text }]);
    await callModel([...messages, { role: 'user', content: text }]);
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Analyst"
      width={720}
      isDirty={stage === 'chat' && display.length > 0}
      confirmMessage="Close the analysis? The conversation isn't saved."
    >
      {stage === 'intro' ? (
        <div className="analyst__intro">
          {llmConfig && !llmConfig.model && (
            <p className="analyst__warning">
              No AI model is configured yet — set one up in Settings → AI Assistant first.
            </p>
          )}
          <p>
            The Analyst looks for patterns across{' '}
            <strong>the {entryIds.length} entr{entryIds.length === 1 ? 'y' : 'ies'} currently shown in your journal list</strong>{' '}
            — reading rhythm, recurring cards, themes in your own notes. It describes; it never interprets.
          </p>
          <p className="analyst__hint">
            To analyze a different set, close this and narrow the journal list first
            (search, querent, dates, or a card filter). Each question re-reads the
            whole excerpt, so smaller sets are cheaper and sharper.
          </p>
          {introError && <p className="analyst__warning">{introError}</p>}
          <div className="analyst__actions">
            <button
              className="primary"
              onClick={handleBegin}
              disabled={busy || entryIds.length === 0 || !llmConfig?.model}
            >
              {busy ? 'Assembling…' : `Analyze ${entryIds.length} entr${entryIds.length === 1 ? 'y' : 'ies'}`}
            </button>
            <ModalCancelButton>Cancel</ModalCancelButton>
          </div>
        </div>
      ) : (
        <div className="analyst__body">
          <ChatPanel
            messages={display}
            busy={busy}
            onSend={handleSend}
            placeholder="Ask about patterns, cards, themes… (Enter to send)"
            busyLabel="Reading the journal…"
          />
          <div className="analyst__actions">
            <ModalCancelButton>Close</ModalCancelButton>
          </div>
        </div>
      )}
    </Modal>
  );
}
