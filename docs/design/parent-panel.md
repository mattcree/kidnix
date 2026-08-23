# The parent panel, v0

*Status: built, 2026-08-23. Source: `parent-panel/` (package
`kidnix_parent_panel`). Screenshots: `docs/design/screenshots/parent-panel-*.png`.*

---

## 1. Why it exists, in the reviewers' own words

Four invented parents were shown the same material and all four stopped at the
same wall (`docs/design/reviews/2026-08-23-parent-panel.md`):

> **Everyone stopped at the same wall: there is no way in.** All four asked some
> form of "and then what do I press?", and all four found the answer is a TOML
> file. The gap between the care in the child's experience and the total absence
> of a parent's experience is the single loudest note in this review.

Their top five asks, in their order, are this app's six tabs:

| Ask | Where it landed |
|---|---|
| 1. A parent panel, even a bad one — children, time, activities, and a PIN | the whole app; **Children**, **Time**, **Activities**, PIN on **Updates & safety** |
| 2. Two children on one machine, without a settings file | **Children** |
| 3. A "keep it the same" switch, and a quiet one | **Activities** (first control) and **Sound & calm** |
| 4. A way out for the child's work | **Their things** |
| 5. An install-and-update story | **Updates & safety** |

And the sixth tab, **Family**, is SYNTHESIS G1's "family recipients" — data
only, and it says so.

The panel is also constrained by what the parents explicitly did **not** ask
for (review §5): *"a parent surveillance dashboard."* There is no time-on-device
chart, no session history, no ranking of activities. The tripwire in
`tests/image/test_parent_panel.sh` is the absence of the *thing*, not of the
word — the panel says "no analytics" in its own honest page — so it asserts the
panel never names the child's own counters (`usage.toml`, `progress.toml`,
`sessions_completed`, `journal_root`), which is where such a chart's data would
have to come from.

## 2. Where it runs, and what it looks like

ADR-0005 gives the parent a **stock GNOME session** on the same login screen,
so this is an ordinary libadwaita preferences app on that session: default font
sizes, default row heights, real numbers in real spin buttons, GNOME's own
dialogue and file-chooser conventions. **Adult typography throughout.** None of
the child's shell applies here — no 18 pt floor, no 20 mm targets, no
hover-to-speak, no read-aloud. The only thing it borrows from the child's side
is the identity colour pairs and shape badges, and only where a row is about a
particular child.

`Applications → Parent Panel` (`kidnix-parent-panel.desktop`,
`Terminal=false`). It is designed to be launchable later from the grown-up
sheet inside the child's session as well; nothing in it assumes it is the only
window on the machine, and nothing in it needs a privilege to *open*.

Six tabs in an `Adw.ViewStack`, one **Apply** in the header bar, one banner
under it. Edits accumulate and are written in a single act, because every save
is a polkit prompt and a machine that asked for a password on every nudged spin
button is a machine nobody finishes setting up. The banner's sentence is the
honest one:

> Saved. It takes effect at your child's next session.

The shell reads `parent.toml` and `session.toml` when a session **starts**, so
a change made mid-sitting reaches the child at the next one. Saying anything
else would be the panel's first broken promise.

## 3. The architecture, and why it is in layers

```
        parent's GNOME session                       root
  ┌──────────────────────────────┐        ┌───────────────────────────┐
  │  kidnix-parent-panel          │        │  kidnix-config apply      │
  │   ui/*      GTK, six tabs     │        │   helper.py               │
  │   state.py  one PanelModel    │        │    · is the caller wheel? │
  │   model.py  pure dataclasses  │        │    · validate AGAIN       │
  │   validate.py  pure rules     │ pkexec │    · render TOML          │
  │   config_io.py renders TOML   │ ─────► │    · PARSE IT BACK with   │
  │   catalogue.py reads manifests│  JSON  │      kidnix_shell's own   │
  │   system.py  the only fork    │ (stdin)│      ParentConfig.load    │
  └──────────────────────────────┘        │    · write atomically     │
                                          └───────────────────────────┘
                                                       │
                                          /etc/kidnix/{parent,session}.toml
                                          /etc/kidnix/tts.env
                                                       │
                                                child's shell
```

