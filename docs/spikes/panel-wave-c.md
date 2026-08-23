# Panel wave C — the image and activities half

**Status:** implemented, 2026-08-23. Built and asserted on `localhost/kidnix:wavec`.

What this covers: the blockers the 2026-08-23 expert panel raised that land in
`build_files/`, `system_files/`, `tests/image/` and the parent-facing docs. The
shell (`shell/`) half — journal export/delete, per-profile paths, the "what a
grown-up can see" screen, the voice rewrite, and the shelf *rendering* — is
another worker's, and §2 below is written to be that worker's contract.

Everything here is asserted in the image test suite. `just tag=wavec test-image`
runs 12 scripts; the two new ones are `tests/image/test_locale.sh` (30
assertions) and `tests/image/test_supply_chain.sh` (30).

---

## 1. The machine is British now

The early-years teacher opened with a BLOCKER and the evidence was our own
screenshot — Tux Paint's status bar reading *"Pick a COLOR and a brush shape to
draw with."* Her sentence: *"A machine whose stated job is helping a UK
five-year-old with letters and spelling cannot show him American spellings."*

Four subsystems own four different halves of "British", and all four are now
set. New stage: **`build_files/05-locale.sh`**.

| What | Where | Value |
|---|---|---|
| C library locale | `/etc/locale.conf` | `LANG=en_GB.UTF-8` |
| console keymap | `/etc/vconsole.conf` | `KEYMAP=uk` |
| system X11/Wayland layout | `/etc/X11/xorg.conf.d/00-keyboard.conf` | `XkbLayout "gb"` |
| the child's session layout | kid dconf `org.gnome.desktop.input-sources` | `[('xkb', 'gb')]`, **locked** |

Notes worth keeping:

* **No package was installed.** `glibc-all-langpacks` comes down from
  `base-main` and already carries `en_GB.utf8`; `dnf5 install glibc-langpack-en`
  measured at *"After this operation, 6 MiB extra will be used"* for locale data
  that is already there. The stage installs it **only if** `locale -a` does not
  list `en_GB.utf8`, so a future base image trimmed to `glibc-minimal-langpack`
  does not silently put the whole machine back into American English.
* **`/etc/locale.conf` is enough for the child.** systemd PID 1 parses it and
  puts `LANG` into the default environment of every unit — gdm included, and
  therefore the child's `systemd --user`, gnome-session, the shell and every
  activity. There is no profile.d step in that path to get wrong (Fedora's
  `/etc/profile.d/lang.sh` only matters for login shells, and only falls back to
  `C.UTF-8` when the named locale is *not installed*).
* **Why both `uk` and `gb`.** `uk` is the kbd console keymap name; `gb` is the
  xkb layout name for the same hardware. They are different namespaces, not a
  typo.
* **Why the layout is set twice.** GNOME's per-session input sources override
  the system layout the moment a session starts, so setting only
  `00-keyboard.conf` would leave the child on the compiled-in `us` — `@` and `"`
  swapped from the keycaps, and no `£` at all.
* The layout is **locked** in the kid profile, and it is a single-entry list on
  purpose: GNOME only shows the input-source indicator and binds `Super+Space`
  when there is more than one source.
* Per-application language settings are separate and each is asserted where it
  lives: GCompris `locale=en_GB.UTF-8`, Tux Paint `lang=british-english`,
  KLettres `/etc/xdg/klettresrc`.

---

## 2. The GCompris shelf — **the data contract for the shell worker**

This is the part another worker needs. Read this section and nothing else.

### The shape

`/usr/share/kidnix/activities/gcompris.toml` gains two keys:

```toml
kind = "shelf"
children_dir = "gcompris"
```

and there is now a directory `/usr/share/kidnix/activities/gcompris/` holding
**18 ordinary activity manifests**, one per curated GCompris activity.

**`children_dir` is resolved relative to the directory the shelf manifest is
in.** So the system shelf resolves to `/usr/share/kidnix/activities/gcompris/`,
and a dev override in `$XDG_DATA_HOME/kidnix/activities/gcompris.toml` resolves
beside itself.

The entire shell-side implementation should be:

