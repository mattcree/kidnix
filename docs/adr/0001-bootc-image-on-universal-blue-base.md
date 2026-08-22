# ADR-0001: kidnix is a bootc image built on the Universal Blue base

- Status: accepted
- Date: 2026-08-22

## Context

kidnix must be unbreakable by a child, trivially updatable/rollbackable by a
parent, and easy to build/test in CI. The author already runs Bluefin (a
Universal Blue bootc image) and likes that model. Alternatives considered:
a classic distro spin (Debian/Ubuntu-based, like Escuelas Linux/Edubuntu),
a from-scratch minimal bootc image (`quay.io/fedora/fedora-bootc`), Endless OS
as a base, or a Yocto/Buildroot appliance.

## Decision

Build kidnix as an OCI/bootc container image: `FROM ghcr.io/ublue-os/base-main:44`
— Universal Blue's *headless* Fedora Atomic base (kernel, firmware, codecs,
Flatpak, NetworkManager, PipeWire, polkit; ~1350 packages; **no GNOME Shell,
no GDM**) — pinned to the Fedora major so a new release is an explicit bump.
On top we install exactly the graphical plumbing a kiosk needs (`gdm`,
`gnome-kiosk`, `malcontent`, `speech-dispatcher`, …) rather than starting from
`silverblue-main` and carrying a full desktop the child never sees. We use the
ublue `image-template` conventions (`build_files/`, `system_files/`), build and
push with GitHub Actions (cosign keyless signed), convert to qcow2/ISO with
bootc-image-builder, and update devices with `bootc upgrade`.

Corrected 2026-08-22 after the first build: the original draft assumed
`base-main` was the GNOME base; it is not (`silverblue-main` is).

## Consequences

- (+) Immutable root, atomic updates, rollback, `bootc switch` for trying new
  builds, signed images — all for free.
- (+) Smaller attack surface and image than a full desktop base; every
  graphical package is one we chose.
- (+) Hardware support and codec/firmware fixes via ublue; matches the
  author's daily driver so the dev loop is familiar.
- (−) The parent's "normal GNOME desktop" is no longer free. Decision on the
  parent experience (full GNOME session vs a parent-panel kiosk session vs
  admin-from-another-device) is deferred to ADR-0003 after the Linux-stack
  research lands.
- (−) Ties us to Fedora's cadence and ublue's base image health.
- Accounts are declared with systemd-sysusers/tmpfiles (idempotent on every
  boot), not `useradd` at build time; `parent`'s password comes from the
  installer / disk config.
- Disk-image generation requires rootful podman (documented; CI runners are
  fine).
