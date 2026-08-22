# Session integration: the real shell under gnome-session

> Implementer's report, 2026-08-22. Companion to `docs/design/shell-v0.1.md`
> and `docs/spikes/lockdown.md`. It closes the "Known: no portals in the kid
> session" section of `docs/BUILDING.md` and open question 2 of the lockdown
> spike ("`gnome-session` vs the supervisor wrapper").

Two things landed together, because neither is testable without the other:

1. the kid session is now a real **gnome-session** session, so
   `graphical-session.target` activates and the portals start;
2. the **real activity shell** (`shell/`) is installed into the image and is
   what the child sees.

Everything below was verified in a booted VM. Where something is not verified,
it says so.

---

## 1. What the session used to be, and why it was wrong

```
GDM -> kidnix-shell.desktop -> /usr/bin/kidnix-shell
                                 exec gnome-kiosk --wayland --display-server \
                                      -- kidnix-app-supervisor gnome-text-editor
```

One process tree, no session manager. It booted, and the boot test was green,
and it was still wrong in a way that would have bitten the first activity that
wanted a file chooser:

- `xdg-desktop-portal.service` and both backends carry
  `Requisite=graphical-session.target`. `Requisite=` does not *start* anything;
  it fails immediately unless the target is **already active**.
- `graphical-session.target` is raised by `gnome-session.target`
  (`BindsTo=graphical-session.target`). Nothing else on the image raises it.
- gnome-kiosk's own units say the same thing from the other side:
  `org.gnome.Kiosk.target` is `Requisite=gnome-session-initialized.target`, so
  it cannot even be started outside a gnome-session — which is why v0.1 had to
  exec the binary directly and got no unit wiring at all.

So `journalctl -b -p warning` was full of *"Dependency failed for
xdg-desktop-portal.service"*, and the crash-proofing promise (AGENTS.md
non-negotiable 8) rested on a bash `while true` loop.

## 2. What it is now

```
GDM
 └─ /usr/share/wayland-sessions/kidnix-shell.desktop   (Exec=/usr/bin/kidnix-shell)
     └─ /usr/bin/kidnix-shell            environment only: DCONF_PROFILE=kid
         └─ gnome-session --session=kidnix
             └─ gnome-session@kidnix.target
                 ├─ Requires org.gnome.Kiosk.target  -> gnome-kiosk (compositor)
                 ├─ Wants    kidnix-shell.service    -> /usr/bin/kidnix-shell-app
                 └─ Wants    org.gnome.SettingsDaemon.{A11ySettings,MediaKeys,Sound}
```

and, because `gnome-session@.target` requires `gnome-session-initialized.target`
which reaches `gnome-session.target` which `BindsTo=graphical-session.target`,
**`graphical-session.target` is active** and the portals start normally.

### Files

| File | What it is |
|---|---|
| `system_files/usr/bin/kidnix-shell` | The GDM entry point. Rewritten: it now only sets up the environment and `exec`s `gnome-session --session=kidnix`. |
| `system_files/usr/share/gnome-session/sessions/kidnix.session` | Makes `--session=kidnix` resolvable. |
| `system_files/usr/lib/systemd/user/gnome-session@kidnix.target.d/session.conf` | The component list: compositor, shell, three gsd targets. |
| `system_files/usr/lib/systemd/user/kidnix-shell.service` | The shell, `Restart=always`, `RestartSec=1`, `StartLimitIntervalSec=0`. |
| `system_files/etc/kidnix/session.toml` | Session policy (25 min, 60 min/day, ending offer T−6, put away T−2, bedtime 19:00–07:00). |
| `build_files/60-shell.sh` | Installs `shell/` into the image and asserts all of the above. |
| `Containerfile` | `COPY shell/ /tmp/shell/` (+ `.containerignore` to keep the venv and caches out of the build context). |
| `tests/image/test_shell.sh` | 66 static assertions. |
| `tests/boot/bcvk_boot_test.py` | 15 new boot assertions (25 total). |

### Why the shape is exactly gnome-kiosk's

Fedora ships `gnome-kiosk-script-session`, which is upstream's own worked
example. Its files were read out of the package and copied structurally:

