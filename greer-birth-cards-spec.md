# Spec: Tarot Birth Card Calculator (Mary K. Greer method)

Implementation spec for a deterministic calculator that derives a person's
"Lifetime Cards" from a birth date. Source system: Mary K. Greer,
*Archetypal Tarot* (Weiser, 2021) — itself a revision of *Who Are You in the
Tarot?* (2011) and *Tarot Constellations* (1987), building on Angeles Arrien's
"Lifetime Cards" concept.

**Scope:** birth-date-derived cards only. Name Cards (Ch. 17 of the source) are
explicitly **out of scope** for this pass.

---

## 0. Why this method and not another

There are several competing addition methods in circulation. The most common
rival is the Amberstone / Tarot School method: `MM + DD + YYYY[0:2] + YYYY[2:4]`.

Greer uses `month + day + full year` and states her reason explicitly: all
addition methods produce the same single-digit root, but hers maximizes the
spread of distinct Personality Cards across the full 1–22 range.

This has a consequence worth encoding:

> **The Soul Card is method-invariant. The Personality Card is not.**

Digit sums are preserved under any regrouping of the same digits, so the root
number is identical across methods; the intermediate 1–22 value is not.

Example — 1945-12-12:
- Greer: `12 + 12 + 1945 = 1969` → `1+9+6+9 = 25` → `2+5 = 7` → **7-7 (Chariot only)**
- Amberstone: `12 + 12 + 19 + 45 = 88` → `8+8 = 16` → **16-7 (Tower + Chariot)**

**Requirement:** the calculation method MUST be a stored, explicit parameter,
not an implicit default. Users arrive with results from either system. Ship
Greer as the default; leave a seam for `method: "amberstone"` later.

---

## 1. Public interface

```
calculate(birth_date: Date, opts?) -> BirthCardProfile
```

`opts`:
| Field | Type | Default | Notes |
|---|---|---|---|
| `method` | `"greer" \| "amberstone"` | `"greer"` | only `greer` implemented in this pass |
| `eight_eleven` | `"golden_dawn" \| "marseille"` | `"golden_dawn"` | display-only, see §7 |
| `reference_year` | int | current year | for Year Card |
| `reference_month` | int | current month | for Personal Month Card |

`BirthCardProfile`:
```
{
  base_number: int,            // the unreduced month+day+year total
  personality: int,            // 1..22
  soul: int,                   // 1..9  (or == personality when 1..9)
  teacher: int | null,         // only populated for the 19-10-1 pattern
  hidden_factor: int[],        // 0, 1, or 2 entries
  pattern: string,             // canonical label, e.g. "12-3", "5-5", "19-10-1"
  constellation: {
    root: int,                 // 1..9
    majors: int[],             // all Majors sharing that root
  },
  lessons_and_opportunities: CardRef[],   // Minor Arcana
  zodiacal_card: CardRef,      // single decan Minor
  dynamic: 1 | 2 | 3 | null,
  karmic_year: int,            // == base_number, read as a calendar year
}
```

Represent Majors as **integers 1–22 throughout**, never as names. The Fool is
`22`, not `0`, in every calculation. Name resolution happens only at render
time (§7).

---

## 2. Personality & Soul Cards

```
base   = month + day + year          // e.g. 7 + 6 + 1907 = 1920
sum1   = digit_sum(base)             // 1 + 9 + 2 + 0 = 12
```

Then branch on `sum1`:

| Condition | Personality | Soul | Extra |
|---|---|---|---|
| `1 <= sum1 <= 9` | `sum1` | `sum1` | same card in both roles |
| `10 <= sum1 <= 22`, `sum1 != 19` | `sum1` | `digit_sum(sum1)` | — |
| `sum1 == 19` | `19` | `1` | `teacher = 10` (see §3) |
| `sum1 > 22` | `digit_sum(sum1)` and re-branch | | reduces into one of the rows above |

Implementation note: the `> 22` case can be folded in by looping
`while sum1 > 22: sum1 = digit_sum(sum1)` **before** branching. A four-digit
base has a max digit sum of 36, and any digit sum > 22 reduces to a single
digit in one step, so the loop runs at most once — but write it as a loop
anyway.

**`sum1 == 22` is not a special case computationally** — 22 → Personality,
`2+2 = 4` → Soul, which falls out of the general 10–22 row. Greer adds an
*interpretive* note that 22/Fool and 4/Emperor "work as a unit" in practice.
Surface that as a flag (`pattern == "22-4"`), don't branch the math.

### Pattern label

- `sum1` single digit → `"{n}-{n}"` (e.g. `"5-5"`)
- `sum1 == 19` → `"19-10-1"`
- otherwise → `"{personality}-{soul}"` (e.g. `"12-3"`, `"22-4"`)

