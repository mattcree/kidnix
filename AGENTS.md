# kidnix — guide for agents and humans

kidnix is an immutable, bootc-based Linux operating system built exclusively for
young children (primary target ages 4–8, centred on 5–6). It is meant to be a
genuinely state-of-the-art piece of child–computer interaction work, not a toy
project. Read this file before doing anything else.

## 1. What we are building (one paragraph)

A real computer (keyboard + mouse/trackpad, optionally touch) that boots into a
full-screen **activity shell** for a child — no desktop metaphor, no windows to
manage, no file browser, no web browser, no app store, no feeds, no
notifications, no telemetry. Work the child makes lives in a **Journal**.
Sessions are **bounded** (visible timer, gentle ending ritual). Every UI element
can be **read aloud** (pre-readers). A parent has a normal admin account plus a
**parent panel** (allow-lists, time budgets, journal view). The OS is an
immutable bootc image so it cannot be broken and updates are atomic/rollbackable.

## 2. Roles

| Role | Model | Owns |
|---|---|---|
| **Thinker** | Claude Fable 5 (the orchestrating session) | research synthesis, plans, priorities, ADRs, specs, reviewing & committing implementer work, talking to the human |
| **Implementer** | Claude Opus 5 (spawned workers, `model: "opus"`) | writing code, build system, tests, CI, fixing things until green |
| **Researcher** | Claude Opus 5 (spawned workers) | `docs/research/*.md` — evidence gathering with sources |
| **Human** | Matt (UK; parent of a 5–6 year old; Bluefin/Fedora user) | direction, taste, testing with the actual child |

Rules for the split:
- The thinker does not write large amounts of product code directly; it
  specifies, delegates to Opus implementers, reviews, and commits.
- Implementers do **not** `git commit`/`push`; they report and the thinker
  commits. Implementers never touch `docs/research`, `docs/plan`, `docs/adr`
  unless told to.
- Every non-trivial decision gets an ADR in `docs/adr/` (short, numbered).
- Every feature claim must be traceable to `docs/research/` evidence or an ADR
  that says "taste call".

## 3. Non-negotiables (design constitution)

These come from the research in `docs/research/`; change them only via ADR.

1. **Child wellbeing over engagement.** Nothing in kidnix is designed to
   maximise time-on-device. No streaks, no variable rewards, no autoplay, no
   infinite anything, no notifications to the child.
2. **Bounded sessions with predictable endings.** A visible, child-legible
   timer; warnings; a save-and-goodbye ritual. Ending is never a surprise.
3. **Making over consuming.** Activities produce something (a drawing, a story,
   a photo, a tune, a program). Passive video is out of scope by default.
4. **Pre-reader first.** Every affordance has audio; icons are concrete;
   text is large; nothing essential is text-only.
5. **Privacy by default, locally.** Zero telemetry. No accounts. Child session
   has no network egress by default. Parent can see/export/delete everything.
6. **Parent is a participant, not a warden.** "Ask a grown-up" instead of
   silent denial; co-use affordances; parent panel shows what was *made*, not
   surveillance metrics.
7. **It teaches real computing.** Real keyboard, real pointer, real files
   behind the scenes, real programs — the child graduates *up* into a normal
   computer, not sideways into an app store.
8. **Cannot be broken.** Immutable root, atomic updates, rollback, crash-proof
   shell, idempotent first boot.
9. **Evidence over vibes.** When we don't know, we say so and test with a
   child.
10. **Localisable from day one.** Every child- and parent-facing string goes
    through gettext (`_()`/`ngettext()`); language is per profile; the TTS
    voice follows the locale; activity content is per-language by design
    (ADR-0012). en_GB is the default, never the only.

## 4. Repository map

```
AGENTS.md / CLAUDE.md   this file (CLAUDE.md just includes it)
README.md               public-facing overview
Containerfile           bootc image (FROM ghcr.io/ublue-os/base-main)
build_files/            scripts run at image build (ublue convention)
system_files/           overlay copied to / in the image
disk_config/            bootc-image-builder config (qcow2/ISO)
Justfile                all dev/CI entry points: build, lint, test-*, vm*, ci
tests/image/            rootless tests run inside the built container
tests/boot/             boots the qcow2 in qemu and asserts the kiosk came up
.github/workflows/      CI: lint + build + push ghcr + (experimental) boot test
docs/research/          evidence base (one doc per topic, sourced)
docs/research/SYNTHESIS.md  the thinker's synthesis → product requirements
docs/plan/              ROADMAP.md, PRIORITIES.md, milestones
docs/adr/               architecture decision records
docs/design/            shell/activity specs
docs/BUILDING.md        how to build, boot, test, upgrade
shell/                  (later) the activity shell
activities/             (later) first-party activities
parent-panel/           (later) parent control panel
```

## 5. Engineering conventions

- **CI from day one.** Every PR runs `just ci` (lint + build + image tests).
  Main builds push to `ghcr.io/mattcree/kidnix`. Boot tests run in a VM.
- **Everything is reproducible from `just`.** If it isn't a `just` recipe, it
  doesn't exist. `just --list` is the documentation of what you can do.
- **Rootless by default.** Only `just build-qcow2` / `build-iso` need `sudo`
  (bootc-image-builder). Print a clear message before any sudo.
- **Fast loop.** `just build && just push-local && just vm-upgrade` should get a
  new image booted in a running VM in minutes. Treat slowness as a bug.
- **Shell scripts:** bash, `set -euo pipefail`, shellcheck-clean.
  **Python:** uv + ruff. **YAML:** yamllint. **Containerfile:** hadolint.
- **Small commits, conventional-commit style subjects** (`feat:`, `fix:`,
  `docs:`, `ci:`, `build:`, `test:`, `research:`).
- **Tests before trust.** A feature isn't done until a test (image test or
  boot test or shell test) proves it in CI.
- **Never make a sound on Matt's machine.** Every shell/activity demo and
  every GTK test sets `KIDNIX_SPEECH=off` (the shell then uses a null voice;
  `shell/Justfile` exports it by default); VMs use `-audiodev none` unless
  Matt explicitly asks to hear one. Host speech-dispatcher is not yours.
- **Never open windows on Matt's desktop.** He is working on this machine.
  GTK demos, screenshot runs and GTK smoke tests run under the Broadway
  backend: `gtk4-broadwayd :7 & GDK_BACKEND=broadway BROADWAY_DISPLAY=:7 …`
  (see `just shell-demo-headless`); QEMU is always `-display none` (the e2e
  harness does this); a visible VM window is launched only when Matt asks.
- **Disk hygiene.** The host has ~60 GB free; prune images, don't hoard
  qcow2s, keep `output/` gitignored.
- **Licensing.** Apache-2.0 for our code unless decided otherwise (ADR).
  Bundled content/fonts/voices must be redistributable; record licences.

## 6. How to work a task (for spawned agents)

1. Read `AGENTS.md`, the relevant `docs/adr/*`, and the relevant
   `docs/research/*` section (or `SYNTHESIS.md`).
2. State assumptions in your final report; don't stall on questions.
3. Verify facts against the actual image/host (`podman run … rpm -q`), not memory.
4. Run `just lint` and the relevant tests; fix until green; report what you
   could not verify and why.
5. Report: what changed (file list), what's green, decisions for the thinker.
