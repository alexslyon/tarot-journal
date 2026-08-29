"""
Static reference datasets for the Reference tab: astrology (signs and
planets), Kabbalah (sephiroth and Tree of Life paths), chakras, and
numerology.

Curated content only — everything computable lives elsewhere and is
never re-declared here: decan spans, decan rulers, sign/planet trumps,
and court systems all come from birth_cards.py; which of the user's
cards belong to a sign/planet/letter/number/chakra comes live from
their correspondence systems at request time (backend/routes/
reference_content.py).

Conventions shared with birth_cards.py: Majors are integers 1-22 with
The Fool as 22; names resolve at the render boundary. Trump
attributions follow the Golden Dawn scheme, noted where modern
(outer-planet) attributions are used.
"""

# === Astrology ===

# Sign order matches birth_cards._SIGN_ORDER (Aries first). Date spans
# are implied by the decan calendar in birth_cards.DECANS — the route
# derives them; they are deliberately not repeated here.
SIGNS = [
    {'name': 'Aries', 'glyph': '♈', 'element': 'Fire', 'modality': 'Cardinal',
     'ruler': 'Mars',
     'themes': 'Initiative, courage, self-assertion, the spark that starts things.'},
    {'name': 'Taurus', 'glyph': '♉', 'element': 'Earth', 'modality': 'Fixed',
     'ruler': 'Venus',
     'themes': 'Stability, embodiment, patience, material pleasure and worth.'},
    {'name': 'Gemini', 'glyph': '♊', 'element': 'Air', 'modality': 'Mutable',
     'ruler': 'Mercury',
     'themes': 'Curiosity, exchange, duality, language and quick connection.'},
    {'name': 'Cancer', 'glyph': '♋', 'element': 'Water', 'modality': 'Cardinal',
     'ruler': 'Moon',
     'themes': 'Nurture, memory, home, protective feeling and belonging.'},
    {'name': 'Leo', 'glyph': '♌', 'element': 'Fire', 'modality': 'Fixed',
     'ruler': 'Sun',
     'themes': 'Radiance, creative self-expression, generosity, sovereignty.'},
    {'name': 'Virgo', 'glyph': '♍', 'element': 'Earth', 'modality': 'Mutable',
     'ruler': 'Mercury',
     'themes': 'Discernment, craft, service, refinement of the useful.'},
    {'name': 'Libra', 'glyph': '♎', 'element': 'Air', 'modality': 'Cardinal',
     'ruler': 'Venus',
     'themes': 'Balance, relationship, aesthetics, weighing and fairness.'},
    {'name': 'Scorpio', 'glyph': '♏', 'element': 'Water', 'modality': 'Fixed',
     'ruler': 'Mars', 'modern_ruler': 'Pluto',
     'themes': 'Intensity, transformation, the hidden, death-and-rebirth.'},
    {'name': 'Sagittarius', 'glyph': '♐', 'element': 'Fire', 'modality': 'Mutable',
     'ruler': 'Jupiter',
     'themes': 'Aspiration, the long view, philosophy, the aimed arrow.'},
    {'name': 'Capricorn', 'glyph': '♑', 'element': 'Earth', 'modality': 'Cardinal',
     'ruler': 'Saturn',
     'themes': 'Ambition, structure, mastery through time and limitation.'},
    {'name': 'Aquarius', 'glyph': '♒', 'element': 'Air', 'modality': 'Fixed',
     'ruler': 'Saturn', 'modern_ruler': 'Uranus',
     'themes': 'The collective, ideals, invention, detachment and reform.'},
    {'name': 'Pisces', 'glyph': '♓', 'element': 'Water', 'modality': 'Mutable',
     'ruler': 'Jupiter', 'modern_ruler': 'Neptune',
     'themes': 'Dissolution, compassion, dream and imagination, the boundless.'},
]

