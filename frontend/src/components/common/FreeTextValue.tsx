import { useState, useEffect } from 'react';
import './MultiValueSelect.css';

interface FreeTextValueProps {
  values: string[];
  onCommit: (values: string[]) => void;
  placeholder?: string;
  compact?: boolean;
}

/**
 * A plain text input for correspondence fields that don't fit a fixed option
 * list (e.g. numerology). Supports multi-value by comma separation. Commits
 * on blur or Enter; Escape resets to the last committed value.
 */
export default function FreeTextValue({
  values,
  onCommit,
  placeholder = '—',
  compact = false,
}: FreeTextValueProps) {
  const [text, setText] = useState(values.join(', '));

  useEffect(() => {
    setText(values.join(', '));
  }, [values]);

  const commit = () => {
    const next = text.split(',').map(s => s.trim()).filter(Boolean);
    const sortedNext = [...next].sort();
    const sortedCurrent = [...values].sort();
    if (JSON.stringify(sortedNext) !== JSON.stringify(sortedCurrent)) {
      onCommit(next);
    }
  };

  return (
    <input
      type="text"
      className={`multi-select__trigger ${compact ? 'multi-select__trigger--compact' : ''}`}
      value={text}
      onChange={e => setText(e.target.value)}
      onBlur={commit}
      onKeyDown={e => {
        if (e.key === 'Enter') {
          e.currentTarget.blur();
        } else if (e.key === 'Escape') {
          setText(values.join(', '));
          e.currentTarget.blur();
        }
      }}
      placeholder={placeholder}
    />
  );
}
