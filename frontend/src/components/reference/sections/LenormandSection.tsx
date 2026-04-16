import { useState } from 'react';
import '../ReferenceTab.css';

interface LenormandCard {
  number: number;
  name: string;
  keywords: string;
  playingCard: string;
}

const LENORMAND_CARDS: LenormandCard[] = [
  { number: 1, name: 'Rider', keywords: 'News, messages, a visitor, speed, something new arriving', playingCard: '9 of Hearts' },
  { number: 2, name: 'Clover', keywords: 'Luck, opportunity, small happiness, lightheartedness', playingCard: '6 of Diamonds' },
  { number: 3, name: 'Ship', keywords: 'Travel, distance, commerce, longing, foreign matters', playingCard: '10 of Spades' },
  { number: 4, name: 'House', keywords: 'Home, stability, family, real estate, traditions', playingCard: 'King of Hearts' },
  { number: 5, name: 'Tree', keywords: 'Health, growth, roots, life, slow steady progress', playingCard: '7 of Hearts' },
  { number: 6, name: 'Clouds', keywords: 'Confusion, doubt, uncertainty, hidden truth, temporary trouble', playingCard: 'King of Clubs' },
  { number: 7, name: 'Snake', keywords: 'Complication, detour, seduction, wisdom, an older woman', playingCard: 'Queen of Clubs' },
  { number: 8, name: 'Coffin', keywords: 'Ending, loss, transformation, illness, something buried', playingCard: '9 of Diamonds' },
  { number: 9, name: 'Bouquet', keywords: 'Gift, beauty, invitation, happiness, appreciation', playingCard: 'Queen of Spades' },
  { number: 10, name: 'Scythe', keywords: 'Sudden event, cutting away, harvest, danger, decision', playingCard: 'Jack of Diamonds' },
  { number: 11, name: 'Whip', keywords: 'Conflict, discussion, repetition, physical activity, tension', playingCard: 'Jack of Clubs' },
  { number: 12, name: 'Birds', keywords: 'Communication, phone calls, nervousness, a couple, chatter', playingCard: '7 of Diamonds' },
  { number: 13, name: 'Child', keywords: 'New beginning, innocence, small, inexperience, a child', playingCard: 'Jack of Spades' },
  { number: 14, name: 'Fox', keywords: 'Cunning, work, self-employment, deception, survival', playingCard: '9 of Clubs' },
  { number: 15, name: 'Bear', keywords: 'Strength, power, boss, finances, mother figure, diet', playingCard: '10 of Clubs' },
  { number: 16, name: 'Stars', keywords: 'Hope, guidance, spirituality, clarity, networking, the internet', playingCard: '6 of Hearts' },
  { number: 17, name: 'Stork', keywords: 'Change, movement, improvement, pregnancy, relocation', playingCard: 'Queen of Hearts' },
  { number: 18, name: 'Dog', keywords: 'Friendship, loyalty, trust, a friend, following', playingCard: '10 of Hearts' },
  { number: 19, name: 'Tower', keywords: 'Authority, institution, solitude, ambition, boundaries', playingCard: '6 of Spades' },
  { number: 20, name: 'Garden', keywords: 'Public, social events, group, reputation, nature', playingCard: '8 of Spades' },
  { number: 21, name: 'Mountain', keywords: 'Obstacle, blockage, delay, challenge, stubbornness', playingCard: '8 of Clubs' },
  { number: 22, name: 'Crossroads', keywords: 'Choice, decision, options, freedom, multiple paths', playingCard: 'Queen of Diamonds' },
  { number: 23, name: 'Mice', keywords: 'Loss, worry, theft, stress, something diminishing', playingCard: '7 of Clubs' },
  { number: 24, name: 'Heart', keywords: 'Love, passion, romance, compassion, the emotional core', playingCard: 'Jack of Hearts' },
  { number: 25, name: 'Ring', keywords: 'Commitment, contract, partnership, cycle, connection', playingCard: 'Ace of Clubs' },
  { number: 26, name: 'Book', keywords: 'Secret, knowledge, education, unknown information', playingCard: '10 of Diamonds' },
  { number: 27, name: 'Letter', keywords: 'Document, message, email, written communication, news', playingCard: '7 of Spades' },
  { number: 28, name: 'Man', keywords: 'Male significator, a man in the querent\'s life', playingCard: 'Ace of Hearts' },
  { number: 29, name: 'Woman', keywords: 'Female significator, a woman in the querent\'s life', playingCard: 'Ace of Spades' },
  { number: 30, name: 'Lily', keywords: 'Peace, maturity, sensuality, wisdom, family harmony', playingCard: 'King of Spades' },
  { number: 31, name: 'Sun', keywords: 'Success, happiness, energy, vitality, warmth, achievement', playingCard: 'Ace of Diamonds' },
  { number: 32, name: 'Moon', keywords: 'Emotions, intuition, recognition, fame, subconscious', playingCard: '8 of Hearts' },
  { number: 33, name: 'Key', keywords: 'Solution, certainty, opening, achievement, importance', playingCard: '8 of Diamonds' },
  { number: 34, name: 'Fish', keywords: 'Money, business, abundance, independence, flow', playingCard: 'King of Diamonds' },
  { number: 35, name: 'Anchor', keywords: 'Stability, work, perseverance, reaching a goal, holding on', playingCard: '9 of Spades' },
  { number: 36, name: 'Cross', keywords: 'Burden, suffering, fate, religion, heavy responsibility', playingCard: '6 of Clubs' },
];