```python
children = load_directory(activity.source_path.parent / activity.children_dir)
children = resolve_availability(children)
# already sorted by (order, filename, id); filter by the profile's band with
# in_age_band() exactly as Home does
```

There is **no new parser and no new schema**. A child is an `Activity`, from the
same `parse_manifest`, with `id`, `name`, `audio_label`, `goal`, `icon`,
`icon_kind`, `exec`, `quit`, `category`, `age_min`/`age_max` (from `age_band`),
`order`, `package`, `licence`, `notes`. `kind` and `children_dir` are currently
*unknown keys* to `activities.py`, so they are logged at debug and ignored —
which means today's shell still loads `gcompris.toml` fine and simply treats it
as a plain tile. Nothing breaks while you implement.

### What one child looks like

```toml
schema = 1
id = "gcompris.smallnumbers"
name = "Dice dots"
audio_label = "Count the dots on the dice, then press that number"
goal = "Saying how many dots are on a dice. Practises seeing a small number without counting -- plain dice pips, not cartoons. No reading needed."
order = 90
icon = "kidnix-act-gcompris"
icon_kind = "icon-name"
exec = ["gcompris-qt", "--launch", "smallnumbers", "--hide-home-button"]
quit = "signal"
category = "learn"
age_band = "4-7"
oars_rating = "none"
network_required = false
source = "rpm"
package = "gcompris-qt"
licence = "AGPL-3.0-only (code); CC-BY-SA-4.0 / GPL-3.0-or-later (...)"
journal_watch = []
wayland_native = true

# kidnix-specific; ignored by the shell's parser, read by the shelf view.
shelf_group = "counting"
shelf_group_name = "Counting"
shelf_group_audio_label = "Counting"
gcompris_difficulty = 2
gcompris_intro_voice_en_GB = true
```

Five points about those extra keys:

1. **`shelf_group` / `shelf_group_name` / `shelf_group_audio_label`** exist so
   the shelf can draw headings without re-reading `curated.toml`. They are
   ignored by `parse_manifest`, so if you want them you have to read the TOML
   yourself or add them to `KNOWN_KEYS` and `Activity` — your call. Group order
   is the order the groups appear in `curated.toml`, which is also the order the
   children's `order` values follow, so **sorting by `order` alone already
   produces correctly grouped output**. The six groups, in order: Point and
   click · Letters · Counting · Numbers in order, and adding · Look, listen and
   remember · Shapes and patterns.
2. **`gcompris_intro_voice_en_GB`** says whether GCompris will speak its own
   introduction. Seven of the eighteen are `false`, and those are exactly the
   tiles where the shell's own `audio_label` is the *whole* instruction a
   pre-reader gets. If you ever shorten a spoken label, shorten a `true` one.
3. **Ids are namespaced** (`gcompris.smallnumbers`, not `smallnumbers`) because
   activity ids are one global namespace in `load_activities`, and `memory` or
   `colors` are names a future top-level activity could want.
4. **The children are in a subdirectory** so `load_directory` on
   `/usr/share/kidnix/activities` cannot pick them up: they must never become 18
   extra tiles on Home. `tests/image/test_gcompris.sh` asserts that.
5. **They are generated at build time** by `build_files/55-gcompris.sh` §7 from
   `/usr/share/kidnix/gcompris/curated.toml`. Do not hand-edit them; edit
   `curated.toml` (and `CURATION.md` beside it) and rebuild.

### The shelf tile's own `exec`

```toml
exec = ["gcompris-qt", "--launch", "erase", "--hide-home-button"]
```

That is the **fallback for a shell that has not implemented shelves yet**, and
it is deliberately not the bare `gcompris-qt`. `--launch` with an unrecognised
or absent id does not fail — it silently opens the full 198-activity menu, which
is the exact BLOCKER this work closes. `55-gcompris.sh` and
`tests/image/test_gcompris.sh` both assert that **no manifest anywhere in the
image starts `gcompris-qt` without `--launch`**. Once you render the shelf,
`exec` on a `kind = "shelf"` manifest should never be run at all.

### Suggested behaviour (not enforced by the data)

* Tapping the shelf tile opens a second screen; Back from that screen returns to
  Home, not out of the session.