# Classical seven first (they carry Golden Dawn trump attributions via
# birth_cards.PLANET_MAJORS), then the three moderns, whose trumps are
# the common modern attributions to the elemental trumps (noted).
PLANETS = [
    {'name': 'Sun', 'glyph': '☉', 'classical': True,
     'rules': ['Leo'],
     'themes': 'Vitality, identity, purpose, the conscious center.'},
    {'name': 'Moon', 'glyph': '☽', 'classical': True,
     'rules': ['Cancer'],
     'themes': 'Instinct, rhythm, memory, the reflective and receptive.'},
    {'name': 'Mercury', 'glyph': '☿', 'classical': True,
     'rules': ['Gemini', 'Virgo'],
     'themes': 'Mind, language, exchange, travel between realms.'},
    {'name': 'Venus', 'glyph': '♀', 'classical': True,
     'rules': ['Taurus', 'Libra'],
     'themes': 'Attraction, harmony, value, art and affection.'},
    {'name': 'Mars', 'glyph': '♂', 'classical': True,
     'rules': ['Aries', 'Scorpio'],
     'themes': 'Drive, courage, conflict, the cutting edge of will.'},
    {'name': 'Jupiter', 'glyph': '♃', 'classical': True,
     'rules': ['Sagittarius', 'Pisces'],
     'themes': 'Expansion, fortune, meaning, generosity and excess.'},
    {'name': 'Saturn', 'glyph': '♄', 'classical': True,
     'rules': ['Capricorn', 'Aquarius'],
     'themes': 'Limitation, time, discipline, the structures that endure.'},
    {'name': 'Uranus', 'glyph': '♅', 'classical': False,
     'rules': ['Aquarius'],
     'themes': 'Rupture, awakening, invention, the sudden and original.'},
    {'name': 'Neptune', 'glyph': '♆', 'classical': False,
     'rules': ['Pisces'],
     'themes': 'Dissolution, glamour, the mystical and oceanic.'},
    {'name': 'Pluto', 'glyph': '♇', 'classical': False,
     'rules': ['Scorpio'],
     'themes': 'The underworld, compulsion, destruction and regeneration.'},
]

# Modern attributions of the three outer planets to the Golden Dawn
# "elemental" trumps (Air, Water, Fire). Widely used; not in Book T
# itself, so kept separate from birth_cards.PLANET_MAJORS.
MODERN_PLANET_MAJORS = {
    'Uranus': 22,    # The Fool (Air)
    'Neptune': 12,   # The Hanged Man (Water)
    'Pluto': 20,     # Judgement (Fire)
}


# === Kabbalah ===

# Positions are abstract chart coordinates for the Tree of Life SVG:
# x in 0-100 (50 = middle pillar), y in 0-100 top-down. The standard
# GD/Kircher layout.
SEPHIROTH = [
    {'number': 1, 'name': 'Kether', 'hebrew': 'כתר', 'translation': 'Crown',
     'pillar': 'middle', 'planet': 'Primum Mobile', 'x': 50, 'y': 4,
     'meaning': 'The undifferentiated source; unity before any division.'},
    {'number': 2, 'name': 'Chokmah', 'hebrew': 'חכמה', 'translation': 'Wisdom',
     'pillar': 'mercy', 'planet': 'The Zodiac', 'x': 82, 'y': 16,
     'meaning': 'Pure dynamic force; the first flash of creative energy.'},
    {'number': 3, 'name': 'Binah', 'hebrew': 'בינה', 'translation': 'Understanding',
     'pillar': 'severity', 'planet': 'Saturn', 'x': 18, 'y': 16,
     'meaning': 'Form and limitation; the womb that gives force a shape.'},
    {'number': 4, 'name': 'Chesed', 'hebrew': 'חסד', 'translation': 'Mercy',
     'pillar': 'mercy', 'planet': 'Jupiter', 'x': 82, 'y': 38,
     'meaning': 'Expansive, ordering benevolence; building and abundance.'},
    {'number': 5, 'name': 'Geburah', 'hebrew': 'גבורה', 'translation': 'Severity',
     'pillar': 'severity', 'planet': 'Mars', 'x': 18, 'y': 38,
     'meaning': 'Restriction and rigor; the strength that cuts away.'},
    {'number': 6, 'name': 'Tiphareth', 'hebrew': 'תפארת', 'translation': 'Beauty',
     'pillar': 'middle', 'planet': 'Sun', 'x': 50, 'y': 50,
     'meaning': 'The reconciling center; harmony, sacrifice, the heart.'},
    {'number': 7, 'name': 'Netzach', 'hebrew': 'נצח', 'translation': 'Victory',
     'pillar': 'mercy', 'planet': 'Venus', 'x': 82, 'y': 62,
     'meaning': 'Desire, instinct, and feeling; the energies of nature.'},
    {'number': 8, 'name': 'Hod', 'hebrew': 'הוד', 'translation': 'Splendour',
     'pillar': 'severity', 'planet': 'Mercury', 'x': 18, 'y': 62,
     'meaning': 'Intellect and form-giving thought; language and magic.'},
    {'number': 9, 'name': 'Yesod', 'hebrew': 'יסוד', 'translation': 'Foundation',
     'pillar': 'middle', 'planet': 'Moon', 'x': 50, 'y': 74,
     'meaning': 'The astral matrix; image, dream, and the machinery of change.'},
    {'number': 10, 'name': 'Malkuth', 'hebrew': 'מלכות', 'translation': 'Kingdom',
     'pillar': 'middle', 'planet': 'The Elements', 'x': 50, 'y': 92,
     'meaning': 'The manifest world; everything brought into body and matter.'},
]

