# Checkpoint 1 — are we adhering to the child–HCI literature? (2026-08-22)

## What was done

1. **Adherence audit** of the built shell/image against every numbered
   guideline in research 01/02/05/06/08, the 03 checklist and SYNTHESIS A–I:
   `docs/design/cci-compliance-audit-2026-08-22.md` (282 rows).
2. **Gap-filling literature sweep** on the nine places we were guessing:
   `docs/research/09-gap-sweep-checkpoint-1.md` (45 tagged sources, incl. the
   full text of Hiniker et al. *Coco's Videos*, CHI 2018; four JABA
   single-case experiments on transition cues; Schneider 2021 and Pailian 2016
   on choice sets; a 2026 RCT n=554 on parental-lock bypass; all 440 IDC
   2024–26 titles screened — still no kids-OS/launcher/kiosk-shell paper).
3. SYNTHESIS §2 updated (A7, B2, B4, D3, D4, D6, G2 + §4b); shell spec §7b
   rulings; ADR-0010 (deliberate deviations with revisit triggers);
   `CHILD-TEST-PROTOCOL.md` with protocols P1–P6.

## Verdict (audit)

Adhering unusually closely: ≈45% MET / 35% PARTIAL / 10% MISSING / 10%
N/A-yet, and the MET set is the literature's most confident items (press-only
input, locked 700 ms double-click / 16 px drag threshold, flat one-level
navigation, no scrolling, no delete, no confirmations in the shell, no
autoplay/streaks/points/telemetry/browser/LLM, analogue digit-free timer,
machine-owned ending with a first-class child-initiated path, Journal as
PNG+JSON on disk). Failures cluster in four places: (a) physical floors that
shrink on small panels; (b) the band vanishes during activities; (c)
parsed-but-unused manifest fields (Library opens nothing; age bands ignored);
(d) claims without CI proof (egress).

## What the sweep changed (design)

- **Offline continuation is chosen at session start** (new S1b screen) and
  shown back at Goodbye — Coco's Videos' strongest result.
- **The sun shrinks/sinks rather than travels**; it is ambient state, not a
  warning (transition cues are inert on their own; the aversive event is the
  drop at the destination).
- **Tile count**: ceiling 12 (geometry), first-run default 5–6 with
  progressive disclosure; the "≤5 from working memory" rule was mis-derived
  for a visible labelled grid.
- **No exit friction** becomes a named principle; Sleeping is parent-side
  enforcement (a hard lock-out was no better for the child than a home
  button); child-initiated endings are normal (31% in Coco's).
- **Hover dwell 450 ms + settle gate**, instrumented; representational
  auditory icons preferred; gate not voiced, silent failure, logged; trackpad
  hardening at libinput level.
- Settled, stop re-litigating: no autoplay/up-next; no scrolling.

## Actions (state)

| # | Action | Owner | State |
|---|---|---|---|
| 1 | Absolute mm floors; 4×2 grid on small panels (42 mm tiles) | shell | done |
| 2 | `content_required`, age bands, `allowed_activity_ids` | shell | done |
| 3 | Label wrap, no ellipsis | shell | done |
| 4 | `.not-allowed` contrast ≥ 3:1; Atkinson Next font name | shell | done |
| 5 | No spoken digits (Journal titles) | shell | done |
| 6 | Tappable sun + phase earcon | shell | done |
| 7 | Egress proven by packet capture in the boot test (found + closed a DNS side-channel via resolved/nss-resolve); licence + package-lock CI gates | image/CI | done |
| 8 | Trackpad hardening in kid dconf (+ orientation lock) | image | done |
| 9 | Piper cori default voice | image | done (verified in image) |
| 10 | S1b "What's next after?"; sun shape; dwell 450 + instrumentation; progressive disclosure; representational earcons; gate not voiced | shell | done |
| 11 | Tux Paint quit dialog: accepted for v0.1 (ADR-0010 #5); band-over-activity spike is the real fix | — | ruled |
| 12 | Child test #1 (baseline), then P1–P6 | Matt + thinker | when hardware arrives |
| 13 | GCompris curation: 18 activities in six groups via --launch; config section bug fixed | activities | done |
| 14 | Band over activities: two toplevels + window-config phases, verified in the VM (e2e asserts geometry) | shell | done |
| 16 | Put-away never destroys work: quit contract signal/confirm + grace; SIGKILL only at hard stop, truthfully worded | shell | done |
| 15 | 24 vs 18 mm floor: keep 18 mm floor / 24 preferred (06) | — | ruled |

## Still genuinely unknown

Visible sun: help or hurt (P1). Hover dwell (P5). Journal comprehension and
resume (P3). Pointer device on the real hardware (P4). Ending ritual as an
anticipated object (P6). Whether a software-imposed limit improves wellbeing
at all — no RCT says so; we keep saying so in the product.
