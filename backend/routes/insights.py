"""
Insights — one aggregate payload for the dashboard (Nocturne 5b).

Counting happens here, in code, over the entries the filters select:
per-card frequency (by archetype where known, so the same card across
decks aggregates), monthly cadence, suit distribution, reversal rate
and the position it concentrates in, plus the headline stat cards.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta

from flask import Blueprint, current_app, jsonify, request

insights_bp = Blueprint('insights', __name__)

CADENCE_MONTHS = 14
MIN_POSITION_SAMPLE = 5   # a "highest reversal position" needs this many draws


def _month_key(dt: datetime) -> str:
    return f"{dt.year:04d}-{dt.month:02d}"


def _shift_month(dt: datetime, back: int) -> datetime:
    y, m = dt.year, dt.month - back
    while m <= 0:
        y -= 1
        m += 12
    return datetime(y, m, 1)


@insights_bp.route('/api/stats/insights')
def get_insights():
    db = current_app.config['DB']
    cur = db.conn.cursor()

    days = request.args.get('days', type=int)          # None = all time
    querent_id = request.args.get('querent_id', type=int)
    deck_id = request.args.get('deck_id', type=int)

    # ── Entries in scope ────────────────────────────────────────────
    sql = '''
        SELECT DISTINCT e.id, COALESCE(e.reading_datetime, e.created_at) AS when_
        FROM journal_entries e
        LEFT JOIN entry_querents q ON q.entry_id = e.id
        WHERE 1=1
    '''
    params: list = []
    if querent_id:
        sql += ' AND (q.profile_id = ? OR e.querent_id = ?)'
        params += [querent_id, querent_id]
    if days:
        sql += " AND COALESCE(e.reading_datetime, e.created_at) >= ?"
        params.append((datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d'))
    rows = cur.execute(sql, params).fetchall()
    entry_when = {r['id']: str(r['when_'] or '') for r in rows}
    entry_ids = set(entry_when)

    # ── Readings + cards ────────────────────────────────────────────
    readings = [dict(r) for r in cur.execute(
        'SELECT entry_id, spread_id, deck_id, cards_used FROM entry_readings'
    ).fetchall() if r['entry_id'] in entry_ids]
    if deck_id:
        readings = [r for r in readings if r['deck_id'] == deck_id]
        # Deck filter narrows the entry set to entries that still have
        # at least one reading with that deck.
        entry_ids = {r['entry_id'] for r in readings}
        entry_when = {k: v for k, v in entry_when.items() if k in entry_ids}

    # Lookups: card_id → archetype/name; archetype name → suit
    card_info = {r['id']: (r['archetype'], r['name']) for r in cur.execute(
        'SELECT id, archetype, name FROM cards').fetchall()}
    suit_of = {}
    for r in cur.execute('SELECT name, suit FROM card_archetypes').fetchall():
        if r['suit']:
            suit_of.setdefault(r['name'].lower(), r['suit'])
    positions_of = {r['id']: json.loads(r['positions'] or '[]') for r in cur.execute(
        'SELECT id, positions FROM spreads').fetchall()}

    card_counts: Counter = Counter()
    suit_counts: Counter = Counter()
    pos_totals: Counter = Counter()
    pos_reversed: Counter = Counter()
    total_cards = 0
    reversed_count = 0

    for rd in readings:
        try:
            cards = json.loads(rd['cards_used'] or '[]')
        except ValueError:
            continue
        positions = positions_of.get(rd['spread_id']) or []
        for c in cards:
            if not isinstance(c, dict):
                continue
            archetype, fallback = card_info.get(c.get('card_id'), (None, None))
            display = archetype or fallback or (c.get('name') or '').strip()
            if not display:
                continue
            total_cards += 1
            card_counts[display] += 1
            suit = suit_of.get(display.lower())
            if suit:
                suit_counts[suit] += 1
            is_reversed = bool(c.get('reversed'))
            if is_reversed:
                reversed_count += 1
            idx = c.get('position_index')
            if isinstance(idx, int) and 0 <= idx < len(positions):
                label = positions[idx].get('label') or f'Position {idx + 1}'
                pos_totals[label] += 1
                if is_reversed:
                    pos_reversed[label] += 1

    # ── Cadence: entries per month, last CADENCE_MONTHS ─────────────
    per_month = Counter(w[:7] for w in entry_when.values() if len(w) >= 7)
    now = datetime.now()
    cadence = []
    for back in range(CADENCE_MONTHS - 1, -1, -1):
        m = _shift_month(now, back)
        key = _month_key(m)
        cadence.append({
            'month': key,
            'label': m.strftime('%b'),
            'count': per_month.get(key, 0),
            'current': back == 0,
        })

    this_month = per_month.get(_month_key(now), 0)
    prev_month = per_month.get(_month_key(_shift_month(now, 1)), 0)

    # ── Highest-reversal position (with a minimum sample) ───────────
    top_pos = None
    best_rate = 0.0
    for label, total in pos_totals.items():
        if total < MIN_POSITION_SAMPLE:
            continue
        rate = pos_reversed[label] / total
        if pos_reversed[label] and rate > best_rate:
            best_rate = rate
            top_pos = {'label': label, 'rate': round(rate * 100, 1)}

    whens = sorted(w for w in entry_when.values() if w)
    return jsonify({
        'entries': len(entry_ids),
        'date_range': {
            'from': whens[0][:10] if whens else None,
            'to': whens[-1][:10] if whens else None,
        },
        'cards_drawn': total_cards,
        'reversed_count': reversed_count,
        'reversal_rate': round(reversed_count / total_cards * 100, 1) if total_cards else 0.0,
        'distinct_cards': len(card_counts),
        'entries_this_month': this_month,
        'entries_prev_month': prev_month,
        'top_cards': [
            {'name': n, 'count': c} for n, c in card_counts.most_common(14)
        ],
        'cadence': cadence,
        'suits': [
            {'suit': s, 'count': c} for s, c in suit_counts.most_common()
        ],
        'top_reversed_position': top_pos,
    })
