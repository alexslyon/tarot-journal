import { useEffect, useState } from 'react';

/** Returns `value`, but only after it has stopped changing for
 *  `delayMs`. Used to make search-as-you-type feel instant without
 *  firing a request on every keystroke. */
export function useDebouncedValue<T>(value: T, delayMs = 300): T {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(timer);
  }, [value, delayMs]);

  return debounced;
}
