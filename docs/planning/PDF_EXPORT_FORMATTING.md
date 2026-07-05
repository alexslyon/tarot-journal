# Journal Entry PDF Export — Formatting Refinements
*June 2026*

The PDF export feature is built and functional. This document specifies formatting fixes and aesthetic improvements to bring the output up to a polished, professional standard. All changes are CSS/template-level — no data model or API changes required.

---

## Bug Fixes

### 1. Eliminate standalone title page
The entry header (title, date, location, querent, reader) must appear at the top of the first content page, above the first spread image — not on its own page. Currently some exports produce a nearly empty first page with only three lines of text.

### 2. Cap single-card spread image size
For spreads with very few cards (especially 1-card daily draws), the card image renders far too large. Individual card images in the spread display should have a maximum height — roughly the size they'd appear in a 5-card spread. The exact pixel cap needs testing, but aim for card images no taller than about 200mm. A single card should be centered horizontally and vertically within a reasonably sized area, not blown up to fill the page.

### 3. Eliminate standalone "Card Details" header page
The "Card Details" section header must not be followed by a page break. It should appear on the same page as the first card's detail block. If there isn't room for the header plus at least one card's content, move both to the next page together.

### 4. Remove "CUSTOM FIELDS" label
The "CUSTOM FIELDS" header above each card's fields is visual noise. Remove it entirely. The individual field names (Keywords, Description, Category, etc.) are sufficient labels.

### 5. Prevent orphan rows in key table
The position key table must not split so that one or two rows end up alone on a new page. Apply a CSS `break-inside: avoid` rule on the table, or at minimum on groups of rows. If the table doesn't fit on the current page, move the entire table to the next page.

### 6. Fix correspondence breakdown inline text rendering
The correspondence breakdown must use the pill/badge styling consistently across all exports. Currently some exports render values and counts as inline unstyled text (e.g. "Suit Cups 3 Pentacles 3 Swords 3"), making it nearly unreadable. Every value-count pair should be a styled pill. If a row has too many pills to fit on one line, they should wrap cleanly — not run together as a single line of text.

### 7. Add visual separation between readings in correspondence breakdown
When an entry has multiple readings, each reading's breakdown section needs a clear divider — a horizontal rule and/or additional spacing. Currently they flow together with no visual boundary.

### 8. Add "Notes" section header
The journal entry notes content at the end of the document needs a clear "Notes" section header and vertical spacing separating it from whatever section precedes it (card details or correspondence breakdown).

---

## Aesthetic Improvements

### Typography hierarchy
Establish a clear size/weight scale throughout the document:

| Element | Size | Weight | Notes |
|---|---|---|---|
| Entry title | 24pt | Bold | Top of document |
| Spread name | 18pt | Bold | Above each spread image |
| Section headers (Key, Correspondence Breakdown, Card Details, Notes) | 14pt | Bold | |
| Card name in details | 13pt | Bold | |
| Field labels (Keywords, Description, etc.) | 10pt | Regular, medium grey (#666) | NOT bold — labels should recede, values should be prominent |
| Field values / body text | 10pt | Regular, dark (#222) | |
| Metadata labels (DATE, LOCATION, etc.) | 8pt | Small caps, medium grey | |
| Metadata values | 10pt | Regular, dark | |

### Header metadata block
Restyle the DATE / LOCATION / QUERENT / READER block as a compact two-column grid:

```
DATE  2026-06-20 10:58          LOCATION  Aberdeen, Maryland, US
QUERENT  Lysander               READER  Lysander
```

Labels in small caps, lighter color. Values in regular weight. Tight vertical spacing. A thin horizontal rule below the block separating it from the spread content. The whole block should feel like a letterhead, not a form.

### Thin horizontal rules between cards
In the Card Details section, use a light hairline rule (0.5pt, light grey #ddd) between card blocks instead of heavy dividers. This provides visual separation without eating vertical space.

### Card detail layout — compact
Restructure each card detail block for density:

- Card name as a bold header line
- Thumbnail floated left (slightly larger than current, with a subtle 1px #ddd border)
- Short fields (Element Number, Symbol, Category, or similar single-value fields) grouped horizontally on one line: `Element Number: 5  ·  Symbol: B  ·  Category: Metalloids`
- Keywords on the same line as the label: `Keywords: Seeker, Duality, Alter-ego, Self-discovery`
- Description as a regular paragraph below
- Target: 2–3 cards per page instead of 1–2

### Archetype notes within card details
When archetype reference notes are included, they appear under a subtle "ARCHETYPE NOTES" subheader (smaller, grey, small caps — similar to the metadata labels). Each source is a bold subheader with its fields below. Same compact layout as custom fields.

### Position key table
- Alternating row shading: white and very light grey (#f7f7f7) on even rows
- KEY column: center-aligned, slightly narrower
- POSITION column: left-aligned
- CARD column: left-aligned, bold

### Correspondence breakdown pills
- Slightly more horizontal padding inside each pill (at least 8px left/right)
- More spacing between pills (at least 6px gap)
- The count number should be a slightly lighter shade or smaller size than the label text, so "Spades" and "3" don't read as one blob
- If a row has many pills (more than about 5–6), allow wrapping with consistent spacing
- For very dense rows (Kabbalah with Hebrew text), consider stacking vertically rather than wrapping pills

### Page numbers
Small centered page numbers in the footer of every page. Format: just the number, no "Page X of Y." Font size 8pt, medium grey.

### Spread image framing
Add a very subtle container around the spread image area — either a light background panel (#fafafa) with 15px padding or a thin border (#eee, 1px). This visually grounds the card images and separates the spread from the key table below.

### Astrological chart cleanup
The Kerykeion SVG includes detailed sidebar information (cusp listings, aspect grid) that is redundant with the summary table below the chart. If possible, render only the wheel portion of the SVG without the sidebars, since the summary table provides the same data in a more readable format. If cropping the SVG is too complex, leave as-is for now — the current rendering is functional.

---

## Page Break Strategy

Apply intelligent page breaks throughout:

- **Never break inside:** a card detail block, the key table (unless it's very long), a single reading's correspondence breakdown
- **Prefer breaks before:** spread name headers, "Card Details" section header, "Correspondence Breakdown" section header, "Notes" section header, "Astrological Event Chart" section header
- **Avoid widows:** don't leave a section header at the bottom of a page with no content below it; don't leave one or two orphan rows from a table on a new page

CSS rules to apply:
```css
.card-detail-block { break-inside: avoid; }
.key-table { break-inside: avoid; }
.reading-breakdown { break-inside: avoid; }
.section-header { break-after: avoid; }
```

---

## Summary of Changes by Section

| Section | Fixes | Aesthetic |
|---|---|---|
| Header | Inline with content (no title page) | Small caps labels, two-column grid, letterhead feel |
| Spread image | Cap max card size | Light background container |
| Position key | Prevent orphan rows | Alternating row shading, centered KEY column |
| Correspondence breakdown | Fix inline text rendering, separate readings | Better pill spacing, count styling |
| Card details | Remove "CUSTOM FIELDS" label, remove standalone header page | Compact layout, float thumbnails, group short fields, lighter labels |
| Notes | Add section header | Standard body text styling |
| Astro chart | — | Crop SVG sidebars if feasible |
| Global | — | Typography hierarchy, page numbers, thin rules, page break strategy |
