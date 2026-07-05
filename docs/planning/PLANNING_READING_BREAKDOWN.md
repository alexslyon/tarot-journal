# Reading Breakdown Feature — Planning Document
*Decisions made in design review session, March 2026*

This document covers the design of the Reading Breakdown feature — an automatically generated table within journal entries showing the distribution of suits, ranks, and correspondences across the cards in a reading. It depends on the Correspondences feature being implemented first.

---

## Overview

A toggleable breakdown table embedded in the journal entry viewer, showing how many cards of each suit, rank, and correspondence type appear in the reading. Toggle state and visible correspondence selection are remembered per entry.

**Initial implementation uses text labels for all values.** Glyphs (SVG and Unicode) will be added in a later pass once the SVG Glyph Library is complete. The table structure and data model are the same regardless of whether values are displayed as text or glyphs — swapping in glyphs later is purely a rendering change with no data or structural impact.

---

## Dependencies

- **Correspondences feature must be implemented first** — the breakdown reads structured correspondence data assigned to cards. Without that data model in place this feature has nothing to query.

---

## Placement in Entry Viewer

A "Reading Breakdown" toggle button in the entry viewer header area. When expanded, the breakdown sits between the spread display and the journal text content.

If the entry has **multiple readings**, a row of tabs appears at the top of the breakdown:
- One tab per reading, labelled by spread name
- An "All Readings" aggregate tab showing combined totals across all readings

The last-viewed tab is remembered per entry alongside the correspondence toggle states.

---

## Table Structure

Each category gets its own row. Columns are the distinct values found in the reading, sorted by count descending. Only values actually present in the reading appear as columns.

**Suits and Ranks** appear as the first rows.

**Correspondence rows** appear below. Only correspondence types that are actually present in the reading appear — if no I Ching hexagrams are assigned to any card in the reading, that row is entirely absent.

### Correspondence rows — initial text display

All values displayed as text labels in the initial implementation.

| Correspondence | Initial Display | Future Glyph Plan |
|---|---|---|
| Element | Text name (e.g. "Fire", "Water", "Aether") | SVG — alchemical symbols |
| Planet | Text name (e.g. "Mars", "Selene", "Lilith (Dark Moon)") | SVG — all bodies. **The two Liliths must have distinct display names.** |
| Zodiac Sign | Text name (e.g. "Aries", "Pisces") | SVG |
| Decan | Text pair (e.g. "Jupiter in Libra") | Composite SVG — Planet + Zodiac side by side |
| Astrological House | Roman numeral (e.g. "I", "XII") | SVG — styled Roman numerals |
| Modality | Text name (e.g. "Cardinal", "Fixed") | Stays as text |
| Kabbalah | Text name (e.g. "Aleph", "Beth") | Unicode Hebrew letters |
| Numerology | Plain integer | Stays as text |
| Rune | Text name (e.g. "Fehu", "Uruz") | Unicode rune characters |
| I Ching Hexagram | Number + name (e.g. "1 · Qian") | Unicode hexagram characters |
| Chakra | Text name (e.g. "Root", "Heart") | SVG |

---

## Toggle UI

A small filter/configure icon in the breakdown header opens a popover containing:
- A checklist of all correspondence types **present in this reading** (absent types are not listed)
- An "All" / "None" bulk toggle at the top
- Individual toggles per correspondence type

Toggle state is saved per entry automatically on change, using the same debounced autosave pattern already in use for profiles. State persists between sessions.

---

## Future: SVG Glyph Library

**Not required for initial implementation.** When built, a dedicated shared asset library in the frontend — SVG components, one per symbol — usable across the entire app wherever glyphs appear (Reading Breakdown, Correspondences Reference viewer, card editing, Insights charts). Build once, use everywhere.

### Three tiers (for future reference)

**Tier 1 — Unicode (styled span, consistent font):**
- Hebrew Letters (Kabbalah)
- Runes (Elder Futhark + Anglo-Saxon Futhorc)
- I Ching Hexagrams

**Tier 2 — SVG (symbols where Unicode exists but rendering is unreliable or visually unsatisfactory):**
- Zodiac Signs
- Elements (alchemical symbols)

**Tier 3 — SVG (no Unicode coverage, or Unicode exists but SVG used for consistency):**
- Planets — all bodies use SVG for visual consistency. Full enumerated list:
  - *Traditional:* Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn, Uranus, Neptune, Pluto
  - *Lunar points:* Ascending Lunar Node, Descending Lunar Node, Selene, Lilith (Dark Moon / Black Moon Lilith)
  - *Asteroids and minor bodies:* Chiron, Ceres, Juno, Vesta, Pallas Athena, Lilith (Asteroid), Hygeia, Eris, Psyche, Eros
  - **The two Liliths — Black Moon Lilith and Asteroid Lilith — are different bodies and must have distinct glyphs and unambiguous display names throughout the UI**
  - **Adding new bodies:** add one entry to a central planet registry (constants file or JSON) and one SVG component. No other changes required.
- Chakras
- Astrological Houses (Roman numerals in consistent styled form)

### Glyph implementation notes (for when glyphs are added)
- SVG components should accept a `size` prop and inherit color from CSS variables so they theme correctly with the rest of the app
- Decan glyphs are composite — render the Planet SVG and Zodiac SVG side by side with a small separator, not a single combined glyph
- The glyph library should be documented internally so future features can use it without reinventing anything
- Swapping text labels for glyphs is a rendering-only change — no data model or structural changes required

---

## Notes for Implementation

- The breakdown is read-only — it derives entirely from card correspondence data, it does not allow editing from within the entry viewer
- Cards with no correspondence data for a given field are silently excluded from that row's count — no "unassigned" column
- The "All Readings" aggregate tab sums counts across all readings in the entry, so a card appearing in two readings counts twice
- Toggle state and last-viewed tab are stored in a per-entry settings structure — consider whether this lives in the `journal_entries` table as a JSON column or in `app_settings` keyed by entry ID. A JSON column on `journal_entries` is probably cleaner.
- Modality may be revised out of the correspondences system in future — the breakdown table should handle its absence gracefully if that happens
- **Build the rendering layer so that swapping a text label for a glyph component is a single-point change per correspondence type** — e.g. a lookup function that takes a correspondence type and value and returns either a text label or a glyph component. This way the glyph migration is trivial when the SVG library is ready.
