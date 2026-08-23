# kidnix — user stories and flows

> Thinker's catalogue, 2026-08-23. Written because we had never written one:
> the spec describes *surfaces*, the implementation notes *changes*, the
> reviews *defects*. Nothing said, end to end, what a person does and what the
> machine does back. Sources: spec §2/§7a–7d, impl. notes §16–§23, SYNTHESIS
> §1–2, the panel synthesis, `PARENTS.md`, `BUILDING.md`, `SUITE.md`.
>
> Steps are what we intend; **Coverage** is what we can prove. Every spoken
> line is captioned (v0.1.8), so "**says**" means says-and-shows.
> **COVERED** — a test drives the flow on the shipped artefact. **PARTIAL** —
> headless/GTK tests prove the logic, or one branch of several is driven.
> **UNCOVERED** — the named test is the one to add. Tests live in
> `tests/e2e/test_scenario.py`, `tests/e2e/test_flows.py`, `shell/tests/`,
> `tests/image/`, `tests/boot/`.

---

# A. The child

### A1 · The very first session — Who's here?
**Child, 4–6, pre-reader.** As a child who cannot read, I want the computer to greet me by picture so I can start alone.
**Pre** fresh install, PIN set, budget unspent, not bedtime.
1. Lid opens → autologin → **band** (tinted strip, sun centred) + **S1**: avatar ≥ 30 mm with its badge; plain grown-up tile bottom-right, unvoiced.
2. Hover or Tab · **says** the child's name; a focus ring is present on arrival.
3. Press the face → profile data swapped in *before* the clock starts → `CHOOSING → NEXT_CHOICE`.
**Accept** service active; `shell geometry ok`; one focused node on arrival; `session started` logged *after* the profile swap.
**Evidence** spec §S1, §7d #11; impl. §23.3; SYNTHESIS need #6.
**Coverage** **COVERED** — e2e `test_01`, `test_02`; `test_profiles.py`, `test_state.py`.

### A2 · What's next after?
**Child.** As a child I want to choose what I do *after* the computer, so that stopping is going somewhere.
1. Titled grid, ≤ `choice_per_page`, Home's tile size · **says** the heading, then each option on focus ("Going outside").
2. Press one → held on `ctx.next_after` → HOME. "Not sure" clears it; Goodbye falls back to a generated line.
3. Back → Who's here **and stops the clock**. The ending *offer* never fires here; the hard stop does.
**Accept** the chosen id reaches Goodbye's spoken line; ≤ 9 options; a malformed one costs a tile, not the screen; `skip_next_choice` bypasses it.
**Evidence** spec §7b, §7d #5; SYNTHESIS D4 (Coco's Videos, CHI 2018); impl. §17.1, §21.7.
**Coverage** **PARTIAL** — e2e `test_02`/`test_06` pick option 0 and assert the echo; `test_next_after.py`. **Add:** "Not sure", and Back-stops-the-clock.

### A3 · Home, first run
**Child.** As a new user I want a small, stable grid so I learn where things are.
1. Tiles ≥ 40 mm, gaps ≥ 8 mm, depictive icon + Andika label ≥ 18 pt; recent work is a **corner badge**, never the picture.
2. "All done" pinned to cell 7; activities grow around it, leaving holes.
3. Focus/hover **says** the label; page dots and ≥ 20 mm arrows beyond one page; no scrolling anywhere.
**Accept** every tile ≥ 20 mm *measured*; All done in the same cell on every panel; no tile for anything missing, empty or out of band.
**Evidence** spec §S2, §7d #5/#6; SYNTHESIS B1–B2; ADR-0011.
**Coverage** **PARTIAL** — e2e `test_02` (first row), `test_metrics.py`, `test_gtk_smoke.py`. **Conflict:** §7d #5 rules disclosure off, impl. §21.7 ships `show_everything = true`, e2e `test_02`'s comment assumes a 4+2 grid.

### A4 · An ordinary session — pick something
**Child.** As a child I want to press a picture and have that thing fill the screen.
1. Press **Draw** (on press; idempotent under burst-clicking) · tap earcon · `HOME → IN_ACTIVITY`.
2. Clean env under the kid home; gnome-kiosk gives the activity the rectangle *below* the band, which stays up throughout.
**Accept** `launched tuxpaint`; band buttons findable mid-activity; the rows under the band are the activity's pixels; a second press starts no second process.
**Evidence** spec §S3; SYNTHESIS B3, A3; impl. §18.1–§18.4.
**Coverage** **COVERED** — e2e `test_04`; `test_kiosk.py`, `test_launcher.py`.

### A5 · Make something, and keep it without being asked
**Child.** As a child I want what I make kept, with no save question.
1. The activity autosaves; the importer sees the file (debounced 2 s) and copies it into `profiles/<id>/journal/YYYY/MM/DD/<entry>/` with a thumbnail.
2. **Keep earcon** (paper gathered up). Nothing modal.
**Accept** one `entry.json` per made thing; open formats; no save prompt ever; the entry lands under the logged-in profile.
**Evidence** SYNTHESIS C1, F1; spec §5.
**Coverage** **COVERED** — e2e `test_04`; `test_journal.py`. **Limit:** activities share save directories, so entries follow whoever is logged in (impl. §23.3).

### A6 · My Things — resume, and star
**Child.** As a child I want to press my picture and be back inside it, not shown a menu about it.
1. **My Things** → JOURNAL (from an activity, it ends the activity first).
2. ≤ 8 starred things, then Today / Yesterday / Before; cards ≥ 20 mm, star + ear badge; headings **spoken**; a card **says** "Draw, from this morning" — never a digit.
3. Press a card = **resume** (`exec_resume`, else plain launch and "Open Draw to find it"). Star toggles; Undo un-stars. No delete.
**Accept** no spoken string contains a digit; a card resumes rather than opening a viewer; pagination, never scrolling.
**Evidence** spec §S4, §7a; SYNTHESIS F1–F3; impl. §16.7.
**Coverage** **COVERED** — e2e `test_flows.py::test_a6_a_journal_card_resumes` presses a card on the shipped image and asserts the launch and that the activity takes the screen; e2e `test_05`; `test_journal.py`. **Limit:** the shipped `tuxpaint.toml` declares no `exec_resume`, so what is driven is the *plain-launch* branch and the argv is asserted to carry no file. **Add:** an activity that really resumes into its own file.

