# Component Splitting Plan

Status: **NOT STARTED**
Created: 2026-03-23

## Overview

Four large React components need to be split into smaller sub-components for maintainability. This is a code quality improvement — nothing is broken. All state management stays in the parent; sub-components are presentational with callbacks.

### Conventions
- New sub-components go alongside their parent in the same directory (no new subdirectories)
- Sub-components share the parent's CSS file (class names already use BEM prefixes that avoid collisions)
- Safest extractions first within each parent
- After each extraction: open the relevant modal/editor, verify all fields render, edit values, save, confirm data persists

---

## 1. DeckEditModal.tsx (835 → ~450 lines)

**File:** `frontend/src/components/library/DeckEditModal.tsx`

The 19 `useState` calls, `isDirty` computation, `handleSave`, and query hooks stay in the parent.

### 1a. DeckEditGroups.tsx — LOW risk
**What:** Groups section (add/rename/recolor/delete)

Props:
- `groups: CardGroup[]`
- `onAddGroup: () => void`
- `onUpdateGroup: (groupId: number, data: { name?: string; color?: string }) => void`
- `onDeleteGroup: (groupId: number) => void`

Test: Add, rename, recolor, delete a group.

### 1b. DeckEditSuitCourtNames.tsx — LOW risk
**What:** Suit Names + Court Card Names sections, including the "Initialize Defaults" buttons

Props:
- `suitNames: Record<string, string>`
- `courtNames: Record<string, string>`
- `hasSuitedDeck: boolean`
- `hasTarot: boolean`
- `onSuitNamesChange: (names: Record<string, string>) => void`
- `onCourtNamesChange: (names: Record<string, string>) => void`
- `onInitSuitNames: () => void`
- `onInitCourtNames: () => void`

Note: The constants `TAROT_SUIT_DEFAULTS`, `PLAYING_SUIT_DEFAULTS`, `COURT_CARD_DEFAULTS`, and the `capitalize` helper can move with this component or be extracted to a shared constants file.

Test: Toggle deck types, verify suit/court sections appear/hide, edit names, initialize defaults.

### 1c. DeckEditFooter.tsx — LOW risk
**What:** Delete confirmation + save/cancel/export footer

Props:
- `deckId: number`
- `name: string`
- `confirmingDelete: boolean`
- `deleting: boolean`
- `saving: boolean`
- `isDirty: boolean`
- `onSave: () => void`
- `onClose: () => void`
- `onDelete: () => void`
- `onConfirmDelete: (confirming: boolean) => void`

Test: Save, cancel, delete flow (both confirm and cancel confirmation).

### 1d. DeckEditCustomFields.tsx — LOW-MEDIUM risk
**What:** Custom Fields section with drag-and-drop reordering

Props:
- `fields: DeckCustomField[]`
- `dragOverId: number | null`
- `onAddField: () => void`
- `onUpdateField: (fieldId: number, updates: { field_name?: string; field_type?: string; field_options?: string[] }) => void`
- `onDeleteField: (fieldId: number) => void`
- `onDragStart: (fieldId: number) => void`
- `onDragOver: (e: React.DragEvent, fieldId: number) => void`
- `onDrop: (e: React.DragEvent, fieldId: number) => void`
- `onDragEnd: () => void`

Note: Drag-and-drop logic uses refs (`draggingIdRef`, `localFieldsRef`) that must stay in the parent because the drop handler mutates state optimistically.

Test: Add field, rename, change type, delete, drag to reorder, verify dropdown field options.

---

## 2. CardEditModal.tsx (689 → ~500 lines)

**File:** `frontend/src/components/library/CardEditModal.tsx`

The complex form population effect (merging legacy JSON, table fields, deck definitions), `isDirty`, and `handleSave` stay in the parent. The `EditableField` interface needs to be exported from this file (or moved to `types/index.ts`).

### 2a. CardEditClassification.tsx — LOW risk
**What:** Archetype/rank/suit text inputs

Props:
- `archetype: string`
- `rank: string`
- `suit: string`
- `onArchetypeChange: (v: string) => void`
- `onRankChange: (v: string) => void`
- `onSuitChange: (v: string) => void`

Test: Type in archetype/rank/suit, verify they persist on save.

### 2b. CardEditFooter.tsx — LOW risk
**What:** Prev/next navigation + save/cancel buttons + error display

Props:
- `error: string | null`
- `saving: boolean`
- `nameIsValid: boolean`
- `cardIds: number[]`
- `currentIndex: number`
- `onSave: (navigateToId?: number) => void`
- `onClose: () => void`

Test: Prev/next navigation with save, save-and-close, cancel.

### 2c. CardEditCustomFields.tsx — MEDIUM risk
**What:** Custom field list with RichTextEditor for text fields and dropdown select for dropdown fields

