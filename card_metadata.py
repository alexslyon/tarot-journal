"""
Canonical card metadata definitions.

This module is the single source of truth for card names, aliases, suits,
ranks, and sort orders. Used by database.py for parsing card names and
by mixin_library.py for sorting/categorizing cards in the UI.
"""

from typing import Dict, List, Optional, Tuple

# =============================================================================
# TAROT - MAJOR ARCANA
# =============================================================================

# Canonical Major Arcana cards with their number (0-21)
# Format: (canonical_name, number)
MAJOR_ARCANA = [
    ("The Fool", 0),
    ("The Magician", 1),
    ("The High Priestess", 2),
    ("The Empress", 3),
    ("The Emperor", 4),
    ("The Hierophant", 5),
    ("The Lovers", 6),
    ("The Chariot", 7),
    ("Strength", 8),
    ("The Hermit", 9),
    ("Wheel of Fortune", 10),
    ("Justice", 11),
    ("The Hanged Man", 12),
    ("Death", 13),
    ("Temperance", 14),
    ("The Devil", 15),
    ("The Tower", 16),
    ("The Star", 17),
    ("The Moon", 18),
    ("The Sun", 19),
    ("Judgement", 20),
    ("The World", 21),
]

# Aliases that map to canonical Major Arcana names
# Each alias maps to (canonical_name, number_string, "Major Arcana")
MAJOR_ARCANA_ALIASES: Dict[str, Tuple[str, str, str]] = {
    # The Fool (0)
    'fool': ('The Fool', '0', 'Major Arcana'),
    'the fool': ('The Fool', '0', 'Major Arcana'),
    # The Magician (1)
    'magician': ('The Magician', '1', 'Major Arcana'),
    'the magician': ('The Magician', '1', 'Major Arcana'),
    'magus': ('The Magician', '1', 'Major Arcana'),  # Thoth
    'the magus': ('The Magician', '1', 'Major Arcana'),
    # The High Priestess (2)
    'high priestess': ('The High Priestess', '2', 'Major Arcana'),
    'the high priestess': ('The High Priestess', '2', 'Major Arcana'),
    'priestess': ('The High Priestess', '2', 'Major Arcana'),
    'the priestess': ('The High Priestess', '2', 'Major Arcana'),
    # The Empress (3)
    'empress': ('The Empress', '3', 'Major Arcana'),
    'the empress': ('The Empress', '3', 'Major Arcana'),
    # The Emperor (4)
    'emperor': ('The Emperor', '4', 'Major Arcana'),
    'the emperor': ('The Emperor', '4', 'Major Arcana'),
    # The Hierophant (5)
    'hierophant': ('The Hierophant', '5', 'Major Arcana'),
    'the hierophant': ('The Hierophant', '5', 'Major Arcana'),
    'high priest': ('The Hierophant', '5', 'Major Arcana'),
    'the high priest': ('The Hierophant', '5', 'Major Arcana'),
    # The Lovers (6)
    'lovers': ('The Lovers', '6', 'Major Arcana'),
    'the lovers': ('The Lovers', '6', 'Major Arcana'),
    # The Chariot (7)
    'chariot': ('The Chariot', '7', 'Major Arcana'),
    'the chariot': ('The Chariot', '7', 'Major Arcana'),
    # Strength (8)
    'strength': ('Strength', '8', 'Major Arcana'),
    'lust': ('Strength', '8', 'Major Arcana'),  # Thoth
    # The Hermit (9)
    'hermit': ('The Hermit', '9', 'Major Arcana'),
    'the hermit': ('The Hermit', '9', 'Major Arcana'),
    # Wheel of Fortune (10)
    'wheel of fortune': ('Wheel of Fortune', '10', 'Major Arcana'),
    'the wheel of fortune': ('Wheel of Fortune', '10', 'Major Arcana'),
    'wheel': ('Wheel of Fortune', '10', 'Major Arcana'),
    'fortune': ('Wheel of Fortune', '10', 'Major Arcana'),
    # Justice (11)
    'justice': ('Justice', '11', 'Major Arcana'),
    'adjustment': ('Justice', '11', 'Major Arcana'),  # Thoth
    # The Hanged Man (12)
    'hanged man': ('The Hanged Man', '12', 'Major Arcana'),
    'the hanged man': ('The Hanged Man', '12', 'Major Arcana'),
    # Death (13)
    'death': ('Death', '13', 'Major Arcana'),
    # Temperance (14)
    'temperance': ('Temperance', '14', 'Major Arcana'),
    'art': ('Temperance', '14', 'Major Arcana'),  # Thoth
    # The Devil (15)
    'devil': ('The Devil', '15', 'Major Arcana'),
    'the devil': ('The Devil', '15', 'Major Arcana'),
    # The Tower (16)
    'tower': ('The Tower', '16', 'Major Arcana'),
    'the tower': ('The Tower', '16', 'Major Arcana'),
    # The Star (17)
    'star': ('The Star', '17', 'Major Arcana'),
    'the star': ('The Star', '17', 'Major Arcana'),
    # The Moon (18)
    'moon': ('The Moon', '18', 'Major Arcana'),
    'the moon': ('The Moon', '18', 'Major Arcana'),
    # The Sun (19)
    'sun': ('The Sun', '19', 'Major Arcana'),
    'the sun': ('The Sun', '19', 'Major Arcana'),
    # Judgement (20)
    'judgement': ('Judgement', '20', 'Major Arcana'),
    'judgment': ('Judgement', '20', 'Major Arcana'),  # US spelling
    'the aeon': ('Judgement', '20', 'Major Arcana'),  # Thoth
    'aeon': ('Judgement', '20', 'Major Arcana'),
    # The World (21)
    'world': ('The World', '21', 'Major Arcana'),
    'the world': ('The World', '21', 'Major Arcana'),
    'universe': ('The World', '21', 'Major Arcana'),  # Thoth
    'the universe': ('The World', '21', 'Major Arcana'),
}

