# Spike: the parent's desktop (ADR-0005)

**Status:** implemented at the image level, green in `test_parent.sh`
(68 assertions), `bootc container lint` clean. Everything about *starting* the
session is structurally verified only — GDM, AccountsService and malcontent all
need a live D-Bus, so nothing here proves the parent can actually log in. §7
lists exactly what a VM has to check.

**Everything below was checked against the real image**
(`podman run --rm localhost/kidnix:parent …`), not against memory or the
research docs.

---

## 1. The headline: the parent desktop is nearly free

ADR-0005 estimated **+400–700 MB** for "gnome-shell, gnome-session,
gnome-control-center, nautilus, a terminal, malcontent-control and the minimal
supporting set". The measured cost is **+63 MiB installed / +0.07 GB on the
image**, because most of it was already there.

`gdm` **hard-requires** `gnome-shell` (it *is* the greeter) and
`gnome-session-wayland-session`; `gnome-shell` **hard-requires**
`gnome-control-center`. Verified in the image:

```
$ rpm -q --whatrequires gnome-shell
gnome-session-wayland-session-50.1-1.fc44.x86_64
gdm-50.2-1.fc44.x86_64
$ rpm -q --whatrequires gnome-control-center
gnome-shell-50.4-1.fc44.x86_64
```

So the moment `00-packages.sh` installed `gdm` — back in M0, for the *child's*
kiosk — the image already contained gnome-shell 50.4, gnome-session 50.1,
gnome-control-center 50.4, gnome-settings-daemon 50.1, xdg-desktop-portal-gnome
50.0 **and** `/usr/share/wayland-sessions/gnome.desktop`. A parent could
already have logged into stock GNOME. The parent desktop was an accident before
it was a decision; this stage turns it into a decision.

What `35-parent-desktop.sh` actually adds:

| Package | Installed size | Why |
|---|---|---|
| `gnome-backgrounds` | 37.8 MiB | Without it GNOME's default `picture-uri` points at a file that does not exist; the parent's desktop is a grey rectangle that reads as "broken" |
| `nautilus` (+ `nautilus-extensions`) | 14.1 MiB | A file manager. Non-negotiable #7: the child's work is real files, and the parent must be able to see, copy and back them up |
| `ptyxis` (+ `vte291`, `vte291-gtk4`, `vte-profile`, `simdutf`) | 5.0 MiB | Fedora 44's default terminal (it replaced gnome-terminal). A parent fixing a broken machine needs a shell |
| `malcontent-tools` | 0.06 MiB | `malcontent-client(1)` — the only scriptable way to read/write the child's policy |
| `glycin-gtk4-libs`, `glycin-thumbnailer`, `gst-thumbnailers`, `gvfs-fuse`, `libportal`, `libportal-gtk4` | 2.4 MiB | Nautilus' thumbnailers and portal glue, via Recommends |
| **total** | **59.3 MiB over 15 packages** | |

`36-fonts.sh` adds **3.7 MiB over 3 packages** (§3).

Image size: `localhost/kidnix:parent` is **8.19 GB**, against **8.12 GB** for
the same working tree built without these two stages, i.e. **+0.07 GB**. (The
6.4 GB figure in older notes predates the activity payload: Tux Paint stamps,
SuperTux and KTuberling alone are ~570 MB. The parent desktop is not what made
this image big.)

### 1.1 What we deliberately did not install

Not the `@gnome-desktop` comps group. Its **mandatory** list alone is
`dconf gdm gnome-control-center gnome-initial-setup gnome-session-wayland-session
gnome-settings-daemon gnome-shell gnome-software gnome-text-editor nautilus
polkit ptyxis yelp` — an app store, a setup wizard a four-year-old cannot
complete, and a help browser with a web engine in it. Its **default** list adds
~50 more (gnome-boxes, gnome-maps, showtime, rygel, sane scanner backends,
gnome-remote-desktop…).

`35-parent-desktop.sh` fails the build if `gnome-software`,
`gnome-initial-setup`, `gnome-boxes`, `yelp`, `gnome-user-share`,
`gnome-classic-session` or `epiphany` ever appear, and `test_parent.sh`
re-asserts it. That tripwire is the actual deliverable of §1.1: it is what
stops someone "simplifying" the package list into `@gnome-desktop` in six
months.

### 1.2 What arrived anyway, that we did not ask for

