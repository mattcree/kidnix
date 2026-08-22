# Spike: the locked-down child session (M1)

**Status:** implemented at the image level, green in `just test-image` /
`test_lockdown.sh`. Several claims are *structurally* verified only — they need
a VM or real hardware before anyone should believe them. Those are listed
explicitly in §3; please do not quote §1 without §3.

**Owner of this milestone:** image-level lockdown. The shell-level half (time
limits, "ask a grown-up", the ending ritual) is not here.

**Everything below was checked against the actual image**
(`podman run --rm localhost/kidnix:… …`), not against memory or the research
docs. Where the research doc said UNVERIFIED and this spike resolved it, that
is called out.

---

## 1. What is implemented

### 1.1 No network egress for `kid`

Three layers, in decreasing order of how much weight they carry.

**(a) nftables, `/usr/lib/kidnix/nftables/kidnix-egress.nft`** — the
load-bearing one. A table of our own (`inet kidnix_egress`) with an `output`
hook that accepts loopback and `reject`s everything from **uid 1000**, loaded
by `kidnix-egress.service` before `network-pre.target`.

- **firewalld coexistence is fine.** firewalld is installed and enabled in the
  base image, `FirewallBackend=nftables`, `FlushAllOnReload=yes`. Read
  `firewall/core/nftables.py` in the image: it only ever names its own tables
  (`TABLE_NAME = "firewalld"`, plus `firewalld_policy_drop` and
  `firewalld_probe`). `inet kidnix_egress` is invisible to it and survives
  `firewall-cmd --reload`. We do **not** use `/etc/sysconfig/nftables.conf`,
  partly because it lives in `/etc` (3-way merged) and mostly because
  `nftables.service`'s `ExecStop` is `nft flush ruleset`, which would take our
  table with it.
- **The UID is numeric, not `"kid"`, and that is deliberate.** `nft` resolves
  `meta skuid "kid"` with `getpwnam()` **at parse time**. `kid` does not exist
  inside the build container — systemd-sysusers creates it on first boot — so a
  named rule cannot be syntax-checked at build time *and* would fail to load on
  a cold boot where the ruleset is applied before sysusers has run. Failing to
  load means failing **open**. `build_files/40-lockdown.sh` asserts that
  `/usr/lib/sysusers.d/kidnix.conf` still pins `kid` to `1000:1000`, and a
  greenboot check re-asserts it on the real machine.
- **`nft -c` needs `CAP_NET_ADMIN`.** It initialises a netlink cache even in
  check mode, so plain `nft -c -f` fails inside a rootless container with
  `cache initialization failed: Operation not permitted`. `unshare -rn nft -c -f`
  works: a throwaway user+network namespace makes us root over our own empty
  netns, which is all the parser needs. Verified that it still rejects real
  syntax errors and unknown usernames, so it is not a check that always passes.
  The build and the image test both use it; greenboot on the real machine uses
  plain `nft -c` as root.
- **Known gap:** `skuid` matches the *effective* UID of the socket owner, so a
  setuid-root network helper launched by `kid` would appear as uid 0. The image
  ships none today (`ping` on Fedora 44 is capability-based, not setuid).

**(b) Flatpak `--unshare=network`, globally.** Flatpak overrides live inside
the *installation* directory, and the system installation is `/var/lib/flatpak`.
`/var` is machine-local in a bootc image and `bootc container lint` fails the
build if we ship content there, so we cannot bake it in. Instead
`/usr/share/kidnix/flatpak/overrides-global` is image-owned and
`/usr/lib/tmpfiles.d/kidnix-lockdown.conf` copies it into place with tmpfiles'
`C` verb — once, on first boot, never clobbering a later parent edit. The build
runs the real `flatpak override --system --unshare=network` and diffs its
output against our seed, so the day the file format changes the build tells us.

*Trade-off, deliberate:* this is the **global** override, so it removes network
from every Flatpak on the machine, the parent's included. Right default for an
offline appliance; a parent can grant it back per-app with
`sudo flatpak override --share=network <app-id>`, which wins over the global
default.

**(c) NetworkManager via polkit** — `kid` is denied the whole
`org.freedesktop.NetworkManager.` prefix, so no joining Wi-Fi, no editing
connections, and no turning the radio off to see what happens.

We did **not** set `NetworkManager.conf [main] auth-polkit=root-only`
(research 07 §2.3 offers it). It would deny *all* non-root NM requests
including the parent's, which breaks `nm-connection-editor` for the person who
has to set the machine's Wi-Fi up. The per-user polkit rule is the same
protection with none of that cost.

