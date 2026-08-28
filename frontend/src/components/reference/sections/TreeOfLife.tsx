/**
 * The interactive Tree of Life: ten sephiroth in the standard
 * GD/Kircher layout joined by the 22 lettered paths. Click a sephira
 * for its meaning and the four Minors of its number; click a path for
 * its letter, trump, and correspondence cross-refs. Positions come
 * from the server dataset (abstract 0-100 chart coordinates).
 */
import { useMemo, useState } from 'react';
import type { KabbalahData, SephiraRef, TreePathRef } from '../../../api/reference';
import { RefTile } from './referenceShared';
import './TreeOfLife.css';

// Chart-space -> SVG-space
const sx = (x: number) => 60 + x * 3.4;
const sy = (y: number) => 42 + y * 5.75;
const R = 33;

const PILLAR_LABELS: Record<string, string> = {
  middle: 'Middle Pillar',
  mercy: 'Pillar of Mercy',
  severity: 'Pillar of Severity',
};

type Selection =
  | { kind: 'sephira'; number: number }
  | { kind: 'path'; path: number }
  | null;

interface TreeOfLifeProps {
  data: KabbalahData;
  openCard: (cardId: number) => void;
}

export default function TreeOfLife({ data, openCard }: TreeOfLifeProps) {
  const [selection, setSelection] = useState<Selection>(null);

  const byNumber = useMemo(
    () => Object.fromEntries(data.sephiroth.map(s => [s.number, s])),
    [data.sephiroth],
  );

  const selectedSephira: SephiraRef | null =
    selection?.kind === 'sephira' ? byNumber[selection.number] : null;
  const selectedPath: TreePathRef | null =
    selection?.kind === 'path'
      ? data.paths.find(p => p.path === selection.path) ?? null
      : null;

  // A selected sephira also lights up the paths touching it.
  const touching = useMemo(() => {
    if (!selectedSephira) return new Set<number>();
    return new Set(data.paths
      .filter(p => p.from === selectedSephira.number || p.to === selectedSephira.number)
      .map(p => p.path));
  }, [selectedSephira, data.paths]);

  return (
    <div className="tree-of-life">
      <div className="tree-of-life__chart">
        <svg viewBox="0 0 460 660" role="img" aria-label="Tree of Life">
          {/* Paths first, so circles sit on top */}
          {data.paths.map(p => {
            const a = byNumber[p.from];
            const b = byNumber[p.to];
            const x1 = sx(a.x); const y1 = sy(a.y);
            const x2 = sx(b.x); const y2 = sy(b.y);
            const mx = (x1 + x2) / 2;
            const my = (y1 + y2) / 2;
            const active = selection?.kind === 'path' && selection.path === p.path;
            const lit = touching.has(p.path);
            return (
              <g key={p.path}>
                <line
                  className={[
                    'tree-of-life__path',
                    active ? 'tree-of-life__path--active' : '',
                    lit ? 'tree-of-life__path--lit' : '',
                  ].join(' ')}
                  x1={x1} y1={y1} x2={x2} y2={y2}
                />
                {/* wide invisible hit target */}
                <line
                  className="tree-of-life__path-hit"
                  x1={x1} y1={y1} x2={x2} y2={y2}
                  onClick={() => setSelection(
                    active ? null : { kind: 'path', path: p.path })}
                >
                  <title>{`Path ${p.path} — ${p.letter} — ${p.trump.name}`}</title>
                </line>
                <g className="tree-of-life__letter" pointerEvents="none">
                  <circle cx={mx} cy={my} r={11} className="tree-of-life__letter-bg" />
                  <text x={mx} y={my} className="tree-of-life__letter-glyph">
                    {p.glyph}
                  </text>
                </g>
              </g>
            );
          })}

          {data.sephiroth.map(s => {
            const x = sx(s.x); const y = sy(s.y);
            const active = selection?.kind === 'sephira' && selection.number === s.number;
            return (
              <g
                key={s.number}
                className={`tree-of-life__sephira ${active ? 'tree-of-life__sephira--active' : ''} tree-of-life__sephira--${s.pillar}`}
                onClick={() => setSelection(
                  active ? null : { kind: 'sephira', number: s.number })}
              >
                <title>{`${s.number} ${s.name} — ${s.translation}`}</title>
                <circle cx={x} cy={y} r={R} className="tree-of-life__circle" />
                <text x={x} y={y - 6} className="tree-of-life__sephira-number">
                  {s.number}
                </text>
                <text x={x} y={y + 10} className="tree-of-life__sephira-name">
                  {s.name}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      <div className="tree-of-life__panel">
        {!selection && (
          <p className="ref-detail__note">
            Click a sephira or a path for details.
          </p>
        )}

        {selectedSephira && (
          <>
            <div className="ref-detail__header">
              <span className="ref-detail__glyph">{selectedSephira.number}</span>
              <h3 className="ref-detail__title">
                {selectedSephira.name}{' '}
                <span className="kabbalah__hebrew">{selectedSephira.hebrew}</span>
              </h3>
              <span className="ref-detail__dates">{selectedSephira.translation}</span>
            </div>
            <div className="ref-detail__meta">
              <span>{PILLAR_LABELS[selectedSephira.pillar]}</span>
              <span>Association: <strong>{selectedSephira.planet}</strong></span>
            </div>
            <p className="ref-detail__themes">{selectedSephira.meaning}</p>
            {selectedSephira.cards ? (
              <>
                <div className="ref-detail__kicker">
                  Cards on {selectedSephira.name}
                </div>
                <div className="ref-detail__row">
                  {selectedSephira.cards.map(c => (
                    <RefTile key={c.archetype_id ?? c.name} card={c} onOpen={openCard} />
                  ))}
                </div>
              </>
            ) : (
              <>
                <div className="ref-detail__kicker">Minors of {selectedSephira.number}</div>
                <div className="ref-detail__row">
                  {selectedSephira.minors.map(m => (
                    <RefTile key={m.name} card={m} caption={m.suit} onOpen={openCard} />
                  ))}
                </div>
                {selectedSephira.courts && (
                  <>
                    <div className="ref-detail__kicker">
                      Courts — the {selectedSephira.court_rank}s
                    </div>
                    <div className="ref-detail__row">
                      {selectedSephira.courts.map(c => (
                        <RefTile key={c.name} card={c} caption={c.suit} onOpen={openCard} />
                      ))}
                    </div>
                  </>
                )}
              </>
            )}
          </>
        )}

        {selectedPath && (
          <>
            <div className="ref-detail__header">
              <span className="ref-detail__glyph">{selectedPath.glyph}</span>
              <h3 className="ref-detail__title">
                Path {selectedPath.path} — {selectedPath.letter}
              </h3>
              <span className="ref-detail__dates">value {selectedPath.value}</span>
            </div>
            <div className="ref-detail__meta">
              <span>
                Joins <strong>{byNumber[selectedPath.from].name}</strong> and{' '}
                <strong>{byNumber[selectedPath.to].name}</strong>
              </span>
            </div>
            <div className="ref-detail__row">
              {selectedPath.letter_cards.length > 0 ? (
                selectedPath.letter_cards.map(c => (
                  <RefTile
                    key={c.archetype_id ?? c.name}
                    card={c}
                    caption={`${selectedPath.letter}'s card`}
                    onOpen={openCard}
                  />
                ))
              ) : (
                <RefTile
                  card={selectedPath.trump}
                  caption={`${selectedPath.letter}'s trump`}
                  onOpen={openCard}
                />
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
