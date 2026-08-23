# kidnix — CCI compliance audit, checkpoint 2 (2026-08-23)

> Auditor's report (Claude Opus 5). A re-audit after the expert panel's fix
> waves A–G: does the build now hold the chair's fourteen rulings and the §2
> convergences, and do the four **new first-party activities** hold the
> research? Read `docs/research/SYNTHESIS.md`, the panel synthesis and
> `cci-compliance-audit-2026-08-22.md` first; this assumes all three.

---

## 1. Method

**Snapshot.** HEAD `2f2d159` **plus an uncommitted wave in flight**. The tree
grew from 4 to 15 modified files *during* this audit (`session.py` gaining
`[[windows]]`, `access.py` gaining `speech_rate`, `home.py` gaining per-child
allow-lists, `clock_time/activity.py` gaining a routine strip);
`activities/letters_to_family/` is entirely git-untracked; and `numbers.toml`
and `clock-time.toml` were **installed into `system_files/` mid-run**, so the
image's tile count changed between two of my own greps. Line numbers are
approximate; every judgement below is of a moving target and should be
re-checked before the child test. Where a test result below looks unstable, it
is — `clock_time` went 395-green → 1-red → green in four minutes.

**What I read.** The panel synthesis §2/§4 in full; spec §7a–§7d; ADR-0010/11/12;
implementation notes §21–§25; `FLOWS.md`; `SUITE.md`; research SYNTHESIS §2/§4,
`05` §3–§4, `10` §4/§4.6; the design notes for sounds-and-words, numbers,
clock-time, parent-panel, activity-sdk, i18n. Then the code: `shell/kidnix_shell/**`,
`shell/kidnix_activity/**`, all four activity packages, `parent-panel/**`,
`system_files/**`, `build_files/{50,55,62,64,70,75}-*`. Then the artefacts:
`e2e-contact-sheet.png`, `demo-a11y-home.png`, `saw-find-it.png`,
`saw-blend-it{,-digraph}.png`, `numbers-{how-many,make-five}.png`,
`clock-{play,minute}.png`, `parent-panel-things.png`, `icons-contact-sheet.png`,
`i18n-pl-home.png`.

**How I judged.** Same rule as checkpoint 1: *a ruling is MET when a named test
or a shipped file proves it, not when a design note describes it.* Screenshots
outrank prose; a test name outranks a comment. Three parallel evidence sweeps
(shell, activities, parent panel) were cross-checked against my own greps, and
where they disagreed I re-verified by hand — the cosign key **does** ship
(`system_files/etc/pki/containers/kidnix.pub`, 178 bytes, added today), and the
build script's "THE KEY IS NOT IN THE REPOSITORY YET" comment is stale.

**Test counts observed.** shell `1375 passed`; parent-panel `189`;
sounds_and_words `554`; numbers `842`; clock_time `395–399` with one in-flight
label-fitting failure appearing and clearing; letters_to_family `168` passed
headless once `tests/test_gtk_smoke.py` is excluded (it hangs waiting for a
display, which is what my first run hit).

---

## 2. Panel rulings and §2 convergences