# Quick lookup: alias -> sort order (0-21)
MAJOR_ARCANA_ORDER: Dict[str, int] = {
    alias: int(info[1]) for alias, info in MAJOR_ARCANA_ALIASES.items()
}

# =============================================================================
# TAROT - SUITS
# =============================================================================

# Canonical suit names
TAROT_SUITS = ['Wands', 'Cups', 'Swords', 'Pentacles']

# Maps alias names to canonical suit names
TAROT_SUIT_ALIASES: Dict[str, str] = {
    # Wands
    'wands': 'Wands', 'wand': 'Wands',
    'rods': 'Wands', 'staves': 'Wands', 'batons': 'Wands',
    # Cups
    'cups': 'Cups', 'cup': 'Cups',
    'chalices': 'Cups', 'chalice': 'Cups',
    # Swords
    'swords': 'Swords', 'sword': 'Swords',
    # Pentacles
    'pentacles': 'Pentacles', 'pentacle': 'Pentacles',
    'coins': 'Pentacles', 'coin': 'Pentacles',
    'disks': 'Pentacles', 'discs': 'Pentacles',
    'disk': 'Pentacles', 'disc': 'Pentacles',
}

# Sort order base values (suit starts at this number, ranks add to it)
TAROT_SUIT_BASES: Dict[str, int] = {
    'Wands': 100,
    'Cups': 200,
    'Swords': 300,
    'Pentacles': 400,
}

# =============================================================================
# TAROT - RANKS
# =============================================================================

# Canonical rank names in order
TAROT_RANKS = [
    'Ace', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven',
    'Eight', 'Nine', 'Ten', 'Page', 'Knight', 'Queen', 'King'
]

