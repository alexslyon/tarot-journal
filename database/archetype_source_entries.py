"""
Per-archetype source content.

Each row stores the content the user has authored for a single
(archetype, source) pair. UNIQUE on the pair so each archetype has at
most one content blob per source.
"""

from datetime import datetime


class ArchetypeSourceEntriesMixin:
    """Replaces the legacy archetype_notes_field_defs +
    archetype_notes_entries pair. Sources are now the field axis (see
    ReferenceSourcesMixin) and content is keyed by (archetype, source)."""

    # === Read ====================================================

    def get_source_entries_for_archetype(
        self,
        archetype_id: int,
        cartomancy_type: str = None,
    ):
        """All non-empty source entries for the given archetype, joined
        with the source row so the caller can render attribution +
        authors without a second fetch.

        When `cartomancy_type` is provided, only entries whose source
        belongs to that type are returned — matches the typical
        Archetypes-viewer fetch pattern.
        """
        cursor = self.conn.cursor()
        sql = '''
            SELECT
                e.id AS entry_id,
                e.archetype_id,
                e.source_id,
                e.content,
                e.updated_at,
                s.name AS source_name,
                s.cartomancy_type AS source_cartomancy_type
            FROM archetype_source_entries e
            JOIN reference_sources s ON s.id = e.source_id
            WHERE e.archetype_id = ?
              AND e.content IS NOT NULL
              AND TRIM(e.content) != ''
        '''
        params: list = [archetype_id]
        if cartomancy_type is not None:
            sql += ' AND s.cartomancy_type = ?'
            params.append(cartomancy_type)
        sql += ' ORDER BY s.name'
        return [dict(r) for r in cursor.execute(sql, params).fetchall()]

    def get_source_entries_for_source(self, source_id: int):
        """Every entry under a source, ordered by archetype rank. Used
        by the Settings page where one source is being authored across
        all of its cartomancy type's archetypes."""
        cursor = self.conn.cursor()
        rows = cursor.execute(
            '''
            SELECT
                e.id AS entry_id,
                e.archetype_id,
                e.source_id,
                e.content,
                e.updated_at,
                a.name AS archetype_name,
                a.rank AS archetype_rank
            FROM archetype_source_entries e
            JOIN card_archetypes a ON a.id = e.archetype_id
            WHERE e.source_id = ?
            ''',
            (source_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_source_entry(self, archetype_id: int, source_id: int):
        """Single (archetype, source) entry, or None if not yet authored."""
        cursor = self.conn.cursor()
        row = cursor.execute(
            'SELECT * FROM archetype_source_entries '
            'WHERE archetype_id = ? AND source_id = ?',
            (archetype_id, source_id)
        ).fetchone()
        return dict(row) if row else None

    # === Write ===================================================

    def set_source_entry(self, archetype_id: int, source_id: int, content: str):
        """Upsert content for an (archetype, source) pair.

        Empty / whitespace content deletes the row instead of storing a
        blank — the viewer treats absence and emptiness as the same
        "no content" signal, so we keep the table tidy.
        """
        cursor = self.conn.cursor()
        is_blank = not content or not content.strip()
        if is_blank:
            cursor.execute(
                'DELETE FROM archetype_source_entries '
                'WHERE archetype_id = ? AND source_id = ?',
                (archetype_id, source_id)
            )
        else:
            now = datetime.now().isoformat()
            cursor.execute(
                '''
                INSERT INTO archetype_source_entries
                    (archetype_id, source_id, content, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT (archetype_id, source_id) DO UPDATE SET
                    content = excluded.content,
                    updated_at = excluded.updated_at
                ''',
                (archetype_id, source_id, content, now)
            )
        self._commit()

    def delete_source_entry(self, archetype_id: int, source_id: int):
        cursor = self.conn.cursor()
        cursor.execute(
            'DELETE FROM archetype_source_entries '
            'WHERE archetype_id = ? AND source_id = ?',
            (archetype_id, source_id)
        )
        self._commit()
