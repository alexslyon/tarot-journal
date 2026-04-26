"""
Shared reference sources used across Reference features (Lenormand
combinations, Archetype notes, etc.).
"""


class ReferenceSourcesMixin:
    """Mixin providing CRUD for the shared sources list."""

    def get_reference_sources(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM reference_sources ORDER BY name')
        return cursor.fetchall()

    def create_reference_source(self, name: str) -> int:
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT INTO reference_sources (name) VALUES (?)',
            (name.strip(),)
        )
        self._commit()
        return cursor.lastrowid

    def update_reference_source(self, source_id: int, name: str):
        cursor = self.conn.cursor()
        cursor.execute(
            'UPDATE reference_sources SET name = ? WHERE id = ?',
            (name.strip(), source_id)
        )
        self._commit()

    def delete_reference_source(self, source_id: int, reassign_to: int = None):
        """Delete a source. Dependent rows in lenormand_meanings and
        archetype_notes_entries are either reassigned to another source or
        set to NULL — never deleted along with the source.
        """
        cursor = self.conn.cursor()
        if reassign_to is not None:
            cursor.execute(
                'UPDATE lenormand_meanings SET source_id = ? WHERE source_id = ?',
                (reassign_to, source_id)
            )
            cursor.execute(
                'UPDATE archetype_notes_entries SET source_id = ? WHERE source_id = ?',
                (reassign_to, source_id)
            )
        else:
            cursor.execute(
                'UPDATE lenormand_meanings SET source_id = NULL WHERE source_id = ?',
                (source_id,)
            )
            cursor.execute(
                'UPDATE archetype_notes_entries SET source_id = NULL WHERE source_id = ?',
                (source_id,)
            )
        cursor.execute('DELETE FROM reference_sources WHERE id = ?', (source_id,))
        self._commit()

    def count_reference_source_dependencies(self, source_id: int) -> dict:
        """Return how many rows in each dependent table reference this source.
        Used by the delete dialog to warn the user before reassignment.
        """
        cursor = self.conn.cursor()
        cursor.execute(
            'SELECT COUNT(*) FROM lenormand_meanings WHERE source_id = ?',
            (source_id,)
        )
        lenormand_count = cursor.fetchone()[0]
        cursor.execute(
            'SELECT COUNT(*) FROM archetype_notes_entries WHERE source_id = ?',
            (source_id,)
        )
        notes_count = cursor.fetchone()[0]
        return {
            'lenormand_meanings': lenormand_count,
            'archetype_notes_entries': notes_count,
        }
