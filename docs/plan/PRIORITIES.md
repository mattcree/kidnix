# kidnix priorities

> Derived from `docs/research/SYNTHESIS.md` (2026-08-22); ticks updated
> 2026-08-23 after checkpoint 2. Ordered by
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
   fast upgrade of a running VM. *(done; CI boot-test green on GitHub runners)*
2. **Locked-down child session** — autologin → gnome-kiosk; no egress by UID;
   polkit deny; no VT/keybinding escape; shell auto-restart; audio cap;
   greenboot rollback; updates parent-driven. *(done; egress and shell-restart
   verified in a VM, rollback proven by `just test-rollback`, and exactly one
   keybinding deliberately left live — a locked `<Super>Tab`, so a keyboard-only
   child can leave an activity at all: `docs/spikes/keyboard-escape.md`)*
3. **Parent session** — stock GNOME for `parent` on the same GDM screen; GNOME
   50 parental controls usable as-is for the things they cover. *(done)*
4. **Shell v0.1** (GTK4/libadwaita, Python): Who's-here → Home (≤ 12 tiles) →
   Activity → My Things; the band (Back · Undo · My Things · sun · Ear · Ask ·
   Grown-up); read-aloud on focus/hover via speech-dispatcher; session timer
   with Ending offer / Put away / Goodbye; parent gate (hold + PIN); single
   profile first, profiles data model from day one. *(done through v0.1.13:
   fit-to-screen closed, the band is its own toplevel over the activity, and
   the panel's fourteen rulings are built — see `docs/plan/CHECKPOINT-2.md`.
   Ask is still hidden; "All done" is the child's own way out.)*
5. **Journal v0.1** — watch activity output dirs, auto-import, thumbnails,
   Today/Yesterday/Before, resume, favourites shelf, "show a grown-up" export
   folder; open formats. *(done; per-profile since v0.1.9)*
6. **Activities wave 1 (RPM)** — Tux Paint (fullscreen, kid config), GCompris
   (with offline voices), KTuberling; manifests (TOML) with audio label, goal
   line, age band, network flag, journal watch paths. *(done; fourteen
   manifests ship, GCompris curated to a shelf of 18 with per-child icons)*
7. **TTS** — speech-dispatcher + espeak-ng en-GB working in the kiosk
   session; Piper `en_GB-cori-high` behind a flag. *(done, and gone further:
   Piper `alba` is the default dynamic voice and the shell's closed vocabulary
   is pre-rendered at build time from Kokoro `bf_emma` — 351 clips, 4.7 MB.
   `KIDNIX_SPEECH=off` is the developer-machine mute.)*
8. **Shell tests in CI** — QMP screenshots + ydotool scripted runs (boot →
   home → open Tux Paint → draw → journal has 1 item → ending ritual).
   *(done as `just test-e2e`: 30 tests over one VM, QMP input rather than
   ydotool, ~10 min; the contact sheet in the README is its artefact)*
9. **Child test #1** — 20–30 min observed session with the family's own child;
   notes in `docs/design/testing-log.md`; decide timer A/B. **← the only P0
   still open, and the only one that is evidence about children.**

## P1 — make it a product a family can live with (M3–M4)

10. Multi-child profiles (colour = whose), instant switching, "both of us".
    **Done**: per-profile journal/budget/progress with a migration, per-child
    allow-lists and age bands, profiles managed from the panel's Children page.
    Instant switching became *true* on 2026-08-23 (ADR-0014): resting is per
    child, a sibling's afternoon survives the other one's ending, and a rested
    face is dimmed on Who's here with the reason spoken. Residual: two
    children in one Unix account still share an activity's own save
    directory; "both of us" (co-use) still has no affordance.
11. Ask-a-grown-up flow end-to-end (request queue in parent panel; outline
    tiles; async reply incl. parent voice note).
12. Parent panel app: Children · Time (session length, daily budget, bedtime,
    schedule windows) · Activities (allow-list per child) · Requests · Their
    things (browse/print/export/restore/delete) · Family recipients · Calm mode
    · Updates (bootc upgrade/rollback). **v0 built 2026-08-23** (parent-panel/;
    Requests tab pending the Ask flow; shell follow-ups: [[windows]], per-child
    allow-list, speech_rate).
12b. **Clock & time** activity (play-with-the-clock toy + curated GCompris clock + visible timers) — see ACTIVITY-IDEAS.md. **Built and installed as a tile** (2026-08-23).
12c. **Numbers** — subitising to 5 and bonds to 5/10, built to the ELG. **Built and installed as a tile.** (Not in the original list; see SUITE.md.)
12d. **Sounds & words** — the literacy vertical (research 10). Weeks 1–3 built; real phoneme recordings outstanding (`docs/design/sounds-and-words.md` §14).
13. Keyboard/typing activity (designed, not Tux Typing as-is — see 05):
    lowercase-first, real keyboard, short bursts, no scores.
14. Story-maker (type/dictate-free: pick pictures + type words + TTS reads it
    back; prints as a booklet) — the "computers are for making" anchor.
15. Photos (webcam → Journal).
16. Music (simple xylophone/sequencer; save as OGG).
17. Letters to family (send-only to parent-curated recipients; export as image
    /PDF; no inbox). **Built and installed as a tile** — and the "no inbox"
    line was wrong: research 05 §3 makes the activity conditional on the reply
    coming back, so there *is* an inbox and the shell imports a reply into My
    Things at "Who's here?" (notes §27).
18. Offline library (Kiwix: wiki-for-kids ZIM + picture books) via
    kiwix-serve + embedded viewer **with no general navigation**.
19. Block coding (TurboWarp Flatpak as offline Scratch for 6–8; ScratchJr-like
    for 5–6 is a gap — build later).
20. Printing from the Journal.
21. Accessibility pass: calm mode, reduced motion, contrast, switch/dwell.
    **Mostly done** (v0.1.8): calm mode and reduced motion built (opt-in, not
    the default — see CHECKPOINT-2), captions on by default and mirrored across
    the activity boundary, contrast recomputed and tested, one key controller
    across both toplevels, 20 mm target floor (ADR-0011). **Open**: switch
    scanning, Orca verified on the real image, 24 mm as a constant.
21b. **Internationalisation** (ADR-0012). Done for the shell: gettext, 276
    msgids, cy/pl sample catalogues, per-profile language. **Open**: the four
    first-party activities and the SDK's own strings.

## P2 — differentiators and polish (M5+)

22. "Listen" mode — screen-off stories/audiobooks; family-recorded content.
22b. **Waydroid spike** — curated, no-network Android apps (ScratchJr, Khan Kids); see ACTIVITY-IDEAS.md
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

- [x] `just ci` green locally and in GitHub Actions
- [x] bcvk boot test green in CI; screenshot artefact uploaded
- [~] Child session: no egress (tested from inside the VM) and shell restarts
      after kill — both proven. VT switch and the 5-minute keybinding mash test
      still want real hardware (`docs/spikes/keyboard-escape.md`)
- [x] Parent session reachable (stock GNOME); update + automatic rollback
      proven in a VM (`just test-rollback`; the btrfs `/boot` boot-counter fix
      ships in `system_files/usr/lib/greenboot/red.d/`)
- [x] `docs/LICENSES.md` exists (fonts, base, voices)
- [x] ADR-0004…0013 written
- [x] Activity manifests validated in CI (fourteen); GCompris offline voices
      baked in by `50-activities.sh` and asserted by `tests/image/`
- [x] First shell screenshot in README (now the e2e contact sheet)

## Next, as of checkpoint 2 (2026-08-23)

From `docs/plan/CHECKPOINT-2.md`, in order:

1. Rebuild and get the full e2e green on the image **with all fourteen tiles**.
2. Refresh the screenshots against that build.
3. Wrap the four activities' and the SDK's strings in `_()` and add
   `activities/` to the extractor's scan path (three cases need restructuring,
   not marking).
4. Record the ~20 phonemes for Sounds & Words — the blocker for the deep
   vertical. The clip player is built; the recordings are not.
5. Icon-naming probe on paper (needs a printer and a child).
6. Agree the child-test protocol's stopping rules with Matt, in writing.
7. **Child test #1.**
