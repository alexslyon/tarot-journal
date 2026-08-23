"""Tests for the Greer birth-card calculator (birth_cards.py).

Vectors come from the worked examples in the spec (§9), the decan
tiling requirement (§5), and the generational guardrails (§10) — the
latter are structural facts about the number system, so a failure
means the arithmetic is wrong, not the fixture.
"""

from datetime import date, timedelta

import pytest

import birth_cards as bc


# === §9 worked-example vectors ===

VECTORS = [
    # (birth, base, pattern, personality, soul, teacher, hidden, l&o ranks, zodiacal, dynamic)
    (date(1907, 7, 6), 1920, '12-3', 12, 3, None, [21], [3], (3, 'Cups'), 3),
    (date(1943, 7, 26), 1976, '5-5', 5, 5, None, [14], [5], (5, 'Wands'), 2),
    (date(1929, 1, 15), 1945, '19-10-1', 19, 1, 10, [], [1, 10], (4, 'Pentacles'), 1),
    (date(1935, 12, 1), 1948, '22-4', 22, 4, None, [13], [4], (8, 'Wands'), None),
    (date(1961, 8, 4), 1973, '20-2', 20, 2, None, [11], [2], (6, 'Wands'), 2),
    (date(1926, 6, 1), 1933, '16-7', 16, 7, None, [], [7], (9, 'Swords'), 1),
]


@pytest.mark.parametrize(
    'birth,base,pattern,personality,soul,teacher,hidden,lo_ranks,zodiacal,dynamic',
    VECTORS)
def test_spec_vectors(birth, base, pattern, personality, soul, teacher,
                      hidden, lo_ranks, zodiacal, dynamic):
    p = bc.calculate(birth)
    assert p['base_number'] == base
    assert p['pattern'] == pattern
    assert p['personality'] == personality
    assert p['soul'] == soul
    assert p['teacher'] == teacher
    assert p['hidden_factor'] == hidden
    assert sorted({c['rank'] for c in p['lessons_and_opportunities']}) == lo_ranks
    # Each rank appears once per suit
    assert len(p['lessons_and_opportunities']) == len(lo_ranks) * 4
    assert (p['zodiacal_card']['rank'], p['zodiacal_card']['suit']) == zodiacal
    assert p['dynamic'] == dynamic
    assert p['karmic_year'] == base


def test_fool_center_flag():
    p = bc.calculate(date(1935, 12, 1))  # 22-4
    assert p['fool_center'] is True
    assert p['dynamic'] is None
    p2 = bc.calculate(date(1907, 7, 6))
    assert p2['fool_center'] is False


def test_nighttime_flag():
    assert bc.calculate(date(1926, 6, 1))['nighttime'] is True   # 16-7
    assert bc.calculate(date(1907, 7, 6))['nighttime'] is False  # 12-3


# === Method divergence (§0) ===

def test_greer_vs_amberstone_divergence():
    birth = date(1945, 12, 12)
    greer = bc.calculate(birth, method=bc.GREER)
    amber = bc.calculate(birth, method=bc.AMBERSTONE)
    assert greer['base_number'] == 1969
    assert greer['pattern'] == '7-7'
    assert amber['base_number'] == 88
    assert amber['pattern'] == '16-7'
    assert greer['soul'] == amber['soul'] == 7


def test_soul_invariant_across_methods():
    # Deterministic scatter of dates across 1900-2100
    d = date(1900, 1, 1)
    personality_diverged = False
    while d < date(2100, 1, 1):
        greer = bc.calculate(d, method=bc.GREER)
        amber = bc.calculate(d, method=bc.AMBERSTONE)
        assert greer['soul'] == amber['soul'], d
        if greer['personality'] != amber['personality']:
            personality_diverged = True
        d += timedelta(days=137)
    assert personality_diverged  # Personality is NOT method-invariant


def test_unknown_method_rejected():
    with pytest.raises(ValueError):
        bc.calculate(date(2000, 1, 1), method='thoth')


# === Pattern closed set + hidden-factor structure ===

ALL_PATTERNS = (
    {f'{n}-{n}' for n in range(1, 10)}
    | {f'{n}-{bc.digit_sum(n)}' for n in range(10, 23) if n != 19}
    | {'19-10-1'}
)


def test_pattern_closed_set_1900_2100():
    seen = set()
    d = date(1900, 1, 1)
    while d < date(2100, 1, 1):
        p = bc.calculate(d)
        assert p['pattern'] in ALL_PATTERNS, d
        assert 1 <= p['soul'] <= 9
        assert 1 <= p['personality'] <= 22
        seen.add(p['pattern'])
        d += timedelta(days=1)
    assert len(ALL_PATTERNS) == 22