---

## 3. Constellations & Hidden Factor

A **constellation** is all Majors sharing a root number (digit sum reduced to
1–9), plus all Minors of that number.

```
CONSTELLATIONS = {
  1: [1, 10, 19],   2: [2, 11, 20],   3: [3, 12, 21],
  4: [4, 13, 22],   5: [5, 14],       6: [6, 15],
  7: [7, 16],       8: [8, 17],       9: [9, 18],
}
```

### The one rule that generates every documented case

Greer presents the Hidden Factor as five separate variants plus a chart. Don't
hard-code the chart. **One set-difference rule reproduces all of it:**

```
hidden_factor = CONSTELLATIONS[soul] - {personality, soul, teacher}
```

Verify against her Chart 5:

| Pattern | Constellation | Minus | Hidden Factor | Her chart |
|---|---|---|---|---|
| `1-1` | {1,10,19} | {1} | {10, 19} | 10, 19 ✓ |
| `10-1` | {1,10,19} | {10,1} | {19} | 19 ✓ |
| `19-10-1` | {1,10,19} | {19,10,1} | {} | none; 10 = Teacher ✓ |
| `20-2` | {2,11,20} | {20,2} | {11} | 11 ✓ |
| `22-4` | {4,13,22} | {22,4} | {13} | 13 ✓ |
| `5-5` | {5,14} | {5} | {14} | 14 ✓ |
| `16-7` | {7,16} | {16,7} | {} | none ✓ |

The "Nighttime Cards" (patterns `14-5`, `15-6`, `16-7`, `17-8`, `18-9`) yield an
empty set automatically, because both constellation members are consumed. Her
rationale is imagistic — Majors 14–18 fall between Death and the Sun and are
depicted at night in Waite-Smith — and she says the shadow is folded *into* the
Personality Card rather than absent. Expose that as a boolean
`nighttime: bool` for UI copy, not as separate math.

Likewise `19-10-1` yields empty because the Wheel appeared in the computation
and so isn't hidden; it becomes the Teacher instead.

### Shadow vs. Teacher naming

Same card, age-dependent label, keyed to the Saturn Return:

- age `< 29` → present as **Shadow Card**
- age `>= 29` → present as **Teacher Card**

This is presentation only. If age is unknown, prefer "Hidden Factor."

---

## 4. Lessons & Opportunities Cards

The four Minor Arcana matching the **Soul** number.

```
if pattern == "19-10-1":
    return ACES + TENS          // both, all four suits — 8 cards
else:
    return [soul of each suit]  // 4 cards
```

Soul is always 1–9, so this maps cleanly onto Ace(1) through 9. Note the
`19-10-1` exception is the only one; `22-4` gets the 4s, not anything special.

---

## 5. Zodiacal Lesson & Opportunity Card

The single decan Minor whose fixed calendar range contains the birthday.
Derived from the Golden Dawn "Book T" decan attributions; Greer credits Muriel
Bruce Hasbrouck's *Pursuit of Destiny* (1941) as her route to them.

⚠️ **Naming collision:** this was called the "Destiny Card" in *Tarot for Your
Self*. In *Archetypal Tarot* "Destiny Cards" means something else entirely (a
Name Card family, out of scope here). Namespace it as `zodiacal_card` in code
and never expose the string "Destiny Card" in this module.

### Decan table (month/day boundaries, inclusive)

