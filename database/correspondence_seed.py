"""
Seeding for the built-in correspondence systems (defaults extracted
from the user's curated systems — see default_correspondences.py),
the I Ching system, and the field options.
"""


def seed_default_correspondences(cursor):
    """Create the built-in default systems (RWS Default, Thoth
    Default, Pre-Golden Dawn Order Default) from the extracted data in
    database/default_correspondences.py. Archetypes resolve by
    (name, cartomancy_type); assignments whose archetype doesn't exist
    in this database are skipped harmlessly."""
    from database.default_correspondences import DEFAULT_SYSTEMS

    for spec in DEFAULT_SYSTEMS:
        cursor.execute(
            'INSERT INTO correspondence_systems '
            '(name, description, is_builtin, cartomancy_type, naming_style) '
            'VALUES (?, ?, 1, ?, ?)',
            (spec['name'], spec['description'], spec['cartomancy_type'],
             spec['naming_style']))
        system_id = cursor.lastrowid
        for (arch_name, arch_type, field_name, field_value,
             source_group) in spec['assignments']:
            cursor.execute(
                'SELECT id FROM card_archetypes '
                'WHERE name = ? AND cartomancy_type = ?',
                (arch_name, arch_type))
            row = cursor.fetchone()
            if not row:
                continue
            cursor.execute(
                'INSERT INTO correspondence_assignments '
                '(system_id, archetype_id, field_name, field_value, '
                ' source_group) VALUES (?, ?, ?, ?, ?)',
                (system_id, row[0], field_name, field_value, source_group))


def _insert_assignment(cursor, system_id, archetype_id, field_name, field_value):
    """Insert a single correspondence assignment, ignoring conflicts."""
    cursor.execute('''
        INSERT OR IGNORE INTO correspondence_assignments
            (system_id, archetype_id, field_name, field_value)
        VALUES (?, ?, ?, ?)
    ''', (system_id, archetype_id, field_name, field_value))


def seed_i_ching_correspondences(cursor):
    """Create the I Ching Default system mapping each archetype to its hexagram.

    Joins on rank (1-64) so the mapping is robust against archetype-name
    edits — every I Ching archetype gets the matching I_CHING_HEXAGRAMS entry.
    """
    cursor.execute('''
        INSERT INTO correspondence_systems
            (name, description, is_builtin, cartomancy_type)
        VALUES (?, ?, 1, 'I Ching')
    ''', (
        'I Ching Default',
        'Each I Ching card mapped to its corresponding hexagram.',
    ))
    system_id = cursor.lastrowid

    cursor.execute(
        "SELECT id, rank FROM card_archetypes WHERE cartomancy_type = 'I Ching'"
    )
    for arch_id, rank in cursor.fetchall():
        try:
            n = int(rank)
        except (TypeError, ValueError):
            continue
        if not 1 <= n <= 64:
            continue
        _insert_assignment(
            cursor, system_id, arch_id, 'i_ching_hexagram',
            I_CHING_HEXAGRAMS[n - 1],
        )