def test_hidden_factor_length_two_only_for_single_digit_1_to_4():
    d = date(1900, 1, 1)
    while d < date(2100, 1, 1):
        p = bc.calculate(d)
        if len(p['hidden_factor']) == 2:
            assert p['pattern'] in {'1-1', '2-2', '3-3', '4-4'}, d
        d += timedelta(days=1)


# === Decan tiling (§5) ===

def test_decan_tiling_covers_every_date_exactly_once():
    """All 366 calendar dates map to exactly one decan card, and all
    36 cards are hit. Uses a leap year so Feb 29 is included."""
    hit_cards = set()
    d = date(2000, 1, 1)
    while d.year == 2000:
        md = (d.month, d.day)
        matches = []
        for start, end, rank, suit in bc.DECANS:
            if start > end:
                hit = md >= start or md <= end
            else:
                hit = start <= md <= end
            if hit:
                matches.append((rank, suit))
        assert len(matches) == 1, f'{md} matched {matches}'
        hit_cards.add(matches[0])
        d += timedelta(days=1)
    assert len(hit_cards) == 36


def test_decan_edge_cases():
    assert bc.zodiacal_card(date(2000, 2, 29)) == {'rank': 8, 'suit': 'Cups'}
    assert bc.zodiacal_card(date(1999, 12, 31)) == {'rank': 3, 'suit': 'Pentacles'}
    assert bc.zodiacal_card(date(2000, 1, 5)) == {'rank': 3, 'suit': 'Pentacles'}
    assert bc.zodiacal_card(date(2000, 7, 1)) == {'rank': 2, 'suit': 'Cups'}   # corrected typo
    assert bc.zodiacal_card(date(2000, 10, 2)) == {'rank': 2, 'suit': 'Swords'}  # corrected typo


# === Generational guardrails (§10) ===

def test_19_10_1_gap_after_1988():
    """The spec (quoting the book) says 19-10-1 resumes 'after 2069',
    but that misses the December tail: 2046-12-31 gives base 2089,
    digit sum 19. The arithmetically true gap is Jan 2 1988 through
    Dec 30 2046 — encode that, since a base with digit sum 19 in the
    reachable range simply doesn't exist in between (1990 and 2089 are
    the only such totals)."""
    d = date(1988, 1, 2)
    while d < date(2046, 12, 31):
        assert bc.calculate(d)['pattern'] != '19-10-1', d
        d += timedelta(days=1)
    assert bc.calculate(date(1988, 1, 1))['pattern'] == '19-10-1'
    assert bc.calculate(date(2046, 12, 31))['pattern'] == '19-10-1'


def test_no_2_2_3_3_4_4_before_1957():
    d = date(1900, 1, 1)
    while d < date(1957, 1, 1):
        assert bc.calculate(d)['pattern'] not in {'2-2', '3-3', '4-4'}, d
        d += timedelta(days=1)


def test_base_2000_gives_high_priestess():
    p = bc.calculate(date(1957, 12, 31))  # 12 + 31 + 1957 = 2000
    assert p['base_number'] == 2000
    assert p['personality'] == 2
    assert p['pattern'] == '2-2'


# === Year and periodic cards (§8) ===

def test_year_card_not_reduced_past_22():
    # 12 + 12 + 1969 = 1993 -> digit sum 22: must stay 22, not become 4
    assert bc.year_card(date(1900, 12, 12), 1969) == 22


def test_year_card_series_and_reference_opts():
    birth = date(1907, 7, 6)
    series = bc.year_card_series(birth, 2020, 2029)
    assert len(series) == 10
    assert all(1 <= s['card'] <= 22 for s in series)
    p = bc.calculate(birth, reference_year=2026, reference_month=8)
    assert p['year_card'] == bc.year_card(birth, 2026)
    assert p['generic_year'] == bc.reduce_to_22(bc.digit_sum(2026))
    assert p['personal_month'] == bc.personal_month(birth, 2026, 8)


# === Name resolution (§7) ===

def test_major_names_and_eight_eleven_swap():
    assert bc.major_name(8) == 'Strength'
    assert bc.major_name(11) == 'Justice'
    assert bc.major_name(8, 'marseille') == 'Justice'
    assert bc.major_name(11, 'marseille') == 'Strength'
    assert bc.major_name(22) == 'The Fool'
    # Swap never touches other cards
    assert bc.major_name(12, 'marseille') == 'The Hanged Man'


def test_archetype_keys_match_app_conventions():
    assert bc.major_archetype_rank(22) == '0'   # The Fool stores rank "0"
    assert bc.major_archetype_rank(7) == '7'
    assert bc.card_ref_name({'rank': 3, 'suit': 'Cups'}) == 'Three of Cups'
    assert bc.card_ref_name({'rank': 1, 'suit': 'Wands'}) == 'Ace of Wands'


