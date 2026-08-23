import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import Modal from '../common/Modal';
import QueryError from '../common/QueryError';
import {
  getProfileBirthCards,
  setBirthCardPrefs,
  type BirthCardMethod,
  type CourtSystem,
  type EightEleven,
  type MajorCardRef,
  type MinorCardRef,
} from '../../api/birthCards';
import { cardThumbnailUrl } from '../../api/images';
import './BirthCardsModal.css';

interface BirthCardsModalProps {
  open: boolean;
  onClose: () => void;
  profileId: number;
  profileName: string;
}

/** One card tile: deck image when the default Tarot deck has the card,
 *  otherwise a text placeholder in card proportions. Shared with the
 *  Name Cards modal (which also reuses the .birth-cards tile CSS). */
export function CardTile({ card, caption, small }: {
  card: { name: string; card_id: number | null } | MajorCardRef | MinorCardRef;
  caption?: string;
  small?: boolean;
}) {
  const cls = small ? 'birth-cards__tile birth-cards__tile--small' : 'birth-cards__tile';
  return (
    <div className={cls}>
      {card.card_id != null ? (
        <img
          className="birth-cards__tile-img"
          src={cardThumbnailUrl(card.card_id)}
          alt={card.name}
        />
      ) : (
        <div className="birth-cards__tile-placeholder">{card.name}</div>
      )}
      <div className="birth-cards__tile-name">{card.name}</div>
      {caption && <div className="birth-cards__tile-caption">{caption}</div>}
    </div>
  );
}

