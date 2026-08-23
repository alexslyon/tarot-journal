"""
Birth card calculator — Mary K. Greer's "Lifetime Cards" system from
*Archetypal Tarot* (2021), per the spec in greer-birth-cards-spec.md.

Pure arithmetic on a birth date; no database, no interpretation. Majors
are integers 1-22 everywhere in this module — The Fool is 22, never 0.
Names (including the Strength/Justice 8-11 swap) are resolved only at
the render boundary via major_name() / card_ref_name().

Two addition methods are supported:
- "greer" (default):     month + day + full year
- "amberstone":          month + day + century + two-digit year
The Soul Card is identical under both (digit sums survive regrouping);
the Personality Card — and everything derived from it — can differ.
"""

from __future__ import annotations

from datetime import date

GREER = 'greer'
AMBERSTONE = 'amberstone'
METHODS = (GREER, AMBERSTONE)

# All Majors sharing a root digit (plus, conceptually, the Minors of
# that number). Roots 1-4 have three members; 5-9 have two.
CONSTELLATIONS = {
    1: [1, 10, 19], 2: [2, 11, 20], 3: [3, 12, 21],
    4: [4, 13, 22], 5: [5, 14], 6: [6, 15],
    7: [7, 16], 8: [8, 17], 9: [9, 18],
}

# Patterns whose Personality Card (Majors 14-18) is depicted at night
# in Waite-Smith; the shadow folds into the Personality Card and the
# hidden-factor set comes out empty. Display copy only.
NIGHTTIME_PATTERNS = {'14-5', '15-6', '16-7', '17-8', '18-9'}

SUITS = ('Wands', 'Cups', 'Swords', 'Pentacles')

# Golden Dawn "Book T" decan Minors on Greer's fixed calendar dates
# (two source typos corrected: 2 of Cups ends Jul 1; 2 of Swords ends
# Oct 2). Inclusive (month, day) bounds; the 3 of Pentacles range wraps
# the year boundary and is handled specially in zodiacal_card().
# Fixed dates, deliberately not ephemeris-accurate — matching the book.
DECANS = [
    ((3, 21), (3, 30), 2, 'Wands'),
    ((3, 31), (4, 10), 3, 'Wands'),
    ((4, 11), (4, 20), 4, 'Wands'),
    ((4, 21), (4, 30), 5, 'Pentacles'),
    ((5, 1), (5, 10), 6, 'Pentacles'),
    ((5, 11), (5, 20), 7, 'Pentacles'),
    ((5, 21), (5, 31), 8, 'Swords'),
    ((6, 1), (6, 10), 9, 'Swords'),
    ((6, 11), (6, 20), 10, 'Swords'),
    ((6, 21), (7, 1), 2, 'Cups'),
    ((7, 2), (7, 11), 3, 'Cups'),
    ((7, 12), (7, 21), 4, 'Cups'),
    ((7, 22), (8, 1), 5, 'Wands'),
    ((8, 2), (8, 11), 6, 'Wands'),
    ((8, 12), (8, 22), 7, 'Wands'),
    ((8, 23), (9, 1), 8, 'Pentacles'),
    ((9, 2), (9, 11), 9, 'Pentacles'),
    ((9, 12), (9, 22), 10, 'Pentacles'),
    ((9, 23), (10, 2), 2, 'Swords'),
    ((10, 3), (10, 12), 3, 'Swords'),
    ((10, 13), (10, 22), 4, 'Swords'),
    ((10, 23), (11, 1), 5, 'Cups'),
    ((11, 2), (11, 12), 6, 'Cups'),
    ((11, 13), (11, 22), 7, 'Cups'),
    ((11, 23), (12, 2), 8, 'Wands'),
    ((12, 3), (12, 12), 9, 'Wands'),
    ((12, 13), (12, 21), 10, 'Wands'),
    ((12, 22), (12, 30), 2, 'Pentacles'),
    ((12, 31), (1, 9), 3, 'Pentacles'),   # wraps the year boundary
    ((1, 10), (1, 19), 4, 'Pentacles'),
    ((1, 20), (1, 29), 5, 'Swords'),
    ((1, 30), (2, 8), 6, 'Swords'),
    ((2, 9), (2, 18), 7, 'Swords'),
    ((2, 19), (2, 29), 8, 'Cups'),        # Feb 29 included in leap years
    ((3, 1), (3, 10), 9, 'Cups'),
    ((3, 11), (3, 20), 10, 'Cups'),
]


