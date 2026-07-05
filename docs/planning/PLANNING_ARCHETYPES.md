# Archetypes Feature — Planning Document
*Decisions made in design review session, March 2026*

This document supersedes PLANNING_LANGUAGES.md. The Languages feature has been subsumed into the broader Archetypes feature described here.

The Archetypes feature is a per-card knowledge base living in the **Reference tab** (sidebar label: "Archetypes"). It provides a structured viewer for canonical card information that belongs to archetypes rather than specific decks — card images across decks, names in other languages, correspondences, freeform notes, and side-by-side deck comparison.

---

## Overview

Archetypes is a card-first reference tool. The user selects a card archetype once at the top level and navigates between sub-tabs to view different kinds of information about that card. Currently scoped to Tarot only, but structured for future expansion to other cartomancy types.

---

## Top-Level Persistent Controls

These controls sit above the sub-tabs and persist across all of them:

- **Cartomancy type selector** — Tarot only initially, but built in from the start so adding Lenormand etc. later requires no UI restructuring
- **Card archetype selector** — dropdown showing all archetypes for the selected type, sorted by card_order. Selecting a card here updates all sub-tabs simultaneously.

---

## Sub-Tabs

### 1. Image
View the selected card's image from any deck in the library that matches the selected cartomancy type.

- Deck selector dropdown (filtered to matching cartomancy type only)
- Card image displayed from the selected deck
- If no deck of the matching type exists in the library, show an appropriate prompt

### 2. Languages
Card names in multiple user-defined languages, with romanization and IPA support.

*For full data model and UI detail see the Languages section below.*

### 3. Correspondences
The selected card's correspondence values within a chosen correspondence system.

- Correspondence system selector dropdown
- Key values displayed inline — Element, Planet, Zodiac Sign, Decan, Astrological House, Modality, Kabbalah, Numerology, Rune, I Ching Hexagram, Chakra
- Fields that are blank for the selected card in the selected system are excluded from display
- Uses the SVG glyph library for visual correspondence values (see PLANNING_READING_BREAKDOWN.md)
- Read-only — editing correspondences is done via the Settings editor

### 4. Notes
Freeform per-card knowledge base. Flexible custom fields, source-attributed.

*For full data model and UI detail see the Notes section below.*

### 5. Compare
Side-by-side comparison of the same archetype across two different decks.

*For full data model and UI detail see the Compare section below.*

---

## Data Model

### Shared with other features
- Correspondence data — existing correspondence tables (see PLANNING_SUMMARY.md Section 3)
- Sources table — shared with Lenormand combinations (`lenormand_sources`). Consider renaming to `reference_sources` since it is now shared across multiple Reference features.

### New tables for Archetypes

**`archetype_card_types`**
Cartomancy type registry. Same concept as `language_reference_card_types` — these should be unified into a single shared table used across all Reference features.

| Column | Type | Notes |
|--------|------|-------|
| id | integer | PK |
| name | text | e.g. "Tarot", "Lenormand", "Kipper" |
| created_at | datetime | |

**`archetype_cards`**
Canonical card identities per cartomancy type. Same concept as `language_reference_archetypes` — these should also be unified.

| Column | Type | Notes |
|--------|------|-------|
| id | integer | PK |
| card_type_id | integer | FK → archetype_card_types |
| archetype_name | text | e.g. "The Moon", "Knight of Cups" |
| card_order | integer | For consistent sorting |
| created_at | datetime | |

**`archetype_language_languages`**
User-defined language list.

| Column | Type | Notes |
|--------|------|-------|
| id | integer | PK |
| name | text | e.g. "French", "Japanese", "Hebrew" |
| sort_order | integer | Controls column order in table mode |
| created_at | datetime | |

**`archetype_language_names`**
Card names in languages. Multiple entries per archetype+language combination.

| Column | Type | Notes |
|--------|------|-------|
| id | integer | PK |
| archetype_id | integer | FK → archetype_cards |
| language_id | integer | FK → archetype_language_languages |
| name | text | The card name in this language |
| romanization | text | Nullable — only displayed if populated |
| ipa | text | Nullable — only displayed if populated |
| sort_order | integer | Display order within archetype+language group |
| created_at | datetime | |

**`archetype_notes_field_defs`**
Field definitions for the Notes tab. Currently freeform per card — designed so this can be changed to per-type shared definitions in future without schema replacement.

| Column | Type | Notes |
|--------|------|-------|
| id | integer | PK |
| archetype_id | integer | FK → archetype_cards. Nullable in future if fields become shared across a type. |
| field_name | text | e.g. "Divinatory Meaning", "Symbolism", "Historical Context" |
| field_order | integer | Display order |
| created_at | datetime | |

**`archetype_notes_entries`**
Individual text entries within a notes field. Multiple entries per field, each optionally source-attributed.

| Column | Type | Notes |
|--------|------|-------|
| id | integer | PK |
| field_def_id | integer | FK → archetype_notes_field_defs |
| content | text | The note content |
| source_id | integer | FK → reference_sources, nullable |
| sort_order | integer | Display order within field |
| created_at | datetime | |

