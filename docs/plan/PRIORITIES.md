# kidnix priorities

> Derived from `docs/research/SYNTHESIS.md` (2026-08-22). Ordered by
> (evidence-weighted value to a 5–6 year old and their parent) × (how much it
> de-risks the product claim "this holds and it's good for them") ÷ cost.
> P0 = the vertical slice a real child can use; nothing in P1+ starts until the
> P0 loop (build → boot → test → child tries it) exists.

## P0 — "one activity, end-to-end, enforced" (M0–M2)

Rationale: the strongest technical claim (enforcement below the session) and
the strongest behavioural claims (machine-owned ending, Journal, no
manipulation) can all be demonstrated with one activity. Breadth is cheap
afterwards; the loop is the hard part.

1. **Build/boot/test loop** — `just ci`, bcvk VM boot test in CI, `just vm`,
   fast upgrade of a running VM. *(in progress)*
2. **Locked-down child session** — autologin → gnome-kiosk; no egress by UID;
   polkit deny; no VT/keybinding escape; shell auto-restart; audio cap;
   greenboot rollback; updates parent-driven. *(in progress)*
3. **Parent session** — stock GNOME for `parent` on the same GDM screen; GNOME
   50 parental controls usable as-is for the things they cover. *(next)*
4. **Shell v0.1** (GTK4/libadwaita, Python): Who's-here → Home (≤ 12 tiles) →
   Activity → My Things; the band (Back · Undo · My Things · sun · Ear · Ask ·
   Grown-up); read-aloud on focus/hover via speech-dispatcher; session timer
   with Ending offer / Put away / Goodbye; parent gate (hold + PIN); single
   profile first, profiles data model from day one.
5. **Journal v0.1** — watch activity output dirs, auto-import, thumbnails,
   Today/Yesterday/Before, resume, favourites shelf, "show a grown-up" export
   folder; open formats.
6. **Activities wave 1 (RPM)** — Tux Paint (fullscreen, kid config), GCompris
   (with offline voices), KTuberling; manifests (TOML) with audio label, goal
   line, age band, network flag, journal watch paths.
7. **TTS** — speech-dispatcher + espeak-ng en-GB working in the kiosk
   session; Piper `en_GB-cori-high` behind a flag.
8. **Shell tests in CI** — QMP screenshots + ydotool scripted runs (boot →
   home → open Tux Paint → draw → journal has 1 item → ending ritual).
9. **Child test #1** — 20–30 min observed session with the family's own child;
   notes in `docs/design/testing-log.md`; decide timer A/B.

## P1 — make it a product a family can live with (M3–M4)

10. Multi-child profiles (colour = whose), instant switching, "both of us".
11. Ask-a-grown-up flow end-to-end (request queue in parent panel; outline
    tiles; async reply incl. parent voice note).
12. Parent panel app: Children · Time (session length, daily budget, bedtime,
    schedule windows) · Activities (allow-list per child) · Requests · Their
    things (browse/print/export/restore/delete) · Family recipients · Calm mode
    · Updates (bootc upgrade/rollback).
12b. **Clock & time** activity (play-with-the-clock toy + curated GCompris clock + visible timers) — see ACTIVITY-IDEAS.md
13. Keyboard/typing activity (designed, not Tux Typing as-is — see 05):
    lowercase-first, real keyboard, short bursts, no scores.
14. Story-maker (type/dictate-free: pick pictures + type words + TTS reads it
    back; prints as a booklet) — the "computers are for making" anchor.
15. Photos (webcam → Journal).
16. Music (simple xylophone/sequencer; save as OGG).
17. Letters to family (send-only to parent-curated recipients; export as image
    /PDF; no inbox).
18. Offline library (Kiwix: wiki-for-kids ZIM + picture books) via
    kiwix-serve + embedded viewer **with no general navigation**.
19. Block coding (TurboWarp Flatpak as offline Scratch for 6–8; ScratchJr-like
    for 5–6 is a gap — build later).
20. Printing from the Journal.
21. Accessibility pass: calm mode, reduced motion, contrast, switch/dwell.

## P2 — differentiators and polish (M5+)

22. "Listen" mode — screen-off stories/audiobooks; family-recorded content.
23. Flip-to-see-how-it-works (Endless Hack idea) for one activity.
24. Anaconda ISO + first-run parent wizard; hardware shortlist validated on
    a refurbished ThinkPad; docs for other families.
25. Age-bracket signal for activities (AB 1043 pattern).
26. Contribute upstream: GNOME web-filter UI, malcontent gaps, GCompris issues.

## Explicitly NOT doing (see SYNTHESIS §2 and 04 "don't")

Web browser · app store · video streaming · accounts · chat/multiplayer ·
notifications · points/streaks/badges · engagement metrics · surveillance ·
generative AI in the child session · age verification · a forked desktop.

## Day-one checklist (what "done" means for M0/M1 before a child touches it)

- [ ] `just ci` green locally and in GitHub Actions
- [ ] bcvk boot test green in CI; screenshot artefact uploaded
- [ ] Child session: no egress (tested from inside the VM), no VT switch, no
      shell escape via any keybinding in a 5-minute mash test, shell restarts
      after kill
- [ ] Parent session reachable and usable (stock GNOME), can run updates and
      roll back
- [ ] `docs/LICENSES.md` exists and covers every bundled third-party asset
- [ ] ADR-0004…0009 written
- [ ] Activity manifests validated in CI; GCompris speaks offline
- [ ] First shell screenshot in README