### A7 · The shelf — Letters and numbers
**Child.** As a child I want a heading and three pictures, not a menu of 198.
1. Press the shelf tile → SHELF. One group per page, heading written and **spoken** on the page turn.
2. A child tile launches like any other; Back from it returns **to the shelf**; Back from the shelf goes Home. No "All done" here.
**Accept** an empty shelf draws no tile; the age band filters the children, not the shelf.
**Evidence** spec §7d #12; panel teacher #12; impl. §23.1.
**Coverage** **PARTIAL** — `test_shelf.py`, `test_gtk_smoke.py`. **Add:** e2e opening the shelf and launching one child.

### A8 · Hover to hear it, and the Ear
**Pre-reader.** As a child who cannot read I want to rest the pointer on something and be told what it is.
1. Dwell runs only while pointer velocity < 40 px/s over 150 ms; at 450 ms it **says** the label once and paints the ring. Sweeping says nothing.
2. Keyboard focus speaks immediately, ungated. **Ear** repeats the last utterance on any surface.
**Accept** one utterance per settle; new speech cancels rather than queues; `hover-speech:` lines only when `research.toml` says so.
**Evidence** spec §3, §7b; SYNTHESIS B4; impl. §17.3, §23.5.
**Coverage** **PARTIAL** — e2e `test_03` proves the ring paints; `test_speech.py`. **Add:** e2e press of the Ear.

### A9 · Ask the sun
**Child.** As a child I want to know how much is left, in words I own.
1. The sun's **height and size** fall; a ghost outline marks where it began; x never moves; it warms in the last window.
2. Press or hover · **says** "Lots of time left." / "About as long as one story." / "A little bit of time left." / "Nearly time to put things away." / "The sun has gone down for today."
**Accept** radius strictly decreasing; no digits anywhere; the sun held **down** from Ending offer through Sleeping, reset only on entering CHOOSING.
**Evidence** spec §7b, §7d #3; SYNTHESIS D3 (Tillman 2018); impl. §16.9, §17.2, §21.4.
**Coverage** **PARTIAL** — `test_sun.py`, `test_session.py`. **Add:** e2e tap of the sun; a pixel check that it is low at Goodbye.

### A10 · Back, from inside an activity
**Child.** As a child I want one way out, always in the same place.
1. Press **Back** → the shell asks the activity to finish (one SIGTERM, **no SIGKILL**) and waits.
2. A `confirm` activity puts its own tick/cross up; after `quit_grace` the band **says** "Draw is asking if you're done."
3. Press the tick → autosave → exit → HOME (or back to the shelf it came from).
**Accept** Back never kills; the drawing survives; Back on Home only **says** "You're home"; no exit friction but the 3 s guard on Put away.
**Evidence** spec §7c; SYNTHESIS D6 (Kuo, Zhao & Scott 2026); impl. §19.2, §20.2.
**Coverage** **COVERED** — e2e `test_04` (Back → find the tick by colour → tap → Home → Journal entry).

### A11 · Undo, inside an activity
**Child.** As a child I want the Undo button to be honest.
1. Press **Undo** mid-activity · **says** "Undo in Draw is Control and Z." where the manifest names `undo_key`, else "Undo for Draw is in Draw's own buttons."
2. Nothing to undo on a shell surface · **says** "Nothing to undo." The control never disappears.
**Accept** the shell never synthesises input into another Wayland client; the sentence names the activity.
**Evidence** spec §7a; impl. §18.4, §23.6.
**Coverage** **PARTIAL** — `test_gtk_smoke.py` (both sentences). **Add:** e2e press of Undo mid-activity.

### A12 · The ending offer arrives while drawing
**Child, mid-activity.** As a child I want to be told the light has changed without losing sight of my drawing.
**Pre** `ENDING_OFFER` at `clamp(20% of granted, 2–4 min)`.
1. Phase earcon (a falling fourth, quietest of five); the sun is low and warm.
2. The band **adds** "Finish this one" and "One last little thing" beside Undo and My Things, which keep their cells; 350 ms scale-in, 3 s of the reserved highlight, the question **said** once.
3. Nothing is raised over the activity; an unanswered offer latches after 20 s.
**Accept** pixels below the band unchanged; `ending offer, in the band` exactly once; the band does not re-flow.
**Evidence** spec §7d #2; panel #55/#57/#61; impl. §18.5, §21.3.
**Coverage** **COVERED** — e2e `test_06`.

### A13 · Answering the offer, and the words being true
**Child.**
1. **"Finish this one"** → put-away deferred to T−1 · **says** "Finish this one. When the sun is down, we'll keep it."
2. **"One last little thing"** → returns to **Home**; put-away stays put · **says** "One last little thing, then we'll keep it."
**Accept** the two answers do measurably different things to the clock; a deferral can only move the ending later (`min()`); `offer < granted/2` and `put_away < offer` on every reachable grant.
**Evidence** spec §7d #2; panel blocker "a promise the clock doesn't keep"; impl. §21.1–§21.2.
**Coverage** **PARTIAL** — `test_session.py`, `test_ritual.py`; e2e `test_06` presses a button but asserts nothing about the deferral. **Add:** that timing assertion.

