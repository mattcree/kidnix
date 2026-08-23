# 07 — The Linux Stack: State of the Art for Building kidnix (2026)

> Research doc for implementers. Everything here was checked against primary sources
> in **August 2026** unless marked otherwise. Facts I could not verify are marked
> **UNVERIFIED** — treat those as spikes, not as design inputs.

---

## 1. Scope & method

**Question:** what is actually available, today, on Fedora-derived immutable Linux to
build kidnix — a bootc image for 4–8 year olds with a custom full-screen Wayland
activity shell, Flatpak activities, a parent admin account, no child network egress,
time limits, local TTS, and automated boot testing?

**Method.** Direct fetches of primary sources: `bootc.dev/bootc` (the bootc book),
`github.com/bootc-dev/*`, `github.com/osbuild/*`, `github.com/ublue-os/*` (including
raw `Containerfile`, `Justfile`, workflow YAML), `gitlab.gnome.org/GNOME/gnome-kiosk`,
`packages.fedoraproject.org` (authoritative for Fedora 44 package versions),
`man.archlinux.org` (authoritative man pages), `help.gnome.org` sysadmin guide,
`docs.flatpak.org`, `flathub.org` app pages, `qemu.org` QMP reference,
`docs.github.com` runner specs, `huggingface.co/rhasspy/piper-voices`.

Roughly 45 fetches. Two sources were unreachable behind Anubis anti-bot
(`gitlab.freedesktop.org`, `docs.fedoraproject.org`, `wiki.archlinux.org`); I routed
around them via mirrors (`github.com/endlessm/malcontent`, `man.archlinux.org`).

**Baseline assumption:** the target is **Fedora 44**, which I confirmed is
**GNOME 50** (`mutter` is `50.4-1.fc44`; `gnome-kiosk` is `50.1-1.fc44`).

---

## 2. Findings

### 2.1 bootc image building

#### The 2026 landscape has moved — three important changes

1. **`osbuild/bootc-image-builder` is archived** (18 June 2026). Its README now says:
   *"The `bootc-image-builder` repository has been merged into the `image-builder`
   repository. All issues have been migrated and this repository has been archived."*
   The functionality lives in `github.com/osbuild/image-builder`. The container
   reference `quay.io/centos-bootc/bootc-image-builder:latest` was still the one
   documented in the archived README **and** is still the default in Universal Blue's
   live `build-disk.yml` (`BIB_IMAGE` env var). Whether a new canonical registry path
   exists post-merge is **UNVERIFIED** — spike this before pinning.
2. **`containers/podman-bootc` is archived** (3 June 2026), superseded by
   **`bootc-dev/bcvk`** ("bootc virtualization kit", Apache-2.0/MIT, ~288 commits,
   actively developed). This is now the ergonomic way to boot a bootc container as a
   VM. Subcommands: `bcvk ephemeral run`, `bcvk ephemeral run-ssh`, `bcvk to-disk`,
   `bcvk libvirt run|ssh|list|stop|start|inspect|rm`. Requires podman + QEMU/KVM.
   Notably it can launch **unprivileged ephemeral VMs** — a big deal for the dev loop.
3. **`greenboot` (shell) is deprecated** in favour of **`greenboot-rs`**
   (`github.com/fedora-iot/greenboot-rs`), a Rust rewrite explicitly targeting bootc
   systems. Fedora ships `greenboot` 0.15.8 (rawhide/F45 confirmed; F44 presence
   **UNVERIFIED**) plus `greenboot-default-health-checks`.

#### Base image choice

| Base | Ref | Notes |
|---|---|---|
| Fedora bootc | `quay.io/fedora/fedora-bootc:44` | Minimal, no desktop, no RPMFusion, no codecs. Fedora-official. |
| Fedora Silverblue (ublue) | `ghcr.io/ublue-os/silverblue-main:latest` | GNOME + ublue fixes. |
| ublue base | `ghcr.io/ublue-os/base-main:latest` | Fedora + "batteries" (codecs, hw enablement). |
| Bazzite/Bluefin/Aurora | `ghcr.io/ublue-os/bluefin:stable` etc. | Full desktop products; heavy. |

**Caveat on ublue `main`:** the repo carries a partial deprecation notice —
*"Universal Blue is trimming support for intermediate images (such as those built in
main) which are not used in our project's final images (Aurora, Bazzite, Bluefin)."*
Since Sept 2025 it builds only `base`, `kinoite`, `silverblue`. `sway`, `budgie` and
`cosmic` images were removed Oct 2025. So `base-main` still exists but is a
second-class citizen; building on it is a mild supply-chain risk for a long-lived
project.

#### The Universal Blue image-template conventions (verified, live)

The template's `Containerfile` (fetched raw) shows the current idiom:

```dockerfile
# Allow build scripts to be referenced without being copied into the final image
FROM scratch AS ctx
COPY build_files /
COPY system_files /system_files

FROM ghcr.io/ublue-os/bazzite:stable@sha256:b923f92d5a5b...   # digest-pinned

RUN --mount=type=bind,from=ctx,source=/,target=/ctx \
    --mount=type=cache,dst=/var/cache \
    --mount=type=cache,dst=/var/log \
    --mount=type=tmpfs,dst=/tmp \
    /ctx/build.sh

### LINTING
RUN bootc container lint
```

Key conventions worth copying verbatim:

- **`FROM scratch AS ctx`** so build scripts never land in the final image layers.
- **digest-pinned base** — reproducibility.
- **`--mount=type=cache,dst=/var/cache` and `dst=/var/log`, `tmpfs` on `/tmp`** — keeps
  `/var` clean, which matters because of bootc's `/var` semantics (see below).
- **`RUN bootc container lint`** as the last layer. (The bootc man page for
  `container lint` was 404 at `bootc.dev/bootc/man/bootc-container-lint.html`; the
  exact check list and `--fatal-warnings` flag are **UNVERIFIED**, but the command
  itself is confirmed in use by ublue.)
- **`system_files/`** tree copied to `/` from `build.sh` — this is where you put
  `/usr/share/wayland-sessions/*.desktop`, systemd units, dconf, polkit rules, nftables
  config. `build_files/build.sh` does packages (`dnf5 install`), COPR enable/disable, and
  `systemctl enable`.

Also of note in the template: an optional `RUN rm /opt && mkdir /opt` to make `/opt`
immutable — Fedora symlinks `/opt` → `/var/opt`, which bootc will not update on upgrade.

#### bootc's filesystem model (this drives most design decisions)

From the bootc book's filesystem page:

- **`/usr`** — the OS. Immutable, part of the composefs read-only root. **Everything
  you ship must live here.**
- **`/etc`** — mutable and persistent; upgrades do a **3-way merge** (new default `/etc`
  as base, then the diff between current and previous `/etc` applied). There is an
  `etc.transient` option to make it ephemeral and eliminate state drift — attractive for
  a kiosk appliance.
- **`/var`** — persistent, but **only initialised from the image on first deployment**.
  *"content included in `/var` in the container image acts like a Docker `VOLUME /var`"*.
  Subsequent image updates to `/var` **do not propagate**.
- **`/opt`** — read-only under composefs by default; escape hatches are symlinking to
  `/var`, `[root] transient = true`, or `ostree-state-overlay@opt.service`.

**Direct consequence for kidnix:** you cannot `flatpak install --system` at build time
and expect it to survive, because the system Flatpak installation is `/var/lib/flatpak`.
Options, in order of preference:

1. **A read-only Flatpak installation under `/usr`.** Define
   `/etc/flatpak/installations.d/kidnix.conf`:
   ```ini
   [Installation "kidnix"]
   Path=/usr/share/flatpak/kidnix
   DisplayName=kidnix Activities
   StorageType=harddisk
   ```
   (Keys `Path`, `DisplayName`, `Priority`, `StorageType` confirmed from
   `flatpak-installation(5)`; `StorageType` ∈ network/mmc/sdcard/harddisk.) Install into
   it at build time with `flatpak --installation=kidnix install ...`. **Spike required:**
   whether Flatpak tolerates a fully read-only installation root at runtime is
   **UNVERIFIED** — it wants to write `.changed` markers and repo locks.
2. **Sideload repos.** `flatpak create-usb` produces an OSTree repo; `flatpak install
   --sideload-repo=/path` (Flatpak ≥ 1.8) or a symlink in the sideload-repos dir makes it
   an offline install source. Ship the repo in `/usr/share/kidnix/flatpak-repo` and do a
   one-shot first-boot install into `/var/lib/flatpak` with no network. This is the
   Endless-style approach and is the **safest bet**.
