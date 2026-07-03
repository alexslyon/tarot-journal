# OCR Issues Log — Booklet Transcriptions

A summary of problems encountered when parsing the .md booklet transcription files into the tarot_journal database. Issues range from minor formatting quirks to entire sections of garbled or missing text.

---

## Haindl Tarot

**Overall quality:** Moderate — dense text with frequent OCR artifacts

- **7 Major Arcana had malformed header lines** (cards 5-Hierophant, 7-Chariot, 14-Alchemy, 15-Devil, 16-Tower, 17-Star, 21-Universe). Newlines appeared mid-line in the Hebrew/Rune/Astrology metadata, or the rune letter designation was missing entirely. Required manual data entry via a fix script.
- **Daughter of Cups** had a stray period in the header (`DAUGHTER OF CUPS.`) that prevented it from being recognized as a court card.
- **Father of Cups** had data corruption: Daughter of Cups text leaked into the Father's Reversed field, and the Divinatory Meaning was absorbed into the Description. Required manual SQL corrections.
- **Scattered OCR character artifacts** throughout: stray `|`, `i`, `:`, `¥` characters appearing in the middle of words or between paragraphs.

---

## Scrying Ink Lenormand

**Overall quality:** Good

- **3 cards in the DB had no corresponding .md entries:** Le Balai (Broom), Le Papillon (Butterfly), and Non-Binaire. These may be deck-exclusive cards not covered in the booklet, or they were missed during transcription.
- No significant OCR corruption in the text that was present.

---

## Eternal Tarot

**Overall quality:** Good

- **2 card name discrepancies** between .md and DB: card 38 is "Duplicity" in the .md but "Biplicity" in the DB; card 64 is "Zeal" in the .md but "Vehemence" in the DB. These may be translation differences rather than OCR errors.
- **Timetable field** was only present for 13 of the 22 Major Arcana — unclear if the remaining 9 were omitted from the source booklet or lost in transcription.
- **Kabbalistic Sephirah** was only present for 10 of the 22 Major Arcana — same ambiguity.

---

## Le Tarot des Femmes Érotiques

**Overall quality:** Good — cleanest of all the files

- No significant OCR issues. All 78 cards parsed and populated without problems.

---

## Otherkin Tarot

**Overall quality:** Poor — the worst of all the files

- **Massive text repetition** throughout. Sentences and entire paragraphs loop and repeat, sometimes 3–7 times within a single card entry. Nearly every card is affected. Examples:
  - Wheel of Fortune: "the acceptance when we were lost" repeats ~5 times in a row
  - The Sun: "You are asked to believe in yourself" repeats 3 times
  - Four of Pentacles reversed: the same paragraph about "clinging to negative attitudes" repeats ~8 times
  - Ace of Pentacles: "If you are actively dating" repeats 4 times
- **Text from other cards bleeding into unrelated entries.** For example:
  - ~~The Hanged Man's description contains paragraphs clearly about the Emperor and Hierophant~~ **FIXED** — re-transcribed from original photos (pages 53–55)
  - Judgement contains text about the Hanged Man
  - Four of Swords contains text about the Ten of Swords
  - Several Pentacles cards contain text recycled from Swords entries
- ~~**28 of 78 cards have no separated Reversed field** because the reversed meaning was either mixed into the description without a clear paragraph break, or the entire entry was one continuous block with no separation between upright and reversed.~~ **ALL 28 FIXED** — 1 fixed earlier (Hanged Man), 27 remaining reversed sections re-transcribed from original photos and inserted into the database. All 78 cards now have all 3 fields (Keywords, Description, Reversed).
- ~~**Ace of Cups** has no upright description at all — the .md entry starts directly with "In reverse..."~~ **FIXED** — upright description re-transcribed from original photos (pages 90–91)
- **Wheel of Fortune** was one continuous paragraph with no breaks, making it impossible to automatically separate description from reversed meaning (fixed manually).
- **Suit introductions for Swords** contained the text from the Pentacles introduction instead (the Swords section opens with "The pentacles are related to the element earth...").
- ~~**Two of Swords** contains the Ace of Swords description instead of its own.~~ **FIXED** — all fields re-transcribed from original photos (pages 184–186)

---

## Little Oracle

**Overall quality:** Excellent — no issues

- Clean formatting, all 32 cards parsed perfectly.

---

## Oracle of the Bible

**Overall quality:** Good

- No OCR issues in the concept glossary. Two cards (Brother, Number) had no associated words listed in the source booklet (marked with "..." and "—").

---

## Eras Tarot

**Overall quality:** Poor — heavy repetition and corruption throughout

- ~~**3 cards completely missing their "Reading Taylor's Symbols" section:**~~ **ALL 3 FIXED** — re-transcribed from original photos:
  - ~~Strength — text trails off into garbled numerology content~~ **FIXED**
  - ~~Three of Wands — text trails off with repeated fragments~~ **FIXED**
  - ~~Knight of Pentacles — the "Reading the Tarot Card" section absorbed 4,970 characters, consuming what should have been the Taylor Symbols section~~ **FIXED**
- **Widespread text repetition**, similar to Otherkin Tarot. Sentences and phrases loop within card entries. Examples:
  - The Star: "are actually stopping you from taking action" repeats 3 times
  - Seven of Cups: "do they decide when to rent or not" repeats 3 times
  - High Priestess: paragraph about karma/lost album appears twice
- **Text from other cards bleeding into unrelated entries:**
  - The Hanged Man contains text from Reputation merch and other cards
  - Death contains content from the Hierophant
  - Multiple cards end with recycled fragments from The Magician or High Priestess entries
  - The Moon contains text from The Prophecy
- **Case inconsistency** in section headers: some cards use `**READING THE TAROT CARD:**` (all caps) while others use `**Reading the Tarot Card:**` (title case). This was handled in parsing but indicates inconsistent OCR processing.
- **"Of" capitalization varies**: Cups/Pentacles suits use `### Ace Of Cups` while Swords uses `### Ace of Swords`. Again handled in parsing but indicates OCR inconsistency.
