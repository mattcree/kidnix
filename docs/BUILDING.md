# Building, testing and running kidnix

kidnix is a [bootc](https://bootc-dev.github.io/bootc/) container image: the OS
*is* an OCI image, built with `podman build`, and installed machines track it
with `bootc upgrade`. Everything here runs on a normal Fedora/Bluefin
workstation.

Run `just` with no arguments to list every recipe.

## Prerequisites

| Tool | Needed for | Notes |
|---|---|---|
| `podman` | everything | rootless is fine except where noted |
| `just` | everything | the task runner |
| `python3` | `test-boot` | standard library only, no venv |
| `bcvk` | `test-boot`, `vm-*`, `build-qcow2-rootless` | `just bcvk-install` |
| `qemu-system-x86_64` + `/dev/kvm` | all VM work | |
| `virtiofsd` | `bcvk` | ships with qemu on Fedora |
| `edk2-ovmf` | `vm`, `test-boot-qcow2` | UEFI firmware; bootc images are UEFI-only |
| `libvirt` (`qemu:///session`) | `vm-graphical` | rootless user session, no sudo |
| `uv` | `just lint-python` | optional; the recipe skips cleanly without it |

No linters are installed on the host. `shellcheck`, `hadolint` and `yamllint`
all run from throwaway containers, and `ruff` runs via `uvx`.

### Installing `bcvk`

`bcvk` ("bootc virtualization kit", `github.com/bootc-dev/bcvk`) is the thing
that makes the whole VM loop rootless. It replaces `containers/podman-bootc`,
which was archived in June 2026.

```sh
just bcvk-install     # -> ~/.local/bin/bcvk, checksum-verified
```

The recipe downloads the upstream `bcvk-x86_64-unknown-linux-gnu.tar.gz`
release asset plus its `.sha256`, verifies it, and installs the binary. It
no-ops if `bcvk` is already on `PATH`, so a distro package wins.

Why that route and not something tidier — all four options were tried:

| Route | Verdict |
|---|---|
| `brew install bcvk` | **No formula exists.** `brew search bcvk` finds nothing. |
| upstream release binary | **What we use.** v0.18.0, ships a `.sha256`, no privileges needed. |
| extract the Fedora 44 RPM | Works, but needs a container round-trip to `dnf5 download` and hand-unpacking into `~/.local` — strictly more moving parts for the same binary. |
| `cargo install` from git | Works, needs a Rust toolchain and several minutes. Fine as a last resort. |

`rpm-ostree install bcvk` is deliberately *not* the answer on this host: Bluefin
is itself a bootc system, so that means sudo plus a reboot for a dev tool.

## The 30-second loop

```sh
just build        # rootless podman build -> localhost/kidnix:latest
just test-image   # assert the image contains what it should (~2s)
just test-boot    # boot it in a real VM and assert the kiosk came up (~30s)
just lint         # shellcheck + hadolint + yamllint + just --fmt + ruff
just ci           # lint + build + test-image, in the order CI runs them
```

**None of that needs `sudo`.** Not the build, not the tests, and — since
`build-qcow2-rootless` landed — not the disk image either.

`just build` produces three tags: `:latest`, `:<YYYYMMDD>` and `:<version>`.
The first build downloads ~6 GB of base image; rebuilds reuse a dnf cache mount
and take about a minute.

`just test-image` runs **every** `tests/image/test_*.sh` inside the freshly
built container, each in its own throwaway container so one script cannot leave
state for the next. Adding a file to `tests/image/` is the whole of "adding a
test"; there is no list to keep in sync. `just test-image lockdown` filters to
the scripts whose name contains `lockdown`.

Image tests are static-only — they prove the *files and packages* are right,
and cannot prove anything that happens at boot. That is `test-boot`'s job.

## Running a VM

Three ways in, in increasing order of fidelity and cost.

### 1. Ephemeral, rootless, seconds — `bcvk ephemeral`

`bcvk` boots the **container image itself** as a VM: it exports the container's
filesystem over virtiofs as the VM's root and boots the kernel out of the image
directly. No disk image, no bootloader, no privileges.

```sh
just vm-ephemeral                        # root shell in a throwaway VM; Ctrl-D destroys it
just vm-exec 'systemctl is-active gdm'   # run one command, exit with its status
just vm-exec 'journalctl -b -p err'
just vm-list                             # VMs still running
just vm-clean                            # remove them all
```

This is headless and cannot be made otherwise: bcvk runs QEMU with
`-nographic -display none -monitor none`. There is a `/dev/dri/card0` inside
(QEMU's stdvga, driven by `bochs-drm`), which is why `gnome-kiosk` starts
perfectly well — you just cannot see it. For pixels, read on.

### 2. Graphical, rootless, persistent — `bcvk libvirt`

```sh
just vm-graphical                                    # create + start, SPICE console
virt-viewer --connect qemu:///session kidnix         # the actual window
just vm-graphical-ssh 'systemctl is-system-running'
just vm-graphical-shot                               # -> output/kidnix.ppm
just vm-graphical-rm                                 # destroy it
```

This installs the image to a libvirt volume, so it is a **real disk boot** —
bootloader, composefs, first-boot units, the lot. It runs on the user session
bus (`qemu:///session`), so still no sudo. `just vm-graphical-shot` wraps
`virsh screenshot`, which is the one screenshot path that needs no disk image
of your own.

> **Not yet exercised end to end.** `bcvk libvirt status` answers correctly on
> `qemu:///session` (libvirt 12.0.0, `supports_readonly_virtiofs: true`) and the
> flags are read off `bcvk libvirt run --help`, but nobody has watched this
> create a domain and take a screenshot — it was skipped to avoid writing
> another ~10 GB disk image onto a host that was already at 94%. Try it and
> report back; if it misbehaves, `just vm` on a `build-qcow2-rootless` disk is
> the proven graphical route.

### 3. Your own qcow2 under QEMU

```sh
just build-qcow2-rootless   # once, no sudo, several minutes
just vm                     # GTK window, KVM accelerated
just vm display=none        # headless
just vm-headless            # headless, serial console on your terminal
just vm-ssh                 # ssh parent@localhost:2222
```

The VM always boots with `-snapshot`, so writes go to a temporary overlay and
`output/qcow2/disk.qcow2` stays pristine. Reboot the VM and you are back to a
clean install — exactly what you want when testing a first-boot flow, and
exactly what you do *not* want if you were hoping to keep state. Drop
`-snapshot` from the recipe if you need persistence.

`just vm-ssh` only works against a disk built by `just build-qcow2`, which is
the one that applies `disk_config/config.toml` and therefore gives `parent` a
password and your SSH key. Dev credentials: user `parent`, password `kidnix`.
**Development only.**

## Disk images

### Rootless — `just build-qcow2-rootless`

```sh
just build-qcow2-rootless   # -> output/qcow2/disk.qcow2
```

`bcvk to-disk` boots a helper VM that runs `bootc install to-disk` against a
virtio disk, reading the image straight out of rootless podman storage. Nothing
on the host needs privileges. The recipe passes
`--karg console=tty0 --karg console=ttyS0,115200n8` so the serial console
carries the boot — without that, `just test-boot-qcow2` sits at a silent GRUB
handoff until it times out, which is a confusing failure to debug.

What it does **not** do is apply a blueprint. There is no customisation support
in `bcvk to-disk`, so the resulting image has no `parent` password and no SSH
key. It is for booting and testing, not for installing on a machine you intend
to log into.

### Customised — `just build-qcow2` (needs `sudo`)

```sh
just build-qcow2   # -> output/, applies disk_config/config.toml
just build-iso     # -> installable Anaconda ISO
```

These are the only recipes left that need `sudo`, for one specific reason: the
disk builder runs privileged and reads images out of **rootful** podman storage
(`/var/lib/containers/storage`), which rootless `podman build` never writes to.
Both print a banner before prompting, and both handle the storage dance:

1. `just disk-config` renders `disk_config/config.toml.example` into
   `output/config.toml`, injecting `~/.ssh/id_ed25519.pub`. The rendered file is
   gitignored because it contains your key and a dev password.
2. `_stage-rootful` streams the rootless image into root's storage with
   `podman save | sudo podman load`. It compares image **IDs** first and skips
   the copy only if they match exactly — comparing by tag would cheerfully
   build a disk from a stale image after a rebuild.
3. The builder runs under `sudo podman` and reads that staged image rather than
   pulling from a registry.

> `podman image scp localhost/kidnix:latest root@localhost::` is the tidier
> version of step 2 and is nicer to type interactively, but it needs working
> SSH to `root@localhost`, which CI runners do not have. The `save | load`
> pipe streams without a temp file and behaves identically everywhere, so
> that is what the recipe uses.

#### Which builder?

`osbuild/bootc-image-builder` **was archived on 18 June 2026** and merged into
`osbuild/image-builder`. `quay.io/centos-bootc/bootc-image-builder:latest` has
had no push since that day — it still works, but it is frozen.

The live successor is **`ghcr.io/osbuild/image-builder`** (rebuilt daily;
`ghcr.io/osbuild/image-builder-cli` is the same digest). `build-qcow2` and
`build-iso` use it, digest-pinned in the Justfile. The CLI shape changed:

```sh
# old (archived bib)
bootc-image-builder --type qcow2 --rootfs btrfs --local localhost/kidnix:latest

# new (image-builder)
image-builder build qcow2 --output-dir /output \
    --bootc-ref localhost/kidnix:latest --bootc-default-fs btrfs \
    --blueprint /config.toml
```

`just build-qcow2-bib` keeps the archived builder as an escape hatch.

> **Not verified on this machine.** The sudo path could not be exercised
> (interactive password prompt), so the `image-builder` invocation above is
> correct on paper — flag names read off `image-builder build --help` from the
> pinned container — but nobody has watched it produce a qcow2 yet. If it
> misbehaves, `just build-qcow2-bib` is the known-good fallback and
> `just build-qcow2-rootless` is the known-good *tested* one.

## The fast "try the newest build" loop

For most changes you never need a disk image at all:

```sh
just build && just test-boot     # ~30s once the image is built
```

If you want to watch a long-running VM pick up a new image instead:

```sh
just registry      # start registry:2 on :5000 (once)
just vm            # in another terminal
just vm-upgrade    # build + push + `bootc switch` inside the VM
just vm-ssh 'sudo systemctl reboot'
```

`vm-upgrade` reaches the host from inside QEMU via `10.0.2.2`, the standard
user-networking alias. Signature enforcement is disabled for the local registry
(`--enforce-container-sigpolicy=false`) — that is fine for a throwaway VM and
must never be how real devices are configured.

Afterwards, `just vm-ssh 'sudo bootc status'` shows both deployments, and
`sudo bootc rollback` inside the VM returns to the previous one.

## The automated boot tests

Two of them, and the difference matters.

### `just test-boot` — the one you run

```sh
just test-boot              # ~30s, rootless, no disk image
just test-boot --verbose    # dump the raw guest probe
just test-boot --keep       # leave the VM running to poke at
just test-boot-dry          # validate both harnesses, boot nothing
```

`tests/boot/bcvk_boot_test.py` starts a detached `bcvk ephemeral` VM, waits for
sshd, and runs one probe script inside the guest that reports back a key=value
block. It asserts:

- `systemctl is-system-running` is `running` or `degraded`
- `systemctl get-default` is `graphical.target`
- `gdm` is enabled and active
- user `kid` has a logind session with **`Type=wayland`** and `Active=yes`
- `gnome-kiosk` is running, **as `kid`**
- no *unexpected* failed units

It writes `output/boot-journal.txt` (`journalctl -b -p warning`) and
`output/console.txt` (the VM's serial console) whether it passes or fails, and
prints boot timings, memory use and whether KVM was actually used. Overall
budget is 6 minutes; a healthy run takes about 30 seconds.

`bootloader-update.service` is expected to fail here and is allow-listed by
name in the harness, with the reason: bcvk boots the kernel directly, so there
is no ESP for it to update. Anything else failing fails the test.

**There is no screenshot.** bcvk runs QEMU with `-nographic -display none
-monitor none`, so there is no QMP socket and no VNC to `screendump`.
`gnome-kiosk` *does* export `org.gnome.Shell.Screenshot` on the session bus,
but it answers `Access denied` — including to a caller running as `kid` from
inside `kid`'s own `session-1.scope` cgroup, so it is not a
wrong-user/wrong-session problem and there is no way in from the test harness.
Use `just test-boot-qcow2` or `just vm-graphical-shot` when you need pixels.

### `just test-boot-qcow2` — the one you run before believing it

```sh
just build-qcow2-rootless
just test-boot-qcow2
just test-boot-qcow2 --verbose
```

`tests/boot/boot_test.py` boots the real disk with `-snapshot`, watches the
serial console for a marker, screenshots the framebuffer over QMP, and exits
non-zero on failure. Artifacts land in `output/`: `boot-serial.log`, `boot.ppm`,
and `boot.png` if ImageMagick or ffmpeg is available.

This is the one that exercises the bootloader, the composefs root, the real
partition layout and first-boot units — none of which `test-boot` can see.

The marker comes from `kidnix-boot-report.service`, which waits for the `kid`
user to have a Wayland session with `gnome-kiosk` actually running, then prints
one of:

```
KIDNIX_BOOT_OK version=0.1.0 session=2 system=running
KIDNIX_BOOT_FAIL no wayland session for user 'kid' after 120s
```

Testing a *marker on the console* rather than scraping for `login:` is
deliberate: the assertion lives in the OS, where it can see `loginctl`, so the
test harness stays dumb and the failure message says what actually broke.

The unit is diagnostic only (`SuccessExitStatus=0 1`) — a child's laptop must
still boot when the probe is unhappy.

## Debugging a boot that goes wrong

**Turn off autologin** to get a normal GDM greeter and a session picker. `/etc`
is writable on a running bootc system:

```sh
sudo sed -i 's/^AutomaticLoginEnable=.*/AutomaticLoginEnable=False/' /etc/gdm/custom.conf
sudo systemctl restart gdm
```

**Skip the graphical stack entirely** — add `systemd.unit=multi-user.target` to
the kernel command line from the GRUB menu (press `e`), or persistently with
`sudo systemctl set-default multi-user.target`.

**Useful commands inside the VM:**

```sh
journalctl -b -u gdm -u kidnix-boot-report
journalctl -b _COMM=gnome-kiosk
loginctl list-sessions && loginctl show-session 2
systemctl is-system-running          # 'degraded' -> systemctl --failed
bootc status                         # which image is booted, what is staged
getent passwd kid parent             # did sysusers run?
```

From the host, without any of that, `just vm-exec 'any shell script'` runs the
lot inside a fresh VM and gives you the output.

### Known: no portals in the kid session

`output/boot-journal.txt` is full of *"Dependency failed for
xdg-desktop-portal.service"*. It is real, it is not a VM artefact, and it will
matter as soon as an activity wants a file chooser or a Flatpak needs a portal.

`xdg-desktop-portal.service` (and the `-gnome` and `-gtk` backends, all three
installed) carry `Requisite=graphical-session.target`. `Requisite=` fails
immediately unless the target is *already active* — and in kid's session it
never becomes active, because `/usr/bin/kidnix-shell` `exec`s `gnome-kiosk`
directly. `graphical-session.target` is normally pulled up by `gnome-session`,
which the kiosk session does not run.

gnome-kiosk ships `/usr/lib/systemd/user/org.gnome.Kiosk.target` and
`org.gnome.Kiosk@wayland.service` for exactly this, but both are
`Requisite=gnome-session-initialized.target`, so they only work under
`gnome-session` — and the Fedora `gnome-kiosk` package ships no `.session` file
to feed it. So the fix is a decision, not a one-liner: either run the session
through `gnome-session` with a kidnix `.session` file, or have `kidnix-shell`
raise `graphical-session.target` itself after the compositor is up.

## How the image is put together

```
Containerfile          FROM ghcr.io/ublue-os/base-main:44, runs build.sh, lints
build_files/build.sh   runs the NN-*.sh stages in order
  00-packages.sh       gdm, gnome-kiosk, malcontent, speech-dispatcher, ...
  10-branding.sh       rewrites /usr/lib/os-release, writes VERSION + image-info
  20-users.sh          validates the declarative account config
  30-kiosk.sh          graphical.target, enables gdm + the boot probe
  90-cleanup.sh        dnf clean, empties /var (bootc requires this)
system_files/          copied verbatim to /
```

### Base image

`ghcr.io/ublue-os/base-main:44` — Universal Blue's **headless** Fedora 44 atomic
base, *not* the GNOME one. kidnix installs `gdm` and `gnome-kiosk` itself rather
than starting from `silverblue-main` and hiding a desktop the child never sees.
That is a smaller image and a much smaller thing for a parent to trust. See
`docs/adr/0001` for the surrounding decision.

The tag is pinned to the Fedora major, not `latest`. `latest` rolls onto Fedora
45 the day it ships; a major bump should be a reviewed pull request.

### Branding

`10-branding.sh` rewrites `/usr/lib/os-release` in place (`/etc/os-release` is a
symlink to it) following the Bluefin convention: `ID=kidnix` with
`ID_LIKE="fedora"`. The `ID_LIKE` is what keeps dnf, Flatpak, rpm-ostree, ublue
tooling and third-party install scripts working. Setting `NAME`/`PRETTY_NAME`
without it is the thing that breaks tooling.

### Users

**No `useradd` runs at build time.** In a bootc image `/etc` is 3-way-merged on
every upgrade and `/var` is not shipped at all, so baking accounts into the
image's `/etc/passwd` re-litigates that merge forever and still leaves the home
directories missing. Instead:

- `/usr/lib/sysusers.d/kidnix.conf` — systemd-sysusers creates `kid` (uid 1000)
  and `parent` (uid 1001, in `wheel`) on **every boot**, idempotently, skipping
  any name that already exists.
- `/usr/lib/tmpfiles.d/kidnix.conf` — systemd-tmpfiles creates `/var/home/*`
  seeded from `/etc/skel`, and drops kid's AccountsService file so GDM knows the
  kiosk is their default session.

sysusers is ordered before tmpfiles, so the owners exist by the time the
directories are made. Because sysusers skips existing names, an installer that
creates `parent` **with a password** wins — which is how
`disk_config/config.toml` and Anaconda both work.

The trade-off: neither mechanism can set a password. `kid` is passwordless by
design (autologin straight into the kiosk). `parent` gets its password from the
installer. **An image installed with neither has a locked `parent` account** —
fine for a kiosk appliance, awkward for a laptop, and something to solve
properly before anyone installs kidnix on real hardware.

### The kiosk session (placeholder)

`/usr/share/wayland-sessions/kidnix-shell.desktop` runs `/usr/bin/kidnix-shell`,
which today is:

```sh
exec gnome-kiosk --wayland --display-server -- "${KIDNIX_KIOSK_APP}"
```

`KIDNIX_KIOSK_APP` defaults to `gnome-text-editor` purely so the boot test has
something visible to verify. Replacing that variable is the whole of "write the
real shell"; nothing else in the chain — GDM, autologin, AccountsService, the
session file, the compositor — needs to change.

`gnome-kiosk` was chosen over `cage`: it shares mutter with the rest of the
stack, ships systemd user units, and has a11y and on-screen-keyboard
subpackages that a 4-year-old will need.

## CI

`.github/workflows/build.yml` — lint, then build, then `test-image`. Pushes to
`ghcr.io/mattcree/kidnix` (`latest`, `<date>`, `<sha>`) and cosign-signs
keylessly, but **only on `main`** — pull requests build and test without ever
touching the registry. Runs weekly so the image picks up Fedora security
updates even when nobody touches the repo.

Verify a published image:

```sh
cosign verify ghcr.io/mattcree/kidnix:latest \
  --certificate-identity-regexp='^https://github.com/mattcree/kidnix/' \
  --certificate-oidc-issuer=https://token.actions.githubusercontent.com
```

`.github/workflows/boot-test.yml` — two jobs:

- **`harness`** runs on every event and costs seconds: byte-compile both boot
  harnesses and run `--dry-run`. A typo in either script fails here rather than
  20 minutes into an OS build.
- **`boot-test`** installs `bcvk` the same way you do locally
  (`just bcvk-install`, same pinned version), builds the image and runs
  `just test-boot`. It uploads `output/boot-journal.txt` and
  `output/console.txt` on success *and* failure. It **skips cleanly and green**
  if `/dev/kvm` is unavailable, because a TCG boot of a GNOME stack will not
  finish inside any sane timeout. If it runs, it must pass.

The runner has passwordless sudo, but the boot test no longer wants it: nothing
between `just build` and `just test-boot` is privileged. Sudo is used only to
`apt-get install` qemu/virtiofsd and to chmod `/dev/kvm`.

Both workflows free ~20 GB before building; the base image alone does not fit in
a stock runner's free space.

## Housekeeping

```sh
just clean        # output/, __pycache__, dangling images
just clean-all    # also removes the kidnix image tags and the local registry
```

`just clean` keeps `base-main` and `kidnix:latest` so the next build is fast.