# === API endpoints ===

def test_api_adhoc_birth_cards(client):
    res = client.get('/api/birth-cards?date=1907-07-06&year=2026&month=8')
    assert res.status_code == 200
    data = res.get_json()
    assert data['pattern'] == '12-3'
    assert data['cards']['personality']['name'] == 'The Hanged Man'
    assert data['cards']['soul']['name'] == 'The Empress'
    assert data['cards']['hidden_factor'][0]['name'] == 'The World'
    assert data['cards']['zodiacal']['name'] == 'Three of Cups'
    assert len(data['cards']['lessons_and_opportunities']) == 4
    assert data['cards']['year_card']['number'] == 14  # 7+6+2026=2039 -> 14 (Temperance)
    assert data['reference_year'] == 2026


def test_api_adhoc_rejects_bad_date(client):
    assert client.get('/api/birth-cards?date=zebra').status_code == 400
    assert client.get('/api/birth-cards').status_code == 400


def test_api_profile_birth_cards(client, db):
    pid = db.add_profile('Greer Test', birth_date='1929-01-15')
    res = client.get(f'/api/profiles/{pid}/birth-cards')
    assert res.status_code == 200
    data = res.get_json()
    assert data['pattern'] == '19-10-1'
    assert data['cards']['teacher']['name'] == 'Wheel of Fortune'
    assert data['cards']['hidden_factor'] == []
    assert len(data['cards']['lessons_and_opportunities']) == 8
    assert data['age'] >= 97


def test_api_profile_without_birth_date(client, db):
    pid = db.add_profile('No Birthday')
    res = client.get(f'/api/profiles/{pid}/birth-cards')
    assert res.status_code == 400
    assert client.get('/api/profiles/99999/birth-cards').status_code == 404


def test_api_prefs_roundtrip_and_method_override(client):
    res = client.get('/api/birth-cards/prefs')
    assert res.get_json() == {'method': 'greer', 'eight_eleven': 'golden_dawn',
                              'court_system': 'golden_dawn'}
    res = client.put('/api/birth-cards/prefs',
                     json={'method': 'amberstone', 'eight_eleven': 'marseille'})
    assert res.get_json() == {'method': 'amberstone', 'eight_eleven': 'marseille',
                              'court_system': 'golden_dawn'}
    # Saved prefs now apply by default
    res = client.get('/api/birth-cards?date=1945-12-12')
    assert res.get_json()['pattern'] == '16-7'
    # Query-param override wins without changing the saved pref
    res = client.get('/api/birth-cards?date=1945-12-12&method=greer')
    assert res.get_json()['pattern'] == '7-7'
    assert client.get('/api/birth-cards/prefs').get_json()['method'] == 'amberstone'
    assert client.put('/api/birth-cards/prefs', json={'method': 'bogus'}).status_code == 400


def test_api_eight_eleven_naming(client):
    # 1961-08-04 -> hidden factor 11 (Justice under Golden Dawn)
    res = client.get('/api/birth-cards?date=1961-08-04')
    assert res.get_json()['cards']['hidden_factor'][0]['name'] == 'Justice'
    res = client.get('/api/birth-cards?date=1961-08-04&eight_eleven=marseille')
    assert res.get_json()['cards']['hidden_factor'][0]['name'] == 'Strength'


# === Decan rulers (Golden Dawn Book T) ===

def test_zodiacal_rulers_known_decans():
    # 3 of Cups = Cancer II, ruled by Mercury -> Chariot + Magician
    r = bc.zodiacal_rulers({'rank': 3, 'suit': 'Cups'})
    assert r == {'sign': 'Cancer', 'planet': 'Mercury',
                 'sign_major': 7, 'planet_major': 1}
    # 5 of Wands = Leo I, ruled by Saturn -> Strength + The World
    r = bc.zodiacal_rulers({'rank': 5, 'suit': 'Wands'})
    assert r == {'sign': 'Leo', 'planet': 'Saturn',
                 'sign_major': 8, 'planet_major': 21}
    # 8 of Wands = Sagittarius I, ruled by Mercury
    r = bc.zodiacal_rulers({'rank': 8, 'suit': 'Wands'})
    assert r['sign'] == 'Sagittarius' and r['planet'] == 'Mercury'