Everything except `ui/` is pure and has no `gi` import, which is what lets 167
tests run with no display and lets the root helper import the same validator
the panel used. `system.py` is the only module that forks, and the runner is an
argument, so nothing in `parent-panel/tests` starts a process.

### 3.1 Why the panel does not write the files itself

`/etc/kidnix/parent.toml` and `/etc/kidnix/session.toml` are root-owned because
the shell runs as the child, and a child-writable session length is not a
session length. The panel runs as the **parent**, who is in `wheel` and is not
root. So:

* `/usr/bin/kidnix-config` — a thin bash wrapper, the same shape as
  `kidnix-export` and `kidnix-set-pin`, which re-execs itself through `pkexec`
  and hands over to `python3 -m kidnix_parent_panel.helper`.
* `org.kidnix.parent-config` — a **new** polkit action,
  `allow_active=auth_admin_keep`, `allow_inactive=no`, matched to that path.
* `40-kidnix-kid.rules` is **unchanged**. Its `"org.kidnix."` prefix denial
  already covers this action, and it must stay covered: the one carve-out in
  that file (`org.kidnix.set-pin`) exists because a fresh machine's first PIN
  has to be settable from the only session the machine shows, and none of that
  argument applies here. A machine with no settings yet has working defaults;
  there is no screen a child is trapped on. Granting a five-year-old this
  action would let them lengthen their own session, empty their own bedtime and
  tick every activity back on. Both `62-parent-panel.sh` and
  `test_parent_panel.sh` fail if that id ever appears in the rules file.

### 3.2 What the root half refuses

The authorisation is not the authority. `kidnix-config` re-decides everything:

1. **Who asked** — root or `wheel`, from `PKEXEC_UID`, then `SUDO_UID`, then
   the real uid. `kid` is named and refused.
2. **Is it valid** — the same `validate.py` the panel ran, re-run as root on
   the payload it is about to write. A privileged writer that trusts its caller
   is a permission bug with a JSON parser.
3. **Can the shell read it back** — the rendered TOML is parsed with
   `kidnix_shell.settings.ParentConfig.load` and `kidnix_shell.session.load_policy`
   in a scratch directory *before* anything in `/etc` is replaced, and the
   children, the sitting length, the budget and the captions flag must come
   back as the values that went in. A rendering bug that dropped a profile
   would otherwise reach `/etc` and take a child's face with it.
4. **Never the PIN** — `pin_salt` and `pin_hash` are read off the file that
   exists now and put back verbatim; a payload carrying different ones is
   ignored. Changing a PIN is `kidnix-set-pin`'s job, because that is the
   command that demands the current PIN and rate-limits guesses.

Writes are atomic: temporary file in the same directory, `fsync`, `chmod 0644`,
`os.replace`, `fsync` on the directory. A power cut leaves the old file or the
new one and never half a PIN and a machine nobody can get into.

Exit codes, which the panel reads: `0` written (each file named on stdout as
`wrote <path>`), `1` refused, `3` invalid, `64` usage; `126`/`127` come from
`pkexec` itself and get their own sentence, because "you dismissed the password
box" and "that setting is wrong" have different fixes.

### 3.3 Why `parent.toml` is re-rendered whole

`tts.env` is edited **in place** — one line, `KIDNIX_PIPER_MODEL=`, the way
`kidnix_shell.settings.rewrite_pin` edits the PIN — so its eighty lines of
measurements survive byte for byte.

`parent.toml` cannot be treated that way. The panel changes *structure*, not
just values: profiles appear and disappear, and tables move between
`[[profiles]]` and `[[retired_profiles]]`. An in-place editor for that is a
TOML round-tripper, which is a dependency this image does not have and a class
of bug nobody wants between a parent and their child's PIN.

