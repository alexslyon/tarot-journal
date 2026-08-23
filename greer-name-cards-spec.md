# Spec: Tarot Name Card Calculator (Mary K. Greer method)

Companion to `greer-birth-cards-spec.md`. Same source: Mary K. Greer,
*Archetypal Tarot* (Weiser, 2021), Ch. 17.

**Scope:** everything derived from a person's birth *name*. Depends on the
birth-card module for exactly one value (`base_number`, §7).

Read §1 before anything else — the input model here is much messier than the
birth-date module, and most of the implementation risk lives in normalization,
not arithmetic.

---

## 0. What makes this different from birth cards

Birth cards take a `Date` — a closed, validated, unambiguous input. Name cards
take a human name, which is an open-ended string with no canonical form. The
arithmetic is trivially simple; **the hard part is deciding what counts as a
letter, what counts as a vowel, and what counts as a "name."**

Greer explicitly punts on this. On unusual name structures she says to adapt the
method to your situation. That's fine advice for a reader with a pencil and
useless for a calculator, so this spec makes those decisions explicit and marks
every place where we're going beyond the source. **Anything marked ⚑ is our
choice, not hers** — surface it as a user-overridable setting rather than baking
it in.

---

## 1. Input model

```
calculate_name_cards(name: NameInput, opts?) -> NameCardProfile
```

```
NameInput = {
  parts: string[],        // ordered name parts as given at birth
  roles?: ("first" | "middle" | "last")[]   // parallel array, optional
}
```

**Do not accept a single joined string and split on whitespace.** Take an
ordered array of parts. This sidesteps the entire "Mary Ann van der Berg" class
of bug and lets the caller resolve naming conventions that aren't Anglo-American
(patronymics, generational names, multiple surnames, name-order-reversed
traditions) before the math ever runs.

### Role assignment ⚑

Greer's three-name model carries semantic weight (§4): first = Conscious Self,
middle = Hidden Self, last = Social Self. Real names don't always have three
parts. Rules:

| Parts | Handling |
|---|---|
| 3 | first / middle / last, in order |
| 2 | first / last; **middle is absent, not zero** |
| 1 | first only; mononym |
| 4+ | first = part 1, last = final part, all interior parts = middle, summed together as one middle |

`roles` overrides all of the above when supplied. **A missing middle name must
produce `null` for the Middle Name Card, not `0` or a card.** Zero is not a
Major Arcana number and silently treating an absent name as 0 corrupts the Theme
Note.

Greer notes the real-world case of a person legally carrying a bare middle
*initial* with no name behind it. Treat a single-letter part as a normal part —
it has a Key Number like any letter.

### Character normalization ⚑

The source assumes clean uppercase A–Z. Specify explicitly:

1. Uppercase.
2. Unicode NFD decompose, strip combining marks — `José` → `JOSE`, `Ångström` →
   `ANGSTROM`. This is a lossy interpretive choice; flag it in output as
   `normalized: true` when it fires.
3. Drop apostrophes, hyphens, spaces, periods: `O'BRIEN` → `OBRIEN`,
   `SMITH-JONES` → `SMITHJONES`.
4. Drop generational suffixes (`JR`, `SR`, `II`, `III`) by default, with an
   override. They aren't given names.
5. Non-Latin scripts: **reject with a clear error.** Do not transliterate.
   Greer's entire justification for the A–V mapping is that the Latin alphabet
   order is imprinted in childhood — transliterating Cyrillic or Devanagari into
   it silently discards the argument for the method working at all. Return an
   error the UI can explain, not a wrong answer.

Store the normalized string alongside the result so the output is auditable.

---

## 2. The alphabet (Key Numbers)

Greer rejects both standard Pythagorean 1–9 numerology *and* Hebrew
transliteration. Her stated objection to the Hebrew route: the English→Hebrew
mappings are inconsistent between authorities and should be based on sound
rather than spelling. Her replacement is the Latin alphabet in learned order
mapped directly onto Majors 1–22.

```
A=1   B=2   C=3   D=4   E=5   F=6   G=7   H=8   I=9   J=10  K=11
L=12  M=13  N=14  O=15  P=16  Q=17  R=18  S=19  T=20  U=21  V=22
W=5   X=6   Y=7   Z=8
```

