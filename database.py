"""
Database module for Tarot Journal App
Handles all data persistence using SQLite
"""

import sqlite3
import json
import zipfile
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional, List
import os


class Database:
    def __init__(self, db_path: str = "tarot_journal.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
    
    def _create_tables(self):
        cursor = self.conn.cursor()
        
        # Cartomancy types (tarot, lenormand, oracle)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cartomancy_types (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
        ''')
        
        # Decks table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS decks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                cartomancy_type_id INTEGER NOT NULL,
                image_folder TEXT,
                suit_names TEXT,
                court_names TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (cartomancy_type_id) REFERENCES cartomancy_types(id)
            )
        ''')

        # Migration: add suit_names and court_names columns if missing
        cursor.execute("PRAGMA table_info(decks)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'suit_names' not in columns:
            cursor.execute('ALTER TABLE decks ADD COLUMN suit_names TEXT')
        if 'court_names' not in columns:
            cursor.execute('ALTER TABLE decks ADD COLUMN court_names TEXT')
        # Migration: add deck metadata columns
        if 'date_published' not in columns:
            cursor.execute('ALTER TABLE decks ADD COLUMN date_published TEXT')
        if 'publisher' not in columns:
            cursor.execute('ALTER TABLE decks ADD COLUMN publisher TEXT')
        if 'credits' not in columns:
            cursor.execute('ALTER TABLE decks ADD COLUMN credits TEXT')
        if 'notes' not in columns:
            cursor.execute('ALTER TABLE decks ADD COLUMN notes TEXT')
        if 'card_back_image' not in columns:
            cursor.execute('ALTER TABLE decks ADD COLUMN card_back_image TEXT')
        if 'booklet_info' not in columns:
            cursor.execute('ALTER TABLE decks ADD COLUMN booklet_info TEXT')

        # Cards table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                deck_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                image_path TEXT,
                card_order INTEGER DEFAULT 0,
                archetype TEXT,
                rank TEXT,
                suit TEXT,
                notes TEXT,
                custom_fields TEXT,
                FOREIGN KEY (deck_id) REFERENCES decks(id) ON DELETE CASCADE
            )
        ''')

        # Migration: add new columns to cards table if missing
        cursor.execute("PRAGMA table_info(cards)")
        card_columns = [col[1] for col in cursor.fetchall()]
        if 'archetype' not in card_columns:
            cursor.execute('ALTER TABLE cards ADD COLUMN archetype TEXT')
        if 'rank' not in card_columns:
            cursor.execute('ALTER TABLE cards ADD COLUMN rank TEXT')
        if 'suit' not in card_columns:
            cursor.execute('ALTER TABLE cards ADD COLUMN suit TEXT')
        if 'notes' not in card_columns:
            cursor.execute('ALTER TABLE cards ADD COLUMN notes TEXT')
        if 'custom_fields' not in card_columns:
            cursor.execute('ALTER TABLE cards ADD COLUMN custom_fields TEXT')
        
        # Spreads table (saved spread layouts)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS spreads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                positions JSON NOT NULL,
                cartomancy_type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Migration: add cartomancy_type column if missing
        cursor.execute("PRAGMA table_info(spreads)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'cartomancy_type' not in columns:
            cursor.execute('ALTER TABLE spreads ADD COLUMN cartomancy_type TEXT')

        # Migration: add allowed_deck_types column for multi-deck-type spreads
        if 'allowed_deck_types' not in columns:
            cursor.execute('ALTER TABLE spreads ADD COLUMN allowed_deck_types TEXT')

        # Migration: add default_deck_id column for spread-specific default deck
        if 'default_deck_id' not in columns:
            cursor.execute('ALTER TABLE spreads ADD COLUMN default_deck_id INTEGER REFERENCES decks(id)')

        # Journal entries table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS journal_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reading_datetime TIMESTAMP,
                location_name TEXT,
                location_lat REAL,
                location_lon REAL
            )
        ''')

        # Migrate journal_entries table if needed
        cursor.execute('PRAGMA table_info(journal_entries)')
        columns = [col[1] for col in cursor.fetchall()]
        if 'reading_datetime' not in columns:
            cursor.execute('ALTER TABLE journal_entries ADD COLUMN reading_datetime TIMESTAMP')
        if 'location_name' not in columns:
            cursor.execute('ALTER TABLE journal_entries ADD COLUMN location_name TEXT')
        if 'location_lat' not in columns:
            cursor.execute('ALTER TABLE journal_entries ADD COLUMN location_lat REAL')
        if 'location_lon' not in columns:
            cursor.execute('ALTER TABLE journal_entries ADD COLUMN location_lon REAL')

        # Entry readings (links entries to spreads and cards used)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS entry_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_id INTEGER NOT NULL,
                spread_id INTEGER,
                spread_name TEXT,
                deck_id INTEGER,
                deck_name TEXT,
                cartomancy_type TEXT,
                cards_used JSON,
                position_order INTEGER DEFAULT 0,
                FOREIGN KEY (entry_id) REFERENCES journal_entries(id) ON DELETE CASCADE,
                FOREIGN KEY (spread_id) REFERENCES spreads(id),
                FOREIGN KEY (deck_id) REFERENCES decks(id)
            )
        ''')
        
        # Tags table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                color TEXT DEFAULT '#6B5B95'
            )
        ''')
        
        # Entry tags junction table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS entry_tags (
                entry_id INTEGER NOT NULL,
                tag_id INTEGER NOT NULL,
                PRIMARY KEY (entry_id, tag_id),
                FOREIGN KEY (entry_id) REFERENCES journal_entries(id) ON DELETE CASCADE,
                FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
            )
        ''')

        # Deck tags table (separate from entry tags)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS deck_tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                color TEXT DEFAULT '#6B5B95'
            )
        ''')

        # Deck tag assignments junction table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS deck_tag_assignments (
                deck_id INTEGER NOT NULL,
                tag_id INTEGER NOT NULL,
                PRIMARY KEY (deck_id, tag_id),
                FOREIGN KEY (deck_id) REFERENCES decks(id) ON DELETE CASCADE,
                FOREIGN KEY (tag_id) REFERENCES deck_tags(id) ON DELETE CASCADE
            )
        ''')

        # Card tags table (separate from deck tags)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS card_tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                color TEXT DEFAULT '#6B5B95'
            )
        ''')

        # Card tag assignments junction table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS card_tag_assignments (
                card_id INTEGER NOT NULL,
                tag_id INTEGER NOT NULL,
                PRIMARY KEY (card_id, tag_id),
                FOREIGN KEY (card_id) REFERENCES cards(id) ON DELETE CASCADE,
                FOREIGN KEY (tag_id) REFERENCES card_tags(id) ON DELETE CASCADE
            )
        ''')

        # Settings table for app preferences
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')

        # Profiles table (for querent and reader information)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                gender TEXT,
                birth_date DATE,
                birth_time TIME,
                birth_place_name TEXT,
                birth_place_lat REAL,
                birth_place_lon REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Migration: add querent_id and reader_id to journal_entries
        cursor.execute('PRAGMA table_info(journal_entries)')
        columns = [col[1] for col in cursor.fetchall()]
        if 'querent_id' not in columns:
            cursor.execute('ALTER TABLE journal_entries ADD COLUMN querent_id INTEGER REFERENCES profiles(id)')
        if 'reader_id' not in columns:
            cursor.execute('ALTER TABLE journal_entries ADD COLUMN reader_id INTEGER REFERENCES profiles(id)')

        # Follow-up notes table (for adding notes to entries after the fact)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS follow_up_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (entry_id) REFERENCES journal_entries(id) ON DELETE CASCADE
            )
        ''')

        # Card archetypes table (predefined standard card archetypes by type)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS card_archetypes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                cartomancy_type TEXT NOT NULL,
                rank TEXT,
                suit TEXT,
                card_type TEXT,
                UNIQUE(name, cartomancy_type)
            )
        ''')

        # Deck custom fields table (define custom fields per deck)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS deck_custom_fields (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                deck_id INTEGER NOT NULL,
                field_name TEXT NOT NULL,
                field_type TEXT NOT NULL,
                field_options TEXT,
                field_order INTEGER DEFAULT 0,
                FOREIGN KEY (deck_id) REFERENCES decks(id) ON DELETE CASCADE
            )
        ''')

        # Card custom fields table (card-specific custom fields)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS card_custom_fields (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                card_id INTEGER NOT NULL,
                field_name TEXT NOT NULL,
                field_type TEXT NOT NULL,
                field_options TEXT,
                field_value TEXT,
                field_order INTEGER DEFAULT 0,
                FOREIGN KEY (card_id) REFERENCES cards(id) ON DELETE CASCADE
            )
        ''')

        # Insert default cartomancy types
        default_types = ['Tarot', 'Lenormand', 'Kipper', 'Playing Cards', 'Oracle', 'I Ching']
        for ct in default_types:
            cursor.execute(
                'INSERT OR IGNORE INTO cartomancy_types (name) VALUES (?)',
                (ct,)
            )

        # Seed card archetypes if table is empty
        cursor.execute('SELECT COUNT(*) FROM card_archetypes')
        if cursor.fetchone()[0] == 0:
            self._seed_card_archetypes(cursor)
        else:
            # Migration: Update Tarot archetypes to new numbering schema
            # Check if migration is needed by looking at Ace of Wands rank
            cursor.execute('''
                SELECT rank FROM card_archetypes
                WHERE name = 'Ace of Wands' AND cartomancy_type = 'Tarot'
            ''')
            row = cursor.fetchone()
            if row and row[0] == 'Ace':  # Old schema used 'Ace', new uses '101'
                self._migrate_tarot_numbering(cursor)

        self.conn.commit()

    def _seed_card_archetypes(self, cursor):
        """Seed the card_archetypes table with standard archetypes for all types.

        Numbering schema for Tarot:
        - Major Arcana: 0-21
        - Wands: 101-114 (Ace=101, Two=102, ... King=114)
        - Cups: 201-214
        - Swords: 301-314
        - Pentacles: 401-414
        """
        archetypes = []

        # Tarot - Major Arcana (22): numbered 0-21
        major_arcana = [
            ('The Fool', '0'), ('The Magician', '1'), ('The High Priestess', '2'),
            ('The Empress', '3'), ('The Emperor', '4'), ('The Hierophant', '5'),
            ('The Lovers', '6'), ('The Chariot', '7'), ('Strength', '8'),
            ('The Hermit', '9'), ('Wheel of Fortune', '10'), ('Justice', '11'),
            ('The Hanged Man', '12'), ('Death', '13'), ('Temperance', '14'),
            ('The Devil', '15'), ('The Tower', '16'), ('The Star', '17'),
            ('The Moon', '18'), ('The Sun', '19'), ('Judgement', '20'),
            ('The World', '21')
        ]
        for name, rank in major_arcana:
            archetypes.append((name, 'Tarot', rank, 'Major Arcana', 'major'))

        # Tarot - Minor Arcana (56)
        # Suit base numbers: Wands=100, Cups=200, Swords=300, Pentacles=400
        tarot_rank_names = ['Ace', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven',
                            'Eight', 'Nine', 'Ten', 'Page', 'Knight', 'Queen', 'King']
        tarot_suits = [('Wands', 100), ('Cups', 200), ('Swords', 300), ('Pentacles', 400)]
        for suit_name, suit_base in tarot_suits:
            for i, rank_name in enumerate(tarot_rank_names):
                name = f"{rank_name} of {suit_name}"
                rank_num = str(suit_base + i + 1)  # 101, 102, ... 114 for Wands
                archetypes.append((name, 'Tarot', rank_num, suit_name, 'minor'))

        # Lenormand (36)
        lenormand_cards = [
            ('Rider', '1'), ('Clover', '2'), ('Ship', '3'), ('House', '4'),
            ('Tree', '5'), ('Clouds', '6'), ('Snake', '7'), ('Coffin', '8'),
            ('Bouquet', '9'), ('Scythe', '10'), ('Whip', '11'), ('Birds', '12'),
            ('Child', '13'), ('Fox', '14'), ('Bear', '15'), ('Stars', '16'),
            ('Stork', '17'), ('Dog', '18'), ('Tower', '19'), ('Garden', '20'),
            ('Mountain', '21'), ('Crossroads', '22'), ('Mice', '23'), ('Heart', '24'),
            ('Ring', '25'), ('Book', '26'), ('Letter', '27'), ('Man', '28'),
            ('Woman', '29'), ('Lily', '30'), ('Sun', '31'), ('Moon', '32'),
            ('Key', '33'), ('Fish', '34'), ('Anchor', '35'), ('Cross', '36')
        ]
        for name, rank in lenormand_cards:
            archetypes.append((name, 'Lenormand', rank, None, 'lenormand'))

        # Playing Cards (54)
        playing_ranks = ['Ace', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven',
                         'Eight', 'Nine', 'Ten', 'Jack', 'Queen', 'King']
        playing_suits = ['Hearts', 'Diamonds', 'Clubs', 'Spades']
        for suit in playing_suits:
            for rank in playing_ranks:
                name = f"{rank} of {suit}"
                archetypes.append((name, 'Playing Cards', rank, suit, 'playing'))

        # Jokers
        archetypes.append(('Red Joker', 'Playing Cards', 'Joker', None, 'playing'))
        archetypes.append(('Black Joker', 'Playing Cards', 'Joker', None, 'playing'))

        # Insert all archetypes
        cursor.executemany('''
            INSERT OR IGNORE INTO card_archetypes (name, cartomancy_type, rank, suit, card_type)
            VALUES (?, ?, ?, ?, ?)
        ''', archetypes)

    def _migrate_tarot_numbering(self, cursor):
        """Migrate Tarot archetypes from old naming schema to new numbering schema.

        Old schema: rank was 'Ace', 'Two', etc. and Roman numerals for Major Arcana
        New schema:
        - Major Arcana: 0-21
        - Wands: 101-114
        - Cups: 201-214
        - Swords: 301-314
        - Pentacles: 401-414
        """
        # Major Arcana: Roman numerals -> Arabic numbers
        major_updates = [
            ('0', 'The Fool'), ('1', 'The Magician'), ('2', 'The High Priestess'),
            ('3', 'The Empress'), ('4', 'The Emperor'), ('5', 'The Hierophant'),
            ('6', 'The Lovers'), ('7', 'The Chariot'), ('8', 'Strength'),
            ('9', 'The Hermit'), ('10', 'Wheel of Fortune'), ('11', 'Justice'),
            ('12', 'The Hanged Man'), ('13', 'Death'), ('14', 'Temperance'),
            ('15', 'The Devil'), ('16', 'The Tower'), ('17', 'The Star'),
            ('18', 'The Moon'), ('19', 'The Sun'), ('20', 'Judgement'),
            ('21', 'The World')
        ]
        for new_rank, name in major_updates:
            cursor.execute('''
                UPDATE card_archetypes SET rank = ?
                WHERE name = ? AND cartomancy_type = 'Tarot'
            ''', (new_rank, name))

        # Minor Arcana: rank names -> numbers with suit prefix
        rank_name_to_num = {
            'Ace': 1, 'Two': 2, 'Three': 3, 'Four': 4, 'Five': 5,
            'Six': 6, 'Seven': 7, 'Eight': 8, 'Nine': 9, 'Ten': 10,
            'Page': 11, 'Knight': 12, 'Queen': 13, 'King': 14
        }
        suit_bases = {'Wands': 100, 'Cups': 200, 'Swords': 300, 'Pentacles': 400}

        for suit_name, suit_base in suit_bases.items():
            for rank_name, rank_num in rank_name_to_num.items():
                new_rank = str(suit_base + rank_num)
                card_name = f"{rank_name} of {suit_name}"
                cursor.execute('''
                    UPDATE card_archetypes SET rank = ?
                    WHERE name = ? AND cartomancy_type = 'Tarot'
                ''', (new_rank, card_name))

    # === Cartomancy Types ===
    def get_cartomancy_types(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM cartomancy_types ORDER BY name')
        return cursor.fetchall()
    
    def add_cartomancy_type(self, name: str):
        cursor = self.conn.cursor()
        cursor.execute('INSERT INTO cartomancy_types (name) VALUES (?)', (name,))
        self.conn.commit()
        return cursor.lastrowid
    
    # === Decks ===
    def get_decks(self, cartomancy_type_id: Optional[int] = None):
        cursor = self.conn.cursor()
        if cartomancy_type_id:
            cursor.execute('''
                SELECT d.*, ct.name as cartomancy_type_name 
                FROM decks d 
                JOIN cartomancy_types ct ON d.cartomancy_type_id = ct.id
                WHERE d.cartomancy_type_id = ?
                ORDER BY d.name
            ''', (cartomancy_type_id,))
        else:
            cursor.execute('''
                SELECT d.*, ct.name as cartomancy_type_name 
                FROM decks d 
                JOIN cartomancy_types ct ON d.cartomancy_type_id = ct.id
                ORDER BY ct.name, d.name
            ''')
        return cursor.fetchall()
    
    def get_deck(self, deck_id: int):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT d.*, ct.name as cartomancy_type_name 
            FROM decks d 
            JOIN cartomancy_types ct ON d.cartomancy_type_id = ct.id
            WHERE d.id = ?
        ''', (deck_id,))
        return cursor.fetchone()
    
    def add_deck(self, name: str, cartomancy_type_id: int, image_folder: str = None,
                 suit_names: dict = None, court_names: dict = None):
        cursor = self.conn.cursor()
        suit_names_json = json.dumps(suit_names) if suit_names else None
        court_names_json = json.dumps(court_names) if court_names else None
        cursor.execute(
            'INSERT INTO decks (name, cartomancy_type_id, image_folder, suit_names, court_names) VALUES (?, ?, ?, ?, ?)',
            (name, cartomancy_type_id, image_folder, suit_names_json, court_names_json)
        )
        self.conn.commit()
        return cursor.lastrowid
    
    def update_deck(self, deck_id: int, name: str = None, image_folder: str = None, suit_names: dict = None,
                    date_published: str = None, publisher: str = None, credits: str = None, notes: str = None,
                    card_back_image: str = None, booklet_info: str = None, cartomancy_type_id: int = None):
        cursor = self.conn.cursor()
        if name:
            cursor.execute('UPDATE decks SET name = ? WHERE id = ?', (name, deck_id))
        if cartomancy_type_id is not None:
            cursor.execute('UPDATE decks SET cartomancy_type_id = ? WHERE id = ?', (cartomancy_type_id, deck_id))
        if image_folder:
            cursor.execute('UPDATE decks SET image_folder = ? WHERE id = ?', (image_folder, deck_id))
        if suit_names is not None:
            suit_names_json = json.dumps(suit_names) if suit_names else None
            cursor.execute('UPDATE decks SET suit_names = ? WHERE id = ?', (suit_names_json, deck_id))
        if date_published is not None:
            cursor.execute('UPDATE decks SET date_published = ? WHERE id = ?', (date_published, deck_id))
        if publisher is not None:
            cursor.execute('UPDATE decks SET publisher = ? WHERE id = ?', (publisher, deck_id))
        if credits is not None:
            cursor.execute('UPDATE decks SET credits = ? WHERE id = ?', (credits, deck_id))
        if notes is not None:
            cursor.execute('UPDATE decks SET notes = ? WHERE id = ?', (notes, deck_id))
        if card_back_image is not None:
            cursor.execute('UPDATE decks SET card_back_image = ? WHERE id = ?', (card_back_image, deck_id))
        if booklet_info is not None:
            cursor.execute('UPDATE decks SET booklet_info = ? WHERE id = ?', (booklet_info, deck_id))
        self.conn.commit()
    
    def get_deck_suit_names(self, deck_id: int) -> dict:
        """Get custom suit names for a deck, or defaults"""
        deck = self.get_deck(deck_id)
        if deck and deck['suit_names']:
            return json.loads(deck['suit_names'])
        return {
            'wands': 'Wands',
            'cups': 'Cups',
            'swords': 'Swords',
            'pentacles': 'Pentacles'
        }

    def get_deck_court_names(self, deck_id: int) -> dict:
        """Get custom court card names for a deck, or defaults"""
        deck = self.get_deck(deck_id)
        if deck:
            try:
                court_names = deck['court_names']
                if court_names:
                    return json.loads(court_names)
            except (KeyError, TypeError):
                pass
        return {
            'page': 'Page',
            'knight': 'Knight',
            'queen': 'Queen',
            'king': 'King'
        }

    def update_deck_suit_names(self, deck_id: int, suit_names: dict, old_suit_names: dict = None):
        """Update suit names and rename all cards accordingly"""
        cursor = self.conn.cursor()
        
        # Update deck
        suit_names_json = json.dumps(suit_names)
        cursor.execute('UPDATE decks SET suit_names = ? WHERE id = ?', (suit_names_json, deck_id))
        
        # Update cards if old names provided
        if old_suit_names:
            for suit_key in ['wands', 'cups', 'swords', 'pentacles']:
                old_name = old_suit_names.get(suit_key)
                new_name = suit_names.get(suit_key)
                if old_name and new_name and old_name != new_name:
                    # Replace "of OldSuit" with "of NewSuit"
                    cursor.execute('''
                        UPDATE cards 
                        SET name = REPLACE(name, ?, ?)
                        WHERE deck_id = ? AND name LIKE ?
                    ''', (f'of {old_name}', f'of {new_name}', deck_id, f'%of {old_name}'))
        
        self.conn.commit()
    
    def delete_deck(self, deck_id: int):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM decks WHERE id = ?', (deck_id,))
        self.conn.commit()
    
    # === Cards ===
    def get_cards(self, deck_id: int):
        cursor = self.conn.cursor()
        cursor.execute(
            'SELECT * FROM cards WHERE deck_id = ? ORDER BY card_order, name',
            (deck_id,)
        )
        return cursor.fetchall()
    
    def get_card(self, card_id: int):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM cards WHERE id = ?', (card_id,))
        return cursor.fetchone()
    
    def add_card(self, deck_id: int, name: str, image_path: str = None, card_order: int = 0,
                 auto_metadata: bool = True):
        """Add a card to a deck. If auto_metadata is True, automatically assign archetype/rank/suit."""
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT INTO cards (deck_id, name, image_path, card_order) VALUES (?, ?, ?, ?)',
            (deck_id, name, image_path, card_order)
        )
        self.conn.commit()
        card_id = cursor.lastrowid

        # Auto-assign metadata based on card name
        if auto_metadata:
            deck = self.get_deck(deck_id)
            if deck:
                cartomancy_type = deck['cartomancy_type_name']
                self.auto_assign_card_metadata(card_id, name, cartomancy_type)

        return card_id

    def update_card(self, card_id: int, name: str = None, image_path: str = None, card_order: int = None):
        cursor = self.conn.cursor()
        updates = []
        params = []
        if name is not None:
            updates.append('name = ?')
            params.append(name)
        if image_path is not None:
            updates.append('image_path = ?')
            params.append(image_path)
        if card_order is not None:
            updates.append('card_order = ?')
            params.append(card_order)
        if updates:
            params.append(card_id)
            cursor.execute(f'UPDATE cards SET {", ".join(updates)} WHERE id = ?', params)
            self.conn.commit()

    def delete_card(self, card_id: int):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM cards WHERE id = ?', (card_id,))
        self.conn.commit()

    def bulk_add_cards(self, deck_id: int, cards: list, auto_metadata: bool = True):
        """Add multiple cards at once.
        cards can be:
        - list of (name, image_path, order) tuples (legacy format)
        - list of dicts with keys: name, image_path, sort_order, archetype, rank, suit, custom_fields (new format)
        If auto_metadata is True and legacy format is used, automatically assign archetype/rank/suit."""
        cursor = self.conn.cursor()

        # Check if new dict format or legacy tuple format
        if cards and isinstance(cards[0], dict):
            # New format with pre-computed metadata
            # Insert cards and collect custom_fields to apply after
            cards_with_custom_fields = []
            for c in cards:
                cursor.execute(
                    '''INSERT INTO cards (deck_id, name, image_path, card_order, archetype, rank, suit)
                       VALUES (?, ?, ?, ?, ?, ?, ?)''',
                    (deck_id, c['name'], c['image_path'], c['sort_order'],
                     c.get('archetype'), c.get('rank'), c.get('suit'))
                )
                card_id = cursor.lastrowid
                if c.get('custom_fields'):
                    cards_with_custom_fields.append((card_id, c['custom_fields']))

            # Apply custom_fields after all cards are inserted
            for card_id, custom_fields in cards_with_custom_fields:
                self.update_card_metadata(card_id, custom_fields=custom_fields)
        else:
            # Legacy tuple format
            cursor.executemany(
                'INSERT INTO cards (deck_id, name, image_path, card_order) VALUES (?, ?, ?, ?)',
                [(deck_id, name, path, order) for name, path, order in cards]
            )
            self.conn.commit()

            # Auto-assign metadata for all cards
            if auto_metadata:
                deck = self.get_deck(deck_id)
                if deck:
                    cartomancy_type = deck['cartomancy_type_name']
                    # Get all cards we just added and assign metadata
                    all_cards = self.get_cards(deck_id)
                    for card in all_cards:
                        # Only update if metadata is not already set
                        existing_archetype = card['archetype'] if 'archetype' in card.keys() else None
                        if not existing_archetype:
                            self.auto_assign_card_metadata(card['id'], card['name'], cartomancy_type)
                    return

        self.conn.commit()
    
    # === Spreads ===
    def get_spreads(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM spreads ORDER BY name')
        return cursor.fetchall()
    
    def get_spread(self, spread_id: int):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM spreads WHERE id = ?', (spread_id,))
        return cursor.fetchone()
    
    def add_spread(self, name: str, positions: list, description: str = None,
                   cartomancy_type: str = None, allowed_deck_types: list = None,
                   default_deck_id: int = None):
        """
        positions is a list of dicts: [{"x": 0, "y": 0, "label": "Past"}, ...]
        cartomancy_type: 'Tarot', 'Lenormand', 'Oracle', etc. (deprecated, for backwards compat)
        allowed_deck_types: list of cartomancy type names allowed for this spread, e.g. ['Tarot', 'Oracle']
        default_deck_id: ID of the default deck for this spread (overrides global default)
        """
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT INTO spreads (name, description, positions, cartomancy_type, allowed_deck_types, default_deck_id) VALUES (?, ?, ?, ?, ?, ?)',
            (name, description, json.dumps(positions), cartomancy_type,
             json.dumps(allowed_deck_types) if allowed_deck_types else None,
             default_deck_id)
        )
        self.conn.commit()
        return cursor.lastrowid

    def update_spread(self, spread_id: int, name: str = None, positions: list = None,
                      description: str = None, allowed_deck_types: list = None,
                      default_deck_id: int = None, clear_default_deck: bool = False):
        cursor = self.conn.cursor()
        if name:
            cursor.execute('UPDATE spreads SET name = ? WHERE id = ?', (name, spread_id))
        if positions:
            cursor.execute('UPDATE spreads SET positions = ? WHERE id = ?', (json.dumps(positions), spread_id))
        if description is not None:
            cursor.execute('UPDATE spreads SET description = ? WHERE id = ?', (description, spread_id))
        if allowed_deck_types is not None:
            cursor.execute('UPDATE spreads SET allowed_deck_types = ? WHERE id = ?',
                          (json.dumps(allowed_deck_types) if allowed_deck_types else None, spread_id))
        if default_deck_id is not None or clear_default_deck:
            cursor.execute('UPDATE spreads SET default_deck_id = ? WHERE id = ?',
                          (default_deck_id, spread_id))
        self.conn.commit()
    
    def delete_spread(self, spread_id: int):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM spreads WHERE id = ?', (spread_id,))
        self.conn.commit()
    
    # === Journal Entries ===
    def get_entries(self, limit: int = 50, offset: int = 0):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM journal_entries 
            ORDER BY created_at DESC 
            LIMIT ? OFFSET ?
        ''', (limit, offset))
        return cursor.fetchall()
    
    def get_entry(self, entry_id: int):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM journal_entries WHERE id = ?', (entry_id,))
        return cursor.fetchone()
    
    def search_entries(self, query: str = None, tag_ids: list = None, 
                      deck_id: int = None, spread_id: int = None,
                      cartomancy_type: str = None, card_name: str = None,
                      date_from: str = None, date_to: str = None):
        """Search entries with various filters"""
        cursor = self.conn.cursor()
        
        sql = 'SELECT DISTINCT je.* FROM journal_entries je'
        joins = []
        conditions = []
        params = []
        
        if tag_ids:
            joins.append('JOIN entry_tags et ON je.id = et.entry_id')
            placeholders = ','.join('?' * len(tag_ids))
            conditions.append(f'et.tag_id IN ({placeholders})')
            params.extend(tag_ids)
        
        if deck_id or spread_id or cartomancy_type or card_name:
            joins.append('JOIN entry_readings er ON je.id = er.entry_id')
            if deck_id:
                conditions.append('er.deck_id = ?')
                params.append(deck_id)
            if spread_id:
                conditions.append('er.spread_id = ?')
                params.append(spread_id)
            if cartomancy_type:
                conditions.append('er.cartomancy_type = ?')
                params.append(cartomancy_type)
            if card_name:
                conditions.append('er.cards_used LIKE ?')
                params.append(f'%{card_name}%')
        
        if query:
            conditions.append('(je.title LIKE ? OR je.content LIKE ?)')
            params.extend([f'%{query}%', f'%{query}%'])
        
        if date_from:
            conditions.append('je.created_at >= ?')
            params.append(date_from)
        
        if date_to:
            conditions.append('je.created_at <= ?')
            params.append(date_to)
        
        sql += ' ' + ' '.join(joins)
        if conditions:
            sql += ' WHERE ' + ' AND '.join(conditions)
        sql += ' ORDER BY je.created_at DESC'
        
        cursor.execute(sql, params)
        return cursor.fetchall()
    
    def add_entry(self, title: str = None, content: str = None,
                  reading_datetime: str = None, location_name: str = None,
                  location_lat: float = None, location_lon: float = None,
                  querent_id: int = None, reader_id: int = None):
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()
        # Use provided reading_datetime or default to now
        if reading_datetime is None:
            reading_datetime = now
        cursor.execute(
            '''INSERT INTO journal_entries
               (title, content, created_at, updated_at, reading_datetime, location_name, location_lat, location_lon, querent_id, reader_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (title, content, now, now, reading_datetime, location_name, location_lat, location_lon, querent_id, reader_id)
        )
        self.conn.commit()
        return cursor.lastrowid

    def update_entry(self, entry_id: int, title: str = None, content: str = None,
                     reading_datetime: str = None, location_name: str = None,
                     location_lat: float = None, location_lon: float = None,
                     querent_id: int = None, reader_id: int = None):
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()
        updates = []
        params = []

        if title is not None:
            updates.append('title = ?')
            params.append(title)
        if content is not None:
            updates.append('content = ?')
            params.append(content)
        if reading_datetime is not None:
            updates.append('reading_datetime = ?')
            params.append(reading_datetime)
        if location_name is not None:
            updates.append('location_name = ?')
            params.append(location_name)
        if location_lat is not None:
            updates.append('location_lat = ?')
            params.append(location_lat)
        if location_lon is not None:
            updates.append('location_lon = ?')
            params.append(location_lon)
        if querent_id is not None:
            updates.append('querent_id = ?')
            params.append(querent_id if querent_id != 0 else None)
        if reader_id is not None:
            updates.append('reader_id = ?')
            params.append(reader_id if reader_id != 0 else None)

        if updates:
            updates.append('updated_at = ?')
            params.append(now)
            params.append(entry_id)
            cursor.execute(f'UPDATE journal_entries SET {", ".join(updates)} WHERE id = ?', params)
            self.conn.commit()
    
    def delete_entry(self, entry_id: int):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM journal_entries WHERE id = ?', (entry_id,))
        self.conn.commit()
    
    # === Entry Readings ===
    def get_entry_readings(self, entry_id: int):
        cursor = self.conn.cursor()
        cursor.execute(
            'SELECT * FROM entry_readings WHERE entry_id = ? ORDER BY position_order',
            (entry_id,)
        )
        return cursor.fetchall()
    
    def add_entry_reading(self, entry_id: int, spread_id: int = None, spread_name: str = None,
                         deck_id: int = None, deck_name: str = None, 
                         cartomancy_type: str = None, cards_used: list = None,
                         position_order: int = 0):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO entry_readings 
            (entry_id, spread_id, spread_name, deck_id, deck_name, cartomancy_type, cards_used, position_order)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (entry_id, spread_id, spread_name, deck_id, deck_name, 
              cartomancy_type, json.dumps(cards_used) if cards_used else None, position_order))
        self.conn.commit()
        return cursor.lastrowid
    
    def delete_entry_readings(self, entry_id: int):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM entry_readings WHERE entry_id = ?', (entry_id,))
        self.conn.commit()

    # === Export/Import ===
    def export_entries_json(self, entry_ids: List[int] = None) -> dict:
        """
        Export entries to a JSON-serializable dictionary.
        If entry_ids is None, exports all entries.
        """
        cursor = self.conn.cursor()

        if entry_ids:
            placeholders = ','.join('?' * len(entry_ids))
            cursor.execute(f'SELECT * FROM journal_entries WHERE id IN ({placeholders})', entry_ids)
        else:
            cursor.execute('SELECT * FROM journal_entries')

        entries_data = []
        for entry in cursor.fetchall():
            entry_dict = dict(entry)
            entry_id = entry_dict['id']

            # Get readings for this entry
            readings = self.get_entry_readings(entry_id)
            entry_dict['readings'] = []
            for reading in readings:
                reading_dict = dict(reading)
                # Parse cards_used JSON string
                if reading_dict.get('cards_used'):
                    reading_dict['cards_used'] = json.loads(reading_dict['cards_used'])
                entry_dict['readings'].append(reading_dict)

            # Get tags for this entry
            cursor.execute('''
                SELECT t.* FROM tags t
                JOIN entry_tags et ON t.id = et.tag_id
                WHERE et.entry_id = ?
            ''', (entry_id,))
            entry_dict['tags'] = [dict(tag) for tag in cursor.fetchall()]

            # Get querent and reader profile names (for portability)
            if entry_dict.get('querent_id'):
                querent = self.get_profile(entry_dict['querent_id'])
                entry_dict['querent_name'] = querent['name'] if querent else None
            else:
                entry_dict['querent_name'] = None

            if entry_dict.get('reader_id'):
                reader = self.get_profile(entry_dict['reader_id'])
                entry_dict['reader_name'] = reader['name'] if reader else None
            else:
                entry_dict['reader_name'] = None

            # Get follow-up notes
            follow_up_notes = self.get_follow_up_notes(entry_id)
            entry_dict['follow_up_notes'] = [dict(note) for note in follow_up_notes]

            entries_data.append(entry_dict)

        return {
            'version': '1.0',
            'exported_at': datetime.now().isoformat(),
            'entries': entries_data
        }

    def export_entries_to_file(self, filepath: str, entry_ids: List[int] = None):
        """Export entries to a JSON file."""
        data = self.export_entries_json(entry_ids)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def export_entries_to_zip(self, filepath: str, entry_ids: List[int] = None):
        """
        Export entries to a ZIP file containing JSON data and card images.
        """
        data = self.export_entries_json(entry_ids)

        # Collect all unique image paths from readings
        image_paths = set()
        for entry in data['entries']:
            for reading in entry.get('readings', []):
                deck_id = reading.get('deck_id')
                if deck_id:
                    cards = self.get_cards(deck_id)
                    for card in cards:
                        if card['image_path'] and os.path.exists(card['image_path']):
                            image_paths.add(card['image_path'])

        # Create ZIP file
        with zipfile.ZipFile(filepath, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Add JSON data
            zf.writestr('entries.json', json.dumps(data, indent=2, ensure_ascii=False))

            # Add images with relative paths
            image_mapping = {}
            for img_path in image_paths:
                # Create a relative path inside the zip
                rel_path = f"images/{Path(img_path).parent.name}/{Path(img_path).name}"
                image_mapping[img_path] = rel_path
                zf.write(img_path, rel_path)

            # Add image mapping file
            zf.writestr('image_mapping.json', json.dumps(image_mapping, indent=2))

    def import_entries_from_json(self, data: dict, merge_tags: bool = True) -> dict:
        """
        Import entries from a JSON dictionary.
        Returns a summary of what was imported.
        """
        if not isinstance(data, dict) or 'entries' not in data:
            raise ValueError("Invalid import data format")

        imported_count = 0
        skipped_count = 0
        tag_map = {}  # old_tag_id -> new_tag_id

        for entry_data in data['entries']:
            # Look up querent and reader by name
            querent_id = None
            reader_id = None

            if entry_data.get('querent_name'):
                profiles = self.get_profiles()
                for p in profiles:
                    if p['name'] == entry_data['querent_name']:
                        querent_id = p['id']
                        break

            if entry_data.get('reader_name'):
                profiles = self.get_profiles()
                for p in profiles:
                    if p['name'] == entry_data['reader_name']:
                        reader_id = p['id']
                        break

            # Create new entry (don't reuse IDs)
            entry_id = self.add_entry(
                title=entry_data.get('title'),
                content=entry_data.get('content'),
                reading_datetime=entry_data.get('reading_datetime'),
                location_name=entry_data.get('location_name'),
                location_lat=entry_data.get('location_lat'),
                location_lon=entry_data.get('location_lon'),
                querent_id=querent_id,
                reader_id=reader_id
            )

            # Import readings
            for reading in entry_data.get('readings', []):
                # Look up spread and deck by name (IDs may differ)
                spread_id = None
                deck_id = None

                if reading.get('spread_name'):
                    spreads = self.get_spreads()
                    for s in spreads:
                        if s['name'] == reading['spread_name']:
                            spread_id = s['id']
                            break

                if reading.get('deck_name'):
                    decks = self.get_decks()
                    for d in decks:
                        if d['name'] == reading['deck_name']:
                            deck_id = d['id']
                            break

                self.add_entry_reading(
                    entry_id=entry_id,
                    spread_id=spread_id,
                    spread_name=reading.get('spread_name'),
                    deck_id=deck_id,
                    deck_name=reading.get('deck_name'),
                    cartomancy_type=reading.get('cartomancy_type'),
                    cards_used=reading.get('cards_used'),
                    position_order=reading.get('position_order', 0)
                )

            # Import tags
            if merge_tags:
                for tag_data in entry_data.get('tags', []):
                    old_tag_id = tag_data.get('id')

                    if old_tag_id not in tag_map:
                        # Check if tag with same name exists
                        existing_tags = self.get_tags()
                        existing_tag = None
                        for t in existing_tags:
                            if t['name'] == tag_data['name']:
                                existing_tag = t
                                break

                        if existing_tag:
                            tag_map[old_tag_id] = existing_tag['id']
                        else:
                            # Create new tag
                            new_tag_id = self.add_tag(
                                name=tag_data['name'],
                                color=tag_data.get('color', '#6B5B95')
                            )
                            tag_map[old_tag_id] = new_tag_id

                    # Link tag to entry
                    self.add_entry_tag(entry_id, tag_map[old_tag_id])

            # Import follow-up notes
            for note_data in entry_data.get('follow_up_notes', []):
                # Insert directly with original timestamp preserved
                cursor = self.conn.cursor()
                cursor.execute('''
                    INSERT INTO follow_up_notes (entry_id, content, created_at)
                    VALUES (?, ?, ?)
                ''', (entry_id, note_data.get('content', ''), note_data.get('created_at')))
                self.conn.commit()

            imported_count += 1

        return {
            'imported': imported_count,
            'skipped': skipped_count,
            'tags_created': len([v for k, v in tag_map.items() if k != v])
        }

    def import_entries_from_file(self, filepath: str, merge_tags: bool = True) -> dict:
        """Import entries from a JSON file."""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return self.import_entries_from_json(data, merge_tags)

    def import_entries_from_zip(self, filepath: str, merge_tags: bool = True) -> dict:
        """
        Import entries from a ZIP file.
        Note: Images are extracted but deck/card image paths are not automatically updated.
        The import matches cards by name within existing decks.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            with zipfile.ZipFile(filepath, 'r') as zf:
                zf.extractall(temp_dir)

            # Read the JSON data
            json_path = Path(temp_dir) / 'entries.json'
            if not json_path.exists():
                raise ValueError("Invalid ZIP file: missing entries.json")

            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            return self.import_entries_from_json(data, merge_tags)

    # === Profiles ===
    def get_profiles(self):
        """Get all profiles"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM profiles ORDER BY name')
        return cursor.fetchall()

    def get_profile(self, profile_id: int):
        """Get a single profile by ID"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM profiles WHERE id = ?', (profile_id,))
        return cursor.fetchone()

    def add_profile(self, name: str, gender: str = None, birth_date: str = None,
                    birth_time: str = None, birth_place_name: str = None,
                    birth_place_lat: float = None, birth_place_lon: float = None):
        """Add a new profile"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO profiles (name, gender, birth_date, birth_time,
                                  birth_place_name, birth_place_lat, birth_place_lon)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (name, gender, birth_date, birth_time, birth_place_name,
              birth_place_lat, birth_place_lon))
        self.conn.commit()
        return cursor.lastrowid

    def update_profile(self, profile_id: int, name: str = None, gender: str = None,
                       birth_date: str = None, birth_time: str = None,
                       birth_place_name: str = None, birth_place_lat: float = None,
                       birth_place_lon: float = None):
        """Update an existing profile"""
        cursor = self.conn.cursor()
        updates = []
        params = []

        if name is not None:
            updates.append('name = ?')
            params.append(name)
        if gender is not None:
            updates.append('gender = ?')
            params.append(gender)
        if birth_date is not None:
            updates.append('birth_date = ?')
            params.append(birth_date)
        if birth_time is not None:
            updates.append('birth_time = ?')
            params.append(birth_time)
        if birth_place_name is not None:
            updates.append('birth_place_name = ?')
            params.append(birth_place_name)
        if birth_place_lat is not None:
            updates.append('birth_place_lat = ?')
            params.append(birth_place_lat)
        if birth_place_lon is not None:
            updates.append('birth_place_lon = ?')
            params.append(birth_place_lon)

        if updates:
            params.append(profile_id)
            cursor.execute(f'UPDATE profiles SET {", ".join(updates)} WHERE id = ?', params)
            self.conn.commit()

    def delete_profile(self, profile_id: int):
        """Delete a profile (will set querent_id/reader_id to NULL in journal entries)"""
        cursor = self.conn.cursor()
        # Clear references in journal entries
        cursor.execute('UPDATE journal_entries SET querent_id = NULL WHERE querent_id = ?', (profile_id,))
        cursor.execute('UPDATE journal_entries SET reader_id = NULL WHERE reader_id = ?', (profile_id,))
        # Delete the profile
        cursor.execute('DELETE FROM profiles WHERE id = ?', (profile_id,))
        self.conn.commit()

    # === Follow-up Notes ===
    def get_follow_up_notes(self, entry_id: int):
        """Get all follow-up notes for an entry, ordered by date"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM follow_up_notes
            WHERE entry_id = ?
            ORDER BY created_at ASC
        ''', (entry_id,))
        return cursor.fetchall()

    def add_follow_up_note(self, entry_id: int, content: str):
        """Add a follow-up note to an entry"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO follow_up_notes (entry_id, content, created_at)
            VALUES (?, ?, ?)
        ''', (entry_id, content, datetime.now().isoformat()))
        self.conn.commit()
        return cursor.lastrowid

    def update_follow_up_note(self, note_id: int, content: str):
        """Update a follow-up note's content"""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE follow_up_notes SET content = ? WHERE id = ?
        ''', (content, note_id))
        self.conn.commit()

    def delete_follow_up_note(self, note_id: int):
        """Delete a follow-up note"""
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM follow_up_notes WHERE id = ?', (note_id,))
        self.conn.commit()

    # === Tags ===
    def get_tags(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM tags ORDER BY name')
        return cursor.fetchall()
    
    def get_tag(self, tag_id: int):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM tags WHERE id = ?', (tag_id,))
        return cursor.fetchone()
    
    def add_tag(self, name: str, color: str = '#6B5B95'):
        cursor = self.conn.cursor()
        cursor.execute('INSERT INTO tags (name, color) VALUES (?, ?)', (name, color))
        self.conn.commit()
        return cursor.lastrowid
    
    def update_tag(self, tag_id: int, name: str = None, color: str = None):
        cursor = self.conn.cursor()
        if name:
            cursor.execute('UPDATE tags SET name = ? WHERE id = ?', (name, tag_id))
        if color:
            cursor.execute('UPDATE tags SET color = ? WHERE id = ?', (color, tag_id))
        self.conn.commit()
    
    def delete_tag(self, tag_id: int):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM tags WHERE id = ?', (tag_id,))
        self.conn.commit()
    
    def get_entry_tags(self, entry_id: int):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT t.* FROM tags t
            JOIN entry_tags et ON t.id = et.tag_id
            WHERE et.entry_id = ?
            ORDER BY t.name
        ''', (entry_id,))
        return cursor.fetchall()
    
    def add_entry_tag(self, entry_id: int, tag_id: int):
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT OR IGNORE INTO entry_tags (entry_id, tag_id) VALUES (?, ?)',
            (entry_id, tag_id)
        )
        self.conn.commit()
    
    def remove_entry_tag(self, entry_id: int, tag_id: int):
        cursor = self.conn.cursor()
        cursor.execute(
            'DELETE FROM entry_tags WHERE entry_id = ? AND tag_id = ?',
            (entry_id, tag_id)
        )
        self.conn.commit()
    
    def set_entry_tags(self, entry_id: int, tag_ids: list):
        """Replace all tags for an entry"""
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM entry_tags WHERE entry_id = ?', (entry_id,))
        for tag_id in tag_ids:
            cursor.execute(
                'INSERT INTO entry_tags (entry_id, tag_id) VALUES (?, ?)',
                (entry_id, tag_id)
            )
        self.conn.commit()

    # === Deck Tags ===
    def get_deck_tags(self):
        """Get all deck tags"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM deck_tags ORDER BY name')
        return cursor.fetchall()

    def get_deck_tag(self, tag_id: int):
        """Get a single deck tag by ID"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM deck_tags WHERE id = ?', (tag_id,))
        return cursor.fetchone()

    def add_deck_tag(self, name: str, color: str = '#6B5B95'):
        """Create a new deck tag"""
        cursor = self.conn.cursor()
        cursor.execute('INSERT INTO deck_tags (name, color) VALUES (?, ?)', (name, color))
        self.conn.commit()
        return cursor.lastrowid

    def update_deck_tag(self, tag_id: int, name: str = None, color: str = None):
        """Update a deck tag's name and/or color"""
        cursor = self.conn.cursor()
        if name:
            cursor.execute('UPDATE deck_tags SET name = ? WHERE id = ?', (name, tag_id))
        if color:
            cursor.execute('UPDATE deck_tags SET color = ? WHERE id = ?', (color, tag_id))
        self.conn.commit()

    def delete_deck_tag(self, tag_id: int):
        """Delete a deck tag (cascades to assignments)"""
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM deck_tags WHERE id = ?', (tag_id,))
        self.conn.commit()

    def get_tags_for_deck(self, deck_id: int):
        """Get all tags assigned to a deck"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT t.* FROM deck_tags t
            JOIN deck_tag_assignments dta ON t.id = dta.tag_id
            WHERE dta.deck_id = ?
            ORDER BY t.name
        ''', (deck_id,))
        return cursor.fetchall()

    def add_tag_to_deck(self, deck_id: int, tag_id: int):
        """Assign a tag to a deck"""
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT OR IGNORE INTO deck_tag_assignments (deck_id, tag_id) VALUES (?, ?)',
            (deck_id, tag_id)
        )
        self.conn.commit()

    def remove_tag_from_deck(self, deck_id: int, tag_id: int):
        """Remove a tag from a deck"""
        cursor = self.conn.cursor()
        cursor.execute(
            'DELETE FROM deck_tag_assignments WHERE deck_id = ? AND tag_id = ?',
            (deck_id, tag_id)
        )
        self.conn.commit()

    def set_deck_tags(self, deck_id: int, tag_ids: list):
        """Replace all tags for a deck"""
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM deck_tag_assignments WHERE deck_id = ?', (deck_id,))
        for tag_id in tag_ids:
            cursor.execute(
                'INSERT INTO deck_tag_assignments (deck_id, tag_id) VALUES (?, ?)',
                (deck_id, tag_id)
            )
        self.conn.commit()

    # === Card Tags ===
    def get_card_tags(self):
        """Get all card tags"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM card_tags ORDER BY name')
        return cursor.fetchall()

    def get_card_tag(self, tag_id: int):
        """Get a single card tag by ID"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM card_tags WHERE id = ?', (tag_id,))
        return cursor.fetchone()

    def add_card_tag(self, name: str, color: str = '#6B5B95'):
        """Create a new card tag"""
        cursor = self.conn.cursor()
        cursor.execute('INSERT INTO card_tags (name, color) VALUES (?, ?)', (name, color))
        self.conn.commit()
        return cursor.lastrowid

    def update_card_tag(self, tag_id: int, name: str = None, color: str = None):
        """Update a card tag's name and/or color"""
        cursor = self.conn.cursor()
        if name:
            cursor.execute('UPDATE card_tags SET name = ? WHERE id = ?', (name, tag_id))
        if color:
            cursor.execute('UPDATE card_tags SET color = ? WHERE id = ?', (color, tag_id))
        self.conn.commit()

    def delete_card_tag(self, tag_id: int):
        """Delete a card tag (cascades to assignments)"""
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM card_tags WHERE id = ?', (tag_id,))
        self.conn.commit()

    def get_tags_for_card(self, card_id: int):
        """Get all tags directly assigned to a card"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT t.* FROM card_tags t
            JOIN card_tag_assignments cta ON t.id = cta.tag_id
            WHERE cta.card_id = ?
            ORDER BY t.name
        ''', (card_id,))
        return cursor.fetchall()

    def get_inherited_tags_for_card(self, card_id: int):
        """Get deck tags inherited by a card (from its parent deck)"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT dt.* FROM deck_tags dt
            JOIN deck_tag_assignments dta ON dt.id = dta.tag_id
            JOIN cards c ON c.deck_id = dta.deck_id
            WHERE c.id = ?
            ORDER BY dt.name
        ''', (card_id,))
        return cursor.fetchall()

    def add_tag_to_card(self, card_id: int, tag_id: int):
        """Assign a tag to a card"""
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT OR IGNORE INTO card_tag_assignments (card_id, tag_id) VALUES (?, ?)',
            (card_id, tag_id)
        )
        self.conn.commit()

    def remove_tag_from_card(self, card_id: int, tag_id: int):
        """Remove a tag from a card"""
        cursor = self.conn.cursor()
        cursor.execute(
            'DELETE FROM card_tag_assignments WHERE card_id = ? AND tag_id = ?',
            (card_id, tag_id)
        )
        self.conn.commit()

    def set_card_tags(self, card_id: int, tag_ids: list):
        """Replace all tags for a card"""
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM card_tag_assignments WHERE card_id = ?', (card_id,))
        for tag_id in tag_ids:
            cursor.execute(
                'INSERT INTO card_tag_assignments (card_id, tag_id) VALUES (?, ?)',
                (card_id, tag_id)
            )
        self.conn.commit()

    # === Card Archetypes ===
    def get_archetypes(self, cartomancy_type: str = None):
        """Get all archetypes, optionally filtered by cartomancy type"""
        cursor = self.conn.cursor()
        if cartomancy_type:
            cursor.execute('''
                SELECT * FROM card_archetypes
                WHERE cartomancy_type = ?
                ORDER BY id
            ''', (cartomancy_type,))
        else:
            cursor.execute('SELECT * FROM card_archetypes ORDER BY cartomancy_type, id')
        return cursor.fetchall()

    def search_archetypes(self, query: str, cartomancy_type: str = None):
        """Search archetypes by name for autocomplete"""
        cursor = self.conn.cursor()
        search_pattern = f'%{query}%'
        if cartomancy_type:
            cursor.execute('''
                SELECT * FROM card_archetypes
                WHERE cartomancy_type = ? AND name LIKE ?
                ORDER BY name
                LIMIT 20
            ''', (cartomancy_type, search_pattern))
        else:
            cursor.execute('''
                SELECT * FROM card_archetypes
                WHERE name LIKE ?
                ORDER BY cartomancy_type, name
                LIMIT 20
            ''', (search_pattern,))
        return cursor.fetchall()

    def get_archetype_by_name(self, name: str, cartomancy_type: str):
        """Get a specific archetype by name and type"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM card_archetypes
            WHERE name = ? AND cartomancy_type = ?
        ''', (name, cartomancy_type))
        return cursor.fetchone()

    def parse_card_name_for_archetype(self, card_name: str, cartomancy_type: str):
        """
        Parse a card name and return archetype info (archetype, rank, suit).
        Handles various naming conventions for Tarot and Lenormand.
        Returns (archetype_name, rank, suit) or (None, None, None) if not found.
        """
        if not card_name:
            return None, None, None

        card_name_lower = card_name.lower().strip()

        if cartomancy_type == 'Tarot':
            return self._parse_tarot_card_name(card_name, card_name_lower)
        elif cartomancy_type == 'Lenormand':
            return self._parse_lenormand_card_name(card_name, card_name_lower)
        elif cartomancy_type == 'Playing Cards':
            return self._parse_playing_card_name(card_name, card_name_lower)

        return None, None, None

    def _parse_tarot_card_name(self, card_name: str, card_name_lower: str):
        """Parse Tarot card names and return (archetype, rank, suit)"""
        # Major Arcana mappings (various naming conventions)
        major_arcana = {
            'fool': ('The Fool', '0', 'Major Arcana'),
            'the fool': ('The Fool', '0', 'Major Arcana'),
            'magician': ('The Magician', '1', 'Major Arcana'),
            'the magician': ('The Magician', '1', 'Major Arcana'),
            'magus': ('The Magician', '1', 'Major Arcana'),
            'the magus': ('The Magician', '1', 'Major Arcana'),
            'high priestess': ('The High Priestess', '2', 'Major Arcana'),
            'the high priestess': ('The High Priestess', '2', 'Major Arcana'),
            'priestess': ('The High Priestess', '2', 'Major Arcana'),
            'the priestess': ('The High Priestess', '2', 'Major Arcana'),
            'empress': ('The Empress', '3', 'Major Arcana'),
            'the empress': ('The Empress', '3', 'Major Arcana'),
            'emperor': ('The Emperor', '4', 'Major Arcana'),
            'the emperor': ('The Emperor', '4', 'Major Arcana'),
            'hierophant': ('The Hierophant', '5', 'Major Arcana'),
            'the hierophant': ('The Hierophant', '5', 'Major Arcana'),
            'high priest': ('The Hierophant', '5', 'Major Arcana'),
            'the high priest': ('The Hierophant', '5', 'Major Arcana'),
            'lovers': ('The Lovers', '6', 'Major Arcana'),
            'the lovers': ('The Lovers', '6', 'Major Arcana'),
            'chariot': ('The Chariot', '7', 'Major Arcana'),
            'the chariot': ('The Chariot', '7', 'Major Arcana'),
            'strength': ('Strength', '8', 'Major Arcana'),
            'lust': ('Strength', '8', 'Major Arcana'),
            'hermit': ('The Hermit', '9', 'Major Arcana'),
            'the hermit': ('The Hermit', '9', 'Major Arcana'),
            'wheel of fortune': ('Wheel of Fortune', '10', 'Major Arcana'),
            'the wheel of fortune': ('Wheel of Fortune', '10', 'Major Arcana'),
            'wheel': ('Wheel of Fortune', '10', 'Major Arcana'),
            'fortune': ('Wheel of Fortune', '10', 'Major Arcana'),
            'justice': ('Justice', '11', 'Major Arcana'),
            'adjustment': ('Justice', '11', 'Major Arcana'),
            'hanged man': ('The Hanged Man', '12', 'Major Arcana'),
            'the hanged man': ('The Hanged Man', '12', 'Major Arcana'),
            'death': ('Death', '13', 'Major Arcana'),
            'temperance': ('Temperance', '14', 'Major Arcana'),
            'art': ('Temperance', '14', 'Major Arcana'),
            'devil': ('The Devil', '15', 'Major Arcana'),
            'the devil': ('The Devil', '15', 'Major Arcana'),
            'tower': ('The Tower', '16', 'Major Arcana'),
            'the tower': ('The Tower', '16', 'Major Arcana'),
            'star': ('The Star', '17', 'Major Arcana'),
            'the star': ('The Star', '17', 'Major Arcana'),
            'moon': ('The Moon', '18', 'Major Arcana'),
            'the moon': ('The Moon', '18', 'Major Arcana'),
            'sun': ('The Sun', '19', 'Major Arcana'),
            'the sun': ('The Sun', '19', 'Major Arcana'),
            'judgement': ('Judgement', '20', 'Major Arcana'),
            'judgment': ('Judgement', '20', 'Major Arcana'),
            'the aeon': ('Judgement', '20', 'Major Arcana'),
            'aeon': ('Judgement', '20', 'Major Arcana'),
            'world': ('The World', '21', 'Major Arcana'),
            'the world': ('The World', '21', 'Major Arcana'),
            'universe': ('The World', '21', 'Major Arcana'),
            'the universe': ('The World', '21', 'Major Arcana'),
        }

        # Check for exact major arcana match
        if card_name_lower in major_arcana:
            return major_arcana[card_name_lower]

        # Minor Arcana parsing
        # Suit name variations
        suit_mappings = {
            'wands': 'Wands', 'wand': 'Wands', 'rods': 'Wands', 'staves': 'Wands', 'batons': 'Wands',
            'cups': 'Cups', 'cup': 'Cups', 'chalices': 'Cups', 'chalice': 'Cups',
            'swords': 'Swords', 'sword': 'Swords',
            'pentacles': 'Pentacles', 'pentacle': 'Pentacles', 'coins': 'Pentacles',
            'disks': 'Pentacles', 'discs': 'Pentacles', 'disk': 'Pentacles', 'disc': 'Pentacles',
        }

        # Rank name variations
        rank_mappings = {
            'ace': ('Ace', 1), 'one': ('Ace', 1), '1': ('Ace', 1), 'i': ('Ace', 1),
            'two': ('Two', 2), '2': ('Two', 2), 'ii': ('Two', 2),
            'three': ('Three', 3), '3': ('Three', 3), 'iii': ('Three', 3),
            'four': ('Four', 4), '4': ('Four', 4), 'iv': ('Four', 4),
            'five': ('Five', 5), '5': ('Five', 5), 'v': ('Five', 5),
            'six': ('Six', 6), '6': ('Six', 6), 'vi': ('Six', 6),
            'seven': ('Seven', 7), '7': ('Seven', 7), 'vii': ('Seven', 7),
            'eight': ('Eight', 8), '8': ('Eight', 8), 'viii': ('Eight', 8),
            'nine': ('Nine', 9), '9': ('Nine', 9), 'ix': ('Nine', 9),
            'ten': ('Ten', 10), '10': ('Ten', 10), 'x': ('Ten', 10),
            'page': ('Page', 11), 'princess': ('Page', 11),
            'knight': ('Knight', 12), 'prince': ('Knight', 12),
            'queen': ('Queen', 13),
            'king': ('King', 14),
        }

        suit_bases = {'Wands': 100, 'Cups': 200, 'Swords': 300, 'Pentacles': 400}

        # Try to find suit and rank in the name
        found_suit = None
        found_rank = None
        found_rank_num = None

        for suit_key, suit_name in suit_mappings.items():
            if suit_key in card_name_lower:
                found_suit = suit_name
                break

        for rank_key, (rank_name, rank_num) in rank_mappings.items():
            if rank_key in card_name_lower.split() or card_name_lower.startswith(rank_key + ' '):
                found_rank = rank_name
                found_rank_num = rank_num
                break

        if found_suit and found_rank:
            archetype = f"{found_rank} of {found_suit}"
            rank = str(suit_bases[found_suit] + found_rank_num)
            return archetype, rank, found_suit

        return None, None, None

    def _parse_lenormand_card_name(self, card_name: str, card_name_lower: str):
        """Parse Lenormand card names and return (archetype, rank, suit)"""
        lenormand_cards = {
            'rider': ('Rider', '1'), 'cavalier': ('Rider', '1'),
            'clover': ('Clover', '2'),
            'ship': ('Ship', '3'),
            'house': ('House', '4'),
            'tree': ('Tree', '5'),
            'clouds': ('Clouds', '6'), 'cloud': ('Clouds', '6'),
            'snake': ('Snake', '7'),
            'coffin': ('Coffin', '8'),
            'bouquet': ('Bouquet', '9'), 'flowers': ('Bouquet', '9'),
            'scythe': ('Scythe', '10'),
            'whip': ('Whip', '11'), 'broom': ('Whip', '11'), 'birch': ('Whip', '11'),
            'birds': ('Birds', '12'), 'owls': ('Birds', '12'),
            'child': ('Child', '13'),
            'fox': ('Fox', '14'),
            'bear': ('Bear', '15'),
            'stars': ('Stars', '16'), 'star': ('Stars', '16'),
            'stork': ('Stork', '17'),
            'dog': ('Dog', '18'),
            'tower': ('Tower', '19'),
            'garden': ('Garden', '20'),
            'mountain': ('Mountain', '21'),
            'crossroads': ('Crossroads', '22'), 'crossroad': ('Crossroads', '22'),
            'paths': ('Crossroads', '22'), 'path': ('Crossroads', '22'),
            'mice': ('Mice', '23'), 'mouse': ('Mice', '23'),
            'heart': ('Heart', '24'),
            'ring': ('Ring', '25'),
            'book': ('Book', '26'),
            'letter': ('Letter', '27'),
            'man': ('Man', '28'), 'gentleman': ('Man', '28'),
            'woman': ('Woman', '29'), 'lady': ('Woman', '29'),
            'lily': ('Lily', '30'), 'lilies': ('Lily', '30'),
            'sun': ('Sun', '31'),
            'moon': ('Moon', '32'),
            'key': ('Key', '33'),
            'fish': ('Fish', '34'),
            'anchor': ('Anchor', '35'),
            'cross': ('Cross', '36'),
        }

        # Try exact match first
        for key, (name, rank) in lenormand_cards.items():
            if key in card_name_lower:
                return name, rank, None

        # Try matching by number prefix (e.g., "01 Rider", "1. Rider")
        import re
        num_match = re.match(r'^(\d+)\D', card_name)
        if num_match:
            num = int(num_match.group(1))
            if 1 <= num <= 36:
                # Find the card with this number
                for key, (name, rank) in lenormand_cards.items():
                    if rank == str(num):
                        return name, rank, None

        return None, None, None

    def _parse_playing_card_name(self, card_name: str, card_name_lower: str):
        """Parse Playing Card names and return (archetype, rank, suit)"""
        suit_mappings = {
            'hearts': 'Hearts', 'heart': 'Hearts', '♥': 'Hearts',
            'diamonds': 'Diamonds', 'diamond': 'Diamonds', '♦': 'Diamonds',
            'clubs': 'Clubs', 'club': 'Clubs', '♣': 'Clubs',
            'spades': 'Spades', 'spade': 'Spades', '♠': 'Spades',
        }

        rank_mappings = {
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

        for suit_key, suit_name in suit_mappings.items():
            if suit_key in card_name_lower:
                found_suit = suit_name
                break

        for rank_key, (rank_name, _) in rank_mappings.items():
            if rank_key in card_name_lower.split() or card_name_lower.startswith(rank_key + ' '):
                found_rank = rank_name
                break

        if found_suit and found_rank:
            archetype = f"{found_rank} of {found_suit}"
            return archetype, found_rank, found_suit

        return None, None, None

    def auto_assign_card_metadata(self, card_id: int, card_name: str, cartomancy_type: str,
                                   preset_name: str = None):
        """Automatically assign archetype, rank, and suit based on card name.
        If preset_name is provided, uses the import_presets module for ordering-aware metadata."""
        if preset_name:
            # Use import_presets for ordering-aware metadata
            from import_presets import get_presets
            presets = get_presets()
            metadata = presets.get_card_metadata(card_name, preset_name)
            if metadata.get('archetype') or metadata.get('rank') or metadata.get('suit'):
                self.update_card_metadata(card_id, archetype=metadata.get('archetype'),
                                         rank=metadata.get('rank'), suit=metadata.get('suit'))
        else:
            # Fall back to legacy parsing
            archetype, rank, suit = self.parse_card_name_for_archetype(card_name, cartomancy_type)
            if archetype or rank or suit:
                self.update_card_metadata(card_id, archetype=archetype, rank=rank, suit=suit)

    def auto_assign_deck_metadata(self, deck_id: int, overwrite: bool = False,
                                   preset_name: str = None, use_sort_order: bool = False):
        """
        Automatically assign metadata to all cards in a deck.
        If overwrite is False, only updates cards without existing archetype.
        If preset_name is provided, uses ordering-aware metadata from import_presets.
        If use_sort_order is True, assigns metadata based on card sort order (1, 2, 3...)
        instead of parsing card names.
        Returns the number of cards updated.
        """
        deck = self.get_deck(deck_id)
        if not deck:
            return 0

        cartomancy_type = deck['cartomancy_type_name']
        cards = self.get_cards(deck_id)
        updated = 0

        # Get custom suit names from deck if available
        custom_suit_names = None
        if deck['suit_names']:
            try:
                custom_suit_names = json.loads(deck['suit_names'])
            except:
                pass

        # Get custom court names from deck if available
        custom_court_names = None
        if deck['court_names']:
            try:
                custom_court_names = json.loads(deck['court_names'])
            except:
                pass

        # Use import_presets if preset_name is provided
        if preset_name:
            from import_presets import get_presets
            presets = get_presets()

            # If using sort order, sort cards and assign metadata sequentially
            if use_sort_order:
                # Sort cards by their current card_order
                sorted_cards = sorted(cards, key=lambda c: c['card_order'] if c['card_order'] else 999)
                for idx, card in enumerate(sorted_cards):
                    # Skip if already has archetype and not overwriting
                    existing_archetype = card['archetype'] if 'archetype' in card.keys() else None
                    if not overwrite and existing_archetype:
                        continue

                    # Use 1-based index as the sort order for metadata lookup
                    sort_order = idx + 1
                    metadata = presets.get_card_metadata_by_sort_order(sort_order, preset_name)

                    if metadata:
                        self.update_card_metadata(card['id'], archetype=metadata.get('archetype'),
                                                 rank=metadata.get('rank'), suit=metadata.get('suit'),
                                                 custom_fields=metadata.get('custom_fields'))
                        # Update sort order to match
                        self.update_card(card['id'], card_order=sort_order)
                        updated += 1
            else:
                # Parse card names for metadata
                for card in cards:
                    # Skip if already has archetype and not overwriting
                    existing_archetype = card['archetype'] if 'archetype' in card.keys() else None
                    if not overwrite and existing_archetype:
                        continue

                    metadata = presets.get_card_metadata(card['name'], preset_name, custom_suit_names,
                                                         custom_court_names)
                    # Check if we have any metadata to update (including sort_order for Oracle decks)
                    has_metadata = metadata.get('archetype') or metadata.get('rank') or metadata.get('suit')
                    has_sort_order = metadata.get('sort_order') is not None and metadata.get('sort_order') != 999

                    if has_metadata or has_sort_order:
                        if has_metadata:
                            self.update_card_metadata(card['id'], archetype=metadata.get('archetype'),
                                                     rank=metadata.get('rank'), suit=metadata.get('suit'),
                                                     custom_fields=metadata.get('custom_fields'))
                        # Also update sort order
                        if has_sort_order:
                            self.update_card(card['id'], card_order=metadata.get('sort_order'))
                        updated += 1
        else:
            # Fall back to legacy parsing (no preset ordering)
            for card in cards:
                existing_archetype = card['archetype'] if 'archetype' in card.keys() else None
                if not overwrite and existing_archetype:
                    continue

                archetype, rank, suit = self.parse_card_name_for_archetype(card['name'], cartomancy_type)
                if archetype or rank or suit:
                    self.update_card_metadata(card['id'], archetype=archetype, rank=rank, suit=suit)
                    updated += 1

        return updated

    # === Card Metadata ===
    def update_card_metadata(self, card_id: int, archetype: str = None, rank: str = None,
                             suit: str = None, notes: str = None, custom_fields: dict = None):
        """Update card metadata fields"""
        cursor = self.conn.cursor()
        updates = []
        params = []

        if archetype is not None:
            updates.append('archetype = ?')
            params.append(archetype)
        if rank is not None:
            updates.append('rank = ?')
            params.append(rank)
        if suit is not None:
            updates.append('suit = ?')
            params.append(suit)
        if notes is not None:
            updates.append('notes = ?')
            params.append(notes)
        if custom_fields is not None:
            updates.append('custom_fields = ?')
            params.append(json.dumps(custom_fields) if custom_fields else None)

        if updates:
            params.append(card_id)
            cursor.execute(f'UPDATE cards SET {", ".join(updates)} WHERE id = ?', params)
            self.conn.commit()

    def get_card_with_metadata(self, card_id: int):
        """Get a card with all its metadata"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT c.*, d.cartomancy_type_id, ct.name as cartomancy_type_name
            FROM cards c
            JOIN decks d ON c.deck_id = d.id
            JOIN cartomancy_types ct ON d.cartomancy_type_id = ct.id
            WHERE c.id = ?
        ''', (card_id,))
        return cursor.fetchone()

    # === Deck Custom Fields ===
    def get_deck_custom_fields(self, deck_id: int):
        """Get custom field definitions for a deck"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM deck_custom_fields
            WHERE deck_id = ?
            ORDER BY field_order, id
        ''', (deck_id,))
        return cursor.fetchall()

    def add_deck_custom_field(self, deck_id: int, field_name: str, field_type: str,
                              field_options: list = None, field_order: int = 0):
        """Add a custom field definition to a deck"""
        cursor = self.conn.cursor()
        options_json = json.dumps(field_options) if field_options else None
        cursor.execute('''
            INSERT INTO deck_custom_fields (deck_id, field_name, field_type, field_options, field_order)
            VALUES (?, ?, ?, ?, ?)
        ''', (deck_id, field_name, field_type, options_json, field_order))
        self.conn.commit()
        return cursor.lastrowid

    def update_deck_custom_field(self, field_id: int, field_name: str = None,
                                 field_type: str = None, field_options: list = None,
                                 field_order: int = None):
        """Update a deck custom field definition"""
        cursor = self.conn.cursor()
        updates = []
        params = []

        if field_name is not None:
            updates.append('field_name = ?')
            params.append(field_name)
        if field_type is not None:
            updates.append('field_type = ?')
            params.append(field_type)
        if field_options is not None:
            updates.append('field_options = ?')
            params.append(json.dumps(field_options) if field_options else None)
        if field_order is not None:
            updates.append('field_order = ?')
            params.append(field_order)

        if updates:
            params.append(field_id)
            cursor.execute(f'UPDATE deck_custom_fields SET {", ".join(updates)} WHERE id = ?', params)
            self.conn.commit()

    def delete_deck_custom_field(self, field_id: int):
        """Delete a deck custom field definition"""
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM deck_custom_fields WHERE id = ?', (field_id,))
        self.conn.commit()

    # === Card Custom Fields ===
    def get_card_custom_fields(self, card_id: int):
        """Get custom fields for a specific card"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM card_custom_fields
            WHERE card_id = ?
            ORDER BY field_order, id
        ''', (card_id,))
        return cursor.fetchall()

    def add_card_custom_field(self, card_id: int, field_name: str, field_type: str,
                              field_value: str = None, field_options: list = None,
                              field_order: int = 0):
        """Add a custom field to a specific card"""
        cursor = self.conn.cursor()
        options_json = json.dumps(field_options) if field_options else None
        cursor.execute('''
            INSERT INTO card_custom_fields (card_id, field_name, field_type, field_options, field_value, field_order)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (card_id, field_name, field_type, options_json, field_value, field_order))
        self.conn.commit()
        return cursor.lastrowid

    def update_card_custom_field(self, field_id: int, field_name: str = None,
                                 field_type: str = None, field_value: str = None,
                                 field_options: list = None, field_order: int = None):
        """Update a card custom field"""
        cursor = self.conn.cursor()
        updates = []
        params = []

        if field_name is not None:
            updates.append('field_name = ?')
            params.append(field_name)
        if field_type is not None:
            updates.append('field_type = ?')
            params.append(field_type)
        if field_value is not None:
            updates.append('field_value = ?')
            params.append(field_value)
        if field_options is not None:
            updates.append('field_options = ?')
            params.append(json.dumps(field_options) if field_options else None)
        if field_order is not None:
            updates.append('field_order = ?')
            params.append(field_order)

        if updates:
            params.append(field_id)
            cursor.execute(f'UPDATE card_custom_fields SET {", ".join(updates)} WHERE id = ?', params)
            self.conn.commit()

    def delete_card_custom_field(self, field_id: int):
        """Delete a card custom field"""
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM card_custom_fields WHERE id = ?', (field_id,))
        self.conn.commit()

    def get_deck_card_custom_field_values(self, deck_id: int, field_name: str):
        """Get all values for a deck-level custom field across all cards in the deck"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT c.id as card_id, c.name as card_name, c.custom_fields
            FROM cards c
            WHERE c.deck_id = ?
        ''', (deck_id,))
        results = []
        for row in cursor.fetchall():
            custom_fields = json.loads(row['custom_fields']) if row['custom_fields'] else {}
            results.append({
                'card_id': row['card_id'],
                'card_name': row['card_name'],
                'value': custom_fields.get(field_name)
            })
        return results

    def set_card_deck_field_value(self, card_id: int, field_name: str, value):
        """Set a deck-level custom field value for a specific card (stored in cards.custom_fields JSON)"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT custom_fields FROM cards WHERE id = ?', (card_id,))
        row = cursor.fetchone()
        custom_fields = json.loads(row['custom_fields']) if row and row['custom_fields'] else {}
        custom_fields[field_name] = value
        cursor.execute('UPDATE cards SET custom_fields = ? WHERE id = ?',
                       (json.dumps(custom_fields), card_id))
        self.conn.commit()

    # === Statistics ===
    def get_stats(self):
        cursor = self.conn.cursor()
        stats = {}
        
        cursor.execute('SELECT COUNT(*) FROM journal_entries')
        stats['total_entries'] = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM decks')
        stats['total_decks'] = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM cards')
        stats['total_cards'] = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM spreads')
        stats['total_spreads'] = cursor.fetchone()[0]
        
        # Most used decks
        cursor.execute('''
            SELECT deck_name, COUNT(*) as count 
            FROM entry_readings 
            WHERE deck_name IS NOT NULL
            GROUP BY deck_name 
            ORDER BY count DESC 
            LIMIT 5
        ''')
        stats['top_decks'] = cursor.fetchall()
        
        # Most used spreads
        cursor.execute('''
            SELECT spread_name, COUNT(*) as count 
            FROM entry_readings 
            WHERE spread_name IS NOT NULL
            GROUP BY spread_name 
            ORDER BY count DESC 
            LIMIT 5
        ''')
        stats['top_spreads'] = cursor.fetchall()
        
        return stats

    # === Settings ===
    def get_setting(self, key: str, default=None):
        """Get a setting value"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
        result = cursor.fetchone()
        return result['value'] if result else default

    def set_setting(self, key: str, value: str):
        """Set a setting value"""
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)',
            (key, value)
        )
        self.conn.commit()

    def get_default_deck(self, cartomancy_type: str):
        """Get the default deck ID for a cartomancy type"""
        deck_id = self.get_setting(f'default_deck_{cartomancy_type.lower()}')
        return int(deck_id) if deck_id else None

    def set_default_deck(self, cartomancy_type: str, deck_id: int):
        """Set the default deck for a cartomancy type"""
        self.set_setting(f'default_deck_{cartomancy_type.lower()}', str(deck_id))

    def get_default_querent(self):
        """Get the default querent profile ID"""
        profile_id = self.get_setting('default_querent')
        return int(profile_id) if profile_id else None

    def set_default_querent(self, profile_id: int):
        """Set the default querent profile ID"""
        self.set_setting('default_querent', str(profile_id) if profile_id else '')

    def get_default_reader(self):
        """Get the default reader profile ID"""
        profile_id = self.get_setting('default_reader')
        return int(profile_id) if profile_id else None

    def set_default_reader(self, profile_id: int):
        """Set the default reader profile ID"""
        self.set_setting('default_reader', str(profile_id) if profile_id else '')

    def get_default_reader_same_as_querent(self):
        """Get whether default reader should be same as querent"""
        val = self.get_setting('default_reader_same_as_querent')
        return val == '1' if val else False

    def set_default_reader_same_as_querent(self, same: bool):
        """Set whether default reader should be same as querent"""
        self.set_setting('default_reader_same_as_querent', '1' if same else '0')

    # === Deck Export/Import with Metadata ===
    def export_deck_json(self, deck_id: int) -> dict:
        """Export a deck with all its cards and metadata to a JSON-serializable dictionary."""
        deck = self.get_deck(deck_id)
        if not deck:
            raise ValueError(f"Deck {deck_id} not found")

        deck_dict = dict(deck)

        # Get suit names
        deck_dict['suit_names'] = self.get_deck_suit_names(deck_id)

        # Get custom field definitions
        custom_fields = self.get_deck_custom_fields(deck_id)
        deck_dict['custom_field_definitions'] = []
        for cf in custom_fields:
            cf_dict = {
                'field_name': cf['field_name'],
                'field_type': cf['field_type'],
                'field_order': cf['field_order']
            }
            if cf['field_options']:
                try:
                    cf_dict['field_options'] = json.loads(cf['field_options'])
                except:
                    cf_dict['field_options'] = None
            deck_dict['custom_field_definitions'].append(cf_dict)

        # Get all cards with metadata
        cards = self.get_cards(deck_id)
        deck_dict['cards'] = []
        for card in cards:
            card_dict = {
                'name': card['name'],
                'image_path': card['image_path'],
                'card_order': card['card_order'],
                'archetype': card['archetype'] if 'archetype' in card.keys() else None,
                'rank': card['rank'] if 'rank' in card.keys() else None,
                'suit': card['suit'] if 'suit' in card.keys() else None,
                'notes': card['notes'] if 'notes' in card.keys() else None,
            }
            # Parse custom fields
            custom_fields_json = card['custom_fields'] if 'custom_fields' in card.keys() else None
            if custom_fields_json:
                try:
                    card_dict['custom_fields'] = json.loads(custom_fields_json)
                except:
                    card_dict['custom_fields'] = None
            else:
                card_dict['custom_fields'] = None

            deck_dict['cards'].append(card_dict)

        return {
            'version': '1.0',
            'exported_at': datetime.now().isoformat(),
            'deck': deck_dict
        }

    def export_deck_to_file(self, deck_id: int, filepath: str):
        """Export a deck to a JSON file."""
        data = self.export_deck_json(deck_id)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def import_deck_from_json(self, data: dict) -> dict:
        """
        Import a deck from a JSON dictionary.
        Returns a summary of what was imported.
        """
        if not isinstance(data, dict) or 'deck' not in data:
            raise ValueError("Invalid deck import data format")

        deck_data = data['deck']

        # Find or create the cartomancy type
        cart_type_name = deck_data.get('cartomancy_type_name', 'Tarot')
        cart_types = self.get_cartomancy_types()
        cart_type_id = None
        for ct in cart_types:
            if ct['name'] == cart_type_name:
                cart_type_id = ct['id']
                break
        if not cart_type_id:
            cart_type_id = 1  # Default to Tarot

        # Create the deck
        deck_id = self.add_deck(
            name=deck_data.get('name', 'Imported Deck'),
            cartomancy_type_id=cart_type_id,
            image_folder=deck_data.get('image_folder'),
            suit_names=deck_data.get('suit_names')
        )

        # Import custom field definitions
        custom_field_map = {}  # Maps field_name to field_id for reference
        for cf_def in deck_data.get('custom_field_definitions', []):
            field_id = self.add_deck_custom_field(
                deck_id=deck_id,
                field_name=cf_def['field_name'],
                field_type=cf_def['field_type'],
                field_options=cf_def.get('field_options'),
                field_order=cf_def.get('field_order', 0)
            )
            custom_field_map[cf_def['field_name']] = field_id

        # Import cards
        cards_imported = 0
        for card_data in deck_data.get('cards', []):
            # Add the card
            card_id = self.add_card(
                deck_id=deck_id,
                name=card_data['name'],
                image_path=card_data.get('image_path'),
                card_order=card_data.get('card_order', 0)
            )

            # Update metadata
            self.update_card_metadata(
                card_id=card_id,
                archetype=card_data.get('archetype'),
                rank=card_data.get('rank'),
                suit=card_data.get('suit'),
                notes=card_data.get('notes'),
                custom_fields=card_data.get('custom_fields')
            )

            cards_imported += 1

        return {
            'deck_id': deck_id,
            'deck_name': deck_data.get('name'),
            'cards_imported': cards_imported,
            'custom_fields_created': len(custom_field_map)
        }

    def import_deck_from_file(self, filepath: str) -> dict:
        """Import a deck from a JSON file."""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return self.import_deck_from_json(data)

    def close(self):
        self.conn.close()


