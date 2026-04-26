"""
Database operations for the Archetype Notes reference feature.

- archetype_notes_field_defs: per-archetype field definitions (e.g.
  "Divinatory Meaning", "Symbolism"). archetype_id is nullable so a future
  migration can promote definitions to per-cartomancy-type without a schema
  rewrite (see PLANNING_ARCHETYPES.md).
- archetype_notes_entries: individual entries per field, optionally tagged
  with a shared reference source.
"""


class ArchetypeNotesMixin:
    """CRUD for archetype notes fields and entries."""

    # === Field definitions (per archetype, currently) ===

    def get_archetype_note_fields(self, archetype_id: int):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM archetype_notes_field_defs
            WHERE archetype_id = ?
            ORDER BY field_order, id
        ''', (archetype_id,))
        return cursor.fetchall()

    def create_archetype_note_field(self, archetype_id: int,
                                    field_name: str) -> int:
        if not field_name or not field_name.strip():
            raise ValueError('Field name is required')
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT COALESCE(MAX(field_order), -1) + 1
            FROM archetype_notes_field_defs
            WHERE archetype_id = ?
        ''', (archetype_id,))
        next_order = cursor.fetchone()[0]
        cursor.execute('''
            INSERT INTO archetype_notes_field_defs
                (archetype_id, field_name, field_order)
            VALUES (?, ?, ?)
        ''', (archetype_id, field_name.strip(), next_order))
        self._commit()
        return cursor.lastrowid

    def update_archetype_note_field(self, field_id: int, field_name: str):
        cursor = self.conn.cursor()
        cursor.execute(
            'UPDATE archetype_notes_field_defs SET field_name = ? WHERE id = ?',
            (field_name.strip(), field_id)
        )
        self._commit()

    def delete_archetype_note_field(self, field_id: int):
        """Delete a field. CASCADE removes its entries."""
        cursor = self.conn.cursor()
        cursor.execute(
            'DELETE FROM archetype_notes_field_defs WHERE id = ?',
            (field_id,)
        )
        self._commit()

    def reorder_archetype_note_fields(self, archetype_id: int,
                                      ordered_ids: list):
        cursor = self.conn.cursor()
        for i, fid in enumerate(ordered_ids):
            cursor.execute('''
                UPDATE archetype_notes_field_defs SET field_order = ?
                WHERE id = ? AND archetype_id = ?
            ''', (i, fid, archetype_id))
        self._commit()

    def count_archetype_note_field_entries(self, field_id: int) -> int:
        cursor = self.conn.cursor()
        cursor.execute(
            'SELECT COUNT(*) FROM archetype_notes_entries WHERE field_def_id = ?',
            (field_id,)
        )
        return cursor.fetchone()[0]

    # === Entries within a field ===

    def get_archetype_note_entries(self, field_id: int):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT e.id, e.field_def_id, e.content, e.source_id,
                   e.sort_order, e.created_at,
                   s.name AS source_name
            FROM archetype_notes_entries e
            LEFT JOIN reference_sources s ON s.id = e.source_id
            WHERE e.field_def_id = ?
            ORDER BY e.sort_order, e.id
        ''', (field_id,))
        return cursor.fetchall()

    def get_archetype_notes(self, archetype_id: int):
        """Convenience: every entry for an archetype, joined with its field
        definition and source. Used by the Reference viewer.
        """
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT e.id, e.field_def_id, e.content, e.source_id,
                   e.sort_order, e.created_at,
                   s.name AS source_name,
                   f.field_name, f.field_order
            FROM archetype_notes_field_defs f
            LEFT JOIN archetype_notes_entries e ON e.field_def_id = f.id
            LEFT JOIN reference_sources s ON s.id = e.source_id
            WHERE f.archetype_id = ?
            ORDER BY f.field_order, f.id, e.sort_order, e.id
        ''', (archetype_id,))
        return cursor.fetchall()

    def add_archetype_note_entry(self, field_id: int, content: str,
                                 source_id: int = None) -> int:
        if not content or not content.strip():
            raise ValueError('Entry content is required')
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT COALESCE(MAX(sort_order), -1) + 1
            FROM archetype_notes_entries
            WHERE field_def_id = ?
        ''', (field_id,))
        next_order = cursor.fetchone()[0]
        cursor.execute('''
            INSERT INTO archetype_notes_entries
                (field_def_id, content, source_id, sort_order)
            VALUES (?, ?, ?, ?)
        ''', (field_id, content, source_id, next_order))
        self._commit()
        return cursor.lastrowid

    def update_archetype_note_entry(self, entry_id: int,
                                    content: str = None,
                                    source_id: int = None,
                                    clear_source: bool = False):
        cursor = self.conn.cursor()
        if content is not None:
            cursor.execute(
                'UPDATE archetype_notes_entries SET content = ? WHERE id = ?',
                (content, entry_id)
            )
        if clear_source:
            cursor.execute(
                'UPDATE archetype_notes_entries SET source_id = NULL WHERE id = ?',
                (entry_id,)
            )
        elif source_id is not None:
            cursor.execute(
                'UPDATE archetype_notes_entries SET source_id = ? WHERE id = ?',
                (source_id, entry_id)
            )
        self._commit()

    def delete_archetype_note_entry(self, entry_id: int):
        cursor = self.conn.cursor()
        cursor.execute(
            'DELETE FROM archetype_notes_entries WHERE id = ?',
            (entry_id,)
        )
        self._commit()

    def reorder_archetype_note_entries(self, field_id: int,
                                       ordered_ids: list):
        cursor = self.conn.cursor()
        for i, eid in enumerate(ordered_ids):
            cursor.execute('''
                UPDATE archetype_notes_entries SET sort_order = ?
                WHERE id = ? AND field_def_id = ?
            ''', (i, eid, field_id))
        self._commit()
