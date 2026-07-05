# Lenormand Combinations Feature — Planning Document
*Decisions made in design review session, March 2026*

This document covers the design and data model for the Lenormand card combinations reference feature. It is intended as a handoff to Claude Code for implementation.

---

## Overview

A reference feature allowing the user to look up meanings for any ordered pair of Lenormand cards, with meanings sourced from multiple books, websites, or personal notes. Lives in the **Reference tab** with its editing interface in **Settings**, following the same pattern as the Correspondences feature.

---

## Key Constraints

- Lenormand has 36 cards, identified canonically by number (1–36).
- Combinations are **non-commutative** — Dog+Ring and Ring+Dog are distinct and must be stored and displayed separately.
- Same-card pairs (e.g. Dog+Dog) are excluded entirely.
- Maximum possible combinations: 36 × 35 = **1,260**.
- Combination records are only created when at least one meaning exists — no empty placeholder rows.
- Card names and images are always derived at display time from the user's selected default Lenormand deck, never stored in the combinations data.

---

## Data Model

### Table: `lenormand_sources`
Reusable source labels, defined once and referenced across many meaning entries.

| Column | Type | Notes |
|--------|------|-------|
| id | integer | PK |
| name | text | e.g. "Caitlín Matthews, *The Complete Lenormand Oracle Handbook*", "LearnLenormand.com", "Personal notes" |
| created_at | datetime | |

### Table: `lenormand_combinations`
Represents an ordered card pair. No meanings stored here — it is purely the pair identifier.

| Column | Type | Notes |
|--------|------|-------|
| id | integer | PK |
| card_1 | integer | Canonical Lenormand card number, 1–36 |
| card_2 | integer | Canonical Lenormand card number, 1–36 |
| | | UNIQUE constraint on (card_1, card_2) |
| | | CHECK constraint: card_1 ≠ card_2 |

### Table: `lenormand_meanings`
Individual meaning entries for a combination. Multiple meanings per combination are supported, each with an optional source.

| Column | Type | Notes |
|--------|------|-------|
| id | integer | PK |
| combination_id | integer | FK → lenormand_combinations |
| meaning | text | The meaning text |
| source_id | integer | FK → lenormand_sources, nullable (unsourced meanings are valid) |
| sort_order | integer | Controls display order within a combination |
| created_at | datetime | |

### Why this supports future bulk import
The structure maps directly onto a CSV of (card_1_number, card_2_number, meaning, source_name). A future import script can parse that format and insert rows without any schema changes. No redesign required.

---

## Reference Tab Viewer

### Layout
- Two dropdowns side by side, each showing card number + name (e.g. "3 · Ship")
- Card image from the default Lenormand deck displayed below each dropdown
- If no default Lenormand deck is set in Settings, display a prompt to set one rather than silently showing no images

### Meanings display
Meanings are grouped by source, each source rendered as a small header with its meanings listed beneath. Unsourced meanings appear at the bottom under a generic "Other" group.

If no meanings exist for the selected combination:
- Display a message indicating no meanings have been entered yet
- Display a direct link that deep-links to the Settings editor with that combination pre-selected

### Deep-link to editor
A clearly visible "Edit this combination" link opens the Settings editor with the same two cards already selected, following the same pattern as the Correspondences Reference viewer.

---

## Settings Editor

Two sections within a dedicated Lenormand Combinations area in Settings.

### Section 1: Sources
A simple managed list of source definitions.
- Add, edit, delete sources
- **Delete safety:** if a source has meanings attached to it, warn the user and offer to either reassign those meanings to another source or make them unsourced — never silently delete meanings

### Section 2: Combinations
Uses the same two-dropdown interface as the Reference viewer. Selecting a combination displays an editable list of meanings for that pair.

Per meaning entry:
- Text field for the meaning
- Optional source dropdown (references Sources list)
- Drag handle for reordering within the combination
- Delete control

Controls at the combination level:
- "Add meaning" button

The editing experience deliberately mirrors the viewing experience — same layout, same card selection interface, just with edit controls added. This makes the editor intuitive to use and consistent with the viewer.

The deep-link from the Reference viewer lands here with the same card pair already selected.

---

## Notes for Implementation

- Card numbers (1–36) are the stable identifier throughout — names and images are always looked up at display time from the selected default Lenormand deck, never stored in this feature's tables.
- The default Lenormand deck is set in Settings (existing app settings mechanism). If unset, the viewer should degrade gracefully with a prompt rather than breaking.
- The non-commutative constraint is enforced by the data model (ordered pair, unique constraint) and must also be clear in the UI — the order of the two dropdowns must be visually unambiguous (e.g. labelled "Card 1" and "Card 2", or "First card" and "Second card").
- Sort order on meanings should default to insertion order and be adjustable by drag.
- Future bulk import (CSV or similar) is explicitly in scope as a future feature. The data model is designed to support it without schema changes.