* The band's Back inside a launched child returns to the **shelf**, not to Home.
* Age filtering applies to the children, not to the shelf. Concretely, with
  `in_age_band`'s overlap rule: a **4–5** profile sees all eighteen (every
  child's `age_min` is 4 or 5), a **4-only** profile sees twelve — the six
  banded 5–8 (`gletters`, `enumerate`, `adjacent_numbers`, `learn_additions`,
  `number_sequence`, `frieze`) drop out — and a **6–8** profile also sees all
  eighteen, because nothing on the shelf is capped below 6. In other words the
  bands only bite at the bottom today; if the shelf ought to shrink for an
  older child, that is a `curated.toml` change, not a shell one.
* If every child is filtered out, hide the shelf tile (`Activity.on_home`
  semantics, applied to the shelf).

---

## 3. KLettres says letter NAMES — settled, with evidence

The teacher's BLOCKER: *"`klettres.toml` is titled 'Letter sounds' when its own
notes say nobody has checked whether en_GB KLettres says the letter's NAME or
its SOUND. A tile called 'Letter sounds' is a phonics claim, made before any
prose can disclaim it."*

**Method.** The en_GB recordings ship in the RPM at
`/usr/share/klettres/en_GB/alpha/{a..z}.ogg`. Every file is padded to ~1.8 s, so
file length says nothing. Extract them and measure the *speech*:

```sh
ffmpeg -i a.ogg -af "silenceremove=start_periods=1:start_threshold=-40dB:\
stop_periods=-1:stop_threshold=-40dB:detection=rms" -f null -
```

**Result** (seconds of continuous speech, all 26):

```
a=0.40 b=0.56 c=0.66 d=0.44 e=0.43 f=0.37 g=0.42 h=0.52 i=0.52 j=0.53 k=0.39
l=0.43 m=0.49 n=0.38 o=0.41 p=0.39 q=0.46 r=0.33 s=0.60 t=0.36 u=0.63 v=0.68
w=0.71 x=0.38 y=0.61 z=0.90
```

**Conclusion: letter names.** An isolated plosive phoneme (/t/, /p/, /k/, /b/,
/d/, /g/) is a burst of 0.1–0.2 s and physically cannot last 0.36–0.56 s. And
`w` — the *shortest* phoneme in the set but the *longest* name, "double-u" — is
0.71 s, the longest of the twenty-six after `z` ("zed"). That is the signature
of names, not sounds.

Two structural facts make it not-phonics regardless of the recordings:
`sounds.xml` presents the alphabet as **uppercase A–Z** (UK phonics teaches
lowercase graphemes first), and the en_GB "syllables" set used by levels 3–4 is
**23 whole real words** (ARM, BALL, CAR, GEM, THE), not phase-controlled blends.
`GEM` alone contradicts the hard /g/ a Phase 2 child has just been taught.

**Changed:** the tile is `name = "Letter names"`, `audio_label = "Listen to the
letter, then press it on the keyboard"`, and the goal says *"The voice says each
letter's NAME -- ay, bee, see -- not its phonics sound, so this practises the
alphabet, not reading."* New `/etc/xdg/klettresrc` pins `Language[$i]=en_GB`
(the kcfg default is `en`, which is the **American** recording set), turns on
kid mode so the text menubar is hidden, and starts at level 1 — the only level
that shows the letter as well as playing it.

`tests/image/test_activities.sh` now asserts that **no tile name or spoken label
anywhere** contains "phonic" or "letter sound", and that the KLettres goal
explicitly disclaims phonics.

---

## 4. TuxMath and SuperTux are 7+

The teacher, MAJOR: *"tuxmath.toml ships timed arithmetic with a score and a
game-over; supertux.toml ships lives and a GAME OVER screen … E1 says no points,
no scores, no levels. A Reception child hitting GAME OVER on a machine whose
premise is 'you cannot fail here' is a tonal break that will produce the first
week's tears."*

