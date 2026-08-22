# The end-to-end scenario: driving kidnix with a fake mouse

> Implementer's report, 2026-08-22. Companion to `docs/design/shell-v0.1.md`,
> `docs/spikes/session-integration.md` and `tests/README.md`. Delivers item 8
> of `docs/plan/PRIORITIES.md`: the first test that uses the machine rather
> than inspecting it.

Everything kidnix could prove about itself before this ran stopped at the
kiosk's front door. `test-image` proves the files are right. `test-boot` proves
the session comes up. `test-boot-qcow2` proves a real disk boots and takes one
screenshot of whatever is on screen. None of them could tell you whether a
child can *click a tile*.

`just test-e2e` boots the same qcow2 and plays one child's session through it
from outside the VM. It clicks the avatar, rests the pointer on the Draw tile
until the shell speaks, opens Tux Paint, draws a stroke, quits, looks at My
Things, and then sits through the whole ending ritual on a session shortened to
ninety seconds. Twelve screenshots, seven steps, two minutes twenty.

**Nothing is installed in the guest.** The image under test is the image we
ship. Every interaction is QEMU's `input-send-event` and every assertion is
either a `screendump` or the guest's own journal read over ssh.

---

## 1. How it works

```
    host                                    guest (unmodified kidnix qcow2)
  ┌──────────────────┐                    ┌─────────────────────────────────┐
  │ pytest           │  input-send-event  │  usb-tablet ──► libinput ──►    │
  │  tests/e2e/      │ ─────────────────► │    mutter ──► kidnix-shell      │
  │   qmp.py         │                    │                                 │
  │   pixels.py      │  screendump        │  virtio-vga framebuffer         │
  │   vm.py          │ ◄───────────────── │                                 │
  │                  │                    │                                 │
  │                  │  ssh (root)        │  journalctl, pgrep, find        │
  │                  │ ◄─────────────────►│                                 │
  └──────────────────┘                    └─────────────────────────────────┘
        QMP unix socket                     -snapshot: the disk is never written
```

| file | what it is |
|---|---|
| `tests/e2e/qmp.py` | a ~200-line QMP client: connect, `screendump`, `input-send-event`, plus a small CLI for `just vm-qmp-*` |
| `tests/e2e/vm.py` | boots QEMU, injects the credentials, waits for the boot marker, wraps ssh and the shell's journal |
| `tests/e2e/pixels.py` | finds the shell's controls in a screenshot |
| `tests/e2e/conftest.py` | the session-scoped VM fixture, the shortened session policy, the contact sheet |
| `tests/e2e/test_scenario.py` | the seven steps |
| `tests/e2e/test_geometry.py` | unit tests for `pixels.py` against synthetic screenshots — no VM, milliseconds |

Standard library only, plus pytest. `just test-e2e` uses the system pytest
where there is one (Fedora has it) and `uv run --with pytest` where there is
not; nothing is installed into the repo. `just test-e2e-offline` runs the
geometry unit tests alone, with no VM and no disk image, in half a second --
which is what makes the harness itself cheap to keep honest.

---

## 2. The three problems worth writing down

### 2.1 Getting root into a disk image that has no credentials

`build-qcow2-rootless` applies no blueprint, so the disk has no `parent`
password and no authorised keys (`docs/BUILDING.md`). Assertions have to happen
*inside* the guest — "is there a `tuxpaint` process owned by `kid`" is not a
question pixels can answer — so the harness needs a way in that does not
involve modifying the image, because modifying it would mean testing a disk we
do not ship.

Three routes were tried. The third works.

**`ssh.authorized_keys.root` over `fw_cfg` — arrives, and does nothing.**
systemd 259 documents this exact credential, `systemd-tmpfiles-setup.service`
carries `ImportCredential=ssh.authorized_keys.root`, and the serial console
confirms PID 1 receives it:

```
systemd[1]: Received regular credentials: ssh.authorized_keys.root
systemd[1]: Acquired 1 regular credentials, 0 untrusted credentials.
```

sshd then refuses the key. The rule that should place it is in
`/usr/lib/tmpfiles.d/provision.conf`:

```
d- /root :0700 root :root -
d- /root/.ssh :0700 root :root -
f^ /root/.ssh/authorized_keys :0600 root :root - ssh.authorized_keys.root
```

…and on a bootc image `/root` is a **symlink to `var/roothome`**, so
systemd-tmpfiles will not treat it as a directory, `/root/.ssh` is never
created, and the `f^` line silently does nothing. This is a real
bootc-vs-systemd interaction and it is worth knowing about beyond this test:
anyone who expects `ssh.authorized_keys.root` to work on a bootc VM will lose
an hour to it. It fails *silently* — no warning on the console, no failed unit.