# Court ranks on the Tree, by the Tetragrammaton attribution (father
# court on Chokmah 2, mother on Binah 3, son on Tiphareth 6, daughter
# on Malkuth 10), rendered into RWS rank names per court system. User
# ruling 2026-08-28: the tree follows the saved Courts preference, and
# B.O.T.A. reads the same as Book T titles. Flat tables, never derived
# from one another.
TREE_COURT_RANKS = {
    'golden_dawn':       {2: 'King', 3: 'Queen', 6: 'Knight', 10: 'Page'},
    'golden_dawn_waite': {2: 'Knight', 3: 'Queen', 6: 'King', 10: 'Page'},
    'bota':              {2: 'King', 3: 'Queen', 6: 'Knight', 10: 'Page'},
}

# The 22 connecting paths, numbered 11-32 by GD convention, each
# carrying one Hebrew letter and one trump (Golden Dawn attributions;
# trump numbers use the internal 1-22 convention, The Fool = 22).
TREE_PATHS = [
    {'path': 11, 'from': 1, 'to': 2, 'letter': 'Aleph', 'glyph': 'א', 'value': 1, 'trump': 22},
    {'path': 12, 'from': 1, 'to': 3, 'letter': 'Beth', 'glyph': 'ב', 'value': 2, 'trump': 1},
    {'path': 13, 'from': 1, 'to': 6, 'letter': 'Gimel', 'glyph': 'ג', 'value': 3, 'trump': 2},
    {'path': 14, 'from': 2, 'to': 3, 'letter': 'Daleth', 'glyph': 'ד', 'value': 4, 'trump': 3},
    {'path': 15, 'from': 2, 'to': 6, 'letter': 'Heh', 'glyph': 'ה', 'value': 5, 'trump': 4},
    {'path': 16, 'from': 2, 'to': 4, 'letter': 'Vav', 'glyph': 'ו', 'value': 6, 'trump': 5},
    {'path': 17, 'from': 3, 'to': 6, 'letter': 'Zayin', 'glyph': 'ז', 'value': 7, 'trump': 6},
    {'path': 18, 'from': 3, 'to': 5, 'letter': 'Cheth', 'glyph': 'ח', 'value': 8, 'trump': 7},
    {'path': 19, 'from': 4, 'to': 5, 'letter': 'Teth', 'glyph': 'ט', 'value': 9, 'trump': 8},
    {'path': 20, 'from': 4, 'to': 6, 'letter': 'Yod', 'glyph': 'י', 'value': 10, 'trump': 9},
    {'path': 21, 'from': 4, 'to': 7, 'letter': 'Kaph', 'glyph': 'כ', 'value': 20, 'trump': 10},
    {'path': 22, 'from': 5, 'to': 6, 'letter': 'Lamed', 'glyph': 'ל', 'value': 30, 'trump': 11},
    {'path': 23, 'from': 5, 'to': 8, 'letter': 'Mem', 'glyph': 'מ', 'value': 40, 'trump': 12},
    {'path': 24, 'from': 6, 'to': 7, 'letter': 'Nun', 'glyph': 'נ', 'value': 50, 'trump': 13},
    {'path': 25, 'from': 6, 'to': 9, 'letter': 'Samekh', 'glyph': 'ס', 'value': 60, 'trump': 14},
    {'path': 26, 'from': 6, 'to': 8, 'letter': 'Ayin', 'glyph': 'ע', 'value': 70, 'trump': 15},
    {'path': 27, 'from': 7, 'to': 8, 'letter': 'Peh', 'glyph': 'פ', 'value': 80, 'trump': 16},
    {'path': 28, 'from': 7, 'to': 9, 'letter': 'Tzaddi', 'glyph': 'צ', 'value': 90, 'trump': 17},
    {'path': 29, 'from': 7, 'to': 10, 'letter': 'Qoph', 'glyph': 'ק', 'value': 100, 'trump': 18},
    {'path': 30, 'from': 8, 'to': 9, 'letter': 'Resh', 'glyph': 'ר', 'value': 200, 'trump': 19},
    {'path': 31, 'from': 8, 'to': 10, 'letter': 'Shin', 'glyph': 'ש', 'value': 300, 'trump': 20},
    {'path': 32, 'from': 9, 'to': 10, 'letter': 'Tav', 'glyph': 'ת', 'value': 400, 'trump': 21},
]


