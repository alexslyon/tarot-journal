# Tarot Journal — Design Planning Summary
*Decisions made in design review session, March 2026*

This document summarizes UI/UX and feature decisions made in a planning conversation. It is intended as a handoff to Claude Code for implementation. None of these changes have been implemented yet.

---

## 1. Navigation Restructure

### Current structure (7 flat tabs)
Library | Journal | Spreads | Profiles | Tags | Stats | Settings

### New structure (6 tabs)
**Library | Spreads | Journal | Reference | Insights | ⚙**

### Rationale per tab

**Library** — unchanged in purpose, first position signals it as a primary destination.

**Spreads** — elevated to top-level alongside Library. Spreads is both a designer *and* a reference viewer (users consult spread position meanings independently of journaling). It sits next to Library because both are collection/reference tabs — things you build up over time and browse.

**Journal** — unchanged in purpose, third position. Library and Spreads are the "what you have," Journal is "what you do with it."

**Reference** — new top-level tab for static cartomancy knowledge lookup. See Section 2 for contents.

**Insights** — replaces Stats. Renamed to signal purpose (reflection on practice over time, not just data). Positioned after Journal since it's derived from journal data.

**⚙ (Settings icon)** — absorbs Profiles and Tags management in addition to existing settings. These are administrative tasks that don't warrant top-level real estate. Using an icon rather than the word "Settings" de-emphasizes it visually without hiding it.

### What moves where
- Spreads → stays top-level (not moved into Journal)
- Profiles → moves into Settings
- Tags → moves into Settings
- Stats → becomes Insights tab

---

## 2. Reference Tab

A new top-level tab for general cartomancy knowledge lookups — objective structural knowledge about cartomancy systems, not interpretation.

### Planned sections (in order of priority)

**Correspondences** — read-only viewer for structured correspondence data (Element, Planet, Zodiac, Decan, Hebrew Letter). Shows assignments by card, by system, and cross-tradition comparisons. See Section 3 for the full correspondences feature.
- Must include a clearly visible "Edit Correspondences" link/button that deep-links directly to the correspondence editor in Settings (not just the top of Settings).

**Lenormand** — two sub-sections:
- Individual card meanings (with tradition variants — German vs French schools differ)
- Pair/combination meanings

**Card Names in Other Languages** — look up card names across languages. Data source will be the existing language-named custom fields (English Name, German Name, Italian Name, Spanish Name, JP Name) already present in some decks, plus future expansion.

**Numerology** — number meanings as they apply to tarot (cross-reference for serious readers).

### Explicitly excluded
Anything interpretive. Reference is for objective structural knowledge only.

### Future Reference candidates (not immediate)
- Suit and court card systems across traditions (subsumed into Correspondences viewer)
- Spread position meaning library (bridge to Spreads tab)

---

## 3. Correspondences Feature

This is the largest planned feature. It touches the data model, Settings, Reference, Library (deck editing), card editing, and eventually Stats/Insights.

### Concept
Structured correspondence data replaces the current freeform custom fields for astrological, elemental, and Kabbalistic card associations. The system is tradition-aware — different systems (RWS, Thoth, etc.) have different canonical assignments.

### Three-tier structure

**Tier 1 — Correspondence Systems (in Settings)**
Named systems (e.g. RWS, Thoth, Golden Dawn) each defining canonical assignments for card archetypes. Editable in Settings under a dedicated Correspondence Systems editor.

**Tier 2 — Deck-level system declaration (in deck editor)**
Each deck selects which correspondence system it follows. Cards in that deck inherit the canonical assignments from the selected system automatically — no manual entry required per card.

**Tier 3 — Card-level overrides (in card editor)**
Where an individual deck deviates from its declared system, the card can have values that override the inherited assignment.

### Structured fields (these become standard fields on every card)
- **Element** — Fire, Water, Air, Earth, Spirit
- **Planet** — Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn, Uranus, Neptune, Pluto
- **Zodiac Sign** — Aries through Pisces
- **Decan** — Planet-in-sign combinations (e.g. Jupiter in Libra). This is a Thoth/Golden Dawn level of specificity.
- **Hebrew Letter** — Aleph through Taw (22 letters, Major Arcana only)
- **Numerology** — Integer. 0–21 for Major Arcana, 1–10 for pips.
- **Rune** — Supports Elder Futhark (24 runes) and Anglo-Saxon Futhorc (28–33 runes) as separate selectable values within the same field. A card can be assigned a rune from either set, and both sets are always available.
- **I Ching Hexagram** — Integer 1–64, referencing the canonical hexagram numbering. Particularly relevant for I Ching decks but can be used as a correspondence for other deck types.

These are **no longer custom fields** — they are default standard fields on every card, blank unless populated by system inheritance or manual override.

### Derived associations
A Decan value automatically implies its Planet and Zodiac components. Example: "Jupiter in Libra" → also tagged as Jupiter (Planet) and Libra (Zodiac Sign). Stats/Insights can query at any level of specificity.