# Maps alias names to (canonical_rank, sort_order)
TAROT_RANK_ALIASES: Dict[str, Tuple[str, int]] = {
    # Ace (1)
    'ace': ('Ace', 1), 'one': ('Ace', 1), '1': ('Ace', 1), 'i': ('Ace', 1),
    # Two (2)
    'two': ('Two', 2), '2': ('Two', 2), 'ii': ('Two', 2),
    # Three (3)
    'three': ('Three', 3), '3': ('Three', 3), 'iii': ('Three', 3),
    # Four (4)
    'four': ('Four', 4), '4': ('Four', 4), 'iv': ('Four', 4),
    # Five (5)
    'five': ('Five', 5), '5': ('Five', 5), 'v': ('Five', 5),
    # Six (6)
    'six': ('Six', 6), '6': ('Six', 6), 'vi': ('Six', 6),
    # Seven (7)
    'seven': ('Seven', 7), '7': ('Seven', 7), 'vii': ('Seven', 7),
    # Eight (8)
    'eight': ('Eight', 8), '8': ('Eight', 8), 'viii': ('Eight', 8),
    # Nine (9)
    'nine': ('Nine', 9), '9': ('Nine', 9), 'ix': ('Nine', 9),
    # Ten (10)
    'ten': ('Ten', 10), '10': ('Ten', 10), 'x': ('Ten', 10),
    # Page/Princess (11)
    'page': ('Page', 11), 'princess': ('Page', 11),
    # Knight/Prince (12)
    'knight': ('Knight', 12), 'prince': ('Knight', 12),
    # Queen (13)
    'queen': ('Queen', 13),
    # King (14)
    'king': ('King', 14),
}

# Quick lookup for sorting: rank_alias -> sort_order (1-14)
TAROT_RANK_ORDER: Dict[str, int] = {
    alias: info[1] for alias, info in TAROT_RANK_ALIASES.items()
}

# =============================================================================
# LENORMAND
# =============================================================================

# Canonical Lenormand cards with their number and playing card suit association
# Format: (canonical_name, number, playing_card_suit)
LENORMAND_CARDS = [
    ("Rider", 1, "Hearts"),
    ("Clover", 2, "Diamonds"),
    ("Ship", 3, "Spades"),
    ("House", 4, "Hearts"),
    ("Tree", 5, "Hearts"),
    ("Clouds", 6, "Clubs"),
    ("Snake", 7, "Clubs"),
    ("Coffin", 8, "Diamonds"),
    ("Bouquet", 9, "Spades"),
    ("Scythe", 10, "Diamonds"),
    ("Whip", 11, "Clubs"),
    ("Birds", 12, "Diamonds"),
    ("Child", 13, "Spades"),
    ("Fox", 14, "Clubs"),
    ("Bear", 15, "Clubs"),
    ("Stars", 16, "Hearts"),
    ("Stork", 17, "Hearts"),
    ("Dog", 18, "Hearts"),
    ("Tower", 19, "Spades"),
    ("Garden", 20, "Spades"),
    ("Mountain", 21, "Clubs"),
    ("Crossroads", 22, "Diamonds"),
    ("Mice", 23, "Clubs"),
    ("Heart", 24, "Hearts"),
    ("Ring", 25, "Clubs"),
    ("Book", 26, "Diamonds"),
    ("Letter", 27, "Spades"),
    ("Man", 28, "Hearts"),
    ("Woman", 29, "Spades"),
    ("Lily", 30, "Spades"),
    ("Sun", 31, "Diamonds"),
    ("Moon", 32, "Hearts"),
    ("Key", 33, "Diamonds"),
    ("Fish", 34, "Diamonds"),
    ("Anchor", 35, "Spades"),
    ("Cross", 36, "Clubs"),
]

