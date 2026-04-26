"""
Database operations for Lenormand card-combination meanings.

Schema overview:
- lenormand_sources: reusable source labels (books, websites, "Personal notes").
- lenormand_combinations: ordered (card_1, card_2) pair, created on demand.
- lenormand_meanings: individual meaning entries, optionally tagged with a source.

Card identities are canonical Lenormand numbers 1-36; names and images are
looked up at display time from the user's selected default Lenormand deck and
are not stored here.
"""


class LenormandCombinationsMixin:
    """Mixin providing CRUD for Lenormand combination meanings."""

    # === Sources ===

    def get_lenormand_sources(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM lenormand_sources ORDER BY name')
        return cursor.fetchall()

    def create_lenormand_source(self, name: str) -> int:
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT INTO lenormand_sources (name) VALUES (?)',
            (name.strip(),)
        )
        self._commit()
        return cursor.lastrowid

    def update_lenormand_source(self, source_id: int, name: str):
        cursor = self.conn.cursor()
        cursor.execute(
            'UPDATE lenormand_sources SET name = ? WHERE id = ?',
            (name.strip(), source_id)
        )
        self._commit()

    def delete_lenormand_source(self, source_id: int, reassign_to: int = None):
        """Delete a source. If meanings reference it, either reassign them to
        another source (reassign_to=<id>) or set them to unsourced (reassign_to=None).
        Never deletes the meanings themselves.
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
        cursor.execute('DELETE FROM lenormand_sources WHERE id = ?', (source_id,))
        self._commit()

    # === Combinations / meanings ===

    def _get_or_create_combination(self, cursor, card_1: int, card_2: int) -> int:
        """Look up the combination row for (card_1, card_2); create it if missing.
        Returns the combination id.
        """
        cursor.execute(
            'SELECT id FROM lenormand_combinations WHERE card_1 = ? AND card_2 = ?',
            (card_1, card_2)
        )
        row = cursor.fetchone()
        if row:
            return row[0] if not isinstance(row, dict) else row['id']
        cursor.execute(
            'INSERT INTO lenormand_combinations (card_1, card_2) VALUES (?, ?)',
            (card_1, card_2)
        )
        return cursor.lastrowid

    def get_lenormand_meanings(self, card_1: int, card_2: int):
        """Return all meanings for an ordered pair, joined with source name.
        Returns an empty list if no combination row exists yet.
        """
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT m.id, m.combination_id, m.meaning, m.source_id,
                   m.sort_order, m.created_at,
                   s.name AS source_name
            FROM lenormand_meanings m
            JOIN lenormand_combinations c ON c.id = m.combination_id
            LEFT JOIN lenormand_sources s ON s.id = m.source_id
            WHERE c.card_1 = ? AND c.card_2 = ?
            ORDER BY m.sort_order, m.id
        ''', (card_1, card_2))
        return cursor.fetchall()

    def add_lenormand_meaning(self, card_1: int, card_2: int,
                              meaning: str, source_id: int = None) -> int:
        """Create the combination row if needed, then append a new meaning at
        the end of its sort order. Returns the new meaning id.
        """
        if card_1 == card_2:
            raise ValueError('Lenormand combinations must use two different cards')
        if not (1 <= card_1 <= 36 and 1 <= card_2 <= 36):
            raise ValueError('Card numbers must be between 1 and 36')
        if not meaning or not meaning.strip():
            raise ValueError('Meaning text is required')
        cursor = self.conn.cursor()
        combination_id = self._get_or_create_combination(cursor, card_1, card_2)
        cursor.execute(
            'SELECT COALESCE(MAX(sort_order), -1) + 1 FROM lenormand_meanings '
            'WHERE combination_id = ?',
            (combination_id,)
        )
        next_order = cursor.fetchone()[0]
        cursor.execute('''
            INSERT INTO lenormand_meanings
                (combination_id, meaning, source_id, sort_order)
            VALUES (?, ?, ?, ?)
        ''', (combination_id, meaning, source_id, next_order))
        new_id = cursor.lastrowid
        self._commit()
        return new_id

    def update_lenormand_meaning(self, meaning_id: int, meaning: str = None,
                                 source_id: int = None,
                                 clear_source: bool = False):
        """Update the text and/or source of an existing meaning.

        Pass clear_source=True to explicitly set source_id to NULL; otherwise
        source_id=None means "leave the source unchanged".
        """
        cursor = self.conn.cursor()
        if meaning is not None:
            cursor.execute(
                'UPDATE lenormand_meanings SET meaning = ? WHERE id = ?',
                (meaning, meaning_id)
            )
        if clear_source:
            cursor.execute(
                'UPDATE lenormand_meanings SET source_id = NULL WHERE id = ?',
                (meaning_id,)
            )
        elif source_id is not None:
            cursor.execute(
                'UPDATE lenormand_meanings SET source_id = ? WHERE id = ?',
                (source_id, meaning_id)
            )
        self._commit()

    def delete_lenormand_meaning(self, meaning_id: int):
        """Delete a meaning. If it was the last meaning in its combination,
        also delete the combination row so we don't accumulate empty pairs.
        """
        cursor = self.conn.cursor()
        cursor.execute(
            'SELECT combination_id FROM lenormand_meanings WHERE id = ?',
            (meaning_id,)
        )
        row = cursor.fetchone()
        if not row:
            return
        combination_id = row[0] if not isinstance(row, dict) else row['combination_id']
        cursor.execute('DELETE FROM lenormand_meanings WHERE id = ?', (meaning_id,))
        cursor.execute(
            'SELECT COUNT(*) FROM lenormand_meanings WHERE combination_id = ?',
            (combination_id,)
        )
        if cursor.fetchone()[0] == 0:
            cursor.execute(
                'DELETE FROM lenormand_combinations WHERE id = ?',
                (combination_id,)
            )
        self._commit()

    def reorder_lenormand_meanings(self, combination_id: int,
                                   ordered_ids: list):
        """Set sort_order based on each id's position in ordered_ids."""
        cursor = self.conn.cursor()
        for i, meaning_id in enumerate(ordered_ids):
            cursor.execute(
                'UPDATE lenormand_meanings SET sort_order = ? '
                'WHERE id = ? AND combination_id = ?',
                (i, meaning_id, combination_id)
            )
        self._commit()
