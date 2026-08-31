"""
Reference sources — many-to-many with cartomancy types via
source_cartomancy_types. Each source carries its own authors list and
exposes per-type field sets (see ArchetypeSourceEntriesMixin).

Lenormand combinations still consume source attribution the legacy
way (per-pair meanings); the cartomancy_types junction isn't visible
to them.
"""


class ReferenceSourcesMixin:

    # === Sources =================================================

    def get_reference_sources(self, cartomancy_type: str = None):
        """List sources, optionally restricted to those that cover the
        given cartomancy type.

        Each returned dict has `authors` and `cartomancy_types` hydrated
        so the caller doesn't need follow-up fetches.
        """
        cursor = self.conn.cursor()
        if cartomancy_type is not None:
            cursor.execute(
                '''
                SELECT s.* FROM reference_sources s
                JOIN source_cartomancy_types sct ON sct.source_id = s.id
                WHERE sct.cartomancy_type = ?
                ORDER BY s.name
                ''',
                (cartomancy_type,)
            )
        else:
            cursor.execute('SELECT * FROM reference_sources ORDER BY name')
        rows = [dict(r) for r in cursor.fetchall()]

        if not rows:
            return rows
        ids = [r['id'] for r in rows]
        placeholders = ','.join('?' * len(ids))
        author_rows = cursor.execute(
            f'SELECT source_id, name FROM source_authors '
            f'WHERE source_id IN ({placeholders}) ORDER BY sort_order, id',
            ids
        ).fetchall()
        type_rows = cursor.execute(
            f'SELECT source_id, cartomancy_type FROM source_cartomancy_types '
            f'WHERE source_id IN ({placeholders}) ORDER BY cartomancy_type',
            ids
        ).fetchall()
        authors_by_source: dict[int, list[str]] = {}
        types_by_source: dict[int, list[str]] = {}
        for ar in author_rows:
            authors_by_source.setdefault(ar['source_id'], []).append(ar['name'])
        for tr in type_rows:
            types_by_source.setdefault(tr['source_id'], []).append(tr['cartomancy_type'])
        for r in rows:
            r['authors'] = authors_by_source.get(r['id'], [])
            r['cartomancy_types'] = types_by_source.get(r['id'], [])
        return rows

    def get_reference_source(self, source_id: int):
        cursor = self.conn.cursor()
        cursor.execute(
            'SELECT * FROM reference_sources WHERE id = ?',
            (source_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None
        d = dict(row)
        d['authors'] = [
            a['name']
            for a in cursor.execute(
                'SELECT name FROM source_authors '
                'WHERE source_id = ? ORDER BY sort_order, id',
                (source_id,)
            ).fetchall()
        ]
        d['cartomancy_types'] = [
            t['cartomancy_type']
            for t in cursor.execute(
                'SELECT cartomancy_type FROM source_cartomancy_types '
                'WHERE source_id = ? ORDER BY cartomancy_type',
                (source_id,)
            ).fetchall()
        ]
        return d

    def create_reference_source(
        self,
        name: str,
        cartomancy_types: list = None,
        authors: list = None,
    ) -> int:
        """Create a source covering one or more cartomancy types.

        At least one cartomancy type is required — callers should pick
        from the seeded cartomancy_types list. Duplicate types are
        deduped silently.
        """
        types = self._normalize_types(cartomancy_types)
        if not types:
            raise ValueError('At least one cartomancy type is required')
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT INTO reference_sources (name) VALUES (?)',
            (name.strip(),)
        )
        source_id = cursor.lastrowid
        for t in types:
            cursor.execute(
                'INSERT OR IGNORE INTO source_cartomancy_types (source_id, cartomancy_type) '
                'VALUES (?, ?)',
                (source_id, t)
            )
        self._set_source_authors(cursor, source_id, authors or [])
        self._commit()
        return source_id

    def update_reference_source(
        self,
        source_id: int,
        name: str = None,
        cartomancy_types: list = None,
        authors: list = None,
    ):
        """Update any subset of name / cartomancy_types / authors.

        For cartomancy_types and authors, passing a list does a full
        set-replace of the existing rows. Pass None to leave them
        alone. Cannot drop the last cartomancy type — at least one
        must remain.
        """
        cursor = self.conn.cursor()
        if name is not None:
            cursor.execute(
                'UPDATE reference_sources SET name = ? WHERE id = ?',
                (name.strip(), source_id)
            )
        if cartomancy_types is not None:
            new_types = self._normalize_types(cartomancy_types)
            if not new_types:
                raise ValueError('At least one cartomancy type is required')
            cursor.execute(
                'DELETE FROM source_cartomancy_types WHERE source_id = ?',
                (source_id,)
            )
            for t in new_types:
                cursor.execute(
                    'INSERT OR IGNORE INTO source_cartomancy_types (source_id, cartomancy_type) '
                    'VALUES (?, ?)',
                    (source_id, t)
                )
            # Fields scoped to a type that's no longer covered are
            # orphaned — drop them along with their entries (CASCADE)
            # so the source's effective field set stays in sync.
            cursor.execute(
                f'DELETE FROM source_fields WHERE source_id = ? '
                f'AND cartomancy_type NOT IN ({",".join("?" * len(new_types))})',
                [source_id, *new_types]
            )
        if authors is not None:
            self._set_source_authors(cursor, source_id, authors)
        self._commit()

    def delete_reference_source(self, source_id: int, reassign_to: int = None):
        """Delete a source. Lenormand-meaning rows are reassigned (or
        nulled out) to preserve the meaning text. Source fields and
        entries cascade away with the source via FK."""
        cursor = self.conn.cursor()
        new_value = reassign_to  # None = clear the attribution
        for table in ('combination_meanings', 'spreads'):
            cursor.execute(
                f'UPDATE {table} SET source_id = ? WHERE source_id = ?',
                (new_value, source_id)
            )
        cursor.execute('DELETE FROM reference_sources WHERE id = ?', (source_id,))
        self._commit()

    def count_reference_source_dependencies(self, source_id: int) -> dict:
        cursor = self.conn.cursor()
        meaning_count = cursor.execute(
            'SELECT COUNT(*) FROM combination_meanings WHERE source_id = ?',
            (source_id,)
        ).fetchone()[0]
        entry_count = cursor.execute(
            '''
            SELECT COUNT(*) FROM archetype_source_entries e
            JOIN source_fields f ON f.id = e.field_id
            WHERE f.source_id = ?
            ''',
            (source_id,)
        ).fetchone()[0]
        field_count = cursor.execute(
            'SELECT COUNT(*) FROM source_fields WHERE source_id = ?',
            (source_id,)
        ).fetchone()[0]
        return {
            'combination_meanings': meaning_count,
            'archetype_source_entries': entry_count,
            'source_fields': field_count,
        }

    # === Internal helpers =======================================

    def _set_source_authors(self, cursor, source_id: int, authors: list):
        cursor.execute('DELETE FROM source_authors WHERE source_id = ?', (source_id,))
        seen = set()
        sort_order = 0
        for raw in authors:
            if not isinstance(raw, str):
                continue
            name = raw.strip()
            if not name or name in seen:
                continue
            seen.add(name)
            cursor.execute(
                'INSERT INTO source_authors (source_id, name, sort_order) '
                'VALUES (?, ?, ?)',
                (source_id, name, sort_order)
            )
            sort_order += 1

    @staticmethod
    def _normalize_types(types) -> list:
        """Strip + dedupe a list of cartomancy type names. Preserves
        first-seen order."""
        if not types:
            return []
        if not isinstance(types, list):
            return []
        out = []
        seen = set()
        for raw in types:
            if not isinstance(raw, str):
                continue
            t = raw.strip()
            if not t or t in seen:
                continue
            seen.add(t)
            out.append(t)
        return out