```
gnome-kiosk-script.session                          -> kidnix.session
gnome-session@gnome-kiosk-script.target.d/session.conf -> gnome-session@kidnix.target.d/session.conf
org.gnome.Kiosk.Script.service                      -> kidnix-shell.service
gnome-kiosk-script-wayland.desktop                  -> kidnix-shell.desktop
```

Two deliberate differences from that reference:

- **No `RequiredComponents=`.** Since GNOME 40 gnome-session is
  systemd-managed; the component list lives in the `gnome-session@<name>.target`
  drop-in. Both reference `.session` files on this image (`gnome.session` and
  `gnome-kiosk-script.session`) carry a `Name` and nothing else. We match them.
  Consequently there is also no `org.kidnix.Shell.desktop` autostart file —
  it would be dead weight.
- **`Wants=kidnix-shell.service`, not `Requires=`.** Upstream `Requires=` the
  script service; we do not, because a shell that cannot start must leave the
  child with a live compositor and a unit that keeps retrying, not a session
  that tears itself down and bounces them through GDM.

### `DCONF_PROFILE` still reaches everything

The wrapper `export`s it, then pushes it into the per-user systemd manager and
the D-Bus activation environment before gnome-session starts anything. It is
deliberately *not* an `/usr/lib/environment.d/` drop-in: that applies to every
user's manager on the machine, and the parent must keep stock GNOME defaults
(ADR-0005). `kidnix-shell.service` also sets `Environment=DCONF_PROFILE=kid` as
a belt to that pair of braces.

Verified in the VM — this also closes item 2 of the lockdown spike's
"NOT verified" list, which asked for exactly this measurement:

```
DCONF_PROFILE from /proc/<gnome-kiosk pid>/environ : kid
DCONF_PROFILE from /proc/<kidnix-shell-app pid>/environ : kid
```

## 3. The shell install

`shell/` is pure Python with **no PyPI runtime dependencies** — PyGObject,
GTK4, libadwaita and `speechd` all come from RPMs. So `60-shell.sh` copies the
package into `/usr/lib/python3.14/site-packages`, writes the `.dist-info`
metadata a wheel install would have left, byte-compiles it with
`--invalidation-mode unchecked-hash`, and generates the console script.

**Why not pip:** the build backend is hatchling, so `pip install` would need
`python3-pip` *and* `python3-hatchling` installed into the image and then
removed again — two extra packages, a `dnf remove` that can cascade, and a
build that reaches PyPI — to produce a tree byte-identical to `cp -a`. Every
claim the copy makes is asserted at the end of `60-shell.sh` (imports from
`/usr/lib`, `--version` runs, GTK4/Adw import, `speechd` imports, manifests
validate, assets present), so the shortcut cannot rot silently.

**Byte-compiling matters more than it looks.** `/usr` is read-only at runtime,
so without shipped `.pyc` the shell re-parses itself on every start and can
never cache the result.

**Two names, on purpose.** `pyproject.toml` declares the console script as
`kidnix-shell`, but `/usr/bin/kidnix-shell` is the session wrapper GDM execs.
The application is therefore installed as **`/usr/bin/kidnix-shell-app`**.