W/X/Y/Z are nominally 23/24/25/26, but Greer is explicit that the **reduced**
values are used in every calculation. Hard-code 5/6/7/8; never let 23–26 enter
the arithmetic.

She also assigns those four to elements — W fire, X earth, Y water, Z air —
which is display metadata only.

---

## 3. Vowel/consonant split — the one real ambiguity ⚑

Vowel and consonant sums must partition the name exactly (they're added back
together in §5), so every letter needs exactly one bucket.

A, E, I, O, U are vowels. B–D, F–H, J–N, P–T, V–Z are consonants. **Y is both**
in the source: Greer writes a Y entry in the vowel list *and* a separate Y entry
in the consonant list, describing "the Chariot in its watery and consonantal
form." The split is phonetic, not orthographic — the Y in `MARY` is a vowel, the
Y in `YVONNE` is a consonant.

Implement as a three-way setting:

| `y_mode` | Behavior |
|---|---|
| `heuristic` (default) | Y is a consonant iff it is word-initial **or** immediately followed by a vowel; otherwise a vowel |
| `always_vowel` | — |
| `always_consonant` | — |

The heuristic gets `YVONNE` (consonant), `MARY` (vowel), `KAYLA` (vowel),
`MAYA` (Y followed by A → consonant) mostly right and will still be wrong
sometimes. **Return `y_positions: {index, classified_as}[]` in the output and
let the user flip individual letters.** Do not hide this behind a default — for
any name containing Y, two legitimate answers exist and the user should see
which one they got.

W is a consonant in every case for our purposes ⚑ (Welsh borrowings like `CWM`
are out of scope).

---

## 4. Per-name cards

For each name part, compute and retain the **unreduced** sums:

```
vowel_sum[i]     = Σ key(letter) for vowels in part i
consonant_sum[i] = Σ key(letter) for consonants in part i
sum[i]           = vowel_sum[i] + consonant_sum[i]        // "Sum 1/2/3" in the book
```

Then:

| Card | Formula | Meaning |
|---|---|---|
| **First Name Card** | `reduce_to_22(sum[first])` | Conscious Self |
| **Middle Name Card** | `reduce_to_22(sum[middle])` | Hidden Self |
| **Last Name Card** | `reduce_to_22(sum[last])` | Social Self |

**Theme Chord** = the three cards as an ordered triple, read as a three-card
spread using those three position meanings. Not a separate calculation — just
return the tuple.

`reduce_to_22` is the same primitive as the birth-card module: repeatedly digit-sum
while `> 22`. Reuse it; don't reimplement.

---

## 5. Whole-name cards

```
all_vowels     = Σ vowel_sum[i]
all_consonants = Σ consonant_sum[i]
all_letters    = Σ sum[i]                    // == all_vowels + all_consonants
```

| Card | Formula |
|---|---|
| **Desires & Inner Motivation Card** | `reduce_to_22(all_vowels)` |
| **Outer Persona Card** | `reduce_to_22(all_consonants)` |
| **Theme Note Card** | `reduce_to_22(Σ reduce_to_22(sum[i]))` — sum the *reduced* per-name cards |
| **Rhythm Card** | `reduce_to_22(inner_motivation + outer_persona)` — sum the two *reduced* cards |
| **Melody Card** | `reduce_to_22(all_letters)` — reduce only at the very end |

The three "Destiny Cards" are **Theme Note, Rhythm, and Melody**. They differ
only in *where* the reduction happens, which is the entire design of the
section — same digits, three reduction points, three (often different) Majors.

### Invariant worth asserting in tests

Because all three sum the same underlying digits, **Theme Note, Rhythm, and
Melody always share a root number and therefore always fall in the same
constellation.** Assert this in a property test over random names. If it ever
fails, a reduction is happening in the wrong place.

### Hidden Factor Name Card

Same set-difference rule as the birth module:

```
hidden_factor_name = CONSTELLATIONS[shared_root] - {theme_note, rhythm, melody}
```