# Create default spreads
def create_default_spreads(db: Database):
    """Create some common tarot and lenormand spreads"""
    spreads = db.get_spreads()
    if len(spreads) == 0:
        # Card dimensions - smaller for better fit
        cw, ch = 60, 90  # card width, height
        
        # === TAROT SPREADS ===
        
        # Single card
        db.add_spread(
            "Daily Draw",
            [
                {"x": 200, "y": 100, "label": "Card of the Day", "width": cw, "height": ch}
            ],
            "A single card for daily reflection",
            "Tarot"
        )
        
        # Three card spread (line)
        db.add_spread(
            "Three Card Line",
            [
                {"x": 80, "y": 100, "label": "Past", "width": cw, "height": ch},
                {"x": 160, "y": 100, "label": "Present", "width": cw, "height": ch},
                {"x": 240, "y": 100, "label": "Future", "width": cw, "height": ch}
            ],
            "A simple past-present-future reading",
            "Tarot"
        )
        
        # Five card spread (line)
        db.add_spread(
            "Five Card Line",
            [
                {"x": 40, "y": 100, "label": "1", "width": cw, "height": ch},
                {"x": 110, "y": 100, "label": "2", "width": cw, "height": ch},
                {"x": 180, "y": 100, "label": "3", "width": cw, "height": ch},
                {"x": 250, "y": 100, "label": "4", "width": cw, "height": ch},
                {"x": 320, "y": 100, "label": "5", "width": cw, "height": ch}
            ],
            "Five cards in a row",
            "Tarot"
        )
        
        # Five card cross
        db.add_spread(
            "Five Card Cross",
            [
                {"x": 150, "y": 110, "label": "Present", "width": cw, "height": ch},
                {"x": 70, "y": 110, "label": "Past", "width": cw, "height": ch},
                {"x": 230, "y": 110, "label": "Future", "width": cw, "height": ch},
                {"x": 150, "y": 10, "label": "Above", "width": cw, "height": ch},
                {"x": 150, "y": 210, "label": "Below", "width": cw, "height": ch}
            ],
            "A five card cross spread for deeper insight",
            "Tarot"
        )
        
        # Celtic Cross - compact layout
        db.add_spread(
            "Celtic Cross",
            [
                {"x": 120, "y": 130, "label": "Present", "width": cw, "height": ch},
                {"x": 120, "y": 130, "label": "Challenge", "width": ch, "height": cw, "rotated": True},
                {"x": 120, "y": 230, "label": "Foundation", "width": cw, "height": ch},
                {"x": 120, "y": 30, "label": "Crown", "width": cw, "height": ch},
                {"x": 30, "y": 130, "label": "Past", "width": cw, "height": ch},
                {"x": 210, "y": 130, "label": "Future", "width": cw, "height": ch},
                {"x": 310, "y": 300, "label": "Self", "width": cw, "height": ch},
                {"x": 310, "y": 200, "label": "Environment", "width": cw, "height": ch},
                {"x": 310, "y": 100, "label": "Hopes/Fears", "width": cw, "height": ch},
                {"x": 310, "y": 0, "label": "Outcome", "width": cw, "height": ch}
            ],
            "The classic 10-card Celtic Cross spread",
            "Tarot"
        )

        # 15-Card Golden Dawn / Thoth Spread
        # Layout: Wide X shape with horizontal triads
        # Center triad in middle, 4 triads at diagonal corners
        # Card size 50x75, gap of 8 between cards
        db.add_spread(
            "Golden Dawn 15-Card",
            [
                # Spirit/Significator Triad (Center) - Cards 2, 1, 3 horizontal
                {"x": 175, "y": 150, "label": "2", "width": 50, "height": 75},
                {"x": 233, "y": 150, "label": "1 - Significator", "width": 50, "height": 75},
                {"x": 291, "y": 150, "label": "3", "width": 50, "height": 75},

                # Current Path / Earth Triad (Upper Right) - Cards 4, 8, 12 horizontal
                {"x": 320, "y": 50, "label": "4", "width": 50, "height": 75},
                {"x": 378, "y": 50, "label": "8 - Current Path", "width": 50, "height": 75},
                {"x": 436, "y": 50, "label": "12", "width": 50, "height": 75},

                # Alternate Path / Water Triad (Upper Left) - Cards 5, 9, 13 horizontal
                {"x": 30, "y": 50, "label": "5", "width": 50, "height": 75},
                {"x": 88, "y": 50, "label": "9 - Alternate Path", "width": 50, "height": 75},
                {"x": 146, "y": 50, "label": "13", "width": 50, "height": 75},

                # Psychological / Air Triad (Lower Left) - Cards 6, 10, 14 horizontal
                {"x": 30, "y": 250, "label": "6", "width": 50, "height": 75},
                {"x": 88, "y": 250, "label": "10 - Psychology", "width": 50, "height": 75},
                {"x": 146, "y": 250, "label": "14", "width": 50, "height": 75},

                # Karma / Fire Triad (Lower Right) - Cards 7, 11, 15 horizontal
                {"x": 320, "y": 250, "label": "7", "width": 50, "height": 75},
                {"x": 378, "y": 250, "label": "11 - Karma/Destiny", "width": 50, "height": 75},
                {"x": 436, "y": 250, "label": "15", "width": 50, "height": 75},
            ],
            "The 15-card Golden Dawn/Thoth spread with five elemental triads. Uses elemental dignities, not reversals.",
            "Tarot"
        )

        # === LENORMAND SPREADS ===
        
        # Three card line (Lenormand)
        db.add_spread(
            "Lenormand 3-Card",
            [
                {"x": 80, "y": 100, "label": "1", "width": cw, "height": ch},
                {"x": 160, "y": 100, "label": "2", "width": cw, "height": ch},
                {"x": 240, "y": 100, "label": "3", "width": cw, "height": ch}
            ],
            "Simple three-card Lenormand line",
            "Lenormand"
        )
        
        # Five card line (Lenormand)
        db.add_spread(
            "Lenormand 5-Card",
            [
                {"x": 40, "y": 100, "label": "1", "width": cw, "height": ch},
                {"x": 110, "y": 100, "label": "2", "width": cw, "height": ch},
                {"x": 180, "y": 100, "label": "3", "width": cw, "height": ch},
                {"x": 250, "y": 100, "label": "4", "width": cw, "height": ch},
                {"x": 320, "y": 100, "label": "5", "width": cw, "height": ch}
            ],
            "Five-card Lenormand line",
            "Lenormand"
        )
        
        # 3x3 Box (Lenormand)
        db.add_spread(
            "Lenormand 3x3 Box",
            [
                {"x": 80, "y": 10, "label": "1", "width": cw, "height": ch},
                {"x": 160, "y": 10, "label": "2", "width": cw, "height": ch},
                {"x": 240, "y": 10, "label": "3", "width": cw, "height": ch},
                {"x": 80, "y": 110, "label": "4", "width": cw, "height": ch},
                {"x": 160, "y": 110, "label": "5", "width": cw, "height": ch},
                {"x": 240, "y": 110, "label": "6", "width": cw, "height": ch},
                {"x": 80, "y": 210, "label": "7", "width": cw, "height": ch},
                {"x": 160, "y": 210, "label": "8", "width": cw, "height": ch},
                {"x": 240, "y": 210, "label": "9", "width": cw, "height": ch}
            ],
            "Nine-card Lenormand box spread",
            "Lenormand"
        )
        
        # Grand Tableau (8x4 + 4 = 36 cards)
        gt_positions = []
        gt_cw, gt_ch = 45, 65  # Even smaller for Grand Tableau
        for row in range(4):
            for col in range(9):
                card_num = row * 9 + col + 1
                if card_num <= 36:
                    gt_positions.append({
                        "x": 10 + col * 52,
                        "y": 10 + row * 75,
                        "label": str(card_num),
                        "width": gt_cw,
                        "height": gt_ch
                    })
        
        db.add_spread(
            "Grand Tableau (9x4)",
            gt_positions,
            "Full 36-card Lenormand Grand Tableau",
            "Lenormand"
        )

    # Always check for missing default spreads (for existing users)
    _add_missing_default_spreads(db)


