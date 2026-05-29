"""Chart cache CRUD — keyed by (source_type, source_id) per UNIQUE constraint."""

from datetime import datetime
import json
from typing import Optional


class ChartsMixin:
    """Methods for the chart_cache table.

    Schema is defined in core.py — this mixin just handles read/write.
    The `source_type` is always 'profile' or 'entry' (CHECK constraint
    enforces this at the DB level).
    """

    def get_cached_chart(self, source_type: str, source_id: int) -> Optional[dict]:
        """Return the cached chart row as a dict, or None if not cached.

        chart_data is parsed from JSON back into a dict for the caller.
        """
        cursor = self.conn.cursor()
        cursor.execute(
            'SELECT * FROM chart_cache WHERE source_type = ? AND source_id = ?',
            (source_type, source_id)
        )
        row = cursor.fetchone()
        if row is None:
            return None
        d = dict(row)
        if d.get('chart_data'):
            try:
                d['chart_data'] = json.loads(d['chart_data'])
            except (ValueError, TypeError):
                d['chart_data'] = None
        return d

    def save_cached_chart(
        self,
        source_type: str,
        source_id: int,
        house_system: str,
        input_hash: str,
        chart_svg: str,
        chart_data: dict,
    ):
        """Upsert a cached chart. Bumps updated_at on conflict."""
        now = datetime.now().isoformat()
        cursor = self.conn.cursor()
        cursor.execute(
            '''
            INSERT INTO chart_cache (
                source_type, source_id, house_system,
                chart_svg, chart_data, input_hash,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (source_type, source_id) DO UPDATE SET
                house_system = excluded.house_system,
                chart_svg    = excluded.chart_svg,
                chart_data   = excluded.chart_data,
                input_hash   = excluded.input_hash,
                updated_at   = excluded.updated_at
            ''',
            (
                source_type, source_id, house_system,
                chart_svg, json.dumps(chart_data, default=str), input_hash,
                now, now,
            ),
        )
        self._commit()

    def delete_cached_chart(self, source_type: str, source_id: int):
        cursor = self.conn.cursor()
        cursor.execute(
            'DELETE FROM chart_cache WHERE source_type = ? AND source_id = ?',
            (source_type, source_id),
        )
        self._commit()
