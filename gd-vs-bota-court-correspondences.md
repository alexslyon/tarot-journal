# Court Card Astrological Correspondences: Golden Dawn vs. BOTA

Reference note for implementation. Scope: the 16 court cards only.

## TL;DR

Both systems use the **same sixteen zodiacal arcs**; what differs is which rank
sits on which arc. Book T assigns Queen = cardinal, Prince = fixed, mounted
King = mutable; Case reassigned King = cardinal, Queen = fixed, Knight = mutable.

Rendering Book T's ranks into RWS naming admits **two defensible readings** —
by TITLE (the Yod King stays "King", the Prince becomes the Knight) or by
FIGURE (the mounted Book T King is the RWS Knight, the enthroned Prince the
RWS King) — so the app carries **three** systems: `golden_dawn` (Book T
titles), `golden_dawn_waite` (Waite figures), and `bota`. The earlier framing
of the difference as a simple "King ↔ Queen swap" describes only the
figure-reading vs. BOTA, and was superseded by the app ruling of Aug 2026:
all three ranks differ in modality between systems.

## The governing rule

**Golden Dawn (Book T)** — courts are Yod-Heh-Vau-Heh = King (mounted) / Queen /
Prince (chariot) / Princess:

- Queen = cardinal sign of the suit's element
- Prince = fixed
- King = mutable
- Princess = quadrant of the heavens, no sign

**Case / BOTA** — keeps YHVH and keeps Waite's mounted/enthroned figures, but
moves the letters: enthroned King takes Yod, mounted Warrior takes Vau.

- King = cardinal
- Queen = fixed
- Knight (Warrior) = mutable
- Page (Servant) = quadrant, same as GD Princess

Case's rationale is more internally consistent: Yod initiates, so Yod gets the
cardinal sign. Under GD, "Fire of Fire" (King of Wands, mounted) lands on
*mutable* Sagittarius.

## Arc table

Arcs are identical between systems. All columns use RWS rank names; the Book T
column header notes which Book T rank each modality carries. Pages/Princesses
(suit quadrant) are identical everywhere and omitted from the modality rows.

| Arc | Modality | GD (Book T titles) | GD (Waite figures) | BOTA / Case |
|---|---|---|---|---|
| 20° Pis – 20° Ari | cardinal | Queen of Wands | Queen of Wands | King of Wands |
| 20° Can – 20° Leo | fixed | Knight of Wands | King of Wands | Queen of Wands |
| 20° Sco – 20° Sag | mutable | King of Wands | Knight of Wands | Knight of Wands |
| Ari–Gem quadrant | — | Page of Wands | Page of Wands | Page of Wands |
| 20° Gem – 20° Can | cardinal | Queen of Cups | Queen of Cups | King of Cups |
| 20° Lib – 20° Sco | fixed | Knight of Cups | King of Cups | Queen of Cups |
| 20° Aqu – 20° Pis | mutable | King of Cups | Knight of Cups | Knight of Cups |
| Can–Vir quadrant | — | Page of Cups | Page of Cups | Page of Cups |
| 20° Vir – 20° Lib | cardinal | Queen of Swords | Queen of Swords | King of Swords |
| 20° Cap – 20° Aqu | fixed | Knight of Swords | King of Swords | Queen of Swords |
| 20° Tau – 20° Gem | mutable | King of Swords | Knight of Swords | Knight of Swords |
| Lib–Sag quadrant | — | Page of Swords | Page of Swords | Page of Swords |
| 20° Sag – 20° Cap | cardinal | Queen of Pentacles | Queen of Pentacles | King of Coins |
| 20° Ari – 20° Tau | fixed | Knight of Pentacles | King of Pentacles | Queen of Coins |
| 20° Leo – 20° Vir | mutable | King of Pentacles | Knight of Pentacles | Knight of Coins |
| Cap–Pis quadrant | — | Page of Pentacles | Page of Pentacles | Page of Coins |

Naming note: in Book T, the cardinal court is the Queen; the fixed court is the
Prince (enthroned figure); the mutable court is the mounted King. Read by
TITLE, King stays King (mutable) and the Prince becomes the Knight (fixed).
Read by FIGURE, the mounted Book T King is the RWS Knight (mutable) and the
enthroned Prince the RWS King (fixed). Both readings are offered in the app;
they never disagree about the Queens or Pages. Case uses Waite's ranks
directly, but in *Oracle of Tarot* calls them King / Queen / Warrior / Servant.

## Pip-triad affinities (matters for dignity calculation)

This is the real fork for anything computing elemental/astrological dignity.

| Pip triad | Decans | GD titles | GD figures | BOTA |
|---|---|---|---|---|
| 2, 3, 4 | cardinal | Queen | Queen | King |
| 5, 6, 7 | fixed | Knight | King | Queen |
| 8, 9, 10 | mutable | King | Knight | Knight |

Aces and Pages/Princesses both attach to the suit's quadrant in either system.

## Implementation caveats

- **Two calendar errors in the primary source.** In *Oracle of Tarot*, Case's
  verbal decan descriptions and his date ranges disagree in two places:
  - King of Cups: text says "last decanate of Gemini to second decanate of
    Cancer," dated Jun 20 – Jul 10. Start should be ~Jun 11.
  - King of Swords: text says "last decanate of Virgo to second decanate of
    Libra," dated Sep 13 – Oct 2. End should be ~Oct 12.

  Trust the decan language, not the printed dates. All fourteen other courts check
  out cleanly against the 20°-to-20° pattern.

- **Store arcs, not signs.** Every court spans the last decan of one sign plus the
  first two of the next. Collapsing to a single "sign" per card loses the cusp
  behavior that makes these usable for person-identification, and the two systems
  become harder to diff.

- **Don't derive one system from another at runtime.** Encoding the differences
  as transforms invites sign errors. Three flat lookup tables — as implemented in
  `birth_cards.py` (`COURT_SYSTEMS` / `_COURT_RANK_BY_MODALITY`).

## Sourcing

- BOTA side: Paul Foster Case, *Oracle of Tarot* (1933), a ten-lesson divination
  course, written for the Knapp–Hall pack and predating the finished BOTA deck.
  PDF: https://benebellwen.com/wp-content/uploads/2013/02/paul-foster-case-oracle-of-the-tarot-1933-source-credit-tarotworks.pdf
  The rank/modality rule and all sixteen time-periods are stated explicitly there.
- GD side: Book T.
- **Unverified:** BOTA's later curriculum (*Tarot Fundamentals*, *Tarot
  Interpretation*) is a closed correspondence course. No reason to expect the
  attributions changed, but this has not been confirmed against those lessons. If
  the app cites BOTA as a system, cite *Oracle of Tarot* specifically.
