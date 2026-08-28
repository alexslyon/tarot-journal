# Handoff: Tarot Journal — visual overhaul

## Overview

A complete dark-mode visual overhaul of Tarot Journal, a desktop (Electron) app for
practitioners who keep a written record of their readings. The overhaul covers every
screen of the app, its empty and error states, its modal interactions, and its printed
output. The design direction is called **3a** throughout this bundle: the Nocturne dark
system as the foundation, with entry titles and headings set in a light Newsreader serif
so a reading reads as a written document on screen and on paper alike.

Fourteen screens are documented. All of them are already built as HTML.

## About the design files

The HTML files in this bundle are **design references**, not production code.
They are prototypes that show intended layout, color, type and behavior at 1:1 scale.

Do not copy the markup into the app. The task is to **recreate these designs in the
app's existing environment** — its component library, its routing, its state layer —
using established patterns there. If the renderer has no component conventions yet,
choose the framework appropriate to the project and implement the designs in it.

Two things in this bundle ARE meant to ship, or to be ported closely:

- `tokens.css` — the application token layer. Port it as-is (or convert it to the
  app's token format); it is the source of truth for every value below.
- `_ds/nocturne/styles.css` — the Nocturne design system stylesheet that tokens.css
  sits on top of. It supplies the 100–900 ramps every app token resolves to.

## Fidelity

**High fidelity.** Colors, type sizes, spacing, radii, hover states and copy are final
and should be reproduced exactly. Every value in the mockups appears in `tokens.css`;
where a mockup shows a literal hex, the migration map in `Design Tokens.dc.html`
(section "Migration map") names the token it maps to.

Two things are deliberately NOT final:

- **Card images.** Every card face in the mockups is a placeholder — a flat surface with
  the card's name set in mono at 9–10px. Real deck art will be wired up from the app's
  existing card database. The placeholder IS the correct fallback rendering for a card
  with no image (see screen 7d).
- **Data.** All entries, decks, counts and statistics are plausible fixtures, not real
  values. Copy that is *interface* copy (button labels, empty-state prose, error text)
  IS final and should be used verbatim.

---

## Design tokens

Load order matters: Nocturne's `styles.css` first, then `tokens.css`. `tokens.css`
never redefines a `--color-*` variable; it only names application roles on top of them.

### Rules for the build

1. No hex, no `rgba()`, no px radius inside a component. If a value is needed and no
   token names it, the token is missing — add it to `tokens.css` with a use note.
2. Alphas come from the channel tokens: `rgb(var(--tj-accent-rgb) / 20%)`. Never a new
   hex for a tint.
3. The accent (#9184d9) appears as a border, as text, as a 3px bar, or as a glow. If it
   is filling an area larger than a chip, it is wrong.
4. Horizontal and vertical rules use `--tj-rule-h` / `--tj-rule-v`, not `border-top`.
   The fade to transparent over the last 48px each side is the system, not a flourish.
5. Print styles read only `--tj-paper-*`.
6. Never pure black or pure white. Every value comes from a ramp. (Shadows are the
   exception — ambient darkness mixed from black is a shadow, not a color.)

### Colors — grounds and surfaces

| Token | Value | Use |
| --- | --- | --- |
| `--tj-canvas` | `#161826` | Window ground |
| `--tj-canvas-lift` | `#232544` | Top stop of the window gradient |
| `--tj-canvas-gradient` | `radial-gradient(120% 80% at 50% -10%, #232544 0%, #161826 60%)` | Every window's background |
| `--tj-panel` | `rgb(29 31 46 / 66%)` | Sidebars, inspectors, stat cards |
| `--tj-panel-quiet` | `rgb(29 31 46 / 50%)` | Reading surfaces, spread boards |
| `--tj-chrome` | `#232532` at 80% | Nav pill track, icon buttons |
| `--tj-well` | `rgb(22 24 38 / 70%)` | Inputs, note fields, segmented tracks |
| `--tj-scrim` | `rgb(11 12 20 / 72%)` | Behind a modal (74% for confirms, 78% for destructive) |
| `--tj-card` | `#242737` | A card face |
| `--tj-card-empty` | `rgb(22 24 38 / 55%)` | Unfilled spread slot |
| `--tj-card-selected` | `#2b2741` | The focused card |

### Colors — text

| Token | Value | Use |
| --- | --- | --- |
| `--tj-text` | `#e9e9ed` | Titles, primary prose |
| `--tj-text-2` | `#cfd3e5` | Panel headings |
| `--tj-text-3` | `#b2b6ca` | Secondary prose |
| `--tj-text-muted` | `#9397ab` | Labels, inactive nav |
| `--tj-text-faint` | `#75798c` | Hints, counts |
| `--tj-text-ghost` | `#595d6c` | Disabled, axis ticks |
| `--tj-text-kicker` | `#968ae0` | Uppercase kickers |
| `--tj-text-accent` | `#d2cefd` | Text on accent tints |
| `--tj-text-accent-2` | `#b5abfc` | Inline emphasis, warnings |
| `--tj-text-on-tint` | `#e7e5fe` | Primary button labels |

### Colors — line, tint, glow

| Token | Value | Use |
| --- | --- | --- |
| `--tj-hairline` | `rgb(233 233 237 / 10%)` | Input borders, rules |
| `--tj-hairline-strong` | `rgb(233 233 237 / 14%)` | Secondary button borders |
| `--tj-edge-card` | `rgb(233 233 237 / 12%)` | Card inset ring |
| `--tj-edge-accent` | `rgb(145 132 217 / 45%)` | Primary button border |
| `--tj-edge-accent-lit` | `rgb(145 132 217 / 60%)` | Selected card ring |
| `--tj-tint` | `rgb(145 132 217 / 14%)` | Selected row |
| `--tj-tint-strong` | `rgb(145 132 217 / 20%)` | Primary button fill, active nav, accent chip |
| `--tj-tint-hover` | `rgb(145 132 217 / 32%)` | Primary button hover |
| `--tj-tint-neutral` | `rgb(233 233 237 / 7%)` | Inactive chip |
| `--tj-tint-neutral-hover` | `rgb(233 233 237 / 5%)` | Row hover on a panel |
| `--tj-glow-soft` | `0 0 18px rgb(145 132 217 / 25%)` | Active nav pill |
| `--tj-glow` | `0 0 22px rgb(145 132 217 / 30%)` | Primary button hover |
| `--tj-glow-card` | `0 0 20px rgb(145 132 217 / 26%)` | Selected card |
| `--tj-glow-line` | `0 0 14px rgb(145 132 217 / 50%)` | Data bars |
| `--tj-shadow-window` | `0 24px 60px rgb(0 0 0 / 50%)` | The window itself |
| `--tj-shadow-modal` | `0 30px 70px rgb(0 0 0 / 60%)` | Modals |

### Type

Two families. **Newsreader** (weight 300 for display, 400 for headings) for anything that
is *written* — entry titles, panel headings, card names, position names, large figures.
**Inter** for the instrument — controls, labels, metadata, data. A mono stack
(`ui-monospace, Menlo, monospace`) appears only for card codes, file paths and key caps.

| Token | Size | Family / weight | Use |
| --- | --- | --- | --- |
| `--tj-size-display` | 46px / 1.04 / -.005em | Newsreader 300 | Screen title |
| `--tj-size-display-sm` | 42px | Newsreader 300 | Secondary screen title |
| (modal title) | 30–34px | Newsreader 300 | Dialog titles |
| `--tj-size-title` | 20px | Newsreader 400 | Panel title |
| `--tj-size-title-sm` | 18px | Newsreader 400 | Small panel title |
| (list title) | 17–19px | Newsreader 400 | Entry rows, deck rows, card names |
| `--tj-size-body` | 14px / 1.6 | Inter 400 | Body prose |
| `--tj-size-ui` | 13px | Inter 400 (500 on primary) | Controls, rows |
| `--tj-size-small` | 12px | Inter 400 | Metadata, counts |
| `--tj-size-kicker` | 11px / .16em / uppercase | Inter 500 | Kickers, tags |
| `--tj-size-mono` | 9–10px / .06em / uppercase | mono | Card codes |

Large figures (stat cards, reversal rate, draw counts) set in Newsreader 300 at 44–52px
with `font-variant-numeric: tabular-nums`. Headings never go past 500 weight — hierarchy
is size and space.

### Radius, spacing, metrics

| Token | Value | Use |
| --- | --- | --- |
| `--tj-radius-panel` / `--tj-radius-card` | 14px | Panels, cards, windows, modals |
| `--tj-radius-row` | 10px | List rows, small chips |
| `--tj-radius-pill` | 999px | Every button, input, chip, nav item, toggle |
| `--tj-gutter` | 18px | Window padding |
| `--tj-gap` | 20–24px | Between columns |
| `--tj-panel-pad` | 18px | Inside a panel |
| `--tj-control-pad` | 10px 18px | Pill buttons (9px 18px when compact, 11–12px 22–24px in empty states) |
| `--tj-chip-pad` | 4px 11px | Tags |
| `--tj-card-ratio` | 2 / 3 | Every card face, everywhere |
| `--tj-measure` | 660px | Settings and prose columns |

### Three documented deviations from Nocturne

Each is deliberate; do not "correct" them back to the system default.

1. **Newsreader.** Nocturne sets everything in Inter. A journal entry is a written object
   that has to survive being printed, and the serif is what makes the screen and the page
   the same document. Inter keeps every interface role.
2. **14px radius, not 8px.** Nocturne bakes 8px. A tarot card has a physical corner; at
   the size the app shows one, 8px reads as a clipped rectangle. Panels match the card so
   nothing looks cut from a different sheet. Rows stay at 10px — they are list items.
3. **A light ground for print.** Nocturne is dark. The printed entry sets on
   `--tj-paper` (neutral-100) with ink from the dark steps of the same ramps. No second
   theme, no new hues; one accent step (700) survives into ink.

---

## Common chrome

Every full screen is a **1440 × 940** window: `--tj-canvas-gradient` ground,
`--tj-radius-panel` corners, `--tj-shadow-window`, `overflow: hidden`, and a column
flex layout.

**Title bar** — 16px 24px padding. Left: three 10px traffic-light dots (`#3f424d`,
`#3f424d`, `#5d5294` — the third takes the accent-700 step). Then the wordmark
"Tarot Journal" in Newsreader 17px `--tj-text-2`.

**Nav** — centered (a `flex:1` spacer each side), a pill track: `--tj-chrome` background,
`inset 0 0 0 1px rgb(233 233 237 / 9%)`, 3px padding, 3px gap, fully round. Items are
7px 16px, 13px. Inactive `--tj-text-muted` → `--tj-text` on hover. Active takes
`rgb(145 132 217 / 22%)`, `--tj-text-on-tint`, weight 500, and `--tj-glow-soft`.
Order: Library · Spreads · Journal · Reference · Insights.

**Right side** — a 34px round icon button on `--tj-chrome` (settings gear), or a status
string in `--tj-text-ghost`.

**Buttons** — all pills, all outlined; the accent is never a solid fill.
- Primary: `--tj-tint-strong` fill, `1px solid --tj-edge-accent`, `--tj-text-on-tint`,
  weight 500, 13px. Hover: `--tj-tint-hover` + `--tj-glow`.
- Secondary: transparent, `1px solid --tj-hairline-strong`, `--tj-text-2`.
  Hover: `rgb(233 233 237 / 6%)`.
- Quiet accent: transparent, `1px solid rgb(145 132 217 / 35%)`, `--tj-text-accent`.
  Hover: `rgb(145 132 217 / 16%)`.
- Text-only (destructive or dismissive): no border, `--tj-text-muted`, underline on hover.
- Disabled: `--tj-text-ghost` on a `rgb(233 233 237 / 8%)` border, `cursor: not-allowed`.
- **All button labels need `white-space: nowrap`** — they wrap mid-word otherwise when a
  header row squeezes.

**Inputs** — pill, `--tj-well` background, `1px solid --tj-hairline`, 10px 16px, 13px,
`outline: none` on the element but `:focus-visible` must carry
`outline: 2px solid var(--color-accent); outline-offset: 2px` per the system.
Disabled inputs drop to `rgb(22 24 38 / 45%)` with a 6% border and `--tj-text-ghost` text.

**Chips / tags** — 11–12px, `--tj-chip-pad`, pill. Selected: `--tj-tint-strong` +
`--tj-text-accent`. Unselected: `--tj-tint-neutral` + `--tj-text-3`.
Removable chips carry a trailing 9px × glyph. An "add" chip uses a 1px dashed
`rgb(233 233 237 / 18%)` border and `--tj-text-faint`.

**Toggles** — 34×20 (38×22 in Settings) pill track, 16px (18px) round knob.
On: `rgb(145 132 217 / 35%)` track, `inset 0 0 0 1px rgb(145 132 217 / 50%)`,
`--tj-text-accent` knob, knob right. Off: `rgb(233 233 237 / 9%)` track,
12% inset border, `#5a5e70` knob, knob left.

**Card faces** — `aspect-ratio: 2/3`, `--tj-radius-card`, `--tj-card` background,
`inset 0 0 0 1px --tj-edge-card`, 9–10px padding, name set in mono 9–10px uppercase
`.06em` bottom-left. Selected: `--tj-card-selected` + `inset 0 0 0 1px --tj-edge-accent-lit`
+ `--tj-glow-card`, label in `--tj-text-accent`. Reversed: `transform: rotate(180deg)` on
the face with a counter-rotation on the label so the text stays upright. Empty slot:
`--tj-card-empty` background, 12% inset ring, a centered 22px plus glyph in
`--tj-text-faint`; hover lifts the ring to `rgb(145 132 217 / 55%)` and the fill to
`rgb(145 132 217 / 10%)`. Position labels sit under the card in Newsreader 14–15px,
centered, `--tj-text-muted`.

**Icons** — Phosphor, 14–22px, `fill: currentColor`.

---

## Screens

Fourteen screens live on one canvas file, `Tarot Journal Overhaul.dc.html`, laid out in
rows. Each carries a visible id badge; the ids below match.

### 3a — Journal (the reference screen)
The direction's canonical screen and the one to build first.
- **Purpose:** read a saved entry.
- **Layout:** title bar; then a 2-column grid `372px 1fr` with `--tj-gutter` padding.
- **Left (panel):** "New Entry" primary (full width, with a 14px plus glyph) + "Export"
  secondary; search input; a row of tag chips ending in a "+ 9" count; then the entry
  list. Each row is 14px 16px, `--tj-radius-panel`, title in Newsreader 19px with the
  day (`11px, --tj-text-faint`) right-aligned on the same baseline, and a 12px meta line
  ("Five-Card Cross · Marseille (Camoin)"). Selected row: `--tj-tint` +
  `inset 0 0 0 1px rgb(145 132 217 / 35%)` + `--tj-glow-soft`.
- **Right:** kicker ("Entry 214 · New Moon in Leo"); `h1` at `--tj-size-display`;
  "Edit" secondary + "Export PDF" primary aligned to its baseline; a metadata row
  (date, querent, reader, place) at 13px with values in `--tj-text` and labels in
  `--tj-text-muted`. Below, a `1fr 316px` grid: the reading on a `--tj-panel-quiet`
  surface (a `repeat(3, 140px)` grid, 18px/24px gaps, cards placed by `grid-area` —
  1/2 Above, 2/1 Behind, 2/2 The Matter, 2/3 Ahead, 3/2 Beneath), and a right column of
  `--tj-panel-quiet` cards: Notes, Repeating cards (chips), Follow-up.
- **Props already wired:** `showPositionLabels`, `showFollowUp`, `cardScale` (0.8–1.3,
  applied as a `scale()` on the spread grid with `transform-origin: top center`).

### 4a — Library
- **Purpose:** browse decks and the cards in one.
- **Layout:** `340px 1fr`, 24px gap.
- **Left:** "Import Deck" primary; "Search decks"; deck rows — a 38×57 spine
  (`--tj-card`, 6px radius; selected spine is `--tj-card-selected` with a 40% accent
  ring) beside name (Newsreader 18–19px) and meta ("Tarot · 78 cards").
- **Right:** kicker with provenance ("Deck · Tarot · 1760, restored 1997"), title,
  "Edit deck" + "Add cards"; a filter row (search input, Major/Minor/Court chips, a
  "Suit ▾" chip, and a "22 of 78" count in `--tj-text-faint`); then a
  `repeat(7, 1fr)` card grid with 16px gaps on a `--tj-panel-quiet` surface. Card hover
  lifts the inset ring to `rgb(145 132 217 / 60%)`. Names sit under each card in
  Newsreader 15px centered.

### 4b — New entry (modal editor)
- **Purpose:** record a reading.
- **Layout:** the Journal screen behind a `rgb(11 12 20 / 72%)` scrim; a
  **1180 × 850** panel centered on `#1a1c2c` with `inset 0 0 0 1px rgb(233 233 237 / 10%)`
  and `--tj-shadow-modal`.
- **Header:** kicker "New entry · draft"; the title is an input with no box —
  transparent, no border except a 1px bottom `--tj-hairline-strong`, set in
  Newsreader 300 at 36px, 520px wide. "Cancel" + "Save entry" right.
- **Body:** `1fr 360px`. Left panel holds "Reading 1" (Newsreader 19px) with two
  dropdown chips (spread, deck) on the `--tj-well` fill; the spread grid at
  `repeat(3, 132px)` mixing filled and empty slots; and a footer row with an
  "Add reading" quiet-accent button plus the hint "Click a slot to assign a card ·
  ⌥-click marks it reversed".
- **Right:** a metadata panel (Date + Time on one row, Querent, Reader, Tags with
  removable chips and a dashed "+ tag"), then a Notes panel with a B / I / U / • pill
  toolbar and a `--tj-well` text area showing a 1px × 15px `--tj-text-accent-2` caret.

### 4c — Printed entry (single page)
A fixed 816 × 1056 Letter page at 96dpi, for reference only. **The real print artifact is
`Printed Entry.dc.html`** — see "Print" below.

### 5a — Spreads
- **Purpose:** define and edit spread layouts.
- **Layout:** `320px 1fr 300px`, 20px gaps.
- **Left:** "New spread" primary; search; then two labelled groups ("Mine", "Built in"),
  each row showing name (Newsreader 18–19px) and `n · used 41×`.
- **Center:** kicker ("Spread · 5 positions · used in 41 entries"), title,
  "Duplicate" + "Use spread"; an Arrange/Preview chip pair with a "Snap to grid" toggle
  right; then the **board** — `--tj-panel-quiet` with a dotted grid
  (`radial-gradient(rgb(233 233 237 / 7%) 1px, transparent 1px)`, `background-size: 28px 28px`),
  the position cards absolutely centered in a `repeat(3, 96px)` grid with 12px/18px gaps.
  Each position card shows its number in Newsreader 22px, `cursor: grab`; position 3 is
  selected. Below the board (not inside it): "Add position" + the hint
  "Drag a card to move it · ⌥-drag to duplicate".
- **Right:** an inspector for the selected position — Name input, a prompt field
  (`--tj-well`, 74px min-height, the prompt shown in the editor), an "Allow reversals"
  toggle — then a reorderable Positions list (mono index, name, a 14px drag handle) and
  the note "Order sets the draw sequence and the print order."

### 5b — Insights
- **Purpose:** see patterns across all entries.
- **Layout:** a single column, 42px side padding — no sidebar.
- **Header:** kicker "214 entries · 1 Jan 2024 – 31 Jul 2026", title "Insights",
  and right-aligned controls: "All decks ▾", "All querents ▾", a 90d/1y/All segmented
  pill, "Export report" primary.
- **Stat row:** `repeat(4, 1fr)`, 14px gap. Each card is `--tj-panel`, 20px 22px, with a
  kicker label, the figure in Newsreader 300 at 44px with tabular numerals, and a note.
- **Body:** a `1fr 1fr` / `1fr 1fr` grid. Left cell spans both rows: "Cards that keep
  coming" — per card, name (Newsreader 17px) and count on one baseline over a 3px track
  (`rgb(233 233 237 / 8%)`) with an accent bar (`#9184d9` + `--tj-glow-line`) at a
  percentage width. Top right: "Cadence" — 14 monthly columns, flex-end aligned, each a
  6px-radius bar; past months `rgb(145 132 217 / 28%)`, the current month solid accent
  with an 18px glow, month label under each. Bottom right: "Suits drawn" (label, track,
  tabular count) beside a vertical `--tj-rule-v` and a "Reversals" figure — 52px
  Newsreader with the % sign at 26px in `--tj-text-muted`, plus the line
  "Highest in the Ahead position" in `--tj-text-accent-2`.

### 5c — Settings
- **Purpose:** app and reading defaults.
- **Layout:** `250px 1fr`, 28px gap. No nav pills — the title bar reads "Settings" with
  a round close button carrying the accent tint.
- **Left:** a pill nav rail on `--tj-panel`; active item is `rgb(145 132 217 / 16%)` with
  a 32% ring; version string pinned to the bottom in `--tj-text-ghost`.
- **Right:** a `--tj-measure` column. Kicker, title "Reading defaults", and a
  one-sentence explanation. Then grouped `--tj-panel` cards; each row is
  label + explanation on the left, control on the right, separated by `--tj-rule-h`.
  Controls seen here: dropdown chips, toggles, a Letter/A4 segmented pill, a
  "Change…" secondary button. Section headings between cards are Newsreader 22px.

### 6a — Reference
- **Purpose:** card meanings, with the practitioner's own history beside them.
- **Layout:** `272px 1fr 316px`, 20px gaps.
- **Left:** "Search meanings"; a Major/Minor/Court segmented pill; then an index — mono
  numeral (26px wide), name in Newsreader 17–18px, draw count right. Selected row takes
  `--tj-tint` + a 32% ring with the numeral in `--tj-text-accent-2`.
- **Center:** a 176px card face (selected treatment) with an Upright/Reversed pill pair
  under it, beside the card's kicker ("Major Arcana XVIII · Water · Pisces"), the name at
  52px Newsreader 300, keyword chips, a lead paragraph, and two actions
  ("Edit my note", "Start reading with this card"). Under a `--tj-rule-h`: a `1fr 1fr`
  grid — left, three headed prose blocks (Upright, Reversed, Symbols in this deck, the
  last a name/note two-column list); right, a `--tj-panel` card holding "My note"
  (the user's own reading of the card, with an italic accent phrase) and, under an inset
  rule, "Traditions" — three sources with the tradition name in `--tj-text`.
- **Right:** "In my practice" — the draw count as a 44px figure with " draws" at 22px,
  a note, a positions histogram, and "Reversed 9 of 31 times" in `--tj-text-accent-2`.
  Below: "Entries with this card" — rows of title (Newsreader 16px) + day + position,
  ending in a "See all 31 entries" text link in `--tj-text-accent`.

### 7a — First launch (no deck, no entries)
- Nav is present but dimmed (`opacity: .45`, items `#5a5e70`, track at 50%) — visible so
  the app doesn't look broken, inert so it doesn't invite a dead click. Title bar right
  reads "Local vault · 0 entries".
- A centered column: a ghost spread (four 124px dashed 2/3 slots at `opacity: .5`, the
  center one dashed in `rgb(145 132 217 / 45%)` with a 26px glow), 52px of space, then
  kicker, `h1` "Bring in a deck to begin" at 52px, a two-sentence promise about local
  storage, and two actions: "Import a deck…" primary, "Start with Marseille" secondary,
  with a clarifying line beneath.
- Below, three numbered steps in 250px columns separated by 1px left borders — mono
  numeral in `--color-accent-700`, Newsreader 19px title, 12px note.

### 7b — Journal, no entries
- Full real chrome. "Insights" in the nav is `#5a5e70` (nothing to show yet).
- Sidebar: "New Entry" stays live; "Export" and the search input are visibly disabled.
  Center of the sidebar: three small dashed spines, "No entries yet" in Newsreader 20px
  `--tj-text-muted`, and a line explaining that search and tags switch on with the first
  entry.
- Main area: a five-slot dashed ghost spread at `opacity: .6`, then kicker
  "Marseille (Camoin) · ready", `h1` "Your first reading", a sentence that removes the
  pressure to do it correctly, and "New entry" + "Import past readings".

### 7c — No results
- The Library screen, intact, with the search field in a focused state
  (`1px solid rgb(145 132 217 / 40%)` + an 18px glow) containing "wands of fire" and a
  round clear button.
- Both active filters render as removable accent chips ("Major Arcana ×", "Suit · Cups ×")
  and the count reads "0 of 78".
- The grid area is replaced by a centered block: three dashed 52×78 card outlines fanned
  (−7°, 0°, +7°) at `opacity: .45`; `h2` "Nothing matches "wands of fire"" at 32px;
  a line that names the cause — in Marseille the wands suit is called *Batons*; and three
  actions: "Search "Batons" instead" (primary), "Clear 2 filters", "Search all 9 decks".
- **Behavior note:** the primary action is derived from a synonym table for suit names
  across traditions (wands/batons/staves/clubs, coins/pentacles/discs/diamonds,
  cups/chalices/hearts, swords/spades). Where no synonym matches, fall back to
  "Clear n filters" as the primary.

### 7d — Missing card images
- Degraded, not broken, and **no red is introduced** — the accent carries the warning.
- Sidebar: the affected deck row shows a dashed spine with a 12px warning glyph and the
  meta line "42 images not found" in `--tj-text-accent-2`.
- Kicker states the split: "Deck · Oracle · 78 cards · 36 with images". Primary action
  becomes "Relink folder…".
- A notice bar under the header: `rgb(145 132 217 / 10%)` fill with a 30% ring, a 20px
  warning glyph, the message "42 card images couldn't be found", the missing path in mono
  `--tj-text-3`, then "Locate folder…" (quiet accent) and "Keep names only" (text-only).
- The card grid still works: cards with images render normally; missing ones render as a
  transparent face with a 1px dashed `rgb(233 233 237 / 16%)` border, a 13px
  broken-image glyph, and the code in `--tj-text-ghost`. Names below stay full strength —
  **the names are the data; the images are a convenience.**

### 8a — Command palette (⌘K)
- The screen behind gets `filter: blur(1.5px)` plus a `rgb(11 12 20 / 70%)` scrim.
- A **720px** panel pinned 104px from the top: `#1a1c2c`, 12% inset ring,
  `--tj-shadow-modal`. Header row — a 17px search glyph in `--color-accent-500`, the
  query at 17px with a caret, and an "esc" key cap. A `--tj-rule-h` under it.
- Results are grouped with uppercase 11px labels: **Cards**, **Entries**, **Commands** —
  the palette is the search, not a separate command list. Each row: a 20px icon column,
  title, right-aligned meta ("Marseille · drawn 31×"), and a key cap. The selected row
  takes `--tj-tint` with its ↵ cap in `rgb(145 132 217 / 22%)`.
- Footer on `rgb(22 24 38 / 60%)`: ↑↓ navigate · ↵ open · ⌘↵ open in new window, and the
  result count right.

### 8b — Shortcuts (?)
- A **940px** modal, 32px 36px padding. Header: kicker "Keyboard", title "Shortcuts",
  and "Editable in Settings → Shortcuts" beside a round close button.
- `repeat(3, 1fr)` with 34px gaps, six groups organised **by context, not
  alphabetically**: Anywhere, Journal, Editor, Library, Spreads, View. Each group has a
  Newsreader 19px heading over a rule that fades on its right end, then rows of
  label + key cap (mono 11.5px, `--tj-text-accent`, on `--tj-tint-neutral`).

### 8c — Unsaved changes
- A **520px** modal over a blurred editor (`rgb(11 12 20 / 74%)` scrim).
- Kicker states the stake in time: "Draft · 4 minutes of work". Title asks the question
  by name: "Close "Threshold at the New Moon" without saving?"
- An inset `--tj-well` list itemizes exactly what would be lost — cards placed and how
  many reversed, the note word count, the tags — each bulleted with a 5px
  `--color-accent-700` dot.
- Actions: "Save and close" primary, "Keep editing" secondary, and **"Discard" as a
  text-only link pushed to the far right**. The safe path is the easy one.

### 8d — Delete entry
- A **540px** modal over a `rgb(11 12 20 / 78%)` scrim — the heaviest in the app.
- There is **no red in the palette**, so risk is carried three other ways: a kicker that
  states the mechanism ("Permanent · not sent to the trash"), an inventory of what goes
  with it (readings, cards placed, note word count, follow-ups — each with a tabular
  count) plus the real vault path in mono, and a **typed confirmation** — the user types
  `delete` before the destructive button enables.
- The destructive button is disabled-styled until then; **"Keep entry" carries the accent**.
  A quiet "Or export it first" sits at the right of the action row.
- **If this proves too heavy in use:** drop the typed confirmation and add an undo toast
  instead. Do not add a red button — it would be the only red in the app.

---

## Interactions & behavior

The mockups are static. This is the behavior they imply.

**Navigation.** Five top-level views (Library, Spreads, Journal, Reference, Insights),
⌘1–⌘5. Settings replaces the nav with its own title bar and closes back to the previous
view. Nav items dim to `--tj-text-ghost` when the view has nothing to show.

**Selection.** One selected item per list; selection is expressed as `--tj-tint` +
a 35% accent ring + `--tj-glow-soft`, never as a bolder weight.

**Hover.** Rows: `--tj-tint-neutral-hover`. Cards: the inset ring lifts to
`rgb(145 132 217 / 60%)`. Primary buttons: `--tj-tint-hover` + `--tj-glow`.
Empty slots: accent-tinted fill and ring.

**Focus.** `:focus-visible { outline: 2px solid var(--color-accent); outline-offset: 2px }`
on every interactive element. Never the browser default.

**Card assignment (editor).** Click an empty slot → card picker. `⌥`-click a placed card
marks it reversed (rotate the face 180°, counter-rotate its label, append
"· reversed" in `--tj-text-accent-2` to the position label). Keys 1–9 assign to slots.

**Spread editing.** Drag to move; `⌥`-drag duplicates; arrows nudge; snap-to-grid is a
toggle. The Positions list order sets both the draw sequence and the print order.

**Destructive and lossy actions.** Two patterns only — the itemized confirm (8c) for
losing unsaved work, and the typed confirm (8d) for deleting a record. Both name the
artifact by title and both make the safe action the accented one.

**Transitions.** Modals fade the scrim in and lift the panel from `translateY(8px)` /
`scale(.98)` over 160ms `cubic-bezier(.2,.8,.2,1)`; the palette is faster, 120ms.
Hovers 120ms. Glows are not animated. Nothing else moves — this is a reading tool.

**Empty and error states.** Every list and grid needs three states: populated, empty
(7a/7b — explain what will fill it and offer the one action that does), and
filtered-to-nothing (7c — name the filters, offer to remove them, and suggest the likely
intended query). Errors that leave data readable (7d) degrade in place with a notice bar
and never block the view.

## State the app needs

- `view` — one of the five, plus `settings`.
- `selectedDeckId`, `selectedCardId`, `selectedEntryId`, `selectedSpreadId`,
  `selectedPositionIndex`.
- `entryDraft` — title, datetime, querent, reader, place, tags[], readings[] (each with
  spreadId, deckId, placements[{positionId, cardId, reversed}]), notes, followUps[].
  `isDirty` drives 8c; the itemized list in that modal is derived from this object.
- `filters` — `{ query, arcana, suit, tags[], deckId, querent, dateRange }`. The
  "Clear n filters" count is derived; do not hard-code it.
- `paletteOpen`, `shortcutsOpen`, `confirm: { kind, payload } | null`.
- `deckImageStatus` per deck — `{ expectedPath, foundCount, missingCount }` drives 7d.
- Derived, cached: card frequency, cadence by month, suit distribution, reversal rate,
  per-card position histogram, entries-per-card index. All of Insights and the right
  column of Reference read from these.

## Print

`Printed Entry.dc.html` is the print artifact and is already print-correct — it uses the
`doc-page` custom element (`doc-page.js`, included) with `margin="0.8in"` and flows the
entry across as many Letter pages as it needs. Do not rebuild it from the 4c mockup.

- Sizes are in **points**, not pixels: `h1` 30pt, section headings 16pt Newsreader 400,
  body 10pt, kickers 9pt, card labels 7pt, header/footer 8pt. Rules are 0.5pt.
- Ink comes from `--tj-paper-*`: ground `#f3f5fe`, card faces `#eef0f8`, body
  `#3f424d`, metadata `#595d6c`, folio `#75798c`, and exactly one accent step
  (`#5d5294`) for the kicker and the selected card.
- `slot="header"` and `slot="footer"` repeat on every page: the wordmark and entry
  number above, the entry title and querent/reader/place below.
- `break-inside: avoid` on `.spread`, `break-inside: avoid-page` on `.reading` — a
  spread must never split across a page break.
- Settings exposes Letter/A4 and an "Include card images" toggle; with images off, print
  names only.

## Assets

No image assets. All icons are inline Phosphor SVG paths (24×24 viewBox 0 0 256 256).
Fonts are Google Fonts — **Newsreader** (300, 400, italic 300) and **Inter**
(300, 400, 500, 600). Card art comes from the app's own deck database; the mockups use
name-only placeholders, which double as the correct no-image fallback.

## Files in this bundle

| File | What it is |
| --- | --- |
| `Tarot Journal Overhaul.dc.html` | All fourteen screens on one canvas, id-badged (3a, 4a–4c, 5a–5c, 6a, 7a–7d, 8a–8d) |
| `Printed Entry.dc.html` | The print artifact — paginated, print-correct as-is |
| `Design Tokens.dc.html` | Token reference: swatches, type specimen, the literal→token migration map, build rules |
| `tokens.css` | **The application token layer — port this** |
| `_ds/nocturne/styles.css` | The Nocturne design system stylesheet tokens.css sits on |
| `_ds/nocturne/readme.md` | Nocturne's own guide — read it for the reasoning behind the ramps and the rules |
| `support.js`, `doc-page.js` | Runtime the HTML references. Not part of the design; needed only to open the files locally |

To view: open any `.dc.html` file directly in a browser. The canvas file is wide — pan
and zoom out to see all fourteen screens.

## Open questions for the design side

1. **Card art** is untested against the real deck database — crop, bleed and the
   `.lighten` blend on dark grounds still need a pass with real scans.
2. **8d's typed confirmation** may be too heavy; the fallback is an undo toast.
3. **No narrow-window layout yet.** Everything is drawn at 1440 × 940. The sidebar fold
   below ~1180px and the 1280 × 800 case are undesigned.
4. **Only the entry has a paper counterpart.** A deck sheet, a spread definition and an
   insights report have not been designed.
