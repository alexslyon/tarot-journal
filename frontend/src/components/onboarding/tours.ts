/** Guided-tour definitions for the Getting Started checklist.
 *
 *  Deliberately terse: each tour is 3–4 steps of one or two
 *  sentences, always skippable, never blocking — the guide card sits
 *  at the bottom while the user actually does the thing. A step's
 *  `selector` (a [data-guide] attribute) gets a glow ring when the
 *  element exists; steps for controls inside modals simply wait until
 *  the modal opens.
 */

export interface TourStep {
  text: string;
  /** Value of the target's data-guide attribute, if any */
  target?: string;
}

export interface Tour {
  id: 'deck' | 'spread' | 'entry';
  steps: TourStep[];
}

export const TOURS: Record<Tour['id'], Tour> = {
  deck: {
    id: 'deck',
    steps: [
      {
        target: 'import-deck',
        text: 'Import brings a folder of card images into your library — one image per card.',
      },
      {
        target: 'import-folder',
        text: "Point it at your deck's image folder. Filenames become card names.",
      },
      {
        target: 'import-preset',
        text: "A preset matching the deck type names cards properly (c01 → Ace of Cups). “None” keeps the raw filenames.",
      },
      {
        target: 'import-scan',
        text: 'Scan Folder previews every detected card before anything is saved.',
      },
    ],
  },
  spread: {
    id: 'spread',
    steps: [
      {
        target: 'new-spread',
        text: 'New starts a blank layout canvas.',
      },
      {
        target: 'add-position',
        text: 'Add Position drops a card slot. Drag to place it; the corner handle resizes; right-click for label, rotation, and layering.',
      },
      {
        target: 'snap-grid',
        text: 'Snap to Grid keeps layouts tidy — and Fit & Center reframes the canvas around your spread.',
      },
      {
        text: "Name it and save. It's immediately available when recording readings.",
      },
    ],
  },
  entry: {
    id: 'entry',
    steps: [
      {
        target: 'new-entry',
        text: '+ New opens a fresh journal entry.',
      },
      {
        text: 'Pick a spread and a deck, then click each position to set its card. Right-click a placed card to mark it reversed.',
      },
      {
        text: 'Notes are rich text, and the querent/reader come from your Profiles.',
      },
      {
        text: 'Save — the cards appear laid out just as they were on the table. Follow-up notes can be added any time after.',
      },
    ],
  },
};