Her own recommendation was to drop TuxMath outright. The decision taken was
`age_min = 7` on both (`tuxmath` was 6, `supertux` was 5), which under
`in_age_band`'s overlap rule removes them from a 4–5 profile **entirely** — not
greyed, not outlined, absent. Both goal strings now say out loud that the
activity can be lost. Asserted, along with a check that a 4–5 year old still has
at least six tiles after the gate.

**Not done, and flagged:** `blinken.toml`'s goal says *"failing just stops the
lights"*, and Blinken has a high-score table. Same objection, smaller. Left for
whoever next opens that manifest.

---

## 5. Tux Paint button size

`tuxpaint --help` on the shipped 0.9.35:
`[--buttonsize=N (24-192; default=48) | --buttonsize=auto]`, and `tuxpaint(1)`:
*"Adjust the size of the buttons in Tux Paint's user interface, between 24 and
192 pixels (48 is the default, and suitable for displays with 96 to 120dpi pixel
density)."*

`/etc/tuxpaint/tuxpaint.conf` now sets **`buttonsize=96`** — double the default,
inside the documented range. Not 192: buttonsize scales the tool columns, which
Tux Paint lays out in a fixed grid down both sides of the canvas, and at 192
there is very little canvas left on a 1366×768 laptop.

**Still owed, and this is the honest state of it.** The teacher's BLOCKER is
specifically about Tux Paint's *quit dialogue* — *"a green tick and a pink cross
around 20 px … the smallest and most consequential target we ship"* — because
the whole Put-away ritual ends there. The man page's wording ("the buttons in
Tux Paint's user interface") covers that dialogue's tick and cross, so
`buttonsize=96` **should** double them. **That is an inference from the man
page, not a measurement.** What is needed: one screenshot of the quit prompt at
1366×768 with a ruler on it, checked against the 18 mm floor. The image test
asserts the option exists and the value is set; it cannot assert millimetres.

---

## 6. Security and privacy

### (a) The update channel — **and a finding that changes the ask**

The safety reviewer, BLOCKER 3: the image writes
`"image-ref": "ostree-image-signed:docker://ghcr.io/mattcree/kidnix"` and CI
does a keyless `cosign sign`, but nothing on a running machine verified
anything. Tom's ordering (#58): *"policy.json and the cosign identity pinned on
the device FIRST, then the button, then a notification."*

**The finding: keyless verification cannot be expressed here.** Chased to the
source, not guessed:

* `containers-policy.json(5)` `sigstoreSigned` accepts exactly one of
  `keyPath` / `keyPaths` / `keyData` / `keyDatas` / `fulcio` / `pki`.
* the `fulcio` object has exactly four keys — `caPath`, `caData`, `oidcIssuer`,
  `subjectEmail`. There is **no regexp option**; an invented
  `subjectEmailRegexp` is rejected at policy load with `Unknown key
  "subjectEmailRegexp"`, and a rejected policy rejects **every pull on the
  machine**, `bootc upgrade` included.
* `subjectEmail` is matched only against the certificate's SAN **rfc822Name**
  list (`signature/fulcio_cert.go`:
  `slices.Contains(untrustedCertificate.EmailAddresses, f.subjectEmail)`), and
  the source carries a `FIXME` saying URIs and *"various values about GitHub
  workflows"* are deliberately not matched.
* a GitHub Actions keyless certificate puts the workflow identity
  (`https://github.com/mattcree/kidnix/.github/workflows/...`) in a SAN **URI**.

So there is no value, exact or otherwise, that makes containers/image accept a
GitHub-Actions-signed image. **The review's literal ask — pin the workflow
certificate identity and issuer — is not implementable on this stack today.**

**What was shipped instead**, following the pattern this image's own base
already uses (`ghcr.io/ublue-os` is pinned in the base policy with
`keyPaths: [/etc/pki/containers/ublue-os.pub, ...]`):

* new stage `build_files/75-supply-chain.sh`, which **merges** one scope into
  the base image's `/etc/containers/policy.json` rather than shipping a
  replacement — clobbering it would silently un-trust our own base image:

  ```json
  "ghcr.io/mattcree/kidnix": [
    { "type": "sigstoreSigned",
      "keyPath": "/etc/pki/containers/kidnix.pub",
      "signedIdentity": { "type": "matchRepository" } }
  ]
  ```

  `matchRepository` is not optional: cosign signatures carry only a repository,
  and the default `matchRepoDigestOrExact` would reject every one of them — a
  policy that looks strict and is simply broken.