export default function LenormandSection() {
  const [filterText, setFilterText] = useState('');

  const filtered = LENORMAND_CARDS.filter(card => {
    if (!filterText) return true;
    const q = filterText.toLowerCase();
    return card.name.toLowerCase().includes(q)
      || card.keywords.toLowerCase().includes(q)
      || String(card.number).includes(q);
  });

  return (
    <div className="reference-section">
      <h2 className="reference-section__title">Lenormand</h2>
      <p className="reference-section__hint">
        Standard Lenormand card meanings with associated playing cards. Keywords represent common traditional interpretations.
      </p>

      <input
        type="text"
        value={filterText}
        onChange={e => setFilterText(e.target.value)}
        placeholder="Search cards or keywords..."
        style={{ marginBottom: 16, maxWidth: 300, width: '100%' }}
      />

      <div className="reference-section__card">
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 'var(--font-size-body)' }}>
          <thead>
            <tr>
              <th style={{ textAlign: 'left', padding: '6px 8px', borderBottom: '1px solid var(--border)', color: 'var(--text-secondary)', fontWeight: 600 }}>#</th>
              <th style={{ textAlign: 'left', padding: '6px 8px', borderBottom: '1px solid var(--border)', color: 'var(--text-secondary)', fontWeight: 600 }}>Card</th>
              <th style={{ textAlign: 'left', padding: '6px 8px', borderBottom: '1px solid var(--border)', color: 'var(--text-secondary)', fontWeight: 600 }}>Playing Card</th>
              <th style={{ textAlign: 'left', padding: '6px 8px', borderBottom: '1px solid var(--border)', color: 'var(--text-secondary)', fontWeight: 600 }}>Keywords</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map(card => (
              <tr key={card.number}>
                <td style={{ padding: '6px 8px', borderBottom: '1px solid var(--border)', color: 'var(--text-dim)', whiteSpace: 'nowrap' }}>
                  {card.number}
                </td>
                <td style={{ padding: '6px 8px', borderBottom: '1px solid var(--border)', color: 'var(--text-primary)', fontWeight: 500, whiteSpace: 'nowrap' }}>
                  {card.name}
                </td>
                <td style={{ padding: '6px 8px', borderBottom: '1px solid var(--border)', color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>
                  {card.playingCard}
                </td>
                <td style={{ padding: '6px 8px', borderBottom: '1px solid var(--border)', color: 'var(--text-primary)' }}>
                  {card.keywords}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
