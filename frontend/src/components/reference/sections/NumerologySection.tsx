import '../ReferenceTab.css';

interface NumerologyEntry {
  number: number;
  title: string;
  meaning: string;
  tarotConnection: string;
}

const NUMEROLOGY_DATA: NumerologyEntry[] = [
  {
    number: 0,
    title: 'The Void / Infinite Potential',
    meaning: 'Nothingness and everything. The unmanifest, pure potential before form. Freedom from limitation.',
    tarotConnection: 'The Fool — the leap into the unknown, beginningless beginning.',
  },
  {
    number: 1,
    title: 'Unity / Beginnings',
    meaning: 'Individuality, initiative, will, leadership, new starts. The seed, the self, the singular point of origin.',
    tarotConnection: 'The Magician and Aces — raw potential channeled into action.',
  },
  {
    number: 2,
    title: 'Duality / Balance',
    meaning: 'Partnership, polarity, receptivity, patience, choice between opposites. The first division — self and other.',
    tarotConnection: 'The High Priestess and Twos — the threshold between known and unknown.',
  },
  {
    number: 3,
    title: 'Creation / Expression',
    meaning: 'Growth, creativity, synthesis, expansion, abundance. What emerges from the union of two — the child, the fruit.',
    tarotConnection: 'The Empress and Threes — creative abundance and early fruition.',
  },
  {
    number: 4,
    title: 'Structure / Foundation',
    meaning: 'Stability, order, discipline, foundation, hard work. The four walls, the four directions — manifestation made solid.',
    tarotConnection: 'The Emperor and Fours — authority, structure, and groundedness.',
  },
  {
    number: 5,
    title: 'Change / Conflict',
    meaning: 'Disruption, freedom, adventure, instability, challenge. The number that breaks the settled four — crisis and growth.',
    tarotConnection: 'The Hierophant and Fives — upheaval that leads to deeper understanding.',
  },
  {
    number: 6,
    title: 'Harmony / Responsibility',
    meaning: 'Love, beauty, balance, nurturing, duty, home. Equilibrium restored after the disruption of five.',
    tarotConnection: 'The Lovers and Sixes — choices made from the heart, reciprocity.',
  },
  {
    number: 7,
    title: 'Introspection / Mystery',
    meaning: 'Wisdom, analysis, solitude, spirituality, inner work. The seeker turning inward — not everything is visible.',
    tarotConnection: 'The Chariot and Sevens — inner mastery and faith through uncertainty.',
  },
  {
    number: 8,
    title: 'Power / Mastery',
    meaning: 'Achievement, abundance, karma, material success, regeneration. Infinite energy (the lemniscate) applied with discipline.',
    tarotConnection: 'Strength and Eights — endurance, control, and the consequences of effort.',
  },
  {
    number: 9,
    title: 'Completion / Wisdom',
    meaning: 'Fulfillment, humanitarianism, endings, universal compassion. The last single digit — the culmination of a cycle.',
    tarotConnection: 'The Hermit and Nines — solitary wisdom at the end of a journey.',
  },
  {
    number: 10,
    title: 'Cycle / Renewal',
    meaning: 'Completion and new beginning combined. The full turn of the wheel — endings that contain seeds of the next cycle.',
    tarotConnection: 'Wheel of Fortune and Tens — the cycle complete, turning toward what comes next.',
  },
];

export default function NumerologySection() {
  return (
    <div className="reference-section">
      <h2 className="reference-section__title">Numerology</h2>
      <p className="reference-section__hint">
        Number meanings as they apply to tarot. Each number carries archetypal significance
        that threads through the Major Arcana, pip cards, and numerological practice.
      </p>

      {NUMEROLOGY_DATA.map(entry => (
        <div key={entry.number} className="reference-section__card">
          <div style={{ display: 'flex', gap: 12, alignItems: 'baseline', marginBottom: 8 }}>
            <span style={{
              fontSize: 'var(--font-size-title)',
              fontWeight: 700,
              color: 'var(--accent)',
              minWidth: 28,
            }}>
              {entry.number}
            </span>
            <h3 style={{
              fontSize: 'var(--font-size-heading)',
              color: 'var(--text-primary)',
              margin: 0,
            }}>
              {entry.title}
            </h3>
          </div>
          <p style={{
            fontSize: 'var(--font-size-body)',
            color: 'var(--text-primary)',
            margin: '0 0 8px',
            lineHeight: 1.5,
          }}>
            {entry.meaning}
          </p>
          <p style={{
            fontSize: 'var(--font-size-small)',
            color: 'var(--text-secondary)',
            margin: 0,
            fontStyle: 'italic',
          }}>
            {entry.tarotConnection}
          </p>
        </div>
      ))}
    </div>
  );
}