# Aliases for Lenormand card names -> (canonical_name, number_string)
LENORMAND_ALIASES: Dict[str, Tuple[str, str]] = {
    # Rider (1)
    'rider': ('Rider', '1'), 'cavalier': ('Rider', '1'),
    # Clover (2)
    'clover': ('Clover', '2'),
    # Ship (3)
    'ship': ('Ship', '3'),
    # House (4)
    'house': ('House', '4'),
    # Tree (5)
    'tree': ('Tree', '5'),
    # Clouds (6)
    'clouds': ('Clouds', '6'), 'cloud': ('Clouds', '6'),
    # Snake (7)
    'snake': ('Snake', '7'),
    # Coffin (8)
    'coffin': ('Coffin', '8'),
    # Bouquet (9)
    'bouquet': ('Bouquet', '9'), 'flowers': ('Bouquet', '9'),
    # Scythe (10)
    'scythe': ('Scythe', '10'),
    # Whip (11)
    'whip': ('Whip', '11'), 'broom': ('Whip', '11'), 'birch': ('Whip', '11'),
    # Birds (12)
    'birds': ('Birds', '12'), 'owls': ('Birds', '12'),
    # Child (13)
    'child': ('Child', '13'),
    # Fox (14)
    'fox': ('Fox', '14'),
    # Bear (15)
    'bear': ('Bear', '15'),
    # Stars (16)
    'stars': ('Stars', '16'), 'star': ('Stars', '16'),
    # Stork (17)
    'stork': ('Stork', '17'),
    # Dog (18)
    'dog': ('Dog', '18'),
    # Tower (19)
    'tower': ('Tower', '19'),
    # Garden (20)
    'garden': ('Garden', '20'),
    # Mountain (21)
    'mountain': ('Mountain', '21'),
    # Crossroads (22)
    'crossroads': ('Crossroads', '22'), 'crossroad': ('Crossroads', '22'),
    'paths': ('Crossroads', '22'), 'path': ('Crossroads', '22'),
    # Mice (23)
    'mice': ('Mice', '23'), 'mouse': ('Mice', '23'),
    # Heart (24)
    'heart': ('Heart', '24'),
    # Ring (25)
    'ring': ('Ring', '25'),
    # Book (26)
    'book': ('Book', '26'),
    # Letter (27)
    'letter': ('Letter', '27'),
    # Man (28)
    'man': ('Man', '28'), 'gentleman': ('Man', '28'),
    # Woman (29)
    'woman': ('Woman', '29'), 'lady': ('Woman', '29'),
    # Lily (30)
    'lily': ('Lily', '30'), 'lilies': ('Lily', '30'),
    # Sun (31)
    'sun': ('Sun', '31'),
    # Moon (32)
    'moon': ('Moon', '32'),
    # Key (33)
    'key': ('Key', '33'),
    # Fish (34)
    'fish': ('Fish', '34'),
    # Anchor (35)
    'anchor': ('Anchor', '35'),
    # Cross (36)
    'cross': ('Cross', '36'),
}

# Maps Lenormand card name -> playing card suit for categorization
LENORMAND_SUIT_MAP: Dict[str, str] = {
    name.lower(): suit for name, _, suit in LENORMAND_CARDS
}
# Add aliases
LENORMAND_SUIT_MAP.update({
    'cavalier': 'Hearts',
    'flowers': 'Spades',
    'broom': 'Clubs',
    'birch': 'Clubs',
    'owls': 'Diamonds',
    'crossroad': 'Diamonds',
    'paths': 'Diamonds',
    'path': 'Diamonds',
    'mouse': 'Clubs',
    'gentleman': 'Hearts',
    'lady': 'Spades',
    'lilies': 'Spades',
})

# =============================================================================
# PLAYING CARDS
# =============================================================================

PLAYING_CARD_SUITS = ['Hearts', 'Diamonds', 'Clubs', 'Spades']

PLAYING_CARD_SUIT_ALIASES: Dict[str, str] = {
    'hearts': 'Hearts', 'heart': 'Hearts', '\u2665': 'Hearts',
    'diamonds': 'Diamonds', 'diamond': 'Diamonds', '\u2666': 'Diamonds',
    'clubs': 'Clubs', 'club': 'Clubs', '\u2663': 'Clubs',
    'spades': 'Spades', 'spade': 'Spades', '\u2660': 'Spades',
}

PLAYING_CARD_RANKS = [
    'Ace', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven',
    'Eight', 'Nine', 'Ten', 'Jack', 'Queen', 'King'
]

PLAYING_CARD_RANK_ALIASES: Dict[str, Tuple[str, int]] = {
    'ace': ('Ace', 1), 'a': ('Ace', 1), '1': ('Ace', 1),
    'two': ('Two', 2), '2': ('Two', 2),
    'three': ('Three', 3), '3': ('Three', 3),
    'four': ('Four', 4), '4': ('Four', 4),
    'five': ('Five', 5), '5': ('Five', 5),
    'six': ('Six', 6), '6': ('Six', 6),
    'seven': ('Seven', 7), '7': ('Seven', 7),
    'eight': ('Eight', 8), '8': ('Eight', 8),
    'nine': ('Nine', 9), '9': ('Nine', 9),
    'ten': ('Ten', 10), '10': ('Ten', 10),
    'jack': ('Jack', 11), 'j': ('Jack', 11), 'knave': ('Jack', 11),
    'queen': ('Queen', 12), 'q': ('Queen', 12),
    'king': ('King', 13), 'k': ('King', 13),
}

