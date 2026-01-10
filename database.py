"""
Database module for Tarot Journal App
Handles all data persistence using SQLite
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Optional
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (cartomancy_type_id) REFERENCES cartomancy_types(id)
            )
        ''')
        
        # Migration: add suit_names column if missing
        cursor.execute("PRAGMA table_info(decks)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'suit_names' not in columns:
            cursor.execute('ALTER TABLE decks ADD COLUMN suit_names TEXT')
        
        # Cards table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                deck_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                image_path TEXT,
                card_order INTEGER DEFAULT 0,
                FOREIGN KEY (deck_id) REFERENCES decks(id) ON DELETE CASCADE
            )
        ''')
        
        # Spreads table (saved spread layouts)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS spreads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                positions JSON NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Journal entries table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS journal_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
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
        
        # Insert default cartomancy types
        default_types = ['Tarot', 'Lenormand', 'Oracle']
        for ct in default_types:
            cursor.execute(
                'INSERT OR IGNORE INTO cartomancy_types (name) VALUES (?)', 
                (ct,)
            )
        
        self.conn.commit()
    
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
    
    def add_deck(self, name: str, cartomancy_type_id: int, image_folder: str = None, suit_names: dict = None):
        cursor = self.conn.cursor()
        suit_names_json = json.dumps(suit_names) if suit_names else None
        cursor.execute(
            'INSERT INTO decks (name, cartomancy_type_id, image_folder, suit_names) VALUES (?, ?, ?, ?)',
            (name, cartomancy_type_id, image_folder, suit_names_json)
        )
        self.conn.commit()
        return cursor.lastrowid
    
    def update_deck(self, deck_id: int, name: str = None, image_folder: str = None, suit_names: dict = None):
        cursor = self.conn.cursor()
        if name:
            cursor.execute('UPDATE decks SET name = ? WHERE id = ?', (name, deck_id))
        if image_folder:
            cursor.execute('UPDATE decks SET image_folder = ? WHERE id = ?', (image_folder, deck_id))
        if suit_names is not None:
            suit_names_json = json.dumps(suit_names) if suit_names else None
            cursor.execute('UPDATE decks SET suit_names = ? WHERE id = ?', (suit_names_json, deck_id))
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
    
    def add_card(self, deck_id: int, name: str, image_path: str = None, card_order: int = 0):
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT INTO cards (deck_id, name, image_path, card_order) VALUES (?, ?, ?, ?)',
            (deck_id, name, image_path, card_order)
        )
        self.conn.commit()
        return cursor.lastrowid
    
    def update_card(self, card_id: int, name: str = None, image_path: str = None):
        cursor = self.conn.cursor()
        if name:
            cursor.execute('UPDATE cards SET name = ? WHERE id = ?', (name, card_id))
        if image_path:
            cursor.execute('UPDATE cards SET image_path = ? WHERE id = ?', (image_path, card_id))
        self.conn.commit()
    
    def delete_card(self, card_id: int):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM cards WHERE id = ?', (card_id,))
        self.conn.commit()
    
    def bulk_add_cards(self, deck_id: int, cards: list):
        """Add multiple cards at once. cards is list of (name, image_path, order) tuples"""
        cursor = self.conn.cursor()
        cursor.executemany(
            'INSERT INTO cards (deck_id, name, image_path, card_order) VALUES (?, ?, ?, ?)',
            [(deck_id, name, path, order) for name, path, order in cards]
        )
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
    
    def add_spread(self, name: str, positions: list, description: str = None):
        """
        positions is a list of dicts: [{"x": 0, "y": 0, "label": "Past"}, ...]
        """
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT INTO spreads (name, description, positions) VALUES (?, ?, ?)',
            (name, description, json.dumps(positions))
        )
        self.conn.commit()
        return cursor.lastrowid
    
    def update_spread(self, spread_id: int, name: str = None, positions: list = None, description: str = None):
        cursor = self.conn.cursor()
        if name:
            cursor.execute('UPDATE spreads SET name = ? WHERE id = ?', (name, spread_id))
        if positions:
            cursor.execute('UPDATE spreads SET positions = ? WHERE id = ?', (json.dumps(positions), spread_id))
        if description is not None:
            cursor.execute('UPDATE spreads SET description = ? WHERE id = ?', (description, spread_id))
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
    
    def add_entry(self, title: str = None, content: str = None):
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute(
            'INSERT INTO journal_entries (title, content, created_at, updated_at) VALUES (?, ?, ?, ?)',
            (title, content, now, now)
        )
        self.conn.commit()
        return cursor.lastrowid
    
    def update_entry(self, entry_id: int, title: str = None, content: str = None):
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()
        if title is not None:
            cursor.execute('UPDATE journal_entries SET title = ?, updated_at = ? WHERE id = ?', 
                          (title, now, entry_id))
        if content is not None:
            cursor.execute('UPDATE journal_entries SET content = ?, updated_at = ? WHERE id = ?', 
                          (content, now, entry_id))
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
            "A single card for daily reflection"
        )
        
        # Three card spread (line)
        db.add_spread(
            "Three Card Line",
            [
                {"x": 80, "y": 100, "label": "Past", "width": cw, "height": ch},
                {"x": 160, "y": 100, "label": "Present", "width": cw, "height": ch},
                {"x": 240, "y": 100, "label": "Future", "width": cw, "height": ch}
            ],
            "A simple past-present-future reading"
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
            "Five cards in a row"
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
            "A five card cross spread for deeper insight"
        )
        
        # Celtic Cross - compact layout
        db.add_spread(
            "Celtic Cross",
            [
                {"x": 140, "y": 130, "label": "Present", "width": cw, "height": ch},
                {"x": 140, "y": 130, "label": "Challenge", "width": ch, "height": cw, "rotated": True},
                {"x": 140, "y": 230, "label": "Foundation", "width": cw, "height": ch},
                {"x": 140, "y": 30, "label": "Crown", "width": cw, "height": ch},
                {"x": 50, "y": 130, "label": "Past", "width": cw, "height": ch},
                {"x": 230, "y": 130, "label": "Future", "width": cw, "height": ch},
                {"x": 330, "y": 240, "label": "Self", "width": cw, "height": ch},
                {"x": 330, "y": 160, "label": "Environment", "width": cw, "height": ch},
                {"x": 330, "y": 80, "label": "Hopes/Fears", "width": cw, "height": ch},
                {"x": 330, "y": 0, "label": "Outcome", "width": cw, "height": ch}
            ],
            "The classic 10-card Celtic Cross spread"
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
            "Simple three-card Lenormand line"
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
            "Five-card Lenormand line"
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
            "Nine-card Lenormand box spread"
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
            "Full 36-card Lenormand Grand Tableau"
        )


def create_default_decks(db: Database):
    """Import default decks if they exist and no decks have been added yet"""
    from import_presets import get_presets

    # Only import if no decks exist yet
    existing_decks = db.get_decks()
    if len(existing_decks) > 0:
        return

    # Get import presets instance
    presets = get_presets()

    # Define default decks to import
    default_decks = [
        {
            'name': 'Hello Tarot',
            'folder': 'Hello Tarot',
            'preset': 'Tarot (RWS Ordering)',
            'type': 'Tarot'
        },
        {
            'name': 'Rider-Waite-Smith',
            'folder': 'Rider-Waite-Smith',
            'preset': 'Tarot (RWS Ordering)',
            'type': 'Tarot'
        },
        {
            'name': 'Blue Owl Lenormand',
            'folder': 'Blue Owl Lenormand',
            'preset': 'Lenormand (36 cards)',
            'type': 'Lenormand'
        }
    ]

    for deck_info in default_decks:
        folder_path = Path(deck_info['folder'])

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

        # Import cards from folder
        valid_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
        cards_to_add = []

        for filepath in sorted(folder_path.iterdir()):
            if filepath.suffix.lower() in valid_extensions:
                # Map filename to card name using preset
                card_name = presets.map_filename_to_card(
                    filepath.name,
                    deck_info['preset']
                )

                # Get sort order
                sort_order = presets._get_card_sort_order(card_name)

                cards_to_add.append((card_name, str(filepath.absolute()), sort_order))

        # Sort by sort order and add to database
        cards_to_add.sort(key=lambda x: x[2])
        db.bulk_add_cards(deck_id, cards_to_add)