Can be empty (when the three cards already cover the constellation) or contain
one or two entries. Constellations 5–9 have only two members, so those bottom
out fast.

⚠️ **Naming collision, third occurrence.** "Destiny Card" now means three
different things across Greer's own bibliography plus one outside it:
1. In *Tarot for Your Self* — the zodiacal decan Minor (called `zodiacal_card`
   in the birth-card spec).
2. In *Archetypal Tarot* — Theme Note / Rhythm / Melody, i.e. this section.
3. In Hasbrouck's *Pursuit of Destiny* (1941) — sense 1, where Greer got it.
4. Outside Greer entirely — Robert Camp / Florence Campbell "Cards of Destiny,"
   a playing-card system with no relation to any of the above.

Never emit the bare string `destiny_card` from either module. Use
`theme_note`, `rhythm`, `melody`, `zodiacal_card`.

---

## 6. Constellation Count

Tally which of the nine constellations are over- and under-represented across
the letters of the full name.

```
for each letter in normalized full name:
    root = digital_root(key(letter))     // 1..9
    counts[root] += 1
```

Return `counts` (all nine keys present, zeros included), plus derived
`most_represented` and `absent` lists. Greer treats both the peaks and the gaps
as characterological indicators, so **do not omit zero entries** — the absences
are the point.

`digital_root(n)` here is the standard 1–9 reduction. Note it differs from
`reduce_to_22`: `digital_root(21) = 3`, `reduce_to_22(21) = 21`.

---

## 7. Life Potential Card

The only card combining name and birth date. This is the module boundary with
the birth-card spec.

```
life_potential = reduce_to_22(birth_base_number + all_letters)
```

Both inputs **unreduced**: `birth_base_number` is `month + day + year` straight
from the birth module (the four-digit total, before any digit-summing), and
`all_letters` is the raw sum from §5.

Read as the highest potential achievable — always interpreted in its most
idealistic register. That framing matters for the content layer; the math
doesn't care.

**Requirement:** the birth-card module must expose `base_number` in its public
output for this to work without a refactor. It already does per that spec.

---

## 8. Non-numeric outputs

These are layout and presentation features, not calculations, but they're part
of what the source delivers and users will expect them:

**Name Mandala / "spelling" the name.** Lay out the Major for every letter of
the full name, vowels raised above consonants. Repeated letters need repeated
cards — the source suggests multiple decks or photocopies; digitally this is
free. Output: the ordered card sequence with a `is_vowel` flag per position, and
let the UI arrange it. Return `max_letter_frequency` too — it's the "how many
decks would you need" number and makes a nice bit of copy.

**Leading letter.** First letter of the first name, flagged separately. Greer
notes that leading with a vowel reads differently from leading with a consonant.

**First vowel.** First vowel anywhere in the full name — "most characteristic
energy expression."

**Musical correspondences.** Paul Foster Case's system, from the Golden Dawn
attributions. Ship as a static table; it lets you sound out the Theme Chord and
play the name as a melody, which is a genuinely fun feature if you have audio.

```
A=E   B=G#  C=F#  D=C   E=C#  F=D   G=D#  H=E   I=F   J=A#  K=F#
L=G#  M=G   N=G#  O=A   P=C   Q=A#  R=B   S=D   T=C   U=A   V=E
W=C#  X=D   Y=D#  Z=E
```

Greer explicitly invites users to substitute their own system here, so make the
mapping swappable rather than hard-coded.

**Personal rhythm.** Beat pattern of vowels vs. consonants across the name.
Reducible to a per-letter V/C string (`CVCC CVVCCV ...`) plus a downbeat on each
name's first letter. Trivially derivable from data you already have.

---

## 9. Name changes and alternate names

Greer's position: the **birth name** is the lifetime name and the primary
subject of this system. A chosen or changed name is treated as a deliberate
modification of personal direction, and nicknames and assumed names can be run
through the same machinery for comparison.

Implication for the data model: `calculate_name_cards` should be callable on any
name, and the profile should carry a `name_kind: "birth" | "chosen" | "nickname"
| "other"` label. Store multiple named profiles per person rather than one.

