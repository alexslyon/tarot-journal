"""
Database operations for correspondence systems and assignments.

Three-tier inheritance:
1. Correspondence systems define canonical assignments per archetype
2. Decks select a system — cards inherit from it
3. Individual cards can override inherited values
"""

import re

CORRESPONDENCE_FIELDS = (
    'element', 'planet', 'zodiac_sign', 'decan',
    'hebrew_letter', 'numerology', 'rune', 'i_ching_hexagram',
    'chakra',
)

ZODIAC_SIGNS = {
    'aries', 'taurus', 'gemini', 'cancer', 'leo', 'virgo',
    'libra', 'scorpio', 'sagittarius', 'capricorn', 'aquarius', 'pisces',
}

PLANETS = {
    'sun', 'moon', 'mercury', 'venus', 'mars',
    'jupiter', 'saturn', 'uranus', 'neptune', 'pluto',
}

DECAN_PATTERN = re.compile(
    r'^(\w+)\s+in\s+(\w+)$', re.IGNORECASE
)


def parse_decan(value: str):
    """Parse a decan string like 'Jupiter in Libra'.

    Returns (planet, zodiac_sign) or None if not a decan pattern.
    """
    m = DECAN_PATTERN.match(value.strip())
    if not m:
        return None
    planet, sign = m.group(1), m.group(2)
    if planet.lower() in PLANETS and sign.lower() in ZODIAC_SIGNS:
        return planet.title(), sign.title()
    return None