| # | Ruling / convergence | Status | Evidence | What remains |
|---|---|---|---|---|
| 1 | Session floor 5 min, proportional windows, refusal at Who's here | **MET** | `session.py:70` `MIN_SESSION_SECONDS=5*60`, `:73` parent floor 3 min, `OFFER_FRACTION=0.20`/2–4, `PUT_AWAY_FRACTION=0.10`/1–2; `app.py:1605-1629` refuses **before** `CHOOSE_PROFILE`; `test_no_session_ever_begins_in_its_own_ending`, `test_the_ritual_always_has_two_beats`, e2e `test_a21` | — |
| 2 | The offer is consequential | **MET** | `DEFERRED_PUT_AWAY_SECONDS=60`; `test_the_two_answers_produce_different_put_away_times`, `test_a_deferral_can_never_bring_the_ending_forward` | "returns Home" only from `State.JOURNAL`; from a shelf it returns to the shelf |
| 3 | Goodbye led by destination; descriptive feedback; Show-a-grown-up always | **MET** | `goodbye.py:118-179` order, `:229` `set_visible(True)` unconditional, `:243` `speak_then` puts destination last; `feedback.py`; contact sheet frame 18 | No test drives Goodbye with destination **and** journal work together |
| 4 | Day vs bedtime vocabularies; rate-limited; dim | **MET** | `resting.py` two tables, `SPEECH_INTERVAL_SECONDS=8.0`, `SILENCE_AFTER_TAPS=3`; dim on the **windows** (`app.py:1273-1289`); AST guard `test_the_word_goodnight_exists_in_exactly_one_module`; frame 17 | The **"All done" tile still wears `kidnix-moon` at 4 pm** — see §5 |
| 5 | All done pinned; disclosure off; band offer ADDs | **MET** | `home.py:80` `ALL_DONE_INDEX=7` with holes; `settings.py:423` `show_everything=True`; `band.py:805` `_show_left()` keys off `_finishing` only; frames 3/4 and 12 | — |
| 6 | "Not sure yet" | **MET** | `next_after.py:151` `SKIP_ID="unsure"`; `app.py:1638` clears `ctx.next_after` | Label is "Not sure"; icon is the reused `kidnix-ask` |
| 7 | Depictive icons; thumbnail as corner badge | **PARTIAL** | 11 hand-drawn `kidnix-act-*.svg` (`icons-contact-sheet.png`); no vendor names in any manifest; badge is an `add_overlay` at END/END | **The 18 GCompris shelf children carry no `icon`** (`curated.toml`, zero `icon` keys) and `55-gcompris.sh:399` inherits the parent's — every shelf tile is the same alphabet-blocks picture, 3–4 identical tiles per page. `kidnix-one-more.svg` still depicts nothing |
| 8 | en_GB; GCompris shelf of 18; KLettres truthful; TuxMath/SuperTux out of band | **MET** | `locale.conf:20`; `curated.toml` 6 groups × 18; `klettres.toml:7` names letter *names*; `age_min=7` on both | — |
| 9 | Starter PIN detected; gate forces a new one | **PARTIAL** | Both `parent.toml` copies ship **no** `pin_hash`; `pin_is_starter` compares the hash; helper refuses `1234`; `test_the_mandatory_flow_cannot_be_escaped_into_the_actions` | `must_set_pin` is read only inside `GrownupSheet` — a PIN-less machine still boots a full child session. Spec §S9 line 104 still documents "default PIN 1234" |
| 10 | Per-profile data; export/wipe; journald cap; research off; signature policy | **MET** | `Paths.for_profile`; `journald.conf.d/10-kidnix.conf` 30 day/200 M asserted via `systemd-analyze cat-config`; `research.toml` all-false, failure-closed; policy merged in `75-supply-chain.sh` **and** `kidnix.pub` ships; panel button gated on `verified` | Export/wipe are **whole-machine**, not per-profile (the panel says so in words) |
| 11 | Accessibility set | **PARTIAL** | One `Keyboard` on both toplevels (`app.py:502-503`); caption hook **before** the enabled check (`speech.py:578`) with two AST guards; `ATTACK_FLOOR_MS=150.0`; contrast recomputed in `test_theme_css.py`; `demo-a11y-home.png` | **`calm` ships `false`** (`access.py:96`) with a test pinning it off; the ruling says `calm = true`. Switch *scan* unbuilt; Orca unverified |
| 12 | 20 s voice note | **MET** | `voice.py:53` `MAX_SECONDS=20.0`, note inside the entry dir; `test_it_stops_itself_after_twenty_seconds`; frame 15 | Journal mic only in showing mode; no delete for a note |
| 13 | 20 mm floor, 24 preferred | **MET** (24 mm not encoded) | `metrics.py:81` `MIN_TARGET_MM=20.0`; `mm_floor` ignores `fit`; `test_millimetres_never_round_down` | No `PREFERRED_TARGET_MM=24`; `band_target` bottoms at ~21 mm |
| 14 | Child-test method; burst detector first | **PARTIAL** | Detector built and wired capture-phase on both toplevels (`research.py:40-45`); protocol §67-72 has alternating treatments + blind coder | **The protocol contradicts itself**: line 73 says the detector "exists only as comments" (false) and line 91 still prescribes ABAB for P1 |
| §2 | Tux Paint quit dialog ≈20 px tick | **PARTIAL** | `50-activities.sh:201` `buttonsize=96` (2×), asserted in `test_activities.sh` | The script states in caps that scaling of the *quit prompt* is an inference from the man page, not a measurement. Frames 7/16 still show a small tick. Owes one ruler-on-screenshot |
| §2 | Nothing records the child's voice | **MET** | ruling 12 | — |
| §2 | All other convergence rows (session arithmetic, promise, All-done migration, Goodbye hierarchy, night vocabulary, shipped PIN, cosmetic profiles, no data exit, locale/GCompris/KLettres, research default, update signing, 18 mm) | **MET** | as rows 1–13 above | — |

