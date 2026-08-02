/**
 * The Insights dashboard hero (Nocturne 5b): headline stat cards, the
 * "Cards that keep coming" frequency bars, the monthly cadence
 * columns, and suits + reversal rate — all fed by one aggregate
 * endpoint whose counting happens in backend code, filtered by
 * timeframe / deck / querent.
 */
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '../../api/client';
import {
  loadSuitViewMode,
  saveSuitViewMode,
  pairSuitCounts,
  type SuitViewMode,
} from '../../utils/suitPairing';
import { getDecks } from '../../api/decks';
import { getProfiles } from '../../api/profiles';
import QueryError from '../common/QueryError';
import type { Deck, Profile } from '../../types';
import './InsightsHero.css';

interface Insights {
  entries: number;
  date_range: { from: string | null; to: string | null };
  cards_drawn: number;
  reversed_count: number;
  reversal_rate: number;
  distinct_cards: number;
  entries_this_month: number;
  entries_prev_month: number;
  top_cards: { name: string; count: number }[];
  cadence: { month: string; label: string; count: number; current: boolean }[];
  suits: { suit: string; count: number }[];
  top_reversed_position: { label: string; rate: number } | null;
}

const TIMEFRAMES = [
  { label: '90d', days: 90 },
  { label: '1y', days: 365 },
  { label: 'All', days: undefined },
] as const;

async function getInsights(params: {
  days?: number;
  deck_id?: number;
  querent_id?: number;
}): Promise<Insights> {
  const p: Record<string, string> = {};
  if (params.days) p.days = String(params.days);
  if (params.deck_id) p.deck_id = String(params.deck_id);
  if (params.querent_id) p.querent_id = String(params.querent_id);
  const res = await api.get('/api/stats/insights', { params: p });
  return res.data;
}

function formatRange(range: Insights['date_range']): string {
  if (!range.from || !range.to) return 'no entries yet';
  const fmt = (s: string) =>
    new Date(s + 'T00:00').toLocaleDateString(undefined, {
      day: 'numeric', month: 'short', year: 'numeric',
    });
  return `${fmt(range.from)} – ${fmt(range.to)}`;
}