So the file is rendered whole, and its header points at
`/usr/share/kidnix/parent.toml` — the byte-identical shipped copy, still in the
image, still carrying every word of the reasoning (why 450 ms, why "empty means
all", what a badge is for), and **replaced by every upgrade** so it never goes
stale. Nothing is lost; the explanations move one path along and the header
says where. Two things are carried across a re-render even though the panel
does not edit them: the PIN hash/salt, and the `[[next_after]]` blocks (a
household may well have replaced Coco's eight with their own — `parent.toml`
invites exactly that).

`tests/test_config_io.py` asserts the renderer is a **fixed point**: render,
read, render again is byte-identical. A renderer that was not would slowly
rewrite a parent's machine on every save.

### 3.4 Nothing privileged runs on the main loop

Every privileged thing the panel does is a subprocess behind `pkexec`, and
`pkexec` blocks until a human has typed a password into an agent that is a
*different process*. Calling that from a GTK signal handler freezes the window
for as long as the parent takes to find their password — and `bootc upgrade`
takes minutes, during which a frozen window is indistinguishable from a crash.
A parent who force-quits a panel mid-`bootc` is the failure mode
`ui/tasks.py` exists to prevent.

So the work happens on a thread, the answer comes back through
`GLib.idle_add`, and the control that started it is insensitive in between.
`synchronous=True` runs it inline instead, for the tests and for
`--screenshot`, where there is no main loop for a thread's answer to return to.

Related, and the reason the first wipe confirmation lists what goes **in
words** rather than by running the helper: producing a live listing would put a
polkit prompt in front of somebody who has pressed the first of two
confirmations, and teaching a parent to type their password at a dialogue
headed "delete everything" is exactly the habit not to teach.

## 4. The tabs

### Children

One row per child: the colour pair drawn with the shape badge over it, the
name, the age band, and two arrows for the order the faces appear in on "Who's
here?". Add, rename, reorder, remove. Colour **and** shape together, never
colour alone — two of the four shipped palettes used to simulate to the same
colour under deuteranopia.

**Remove is not delete, and the row says so.** Removing a child moves their
table to `[[retired_profiles]]`. The shell only ever reads `profiles`, so the
face disappears from "Who's here?" at the next session while the id — and
therefore `~/.local/share/kidnix/profiles/<id>/journal` — stays written down
where a parent can restore it. This needs **no shell change at all**. The only
thing on the machine that deletes a child's work is `kidnix-wipe`, on Their
things, behind two confirmations and a typed word.

Renaming does **not** re-derive the id. The id is the Journal's directory name;
a rename that moved it would orphan every drawing.

### Time

*One sitting* (length, and the floor, with the floor shown rather than hidden —
it is what makes "+10 on a rainy Saturday" safe); *a whole day* (the budget,
with the arithmetic printed underneath: "60 minutes is 2 full 25-minute
sittings and 10 minutes over, which is less than the 5-minute floor, so it is
refused rather than handed out as a stub of a session"); *bedtime*; *when it may
be used at all* (`[[windows]]`, §7.1); and *how the ending goes*, whose two
numbers are labelled as the **ceilings** they are.

### Activities

**"Keep the grid the same"** is the first control on the tab and is on by
default. It is the inverse of the shell's key — the switch ON means
`show_everything = true`, i.e. no progressive disclosure — and it is the right
way round for the person reading it: a parent is choosing predictability, not
choosing a research feature. Turning it *off* is what reveals `initial_tiles`
and `reveal_every_sessions`.

Under it, one switch per activity showing **the picture the child actually
sees** (resolved the same way the shell resolves it: manifest path, then one of
the shell's own drawings, then the category fallback) and the manifest's own
`goal` line, which is the schema's one sentence written for a grown-up. Shelf
children hang under their shelf in an expander, grouped by their own headings,
so removing one of GCompris's eighteen is possible without opening anything.
An activity outside the child's age band is shown greyed with the band named,
so a parent can see *why* TuxMath is not on their four-year-old's list.

Unticking the last box does not empty the screen: an empty list means
"everything", exactly as the shell reads it, and the copy says so.

### Sound & calm

Calm mode; captions (on by default, with the reason); mute; volume; the voice;
the reading speed. The panel **refuses to save** a machine with both the sound
and the captions off — muted-with-captions is quiet, muted without them is
broken, and a pre-reader is then told nothing at all.

### Their things

Copy everything to a folder (`kidnix-export`), open that folder in Files,
print a picture (`xdg-open` → the image viewer's own Print), and delete
everything (`kidnix-wipe`, two confirmations, the second one typing `DELETE` —
the same word the helper itself asks for).

Everything starts with an export because `/var/home/kid` is `0700 kid:kid` so
that nothing on the machine can read a child's work, *including the parent's
own account*. Rather than loosen the child's home, the parent borrows root for
the length of one copy and gets a file they own. That is one extra step and it
is the step that keeps the home private.

### Family

Names and photographs of people a drawing could be sent to. Data only, and the
first thing on the tab says nothing sends anything yet. Writing the names down
now means the feature, when it lands, does not begin with a form at the moment
a child is holding up a picture.

### Updates & safety

The PIN change (current PIN, then the new one twice, both on `kidnix-set-pin`'s
stdin, never in `argv`); `bootc status --format=json`; "Check for updates"
(`bootc upgrade --check`); "Update now"; "Roll back"; and the plain-English
page from `PARENTS.md`.

**The update button is behind the signature check**, because the review
reordered Tom's ask itself: *"an update button that pulls from ghcr with no
signature policy on the device is a worse position than being unpatched. Policy
and pinned identity first, button second."* So the tab reads
`/etc/containers/policy.json`, finds the most precise scope covering
`ghcr.io/mattcree/kidnix`, requires it to be `sigstoreSigned` with a `keyPath`
that exists on disk, and says the answer in a sentence either way. A scope of
`insecureAcceptAnything` is reported as **not** verified even though pulls
would succeed — "it works" and "it is checked" are different sentences. When
the check fails, Update now is insensitive with the reason on its tooltip.

A failed `bootc upgrade --check` is reported as a failure, never as "up to
date". On a machine whose policy has no key, the pull is *refused*; telling a
parent that means "you are up to date" is the one lie this tab must not tell.

## 5. Testing

| Where | What | Tests |
|---|---|---|
| `parent-panel/tests/test_model.py` | ids, slugs, the allow-list union, payload round trip | 29 |
| `parent-panel/tests/test_validate.py` | every rule, fatal vs note | 48 |
| `parent-panel/tests/test_config_io.py` | rendering, reading, the fixed point, `tts.env` in place | 25 |
| `parent-panel/tests/test_catalogue_system.py` | manifests, shelves, `bootc` parsing, the signature policy, `run_async` | 40 |
| `parent-panel/tests/test_helper.py` | who may ask, atomic writes, PIN preservation, the shell round trip | 22 |
| `parent-panel/tests/test_gtk_smoke.py` | every page under **Broadway**; skips with no display | 22 |
| `tests/image/test_parent_panel.sh` | install, launcher, helper, polkit, drift, no surveillance | 41 assertions |

**167 pure tests** (no display, no fork) and 22 GTK ones. `uv run ruff check`
and `uv run ruff format --check` are green; `uv run pytest` is 189 passing. The GTK suite runs under Broadway and does **not** segfault:

```
gtk4-broadwayd :10 &
GDK_BACKEND=broadway BROADWAY_DISPLAY=:10 uv run pytest
GDK_BACKEND=broadway BROADWAY_DISPLAY=:10 \
    uv run kidnix-parent-panel --screenshot docs/design/screenshots
```

The venv must be created with `uv venv --system-site-packages` (same rule as
`shell/`): `gi` and `kidnix_shell` come from the system, never from PyPI.

## 6. What the panel writes that the shell does not read yet

Three keys and one table are written as **valid TOML the shell ignores today**
rather than being held back. Each is labelled in the file and in the UI. The
alternative — waiting — means a household sets everything up twice.

## 7. Shell follow-ups, precisely

### 7.1 Schedule windows (`[[windows]]` in `session.toml`)

FLOWS B5 already records that "schedule windows are unbuilt" and that
SYNTHESIS D1 asks for windows matching household boundaries. The panel now
writes them:

```toml
[[windows]]
label = "After school"
days  = ["mon", "tue", "wed", "thu", "fri"]
start = "15:30"
end   = "18:00"
```

Days are the first three letters, lower case. Times are 24-hour. A window whose
`end` is at or before its `start` runs past midnight into the next morning and
belongs to the day it *starts* on.

**What the shell needs to do:**

1. `kidnix_shell/session.py` — `load_policy()` gains a `windows` field on
   `SessionPolicy`: `tuple[Window, ...]`, where
   `Window = (days: frozenset[str], start: time, end: time)`. Parse
   defensively, the way every other key in that file is parsed: a malformed
   window is skipped with a warning and **no windows at all means no
   restriction** (an empty list must never lock a child out — the same
   empty-means-all reasoning as `allowed_activity_ids`).
2. `SessionPolicy.in_window(when: datetime) -> bool` — true when no windows are
   configured, or when `when` falls inside one. Wrap-over-midnight is the same
   arithmetic `is_bedtime` already does.
3. `StartRefusal` gains `OUT_OF_HOURS`. `Session.may_start()` returns it after
   the `BEDTIME` check and before the budget check, so the stricter and more
   comprehensible refusal wins: a child outside their window at 8 pm is told it
   is bedtime, not that it is Tuesday.
4. `SessionPolicy.next_window_start(when)` — the earliest future window start,
   used by the Resting screen's "when" line so it says *"after school
   tomorrow"* rather than a time. `next_wake()` becomes the later of the
   bedtime gate, the 04:00 budget reset and this.
5. `screens/resting.py` — one more phrasing for `OUT_OF_HOURS`, in child terms
   and in the day/bedtime vocabularies that already exist.

Until then the data sits in the file and the panel says, in the tab, that
setting one changes nothing today.

### 7.2 A per-child allow-list

The panel writes `allowed_activity_ids` **inside each `[[profiles]]` table** and
also writes the machine-wide list at the top as the **union** of the active
children's lists (empty — "everything" — if any child is on everything). The
Activities tab says so in words whenever the two children's lists differ.

**What the shell needs to do:** `ParentConfig.is_allowed(activity_id)` becomes
`is_allowed(activity_id, profile_id="")`, reading the profile's own list when it
is non-empty and falling back to the machine-wide list otherwise. `Profile`
gains `allowed_activity_ids: tuple[str, ...] = ()`. The age band already filters
per child, so the youngest is not seeing the six-plus activities in the
meantime — the union only widens what an *older* sibling's list would have
allowed anyway.

### 7.3 Read-aloud pace (`[access] speech_rate`)

`tts.env` deliberately refuses to carry `length_scale`: the shell overrides it
per utterance through speech-dispatcher's rate, and a value set in that file
would be silently ignored. So the panel writes the **rate** next to the other
`[access]` keys, and shows the resulting `length_scale` (`1.0 - rate/200`,
quantised to 0.05) beside the control so a parent can see it is a real
quantity.

**What the shell needs to do:** `kidnix_shell/access.py` — `AccessConfig` gains
`speech_rate: int = SPEECH_RATE`, `parse_access` reads it (clamped to
−100…100), and `AccessConfig.speech_rate` becomes a field rather than a
property, with calm mode taking `min(configured, CALM_SPEECH_RATE)` so calm is
still at least as slow as the parent asked for. `SPEECH_RATE` stays as the
default. One line in `speech.py` where the rate is set.

### 7.4 Removed children (`[[retired_profiles]]`)

No shell change is needed, and that is the point: the shell reads `profiles`,
so a retired child simply is not there. It is recorded here so that nobody
later "tidies up" by teaching the shell to read `retired_profiles` and puts the
face back.

### 7.5 Family recipients (`[[family]]`)

Data only. When "send to family" is built (SYNTHESIS F3), the list is already
on the machine.

## 8. Deliberately not built in v0

* **A Journal browser.** FLOWS B11 is explicit that the parent's route is a
  plain directory tree in Files, and that nothing in the parent's view may be a
  surveillance metric. Export, then Files.
* **Per-child wipe.** `kidnix-wipe` is machine-wide and the tab says so in the
  row's subtitle rather than pretending otherwise. A per-profile mode belongs
  in `kidnix-parent-tools`, not in a dialogue that lies about what it does.
* **Editing "What's next after?".** Eight pictures is a screen of its own. The
  panel carries the blocks through a round trip untouched so a household's own
  options are never eaten.
* **malcontent integration.** ADR-0005 says the panel should record its policy
  in malcontent so GNOME's tooling agrees with ours. That is real and it is not
  v0; the allow-list that matters today is the one the shell reads.
* **A first-run wizard.** The tabs are the wizard. Mags's ask was a printed
  page, which is `PARENTS.md`, not a modal.