3. **First-boot systemd unit pulling from Flathub** — what Bluefin effectively does
   (it also ships `flatpak-nuke-fedora.service` to remove Fedora's own remote). Requires
   network on first boot; unacceptable for a child-only device but fine if setup runs as
   the parent.

#### bootc-image-builder usage (verified from ublue's live `Justfile`)

```bash
sudo podman run \
  --rm -it \
  --privileged \
  --pull=newer \
  --net=host \
  --security-opt label=type:unconfined_t \
  -v "$(pwd)/disk_config/disk.toml":/config.toml:ro \
  -v "$(pwd)/output":/output \
  -v /var/lib/containers/storage:/var/lib/containers/storage \
  quay.io/centos-bootc/bootc-image-builder:latest \
  --type qcow2 \
  --use-librepo=True \
  --rootfs=btrfs \
  localhost/kidnix:latest
```

- Output types: `ami, qcow2 (default), vmdk, bootc-installer, anaconda-iso, raw, vhd,
  gce, pxe-tar-xz`.
- **Rootful podman is required** in practice (the `-v /var/lib/containers/storage` bind
  is how it reads your locally built image). There is *experimental* rootless support
  using KVM via an `--in-vm` flag — treat as unreliable.
- `--rootfs` ∈ `ext4|xfs|btrfs`.
- `config.toml`:
  ```toml
  [[customizations.user]]
  name = "parent"
  password = "changeme"
  key = "ssh-ed25519 AAAA... parent@laptop"
  groups = ["wheel"]

  [[customizations.filesystem]]
  mountpoint = "/"
  minsize = "20 GiB"

  [customizations.kernel]
  append = "quiet loglevel=3 systemd.show_status=false plymouth.ignore-serial-consoles"
  ```
  (Schema confirmed: users with name/password/key/groups; filesystem mountpoint/minsize;
  kernel append; installer/kickstart for ISO.)

#### Anaconda ISO / install media

`--type anaconda-iso` produces an installable ISO. Under the hood the kickstart uses the
**`ostreecontainer`** command (pykickstart, marked *experimental*):

```
ostreecontainer --url=ghcr.io/you/kidnix:latest --transport=registry \
                --no-signature-verification --stateroot=default
```

Options confirmed: `--stateroot`, `--url`, `--transport` (registry/oci/oci-archive),
`--remote`, `--no-signature-verification`. **`ostreecontainer` cannot be combined with
`ostreesetup` or `bootc`.** You can supply your own kickstart via
`[customizations.installer.kickstart] contents = """..."""` in `config.toml`.

#### CI: what Universal Blue actually does

`ublue-os/image-template/.github/workflows/build.yml` (fetched):
- Triggers: PR to main, daily cron `05 10 * * *`, push to main (README excluded),
  `workflow_dispatch`.
- `actions/checkout@v7`, installs `just`, runs the Justfile build.
- **rpm-ostree rechunk** step for smaller deltas.
- Registry login → `podman push` to `ghcr.io` — gated to non-PR main-branch events.
- **Cosign v3.1.2** signing with a repo secret. Setup is:
  ```bash
  COSIGN_PASSWORD="" cosign generate-key-pair   # commit cosign.pub, NEVER cosign.key
  ```
  private key goes into the Actions secret `SIGNING_SECRET`.
- Permissions: `contents`, `packages`, `id-token` (OIDC).

`build-disk.yml` (fetched) uses **`osbuild/bootc-image-builder-action`** rather than a
raw podman invocation. Inputs: `image`, `config-file`, `types` (default `qcow2`),
`rootfs`, `builder-image` (default `quay.io/centos-bootc/bootc-image-builder:latest`).
Runners: `ubuntu-24.04` / `ubuntu-24.04-arm`. Disk pressure handled by
`ublue-os/remove-unwanted-software`. Artifacts either uploaded to Actions or rclone-synced
to S3.

**Rechunking** (`github.com/hhd-dev/rechunk`) flattens the OSTree tree and re-partitions
into N equal layers. Claimed benefit: **40% smaller weekly updates, 60–80% for frequent
updates**. Costs **6–10 minutes** per build and **requires rootful podman on Ubuntu 24.04**.

#### Dev loop

```bash
# on the dev host
podman build -t localhost/kidnix:dev .
# in the VM (bootc >= 1.x supports containers-storage transport)
sudo bootc switch --transport containers-storage localhost/kidnix:dev
```
`--transport` values confirmed from the bootc book: `registry` (default), `oci`,
`oci-archive`, `docker-daemon`, `containers-storage`.

A local registry (`podman run -d -p 5000:5000 registry:2`, then
`podman push --tls-verify=false localhost:5000/kidnix:dev` and `bootc switch
--tls-verify=false localhost:5000/kidnix:dev`) is the more robust variant because the VM
does not share the host's container store. `bcvk` mostly obviates this.

Fedora 44 ships **`bootc` 1.16.7-1.fc44** (same version in F45/rawhide).

---

### 2.2 Kiosk / session

#### gnome-kiosk is the right primitive and it is well-packaged

`gnome-kiosk` is *"a mutter based compositor for kiosks… suitable for fixed purpose, or
single application deployments"*. Fedora 44 has **50.1-1.fc44**, actively maintained by
Red Hat (rstrode). Subpackages: `gnome-kiosk-a11y`, `gnome-kiosk-notification-daemon`,
`gnome-kiosk-root-menu`, `gnome-kiosk-script-session`, `gnome-kiosk-search-appliance`.

Files it installs (verified from the Fedora file list):

```
/usr/bin/gnome-kiosk
/usr/lib/systemd/user/org.gnome.Kiosk.target
/usr/lib/systemd/user/org.gnome.Kiosk@wayland.service
/usr/share/applications/org.gnome.Kiosk.desktop
/usr/share/dconf/profile/gnomekiosk
/usr/share/gnome-kiosk/gnomekiosk.dconf.compiled
/usr/share/gnome-kiosk/window-config.ini
/usr/share/doc/gnome-kiosk/CONFIG.md
```

`gnome-kiosk-script-session` adds:

```
/usr/bin/gnome-kiosk-script
/usr/share/wayland-sessions/gnome-kiosk-script-wayland.desktop
/usr/share/gnome-session/sessions/gnome-kiosk-script.session
/usr/share/applications/org.gnome.Kiosk.Script.desktop
/usr/lib/systemd/user/org.gnome.Kiosk.Script.service
/usr/lib/systemd/user/gnome-session@gnome-kiosk-script.target.d/session.conf
```

The session desktop file is essentially:

```ini
[Desktop Entry]
Name=Kiosk Script Session (Wayland Display Server)
Comment=This session logs you into the session started by ~/.local/bin/gnome-kiosk-script
Exec=gnome-session --session gnome-kiosk-script
DesktopNames=GNOME-Kiosk;GNOME
X-GDM-SessionRegisters=false
X-GDM-CanRunHeadless=true
Type=Application
```

**`X-GDM-CanRunHeadless=true` is a gift for CI** — it means the session can be started
without a physical display.

The upstream README documents the three-file recipe for a custom kiosk session:
1. a session file in `/usr/share/wayland-sessions` telling the DM to start GNOME Session
   in a custom mode;
2. a session description in `/usr/share/gnome-session/sessions` listing components
   (gnome-kiosk + your app);
3. a `.desktop` for your app.

So kidnix ships `/usr/share/wayland-sessions/kidnix-shell.desktop`,
`/usr/share/gnome-session/sessions/kidnix.session` with
`RequiredComponents=org.gnome.Kiosk;dev.kidnix.Shell;`, and a systemd user unit for the
shell with `Restart=always` / `RestartSec=1` so a crashed shell comes straight back
(confirmed `Restart=` semantics from `systemd.service(5)`).

**Automatic fullscreen** is a documented gnome-kiosk feature ("automatic fullscreen
application launching"). `window-config.ini` (see `/usr/share/doc/gnome-kiosk/CONFIG.md`)
controls per-window placement/fullscreen policy — I could not fetch CONFIG.md
(gitlab paths 404'd), so **the exact ini schema is UNVERIFIED**; read it on a running
system.

#### Runners-up

- **cage** (`cage` 0.3.1-1.fc44) — wlroots kiosk, runs a single maximised app. Tiny and
  predictable, but: single app only, no XDG portal ecosystem set up for you, no a11y
  bus, no GNOME session integration, and you inherit the wlroots screenshot/input tools
  (grim/wlrctl) which is actually a *testing advantage*. Weak on multi-window Flatpak
  apps that spawn dialogs.
- **labwc** — Fedora 44 has an old **0.9.6**; F45/rawhide jumps to **0.20.0**. That
  version skew is a red flag for building on F44.
- **Plasma kiosk** (`kiosk`/Kiosk framework via KDE) — mature lockdown (`kdeglobals`
  `[KDE Action Restrictions]`) but drags in the whole Plasma stack. Not evaluated in
  depth here.

#### Two users, two sessions

GDM autologin is a global setting:

```ini
# /etc/gdm/custom.conf
[daemon]
AutomaticLoginEnable=True
AutomaticLogin=kid
```

The **session** each user gets is stored per-user by AccountsService in
`/var/lib/AccountsService/users/<name>`:

```ini
[User]
Session=kidnix-shell
XSession=
SystemAccount=false
```

The `parent` user simply has no override (or `Session=gnome`) and gets stock GNOME on
Wayland. Note `/var/lib/AccountsService` is under `/var`, so it is **first-boot-only**
from the image — write it from a first-boot systemd unit or a `tmpfiles.d` snippet, not
by baking the file into the container. This is a classic bootc footgun.

#### Locking the child session down

- **dconf lockdown** (verified pattern from the GNOME sysadmin guide):
  ```
  # /etc/dconf/db/kid.d/00-lockdown
  [org/gnome/desktop/lockdown]
  disable-command-line=true
  disable-user-switching=true
  disable-log-out=true
  disable-lock-screen=true
  user-administration-disabled=true

  # /etc/dconf/db/kid.d/locks/lockdown
  /org/gnome/desktop/lockdown/disable-command-line
  /org/gnome/desktop/lockdown/disable-user-switching
  ```
  then `dconf update`. gnome-kiosk already ships its own dconf **profile**
  (`/usr/share/dconf/profile/gnomekiosk`) — model kidnix's on that, and set
  `/etc/dconf/profile/user` per-session via the session's `dconf` profile name.
  (The precise keys beyond `disable-command-line` are from the standard
  `org.gnome.desktop.lockdown` schema; only `disable-command-line` was verified verbatim
  in the guide — **the rest are UNVERIFIED against GNOME 50's schema**, check with
  `gsettings list-keys org.gnome.desktop.lockdown`.)
- **VT switching.** Compositor-level Ctrl+Alt+F<n> handling is baked into mutter and is
  not a gsettings key. The practical mitigation is to remove the VTs to switch *to*:
  ```ini
  # /etc/systemd/logind.conf.d/kiosk.conf
  [Login]
  NAutoVTs=0
  ReserveVT=0
  KillUserProcesses=yes
  ```
  `NAutoVTs=0` disables autovt spawning (default 6); `ReserveVT=0` disables the reserved
  VT (default 6). Both verified from `logind.conf(5)`. This does **not** stop the
  keystroke reaching the kernel VT layer, only ensures nothing useful is there.
  **UNVERIFIED:** whether mutter/gnome-kiosk has a build/runtime option to swallow VT
  switch keys entirely. Belt-and-braces: also disable `getty@.service` instances and
  strip `sysrq` via `kernel.sysrq=0`.
- **Keyboard shortcuts.** Wipe the `org.gnome.desktop.wm.keybindings` and
  `org.gnome.mutter.keybindings` schemas to `@as []` in the child's dconf db and lock
  them. gnome-kiosk deliberately implements very few keybindings itself (the README
  calls out Super+Space / Shift+Super+Space for keyboard layout as the *only* built-ins).
  Alt+F4 (`close`) is a `wm.keybindings` key — settable to `[]`.
- **Screen lock.** gnome-kiosk's README lists screen locking as a *planned* feature —
  i.e. **there is no lock screen in gnome-kiosk today**. For kidnix that is arguably
  correct (a 5-year-old must never be able to lock themselves out), but it means the
  "time's up" experience must be implemented by your shell, not by a locker.
- **Portals.** `xdg-desktop-portal` picks its backend from `XDG_CURRENT_DESKTOP`
  (lowercased) → `xdg-desktop-portal/<desktop>-portals.conf`, falling back to
  `portals.conf`. Since our session sets `DesktopNames=GNOME-Kiosk;GNOME`, ship:
  ```ini
  # /usr/share/xdg-desktop-portal/gnome-kiosk-portals.conf
  [preferred]
  default=gtk
  org.freedesktop.impl.portal.Access=none
  org.freedesktop.impl.portal.Screenshot=none
  org.freedesktop.impl.portal.Camera=none
  ```
  `none` disables an interface; `*` picks the first available lexicographically. Using
  `xdg-desktop-portal-gtk` rather than `-gnome` avoids pulling gnome-shell in. **Spike:**
  the GTK file chooser portal in a kiosk with no window manager decorations — verify it
  renders and is dismissible.

---

### 2.3 Parental-control plumbing

#### malcontent — useful, but do not rely on it as a security boundary

Fedora 44 ships **malcontent 0.14.0-1.fc44** (0.14.0-7.fc45 in rawhide). Subpackages:
`malcontent-control`, `malcontent-libs`, `malcontent-pam`, `-devel`, `-doc`.

Components: `libmalcontent` (query API), `libmalcontent-ui`, `malcontent-control` (GUI),
`malcontent-client` (CLI). Two policy types:
1. **App filter** — allow/deny list of installed apps, "particularly Flatpak apps".
2. **OARS content ratings** — max acceptable rating per OARS category
   (`violence-realistic=mild` etc.), used to block *installation* of apps above threshold.

Storage: `/var/lib/AccountsService/users/${user}`, exposed over D-Bus via
accounts-service. **Enforcement is per-application and voluntary** — GNOME Software,
Flatpak and GNOME Shell each query the filter and enforce independently.

The README is explicit: *"A sufficiently technically advanced user may always work
around these parental controls"* — it is **not** a MAC system like SELinux/AppArmor.

**Verdict for kidnix:** malcontent is the right place to *record* policy (it's the
freedesktop-blessed schema, it shows up in `malcontent-control` for the parent, and
GNOME tooling respects it) but the *actual* enforcement in kidnix must be structural:
the child's shell only knows about the activities we ship, and there is no other way to
launch anything.

A useful side-effect: Flathub OARS ratings are visible on app pages. Note that
**SuperTuxKart, Stellarium and Luanti are all rated 13+**, while GCompris, Tux Paint,
SuperTux, KTuberling, Blinken and Nibbles are **3+**. If you set a 3+ OARS ceiling you
will exclude Luanti and Stellarium — which may be exactly right for 4–8, but decide
deliberately.

#### polkit

Verified from `polkit(8)`: JS rules live in `/etc/polkit-1/rules.d` (also `/run`,
`/usr/local/share`, `/usr/share`), ECMA-262 ed.5. Results:
`polkit.Result.YES|NO|AUTH_SELF|AUTH_ADMIN|AUTH_SELF_KEEP|AUTH_ADMIN_KEEP`. Subject
properties: `subject.user`, `subject.local`, `subject.active`, `subject.isInGroup()`.

```javascript
// /usr/share/polkit-1/rules.d/10-kidnix-lockdown.rules
polkit.addRule(function(action, subject) {
    if (subject.user !== "kid") return polkit.Result.NOT_HANDLED;
    if (action.id.indexOf("org.freedesktop.NetworkManager.") === 0 ||
        action.id.indexOf("org.freedesktop.Flatpak.")        === 0 ||
        action.id.indexOf("org.freedesktop.login1.")         === 0 ||
        action.id.indexOf("org.projectatomic.rpmostree1.")   === 0 ||
        action.id.indexOf("org.fedoraproject.bootc.")        === 0) {
        return polkit.Result.NO;
    }
});
```

Ship this in `/usr/share/polkit-1/rules.d/` (image-owned, immutable), not `/etc`.

`NetworkManager.conf` also has `[main] auth-polkit=true|false|root-only` (verified):
`root-only` disables polkit entirely and denies all non-root requests. That is a blunt
but effective global setting if the parent uses `nmtui` via `sudo`.

#### Per-UID network egress

**firewalld rich rules cannot match UID.** Confirmed from
`firewalld.richlanguage(5)`: matching is by address/MAC/ipset/protocol/port/service/ICMP
only. So use nftables directly.

`meta skuid` matches the **UID owning the originating socket** and only makes sense in
the `output` hook (verified from wiki.nftables.org). Caveat from the same page: setuid
binaries (e.g. `ping`) appear as their effective uid, so a setuid helper could leak.

```nft
# /etc/nftables/kidnix-egress.nft  (included from /etc/sysconfig/nftables.conf)
table inet kidnix {
    chain output {
        type filter hook output priority filter; policy accept;

        # loopback and local TTS/portal traffic is fine
        oifname "lo" accept

        # allow DNS+HTTPS only for the parent-controlled updater
        meta skuid 0 accept

        # everything the child user emits: drop
        meta skuid "kid" counter reject with icmpx type admin-prohibited
    }
}
```

Belt-and-braces (recommended — do both):
- **Flatpak override.** `flatpak override --unshare=network <appid>` per app, or
  system-wide global `flatpak override --unshare=network` (no app id = global default).
  Overrides live in the installation's `overrides/` dir; user overrides in
  `$XDG_DATA_HOME/flatpak/overrides`. Verified from `flatpak-override(1)`.
  Note the documented gotcha in the Flatpak permissions docs: granting `--share=network`
  *"also grants access to all host services listening on abstract Unix sockets"* — one
  more reason to keep it off.
- **Disable remotes for the child.** `flatpak remote-modify --disable flathub` on the
  child's user installation, and don't give the child user polkit rights to
  `org.freedesktop.Flatpak.*`.

The nftables rule is the load-bearing one: it survives a Flatpak app that finds a hole,
and it catches non-Flatpak processes too.

#### Time limits

There are three mechanisms and none of them alone is sufficient:

| Mechanism | What it does | Why it's not enough |
|---|---|---|
| `pam_time` (+`/etc/security/time.conf`, **account** stack) | Denies *login* in forbidden windows | Verified: it gates authorisation only. It does **not** terminate a session already running. |
| `logind` `IdleAction=`/`IdleActionSec=` | System-wide idle action (`lock`, `suspend`, `poweroff`) | Idle ≠ time-used. Global, not per-user. |
| `systemd` `RuntimeMaxSec=` on the user's graphical session unit | Hard kill after N seconds | Verified in `systemd.service(5)`: unit fails after the limit. Blunt — no warning, no grace, no "5 more minutes". |

**Recommended shape:** a per-user systemd *user* service (`kidnix-timekeeper.service`)
owned by the shell that (a) accounts wall-clock usage into a state file under
`/var/lib/kidnix/`, (b) tells the shell to show warnings, (c) at expiry asks the shell to
show a "time's up" screen, then (d) `loginctl terminate-user kid` after a grace period.
Back it with a *system* unit using `RuntimeMaxSec=` as a fail-safe so a wedged shell
can't grant unlimited time. `logind.conf` `KillUserProcesses=yes` and
`UserStopDelaySec=0` make termination clean (both verified). `SessionsMax` exists but
defaults to 8192 and is not a useful control here.

---

### 2.4 Speech & audio

Fedora 44 baseline (all verified via `mdapi.fedoraproject.org/f44/pkg/<name>`):
`speech-dispatcher 0.12.1-6.fc44`, `python3-speechd 0.12.1-6.fc44`,
`espeak-ng 1.52.0-3.fc44`, `festival 2.5.0-29.fc44`, `pipewire 1.6.2`,
`wireplumber 0.5.14`, `at-spi2-core 2.60.0`, `orca 50.0.9`, `flatpak 1.17.6`.

#### speech-dispatcher

Upstream 0.12.1 was tagged **2025-05-06**; master is very much alive (last commit
2026-08-20). 0.12.0 added **socket activation** and moved modules to
`/usr/libexec/speech-dispatcher-modules/`. Fedora subpackages that matter:
`speech-dispatcher-espeak-ng`, `speech-dispatcher-festival`, **`python3-speechd`**.

In a kiosk, don't rely on autospawn — enable the socket explicitly so the first utterance
isn't delayed:

```bash
systemctl --user enable --now speech-dispatcherd.socket
```

Config: `/etc/speech-dispatcher/speechd.conf` + `/etc/speech-dispatcher/modules/*.conf`,
overridden per-user at `~/.config/speech-dispatcher/speechd.conf`. Directives that
matter: `AddModule`, `DefaultModule`, `DefaultLanguage`, `DefaultVoiceType`,
`AudioOutputMethod "pulse"` (goes to pipewire-pulse), `DefaultVolume/Rate/Pitch`. Since
0.11 the **server** plays audio, so you get one PipeWire stream rather than one per
module — which is what you want when capping volume.

Shell integration: `python3-speechd`'s `speechd.SSIPClient`, or `spd-say -o <module>
-l en-GB -r <rate> -i <volume> "text"` (`-O` lists modules, `-L` lists voices).

#### Piper — the key 2026 finding

- `rhasspy/piper` was **archived read-only in Oct 2025**. The live project is
  **`OHF-Voice/piper1-gpl`** (Open Home Foundation), relicensed **MIT → GPL-3.0-or-later**.
  PyPI **`piper-tts` 1.7.0, released 2026-08-15**. Actively developed, but the README
  carries a **"Looking for Maintainers"** banner — maintained-but-thin.
- **Fedora has `python3-piper-tts 1.4.2-5` in F45/rawhide only — not in F44.** There is
  **no `piper-voices` RPM** (a full voice set is ~2 GB, the stated blocker on
  fedora-devel) and **no Piper Flatpak**.
- **speech-dispatcher master now has a native Piper module**: `src/modules/cxxpiper.cpp`
  with `config/modules/cxxpiper.conf` (commits through 2026-05-04), taking `ModelPath`,
  `ConfigPath`, `ESpeakNGDataDirPath`, `UseCUDA`, and exposing multi-speaker models as
  `<model>~<speaker-id>~<mnemonic>`. **It is not in 0.12.1, therefore not in Fedora 44.**
  There is no `sd_piper` binary. Until it ships, the only route is the **generic module**
  (`sd_generic`) shelling out to Piper. Upstream ships `mimic3-generic.conf` as the
  worked example; there is no released `piper.conf`.

```
# /etc/speech-dispatcher/modules/piper-generic.conf   (pattern, VERIFY on-target)
GenericExecuteSynth "printf %s \'$DATA\' | python3 -m piper -m $VOICE --output-raw | \
    aplay -r 22050 -f S16_LE -c 1 -q -"
GenericCmdDependency "python3"
AddVoice "en" "FEMALE1" "en_GB-cori-high"
DefaultCharset "UTF-8"
```
plus `AddModule "piper-generic" "sd_generic" "piper-generic.conf"` in `speechd.conf`.
**Caveat:** the Piper CLI reloads the model on every invocation, which is far too slow
for hover-to-read. For a kiosk, run Piper's bundled HTTP server
(`pip install piper-tts[http]`) as a systemd **user** service so the model stays resident,
and have `GenericExecuteSynth` curl it.

**en_GB voices** (sizes from `voices.json`, licences from each `MODEL_CARD`):

| Voice | Quality | .onnx | Speakers | Dataset licence |
|---|---|---|---|---|
| `en_GB-cori-high` | high | 108.9 MB | 1 | **public domain** (LibriVox, 24 h) |
| `en_GB-cori-medium` | medium | 60.6 MB | 1 | **public domain** |
| `en_GB-alba-medium` | medium | 60.3 MB | 1 | CC-BY-4.0 |
| `en_GB-jenny_dioco-medium` | medium | 60.3 MB | 1 | commercial OK, **attribution required** |
| `en_GB-northern_english_male-medium` | medium | 60.3 MB | 1 | CC-BY-SA-4.0 (OpenSLR 83) |
| `en_GB-semaine-medium` | medium | 73.2 MB | 4 | **CC-BY-NC-SA-4.0 — non-commercial** |
| `en_GB-southern_english_female-low` | low | 60.2 MB | 1 | CC-BY-SA-4.0 |
| `en_GB-alan-low` / `-medium` | low/med | ~60 MB | 1 | "See URL" — **unclear, avoid** |
| `en_GB-aru-medium` | medium | 73.2 MB | 12 | CC-BY-4.0 |
| `en_GB-vctk-medium` | medium | 73.4 MB | 109 | CC-BY-4.0 |

**Pick `en_GB-cori-high`** — public domain, warm female UK read-aloud, the only en_GB
"high". Fall back to `en_GB-cori-medium` on low-CPU hardware. Sample rate is
**22,050 Hz** for medium/high (verified on alba + jenny); `low` models are 16 kHz
(**UNVERIFIED**, standard Piper convention). Note Piper's own README says the models are
"intended for personal use and text-to-speech research only" — worth a legal glance
before distributing an image. Latency: roughly RTF 0.1–0.3 single-threaded for medium
once resident, ~2× for high (**UNVERIFIED** — no published 2026 benchmark found;
measure on target).

#### TTS alternatives

| Engine | Fedora 44 | Status | Verdict |
|---|---|---|---|
| **espeak-ng** | `1.52.0-3.fc44` | Alive (commit 2026-08-19) | Robotic but always works; also Piper's phonemizer. **Ship as fallback.** |
| festival | `2.5.0-29.fc44` | Frozen | Skip |
| RHVoice | **not packaged** | Alive (1.18.4, 2026-03-31) | Would need packaging; between espeak and Piper. Skip |
| Mimic3 | no | **Dead** (last commit 2025-03-25) | Skip |
| Kokoro-82M | no | Model frozen 2025; Apache-2.0; ONNX ~330 MB fp32 / ~90 MB int8 | Great quality, no speech-dispatcher module, heavier CPU. Not worth it vs Piper |
| MaryTTS | no | Dormant Java | Skip |

#### Orca / AT-SPI (matters for testing, not for the child)

- **Orca is alive**: tags `50.2` (2026-05-26) and `51.beta` (2026-08-03); Fedora 44 has
  `orca 50.0.9`. `at-spi2-core 2.60.0` is present, so **AT-SPI over D-Bus still works on
  Wayland** and remains the GNOME 50 accessibility stack.
- **"Newton" / Wayland-native a11y has NOT landed.** Checked
  `gitlab.freedesktop.org/wayland/wayland-protocols` staging via API: **no accessibility
  protocol** is in staging as of Aug 2026 (staging = alpha-modifier, color-management,
  ext-*, xdg-*, …). AccessKit itself is very active (commit 2026-08-21) but a canonical
  "Newton" repo could not be located — **UNVERIFIED; do not build on it.**
- **Implication:** AT-SPI is a *viable* automation hook today. Keep it enabled in the
  test image (`QT_LINUX_ACCESSIBILITY_ALWAYS_ON=1` for the Qt-based activities) even if
  you disable it in production. `gnome-kiosk-a11y` exists in Fedora 44 ("accessibility
  panel for gnome-kiosk"), implying the a11y bus is expected to work inside kiosk sessions.

#### Volume capping / loudness safety

Honest summary: **PipeWire/WirePlumber has no declarative "max volume" setting.** Three
mechanisms actually exist:

1. **`wpctl set-volume -l <limit>`** — verified in WirePlumber's `src/tools/wpctl.c`
   (`--limit`, *"Limits the final volume percentage to below this value, 1.0 is 100%"*).
   It clamps **that invocation only**; it is not persistent policy. Useful *if the shell
   owns all volume keys*: route every change through
   `wpctl set-volume -l 0.7 @DEFAULT_AUDIO_SINK@ 5%+`.
2. **Hardware/ALSA ceiling** — cap the mixer once at boot (`amixer -c0 sset Master 70%`,
   `alsactl store`) and set `api.alsa.soft-mixer = true` in a WirePlumber ALSA rule so
   PipeWire never touches the hardware mixer. **Most robust hard cap.**
3. **filter-chain sink.** PipeWire 1.6 `module-filter-chain` builtins are `clamp`
   (Min/Max), `linear` (Mult/Add), `noisegate`, `ramp`, biquads, convolver — **no
   lookahead limiter/compressor**. For a real limiter load LADSPA: Fedora 44 has
   `ladspa-swh-plugins-0.4.17` (fast lookahead limiter) and `lsp-plugins-ladspa-1.2.27`.
   Simplest image-baked version, in `/usr/share/pipewire/pipewire.conf.d/50-kid-limiter.conf`:
   an `Audio/Sink` filter-chain of `linear` (Mult = 0.6) → `clamp` (Min −0.8 / Max 0.8),
   made the default sink, with the raw device hidden from the child.

**WirePlumber 0.5 config is SPA-JSON, not Lua** (Lua survives only for scripts).
Drop-ins: `/usr/share/wireplumber/wireplumber.conf.d/*.conf`,
`/etc/wireplumber/wireplumber.conf.d/*.conf`, `~/.config/wireplumber/wireplumber.conf.d/*.conf`.
Upstream examples live in `src/config/wireplumber.conf.d.examples/`.

**Flatpak audio:** `--socket=pulseaudio` bind-mounts the pipewire-pulse socket.
WirePlumber's `access.conf` example shows clients with `pipewire.access = "flatpak"` get
only `rx` by default, and full `all` only for `media.category = "Manager"`. Whether
pipewire-pulse marks ordinary PulseAudio clients as `Manager` (which would let a Flatpak
`pactl set-sink-volume` the master sink) is **UNVERIFIED**. Assume it can, and rely on
mechanism 2 or 3. Optionally add an `access.rules` drop-in matching
`pipewire.access = "flatpak"` with `default_permissions = "r"`.

---

### 2.5 Candidate activities on Flathub (verified Aug 2026)

Verified via `flathub.org/api/v2/appstream/<id>` + `/api/v2/summary/<id>` (build
timestamp, installed size, sandbox sockets, runtime EOL flag) and the Flathub web pages.
"Wayland" = `wayland` present in the Flatpak socket list.

| App ID | Version | Last build | Wayland | Installed | Offline | Status |
|---|---|---|---|---|---|---|
| `org.kde.gcompris` | 26.1 | **2026-07-26** | ✅ | 91 MB | ⚠️ **downloads voices** | Alive, **Flathub-verified (KDE)**, AGPL-3.0. Has `shared=network`. |
| `org.tuxpaint.Tuxpaint` | 0.9.35 | 2026-05-26 | ✅ | 150 MB | ✅ no network perm | Alive, verified, GPL-2.0+. Best-in-class 4–8. |
| `org.kde.ktuberling` | 26.08.0 | **2026-08-20** | ✅ | 31 MB | ✅ | Alive, verified. *Perfect* 4–6 (spoken part names). |
| `org.kde.blinken` | 26.08.0 | 2026-08-20 | ✅ | 1 MB | ✅ | Alive, verified. Simon-says. Ideal 4–8. |
| `org.kde.klettres` | 26.04.3 | 2026-07-03 | ✅ | 44 MB | ✅ | Alive, verified. Alphabet/phonics with recorded audio. |
| `org.kde.kolf` | 26.08.0 | 2026-08-20 | ✅ | 4 MB | ✅ | Alive, verified. Mini-golf, 5+. |
| `org.gnome.Nibbles` | 4.5.2 | 2026-05-10 | ✅ | 2 MB | ✅ | Alive. Not GNOME-official on Flathub. |
| `org.turbowarp.TurboWarp` | 1.16.0 | 2026-05-25 | ✅ | 382 MB | ✅ **fully offline** | **Alive** (repo commit 2026-07-10), GPL-3.0. **This is your Scratch.** |
| `org.supertuxproject.SuperTux` | 0.7.0 | 2026-03-29 | ✅ | 357 MB | ✅ | Alive, not verified. |
| `org.luanti.luanti` | 5.16.1 | 2026-08-01 | ✅ | 27 MB | ✅ (pre-install games) | Alive, verified. **13+** OARS. |
| `org.stellarium.Stellarium` | 26.2 | 2026-08-11 | ✅ | **671 MB** | ✅ core | Alive, verified. **13+**. |
| `net.supertuxkart.SuperTuxKart` | 1.5 | 2025-12-25 | ✅ | **791 MB** | ✅ | Alive, verified. **13+**. Huge. |
| `org.kde.minuet` | 0.4.0.26042 | 2026-06-04 | ✅ | 32 MB | ✅ | Alive, verified. Best simple music pick (ear training). |
| `org.kde.kturtle` | 26.04.3 | 2026-07-03 | ✅ | 1 MB | ✅ | Alive, verified. Logo turtle, 7+. |
| `org.kde.khangman` / `org.kde.kanagram` | 26.08 / 26.04.2 | 2026-07/08 | ✅ | 12 / 11 MB | ✅ | Alive, verified. 7+ (needs reading). |
| `org.kiwix.desktop` | 2.4.1 | **2024-12-20** | ✅ | 173 MB | ✅ with local ZIMs | **Flathub build 20 months stale; runtime `org.kde.Platform/5.15-23.08` is EOL.** Upstream repo *is* alive (2.5.1, 2026-01-04). **Risk.** |
| `com.tux4kids.tuxtype` | 1.8.3 (2014) | 2026-03-14 | ❌ **X11** | 25 MB | ✅ | Upstream dead, packaging alive. ID is **`com.tux4kids.tuxtype`**, not `net.sourceforge.*`. |
| `com.tux4kids.tuxmath` | 2.0.3 (2013) | 2026-03-14 | ❌ **X11** | 26 MB | ✅ | Upstream dead. ID is **`com.tux4kids.tuxmath`**. |
| `org.kde.marble` | 26.04.3 | 2026-07-03 | ✅ | 323 MB | ⚠️ **needs network for tiles** | Alive, verified. Offline = bundled low-res globe only. |
| `org.sugarlabs.Paint` / `.Speak` / `.MusicBlocks` / `.TypingTurtle` / … | 2019–2024 | **2026-04** | ❌ **X11** | 12–305 MB | ✅ | Rebuilt Apr 2026; `sugarlabs/sugar` commit 2026-03-17. **Sugar activities run standalone as Flatpaks — no Sugar shell needed.** |
| `edu.mit.Scratch` | 3.10.1 (2020) | **2023-12-08** | ❌ X11 | 421 MB | ✅ | **Abandoned; runtime 22.08 EOL. Do not ship.** |
| `org.learningequality.Kolibri` | 3.8 (2024) | 2026-01-23 | ✅ | 217 MB | ❌ content downloads | Stale; runtime GNOME 47 EOL. Skip. |
| `net.sonic_pi.SonicPi` | 5.0.0 | 2026-08-08 | ✅ | 126 MB | ✅ | Alive. 8+, code-heavy. |
| `io.lmms.LMMS` | 1.2.2 (2020) | — | — | — | — | Stale on Flathub. Skip. |

**Not on Flathub at all** (verified 404): `org.kde.step`, `net.sourceforge.tuxtype`,
`net.sourceforge.tuxmath`, `org.sugarlabs.Sugarizer`, `org.gnu.Solfege`,
`io.github.pianobooster.PianoBooster`, Childsplay, OMNITUX, Pysiogame. (TuxGuitar's real
ID is `ar.com.tuxguitar.TuxGuitar`.)

**ScratchJr: there is no supported Linux build.** `jfo8000/ScratchJr-Desktop`'s last
commit was **2020-11-21** — dead. No Flathub package. Use **TurboWarp** (a fully offline
Scratch 3 fork, actively maintained) or Sugar's Music Blocks instead. `edu.mit.Scratch`
is abandoned on an EOL runtime; do not ship it.

**Luanti rename confirmed:** `net.minetest.Minetest` still exists but is frozen at 5.11.0
(2025-02-14). Use `org.luanti.luanti`.

#### The offline problem, concretely

- **GCompris is the big one.** The Flatpak is only **91 MB installed**; voices, word
  lists and background music are **not bundled**. Verified in
  `src/core/ApplicationSettings.cpp`: `DEFAULT_DOWNLOAD_SERVER = "https://cdn.kde.org/gcompris"`,
  and `DownloadManager.cpp` fetches `data3/voices-ogg/<Contents>` + `voices-<locale>.rcc`,
  `data3/words/`, `data3/backgroundMusic/`. **Mitigation:** `getSystemResourcePaths()`
  also searches `QStandardPaths::GenericDataLocation + "/GCompris"` and the app's own
  `.../rcc/` dir. So at image-build time pre-fetch the `.rcc` files **plus their
  `Contents` index files** into
  `~/.var/app/org.kde.gcompris/data/GCompris/data3/{voices-ogg,words,backgroundMusic}/`,
  set `downloadServerUrl`, disable automatic downloads in GCompris' admin config, and
  `flatpak override --unshare=network org.kde.gcompris`.
- **Kiwix ZIM sizes** (verified from `library.kiwix.org/catalog/v2/entries`):
  Wikipedia Simple English maxi **3341 MB** / nopic **944 MB** / **mini 450 MB**;
  **Vikidia en nopic 8 MB**; Vikidia fr maxi 1317 MB; TED Kids 3014 MB; TED-Ed 5798 MB;
  Simple Wiktionary 25 MB. **There is no `wikipedia_en_for_kids` or Wikijunior ZIM** —
  those searches returned nothing. Practical kid bundle:
  `wikipedia_en-simple_all_mini` (450 MB) + `vikidia_en_all_nopic` (8 MB) ≈ **458 MB**.
- Everything else in the table (SuperTuxKart, KDE apps that carry `shared=network`
  boilerplate, TuxMath, TurboWarp, Luanti) functions fully offline — strip the permission
  with `flatpak override --unshare=network`.

#### Shortlist for kidnix v0.1

**Core (4–6):** GCompris (voices baked in), Tux Paint, KTuberling, Blinken, KLettres,
Kolf, Nibbles. **Growth (6–8):** TurboWarp, SuperTux, Minuet, KTurtle, Stellarium,
Luanti, Kiwix + two small ZIMs. **Avoid:** `edu.mit.Scratch`, Kolibri, LMMS, anything
ScratchJr.

---

### 2.6 Shell technology

Confirmed versions: **GTK 4.20–4.24** era (gtk4-rs 0.11.x binds `v4_20`…`v4_24`;
release dates reported by the GitHub releases page looked implausible and are
**UNVERIFIED**). **WebKitGTK 2.52.6, released 19 Aug 2026.** **Godot 4.7.2, released
18 Aug 2026.** Flutter's own Linux docs still list `libgtk-3-0` as the runtime
dependency — i.e. the embedder is **GTK3, hence XWayland**, in 2026.

| Option | Startup | Animation | TTS | Wayland | Testability | Verdict |
|---|---|---|---|---|---|---|
| **GTK4 + libadwaita (Python/Rust)** | Fast | Good (Adw.TimedAnimation/SpringAnimation, GPU renderer since 4.14) | Trivial (`python3-speechd`, D-Bus) | Native | AT-SPI a11y tree for free (stack confirmed stable through 2026) | **Pick** |
| Qt6/QML | Fast | Excellent (Qt Quick is the best animation story here) | Easy via D-Bus | Native (qtwayland) | `qmltestrunner`, but weak on external drivers | Strong runner-up |
| WebKitGTK web shell | Medium | Excellent (CSS/WebGL) | Via a GTK host process | Native (GTK4 host) | **Playwright/CDP — the best testing story** | Runner-up |
| Electron/Chromium kiosk | Slow | Excellent | Awkward (needs a bridge) | `--ozone-platform=wayland` | Playwright | Rejected: ~200 MB in an immutable image, update churn |
| Tauri v2 | Fast | Excellent | Rust ↔ D-Bus | WebKitGTK under the hood | Playwright-ish | Interesting, but you inherit WebKitGTK anyway |
| Flutter | Fast | Excellent | FFI/method channel | **XWayland (GTK3)** | Flutter driver | Rejected on Wayland grounds |
| Godot 4.7 | Medium | Best-in-class | `OS.execute` → `spd-say` | Native since 4.3; **4.5 added Wayland sub-windows** | GUT/gdUnit4; **4.5 added AccessKit screen-reader support** | Tempting; rejected on integration cost |

The Godot option deserves a note because it is genuinely attractive for a pre-reader UI:
4.5's release notes say sub-window support means *"Godot can now spawn new independent
windows when running on Wayland natively"*, and it gained AccessKit-based screen reader
support (explicitly *experimental*, editor support limited). `--display-driver` and
`--headless` exist for CI. But a Godot shell is a foreign body in a GNOME/Flatpak system:
no portals, no GTK theming, no AT-SPI-native widgets, and every D-Bus interaction is
hand-rolled. For a **launcher** — as opposed to an activity — the integration tax is not
worth the animation win.

The web shell deserves an equally serious note in the other direction: **Playwright is
the single best automated-UI-testing tool in this entire document**, and CSS animation is
effortless. The cost is WebKitGTK's GPU/perf variability on low-end hardware and a fuzzy
boundary between "shell" and "app".

---

### 2.7 Testing

#### Booting the image

Two tiers:

1. **Fast, unprivileged, per-commit:** `bcvk ephemeral run-ssh` against the freshly built
   container. No disk image build, no root. This is the loop you want developers using.
2. **Full fidelity, nightly:** `bootc-image-builder` → qcow2 → QEMU/KVM, exercising the
   real bootloader, composefs root, first-boot units and greenboot.

QEMU invocation for tier 2 (Fedora host: `dnf install edk2-ovmf qemu-system-x86-core`):

```bash
qemu-system-x86_64 \
  -machine q35,accel=kvm -cpu host -smp 4 -m 4096 \
  -drive if=pflash,format=raw,readonly=on,file=/usr/share/edk2/ovmf/OVMF_CODE.fd \
  -drive if=pflash,format=raw,file=./OVMF_VARS.fd \
  -drive file=output/qcow2/disk.qcow2,if=virtio,format=qcow2 \
  -netdev user,id=n0,hostfwd=tcp::2222-:22 -device virtio-net-pci,netdev=n0 \
  -device virtio-vga-gl -display none \
  -serial file:serial.log \
  -qmp unix:./qmp.sock,server,nowait
```

#### Screenshots without a compositor-specific tool

**QMP `screendump` is the compositor-agnostic answer.** Verified from the QMP reference:
arguments are `filename`, optional `device`, `head`, and `format` (`png`|`ppm`); the
`format` argument landed in **QEMU 6.1**. So:

```json
{ "execute": "screendump",
  "arguments": { "filename": "/tmp/shot.png", "format": "png" } }
```

This works identically for gnome-kiosk/mutter and for cage — unlike `grim`, which is
wlroots-only and therefore **will not work under mutter**. `send-key` and `query-status`
round out the QMP surface. Drive it from Python with the `qemu.qmp` package
(**version/maintenance UNVERIFIED**).

Pair screenshots with perceptual diffing against golden images (the openQA "needle"
model) for the visual regression suite.

#### Readiness and health assertions over SSH

```bash
ssh -p 2222 parent@localhost 'systemctl is-system-running --wait'   # -> running|degraded
ssh -p 2222 parent@localhost 'systemctl --failed --no-legend'       # must be empty
ssh -p 2222 parent@localhost 'systemd-analyze time; systemd-analyze blame | head -20'
ssh -p 2222 parent@localhost 'bootc status --json'
ssh -p 2222 parent@localhost 'loginctl show-session $(loginctl list-sessions --no-legend | awk "\$3==\"kid\"{print \$1}") -p Type -p Active'
```

**Do not build on `pytest-testinfra`**: its README states *"This project is currently
**not actively maintained**, and responses to issues or pull requests may be delayed for
**several months**."* Use plain `pytest` + `subprocess`/`paramiko` with a small
`Host.run()` helper — it is ~50 lines and you own it.

`tmt` (Test Management Tool) is the Fedora-native alternative: L1 tests / L2 plans / L3
stories in `fmf`, provision plugins for `virtual` (QEMU via testcloud), `container`,
`connect`, `local`, and it plugs into Testing Farm and Packit. Worth adopting **if** you
want your tests to also run in Fedora CI; overkill otherwise.

#### Driving the UI

- **AT-SPI + `dogtail`** (`gitlab.com/dogtail/dogtail`, 1211 commits; current maintenance
  **UNVERIFIED**) — semantic and robust. AT-SPI itself is safe to bet on for now:
  `at-spi2-core 2.60.0` is in F44, Orca is actively released (50.2 / 51.beta), and **no
  Wayland-native accessibility protocol exists in `wayland-protocols` staging as of
  Aug 2026** — so the D-Bus AT-SPI stack is not about to be replaced. The open question is
  whether the a11y bus starts in a *kiosk* session with no gnome-shell.
- **`ydotool`** — uinput-based, works under *any* compositor including Wayland/GNOME
  (*"ydotool is not limited to Wayland… X11, text console, fbdev apps, etc."*). Needs
  `ydotoold` running and `/dev/uinput` access. Commands: `click`, `mousemove`, `type`,
  `key`, `stdin`. This is the pragmatic input driver for VM tests.
- **`libei`/portal RemoteDesktop** — the "correct" modern route, but I could not fetch
  the upstream project (Anubis). **UNVERIFIED**.
- **`wlrctl`, `grim`, `slurp`** — wlroots-only. Usable with cage, useless with mutter.

**Recommended combo under gnome-kiosk:** `ydotool` for input + QMP `screendump` for
output + SSH assertions for state. Compositor-agnostic, no a11y dependency, works
identically in CI and on a dev laptop.

#### GitHub Actions

- Standard `ubuntu-latest`: **public repos 4 vCPU / 16 GB RAM / 14 GB SSD**; private
  repos 2 / 8 / 14. The 14 GB disk is the binding constraint — a Fedora desktop bootc
  image plus Flatpaks will blow it.
- Mitigation: `jlumbroso/free-disk-space@main` frees **~31 GB** in ~3 min (Android 14 GB,
  tool cache 5.9 GB, large packages 5.3 GB, swap 4 GB, .NET 2.7 GB). Universal Blue uses
  its own `ublue-os/remove-unwanted-software` for the same job.
- **KVM:** GitHub's docs state *"GitHub-hosted Linux runners support hardware acceleration
  for Android SDK tools"* — which implies `/dev/kvm` is present on Linux runners — but the
  runner-specs page **does not** mention KVM or nested virtualisation for standard
  runners, and the 2023 changelog announcing it scoped it to *"larger Linux runners"*.
  **Status on standard `ubuntu-latest` in 2026 is UNVERIFIED and must be spiked** with a
  one-line `ls -l /dev/kvm` job. The standard workaround if the device exists but is
  unreadable:
  ```yaml
  - run: |
      echo 'KERNEL=="kvm", GROUP="kvm", MODE="0666", OPTIONS+="static_node=kvm"' \
        | sudo tee /etc/udev/rules.d/99-kvm4all.rules
      sudo udevadm control --reload-rules && sudo udevadm trigger --name-match=kvm
  ```
  ARM64 nested virt is explicitly unsupported. **Plan B: TCG** (`accel=tcg`) — 10–30×
  slower but adequate for a "does it reach `graphical.target`" smoke test.
- **Caching:** push intermediate/base layers to GHCR and rely on registry pulls rather
  than the Actions cache (10 GB/repo is too small for OS images). ublue's daily rebuild +
  rechunk pattern is the proven shape.

---

### 2.8 Update / rollback UX

- **`bootc upgrade`** — downloads and *stages* an update using an A/B deployment model.
  Flags confirmed: `--check` (detect without full download), `--apply` (reboot after
  staging), `--download-only`, `--from-downloaded`, `--soft-reboot=auto|required`.
- **`bootc switch <ref>`** — retarget the image (blue/green). `--transport` ∈
  `registry|oci|oci-archive|docker-daemon|containers-storage`.
- **`bootc rollback`** — reorders bootloader entries to the previous deployment.
- **`bootc status [--json]`** — machine-readable current/staged/rollback state.
- **Automatic updates:** `bootc-fetch-apply-updates.timer` + `.service` (daily check +
  reboot if updates found). **For kidnix this must be disabled by default** and driven
  from the parent panel — an unattended reboot mid-activity is a terrible child UX.
  `systemctl mask bootc-fetch-apply-updates.timer`.
- **`--soft-reboot`** is genuinely interesting for kidnix: a userspace-only restart is
  far less jarring than a full boot. **Applicability to a graphical session is
  UNVERIFIED** — spike it.

**greenboot.** Use **`greenboot-rs`**, not the deprecated shell version. Health checks:

```
/etc/greenboot/check/required.d/*.sh   # failure => boot marked red => rollback
/etc/greenboot/check/wanted.d/*.sh     # failure logged only
/etc/greenboot/green.d/*.sh            # ran after a good boot
/etc/greenboot/red.d/*.sh              # ran after a bad boot
```
`greenboot-healthcheck.service` runs before `boot-complete.target`. Config in
`/etc/greenboot/greenboot.conf` (`GREENBOOT_MAX_BOOT_ATTEMPTS`,
`GREENBOOT_WATCHDOG_GRACE_PERIOD` / `GREENBOOT_WATCHDOG_CHECK_ENABLED`). Rollback is
driven by GRUB2's `boot_counter` reaching -1. The **shell** greenboot then ran
`rpm-ostree rollback`; whether greenboot-rs calls `bootc rollback` is **UNVERIFIED**
(the README describes GRUB env tracking but not the rollback call) — **spike this, it is
the linchpin of unattended safety.**

kidnix's required health checks should be, at minimum:
1. `systemctl --failed` is empty (or on a known-benign allowlist);
2. GDM reached `graphical.target`;
3. the child session's shell unit is `active`;
4. the nftables egress table is loaded and the child chain has a `reject` rule.

That last one is important: a boot where the network lockdown silently failed should be
treated as a *failed boot* and rolled back.

**Fast "try a new version":**
```bash
sudo bootc switch --apply ghcr.io/you/kidnix:testing   # try
sudo bootc rollback && sudo systemctl reboot           # undo
sudo ostree admin pin 0                                # pin a known-good deployment
```
Plus `bootc usroverlay` for a transient writable `/usr` when debugging on-device
(command name **UNVERIFIED** for bootc 1.16 — `rpm-ostree usroverlay` is the ancestor).

---

## 3. Recommended architecture for kidnix v0.1

| Layer | Pick | Why | Runner-up |
|---|---|---|---|
| **Base image** | `quay.io/fedora/fedora-bootc:44`, digest-pinned | Fedora-official, no third-party lifecycle risk, minimal surface (we're building an appliance, not a desktop). ublue `main` carries an explicit trimming-support notice. | `ghcr.io/ublue-os/silverblue-main` if hardware enablement/codecs bite |
| **Build tooling** | ublue `image-template` *conventions* (scratch ctx stage, `build_files/`, `system_files/`, `RUN bootc container lint`, `just`), own repo | Proven idioms, no dependency on their base | BlueBuild (declarative YAML) |
| **Disk images** | `bootc-image-builder` via `osbuild/bootc-image-builder-action` for qcow2 + anaconda-iso | Only supported path to installable media | `bcvk to-disk` |
| **Dev/test VM** | **`bcvk`** | Replaces archived podman-bootc; unprivileged ephemeral VMs = fast loop | raw qemu + local registry |
| **Kiosk compositor** | **gnome-kiosk 50** (`gnome-kiosk` + `gnome-kiosk-script-session` as reference) | Mutter-based: real Wayland/XWayland/portal/a11y/input support, Red-Hat-maintained, `X-GDM-CanRunHeadless=true` helps CI, Flatpak apps behave. Custom `.session` gives us exactly one shell + fullscreen apps. | `cage` (simpler and gives wlroots test tooling, but single-app and no portal story) |
| **Session split** | GDM `AutomaticLogin=kid` + AccountsService `Session=kidnix-shell` for `kid`; `parent` gets stock GNOME | Standard, no custom DM | greetd (loses GNOME integration) |
| **Shell tech** | **GTK4 + libadwaita, Python/PyGObject** | Native Wayland, native portals, `python3-speechd` for TTS in three lines, AT-SPI tree for free, fastest iteration, smallest image delta, and it *is* the platform we're already shipping. Adw animations are good enough for tiles/transitions. | WebKitGTK web shell (much better test story via Playwright, much better animation; revisit if the pre-reader UI demands motion GTK can't do) |
| **Activities** | Flatpak, sideloaded offline from a repo baked into `/usr`, installed by a first-boot unit; `--unshare=network` globally | Only reliable way to get Flatpaks onto an image with bootc `/var` semantics | Read-only extra installation under `/usr` (needs a spike) |
| **Network policy** | nftables `meta skuid "kid" reject` in the `output` hook, image-owned, plus global `flatpak override --unshare=network`, plus `auth-polkit=root-only` | firewalld cannot match UID; defence in depth | — |
| **Parental policy store** | malcontent 0.14 (record) + kidnix's own enforcement (enforce) | malcontent is advisory by design | custom only |
| **Time limits** | shell-owned `kidnix-timekeeper` user service with warnings + `loginctl terminate-user`, backstopped by `RuntimeMaxSec=` | pam_time can't end a live session | pam_time alone (insufficient) |
| **TTS** | `speech-dispatcher` 0.12.1 + **espeak-ng as the shipped default**; Piper **`en_GB-cori-high`** (public domain) via `sd_generic` → a resident Piper HTTP server, as the quality upgrade | espeak-ng works today and is packaged; Piper has no F44 RPM, no released speech-dispatcher module, and a thin upstream. cori is the only en_GB voice with a clean licence *and* a "high" tier | Piper-only (too risky for v0.1); Kokoro (better quality, no integration path) |
| **Audio safety** | ALSA master cap at boot + `api.alsa.soft-mixer=true`, plus a `linear`(0.6)→`clamp` filter-chain sink as the child's fixed default | PipeWire has **no** declarative max-volume and **no builtin limiter**; a device-level cap is the only unbypassable one | `wpctl set-volume -l` routed through the shell (works only if the shell owns all volume keys) |
| **Testing** | pytest (hand-rolled SSH helper) + QMP `screendump` + `ydotool` input, run against `bcvk` on every PR and against a full qcow2 nightly | Compositor-agnostic, no dependence on the in-flux a11y stack, no dependence on unmaintained testinfra | tmt/Testing Farm if we want Fedora CI |
| **Safety net** | **greenboot-rs** with four required health checks incl. "egress lockdown loaded" | Automatic rollback of a bad update on a device a child uses unsupervised | manual `bootc rollback` |
| **Updates** | auto-update timer **masked**; parent panel triggers `bootc upgrade --check` then `--apply` | No surprise reboots mid-activity | default daily timer |

---

## 4. Risks & unknowns needing a spike

1. **bootc-image-builder's post-archive home.** The repo merged into
   `osbuild/image-builder` in June 2026; the canonical container ref going forward is
   unclear. *Spike: 1h — find the current ref, pin it.*
2. **Piper ↔ speech-dispatcher.** No F44 RPM, no released module (the native
   `cxxpiper` module is master-only), and the CLI reloads the model per call. The
   `sd_generic` + resident-HTTP-server shape above is unverified end-to-end.
   *Spike: 1 day. Ship espeak-ng regardless.*
3. **Flatpaks in an immutable image.** Read-only `/usr` installation vs sideload-repo +
   first-boot install. Both plausible, neither verified. *Spike: 1–2 days. This is the
   highest-risk unknown in the whole build.*
4. **greenboot-rs → bootc rollback.** If greenboot-rs doesn't actually invoke
   `bootc rollback`, the unattended-safety story collapses. *Spike: 0.5 day.*
5. **KVM on GitHub-hosted standard runners.** Docs are contradictory. *Spike: 20 min
   (`ls -l /dev/kvm` job). Plan B is TCG.*
6. **AT-SPI inside a gnome-kiosk session.** AT-SPI itself is fine on Wayland in GNOME 50
   (`at-spi2-core 2.60.0`, Orca 50.x alive) and the Wayland-native replacement has *not*
   landed — so dogtail is viable in principle. What's unverified is whether the a11y bus
   is actually started in a *kiosk* session (no gnome-shell). *Spike: 0.5 day.*
   (Mitigated: the recommended test stack doesn't depend on it.)
7. **VT switching.** `NAutoVTs=0`/`ReserveVT=0` removes the destination but not the
   keystroke handling. *Spike: 0.5 day on real hardware — a 6-year-old mashing Ctrl+Alt+F3
   must not produce a black screen.*
8. **GCompris offline voice packs.** Mechanism is now understood (pre-seed `.rcc` +
   `Contents` into `data3/`), but the exact on-disk layout the app accepts is unverified.
   *Spike: 1 day. Without this, the anchor app is mute.*
9. **`bootc --soft-reboot` with a graphical session.** Would materially improve update UX.
   *Spike: 0.5 day.*
10. **gnome-kiosk `window-config.ini` schema** — read `/usr/share/doc/gnome-kiosk/CONFIG.md`
    on a live F44 system; controls whether Flatpak activities auto-fullscreen correctly.
11. **`/var` first-boot ordering.** AccountsService session overrides, Flatpak installs,
    and kidnix state all live in `/var` and are image-initialised only once. Get the
    first-boot unit ordering right or upgrades will silently stop applying policy.
12. **Disk budget.** Installed sizes: SuperTuxKart 791 MB + Stellarium 671 MB + TurboWarp
    382 MB + SuperTux 357 MB + Marble 323 MB + Kiwix 173 MB + Tux Paint 150 MB +
    GCompris 91 MB (+voices) + ZIMs ~458 MB. That is ~3.4 GB of activities on top of the
    OS, and it will not fit alongside a build on a 14 GB CI runner. Plan tiered images
    (`kidnix-core` ≈ 4–6, `kidnix-full` ≈ 6–8) from day one.
13. **Kiwix's Flathub build is 20 months stale on an EOL KDE runtime** while upstream is
    alive. Either wait for a rebuild, build our own Flatpak, or use `kiwix-serve` +
    a WebKitGTK view instead of `kiwix-desktop`. *Spike: 0.5 day.*

---

## 5. Top 10 takeaways

1. **Fedora 44 = GNOME 50** (`mutter 50.4-1.fc44`), `bootc 1.16.7-1.fc44`,
   `gnome-kiosk 50.1-1.fc44`, `malcontent 0.14.0-1.fc44`, `speech-dispatcher 0.12.1-6.fc44`.
2. **Three tools you'd have reached for are dead or moved in 2026:**
   `bootc-image-builder` (archived → `osbuild/image-builder`), `podman-bootc` (archived →
   **`bcvk`**), shell `greenboot` (→ **`greenboot-rs`**). Also `pytest-testinfra` is
   explicitly unmaintained.
3. **gnome-kiosk is the right compositor**, and it is a *real* packaged product with
   a11y, notification-daemon and script-session subpackages — not a research project.
   Three files (`wayland-sessions/*.desktop`, `gnome-session/sessions/*.session`, your
   app's `.desktop`) is the whole integration.
4. **bootc's `/var` semantics are the design constraint that bites hardest.** Anything in
   `/var` is initialised from the image *once*. Flatpaks, AccountsService session
   overrides and kidnix state all live there. Plan first-boot units, not image content.
5. **firewalld cannot filter by UID.** Use nftables `meta skuid` in the `output` hook —
   and layer `flatpak override --unshare=network` on top, because setuid binaries defeat
   `skuid`.
6. **malcontent is advisory, not a security boundary** — its own README says so. Record
   policy there; enforce structurally.
7. **`pam_time` cannot end a running session.** Time limits need a session-owned daemon
   plus `RuntimeMaxSec=` as a fail-safe plus `loginctl terminate-user`.
8. **QMP `screendump` (PNG since QEMU 6.1) + `ydotool` is the compositor-agnostic test
   harness.** `grim`/`wlrctl` are wlroots-only and will not work under mutter.
9. **Piper is packaged nowhere useful.** `rhasspy/piper` archived Oct 2025 →
   `OHF-Voice/piper1-gpl` (GPL-3.0, `piper-tts` 1.7.0, "looking for maintainers");
   `python3-piper-tts` is **F45+ only**; the native `cxxpiper` speech-dispatcher module is
   **master-only, not in 0.12.1**. Ship `speech-dispatcher-espeak-ng` as the guaranteed
   path and add Piper **`en_GB-cori-high`** (the only public-domain, high-quality en_GB
   voice) behind a flag, served by a resident HTTP process.
10. **App IDs and ratings will trip you up.** Real IDs are `com.tux4kids.tuxtype` /
    `com.tux4kids.tuxmath` (not `net.sourceforge.*`), `org.luanti.luanti` (not
    `net.minetest.Minetest`). `edu.mit.Scratch` is **abandoned on an EOL runtime** —
    **`org.turbowarp.TurboWarp` is the offline Scratch**, and ScratchJr has **no Linux
    build at all**. Luanti/Stellarium/SuperTuxKart are OARS **13+**; GCompris, Tux Paint,
    SuperTux, KTuberling, Blinken, Nibbles are **3+**. KDE Gear apps were rebuilt *two
    days* before this research and are the most reliably maintained kids' apps on Flathub.

---

## 6. Sources

**bootc & image building**
- https://bootc.dev/bootc/ (redirected from bootc-dev.github.io/bootc)
- https://bootc.dev/bootc/filesystem.html
- https://bootc.dev/bootc/print.html (full book — upgrade/switch/rollback/install/transports)
- https://github.com/bootc-dev/bcvk
- https://github.com/containers/podman-bootc (archived 2026-06-03)
- https://github.com/osbuild/bootc-image-builder (archived 2026-06-18)
- https://raw.githubusercontent.com/osbuild/bootc-image-builder/main/README.md
- https://github.com/osbuild/image-builder
- https://github.com/osbuild/bootc-image-builder-action
- https://pykickstart.readthedocs.io/en/latest/kickstart-docs.html (`ostreecontainer`)
- https://gitlab.com/fedora/bootc/base-images

**Universal Blue**
- https://github.com/ublue-os/image-template
- https://raw.githubusercontent.com/ublue-os/image-template/main/Containerfile
- https://raw.githubusercontent.com/ublue-os/image-template/main/Justfile
- https://raw.githubusercontent.com/ublue-os/image-template/main/build_files/build.sh
- https://raw.githubusercontent.com/ublue-os/image-template/main/README.md
- https://raw.githubusercontent.com/ublue-os/image-template/main/.github/workflows/build.yml
- https://raw.githubusercontent.com/ublue-os/image-template/main/.github/workflows/build-disk.yml
- https://github.com/ublue-os/main
- https://github.com/ublue-os/bluefin
- https://github.com/hhd-dev/rechunk

**Kiosk / session / GNOME**
- https://gitlab.gnome.org/GNOME/gnome-kiosk
- https://gitlab.gnome.org/GNOME/gnome-kiosk/-/raw/main/README.md
- https://github.com/GNOME/gnome-kiosk (mirror; `kiosk-script/` tree)
- https://raw.githubusercontent.com/GNOME/gnome-kiosk/main/kiosk-script/gnome-kiosk-script
- https://raw.githubusercontent.com/GNOME/gnome-kiosk/main/kiosk-script/wayland-sessions/gnome-kiosk-script-wayland.desktop.in
- https://packages.fedoraproject.org/pkgs/gnome-kiosk/gnome-kiosk/ (+ `/fedora-44.html`)
- https://packages.fedoraproject.org/pkgs/gnome-kiosk/gnome-kiosk-script-session/ (+ `/fedora-44.html`)
- https://packages.fedoraproject.org/pkgs/gnome-kiosk/gnome-kiosk-a11y/
- https://packages.fedoraproject.org/pkgs/mutter/mutter/
- https://packages.fedoraproject.org/pkgs/cage/cage/
- https://packages.fedoraproject.org/pkgs/labwc/labwc/
- https://help.gnome.org/admin/system-admin-guide/stable/login-automatic.html.en
- https://help.gnome.org/admin/system-admin-guide/stable/lockdown-command-line.html.en
- https://man.archlinux.org/man/logind.conf.5
- https://man.archlinux.org/man/portals.conf.5

**Parental controls / lockdown**
- https://github.com/endlessm/malcontent (mirror of gitlab.freedesktop.org/pwithnall/malcontent)
- https://packages.fedoraproject.org/pkgs/malcontent/malcontent/
- https://man.archlinux.org/man/polkit.8
- https://man.archlinux.org/man/pam_time.8
- https://man.archlinux.org/man/systemd.service.5
- https://man.archlinux.org/man/systemd.resource-control.5
- https://man.archlinux.org/man/NetworkManager.conf.5
- https://man.archlinux.org/man/firewalld.richlanguage.5
- https://wiki.nftables.org/wiki-nftables/index.php/Matching_packet_metainformation
- https://man.archlinux.org/man/flatpak-override.1
- https://man.archlinux.org/man/flatpak-installation.5
- https://docs.flatpak.org/en/latest/sandbox-permissions.html
- https://docs.flatpak.org/en/latest/usb-drives.html

**Audio / TTS / a11y**
- https://packages.fedoraproject.org/pkgs/speech-dispatcher/speech-dispatcher/
- https://packages.fedoraproject.org/pkgs/python-piper-tts/python3-piper-tts/
- https://mdapi.fedoraproject.org/f44/pkg/{speech-dispatcher,python3-speechd,espeak-ng,festival,orca,at-spi2-core,pipewire,wireplumber,ladspa-swh-plugins,lsp-plugins-ladspa,flatpak}
- https://github.com/brailcom/speechd (releases; `src/modules/cxxpiper.cpp`; `config/modules/cxxpiper.conf`)
- https://github.com/OHF-Voice/piper1-gpl (+ `docs/CLI.md`, `docs/VOICES.md`)
- https://pypi.org/project/piper-tts/
- https://huggingface.co/rhasspy/piper-voices (`voices.json`, per-voice `MODEL_CARD`)
- https://github.com/dioco-group/jenny-tts-dataset
- https://docs.pipewire.org/page_module_filter_chain.html
- https://pipewire.pages.freedesktop.org/wireplumber/daemon/configuration.html
- https://github.com/PipeWire/wireplumber (`src/tools/wpctl.c`; `src/config/wireplumber.conf.d.examples/`)
- https://gitlab.gnome.org/GNOME/orca (tags)
- https://accesskit.dev/blog/ ; https://github.com/AccessKit/accesskit
- https://gitlab.freedesktop.org/wayland/wayland-protocols (staging tree listing — no a11y protocol)
- https://github.com/RHVoice/RHVoice ; https://github.com/MycroftAI/mimic3 ; https://github.com/espeak-ng/espeak-ng
- https://huggingface.co/hexgrad/Kokoro-82M ; https://huggingface.co/onnx-community/Kokoro-82M-v1.0-ONNX

**Apps**
- https://flathub.org/api/v2/appstream/`<id>` and /api/v2/summary/`<id>` for every ID in the table
- https://flathub.org/apps/org.kde.gcompris
- https://flathub.org/apps/org.tuxpaint.Tuxpaint
- https://flathub.org/apps/org.kiwix.desktop
- https://flathub.org/apps/org.luanti.luanti
- https://flathub.org/apps/org.supertuxproject.SuperTux
- https://flathub.org/apps/net.supertuxkart.SuperTuxKart
- https://flathub.org/apps/org.stellarium.Stellarium
- https://flathub.org/apps/org.kde.ktuberling
- https://flathub.org/apps/org.kde.blinken
- https://flathub.org/apps/org.gnome.Nibbles
- https://invent.kde.org/education/gcompris (`src/core/DownloadManager.cpp`, `src/core/ApplicationSettings.cpp`)
- https://library.kiwix.org/catalog/v2/entries (OPDS — ZIM sizes)
- https://github.com/kiwix/kiwix-desktop ; https://github.com/TurboWarp/desktop
- https://github.com/jfo8000/ScratchJr-Desktop (dead, last commit 2020-11-21)
- https://github.com/sugarlabs/sugar

**Shell tech**
- https://github.com/gtk-rs/gtk4-rs/releases
- https://webkitgtk.org/
- https://godotengine.org/download/linux/
- https://godotengine.org/releases/4.5/
- https://docs.godotengine.org/en/stable/tutorials/editor/command_line_tutorial.html
- https://docs.flutter.dev/platform-integration/linux/building

**Testing / CI / rollback**
- https://www.qemu.org/docs/master/interop/qemu-qmp-ref.html
- https://github.com/pytest-dev/pytest-testinfra
- https://tmt.readthedocs.io/en/stable/overview.html
- https://github.com/ReimuNotMoe/ydotool
- https://gitlab.com/dogtail/dogtail
- https://docs.github.com/en/actions/reference/runners/github-hosted-runners
- https://github.blog/changelog/2023-02-23-hardware-accelerated-android-virtualization-on-actions-windows-and-linux-larger-hosted-runners/
- https://github.com/actions/runner-images/issues/183
- https://github.com/jlumbroso/free-disk-space
- https://github.com/fedora-iot/greenboot
- https://github.com/fedora-iot/greenboot-rs

**Unreachable during research** (Anubis anti-bot; routed around via mirrors):
`gitlab.freedesktop.org/pwithnall/malcontent`, `gitlab.freedesktop.org/libinput/libei`,
`docs.fedoraproject.org/en-US/bootc/`, `wiki.archlinux.org`.

---

**Erratum (2026-08-22, TTS spike):** §2.4 says onnxruntime is not packaged
for Fedora 44 — it is (`python3-onnxruntime` 1.22.2), but pulling it costs
256 MiB–1 GiB of dependencies. kidnix vendors the archived MIT `rhasspy/piper`
2023.11.14-2 binary (22 MiB, relinked against Fedora's espeak-ng) with
`en_GB-cori-{high,medium}` (public domain); see `docs/spikes/tts.md`.

**Erratum 2 (2026-08-23, rollback spike):** §4 item 4 doubted that greenboot-rs
calls `bootc rollback`; it does (0.16.3). What actually broke automatic rollback
in kidnix was GRUB being unable to write `grubenv` on a btrfs `/boot`, so
`boot_counter` never decremented — fixed by an image-owned `red.d` script that
decrements it from Linux; see `docs/spikes/rollback.md` and `just test-rollback`.