**`systemd.extra-unit.*` over `fw_cfg` — does not fit.** QEMU caps a `fw_cfg`
name at 55 characters. `opt/io.systemd.credentials/` is 27 of them, and
`systemd.extra-unit.kidnix-e2e.service` is 37:

```
qemu-system-x86_64: -fw_cfg name=opt/io.systemd.credentials/systemd.extra-unit.kidnix-e2e.service,file=...: name too long (max. 55 char)
```

**`systemd.extra-unit.*` over SMBIOS type 11 — works.** SMBIOS OEM strings have
no such cap, and `systemd-debug-generator` reads both
`systemd.extra-unit.<name>` and `systemd.unit-dropin.<unit>` as system
credentials. So the harness passes three base64 blobs:

```
-smbios type=11,value=io.systemd.credential.binary:systemd.extra-unit.kidnix-e2e.service=<unit>
-smbios type=11,value=io.systemd.credential.binary:systemd.unit-dropin.multi-user.target=<[Unit] Wants=kidnix-e2e.service>
-smbios type=11,value=io.systemd.credential.binary:kidnix-e2e-setup=<a shell script>
```

The drop-in is not optional: `[Install]` sections are not processed for
generated units, so without something pulling the unit into the transaction it
is generated and never started. The unit is `Before=sshd.service gdm.service`
and runs the script, which writes `/root/.ssh/authorized_keys` and
`/etc/kidnix/session.toml`. The keypair is generated per run into
`output/e2e/`, and the guest filesystem is a `-snapshot` overlay, so nothing
survives the test.

This is a generally useful hook, not a one-off: it is arbitrary root setup on
an unmodified bootc disk image, and `just vm-qmp` exposes it too.

### 2.2 Making the pointer land somewhere

q35's default mouse is a **relative** PS/2 device. `input-send-event` will
happily accept absolute coordinates for it and the guest will ignore them, so
the first run clicked whatever happened to be under the pointer's initial
position — which on both Who's here? and Home is the middle of the screen, and
therefore looked like it was working. Add an absolute pointer:

```
-device qemu-xhci,id=xhci -device usb-tablet,bus=xhci.0
```

QEMU normalises every absolute device onto `0..0x7fff` whatever the guest's
resolution is, so a guest pixel is `round(px * 0x7fff / (extent - 1))`.

The display has to be non-GL — `-device virtio-vga -display none`, exactly what
`tests/boot/boot_test.py` uses — or `screendump` has nothing to read.
`xres`/`yres` pin the EDID to 1280×800.

### 2.3 Knowing where the shell put things

**The plan was to compute the layout from `metrics.py`. It does not work.**

Two reasons, both instructive:

1. **The DPI is not 96.** QEMU's virtio-vga generates an EDID that reports a
   physical size, so the shell measures **102 dpi**, not the 96 dpi a
   from-first-principles calculation would assume. It logs what it decided,
   which is how we know:

   ```
   INFO kidnix_shell.app: display metrics: 1280x800 at 102 dpi (scale 1),
        fit 0.83, tile 141 px (35 mm), band 85 px, grid 4x3, needs 844x793
   ```

2. **`Gtk.Grid` columns are not homogeneous.** The metrics say every tile is
   141 px. The tiles as drawn are 209, 275, 185 and 203 px wide, because a
   column is as wide as its widest label and "Letters and Sounds" is a longer
   word than "Library". A computed 4-column grid puts the Draw tile 73 px to
   the left of where it is — which, on the first run, launched **TurboWarp**
   instead of Tux Paint.

So the test reads the pixels. `tests/e2e/pixels.py` exploits a design decision
in `theme.css`: every child-facing box has a **thin top border and a thick
bottom one** (`border: 2px` with `border-bottom-width: 6px` plus a 4 px shadow
for a tile; 3/8/5 for a ritual button) because the boxes are meant to sit *on*
the page rather than float in it. That asymmetry makes rows findable — a run of
border rows two to four deep opens a band, the next run six or more deep closes
it — and a glyph never covers enough of the width to be mistaken for either.
Columns are the vertical borders inside a band, which run its whole height
where a letter stroke does not.

Three refinements were needed, each of which is now a unit test in
`test_geometry.py`:

- **Rounded corners.** A ritual button is 136 px tall with a 32 px radius, so
  its left border exists for barely half the band. Sample only the middle 40%.
- **Coverage.** A full Home grid covers 65% of the width; a single Journal card
  covers 21%. One threshold cannot see both without also reading the "All done"
  tile's lavender fill as an edge, so `find_grid` tries 40%, then 18%, then 10%
  and takes the densest reading that finds anything.
- **Gaps are not boxes.** The 83 px of paper between "Finish this one" and "One
  last little thing" read as a third button until spans were required to have a
  horizontal border across the top of them.

The result needs no hard-coded coordinate anywhere in the shell's own UI, and
it re-derives the layout on every run, so a metrics change re-aims the clicks
instead of breaking them. The only fixed coordinates in the whole test are Tux
Paint's, which is a foreign application with its own fixed tool grid.