class CorrespondencesMixin:
    """Mixin providing correspondence system and assignment operations."""

    # === Correspondence Systems ===

    def get_correspondence_systems(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT cs.*,
                   (SELECT COUNT(DISTINCT archetype_id)
                    FROM correspondence_assignments
                    WHERE system_id = cs.id) AS archetype_count,
                   (SELECT COUNT(*)
                    FROM correspondence_assignments
                    WHERE system_id = cs.id) AS assignment_count
            FROM correspondence_systems cs
            ORDER BY cs.is_builtin DESC, cs.name
        ''')
        return cursor.fetchall()

    def get_correspondence_system(self, system_id: int):
        cursor = self.conn.cursor()
        cursor.execute(
            'SELECT * FROM correspondence_systems WHERE id = ?', (system_id,)
        )
        return cursor.fetchone()

    def create_correspondence_system(self, name: str, description: str = None,
                                     is_builtin: bool = False):
        cursor = self.conn.cursor()
        cursor.execute(
            '''INSERT INTO correspondence_systems (name, description, is_builtin)
               VALUES (?, ?, ?)''',
            (name, description, int(is_builtin))
        )
        self._commit()
        return cursor.lastrowid

    def update_correspondence_system(self, system_id: int, name: str = None,
                                     description: str = None):
        cursor = self.conn.cursor()
        if name is not None:
            cursor.execute(
                'UPDATE correspondence_systems SET name = ? WHERE id = ?',
                (name, system_id)
            )
        if description is not None:
            cursor.execute(
                'UPDATE correspondence_systems SET description = ? WHERE id = ?',
                (description, system_id)
            )
        self._commit()

    def delete_correspondence_system(self, system_id: int):
        cursor = self.conn.cursor()
        cursor.execute(
            'DELETE FROM correspondence_systems WHERE id = ?', (system_id,)
        )
        self._commit()

    def clone_correspondence_system(self, source_id: int, new_name: str):
        """Clone an existing system with all its assignments."""
        source = self.get_correspondence_system(source_id)
        if not source:
            return None
        new_id = self.create_correspondence_system(
            new_name, source['description']
        )
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO correspondence_assignments
                (system_id, archetype_id, field_name, field_value)
            SELECT ?, archetype_id, field_name, field_value
            FROM correspondence_assignments
            WHERE system_id = ?
        ''', (new_id, source_id))
        self._commit()
        return new_id

    # === System-Level Assignments ===

    def get_system_assignments(self, system_id: int, archetype_id: int = None):
        """Get assignments for a system, optionally filtered by archetype."""
        cursor = self.conn.cursor()
        if archetype_id:
            cursor.execute('''
                SELECT ca.*, a.name AS archetype_name, a.cartomancy_type,
                       a.rank, a.suit, a.card_type
                FROM correspondence_assignments ca
                JOIN card_archetypes a ON a.id = ca.archetype_id
                WHERE ca.system_id = ? AND ca.archetype_id = ?
                ORDER BY CAST(a.rank AS INTEGER)
            ''', (system_id, archetype_id))
        else:
            cursor.execute('''
                SELECT ca.*, a.name AS archetype_name, a.cartomancy_type,
                       a.rank, a.suit, a.card_type
                FROM correspondence_assignments ca
                JOIN card_archetypes a ON a.id = ca.archetype_id
                WHERE ca.system_id = ?
                ORDER BY a.cartomancy_type, CAST(a.rank AS INTEGER)
            ''', (system_id,))
        return cursor.fetchall()

    def set_system_assignment(self, system_id: int, archetype_id: int,
                              field_name: str, field_value: str):
        """Set or update a single assignment. Handles decan derivation."""
        if field_name not in CORRESPONDENCE_FIELDS:
            raise ValueError(f"Invalid field name: {field_name}")
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO correspondence_assignments
                (system_id, archetype_id, field_name, field_value)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(system_id, archetype_id, field_name)
            DO UPDATE SET field_value = excluded.field_value
        ''', (system_id, archetype_id, field_name, field_value))

        # Decan derivation: auto-set planet and zodiac_sign
        if field_name == 'decan':
            derived = parse_decan(field_value)
            if derived:
                planet, sign = derived
                # Only set if not already explicitly set
                cursor.execute('''
                    INSERT INTO correspondence_assignments
                        (system_id, archetype_id, field_name, field_value)
                    VALUES (?, ?, 'planet', ?)
                    ON CONFLICT(system_id, archetype_id, field_name)
                    DO UPDATE SET field_value = excluded.field_value
                ''', (system_id, archetype_id, planet))
                cursor.execute('''
                    INSERT INTO correspondence_assignments
                        (system_id, archetype_id, field_name, field_value)
                    VALUES (?, ?, 'zodiac_sign', ?)
                    ON CONFLICT(system_id, archetype_id, field_name)
                    DO UPDATE SET field_value = excluded.field_value
                ''', (system_id, archetype_id, sign))

        self._commit()

    def delete_system_assignment(self, system_id: int, archetype_id: int,
                                 field_name: str):
        cursor = self.conn.cursor()
        cursor.execute('''
            DELETE FROM correspondence_assignments
            WHERE system_id = ? AND archetype_id = ? AND field_name = ?
        ''', (system_id, archetype_id, field_name))
        self._commit()

    def bulk_set_system_assignments(self, system_id: int,
                                    assignments: list[dict]):
        """Bulk upsert assignments. Each dict: {archetype_id, field_name, field_value}."""
        cursor = self.conn.cursor()
        for a in assignments:
            if a['field_name'] not in CORRESPONDENCE_FIELDS:
                continue
            cursor.execute('''
                INSERT INTO correspondence_assignments
                    (system_id, archetype_id, field_name, field_value)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(system_id, archetype_id, field_name)
                DO UPDATE SET field_value = excluded.field_value
            ''', (system_id, a['archetype_id'], a['field_name'], a['field_value']))
        self._commit()

    # === Card-Level Overrides ===

    def set_card_correspondence_override(self, card_id: int, field_name: str,
                                         field_value: str):
        if field_name not in CORRESPONDENCE_FIELDS:
            raise ValueError(f"Invalid field name: {field_name}")
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO card_correspondence_overrides
                (card_id, field_name, field_value)
            VALUES (?, ?, ?)
            ON CONFLICT(card_id, field_name)
            DO UPDATE SET field_value = excluded.field_value
        ''', (card_id, field_name, field_value))

        # Decan derivation for card overrides too
        if field_name == 'decan' and field_value:
            derived = parse_decan(field_value)
            if derived:
                planet, sign = derived
                cursor.execute('''
                    INSERT INTO card_correspondence_overrides
                        (card_id, field_name, field_value)
                    VALUES (?, 'planet', ?)
                    ON CONFLICT(card_id, field_name)
                    DO UPDATE SET field_value = excluded.field_value
                ''', (card_id, planet))
                cursor.execute('''
                    INSERT INTO card_correspondence_overrides
                        (card_id, field_name, field_value)
                    VALUES (?, 'zodiac_sign', ?)
                    ON CONFLICT(card_id, field_name)
                    DO UPDATE SET field_value = excluded.field_value
                ''', (card_id, sign))

        self._commit()

    def delete_card_correspondence_override(self, card_id: int,
                                            field_name: str):
        cursor = self.conn.cursor()
        cursor.execute('''
            DELETE FROM card_correspondence_overrides
            WHERE card_id = ? AND field_name = ?
        ''', (card_id, field_name))
        self._commit()

    # === Resolved Correspondences (Three-Tier Inheritance) ===

    def get_card_correspondences(self, card_id: int):
        """Resolve all correspondence fields for a card with inheritance.

        Returns a list of dicts: [{field_name, value, source}]
        where source is 'override', 'inherited', or 'none'.
        """
        cursor = self.conn.cursor()
        # Get card info for archetype lookup
        cursor.execute('''
            SELECT c.archetype, c.deck_id, d.correspondence_system_id
            FROM cards c
            JOIN decks d ON d.id = c.deck_id
            WHERE c.id = ?
        ''', (card_id,))
        card = cursor.fetchone()
        if not card:
            return []

        result = []
        for field in CORRESPONDENCE_FIELDS:
            # Check card-level override first
            cursor.execute('''
                SELECT field_value FROM card_correspondence_overrides
                WHERE card_id = ? AND field_name = ?
            ''', (card_id, field))
            override = cursor.fetchone()
            if override:
                result.append({
                    'field_name': field,
                    'value': override['field_value'],
                    'source': 'override',
                })
                continue

            # Check system-level inheritance
            if card['correspondence_system_id'] and card['archetype']:
                cursor.execute('''
                    SELECT ca.field_value
                    FROM correspondence_assignments ca
                    JOIN card_archetypes a ON a.id = ca.archetype_id
                    WHERE ca.system_id = ?
                      AND a.name = ?
                      AND ca.field_name = ?
                ''', (card['correspondence_system_id'], card['archetype'], field))
                inherited = cursor.fetchone()
                if inherited:
                    result.append({
                        'field_name': field,
                        'value': inherited['field_value'],
                        'source': 'inherited',
                    })
                    continue

            result.append({
                'field_name': field,
                'value': None,
                'source': 'none',
            })

        return result

    def get_deck_correspondences(self, deck_id: int):
        """Get resolved correspondences for all cards in a deck.

        Returns a dict keyed by card_id, each value is a list of
        resolved correspondence dicts.
        """
        cursor = self.conn.cursor()
        cursor.execute('SELECT id FROM cards WHERE deck_id = ?', (deck_id,))
        cards = cursor.fetchall()
        result = {}
        for card in cards:
            result[card['id']] = self.get_card_correspondences(card['id'])
        return result

    # === Cross-System Queries (for Reference tab) ===

    def get_correspondences_by_archetype(self, archetype_id: int):
        """Get all systems' assignments for a single archetype."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT ca.*, cs.name AS system_name
            FROM correspondence_assignments ca
            JOIN correspondence_systems cs ON cs.id = ca.system_id
            WHERE ca.archetype_id = ?
            ORDER BY cs.name, ca.field_name
        ''', (archetype_id,))
        return cursor.fetchall()

    # === Stats / Insights Queries ===

    def get_correspondence_frequency(self, field_name: str, months: int = 6):
        """Count frequency of each value for a correspondence field across readings.

        Resolves correspondences for every card drawn in journal entries
        within the given time period, using the three-tier inheritance.
        Returns: [{value, count}] sorted by count descending.
        """
        if field_name not in CORRESPONDENCE_FIELDS:
            return []

        cursor = self.conn.cursor()
        # Get all readings within the period
        cursor.execute('''
            SELECT er.cards_used, er.deck_id
            FROM entry_readings er
            JOIN journal_entries je ON je.id = er.entry_id
            WHERE er.cards_used IS NOT NULL
              AND je.created_at >= date('now', ?)
        ''', (f'-{months} months',))

        import json
        value_counts = {}
        for row in cursor.fetchall():
            try:
                cards = json.loads(row['cards_used'])
            except (json.JSONDecodeError, TypeError):
                continue
            deck_id = row['deck_id']

            for card_entry in cards:
                card_name = card_entry.get('name')
                card_deck_id = card_entry.get('deck_id', deck_id)
                if not card_name or not card_deck_id:
                    continue

                # Look up the card
                cursor.execute('''
                    SELECT c.id, c.archetype, d.correspondence_system_id
                    FROM cards c
                    JOIN decks d ON d.id = c.deck_id
                    WHERE c.name = ? AND c.deck_id = ?
                    LIMIT 1
                ''', (card_name, card_deck_id))
                card_row = cursor.fetchone()
                if not card_row:
                    continue

                # Resolve the correspondence value (override → inherited → none)
                value = None

                # Check card override
                cursor.execute('''
                    SELECT field_value FROM card_correspondence_overrides
                    WHERE card_id = ? AND field_name = ?
                ''', (card_row['id'], field_name))
                override = cursor.fetchone()
                if override:
                    value = override['field_value']
                elif card_row['correspondence_system_id'] and card_row['archetype']:
                    # Check system inheritance
                    cursor.execute('''
                        SELECT ca.field_value
                        FROM correspondence_assignments ca
                        JOIN card_archetypes a ON a.id = ca.archetype_id
                        WHERE ca.system_id = ?
                          AND a.name = ?
                          AND ca.field_name = ?
                    ''', (card_row['correspondence_system_id'], card_row['archetype'], field_name))
                    inherited = cursor.fetchone()
                    if inherited:
                        value = inherited['field_value']

                if value:
                    value_counts[value] = value_counts.get(value, 0) + 1

        result = [{'value': v, 'count': c} for v, c in value_counts.items()]
        result.sort(key=lambda x: x['count'], reverse=True)
        return result

    def get_correspondence_timeline(self, field_name: str, months: int = 12):
        """Get monthly breakdown of correspondence field values across readings.

        Returns: [{period, values: {value: count, ...}}] for each month.
        """
        if field_name not in CORRESPONDENCE_FIELDS:
            return []

        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT er.cards_used, er.deck_id,
                   strftime('%Y-%m', je.created_at) as period
            FROM entry_readings er
            JOIN journal_entries je ON je.id = er.entry_id
            WHERE er.cards_used IS NOT NULL
              AND je.created_at >= date('now', ?)
            ORDER BY je.created_at
        ''', (f'-{months} months',))

        import json
        monthly = {}  # period -> {value -> count}
        for row in cursor.fetchall():
            try:
                cards = json.loads(row['cards_used'])
            except (json.JSONDecodeError, TypeError):
                continue
            deck_id = row['deck_id']
            period = row['period']
            if period not in monthly:
                monthly[period] = {}

            for card_entry in cards:
                card_name = card_entry.get('name')
                card_deck_id = card_entry.get('deck_id', deck_id)
                if not card_name or not card_deck_id:
                    continue

                cursor.execute('''
                    SELECT c.id, c.archetype, d.correspondence_system_id
                    FROM cards c
                    JOIN decks d ON d.id = c.deck_id
                    WHERE c.name = ? AND c.deck_id = ?
                    LIMIT 1
                ''', (card_name, card_deck_id))
                card_row = cursor.fetchone()
                if not card_row:
                    continue

                value = None
                cursor.execute('''
                    SELECT field_value FROM card_correspondence_overrides
                    WHERE card_id = ? AND field_name = ?
                ''', (card_row['id'], field_name))
                override = cursor.fetchone()
                if override:
                    value = override['field_value']
                elif card_row['correspondence_system_id'] and card_row['archetype']:
                    cursor.execute('''
                        SELECT ca.field_value
                        FROM correspondence_assignments ca
                        JOIN card_archetypes a ON a.id = ca.archetype_id
                        WHERE ca.system_id = ?
                          AND a.name = ?
                          AND ca.field_name = ?
                    ''', (card_row['correspondence_system_id'], card_row['archetype'], field_name))
                    inherited = cursor.fetchone()
                    if inherited:
                        value = inherited['field_value']

                if value:
                    monthly[period][value] = monthly[period].get(value, 0) + 1

        result = [{'period': p, 'values': v} for p, v in sorted(monthly.items())]
        return result

    def compare_correspondence_systems(self, system_ids: list[int]):
        """Compare assignments across multiple systems.

        Returns assignments grouped by archetype for the given systems.
        """
        if not system_ids:
            return []
        placeholders = ','.join('?' for _ in system_ids)
        cursor = self.conn.cursor()
        cursor.execute(f'''
            SELECT ca.*, cs.name AS system_name,
                   a.name AS archetype_name, a.cartomancy_type,
                   a.rank, a.suit, a.card_type
            FROM correspondence_assignments ca
            JOIN correspondence_systems cs ON cs.id = ca.system_id
            JOIN card_archetypes a ON a.id = ca.archetype_id
            WHERE ca.system_id IN ({placeholders})
            ORDER BY a.cartomancy_type, CAST(a.rank AS INTEGER), a.name, cs.name, ca.field_name
        ''', system_ids)
        return cursor.fetchall()