I_CHING_HEXAGRAMS = [
    '1 \u4dc0 The Creative',
    '2 \u4dc1 The Receptive',
    '3 \u4dc2 Difficulty at the Beginning',
    '4 \u4dc3 Youthful Folly',
    '5 \u4dc4 Waiting',
    '6 \u4dc5 Conflict',
    '7 \u4dc6 The Army',
    '8 \u4dc7 Holding Together',
    '9 \u4dc8 The Taming Power of the Small',
    '10 \u4dc9 Treading',
    '11 \u4dca Peace',
    '12 \u4dcb Standstill',
    '13 \u4dcc Fellowship with Men',
    '14 \u4dcd Possession in Great Measure',
    '15 \u4dce Modesty',
    '16 \u4dcf Enthusiasm',
    '17 \u4dd0 Following',
    '18 \u4dd1 Work on What Has Been Spoiled',
    '19 \u4dd2 Approach',
    '20 \u4dd3 Contemplation',
    '21 \u4dd4 Biting Through',
    '22 \u4dd5 Grace',
    '23 \u4dd6 Splitting Apart',
    '24 \u4dd7 Return',
    '25 \u4dd8 Innocence',
    '26 \u4dd9 The Taming Power of the Great',
    '27 \u4dda Nourishment',
    '28 \u4ddb Preponderance of the Great',
    '29 \u4ddc The Abysmal (Water)',
    '30 \u4ddd The Clinging (Fire)',
    '31 \u4dde Influence',
    '32 \u4ddf Duration',
    '33 \u4de0 Retreat',
    '34 \u4de1 The Power of the Great',
    '35 \u4de2 Progress',
    '36 \u4de3 Darkening of the Light',
    '37 \u4de4 The Family',
    '38 \u4de5 Opposition',
    '39 \u4de6 Obstruction',
    '40 \u4de7 Deliverance',
    '41 \u4de8 Decrease',
    '42 \u4de9 Increase',
    '43 \u4dea Breakthrough',
    '44 \u4deb Coming to Meet',
    '45 \u4dec Gathering Together',
    '46 \u4ded Pushing Upward',
    '47 \u4dee Oppression',
    '48 \u4def The Well',
    '49 \u4df0 Revolution',
    '50 \u4df1 The Cauldron',
    '51 \u4df2 The Arousing (Thunder)',
    '52 \u4df3 Keeping Still (Mountain)',
    '53 \u4df4 Development',
    '54 \u4df5 The Marrying Maiden',
    '55 \u4df6 Abundance',
    '56 \u4df7 The Wanderer',
    '57 \u4df8 The Gentle (Wind)',
    '58 \u4df9 The Joyous (Lake)',
    '59 \u4dfa Dispersion',
    '60 \u4dfb Limitation',
    '61 \u4dfc Inner Truth',
    '62 \u4dfd Preponderance of the Small',
    '63 \u4dfe After Completion',
    '64 \u4dff Before Completion',
]


def seed_field_options(cursor):
    """Populate the default options for each correspondence field."""

    planets = ['Sun', 'Moon', 'Mercury', 'Venus', 'Mars',
               'Jupiter', 'Saturn', 'Uranus', 'Neptune', 'Pluto']
    signs = ['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo',
             'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces']

    options = {
        'element': ['Fire', 'Water', 'Air', 'Earth', 'Aether', 'Spirit'],
        'planet': planets,
        'zodiac_sign': signs,
        'decan': [f'{p} in {s}' for s in signs for p in planets],
        # 22 Hebrew letters of the Kabbalah (traditional Golden Dawn attribution order)
        'hebrew_letter': [
            'Aleph', 'Beth', 'Gimel', 'Daleth', 'He', 'Vav', 'Zayin',
            'Cheth', 'Teth', 'Yod', 'Kaph', 'Lamed', 'Mem', 'Nun',
            'Samekh', 'Ayin', 'Pe', 'Tzade', 'Qoph', 'Resh', 'Shin', 'Tav',
        ],
        'numerology': [str(i) for i in range(0, 22)],
        # Elder Futhark (24 runes, in traditional order)
        'rune': [
            'Fehu', 'Uruz', 'Thurisaz', 'Ansuz', 'Raidho', 'Kenaz', 'Gebo', 'Wunjo',
            'Hagalaz', 'Nauthiz', 'Isa', 'Jera', 'Eihwaz', 'Perthro', 'Algiz', 'Sowilo',
            'Tiwaz', 'Berkano', 'Ehwaz', 'Mannaz', 'Laguz', 'Ingwaz', 'Dagaz', 'Othala',
        ],
        'i_ching_hexagram': list(I_CHING_HEXAGRAMS),
        'chakra': [
            'Root', 'Sacral', 'Solar Plexus', 'Heart', 'Throat', 'Third Eye', 'Crown',
        ],
        'modality': ['Cardinal', 'Fixed', 'Mutable'],
        # Standard 12 astrological houses with the most common keyword for each.
        'astrological_house': [
            '1st House (Self)',
            '2nd House (Possessions)',
            '3rd House (Communication)',
            '4th House (Home)',
            '5th House (Pleasure)',
            '6th House (Health)',
            '7th House (Partnership)',
            '8th House (Transformation)',
            '9th House (Philosophy)',
            '10th House (Career)',
            '11th House (Friendship)',
            '12th House (Subconscious)',
        ],
    }

    for field_name, values in options.items():
        for i, value in enumerate(values):
            cursor.execute('''
                INSERT OR IGNORE INTO correspondence_field_options
                    (field_name, option_value, sort_order)
                VALUES (?, ?, ?)
            ''', (field_name, value, i))
