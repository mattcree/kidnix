# ADR-0013: The five-choice ceiling applies to decisions, not to labelled grids

- Status: accepted
- Date: 2026-08-23

## Context

SYNTHESIS B2 (as revised at checkpoint 1 from Pailian 2016 / Schneider 2021)
says working-memory limits bind on *held* option sets, not on a visible,
labelled, spatially stable grid; the Home grid may hold up to 12 tiles while
*dialogs and choices* stay ≤ 5. The checkpoint-2 audit found three activities
exceeding five: Numbers (ten numeral tiles at `range = "ten"`), Clock's Year-2
dial (twelve rim targets), Letters' recipient grid (uncapped), and asked for
an explicit ruling.

## Decision

- **≤ 5 applies to a choice the child must *weigh*** — the ending offer,
  What's next after (one page of ≤ 8 pictures is the tolerated exception
  already argued in §7b), yes/no-type decisions, and any prompt that asks the
  child to pick between alternatives they cannot see all at once.
- **A labelled grid whose items are the task itself is not a choice set**: the
  numerals 1–10 on a number line, the twelve hours on a clock face, the
  graphemes on a keyboard-like board, the family recipients (cap at 8; page
  beyond). These are read by position and label, like the Home grid, and are
  bounded by the domain, not by our taste.
- Consequences for the three: Numbers keeps 10 numerals at `range = "ten"` but
  defaults to the five-range for age 4–5 (already the case); Clock's Y2 dial
  stays (it *is* a clock) but Year 1 (default) shows only the twelve hour
  marks without audio targets on the five-minute rim; Letters caps the
  recipient page at 8 and pages beyond.

## Consequences

- Activity audits should cite this ADR rather than B2 for domain grids.
- Any new *decision* surface with more than five options needs its own ADR.