`/etc/kidnix/session.toml` ships the policy (in `/etc` so a parent can edit it
and bootc's 3-way merge preserves the edit). `parent.toml` is deliberately
**not** shipped: `settings.Paths.parent_config` prefers `/etc/kidnix/parent.toml`
when it exists, and the child's grown-up sheet has to be able to *write* the
file to change the PIN. See open questions.

## 4. Verified in the VM

`just tag=shell test-boot`, 25/25 checks, ~35 s. Three consecutive runs.

```
  PASS  kid's session Type=wayland (got 'wayland')
  PASS  gnome-kiosk runs as kid (got 'kid')
  PASS  kid's graphical-session.target is active (got 'active')
  PASS  kid's gnome-session@kidnix.target is active (got 'active')
  PASS  kid's org.gnome.Kiosk.target is active (got 'active')
  PASS  kid's xdg-desktop-portal.service is active (got 'active')
  PASS  kid's xdg-desktop-portal-gnome.service is active (got 'active')
  PASS  gnome-session is running the kidnix session
  PASS  DCONF_PROFILE=kid reached gnome-kiosk (got 'kid')
  PASS  DCONF_PROFILE=kid reached the shell (got 'kid')
  PASS  kidnix-shell.service is active (got 'active')
  PASS  the activity shell is running
  PASS  the activity shell runs as kid (got 'kid')
  PASS  the shell comes back within 10s of being killed (took 1.0s, pid 2024 -> 2558)
  PASS  kidnix-shell.service is active again after the kill (got 'active')
  PASS  nft table inet kidnix_egress is loaded (got 'loaded')
  PASS  kid cannot reach the network (curl exited 7; root got out fine)
  PASS  no unexpected failed units
```

The target tree, read out of kid's own manager:

```
# systemctl --user -M kid@ list-units --type=target --state=active
gnome-session-initialized.target  active  GNOME Session is initialized
gnome-session-manager.target      active  GNOME Session Manager is ready
gnome-session-pre.target          active  Tasks to be run before GNOME Session starts
gnome-session.target              active  GNOME Session
gnome-session@kidnix.target       active  GNOME Session (session: kidnix)
graphical-session-pre.target      active  Session services which should run early ...
graphical-session.target          active  Current graphical user session
org.gnome.Kiosk.target            active  GNOME Kiosk
```

and the warning that started all this is gone:

```
# journalctl -b _UID=1000 | grep -c "Dependency failed for xdg-desktop-portal"
0
```

The shell's own first words in the journal:

```
INFO kidnix_shell.settings: no parent config at /var/home/kid/.config/kidnix/parent.toml; using defaults (PIN 1234)
INFO kidnix_shell.app: display metrics: 102 dpi, tile 170 px (42 mm), band 102 px
INFO kidnix_shell.app: read-aloud backend: speechd
INFO kidnix_shell.journal: watching /var/home/kid/.tuxpaint/saved for new work
INFO kidnix_shell.journal: watching /var/home/kid/Pictures/TuxPaint for new work
```

**Egress**, which `docs/spikes/lockdown.md` §3 called "the single most important
boot-test assertion to add", is now asserted differentially: `curl -m5
http://1.1.1.1/` exits **7** as `kid` and **0** as root, with
`nft list table inet kidnix_egress` loaded. Item 3 of that list is closed.

### A real screenshot

`just build-qcow2-rootless && just test-boot-qcow2` — a full disk boot with
bootloader, composefs and first-boot units — screenshots the framebuffer over
QMP. `docs/design/screenshots/boot-home.png` is that frame: the S1 "Who's here?"
screen with the band, the sun, and the single "Me" profile, in Andika. The
child's computer boots to the real shell in about 17 s.

## 5. Two bugs found by running it for real

### 5.1 speech-dispatcher made every crash an 11-second black screen

`python3-speechd` autospawns `speech-dispatcher --spawn` when nothing is
listening on `$XDG_RUNTIME_DIR/speech-dispatcher/speechd.sock`. The spawned
daemon then lives inside `kidnix-shell.service`'s control group **and does not
answer SIGTERM**, so every restart of the shell sat in `stop-sigterm` for the
full `TimeoutStopSec` before systemd escalated:

```
systemd[1061]: kidnix-shell.service: Main process exited, code=killed, status=9/KILL
systemd[1061]: kidnix-shell.service: State 'stop-sigterm' timed out. Aborting.
systemd[1061]: kidnix-shell.service: Killing process 2104 (speech-dispatch) with signal SIGABRT.
systemd[1061]: kidnix-shell.service: Scheduled restart job, restart counter is at 1.
```

Measured: **11.4 s** of empty compositor after a crash. A five-year-old notices
eleven seconds.

Fix: `Wants=speech-dispatcher.socket` + `After=speech-dispatcher.socket` on
`kidnix-shell.service`. Fedora's `speech-dispatcher` ships a user socket unit
listening on exactly the path `python3-speechd` probes, so the client connects
instead of autospawning and the daemon lands in
`app.slice/speech-dispatcher.service` — its own cgroup. Re-measured: **1.3 s**,
and the shell still selects the `speechd` backend. `TimeoutStopSec` stays at 10 s
so the shell keeps its five-second SIGTERM grace for a running activity
(spec §7a).

### 5.2 `pgrep -f` in a probe matches the probe

Not a product bug but worth recording, because it cost an hour: the boot
probe's `pgrep -f '/usr/bin/kidnix-shell-app'` also matched **the probe script
itself** — the script text is the command line of the shell running it — so the
"kill the shell and watch it come back" step killed the probe and the harness
reported "the guest probe did not produce a result block" with no other clue.
The probe now asks systemd (`show kidnix-shell.service -p MainPID`) and scopes
its one remaining `pgrep` with `-u kid`.

## 6. Not verified

1. **The shell being *usable*.** Nobody has clicked anything. The screenshot
   proves it renders; it does not prove a tile launches Tux Paint, that the
   Journal imports a drawing, or that the ending ritual fires. That needs a
   graphical VM session and, really, a child.
2. **Read-aloud making a sound.** `speechd` is the selected backend and
   `sd_espeak-ng` is running, but there is no sound card in either VM. Whether
   a child hears anything is untested.
3. **The band over an activity.** Unchanged and still the open gap in
   `docs/design/shell-v0.1.md` §8.
4. **Portals doing portal things.** They are *active*; no activity has opened a
   file chooser through one.
5. **greenboot under bcvk.** `greenboot-healthcheck.service` and
   `greenboot-set-rollback-trigger.service` fail in `bcvk ephemeral` with
   `Failed to check boot mount state: Failed to read mount info` — there is no
   `/boot` mount when the VM roots on virtiofs. The health *checks* themselves
   all pass (the journal shows all three `required.d` scripts succeeding). Both
   units are now allow-listed in the boot harness with that reason, exactly like
   `bootloader-update.service`. **greenboot can only be judged by
   `just test-boot-qcow2`, and has not been.**
6. **Multiple monitors, real GPUs, HiDPI.** One 1280×800 virtio-vga panel.

## 7. Open questions for the thinker

1. **The shell's window is bigger than a 1280×800 screen.** In the qcow2
   screenshot the band's buttons are clipped at the top and the Grown-up tile
   is clipped at the bottom-right — the content is roughly 6% wider and taller
   than the display, which is exactly the 102 dpi / 96 dpi ratio the shell
   logs. Physical-size scaling is a §7a ruling, so this is a design call, not an
   obvious bug: either the layout needs a "shrink to fit the monitor" floor, or
   the band/tile minima need to be advisory. It is the most visible problem in
   the image today.
2. **`parent.toml` has nowhere to live.** `settings.Paths.parent_config` prefers
   `/etc/kidnix/parent.toml` if present, but the grown-up sheet must be able to
   *write* it to change the PIN, and `kid` cannot write `/etc`. Today the file
   falls back to `~/.config/kidnix/parent.toml`, which the child owns — so the
   PIN, the allow-list and the profiles are child-writable in principle. Needs a
   parent-owned, group-readable directory under `/var/lib/kidnix` and a change
   in `settings.py`, or a small setuid/polkit-mediated writer. **Flagging as the
   one security-shaped gap this milestone introduces.**
3. **Bedtime is on by default (19:00–07:00) and there is no parent panel.** With
   the shipped `session.toml` a child cannot start a session after 19:00 without
   the grown-up PIN. That is the specified policy, and it is also the first
   thing a parent will want to change on a machine with no UI to change it.
4. **The "All done" Home tile** from the §7a rulings is **not implemented** in
   `shell/` — nothing to ship yet. Not attempted here (shell code is out of this
   task's scope).
5. **Delete `/usr/libexec/kidnix-app-supervisor`.** Nothing in the session path
   references it any more. It is still on the image and still tested, because
   `greenboot/check/required.d/30-kidnix-session.sh` requires it to exist.
   Removing it is a three-line change across that check, `test_lockdown.sh` and
   `system_files/` — deliberately left for the thinker so this diff does not
   quietly delete a greenboot dependency.
6. **`gnome-text-editor` is gone from the image.** It was only ever the kiosk
   placeholder. If the parent's stock GNOME session wants a text editor, it
   should ask for it in `35-parent-desktop.sh`, not inherit it from the child's
   scaffolding.
7. **The three gsd components** in the session drop-in (a11y, media keys, sound)
   are a judgement call. Everything else `gnome-settings-daemon` offers is
   either noise a five-year-old must never see (print notifications, disk-full
   warnings, donation reminders) or surface area we do not want. Worth a look.
8. **`X-GDM-SessionRegisters=false`** is kept from v0.1 and matches upstream's
   kiosk-script session, even though gnome-session *can* register. It works;
   nobody has tested what changes if it is `true`.