export default function InsightsHero() {
  const [timeframe, setTimeframe] = useState<(typeof TIMEFRAMES)[number]['label']>('All');
  const [deckId, setDeckId] = useState<number | ''>('');
  const [querentId, setQuerentId] = useState<number | ''>('');
  const [suitMode, setSuitMode] = useState<SuitViewMode>(loadSuitViewMode);

  const changeSuitMode = (m: SuitViewMode) => {
    setSuitMode(m);
    saveSuitViewMode(m);
  };

  const days = TIMEFRAMES.find(t => t.label === timeframe)?.days;

  const { data, error, refetch } = useQuery<Insights>({
    queryKey: ['insights', days, deckId, querentId],
    queryFn: () => getInsights({
      days,
      deck_id: deckId === '' ? undefined : deckId,
      querent_id: querentId === '' ? undefined : querentId,
    }),
  });
  const { data: decks = [] } = useQuery<Deck[]>({ queryKey: ['decks'], queryFn: () => getDecks() });
  const { data: profiles = [] } = useQuery<Profile[]>({ queryKey: ['profiles'], queryFn: getProfiles });

  if (error) return <QueryError what="insights" onRetry={() => refetch()} />;
  if (!data) return <div className="insights-hero__loading">Reading the journal…</div>;

  const maxCard = Math.max(1, ...data.top_cards.map(c => c.count));
  const maxMonth = Math.max(1, ...data.cadence.map(m => m.count));
  const suits = suitMode === 'paired' ? pairSuitCounts(data.suits) : data.suits;
  const maxSuit = Math.max(1, ...suits.map(s => s.count));
  const monthDelta = data.entries_this_month - data.entries_prev_month;

  return (
    <div className="insights-hero">
      <header className="insights-hero__header">
        <div>
          <div className="tj-kicker">
            {data.entries} entr{data.entries === 1 ? 'y' : 'ies'} · {formatRange(data.date_range)}
          </div>
          <h2 className="insights-hero__title">Insights</h2>
        </div>
        <div className="insights-hero__controls">
          <select
            value={deckId}
            onChange={e => setDeckId(e.target.value ? Number(e.target.value) : '')}
          >
            <option value="">All decks</option>
            {decks.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
          </select>
          <select
            value={querentId}
            onChange={e => setQuerentId(e.target.value ? Number(e.target.value) : '')}
          >
            <option value="">All querents</option>
            {profiles.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
          <div className="insights-hero__segment" role="group" aria-label="Timeframe">
            {TIMEFRAMES.map(t => (
              <button
                key={t.label}
                className={timeframe === t.label ? 'insights-hero__segment-opt--active' : ''}
                onClick={() => setTimeframe(t.label)}
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>
      </header>

      {/* ── Stat row ── */}
      <div className="insights-hero__stats">
        <div className="insights-hero__stat">
          <div className="insights-hero__stat-kicker">Entries</div>
          <div className="insights-hero__figure">{data.entries}</div>
          <div className="insights-hero__stat-note">{formatRange(data.date_range)}</div>
        </div>
        <div className="insights-hero__stat">
          <div className="insights-hero__stat-kicker">Cards drawn</div>
          <div className="insights-hero__figure">{data.cards_drawn}</div>
          <div className="insights-hero__stat-note">
            {data.distinct_cards} distinct card{data.distinct_cards === 1 ? '' : 's'}
          </div>
        </div>
        <div className="insights-hero__stat">
          <div className="insights-hero__stat-kicker">Reversals</div>
          <div className="insights-hero__figure">
            {data.reversal_rate}<span className="insights-hero__figure-unit">%</span>
          </div>
          <div className="insights-hero__stat-note">
            {data.reversed_count} of {data.cards_drawn} cards
          </div>
        </div>
        <div className="insights-hero__stat">
          <div className="insights-hero__stat-kicker">This month</div>
          <div className="insights-hero__figure">{data.entries_this_month}</div>
          <div className="insights-hero__stat-note">
            {monthDelta === 0
              ? 'level with last month'
              : monthDelta > 0
                ? `${monthDelta} more than last month`
                : `${-monthDelta} fewer than last month`}
          </div>
        </div>
      </div>

      {/* ── Body grid ── */}
      <div className="insights-hero__grid">
        <section className="insights-hero__panel insights-hero__panel--cards">
          <h3 className="insights-hero__panel-kicker">Cards that keep coming</h3>
          {data.top_cards.length === 0 ? (
            <p className="insights-hero__empty">No cards drawn in this range.</p>
          ) : (
            <div className="insights-hero__card-list">
              {data.top_cards.map(c => (
                <div key={c.name} className="insights-hero__card-row">
                  <div className="insights-hero__card-line">
                    <span className="insights-hero__card-name">{c.name}</span>
                    <span className="insights-hero__card-count">{c.count}</span>
                  </div>
                  <div className="insights-hero__track">
                    <div
                      className="insights-hero__bar"
                      style={{ width: `${(c.count / maxCard) * 100}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="insights-hero__panel">
          <h3 className="insights-hero__panel-kicker">Cadence</h3>
          <div className="insights-hero__cadence">
            {data.cadence.map(m => (
              <div key={m.month} className="insights-hero__cadence-col" title={`${m.label}: ${m.count}`}>
                <div
                  className={`insights-hero__cadence-bar ${m.current ? 'insights-hero__cadence-bar--current' : ''}`}
                  style={{ height: `${Math.max(3, (m.count / maxMonth) * 100)}%` }}
                />
                <span className="insights-hero__cadence-label">{m.label}</span>
              </div>
            ))}
          </div>
        </section>

        <section className="insights-hero__panel insights-hero__panel--split">
          <div className="insights-hero__suits">
            <div className="insights-hero__suits-head">
              <h3 className="insights-hero__panel-kicker">Suits drawn</h3>
              <div className="insights-hero__suit-mode" role="group" aria-label="Suit display">
                <button
                  className={suitMode === 'separate' ? 'insights-hero__segment-opt--active' : ''}
                  onClick={() => changeSuitMode('separate')}
                >
                  Separate
                </button>
                <button
                  className={suitMode === 'paired' ? 'insights-hero__segment-opt--active' : ''}
                  onClick={() => changeSuitMode('paired')}
                >
                  Paired
                </button>
              </div>
            </div>
            {suits.length === 0 ? (
              <p className="insights-hero__empty">No suited cards in this range.</p>
            ) : (
              suits.map(s => (
                <div key={s.suit} className="insights-hero__suit-row">
                  <span className="insights-hero__suit-name">{s.suit}</span>
                  <div className="insights-hero__track">
                    <div
                      className="insights-hero__bar"
                      style={{ width: `${(s.count / maxSuit) * 100}%` }}
                    />
                  </div>
                  <span className="insights-hero__suit-count">{s.count}</span>
                </div>
              ))
            )}
          </div>
          <div className="insights-hero__vrule" aria-hidden="true" />
          <div className="insights-hero__reversals">
            <h3 className="insights-hero__panel-kicker">Reversals</h3>
            <div className="insights-hero__figure insights-hero__figure--large">
              {data.reversal_rate}<span className="insights-hero__figure-unit">%</span>
            </div>
            {data.top_reversed_position && (
              <div className="insights-hero__reversal-note">
                Highest in the {data.top_reversed_position.label} position
                ({data.top_reversed_position.rate}%)
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