### 1.2 polkit

`/usr/share/polkit-1/rules.d/40-kidnix-kid.rules`, image-owned.

- **Ordering matters and is now pinned.** polkit walks `rules.d` files in
  lexical order by basename and stops at the first rule returning something
  other than `NOT_HANDLED`. `40-` puts us ahead of Fedora's `50-default.rules`
  (which grants `wheel` `AUTH_ADMIN_KEEP`) and ahead of the unnumbered vendor
  files like `org.freedesktop.NetworkManager.rules` (digits sort before
  letters).
- **The engine is duktape, i.e. ECMAScript 5.1.** Verified:
  `rpm -q --requires polkit` → `libduktape.so.207()(64bit)`. A rules file
  duktape cannot parse is *ignored*, which fails **open** — so ES6 syntax in
  this file is a security bug, not a style nit. Both the build and the image
  test grep for `=>`, `let`, `const`, backticks, spread, `.includes(`, `class`
  and `for…of` after stripping comments.
- **There is no polkit dry-run**, so we built one:
  `/usr/share/kidnix/polkit-eval.js` + `/usr/libexec/kidnix-polkit-check`. It
  stubs the `polkit` global under `gjs`, loads the *real* rules file, and
  answers "what would you decide for user X and action Y". The build asserts 20
  cases; the image test asserts 26. This is a behavioural check, not a syntax
  check — but note gjs is SpiderMonkey and accepts far more than duktape, which
  is exactly why the ES5 grep exists alongside it.

**What `kid` is denied** (prefixes): NetworkManager, ModemManager, FirewallD,
Flatpak, rpm-ostree, bootc, PackageKit, sysupdate1, login1, systemd1, accounts,
gnome-control-center, gdm, udisks2/UDisks2, gvfs file-operations, hostname1,
locale1, timedate1, timesync1, home1, machine1, portable1, fwupd, bolt,
policykit (which is what `pkexec` asks for), and malcontent/ParentalControls.

**Deliberate carve-outs**, because denying them makes the machine worse without
making it safer:

- `org.freedesktop.login1.inhibit-*` — normal session plumbing.
  gnome-settings-daemon takes `inhibit-handle-power-key` and
  `inhibit-handle-lid-switch`; denying those hands the power key straight back
  to logind's default `HandlePowerKey=poweroff`, which is *less* safe.
- `*.ReadOwn` — reading (not changing) your own malcontent policy. Minor
  known looseness: the suffix carve-out is checked against *any* action id, not
  only the malcontent prefixes. No other action in this image ends in
  `.ReadOwn` (checked against every `.policy` file in
  `/usr/share/polkit-1/actions/`), so it is currently exact; tighten it if a
  future package introduces one.
- Everything not on the deny list: RealtimeKit (PipeWire needs it), colord,
  UPower, PowerProfiles, `org.gnome.mutter.backlight-helper` (a child adjusting
  screen brightness is fine).

**Decision for the thinker — suspend is DENIED.** `org.freedesktop.login1.suspend`
is inside the denied `login1.` prefix. Rationale: a child suspending mid-activity
is indistinguishable from a crash, and the shell's ending ritual (AGENTS.md
non-negotiable #2) owns "we're finished now". Lid-close suspend is *unaffected*
— logind handles that itself as root, not via polkit. If the thinker wants
suspend back it is a one-line carve-out next to the `inhibit-` one.

`parent` is untouched: the rule returns `NOT_HANDLED` for every user that is
not `kid`, so stock Fedora behaviour (password-prompted admin via wheel)
applies. AGENTS.md non-negotiable #6.

### 1.3 Kiosk hardening

**dconf.** `/etc/dconf/profile/kid` selects a compiled, image-owned database at
`/usr/share/kidnix/dconf/kid.compiled`, built from
`/usr/share/kidnix/dconf/kid.d/` with `dconf compile` (**not** `dconf update` —
`update` writes into `/etc/dconf/db`, and a binary blob in `/etc` gets
3-way-merged on every upgrade). Same shape as gnome-kiosk's own
`/usr/share/gnome-kiosk/gnomekiosk.dconf.compiled`.

Verified in the image:

- `dconf compile` works fine inside a bootc build — no dbus, no session needed.
- dconf finds profiles in **both** `/etc/dconf/profile/` and
  `$XDG_DATA_DIRS/dconf/profile/`. We use `/etc` because it is unconditional.
- Locks work with a `file-db` exactly as they do with a `system-db`:
  `DCONF_PROFILE=kid gsettings writable …` returns `false` for locked keys.
