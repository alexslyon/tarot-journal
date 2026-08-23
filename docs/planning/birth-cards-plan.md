# Implementation Plan: Greer Birth Cards

Source spec: `greer-birth-cards-spec.md` (repo root). Status: planned, not started.

## Shape of the feature

A deterministic calculator (no AI, no interpretation — fits the app's non-goals)
that turns a birth date into the Greer "Lifetime Cards", surfaced on Profiles
the same way natal charts already are: a button on the profile that opens a
modal. All math lives in one pure Python module; the UI only renders.

## Phase 0 — Promote Profiles to a top-level tab

Requested alongside this feature: Profiles moves out of Settings into its own
tab in the main nav. `ProfilesTab` is already a self-contained component
(Settings wraps it in a one-line `ProfilesSection` shell), so this is a
rewiring, not a rewrite:

- `TabNav`: add `profiles` to the `TabId` union and the `TABS` list
  (proposed order: Library, Spreads, Journal, Profiles, Reference, Insights).
- `App.tsx`: render `<ProfilesTab />` for the new tab.
- `SettingsLayout`: drop the Profiles sidebar entry and section.
- `CommandPalette`: repoint its "Profiles" entry from the Settings section to
  the new top-level tab.
- Delete the now-unused `ProfilesSection.tsx` wrapper.

This also gives the Birth Cards button (Phase 3) a more visible home.

## Phase 1 — Core calculator (pure Python, no DB, no API)

New root-level shared helper `birth_cards.py` (same tier as `astrology.py`):

- `digit_sum`, `reduce_to_22`, `reduce_to_9` primitives
- `calculate(birth_date, method, eight_eleven, reference_year, reference_month)`
  → dict matching the spec's `BirthCardProfile` (§1). Majors as ints 1–22
  everywhere; Fool = 22 internally.
- `CONSTELLATIONS` table (§3); hidden factor via the set-difference rule, with
  `nighttime` flag; Shadow-vs-Teacher naming left to the render layer (age is
  computed API-side where "today" is known).
- Decan table (§5) with the two explicit gotchas: 3 of Pentacles wraps the year
  boundary; 8 of Cups upper bound = end of February (leap-safe).
- Dynamics via the `((n-1) mod 3) + 1` formula (§6), `null` + `fool_center`
  for 22.
- Year/periodic cards (§8): `year_card`, `generic_year`, `personal_month`,
  `karmic_year`, `year_card_series(birth, from, to)`.
- Name resolution at the boundary only (§7): int → display name with the
  8/11 Strength–Justice toggle and the Thoth alias map. Also emit
  (rank, suit) keys that match `card_archetypes` rows — Majors are rank
  "0".."21" (spec's 22 → rank "0"), Minors are e.g. name "Three of Cups".
- **Amberstone**: implemented as a first-class alternative method
  (`MM + DD + YYYY[0:2] + YYYY[2:4]`), user-selectable — see the UI toggle in
  Phase 3. The spec's test vectors (soul invariance, the 1945-12-12
  divergence) exercise both methods.

Tests in `tests/test_birth_cards.py`:
- All six §9 vectors, exactly as tabled.
- 366-date decan tiling: every date maps to exactly one card, all 36 hit.
- Soul invariance greer-vs-amberstone over a random sample; the §0 divergence
  case; pattern closed-set over 1900–2100; hidden-factor length-2 only for
  1-1/2-2/3-3/4-4; spot-checks from the §10 generational facts.

## Phase 2 — API (no migration needed; pure computation)

In a new `backend/routes/birth_cards.py`:
- `GET /api/profiles/<id>/birth-cards?year=&month=` — reads the profile's
  `birth_date`, returns the profile plus resolved names and matched
  `card_archetypes` ids (Tarot) so the UI can link into Reference. Includes
  the person's age so the UI can pick Shadow vs Teacher wording. Clean error
  when the profile has no birth date.
- `GET /api/birth-cards?date=YYYY-MM-DD` — ad-hoc lookup for any date (lets
  the modal offer a "try another date" field without creating a profile).
- Preferences stored in the existing settings table:
  `birth_cards_method` (default `greer`) and `birth_cards_eight_eleven`
  (default `golden_dawn`). Both endpoints also accept a `method` query
  param override so the modal toggle can preview without saving.

## Phase 3 — UI

- **ProfilesTab**: a "Birth Cards" button beside "View Chart", enabled only
  when the profile has a birth date.
- **BirthCardsModal** (shared `Modal` component, theme vars, `QueryError`):
  - Header: pattern label ("12-3" etc.) + short plain-language explainer
    reflecting the spec's §12 framing (cultural imprinting, not ancient cosmic
    fact).
  - Sections: Personality & Soul; Teacher (19-10-1 only); Hidden Factor
    (labelled Shadow under age 29, Teacher at 29+, "Hidden Factor" if age
    unknown; nighttime copy when flagged); Constellation; Lessons &
    Opportunities (the four — or eight — Minors); Zodiacal Lesson &
    Opportunity (never the string "Destiny Card"); Dynamic group; Year Card
    for the current year with both cycle framings; Personal Month; Karmic Year.
  - Cards render as images from the user's default Tarot deck where an
    archetype match resolves (card `archetype` field), falling back to a
    text chip. Clicking a card opens the existing archetype-notes viewer.
  - Two small persisted controls in the modal:
    - **Method toggle: Greer / Amberstone.** Unlike 8/11 this IS a
      recalculation — the Soul Card never changes but the Personality Card
      (and everything downstream of it: pattern, hidden factor, dynamic)
      can. A one-line note in the modal explains that, so a user comparing
      against a Tarot School result understands why the cards moved.
    - **8/11 toggle: Strength/Justice** — display-only relabel, never a
      recalculation.

## Phase 4 — Verification

Usual rhythm: `npm run build:frontend`, pytest (new suite + existing), live
Playwright screenshots against real data (a profile with a birth date),
explicit-path commit, ask before push.

## Open questions (defaults chosen, easy to change)

1. Profiles-only for now. Could later add a small birth-cards chip for the
   querent in the entry viewer — deferred until asked.
2. Year Card series / "cycle themes" timeline (§8) — the API function will
   exist; a timeline visual is deferred (could join Insights later).
