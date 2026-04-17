import type { CorrespondenceAssignment } from '../types';
import { CORRESPONDENCE_FIELDS, CORRESPONDENCE_FIELD_LABELS } from '../types';

export interface GroupPattern {
  groupLabel: string;
  fieldName: string;
  fieldLabel: string;
  value: string;
}

/** Detect group-level patterns: values shared by all cards in a group. */
export function detectGroupPatterns(
  assignments: CorrespondenceAssignment[],
): GroupPattern[] {
  const cards = new Map<number, {
    name: string;
    suit: string | null;
    card_type: string | null;
    fields: Map<string, string>;
  }>();

  for (const a of assignments) {
    if (!cards.has(a.archetype_id)) {
      cards.set(a.archetype_id, {
        name: a.archetype_name,
        suit: a.suit,
        card_type: a.card_type,
        fields: new Map(),
      });
    }
    cards.get(a.archetype_id)!.fields.set(a.field_name, a.field_value);
  }

  const allCards = [...cards.values()];
  const patterns: GroupPattern[] = [];

  const groups: { label: string; filter: (c: typeof allCards[0]) => boolean }[] = [
    { label: 'Wands', filter: c => c.suit === 'Wands' },
    { label: 'Cups', filter: c => c.suit === 'Cups' },
    { label: 'Swords', filter: c => c.suit === 'Swords' },
    { label: 'Pentacles', filter: c => c.suit === 'Pentacles' },
    { label: 'Pages', filter: c => c.name.startsWith('Page of') },
    { label: 'Knights', filter: c => c.name.startsWith('Knight of') },
    { label: 'Queens', filter: c => c.name.startsWith('Queen of') },
    { label: 'Kings', filter: c => c.name.startsWith('King of') },
    { label: 'Aces', filter: c => c.name.startsWith('Ace of') },
    { label: 'Major Arcana', filter: c => c.card_type === 'major' },
  ];

  for (const group of groups) {
    const members = allCards.filter(group.filter);
    if (members.length < 2) continue;

    for (const field of CORRESPONDENCE_FIELDS) {
      const values = members.map(m => m.fields.get(field)).filter(Boolean);
      if (values.length === members.length) {
        const unique = new Set(values);
        if (unique.size === 1) {
          patterns.push({
            groupLabel: group.label,
            fieldName: field,
            fieldLabel: CORRESPONDENCE_FIELD_LABELS[field],
            value: values[0]!,
          });
        }
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