- Profile order is `user-db:user` first, `file-db:` second. Counter-intuitive
  but correct: first entry is the *writable* db, later entries are lower-priority
  defaults; locks override the user db regardless.

`kidnix-shell` exports `DCONF_PROFILE=kid` and also pushes it into
`systemd --user` and the dbus activation environment, because portals and gsd
helpers are started by the per-user manager (which `pam_systemd` started before
GDM ever exec'd us) and would not otherwise inherit it.

**A trap worth knowing about.** `dconf compile` accepts a value whose GVariant
type does not match the schema, stores it, and `gsettings` then silently
ignores it and returns the stock default. `disable-while-typing-timeout=1000`
sat in the compiled database looking perfectly correct while the touchpad kept
GNOME's 500 ms, because that key is `uint32` and wants
`disable-while-typing-timeout=uint32 1000`. The image test caught it; the build
now hard-fails if **any** key in `kid.d/` does not read back under
`DCONF_PROFILE=kid` as exactly what was written (doubles compared numerically,
since GVariant prints whatever precision round-trips). A lockdown that compiles
but does not apply is the worst outcome available.

Research 07 flagged most of `org.gnome.desktop.lockdown` as UNVERIFIED. **Now
verified against GNOME 50's schema**: `disable-command-line`,
`disable-lock-screen`, `disable-log-out`, `disable-user-switching`,
`disable-printing`, `disable-print-setup`, `user-administration-disabled`,
`disable-application-handlers`,
`mount-removable-storage-devices-as-read-only`, `disable-save-to-disk`,
`disable-show-password` all exist. The build refuses to ship if any key in
`kid.d/` is not in an installed schema.

**Keybindings and VT switching — the notable finding.**
`org.gnome.mutter.wayland.keybindings` contains `switch-to-session-1` …
`switch-to-session-12`. **That is where mutter — and therefore gnome-kiosk —
implements Ctrl+Alt+F<n> VT switching on Wayland.** Research 07 risk #7 recorded
"whether mutter/gnome-kiosk has a build/runtime option to swallow VT switch keys
entirely" as UNVERIFIED; the answer is yes, it is a gsettings key, and we blank
and lock all twelve.

The keybinding keyfile is **generated at build time** from
`gsettings list-keys` over `org.gnome.desktop.wm.keybindings`,
`org.gnome.mutter.keybindings` and `org.gnome.mutter.wayland.keybindings`
(102 keys on this image, all of type `as`), rather than hand-written. A GNOME
upgrade that adds a shortcut therefore cannot quietly add an escape hatch. The
build hard-fails if `switch-to-session-N` or `close` is missing from the result.

**logind.** `/usr/lib/systemd/logind.conf.d/10-kidnix-kiosk.conf` sets
`NAutoVTs=0` and `ReserveVT=0`, verified in force with
`systemd-analyze cat-config systemd/logind.conf`. This removes the VTs to
switch *to*; it does not stop the keystroke reaching the kernel. The dconf
keybinding blanking above is the layer that actually swallows the keystroke.
`getty@tty1.service` remains enabled (it is preset-enabled independently of
`NAutoVTs`, which only governs `autovt@` spawning), so a parent booting with
`systemd.unit=multi-user.target` still gets a real console. `KillUserProcesses=yes`
is deliberately **not** set — it belongs with the timekeeper milestone.

**Screen lock.** `lock-enabled=false`, `idle-activation-enabled=false`,
`user-switch-enabled=false`, `logout-enabled=false`, all locked. Idle *dim* and
*blank* survive: `org.gnome.desktop.session idle-delay = 900` (15 min) and
`org.gnome.settings-daemon.plugins.power idle-dim = true`, with
`sleep-inactive-{ac,battery}-type = 'nothing'` so the machine never suspends out
from under a drawing. A 5-year-old must never be able to lock themselves out.

**Shell auto-restart.** `/usr/libexec/kidnix-app-supervisor` wraps the payload:
`gnome-kiosk … -- kidnix-app-supervisor <app>`. When the app exits it restarts
it in place with a 0/1/2/5/10/30 s backoff, resets the backoff after 60 s of
healthy runtime, forwards SIGTERM/INT/HUP so logout is clean, and **never gives
up** — a black screen is not something a child can recover from. Without it,
gnome-kiosk exits when its app exits, ending the session and flashing the child
through GDM.

*Why not the "supported" way:* gnome-kiosk's documented recipe is a
`gnome-session` `.session` file with `RequiredComponents=` plus a systemd
**user** unit with `Restart=always`. That is the right end state and the thinker
should plan it, but it changes how GDM starts us and what the boot test asserts;
this wrapper gets the same behaviour today with one moving part. Recorded as an
open question in §4.

### 1.3b Trackpad and touch hardening

Research 09 Q7's verdict is blunt: *"a five-year-old on a trackpad is the worst
pointing case in the household"*, so **optimise for mouse and touch, treat the
trackpad as the degraded path, and harden it in software.** That is now
`/usr/share/kidnix/dconf/kid.d/11-trackpad` plus `locks/11-trackpad`. The whole
`org.gnome.desktop.peripherals.touchpad` schema moved out of `10-input` into
that file — one schema, one keyfile — and the build fails if it ever appears in
two, because `dconf compile` resolves a duplicate key by directory order and
nobody should have to reason about that.

**Every key was checked against this image's schemas**, not against memory:
`gsettings list-recursively org.gnome.desktop.peripherals.touchpad` on GNOME 50
lists `send-events`, `tap-to-click`, `tap-and-drag`, `tap-and-drag-lock`,
`tap-button-map`, `click-method`, `middle-click-emulation`,
`two-finger-scrolling-enabled`, `edge-scrolling-enabled`, `natural-scroll`,
`left-handed`, `disable-while-typing`, `disable-while-typing-timeout`,
`accel-profile`, `speed`.

**These keys are read by mutter itself, which is why they work here.** Verified
by grepping `/usr/lib64/libmutter-18.so.0`: it contains the key names *and*
`libinput_device_config_{tap,click,scroll}_set_*`. gnome-kiosk is mutter, so
the settings apply in the kid session even though no `gnome-settings-daemon`
input plugin is running in it. The image test asserts that grep, so a GNOME
release that moves the input backend out of mutter tells us.

| Key | Value | Why |
|---|---|---|
| `tap-to-click` | `false` | 09 Q7. Accidental taps from a resting palm or a wandering finger are the trackpad's dominant failure mode with small hands, and A3 ("input registers on press") makes every accidental tap a real action. |
| `click-method` | `'fingers'` | See below — this is the decision that needed making. |
| `two-finger-scrolling-enabled` | `false` | 09 Q7; A2 bans multi-touch as a design rule and this enforces it. |
| `edge-scrolling-enabled` | `false` | Same. Both false is what turns scrolling *off*. |
| `send-events` | `'enabled'` | The pointer must never silently die. |
| `disable-while-typing` (+ `timeout` 1000 ms) | `true` | 06 spec 6; the closest thing GNOME exposes to "maximum palm rejection". |
| `middle-click-emulation` | `false` | Never invent a button a child did not press. Mirrors the mouse. |
| `accel-profile` | `'flat'` | 06 spec 4, as for the mouse. |
| `speed` | `-0.2` | Moderate, and **not locked** — see below. |
| `org.gnome.mutter edge-tiling` | `false` | 06 spec 17: nothing a child needs lives at a screen edge. |
| `org.gnome.settings-daemon.peripherals.touchscreen orientation-lock` | `true` | Convertibles: no screen spinning mid-drawing. **Not locked** — see below. |

**`click-method='fingers'`, and `'default'` is a trap.** The choice is between
`'areas'` (libinput button-areas: the bottom edge of the pad is divided into
left / middle / right button zones) and `'fingers'` (clickfinger: one finger
down is a left click *anywhere* on the pad, two is right, three is middle).
`'areas'` means pressing in the wrong place is a right-click — a
position-driven misfire, and a child presses wherever their finger happens to
be. Clickfinger's misfire needs two separate fingers in contact at once, which
is rarer and which libinput's palm detection already works against. So
`'fingers'` minimises accidental right/middle clicks, and it is set
**explicitly rather than left at `'default'`**: `'default'` defers to
libinput's per-device default, which is button-areas on every touchpad except
Apple's — i.e. `'default'` would quietly mean `'areas'` on the ThinkPad-class
hardware we actually target. (`'none'` disables the click button entirely and
leaves a child with no way to click at all.) 06 §7.1 spec 3 — both buttons do
the same primary thing — means a stray right-click is harmless *inside our
shell*; it is not harmless inside a third-party activity, which is why this is
tuned rather than ignored.

**Disabling both scroll booleans really does mean no scrolling.** There is no
third key. mutter picks two-finger if enabled, else edge if enabled, else the
disabled scroll method, which becomes libinput's `SCROLL_NO_SCROLL`. `natural-
scroll` is therefore irrelevant and is **deliberately not set** — writing it
would be a taste call dressed up as evidence, and a key that reads back as a
lie about what the session does. A mouse wheel and a TrackPoint are separate
devices and keep scrolling; 06 §7.1 spec 11 says never *require* scroll
anyway (paginate, or offer large on-screen up/down buttons).

**`send-events='enabled'`, not `'disabled-on-external-mouse'`.** The latter is
tempting — research says optimise for the mouse, so kill the trackpad when a
mouse appears — but a trackpad that stops working when a mouse is plugged in
(and comes back when its battery dies) is exactly the kind of unexplained state
change a five-year-old cannot diagnose, with no adult-visible error anywhere.
Determinism wins. Recorded for the thinker as a one-value change if the family
decides otherwise.

**Two keys are deliberately left writable, and the build asserts that too.**
`speed`, because -0.2 is a starting point to be measured with the child
(SYNTHESIS §6 #5), not a finding — it is deliberately *less* slow than the
mouse's -0.4 because libinput applies an extra constant deceleration to
touchpads on top of the profile, and with tap-to-click off every click now
costs a reach and a press, so the pointer has to cross the screen without
repeated clutching. And `orientation-lock`, because 09 Q7 recommends **tent
mode** as the touch-first posture for 4–6 and getting into tent mode needs one
rotation; a locked key could not be flipped even by the parent panel acting on
the child's behalf (same rationale as `text-scaling-factor`). Everything else
in the table is locked.

**Gestures: there is no gsettings key, and that is a finding, not an
omission.** Swept *every* installed schema for keys matching
`*gesture*|*swipe*|*finger*`; the only hits are `a11y.mouse dwell-gesture-*`,
`touchpad tap-and-drag*` and `two-finger-scrolling-enabled`. Multi-finger
swipes are not configurable in GNOME 50 and libinput has no gesture-disable
API either. What we can say instead:

- mutter turns libinput gestures into Wayland `zwp_pointer_gestures_v1`
  swipe/pinch/hold events and **forwards them to the focused client**. It
  implements no workspace or overview swipe of its own — that is gnome-shell's
  JS `SwipeTracker`, which is not running in a kiosk session.
- `/usr/bin/gnome-kiosk` contains **no** gesture or swipe strings at all
  (asserted by the image test). So three- and four-finger swipes in the kid
  session go nowhere unless the shell itself asks for
  `zwp_pointer_gestures_v1`.
- **Therefore this is a requirement on the shell, not on the image:** the
  kidnix shell must not bind multi-finger gestures (A2 / 06 spec 12 already say
  so). `num-workspaces=1` and the blanked keybindings mean there is nowhere for
  a swipe to go even if one were delivered.

**Touchscreen: mostly not configurable here.**
`org.gnome.desktop.peripherals.touchscreen` is a **relocatable** schema —
per-device, under `/org/gnome/desktop/peripherals/touchscreens/<device>/` — and
its only key is `output` (monitor mapping). There is no profile-wide touchscreen
setting to lock, and we cannot know a device id at build time.
`org.gnome.settings-daemon.peripherals.touchscreen` *is* non-relocatable, has
exactly one key (`orientation-lock`), and is set as above. On hardware with no
accelerometer this is simply inert.

**Not verified — add to §3.** (i) That `'fingers'` actually reduces a *child's*
misfire rate; there is no child evidence on trackpad click methods at all
(09 Q7 marks it `GAP`), so this is reasoned, not measured — it is exactly what
the T480 protocol in 09 §11 should count. (ii) That both scroll booleans false
produces `SCROLL_NO_SCROLL` on real hardware; the mapping is read out of
mutter's use of libinput's scroll-method API, not observed. (iii) That
`disable-while-typing` plus libinput's automatic palm detection is enough palm
rejection for a five-year-old's hand — libinput exposes no palm-rejection knob,
so "maximum palm rejection" from 09 Q7 is as implemented as it can be.
(iv) Whether `orientation-lock=true` interacts badly with putting the machine
*into* tent mode; leaving the key writable is the mitigation, not the answer.

### 1.4 Audio safety

Research 07 §2.4 is honest that PipeWire has **no** declarative max-volume and
**no** built-in limiter. We shipped the two halves that are verifiable and
staged the one that is not.

- **ALSA hardware ceiling.** `/usr/libexec/kidnix-audio-cap` +
  `kidnix-audio-cap.service` (before `gdm.service`) set every card's
  `Master`/`Speaker`/`Headphone`/`PCM`/`Digital` control to 70% and
  `alsactl store`. Deliberately best-effort: no card, no such control, or a
  failed store all exit 0. A slightly-loud laptop is a bad day; a computer that
  will not start is a broken promise.
- **`api.alsa.soft-mixer = true`**, via
  `/usr/share/wireplumber/wireplumber.conf.d/50-kidnix-soft-mixer.conf`
  (WirePlumber 0.5 SPA-JSON, modelled on the shipped `alsa-vm.conf`). This is
  what makes the hardware cap *stick* — without it the first app to move the
  volume pushes the hardware `Master` back to 100%.
- **Filter-chain limiter: STAGED, NOT ACTIVE.** Written to
  `/usr/share/kidnix/examples/pipewire-kidnix-limiter.conf`
  (`linear` ×0.6 → `clamp` ±0.8; PipeWire 1.6 has no lookahead limiter builtin,
  so it is attenuate-then-clip). It is not enabled because making a filter-chain
  sink the default without creating a loopback loop cannot be verified in a
  build container with no sound card and no session bus, and the failure mode is
  *a child's computer with no sound at all* — strictly worse than occasionally
  too loud, and the ALSA cap already gives an unbypassable ceiling. The image
  test asserts it is **not** installed into `pipewire.conf.d`.

### 1.5 Health checks and rollback

**greenboot 0.16.3 on F44 is greenboot-rs, the Rust rewrite.** Verified:
`/usr/libexec/greenboot/greenboot` is a stripped ELF binary and the shipped
`/usr/share/doc/greenboot/README.md` is greenboot-rs's, describing itself as
"designed for bootc based systems". Research 07 had F44 presence as UNVERIFIED;
it is present, and it is the Rust one.

Checks live in `/usr/lib/greenboot/check/{required,wanted}.d/` — image-owned,
which is where `greenboot-default-health-checks` puts its own and which the
README calls "a read-only directory in ostree systems". (The README's prose
talks about `/etc`; both are read.)

| Check | Tier | Asserts |
|---|---|---|
| `10-kidnix-accounts.sh` | required | `kid` and `parent` exist; `kid` is uid **1000** (what the firewall filters); `kid` is in no admin group |
| `20-kidnix-egress.sh` | required | ruleset file present, `nft -c` parses it, table `inet kidnix_egress` is **loaded**, and it still contains a reject for uid 1000 |
| `30-kidnix-session.sh` | required | `kidnix-shell`, `gnome-kiosk`, the supervisor, the session desktop file, the polkit rules, the compiled dconf db, the dconf profile and the logind drop-in all exist; gdm and kidnix-egress enabled; bootc update timer masked |
| `10-kidnix-graphical.sh` | **wanted** | gdm active, default target graphical, a session for `kid`, flatpak override seeded |

**Why "gdm is active" is `wanted` and not `required`:** a required check that
fails is a RED boot; three of those and GRUB rolls the deployment back. "Did the
session come up *yet*" is the thing most likely to be slow rather than broken on
a cheap laptop's first cold boot, and a rollback loop is a far worse failure
than a red line in the journal. Required checks are all *structural* — true or
false the instant the deployment lands, incapable of being flaky.

**`greenboot-default-health-checks` is deliberately NOT installed.** Its
`01_repository_dns_check.sh` sits in `required.d` and resolves the DNS names of
the package repositories. kidnix is an offline appliance for a child; on a
machine with no network that check fails **every** boot, marks every boot red,
and rolls a perfectly good deployment back three boots later. The build
hard-fails if the subpackage ever gets pulled in as a dependency.

**How rollback actually fires (honest version).** greenboot-rs does *not* call
`bootc rollback`. Verified by grepping the binary: it touches
`/boot/grub2/grubenv`, `grub2-editenv`, `boot_counter` and `boot_success`. The
mechanism is GRUB-level — `/usr/lib/bootupd/grub2-static/configs.d/08_greenboot.cfg`
(shipped by **bootupd**, not greenboot) decrements `boot_counter` on each boot
and, when it hits 0/-1 with `boot_success=0`, does `set default=1`, i.e. boots
the previous ostree deployment. `greenboot-set-rollback-trigger.service` arms
the counter when `/etc` or `/var` needs update, i.e. after a new deployment.
So research 07 risk #4 resolves as: **rollback does not depend on
`bootc rollback` at all**, it depends on bootupd having installed that GRUB
snippet and on the system using GRUB. The image test asserts the snippet is
present. **Whether the whole chain actually fires is UNVERIFIED — see §3.**

### 1.6 Updates

`systemctl mask bootc-fetch-apply-updates.timer` at build time (verified: the
`/etc/systemd/system/…timer` symlink points at `/dev/null`). The timer checks
daily and **reboots** if it finds an update — mid-activity, unannounced, on a
child's computer. `bootc-fetch-apply-updates.service` is left unmasked so the
parent panel can invoke it deliberately; the panel will drive
`bootc upgrade --check` then `--apply` at a moment the family chose.

### 1.7 Flatpak remotes

Only the **system** installation exists (`flatpak --installations` →
`/var/lib/flatpak`). `kid` cannot add, modify or disable a remote because
`org.freedesktop.Flatpak.` is denied wholesale in polkit — that covers
`configure-remote`, `modify-repo`, `update-remote`, `install-bundle` and
`override-parental-controls`. A *user* installation under `~/.local/share/flatpak`
needs no polkit at all, so it is not blocked by policy — but with no network
egress there is nothing for it to pull from, and the shell offers no way to run
`flatpak`. Recorded in §4 as something to revisit if the shell ever gains a
terminal-ish affordance.

---

## 2. Verified at image level

Everything in this list is asserted by `tests/image/test_lockdown.sh` (137
assertions) and/or `build_files/40-lockdown.sh`, running inside the built
container:

- nftables ruleset parses (`unshare -rn nft -c -f`), rejects uid 1000, accepts
  loopback, reloads idempotently, and `kid` really is uid 1000 in sysusers.
- `kidnix-egress.service` is enabled in both multi-user and graphical wants.
- polkit rules are ES5, sort before `50-default.rules`, and return `NO` for 19
  specific actions as `kid` while returning `NOT_HANDLED` for `parent`, `root`
  and the three carve-outs.
- The compiled dconf database answers with the expected value for 30+ keys
  under `DCONF_PROFILE=kid`, reports the locked ones as non-writable, and does
  **not** leak into the default profile.
- All 102 mutter keybindings are blanked, including `switch-to-session-1..12`,
  `close`, `panel-run-dialog`, `switch-applications`.
- `NAutoVTs=0` / `ReserveVT=0` appear in the merged logind config;
  `getty@tty1` is still enabled.
- The supervisor really restarts a crashing payload (the test runs it against
  `/usr/bin/false` for 6 s and counts ≥3 starts).
- `kidnix-audio-cap` exits 0 with no sound card; the soft-mixer drop-in is
  present; the unverified limiter is **not** active.
- Four greenboot checks exist, are +x, and are valid bash; greenboot is
  installed and `greenboot-default-health-checks` is not; the GRUB
  `boot_counter` snippet is present.
- `bootc-fetch-apply-updates.timer` is masked.
- No lockdown content in `/var` (so `bootc container lint` stays green).

---

## 3. NOT verified — needs a VM or real hardware

Nothing in this section should be described as working.

1. **VT switching.** We can prove the keybindings are blanked and the VTs are
   gone. We cannot prove that a 6-year-old mashing Ctrl+Alt+F3 on real hardware
   sees nothing happen. *Test: boot the qcow2, send the key combo via ydotool,
   screenshot.* (research 07 risk #7)
2. **Keybindings inside a live gnome-kiosk.** dconf says the values are blank;
   whether mutter picked up the profile at session start is a different claim.
   In particular `DCONF_PROFILE` reaching `systemd --user`-activated helpers is
   best-effort. *Test: `DCONF_PROFILE` in `/proc/<gnome-kiosk-pid>/environ`, then
   `gsettings get` inside the session.*
3. **The nftables rule actually blocking a packet.** Loading is asserted;
   filtering is not. *Test: `sudo -u kid curl -m5 http://10.0.2.2/` in the VM
   must fail while the same command as `parent` succeeds. This is the single
   most important boot-test assertion to add.*
4. **The audio ceiling.** No sound card in a container. Unknown: whether every
   card exposes a control named `Master`, whether `soft-mixer` costs measurable
   CPU on the low-end targets in research 06 §3.1, and whether a Flatpak with
   `--socket=pulseaudio` can still raise the software volume above the cap.
5. **greenboot rollback end-to-end.** We verified the *mechanism* (GRUB
   `boot_counter`, not `bootc rollback`) but not that a deliberately-failing
   required check produces a rollback after three boots. *Test: drop a
   `required.d` script that exits 1, reboot three times, assert
   `bootc status` shows the older deployment.* (research 07 risk #4)
6. **The flatpak override reaching `/var` on a real install.** tmpfiles' `C`
   verb is asserted to be *configured*; the copy happening is a first-boot
   event.
7. **The supervisor under a real compositor.** Verified standalone. Not
   verified that gnome-kiosk is happy with a shell wrapper as its app argument
   (window matching in `window-config.ini` matches on title/class/sandboxed-app-id,
   which the wrapper does not change — but that is reasoning, not evidence).
8. **`NAutoVTs=0` and GDM.** GDM allocates a VT through logind. This is common
   kiosk practice, but "GDM still starts with no auto-VTs" is not something a
   container can tell us.

---

## 4. Open questions for the thinker

1. **Suspend is currently denied for `kid`.** Deliberate (§1.2). Confirm or
   reverse — it is a one-line carve-out.
2. **`gnome-session` vs the supervisor wrapper.** The wrapper is the pragmatic
   M1 answer. Moving to a `.session` file with `RequiredComponents=` plus a
   `Restart=always` user unit is the upstream-blessed shape and would also give
   us somewhere natural to hang `kidnix-timekeeper.service`. Worth an ADR before
   the real shell lands, because it changes the GDM entry point.
3. **`KillUserProcesses=yes`.** Research 07 §2.3 wants it for clean time-limit
   termination. Left off here because it also kills a parent's detached
   ssh/tmux work. Decide with the timekeeper milestone.
4. **Global vs per-app Flatpak network override.** Currently global, so the
   parent's Flatpaks lose network too. Alternative is per-app overrides written
   by the activities first-boot unit. Global is simpler and matches research;
   flagging it because it is a visible parent-facing consequence.
5. **User-installation Flatpaks.** `kid` could in principle
   `flatpak install --user` with no polkit involved. Moot today (no network, no
   terminal). Revisit if the shell ever gains a way to run arbitrary commands.
6. **`text-scaling-factor` and `cursor-theme` are unlocked on purpose** so the
   parent panel can tune them per child; `cursor-size` **is** locked at 48.
   Confirm that split.
7. **Duplicate tmpfiles lines.** `kidnix-lockdown.conf` and the activities
   milestone both want `d /var/lib/flatpak` and `d /var/lib/kidnix`.
   systemd-tmpfiles warns and continues, but it would be tidier for one file to
   own each path.
8. **`sysrq`.** Research 07 suggests `kernel.sysrq=0` as belt-and-braces. Not
   done here — it is a kernel-cmdline/sysctl change that also removes a
   parent's emergency escape. Cheap to add if wanted.

---

## 5. Files

**New build stage**

- `build_files/40-lockdown.sh`

**New image content**

- `system_files/usr/lib/kidnix/nftables/kidnix-egress.nft`
- `system_files/usr/lib/systemd/system/kidnix-egress.service`
- `system_files/usr/lib/systemd/system/kidnix-audio-cap.service`
- `system_files/usr/lib/systemd/logind.conf.d/10-kidnix-kiosk.conf`
- `system_files/usr/lib/tmpfiles.d/kidnix-lockdown.conf`
- `system_files/usr/share/polkit-1/rules.d/40-kidnix-kid.rules`
- `system_files/usr/share/kidnix/polkit-eval.js`
- `system_files/usr/share/kidnix/dconf/kid.d/00-lockdown`
- `system_files/usr/share/kidnix/dconf/kid.d/10-input`
- `system_files/usr/share/kidnix/dconf/kid.d/locks/00-lockdown`
- `system_files/usr/share/kidnix/dconf/kid.d/locks/10-input`
- `system_files/usr/share/kidnix/flatpak/overrides-global`
- `system_files/usr/share/kidnix/examples/pipewire-kidnix-limiter.conf`
- `system_files/usr/share/wireplumber/wireplumber.conf.d/50-kidnix-soft-mixer.conf`
- `system_files/usr/libexec/kidnix-app-supervisor`
- `system_files/usr/libexec/kidnix-audio-cap`
- `system_files/usr/libexec/kidnix-polkit-check`
- `system_files/usr/lib/greenboot/check/required.d/10-kidnix-accounts.sh`
- `system_files/usr/lib/greenboot/check/required.d/20-kidnix-egress.sh`
- `system_files/usr/lib/greenboot/check/required.d/30-kidnix-session.sh`
- `system_files/usr/lib/greenboot/check/wanted.d/10-kidnix-graphical.sh`
- `system_files/etc/dconf/profile/kid`

Generated at build time into the image (not in git):
`/usr/share/kidnix/dconf/kid.d/50-keybindings`,
`/usr/share/kidnix/dconf/kid.d/locks/50-keybindings`,
`/usr/share/kidnix/dconf/kid.compiled`.

**Modified**

- `system_files/usr/bin/kidnix-shell` — exports `DCONF_PROFILE=kid`, pushes it
  into the user manager and dbus activation environment, and runs the payload
  under `kidnix-app-supervisor`.

**New test**

- `tests/image/test_lockdown.sh`
