"""
Database operations for the Archetype Languages reference feature.

- archetype_language_languages: user-defined language list with sort order.
- archetype_language_names: card names per (archetype, language), with optional
  romanization and IPA.
"""


class ArchetypeLanguagesMixin:
    """CRUD for archetype languages and their per-card name entries."""

    # === Languages ===

    def get_archetype_languages(self):
        cursor = self.conn.cursor()
        cursor.execute(
            'SELECT * FROM archetype_language_languages ORDER BY sort_order, name'
        )
        return cursor.fetchall()

    def create_archetype_language(self, name: str) -> int:
        cursor = self.conn.cursor()
        cursor.execute(
            'SELECT COALESCE(MAX(sort_order), -1) + 1 FROM archetype_language_languages'
        )
        next_order = cursor.fetchone()[0]
        cursor.execute(
            'INSERT INTO archetype_language_languages (name, sort_order) VALUES (?, ?)',
            (name.strip(), next_order)
        )
        self._commit()
        return cursor.lastrowid

    def update_archetype_language(self, language_id: int, name: str):
        cursor = self.conn.cursor()
        cursor.execute(
            'UPDATE archetype_language_languages SET name = ? WHERE id = ?',
            (name.strip(), language_id)
        )
        self._commit()

    def delete_archetype_language(self, language_id: int):
        """Delete a language; CASCADE drops all its name rows."""
        cursor = self.conn.cursor()
        cursor.execute(
            'DELETE FROM archetype_language_languages WHERE id = ?',
            (language_id,)
        )
        self._commit()

    def reorder_archetype_languages(self, ordered_ids: list):
        cursor = self.conn.cursor()
        for i, lid in enumerate(ordered_ids):
            cursor.execute(
                'UPDATE archetype_language_languages SET sort_order = ? WHERE id = ?',
                (i, lid)
            )
        self._commit()

    def count_archetype_language_names(self, language_id: int) -> int:
        """Number of name rows that would be removed if this language were deleted."""
        cursor = self.conn.cursor()
        cursor.execute(
            'SELECT COUNT(*) FROM archetype_language_names WHERE language_id = ?',
            (language_id,)
        )
        return cursor.fetchone()[0]

    # === Names per archetype ===

    def get_archetype_names(self, archetype_id: int):
        """Names for a single archetype, joined with language metadata."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT n.id, n.archetype_id, n.language_id, n.name,
                   n.romanization, n.ipa, n.sort_order, n.created_at,
                   l.name AS language_name, l.sort_order AS language_sort_order
            FROM archetype_language_names n
            JOIN archetype_language_languages l ON l.id = n.language_id
            WHERE n.archetype_id = ?
            ORDER BY l.sort_order, l.name, n.sort_order, n.id
        ''', (archetype_id,))
        return cursor.fetchall()

    def get_archetype_names_for_type(self, cartomancy_type: str):
        """All names for every archetype of a cartomancy type. Used by
        Languages table mode in the Reference viewer.
        """
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT n.id, n.archetype_id, n.language_id, n.name,
                   n.romanization, n.ipa, n.sort_order,
                   l.name AS language_name, l.sort_order AS language_sort_order,
                   a.name AS archetype_name, a.rank AS archetype_rank
            FROM archetype_language_names n
            JOIN archetype_language_languages l ON l.id = n.language_id
            JOIN card_archetypes a ON a.id = n.archetype_id
            WHERE a.cartomancy_type = ?
            ORDER BY CAST(a.rank AS INTEGER), a.id, l.sort_order, n.sort_order, n.id
        ''', (cartomancy_type,))
        return cursor.fetchall()

    def add_archetype_name(self, archetype_id: int, language_id: int,
                           name: str, romanization: str = None,
                           ipa: str = None) -> int:
        if not name or not name.strip():
            raise ValueError('Name is required')
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT COALESCE(MAX(sort_order), -1) + 1
            FROM archetype_language_names
            WHERE archetype_id = ? AND language_id = ?
        ''', (archetype_id, language_id))
        next_order = cursor.fetchone()[0]
        cursor.execute('''
            INSERT INTO archetype_language_names
                (archetype_id, language_id, name, romanization, ipa, sort_order)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (archetype_id, language_id, name.strip(),
              (romanization or '').strip() or None,
              (ipa or '').strip() or None,
              next_order))
        self._commit()
        return cursor.lastrowid

    def update_archetype_name(self, name_id: int, name: str = None,
                              romanization: str = None, ipa: str = None,
                              clear_romanization: bool = False,
                              clear_ipa: bool = False):
        cursor = self.conn.cursor()
        if name is not None:
            cursor.execute(
                'UPDATE archetype_language_names SET name = ? WHERE id = ?',
                (name.strip(), name_id)
            )
        if clear_romanization:
            cursor.execute(
                'UPDATE archetype_language_names SET romanization = NULL WHERE id = ?',
                (name_id,)
            )
        elif romanization is not None:
            cursor.execute(
                'UPDATE archetype_language_names SET romanization = ? WHERE id = ?',
                (romanization.strip() or None, name_id)
            )
        if clear_ipa:
            cursor.execute(
                'UPDATE archetype_language_names SET ipa = NULL WHERE id = ?',
                (name_id,)
            )
        elif ipa is not None:
            cursor.execute(
                'UPDATE archetype_language_names SET ipa = ? WHERE id = ?',
                (ipa.strip() or None, name_id)
            )
        self._commit()

    def delete_archetype_name(self, name_id: int):
        cursor = self.conn.cursor()
        cursor.execute(
            'DELETE FROM archetype_language_names WHERE id = ?',
            (name_id,)
        )
        self._commit()

    def reorder_archetype_names(self, archetype_id: int, language_id: int,
                                ordered_ids: list):
        """Reorder names within a single (archetype, language) group."""
        cursor = self.conn.cursor()
        for i, nid in enumerate(ordered_ids):
            cursor.execute('''
                UPDATE archetype_language_names SET sort_order = ?
                WHERE id = ? AND archetype_id = ? AND language_id = ?
            ''', (i, nid, archetype_id, language_id))
        self._commit()