# === Numeric primitives ===

def digit_sum(n: int) -> int:
    return sum(int(d) for d in str(abs(n)))


def reduce_to_22(n: int) -> int:
    """Repeated digit sum, stopping at the first value <= 22.
    Never reduces past 22 — Year Cards can be any of the 22 Majors."""
    while n > 22:
        n = digit_sum(n)
    return n


def method_base(birth: date, method: str = GREER) -> int:
    """The unreduced addition total under the chosen method."""
    if method == GREER:
        return birth.month + birth.day + birth.year
    if method == AMBERSTONE:
        century, two_digit = divmod(birth.year, 100)
        return birth.month + birth.day + century + two_digit
    raise ValueError(f'Unknown method: {method!r}')


# === Core profile ===

def calculate(birth: date, method: str = GREER,
              reference_year: int | None = None,
              reference_month: int | None = None) -> dict:
    """Full BirthCardProfile for a birth date. All Majors as ints 1-22."""
    base = method_base(birth, method)
    sum1 = reduce_to_22(base)

    teacher = None
    if 1 <= sum1 <= 9:
        personality, soul = sum1, sum1
        pattern = f'{sum1}-{sum1}'
    elif sum1 == 19:
        personality, soul, teacher = 19, 1, 10
        pattern = '19-10-1'
    else:  # 10..22, not 19
        personality, soul = sum1, digit_sum(sum1)
        pattern = f'{personality}-{soul}'

    consumed = {personality, soul} | ({teacher} if teacher else set())
    hidden_factor = sorted(set(CONSTELLATIONS[soul]) - consumed)

    profile = {
        'method': method,
        'base_number': base,
        'personality': personality,
        'soul': soul,
        'teacher': teacher,
        'hidden_factor': hidden_factor,
        'pattern': pattern,
        'nighttime': pattern in NIGHTTIME_PATTERNS,
        'constellation': {
            'root': soul,
            'majors': list(CONSTELLATIONS[soul]),
        },
        'lessons_and_opportunities': lessons_and_opportunities(soul, pattern),
        'zodiacal_card': zodiacal_card(birth),
        'dynamic': dynamic_group(personality),
        'fool_center': personality == 22,
        # The base total read as a calendar year. Defined on the Greer
        # form (month + day + full year) regardless of method — the
        # Amberstone total isn't year-shaped.
        'karmic_year': method_base(birth, GREER),
    }
    if reference_year is not None:
        profile['year_card'] = year_card(birth, reference_year)
        profile['generic_year'] = reduce_to_22(digit_sum(reference_year))
        if reference_month is not None:
            profile['personal_month'] = personal_month(
                birth, reference_year, reference_month)
    return profile


def lessons_and_opportunities(soul: int, pattern: str) -> list[dict]:
    """Minor Arcana matching the Soul number — the 19-10-1 pattern gets
    both Aces and Tens (8 cards); everyone else gets their soul number
    in all four suits (4 cards)."""
    if pattern == '19-10-1':
        ranks = [1, 10]
    else:
        ranks = [soul]
    return [{'rank': r, 'suit': s} for r in ranks for s in SUITS]


