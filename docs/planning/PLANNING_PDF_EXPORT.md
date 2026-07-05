# Journal Entry PDF Export — Planning Document
*Decisions made in design review session, March 2026*

This document covers the design of the journal entry PDF export feature.

---

## Overview

Export individual journal entries as formatted PDF files suitable for printing or archiving. The PDF includes the reading's visual spread layout with card images, card and position information, notes, and optionally correspondence breakdowns, custom field data, archetype reference info, and the astrological event chart.

---

## Dependencies

- **Correspondences feature** — needed for correspondence breakdown option
- **Archetypes feature** — needed for archetype field info option
- **Astrological Chart Integration** — needed for event chart option
- The feature can be built incrementally — the core export (spread image, key, notes) works without any of the optional dependencies. Optional sections are hidden from the export dialog if their underlying feature isn't implemented yet.

---

## Trigger

An "Export as PDF" button in the entry viewer, alongside existing entry controls. Opens an export options modal before generating.

---

## Export Options Modal

The modal allows the user to configure what the PDF includes before generating it.

### Reading selection
If the entry has multiple readings, a checklist of all readings (labelled by spread name). All checked by default. At least one must be selected.

### Always included (not toggleable)
- Querent name(s) and Reader name
- Spread image with card images and position labels
- Position key (position names + card names)
- Journal entry notes (rich text content)
- Follow-up notes

### Optional sections (individually toggleable)

**Correspondence Breakdown**
- Master toggle: "Include correspondence breakdown"
- When enabled, sub-toggles for each correspondence type (same checklist as the Reading Breakdown feature)
- Defaults to the same toggle state the user has saved for this entry's Reading Breakdown, if any — otherwise all present correspondences enabled

**Card Custom Fields**
- Master toggle: "Include card custom fields"
- When enabled, a checklist of all custom fields defined on the deck(s) used in the selected readings
- Each field individually selectable
- All checked by default

**Archetype Reference Fields**
- Master toggle: "Include archetype reference info"
- When enabled, a checklist of the Notes fields that exist for the archetypes of cards used in this reading
- Each field individually selectable
- All checked by default

**Astrological Event Chart**
- Single toggle: "Include astrological chart"
- Only available if the entry has reading_datetime and location data
- Greyed out with explanation if data is missing

### Generate button
"Generate PDF" button at the bottom. Shows a loading indicator during generation. When complete, triggers a download or save dialog.

---

## PDF Layout

### Page setup
- Size: A4 (210 × 297 mm)
- Orientation: Portrait
- Background: White / light (print-friendly)
- Text color: Dark grey/black
- Margins: 20mm all sides
- Font: Clean sans-serif (system font or bundled)

### Page structure

#### Page 1: Header + Spread

**Header block:**
- Entry title (large, prominent)
- Reading date and time
- Location (if present)
- Querent name(s) and Reader name
- Tags (if any)

**Spread image:**
- Rendered as the spread layout with card images placed in their positions
- Position labels visible on or near each card position
- Scaled to fit the page width while maintaining aspect ratio
- If the spread is very wide/landscape-oriented, it may need to be rotated or scaled down — handle gracefully

If the entry has multiple selected readings, each reading gets its own spread image section. If this overflows page 1, it continues onto subsequent pages.

#### Position Key (follows spread image)

A table or structured list for each reading:
- Reading header: spread name, deck name
- One row per position: position label, card name, reversed status (if applicable)

#### Correspondence Breakdown (if enabled)

Same table format as the Reading Breakdown feature but rendered for print:
- One row per correspondence type
- Columns are distinct values with counts
- Text labels (not glyphs) for PDF — even if the app has glyphs by then, text is more reliable for PDF rendering
- If multiple readings are selected, show per-reading breakdowns and an aggregate, matching the Reading Breakdown feature's tab structure

#### Card Detail Section (if custom fields or archetype fields enabled)

For each card in the reading(s), a card detail block:
- Card name (and deck name if multi-deck reading)
- Card image thumbnail
- Custom fields: field name + value for each selected field
- Archetype fields: field name + entries for each selected field, with source attribution

Cards are listed in position order within each reading. If neither custom fields nor archetype fields are enabled, this entire section is omitted.