Installing `gdm`/`gnome-shell` with weak dependencies on (which
`00-packages.sh` documents as a deliberate day-one choice) already pulled in
**gnome-remote-desktop, rygel, gnome-tour, gnome-color-manager,
nm-connection-editor, gnome-bluetooth, bolt** — all present in the image
*before* this stage. gnome-remote-desktop and rygel (a UPnP/DLNA media server)
are the two that deserve a decision: both are network-facing services on a
child's machine.

This stage does not remove them — `00-packages.sh` owns the weak-dependency
policy and is not mine to edit — but it counts them and prints them in the
build log so the number stays visible. See open question 1.

**And `base-main` ships Firefox.** Not installed by kidnix, not launchable from
the child's session (no launcher, and uid 1000 has no egress), but it is in the
image. Recorded in `docs/LICENSES.md`; open question 2.

---

## 2. GDM, AccountsService and who gets which session

### 2.1 The mechanism

Two Wayland sessions exist in the image and only two:

```
/usr/share/wayland-sessions/gnome.desktop          (gnome-session-wayland-session)
/usr/share/wayland-sessions/kidnix-shell.desktop   (ours)
```

`/usr/share/xsessions` is empty and `gnome-session-xsession` is not installed —
kidnix is Wayland-only, asserted at build time, because an X session in the
greeter would be a second code path nobody tests and a second lockdown surface.

Which session a user gets is stored per-user by AccountsService in
`/var/lib/AccountsService/users/<name>`, and the session *name* is the desktop
file's basename. kidnix ships two seeds:

| File | Seeded to | Contents |
|---|---|---|
| `/usr/share/kidnix/accountsservice-kid` | `/var/lib/AccountsService/users/kid` | `Session=kidnix-shell` |
| `/usr/share/kidnix/accountsservice-parent` | `/var/lib/AccountsService/users/parent` | `Session=gnome` |

Both are copied by `systemd-tmpfiles` (`kidnix.conf` for the kid,
**`kidnix-parent.conf`** for the parent) rather than baked into the image,
because `/var` is machine-local in bootc: image content under `/var` is
first-boot-only at best and silently discarded at worst. `C` copies only when
the target does not exist, so a parent who later picks a different session in
GDM keeps it across upgrades.

