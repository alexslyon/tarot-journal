# Implementation Plan: Greer Name Cards

Source spec: `greer-name-cards-spec.md` (repo root). Companion to the shipped
birth-cards feature. Status: planned, not started.

## Shape of the feature

Like birth cards: pure calculator module + thin API + a modal on Profiles.
Unlike birth cards, the input is a *name*, which has no canonical form.

Per user direction: profiles gain a **Full Name** field, separate from the
display name, and that field is what name cards read. The modal parses it
into first/middle/last parts as an *editable suggestion* (the spec's role
rules), and the user's adjustments — merged parts for names like
"van der Berg", role reassignments, Y flips — persist per profile. The
calculate API still takes an ordered parts array, honoring the spec's
"never split on whitespace at the API layer" rule; whitespace splitting
happens only in the UI as a suggestion the user confirms.

## Phase 1 — Core calculator (`name_cards.py`, pure Python)

Root-level module beside `birth_cards.py`, importing `reduce_to_22` and
`CONSTELLATIONS` from it (never reimplementing them):

- **Key numbers** A=1…V=22 with W/X/Y/Z hard-coded as 5/6/7/8 (23–26 never
  enter arithmetic); W/X/Y/Z element tags as display metadata.
- **Normalization** exactly as §1: uppercase → NFD-strip diacritics (flagged
  `normalized: true`) → drop apostrophes/hyphens/periods/spaces → drop
  generational suffixes (overridable) → **reject non-Latin scripts with a
  clear error**, never transliterate. Normalized strings returned for audit.
- **Role assignment**: 3 parts = first/middle/last; 2 = first/last with
  middle **null (never 0)**; 1 = mononym; 4+ = interior parts merged as one
  middle. Explicit `roles` array overrides. Single-letter parts are normal
  parts.
- **Y split** (`y_mode`): heuristic default (consonant iff word-initial or
  followed by a vowel), `always_vowel`, `always_consonant`, plus per-letter
  `y_overrides`. Output always includes `y_positions` so the UI can show and
  flip each Y individually. W is always a consonant.
- **Per-name cards**: unreduced vowel/consonant/total sums per part; First /
  Middle / Last Name Cards; Theme Chord as the ordered triple.
- **Whole-name cards**: Desires & Inner Motivation (vowels), Outer Persona
  (consonants), and the three carefully-named cards — `theme_note` (sum of
  *reduced* per-name cards), `rhythm` (sum of the two reduced persona cards),
  `melody` (reduce only at the end). The string "destiny card" never appears
  in code, per the triple naming collision.
- **Hidden Factor Name**: same set-difference rule against the shared
  constellation root.
- **Constellation Count**: per-letter digital roots (1–9 reduction, distinct
  from reduce_to_22), all nine keys always present — zeros are the point.
- **Life Potential**: `reduce_to_22(birth_base_number + all_letters)`, both
  unreduced — the single boundary with the birth module, which already
  exposes `base_number`.
- **Presentation data**: mandala sequence (per-letter card + is_vowel +
  which name part), `max_letter_frequency`, leading letter, first vowel,
  V/C rhythm string with downbeats, and Case's musical-note table as a
  swappable mapping.

Tests (`tests/test_name_cards.py`):
- The full `JOHN QUINCY ADAMS` vector from §10 (y_mode always_vowel),
  including the Life Potential pairing with 1961-08-04 → 14.
- Property tests over seeded random names: vowels + consonants == letters
  (the partition check that catches Y bugs); Theme Note / Rhythm / Melody
  always share a root; y_mode changes Desires/Persona but never Melody.
- Two-part name → null middle, Theme Note sums two cards; 4+ parts merge;
  mononym; single-letter middle.
- `JOSÉ` ≡ `JOSE`; `О'BRIEN` with Cyrillic О rejected, not coerced;
  suffix drop (`JR`, `III`); constellation count totals the letter count.

## Phase 2 — Storage + API

- **Two additive columns on `profiles`** (no table rebuild):
  - `full_name` TEXT NULL — the birth/full name, user-edited in the profile
    form.
  - `name_cards_config` TEXT NULL — JSON holding the user's adjustments:
    parts + roles (only stored once they diverge from the default parse of
    full_name), y_mode, y_overrides, drop_suffixes.
- **Endpoints** (`backend/routes/name_cards.py`):
  - `POST /api/name-cards/calculate` — body: parts, roles, y_mode,
    y_overrides, optional profile_id (pulls birth_date for Life Potential).
    Returns the computed profile hydrated with display names, archetype ids,
    and default-Tarot-deck card ids. The hydration helpers in
    backend/routes/birth_cards.py get refactored into a shared spot both
    routes import.
  - `GET/PUT /api/profiles/<id>/name-cards-config` — persisted adjustments.
  - Profile GET/PUT gains full_name passthrough.
  - Non-Latin input returns a 400 whose message the UI shows verbatim.
- Migration tested against a copy of the real DB before shipping, per house
  rules.

## Phase 3 — UI

- **ProfilesTab**: the profile form gains a **Full Name** field (under the
  display name, with a hint that it feeds name cards), and a "Name Cards"
  button beside "Birth Cards" — enabled when full_name is set (no birth date
  required — only Life Potential needs one).
- **NameCardsModal** (shared Modal, theme vars, QueryError):
  - Top: the parsed parts as editable chips — each part shows its role
    (first/middle/last per the 1/2/3/4+ rules), with controls to merge
    adjacent parts ("van" + "der" + "Berg" → one last name) and reassign
    roles. Adjustments persist to name_cards_config; a "reset to parsed"
    link discards them.
  - Results, per the book's structure: Theme Chord (three tiles captioned
    Conscious / Hidden / Social Self), Desires & Inner Motivation + Outer
    Persona, the Theme Note / Rhythm / Melody trio with their shared-
    constellation note, Hidden Factor Name, Life Potential (shown only when
    the profile has a birth date), Constellation Count as a nine-cell strip
    where absences are visibly flagged, and the Name Mandala — vowel cards
    raised above consonant cards, letter and musical note under each tile,
    with the "you'd need N decks" line from max_letter_frequency.
  - **Y panel**: every Y listed with its current classification and a
    click-to-flip that persists into name_cards_config — the spec is
    emphatic this can't hide behind a default.
  - Normalization notices ("José → JOSE", "dropped: Jr") shown inline.
- Explanatory copy follows §12's framing (culturally imprinted alphabet
  order; Latin-alphabet names only, by the author's own argument).

## Phase 4 — Verification

Usual rhythm: build, pytest (new + full suite), live Playwright screenshots
(create a throwaway profile + saved name, exercise the Y flip and a JQA-style
calculation, clean up), explicit-path commits, ask before push.

## Decisions taken (flagged ⚑ in the spec, surfaced as settings/overrides)

- y_mode default: heuristic, per saved name, with per-letter overrides.
- Suffix dropping: on by default, toggle stored per saved name.
- Musical mapping: Case's table shipped as data, swappable later.
- Non-Latin: rejected with explanation, honoring the spec's reasoning.

## Deferred

- Multiple saved names per profile (chosen names, nicknames — spec §9).
  The full_name field covers the birth name, which Greer treats as primary;
  a `profile_names` table can layer alternates on later without touching
  what ships now.
- Audio playback of the chord/melody (note mapping ships, synth doesn't).
- Per-letter interpretive text and mythological name lists (content layer).
- Any phonetic analysis beyond the Y heuristic.