Greer also acknowledges genuinely indeterminate cases — people with two recorded
birth dates, or birth certificates reading only "Baby Girl [Surname]" — and says
to work with what feels right or hold all possibilities as aspects of self.
⚑ Support this by allowing multiple profiles per person with no forced primary,
rather than requiring a single canonical answer.

---

## 10. Test vectors

⚑ **All computed for this spec, not taken from the book** — the source's worked
example is an illustration whose underlying name isn't fully given in the text.
Hand-verify these once before trusting them as fixtures.

### `JOHN QUINCY ADAMS`, `y_mode: always_vowel`

Per-letter keys:
- `JOHN` = J10 O15 H8 N14
- `QUINCY` = Q17 U21 I9 N14 C3 Y7
- `ADAMS` = A1 D4 A1 M13 S19

| Quantity | Value |
|---|---|
| `vowel_sum` | 15, 37, 2 |
| `consonant_sum` | 32, 34, 36 |
| `sum` (Sum 1/2/3) | 47, 71, 38 |
| First Name Card | `reduce_to_22(47)` = **11** |
| Middle Name Card | `reduce_to_22(71)` = **8** |
| Last Name Card | `reduce_to_22(38)` = **11** |
| Theme Chord | (11, 8, 11) |
| Desires & Inner Motivation | `reduce_to_22(54)` = **9** |
| Outer Persona | `reduce_to_22(102)` = **3** |
| Theme Note | `reduce_to_22(11+8+11 = 30)` = **3** |
| Rhythm | `reduce_to_22(9+3 = 12)` = **12** |
| Melody | `reduce_to_22(156)` = **12** |
| Shared root | 3 (3→3, 12→3, 12→3) ✓ |
| Hidden Factor Name | {3,12,21} − {3,12,12} = **[21]** |

Constellation Count (roots of J10,O15,H8,N14,Q17,U21,I9,N14,C3,Y7,A1,D4,A1,M13,S19):

```
1: 4   2: 0   3: 2   4: 2   5: 2   6: 1   7: 1   8: 2   9: 1     (total 15 ✓)
```

Life Potential, paired with birth date 1961-08-04 (`base_number` 1973):
`reduce_to_22(1973 + 156 = 2129)` → `2+1+2+9 = 14` → **14 (Temperance)**.

### Additional assertions

- `all_vowels + all_consonants == all_letters` for every input (partition check —
  this is what catches Y-handling bugs).
- Theme Note, Rhythm, and Melody share a root for 10,000 random names.
- Two-part name → Middle Name Card is `null`; Theme Note sums only two cards.
- Same name with `y_mode: always_vowel` vs `always_consonant` produces different
  Desires/Outer Persona but an **identical** Melody Card — the split doesn't
  change the total.
- `JOSÉ` and `JOSE` produce identical output; `О'BRIEN` with a Cyrillic О is
  rejected, not silently coerced.
- Constellation Count sums to the letter count of the normalized name.

---

## 11. Explicit non-goals

- Interpretive text for individual letters, vowels, or consonants. The source
  has a paragraph per letter; that's content-layer material, and Greer flags
  those readings as her own personal suggestions rather than fixed meanings.
- Mythological name associations (the `Adam, Agni, Amaterasu...` lists).
- Audio playback of the Theme Chord or melody — ship the note mapping, defer the
  synth.
- Automatic phonetic analysis beyond the Y heuristic. No pronunciation
  dictionary, no IPA. If you ever want better Y handling, that's a separate
  project with a real lexicon behind it.

---

## 12. Carry-over caveat

Same honesty note as the birth module. Greer's defense of the A=1…V=22 mapping
is that the Latin alphabet order is culturally imprinted from early childhood —
she cites the alphabet song and language-acquisition research — not that it's a
recovered ancient correspondence. She's directly critical of pseudo-Qabalistic
letter mappings on the grounds that they're inconsistent and spelling-based
rather than sound-based.

That's a self-aware position and worth preserving in any explanatory copy. It
also means the system is explicitly scoped to Latin-alphabet names, which is the
principled reason for §1's rejection rather than transliteration of non-Latin
scripts — the refusal follows from the author's own argument, not from
implementation laziness.