| Card | From | To | Sign / degrees |
|---|---|---|---|
| 2 of Wands | Mar 21 | Mar 30 | Aries 0–10 |
| 3 of Wands | Mar 31 | Apr 10 | Aries 10–20 |
| 4 of Wands | Apr 11 | Apr 20 | Aries 20–30 |
| 5 of Pentacles | Apr 21 | Apr 30 | Taurus 0–10 |
| 6 of Pentacles | May 1 | May 10 | Taurus 10–20 |
| 7 of Pentacles | May 11 | May 20 | Taurus 20–30 |
| 8 of Swords | May 21 | May 31 | Gemini 0–10 |
| 9 of Swords | Jun 1 | Jun 10 | Gemini 10–20 |
| 10 of Swords | Jun 11 | Jun 20 | Gemini 20–30 |
| 2 of Cups | Jun 21 | Jul 1 | Cancer 0–10 |
| 3 of Cups | Jul 2 | Jul 11 | Cancer 10–20 |
| 4 of Cups | Jul 12 | Jul 21 | Cancer 20–30 |
| 5 of Wands | Jul 22 | Aug 1 | Leo 0–10 |
| 6 of Wands | Aug 2 | Aug 11 | Leo 10–20 |
| 7 of Wands | Aug 12 | Aug 22 | Leo 20–30 |
| 8 of Pentacles | Aug 23 | Sep 1 | Virgo 0–10 |
| 9 of Pentacles | Sep 2 | Sep 11 | Virgo 10–20 |
| 10 of Pentacles | Sep 12 | Sep 22 | Virgo 20–30 |
| 2 of Swords | Sep 23 | Oct 2 | Libra 0–10 |
| 3 of Swords | Oct 3 | Oct 12 | Libra 10–20 |
| 4 of Swords | Oct 13 | Oct 22 | Libra 20–30 |
| 5 of Cups | Oct 23 | Nov 1 | Scorpio 0–10 |
| 6 of Cups | Nov 2 | Nov 12 | Scorpio 10–20 |
| 7 of Cups | Nov 13 | Nov 22 | Scorpio 20–30 |
| 8 of Wands | Nov 23 | Dec 2 | Sagittarius 0–10 |
| 9 of Wands | Dec 3 | Dec 12 | Sagittarius 10–20 |
| 10 of Wands | Dec 13 | Dec 21 | Sagittarius 20–30 |
| 2 of Pentacles | Dec 22 | Dec 30 | Capricorn 0–10 |
| 3 of Pentacles | Dec 31 | Jan 9 | Capricorn 10–20 |
| 4 of Pentacles | Jan 10 | Jan 19 | Capricorn 20–30 |
| 5 of Swords | Jan 20 | Jan 29 | Aquarius 0–10 |
| 6 of Swords | Jan 30 | Feb 8 | Aquarius 10–20 |
| 7 of Swords | Feb 9 | Feb 18 | Aquarius 20–30 |
| 8 of Cups | Feb 19 | Feb 29 | Pisces 0–10 |
| 9 of Cups | Mar 1 | Mar 10 | Pisces 10–20 |
| 10 of Cups | Mar 11 | Mar 20 | Pisces 20–30 |

Notes for the implementer:

1. **The 3 of Pentacles range wraps the year boundary** (Dec 31 → Jan 9). Handle
   it explicitly; a naive `start <= date <= end` comparison fails.
2. **The 8 of Cups range must accept Feb 29.** Use an upper bound of "last day
   of February" rather than a literal 29, or the range simply ends at Feb 29 and
   non-leap years never hit it.
3. **Two ranges in the source book are typos** and are corrected above:
   - 2 of Cups printed as "June 21–July 12"; corrected to **Jul 1** (the 3 of
     Cups begins Jul 2).
   - 2 of Swords printed as "September 23–October 22"; corrected to **Oct 2**
     (the 3 of Swords begins Oct 3).
   With these fixes the 36 decans tile the full year with no gaps or overlaps.
   **Add a test that asserts exactly that** — iterate all 366 dates, assert each
   maps to exactly one card and all 36 cards are hit.
4. These are **fixed calendar approximations**, not computed solar longitudes.
   Real decan boundaries drift ±1 day year to year. Greer uses fixed dates;
   match her, and document the choice rather than silently improving on it.
   If you later add true ephemeris boundaries, make it an opt-in flag.

---

## 6. Dynamics / Soul Groups

Three seven-card hexagram groups centered on Majors 19, 20, 21. Greer credits
Vicki Noble and Jonathan Tenney's *Motherpeace Tarot Playbook*, noting Papus and
Lois Ellis worked with the pattern too. Used for relationship compatibility.

```
Dynamic 1: center 19, ring [1, 4, 7, 10, 13, 16]
Dynamic 2: center 20, ring [2, 5, 8, 11, 14, 17]
Dynamic 3: center 21, ring [3, 6, 9, 12, 15, 18]
```

This is just `((n - 1) mod 3) + 1` for `n` in 1–18, with 19/20/21 assigned
directly to 1/2/3. Compute it, don't table it.

The Fool (22) sits at the center of all three groups — return `null` and flag
`fool_center: true` rather than forcing a single value.

Assign the dynamic from the **Personality Card**.

---

## 7. Card naming (render layer only)

Keep all math on integers. Resolve names at the boundary.

**The 8/11 Strength–Justice swap is a display toggle, never a recalculation.**
Greer writes both readings into the text ("If you see 11 as Strength, read:").

| Number | `golden_dawn` (default) | `marseille` |
|---|---|---|
| 8 | Strength | Justice |
| 11 | Justice | Strength |

Other name variants the source acknowledges (Thoth lineage): 11 Justice /
Adjustment, 20 Judgement / Aeon, 10 Wheel of Fortune / Fortune. Support an
alias map; don't fork the model.

**22 is The Fool.** Conventionally numbered 0. Store 22, render "The Fool (0)"
or "The Fool" per deck convention.

