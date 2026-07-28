/**
 * Reusable assistant chat: message log + input row. Purely
 * presentational — the parent owns the conversation state and calls
 * the model; this renders whatever it's given and reports sends.
 */
import { useEffect, useRef, useState } from 'react';
import './ChatPanel.css';

export interface ChatDisplayMessage {
  role: 'user' | 'assistant' | 'error';
  text: string;
}

interface ChatPanelProps {
  messages: ChatDisplayMessage[];
  busy: boolean;
  onSend: (text: string) => void;
  placeholder?: string;
  /** Shown in the empty log before any messages arrive. */
  emptyHint?: string;
  busyLabel?: string;
}

export default function ChatPanel({
  messages,
  busy,
  onSend,
  placeholder = 'Type a message… (Enter to send, Shift+Enter for a new line)',
  emptyHint,
  busyLabel = 'Working…',
}: ChatPanelProps) {
  const [input, setInput] = useState('');
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, busy]);

  const send = () => {
    const text = input.trim();
    if (!text || busy) return;
    setInput('');
    onSend(text);
  };

  return (
    <div className="chat-panel">
      <div className="chat-panel__log">
        {messages.length === 0 && !busy && emptyHint && (
          <p className="chat-panel__empty">{emptyHint}</p>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`chat-panel__msg chat-panel__msg--${m.role}`}>
            {m.text}
          </div>
        ))}
        {busy && (
          <div className="chat-panel__msg chat-panel__msg--assistant chat-panel__msg--busy">
            {busyLabel}
          </div>
        )}
        <div ref={endRef} />
      </div>
      <div className="chat-panel__input">
        <textarea
          value={input}
          placeholder={placeholder}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => {
            if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
          }}
          rows={2}
          disabled={busy}
        />
        <button onClick={send} disabled={busy || !input.trim()}>Send</button>
      </div>
    </div>
  );
}