### Migration from existing custom fields
The following existing custom fields contain data that must be migrated automatically:
- `Astrology` (Antique Anatomy Tarot — 22 cards, Erotic Tarot of Manara — 37 cards)
- `Element` (Antique Anatomy Tarot — 22 cards)
- `Numerology` (Antique Anatomy Tarot — 22 cards)
- `Sign` (Oracle of the Radiant Sun — 24 cards) → maps to Zodiac Sign

**Migration rules:**
- Plain zodiac values (e.g. "Aquarius") → map to Zodiac Sign
- Plain planet values (e.g. "Jupiter") → map to Planet
- Plain element values (e.g. "Fire", "Water") → map to Element
- Planet-in-sign values (e.g. "Jupiter in Libra") → map to Decan AND derive Planet and Zodiac Sign
- Values that also contain element-like words (e.g. "Air") in the Astrology field → map to Element
- Anything that doesn't cleanly parse → flag for manual review, do not silently drop

After successful migration, the old custom fields (Astrology, Element, Numerology, Sign) are removed from the decks they were defined on.

### Reference tab connection
The Correspondences section in Reference is a **read-only view** of the same data managed in Settings. It should support:
- View by card (show all correspondences for The Moon)
- View by system (show full elemental table for RWS)
- View by tradition comparison (show how Thoth differs from RWS across all cards)

The "Edit Correspondences" escape hatch in Reference must deep-link to the correct section in Settings.

---

## 4. Insights Tab (renamed from Stats)

Renamed from Stats to Insights to signal purpose. Contents largely unchanged for now, but the Correspondences feature will unlock new query types:

**New queries enabled by structured correspondences:**
- Element distribution across a time period
- Zodiac sign frequency across readings
- Planet frequency with specific querents
- Time-of-day patterns correlated with planetary assignments
- Elemental shifts across seasons

These are not immediate implementation work — they depend on the Correspondences data model being in place first.

---

## 5. Keywords — Decision Deferred

The `Keywords` custom field is set up on 18 decks and partially populated. It has potential as a queryable tag-like structure (a controlled vocabulary applied across decks) rather than freeform text. This decision is intentionally deferred — it is not part of the current implementation scope but should be revisited after the Correspondences work is complete.

---


---

## 7. Anki Export Feature

Export a deck in a format that can be directly imported into Anki. The user handles Anki note type creation themselves — the app just needs to produce a clean, correctly formatted import package.

### Trigger
A button in the deck edit modal alongside the existing JSON export option, labelled "Export for Anki."

### Export modal
A checklist of every available field for that specific deck, in the following order:

**Always present:**
- Card image
- Card name

**If populated for the deck:**
- Each correspondence field (Element, Planet, Zodiac Sign, Decan, Hebrew Letter, Numerology, Rune, I Ching Hexagram) — each as its own separate column
- Keywords
- Notes
- Any custom fields defined for the deck

Fields should be **reorderable by drag** within the checklist. Column order in the export matches the order selected here, which is how Anki maps columns to note type fields.

### Output format
A zip file containing:
- A tab-separated `.txt` file with one row per card
- All card images flat in the same folder, full size, with filenames matching the image references in the txt file

### txt file format
- First line: `#separator:tab`
- Second line: `#html:true`
- Third line: `#notetype column:` (optional, can be omitted if user handles this in Anki)
- Optional header row with field names, prefixed with `#` so Anki skips it as a comment — useful reference when setting up the note type in Anki
- One row per card, tab-separated, image column uses `<img src="filename.jpg">` syntax

### Scope
One deck at a time only. No reversed card handling.

### Implementation note
Column count and order must exactly match the user's Anki note type field definitions — the app has no way to enforce this, but the optional commented header row helps the user verify the match before importing.

These changes are not all immediate — they are in rough priority order:

## 8. Implementation Order

1. **Navigation restructure** — TabNav reorganization. Relatively straightforward, high visible impact.
2. **Settings reorganization** — Move Profiles and Tags management into Settings.
3. **Correspondences data model** — New tables, standard card fields, system/deck/card-level structure. Do this on its own branch. Get the schema right before writing UI.
4. **Migration script** — Parse and migrate existing Astrology/Element/Numerology/Sign custom field data.
5. **Correspondences UI** — Settings editor, deck-level selector, card-level override fields.
6. **Reference tab** — Correspondences viewer with deep-link back to Settings editor. Lenormand sections and Card Names sections to follow.
7. **Insights enhancements** — Correspondence-based queries once data model is in place.
8. **Anki export** — Depends on Correspondences being in place so correspondence fields are available for export selection.

---

## Notes for Implementation

- The Correspondences data model change is the most consequential. Schema mistakes are expensive. Review carefully before writing any migration code.
- The migration script should be non-destructive — flag unparseable values rather than dropping them.
- The old custom fields should only be removed *after* migration is verified as complete and correct.
- The Correspondences feature warrants its own git branch before any code is written.