* `/etc/containers/registries.d/kidnix.yaml` with
  `use-sigstore-attachments: true`, without which nothing looks for a cosign
  attachment at all and every pull fails with "no signatures found".
* the policy is loaded through **skopeo's own loader** at build time and again
  in `tests/image/test_supply_chain.sh`, because "valid JSON" and "a valid
  policy" are different things.

**`/etc/pki/containers/kidnix.pub` is deliberately not in the repository yet.**
Until someone runs `cosign generate-key-pair`, puts the private half in Actions
secrets, adds a `cosign sign --key` step and commits the public half,
`ghcr.io/mattcree/kidnix` **fails to pull**. That is the intended direction of
failure and is exactly Tom's ordering: unpatched beats an unauthenticated
root-level update channel, and the machine has no update mechanism today anyway.
The build prints four loud `!!` lines saying so; `docs/BUILDING.md` carries the
recipe to close it.

**Needs a VM, not an image test:** that an unsigned image is actually *refused*.
The commands, for whoever does it:

```sh
# on the machine, after install
sudo bootc switch --enforce-container-sigpolicy ghcr.io/mattcree/kidnix:latest
sudo bootc upgrade          # must refuse while no key is installed
skopeo inspect --policy /etc/containers/policy.json \
    docker://ghcr.io/mattcree/kidnix:latest   # must refuse
skopeo inspect docker://ghcr.io/ublue-os/base-main:44   # must still work
```

Also worth knowing: `bootc switch` defaults to the *permissive* variant
(`ostree-unverified-registry:`) and only `--enforce-container-sigpolicy` selects
`ostree-image-signed:`. The mode is fixed at install/switch time and reused by
every later `bootc upgrade`, so the install command is where this is won or lost.

### (b) Research instrumentation ships OFF

New file **`/etc/kidnix/research.toml`**, root-owned, `0644`:

```toml
schema = 1
[research]
enabled = false
hover_instrumentation = false
hover_record_selection = false
pin_attempt_logging = false
journal_path = ""
```

**Contract for the shell worker.** Read this file at start-up. If it is missing,
unreadable or malformed, behave as if every key were `false`. Never log an event
this file does not enable. `enabled = false` is a master switch that overrides
the individual keys. Specifically: `speech.py::_flush_hover_log` must not emit
its line unless `enabled && hover_instrumentation`, must omit `selected=` unless
`hover_record_selection` as well, and `screens/grownup.py::_check` must not log
a PIN attempt unless `enabled && pin_attempt_logging`.

It is a separate file from `parent.toml` on purpose: `parent.toml` is settings a
parent chooses for their child, this is a switch for a study, and mixing them
would put "record my child" one mis-tap from "25 minutes".

### (c) journald retention

New **`/usr/lib/systemd/journald.conf.d/10-kidnix.conf`**:
`MaxRetentionSec=30day`, `SystemMaxUse=200M`, `SystemMaxFileSize=20M`,
`MaxFileSec=1day`, `ForwardToSyslog=no`, `ForwardToWall=no`. Asserted both as a
file and through `systemd-analyze cat-config systemd/journald.conf`, so a
misspelled key fails the test rather than being ignored at boot.

`/usr/lib` rather than `/etc` (matching the existing
`logind.conf.d/10-kidnix-kiosk.conf`): bootc owns it, an upgrade reinstates it,
and a parent who wants different numbers drops a file in `/etc/systemd/journald.conf.d/`,
which sorts later and wins.

### (d) Export and wipe

* **`/usr/bin/kidnix-export [DESTINATION]`** — tars the child's Journal
  (`~/.local/share/kidnix`), session state (`~/.local/state/kidnix`), Tux Paint's
  saved pictures (`~/.tuxpaint/saved`), `~/Pictures` and `~/.config/gcompris`
  into `kidnix-kid-<date>.tar.gz` in the parent's home (or a path you give it,
  e.g. a USB stick), `chown`ed to the parent and `0600`. Prints the path, the
  size, and the two commands to look inside.
