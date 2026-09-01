/**
 * The querents' Greer birth and name cards inside a journal entry: a
 * hook that fetches and flattens them for spread highlighting, and a
 * collapsible panel of mini card tiles under the querent line,
 * grouped the same way the profile modals group them.
 *
 * Matching is by canonical archetype name (resolved through the Tarot
 * archetype list), so the 8/11 display preference can't cause a miss.
 */
import { useMemo, useState } from 'react';
import { useQueries, useQuery } from '@tanstack/react-query';
import { getProfileBirthCards, type BirthCardProfile } from '../../api/birthCards';
import {
  calculateNameCards,
  getNameCardsConfig,
  type NameCardsResult,
} from '../../api/nameCards';
import { getArchetypes, type Archetype } from '../../api/correspondences';
import { cardThumbnailUrl } from '../../api/images';
import type { Profile } from '../../types';
import './QuerentBirthCards.css';

/** Which system(s) flagged a card, for the color coding: birth
 *  cards gold, name cards violet, both when the systems overlap. */
export type IndicationSystem = 'birth' | 'name' | 'both';

export interface BirthCardTag {
  label: string;
  system: IndicationSystem;
}

interface QuerentCardEntry {
  label: string;
  cardName: string;
  cardId: number | null;
}

interface QuerentCardGroup {
  title: string;
  cards: QuerentCardEntry[];
  system: 'birth' | 'name';
}

export interface QuerentBirthCardData {
  /** lowercase canonical archetype name → labels ("Soul", "Anna: Soul") */
  labelsByArchetype: Map<string, BirthCardTag>;
  /** For the panel: per-querent grouped card listings. */
  perQuerent: { name: string; groups: QuerentCardGroup[] }[];
  ready: boolean;
}

/** The minimal shape matching needs — covers Majors, Minors, and the
 *  court ruler alike. */
type CardRefLike = {
  name: string;
  archetype_id: number | null;
  card_id?: number | null;
} | null;

interface LabeledRef {
  label: string;
  ref: CardRefLike;
}

/** Birth-card groups, mirroring the Birth Cards modal's sections. */
function collectBirthGroups(data: BirthCardProfile): {
  title: string; entries: LabeledRef[];
}[] {
  const c = data.cards;
  const hiddenLabel = data.age >= 29 ? 'Teacher' : 'Shadow';
  const core: LabeledRef[] = [];
  if (data.personality === data.soul) {
    core.push({ label: 'Personality & Soul', ref: c.personality });
  } else {
    core.push({ label: 'Personality', ref: c.personality });
    core.push({ label: 'Soul', ref: c.soul });
  }
  core.push({ label: 'Teacher', ref: c.teacher });
  for (const card of c.hidden_factor) core.push({ label: hiddenLabel, ref: card });

  return [
    { title: 'Birth Cards', entries: core },
    {
      title: 'Lessons & Opportunities',
      entries: c.lessons_and_opportunities.map(card => ({
        label: 'Lesson & Opportunity', ref: card,
      })),
    },
    {
      title: 'Zodiacal',
      entries: [
        { label: 'Zodiacal Lesson', ref: c.zodiacal },
        { label: 'Zodiacal Ruler', ref: c.zodiacal_sign_ruler },
        { label: 'Planetary Ruler', ref: c.zodiacal_planet_ruler },
        { label: 'Court Ruler', ref: c.decan_court },
      ],
    },
    {
      title: `Year Card ${data.reference_year}`,
      entries: [{ label: `Year Card ${data.reference_year}`, ref: c.year_card }],
    },
  ];
}

/** Name-card groups, mirroring the Name Cards modal's sections. */
function collectNameGroups(data: NameCardsResult): {
  title: string; entries: LabeledRef[];
}[] {
  const c = data.cards;
  const destiny: LabeledRef[] = [
    { label: 'Theme Note', ref: c.theme_note },
    { label: 'Rhythm', ref: c.rhythm },
    { label: 'Melody', ref: c.melody },
  ];
  for (const card of c.hidden_factor_name) {
    destiny.push({ label: 'Hidden Factor (Name)', ref: card });
  }
  destiny.push({ label: 'Life Potential', ref: c.life_potential });

  return [
    {
      title: 'Theme Chord',
      entries: [
        { label: 'First Name', ref: c.first_name },
        { label: 'Middle Name', ref: c.middle_name },
        { label: 'Last Name', ref: c.last_name },
      ],
    },
    {
      title: 'Inner & Outer',
      entries: [
        { label: 'Desires & Inner Motivation', ref: c.desires_inner_motivation },
        { label: 'Outer Persona', ref: c.outer_persona },
      ],
    },
    { title: 'Theme Note · Rhythm · Melody', entries: destiny },
  ];
}

