# Planning: iOS Companion App

*Drafted 2026-09-01. Status: **Phases 0–3 shipped 2026-09-03.**
Browsing, quick entry with offline outbox, bundled Newsreader,
pinch-zoom spreads and card viewer. Remaining ideas (unscheduled):
home-screen widget (skipped — 7-day install expiry makes widgets die
weekly on a free account), editing phone-created entries' notes,
iCloud transport (needs the paid developer account), headless sync
daemon on the Mac.*
*2026-09-02: worked into a concrete build plan (see "Build plan"
below) after auditing the codebase; corrections noted inline.*

Build notes from Phase 1 (2026-09-02):

- The iOS app lives in `ios/` (SwiftUI + GRDB; `.xcodeproj` generated
  by `xcodegen` from `ios/project.yml`, signing team baked in there).
- Screens shipped: journal list (querent filter, search,
  pull-to-refresh) → entry detail with the 2D spread-layout renderer
  (reversals, sideways cards, clarifiers), reference search → source
  texts per archetype, favorite-deck galleries, Insights charts,
  Settings with Bonjour pairing.
- Sync: pull on app-foreground + pull-to-refresh; images cached on
  the phone permanently after first fetch.
- Gotcha: resolving a Bonjour service to an IP had to use Foundation's
  NetService — NWConnection.currentPath doesn't reliably expose the
  resolved address.
- The 7-day free-account reinstall ritual applies: plug in, ⌘R from
  Xcode when the app stops launching.

## Concept

A small native iPhone app that complements the desktop Tarot Journal rather than replacing it. The Mac app remains the authoritative home of the library and all heavy features (deck imports, PDF export, astrology, correspondence management, the Scribe). The phone handles the things you'd actually want in your hand at the reading table or away from your desk.

## Scope

**In:**

- **Browse journal** — read past entries with card images arranged in their spread layout, querent/reader info, and notes.
- **Quick reading entry** — log a new reading on the phone: pick deck, spread, cards, jot notes. Optimized for speed at the table; entries sync back and can be polished on the desktop later.
- **Reference lookup** — search card meanings and correspondence entries across reference sources (the `archetype_source_entries` data).
- **Stats/trends** — the existing charts (card frequency, suit distribution, etc.) in read-only phone form.
- **Favorite decks** — browse a hand-picked subset of decks marked as favorites on the desktop, so the phone only carries a few decks' images rather than the whole multi-gigabyte library.

**Out (stays desktop-only):** deck importing/scanning, spread designer, correspondence editing, PDF/Anki/LLM export, astrology charts, the Scribe, profile management beyond picking a querent.

## Sync: local Wi-Fi first, iCloud later

**Decision (2026-09-01):** start with **local Wi-Fi sync** — the phone talks directly to the desktop app's backend when both devices are on the home network. This avoids the Apple Developer Program fee ($99/yr), which is required for iCloud/CloudKit. The app will be built and installed with a **free Apple developer account**, which has two known trade-offs: no CloudKit, and installs expire after 7 days, requiring a re-install from Xcode (or automated re-signing via AltStore). If the weekly ritual grows old, upgrading to the paid tier later swaps the sync transport without rewriting the app.

How Wi-Fi sync works in practice:

