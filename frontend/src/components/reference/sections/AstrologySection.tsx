/**
 * Astrology reference: the twelve signs and ten planets, each tied
 * back to the deck — sign/planet trumps, decan Minors, court arcs
 * under all three court systems, and whatever the chosen
 * correspondence system assigns. Sub-tabs: Signs | Planets (the decan
 * wheel joins as a third tab).
 */
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import QueryError from '../../common/QueryError';
import { getAstrologyReference } from '../../../api/reference';
import type { CourtSystem } from '../../../api/birthCards';
import {
  AssignedCards,
  ReferenceSystemPicker,
  RefTile,
  useCardPeek,
  useReferenceSystem,
} from './referenceShared';
import DecanWheel from './DecanWheel';
import '../ReferenceTab.css';

const COURT_SYSTEM_LABELS: Record<CourtSystem, string> = {
  golden_dawn: 'Golden Dawn (Book T titles)',
  golden_dawn_waite: 'Golden Dawn (Waite figures)',
  bota: 'B.O.T.A.',
};

interface AstrologySectionProps {
  onOpenArchetype?: (id: number, cartomancyType: string) => void;
}

export default function AstrologySection({ onOpenArchetype }: AstrologySectionProps) {
  const [tab, setTab] = useState<'signs' | 'planets' | 'wheel'>('signs');
  const [signName, setSignName] = useState('Aries');
  const [planetName, setPlanetName] = useState('Sun');
  const { systems, systemId, setSystemId } = useReferenceSystem();
  const { openCard, cardModal } = useCardPeek();
  // Which court system the sign panel shows; follows the saved
  // preference until changed here (view-only, not persisted).
  const [courtView, setCourtView] = useState<CourtSystem | null>(null);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['reference-astrology', systemId],
    queryFn: () => getAstrologyReference(systemId),
  });

  const sign = data?.signs.find(s => s.name === signName);
  const planet = data?.planets.find(p => p.name === planetName);
  const courtSystem = courtView ?? data?.court_system ?? 'golden_dawn';

  return (
    <div className="reference-section">
      <h2 className="reference-section__title">Astrology</h2>
      <p className="reference-section__hint">
        Golden Dawn attributions: each sign and classical planet has its
        trump, each decan its Minor. Symbolic reference only — for live
        charts, see a profile's natal chart.
      </p>
      <ReferenceSystemPicker systems={systems} systemId={systemId} onChange={setSystemId} />

      <div className="ref-subtabs">
        <button
          type="button"
          className={`ref-subtabs__tab ${tab === 'signs' ? 'ref-subtabs__tab--active' : ''}`}
          onClick={() => setTab('signs')}
        >
          Signs
        </button>
        <button
          type="button"
          className={`ref-subtabs__tab ${tab === 'planets' ? 'ref-subtabs__tab--active' : ''}`}
          onClick={() => setTab('planets')}
        >
          Planets
        </button>
        <button
          type="button"
          className={`ref-subtabs__tab ${tab === 'wheel' ? 'ref-subtabs__tab--active' : ''}`}
          onClick={() => setTab('wheel')}
        >
          Decan Wheel
        </button>
      </div>

      {isLoading && <p className="reference-section__hint">Loading…</p>}
      {isError && <QueryError what="astrology reference" onRetry={() => refetch()} />}

      {data && tab === 'signs' && (
        <>
          <div className="ref-selector">
            {data.signs.map(s => (
              <button
                key={s.name}
                type="button"
                className={`ref-selector__item ${s.name === signName ? 'ref-selector__item--active' : ''}`}
                onClick={() => setSignName(s.name)}
              >
                <span className="ref-selector__glyph">{s.glyph}</span>
                <span className="ref-selector__name">{s.name}</span>
              </button>
            ))}
          </div>

          {sign && (
            <div className="ref-detail">
              <div className="ref-detail__header">
                <span className="ref-detail__glyph">{sign.glyph}</span>
                <h3 className="ref-detail__title">{sign.name}</h3>
                <span className="ref-detail__dates">{sign.dates}</span>
              </div>
              <div className="ref-detail__meta">
                <span><strong>{sign.element}</strong> · {sign.modality}</span>
                <span>
                  Ruled by <strong>{sign.ruler}</strong>
                  {sign.modern_ruler && <> (modern: {sign.modern_ruler})</>}
                </span>
              </div>
              <p className="ref-detail__themes">{sign.themes}</p>

              <div className="ref-detail__kicker">Trump</div>
              <div className="ref-detail__row">
                <RefTile card={sign.trump} caption={`${sign.name}'s trump`} onOpen={openCard} />
              </div>

              <div className="ref-detail__kicker">Decans</div>
              <div className="ref-detail__row">
                {sign.decans.map(d => (
                  <RefTile
                    key={d.index}
                    card={d.minor}
                    caption={`${d.dates} · ${d.planet}`}
                    onOpen={openCard}
                  />
                ))}
              </div>

              <div className="ref-detail__kicker">Court arcs</div>
              <label className="ref-system-picker">
                <span>System</span>
                <select
                  value={courtSystem}
                  onChange={(e) => setCourtView(e.target.value as CourtSystem)}
                >
                  {(Object.keys(COURT_SYSTEM_LABELS) as CourtSystem[]).map(cs => (
                    <option key={cs} value={cs}>{COURT_SYSTEM_LABELS[cs]}</option>
                  ))}
                </select>
              </label>
              <div className="ref-detail__row">
                {sign.courts[courtSystem].map((arc, i) => (
                  <RefTile
                    key={`${arc.name}-${i}`}
                    card={arc}
                    caption={arc.span}
                    onOpen={openCard}
                  />
                ))}
              </div>
              <p className="ref-detail__note">
                Each court card rules the last decan of one sign and the
                first two of the next; two arcs touch every sign.
              </p>

              <AssignedCards refs={sign.assigned} onOpenArchetype={onOpenArchetype} />
            </div>
          )}
        </>
      )}

      {data && tab === 'planets' && (
        <>
          <div className="ref-selector">
            {data.planets.map(p => (
              <button
                key={p.name}
                type="button"
                className={`ref-selector__item ${p.name === planetName ? 'ref-selector__item--active' : ''}`}
                onClick={() => setPlanetName(p.name)}
              >
                <span className="ref-selector__glyph">{p.glyph}</span>
                <span className="ref-selector__name">{p.name}</span>
              </button>
            ))}
          </div>

          {planet && (
            <div className="ref-detail">
              <div className="ref-detail__header">
                <span className="ref-detail__glyph">{planet.glyph}</span>
                <h3 className="ref-detail__title">{planet.name}</h3>
                {!planet.classical && (
                  <span className="ref-detail__dates">modern planet</span>
                )}
              </div>
              <div className="ref-detail__meta">
                <span>Rules <strong>{planet.rules.join(' & ')}</strong></span>
              </div>
              <p className="ref-detail__themes">{planet.themes}</p>

              {planet.trump && (
                <>
                  <div className="ref-detail__kicker">Trump</div>
                  <div className="ref-detail__row">
                    <RefTile
                      card={planet.trump}
                      caption={planet.modern_attribution ? 'modern attribution' : `${planet.name}'s trump`}
                      onOpen={openCard}
                    />
                  </div>
                </>
              )}

              {planet.decans_ruled.length > 0 && (
                <>
                  <div className="ref-detail__kicker">
                    Decans ruled ({planet.decans_ruled.length})
                  </div>
                  <div className="ref-detail__row">
                    {planet.decans_ruled.map((d, i) => (
                      <RefTile
                        key={`${d.minor.name}-${i}`}
                        card={d.minor}
                        caption={d.sign}
                        onOpen={openCard}
                      />
                    ))}
                  </div>
                </>
              )}
              {!planet.classical && (
                <p className="ref-detail__note">
                  Modern planets sit outside the Chaldean decan sequence;
                  their trump attributions are modern extensions of the
                  Golden Dawn scheme.
                </p>
              )}

              <AssignedCards refs={planet.assigned} onOpenArchetype={onOpenArchetype} />
            </div>
          )}
        </>
      )}

      {data && tab === 'wheel' && (
        <DecanWheel data={data} openCard={openCard} />
      )}

      {cardModal}
    </div>
  );
}