def zodiacal_card(birth: date) -> dict:
    """The decan Minor whose fixed calendar range contains the birthday."""
    md = (birth.month, birth.day)
    for start, end, rank, suit in DECANS:
        if start > end:  # the one year-boundary wrap (3 of Pentacles)
            hit = md >= start or md <= end
        else:
            hit = start <= md <= end
        if hit:
            return {'rank': rank, 'suit': suit}
    raise AssertionError(f'decan table gap at {md}')  # tiling test proves unreachable


# === Decan rulers (Golden Dawn Book T) ===

# Sign trumps. Astrological attributions are card identities in the
# Golden Dawn scheme — Leo is always the Strength card and Libra always
# Justice, so the 8/11 numbering toggle deliberately does not apply.
SIGN_MAJORS = {
    'Aries': 4, 'Taurus': 5, 'Gemini': 6, 'Cancer': 7, 'Leo': 8,
    'Virgo': 9, 'Libra': 11, 'Scorpio': 13, 'Sagittarius': 14,
    'Capricorn': 15, 'Aquarius': 17, 'Pisces': 18,
}

PLANET_MAJORS = {
    'Mercury': 1, 'Moon': 2, 'Venus': 3, 'Jupiter': 10,
    'Mars': 16, 'Sun': 19, 'Saturn': 21,
}

# Book T's planetary rulers walk the descending Chaldean order
# (Saturn, Jupiter, Mars, Sun, Venus, Mercury, Moon) starting from
# Mars at Aries I; Mars also closes the year at Pisces III — the
# well-known doubling that bridges the zodiac's seam. DECANS is
# ordered from Aries I, so both signs and planets derive by index.
_CHALDEAN_FROM_MARS = ['Mars', 'Sun', 'Venus', 'Mercury', 'Moon', 'Saturn', 'Jupiter']
_SIGN_ORDER = ['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo',
               'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces']

