/**
 * The interactive decan wheel: outer ring of 12 sign glyphs, inner
 * ring of 36 decan segments (each showing its ruling planet's glyph —
 * the Chaldean sequence made visible), and an optional overlay of the
 * twelve 30° court arcs. Click a decan for its full story: dates,
 * Minor, sign trump, planetary ruler, and its court under all three
 * systems side by side.
 *
 * Aries sits at 12 o'clock, the year running clockwise. Fixed
 * calendar dates (Greer's tables), deliberately not an ephemeris.
 */
import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getProfiles } from '../../../api/profiles';
import { getProfileBirthCards, type CourtSystem } from '../../../api/birthCards';
import type { AstrologyData, SignRef } from '../../../api/reference';
import type { Profile } from '../../../types';
import { RefTile } from './referenceShared';
import './DecanWheel.css';

const COURT_SYSTEM_SHORT: Record<CourtSystem, string> = {
  golden_dawn: 'Golden Dawn (Book T)',
  golden_dawn_waite: 'Golden Dawn (Waite)',
  bota: 'B.O.T.A.',
};

const CX = 320;
const CY = 320;

function point(r: number, deg: number): [number, number] {
  const rad = (deg * Math.PI) / 180;
  return [CX + r * Math.cos(rad), CY + r * Math.sin(rad)];
}

/** Annular sector from a0° to a1° (clockwise) between radii r0 < r1. */
function sector(r0: number, r1: number, a0: number, a1: number): string {
  const large = a1 - a0 > 180 ? 1 : 0;
  const [x1, y1] = point(r1, a0);
  const [x2, y2] = point(r1, a1);
  const [x3, y3] = point(r0, a1);
  const [x4, y4] = point(r0, a0);
  return [
    `M ${x1} ${y1}`,
    `A ${r1} ${r1} 0 ${large} 1 ${x2} ${y2}`,
    `L ${x3} ${y3}`,
    `A ${r0} ${r0} 0 ${large} 0 ${x4} ${y4}`,
    'Z',
  ].join(' ');
}

/** Wheel angle of a global decan index's start: Aries I begins at the
 *  top (-90°), each decan is 10°. */
const decanStart = (i: number) => -90 + i * 10;

interface DecanWheelProps {
  data: AstrologyData;
  openCard: (cardId: number) => void;
}