def test_decan_rulers_structure():
    """Every decan has a valid sign and planet; each sign covers exactly
    three decans; Mars famously rules both Aries I and Pisces III."""
    assert len(bc.DECAN_RULERS) == 36
    sign_counts = {}
    for rulers in bc.DECAN_RULERS.values():
        assert rulers['sign'] in bc.SIGN_MAJORS
        assert rulers['planet'] in bc.PLANET_MAJORS
        sign_counts[rulers['sign']] = sign_counts.get(rulers['sign'], 0) + 1
    assert all(count == 3 for count in sign_counts.values())
    assert bc.DECAN_RULERS[(2, 'Wands')]['planet'] == 'Mars'    # Aries I
    assert bc.DECAN_RULERS[(10, 'Cups')]['planet'] == 'Mars'    # Pisces III


def test_api_zodiacal_rulers(client):
    res = client.get('/api/birth-cards?date=1907-07-06')  # 3 of Cups
    data = res.get_json()
    assert data['zodiacal_rulers']['sign'] == 'Cancer'
    assert data['cards']['zodiacal_sign_ruler']['name'] == 'The Chariot'
    assert data['cards']['zodiacal_planet_ruler']['name'] == 'The Magician'
    # Ruler names ignore the 8/11 relabel: Leo is always the Strength card
    res = client.get('/api/birth-cards?date=1943-07-26&eight_eleven=marseille')
    data = res.get_json()
    assert data['zodiacal_rulers']['sign'] == 'Leo'
    assert data['cards']['zodiacal_sign_ruler']['name'] == 'Strength'


# === Decan court rulers (Golden Dawn vs B.O.T.A.) ===

def test_decan_court_known_cases():
    # Cancer II (3 of Cups): cardinal water -> Queen of Cups, both systems
    for system in bc.COURT_SYSTEMS:
        court = bc.decan_court({'rank': 3, 'suit': 'Cups'}, system)
        assert court['name'] == 'Queen of Cups', system
        assert court['span'] == '20° Gemini – 20° Cancer'
    # Sagittarius I (8 of Wands): mutable fire -> GD King / BOTA Knight
    assert bc.decan_court({'rank': 8, 'suit': 'Wands'})['name'] == 'King of Wands'
    assert bc.decan_court({'rank': 8, 'suit': 'Wands'}, 'bota')['name'] == 'Knight of Wands'
    # Capricorn III (4 of Pentacles): span belongs to the NEXT sign's
    # court — fixed air Aquarius -> GD Knight / BOTA King of Swords
    gd = bc.decan_court({'rank': 4, 'suit': 'Pentacles'})
    assert gd['name'] == 'Knight of Swords'
    assert gd['court_sign'] == 'Aquarius'
    assert gd['span'] == '20° Capricorn – 20° Aquarius'
    assert bc.decan_court({'rank': 4, 'suit': 'Pentacles'}, 'bota')['name'] == 'King of Swords'


def test_decan_court_structure():
    """Across all 36 decans: every span is a real 20-20 court span,
    each of the 12 courts rules exactly three decans, Queens are
    system-invariant, and Kings/Knights swap exactly between systems."""
    gd_counts = {}
    for (rank, suit) in bc._DECAN_INDEX:
        ref = {'rank': rank, 'suit': suit}
        gd = bc.decan_court(ref, 'golden_dawn')
        bota = bc.decan_court(ref, 'bota')
        assert gd['suit'] == bota['suit']
        assert gd['span'] == bota['span']
        if gd['rank'] == 'Queen':
            assert bota['rank'] == 'Queen'
        else:
            assert {gd['rank'], bota['rank']} == {'King', 'Knight'}
        gd_counts[gd['name']] = gd_counts.get(gd['name'], 0) + 1
    assert len(gd_counts) == 12
    assert all(count == 3 for count in gd_counts.values())


def test_decan_court_rejects_unknown_system():
    with pytest.raises(ValueError):
        bc.decan_court({'rank': 3, 'suit': 'Cups'}, 'thoth')


def test_api_decan_court(client):
    # 1929-01-15 -> 4 of Pentacles (Capricorn III)
    res = client.get('/api/birth-cards?date=1929-01-15')
    data = res.get_json()
    assert data['decan_court']['name'] == 'Knight of Swords'
    assert data['cards']['decan_court']['name'] == 'Knight of Swords'
    assert data['court_system'] == 'golden_dawn'
    res = client.get('/api/birth-cards?date=1929-01-15&court_system=bota')
    data = res.get_json()
    assert data['decan_court']['name'] == 'King of Swords'
    # Prefs roundtrip includes the court system
    res = client.put('/api/birth-cards/prefs', json={'court_system': 'bota'})
    assert res.get_json()['court_system'] == 'bota'
    res = client.get('/api/birth-cards?date=1929-01-15')
    assert res.get_json()['decan_court']['name'] == 'King of Swords'
    assert client.put('/api/birth-cards/prefs',
                      json={'court_system': 'thoth'}).status_code == 400