---

## 3. What it found

### 3.1 An activity tile that cannot work, and says nothing (real bug)

The first misaimed click landed on the TurboWarp tile, which turned out to be
more useful than a correct click:

```
INFO kidnix_shell.launcher: launched turbowarp as pid 2590: ['flatpak', 'run', 'org.turbowarp.TurboWarp']
error: app/org.turbowarp.TurboWarp/x86_64/master not installed
INFO kidnix_shell.launcher: turbowarp exited with code 1
INFO kidnix_shell.app: turbowarp finished (1)
INFO kidnix_shell.app: state in_activity -> home (activity_exited)
```

**Repro:** boot the qcow2, choose a profile, click TurboWarp. The screen
flickers to nothing and comes back to Home. From the child's side a button they
pressed did nothing at all, twice in a row if they try again.

`system_files/usr/share/kidnix/flatpaks.txt` plus
`kidnix-flatpaks-firstboot.timer` are supposed to install it, and on a machine
that has never had network egress they have not. Whatever the cause, the shell
currently has no answer for "the activity's binary is not there": it launches,
the process exits non-zero within a second, and the child is returned to Home
silently. AGENTS.md non-negotiable 6 says "Ask a grown-up instead of silent
denial", and this is a silent denial with extra steps.

Two things are worth separating:

- **The shell should notice.** An activity that exits non-zero in under a
  second or two never really started. `HomeScreen._activate` already knows how
  to say "Ask a grown-up for this one" when a tile is not allowed; the same
  voice fits "That one isn't ready yet. Ask a grown-up."
- **A tile should not exist for an activity that is not installed.**
  `activities.py` could check `exec[0]` resolves (and, for `source = "flatpak"`,
  that the ref is installed) and drop the manifest with a warning, the way it
  drops an invalid one.

Not fixed here: `shell/kidnix_shell/` is not this task's to change beyond the
one log line in §4.

### 3.2 "Finish this one" does nothing (real bug)

`app._advance_ritual` re-presents the ending offer on **every tick** while the
session is inside the ending-offer window and the child is on Home, In-activity
or Journal. `dismiss_offer` fires `DISMISS_OFFER`, which returns the child to
Home — and one second later the next tick puts the offer straight back:

```
INFO kidnix_shell.app: state ending_offer -> home (dismiss_offer)
INFO kidnix_shell.app: state home -> ending_offer (ending_offer_due)
```

**Repro:** shorten the session (`/etc/kidnix/session.toml`, `length_minutes =
1.5`, `ending_offer_minutes = 1`), restart `kidnix-shell.service`, choose a
profile, wait 30 s for the offer, click "Finish this one". You are back on Home
for about a second and then back on the offer, and this repeats for the whole
ending-offer window — four minutes with the shipped numbers.

For a five-year-old this is the worst possible failure mode of a ritual screen:
they answered the question, and the machine asked it again, and again. It also
makes "One last little thing" indistinguishable from "Finish this one", which
throws away the one bit of agency S5 exists to offer.

**Fix shape:** remember that the offer was answered for this session — a flag
on the window cleared by `Session.start`, checked in `_advance_ritual` before
`_present_ending_offer`. The state machine should not need changing;
`_offer_return` already remembers where to go back to.

The scenario test **reports** this rather than asserting it, so that the day the
guard lands the test still passes and simply prints "stayed on Home" instead of
"the offer came straight back".

### 3.3 Everything else worked, and it is worth saying so

- **Tux Paint is genuinely well integrated.** It launches fullscreen at the
  panel's own 1280×800, a mouse press-move-release over QMP draws a real stroke,
  the Quit tool asks "Do you really want to quit?" once (and only once — the
  `autosave=yes` in `/etc/tuxpaint/tuxpaint.conf` means nobody is asked whether
  to save), and on quit the drawing lands in `~/.tuxpaint/saved/` where the
  shell's watcher finds it. Within a few seconds there is an
  `entry.json` under
  `~kid/.local/share/kidnix/journal/2026/08/22/tuxpaint-113039-405c4b/`, and My
  Things shows a card with the drawing as its thumbnail. The whole
  make-something-and-keep-it loop works, unattended, from a synthetic mouse.
- **The read-aloud dwell works.** Resting the pointer on a tile for 1.2 s
  repaints 86% of it — the shell's speaking highlight — and
  `speech-dispatcher.service` is running in the child's session.
- **The ending ritual runs itself.** `ending_offer` → `put_away` → `goodbye` →
  `sleeping`, each transition logged, each screen screenshotted, with no help
  beyond one click on "Finish this one" and one on "Goodnight".