* **`/usr/bin/kidnix-wipe [--yes]`** — lists what it will delete with sizes,
  requires the human to type `DELETE`, unlinks all of it, then re-creates the
  empty directories owned by `kid` so the next session starts cleanly. The
  account itself is untouched. Reminds the reader to change the PIN and the
  parent password if the machine is being given away.
* Both are thin `pkexec` wrappers around
  **`/usr/libexec/kidnix-parent-tools`**, because `/var/home/kid` is `0700
  kid:kid` — deliberately, and that is exactly why the parent cannot read it
  (Tom: *"her drawings live in the child account's home; I am a different user;
  no export, no printing, no send-to-Granny"*).
* New polkit action `org.kidnix.parent-tools`
  (`allow_active=auth_admin_keep`, `allow_inactive=no`), matched to the helper
  by the `exec.path` annotation.
* **`"org.kidnix."` was added to the deny list in `40-kidnix-kid.rules`.** This
  is load-bearing, not defensive: pkexec asks for the *annotated* action id, so
  the existing `org.freedesktop.policykit.` denial does not cover it. Asserted
  with `kidnix-polkit-check` at build time and in the image tests.

### (e) `parent.toml` — for the shell worker

Not touched here (`parent.toml` is yours), but the expectation from forum #44,
#56 and the safety review, recorded so it does not get lost:

> `ParentConfig.is_default` is only `True` when **no** `pin_hash` was found, and
> `/etc/kidnix/parent.toml` ships **with** the 1234 hash and a fixed public
> salt. So on a stock install `is_default` is `False` and the "This machine has
> no parent config" warning never appears: **the one signal that the gate is
> open is suppressed by the file that opens it.**

Mags, reading that: *"the only way I would ever learn my lock is not a lock is
by reading a file I would never open. Please make it refuse to start until I
have picked my own four numbers, and please let me pick them somewhere he is not
looking."*

The two options the reviewer offered: ship **no** `pin_hash` (letting
`__post_init__` supply the default and flag `is_default`), or add an explicit
`pin_is_default = true` key. Either is fine from this side. Note that
`70-hardening.sh` currently *asserts* the shipped file verifies the default PIN,
so whichever you pick, that assertion needs updating with you — say which and it
will be changed in the same commit.

Related, and also yours: `ParentConfig.save()` will raise `PermissionError`
because `kid` cannot write `/etc`. The image can create a parent-owned,
group-readable directory under `/var/lib/kidnix` for you — say the word and the
`tmpfiles.d` fragment lands.

---

## 7. Docs

* **`docs/BUILDING.md`** gained a "Before you install this on real hardware"
  section — the password step made unmissable, the recovery path spelled out
  (`PasswordAuthentication no` + a locked `parent` account = rescue USB), the
  fact that installing wipes the disk stated in those words, the absence of disk
  encryption stated, and the cosign key recipe.
* **`docs/PARENTS.md`** is new and is written for Mags. One page, no commands
  above the fold, and it answers her three questions and Tom's and Priya's and
  Dan's by name.

## 8. Not done, deliberately

* **The Flathub first-boot timer still retries forever** (`OnUnitActiveSec=30min`,
  `Persistent=true`). The safety review's MAJOR 4. It is a two-line change to
  the timer unit and it touches the egress tests, so it was left rather than
  rushed alongside everything else.
* **No disk encryption.** `disk_config/` is untouched; `BUILDING.md` and
  `PARENTS.md` now *say* the disk is not encrypted rather than leaving it
  unmentioned, which is the reviewer's stated minimum.
* **Blinken's high-score table** (see §4).
* **Tux Paint's wider UI** — ~20 tool buttons, 20 colour swatches, all under
  18 mm. The teacher's list of build-time levers (`colorfile=` with ten named
  colours, `simpleshapes=yes`, `nomagiccontrols`, a reduced brush set) is real
  and all available here; it is a session's work of its own and wants a child in
  front of it.
* **The three pointer activities and `gletters`** on the GCompris shelf. The
  teacher would cut one or two; both cuts want a real five-and-a-half-year-old
  first, and are recorded in `CURATION.md`.
