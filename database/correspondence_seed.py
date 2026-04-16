"""
Seed data for the RWS Traditional correspondence system.

Sources: Standard Golden Dawn / Rider-Waite-Smith attributions.
These are the most commonly accepted Western esoteric correspondences.
"""


def seed_rws_correspondences(cursor):
    """Create the RWS Traditional system and populate its assignments."""

    # Create the system
    cursor.execute('''
        INSERT INTO correspondence_systems (name, description, is_builtin)
        VALUES (?, ?, 1)
    ''', (
        'RWS Traditional',
        'Standard Rider-Waite-Smith correspondences based on Golden Dawn attributions',
    ))
    system_id = cursor.lastrowid

    # === Major Arcana ===
    # Each entry: (archetype_name, element, planet, zodiac, decan, hebrew_letter, numerology)
    major_arcana = [
        ('The Fool',            'Air',   'Uranus',  None,          None,                   'Aleph',  '0'),
        ('The Magician',        None,    'Mercury', None,          None,                   'Beth',   '1'),
        ('The High Priestess',  'Water', 'Moon',    None,          None,                   'Gimel',  '2'),
        ('The Empress',         'Earth', 'Venus',   None,          None,                   'Daleth', '3'),
        ('The Emperor',         'Fire',  'Mars',    'Aries',       None,                   'He',     '4'),
        ('The Hierophant',      'Earth', None,      'Taurus',      None,                   'Vav',    '5'),
        ('The Lovers',          'Air',   None,      'Gemini',      None,                   'Zayin',  '6'),
        ('The Chariot',         'Water', None,      'Cancer',      None,                   'Cheth',  '7'),
        ('Strength',            'Fire',  None,      'Leo',         None,                   'Teth',   '8'),
        ('The Hermit',          'Earth', None,      'Virgo',       None,                   'Yod',    '9'),
        ('Wheel of Fortune',    None,    'Jupiter', None,          None,                   'Kaph',   '10'),
        ('Justice',             'Air',   None,      'Libra',       None,                   'Lamed',  '11'),
        ('The Hanged Man',      'Water', 'Neptune', None,          None,                   'Mem',    '12'),
        ('Death',               'Water', 'Pluto',   'Scorpio',     None,                   'Nun',    '13'),
        ('Temperance',          'Fire',  None,      'Sagittarius', None,                   'Samekh', '14'),
        ('The Devil',           'Earth', 'Saturn',  'Capricorn',   None,                   'Ayin',   '15'),
        ('The Tower',           'Fire',  'Mars',    None,          None,                   'Pe',     '16'),
        ('The Star',            'Air',   None,      'Aquarius',    None,                   'Tzade',  '17'),
        ('The Moon',            'Water', None,      'Pisces',      None,                   'Qoph',   '18'),
        ('The Sun',             'Fire',  'Sun',     None,          None,                   'Resh',   '19'),
        ('Judgement',           None,    'Pluto',   None,          None,                   'Shin',   '20'),
        ('The World',           'Earth', 'Saturn',  None,          None,                   'Tav',    '21'),
    ]

    for name, element, planet, zodiac, decan, hebrew, numerology in major_arcana:
        # Look up archetype ID
        cursor.execute(
            "SELECT id FROM card_archetypes WHERE name = ? AND cartomancy_type = 'Tarot'",
            (name,)
        )
        row = cursor.fetchone()
        if not row:
            continue
        arch_id = row[0]

        if element:
            _insert_assignment(cursor, system_id, arch_id, 'element', element)
        if planet:
            _insert_assignment(cursor, system_id, arch_id, 'planet', planet)
        if zodiac:
            _insert_assignment(cursor, system_id, arch_id, 'zodiac_sign', zodiac)
        if decan:
            _insert_assignment(cursor, system_id, arch_id, 'decan', decan)
        if hebrew:
            _insert_assignment(cursor, system_id, arch_id, 'hebrew_letter', hebrew)
        if numerology:
            _insert_assignment(cursor, system_id, arch_id, 'numerology', numerology)

    # === Minor Arcana: Suit Elements ===
    suit_elements = {
        'Wands': 'Fire',
        'Cups': 'Water',
        'Swords': 'Air',
        'Pentacles': 'Earth',
    }

    rank_names = [
        'Ace', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven',
        'Eight', 'Nine', 'Ten', 'Page', 'Knight', 'Queen', 'King',
    ]

    for suit, element in suit_elements.items():
        for i, rank in enumerate(rank_names):
            card_name = f"{rank} of {suit}"
            cursor.execute(
                "SELECT id FROM card_archetypes WHERE name = ? AND cartomancy_type = 'Tarot'",
                (card_name,)
            )
            row = cursor.fetchone()
            if not row:
                continue
            arch_id = row[0]

            # Element from suit
            _insert_assignment(cursor, system_id, arch_id, 'element', element)

            # Numerology for pips (Ace=1 through Ten=10)
            if i < 10:
                _insert_assignment(cursor, system_id, arch_id, 'numerology', str(i + 1))

    # === Minor Arcana: Decan Assignments (Golden Dawn) ===
    # Pip cards 2-10 have decan assignments
    decan_assignments = {
        # Wands (Fire)
        'Two of Wands':   'Mars in Aries',
        'Three of Wands': 'Sun in Aries',
        'Four of Wands':  'Venus in Aries',
        'Five of Wands':  'Saturn in Leo',
        'Six of Wands':   'Jupiter in Leo',
        'Seven of Wands': 'Mars in Leo',
        'Eight of Wands': 'Mercury in Sagittarius',
        'Nine of Wands':  'Moon in Sagittarius',
        'Ten of Wands':   'Saturn in Sagittarius',
        # Cups (Water)
        'Two of Cups':    'Venus in Cancer',
        'Three of Cups':  'Mercury in Cancer',
        'Four of Cups':   'Moon in Cancer',
        'Five of Cups':   'Mars in Scorpio',
        'Six of Cups':    'Sun in Scorpio',
        'Seven of Cups':  'Venus in Scorpio',
        'Eight of Cups':  'Saturn in Pisces',
        'Nine of Cups':   'Jupiter in Pisces',
        'Ten of Cups':    'Mars in Pisces',
        # Swords (Air)
        'Two of Swords':   'Moon in Libra',
        'Three of Swords': 'Saturn in Libra',
        'Four of Swords':  'Jupiter in Libra',
        'Five of Swords':  'Venus in Aquarius',
        'Six of Swords':   'Mercury in Aquarius',
        'Seven of Swords': 'Moon in Aquarius',
        'Eight of Swords': 'Jupiter in Gemini',
        'Nine of Swords':  'Mars in Gemini',
        'Ten of Swords':   'Sun in Gemini',
        # Pentacles (Earth)
        'Two of Pentacles':   'Jupiter in Capricorn',
        'Three of Pentacles': 'Mars in Capricorn',
        'Four of Pentacles':  'Sun in Capricorn',
        'Five of Pentacles':  'Mercury in Taurus',
        'Six of Pentacles':   'Moon in Taurus',
        'Seven of Pentacles': 'Saturn in Taurus',
        'Eight of Pentacles': 'Sun in Virgo',
        'Nine of Pentacles':  'Venus in Virgo',
        'Ten of Pentacles':   'Mercury in Virgo',
    }

    for card_name, decan_value in decan_assignments.items():
        cursor.execute(
            "SELECT id FROM card_archetypes WHERE name = ? AND cartomancy_type = 'Tarot'",
            (card_name,)
        )
        row = cursor.fetchone()
        if not row:
            continue
        arch_id = row[0]
        _insert_assignment(cursor, system_id, arch_id, 'decan', decan_value)

        # Derive planet and zodiac from decan
        parts = decan_value.split(' in ')
        if len(parts) == 2:
            _insert_assignment(cursor, system_id, arch_id, 'planet', parts[0])
            _insert_assignment(cursor, system_id, arch_id, 'zodiac_sign', parts[1])

    # === Court Card Zodiac Assignments (Golden Dawn) ===
    court_zodiac = {
        'King of Wands': ('Aries', 'Fire'),
        'Queen of Wands': ('Leo', 'Fire'),
        'Knight of Wands': ('Sagittarius', 'Fire'),
        'King of Cups': ('Cancer', 'Water'),
        'Queen of Cups': ('Scorpio', 'Water'),
        'Knight of Cups': ('Pisces', 'Water'),
        'King of Swords': ('Libra', 'Air'),
        'Queen of Swords': ('Aquarius', 'Air'),
        'Knight of Swords': ('Gemini', 'Air'),
        'King of Pentacles': ('Capricorn', 'Earth'),
        'Queen of Pentacles': ('Taurus', 'Earth'),
        'Knight of Pentacles': ('Virgo', 'Earth'),
    }

    for card_name, (zodiac, _element) in court_zodiac.items():
        cursor.execute(
            "SELECT id FROM card_archetypes WHERE name = ? AND cartomancy_type = 'Tarot'",
            (card_name,)
        )
        row = cursor.fetchone()
        if not row:
            continue
        arch_id = row[0]
        _insert_assignment(cursor, system_id, arch_id, 'zodiac_sign', zodiac)


def _insert_assignment(cursor, system_id, archetype_id, field_name, field_value):
    """Insert a single correspondence assignment, ignoring conflicts."""
    cursor.execute('''
        INSERT OR IGNORE INTO correspondence_assignments
            (system_id, archetype_id, field_name, field_value)
        VALUES (?, ?, ?, ?)
    ''', (system_id, archetype_id, field_name, field_value))
