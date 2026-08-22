# ADR-0010: Deliberate deviations from the literature (checkpoint 1)

- Status: accepted
- Date: 2026-08-22

## Context

`docs/design/cci-compliance-audit-2026-08-22.md` separated places where the
build deviates from the research *on purpose* from accidental ones. The
accidental ones are being fixed. This ADR records the purposeful ones so they
are not re-litigated by every reader, and names the evidence that would
change our mind.

## Decisions

1. **Transitions are 350–450 ms, not < 250 ms.** 08 §3.5 ("legible as a
   journey"; under 250 ms reads as a cut) is the more specific source than
   06 #27. Revisit if the child test shows impatience or motion discomfort.
2. **Undo is always visible and speaks "Nothing to undo" when empty.**
   Spatial stability (01 #11, #13) outranks availability signalling (08 §3.4)
   for a pre-reader learning positions. Revisit if children repeatedly tap it
   expecting an effect.
3. **Ask is hidden until the flow exists**, rather than shown disabled — a
   control that never does anything teaches that buttons lie.
4. **The child cannot delete.** 08 §4.3 (recoverability licenses exploration)
   over 03 #9 (agency: a child can get rid of a drawing). Resolution path: a
   "Put away" (hide, recoverable by the parent for ≥ 30 days) on Journal
   cards — agency without loss. Until built, no delete.
5. **Tux Paint's own "Do you really want to quit?" dialog stays for v0.1.**
   It is picture-coded (tick/cross), two large targets, and it is the child's
   only way out of the activity until the band is visible over activities.
   Removing the Quit tool (`noquit`) without a band would trap the child.
   Revisit when the band-over-activity spike lands (then `noquit` + band Back
   with autosave).
6. **Hover dwell 300 ms** (spec §3) rather than 08's ~600 ms — so a sweeping
   pointer hears the grid. To be measured in the child test (utterances per
   minute, does the child stop moving?).
7. **"Ask for more time" dismisses the offer** (a child who went to find an
   adult must not return to the same question) — an improvement on spec §7a.
8. **Sleeping does not auto-wake while budget remains**; "Goodnight" means the
   sitting is over (D2).
9. **Favourites evict quietly at 8**; refusing would need an error a
   pre-reader cannot read.
10. **Firefox is removed from the whole image**, stronger than the research
    asked for; "no browser" is a property of the machine.
11. **Tile count**: SYNTHESIS B2 allows ≤ 12 tiles with progressive
    disclosure; 01 #12 says ≤ 5 primary choices. Ruling deferred to the
    literature sweep (`docs/research/09-gap-sweep-checkpoint-1.md`) and the
    first child test; `allowed_activity_ids` in `parent.toml` makes the
    subset a configuration, not a rebuild.

## Consequences

- The audit's "on purpose" table now has an ADR to point to.
- Each item lists its revisit trigger; the child-test protocol must collect
  the corresponding observation.