def _add_missing_default_spreads(db: Database):
    """Add any default spreads that are missing (for existing databases)"""
    existing_spreads = {s['name'] for s in db.get_spreads()}

    # Golden Dawn 15-Card spread - wide X shape with horizontal triads
    if "Golden Dawn 15-Card" not in existing_spreads:
        db.add_spread(
            "Golden Dawn 15-Card",
            [
                # Spirit/Significator Triad (Center) - Cards 2, 1, 3 horizontal
                {"x": 175, "y": 150, "label": "2", "width": 50, "height": 75},
                {"x": 233, "y": 150, "label": "1 - Significator", "width": 50, "height": 75},
                {"x": 291, "y": 150, "label": "3", "width": 50, "height": 75},

                # Current Path / Earth Triad (Upper Right) - Cards 4, 8, 12 horizontal
                {"x": 320, "y": 50, "label": "4", "width": 50, "height": 75},
                {"x": 378, "y": 50, "label": "8 - Current Path", "width": 50, "height": 75},
                {"x": 436, "y": 50, "label": "12", "width": 50, "height": 75},

                # Alternate Path / Water Triad (Upper Left) - Cards 5, 9, 13 horizontal
                {"x": 30, "y": 50, "label": "5", "width": 50, "height": 75},
                {"x": 88, "y": 50, "label": "9 - Alternate Path", "width": 50, "height": 75},
                {"x": 146, "y": 50, "label": "13", "width": 50, "height": 75},

                # Psychological / Air Triad (Lower Left) - Cards 6, 10, 14 horizontal
                {"x": 30, "y": 250, "label": "6", "width": 50, "height": 75},
                {"x": 88, "y": 250, "label": "10 - Psychology", "width": 50, "height": 75},
                {"x": 146, "y": 250, "label": "14", "width": 50, "height": 75},

                # Karma / Fire Triad (Lower Right) - Cards 7, 11, 15 horizontal
                {"x": 320, "y": 250, "label": "7", "width": 50, "height": 75},
                {"x": 378, "y": 250, "label": "11 - Karma/Destiny", "width": 50, "height": 75},
                {"x": 436, "y": 250, "label": "15", "width": 50, "height": 75},
            ],
            "The 15-card Golden Dawn/Thoth spread with five elemental triads. Uses elemental dignities, not reversals.",
            "Tarot"
        )

    # Fix Thoth deck metadata if needed
    _fix_thoth_deck_metadata(db)


