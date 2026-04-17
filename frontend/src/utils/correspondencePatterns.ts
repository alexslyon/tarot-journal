import type { CorrespondenceAssignment } from '../types';
import { CORRESPONDENCE_FIELDS, CORRESPONDENCE_FIELD_LABELS } from '../types';

export interface GroupPattern {
  groupLabel: string;
  fieldName: string;
  fieldLabel: string;
  value: string;
}

/** Detect group-level patterns from source_group-tagged assignments.
 *
 * Any source_group that has entries with consistent values across all its
 * members produces a pattern. Works for any custom group the user creates.
 */
export function detectGroupPatterns(
  assignments: CorrespondenceAssignment[],
): GroupPattern[] {
  // group -> field -> Map<archetype_id, value>
  const groupFieldValues = new Map<string, Map<string, Map<number, string>>>();

  for (const a of assignments) {
    if (!a.source_group) continue;
    if (!groupFieldValues.has(a.source_group)) {
      groupFieldValues.set(a.source_group, new Map());
    }
    const fieldMap = groupFieldValues.get(a.source_group)!;
    if (!fieldMap.has(a.field_name)) fieldMap.set(a.field_name, new Map());
    fieldMap.get(a.field_name)!.set(a.archetype_id, a.field_value);
  }

  const patterns: GroupPattern[] = [];

  for (const [groupLabel, fieldMap] of groupFieldValues) {
    for (const field of CORRESPONDENCE_FIELDS) {
      const entries = fieldMap.get(field);
      if (!entries || entries.size === 0) continue;
      const uniqueValues = new Set(entries.values());
      if (uniqueValues.size === 1) {
        patterns.push({
          groupLabel,
          fieldName: field,
          fieldLabel: CORRESPONDENCE_FIELD_LABELS[field],
          value: [...uniqueValues][0],
        });
      }
    }
  }

  return patterns;
}

/** Group patterns by field label for display. */
export function groupPatternsByField(patterns: GroupPattern[]): Map<string, GroupPattern[]> {
  const map = new Map<string, GroupPattern[]>();
  for (const p of patterns) {
    if (!map.has(p.fieldLabel)) map.set(p.fieldLabel, []);
    map.get(p.fieldLabel)!.push(p);
  }
  return map;
}

// Canonical display order for known group labels — keeps related groups together
const GROUP_ORDER = [
  'Major Arcana',
  'All Minor Arcana',
  // Suits
  'Wands', 'Cups', 'Swords', 'Pentacles',
  // Court ranks
  'All Pages', 'All Knights', 'All Queens', 'All Kings', 'All Court Cards',
  // Pip numbers
  'All Aces', 'All Twos', 'All Threes', 'All Fours', 'All Fives',
  'All Sixes', 'All Sevens', 'All Eights', 'All Nines', 'All Tens',
  'All Pips (Ace-10)',
];

/** Group patterns by card-group label for display, sorted by canonical order. */
export function groupPatternsByGroup(patterns: GroupPattern[]): Map<string, GroupPattern[]> {
  const unordered = new Map<string, GroupPattern[]>();
  for (const p of patterns) {
    if (!unordered.has(p.groupLabel)) unordered.set(p.groupLabel, []);
    unordered.get(p.groupLabel)!.push(p);
  }

  // Build an ordered Map: canonical order first, then any unknown labels alphabetically
  const ordered = new Map<string, GroupPattern[]>();
  for (const label of GROUP_ORDER) {
    if (unordered.has(label)) {
      ordered.set(label, unordered.get(label)!);
      unordered.delete(label);
    }
  }
  // Remaining custom labels — sort alphabetically
  const remaining = [...unordered.keys()].sort();
  for (const label of remaining) {
    ordered.set(label, unordered.get(label)!);
  }
  return ordered;
}
