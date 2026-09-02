# Tarot Journal

A desktop app for serious tarot practitioners: catalog your cartomancy
decks and keep a visual reading journal. Built with Electron, React,
and a Python/Flask backend, with an optional iPhone companion app.

Tarot Journal supports your practice rather than replacing it. It
won't draw cards for you or interpret your readings — it gives you an
organized, beautiful place to store your collection and record your
readings with the cards laid out just as they were on the table.

## What it does

- **Deck Library** — store and browse tarot, Lenormand, oracle,
  playing-card, and custom deck types with full-size scans, metadata,
  custom fields, tags, and powerful search across the whole collection
- **Visual Reading Journal** — record readings with cards arranged in
  their spread positions (reversals, clarifiers, multi-deck spreads),
  rich-text notes, querent/reader profiles, and timestamped follow-up
  notes as a reading unfolds
- **Spread Designer** — drag-and-drop editor for custom layouts,
  including multi-deck spreads and per-position meanings
- **Reference Library** — your own cartomancy reference, built from
  the sources you own: per-card notes from any number of books
  (organized by source), card combination meanings, plus sections for
  astrology (signs, planets, decans), Kabbalah (Tree of Life), suits,
  ranks and numerology, and chakras — cross-linked with your cards
- **Correspondence systems** — configurable card↔astrology↔letter
  assignment sets (Golden Dawn, Thoth, and friends), birth cards and
  name cards with per-role color coding, and natal/event astrology
  charts for profiles and entries
- **Insights** — charts of your reading rhythm, most-drawn cards, tag
  trends, and deck/spread usage
- **AI assistants (optional)** — bring your own Anthropic API key and
  the Scribe imports reference texts from your books into the right
  cards, combinations, and reference entries; prompt templates are
  fully editable
- **iPhone companion** (`ios/`) — journal, reference library, favorite
  decks, and stats in your pocket, synced over home Wi-Fi; quick entry
  at the reading table pushes back to the desktop
- **PDF export, backups, sharing** — formatted journal-entry PDFs,
  full database backups with optional images, and shareable JSON
  exports for decks and spreads

Everything is stored locally in SQLite. No accounts, no cloud, no
telemetry; the optional AI features call Anthropic's API with your
key, and everything else never leaves your machine.

## Requirements

- **Node.js** 20+
- **Python** 3.9+
- macOS is the primary platform (Windows/Linux mostly work but get
  less testing). The iPhone app additionally needs Xcode.

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/lysander8cha/tarot-journal.git
   cd tarot-journal
   ```

2. **Python environment and dependencies:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate        # macOS / Linux
   pip install -r requirements.txt
   ```

   *PDF export on macOS* uses WeasyPrint, which needs pango/cairo at
   runtime:
   ```bash
   brew install pango cairo glib gdk-pixbuf libffi
   ```
   (On Debian/Ubuntu: `apt install libpango-1.0-0 libcairo2
   libgdk-pixbuf2.0-0`.)

3. **Node dependencies** (root and frontend):
   ```bash
   npm install
   cd frontend && npm install && cd ..
   ```

4. **Run it:**
   ```bash
   npm run start      # build the frontend, launch the app
   npm run dev        # development mode (hot reload)
   ```

### Make a double-clickable app (macOS)

Once the install steps above work (both `npm install`s done and the
Python environment set up — the packager borrows this machine's
`python3` to build the app's own), you can build a normal Mac app so
you never touch a terminal again:

```bash
npm run make:app
```

This packages the app and installs a self-contained Python
environment inside the bundle. The result lands at:

```
out/Tarot Journal-darwin-arm64/Tarot Journal.app
```

Drag it into `/Applications` (or anywhere) and double-click. Notes:

- It uses the same data as the dev version (`~/Library/Application
  Support/TarotJournal`) — it *is* the app, just launchable normally.
  Don't run it and `npm run dev` at the same time; they share a port.
- It's a snapshot of the code at build time: after pulling updates,
  rerun `npm run make:app` and replace the old copy.
- The bundled Python environment is tied to the machine that built
  it — build the app on the machine that will run it, rather than
  copying the .app to another computer.

### Other useful launch modes

- `npm run scratch` — launch against a **throwaway database** (fresh
  every run, own port, real data untouchable). Ideal for trying
  things risk-free or seeing the first-run experience;
  `KEEP_SCRATCH=1 npm run scratch` keeps the scratch data between
  runs.

### Optional setup

- **AI assistants:** Settings → AI Assistant → paste an Anthropic API
  key. Without a key, everything else works normally.
- **iPhone companion:** see `ios/` — the project is generated with
  [XcodeGen](https://github.com/yonaskolb/XcodeGen) (`cd ios &&
  xcodegen`), built with Xcode, and paired from the desktop app's
  Settings → General → Phone Sync.

## Quick start

**Import a deck:** Library tab → Import → choose the folder of card
images → pick the preset matching the deck type → adjust names →
Import. JPG/PNG/GIF/WebP are supported; thumbnails generate
automatically.

**Record a reading:** Journal tab → New Entry → title, date, querent →
pick a spread and deck → click positions to assign cards (right-click
options for reversals) → write your notes → Save. Entries can hold
several readings, and follow-up notes can be added any time after.

**Design a spread:** Spreads tab → New Spread → add positions on the
canvas, drag/resize them, label each position → Save. It's immediately
available when recording readings.

**Build your reference library:** Settings → Reference Sources to
register the books you use, then attach per-card notes in the
Reference tab (or let the Scribe import a whole book's worth at once).

## The tabs

| Tab | What lives there |
|---|---|
| **Library** | Deck collection, card browsing/editing, search, batch edits |
| **Spreads** | The spread designer |
| **Journal** | Entries, readings, follow-ups, search and filters |
| **Profiles** | Querents and readers, with birth data for charts and birth/name cards |
| **Reference** | Card notes by source, combinations, astrology, Kabbalah, suits/ranks/numerology, chakras |
| **Insights** | Charts and trends across your journal |
| **Settings** (gear) | Appearance, defaults, AI, backups, tags, deck types, correspondences, reference sources, import presets, phone sync |

Browser-style back/forward buttons (⌘[ / ⌘]) navigate your history
across tabs, and ⌘K opens a command palette for jumping anywhere.

## Data storage

| Location | Contents |
|---|---|
| `~/Library/Application Support/TarotJournal/` | The SQLite database and automatic backups |
| `.thumbnail_cache/` | Auto-generated image thumbnails (safe to clear) |
| Your deck image folders | Original scans, referenced in place — never copied or moved |

The database runs in WAL mode for crash safety. Settings → Backup &
Restore makes full ZIP backups (optionally including images) and
restores them with an automatic safety backup first.

## Troubleshooting

- **App won't start** — check `python3 --version` (3.9+) and `node
  --version` (20+); make sure the venv lives at `.venv/` in the
  project root with requirements installed.
- **Images missing** — the app references your image files where they
  are; if a folder moved, re-point the deck at it in the deck editor.
- **First view of a deck is slow** — thumbnails are being generated;
  it's one-time per deck.
- **Phone won't pair** — both devices on the same Wi-Fi, desktop app
  open, phone sync enabled in Settings (restart the desktop app after
  enabling). The phone's Settings tab has a "Test connection" button
  that diagnoses the rest.
