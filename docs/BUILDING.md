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
| `qemu-system-x86_64` + `/dev/kvm` | `vm`, `test-boot` | |
| `edk2-ovmf` | `vm`, `test-boot` | UEFI firmware; bootc images are UEFI-only |
| `uv` | `just lint-python` | optional; the recipe skips cleanly without it |

No linters are installed on the host. `shellcheck`, `hadolint` and `yamllint`
all run from throwaway containers, and `ruff` runs via `uvx`.

## The 30-second loop

```sh
just build        # rootless podman build -> localhost/kidnix:latest
just test-image   # assert the image contains what it should (~2s)
just lint         # shellcheck + hadolint + yamllint + just --fmt + ruff
just ci           # all three, in the order CI runs them
```

`just build` produces three tags: `:latest`, `:<YYYYMMDD>` and `:<version>`.
The first build downloads ~6 GB of base image; rebuilds reuse a dnf cache mount
and take about a minute.

`just test-image` runs `tests/image/test_image.sh` inside the freshly built
container. It is static-only — it proves the *files and packages* are right, and
cannot prove anything that happens at boot. That is `test-boot`'s job.

## Disk images — the one step that needs `sudo`

Everything above is rootless. Building a bootable disk is not, for one specific
reason: `bootc-image-builder` runs privileged and reads images out of **rootful**
podman storage (`/var/lib/containers/storage`), which rootless `podman build`
never writes to.

```sh
just build-qcow2   # -> output/qcow2/disk.qcow2
just build-iso     # -> output/bootiso/install.iso
```

Both print a banner before prompting, and both handle the storage dance for you:

1. `just disk-config` renders `disk_config/config.toml.example` into
   `output/config.toml`, injecting `~/.ssh/id_ed25519.pub`. The rendered file is
   gitignored because it contains your key and a dev password.
2. `_stage-rootful` streams the rootless image into root's storage with
   `podman save | sudo podman load`. It compares image **IDs** first and skips
   the copy only if they match exactly — comparing by tag would cheerfully
   build a disk from a stale image after a rebuild.
3. `bootc-image-builder` runs under `sudo podman` with `--local`, so it reads
   that staged image rather than pulling from a registry.

You will be asked for your password once (possibly twice, if sudo's timestamp
expires mid-build).

> `podman image scp localhost/kidnix:latest root@localhost::` is the tidier
> version of step 2 and is nicer to type interactively, but it needs working
> SSH to `root@localhost`, which CI runners do not have. The `save | load`
> pipe streams without a temp file and behaves identically everywhere, so
> that is what the recipe uses.

## Running a VM

```sh
just build-qcow2         # once
just vm                  # GTK window, KVM accelerated
just vm display=none     # headless
just vm-headless         # headless, serial console on your terminal
just vm-ssh              # ssh parent@localhost:2222
just vm-ssh 'systemctl status gdm'
```

The VM always boots with `-snapshot`, so writes go to a temporary overlay and
`output/qcow2/disk.qcow2` stays pristine. Reboot the VM and you are back to a
clean install — which is exactly what you want when testing a first-boot flow,
and exactly what you do *not* want if you were hoping to keep state. Drop
`-snapshot` from the recipe if you need persistence.

Dev credentials (from `disk_config/config.toml.example`): user `parent`,
password `kidnix`, plus your SSH key. **Development only.**

## The fast "try the newest build" loop

Rebuilding a qcow2 for every change takes minutes. Don't. Once a VM is running,
push the new image to a local registry and have the running system switch onto
it:

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

## The automated boot test

```sh
just test-boot            # boots the qcow2 headless and asserts the kiosk came up
just test-boot --verbose  # tee the serial console while it runs
just test-boot-dry        # validate the harness without booting anything
```

`tests/boot/boot_test.py` boots the disk with `-snapshot`, watches the serial
console for a marker, screenshots the framebuffer over QMP, and exits non-zero
on failure. Artifacts land in `output/`: `boot-serial.log`, `boot.ppm`, and
`boot.png` if ImageMagick or ffmpeg is available.

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

`.github/workflows/boot-test.yml` — builds a qcow2 on the runner (passwordless
sudo) and runs `just test-boot`, uploading the screenshot and serial log as
artifacts. It **skips cleanly and green** if `/dev/kvm` is unavailable, because
a TCG boot of a GNOME stack will not finish inside any sane timeout. If it runs,
it must pass.

Both workflows free ~20 GB before building; the base image alone does not fit in
a stock runner's free space.

## Housekeeping

```sh
just clean        # output/, __pycache__, dangling images
just clean-all    # also removes the kidnix image tags and the local registry
```

`just clean` keeps `base-main` and `kidnix:latest` so the next build is fast.
