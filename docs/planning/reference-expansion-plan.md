# Implementation Plan: Reference Tab Expansion

Requested 2026-08-24. Six items: interactive Tree of Life, interactive
decan-rulership wheel, and reference sections for astrology, Kabbalah,
chakras, and numerology. Status: planned, not started.

## Shape

Two principles keep this coherent:

1. **Charts live inside their sections, not beside them.** The Tree of
   Life IS the Kabbalah section's navigation (per the user's "maybe
   integrated" note); the decan wheel is a tab of the Astrology
   section. The Reference sidebar grows four items — Astrology,
   Kabbalah, Numerology, Chakras — not six.
2. **Cross-references are computed, content is curated.** Which cards
   belong to Leo, Mercury, the heart chakra, or path 14 comes LIVE
   from the user's correspondence systems (zodiac_sign / planet /
   chakra / hebrew_letter / numerology assignment fields) and from the
   birth-cards decan tables — never duplicated by hand. The short
   descriptive text per sign/planet/sephira/chakra is static curated
   data, written once, plainly, and non-interpretive.

## Phase 1 — Foundation

- **Root module `reference_content.py`** (beside birth_cards.py):
  static datasets —
  - `SIGNS`: 12 × {name, glyph, element, modality, ruler, dates,
    trump number, brief description}.
  - `PLANETS`: 10 (7 classical + 3 modern) × {name, glyph, trump
    number where GD assigns one, themes, signs ruled}.
  - `SEPHIROTH`: 10 × {number, name, translation, meaning, planet
    association, pillar, tree position (x, y)}.
  - `TREE_PATHS`: 22 × {path number 11–32, from/to sephiroth, Hebrew
    letter + value, trump number}. GD attributions, noted as such.
  - `CHAKRAS`: 7 × {name, Sanskrit, color, location, themes}.
  - `NUMBERS`: 0–9 meanings — seeded from the existing unwired
    NumerologySection.tsx content, moved server-side.
  - Decan wheel data derives from birth_cards.py (DECANS,
    DECAN_RULERS, SIGN_MAJORS, PLANET_MAJORS, decan_court × all three
    court systems) — nothing re-declared.
- **Blueprint `routes/reference_content.py`**: one endpoint per
  section returning the static data hydrated with card cross-refs
  (archetype ids + default-Tarot-deck card ids via the birth-cards
  route helpers) and correspondence-assignment matches (which cards
  the active system puts under each sign/planet/chakra/letter/number).
- **ReferenceTab**: sidebar gains the four sections (flat list still
  fine at seven items); ⌘K palette entries.

## Phase 2 — Astrology section (Signs & Planets)

- Two sub-tabs: **Signs** and **Planets** (the wheel joins as a third
  tab in Phase 3).
- Signs: 12-item selector (glyph + name); detail panel shows element /
  modality / ruler / date span / trump (with card image), the sign's
  three decans (each with its minor + dates), the sign's court arcs
  under the chosen court system, and every card the active
  correspondence system assigns to the sign.
- Planets: selector; detail shows themes, signs ruled, trump where one
  exists, decans ruled (from the Chaldean sequence), and
  correspondence-assigned cards.
- Card tiles reuse the birth-cards tile pattern; click opens the card
  viewer (same path as the entry-viewer tiles).

## Phase 3 — Interactive decan wheel

- Inline SVG inside the Astrology section: outer ring of 12 sign
  glyphs, inner ring of 36 decan segments; theme-aware via CSS
  variables (no hardcoded colors).
- Hover highlights a segment; click selects → side panel with the
  decan's dates, minor card (image), sign trump, planetary ruler
  trump, and its court under **all three court systems side by side**
  (golden_dawn / golden_dawn_waite / bota), the saved preference
  marked.
- A "today" marker on the current date's decan; optionally a marker
  for a chosen profile's birth decan (small querent picker) — the
  personal tie-in that makes the wheel more than a poster.
- Court-arc overlay toggle: shade the sixteen 20°–20° arcs for the
  selected system.

## Phase 4 — Kabbalah section + interactive Tree of Life

- Inline SVG tree: 10 sephiroth (three pillars, standard layout from
  SEPHIROTH positions), 22 connecting paths; theme-aware.
- Click a **path** → detail panel: path number, Hebrew letter (glyph,
  name, value), its trump with card image, the letter's
  correspondence-assigned cards (hebrew_letter field), and which
  sephiroth it joins.
- Click a **sephira** → name, translation, meaning, planetary
  association, pillar, and the four minors of its number (Aces for
  Kether … Tens for Malkuth) with images; court/world note kept brief.
- Attribution note: paths follow the Golden Dawn letter–trump scheme;
  the 8/11 display preference applies to trump NAMES only (the
  letter–path structure doesn't move).
- Below the chart: a flat table view of the same 22 paths for
  scanning/reference without the chart.

## Phase 5 — Numerology section

- **Built expandable — the user hasn't settled on a system or number
  range yet.** No assumptions baked in:
  - The dataset is a flat list of number entries, not a fixed 0–9
    array: each entry is {number (or label — "11", "22", "33" master
    numbers, or anything else later), title, meaning, optional
    extras}. The API returns whatever the list holds; the UI renders
    however many entries exist, in list order.
  - Entries carry an optional `system` tag so a second numerological
    system can sit alongside the first later (UI grows a system
    picker only when more than one tag exists; invisible until then).
  - Derived material stays conditional: the constellation block
    renders only for numbers 1–9 (where CONSTELLATIONS applies), the
    minors block only where a matching pip rank exists, correspondence
    cross-refs match by the entry's number-as-string against the
    numerology field. An entry outside those ranges still renders its
    text cleanly with nothing broken.
- Rescue the unwired NumerologySection.tsx: its 0–9 meaning texts seed
  the initial list; the component gets rebuilt on the live data.
- A short header explains reduce-to-22 vs digital-root since both
  appear in the app.

## Phase 6 — Chakras section

- 7 chakras, root to crown, each with its color as the accent: name,
  Sanskrit, location, themes, and the cards the active correspondence
  system's chakra field assigns. Simplest section; closes the docket
  item.

## Verification & rhythm

Per phase: build + pytest (new endpoint tests assert dataset
integrity — 12 signs, 36 decans, 22 paths summing correctly, three
distinct court tables — and cross-ref hydration), live Playwright
screenshots when the app is closed, explicit-path commit, push on
approval. SVG charts get a click-through check (click decan/path →
panel content).

## Deliberately deferred

- Editable/user-authored notes on signs/planets/etc. (could later
  reuse the reference-sources model keyed to these entities).
- Astronomical accuracy (real-time planet positions) — this is a
  symbolic reference, not an ephemeris; the natal chart feature
  already covers live astrology.
- Non-GD path attribution schemes for the Tree (e.g. Case's color
  scales are fine to show; alternate letter orders are not offered).
