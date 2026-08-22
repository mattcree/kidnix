# kidnix tests

Two layers, deliberately very different in cost.

| | `tests/image/` | `tests/boot/` |
|---|---|---|
| Runs | `podman run` inside the built image | a real VM under QEMU/KVM |
| Needs | rootless podman | a qcow2 (so: one `sudo`) + `/dev/kvm` |
| Takes | ~2 seconds | ~2 minutes |
| Proves | the right files and packages are present | the machine actually boots into the kiosk |
| Command | `just test-image` | `just test-boot` |

The split matters: `test-image` is cheap enough to run on every save and catches
almost every packaging mistake, so `test-boot` — which needs privileges and a
disk image — is reserved for the questions only a running system can answer.

## `tests/image/test_image.sh`

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

## `tests/boot/boot_test.py`

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
just test-boot              # needs `just build-qcow2` first (one sudo)
just test-boot --verbose    # tee the serial console live
just test-boot-dry          # no disk image needed
```

`test-boot-dry` byte-compiles the script and checks qemu, UEFI firmware, KVM and
command construction — including that `-snapshot` is still present, because
losing it would silently start corrupting the developer's disk image. Run it in
CI on every PR; it costs nothing.