- The Flask backend already runs a local web server (port 5678, currently loopback-only). It gains a small set of **sync endpoints** and starts listening on the local network (with a pairing token so only the phone can connect). The phone pulls changes when opened on home Wi-Fi and pushes any entries logged while away.
- The phone keeps a **full local copy** of its subset of data, so everything works offline; sync just reconciles when back in range of the Mac (Mac must be awake with the app running).
- Change tracking is still needed: each synced table needs a stable unique ID and a last-modified timestamp (`updated_at` exists on some tables already; others need it added). This work carries over unchanged to a future iCloud upgrade.
- **Not everything syncs.** Only the data the phone needs: journal entries + readings, spreads, tags, profiles (names only), reference entries, and favorited decks' card list + images. Reference data is essentially one-way (desktop → phone); journal entries are two-way (phone can create them).
- **Conflict handling can be simple.** One person, two devices: "most recent edit wins" is fine, and new-entry creation (the phone's main write) can't conflict at all.

**iCloud upgrade path:** join the paid program, add CloudKit as the transport on both sides, retire the Wi-Fi endpoints (or keep them as a fallback). The data model, change tracking, and app screens all remain the same.

## Images

The full scan library (multi-GB, ~15 MB per card for some decks) must not go to the phone. Plan:

- Desktop generates **phone-sized derivatives** for favorited decks only — the existing `thumbnail_cache.py` already does almost exactly this. *(Size decision 2026-09-02: not a minimal thumbnail — large enough to look good full-screen on the phone: ~1000×1500 JPEG, roughly 150–300 KB per card.)*
- A 78-card deck at that size is ~15–25 MB; ten favorite decks stay in the low hundreds of MB — fine for a modern phone.
- Derivatives are fetched over the Wi-Fi sync connection, keyed to card
  IDs. *(Correction 2026-09-02: an earlier draft said "via iCloud" —
  leftover from before the Wi-Fi-first decision.)*

## Desktop prerequisites (do these first, in the existing app)

1. **Add a "favorite" flag to decks** — doesn't exist yet (no favorites concept anywhere in the codebase as of this writing). Small change: one column, a toggle in the deck UI, a filter.
2. **Audit IDs and timestamps** — ensure every synced table has `updated_at` maintained on writes; add where missing.
3. **Build the sync layer** in the Python backend: change tracking plus a handful of new `/api/sync/...` endpoints, and open the server to the local network with a pairing token (currently loopback-only, CORS pinned to localhost).
4. **Phone-derivative generation** for favorited decks.

## iOS app itself

- **Technology: SwiftUI** (Apple's native UI framework) is the recommended route for a companion this small — no cross-platform overhead, and first-class CloudKit integration when the iCloud upgrade happens. React Native was considered (would reuse some desktop UI thinking) but its CloudKit story is weak, and the phone screens will be redesigned from scratch anyway.
- **Local storage:** SQLite (or SwiftData backed by it) mirroring the synced subset of the schema.
- **Screens (v1):** journal list → entry detail (spread layout view), new-entry flow, reference search → card detail, stats, deck gallery for favorites, settings.
- The spread-layout view is the one genuinely custom UI piece — it must render the 2D positional layouts from the `spreads` data on a small screen (likely pinch-zoomable).

## Rough phasing

1. **Phase 0 — desktop prep:** favorites flag, timestamp audit, derivative generation. No visible iOS work yet.
2. **Phase 1 — one-way sync + read-only app:** journal, reference, stats, favorite decks all viewable on the phone. This alone is most of the daily value.
3. **Phase 2 — quick entry:** phone can create entries; two-way sync for the journal tables.
4. **Phase 3 — polish:** stats charts, spread-layout refinements, widget/complications if desired.

## Open questions

- Weekly re-install with the free account: plug-into-Xcode manually, or set up AltStore to automate it?
- Should quick entries created on the phone be marked "draft" for desktop review, or be full entries immediately?
- Reference lookup: sync *all* sources' entries (~a few MB of text, simplest) or let the user pick sources?
- Does the journal need to be editable on the phone (Phase 2+), or is create-only enough?

---

## Build plan (2026-09-02)

Grounded in a codebase audit. Facts that shape the design:

- **Timestamps today:** `journal_entries` has `updated_at` and the
  update path maintains it. `archetype_source_entries` and
  `entity_source_notes` have it too. `spreads`, `profiles`, `decks`,
  `cards`, tags, and `combination_meanings` don't.
- **Entry shape:** an entry is an aggregate — `journal_entries` row +
  `entry_readings` (cards as JSON) + `entry_tags` + `entry_querents`.
  The children have no timestamps, but every write path touches the
  parent, so the **sync unit is the whole entry aggregate**, keyed by
  the parent's `updated_at`. No child-table change tracking needed.
- **Data sizes (live DB):** 313 entries, ~13k archetype source
  entries, ~10.7k cards. Everything except entries and source entries
  is small enough to sync as a **full snapshot** each time — which
  makes deletions free (phone mirrors the snapshot) and avoids
  tombstones entirely. For the two big tables: delta by `updated_at`,
  plus a full ID list each pull (a few KB) so the phone can prune
  deletions. **No tombstone machinery anywhere.**
- **Server:** Flask binds 127.0.0.1 only; CORS pinned to localhost.
  Opening to the LAN is an explicit opt-in setting, scoped: the sync
  endpoints get bearer-token auth; everything else stays
  loopback-only even when the LAN listener is on.
- **Images:** `thumbnail_cache.py` already renders arbitrary sizes
  with mtime-keyed caching — phone derivatives are a new size preset
  (~500×750 JPEG) plus a batch endpoint, not new machinery.

Gaps the original draft missed, now designed in:

1. **Deletion propagation** — solved by snapshot-tables + ID-list
   pruning (above), no tombstones.
2. **Phone-created entry identity** — the phone writes entries
   offline, so pushes need idempotency: add a nullable `sync_uuid`
   column to `journal_entries`; the phone generates it, the desktop
   dedupes on it. Desktop-created entries never need one.
3. **Mac availability** — sync requires the desktop app running and
   the Mac awake. Acceptable for v1; a headless launchd backend is a
   possible later comfort, noted as an open question.
4. **Discovery** — the phone shouldn't need a typed IP: advertise the
   sync service over Bonjour/mDNS (python `zeroconf` on the desktop,
   `NWBrowser` on the phone), with manual IP entry as fallback.

### Decisions on the open questions

- **Weekly re-install:** start with plugging into Xcode manually
  (zero extra moving parts); adopt AltStore only if the ritual grates.
- **Phone entries are full entries**, not drafts — but tagged with an
  automatic "logged on phone" entry tag so they're easy to find and
  polish on the desktop. No review gate.
- **Reference sync: all sources' entries.** A few MB of text over
  home Wi-Fi is nothing; source picking is complexity with no payoff.
- **Phone editing:** v1 read-only; v2 create-only plus editing the
  notes of entries the phone itself created. Full editing only if
  genuinely missed.

### Phase 0 — desktop prep (in this repo, testable like any feature)

1. **Deck favorites** — `favorite` column on decks (additive
   migration), star toggle in the deck list, "Favorites" filter.
2. **Sync identity** — `sync_uuid` on `journal_entries`;
   confirm/repair `updated_at` bumping on every entry write path
   (SQLite trigger as a safety net).
3. **Phone derivatives** — phone-size preset in `thumbnail_cache`,
   `/api/sync/card-image/<id>` endpoint; derivatives generate lazily on
   first request and persist in the cache (first sync of a new
   favorite deck is ~30s slower, then never again).
4. **Sync API v1 (read-only)** —
   `/api/sync/manifest` (per-table counts + max updated_at, so the
   phone skips unchanged tables), `/api/sync/snapshot/<table>` for the
   small tables, `/api/sync/entries?since=` + ID list,
   `/api/sync/source-entries?since=` + ID list.
5. **Pairing & LAN exposure** — Settings toggle "Enable phone sync":
   binds a second listener on the LAN interface, shows a 6-digit
   pairing code; the phone exchanges it for a long-lived bearer token;
   Bonjour advertisement. Sync routes require the token; the rest of
   the API refuses non-loopback callers.

Everything in Phase 0 is verifiable with the existing pytest +
Playwright rhythm, plus curl-from-another-interface checks for the
auth scoping.

### Phase 1 — the read-only phone app

1. **Environment** (needs the user): install Xcode, sign in with the
   free Apple ID, enable Developer Mode on the iPhone. Project
   scaffold: SwiftUI + GRDB (plain SQLite mirroring the synced
   subset — closer fit than SwiftData for mirroring a server schema).
2. **Pairing + sync client** — Bonjour browse → pairing-code screen →
   token in the keychain; pull engine implementing the manifest/
   snapshot/delta protocol; image fetch with local file cache.
3. **Screens** — journal list (search + querent filter), entry detail
   with the **spread-layout renderer** (the one custom piece:
   positioned percent-based layout, pinch-zoom), reference search →
   card detail (source texts), favorite-deck gallery, simple stats,
   settings/sync status.
4. **Verification story:** the iOS Simulator runs on this Mac — the
   app can be built, driven, and screenshotted there against the real
   desktop backend without touching the phone. Device installs are
   the user's part (plug in, trust, 7-day refresh).

### Phase 2 — quick entry + push

1. Entry composer optimized for the table: querent → deck (favorites)
   → spread → per-position card picker (search, reversal toggle) →
   notes. Single-deck readings only; clarifiers and multi-deck slots
   stay desktop.
2. `/api/sync/push-entry` accepting the aggregate with `sync_uuid`
   idempotency; the "logged on phone" tag applied server-side.
3. Offline queue on the phone; push-then-pull on reconnect.

### Phase 3 — polish & options

Stats charts (Swift Charts), spread-layout refinements, optional
widget; revisit iCloud (paid account) — the transport swaps, data
model and screens stay; revisit headless sync daemon.

### Sequencing note

Phase 0 is ordinary desktop work and can start any time; nothing in
it is wasted even if the iOS half stalls (favorites and derivative
generation are useful on their own). Phase 1 should start only when
the user has Xcode installed and an afternoon for the first device
install. Phases are separately shippable; the natural first
milestone is "read last night's reading on the phone at breakfast."