def _fix_thoth_deck_metadata(db: Database):
    """Fix Thoth deck court card metadata to use proper verbose rank names.

    This fixes an issue where Thoth court cards were imported with incomplete
    verbose rank names (e.g., 'King / Court Rank 4' instead of
    'King / Knight (Thoth) / Court Card 4').
    """
    # Find Thoth decks (could be named 'Thoth' or 'Thoth Tarot')
    decks = db.get_decks()
    thoth_deck = None
    for deck in decks:
        if deck['name'] in ('Thoth', 'Thoth Tarot'):
            thoth_deck = deck
            break

    if not thoth_deck:
        return

    # Check if fix is needed by looking at Knight of Disks
    cards = db.get_cards(thoth_deck['id'])
    knight_of_disks = None
    for card in cards:
        if card['name'] == 'Knight of Disks':
            knight_of_disks = card
            break

    if not knight_of_disks:
        return

    # Check if rank is already correct - should be the full verbose format
    # with "Knight (Thoth)" in it, not just "King / Court Rank 4"
    current_rank = knight_of_disks['rank'] if knight_of_disks['rank'] else ''
    if 'Knight (Thoth)' in str(current_rank):
        return  # Already fixed

    # Fix the metadata using preset-aware function
    db.auto_assign_deck_metadata(thoth_deck['id'], overwrite=True, preset_name='Tarot (Thoth)')