- **No GL, no problem.** Under `virtio-vga` with no GL the session logs
  `MESA: error: ZINK: failed to choose pdev` and four `libEGL` warnings, then
  renders the whole shell in software at a perfectly usable speed. Worth
  knowing that the shell does not need a working GPU.

---

## 4. One line added to the shell

`SpeechManager.speak` now logs the utterance at INFO:

```python
log.info("speaking: %s", text)
```

That is the only change to `shell/` in this task. The intent was for step 3 to
assert *what the shell said* rather than *that a tile repainted* — a much
sharper assertion, and the one the task asked for. It is not yet usable,
because the image the test runs against was built before the line existed and
this task does not rebuild it. Once `just build && just build-qcow2-rootless`
have run, step 3 can be tightened to:

```python
scenario.expect_log("speaking: Tux Paint. Draw a picture.")
```

which would also make the *coordinate* check exact: the shell would be telling
us which tile the pointer is on, before we click it.

The line is safe to keep: it is the shell's own UI text, never anything the
child typed or made, and it goes to the local journal, which the parent already
owns. `state ... -> ...` transitions were already logged at INFO
(`app.py`), so steps 2, 4, 5 and 6 needed nothing.

---

## 5. Assumptions, and where they are recorded

| assumption | why it is safe | where it would break |
|---|---|---|
| the panel is 1280×800 | pinned by `-device virtio-vga,xres=1280,yres=800` | a different resolution re-derives the grid from pixels anyway; only Tux Paint's coordinates are fixed |
| Tux Paint's Quit tool is at (71, 400) and "Yes, I'm done!" at (446, 346) | Tux Paint lays its tool column out in a fixed grid at a given resolution | a Tux Paint release that moves its furniture; the failure is loud (`tuxpaint` stays in the process table) |
| the Draw tile is row 1, column 2 | activities sort by `(category, name)`; asserted, not assumed — `launched tuxpaint` in the journal is what the step actually checks | adding a "learn" or "make" activity before Tux Paint; the failure names the activity that launched instead |
| the profile avatar is the one big dark shape on S1 | it is a 194 px black smiley on cream; the title is text | a profile with a pale avatar |
| the bedtime window can be moved | `/etc/kidnix/session.toml` is root-owned and the harness owns root | — |

That last one matters more than it looks. The shipped bedtime is 19:00–07:00,
so a scenario test run in the evening would be refused a session and fail for a
reason with nothing to do with the code. `conftest.session_policy` pins the
bedtime window to one minute, six hours from now, wherever "now" is.

---

## 6. Cost, and whether CI should pay it

| | seconds |
|---|---|
| boot to `KIDNIX_BOOT_OK` | 16–20 |
| root ssh answers | < 1 |
| steps 1–5 (through My Things) | ~35 |
| step 6 (the 93-second ritual, plus a shell restart) | ~100 |
| **total (19 tests, measured)** | **140 s** |

Well under the six-minute target, and the dominant term is the ritual, which is
a wall clock we chose. It could be halved again by shortening
the session further; 90 seconds was kept because it exercises a plausible
ending rather than a degenerate one.

`.github/workflows/e2e.yml` splits this in two:

- **`harness`** runs on every push and PR. No VM, no KVM: byte-compile,
  run `just test-e2e-offline` (the `pixels.py` unit tests against synthetic
  screenshots), and prove the scenario *skips* cleanly when there is no disk
  image. Seconds.
- **`scenario`** is `workflow_dispatch` and nightly. It needs `just build`
  (~10 min) and `just build-qcow2-rootless` (~5 min) before it can start, so
  per-PR it would cost ~20 minutes of runner to re-prove the boot that
  `just test-boot` already gates on in 30 seconds. It reuses boot-test.yml's
  runner setup (KVM check, disk cleanup, virtiofsd 1.14, the `/dev/kvm` chmod)
  and adds `ovmf`, because a bootc disk is UEFI-only.

`boot-test.yml` is unchanged.

---

## 7. Open questions

1. **Assert the voice, not the highlight.** §4: one image rebuild away.
2. **Is `usb-tablet` enough for touch?** The scenario drives a mouse. kidnix is
   meant to work on a touchscreen too, and QEMU can present one
   (`-device virtio-tablet-pci` with multitouch, or `input-send-event` with
   `mtt` events). Nobody has checked that the shell's dwell-to-speak makes
   sense under a finger, which is the interaction most likely to be wrong.
3. **Should the scenario assert audio?** "speech-dispatcher ran" is weaker than
   "a sound came out". The TTS spike (`docs/spikes/tts.md`) may give a better
   hook; `/usr/libexec/kidnix-audio-cap` exists and was not used here.
4. **Flakiness under CI's slower clock.** Every wait here polls with a timeout
   rather than sleeping a fixed time, except three `time.sleep` calls that let
   an animation settle before a screenshot. On a nested-virtualisation runner
   those may need to grow. The nightly job will say.
