# ADR-0007: Dev/test loop uses bcvk (rootless VMs); disk media via image-builder

- Status: accepted
- Date: 2026-08-22

## Context

`bootc-image-builder` and `podman-bootc` were archived in June 2026
(*07 §2.1*). Their successors are `osbuild/image-builder` (CLI + container)
and `bootc-dev/bcvk`. On the developer host `sudo` needs a password, so a
rootless loop matters; on CI runners KVM is available.

## Decision

- **Inner loop:** `bcvk ephemeral` boots the freshly built container image as
  an unprivileged KVM VM (`just test-boot`, ~30 s, 10+ checks;
  `just vm-exec` for ad-hoc commands). `bcvk to-disk` produces a rootless
  qcow2 (`just build-qcow2-rootless`) for `just test-boot-qcow2` with QMP
  screenshots. bcvk is installed from the upstream release binary
  (sha256-verified) by `just bcvk-install`.
- **Installable media:** `ghcr.io/osbuild/image-builder` (digest-pinned)
  produces qcow2/Anaconda ISO via rootful podman (`just build-qcow2`,
  `just build-iso`); the archived bootc-image-builder path is kept as
  `build-qcow2-bib` until the new path is verified on this host.
- **CI:** `build.yml` lints, builds, runs image tests, pushes to
  `ghcr.io/mattcree/kidnix` (latest, date, sha) and signs with cosign
  keyless; `boot-test.yml` runs the bcvk boot test on a KVM-capable runner
  and skips gracefully otherwise.

## Consequences

- No root needed for the everyday loop; root only for installer media.
- Screenshots come from the qcow2 path (bcvk ephemeral runs headless and
  gnome-kiosk denies `org.gnome.Shell.Screenshot` to non-Shell callers).
- Known gap: `bcvk ephemeral` has no ESP, so `bootloader-update.service` is
  allow-listed as a failed unit in the boot test.