Props:
- `fields: EditableField[]` (the visible/non-deleted list)
- `allFields: EditableField[]` (full array, needed to compute `realIndex`)
- `onAddField: () => void`
- `onUpdateField: (realIndex: number, key: 'field_name' | 'field_value', value: string) => void`
- `onRemoveField: (realIndex: number) => void`

Note: The `realIndex` lookup (`customFields.indexOf(field)`) means the sub-component needs access to the full unfiltered array to compute the correct index. Consider passing a mapping function or using field IDs instead of indices.

Test: Add field, edit name/value, delete, verify dropdown fields work, verify RichTextEditor renders.

---

## 3. ReadingEditor.tsx (657 → ~350 lines)

**File:** `frontend/src/components/journal/ReadingEditor.tsx`

The spread/deck change effects and `slotDecks` coordination stay in the parent. The `SlotDeckMap` type needs to be exported.

### 3a. VisualSpreadEditor.tsx — LOW risk
**What:** Already a separate function component in the same file (lines ~428-641). Just move to its own file.

This component already receives all data via props and does its own `useQueries` for deck cards. The `getCardImageStyle` helper moves with it.

Test: Select a spread with positions, verify visual canvas renders, select cards, toggle reversed.

### 3b. FreeformCardList.tsx — LOW risk
**What:** The "no spread" free-form card list with card name inputs/selectors, reversed checkbox, remove button, add button

Props:
- `cards: ReadingData['cards']`
- `deckCards: Card[]`
- `onUpdateCard: (idx: number, field: string, val: string | boolean) => void`
- `onAddCard: () => void`
- `onRemoveCard: (idx: number) => void`

Test: Use "No Spread" mode, add cards, select from dropdown, toggle reversed, remove cards.

### 3c. DeckSlotSelector.tsx — LOW risk
**What:** Multi-deck slot selector rows (one dropdown per deck slot)

Props:
- `deckSlots: DeckSlot[]`
- `slotDecks: SlotDeckMap`
- `decks: Deck[]`
- `useAnyDeck: boolean`
- `onSlotDeckChange: (slotKey: string, deckId: number | null) => void`

Test: Select a multi-deck spread, verify slot selectors appear, change deck per slot, verify card list updates.

---

## 4. EntryEditorModal.tsx (575 → ~420 lines)

**File:** `frontend/src/components/journal/EntryEditorModal.tsx`

`handleSave`, `isDirty`, and form population effects stay in the parent.

### 4a. EntryEditorTagSelector.tsx — LOW risk
**What:** Tag checkbox grid

Props:
- `allTags: Tag[]`
- `selectedTagIds: number[]`
- `onToggleTag: (tagId: number) => void`

Test: Toggle tags, verify they persist on save.

### 4b. EntryEditorDateLocation.tsx — LOW risk
**What:** Date/time radio (now/custom) + datetime-local input + location text input

Props:
- `dateMode: 'now' | 'custom'`
- `readingDatetime: string`
- `locationName: string`
- `onDateModeChange: (mode: 'now' | 'custom') => void`
- `onDatetimeChange: (datetime: string) => void`
- `onLocationChange: (location: string) => void`

Test: Toggle now/custom, set datetime, type location, verify on save.

### 4c. EntryEditorQuerentReader.tsx — LOW risk
**What:** Querent multi-select (add/remove) + reader dropdown

Props:
- `profiles: Profile[]`
- `querentIds: number[]`
- `readerId: number | null`
- `onQuerentIdsChange: (ids: number[]) => void`
- `onReaderIdChange: (id: number | null) => void`

Test: Add multiple querents, remove one, change reader, verify on save.

---

## Future Follow-Up

All three modals (DeckEditModal, CardEditModal, EntryEditorModal) have near-identical tag checkbox sections. After splitting, these could be consolidated into a shared `TagCheckboxGroup` component in `components/common/`.

---

## Summary

| # | Parent | Sub-Component | Risk | Lines Extracted |
|---|--------|--------------|------|----------------|
| 1 | DeckEditModal | DeckEditGroups | LOW | ~55 |
| 2 | DeckEditModal | DeckEditSuitCourtNames | LOW | ~75 |
| 3 | DeckEditModal | DeckEditFooter | LOW | ~48 |
| 4 | DeckEditModal | DeckEditCustomFields | LOW-MED | ~92 |
| 5 | CardEditModal | CardEditClassification | LOW | ~30 |
| 6 | CardEditModal | CardEditFooter | LOW | ~33 |
| 7 | CardEditModal | CardEditCustomFields | MEDIUM | ~58 |
| 8 | ReadingEditor | VisualSpreadEditor (move) | LOW | ~214 |
| 9 | ReadingEditor | FreeformCardList | LOW | ~46 |
| 10 | ReadingEditor | DeckSlotSelector | LOW | ~24 |
| 11 | EntryEditorModal | EntryEditorTagSelector | LOW | ~22 |
| 12 | EntryEditorModal | EntryEditorDateLocation | LOW | ~43 |
| 13 | EntryEditorModal | EntryEditorQuerentReader | LOW | ~64 |
