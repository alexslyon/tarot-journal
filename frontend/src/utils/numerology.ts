/**
 * Compute the digit-sum reduction chain for a numeric string. Does NOT
 * include the input value itself.
 *
 * Examples:
 *   "156" -> ["12", "3"]
 *   "12"  -> ["3"]
 *   "9"   -> []
 *   "abc" -> []   (non-numeric values are skipped)
 *   ""    -> []
 *
 * The chain reduces all the way to a single digit. Master numbers (11, 22)
 * are not preserved — if a numerologist needs them unreduced they can simply
 * delete the further-reduced value after entry.
 */
export function numerologyReductions(value: string): string[] {
  if (!/^\d+$/.test(value) || value.length <= 1) return [];
  const out: string[] = [];
  let current = value;
  while (current.length > 1) {
    let sum = 0;
    for (const ch of current) sum += parseInt(ch, 10);
    current = String(sum);
    out.push(current);
  }
  return out;
}

/**
 * Expand a numerology value list after a commit, appending the digit-sum
 * reductions of any value that's NEW relative to `previous`. Reductions that
 * existed before but were just removed by the user stay removed.
 */
export function expandNumerologyOnAdd(
  previous: string[],
  next: string[],
): string[] {
  const previousSet = new Set(previous);
  const seen = new Set(next);
  const result = [...next];
  for (const v of next) {
    if (previousSet.has(v)) continue; // unchanged or pre-existing
    for (const r of numerologyReductions(v)) {
      if (!seen.has(r)) {
        seen.add(r);
        result.push(r);
      }
    }
  }
  return result;
}