### A14 · "Ask for more time"
**Child.** As a child I want to be able to ask without being handed a negotiation.
1. Press the small third option · **says** "A grown-up can add time." · dismissed. Nobody named, nothing promised, no adult summoned.
**Accept** no "go and ask", no parent's name, no "See you tomorrow" — an AST walk over the package's literals asserts it.
**Evidence** spec §7d #1/#2; panel §3; impl. §21.2, §21.5.
**Coverage** **PARTIAL** — `test_ritual.py`. **Add:** e2e press of ASK.

### A15 · Put away — via the activity's own tick
**Child.** As a child I want the program I am in to ask me to finish, and not have my drawing taken.
**Pre** `PUT_AWAY` at `clamp(10%, 1–2 min)`; `quit = "confirm"`, `quit_grace = 30`.
1. **Nothing is raised.** Journal swept; one SIGTERM sent.
2. The band strips to Back / sun / Ear (Back now means *finish*) · **says** "Let's keep that. Press the tick." (a `signal` activity: "Let's keep that.").
3. One more ask after the grace. Once — never a repeating timer.
4. The child presses the tick → autosave → exit → **now** S6, keep earcon, work flies into My Things.
**Accept** `-> put_away` never before the activity has gone; the process alive while the question is up; no "unsaved work possible"; the Journal grew.
**Evidence** spec §7c; panel blocker (Tux Paint's quit dialog *is* the save step); impl. §19.3, §20.2.
**Coverage** **COVERED** — e2e `test_06`.

### A16 · "Let's keep that" — tell me about it
**Child.** As a child I want to say what my picture is.
1. S6 shows the kept thing and a **mic button** — only if a microphone and an Ogg encoder were found at start-up.
2. Press to record with a level meter; press again or 20 s stops it; `note.ogg` lands inside the entry directory. A second recording replaces the first after one quiet "Again?".
**Accept** no transcription, nothing sent, no instrumentation; `kidnix-export` takes the note and `kidnix-wipe` deletes it; no mic button without a mic.
**Evidence** spec §7d #9; SYNTHESIS §4 (Draw); impl. §23.2.
**Coverage** **PARTIAL** — `test_voice.py`, `test_gtk_smoke.py`. **Add:** the VM has no audio input, so assert the *absence* path until a virtual source exists.

### A17 · Goodbye, led by where they are going
**Child.** As a child I want the ending to be the best screen, not the emptiest.
1. Destination picture ≥ 40 mm · "Ready to go outside?" · up to 3 thumbnails · one line of descriptive feedback ("You drew two pictures and used five colours.") · "Show a grown-up" and "Goodnight"/"Resting".
2. Spoken in that order, destination **last, as its own sentence**.
3. "Show a grown-up" → `SHOWING`: read-only Journal, 600 s, voice notes playable, never revoked mid-narration.
**Accept** "Show a grown-up" never hidden, even on a day nothing was made; the count counts only what the Journal holds; no return promises in daytime.
**Evidence** spec §7d #3; SYNTHESIS E1; impl. §21.5, §23.7.
**Coverage** **PARTIAL** — e2e `test_06` asserts the "Ready to …" line. **Add:** the feedback line, and that S7 is not clipped at 1280×800 (it regressed once).

### A18 · Goodnight → Sleeping (bedtime)
**Child, after 19:00.**
1. Press **Goodnight** → SLEEPING; sleep earcon (a yawn), moon, the **whole content window** and band strip dim navy.
2. A tap · **says** "kidnix is sleeping." — at most once per 8 s, never cut mid-word, silent after three taps in 30 s.
3. The gate stays reachable; Sleeping ends at the next allowed window, a new day, or an unlock.
**Accept** the dim is on the *windows*, not a centred box; the band window stays mapped (unmapping loses its placement).
**Evidence** spec §S8, §7a, §7d #4; impl. §18.6, §21.6.
**Coverage** **PARTIAL** — e2e `test_flows.py::test_a18_bedtime_speaks_night_words_and_sleeps` writes a policy whose window contains the *guest's* now and asserts "It's night time. kidnix is going to sleep." and a dim navy surface painted on the whole window; `test_resting.py`. **Limit:** the route is the refusal at Who's here, because a session cannot *start* at bedtime — the moon at the end of a sitting still needs the clock stepped over `bedtime_start` mid-session (C10). e2e `test_06` reaches `sleeping` in daytime, so it exercises A19's screen while asserting the `goodnight` event.

### A19 · Resting (daytime) — and a dysregulated child
**Child at 4 pm; or a child in distress.**
1. `is_bedtime` false → **Resting**: warm, dim, no moon, no yawn · **says** "kidnix is resting. Back after tea." / "…Back tomorrow.", from `next_allowed`.
2. A child hammering the screen gets one line then silence: presses inside 8 s are **ignored** (not queued, not cut off); nothing after three in 30 s.
3. The line demands nothing — no "Ask a grown-up", no return promise.
**Accept** no night vocabulary before `bedtime_start`; the third tap in 30 s produces silence.
**Evidence** spec §7d #4; panel MH #17/#23, child-psych #31; impl. §21.6.
**Coverage** **PARTIAL** — e2e `test_flows.py::test_a20_all_done_ends_the_session_and_a19_it_rests` ends a daytime sitting and asserts the resting line, the warm surface and the *absence* of "kidnix is sleeping."; the other vocabulary is A18's test, so both are now proved on the image. `test_resting.py`, `demo-resting.png`. **Add:** the dysregulated half — three presses in 30 s earning silence.

### A20 · "All done" — the child ends it
**Child.** As a child I want to stop when I have had enough, and get the same ending.
1. Press **All done** (pinned cell, moon/bed icon) · **says** "All done for today?" · one tap, **no confirmation, no bribe** → PUT_AWAY.
2. The same ritual from S6 on. Back on Put away is inert 3 s (accidental-tap guard), then Home.
**Accept** All done reaches Put away in one event from Home, an activity, My Things and S1b; the back-delay table has exactly one row.
**Evidence** spec §7a, §7d #5; SYNTHESIS D5 (children ended early 31% of the time); impl. §17.7, §21.7.
**Coverage** **COVERED** — e2e `test_flows.py::test_a20_all_done_ends_the_session_and_a19_it_rests` finds the lavender tile by colour (it is the only control whose fill is not paper), checks it is the last cell of its row, presses it once, and asserts Put away in one event with nothing in between asking the child to confirm; `test_ritual.py`, `test_gtk_smoke.py`. Also driven by key in `test_a25_a_whole_session_on_the_keyboard`.

### A21 · The session refused at the door
**Child whose budget is spent, or who arrives at bedtime.**
1. Press the face. `may_start` refuses **before** What's-next-after — before any plan is collected.
2. Resting/Sleeping for the reason · **says**, in daytime words, "That's all the computer time for today. Ready to go and play?"
**Accept** the refusal is at Who's here, never after a plan; a grant the budget would truncate below `min_session_minutes` (5, floor 3) is refused whole; no session begins outside `Phase.RUNNING`.
**Evidence** spec §7d #1; panel blocker "session arithmetic"; impl. §21.1.
**Coverage** **COVERED** — e2e `test_flows.py::test_a21_the_session_is_refused_at_whos_here` gives the day one minute against a three-minute floor, presses the face, and asserts the daytime refusal *and* that `NEXT_CHOICE` was never entered and no clock started; `test_session.py` (invariants over every reachable grant); `--start-on resting` earns the refusal for the screenshot.

### A22 · An activity that fails to open
**Child.** As a child I want the machine to go back to something I recognise, not show me an error.
1. Press a tile; the process exits non-zero or never maps a window.
2. Return to HOME · **says** a friendly line; the detail goes to the journal for the parent only. No adult error text, no modal.
**Accept** the child is never left on a blank screen; `IN_ACTIVITY` is always left through one path (`_activity_finished`); the failure is one log line.
**Evidence** SYNTHESIS C3; AGENTS §3 #8; impl. §19.2 (the "sat in IN_ACTIVITY with nothing on screen" regression).
**Coverage** **COVERED** — e2e `test_flows.py::test_a22_an_activity_that_fails_to_open` drops a manifest pointing at `/bin/false` into the kid's own activity directory, presses its tile, and asserts the friendly line, the single WARNING with the reason, and Home with tiles on it. **Add:** the other half of step 1 — a program that starts and never maps a window — plus a `--demo` failure mode (the demo has five; none is "exec fails").

### A23 · Tiles not allowed, not ready, or not for them
**Child.**
1. **Not on the allow-list** → outline-only · **says** "Ask a grown-up for this one."
2. **Program missing / `content_required` unmatched** → outline or no tile · **says** "This one isn't ready yet. Ask a grown-up."
3. **Outside the age band** → **no tile at all**; an empty shelf likewise.
**Accept** outline edges ≥ 3:1 on paper; an empty `allowed_activity_ids` means *everything*, never nothing; no tile opens something empty.
**Evidence** SYNTHESIS G3, B8; impl. §16.2–§16.5, §23.1.
**Coverage** **PARTIAL** — `--demo` reproduces five failure modes; `test_activities.py`, `test_theme_css.py`. **Add:** e2e assertion of one outline tile and one absent tile.

### A24 · Two children, one machine
**Two siblings.** As the second child I want my own things and my own time.
1. Who's here shows both faces, each with its own colour **and badge** (colour is never the sole carrier).
2. Choosing a face swaps journal, budget and progress to `profiles/<id>/…` before the clock starts.
3. A pre-profiles machine migrates into the **first** profile once, idempotently, never overwriting.
**Accept** independent budgets; the migration never loses a Journal; colour pairs ≥ 0.40 apart under deuteranopia and protanopia.
**Evidence** SYNTHESIS need #6; spec §7d #11; impl. §22.4, §23.3.
**Coverage** **PARTIAL** — `test_profiles.py`, `test_theme_css.py`. **Limit:** activities share save directories (impl. §23.9 #2). **Add:** e2e with two profiles.

### A25 · A child who cannot use a pointer
**Child using a keyboard, or a switch.**
1. One key controller on **both** toplevels, capture phase; Tab/arrows are one cycle, **band first**; the ring is the shell's (`.kid-focus`), so it draws on the toplevel the compositor has not focused.
2. Focus lands on every arrival; **Escape is Back**. The gate: Enter/Space **held 3 s**, or five presses inside 3 s (a switch cannot hold).
**Accept** a whole session completes on key values alone; nothing raises the content window to chase the ring over a drawing.
**Evidence** spec §7d #7; panel a11y #8/#21; impl. §22.1.
**Coverage** **PARTIAL** — e2e `test_flows.py::test_a25_a_whole_session_on_the_keyboard` drives Who's here → What's next after → My Things → Home → Draw → All done on Tab/Enter/Escape over QMP, reading the ring's position from the shell's own focus speech, and asserts `.kid-focus` paints on the content window; `test_gtk_smoke.py::test_a_whole_session_without_touching_the_mouse`, `test_access.py`. **Finding, measured on the image:** inside an activity the compositor gives the keyboard to the *activity's* toplevel, so Escape never reaches the shell's Back — on Tux Paint it raises Tux Paint's own quit key instead, and the SIGTERM the band later sends dismisses that prompt rather than answering it. **Leaving an activity is the one step of a session a switch user cannot take**, so "a whole session completes on key values alone" is not yet true here; it wants a fix or an ADR, not a quieter test.

### A26 · A deaf or hard-of-hearing child
**Child.** As a child who cannot hear the voice I want to read every line.
1. Every spoken line appears in the **caption strip** for 4 s, 20 pt ink on paper (16.6:1) — including when speech-dispatcher is dead.
2. The strip lives in the **band window**, so put-away and the offer are readable while an activity covers the content window.
**Accept** the hook is inside `SpeechManager.speak` *before* the enabled check; an AST walk fails on any `.speak(` whose receiver is not the manager; the longest line fits at 18 pt on the narrowest panel.
**Evidence** spec §7d #7; AGENTS §3 #4; impl. §22.2.
**Coverage** **COVERED** — e2e asserts ink in the caption strip's own rows (parsed out of the shell's `display metrics:` line) at the two moments that matter: put-away with no activity (`test_a20_…`, 2.9% ink on blank paper) and put-away *over Tux Paint's own quit prompt* (`test_a28_…`, 4.3%); `test_access.py`, `test_gtk_smoke.py`.

### A27 · A child who needs it calm
**Autistic / sensory-defensive / anxious child.**
1. `calm = true` is **one switch**: the stack cuts instead of sliding, the offer arrives without its scale-in, the put-away flight is skipped, only the `keep` earcon plays, the voice slows.
2. `gtk-enable-animations` is honoured; volume/mute exist, and **mute is safe because captions default on**. Every earcon attacks over ≥ 150 ms.
**Accept** one switch, not four settings; a muted shell still shows every line.
**Evidence** spec §7d #7; SYNTHESIS H6; impl. §22.3.
**Coverage** **PARTIAL** — `test_access.py`, `test_sound.py`, `demo-a11y-*.png`. **Open:** the 150 ms attack costs press-feedback latency on `tap` (impl. §22.7 #1).

### A28 · The hard stop, and telling the truth about it
**Child whose activity never answered.**
1. At T−0 the shell SIGKILLs, logs `put-away: killed <id> with unsaved work possible` (WARNING) and sets `ctx.work_lost`.
2. S6 becomes **"Time to stop now."** — no keep earcon, no flight: nothing flew anywhere.
3. Goodbye counts only `journal.made_on_today()`, so nothing claims to have kept what was destroyed.
**Accept** the three sentences live in one pure function; the kill happens once; `HARD_STOP` is unreachable outside `IN_ACTIVITY`.
**Evidence** spec §7c; impl. §19.3, §20.3.
**Coverage** **COVERED** — e2e `test_flows.py::test_a28_the_hard_stop_tells_the_truth` runs a three-minute sitting with a stroke on the canvas and the tick left unanswered, on an emptied Journal, and asserts all three audiences at once: one WARNING `killed tuxpaint with unsaved work possible`, "Time to stop now." spoken instead of "Let's keep that", and a Goodbye that claims nothing because nothing reached the Journal. `test_ritual.py`, `test_launcher.py`, plus a live `--demo` run.

---

# B. The parent

### B1 · Install it on a laptop
**Parent, or the friend doing it for them.** As a parent I want one old laptop turned into my child's computer, knowing what I give up.
1. `BUILDING.md`'s four warnings: the disk is **erased**; `parent` must get a password or key **at install time**; the disk is **not encrypted**; **nothing is backed up**.
2. Install, create `parent` with a credential, and **log in as `parent` once before handing it over**.
**Accept** an image installed with no password and no key leaves `parent` locked and the machine unrecoverable without a rescue stick.
**Evidence** `BUILDING.md` §⚠1–4; panel parents.
**Coverage** **UNCOVERED** (documentation only). **Add:** a greenboot check that `parent` has a usable credential.

### B2 · First boot: set the PIN
**Parent, before the child touches it.**
1. Hold the plain corner tile 3 s (or the keyboard/switch equivalent).
2. The sheet opens on **"This machine has no grown-up PIN yet"** — a pad, twice, nothing else reachable; 1234 is refused.
3. It writes `parent.toml` if it can; else `pkexec kidnix-set-pin --stdin`; else it keeps the PIN **for the session** and names the command that makes it permanent.
**Accept** the shipped file carries no `pin_hash`/`pin_salt` *and* the shell demands one; changing a PIN needs the current one; never in `argv`; failure is free, silent, logged without digits.
**Evidence** spec §7d #11; panel Mags #13, safety #44; impl. §21.8, §23.4.
**Coverage** **PARTIAL** — `test_hardening.sh` (both assertions, `--stdin`, polkit refusal for `kid`), `test_gtk_smoke.py`. **Add:** the three VM checks in impl. §23.4.

### B3 · Add or rename a child
**Parent.** As a parent of two I want a second face on the machine.
1. Edit `[[profile]]` in `/etc/kidnix/parent.toml`: name, colours, badge, age band, `skip_next_choice`. Restart the shell.
**Accept** a malformed profile costs one face and a log line, never a session; an unparsable `age_band` filters nothing — we do not guess a child's age from silence.
**Evidence** spec §S1, §7d #11; SYNTHESIS need #6, G1.
**Coverage** **UNCOVERED** — no UI exists; a root-owned text file. Belongs to parent panel v0 (`SUITE.md` §4).

### B4 · Set the session length and the daily budget
**Parent.**
1. Gate → **Default session length** (holds for the boot), or edit `session.toml`: `length_minutes` 25 (10–45), `daily_budget_minutes` 60, `min_session_minutes` 5 (floor 3). Ending windows follow proportionally; both window keys are **ceilings**.
**Accept** every unparseable value falls back with a warning and never stops a child logging in; the file is root-owned and 3-way-merged.
**Evidence** spec §6, §7d #1; SYNTHESIS D1; impl. §21.1.
**Coverage** **PARTIAL** — `test_settings.py`, `test_session.py`; the e2e rewrites the policy over ssh every run, so the read path is exercised on the image.

### B5 · Bedtime, and a schedule
**Parent.**
1. `bedtime_start`/`bedtime_end` (19:00–07:00; equal values switch it off). Outside: Sleeping. Daytime: Resting says *when* it comes back.
**Accept** `is_bedtime` handles the wrap over midnight; `next_allowed` is the later of the bedtime gate and the 04:00 budget reset.
**Evidence** spec §6, §7a, §7d #4; SYNTHESIS D1.
**Coverage** **PARTIAL** for bedtime (`test_session.py`, `test_resting.py`); **schedule windows are unbuilt** — D1 asks for windows matching household boundaries and only one range exists (impl. §21.10 #2).

### B6 · Choose which tiles exist
**Parent.** As a parent I want five things on the screen, not twelve.
1. Set `allowed_activity_ids`; empty *and* absent both mean **everything**.
2. Not-allowed activities render outline-only and speak the Ask line; the age band removes rather than outlines.
**Accept** unticking the last box can never produce a Home with no way out; both copies of `parent.toml` stay byte-identical.
**Evidence** SYNTHESIS G1, need #1; impl. §16.4.
**Coverage** **PARTIAL** — `test_settings.py`, `test_hardening.sh`. **Add:** parent panel v0.

### B7 · "Keep the grid the same"
**Parent.** As a parent I do not want a new button appearing every fortnight.
1. `[home] show_everything` defaults **true**: progressive disclosure is opt-in.
2. If enabled: `initial_tiles = 6` (counting All done), one more every 2 sessions in manifest `order`; a revealed tile never goes away; All done keeps its cell.
**Accept** the counter is not a streak — nothing shows it to the child, and a corrupt file costs tiles, not a session.
**Evidence** spec §7d #5; panel §3; impl. §17.4, §21.7.
**Coverage** **PARTIAL** — `test_settings.py`. **Flag:** e2e `test_02` still documents the old default (A3).

### B8 · Calm, volume, captions
**Parent.**
1. Gate → Sound and calm: **Volume**, **Mute** ("Silence, not a broken machine: every line is still captioned"), **Calm mode**, **Captions** (on by default). Permanent values live in `[access]`.
**Accept** sheet changes hold for one boot and say so; captions cannot be silently lost.
**Evidence** spec §7d #7; impl. §22.3.
**Coverage** **PARTIAL** — `test_access.py`, `test_gtk_smoke.py`. **Open:** impl. §22.7 #6 — no panel owns it.

### B9 · Grant more time
**Parent, invited by the child's "Ask for more time".**
1. Gate → **Add time** +5 / +15 / +30.
2. A grant the budget would truncate below the floor is **refused whole, in words, with the minimum named**: "Not added. Today's budget has N minutes…".
3. A grant landing while the shell waits for put-away cancels the wait and returns the phase to RUNNING.
**Accept** no grant produces a sitting shorter than `min_session`; a soft stop, never a hard cut; the child is never told a parent's name.
**Evidence** spec §7d #1; SYNTHESIS D7; impl. §21.1, §21.8, §20.5.
**Coverage** **PARTIAL** — `test_session.py` (`may_add`, `grant_refusal`), `test_gtk_smoke.py`. **Add:** e2e grant mid-session.

### B10 · End the session now
**Parent.**
1. Gate → **End the session now** ("Runs the same put-away and goodbye the child knows") → the identical ritual.
**Accept** the parent never ends it *at* the child — the machine does, in the same words as always (SYNTHESIS D2: never "your mum said stop").
**Evidence** spec §S9; SYNTHESIS D2; impl. §20.5.
**Coverage** **PARTIAL** — `test_gtk_smoke.py`. **Add:** e2e via the gate.

### B11 · See what they made
**Parent.**
1. With the child: "Show a grown-up" at Goodbye → read-only Journal, 600 s, voice notes playable.
2. Alone: a plain directory tree — `entry.json`, `v001.png`, `thumb.png`, `note.ogg` — in Files. No dashboard, no metrics, no time-on-device chart.
**Accept** nothing in the parent's view is a surveillance metric; open formats only.
**Evidence** SYNTHESIS F4, G1/G4; spec §5.
**Coverage** **UNCOVERED** on the parent side (there is no parent view); showing mode is `test_gtk_smoke.py` only. **Add:** an e2e press of "Show a grown-up".

### B12 · Get the drawings out
**Parent.** As a parent I want my child's work off this machine before the laptop dies.
1. Terminal on `parent` → `kidnix-export` (polkit asks for the *parent's* password) → `~/kidnix-kid-<date>.tar.gz`; a path argument writes to a USB stick.
**Accept** `kid` cannot authorise it (polkit denies every `org.kidnix.*` action); the archive holds journal, drawings and voice notes.
**Evidence** spec §7d #11; panel safety #10, Tom #16; `PARENTS.md`.
**Coverage** **PARTIAL** — `test_supply_chain.sh` (exists, executable, child refused). **Add:** a VM test that runs it and untars the result.

### B13 · Wipe it, or hand it on
**Parent.**
1. `kidnix-wipe` lists exactly what it will delete and does nothing until the parent types `DELETE`; accounts stay.
2. Handing it on also means a new PIN, a new parent password, and knowing the disk is not encrypted.
**Accept** no deletion without the typed word; `kidnix-export` is offered first.
**Evidence** panel safety; `PARENTS.md`; `BUILDING.md` §⚠3.
**Coverage** **PARTIAL** — `test_supply_chain.sh`. **Add:** a VM test of the confirm-word path.

### B14 · Print one
**Parent + child.** As a parent I want to put it on the fridge.
1. From a Journal card in showing mode: Print. **Not built.**
**Accept** F3 names Print / Send to family / Put away as card actions.
**Evidence** SYNTHESIS F3; `SUITE.md` §1.
**Coverage** **UNCOVERED** (unimplemented). Today's route is `kidnix-export` and printing the PNG.

### B15 · Update the machine
**Parent.**
1. Today a grown-up runs `bootc upgrade`. **There is no button, deliberately.**
2. The policy demands a cosign signature from `/etc/pki/containers/kidnix.pub`; that key is not in the repo, so the published image **refuses to pull** — intended.
3. Nothing is scheduled; nothing reboots overnight.
**Accept** no update button before the signature policy closes; enforcement is fixed at install/switch time.
**Evidence** SYNTHESIS G5; panel safety #25, Tom #58; `BUILDING.md`.
**Coverage** **PARTIAL** — `test_supply_chain.sh`. **Add:** once the key exists, a VM test of a signed upgrade *and* a rejected unsigned one.

### B16 · Roll back a bad update
**Parent.**
1. `sudo bootc rollback`; or a failed greenboot check rolls back automatically at the next boot (required: accounts, egress, session).
**Accept** a boot whose required checks fail returns to the last deployment that worked, unattended.
**Evidence** AGENTS §3 #8; SYNTHESIS I1, G5; `usr/lib/greenboot/check/`.
**Coverage** **UNCOVERED** — the checks ship, but **nothing ever fails one on purpose**. The largest untested safety claim on the machine.

### B17 · "It won't start"
**Parent on the sofa.**
1. Blank/grey > 1 min → hold power 10 s, press again; it returns to the last version that worked.
2. A grey desktop or login box **is** the parent desktop — log in as `parent`; nothing is lost.
3. A password nobody has = rescue stick only (B1).
**Accept** every branch is something a non-technical adult can do without a second machine.
**Evidence** `PARENTS.md`; AGENTS §3 #8.
**Coverage** **UNCOVERED**. **Add:** a boot test for the fallback to the parent session when the shell fails, and one that the one-window fallback fires (impl. §19.5 #2: it never has).

### B18 · Lost PIN
**Parent.** As a parent whose child set the PIN first, I want back in.
1. Terminal on `parent` → `sudo kidnix-set-pin --reset` → their own password, then the new PIN twice. Nothing the child made is touched.
**Accept** the reset needs a system credential, not the old PIN; `kid` cannot run it.
**Evidence** `PARENTS.md`; impl. §23.4.
**Coverage** **PARTIAL** — `test_hardening.sh` exercises `--reset` and the `PKEXEC_UID=1000` refusal. **Add:** the live VM check.

### B19 · Check the no-internet claim without trusting us
**Sceptical parent.**
1. While the child's session runs: `sudo journalctl -u kidnix-egress` shows the rule refusing that account's traffic. Simpler: there is no browser and no address bar anywhere.
**Accept** the block is by UID at the kernel (nftables `meta skuid`), not a filter list; Flatpaks are `--unshare=network`; NM polkit denies the child.
**Evidence** SYNTHESIS H1; `PARENTS.md`.
**Coverage** **COVERED** — `test_egress.sh`, `test_lockdown.sh`, greenboot `20-kidnix-egress.sh`.

### B20 · The parent's own computer
**Parent.**
1. Gate → **Log out** → GDM; the parent logs into a **stock GNOME session** on the same login screen.
2. Their tools: `gnome-control-center`, `malcontent-control`, Files, a terminal. `kidnix-parent-panel` is a placeholder that says so loudly rather than silently.
**Accept** exactly two sessions exist (kiosk and stock GNOME); Wayland only; the parent's AccountsService file says `gnome`.
**Evidence** ADR-0005; SYNTHESIS need #9 (Sugar's fatal wound).
**Coverage** **PARTIAL** — `test_parent.sh` is static and cannot prove the session starts. **Add:** a boot test that logs the parent in.

---

# C. The machine

### C1 · Boot into the child's screen
1. Power on → GDM autologin for `kid` → gnome-kiosk; `/usr/bin/kidnix-shell` seeds `window-config.ini` **before** gnome-session; the shell presents the band, polls until it is placed, writes phase B, then presents the content window.
**Accept** `KIDNIX_BOOT_OK`; `shell geometry ok`. Unplaced after 2.5 s → three fresh-toplevel retries → one-window fallback with an ERROR: a shell that cannot get its strip still works.
**Evidence** spec §7; AGENTS §3 #8; impl. §18.2, §19.1.
**Coverage** **COVERED** — `tests/boot/*.py`, e2e `test_01`, `test_geometry.py`, `test_kiosk.py`.

### C2 · Upgrade
1. `bootc upgrade` (parent-driven) → staged → reboot when the parent chooses.
2. `/etc` is 3-way-merged so config edits survive; `/var` is untouched; the profile migration runs once, idempotently.
**Accept** never a surprise reboot mid-activity; the migration is never fatal.
**Evidence** SYNTHESIS G5; spec §6; impl. §23.3.
**Coverage** **PARTIAL** — `just vm-upgrade` is manual; the migration is `test_profiles.py`. **Add:** a VM upgrade across a version boundary asserting the Journal survived.

### C3 · A boot that fails its health checks
See **B16**. **UNCOVERED.**

### C4 · First boot with no network
1. Idempotent first-boot units run; `kidnix-flatpak-firstboot` cannot fetch TurboWarp and must fail **soft**.
2. The child's session comes up regardless; the missing activity has no tile (A23).
**Accept** no first-boot failure blocks `graphical-session.target`; nothing retries on a timer against the child's session.
**Evidence** SYNTHESIS need #7, I1; ADR-0006.
**Coverage** **PARTIAL** — the tile-hiding half is `test_activities.py`; the offline boot is untested. **Add:** a boot test with networking disabled.

### C5 · No microphone
1. `GstRecorder` probes `pipewiresrc`/`autoaudiosrc` and an Ogg encoder once at start-up; if either is missing, no mic button is drawn anywhere.
**Accept** S6 and showing mode render correctly with no mic. A control that does nothing is what Ask was removed from the band to avoid.
**Evidence** spec §7a, §7d #9; impl. §23.2.
**Coverage** **PARTIAL** — `test_gtk_smoke.py`. The VM has no audio input, so e2e gets this path for free.

### C6 · No speaker, or speech-dispatcher dead
1. The shell degrades **silently** and logs once; every line still appears in the caption strip, because the hook sits before the enabled check.
**Accept** a dead TTS never blocks a transition; no repeated error lines; the caption invariant holds.
**Evidence** spec §3; impl. §22.2.
**Coverage** **PARTIAL** — `test_access.py`, `test_tts.sh`. **Add:** an e2e run with speech-dispatcher masked.

### C7 · Monitor hotplug, docking, tent mode
1. A monitor change mid-session **leaves the band where it was** — gnome-kiosk applies geometry only at a window's first configure.
2. The shell rewrites phase B so every subsequent activity is placed correctly, and logs the limitation.
**Accept** a known limitation, logged, not silent. Multi-monitor is untested; tent mode affects input hardening only.
**Evidence** impl. §18.9 #3/#4; SYNTHESIS A7; `HARDWARE.md`.
**Coverage** **UNCOVERED**. **Add:** a VM resolution change mid-session asserting the log line rather than a broken band.

### C8 · Lid, sleep and idle
1. The kid session **never auto-suspends** mid-drawing; logind has no VTs to switch to (`NAutoVTs=0`, `ReserveVT=0`); `kid` may not authorise suspend.
2. Reopening the lid returns to the same session, mid-activity, band placed.
**Accept** no idle blank a child cannot dismiss; the clock stays honest across a lid close.
**Evidence** `40-lockdown.sh`; `dconf/kid.d/00-lockdown`.
**Coverage** **UNCOVERED** for the resume path (the policy is `test_lockdown.sh`). **Add:** a VM suspend/resume around a running activity.

### C9 · Low disk
1. The Journal keeps every version and never deletes; journald is capped at 30 days / 200 MB.
2. A full disk must not lose the entry being imported, or leave the child on an error.
**Accept** an import that cannot write fails soft with a log line; the shell stays usable.
**Evidence** SYNTHESIS C1–C3; `journald.conf.d/10-kidnix.conf`.
**Coverage** **UNCOVERED**. **Add:** a headless `ENOSPC` test for the importer, and a VM test with `/var` filled.

### C10 · The clock moves, or bedtime arrives mid-session
1. The budget rolls at 04:00 local; `budget_day` decides which day a sitting belongs to.
2. A clock jumping past `bedtime_start` mid-session: the granted sitting runs to its end (phases count elapsed seconds) and the *next* `may_start` refuses.
3. A clock slipping backwards must never make the Journal speak about the future — `when_words` says "this", never a future tense.
**Accept** `time_left_words` is total over any float, including one from a jumped clock.
**Evidence** spec §7a; impl. §16.7, §16.9, §21.1.
**Coverage** **PARTIAL** headless (`test_journal.py` over every hour of three days, `test_session.py`); nothing on the image. **Add:** a VM test stepping the clock across `bedtime_start` mid-session.

---

# Coverage summary

| Group | Flows | COVERED | PARTIAL | UNCOVERED |
|---|---|---|---|---|
| A — child | 28 | 12 | 16 | 0 |
| B — parent | 20 | 1 | 13 | 6 |
| C — machine | 10 | 1 | 5 | 4 |
| **Total** | **58** | **14** | **34** | **10** |

> Updated 2026-08-23 with `tests/e2e/test_flows.py`, which drives A6, A18,
> A19, A20, A21, A22, A25, A26 and A28 on the shipped qcow2. Group A has no
> UNCOVERED flow left; what remains PARTIAL there is a named branch of a flow
> whose main path is now driven on the image.

The child's *ordinary happy path* is genuinely covered on the shipped image —
boot, choose, plan, launch, draw, keep, the band over an activity, the offer,
put-away via the activity's own tick, Goodbye, Sleeping. Almost everything else
is proved in Python and asserted nowhere on a real machine. One parent flow is
COVERED, and the panel that would own most of them does not exist. The two
loudest machine claims — rollback, and recovery when the shell will not start —
have no test at all.

# The ten worth automating next

1. **B16/C3 — break a required greenboot check and assert the rollback.** The largest untested claim in the product ("cannot be broken").
2. **A6 — resume a Journal card in the e2e.** The whole point of My Things; no card has ever been pressed on a real image.
3. **A21 — the refusal at Who's here.** Spend the budget over ssh, click the face, assert the daytime refusal *before* What's-next-after.
4. **A19/A18 — both endings, on the clock.** Run the e2e once past `bedtime_start` and once before; Resting and Sleeping must not be interchangeable.
5. **A28 — the hard stop.** Leave the tick unanswered: assert "Time to stop now.", the WARNING line, and that Goodbye claims nothing.
6. **A25 — a keyboard-only session over QMP.** The harness already sends key events; this is the SEND blocker's only real proof.
7. **A20 — "All done".** Every automated ending today is clock-driven; D5 says a third of real endings are the child's.
8. **B2/B18 — the PIN, in a VM.** The three checks in impl. §23.4, plus the mandatory flow on a fresh install.
9. **A22 — an activity that fails to open.** Cheap; today the child sits on a blank screen behind the band.
10. **A26 — captions in pixels during put-away.** The moment a deaf child either presses the tick or loses the drawing.

Near misses: **A16** needs a virtual audio source; **B15** waits on the cosign
key; **C7** is a documented limitation we intend to change.

> **Status note (2026-08-23, after e2e wave 2 + the rollback spike; `just test-rollback` passes 11/11 on the shipped image and `just test-e2e` 30/30):** of the
> top-10 above, 1 (`just test-rollback`), 2, 3, 4, 5, 6 (partial — see A25
> finding), 7, 9 and 10 now exist; 8 (PIN in a VM) is covered by the boot
> test's set-pin checks. Next: A25's keyboard escape from an activity, the
> parent flows (B*), and the machine flows (C*), most of which need the parent
> panel or real hardware.

> **A25 update (2026-08-23):** the lockdown now re-enables exactly one
> window-switch binding (`<Super>Tab`, locked) so a keyboard/switch user can
> return from an activity to the shell and press Escape (Back); proven in the
> boot test with an in-guest uinput keyboard (docs/spikes/keyboard-escape.md).
> The shell raises the band before spawning an activity so the switch lands on
> the band, not over the drawing (shell follow-up in the i18n wave).