**Ordering was a real worry and turned out not to be one.** `kidnix.conf` owns
the `d /var/lib/AccountsService{,/users}` lines, and `kidnix-parent.conf` sorts
*before* it alphabetically (`-` is 0x2D, `.` is 0x2E). But systemd-tmpfiles
executes items in **path** order across every fragment, so the directories are
created and chmodded before any `C` line copies into them. Verified by running
`systemd-tmpfiles --create` on the fragment alone inside the container with
`/var/lib/AccountsService` deleted: it recreated the tree and produced a
correct `users/parent`. The build script does exactly that check on every
build, then deletes `/var/lib/AccountsService` again so nothing leaks into the
image (`bootc container lint` and `test_image.sh`'s "/var carries no image
content" both stay green).

### 2.2 Why `parent` gets an explicit override at all

Research 07 §2.2 says the parent "simply has no override (or `Session=gnome`)".
We chose the explicit form. With no override, which session GDM picks depends
on its fallback ordering over `/usr/share/wayland-sessions`, where the only two
candidates are `gnome.desktop` and `kidnix-shell.desktop`. A parent silently
landing inside the child's kiosk — which has no launcher, no terminal and no
way out except a hard reboot — is a catastrophic first five minutes, and it
depends on undocumented GDM behaviour. Being explicit costs one file.

### 2.3 What is and is not possible: per-user session filtering

**GDM cannot filter the session list per user.** The greeter's session chooser
enumerates `/usr/share/wayland-sessions` and `/usr/share/xsessions` globally;
there is no per-user allow-list, and AccountsService's `Session` key sets a
*default*, not a *restriction*. So:

- The `gnome` session **is** selectable for `kid` at the greeter, and
  `kidnix-shell` **is** selectable for `parent`. Neither can be hidden from the
  other by any supported GDM mechanism.
- This does not matter today, and here is why: `kid` **never reaches a
  greeter**. `/etc/gdm/custom.conf` has `AutomaticLoginEnable=True` /
  `AutomaticLogin=kid`, so the machine boots straight into the kiosk. The
  lockdown (`40-lockdown.sh`) then removes every route back out: no VT
  switching (`NAutoVTs=0`, `ReserveVT=0`, all twelve
  `switch-to-session-N` keybindings blanked and locked), no user switching
  (`org.gnome.desktop.lockdown disable-user-switching`), no log-out affordance
  in gnome-kiosk, and polkit denies `org.freedesktop.login1.chvt`.
- The parent reaches the greeter the way ADR-0005 describes: the Grown-up gate
  in the kid session logs the kid out (GDM's automatic login fires once per
  boot, so the greeter appears), or the parent boots with autologin disabled.
- **The residual risk is a child who reaches a greeter anyway** — e.g. after a
  parent logs out — and picks `kidnix-shell` for the `parent` account, or picks
  `gnome` for `kid`. The second is the interesting one: `kid` in stock GNOME
  would have a launcher and a Files app. It is still bounded (no network for
  uid 1000, polkit denies everything that matters, the kid dconf profile is
  *not* applied outside `kidnix-shell` — see open question 3), but it is not
  the designed experience.
- **The honest mitigation** is a password on `kid`… which contradicts the
  autologin design, or a shell-side change: hide the session chooser entirely
  by shipping only one session file and having `kidnix-shell` `exec` GNOME for
  uid 1001. Both are worse than the current arrangement for v0.1. Recorded as
  open question 3.

### 2.4 Autologin and the parent

`AutomaticLoginEnable=True` means the first graphical session after boot is
always `kid`. Logging that session out brings up the greeter with the normal
user list and the gear-icon session chooser, and `parent` can log in there.
GDM does **not** re-autologin within the same boot. This is standard GDM
behaviour but has **not** been observed on kidnix — it is item 1 in §4.

---

## 3. Fonts

`sil-andika-fonts` **is** packaged in Fedora 44 (6.101-9.fc44), so the
build-time download with SHA-256 verification that the task anticipated is not
needed and does not exist. Same for Atkinson: Fedora 44 has
`atkinson-hyperlegible-next-fonts` and `atkinson-hyperlegible-mono-fonts`
(2.100-3.fc44). The plain `atkinson-hyperlegible-fonts` name is **gone** from
F44 — "Next" is the second-generation family and the only one packaged. Both
are OFL-1.1; `docs/LICENSES.md` records the licences, sources and install
paths, plus the fallback download URLs if a future Fedora drops them.

Deliberately *not* installed: `sil-andika-compact-fonts` (a tighter-spaced cut
aimed at print) and `sil-andika-new-basic-fonts` (superseded by Andika 6).

`36-fonts.sh` runs `fc-cache --force --system-only` in the image. This matters
for two reasons beyond speed:

1. Without it, fontconfig rebuilds into `~/.cache/fontconfig` on the first GTK
   launch, per account — a visible stall on the refurbished laptops kidnix
   targets.
2. The cache lands in **`/usr/lib/fontconfig/cache`** (32 files, ~1.2 MB),
   which is image-owned and survives into the bootc deployment. If a future
   fontconfig moved it under `/var`, it would evaporate at install time and
   nobody would notice — so the build asserts the path.

The build also proves fontconfig can *resolve* each family, not merely that
files landed: `fc-list : family` must contain each name, and
`fc-match Andika family` must return `Andika` rather than a fallback. A font
with a broken name table is invisible to every toolkit, and `rpm -q` cannot
tell you that.

**This stage sets no default font.** Which face the child's shell renders in
belongs to the shell (ADR-0004) and to the kid dconf profile in
`40-lockdown.sh`; `36-fonts.sh` only guarantees the faces are on disk and
findable. Recommendation for the shell agent: `Andika` for all child-facing UI
text, `Atkinson Hyperlegible Mono` anywhere a child sees code.

---

## 4. GNOME 50 parental controls: what exists, and the integration plan

### 4.1 What is actually in the image (verified)

| Surface | Present? | Evidence |
|---|---|---|
| `malcontent` 0.14.0 | yes | + `malcontent-libs`, `malcontent-control`, and now `malcontent-tools` |
| `malcontent-client(1)` | yes, **newly added** | ships in `malcontent-tools`, which was **not** installed before this stage — `malcontent` alone gives you daemons and D-Bus XML, no CLI |
| `malcontent-control` GUI | yes | `/usr/bin/malcontent-control`, `/usr/share/applications/org.freedesktop.MalcontentControl.desktop` |
| Settings → **Wellbeing** panel | yes | `XDG_CURRENT_DESKTOP=GNOME gnome-control-center --list` lists `wellbeing` (it refuses to run at all without that env var, which is why the naive check fails in a container) |
| Screen-time schema | yes | `org.gnome.desktop.screen-time-limits`: `daily-limit-enabled`, `daily-limit-seconds` (u, default 28800), `grayscale` (default true), `history-enabled` |
| malcontent daemons | yes | `malcontent-timerd.service`, `malcontent-webd.service`, `malcontent-webd-update.timer`, `malcontent-timer-extension-agent.service` |
| A Settings "Parental Controls" panel | **no** | GNOME 50 has no such panel; `malcontent-control` is a separate app. The Settings half is `wellbeing`, which is *self*-imposed screen time, not parental policy |

Note the split, because it is easy to get wrong: **`org.gnome.desktop.screen-time-limits` is a per-user gsetting the user sets on themselves** (GNOME's digital-wellbeing feature). **Parental policy lives in malcontent**, in AccountsService, and is what a *different* user (the parent, via polkit) sets on the child. They are different mechanisms with confusingly similar names.

### 4.2 The storage format (verified from the shipped D-Bus XML)

`/usr/share/accountsservice/interfaces/` carries three vendor extensions:

| Interface | Property | Type | Default |
|---|---|---|---|
| `com.endlessm.ParentalControls.AppFilter` | `AppFilter` | `(bas)` | `(false, [])` |
| | `OarsFilter` | `(sa{ss})` | `('oars-1.1', {})` |
| | `AllowUserInstallation` / `AllowSystemInstallation` | `b` | `true` |
| `com.endlessm.ParentalControls.SessionLimits` | `LimitType` | `u` | `0` (none) |
| | `DailySchedule` | `(uu)` | `(0, 86400)` |
| | `DailyLimit` | `u` | `0` |
| | `ActiveExtension` | `(tu)` | `(0, 0)` |
| `org.freedesktop.Malcontent.WebFilter` | `FilterType`, `BlockLists`, `CustomBlockList`, `AllowLists`, `CustomAllowList`, `ForceSafeSearch` | | |

The boolean in `AppFilter (bas)` is **"this list is an allow-list"**. That is
the mode kidnix wants: `(true, [<the activities we ship>])`.

**Gotcha found:** `malcontent-client set-app-filter` only takes *"paths, content
types or flatpak refs to **blocklist**"* — its CLI has no allow-list switch.
Allow-list mode has to be written over D-Bus / `libmalcontent` (`Malcontent-0`
typelib is installed, so GJS or Python-gi can do it). The parent panel will do
this natively; a shell script cannot.

Also present: `libnss_malcontent.so` — malcontent hooks NSS, which is how the
"account is managed" state reaches things that only know about users.

### 4.3 How kidnix should use it (proposal for the thinker)

The rule from research 07 §2.3 is the right one and this spike does not change
it: **malcontent is where kidnix *records* policy; it is never what *enforces*
it.** malcontent's own README says a technically advanced user can work around
it, and every consumer (Flatpak, GNOME Software, gnome-shell) enforces
voluntarily and independently.

Concretely, kidnix should:

1. **Write, on first boot / when the parent panel changes the activity list:**
   - `AppFilter = (true, [<flatpak refs and /usr/bin paths of every enabled
     activity>])` — allow-list mode. This makes `malcontent-control` show the
     parent a truthful picture of what their child can run, in the
     freedesktop-standard schema, without kidnix inventing a format.
   - `OarsFilter = ('oars-1.1', {…})` with a **3+ ceiling**. Research 07 §2.5
     notes GCompris, Tux Paint, SuperTux, KTuberling and Blinken are rated 3+
     while SuperTuxKart, Stellarium and Luanti are 13+; a 3+ ceiling excludes
     the latter, which for ages 4–8 is probably correct but must be a
     deliberate choice, not a side effect.
   - `AllowUserInstallation = false`, `AllowSystemInstallation = false` for
     `kid` — belt and braces with the polkit denials already in
     `40-lockdown.sh`.
2. **Read, but not depend on:** `SessionLimits`. kidnix's own timekeeper
   (research 07 §2.3) owns the child-facing experience — the visible timer, the
   warnings, the save-and-goodbye ritual — because non-negotiable #2 says
   ending is never a surprise, and malcontent's `LimitType` has no concept of a
   gentle ending. But kidnix should *mirror* the parent's chosen budget into
   `DailyLimit` / `DailySchedule` so `malcontent-control` and GNOME agree with
   the parent panel, and should read them back if the parent edits them in
   `malcontent-control` instead.
3. **Ignore for now:** `WebFilter`. There is no browser in the child session
   and no egress for uid 1000, so a web filter is policy about something that
   cannot happen. Revisit if a Kiwix-style offline browser ever ships.
4. **Never** treat a malcontent "allow" as authorisation to launch. The
   structural enforcement stays what it is: the child's shell only knows about
   the activities we ship, and there is no other way to launch anything.

---

## 5. The parent panel placeholder

`/usr/bin/kidnix-parent-panel` is a bash stub that prints what it is, that it
is not built yet, and the four commands a parent can use in the meantime
(`malcontent-control`, `gnome-control-center`, `journalctl -u 'kidnix-*'`,
`bootc upgrade --check`). `/usr/share/applications/kidnix-parent-panel.desktop`
launches it with `Terminal=true` so the message is actually seen — a launcher
that appears to do nothing when clicked reads as a broken machine.

It exists now, before the real panel, so that the desktop entry, its icon slot
and its place in the parent's app grid are real and testable from M1. The
`.desktop` passes `desktop-file-validate` (unlike `kidnix-shell.desktop`, which
legitimately uses the non-registry `DesktopNames` key and is validated with
`|| true`).

It is not hidden from the kid: `NoDisplay` would be theatre, since the kid
session has no launcher to hide it *from*.

---

## 6. Verified at image level

Everything in this list is asserted by `build_files/35-parent-desktop.sh`,
`build_files/36-fonts.sh` or `tests/image/test_parent.sh` (68 assertions), and
runs on every build:

1. gnome-shell, gnome-session, gnome-session-wayland-session,
   gnome-settings-daemon, gnome-control-center, xdg-desktop-portal-gnome,
   nautilus, ptyxis, gnome-backgrounds are installed.
2. `/usr/share/wayland-sessions/gnome.desktop` exists and has an `Exec` line;
   `/usr/share/gnome-session/sessions/gnome.session` exists.
3. Exactly two Wayland sessions are offered, and no X sessions at all.
4. The parent's AccountsService seed says `Session=gnome` / `XSession=gnome` /
   `SessionType=wayland`, names a session file that exists, and is different
   from the kid's.
5. `kidnix-parent.conf` seeds it, the whole tmpfiles set still parses, and a
   real `systemd-tmpfiles --create` run produces the right file.
6. malcontent, -libs, -control, -tools installed; `malcontent-client` and
   `malcontent-control` are executable; all three AccountsService interface
   XMLs are present; `malcontent-timerd.service` exists.
7. `gnome-control-center --list` includes `wellbeing`, and the
   `org.gnome.desktop.screen-time-limits` schema is installed.
8. Andika, Atkinson Hyperlegible Next and Atkinson Hyperlegible Mono are
   installed, visible to `fc-list`, and `fc-match Andika` resolves to Andika.
9. The font cache is built and lives under `/usr`.
10. The parent panel stub is executable, valid bash, actually runs and prints
    an explanation; its `.desktop` validates and has both `Exec` and `TryExec`.
11. gnome-software, gnome-initial-setup, gnome-boxes, yelp, gnome-user-share,
    gnome-classic-session, epiphany and chromium are absent.
12. `parent` is uid 1001, outside the uid-1000 egress filter.
13. `bootc container lint` passes (13 checks) and `/var` carries no image
    content after these stages.

---

## 7. NOT verified — needs a VM or real hardware

Nothing about *starting* a session can be proven in a container. In rough order
of importance:

1. **The parent can actually log in and gets stock GNOME.** Boot, log the kid
   session out, log in as `parent`, confirm gnome-shell (not gnome-kiosk).
   ```
   loginctl list-sessions
   loginctl show-session "$XDG_SESSION_ID" -p Type -p Desktop
   echo "$XDG_CURRENT_DESKTOP"          # expect GNOME
   busctl --user list | grep org.gnome.Shell
   ```
2. **GDM honoured the AccountsService seed.**
   ```
   sudo cat /var/lib/AccountsService/users/parent   # expect Session=gnome
   busctl call org.freedesktop.Accounts /org/freedesktop/Accounts/User1001 \
       org.freedesktop.DBus.Properties Get ss org.freedesktop.Accounts.User XSession
   ```
3. **GDM does not re-autologin the kid after a logout in the same boot** — the
   whole "parent reaches the greeter" story depends on it.
4. **malcontent can read and write the child's policy.** Needs accounts-service
   on the system bus, so container-impossible. As `parent`:
   ```
   malcontent-client get-app-filter kid
   malcontent-client get-app-filter 1000
   malcontent-client get-session-limits kid
   malcontent-client set-session-limits kid daily-limit 3600
   malcontent-client check-app-filter kid /usr/bin/gcompris-qt
   ```
   Expect a polkit prompt (`com.endlessm.ParentalControls.AppFilter.ChangeAny`)
   the first time, and expect `get-app-filter kid` **as `kid`** to work
   (`ReadOwn` is `NOT_HANDLED` by our polkit rules) while
   `set-app-filter` as `kid` is denied.
5. **Allow-list mode over D-Bus.** No CLI path (§4.2), so this needs a real
   GJS/Python-gi snippet against `Malcontent-0`. Untested; the parent panel is
   the first thing that will exercise it.
6. **`malcontent-control` renders and shows `kid`.** It is a GTK4 app; nobody
   has seen it run on this image.
7. **The Wellbeing panel renders** and its screen-time UI does something
   sensible for a managed child account.
8. **Nautilus and Ptyxis actually start on Wayland** in the parent session.
9. **Andika renders.** `fc-match` says the family resolves; nobody has seen a
   glyph. The interesting question is whether Andika's single-storey `a` is
   legible at the sizes and on the panels kidnix will run on.
10. **The kid dconf profile does not leak into the parent session.**
    `DCONF_PROFILE=kid` is exported only by `kidnix-shell`, so it should not,
    but "should not" is not "does not". As `parent`:
    `gsettings get org.gnome.desktop.interface cursor-size` should be 24, not 48.
11. **The greeter's session chooser** — confirm it lists both sessions, so §2.3
    is describing reality.

---

## 8. Open questions for the thinker

1. **Weak dependencies.** gnome-remote-desktop and rygel are network-facing
   services that arrived as Recommends of the GNOME stack, before this stage,
   on a machine whose entire premise is that a child cannot reach the network.
   Options: `--setopt=install_weak_deps=False` for the GNOME installs (risky —
   `00-packages.sh`'s comment explains why weak deps are on), targeted
   `dnf5 remove` in a late stage, or masking their units. This is
   `00-packages.sh`/`40-lockdown.sh` territory, not mine. Recommend: mask the
   units in M1, revisit removal at M2 with a measured package diff.
2. **Firefox in the image.** Ships with `base-main`. Unreachable by the child;
   arguably useful to the parent; definitely surprising in a "no web browser"
   OS. Keep, remove, or keep-and-document? Needs a one-line ADR either way.
3. **Session chooser leakage (§2.3).** Nothing prevents someone at a greeter
   picking `gnome` for `kid`. Cheap partial fix: make the kid's *session* fail
   closed by having `kidnix-shell` refuse to run for uid ≠ 1000 and having a
   greenboot/logind check terminate a `gnome` session owned by uid 1000. Is
   that worth the complexity for v0.1, given the kid never sees a greeter?
4. **Should the parent get a dconf profile at all?** Currently no — stock GNOME
   defaults. A small one could pin sensible things (dark style, a kidnix
   wallpaper, favourite-apps including the parent panel) without restricting
   anything. Taste call; ADR-0005 says "familiar", which argues for leaving it
   alone.
5. **`gnome-backgrounds` is 60% of this stage's cost.** Drop it and ship one
   kidnix wallpaper instead (~2 MB)? That trades 36 MiB for a less
   stock-feeling parent desktop and a small amount of art work.
6. **OARS ceiling (§4.3).** 3+ is the obvious default for 4–8 and it excludes
   Luanti and Stellarium. Confirm that is intended before the parent panel
   hard-codes it.
7. **Where does the parent panel live in the kid session?** ADR-0005 says the
   Grown-up gate launches it. That means the panel must be runnable as `parent`
   from inside a session owned by `kid` — a polkit/`pkexec` or D-Bus-activation
   design question that the shell spec should settle before the panel is built.

---

## 9. Files

| File | What it does |
|---|---|
| `build_files/35-parent-desktop.sh` | installs the stock GNOME payload, asserts the session exists, validates the AccountsService seed by running tmpfiles, validates the panel stub, prints the size delta |
| `build_files/36-fonts.sh` | installs Andika + Atkinson Hyperlegible, builds the system font cache, proves fontconfig resolves each family |
| `system_files/usr/share/kidnix/accountsservice-parent` | `Session=gnome` for the parent |
| `system_files/usr/lib/tmpfiles.d/kidnix-parent.conf` | seeds it into `/var/lib/AccountsService/users/parent` on first boot |
| `system_files/usr/bin/kidnix-parent-panel` | the placeholder panel |
| `system_files/usr/share/applications/kidnix-parent-panel.desktop` | its launcher |
| `tests/image/test_parent.sh` | 68 assertions |
| `docs/LICENSES.md` | the licensing ledger this milestone started |