---

## 8. Year Cards and periodic cards

Separate module, same numeric primitives.

### Year Card
```
base_y = birth_month + birth_day + reference_year
year_card = reduce_to_22(digit_sum(base_y))
```
**Do not reduce past 22.** Greer is emphatic: keep the highest value under 23.
Year Cards therefore range across all 22 Majors, unlike the Personality/Soul
pairing. Example from the source: month 8, day 26, year 2012 → 2048 → 14
(Temperance).

### Cycle boundary
Two overlapping cycles; Greer says use both:
- **January-to-January** — reads as outer events
- **Birthday-to-birthday** — reads as inner motivation

Expose as a `cycle` parameter with both values computable; don't pick one.

### Karmic Year
The four-digit `base_number` from §2, read as a calendar year. No further math.

### Generic Year
`digit_sum(reference_year)`, reduced to ≤22. Same for everyone. 2012 → 5.

### Personal Month Card
```
reduce_to_22(digit_sum(birth_month + birth_day + reference_year + reference_month))
```

### Cycle Themes
Year Cards run in consecutive runs of ~10 years, then jump to a new run starting
one number higher. The first card of a run themes the whole run. Derivable by
generating a lifetime series — implement as `year_card_series(birth, from, to)`
and let the caller detect runs.

---

## 9. Test vectors

All from worked examples in the source (§2–3 values), except `zodiacal` and
`dynamic`, which are derived from the tables above and should be verified by
hand once before being trusted.

| Birth date | base | sum1 | pattern | P | S | Teacher | Hidden | L&O | Zodiacal | Dyn |
|---|---|---|---|---|---|---|---|---|---|---|
| 1907-07-06 | 1920 | 12 | `12-3` | 12 | 3 | — | [21] | 3s | 3 of Cups | 3 |
| 1943-07-26 | 1976 | 23→5 | `5-5` | 5 | 5 | — | [14] | 5s | 5 of Wands | 2 |
| 1929-01-15 | 1945 | 19 | `19-10-1` | 19 | 1 | 10 | [] | Aces + 10s | 4 of Pentacles | 1 |
| 1935-12-01 | 1948 | 22 | `22-4` | 22 | 4 | — | [13] | 4s | 8 of Wands | null |
| 1961-08-04 | 1973 | 20 | `20-2` | 20 | 2 | — | [11] | 2s | 6 of Wands | 2 |
| 1926-06-01 | 1933 | 16 | `16-7` | 16 | 7 | — | [] | 7s | 9 of Swords | 1 |

Additional assertions worth writing:

- Soul number is invariant across `greer` and `amberstone` for every date in a
  large random sample; Personality number is not.
- 1945-12-12 → Greer `7-7`, Amberstone `16-7` (the divergence case from §0).
- Every date 1900–2100 produces a valid `pattern` from the closed set of 22.
- `hidden_factor` has length 2 only for patterns `1-1`, `2-2`, `3-3`, `4-4`.
- The 366-date decan tiling test from §5.

---

## 10. Generational sanity checks

Useful as fixtures, and as guardrails against off-by-one bugs — these are
structural facts about the number system, so a violation means the math is wrong:

- No `1-1` (Single 1) births since 998 CE.
- `2-2`, `3-3`, `4-4` became possible only from Jan 1, 1957.
- No `19-10-1` births after Jan 1, 1988; they resume after 2069.
- No `22-4` births after 1991 until late in the 21st century.
- Birth dates summing to a base of exactly 2000 (common 1957-12-31 through
  1997-12-31 window) give the High Priestess as Personality Card.

---

## 11. Explicit non-goals for this pass

- Name Cards (Ch. 17): Desires/Inner Motivation, Outer Persona, First/Middle/
  Last Name Cards, Theme Chord, Theme Note, Rhythm, Melody, Hidden Factor Name
  Card, Life Potential Card, Constellation Count. Design the module boundary so
  Life Potential (which needs `base_number` **unreduced** plus an unreduced name
  total) can be added without refactoring.
- Interpretive text for any card. Return numbers and identifiers; let the
  content layer own meanings.
- The Amberstone method beyond a stubbed enum value.
- Ephemeris-accurate decan boundaries.

---

## 12. Design caveat worth carrying into the UI

Greer herself opens the Birth Cards chapter by acknowledging that the Gregorian
calendar is arbitrary — it wasn't adopted in England and the colonies until 1752
— and argues the system's validity rests on cultural imprinting rather than
cosmic correspondence. That's a more defensible framing than the "ancient
practice" boilerplate common elsewhere, and it's worth reflecting in any
explanatory copy the calculator ships with.