DECAN_RULERS = {
    (rank, suit): {
        'sign': _SIGN_ORDER[i // 3],
        'planet': _CHALDEAN_FROM_MARS[i % 7],
    }
    for i, (_, _, rank, suit) in enumerate(DECANS)
}


# === Decan court rulers ===

# Each non-Page court card rules 20° of one sign through 20° of the
# next: the last decan of the earlier sign plus the first two of its
# own. Queens take the cardinal-sign spans in every tradition; the
# other two ranks differ by naming lineage. Waite renamed the Golden
# Dawn's fire courts (Book T "Knights") to Kings, while Case's B.O.T.A.
# kept Knight = fire — so in RWS-named decks the two systems swap
# King and Knight for the same span.
COURT_SYSTEMS = ('golden_dawn', 'bota')

_SUIT_BY_SIGN_INDEX = ['Wands', 'Pentacles', 'Swords', 'Cups']    # fire/earth/air/water
_MODALITY_BY_SIGN_INDEX = ['cardinal', 'fixed', 'mutable']

_DECAN_INDEX = {(rank, suit): i for i, (_, _, rank, suit) in enumerate(DECANS)}


def decan_court(ref: dict, system: str = 'golden_dawn') -> dict:
    """The court card ruling a decan Minor's span, in RWS rank names.

    system='golden_dawn': Waite's rendering of Book T (mutable -> King,
    fixed -> Knight). system='bota': Case's naming (mutable -> Knight,
    fixed -> King). Queens (cardinal) are identical in both.
    """
    if system not in COURT_SYSTEMS:
        raise ValueError(f'Unknown court system: {system!r}')
    i = _DECAN_INDEX[(ref['rank'], ref['suit'])]
    sign_i, decan_in_sign = i // 3, i % 3 + 1
    # Decan III belongs to the NEXT sign's court (its span starts at
    # 20 degrees of this sign).
    court_sign_i = sign_i if decan_in_sign <= 2 else (sign_i + 1) % 12
    court_sign = _SIGN_ORDER[court_sign_i]
    suit = _SUIT_BY_SIGN_INDEX[court_sign_i % 4]
    modality = _MODALITY_BY_SIGN_INDEX[court_sign_i % 3]
    if modality == 'cardinal':
        rank = 'Queen'
    elif modality == 'fixed':
        rank = 'Knight' if system == 'golden_dawn' else 'King'
    else:  # mutable — the fire/"mounted" court of Book T
        rank = 'King' if system == 'golden_dawn' else 'Knight'
    prev_sign = _SIGN_ORDER[(court_sign_i - 1) % 12]
    return {
        'rank': rank,
        'suit': suit,
        'name': f'{rank} of {suit}',
        'court_sign': court_sign,
        'span': f'20° {prev_sign} – 20° {court_sign}',
    }


def zodiacal_rulers(ref: dict) -> dict:
    """Sign and planetary rulers of a decan Minor, with each ruler's
    Major Arcana trump (Golden Dawn attributions)."""
    rulers = DECAN_RULERS[(ref['rank'], ref['suit'])]
    return {
        'sign': rulers['sign'],
        'planet': rulers['planet'],
        'sign_major': SIGN_MAJORS[rulers['sign']],
        'planet_major': PLANET_MAJORS[rulers['planet']],
    }


def dynamic_group(personality: int) -> int | None:
    """Soul-group hexagram (1/2/3) from the Personality Card. The Fool
    (22) sits at the center of all three — None, with fool_center set."""
    if personality == 22:
        return None
    return ((personality - 1) % 3) + 1


# === Year and periodic cards ===

def year_card(birth: date, reference_year: int) -> int:
    return reduce_to_22(digit_sum(birth.month + birth.day + reference_year))


def personal_month(birth: date, reference_year: int, reference_month: int) -> int:
    return reduce_to_22(digit_sum(
        birth.month + birth.day + reference_year + reference_month))


def year_card_series(birth: date, year_from: int, year_to: int) -> list[dict]:
    """Year Cards over a span (inclusive) — callers detect the ~10-year
    runs ("cycle themes") from the sequence."""
    return [{'year': y, 'card': year_card(birth, y)}
            for y in range(year_from, year_to + 1)]


# === Render-boundary name resolution ===

# Golden Dawn ordering (8 Strength / 11 Justice) is the default; the
# Marseille toggle swaps those two labels. Display only — never math.
MAJOR_NAMES = {
    1: 'The Magician', 2: 'The High Priestess', 3: 'The Empress',
    4: 'The Emperor', 5: 'The Hierophant', 6: 'The Lovers',
    7: 'The Chariot', 8: 'Strength', 9: 'The Hermit',
    10: 'Wheel of Fortune', 11: 'Justice', 12: 'The Hanged Man',
    13: 'Death', 14: 'Temperance', 15: 'The Devil', 16: 'The Tower',
    17: 'The Star', 18: 'The Moon', 19: 'The Sun', 20: 'Judgement',
    21: 'The World', 22: 'The Fool',
}

# Thoth-lineage aliases, for recognizing decks that use them.
MAJOR_ALIASES = {
    10: ['Fortune'], 11: ['Adjustment'], 20: ['The Aeon', 'Aeon'],
}

RANK_WORDS = {
    1: 'Ace', 2: 'Two', 3: 'Three', 4: 'Four', 5: 'Five', 6: 'Six',
    7: 'Seven', 8: 'Eight', 9: 'Nine', 10: 'Ten',
}


def major_name(n: int, eight_eleven: str = 'golden_dawn') -> str:
    if eight_eleven == 'marseille':
        if n == 8:
            return 'Justice'
        if n == 11:
            return 'Strength'
    return MAJOR_NAMES[n]


def major_archetype_rank(n: int) -> str:
    """The card_archetypes.rank value for a Major: '0' for The Fool
    (stored internally as 22), else the number as a string."""
    return '0' if n == 22 else str(n)


def card_ref_name(ref: dict) -> str:
    """'Three of Cups'-style name for a Minor CardRef — matches the
    app's Tarot archetype naming."""
    return f"{RANK_WORDS[ref['rank']]} of {ref['suit']}"
