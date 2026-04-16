"""
One-time migration of custom field data to structured correspondence overrides.

Parses existing Astrology, Element, Numerology, and Sign custom fields
and writes them as card_correspondence_overrides. Non-destructive: old
custom fields are preserved, unparseable values are logged.
"""

import json
import re

from logger_config import get_logger

logger = get_logger('correspondence_migration')

# Unicode astrological symbols → names
PLANET_SYMBOLS = {
    '☉': 'Sun', '☽': 'Moon', '☿': 'Mercury', '♀': 'Venus', '♂': 'Mars',
    '♃': 'Jupiter', '♄': 'Saturn', '♅': 'Uranus', '♆': 'Neptune', '♇': 'Pluto',
}

SIGN_SYMBOLS = {
    '♈': 'Aries', '♉': 'Taurus', '♊': 'Gemini', '♋': 'Cancer',
    '♌': 'Leo', '♍': 'Virgo', '♎': 'Libra', '♏': 'Scorpio',
    '♐': 'Sagittarius', '♑': 'Capricorn', '♒': 'Aquarius', '♓': 'Pisces',
}

ZODIAC_SIGNS = {
    'aries', 'taurus', 'gemini', 'cancer', 'leo', 'virgo',
    'libra', 'scorpio', 'sagittarius', 'capricorn', 'aquarius', 'pisces',
}

PLANETS = {
    'sun', 'moon', 'mercury', 'venus', 'mars',
    'jupiter', 'saturn', 'uranus', 'neptune', 'pluto',
}

ELEMENTS = {'fire', 'water', 'air', 'earth', 'spirit'}

# Common typos / alternate spellings
TYPO_FIXES = {
    'ares': 'Aries',
}


def strip_html(value: str) -> str:
    """Remove HTML tags and decode entities."""
    text = re.sub(r'<[^>]+>', ' ', value)
    text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    return text.strip()


def replace_symbols(value: str) -> str:
    """Replace Unicode astrological symbols with their text names."""
    for symbol, name in PLANET_SYMBOLS.items():
        value = value.replace(symbol, name)
    for symbol, name in SIGN_SYMBOLS.items():
        value = value.replace(symbol, name)
    return value


def clean_value(raw: str) -> str:
    """Strip HTML, replace symbols, normalize whitespace."""
    text = strip_html(raw)
    text = replace_symbols(text)
    text = ' '.join(text.split())  # normalize whitespace
    # Fix common typos
    if text.lower() in TYPO_FIXES:
        text = TYPO_FIXES[text.lower()]
    return text


def parse_astrology_value(raw: str):
    """Parse an Astrology field value into correspondence fields.

    Returns: {
        'fields': {field_name: field_value, ...},
        'unparseable': str or None  (original value if couldn't fully parse)
    }
    """
    cleaned = clean_value(raw)

    # Skip empty / "None" values
    if not cleaned or cleaned.lower() == 'none':
        return {'fields': {}, 'unparseable': None}

    fields = {}
    unparseable = None

    # Check for "Planet in Sign" decan pattern
    decan_match = re.match(r'^(\w+)\s+in\s+(\w+)$', cleaned, re.IGNORECASE)
    if decan_match:
        planet, sign = decan_match.group(1).title(), decan_match.group(2).title()
        if planet.lower() in PLANETS and sign.lower() in ZODIAC_SIGNS:
            fields['decan'] = f"{planet} in {sign}"
            fields['planet'] = planet
            fields['zodiac_sign'] = sign
            return {'fields': fields, 'unparseable': None}

    # Check for "The Sun" / "The Moon" (planet references with article)
    if cleaned.lower().startswith('the '):
        name = cleaned[4:].strip().title()
        if name.lower() in PLANETS:
            fields['planet'] = name
            return {'fields': fields, 'unparseable': None}

    # Check for single zodiac sign
    if cleaned.lower() in ZODIAC_SIGNS:
        fields['zodiac_sign'] = cleaned.title()
        return {'fields': fields, 'unparseable': None}

    # Check for single planet
    if cleaned.lower() in PLANETS:
        fields['planet'] = cleaned.title()
        return {'fields': fields, 'unparseable': None}

    # Check for single element
    if cleaned.lower() in ELEMENTS:
        fields['element'] = cleaned.title()
        return {'fields': fields, 'unparseable': None}

    # Multi-value entries (comma or "and" separated) — flag for review
    # but still try to extract what we can
    if ',' in cleaned or ' and ' in cleaned.lower():
        unparseable = cleaned
        # Try to extract individual values
        parts = re.split(r'[,]|\band\b', cleaned, flags=re.IGNORECASE)
        zodiac_found = []
        for part in parts:
            part = part.strip().title()
            if part.lower() in ZODIAC_SIGNS:
                zodiac_found.append(part)
        # If all parts are zodiac signs, use the first one
        if zodiac_found:
            fields['zodiac_sign'] = zodiac_found[0]
        return {'fields': fields, 'unparseable': unparseable}

    # Anything else: flag as unparseable
    return {'fields': {}, 'unparseable': cleaned}


