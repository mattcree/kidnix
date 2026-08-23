# ADR-0011: Target floor is 20 mm; panel rulings of 2026-08-23 are binding

- Status: accepted
- Date: 2026-08-23

## Context
The expert panel (`docs/design/reviews/2026-08-23-SYNTHESIS.md`) found that
the 18 mm floor in 06/SYNTHESIS was a unit-conversion artefact: Hourcade et
al. 2004's 64 px was on a ~75–80 dpi CRT, i.e. ~20–24 mm, and 01 #1 reports
the study's own physical figure as 23.7 mm. Checkpoint-1 item 15 ruled
"keep 18 / prefer 24" without noticing this.

## Decision
- Minimum interactive target **20 mm**; preferred 24 mm; primary tiles ≥ 40 mm.
  `metrics.py` floors change accordingly; grid falls to 4×2 earlier on small
  panels; band buttons must reach 20 mm (band height clamp may rise to 136 px).
- The chair's rulings in `shell-v0.1.md §7d` (session floor and proportional
  windows; consequential offer; Goodbye hierarchy; day/bedtime vocabularies;
  All done pinned; disclosure off; depictive icons; accessibility set; voice
  recorder; research logging off; per-profile data; export/wipe; signature
  policy before updates) are binding requirements for v0.2.

## Consequences
- A few fewer pixels per tile on 1280×800 (42 → ~40 mm tiles are still fine);
  recompute and re-test contrast/targets.
- Supersedes ADR-0010 #11 (tile count) and checkpoint-1 item 15.
