/**
 * Kabbalah reference: the ten sephiroth (each with the four Minors of
 * its number) and the 22 Tree of Life paths (Golden Dawn letter–trump
 * attributions), with a flat scanning table. The interactive Tree
 * chart joins this section in a later phase.
 */
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import QueryError from '../../common/QueryError';
import { getKabbalahReference } from '../../../api/reference';
import {
  AssignedCards,
  ReferenceSystemPicker,
  RefTile,
  useCardPeek,
  useReferenceSystem,
} from './referenceShared';
import '../ReferenceTab.css';
import './KabbalahSection.css';

const PILLAR_LABELS: Record<string, string> = {
  middle: 'Middle Pillar',
  mercy: 'Pillar of Mercy',
  severity: 'Pillar of Severity',
};

interface KabbalahSectionProps {
  onOpenArchetype?: (id: number, cartomancyType: string) => void;
}

export default function KabbalahSection({ onOpenArchetype }: KabbalahSectionProps) {
  const [tab, setTab] = useState<'sephiroth' | 'paths'>('sephiroth');
  const [sephiraNumber, setSephiraNumber] = useState(1);
  const [pathNumber, setPathNumber] = useState(11);
  const { systems, systemId, setSystemId } = useReferenceSystem();
  const { openCard, cardModal } = useCardPeek();

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['reference-kabbalah', systemId],
    queryFn: () => getKabbalahReference(systemId),
  });

  const sephira = data?.sephiroth.find(s => s.number === sephiraNumber);
  const path = data?.paths.find(p => p.path === pathNumber);
  const sephiraName = (n: number) =>
    data?.sephiroth.find(s => s.number === n)?.name ?? String(n);

  return (
    <div className="reference-section">
      <h2 className="reference-section__title">Kabbalah</h2>
      <p className="reference-section__hint">
        The Tree of Life: ten sephiroth joined by twenty-two paths, one
        Hebrew letter and one trump per path. Letter–trump attributions
        follow the Golden Dawn scheme; trump names stay canonical (the
        8/11 numbering choice never moves a letter).
      </p>
      <ReferenceSystemPicker systems={systems} systemId={systemId} onChange={setSystemId} />

      <div className="ref-subtabs">
        <button
          type="button"
          className={`ref-subtabs__tab ${tab === 'sephiroth' ? 'ref-subtabs__tab--active' : ''}`}
          onClick={() => setTab('sephiroth')}
        >
          Sephiroth
        </button>
        <button
          type="button"
          className={`ref-subtabs__tab ${tab === 'paths' ? 'ref-subtabs__tab--active' : ''}`}
          onClick={() => setTab('paths')}
        >
          Paths
        </button>
      </div>

      {isLoading && <p className="reference-section__hint">Loading…</p>}
      {isError && <QueryError what="Kabbalah reference" onRetry={() => refetch()} />}

      {data && tab === 'sephiroth' && (
        <>
          <div className="ref-selector">
            {data.sephiroth.map(s => (
              <button
                key={s.number}
                type="button"
                className={`ref-selector__item ${s.number === sephiraNumber ? 'ref-selector__item--active' : ''}`}
                onClick={() => setSephiraNumber(s.number)}
              >
                <span className="ref-selector__glyph">{s.number}</span>
                <span className="ref-selector__name">{s.name}</span>
              </button>
            ))}
          </div>

          {sephira && (
            <div className="ref-detail">
              <div className="ref-detail__header">
                <span className="ref-detail__glyph">{sephira.number}</span>
                <h3 className="ref-detail__title">
                  {sephira.name} <span className="kabbalah__hebrew">{sephira.hebrew}</span>
                </h3>
                <span className="ref-detail__dates">{sephira.translation}</span>
              </div>
              <div className="ref-detail__meta">
                <span>{PILLAR_LABELS[sephira.pillar]}</span>
                <span>Association: <strong>{sephira.planet}</strong></span>
              </div>
              <p className="ref-detail__themes">{sephira.meaning}</p>

              <div className="ref-detail__kicker">
                The four {sephira.number === 1 ? 'Aces' : `${sephira.minors[0].name.split(' of ')[0]}s`}
              </div>
              <div className="ref-detail__row">
                {sephira.minors.map(m => (
                  <RefTile key={m.name} card={m} caption={m.suit} onOpen={openCard} />
                ))}
              </div>
              <p className="ref-detail__note">
                The Minors of each number sit on their sephira across all
                four worlds — one suit per world.
              </p>
            </div>
          )}
        </>
      )}

      {data && tab === 'paths' && (
        <>
          <div className="ref-selector">
            {data.paths.map(p => (
              <button
                key={p.path}
                type="button"
                className={`ref-selector__item ${p.path === pathNumber ? 'ref-selector__item--active' : ''}`}
                onClick={() => setPathNumber(p.path)}
              >
                <span className="ref-selector__glyph">{p.glyph}</span>
                <span className="ref-selector__name">{p.letter}</span>
              </button>
            ))}
          </div>

          {path && (
            <div className="ref-detail">
              <div className="ref-detail__header">
                <span className="ref-detail__glyph">{path.glyph}</span>
                <h3 className="ref-detail__title">
                  Path {path.path} — {path.letter}
                </h3>
                <span className="ref-detail__dates">value {path.value}</span>
              </div>
              <div className="ref-detail__meta">
                <span>
                  Joins <strong>{sephiraName(path.from)}</strong> and{' '}
                  <strong>{sephiraName(path.to)}</strong>
                </span>
              </div>

              <div className="ref-detail__kicker">Trump</div>
              <div className="ref-detail__row">
                <RefTile card={path.trump} caption={`${path.letter}'s trump`} onOpen={openCard} />
              </div>

              <AssignedCards refs={path.assigned} onOpenArchetype={onOpenArchetype} />
            </div>
          )}

          <div className="reference-section__subtitle">All 22 paths</div>
          <div className="kabbalah__table-wrap">
            <table className="kabbalah__table">
              <thead>
                <tr>
                  <th>Path</th>
                  <th>Letter</th>
                  <th>Value</th>
                  <th>Trump</th>
                  <th>Joins</th>
                </tr>
              </thead>
              <tbody>
                {data.paths.map(p => (
                  <tr
                    key={p.path}
                    className={p.path === pathNumber ? 'kabbalah__row--active' : ''}
                    onClick={() => setPathNumber(p.path)}
                  >
                    <td>{p.path}</td>
                    <td>{p.glyph} {p.letter}</td>
                    <td>{p.value}</td>
                    <td>{p.trump.name}</td>
                    <td>{sephiraName(p.from)} – {sephiraName(p.to)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {cardModal}
    </div>
  );
}