# Sort bases for playing cards: Spades, Hearts, Clubs, Diamonds (bridge order)
PLAYING_CARD_SUIT_BASES: Dict[str, int] = {
    'Spades': 100,
    'Hearts': 200,
    'Clubs': 300,
    'Diamonds': 400,
}

# =============================================================================
# PARSING HELPER FUNCTIONS
# =============================================================================

def parse_tarot_major_arcana(card_name_lower: str) -> Optional[Tuple[str, str, str]]:
    """
    Check if a card name matches a Major Arcana card.

    Args:
        card_name_lower: Lowercase card name

    Returns:
        (archetype, rank, suit) tuple if match, None otherwise
        For Major Arcana: suit is always "Major Arcana", rank is the number (0-21)
    """
    return MAJOR_ARCANA_ALIASES.get(card_name_lower)


def parse_tarot_minor_arcana(card_name_lower: str) -> Optional[Tuple[str, str, str]]:
    """
    Parse a Minor Arcana card name to extract archetype, rank, and suit.

    Args:
        card_name_lower: Lowercase card name

    Returns:
        (archetype, rank, suit) tuple if valid minor arcana, None otherwise
        archetype: e.g. "Five of Wands"
        rank: sort order as string (e.g. "105" for Wands + rank 5)
        suit: canonical suit name (e.g. "Wands")
    """
    found_suit = None
    found_rank = None
    found_rank_num = None

    # Find suit
    for suit_key, suit_name in TAROT_SUIT_ALIASES.items():
        if suit_key in card_name_lower:
            found_suit = suit_name
            break

    # Find rank
    words = card_name_lower.split()
    for rank_key, (rank_name, rank_num) in TAROT_RANK_ALIASES.items():
        if rank_key in words or card_name_lower.startswith(rank_key + ' '):
            found_rank = rank_name
            found_rank_num = rank_num
            break

    if found_suit and found_rank:
        archetype = f"{found_rank} of {found_suit}"
        rank = str(TAROT_SUIT_BASES[found_suit] + found_rank_num)
        return archetype, rank, found_suit

    return None


def parse_lenormand_card(card_name: str, card_name_lower: str) -> Optional[Tuple[str, str, None]]:
    """
    Parse a Lenormand card name.

    Args:
        card_name: Original card name (for number extraction)
        card_name_lower: Lowercase card name

    Returns:
        (archetype, rank, None) tuple if match, None otherwise
        archetype: canonical card name (e.g. "Rider")
        rank: card number as string (e.g. "1")
        suit: always None for Lenormand
    """
    import re

    # Try alias match first
    for key, (name, rank) in LENORMAND_ALIASES.items():
        if key in card_name_lower:
            return name, rank, None

    # Try matching by number prefix (e.g., "01 Rider", "1. Rider")
    num_match = re.match(r'^(\d+)\D', card_name)
    if num_match:
        num = int(num_match.group(1))
        if 1 <= num <= 36:
            # Find the card with this number
            for key, (name, rank) in LENORMAND_ALIASES.items():
                if rank == str(num):
                    return name, rank, None

    return None


def parse_playing_card(card_name_lower: str) -> Optional[Tuple[str, str, str]]:
    """
    Parse a playing card name.

    Args:
        card_name_lower: Lowercase card name

    Returns:
        (archetype, rank, suit) tuple if match, None otherwise
    """
    # Check for joker
    if 'joker' in card_name_lower:
        if 'red' in card_name_lower:
            return 'Red Joker', 'Joker', None
        elif 'black' in card_name_lower:
            return 'Black Joker', 'Joker', None
        else:
            return 'Red Joker', 'Joker', None  # Default to red

    found_suit = None
    found_rank = None

    for suit_key, suit_name in PLAYING_CARD_SUIT_ALIASES.items():
        if suit_key in card_name_lower:
            found_suit = suit_name
            break

    words = card_name_lower.split()
    for rank_key, (rank_name, _) in PLAYING_CARD_RANK_ALIASES.items():
        if rank_key in words or card_name_lower.startswith(rank_key + ' '):
            found_rank = rank_name
            break

    if found_suit and found_rank:
        archetype = f"{found_rank} of {found_suit}"
        return archetype, found_rank, found_suit

    return None