def parse_element_value(raw: str):
    """Parse an Element field value.

    Returns: {
        'fields': {field_name: field_value, ...},
        'unparseable': str or None
    }
    """
    cleaned = clean_value(raw)

    if not cleaned:
        return {'fields': {}, 'unparseable': None}

    # Simple element match
    if cleaned.lower() in ELEMENTS:
        return {'fields': {'element': cleaned.title()}, 'unparseable': None}

    # Combined elements like "Fire + Water" — flag for review, use first
    if '+' in cleaned or ',' in cleaned:
        parts = re.split(r'[+,]', cleaned)
        first = parts[0].strip().title()
        if first.lower() in ELEMENTS:
            return {'fields': {'element': first}, 'unparseable': cleaned}
        return {'fields': {}, 'unparseable': cleaned}

    # Values with extra context like "Air (Earth, Water...)" — extract primary
    paren_match = re.match(r'^(\w+)\s*[\(<]', cleaned)
    if paren_match:
        primary = paren_match.group(1).title()
        if primary.lower() in ELEMENTS:
            return {'fields': {'element': primary}, 'unparseable': None}

    return {'fields': {}, 'unparseable': cleaned}


def parse_numerology_value(raw: str):
    """Parse a Numerology field value."""
    cleaned = clean_value(raw)
    if not cleaned:
        return {'fields': {}, 'unparseable': None}
    try:
        num = int(cleaned)
        return {'fields': {'numerology': str(num)}, 'unparseable': None}
    except ValueError:
        return {'fields': {}, 'unparseable': cleaned}


def parse_sign_value(raw: str):
    """Parse a Sign field value."""
    cleaned = clean_value(raw)
    if not cleaned:
        return {'fields': {}, 'unparseable': None}
    if cleaned.lower() in ZODIAC_SIGNS:
        return {'fields': {'zodiac_sign': cleaned.title()}, 'unparseable': None}
    return {'fields': {}, 'unparseable': cleaned}


# Map custom field names to their parser functions
FIELD_PARSERS = {
    'astrology': parse_astrology_value,
    'element': parse_element_value,
    'numerology': parse_numerology_value,
    'sign': parse_sign_value,
}


def run_correspondence_migration(db):
    """Migrate custom field data to structured correspondence overrides.

    Guarded by 'correspondence_migration_done' setting — runs only once.
    """
    if db.get_setting('correspondence_migration_done') == 'true':
        return

    logger.info('Starting correspondence field migration...')

    cursor = db.conn.cursor()
    migration_log = []
    migrated_count = 0
    skipped_count = 0

    # Fetch all relevant custom field values
    cursor.execute('''
        SELECT ccf.id, ccf.card_id, ccf.field_name, ccf.field_value,
               c.name AS card_name, c.deck_id, d.name AS deck_name
        FROM card_custom_fields ccf
        JOIN cards c ON c.id = ccf.card_id
        JOIN decks d ON d.id = c.deck_id
        WHERE LOWER(ccf.field_name) IN ('astrology', 'element', 'numerology', 'sign')
          AND ccf.field_value IS NOT NULL
          AND ccf.field_value != ''
        ORDER BY d.name, c.card_order
    ''')
    rows = cursor.fetchall()

    for row in rows:
        field_name_lower = row['field_name'].lower()
        parser = FIELD_PARSERS.get(field_name_lower)
        if not parser:
            continue

        result = parser(row['field_value'])

        # Write parsed fields as card overrides
        for corr_field, corr_value in result['fields'].items():
            cursor.execute('''
                INSERT INTO card_correspondence_overrides
                    (card_id, field_name, field_value)
                VALUES (?, ?, ?)
                ON CONFLICT(card_id, field_name)
                DO UPDATE SET field_value = excluded.field_value
            ''', (row['card_id'], corr_field, corr_value))
            migrated_count += 1

        # Log unparseable values
        if result['unparseable']:
            log_entry = {
                'card_id': row['card_id'],
                'card_name': row['card_name'],
                'deck_id': row['deck_id'],
                'deck_name': row['deck_name'],
                'field_name': row['field_name'],
                'original_value': row['field_value'],
                'cleaned_value': result['unparseable'],
                'partial_fields': result['fields'],
            }
            migration_log.append(log_entry)
            if not result['fields']:
                skipped_count += 1

    db.conn.commit()

    # Store migration log for review
    db.set_setting('correspondence_migration_log', json.dumps(migration_log))
    db.set_setting('correspondence_migration_done', 'true')

    logger.info(
        'Correspondence migration complete: %d fields migrated, %d fully skipped, %d flagged for review',
        migrated_count, skipped_count, len(migration_log)
    )