export default function DecanWheel({ data, openCard }: DecanWheelProps) {
  const [selected, setSelected] = useState<number | null>(null);
  const [hovered, setHovered] = useState<number | null>(null);
  const [showCourts, setShowCourts] = useState(false);
  const [profileId, setProfileId] = useState<number | null>(null);

  const planetGlyphs = useMemo(
    () => Object.fromEntries(data.planets.map(p => [p.name, p.glyph])),
    [data.planets],
  );

  // Flatten: global decan index 0-35 -> (sign, decan)
  const decans = useMemo(
    () => data.signs.flatMap(sign => sign.decans.map(d => ({ sign, decan: d }))),
    [data.signs],
  );

  const todayIndex =
    data.signs.findIndex(s => s.name === data.today_decan.sign) * 3 +
    (data.today_decan.index - 1);

  // Optional profile birth-decan marker
  const { data: profiles = [] } = useQuery<Profile[]>({
    queryKey: ['profiles'],
    queryFn: getProfiles,
  });
  const datedProfiles = profiles.filter(p => p.birth_date);
  const { data: profileBirthCards } = useQuery({
    queryKey: ['birth-cards', profileId, null, null, null],
    queryFn: () => getProfileBirthCards(profileId as number),
    enabled: profileId !== null,
    staleTime: 30_000,
  });
  const profileIndex = useMemo(() => {
    const z = profileBirthCards?.cards?.zodiacal;
    if (!z) return null;
    const i = decans.findIndex(
      d => d.decan.minor.rank === z.rank && d.decan.minor.suit === z.suit);
    return i >= 0 ? i : null;
  }, [profileBirthCards, decans]);

  const sel = selected !== null ? decans[selected] : null;

  const courtFor = (sign: SignRef, decanIndex: number, system: CourtSystem) =>
    sign.courts[system][decanIndex <= 2 ? 0 : 1];

  return (
    <div className="decan-wheel">
      <div className="decan-wheel__chart">
        <svg viewBox="0 0 640 640" role="img" aria-label="Decan rulership wheel">
          {/* Sign ring */}
          {data.signs.map((sign, i) => {
            const a0 = -90 + i * 30;
            const [gx, gy] = point(271, a0 + 15);
            return (
              <g key={sign.name}>
                <path className="decan-wheel__sign" d={sector(250, 292, a0, a0 + 30)}>
                  <title>{`${sign.name} · ${sign.dates}`}</title>
                </path>
                <text className="decan-wheel__sign-glyph" x={gx} y={gy}>
                  {sign.glyph}
                </text>
              </g>
            );
          })}

          {/* Decan ring */}
          {decans.map(({ sign, decan }, i) => {
            const a0 = decanStart(i);
            const [gx, gy] = point(212, a0 + 5);
            const classes = ['decan-wheel__decan'];
            if (i === selected) classes.push('decan-wheel__decan--selected');
            else if (i === hovered) classes.push('decan-wheel__decan--hover');
            if (i === todayIndex) classes.push('decan-wheel__decan--today');
            if (i === profileIndex) classes.push('decan-wheel__decan--profile');
            return (
              <g key={`${sign.name}-${decan.index}`}>
                <path
                  className={classes.join(' ')}
                  d={sector(175, 246, a0, a0 + 10)}
                  onClick={() => setSelected(i === selected ? null : i)}
                  onMouseEnter={() => setHovered(i)}
                  onMouseLeave={() => setHovered(h => (h === i ? null : h))}
                >
                  <title>{`${decan.minor.name} · ${decan.dates} · ${decan.planet}`}</title>
                </path>
                <text className="decan-wheel__planet-glyph" x={gx} y={gy}>
                  {planetGlyphs[decan.planet] ?? ''}
                </text>
              </g>
            );
          })}

          {/* Court arcs: each sign's court covers its own first 20°
              plus the previous sign's last 10°. */}
          {showCourts && data.signs.map((sign, i) => {
            const court = sign.courts[data.court_system][0];
            const a0 = -90 + i * 30 - 10;
            const [tx, ty] = point(150, a0 + 15);
            return (
              <g key={`court-${sign.name}`}>
                <path className="decan-wheel__court" d={sector(130, 170, a0, a0 + 30)}>
                  <title>{`${court.name} — ${court.span}`}</title>
                </path>
                <text className="decan-wheel__court-label" x={tx} y={ty}>
                  <tspan x={tx} dy="-0.15em">{court.rank}</tspan>
                  <tspan x={tx} dy="1.05em">{court.suit}</tspan>
                </text>
              </g>
            );
          })}
        </svg>

        <div className="decan-wheel__controls">
          <label className="decan-wheel__control">
            <input
              type="checkbox"
              checked={showCourts}
              onChange={(e) => setShowCourts(e.target.checked)}
            />
            Court arcs ({COURT_SYSTEM_SHORT[data.court_system]})
          </label>
          {datedProfiles.length > 0 && (
            <label className="decan-wheel__control">
              <span>Birth decan of</span>
              <select
                value={profileId === null ? '' : String(profileId)}
                onChange={(e) => setProfileId(e.target.value ? Number(e.target.value) : null)}
              >
                <option value="">Nobody</option>
                {datedProfiles.map(p => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
            </label>
          )}
          <div className="decan-wheel__legend">
            <span className="decan-wheel__legend-item decan-wheel__legend-item--today">
              today
            </span>
            {profileIndex !== null && (
              <span className="decan-wheel__legend-item decan-wheel__legend-item--profile">
                birth decan
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="decan-wheel__panel">
        {!sel && (
          <p className="ref-detail__note">
            Click a decan segment for its Minor, rulers, and court.
          </p>
        )}
        {sel && (
          <>
            <div className="ref-detail__header">
              <span className="ref-detail__glyph">{sel.sign.glyph}</span>
              <h3 className="ref-detail__title">
                {sel.sign.name} {['I', 'II', 'III'][sel.decan.index - 1]}
              </h3>
              <span className="ref-detail__dates">{sel.decan.dates}</span>
            </div>
            <div className="ref-detail__row">
              <RefTile card={sel.decan.minor} caption="Decan Minor" onOpen={openCard} />
              <RefTile card={sel.sign.trump} caption={`${sel.sign.name}'s trump`} onOpen={openCard} />
              <RefTile
                card={sel.decan.planet_trump}
                caption={`Ruler — ${sel.decan.planet}`}
                onOpen={openCard}
              />
            </div>
            <div className="ref-detail__kicker">Court ruler by system</div>
            <div className="decan-wheel__courts">
              {(Object.keys(COURT_SYSTEM_SHORT) as CourtSystem[]).map(system => {
                const court = courtFor(sel.sign, sel.decan.index, system);
                const isPref = system === data.court_system;
                return (
                  <div
                    key={system}
                    className={`decan-wheel__court-cell ${isPref ? 'decan-wheel__court-cell--pref' : ''}`}
                  >
                    <div className="decan-wheel__court-system">
                      {COURT_SYSTEM_SHORT[system]}
                      {isPref && ' ★'}
                    </div>
                    <RefTile card={court} caption={court.span} onOpen={openCard} />
                  </div>
                );
              })}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