**`reference_sources`**
Shared sources table used across Reference features (Archetypes notes, Lenormand combinations). Rename from `lenormand_sources` if that table is built first, or build as `reference_sources` from the start.

| Column | Type | Notes |
|--------|------|-------|
| id | integer | PK |
| name | text | e.g. "Caitlín Matthews, The Complete Lenormand Oracle Handbook", "Personal notes" |
| created_at | datetime | |

---

## Languages Sub-Tab Detail

### Two viewing modes, toggled at the top of the sub-tab

**Card mode (default)**
- Names grouped by language — each language as a header, names listed beneath
- Romanization and IPA appear below each name if populated, visually subordinated
- Languages with no entries for the selected card are hidden
- "Edit" link deep-links to Settings editor with current card pre-selected

**Table mode**
- Rows are all card archetypes in card_order sequence
- Columns are languages in sort_order sequence
- Each cell shows all names stacked if multiples exist
- Romanization and IPA not shown inline — clicking/hovering a cell expands to show full detail
- "Edit" control per row deep-links to Settings editor with that card pre-selected

### Settings editor (Languages section)
Two sections:

**Languages list** — add, rename, delete, drag to reorder. Delete safety: warn with count of affected entries, require confirmation. Deleting a language deletes all its name entries.

**Names editor** — card-first interface mirroring Card mode layout. Per name entry: name field, optional romanization, optional IPA, drag handle, delete. "Add name" per language group. Collapsed language groups for languages with no entries for the current card.

### Empty states
- No languages defined → prompt to Settings
- No entries for selected card → prompt with link to add

### Future bulk import
Maps cleanly onto (archetype_name, language_name, name, romanization, ipa) — no schema changes required.

---

## Notes Sub-Tab Detail

### Viewer
Fields displayed in field_order sequence. Each field shows its name as a header, with entries listed beneath grouped by source. Unsourced entries appear at the bottom under "Other." Empty fields are hidden.

"Edit" link deep-links to Settings editor with current card and field pre-selected.

### Settings editor (Notes section)
Card-first interface. Selecting a card shows all defined fields for that card.

Per field:
- Field name (editable inline)
- Drag handle for reordering
- Delete field (with confirmation if entries exist)
- "Add entry" button

Per entry within a field:
- Text content field
- Optional source dropdown (references shared sources table)
- Drag handle for reordering within field
- Delete entry

"Add field" button at the card level.

### Sources management
Shared sources list managed in a dedicated section of Settings — not within the Notes editor itself. Same sources are used by Lenormand combinations. Add, edit, delete with same delete safety as Lenormand (warn if source has entries attached, offer to reassign or make unsourced).

### Freeform-to-structured migration path
Field definitions are currently per-card (archetype_id on field_def). To move to per-type shared fields in future: add a card_type_id column to `archetype_notes_field_defs`, make archetype_id nullable, and migrate existing field names to shared definitions. No data is lost. This should be kept in mind when building the editor so the UI can accommodate shared field definitions without a full rewrite.

---

## Compare Sub-Tab Detail

### What is compared
The same archetype across two different decks of the matching cartomancy type. Not two different archetypes.

### Layout
Two columns, side by side. Each column contains:
- Deck selector dropdown (filtered to matching cartomancy type)
- Card image from the selected deck
- Correspondence values inline (same display as Correspondences sub-tab) — fields blank in both cards are excluded; fields blank in only one card show blank for that column
- Notes fields — shown in parallel if the same field name exists on both, shown in a single column if unique to one card

### Interaction
Each deck selector is independent. Changing the card archetype at the top level updates both columns to show the new archetype from whichever decks were already selected.

---

## Notes for Implementation

- **CRITICAL SEQUENCING:** The unified archetype card types and archetype cards tables are a shared dependency for both this feature and Lenormand Combinations. The decision on table unification must be made and implemented before either feature is built. Do not build Lenormand Combinations with its own separate card type/archetype tables if Archetypes is also planned — they must share the same tables from the start.
- **CRITICAL SEQUENCING:** The sources table must be built as `reference_sources` from the start, shared across Archetypes notes and Lenormand combinations. If `lenormand_sources` is built first as part of Lenormand Combinations, rename it to `reference_sources` before Archetypes is implemented. Do not build two separate sources tables.
- The archetype card types and archetype cards tables serve the same conceptual purpose as equivalent tables being designed for the Languages feature. These should be a single unified set of tables used across all Reference features — not duplicated per feature.
- Tarot archetypes should be seeded at setup using the standard 78-card ordering. Users should not need to create them manually.
- The freeform-per-card notes structure is explicitly temporary — build the editor with the future migration to shared field definitions in mind.
- The Languages table mode column order follows `archetype_language_languages.sort_order`, controlled by drag reorder in Settings.
- All sub-tabs read the card selection from the persistent top-level selector. Sub-tab state (selected deck, selected correspondence system, selected language mode) is remembered per card per sub-tab between sessions.
- The Compare sub-tab has no Settings counterpart — it is view-only, deriving all its data from other features.
