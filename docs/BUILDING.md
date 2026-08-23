# Building, testing and running kidnix

kidnix is a [bootc](https://bootc-dev.github.io/bootc/) container image: the OS
*is* an OCI image, built with `podman build`, and installed machines track it
with `bootc upgrade`. Everything here runs on a normal Fedora/Bluefin
workstation.

Run `just` with no arguments to list every recipe.

**If you are a parent rather than a builder, this is the wrong page.** Read
[PARENTS.md](PARENTS.md) — one page, no commands, written for the person who
will actually switch the machine on.

---

## ⚠ Before you install this on real hardware

Four things, in this order. Three of the four are irreversible and none of them
is recoverable from the sofa. They are here rather than buried in the install
section because three of four parents on the 2026-08-23 review panel opened this
file, found nothing addressed to them, and closed it.

### 1. Installing kidnix **erases the whole disk**

Not "installs alongside". Not "makes a partition". Everything already on that
laptop — photos, documents, the other operating system — is gone. kidnix takes
the entire machine, which is the point of it; there is no dual-boot story and
there is not going to be one.

Copy anything you want off the laptop first, and check you actually have it.

### 2. **Never install without setting the parent password**

`kid` is passwordless by design (GDM autologin straight into the child's
screen). `parent` gets its password **from the installer, and from nowhere
else** — `systemd-sysusers` cannot set one, and neither can the image.

**An image installed with no password and no SSH key leaves `parent` LOCKED.**
Combined with `PasswordAuthentication no` in
`/etc/ssh/sshd_config.d/10-kidnix.conf` (see `docs/spikes/hardening.md` §3.4),
that means:

> there is no way into that machine, ever, except a rescue USB stick — and the
> only copy of your child's drawings is on it.

So, at install time, do **one** of these:

- **`disk_config/config.toml`** (`just build-qcow2`): set a real password in the
  `[[customizations.user]]` block. The one in the repo is a development
  placeholder and must not reach a household machine.
- **Anaconda / the ISO**: create the `parent` user with a password at the user
  screen. Do not skip it.
- **An SSH key**: put an `authorized_keys` into the `parent` user's
  customisation. A key is fine on its own; a key *and* a password is better,
  because a key on a laptop you have lost is not much use.

**Then check it before you hand the machine over.** Boot it, get to a text
console or the parent desktop, and actually log in as `parent`. Five seconds
now, a rescue USB later.

### 3. The disk is **not encrypted**

There is no LUKS, no FDE, and no prompt at boot. Possession of the laptop is
possession of everything on it: every drawing, and the journal of what the child
did and when.

That is a deliberate trade for a machine a four-year-old switches on alone (a
passphrase at boot would defeat the entire premise), but it is a trade, and it
has to be a decision somebody made rather than a thing nobody mentioned. If the
machine will hold anything you would mind losing with the machine, do not put it
on this one.

### 4. Nothing is backed up

The child's work lives in `/var/home/kid`, on that disk, and nothing copies it
anywhere. If the laptop dies, it is gone.

`kidnix-export` (run from the parent account; asks for the parent's password via
polkit) tars everything into one file you can put on a USB stick. Tell whoever
owns the machine that it exists, because they will not find it on their own.
`kidnix-wipe` is the other half, for handing the machine on.

---

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
just ci           # lint + build + test-image + licences + packages-check
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

## Working on the shell — and never making a sound

The shell is a uv project in `shell/`, with its own Justfile. Run these from
`shell/`:

```sh
just setup              # uv venv --system-site-packages (GTK comes from the system)
just demo               # the whole ritual in three minutes, windowed
just test-headless      # the CI floor: pure logic, no display
just lint               # ruff + mypy
just validate-manifests # gates the manifests the image ships
just ci                 # lint + test-headless + po-check + validate-manifests + validate-activity
```

**`shell/Justfile` exports `KIDNIX_SPEECH=off`**, and that is not a nicety. Any
value in `off / 0 / false / none / null` makes `speech.speech_off()` true and
the shell takes a null voice: no speech-dispatcher connection, no Piper, no
pre-rendered clip playback. Every demo, screenshot run and GTK test is therefore
silent by default on a developer's machine. `KIDNIX_SPEECH=on just demo` is the
deliberate opt-in, and it uses **your** speakers and **your** speech-dispatcher.
A real kiosk session never goes through this Justfile and is unaffected.

For pixels without a window appearing on your desktop, use the repo-root recipe,
which runs the demo under GTK's Broadway backend and screenshots it:

```sh
just shell-demo-headless 1280x800@102 output/home.png
just shell-demo-headless 1280x800@102 output/resting.png --start-on resting
```

`--start-on` takes the state to jump to (`home`, `offer`, `resting`, …), and
`--screen WxH@DPI` makes the layout believe it is on a panel that size, which is
how the small-panel fit budget is checked without owning the panel.

## Running a VM

**None of these recipes gives the VM a sound device.** No `-audiodev`, no
`-device` for audio: a kidnix VM is silent on the host, on purpose, so a test
run cannot take over the machine's speakers. If you actually need to *hear* the
shell — checking a Piper voice or an earcon — add `-audiodev pipewire,id=snd
-device intel-hda -device hda-duplex` to the `vm` recipe by hand, and take it
out again afterwards.

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

Four recipes, and the differences matter.

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

### `just test-e2e` — the one that drives the shell

```sh
just build-qcow2-rootless   # once
just test-e2e               # ~10 minutes
just test-e2e-offline       # the pixel-geometry helpers alone, milliseconds
```

**30 tests** in three files, sharing **one** VM because a second boot costs
60–90 s of the budget: `test_geometry.py` (15, offline, run first so a typo in
the pixel helpers fails in a second rather than in four minutes),
`test_scenario.py` (7 — one child's ordinary session: boot, choose, plan,
launch Tux Paint, draw, keep, the offer, put-away, Goodbye, Resting) and
`test_flows.py` (8 — the flows the happy path cannot reach: a spent budget, a
bedtime clock, an activity that fails to open, "All done", a whole session on
the keyboard, the hard stop). `conftest.pytest_collection_modifyitems` enforces
that order.

Nothing is installed in the guest and the image under test is the image we ship:
the *interaction* is QEMU `input-send-event` over QMP (absolute pointer, real
key presses), and the *evidence* is a framebuffer screendump plus the guest's
own journal read over ssh. Root SSH comes from an ephemeral key passed as a
systemd credential over SMBIOS. QEMU runs `-display none`; see
`docs/spikes/e2e-scenario.md`.

Artefacts land in `output/e2e/`: a numbered PNG per step, the serial console,
the QEMU command line, and `contact-sheet.png` — which is copied over
`docs/design/screenshots/e2e-contact-sheet.png`, the picture in the README.

### `just test-rollback` — the one that proves the biggest claim

```sh
just build-qcow2-rootless
just test-rollback          # ~4 minutes, needs KVM; nightly, not per-PR
just rollback-clean         # stop the registry, drop the unhealthy image
```

"Immutable, so it cannot be broken" is the largest claim in the product. This
recipe builds a variant image carrying **one** extra file — an always-failing
*required* greenboot check, from `--build-arg KIDNIX_SELFTEST_BREAK_HEALTH=1` —
serves it from the throwaway local registry, `bootc switch`es a real booted
machine onto it, and waits for the machine to put itself back. It asserts the
counter arms, decrements on every failed boot, that the machine rolled *itself*
back, that `bootc` agrees it is the original digest, and that the child's shell
is running again.

`tests/image/test_lockdown.sh` asserts the failing check is absent from every
normal build, so it cannot reach a shipped image by accident.

The first run of this test found the claim was **false**: GRUB cannot write
`/boot/grub2/grubenv` when `/boot` is btrfs, so bootupd's `decrement
boot_counter` never happened and a bad update reboot-looped for ever instead of
rolling back. The fix now ships —
`system_files/usr/lib/greenboot/red.d/10-kidnix-boot-counter.sh` does the
decrement greenboot's own rollback trigger is waiting for. `docs/spikes/rollback.md`
has the full root cause and the verified 11/11 run; its header still describes
the pre-fix state.

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

### Portals in the kid session — solved

This section used to describe a boot journal full of *"Dependency failed for
xdg-desktop-portal.service"*. It is fixed: the kid session is now a real
`gnome-session --session=kidnix`, so `graphical-session.target` becomes active
and all three portals start normally. `journalctl -b _UID=1000 | grep -c
"Dependency failed for xdg-desktop-portal"` is `0`, and `just test-boot`
asserts `xdg-desktop-portal.service` and `xdg-desktop-portal-gnome.service` are
active in kid's own user manager.

How and why, including the two upstream constraints that made it a decision
rather than a one-liner (`Requisite=graphical-session.target` on the portals,
`Requisite=gnome-session-initialized.target` on gnome-kiosk's own units):
**`docs/spikes/session-integration.md`**.

## How the image is put together

```
Containerfile          FROM ghcr.io/ublue-os/base-main:44, runs build.sh, lints
build_files/build.sh   runs the NN-*.sh stages in order
  00-packages.sh       gdm, gnome-kiosk, malcontent, speech-dispatcher, ...
  05-locale.sh         en_GB everywhere: locale.conf, keyboard, per-app nudges
  10-branding.sh       rewrites /usr/lib/os-release, writes VERSION + image-info
  20-users.sh          validates the declarative account config
  30-kiosk.sh          graphical.target, enables gdm + the boot probe
  35-parent-desktop.sh the parent's stock GNOME session (ADR-0005)
  36-fonts.sh          Andika + Atkinson Hyperlegible, system font cache
  40-lockdown.sh       no egress for uid 1000, dconf locks, polkit, greenboot
  50-activities.sh     the curated third-party payload and its manifests
  55-gcompris.sh       turns GCompris' 198 activities into a shelf of 18
  60-shell.sh          installs shell/ + kidnix_activity, wires gnome-session
  62-parent-panel.sh   installs parent-panel/ and its root helper (wheel-only)
  64-first-party-activities.sh   Sounds & words, Numbers, Clock, Letters
  65-tts.sh            Piper + the en_GB alba/cori voices behind speech-dispatcher
  66-prerender-speech.sh  renders the shell's closed vocabulary to Ogg clips
  70-hardening.sh      removes firefox & co, masks noisy units, one wallpaper
  75-supply-chain.sh   signature policy + the pinned cosign key for updates
  90-cleanup.sh        dnf clean, empties /var (bootc requires this)
system_files/          copied verbatim to /
```

### What the child actually sees

Fourteen manifests in `system_files/usr/share/kidnix/activities/`, filtered per
child by age band and the parent's allow-list, so no one child sees all of them:

| Tile | What it is | Ages |
|---|---|---|
| **Draw** | Tux Paint, tuned | 3–10 |
| **Sounds & words** | first-party phonics (the deep vertical) | 4–6 |
| **Numbers** | first-party subitising and bonds to 5/10 | 4–7 |
| **Potato faces** | KTuberling | 3–7 |
| **Clock** | first-party play-with-the-clock toy | 4–8 |
| **Letters** | first-party letters to family (picture + words + voice) | 4–8 |
| **Make a game** | TurboWarp; hidden unless installed | 6–12 |
| **Letters & numbers** | the GCompris shelf of 18 curated children | 4–8 |
| **Letter names** | KLettres — letter *names*, not phonics, and says so | 4–8 |
| **Number game** | TuxMath — it can be lost, so 7+ | 7–10 |
| **Copy the lights** | Blinken | 4–10 |
| **Mini golf** | Kolf | 5–10 |
| **Jump and run** | SuperTux — has a GAME OVER, so 7+ | 7–12 |
| **Library** | Kiwix; absent until a grown-up adds a ZIM | 5–12 |

The four first-party ones are built in this repo under `activities/` and
installed by `build_files/64-first-party-activities.sh` — a `cp -a` into
site-packages plus the dist-info a wheel would have left, for the same reason
`60-shell.sh` does it that way (pip and hatchling would have to be installed
into a child's OS and removed again to produce a byte-identical tree). Each one
gets its console script, its icon and its manifest, and the stage asserts all of
it. `tests/image/test_first_party.sh` is the gate.

`just validate-manifests` (from `shell/`) exits non-zero on any manifest error;
`shell/just ci` runs it.

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
installer. **An image installed with neither has a locked `parent` account**,
and with `PasswordAuthentication no` in the sshd drop-in that machine has no
recovery path but a rescue USB — see
[Before you install this on real hardware](#-before-you-install-this-on-real-hardware)
at the top of this file, which is where that now lives in full.

### The kiosk session

`/usr/share/wayland-sessions/kidnix-shell.desktop` runs `/usr/bin/kidnix-shell`,
which execs `gnome-session --session=kidnix` (see
`docs/spikes/session-integration.md`). That session starts `gnome-kiosk` as the
compositor and `kidnix-shell.service` as the payload — the **real** shell from
`shell/` in this repo, installed into site-packages by
`build_files/60-shell.sh` and run as `/usr/bin/kidnix-shell-app`.

An older version of this page said the kiosk launched `gnome-text-editor` as a
placeholder. It has not for some time; that text editor is deliberately not in
the image at all (a five-year-old has no use for one, and it is one more window
surface to reason about). Flagged by the parent panel, who read this page and
concluded the docs were behind the code — they were.

`gnome-kiosk` was chosen over `cage`: it shares mutter with the rest of the
stack, ships systemd user units, and has a11y and on-screen-keyboard
subpackages that a 4-year-old will need.

## CI

`.github/workflows/build.yml` — lint, then build, then `test-image`. Pushes to
`ghcr.io/mattcree/kidnix` (`latest`, `<date>`, `<sha>`) and cosign-signs
keylessly, but **only on `main`** — pull requests build and test without ever
touching the registry. Runs weekly so the image picks up Fedora security
updates even when nobody touches the repo.

Verify a published image, **on a workstation**:

```sh
cosign verify ghcr.io/mattcree/kidnix:latest \
  --certificate-identity-regexp='^https://github.com/mattcree/kidnix/' \
  --certificate-oidc-issuer=https://token.actions.githubusercontent.com
```

### On the machine itself: the signature policy, and what is still missing

`build_files/75-supply-chain.sh` merges one scope into the base image's
`/etc/containers/policy.json`, and ships
`/etc/containers/registries.d/kidnix.yaml` with `use-sigstore-attachments: true`
so anything looks for a cosign signature at all:

```json
"ghcr.io/mattcree/kidnix": [
  { "type": "sigstoreSigned",
    "keyPath": "/etc/pki/containers/kidnix.pub",
    "signedIdentity": { "type": "matchRepository" } }
]
```

**That key file is not in this repository, so `ghcr.io/mattcree/kidnix` currently
refuses to pull.** That is intended, not an oversight: the review panel's
position was that an unauthenticated root-level update channel is worse than no
updates, and the machine has no update mechanism today anyway. The build prints
four `!!` lines saying so.

**Why the `cosign verify` command above cannot be turned into a device policy.**
containers/image's `sigstoreSigned` has a `fulcio` mode, but its `subjectEmail`
is matched only against the certificate's SAN **rfc822Name** list, there is no
regexp option, and a GitHub Actions keyless certificate puts the workflow
identity in a SAN **URI**. There is no value that matches. (An invented
`subjectEmailRegexp` is not ignored — it rejects the entire policy file, which
rejects every pull on the machine including `bootc upgrade`.) Full working in
`docs/spikes/panel-wave-c.md` §6a.

**To close it**, which is the prerequisite for ever shipping an update button:

```sh
cosign generate-key-pair                      # produces cosign.key + cosign.pub
# put cosign.key and its password in the repo's Actions secrets as
# COSIGN_PRIVATE_KEY / COSIGN_PASSWORD, and add to build.yml, alongside the
# existing keyless sign:
#     cosign sign --key env://COSIGN_PRIVATE_KEY "$IMAGE@$DIGEST"
cp cosign.pub system_files/etc/pki/containers/kidnix.pub
```

Never commit `cosign.key`. `75-supply-chain.sh` fails the build if the file at
that path contains `PRIVATE KEY`.

Install with the policy enforced (the mode is fixed at install/switch time and
reused by every later `bootc upgrade`, so this is where it is won or lost):

```sh
sudo bootc switch --enforce-container-sigpolicy ghcr.io/mattcree/kidnix:latest
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