def create_default_decks(db: Database):
    """Import default decks if they exist and no decks have been added yet"""
    from import_presets import get_presets

    # Only import if no decks exist yet
    existing_decks = db.get_decks()
    if len(existing_decks) > 0:
        return

    # Get the directory where this script is located (for resolving relative paths)
    script_dir = Path(__file__).parent.resolve()

    # Get import presets instance
    presets = get_presets()

    # Define default decks to import
    default_decks = [
        {
            'name': 'Rider-Waite-Smith',
            'folder': 'Rider-Waite-Smith',
            'preset': 'Tarot (RWS Ordering)',
            'type': 'Tarot'
        },
        {
            'name': 'Tarot de Marseille',
            'folder': 'TdM',
            'preset': 'Tarot (Pre-Golden Dawn Ordering)',
            'type': 'Tarot'
        },
        {
            'name': 'Thoth',
            'folder': 'Thoth',
            'preset': 'Tarot (Thoth)',
            'type': 'Tarot'
        },
        {
            'name': 'Blue Owl Lenormand',
            'folder': 'Blue Owl Lenormand',
            'preset': 'Lenormand (36 cards)',
            'type': 'Lenormand'
        },
        {
            'name': 'Playing Cards',
            'folder': 'PlayingCards',
            'preset': 'Playing Cards with Jokers (54 cards)',
            'type': 'Playing Cards'
        }
    ]

    for deck_info in default_decks:
        # Use script directory as base for relative paths
        folder_path = script_dir / deck_info['folder']

        # Skip if folder doesn't exist
        if not folder_path.exists():
            continue

        # Get cartomancy type ID
        type_id = None
        for ct in db.get_cartomancy_types():
            if ct['name'] == deck_info['type']:
                type_id = ct['id']
                break

        if not type_id:
            continue

        # Create the deck
        deck_id = db.add_deck(
            name=deck_info['name'],
            cartomancy_type_id=type_id,
            image_folder=str(folder_path.absolute())
        )

        # Look for card back image
        card_back_path = presets.find_card_back_image(str(folder_path), deck_info['preset'])
        if card_back_path:
            db.update_deck(deck_id, card_back_image=card_back_path)

        # Import cards from folder
        valid_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
        cards_to_add = []

        for filepath in sorted(folder_path.iterdir()):
            if filepath.suffix.lower() in valid_extensions:
                # Skip card back images
                if presets.is_card_back_file(filepath.name, deck_info['preset']):
                    continue

                # Map filename to card name using preset
                card_name = presets.map_filename_to_card(
                    filepath.name,
                    deck_info['preset']
                )

                # Get full metadata including verbose rank names
                metadata = presets.get_card_metadata(card_name, deck_info['preset'])

                cards_to_add.append({
                    'name': card_name,
                    'image_path': str(filepath.absolute()),
                    'sort_order': metadata.get('sort_order', 0),
                    'archetype': metadata.get('archetype'),
                    'rank': metadata.get('rank'),
                    'suit': metadata.get('suit')
                })

        # Sort by sort order and add to database
        cards_to_add.sort(key=lambda x: x['sort_order'])
        db.bulk_add_cards(deck_id, cards_to_add)