#### Notes Section

- Journal entry content rendered as formatted text (preserve bold, italic, lists from the TipTap HTML)
- Follow-up notes listed chronologically with timestamps

#### Astrological Chart (if enabled)

- The cached SVG event chart, rendered into the PDF
- Summary table of planetary positions (planet, sign, degree, house)
- Placed at the end of the PDF, as a final page or section

---

## Technical Implementation

### PDF generation approach

Use the existing Flask backend to generate the PDF server-side. Recommended library: **WeasyPrint** or **ReportLab**.

**WeasyPrint** is the better fit because:
- It renders HTML/CSS to PDF, which means the rich text content (TipTap HTML) can be rendered directly
- CSS gives fine control over page layout, margins, headers
- SVG support for the spread layout and astrological chart
- The spread image can be composed as an HTML/CSS layout with positioned card images, matching how SpreadDisplay already works

**Approach:**
1. Frontend sends export request with selected options to a new API endpoint
2. Backend assembles an HTML document containing all selected content
3. Backend renders HTML to PDF via WeasyPrint
4. Backend returns the PDF file as a download

### Card images in the PDF
- Card images need to be embedded in the HTML as base64 data URIs or referenced as local file paths (WeasyPrint can resolve local paths)
- Use full-size images, not thumbnails, for print quality
- Images should be sized appropriately for A4 — card images in the spread don't need to be full resolution, but should be crisp at print size

### Spread layout rendering
- Reconstruct the spread layout in HTML/CSS using absolute positioning, matching the SpreadPosition data (x, y, width, height, rotation)
- Place card images within position slots
- Overlay position labels
- This mirrors what SpreadDisplay does in SVG but rendered as HTML for WeasyPrint

### Rich text rendering
- TipTap stores content as HTML — pass it directly to the WeasyPrint template
- Apply print-appropriate CSS styling (readable font sizes, proper spacing)

### Astrological chart rendering
- The cached SVG from Kerykeion can be embedded directly in the HTML — WeasyPrint supports inline SVG
- May need CSS overrides to ensure the chart renders well on a white background (since Kerykeion's default theme may use colors that don't print well)

---

## API Endpoint

### POST `/api/entries/<id>/export-pdf`

**Request body:**
```json
{
  "readings": [1, 3],
  "include_correspondences": true,
  "correspondence_types": ["element", "planet", "zodiac_sign"],
  "include_custom_fields": true,
  "custom_fields": ["Keywords", "Symbolism"],
  "include_archetype_fields": true,
  "archetype_fields": ["Divinatory Meaning", "Historical Context"],
  "include_chart": true
}
```

**Response:**
- Content-Type: `application/pdf`
- Content-Disposition: `attachment; filename="journal_entry_<id>_<date>.pdf"`

**Error responses:**
- 404 if entry not found
- 400 if no readings selected
- 500 if PDF generation fails (with error message)

---

## Notes for Implementation

- **WeasyPrint must be installed** in the app's Python environment. Add to requirements.txt. Note that WeasyPrint has system-level dependencies (cairo, pango, etc.) that must be installed on the OS — document these in the app's setup instructions.
- The export options modal should grey out sections that aren't available (e.g. correspondences if the feature isn't built yet, chart if no datetime/location on the entry).
- The PDF template should be an HTML file (Jinja2 template) in the backend, not constructed as a string in Python code. This keeps the layout maintainable.
- Card images for the spread should be sized so the complete spread fits within the A4 printable area (170 × 257mm after margins). Scale the spread proportionally if it would overflow.
- If a reading uses a very large spread (many positions), consider scaling card images smaller to fit rather than overflowing to multiple pages for a single spread.
- The position key table and correspondence breakdown should use page breaks intelligently — don't start a new section at the very bottom of a page.
- This feature warrants its own git branch.
- **Print-friendly styling:** no dark backgrounds, good contrast, readable font sizes (minimum 10pt body text), and adequate spacing. Test with actual printing.
- **Filename:** use the entry title (sanitized for filesystem) and date in the filename, e.g. `Celtic_Cross_Reading_2026-03-15.pdf`.