export default function BirthCardsModal({
  open,
  onClose,
  profileId,
  profileName,
}: BirthCardsModalProps) {
  const queryClient = useQueryClient();
  // null = use the saved preference; the response echoes what applied.
  const [method, setMethod] = useState<BirthCardMethod | null>(null);
  const [eightEleven, setEightEleven] = useState<EightEleven | null>(null);
  const [courtSystem, setCourtSystem] = useState<CourtSystem | null>(null);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['birth-cards', profileId, method, eightEleven, courtSystem],
    queryFn: () => getProfileBirthCards(profileId, {
      method: method ?? undefined,
      eightEleven: eightEleven ?? undefined,
      courtSystem: courtSystem ?? undefined,
    }),
    enabled: open,
    staleTime: 30_000,
  });

  const changeMethod = (m: BirthCardMethod) => {
    setMethod(m);
    // Persist as the new default; errors are non-fatal (display still updates)
    setBirthCardPrefs({ method: m })
      .then(() => queryClient.invalidateQueries({ queryKey: ['birth-cards'] }))
      .catch(() => {});
  };

  const changeEightEleven = (v: EightEleven) => {
    setEightEleven(v);
    setBirthCardPrefs({ eight_eleven: v })
      .then(() => queryClient.invalidateQueries({ queryKey: ['birth-cards'] }))
      .catch(() => {});
  };

  const changeCourtSystem = (v: CourtSystem) => {
    setCourtSystem(v);
    setBirthCardPrefs({ court_system: v })
      .then(() => queryClient.invalidateQueries({ queryKey: ['birth-cards'] }))
      .catch(() => {});
  };

  const c = data?.cards;
  // Same card in both roles for single-digit patterns — show it once.
  const soulIsPersonality = data != null && data.personality === data.soul;
  // Shadow vs Teacher framing is keyed to the Saturn return (~29).
  const hiddenLabel = data == null ? 'Hidden Factor'
    : data.age >= 29 ? 'Teacher Card' : 'Shadow Card';

  return (
    <Modal open={open} onClose={onClose} title={`Birth Cards — ${profileName}`} width={860}>
      <div className="birth-cards">
        {isLoading && <div className="birth-cards__loading">Calculating…</div>}
        {isError && <QueryError what="birth cards" onRetry={() => refetch()} />}

        {data && c && (
          <>
            <div className="birth-cards__header">
              <span className="birth-cards__pattern" title="Constellation pattern">
                {data.pattern}
              </span>
              <span className="birth-cards__birthdate">
                born {data.birth_date}
              </span>
              <div className="birth-cards__controls">
                <label className="birth-cards__control">
                  <span>Method</span>
                  <select
                    value={data.method}
                    onChange={(e) => changeMethod(e.target.value as BirthCardMethod)}
                  >
                    <option value="greer">Greer</option>
                    <option value="amberstone">Amberstone</option>
                  </select>
                </label>
                <label className="birth-cards__control">
                  <span>8 / 11</span>
                  <select
                    value={data.eight_eleven}
                    onChange={(e) => changeEightEleven(e.target.value as EightEleven)}
                  >
                    <option value="golden_dawn">8 Strength · 11 Justice</option>
                    <option value="marseille">8 Justice · 11 Strength</option>
                  </select>
                </label>
                <label className="birth-cards__control">
                  <span>Courts</span>
                  <select
                    value={data.court_system ?? 'golden_dawn'}
                    onChange={(e) => changeCourtSystem(e.target.value as CourtSystem)}
                  >
                    <option value="golden_dawn">Golden Dawn</option>
                    <option value="bota">B.O.T.A.</option>
                  </select>
                </label>
              </div>
            </div>
            <p className="birth-cards__method-note">
              The Soul Card is the same under every addition method; the
              Personality Card (and what follows from it) can differ between
              Greer and Amberstone. The 8/11 choice only relabels
              Strength and Justice — it never changes the math.
            </p>

            <div className="birth-cards__section">
              <h3 className="birth-cards__heading">
                {soulIsPersonality ? 'Personality & Soul' : 'Personality and Soul Cards'}
              </h3>
              <div className="birth-cards__row">
                {soulIsPersonality ? (
                  <CardTile card={c.personality} caption="Personality & Soul in one card" />
                ) : (
                  <>
                    <CardTile card={c.personality} caption="Personality" />
                    <CardTile card={c.soul} caption="Soul" />
                  </>
                )}
                {c.teacher && <CardTile card={c.teacher} caption="Teacher" />}
                {c.hidden_factor.map((card) => (
                  <CardTile key={card.number} card={card} caption={hiddenLabel} />
                ))}
              </div>
              {data.nighttime && (
                <p className="birth-cards__note">
                  A “nighttime” pattern: the shadow isn’t a separate card here —
                  it folds into the Personality Card itself.
                </p>
              )}
              {data.pattern === '22-4' && (
                <p className="birth-cards__note">
                  The Fool and the Emperor work as a unit in this pattern.
                </p>
              )}
              {data.pattern === '19-10-1' && (
                <p className="birth-cards__note">
                  The rare triple pattern: Sun personality, Magician soul, with
                  the Wheel of Fortune as Teacher.
                </p>
              )}
            </div>

            <div className="birth-cards__section">
              <h3 className="birth-cards__heading">
                Constellation of {c.soul.name}
              </h3>
              <div className="birth-cards__row">
                {c.constellation_majors.map((card) => (
                  <CardTile key={card.number} card={card} small />
                ))}
              </div>
            </div>

            <div className="birth-cards__section">
              <h3 className="birth-cards__heading">Lessons & Opportunities</h3>
              <div className="birth-cards__row">
                {c.lessons_and_opportunities.map((card) => (
                  <CardTile key={card.name} card={card} small />
                ))}
              </div>
            </div>

            <div className="birth-cards__section">
              <h3 className="birth-cards__heading">Zodiacal Lesson & Opportunity</h3>
              <div className="birth-cards__row">
                <CardTile card={c.zodiacal} small caption="From the birthday's decan" />
                {/* Guarded so a stale backend (older response shape)
                    degrades to just the decan card, not a crash */}
                {c.zodiacal_sign_ruler && data.zodiacal_rulers && (
                  <CardTile
                    card={c.zodiacal_sign_ruler}
                    small
                    caption={`Zodiacal ruler — ${data.zodiacal_rulers.sign}`}
                  />
                )}
                {c.zodiacal_planet_ruler && data.zodiacal_rulers && (
                  <CardTile
                    card={c.zodiacal_planet_ruler}
                    small
                    caption={`Planetary ruler — ${data.zodiacal_rulers.planet}`}
                  />
                )}
                {c.decan_court && data.decan_court && (
                  <CardTile
                    card={c.decan_court}
                    small
                    caption={`Court ruler — ${data.decan_court.span}`}
                  />
                )}
              </div>
            </div>

            <div className="birth-cards__section">
              <h3 className="birth-cards__heading">Dynamic</h3>
              <p className="birth-cards__text">
                {data.fool_center
                  ? 'The Fool sits at the center of all three soul groups.'
                  : `Soul group ${data.dynamic} of 3 — shared with everyone whose Personality Card falls in the same hexagram.`}
              </p>
            </div>

            <div className="birth-cards__section">
              <h3 className="birth-cards__heading">
                {data.reference_year} Cards
              </h3>
              <div className="birth-cards__row">
                <CardTile card={c.year_card} small caption={`Year Card ${data.reference_year}`} />
                <CardTile card={c.personal_month} small caption="Personal Month" />
                <CardTile card={c.generic_year} small caption="Generic Year (everyone's)" />
              </div>
              <p className="birth-cards__note">
                Read the Year Card two ways: January-to-January for outer
                events, birthday-to-birthday for inner motivation.
                Karmic Year: <strong>{data.karmic_year}</strong> — the birth
                total read as a calendar year.
              </p>
            </div>

            <p className="birth-cards__footnote">
              Numbers follow Mary K. Greer's <em>Archetypal Tarot</em>.
            </p>
          </>
        )}
      </div>
    </Modal>
  );
}
