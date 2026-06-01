"""
Reference sources — typed per cartomancy type. Each source is the
column under which per-archetype content lives (see
ArchetypeSourceEntriesMixin), plus an optional list of authors.

Lenormand combinations still use this table the legacy way (per-pair
meanings with a source attribution); only Archetype reference content
moved onto the new (archetype_id, source_id) entry model.
"""


class ReferenceSourcesMixin:
    """Reference sources + their authors. Author rows live in the
    `source_authors` table and are returned as a list on get/list."""

    # === Sources =================================================

    def get_reference_sources(self, cartomancy_type: str = None):
        """List sources, optionally filtered by cartomancy type.

        Each returned dict has its `authors` array hydrated so callers
        don't need to do an N+1 fetch.
        """
        cursor = self.conn.cursor()
        if cartomancy_type is not None:
            cursor.execute(
                'SELECT * FROM reference_sources WHERE cartomancy_type = ? '
                'ORDER BY name',
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
        authors_by_source: dict[int, list[str]] = {}
        for ar in author_rows:
            authors_by_source.setdefault(ar['source_id'], []).append(ar['name'])
        for r in rows:
            r['authors'] = authors_by_source.get(r['id'], [])
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
        return d

    def create_reference_source(
        self,
        name: str,
        cartomancy_type: str,
        authors: list = None,
    ) -> int:
        """Create a source. cartomancy_type is required in the new model —
        callers should pick from the seeded cartomancy_types list."""
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT INTO reference_sources (name, cartomancy_type) VALUES (?, ?)',
            (name.strip(), cartomancy_type)
        )
        source_id = cursor.lastrowid
        self._set_source_authors(cursor, source_id, authors or [])
        self._commit()
        return source_id

    def update_reference_source(
        self,
        source_id: int,
        name: str = None,
        cartomancy_type: str = None,
        authors: list = None,
    ):
        """Update any subset of name / cartomancy_type / authors.

        Authors are upserted-as-a-set: passing a list replaces the
        existing rows entirely. Pass None to leave them untouched.
        """
        cursor = self.conn.cursor()
        updates = []
        params = []
        if name is not None:
            updates.append('name = ?')
            params.append(name.strip())
        if cartomancy_type is not None:
            updates.append('cartomancy_type = ?')
            params.append(cartomancy_type)
        if updates:
            params.append(source_id)
            cursor.execute(
                f'UPDATE reference_sources SET {", ".join(updates)} WHERE id = ?',
                params
            )
        if authors is not None:
            self._set_source_authors(cursor, source_id, authors)
        self._commit()

    def delete_reference_source(self, source_id: int, reassign_to: int = None):
        """Delete a source. Lenormand-meaning rows are reassigned (or
        nulled out) to preserve the meaning text. Archetype source
        entries are deleted along with the source via the FK CASCADE
        — they don't carry useful content without their source column.
        """
        cursor = self.conn.cursor()
        if reassign_to is not None:
            cursor.execute(
                'UPDATE lenormand_meanings SET source_id = ? WHERE source_id = ?',
                (reassign_to, source_id)
            )
        else:
            cursor.execute(
                'UPDATE lenormand_meanings SET source_id = NULL WHERE source_id = ?',
                (source_id,)
            )
        cursor.execute('DELETE FROM reference_sources WHERE id = ?', (source_id,))
        self._commit()

    def count_reference_source_dependencies(self, source_id: int) -> dict:
        """How many dependent rows reference this source. Entries are
        joined through the source's fields since the entry table no
        longer stores source_id directly."""
        cursor = self.conn.cursor()
        lenormand_count = cursor.execute(
            'SELECT COUNT(*) FROM lenormand_meanings WHERE source_id = ?',
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
            'lenormand_meanings': lenormand_count,
            'archetype_source_entries': entry_count,
            'source_fields': field_count,
        }

    # === Authors (internal helpers) ==============================

    def _set_source_authors(self, cursor, source_id: int, authors: list):
        """Replace the author rows for a source with the given list.

        Empty strings and whitespace-only names are filtered out;
        duplicates within a single update are deduped while preserving
        first-occurrence order so the user can paste a quick list
        without worrying about typos.
        """
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
