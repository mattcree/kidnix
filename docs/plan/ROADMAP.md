# kidnix roadmap

> Draft v0 (2026-08-22); status updated 2026-08-23 after checkpoint 2.
> Milestones M0–M1 are infrastructure and do not depend on the research
> synthesis; M2 onward was re-prioritised against `docs/research/SYNTHESIS.md`,
> `PRIORITIES.md` and `SUITE.md`. **`docs/plan/CHECKPOINT-2.md` is the current
> state of the build**; this file is the shape of the plan.

## Principles for sequencing

1. Get a bootable, testable, upgradable image first — everything else is
   iteration on top of a loop that already works.
2. Build the thinnest vertical slice a 5-year-old can actually touch
   (shell → one activity → journal → timer) before adding breadth.
3. Every milestone ends with something that can be booted in a VM by `just`
   and asserted by CI.

## M0 — Day one infrastructure (done 2026-08-22, bar CI green on main)

- [x] Repo, AGENTS.md, ADRs 0001–0005, 0009, licence
- [x] `Containerfile` on ublue base-main:44, `build_files/`, `system_files/`
- [x] `Justfile`: build / lint / test-image / test-boot (bcvk, rootless) /
      build-qcow2(-rootless) / vm / push-local / vm-upgrade / ci
- [x] GitHub repo (private) + Actions: lint, build, push
      `ghcr.io/mattcree/kidnix`, cosign, bcvk boot test
- [x] `docs/BUILDING.md`
- [x] Research docs 01–08 + `SYNTHESIS.md` + `PRIORITIES.md`
- [x] CI build green on main (image pushed to ghcr + signed)
- [x] CI boot-test green on GitHub runners (bcvk; virtiofsd ≥ 1.11 needed on ubuntu-24.04)

Exit reached locally: `just test-boot` boots the image into the kiosk
session for `kid` in ~30 s under KVM; `just test-boot-qcow2` screenshots it.

## M1 — Locked-down kiosk skeleton — **verified in a VM 2026-08-23**

- [x] `kid`: GDM autologin → gnome-kiosk; VT-switch keybindings blanked and
      locked; app supervisor with backoff; logind NAutoVTs=0
- [x] nftables per-UID egress reject; polkit deny set; dconf kid profile with
      child input settings; Flatpak `--unshare=network`; greenboot checks;
      auto-update timer masked; ALSA cap + soft-mixer
- [x] `parent`: stock GNOME session (ADR-0005), Andika/Atkinson fonts
- [x] Portals in the kid session via gnome-session (`kidnix.session`);
      shell as a Restart=always user service (back in ~1 s after SIGKILL)
- [x] Boot test asserts: no egress from kid (`curl` exits 7) while root
      succeeds; shell restart after kill
- [~] Keybinding mash test on real hardware. The 101 blanked keybindings are
      asserted in the image tests; exactly one is deliberately live — a locked
      `<Super>Tab`, without which a keyboard-only child cannot leave an
      activity (`docs/spikes/keyboard-escape.md`). The 5-minute mash still
      wants a real laptop.
- [x] `bootc upgrade` + automatic rollback proven in a VM (`just test-rollback`,
      red.d boot-counter fix for btrfs /boot); first-boot idempotency via e2e

## M2 — Shell vertical slice ("one activity, end-to-end") — **done 2026-08-23**

Exit criterion met except the last line: the loop runs end to end on a real
image and is asserted by 30 automated tests through a real VM. What remains is
not code.

- [x] Shell tech chosen: GTK4 + libadwaita, Python (ADR-0004)
- [x] Home screen: big spoken tiles, Tux Paint, Journal view, session sun,
      ending ritual, profile picker (single profile), parent gate, All done
- [x] TTS: speech-dispatcher with espeak-ng as the guaranteed fallback, Piper
      `alba` as the default dynamic voice, and the shell's closed vocabulary
      pre-rendered at build time from Kokoro `bf_emma` (351 clips, 4.7 MB).
      `KIDNIX_SPEECH=off` mutes everything on a developer's machine.
- [x] Journal: auto-import of Tux Paint saves; thumbnails; Today/Yesterday
- [x] "Show a grown-up": a read-only showing mode on the Journal, and
      `kidnix-export` for getting the work off the machine
- [x] End-to-end scenario test (QMP input + screenshots) — `just test-e2e`
- [x] Fix: "Finish this one" re-presents the offer; unavailable activities
      must not fail silently; kid-facing tile names
- [x] Checkpoint 1: adherence audit + gap sweep; band over activities (two
      toplevels + gnome-kiosk window-config); What's-next-after; sinking sun;
      put-away never destroys work; progressive disclosure; GCompris shelf
- [x] Expert panel (9 reviewers) + fix waves A–G: session floor/proportional
      windows, consequential offer, Goodbye led by the destination, day/bedtime
      vocabularies, All done pinned, depictive icons, en_GB, GCompris shelf,
      keyboard/captions/calm, voice notes, per-profile data, mandatory PIN,
      device-verified image signing; e2e 30/30 on the result
- [x] Checkpoint 2: re-audit against the panel's fourteen rulings —
      10 met with named tests, 4 partial, 0 missing
- [ ] **First test with a real child; notes in `docs/design/testing-log.md`.**
      The one thing still owed, and the only evidence about children anywhere
      in this repo.

## M3 — Activity breadth — in progress

- [x] Activity manifest format, validated in CI (`--validate-manifests`), and
      an activity **SDK** (`kidnix_activity`) with the quit contract, captions,
      journal writing and a scaffolder (`docs/design/activity-sdk.md`)
- [x] Curated: Tux Paint, KTuberling, Blinken, Kolf, KLettres, TuxMath,
      SuperTux, TurboWarp, Kiwix, and GCompris as a one-level shelf of 18
- [x] First-party: **Numbers**, **Clock**, **Letters to family** (with the
      reply importing back into My Things), **Sounds & words** weeks 1–3
- [ ] Sounds & words: real phoneme recordings, then Read it (the deep vertical)
- [ ] Story-maker, music, photos, Listen, printing from the Journal
- [ ] i18n for the activities and the SDK (the shell is done — ADR-0012)

## M4 — Parent panel — v0 done 2026-08-23

- [x] `parent-panel/`: a GTK4/libadwaita app on the grown-up's desktop, seven
      pages (Children · Time · Activities · Sound & calm · Their things ·
      Family · Updates & safety), writing through a `pkexec` helper that
      re-validates as root and round-trips the config through the shell's own
      parsers. **No counters, no charts, no dashboard of the child** — asserted
      by test, not by intent.
- [x] The shell reads what the panel writes: schedule `[[windows]]`, per-child
      allow-lists, read-aloud pace
- [x] Update and rollback buttons, gated on the device being able to verify who
      signed the image
- [ ] Requests tab — waits on the Ask-a-grown-up flow
- [ ] An update *notification*; per-profile export and wipe (both are currently
      whole-machine, and the panel says so in words)

## M5 — Installability and polish

- Anaconda ISO, first-run wizard for parent, hardware shortlist validated,
  remaining accessibility work (switch scanning, Orca on the real image), docs
  for other families