**Score.** 10 of 14 rulings MET, 4 PARTIAL, 0 MISSING. Every §2 blocker is
addressed at least partially; the two that are not closed are the **shelf icons**
and **`calm`'s default**.

---

## 3. The four first-party activities

Common ground first. All four run on `kidnix_activity`; all four declare
`quit = "signal"` and `quit_grace = 5.0`; all four route every spoken line
through the SDK, so the shell's caption listener (§25) shows it. `grep` for
`streak|badge|leaderboard|coin|score|points|level` returns only *tests asserting
their absence* and one geometric `points` tuple. `grep` for `socket|requests|
urllib|onnx|openai` returns nothing in any activity. All four use `GrownUpTurn`.

| Axis | Sounds & Words (Find it / Blend it) | Numbers | Clock & time | Letters to family |
|---|---|---|---|---|
| **A — input** | Press-only; tile *or* key; digraph = two keys, the first *pending*, never wrong; explicitly no timer (`keys.py`) — **MET** | Press-only; "Look" re-shows the arrangement — **MET** | Press-only; the hands are pressed, not dragged; the minute stopwatch is a toy the child stops — **MET** | Press-only; scribble is press-drag on a canvas (legitimate, C1-recoverable) — **MET** | 
| **B — icon+label+audio, ≤5** | Find it: 4 (`distractors.py:396`). Blend it: **no explicit ceiling** — one button per grapheme, bounded only by the schedule's taste for short words — **MET/minor** | **FAIL at `range = "ten"`.** `settings.py:161` `range(1, top+1)` → **10** numeral tiles + Look. Default `five` is what the screenshot shows and is compliant; nothing in the package argues the exception, and the rationale given (`:158`) cites B1 stability, a different rule. Also: `numerals = false` strips every label (`activity.py:344`), and the ten-frame boxes are **audio-only, no child widget at all** (`:241-250`) — **MAJOR** | **FAIL.** `clock-minute.png`: six buttons — *Start · Watch · Half · One · Two · Clock* — only "Clock" has an icon. `clock-play.png`: eight routine tiles, labels hyphenating mid-syllable ("Scho-ol", "Brea-kfast"). And Year 2 draws **12 audio-only rim targets** (`words.py:128`) — **MAJOR** | **FAIL.** `activity.py:325` iterates the whole `[[family]]` list with no slice: 12 relatives = 12 tiles on the first screen a pre-reader sees. Journal picture tiles have `speak_text` but no `label`; crayons are `BigButton("")` — **MAJOR** |
| **C — undo / recoverability** | Wrong answer: nothing happens to the tile pressed, the right one pulses, the loop moves on after two tries — **MET** | `respond()` scaffolds then gives the answer plainly and moves on; "never called wrong" is tested — **MET** | No undo; nothing is destructible — **N/A** | The only activity with an in-activity **Undo** button (`activity.py:429`) — **MET** | 
| | *Cross-cutting:* **no first-party manifest sets `undo_key`**, so the band's Undo speaks "Undo for X is in X's own buttons" — which is **false** for S&W, Numbers and Clock. **MAJOR** | | | |
| **E — artefact, informational, no scores** | Journal card = "the words read today"; feedback names the sound, not the child | Journal card records what was practised; `words.py` docstring is the rule and is tested | `minute.py:35` "no percentage, no score, no best-ever, no streak"; `test_minute.py:129` forbids the vocabulary | The letter *is* the artefact; caption byte-for-byte, no spell-check | **MET, exemplary, across all four** |
| **H3 — no AI** | Leitner boxes + a SQL-shaped filter (10 §4.3) | pure arithmetic | pure arithmetic | none | **MET** |
| **05 §3 / 10 §4 rules** | Corpus is L&S 2007 OGL; hard ceiling; Appendix-7 acceptance test; dot/bar convention correct (`saw-blend-it-digraph.png`, `r·a·**ng**`); distractors chosen in four tiers and never untaught | Subitising to 5 + bonds to 5/10, the two things the ELG actually names (05 §3 "Add" #2) | Play, not a test; the manifest says so | 05 §3 calls this **the strongest activity in the list**; a real named recipient, no address field, no spelling correction, reply comes back | **MET on design** |
| **10 §4.6 "what NOT to do"** | No progression invented ✓; no hotspots ✓; no reward economy ✓; no ASR ✓; no auto-correct ✓; no pseudo-word test ✓ — **but two live defects**, below | — | — | — | |
| **SDK contract** | `quit="signal"` ✓, captions ✓, `save_entry` ✓ | ✓ ✓ ✓ | ✓ ✓ ✓ (`activity.py:1056`) | ✓ ✓ ✓ (`assemble.py:124`) | **MET** |
| **i18n** | **0** `_()`/`N_()` calls | **0** | **0** | **0** | **MISSING, all four** — and so is the SDK's own copy (`kidnix_activity/widgets.py:57,64,65`). `kidnix_activity/i18n.py` is imported by nobody, and `shell/Justfile:84` does not scan `activities/` at all, so the extractor could not see the strings even if wrapped. `i18n-pl-home.png` shows the same at the tile layer: only "Gotowe" is Polish |
| **Accessibility** | Digit/letter keys are a second equal route; nothing below 20 mm | Digit keys 1–9/0; `TILE_MM` floors at exactly 20 | Arrow keys step the hands; a 9th routine moment is **dropped** rather than shrunk below 20 mm | `keys.py` wraps the SDK ring so a text box gets arrows but Tab always escapes — the best keyboard work in the suite | **PARTIAL.** One real sub-floor target: `letters_to_family/activity.css:100` `entry.caption { min-height: 56px }` ≈ 15 mm, specified in px outside `ContentArea`. And Clock's text-only buttons defeat the point for the target user |
| **Manifest goal line** | "Practises the letter sounds the school has already taught. **Not a reading programme.**" | "Seeing how many without counting (up to 5), and which two numbers make 5 and 10. **Practice, not a test.**" | "Playing with a clock: o'clock and half past, and what happens when. **Not a test.**" | "Make a letter for someone in your family: a picture, a few words, your voice. **A grown-up sends it.**" | **All four honest, all four name what they are not. Best in the industry; keep them.** |

### Two live defects in Sounds & Words

1. **The visible prompt prints the answer.** `activity.py:558` renders
   `f"Find the one that says {say_label(gpc)}."` — and `saw-find-it.png` shows
   *"Find the one that says k."* over four tiles one of which is `k`. The task
   is "match a **sound** to a grapheme"; the screen shows the grapheme. The
   prompt should read "Find the one that says …" with a speaker glyph, and the
   grapheme should appear **only in the caption strip**, where it is a deaf
   child's necessary accommodation rather than everyone's answer key.
2. **Every phoneme is a placeholder.** `docs/design/sounds-and-words.md` §12.6
   and `64-first-party-activities.sh` §4 both say so honestly: no real clip
   exists, GCompris's a–z are letter *names* and are shipped inert, and **the
   SDK has no clip player**, so the first real recording will fail as a missing
   player. A phonics activity whose phonemes are TTS spellings ("sss", "ck") is
   not ready to be put in front of a five-year-old who is being taught by a
   school. ~20 recordings, one adult, one morning.

### Letters to family — a blocking bug, verified by hand

**Pressing "Post it" raises `TypeError`, and so does put-away.**
`assemble.py:134` calls its injected `save_entry(..., activity_name=…)`.
`activity.py:719` and `:887` inject `self.app.save_entry`. But
`kidnix_activity/app.py:261-269` is `def save_entry(self, kind, files, caption,
voice, meta, *, keep_sound=True)` — **no `activity_name`, no `**kwargs**` — it
hard-codes `activity_name=self.title` at `:286`. The module-level
`journal.save_entry` does accept the argument; the activity is wired to the
wrapper, not the function. So the child's letter cannot be kept by either
route.

**The tests cannot see it** because the `SaveEntry` Protocol (`assemble.py:55-63`)
and the test fake (`tests/test_assemble.py:44-49`) both declare `**kwargs: Any`.
A Protocol that is wider than the real callee is a test that proves the fake.
That is the lesson worth carrying past this fix: type the seam to the *narrowest*
real implementation.

Otherwise: untracked, ~90% built, no stubs, and the strongest undo story in the
suite. `docs/design/letters-to-family.md` **does not exist**, and both
`manifest.toml` and `README.md` link to it. Correctly not installed. Two
layering notes: it imports `kidnix_shell.sound`/`voice` directly, past the SDK
and undeclared in `pyproject.toml`; and `journal_read.py` is a *second* reader
of the on-disk Journal layout, which will drift.

---

## 4. Parent panel

**Shape of the sandbox, and no surveillance (G1/G4) — MET, and this is the
strongest single answer in the build.** Seven pages (`ui/app.py:61-69`), no
stubs. A grep for `usage.toml|progress.toml|sessions_completed|journal_root`
across the whole package returns **zero hits**; `tests/image/test_parent_panel.sh:279-306`
asserts no counters, no charts, no network, and an honesty page with ≥7 claims.
"Their things" (`parent-panel-things.png`) offers copy / open / print / delete
and says in the child's favour: *"Everything your child has made lives in their
own account, which nothing else on the computer can read — not even you."*

**The four-parent panel's top-5 asks:**

1. *A parent panel, and the PIN first* — **MET.** Panel exists; no `pin_hash`
   ships; `kidnix-set-pin` refuses `1234`; forced-set flow in the gate.
2. *Two children on one machine* — **MET at the panel**, and the in-flight wave
   is pushing per-child allow-lists into the shell. Residual: two children in
   one Unix account still share the activities' own save directories (§23.3).
3. *"Keep it the same" + a quiet one* — **MET** (`activities.py:95` freeze on by
   default; warning times; volume/mute/voice in one place). **The Tux Paint half
   of this ask is not addressed anywhere in the panel.**
4. *A way out for the child's work* — **MET** for export/open/print; family is
   data-only ("Nothing sends anything yet", `family.py:66`).
5. *Install-and-update story* — **PARTIAL.** `PARENTS.md` is the printed page;
   the update button exists and is gated on signature verification
   (`updates.py:245`). No update *notification*.

**Security.** `kidnix-config` is invoked through `pkexec` with
`allow_active=auth_admin_keep`; three verbs only (`apply|show|check`);
`apply` forces the PIN back from disk, re-validates as root, and round-trips
the rendered TOML through the shell's own parsers before writing. `kid` is
refused twice — by `40-kidnix-kid.rules` denying the whole `org.kidnix.` prefix
(sole carve-out `org.kidnix.set-pin`, exact match, build-asserted) and by the
helper's own `is_admin`. **No child path to the parent session was found.**

Three findings worth fixing:

- **`kidnix-config show` is unprivileged and prints `pin_salt` + `pin_hash`.**
  `parent.toml` is 0644 by design, so `cat` gives the same — but a 4-digit PIN
  behind PBKDF2 is a **10,000-candidate offline search**, which bypasses the
  helper's 5-per-60 s rate limiter entirely. The gate's strength is the file
  mode, not the KDF. Either drop the PIN fields from `show`, or move the hash
  to a 0600 file the shell reads through the helper.
- **`kidnix-export [DEST]` takes an arbitrary path**, forwarded verbatim and
  `[[ -w ]]`-checked *as root*, so the guard is vacuous. Not an escalation
  (callers are already wheel) but it is an unvalidated root-side path.
- **`child.name` has no character-class validation** and `toml_str` escapes
  only `\` and `"`. It fails closed only because the round-trip catches it —
  and that check returns `[]` when `kidnix_shell` is not importable.

---

## 5. Regressions and drift since checkpoint 1

Nothing has got *worse* in the shell's behaviour. What has decayed is the
paperwork, and two things were drawn and never wired.

1. **`kidnix-act-all-done-day.svg` is a dead asset.** Wave D drew a day variant
   of the All-done tile; `home.py:118` still hard-codes `icon = "kidnix-moon"`,
   and a grep for `all-done-day` across the whole tree returns **nothing**. The
   contact sheet, the a11y shot and the Polish shot all show a moon on Home at
   four in the afternoon — the exact cue ruling 4 removed from the words.
2. **The GCompris shelf reproduces the icon blocker one level down** (§2 row 7).
   This is new: the shelf did not exist at checkpoint 1.
3. **`docs/design/FLOWS.md` B20** still says `kidnix-parent-panel` "is a
   placeholder that says so loudly". It shipped in commit `8849379`.
4. **Spec §S9 line 104** still documents "default PIN 1234", which is the one
   sentence the panel's most-cited defect made false.
5. **`CHILD-TEST-PROTOCOL.md` contradicts itself** — alternating treatments at
   line 67, ABAB at line 91; and line 73 calls the burst detector unbuilt.
6. **`build_files/75-supply-chain.sh:53-58`** says the cosign key is not in the
   repository. It is (`system_files/etc/pki/containers/kidnix.pub`).
7. **The implementation notes stop at §25.** The i18n wave (`2f2d159`, 239
   msgids, ADR-0012) and the in-flight schedule-windows wave have no section.
8. **Group A of FLOWS covers 28 child flows, none of them an activity.** Four
   activities now exist and no user story describes using one.

---

## 6. Top ten before child test #1

1. **Fix `save_entry(activity_name=…)` in letters-to-family**, and narrow the
   `SaveEntry` Protocol and the test fake so `**kwargs` stops hiding the next
   one. (SDK + activity) Today the child's letter cannot be kept at all.
2. **Give the 18 shelf children their own icons.** (image) Add `icon` to each
   row of `curated.toml` and draw 18 small SVGs, or drop the shelf to the six
   group tiles for the first test. Three identical pictures on a page is not a
   choice for a pre-reader. *Blocks the shelf entirely.*
3. **Cap the choice sets that exceed five and say so in an ADR.** (activity)
   Numbers at `range = "ten"` draws 10 tiles; Clock's Year 2 dial draws 12
   audio-only rim targets; the letters recipient grid is uncapped. B2's ceiling
   is five on a choice screen. Either hold it or write down why not — this is
   the one place we have quietly taken the permissive reading again.
4. **Fix Clock's "How long is a minute" screen.** (activity) Six buttons, five
   of them text-only, for a child who cannot read. Give each an icon, cut to
   ≤5, and fix the mid-syllable hyphenation on the routine strip ("Scho-ol").
5. **Wire `kidnix-act-all-done-day.svg`.** (shell) Switch `AllDone.icon` on
   `is_bedtime`, the same predicate ruling 4 already uses. Two lines and a test.
6. **Record the ~20 phonemes, and add a clip player to the SDK.** (activity)
   Until then Sounds & Words teaches a school's phonemes in a TTS accent.
   *This is the blocker for the deep vertical.*
7. **Stop printing the target grapheme in Find it's visible prompt.** (activity)
   Keep it in the caption strip; replace it on screen with a speaker glyph.
8. **Decide `calm`'s default, and record it.** (docs) The ruling says
   `calm = true`; the code ships `false` with a test pinning it. One of the two
   is wrong and a SEND child's first session depends on which.
9. **Wrap the activities' — and the SDK's — strings in `_()`, and add
   `activities/` to the extractor's scan path** (`shell/Justfile:84`). Note that
   three cases need restructuring, not marking: `clock_time/words.py:279`
   hard-codes English word order, `minute.py:109` has no `ngettext`, and several
   string tests assert exact English equality, which currently pins the strings
   against ever being wrapped.
10. **Fix the paperwork that now lies**: FLOWS B20, spec §S9's 1234,
    CHILD-TEST-PROTOCOL's ABAB and its "detector doesn't exist", the
    supply-chain comment, notes §26, and the missing
    `docs/design/letters-to-family.md`. (docs) A protocol that contradicts
    itself cannot be run by a second coder.

*Not in the ten, deliberately:* the band's Undo sentence being false inside
first-party activities (real, and the caption socket shows the reverse channel
is cheap — but it is a design decision, not a fix); `kidnix-config show`'s PIN
exposure and `kidnix-export`'s path; `letters`' 15 mm caption box; the 24 mm
constant; the switch scan; per-profile export.

---

## 7. Verdict

**The panel got what it asked for.** Ten of fourteen rulings are met with named
tests behind them, and the four that are partial are partial in named,
tractable ways — one default value, one dead asset, one set of missing icons,
one self-contradictory doc. The session arithmetic, the consequential offer,
the inverted Goodbye, the two vocabularies, the pinned escape hatch, the
caption invariant, the 20 mm floor, the per-profile data, the PIN that no
longer ships, the research logging that ships off: all of it landed, and most
of it landed with an AST-walking test that will catch the regression rather
than a comment asking not to cause one. The parent panel is the answer to
Sugar's fatal wound and it contains no dashboard of the child. That is a very
good six weeks.

**The activities are younger than the shell, and it shows — in one particular
way.** What they get *right* is the hard, philosophical half: no scores anywhere
(Numbers AST-parses its own source against a 26-word ban-list, and Sounds &
Words refuses to render "3 words" because that is "a score with a friendly face
on it"), honest goal lines on all four, no network, no adaptivity beyond a
readable Leitner box, and a wrong answer that is answered rather than marked.
What they get wrong is the arithmetic and the plumbing — the same split the
developmental psychologist named about the shell in the first place. Three of
four exceed the five-choice ceiling. None of four is localised, three commits
after the shell was. Sounds & Words prints its own answer and says the phonemes
wrong. And letters-to-family — the activity 05 §3 calls the strongest in the
list — cannot save the letter, because a Protocol was written wider than the
function behind it.

**So: test the shell, again, not the system.** The honest framing from
checkpoint 1 holds one layer up. The shell is ready for a child. Of the
activities, Numbers is ready at its default range, Clock after item 4, Sounds &
Words not until item 6, and Letters not until item 1. Do items 1–5 and 10 — a
day's work, all of it small and all of it named — and the first session will
measure the design rather than the missing pictures.

One thing to keep saying out loud: nothing in this audit is evidence about
children. It is evidence about whether we did what we said. The panel's own
first line still stands — *an unusually good design rationale with zero
children in it.*
