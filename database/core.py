"""
Database core: initialization, migrations, and transaction management.
"""

import atexit
import sqlite3
import threading
from contextlib import contextmanager

from logger_config import get_logger
from app_config import get_config

logger = get_logger('database')
_cfg = get_config()


class CoreMixin:
    """Base mixin providing database initialization and transaction support."""

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = _cfg.get("paths", "database", "tarot_journal.db")
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._in_transaction = False

        # Thread safety: RLock allows the same thread to acquire multiple times
        # (important because DB methods call other DB methods)
        self._lock = threading.RLock()

        # WAL mode: allows reads during writes and protects against
        # data corruption if the app crashes mid-write
        self.conn.execute('PRAGMA journal_mode=WAL')

        # Enable foreign key enforcement so CASCADE deletes work properly
        # (SQLite has this OFF by default, which can leave orphaned records)
        self.conn.execute('PRAGMA foreign_keys = ON')

        self._create_tables()

        # Ensure the connection is closed if the app exits unexpectedly
        atexit.register(self.close)

    def _commit(self):
        """Commit unless inside a managed transaction (which commits at the end).

        Thread-safe: acquires lock before committing.
        """
        if not self._in_transaction:
            with self._lock:
                self.conn.commit()

    @contextmanager
    def transaction(self):
        """Wrap multiple operations in a single atomic transaction.

        If anything fails, all changes since the start are rolled back
        so the database never ends up in a half-finished state.

        Thread-safe: holds lock for entire transaction duration.
        """
        with self._lock:
            self._in_transaction = True
            try:
                yield
                self.conn.commit()
            except Exception:
                self.conn.rollback()
                raise
            finally:
                self._in_transaction = False

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
                image_folder TEXT,
                suit_names TEXT,
                court_names TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

        # Migration: add deck_slots column for multi-deck spreads
        if 'deck_slots' not in columns:
            cursor.execute('ALTER TABLE spreads ADD COLUMN deck_slots TEXT')

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

        # Card groups (per-deck custom groupings)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS card_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                deck_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                color TEXT DEFAULT '#6B5B95',
                FOREIGN KEY (deck_id) REFERENCES decks(id) ON DELETE CASCADE,
                UNIQUE(deck_id, name)
            )
        ''')

        # Card group assignments junction table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS card_group_assignments (
                card_id INTEGER NOT NULL,
                group_id INTEGER NOT NULL,
                PRIMARY KEY (card_id, group_id),
                FOREIGN KEY (card_id) REFERENCES cards(id) ON DELETE CASCADE,
                FOREIGN KEY (group_id) REFERENCES card_groups(id) ON DELETE CASCADE
            )
        ''')

        # Migration: add sort_order to card_groups
        cursor.execute('PRAGMA table_info(card_groups)')
        columns = [col[1] for col in cursor.fetchall()]
        if 'sort_order' not in columns:
            cursor.execute('ALTER TABLE card_groups ADD COLUMN sort_order INTEGER DEFAULT 0')
            # Initialize sort_order for existing groups based on name order
            cursor.execute('SELECT id, deck_id FROM card_groups ORDER BY deck_id, name')
            rows = cursor.fetchall()
            current_deck = None
            pos = 0
            for row in rows:
                if row[1] != current_deck:
                    current_deck = row[1]
                    pos = 0
                cursor.execute('UPDATE card_groups SET sort_order = ? WHERE id = ?', (pos, row[0]))
                pos += 1

        # Deck type assignments junction table (allows decks to have multiple types)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS deck_type_assignments (
                deck_id INTEGER NOT NULL,
                type_id INTEGER NOT NULL,
                PRIMARY KEY (deck_id, type_id),
                FOREIGN KEY (deck_id) REFERENCES decks(id) ON DELETE CASCADE,
                FOREIGN KEY (type_id) REFERENCES cartomancy_types(id) ON DELETE CASCADE
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

        # Migration: add querent_only and hidden columns to profiles
        cursor.execute('PRAGMA table_info(profiles)')
        profile_columns = [col[1] for col in cursor.fetchall()]
        if 'querent_only' not in profile_columns:
            cursor.execute('ALTER TABLE profiles ADD COLUMN querent_only INTEGER DEFAULT 0')
        if 'hidden' not in profile_columns:
            cursor.execute('ALTER TABLE profiles ADD COLUMN hidden INTEGER DEFAULT 0')

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

        # Entry querents junction table (allows entries to have multiple querents)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS entry_querents (
                entry_id INTEGER NOT NULL,
                profile_id INTEGER NOT NULL,
                position INTEGER DEFAULT 0,
                PRIMARY KEY (entry_id, profile_id),
                FOREIGN KEY (entry_id) REFERENCES journal_entries(id) ON DELETE CASCADE,
                FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE
            )
        ''')

        # Migrate existing querent_id values to entry_querents table
        cursor.execute('SELECT COUNT(*) FROM entry_querents')
        if cursor.fetchone()[0] == 0:
            cursor.execute('''
                INSERT OR IGNORE INTO entry_querents (entry_id, profile_id, position)
                SELECT id, querent_id, 0 FROM journal_entries
                WHERE querent_id IS NOT NULL
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

        # Migration: populate junction table from legacy cartomancy_type_id, then drop column
        cursor.execute("PRAGMA table_info(decks)")
        deck_columns = [col[1] for col in cursor.fetchall()]
        if 'cartomancy_type_id' in deck_columns:
            # Ensure all decks have junction table entries before dropping
            cursor.execute('''
                INSERT OR IGNORE INTO deck_type_assignments (deck_id, type_id)
                SELECT id, cartomancy_type_id FROM decks
                WHERE cartomancy_type_id IS NOT NULL
            ''')
            # Can't use ALTER TABLE DROP COLUMN because the column has a FK constraint.
            # Rebuild the table without the column instead.
            cursor.execute('''
                CREATE TABLE decks_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    image_folder TEXT,
                    suit_names TEXT,
                    court_names TEXT,
                    date_published TEXT,
                    publisher TEXT,
                    credits TEXT,
                    notes TEXT,
                    card_back_image TEXT,
                    booklet_info TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            # Copy all non-legacy columns
            cursor.execute('''
                INSERT INTO decks_new (id, name, image_folder, suit_names, court_names,
                    date_published, publisher, credits, notes, card_back_image, booklet_info, created_at)
                SELECT id, name, image_folder, suit_names, court_names,
                    date_published, publisher, credits, notes, card_back_image, booklet_info, created_at
                FROM decks
            ''')
            # Must disable FK checks to drop a table referenced by other tables.
            # PRAGMA foreign_keys only takes effect outside transactions.
            self.conn.commit()
            self.conn.execute('PRAGMA foreign_keys = OFF')
            cursor.execute('DROP TABLE decks')
            cursor.execute('ALTER TABLE decks_new RENAME TO decks')
            self.conn.commit()
            self.conn.execute('PRAGMA foreign_keys = ON')

        # Migration: recreate correspondence tables if CHECK constraint is missing 'chakra'
        # or if source_group column is missing (needed for multi-value support)
        cursor.execute("SELECT sql FROM sqlite_master WHERE name='correspondence_assignments'")
        row = cursor.fetchone()
        needs_recreate = False
        if row:
            existing_sql = row[0] or ''
            if ('chakra' not in existing_sql
                    or 'source_group' not in existing_sql
                    or 'modality' not in existing_sql):
                needs_recreate = True
        if needs_recreate:
            cursor.execute('SELECT * FROM correspondence_assignments')
            saved_assignments = [dict(r) for r in cursor.fetchall()]
            cursor.execute('SELECT * FROM card_correspondence_overrides')
            saved_overrides = [dict(r) for r in cursor.fetchall()]
            cursor.execute('DROP TABLE IF EXISTS correspondence_assignments')
            cursor.execute('DROP TABLE IF EXISTS card_correspondence_overrides')
            self._needs_corr_restore = (saved_assignments, saved_overrides)

        # Correspondence systems (RWS, Thoth, Golden Dawn, user-defined)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS correspondence_systems (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                is_builtin INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # System-level correspondence assignments.
        # Multiple rows per (system, archetype, field) allowed — each tagged with
        # source_group so a card can have multiple values contributed by different
        # bulk groups (e.g. Page of Wands gets Fire from "Wands" and Earth from "Pages").
        # source_group IS NULL means an individual cell edit (not from a bulk group).
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS correspondence_assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                system_id INTEGER NOT NULL,
                archetype_id INTEGER NOT NULL,
                field_name TEXT NOT NULL CHECK(field_name IN (
                    'element', 'planet', 'zodiac_sign', 'decan',
                    'hebrew_letter', 'numerology', 'rune', 'i_ching_hexagram',
                    'chakra', 'modality'
                )),
                field_value TEXT NOT NULL,
                source_group TEXT,
                FOREIGN KEY (system_id) REFERENCES correspondence_systems(id) ON DELETE CASCADE,
                FOREIGN KEY (archetype_id) REFERENCES card_archetypes(id) ON DELETE CASCADE
            )
        ''')
        # Both NULL and non-NULL source groups can contribute multiple values
        # per cell (e.g. a manual edit can pick multiple zodiac signs). Unique
        # indexes include field_value so we only prevent exact duplicates.
        cursor.execute('DROP INDEX IF EXISTS idx_corr_assignments_unique_manual')
        cursor.execute('''
            CREATE UNIQUE INDEX IF NOT EXISTS idx_corr_assignments_unique_manual_value
            ON correspondence_assignments(system_id, archetype_id, field_name, field_value)
            WHERE source_group IS NULL
        ''')
        cursor.execute('DROP INDEX IF EXISTS idx_corr_assignments_unique_group')
        cursor.execute('''
            CREATE UNIQUE INDEX IF NOT EXISTS idx_corr_assignments_unique_group_value
            ON correspondence_assignments(system_id, archetype_id, field_name, source_group, field_value)
            WHERE source_group IS NOT NULL
        ''')

        # Card-level correspondence overrides (individual cards deviating from deck's system)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS card_correspondence_overrides (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                card_id INTEGER NOT NULL,
                field_name TEXT NOT NULL CHECK(field_name IN (
                    'element', 'planet', 'zodiac_sign', 'decan',
                    'hebrew_letter', 'numerology', 'rune', 'i_ching_hexagram',
                    'chakra', 'modality'
                )),
                field_value TEXT,
                FOREIGN KEY (card_id) REFERENCES cards(id) ON DELETE CASCADE,
                UNIQUE(card_id, field_name)
            )
        ''')

        # Migration: recreate field options table if CHECK constraint is missing 'modality'
        cursor.execute("SELECT sql FROM sqlite_master WHERE name='correspondence_field_options'")
        fo_row = cursor.fetchone()
        if fo_row and 'modality' not in (fo_row[0] or ''):
            cursor.execute('SELECT * FROM correspondence_field_options')
            saved_options = [dict(r) for r in cursor.fetchall()]
            cursor.execute('DROP TABLE IF EXISTS correspondence_field_options')
            self._needs_options_restore = saved_options

        # Correspondence field options: the allowed values for each correspondence field
        # (Element, Planet, Zodiac, etc). Global list, shared across all systems.
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS correspondence_field_options (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                field_name TEXT NOT NULL CHECK(field_name IN (
                    'element', 'planet', 'zodiac_sign', 'decan',
                    'hebrew_letter', 'numerology', 'rune', 'i_ching_hexagram',
                    'chakra', 'modality'
                )),
                option_value TEXT NOT NULL,
                sort_order INTEGER DEFAULT 0,
                UNIQUE(field_name, option_value)
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_corr_field_options_field ON correspondence_field_options(field_name, sort_order)')

        # Migration: add correspondence_system_id to decks
        cursor.execute("PRAGMA table_info(decks)")
        deck_cols = [col[1] for col in cursor.fetchall()]
        if 'correspondence_system_id' not in deck_cols:
            cursor.execute('''
                ALTER TABLE decks ADD COLUMN correspondence_system_id
                INTEGER REFERENCES correspondence_systems(id)
            ''')

        # Indexes for commonly queried foreign keys and search columns.
        # These speed up filtering, joining, and sorting as data grows.
        # "IF NOT EXISTS" means they're safe to run every startup.
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_cards_deck_id ON cards(deck_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_cards_card_order ON cards(deck_id, card_order)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_entry_readings_entry_id ON entry_readings(entry_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_entry_tags_entry_id ON entry_tags(entry_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_entry_tags_tag_id ON entry_tags(tag_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_deck_tag_assignments_deck_id ON deck_tag_assignments(deck_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_card_tag_assignments_card_id ON card_tag_assignments(card_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_card_group_assignments_card_id ON card_group_assignments(card_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_card_group_assignments_group_id ON card_group_assignments(group_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_card_groups_deck_id ON card_groups(deck_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_deck_type_assignments_deck_id ON deck_type_assignments(deck_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_follow_up_notes_entry_id ON follow_up_notes(entry_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_entry_querents_entry_id ON entry_querents(entry_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_journal_entries_created_at ON journal_entries(created_at DESC)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_card_custom_fields_card_id ON card_custom_fields(card_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_deck_custom_fields_deck_id ON deck_custom_fields(deck_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_corr_assignments_system ON correspondence_assignments(system_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_corr_assignments_archetype ON correspondence_assignments(archetype_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_corr_assignments_field ON correspondence_assignments(field_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_card_corr_overrides_card ON card_correspondence_overrides(card_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_decks_corr_system ON decks(correspondence_system_id)')

        # Restore correspondence data after CHECK constraint migration
        if hasattr(self, '_needs_corr_restore'):
            saved_assignments, saved_overrides = self._needs_corr_restore
            # Temporarily disable FK checks — the referenced rows exist but
            # the table was just recreated so SQLite needs this
            self.conn.commit()
            self.conn.execute('PRAGMA foreign_keys = OFF')
            for a in saved_assignments:
                # Preserve existing source_group if present, else default to NULL
                source_group = a.get('source_group')
                cursor.execute('''
                    INSERT OR IGNORE INTO correspondence_assignments
                        (system_id, archetype_id, field_name, field_value, source_group)
                    VALUES (?, ?, ?, ?, ?)
                ''', (a['system_id'], a['archetype_id'], a['field_name'], a['field_value'], source_group))
            for o in saved_overrides:
                cursor.execute('''
                    INSERT OR IGNORE INTO card_correspondence_overrides
                        (card_id, field_name, field_value)
                    VALUES (?, ?, ?)
                ''', (o['card_id'], o['field_name'], o['field_value']))
            self.conn.commit()
            self.conn.execute('PRAGMA foreign_keys = ON')
            del self._needs_corr_restore

        # Restore field options after CHECK constraint migration
        if hasattr(self, '_needs_options_restore'):
            for o in self._needs_options_restore:
                cursor.execute('''
                    INSERT OR IGNORE INTO correspondence_field_options
                        (field_name, option_value, sort_order)
                    VALUES (?, ?, ?)
                ''', (o['field_name'], o['option_value'], o['sort_order']))
            del self._needs_options_restore

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

        # Seed correspondence systems if table is empty
        cursor.execute('SELECT COUNT(*) FROM correspondence_systems')
        if cursor.fetchone()[0] == 0:
            from database.correspondence_seed import seed_rws_correspondences
            seed_rws_correspondences(cursor)

        # One-time migration: rename legacy source_group labels (remove "All " prefix)
        if self.get_setting('source_group_label_migration_done') != 'true':
            legacy_rename = {
                'All Minor Arcana': 'Minor Arcana',
                'All Pages': 'Pages',
                'All Knights': 'Knights',
                'All Queens': 'Queens',
                'All Kings': 'Kings',
                'All Aces': 'Aces',
                'All Twos': 'Twos',
                'All Threes': 'Threes',
                'All Fours': 'Fours',
                'All Fives': 'Fives',
                'All Sixes': 'Sixes',
                'All Sevens': 'Sevens',
                'All Eights': 'Eights',
                'All Nines': 'Nines',
                'All Tens': 'Tens',
                'All Pips (Ace-10)': 'Pips (Ace-10)',
                'All Court Cards': 'Court Cards',
            }
            for old, new in legacy_rename.items():
                cursor.execute(
                    'UPDATE correspondence_assignments SET source_group = ? WHERE source_group = ?',
                    (new, old)
                )
            self.set_setting('source_group_label_migration_done', 'true')

        # Seed correspondence field options if table is empty, or if modality is missing
        cursor.execute('SELECT COUNT(*) FROM correspondence_field_options')
        total_options = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM correspondence_field_options WHERE field_name = 'modality'")
        modality_count = cursor.fetchone()[0]
        if total_options == 0 or modality_count == 0:
            from database.correspondence_seed import seed_field_options
            seed_field_options(cursor)

        # One-time migration: upgrade plain-numeric I Ching options to "N ䷀ Name" format.
        # Renames cascade to correspondence_assignments / card_correspondence_overrides.
        if self.get_setting('i_ching_hexagram_format_migration_done') != 'true':
            from database.correspondence_seed import I_CHING_HEXAGRAMS
            for i, new_value in enumerate(I_CHING_HEXAGRAMS, start=1):
                old_value = str(i)
                # Skip if the option is already in the new format
                cursor.execute(
                    "SELECT id, option_value FROM correspondence_field_options WHERE field_name = 'i_ching_hexagram' AND option_value = ?",
                    (old_value,)
                )
                row = cursor.fetchone()
                if not row:
                    continue
                opt_id = row['id']
                # Rename the option
                cursor.execute(
                    'UPDATE correspondence_field_options SET option_value = ? WHERE id = ?',
                    (new_value, opt_id)
                )
                # Cascade to assignments + overrides
                cursor.execute(
                    "UPDATE correspondence_assignments SET field_value = ? WHERE field_name = 'i_ching_hexagram' AND field_value = ?",
                    (new_value, old_value)
                )
                cursor.execute(
                    "UPDATE card_correspondence_overrides SET field_value = ? WHERE field_name = 'i_ching_hexagram' AND field_value = ?",
                    (new_value, old_value)
                )
            self.set_setting('i_ching_hexagram_format_migration_done', 'true')

        self._commit()

        # Run one-time correspondence field migration (after commit so tables exist)
        from database.correspondence_migration import run_correspondence_migration
        run_correspondence_migration(self)

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

    def close(self):
        """Close the database connection (safe to call more than once)."""
        if self.conn:
            try:
                self.conn.execute('PRAGMA wal_checkpoint(TRUNCATE)')
                self.conn.close()
            except Exception as e:
                logger.debug("Error closing database connection: %s", e)
            self.conn = None
