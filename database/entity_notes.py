"""
Source notes on non-card reference entities — signs, planets,
sephiroth, tree paths, chakras, numerology numbers.

One rich-text blob per (entity, reference source), mirroring the
archetype source entries' "absent = hidden" rule: blank content
deletes the row. Entities are identified by (kind, key) string pairs
('sign' / 'Leo', 'sephira' / 'Geburah', 'chakra' / 'Root', ...) —
they have no table of their own, the reference datasets are static.

Suit and rank keys are additionally scoped by deck type as
'<cartomancy_type>::<name>' ('Petit Lenormand::Clubs',
'Tarot::King') — the same suit name means different things in
different traditions. The other kinds are universal and stay bare.
"""

from datetime import datetime

ENTITY_KINDS = ('sign', 'planet', 'sephira', 'path', 'chakra', 'number',
                'suit', 'rank')


class EntityNotesMixin:

    def get_entity_notes(self, entity_kind: str, entity_key: str):
        """Non-empty notes for one entity, hydrated with source names,
        ordered by source name."""
        cursor = self.conn.cursor()
        rows = cursor.execute(
            '''
            SELECT n.id, n.entity_kind, n.entity_key, n.source_id,
                   n.content, n.updated_at, s.name AS source_name
            FROM entity_source_notes n
            JOIN reference_sources s ON s.id = n.source_id
            WHERE n.entity_kind = ? AND n.entity_key = ?
              AND n.content IS NOT NULL AND TRIM(n.content) != ''
            ORDER BY s.name
            ''',
            (entity_kind, entity_key)
        ).fetchall()
        return [dict(r) for r in rows]

    def set_entity_note(self, entity_kind: str, entity_key: str,
                        source_id: int, content: str):
        """Upsert one (entity, source) note. Blank content deletes."""
        if entity_kind not in ENTITY_KINDS:
            raise ValueError(f'Unknown entity kind: {entity_kind!r}')
        cursor = self.conn.cursor()
        if not content or not content.strip():
            cursor.execute(
                'DELETE FROM entity_source_notes '
                'WHERE entity_kind = ? AND entity_key = ? AND source_id = ?',
                (entity_kind, entity_key, source_id)
            )
        else:
            cursor.execute(
                '''
                INSERT INTO entity_source_notes
                    (entity_kind, entity_key, source_id, content, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT (entity_kind, entity_key, source_id) DO UPDATE SET
                    content = excluded.content,
                    updated_at = excluded.updated_at
                ''',
                (entity_kind, entity_key, source_id, content,
                 datetime.now().isoformat())
            )
        self._commit()
