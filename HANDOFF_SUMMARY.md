# Tarot Correspondences Import — Session Handoff Summary

## What Was Done

We imported correspondence data from "Tarot Correspondences" by T. Susan Chang into the `tarot_journal.db` SQLite database. The data covers all 78 Tarot cards (22 Major Arcana + 56 Minor Arcana) across 53 reference fields.

### Source Material

- **Book**: "Tarot Correspondences" by T. Susan Chang (Llewellyn Publications, 2018)
- **Format**: EPUB, parsed from HTML tables in `OEBPS/TC-14.xhtml`
- **Local copy**: `/sessions/pensive-sharp-einstein/tc.epub` (copied from `/sessions/pensive-sharp-einstein/mnt/tarot/tarot books/`)
- We originally tried parsing from a PDF but switched to the EPUB because the PDF had significant OCR artifacts. The EPUB gave dramatically cleaner data (704 → 1,501+ entries).

### Database Details

- **Database file**: `/sessions/pensive-sharp-einstein/mnt/tarot_journal/tarot_journal.db`
- **IMPORTANT**: This is a working copy. The user must manually copy it back to `~/Library/Application Support/TarotJournal/` when all work is done.
- **WAL checkpoint**: Always run `PRAGMA wal_checkpoint(TRUNCATE)` after commits.
- **Reference source**: `reference_sources` id = **9**, name = "Tarot Correspondences"

### Schema

- `card_archetypes` — id, name, cartomancy_type ('Tarot'), rank, suit, card_type
- `reference_sources` — id=9 for this book
- `source_fields` — 53 fields, ids 45–97 (listed below)
- `archetype_source_entries` — (archetype_id, field_id, content, updated_at), UNIQUE(archetype_id, field_id)

### Field IDs (source_id=9)

```
45: Conventional Card Numbering          (22 entries — Major Arcana only)
46: Conventional Card Title              (9 entries — only cards with alt names)
47: Alternative English Titles           (22 — Majors)
48: Romance Language Titles              (22 — Majors)
49: Hermetic Titles                      (78 — all cards)
50: Zodiacal Glyph                       (0 — visual glyphs, not text-extractable)
51: Planet, sign or element              (26)
52: Hebrew alphabet letter               (22 — Unicode Hebrew chars: א through ת)
53: Hebrew transliteration/pronunciation (22)
54: Type of letter                       (22 — Single, Double, or Mother)
55: English letter equivalent            (22)
56: Hebrew letter meanings               (22)
57: Number equivalent                    (62)
58: Gifts and attributes                 (22)
59: Gateways                             (22)
60: Sephirotic Path                      (22)
61: King Scale                           (22)
62: Queen Scale                          (22)
63: Prince Scale                         (22)
64: Princess Scale                       (22)
65: Animal                               (22)
66: Plant                                (22)
67: Perfume/Incense                      (22)
68: Gemstone/Metal                       (22)
69: Mythic figures                       (22)
70: Magical weapon                       (22)
71: Musical note                         (22)
72: Color Correspondence for Musical Note (21 — The Hermit is missing; epub omits it)
73: Dates                                (56)
74: Zodiacal major(s)                    (40)
75: Geometric forms of number            (40)
76: Number correspondences               (40)
77: Tree of life sephira                 (56)
78: Traditional meaning                  (40)
79: Tree of life world                   (55)
80: Color associated with Number/World   (40)
81: Type of deities associated with number (40)
82: Papus' dialectic                     (40)
83: Number significations                (40)
84: Planetary majors(s)                  (36)
85: Planet ruling decan                  (36)
86: Zodiac                               (36)
87: Decan image from the Picatrix        (36)
88: Decan signification from the Picatrix (36)
89: Decan image from Agrippa             (36)
90: Decan signification from Agrippa     (36)
91: Corresponding minors                 (16 — Court cards only)
92: Corresponding majors                 (16 — Court cards only)
93: Corresponding minors hermetic titles (18 — Courts + some pip cards)
94: Elemental title                      (16 — Court cards only)
95: Elemental glyph                      (0 — visual glyphs, not text-extractable)
96: Zodiacal decans                      (16 — Court cards only)
97: Zodiacal modality                    (12)
```

**Total entries**: 1,513 across 78 cards.

### Cleanup Performed

After the initial EPUB import, we did a comprehensive cleanup pass fixing ~50 stray text issues:

- **Hebrew letters**: Inserted all 22 as actual Unicode characters (field_id=52)
- **Garbled values**: Fixed Color Correspondence for Musical Note (Death, Chariot, Tower, World), Type of deities (Four of Cups, Ten of Swords, Nine of Pentacles), English letter equivalents (8+ cards), Hebrew transliteration (Hermit), and several others
- **Stray prefixes**: Removed garbage prefixes like "my ", "ma ", "am ", "i ", "# ", "Se) ", etc. from ~15 entries
- **Duplicated content**: Deduplicated card titles/numbering for Hierophant, Magician, High Priestess, Death, Strength
- **Field bleed**: Fixed Animal fields (High Priestess, Sun, World) that had Plant text appended; fixed Perfume/Incense fields that had Gemstone text leaked in; fixed Romance Language Titles that had Hermetic Titles appended
- **Swapped values**: Fixed Nine of Cups and Nine of Pentacles where Number equivalent and Geometric forms content was swapped
- **Invalid entries deleted**: Removed 10 Major Arcana entries that incorrectly had "Corresponding minors hermetic titles" (a Minor-only field)
- **Formatting**: Fixed double-dashes to proper em-dashes in degree notation, removed trailing stray characters

### Known Gaps

- **Zodiacal Glyph** (field 50) and **Elemental Glyph** (field 95): Zero entries. These are visual symbols in the book that don't survive text extraction.
- **The Hermit / Color Correspondence for Musical Note** (field 72): Missing. The epub table for The Hermit ends at "Musical note: F" without listing the corresponding color.
- **Conventional Card Title** (field 46): Only 9 entries. Most cards have their standard name as their only title, so entries were only created for cards with notable alternative names (Magician/Magus, Strength/Lust, etc.).

### Card Name Conventions

- The database uses **spelled-out numbers** for pip cards: "Two of Wands", not "2 of Wands"
- The database uses **Pentacles** for the earth suit; the book uses "Disks" (Thoth terminology). All "Disks" were mapped to "Pentacles" during import.
- Court card ranks: Page, Knight, Queen, King

### Files on Disk

- `/sessions/pensive-sharp-einstein/tc.epub` — local copy of the EPUB
- `/sessions/pensive-sharp-einstein/epub_parsed_v2.json` — JSON of all 78 cards parsed from EPUB (intermediate artifact)
- `/sessions/pensive-sharp-einstein/mnt/tarot_journal/tarot_journal.db` — the database with all imported data

### What's Left

The import is complete and cleaned. The user needs to copy the database back to its live location (`~/Library/Application Support/TarotJournal/`) when ready. If the user wants to fill in the two glyph fields (50, 95) or the Hermit's missing color correspondence, those would need to be done manually or from a different source.
