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

## M0 — Day one infrastructure (in progress)

- [x] Repo, AGENTS.md, ADRs, licence
- [ ] `Containerfile` on ublue base-main, `build_files/`, `system_files/`
- [ ] `Justfile`: build / lint / test-image / build-qcow2 / vm / test-boot /
      push-local / vm-upgrade / ci
- [ ] GitHub repo + Actions: lint, build, push `ghcr.io/mattcree/kidnix`,
      experimental boot test
- [ ] `docs/BUILDING.md`
- [ ] Research docs 01–08 + `SYNTHESIS.md` + `PRIORITIES.md`

Exit: `just ci` green locally and in GitHub; a qcow2 boots in qemu to a kiosk
placeholder session for the `kid` user; `just vm-upgrade` swaps a running VM to
a new build.

## M1 — Locked-down kiosk skeleton

- `kid` user: GDM autologin → gnome-kiosk (or cage) session that launches a
  placeholder shell; no VT switch, no shortcuts to escape, shell auto-restarts
- `parent` user: normal GNOME, admin
- Child session: no network egress (nftables by UID) ; Flatpak remotes
  disabled for `kid`; malcontent policy in place
- Boot test asserts: kiosk session active for kid, no egress, shell process
  alive, screenshot captured
- First-boot idempotency and `bootc upgrade`/rollback tested

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
