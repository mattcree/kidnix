# kidnix roadmap

> Draft v0 (2026-08-22). Milestones M0–M1 are infrastructure and do not depend
> on the research synthesis; M2 onward will be re-prioritised against
> `docs/research/SYNTHESIS.md` and `PRIORITIES.md` once the evidence is in.

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

## M1 — Locked-down kiosk skeleton (image level done; VM verification next)

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
- [ ] Keybinding mash test on real hardware
- [ ] First-boot idempotency and `bootc upgrade`/rollback tested in a VM

## M2 — Shell vertical slice ("one activity, end-to-end")

- Shell tech chosen (ADR) per research §07/§08
- Home screen: big spoken icons, one activity (Tux Paint), Journal view,
  session timer, goodbye ritual, profile picker (single profile), parent gate
- TTS (Piper en_GB) wired to hover/focus read-aloud
- Journal: auto-import of Tux Paint saves; thumbnails; "show Dad" shared folder
- Shell integration tests (accessibility tree or Playwright) in CI
- First test with a real child; notes in `docs/design/testing-log.md`

## M3 — Activity breadth (priority order TBD by PRIORITIES.md)

- GCompris, keyboard game, story-maker, music, photos, block coding,
  letters-to-family, offline library (Kiwix)
- Activity manifest format (name, icon, audio label, launch, journal hooks,
  OARS-like rating, network need)

## M4 — Parent panel

- Local admin app/web UI: allow-list, time budgets, quiet hours, journal
  browser, export/delete, multi-child profiles

## M5 — Installability and polish

- Anaconda ISO, first-run wizard for parent, hardware shortlist validated,
  accessibility pass, docs for other families
