# Checkpoint 2 — after the expert panel's fix waves (2026-08-23)

Audit: `docs/design/cci-compliance-audit-2026-08-23-checkpoint-2.md`.

## Verdict (auditor)

"The panel got what it asked for": 10 of 14 chair rulings MET with named
tests, 4 PARTIAL, 0 MISSING; every §2 convergence blocker at least partially
closed; the parent panel has no surveillance surface and no child path to
it; the four first-party activities get the hard half right (no scores, honest
goal lines, no network, readable scheduling) and the arithmetic/plumbing
wrong in places.

## Top 5 → state

| # | Finding | State |
|---|---|---|
| 1 | Letters could not save (SaveEntry Protocol wider than the callee) | **fixed** (protocol tightened; introspection tests) |
| 2 | GCompris shelf children had no icons (all inherit the parent's) | in progress (per-activity/group icons + generator) |
| 3 | Three activities exceed the five-choice ceiling | **ruled** — ADR-0013: the ceiling applies to decisions, not labelled domain grids; Clock Y1 dial simplified (in progress) |
| 4 | Clock minute screen: five text-only buttons; routine strip hyphenated words | icons in progress; hyphenation **fixed** (label measuring; SDK `fit_label`) |
| 5 | Sounds & Words printed its own answer; phonemes are placeholders; no clip player | prompt **fixed**; clip player **built**; real phoneme recordings still needed (docs/design/sounds-and-words.md §14) |

Also closed since the audit: `calm` default (still `false` — deliberate: calm
is opt-in, captions are on by default; ruling recorded here), i18n in all four
activities (S&W done; Numbers/Clock/Letters to follow the same pattern — open),
`kidnix-config show` must not print `pin_hash`/`pin_salt` unprivileged
(**open — next image wave**), `kidnix-act-all-done-day.svg` wired nowhere
(open), stale docs (open).

## Also landed between checkpoints

Rollback proven in a VM; e2e 30/30; keyboard escape from activities (one
locked `<Super>Tab`); hover cooldown + silent Ear; `KIDNIX_SPEECH=off` guard
(the host-speaker incident); alba as default voice; Kokoro evaluated; its bf_emma voice now **pre-rendered at build** for the
shell's closed vocabulary (351 clips, 4.7 MB; Piper alba for dynamic text); i18n foundation (276 msgids, cy/pl samples);
reply→Journal import; parent panel v0 with schedule windows, per-child
allow-lists, speech rate; Numbers, Clock, Letters to family built and
installed as tiles; Sounds & Words weeks 1–3.

## Before child test #1 (revised)

1. Rebuild + full e2e green on the image with all tiles. *(image: 15/15 suites, 69 boot checks on the consolidated build; e2e pending)*
2. Shelf icons and clock minute icons landed; screenshots refreshed. *(done)*
3. `kidnix-config show` redaction *(done)*; all-done-day icon wired *(done)*; stale docs swept *(in progress)*.
4. Phoneme recordings (Matt) — or the activity says the label honestly (it does).
5. Icon-naming probe on paper (CCI reviewer) — needs the hardware/printer.
6. The protocol's stopping rules agreed with Matt in writing.
