# Spike: the hardening pass

**Status:** implemented, green. `build_files/70-hardening.sh` runs on every
build; `tests/image/test_hardening.sh` is 93 assertions; `just test-boot`
against the hardened image is 25/25; `bootc container lint` is 13/13 with no
warnings.

This closes the three follow-ups ADR-0005 accepted as decisions ("remove
Firefox", "remove or mask `gnome-remote-desktop` and `rygel`", "replace
`gnome-backgrounds` with one kidnix wallpaper") and open questions 1, 2 and 5
of `docs/spikes/parent-desktop.md`.

**Everything below was measured against the real image**
(`podman run --rm localhost/kidnix:hardening …`), not against memory. Where a
decision went the other way from the brief, the evidence that changed it is
quoted.

---

## 1. The headline numbers

| | before (`:shell`) | after (`:hardening`) | delta |
|---|---|---|---|
| packages | 1633 | 1615 | **−18** |
| installed size (`rpm -qa --qf %{SIZE}`) | 6093 MiB | 5705 MiB | **−388 MiB** |
| `/usr` on the deployed root (`du -sxm`) | 6886 MiB | 6496 MiB | **−390 MiB** |
| container image (sum of layers) | 8110627113 B | 8048170793 B | −62 MB |
| enabled system units | 92 | 80 | −12 |
| masked system units | 1 | 13 | +12 |

**The last two rows of that table disagree on purpose, and it is worth being
precise about why.** A bootc *machine* gets 390 MiB smaller: that is real disk
on a refurbished laptop, and it is the number that matters for what a parent
has to trust. The *pullable image* barely moves, because OCI layers are
additive — deleting Firefox in our layer writes whiteouts over files that are
still sitting in `ghcr.io/ublue-os/base-main`'s layer, so they are still
downloaded on a fresh pull. The 62 MB it did save is almost entirely
`gnome-backgrounds`, which we stopped *installing* rather than removed.

If image transfer size ever becomes the constraint, the fix is upstream
(`base-main` not shipping Firefox, or kidnix flattening to a single layer), not
here. Recorded so nobody re-measures this and concludes the removal did
nothing.

---

## 2. What was removed, and why

`build_files/70-hardening.sh` runs **after every install stage** (`00`, `35`,
`36`, `50`, `60`) so it can see what weak dependencies actually dragged in, and
before `90-cleanup.sh`.

| Package | Size | Why it is gone |
|---|---|---|
| `firefox` + `firefox-langpacks` | 328 MiB | The big one. `base-main` ships it; kidnix never asked for it. ADR-0005 is explicit that **"no web browser" is a property of the machine, not of the child's session** — the parent has other devices, and a browser in the image is the residual hole if a child ever reaches the parent's desktop. It is also, by a wide margin, the largest attack surface in desktop software. |
| `gnome-remote-desktop` | 2.1 MiB (+3.8 MiB `freerdp-libs`, 1.1 MiB `libvncserver`, 1.3 MiB `libwinpr`) | An RDP **and** VNC server. Arrived as a `Recommends` of `gnome-shell`. On a machine whose entire premise is that the child cannot reach the network, a service that lets the network reach the machine is the exact inverse of the design. |
| `rygel` | 4.7 MiB (+`gupnp-av`, `gupnp-dlna`, `gst-editing-services`, `libgee`, `libmediaart`) | A UPnP/DLNA media server: it announces itself on the LAN and serves files out of the machine. Same provenance, same objection, and kidnix has no media library to share. |
| `cups-browsed` | 400 KiB | **Not CUPS.** `cups-browsed` is the separate daemon that listens on the network for printer announcements and creates queues from them — the component behind the 2024 CUPS remote-code-execution family (CVE-2024-47076 / 47175 / 47176 / 47177). Printing keeps working without it. What stops working is printers appearing by magic, which a parent does once, by hand, in Settings. |
| `gnome-tour` | 2.3 MiB | A slideshow that autostarts on first login to explain GNOME. The parent gets a stock desktop, not a guided tour; the child must never see it at all. |
| `gnome-color-manager` | 3.1 MiB | Display-calibration tooling for photographers. Nothing here calibrates a display. |
| `gnome-backgrounds` | 37.8 MiB | 60% of the entire parent-desktop stage (`docs/spikes/parent-desktop.md` §1). Now **never installed**: `35-parent-desktop.sh` dropped it and §4 below replaces it. |

Plus the transitive `Removing unused dependencies` set dnf chose:
`sso-mib-libs`, `uriparser` — 17 packages in one transaction, 350 MiB freed.

### 2.1 Three things `rpm` left behind, that nothing would have caught

Removal is not the same as absence, and each of these was found by looking
rather than by assuming:

1. **`/usr/share/applications/mimeapps.list` still named Firefox** as the
   handler for `x-scheme-handler/http`, `https`, `text/html` and
   `application/xhtml+xml`. With Firefox gone those are dangling: an activity
   calling `xdg-open("https://…")` gets a broken handler rather than nothing,
   and GNOME's Default Applications panel offers a browser that is not there.
   The stage deletes the four lines. **Consequence to know about:** `rpm -V`
   now reports `mimeapps.list` as modified. That is the honest trade — the
   alternative, an `/etc/xdg/mimeapps.list` override, can only *redirect* a
   default, and there is nothing to redirect it to.
2. **`/usr/lib64/firefox` survived as an empty directory tree**, along with
   `/etc/cups/cups-browsed.conf.rpmsave` (rpm renames `%config` files rather
   than deleting them). Both are removed.
3. **The `gnome-remote-desktop` service account stayed in `/etc/passwd`,
   `/etc/group`, `/etc/shadow` and `/etc/gshadow`.** rpm's `%postun`
   deliberately does not `userdel` — a package might be reinstalled, and files
   on disk might still be owned by that uid. Neither applies here, and `bootc
   container lint` flags it (*"Found /etc/passwd entry without corresponding
   systemd sysusers.d"*). It matters more than it looks: `/etc` is 3-way
   merged, so a ghost account created once would follow the machine across
   every future upgrade forever. Reaping it took the lint from *"12 passed, 1
   warning"* back to **13 passed, 0 warnings**.

### 2.2 The assertion that actually matters

The dangerous failure mode of this stage is not "the removal did not happen".
It is **"the removal took GDM with it and the build passed anyway"** — see §3.1
for how close that is. So the stage asserts *both* directions: seven packages
must be gone, and `gdm gnome-shell gnome-session gnome-control-center
gnome-kiosk nautilus ptyxis malcontent cups` must all still be installed.

It also asserts the *property* rather than the package list, because the next
browser will not be called firefox:

- no `.desktop` in the image declares `Categories=…WebBrowser` or
  `MimeType=…x-scheme-handler/http(s)`;
- nothing under `/usr/share/applications/` mentions firefox or mozilla;
- `/usr/share/kidnix/flatpaks.txt` lists no browser (the one route by which a
  browser could still arrive on **first boot**, after every image test has
  already passed).

---

## 3. What was deliberately KEPT, and the evidence

This is the more useful half of the document. Four things the brief expected to
be removed are still here, three because removing them costs more than it buys
and one because it is not removable at all.

### 3.1 `gnome-online-accounts` — NOT REMOVABLE. The finding of this spike.

The brief said "remove/mask goa: no accounts". Measured:

```
# dnf5 --assumeno remove gnome-online-accounts
Removing dependent packages:
 gdm, gnome-shell, gnome-session-wayland-session
Removing unused dependencies:
 gnome-control-center, gnome-keyring, evolution-data-server,
 webkit2gtk4.1, webkitgtk6.0, gjs, mozjs140, … (92 packages, 475 MiB)
```

`gnome-control-center` hard-requires `gnome-online-accounts`, `gnome-shell`
hard-requires `gnome-control-center`, and `gdm` hard-requires `gnome-shell`.
Removing goa removes the display manager. **It stays.**

Residual risk, stated plainly because it is the most uncomfortable line in this
document: **`webkit2gtk4.1` and `webkitgtk6.0` (183 MiB of browser engine) are
still on the image**, pulled by `evolution-data-server`, pulled by
`gnome-online-accounts`. We removed the browser; we could not remove the
engine. Mitigations: no launcher, no `.desktop`, no mime association, and uid
1000 has no network egress at all (`docs/spikes/lockdown.md` §1.1). It is a
library, not an application — nothing on the image starts it. But "there is no
web engine on this machine" would be a false claim, so nobody should make it.

There is no supported way to hide the Online Accounts panel from
`gnome-control-center` either. A parent who wants to add a Google account to
their own desktop can; that is their machine and their decision, and ADR-0005's
"familiar" argues for not fighting it.

### 3.2 `avahi` — KEPT

mDNS/DNS-SD. It is a network-facing daemon, and the temptation to kill it is
real. Against that:

- `cups-filters-driverless` and `cups-ipptool` **require** it, and driverless
  (IPP Everywhere) printing — which is every printer sold in the last decade —
  finds printers over mDNS. With `cups-browsed` gone (§2), avahi is now the
  *only* way a parent finds their printer without typing an IP address.
- It is link-local by design: it does not route, so it does not leave the
  house.
- kidnix ships no service to advertise, so it is a resolver here, not a
  publisher.

Keeping printing is a product decision — "making over consuming"
(non-negotiable 3) means a drawing that can come out on paper. Revisit if
`avahi-daemon` ever needs to be reachable rather than just able to ask.

### 3.3 `cups` — KEPT

Printing is a feature, not an oversight. `cups.socket` is socket-activated and
listens on a **unix socket plus localhost:631** by default, not on the LAN.
`cups-browsed`, the part that listened to the network, is gone.

### 3.4 `sshd` — KEPT ENABLED, and trimmed

The brief's preferred answer was "installed but disabled by default". Measured
against reality, that breaks the project's most valuable test:

`just test-boot` reaches the VM with `bcvk ephemeral ssh`
(`tests/boot/bcvk_boot_test.py`, `VM.ssh()` → `bcvk ephemeral ssh <name> -- …`,
launched with `--ssh-keygen`). bcvk generates a key, injects it, and logs into
the guest's **sshd**. Disabling sshd in the image deletes the only fast,
rootless, no-sudo proof that the machine boots into the kiosk at all. That is a
worse trade than the surface it saves — and a parent whose graphical session is
broken keeps one way in that is not a rescue USB.

So it stays on, and `system_files/etc/ssh/sshd_config.d/10-kidnix.conf` shrinks
it instead. sshd takes the **first** value it sees for a keyword and
`/etc/ssh/sshd_config`'s `Include /etc/ssh/sshd_config.d/*.conf` is its first
line, so `10-` beats Fedora's `40-`/`50-` drop-ins (the test asserts that
ordering, because the file is decoration if it ever stops being true):

| Setting | Why |
|---|---|
| `DenyUsers kid` | The child's account must not be reachable from the network under any circumstances. `kid` has no password today — but that is a fact about the current build, not a policy. This is the policy. |
| `PasswordAuthentication no`, `KbdInteractiveAuthentication no`, `PermitEmptyPasswords no` | The parent's password exists for `sudo` and GDM, both of which need physical presence. A laptop that spends its life on other people's wifi should not also accept that password from the network. bcvk and the parent's own laptop both use keys. |
| `PermitRootLogin prohibit-password` | Already upstream's default; stated explicitly so a future default change cannot quietly loosen a child's machine. |
| `GSSAPIAuthentication no`, `X11Forwarding no`, `AllowTcpForwarding no`, `AllowAgentForwarding no`, `PermitTunnel no` | Code paths reachable before authentication, or pivots after it, for features a family computer does not have. There is no X on this image at all. |

The build runs `sshd -t` over the whole include tree (lending it a throwaway
host key, since an image has none) so a typo fails the build rather than
leaving a machine with no sshd on first boot. `just test-boot` passing 25/25
against the hardened image is the proof that none of this broke bcvk.

**Reversible in one line on a running machine:** `/etc` is writable and 3-way
merged, so `sudo $EDITOR /etc/ssh/sshd_config.d/10-kidnix.conf` sticks across
upgrades.

### 3.5 `bluetooth`/`bluez` — KEPT

kidnix targets refurbished laptops, and a Bluetooth mouse or keyboard is a very
ordinary thing for one to have. It is real surface (`bluetoothd` parses
attacker-controlled input from the air) and it is on the list of things to
revisit if `gnome-bluetooth` is ever shown to be unnecessary. Documented, not
masked.

### 3.6 Considered and left alone

`systemd-homed` (not network-facing; part of the stock boot path; masking buys
nothing measurable), `qemu-guest-agent` / `vboxservice` / `vgauthd` /
`vmtoolsd` (all `ConditionVirtualization`, and the first is useful to our own
VM tests), `smartd` / `mcelog` / `mdmonitor` / `raid-check.timer` (hardware
health, no network), `NetworkManager-wait-online` (does not gate
`graphical.target`; only `kidnix-flatpaks-firstboot` pulls
`network-online.target`), `nm-connection-editor` / `gnome-bluetooth` / `bolt`
(the three GNOME weak-dependency extras that remain after §2 — all local UI).

---

## 4. One wallpaper

`gnome-backgrounds` was 37.8 MiB and **60% of the entire parent-desktop
stage**. It is no longer installed at all (`35-parent-desktop.sh` lost it), and
kidnix ships one wallpaper instead:

| File | What |
|---|---|
| `system_files/usr/share/backgrounds/kidnix/default.png` | 2560×1440, **112 KiB**. A warm dawn gradient, one low sun with two haloes, two hills as circle segments. No text, no logo, no faces. Low contrast, because windows sit on top of it. |
| `system_files/usr/share/backgrounds/kidnix/default.svg` | The editable source, kept so the wallpaper can be changed without reverse-engineering a bitmap. |
| `system_files/usr/share/gnome-background-properties/kidnix.xml` | Puts it in Settings → Appearance, so a parent who changes it can get back to it. |
| `system_files/etc/dconf/db/local.d/10-kidnix-background` | Makes it the default. |

**340× smaller**, and the parent's Appearance panel is not empty:
`fedora-workstation-backgrounds` (5.1 MiB, 6 wallpapers) is deliberately still
installed, so choosing a different wallpaper still works. Dropping the 38 MiB
set while keeping a 5 MiB one is the whole trade — kidnix owns the *default*,
the parent keeps a *choice*.

The PNG was generated by a short PIL script (recorded in the SVG's header and
reproducible from it); the SVG is the design of record. One gotcha worth
writing down, because the first attempt shipped it: **blurring an RGBA layer
bleeds the transparent pixels' black into every soft edge**, which drew a grey
ring around the sun's outer halo. Soft edges have to be drawn as an 8-bit
*mask*, blurred, and then used to composite a flat colour.

### 4.1 Why the dconf default is needed, and who it reaches

GNOME's compiled-in `picture-uri` default is
`file:///usr/share/backgrounds/gnome/adwaita-l.jxl`, which `gnome-backgrounds`
owned. Without an override, a parent's first login is a grey rectangle that
reads as "broken" rather than "minimal" — which is exactly the argument that
put `gnome-backgrounds` in the image in the first place.

The override goes in `/etc/dconf/db/local.d/`, and it reaches precisely the
right people by accident of Fedora's stock profile:

```
$ cat /etc/dconf/profile/user
user-db:user
system-db:local      <- ours
system-db:site
system-db:distro
```

- **The parent gets it**, because their session uses the stock `user` profile.
- **The child does not**, because `kidnix-shell` exports `DCONF_PROFILE=kid`
  and `/etc/dconf/profile/kid` is `user-db:user` +
  `file-db:/usr/share/kidnix/dconf/kid.compiled` — it never reads
  `system-db:local`. The kid shell paints its own background anyway. The test
  asserts this non-leak in both directions.
- **Nothing is locked.** There is no matching entry under `locks/`. ADR-0005
  says the parent's desktop should be familiar, and changing your wallpaper is
  the most ordinary thing a person does to a computer.

This is a partial answer to open question 4 of `docs/spikes/parent-desktop.md`
("should the parent get a dconf profile at all?"): they get exactly one default
key group, no profile of their own, and no locks.

The build compiles the database with `dconf update` and then **reads the value
back out of the compiled binary** (a profile containing only a `file-db` needs
no D-Bus and no writable user database) rather than trusting that
`dconf update` did what the keyfile said.

---

## 5. The unit audit

`70-hardening.sh` prints the full enabled-unit list on **every** build, so a
new unit arriving in a base-image bump is visible in the log the day it lands
rather than the day it does something.

### 5.1 Masked, with reasons

13 units masked (12 new, plus `bootc-fetch-apply-updates.timer` from
`40-lockdown.sh`). `systemctl mask` — a symlink to `/dev/null` in `/etc` —
rather than removing packages, because most of these come from packages that
also provide something wanted, and because a mask is one `systemctl unmask`
away from being undone by a parent who disagrees.

Nothing is masked for being "unnecessary". The test is narrower: **does this
unit reach the network on its own schedule, change the machine on its own
schedule, or exist only to serve software kidnix deliberately does not ship?**

| Unit | Reason |
|---|---|
| `rpm-ostreed-automatic.timer` | Stages and applies an rpm-ostree update on a timer. kidnix updates are atomic and rollbackable *precisely so a family can choose their moment*; doing it automatically throws that property away. The parent panel will drive `bootc upgrade`. |
| `bootc-fetch-apply-updates.timer` | (already masked by `40-lockdown.sh`) The bootc equivalent, which also **reboots**. |
| `flatpak-system-update.timer` | Updates every installed Flatpak in the background. A child's activity changing shape mid-session, or a 400 MB TurboWarp download starting on a metered phone hotspot, must both be decisions. |
| `flatpak-user-update.timer` (`--global`) | The per-user counterpart. ublue's *user* preset enables it for every account **including the child's**, so without a `--global` mask a background Flatpak update runs inside the kid session. Easy to miss: it does not appear in `systemctl list-unit-files --state=enabled`. |
| `rpm-ostree-countme.timer` | DNF's "count me" telemetry: a weekly HTTPS request to Fedora's mirrors carrying a coarse age bucket for this machine. It is deliberately privacy-preserving, and it is still an unrequested outbound connection from a five-year-old's computer. Non-negotiable 5 is unconditional. |
| `dnf-makecache.timer` (and its `dnf5-makecache.timer` alias) | Downloads repository metadata on a timer. This image is built from a Containerfile and updated as a whole; nothing on the running machine installs RPMs, so the metadata is only ever bandwidth. |
| `unbound-anchor.timer` | Fetches the DNSSEC root trust anchor daily — for `unbound`, which is **not installed** (only `unbound-anchor` is) and is not this machine's resolver. `systemd-resolved` is. |
| `ModemManager.service` | Probes every serial device at boot looking for a cellular modem, then sits on D-Bus managing WWAN. kidnix targets refurbished laptops on home wifi. |
| `pcscd.socket` | Smartcard daemon. No smartcards, and authselect has already disabled smartcard authentication in the greeter (`/etc/dconf/db/distro.d/20-authselect`). |
| `sssd.service`, `sssd-kcm.socket` | Enterprise identity (LDAP/AD/Kerberos). **Verified safe:** `/etc/nsswitch.conf` is `passwd: files altfiles systemd` — `sss` is not in it, so nothing can consult sssd even if it ran. It has no config either, so its `ConditionPathExists` already prevented it starting; masking says so out loud. The test asserts the nsswitch precondition, not just the mask. |
| `fedora-atomic-desktop-appstream-cache-refresh.service` | Runs `appstreamcli refresh --force` at every boot to keep the software-catalogue cache warm — for the software centre this image deliberately does not have (ADR-0005 §1.1). |

Enabled system units: **92 → 80**.

### 5.2 The other half: what must stay enabled

Masking is a blunt instrument and mask lists get edited in a hurry, so the
build fails if any of these stops being `enabled`:

`gdm.service`, `NetworkManager.service`, `systemd-resolved.service`,
`chronyd.service`, `firewalld.service`, `sshd.service`,
`kidnix-egress.service`, `kidnix-boot-report.service`,
`kidnix-audio-cap.service`, `greenboot-healthcheck.service`,
`flatpak-add-fedora-repos.service`.

The last is the non-obvious one: on ublue it is what runs
`flatpak remote-add … flathub`, and `kidnix-flatpaks-firstboot` needs Flathub
to install TurboWarp. Masking it as "ublue phoning home" would silently break
the only Flatpak activity kidnix ships.

### 5.3 The full enabled list after hardening

```
NetworkManager-dispatcher.service   fedora-atomic-desktop-mandb-update.service
NetworkManager-wait-online.service  fips-crypto-policy-overlay.service
NetworkManager.service              firewalld.service
accounts-daemon.service             flatpak-add-fedora-repos.service
audit-rules.service                 fstrim.timer
auditd.service                      gdm.service
authselect-apply-changes.service    getty@.service
avahi-daemon.service                greenboot-healthcheck.service
avahi-daemon.socket                 greenboot-set-rollback-trigger.service
bluetooth.service                   greenboot-success.target
bootloader-update.service           intel_lpmd.service
chronyd.service                     kidnix-audio-cap.service
cups.path                           kidnix-boot-report.service
cups.socket                         kidnix-egress.service
dbus-broker.service                 kidnix-flatpaks-firstboot.timer
dbus.socket                         logrotate.timer
dm-event.socket                     lvm-devices-import.path
lvm-devices-import.service          systemd-boot-clear-sysfail.service
lvm2-lvmpolld.socket                systemd-confext.service
lvm2-monitor.service                systemd-homed-activate.service
machines.target                     systemd-homed.service
mcelog.service                      systemd-journald-audit.socket
mdmonitor.service                   systemd-mountfsd.socket
nfs-client.target                   systemd-network-generator.service
ostree-remount.service              systemd-nsresourced.socket
qemu-guest-agent.service            systemd-oomd.service
raid-check.timer                    systemd-oomd.socket
reboot.target                       systemd-pstore.service
remote-cryptsetup.target            systemd-resolved-monitor.socket
remote-fs.target                    systemd-resolved-varlink.socket
remote-integritysetup.target        systemd-resolved.service
remote-veritysetup.target           systemd-sysext.service
rpmdb-rebuild.service               systemd-tpm2-clear.service
rtkit-daemon.service                systemd-userdbd.socket
selinux-autorelabel-mark.service    thermald.service
smartd.service                      tuned-ppd.service
sshd.service                        tuned.service
switcheroo-control.service          udisks2.service
                                    upower.service
                                    uresourced.service
                                    vboxservice.service
                                    vgauthd.service
                                    vmtoolsd.service
```

Nothing ublue-specific survives that phones home: `ublue-os-update-services`
only ever shipped `flatpak-system-update.*` and `rpm-ostreed-automatic`
drop-ins (both masked). There is no `uupd`, no `ublue-update`, no `tailscaled`,
no Homebrew unit and no `podman.socket` enabled on `base-main:44` — that was
worth checking and it was not there.

---

## 6. `parent.toml`

Two **byte-identical** copies now ship:

| Path | Role |
|---|---|
| `/usr/share/kidnix/parent.toml` | Image-owned fallback. Replaced wholesale by every bootc upgrade. |
| `/etc/kidnix/parent.toml` | The machine's copy. `/etc` is writable and 3-way merged, so a parent's edits survive upgrades. |

`kidnix_shell.settings.Paths.parent_config` prefers `/etc` and falls back to
`$XDG_CONFIG_HOME`; the shell agent is concurrently adding the `/usr/share`
step. Shipping both makes every plausible resolution order work, and the build
log prints which one `Paths.parent_config` actually chose today.

Contents are the schema `ParentConfig` reads: `pin_salt`, `pin_hash`,
`default_session_minutes = 25`, no `allowed_activity_ids` (absent means "every
installed activity is allowed" — shipping a list would hide activities by
default), and one `[[profiles]]` entry (`id = "child"`, `name = "Me"`).

**Mode 0644 root:root**, not 0640 root:parent. The shell runs as `kid` and has
to *read* the PIN hash to check a PIN; a PBKDF2-SHA256 hash at 200 000 rounds
is not a secret from the account it protects — the protection is that guessing
is expensive, not that the digest is hidden. Root ownership is what stops the
child rewriting it.

The PIN is the documented development PIN **1234** with a fixed, public salt.
That is deliberate: a freshly installed machine has to let the grown-up in
before there is any UI to set a PIN with. **"Still 1234" means
"unconfigured", never "secured"**, and the parent panel must force a change.

### 6.1 The assertion that keeps this honest

The build loads the shipped file **through `kidnix_shell.settings` itself** —
the copy `60-shell.sh` installed into site-packages — and asserts the PIN
verifies, a wrong PIN does not, and every field parsed. Rename a field in
`settings.py` and the build stops here, rather than a child meeting a broken
grown-up gate. `tests/image/test_hardening.sh` repeats it.

### 6.2 The gap this does NOT close

`docs/spikes/session-integration.md` open question 2 is still open, and
shipping `/etc/kidnix/parent.toml` sharpens it rather than solving it: **the
grown-up sheet has to be able to WRITE this file to change the PIN, and `kid`
cannot write `/etc`.** `ParentConfig.save()` will raise `PermissionError`.

Before, the file fell back to `~/.config/kidnix/parent.toml`, which the child
*owns* — so the PIN was child-writable in principle, which is worse. Now it is
correctly unwritable, and the write path needs somewhere to go. That is a
`settings.py` + parent-panel decision (a parent-owned group-readable directory
under `/var/lib/kidnix`, or a polkit-mediated writer), not an image one.
Flagged for the thinker, and flagged to the shell agent.

---

## 7. NOT verified — needs a VM with a screen, or real hardware

1. **The parent's desktop actually shows the wallpaper.** The dconf default is
   compiled and reads back correctly; nobody has logged in as `parent` and
   looked. The failure mode if it is wrong is cosmetic (grey desktop), not
   functional.
2. **Settings → Appearance lists it.** `gnome-background-properties/kidnix.xml`
   is the documented mechanism and matches the shipped `petals.xml` structurally;
   it has not been rendered.
3. **Printing still works without `cups-browsed`.** No printer has been near
   this image. The claim "driverless printing finds printers over mDNS" is from
   the package dependency graph, not from a print job.
4. **sshd from a real client.** `bcvk ephemeral ssh` works (25/25 boot test),
   which exercises key auth as root. Nobody has tried `ssh parent@…` with a key,
   nor confirmed `ssh kid@…` is refused by `DenyUsers`.
5. **`rpm -V` noise.** The `mimeapps.list` edit will make `rpm -V` report a
   modified file forever. Harmless, but if anything ever gates on a clean
   `rpm -Va`, this is why it is not clean.
6. **A masked unit surviving `systemctl daemon-reload` on a real machine.**
   Masks are `/etc` symlinks and `/etc` is 3-way merged; a future upgrade that
   ships the same unit path should not disturb them, but that is reasoning, not
   a measurement.

---

## 8. Open questions for the thinker

1. **183 MiB of WebKit is still on the image** (§3.1), unreachable and
   unlaunchable, because `gdm → gnome-shell → gnome-control-center →
   gnome-online-accounts → evolution-data-server → webkitgtk` is an unbroken
   chain of hard requirements. Accept and document, or is this worth an ADR
   about eventually replacing `gnome-control-center` in the parent session?
2. **`gnome-backgrounds` is gone but `fedora-workstation-backgrounds` (5.1 MiB)
   stayed** so the Appearance panel is not empty. Is that the right line, or
   should kidnix ship *only* its own wallpaper?
3. **`PasswordAuthentication no` is a real behaviour change for a parent** who
   expects to `ssh parent@kidnix` with a password. It is one line in `/etc` to
   undo. Keep, or ship it permissive and let the parent panel harden it?
4. **Bluetooth is still enabled** (§3.5). It is the largest remaining
   network-adjacent surface after this pass. A taste call about hardware kidnix
   expects to meet.
5. **The image only shrank 62 MB even though the machine shrank 390 MiB** (§1).
   If pull size matters for CI or for parents on slow links, that is a
   Containerfile/flattening question, not a hardening one.
6. **Firefox is gone, so the parent has no browser at all.** ADR-0005 says that
   is intended ("the parent has other devices"). Worth confirming with the human
   before someone discovers it while trying to look up an error message.

---

## 9. Files

| File | What it does |
|---|---|
| `build_files/70-hardening.sh` | the whole pass: removals, leftovers, masks, sshd drop-in check, wallpaper + dconf, parent.toml, the size delta and the unit audit |
| `build_files/35-parent-desktop.sh` | (edited) no longer installs `gnome-backgrounds`; its weak-dependency note now points here |
| `system_files/usr/share/backgrounds/kidnix/default.png` | the wallpaper, 2560×1440, 112 KiB |
| `system_files/usr/share/backgrounds/kidnix/default.svg` | its editable source |
| `system_files/usr/share/gnome-background-properties/kidnix.xml` | puts it in Settings → Appearance |
| `system_files/etc/dconf/db/local.d/10-kidnix-background` | makes it the parent's default |
| `system_files/etc/ssh/sshd_config.d/10-kidnix.conf` | sshd stays on, with a much smaller surface |
| `system_files/usr/share/kidnix/parent.toml` | shipped defaults (fallback) |
| `system_files/etc/kidnix/parent.toml` | the machine's editable copy, byte-identical |
| `tests/image/test_hardening.sh` | 93 assertions |
| `tests/image/test_parent.sh` | (edited) dropped the `gnome-backgrounds` assertion |
