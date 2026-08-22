# ADR-0003: Stay on `ghcr.io/ublue-os/base-main:44` for v0.1; revisit triggers

- Status: accepted (revisit at M2)
- Date: 2026-08-22

## Context

`docs/research/07-linux-stack.md` recommends `quay.io/fedora/fedora-bootc:44`
over ublue's `base-main`, because ublue has announced it is "trimming support
for intermediate images … not used in our project's final images" (since
Sept 2025 it builds only `base`, `kinoite`, `silverblue`; several variants were
removed Oct 2025). `base-main` is still built, but it is a second-class
citizen and a mild supply-chain risk for a long-lived project.

Against that: `base-main` gives kernel/firmware/codec/hardware enablement that
matters on the refurbished laptops kidnix will realistically run on, it is
what the day-one build (48 image tests, `bootc container lint` clean) already
uses, and the Containerfile takes the base as an `ARG`, so swapping is a
one-line change plus a package-list diff.

## Decision

Keep `ghcr.io/ublue-os/base-main:44` (digest-pinned in CI) for v0.1.
Schedule a measured spike before M2: build the same image `FROM
quay.io/fedora/fedora-bootc:44`, diff the package set and boot behaviour on
real hardware (wifi, audio, webcam, printer), and record the result. Switch
immediately if any of these triggers fire:

1. ublue drops or stops updating `base` images for the current Fedora major.
2. The fedora-bootc build is within ~150 packages / hardware-parity of
   base-main on our test hardware.
3. base-main's update cadence lags Fedora security updates by > 2 weeks.

## Consequences

- No churn now; the dev loop and tests stay green.
- A known, bounded migration task exists with objective triggers.
- All kidnix build scripts must stay base-agnostic (no reliance on ublue-only
  tooling beyond the image-template *conventions*).