# === Suits ===

# Structural data only (no editorial prose — descriptions come from
# the user's reference sources as entity notes). Golden Dawn elemental
# attributions; playing-card counterparts are the common mapping.
SUIT_INFO = [
    {'name': 'Wands', 'element': 'Fire', 'glyph': '🜂',
     'alt_names': ['Rods', 'Staves', 'Batons', 'Clubs'],
     'playing_card': 'Clubs'},
    {'name': 'Cups', 'element': 'Water', 'glyph': '🜄',
     'alt_names': ['Chalices', 'Vessels', 'Hearts'],
     'playing_card': 'Hearts'},
    {'name': 'Swords', 'element': 'Air', 'glyph': '🜁',
     'alt_names': ['Blades', 'Spades'],
     'playing_card': 'Spades'},
    {'name': 'Pentacles', 'element': 'Earth', 'glyph': '🜃',
     'alt_names': ['Coins', 'Disks', 'Diamonds'],
     'playing_card': 'Diamonds'},
]

# Court ranks, low to high in RWS convention. Rank entities live in
# the Numerology & Ranks section beside the numbers.
COURT_RANKS = ['Page', 'Knight', 'Queen', 'King']

# The classic 36-card Lenormand playing-card insets, by card number.
# The archetypes' rank field holds the Lenormand number (1-36), so the
# inset attributions live here instead: number -> (rank word, suit).
# Standard Petit Lenormand set (each suit: Ace + Six through Ten +
# Jack, Queen, King).
LENORMAND_INSETS = {
    1: ('Nine', 'Hearts'),      # Rider
    2: ('Six', 'Diamonds'),     # Clover
    3: ('Ten', 'Spades'),       # Ship
    4: ('King', 'Hearts'),      # House
    5: ('Seven', 'Hearts'),     # Tree
    6: ('King', 'Clubs'),       # Clouds
    7: ('Queen', 'Clubs'),      # Snake
    8: ('Nine', 'Diamonds'),    # Coffin
    9: ('Queen', 'Spades'),     # Bouquet
    10: ('Jack', 'Diamonds'),   # Scythe
    11: ('Jack', 'Clubs'),      # Whip
    12: ('Seven', 'Diamonds'),  # Birds
    13: ('Jack', 'Spades'),     # Child
    14: ('Nine', 'Clubs'),      # Fox
    15: ('Ten', 'Clubs'),       # Bear
    16: ('Six', 'Hearts'),      # Stars
    17: ('Queen', 'Hearts'),    # Stork
    18: ('Ten', 'Hearts'),      # Dog
    19: ('Six', 'Spades'),      # Tower
    20: ('Eight', 'Spades'),    # Garden
    21: ('Eight', 'Clubs'),     # Mountain
    22: ('Queen', 'Diamonds'),  # Crossroads
    23: ('Seven', 'Clubs'),     # Mice
    24: ('Jack', 'Hearts'),     # Heart
    25: ('Ace', 'Clubs'),       # Ring
    26: ('Ten', 'Diamonds'),    # Book
    27: ('Seven', 'Spades'),    # Letter
    28: ('Ace', 'Hearts'),      # Man
    29: ('Ace', 'Spades'),      # Woman
    30: ('King', 'Spades'),     # Lily
    31: ('Ace', 'Diamonds'),    # Sun
    32: ('Eight', 'Hearts'),    # Moon
    33: ('Eight', 'Diamonds'),  # Key
    34: ('King', 'Diamonds'),   # Fish
    35: ('Nine', 'Spades'),     # Anchor
    36: ('Six', 'Clubs'),       # Cross
}


# === Chakras ===

