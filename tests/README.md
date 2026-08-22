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

Artifacts, written pass or fail:

| file | what it is | survives a boot that never reaches sshd |
|---|---|---|
| `output/console.txt` | the serial console | yes — but it stops at the SeaBIOS banner |
| `output/journal.json`, `journal-initrd.json` | the guest journal, streamed live out of the VM over virtio-serial by bcvk `--log-dir journal` | **yes** |
| `output/boot-journal-stream.txt` | the above, flattened to `identifier: message` lines for humans | yes |
| `output/boot-journal.txt` | `journalctl -b -p warning`, fetched over ssh | no |
| `output/diagnostics.txt` | host side: `podman logs` of the VM container, the QEMU command line, `/dev/kvm` and `/dev/vhost-vsock` permissions, podman's runtime config | yes |

`diagnostics.txt` is written *while the VM is still alive* — `--rm` takes the
container, and with it `podman logs` and the QEMU process, the moment the test
gives up. The summary also prints boot timings, memory use and whether KVM was
really used.

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
just test-boot --timeout 600  # a slow host (see "In CI" below)
```

### In CI

`.github/workflows/boot-test.yml` runs this job on `ubuntu-24.04`. Four things
about a GitHub runner differ from a developer's machine, and each one has cost
us a red build:

1. **It is nested virtualisation on shared hardware.** `/dev/kvm` exists and
   bcvk really does use it, but the same boot that takes 20 s locally takes
   minutes there. The job passes `--timeout 600`; that is a ceiling for a
   broken boot, not a target.
2. **`bcvk ephemeral ssh` blocks; it does not fail fast.** It waits inside
   bcvk until the guest answers. So the harness's "poll for ssh" loop must
   treat a `subprocess.TimeoutExpired` as *keep waiting*, not as an error. It
   did not, and a fixed 30 s per-attempt timeout escaped the loop and killed
   the whole run in 31 s — while the log claimed a 360 s budget. If you ever
   shorten `SSH_POLL_SECONDS`, keep the `except TimeoutExpired: continue`.
3. **QEMU and virtiofsd come from the *host*, not the image.** bcvk runs QEMU
   inside a podman container but bind-mounts the host's `/usr` in to find it,
   so the runner must `apt-get install qemu-system-x86 virtiofsd` — and
   **noble's virtiofsd is 1.10.0, which is too old for bcvk 0.18.** bcvk passes
   `--allow-mmap`, added in virtiofsd 1.11; 1.10 rejects it with a clap usage
   error and exits 2. bcvk's entrypoint then aborts, the VM container exits
   before QEMU is ever spawned, and you get an *empty* `output/` — no console
   log (QEMU creates that file), no journal, and, with `--rm`, not even a
   container to ask. The workflow installs `virtiofsd 1.14.0` from the Ubuntu
   archive over the top, which is the same version Fedora/Bluefin ships. If
   that URL ever 404s, any `virtiofsd >= 1.11` will do; check with
   `virtiofsd --help | grep allow-mmap`.
4. **`/dev/kvm` and `vhost_vsock` need a nudge.** `sudo chmod 0666 /dev/kvm`,
   because `usermod -aG kvm` does not affect the already-running shell and bcvk
   passes the host device straight into an unprivileged rootless container.
   `sudo modprobe vhost_vsock` (then `chmod 0666` it too — it comes up
   `0660 root:kvm` and `runner` is not in the `kvm` group), because the module
   is not loaded on a stock runner.
5. **Two cores, not four.** A hosted runner has 2 vCPUs and 8 GB, so CI passes
   `--cpus 2`; more vCPUs than the host has only buys contention between QEMU,
   virtiofsd and the harness.
6. **The account can run out of artifact storage.** The upload step is
   `continue-on-error` for exactly that reason — a storage quota must never
   fail a boot that passed. The job log carries the same diagnostics.

The job uploads the whole of `output/` on success *and* failure, and prints the
tail of the console and the guest journal into the job log, so a red build is
readable without downloading anything.

To iterate on the CI plumbing without paying for a ~10 minute image build,
dispatch the workflow against an image that already exists:

```sh
gh workflow run boot-test.yml --ref ci/boot-test \
  -f image_ref=ghcr.io/mattcree/kidnix:latest
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