def get_lenormand_suit(card_name_lower: str) -> Optional[str]:
    """
    Get the playing card suit association for a Lenormand card.

    Args:
        card_name_lower: Lowercase card name

    Returns:
        Suit name (Hearts, Diamonds, Clubs, Spades) or None
    """
    return LENORMAND_SUIT_MAP.get(card_name_lower.strip())


def get_tarot_sort_key(card_name_lower: str, custom_suit_names: Optional[Dict] = None):
    """
    Get a sort key for a tarot card name.

    Returns a tuple (group, sort_value, subsort) for sorting:
    - Major Arcana: (0, 0-21, 0)
    - Minor Arcana: (1, suit_base + rank, 0)
    - Unknown: (2, 999, 0)

    Args:
        card_name_lower: Lowercase card name
        custom_suit_names: Optional dict mapping 'wands'/'cups'/'swords'/'pentacles' to custom names
    """
    # Check Major Arcana
    if card_name_lower in MAJOR_ARCANA_ORDER:
        return (0, MAJOR_ARCANA_ORDER[card_name_lower], 0)

    # Check Minor Arcana
    # Build suit order including custom names
    suit_order = dict(TAROT_SUIT_BASES)
    if custom_suit_names:
        for key, base in [('wands', 100), ('cups', 200), ('swords', 300), ('pentacles', 400)]:
            custom = custom_suit_names.get(key, '').lower()
            if custom:
                suit_order[custom] = base

    # Also add lowercase canonical names
    for suit, base in TAROT_SUIT_BASES.items():
        suit_order[suit.lower()] = base

    # Add common aliases
    for alias, canonical in TAROT_SUIT_ALIASES.items():
        suit_order[alias] = TAROT_SUIT_BASES[canonical]

    # Find suit in card name
    for suit_name, suit_val in suit_order.items():
        if f'of {suit_name}' in card_name_lower:
            # Find rank
            for rank, rank_val in TAROT_RANK_ORDER.items():
                if card_name_lower.startswith(rank):
                    return (1, suit_val, rank_val)
            return (1, suit_val, 50)  # Unknown rank

    return (2, 999, 0)


def get_playing_card_sort_key(card_name_lower: str):
    """
    Get a sort key for a playing card name.

    Order: Jokers first, then Spades, Hearts, Clubs, Diamonds (2-A within each suit)

    Returns an integer sort value.
    """
    # Jokers come first
    if 'joker' in card_name_lower:
        if 'red' in card_name_lower:
            return 1
        elif 'black' in card_name_lower:
            return 2
        return 1

    # Find suit and rank
    for suit_name, suit_base in [('spades', 100), ('spade', 100),
                                  ('hearts', 200), ('heart', 200),
                                  ('clubs', 300), ('club', 300),
                                  ('diamonds', 400), ('diamond', 400)]:
        if suit_name in card_name_lower:
            # Ranks: 2-10, J, Q, K, A (2=1, ..., K=12, A=13)
            rank_values = {
                'two': 1, '2': 1,
                'three': 2, '3': 2,
                'four': 3, '4': 3,
                'five': 4, '5': 4,
                'six': 5, '6': 5,
                'seven': 6, '7': 6,
                'eight': 7, '8': 7,
                'nine': 8, '9': 8,
                'ten': 9, '10': 9,
                'jack': 10, 'j': 10,
                'queen': 11, 'q': 11,
                'king': 12, 'k': 12,
                'ace': 13, 'a': 13,
            }
            for rank_name, rank_val in rank_values.items():
                if f'{rank_name} of' in card_name_lower or card_name_lower.startswith(rank_name + ' '):
                    return suit_base + rank_val
            return suit_base + 50  # Unknown rank

    return 999  # Unknown card
