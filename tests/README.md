# kidnix tests

Three layers, deliberately very different in cost. None of them needs `sudo`.

| | `tests/image/` | `tests/boot/bcvk_boot_test.py` | `tests/boot/boot_test.py` |
|---|---|---|---|
| Runs | `podman run` inside the built image | the image as a VM, via `bcvk` | the real qcow2, under QEMU |
| Needs | rootless podman | `bcvk` + `/dev/kvm` | a qcow2 + `/dev/kvm` + OVMF |
| Takes | ~2 seconds | ~30 seconds | ~2 minutes plus the disk build |
| Proves | the right files and packages are present | the machine boots into the kiosk | …and that the bootloader and composefs root work |
| Command | `just test-image` | `just test-boot` | `just test-boot-qcow2` |

`test-image` is cheap enough to run on every save and catches almost every
packaging mistake. `test-boot` is cheap enough to run on every commit and is the
only thing that can prove the *session* comes up. `test-boot-qcow2` is the one
that exercises everything a real install does, and the only one that produces a
screenshot — run it before believing an image will install.

## `tests/image/`

`just test-image` runs **every** `test_*.sh` in this directory, each in its own
throwaway container. Adding a file is the whole of adding a test; there is no
list to keep in sync. `just test-image lockdown` filters by substring.

### `test_image.sh`

Static assertions, run inside the container. It checks packages are installed,
`os-release` is branded without breaking `ID_LIKE`, the kiosk session file
points at a binary that exists, the sysusers/tmpfiles configs parse, GDM
autologin is configured for `kid`, units are enabled, and `/var` carries no
image content (which `bootc` requires and would otherwise fail at install time).

It also asserts `kid` is **not** in an admin group. That one is a policy test,
not a packaging test, and should stay.

Add a case by calling one of the `assert_*` helpers under the right `section`.
Failures print the reason, and the script exits non-zero if any failed.

```sh
just test-image
```

Cannot see: anything that only happens at boot. Users are declared, not created,
at build time (see `docs/BUILDING.md`), so `getent passwd kid` inside the
container tells you nothing.

## `tests/boot/bcvk_boot_test.py` — `just test-boot`

The fast one, and the one CI gates on. `bcvk ephemeral` boots the **container
image** as a VM: the container filesystem is exported over virtiofs as the VM's
root and the kernel is booted directly out of the image. No disk image, no
bootloader, no privileges, about 30 seconds cold.

It starts a detached VM, waits for sshd, then runs a single probe script inside
the guest that reports a `key=value` block back. Assertions:

- `systemctl is-system-running` ∈ {`running`, `degraded`}
- `systemctl get-default` == `graphical.target`
- `gdm` enabled and active
- `kid` has a logind session with `Type=wayland`, `Active=yes`
- `gnome-kiosk` running, owned by `kid`
- no failed units beyond an explicit allow-list

The allow-list currently holds exactly one entry, `bootloader-update.service`,
with the reason recorded in the source: there is no ESP in an ephemeral VM.
Every other failed unit fails the test.

Artifacts, written pass or fail: `output/boot-journal.txt`
(`journalctl -b -p warning`) and `output/console.txt` (the serial console). The
summary also prints boot timings, memory use and whether KVM was really used.

**It cannot screenshot.** bcvk runs QEMU with `-nographic -display none
-monitor none`, so there is no QMP socket or VNC. `gnome-kiosk` does own
`org.gnome.Shell.Screenshot`, but every method returns `Access denied` — even
to a caller running as `kid` inside `kid`'s own `session-1.scope` cgroup, so it
is not a wrong-user problem. Use `just test-boot-qcow2` or
`just vm-graphical-shot` for pixels.

```sh
just test-boot              # ~30s
just test-boot --verbose    # dump the raw guest probe
just test-boot --keep       # leave the VM up to poke at
```

## `tests/boot/boot_test.py` — `just test-boot-qcow2`

Python 3.9+, standard library only — no venv, no pip, so it runs unchanged on a
CI runner or in a minimal container.

It boots `output/qcow2/disk.qcow2` with `-snapshot` (the image is never
mutated), tees the serial console to `output/boot-serial.log`, and waits for a
marker printed by `kidnix-boot-report.service` inside the guest:

```
KIDNIX_BOOT_OK version=0.1.0 session=2 system=running
KIDNIX_BOOT_FAIL no wayland session for user 'kid' after 120s
```

The assertion lives in the **guest**, not the harness. `/usr/libexec/kidnix-boot-report`
can call `loginctl` and `pgrep` directly, so it can say *"the session exists but
gnome-kiosk is not running"* — a sentence no amount of console scraping from
outside would produce. The harness only has to recognise two strings.

It also watches for kernel panics and emergency mode so a broken boot fails in
seconds rather than after the full timeout, and screenshots the framebuffer over
QMP (`output/boot.ppm`, converted to `boot.png` when ImageMagick or ffmpeg is
around) **whether or not the test passed** — the failure screenshot is usually
the most useful artifact.

```sh
just build-qcow2-rootless        # no sudo, several minutes
just test-boot-qcow2             # ~2 minutes
just test-boot-qcow2 --verbose   # tee the serial console live
just test-boot-dry               # validates BOTH harnesses, boots nothing
```

The disk must carry `console=ttyS0` on its kernel command line or the marker
never reaches the harness and the test times out at a silent GRUB handoff.
`build-qcow2-rootless` passes the karg; `disk_config/config.toml.example` sets
it for the `build-qcow2` path.

`test-boot-dry` byte-compiles both scripts and checks bcvk, podman, qemu, UEFI
firmware, KVM and command construction — including that `-snapshot` is still
present, because losing it would silently start corrupting the developer's disk
image. Run it in CI on every PR; it costs nothing.