# Root to crown. `color` is a plain CSS color used only as a small
# accent swatch — content color, not theme color.
CHAKRAS = [
    {'name': 'Root', 'sanskrit': 'Muladhara', 'color': '#c0392b',
     'location': 'Base of the spine',
     'themes': 'Survival, grounding, safety, belonging to the body and the earth.'},
    {'name': 'Sacral', 'sanskrit': 'Svadhisthana', 'color': '#e67e22',
     'location': 'Lower abdomen',
     'themes': 'Pleasure, desire, creativity, emotional flow.'},
    {'name': 'Solar Plexus', 'sanskrit': 'Manipura', 'color': '#f1c40f',
     'location': 'Upper abdomen',
     'themes': 'Will, confidence, personal power, digestion of experience.'},
    {'name': 'Heart', 'sanskrit': 'Anahata', 'color': '#27ae60',
     'location': 'Center of the chest',
     'themes': 'Love, compassion, connection, the bridge between lower and upper.'},
    {'name': 'Throat', 'sanskrit': 'Vishuddha', 'color': '#2980b9',
     'location': 'Throat',
     'themes': 'Expression, truth-telling, voice, listening.'},
    {'name': 'Third Eye', 'sanskrit': 'Ajna', 'color': '#4b3f9e',
     'location': 'Between the brows',
     'themes': 'Insight, imagination, inner vision, discernment beyond the senses.'},
    {'name': 'Crown', 'sanskrit': 'Sahasrara', 'color': '#8e44ad',
     'location': 'Top of the head',
     'themes': 'Unity, transcendence, connection to what is larger than the self.'},
]


# === Numerology ===

# Deliberately a flat, open-ended list — not a fixed 0-9 array. The
# number of entries, their labels ('11', '22', ... master numbers are
# fine later), and the optional `system` tag can all grow without any
# code change: the API returns whatever this list holds, in order, and
# the UI renders exactly that. Derived blocks (constellation Majors,
# matching pip Minors) attach at the route only where they apply.
NUMBERS = [
    {'number': '0', 'system': None, 'title': 'The Void / Infinite Potential',
     'meaning': 'Nothingness and everything. The unmanifest, pure potential '
                'before form. Freedom from limitation.',
     'tarot_connection': 'The Fool — the leap into the unknown, beginningless beginning.'},
    {'number': '1', 'system': None, 'title': 'Unity / Beginnings',
     'meaning': 'Individuality, initiative, will, leadership, new starts. The '
                'seed, the self, the singular point of origin.',
     'tarot_connection': 'The Magician and Aces — raw potential channeled into action.'},
    {'number': '2', 'system': None, 'title': 'Duality / Balance',
     'meaning': 'Partnership, polarity, receptivity, patience, choice between '
                'opposites. The first division — self and other.',
     'tarot_connection': 'The High Priestess and Twos — the threshold between known and unknown.'},
    {'number': '3', 'system': None, 'title': 'Creation / Expression',
     'meaning': 'Growth, creativity, synthesis, expansion, abundance. What '
                'emerges from the union of two — the child, the fruit.',
     'tarot_connection': 'The Empress and Threes — creative abundance and early fruition.'},
    {'number': '4', 'system': None, 'title': 'Structure / Foundation',
     'meaning': 'Stability, order, discipline, foundation, hard work. The four '
                'walls, the four directions — manifestation made solid.',
     'tarot_connection': 'The Emperor and Fours — authority, structure, and groundedness.'},
    {'number': '5', 'system': None, 'title': 'Change / Conflict',
     'meaning': 'Disruption, freedom, adventure, instability, challenge. The '
                'number that breaks the settled four — crisis and growth.',
     'tarot_connection': 'The Hierophant and Fives — upheaval that leads to deeper understanding.'},
    {'number': '6', 'system': None, 'title': 'Harmony / Responsibility',
     'meaning': 'Love, beauty, balance, nurturing, duty, home. Equilibrium '
                'restored after the disruption of five.',
     'tarot_connection': 'The Lovers and Sixes — choices made from the heart, reciprocity.'},
    {'number': '7', 'system': None, 'title': 'Introspection / Mystery',
     'meaning': 'Wisdom, analysis, solitude, spirituality, inner work. The '
                'seeker turning inward — not everything is visible.',
     'tarot_connection': 'The Chariot and Sevens — inner mastery and faith through uncertainty.'},
    {'number': '8', 'system': None, 'title': 'Power / Mastery',
     'meaning': 'Achievement, abundance, karma, material success, regeneration. '
                'Infinite energy (the lemniscate) applied with discipline.',
     'tarot_connection': 'Strength and Eights — endurance, control, and the consequences of effort.'},
    {'number': '9', 'system': None, 'title': 'Completion / Wisdom',
     'meaning': 'Fulfillment, humanitarianism, endings, universal compassion. '
                'The last single digit — the culmination of a cycle.',
     'tarot_connection': 'The Hermit and Nines — solitary wisdom at the end of a journey.'},
    {'number': '10', 'system': None, 'title': 'Cycle / Renewal',
     'meaning': 'Completion and new beginning combined. The full turn of the '
                'wheel — endings that contain seeds of the next cycle.',
     'tarot_connection': 'Wheel of Fortune and Tens — the cycle complete, turning toward what comes next.'},
]