export function useQuerentBirthCards(
  querents: Profile[] | undefined,
  year: number | undefined,
  enabled: boolean,
): QuerentBirthCardData {
  // Birth cards need a birth date; name cards need a full name. A
  // querent qualifies with either.
  const relevant = (querents ?? []).filter(q => q.birth_date || q.full_name);

  const { data: archetypes = [] } = useQuery<Archetype[]>({
    queryKey: ['archetypes', 'Tarot'],
    queryFn: () => getArchetypes('Tarot'),
    enabled: enabled && relevant.length > 0,
    staleTime: 60_000,
  });

  const birthResults = useQueries({
    queries: relevant.map(q => ({
      queryKey: ['birth-cards-for-entry', q.id, year],
      queryFn: () => getProfileBirthCards(q.id, { year }),
      enabled: enabled && !!q.birth_date,
      staleTime: 60_000,
    })),
  });

  // Name cards ride the saved per-profile adjustments, exactly like
  // the Name Cards modal's birth-name view.
  const nameResults = useQueries({
    queries: relevant.map(q => ({
      queryKey: ['name-cards-for-entry', q.id],
      queryFn: async (): Promise<NameCardsResult | null> => {
        const saved = await getNameCardsConfig(q.id);
        const fullName = (saved.full_name || '').trim();
        if (!fullName) return null;
        const cfg = saved.config ?? {};
        try {
          return await calculateNameCards({
            parts: cfg.parts?.length ? cfg.parts : fullName.split(/\s+/),
            roles: cfg.roles ?? null,
            y_mode: cfg.y_mode ?? 'heuristic',
            y_overrides: cfg.y_overrides ?? [],
            drop_suffixes: cfg.drop_suffixes ?? true,
            profile_id: q.id,
          });
        } catch {
          return null;   // e.g. non-Latin name — skip quietly here
        }
      },
      enabled: enabled && !!q.full_name,
      staleTime: 60_000,
    })),
  });

  return useMemo(() => {
    const canonicalById = new Map(archetypes.map(a => [a.id, a.name]));
    const labelsByArchetype = new Map<string, BirthCardTag>();
    const perQuerent: { name: string; groups: QuerentCardGroup[] }[] = [];
    const multi = relevant.length > 1;

    relevant.forEach((q, i) => {
      const groups: QuerentCardGroup[] = [];
      const addGroup = (title: string, entries: LabeledRef[], system: 'birth' | 'name') => {
        const cards: QuerentCardEntry[] = [];
        for (const { label, ref } of entries) {
          if (!ref) continue;
          const canonical = (ref.archetype_id != null
            ? canonicalById.get(ref.archetype_id)
            : undefined) ?? ref.name;
          cards.push({ label, cardName: canonical, cardId: ref.card_id ?? null });
          const key = canonical.toLowerCase();
          const tagged = multi ? `${q.name}: ${label}` : label;
          const prior = labelsByArchetype.get(key);
          labelsByArchetype.set(key, {
            label: prior ? `${prior.label} · ${tagged}` : tagged,
            system: prior && prior.system !== system ? 'both' : (prior?.system ?? system),
          });
        }
        if (cards.length) groups.push({ title, cards, system });
      };

      const birth = birthResults[i]?.data;
      if (birth) {
        for (const g of collectBirthGroups(birth)) addGroup(g.title, g.entries, 'birth');
      }
      const nameData = nameResults[i]?.data;
      if (nameData) {
        for (const g of collectNameGroups(nameData)) addGroup(g.title, g.entries, 'name');
      }
      if (groups.length) perQuerent.push({ name: q.name, groups });
    });

    const settled = (r: { data?: unknown; isError: boolean } | undefined,
                     wanted: boolean) => !wanted || !!(r && (r.data !== undefined || r.isError));
    return {
      labelsByArchetype,
      perQuerent,
      ready: relevant.length > 0 && relevant.every((q, i) =>
        settled(birthResults[i], !!q.birth_date)
        && settled(nameResults[i], !!q.full_name)),
    };
  }, [archetypes, birthResults, nameResults, relevant]);
}

/** Collapsible mini-tile listing under the querent line. */
export function QuerentBirthCardsPanel({ data, onCardClick }: {
  data: QuerentBirthCardData;
  /** Opens the card viewer for a tile's default-deck card. */
  onCardClick?: (cardId: number) => void;
}) {
  const [open, setOpen] = useState(false);
  if (!data.perQuerent.length) return null;
  return (
    <div className="querent-birth-cards">
      <button
        type="button"
        className="querent-birth-cards__toggle"
        aria-expanded={open}
        onClick={() => setOpen(o => !o)}
      >
        <span
          className={`querent-birth-cards__chevron ${open ? 'querent-birth-cards__chevron--open' : ''}`}
          aria-hidden="true"
        >
          ▸
        </span>
        Birth &amp; name cards
      </button>
      {open && (
        <div className="querent-birth-cards__legend" aria-hidden="true">
          <span className="querent-birth-cards__legend-item querent-birth-cards__legend-item--birth">birth cards</span>
          <span className="querent-birth-cards__legend-item querent-birth-cards__legend-item--name">name cards</span>
        </div>
      )}
      {open && data.perQuerent.map(q => (
        <div key={q.name} className="querent-birth-cards__querent">
          {data.perQuerent.length > 1 && (
            <span className="querent-birth-cards__querent-name">{q.name}</span>
          )}
          {q.groups.map(group => (
            <div key={group.title} className={`querent-birth-cards__group querent-birth-cards__group--${group.system}`}>
              <div className="querent-birth-cards__group-title">{group.title}</div>
              <div className="querent-birth-cards__tiles">
                {group.cards.map((entry, i) => {
                  const clickable = entry.cardId != null && onCardClick;
                  return (
                    <button
                      key={i}
                      type="button"
                      className={`querent-birth-cards__tile ${clickable ? 'querent-birth-cards__tile--clickable' : ''}`}
                      title={`${entry.cardName} — ${entry.label}`}
                      disabled={!clickable}
                      onClick={() => {
                        if (entry.cardId != null) onCardClick?.(entry.cardId);
                      }}
                    >
                      {entry.cardId != null ? (
                        <img src={cardThumbnailUrl(entry.cardId)} alt={entry.cardName} />
                      ) : (
                        <div className="querent-birth-cards__tile-fallback">
                          {entry.cardName}
                        </div>
                      )}
                      <span className="querent-birth-cards__tile-caption">
                        {entry.label}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}
