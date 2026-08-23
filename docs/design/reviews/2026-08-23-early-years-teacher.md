# Review: kidnix from a Reception/Year 1 classroom

**Reviewer:** early years teacher and SENCO (EYFS, validated SSP phonics, maths
mastery, EHCPs, autism/ADHD/DLD in mainstream); GCompris and Tux Paint in class
since 2016. **Date:** 2026-08-23.
**Read:** AGENTS.md §3; SYNTHESIS §2 B/E, §4; 05 §3–§4; the GCompris curation
spike and shipped `curated.toml`/`CURATION.md`; all ten manifests; the Tux Paint
heredoc; shell-v0.1 §7a–7c; ACTIVITY-IDEAS; CHILD-TEST-PROTOCOL; screenshots.

---

## 1. Verdict

**Conditional pass.** The *shape* is better than anything I have used in a
classroom: the session ritual, the machine-owned ending, the pre-chosen "what's
next", no points and no streaks, the artefact-as-reward. That is the model I
would design if someone gave me an OS, and it is not on the market. The curation
spike is the most honest piece of edtech reasoning I have read — it names the
phonics deviation instead of hiding it.

It is not yet ready to sit in front of a Reception child unaccompanied, for
three reasons, none architectural: the parent-facing copy contradicts the
curation and over-promises phonics; the machine runs in American English; and
the save step of the ending ritual is a 20-pixel tick inside Tux Paint that
nobody has measured. Days of work, not months.

The deeper curricular gap — the interesting one — is that a system built for
four- to six-year-olds has nowhere for the child to *talk*. See §3.7.

---

## 2. Five strengths

1. **The ending ritual is classroom-correct.** T−6 offer, T−2 put away, goodbye
   with the artefact, machine-owned, no "are you sure". That is the tidy-up
   sequence a good Reception class runs, and D2 ("never 'your mum said stop'") is
   the most useful line in the document set.
2. **"What's next after?" is a now-and-next board** — chosen at the start, shown
   back at the end. Now/next boards are the most-used visual support in EYFS SEND
   practice and this reinvents one without being told to. Strongest inclusion
   feature in the product, and the team may not realise it.
3. **The refusal to gamify.** No stars, streaks, scores or badges. I spend real
   energy undoing what star-chart apps do to motivation; E1 is worth more than
   any activity on the shelf.
4. **The curation reasoning.** Spike §4.1 — "`click_on_letter` teaches letter
   names, Reception teaches sounds, we ship it anyway and here is the copy
   constraint" — is the standard I want. Likewise rejecting double-click and
   right-click activities because the OS itself forbids them.
5. **`smallnumbers` and the dice-pip argument.** Somebody read the 2021 ELG
   revision, noticed subitising was *added*, and chose plain pips over cartoons.
   A better call than most published maths apps make.

---

## 3. Ranked concerns

### 3.1 BLOCKER — shipped parent-facing copy contradicts the curation

**Evidence.** `gcompris.toml` still ships `goal = "About 190 small learning
games. Not curated yet -- some are pitched well above five."`, and spike §6
confirms nothing reads `curated.toml` yet. So the machine a parent boots has one
tile opening the full 198-activity menu — its own goal line admits it — while
`curated.toml` carries eighteen EYFS/KS1 mappings no child can reach.

Separately, `klettres.toml` is titled **"Letter sounds"** while its own notes say
nobody has checked whether en_GB KLettres says the letter's *name* or its
*sound*. A tile named "Letter sounds" is a phonics claim, made before any prose
gets the chance to disclaim it (05 §4.5).

**Recommendation.** Do not ship the GCompris tile until the shell reads
`curated.toml`; if the shelf slips, hide the tile rather than expose the menu.
Rename KLettres to **"Letters"** until someone has listened to it.

### 3.2 BLOCKER — the system locale is not en_GB

**Evidence.** No `/etc/locale.conf`, no `LANG=`, no `glibc-langpack-en_GB`
anywhere in `build_files/` or `system_files/`; only GCompris sets
`locale=en_GB.UTF-8`, in its own config. The proof is your own screenshot: Tux
Paint's status bar reads *"Pick a **color** and a brush shape to draw with."* A
machine whose job is helping a UK five-year-old with letters and spelling cannot
show him American spellings.

**Recommendation.** Install `glibc-langpack-en_GB`, write `LANG=en_GB.UTF-8` to
`/etc/locale.conf`, set Tux Paint's `lang=` to its British English value, and add
an image test asserting no child-facing binary starts in `C`/`en_US`.

### 3.3 BLOCKER — the Put-away ritual depends on an unmeasured 20 px tick

**Evidence.** Contact sheet panel 7: Tux Paint's own dialogue, *"Do you really
want to quit? / Yes, I'm done! / No, take me back!"*, at roughly 12 pt with tick
and cross around 20 px. Shell §7c makes that dialogue the save step — only the
tick writes the file. Against our own numbers (18 mm floor; a four-year-old hits
16 px 43% of the time) it is the smallest and most consequential target we ship,
and it asks a pre-reader to answer two sentences.

Worse than the size is the shape. In Reception we never let a transition contain
a question the child can answer "no" to — and the pink cross is a live "carry on
drawing" button, placed there by a program the shell does not control. Press it
once and the ending is negotiable.

**Recommendation.** Measure the tick in millimetres at 1366×768 on the real
laptop before v0.1. Longer term, treat that dialogue as a bug to route around,
not as the save step.

### 3.4 MAJOR — the number strand has no spoken instruction for a pre-reader

**Evidence.** `intro_voice_en_GB = false` for `learn_digits`,
`learn_quantities`, `learn_additions`, `adjacent_numbers`,
`memory-case-association` and `frieze` — the *entire* counting-and-adding half of
the shelf. Spike §4.2 hands the job to `audio_label`, but those labels are not
instructions a five-year-old can act on: *"Show how many the number means"* is
not a sentence a Reception child parses.

**Recommendation.** Rewrite those six as imperative, ≤12 words, in the register
a teacher uses on the carpet: *"Here is a number. Put that many things in the
box."* / *"Count the oranges. Then click the same number."* / *"Put the two
groups together. How many now?"* / *"Which number goes in the gap?"* / *"Find
the big letter and the little letter that go together."* / *"Look at the
pattern. Make it carry on."*

### 3.5 MAJOR — GCompris picks: three I would swap

The shelf is good. Four arguments with it:

- **Drop `clockgame` from v0.1.** Time to the hour is Year 1 Measurement, in
  practice the summer term; most Reception children cannot yet hold "the long
  hand means minutes", and it needs a precise mouse drag on a clock hand. Matt's
  own idea (a)/(c) in ACTIVITY-IDEAS — play with the clock, day-routine scenes,
  "how long is a minute", sharing the sun's visual language — is better pedagogy
  *and* better sequencing: duration and routine language come years before hands
  on a dial.
- **Three pointer activities is a lot of eighteen.** `erase`, `erase_clic` and
  `clickgame` are right at four and largely solved by five and a half — the best
  case for the per-age-band question in spike §7.1.
- **Add `number_sequence` (join-the-dots):** 1★, no reading, counting order, and
  it *makes a picture*. Reconsider `smallnumbers2`: two dice is composition of
  number, the ELG line the shelf under-serves.
- **`gletters` is what I'd cut second.** Falling letters on a timer, for a child
  who cannot locate a key, is a losing race. If it stays, pin it to level 1.

On the phonics honesty question (spike §7 Q4): **keep `click_on_letter`, but do
not put it in a group called "Letters and sounds".** Letter names are a
respectable predictor and nothing better exists in the suite — the group name is
the claim, not the activity. Call it **"Letters"**. The one thing that would
truly align this with school is a phoneme→grapheme activity (hear /a/, find `a`)
with the phase set once by the parent. No GCompris activity does it.

### 3.6 MAJOR — SuperTux and TuxMath contradict E1 and D-series rules

`tuxmath.toml` ships timed arithmetic with a score and a game-over;
`supertux.toml` ships lives and a GAME OVER screen, and its own manifest asks the
question. E1 says no points, no scores, no levels. A Reception child hitting GAME
OVER on a machine whose premise is "you cannot fail here" is a tonal break that
will produce the first week's tears. Check `blinken` too (high-score table).
**Park both outside the 4–6 default allow-list**; drop `tuxmath` outright —
timed drill is against maths mastery pedagogy as well as against E1.

### 3.7 MAJOR — nothing in kidnix records the child's voice

The biggest curricular gap and the cheapest to close. EYFS leads with
Communication and Language; Year 1 composition *begins orally*; 05 §3 calls a
"tell me about it" recorder on every drawing "the cheapest literacy win in the
product" and names an oral-storytelling recorder as developmentally *ahead* of a
typing story tool at five. None ship; the Journal has no audio. Twenty seconds of
recording on the "Let's keep that" screen would be the best thing in this
product and would give the Journal something to co-use. **Put it in v0.1.**

### 3.8 MAJOR — Tux Paint's own UI is the least age-appropriate surface you ship

**Evidence.** Contact-sheet panels 5–6: ~20 tool buttons, a brush column of
similar density, 20 colour swatches, all well under 18 mm, against 05 §3's "≤8
tools visible at once". The config heredoc sets seven sensible things and
touches none of this.

**Recommendation** (all available at build time): ship a reduced brush and
magic-plugin set (delete the rest from `/usr/share/tuxpaint/`); `colorfile=` with
~10 named colours, used as vocabulary; `simpleshapes=yes`,
`nomagiccontrols`/`nostampcontrols`, `noshortcuts`; decide Print — wire it to the
Journal's Print action or `noprint=yes`, because a dead Print button lies;
evaluate `--mouse-accessibility` (click-move-click instead of drag — rule A5,
free); and test `nobuttondistinction` rather than omitting it for being
undocumented, since A2 requires it.

On the open question **"`uppercase=yes` for Tux Paint?" — no.** Reception teaches
lowercase graphemes; he meets uppercase on keycaps and on the first letter of his
name and copes fine. The spike's `fontCapitalization=0` call is right for the
same reason.

### 3.9 MINOR/MAJOR — no name, no name-writing

"Who's here?" shows a tile labelled **"Me"**. Name recognition and name writing
are the most-practised literacy skills in Reception; his photo and his name
(capital initial, rest lowercase) on that tile is free, and it is his first daily
reading. A "sign your picture" step would be worth more than half the shelf.

### 3.10 MAJOR — the activity icons are vendor logos, not pictures of the thing

Every manifest sets `icon_kind = "icon-name"`, so Draw is a penguin, KLettres a
flag, GCompris a brand swirl (panel 3). In class the picture *is* the label for a
pre-reader — tray labels, visual timetables and choosing boards are photographs
or line drawings of the thing you do, never a brand. Draw ten depictive icons
showing the **output or the action**, not the tool: a scribbled picture for Draw,
a face for Potato faces. The What's-next-after set (apple, bath, pan) proves the
team can. (Also raised by the CCI reviewer.)

### 3.11 MINOR — choice screens, wording, and a moon at four in the afternoon

- The "What's next after?" screen shows **eight** options. B2 says ≤5; §7b says
  6–9. A real choice board runs 2–4; at eight a four-year-old picks the last one
  he heard. Resolve the contradiction at 4.
- **"Goodnight"** and a **moon** on "All done"/"Sleeping": at 4 p.m. that reads
  as bedtime. Use "Bye for now" and a closed door.
- The `goal` lines are written for a technical parent. Compare "Drag-and-drop
  play. Every part is spoken aloud…" with what a parent wants: *"Making faces.
  Practises listening, naming things and using a mouse. No reading needed."*
  And `ktuberling.audio_label = "Make a potato face"` is the model for spoken
  labels — it says what you **do**; "Letters and numbers" does not.

### 3.12 MINOR — SEND: calm mode is named but not specified

Calm mode appears in H6/G1 with no definition. From a SENCO's chair, in order:
(1) a per-child switch turning **hover-speech off** — at 450 ms a child sweeping
across twelve tiles gets chatter that is noise to an autistic child and a
distraction to an ADHD one, and the Ear covers the need on demand;
(2) progressive disclosure **off by default** — an unannounced new tile is a
ruined afternoon, and a stable grid beats novelty for every child this age, not
just the autistic one; (3) no unexpected sound and none *under* speech; (4) a
fade, not a cut, into the dark Sleeping screen; (5) an option to hide the sun.
Write these down as *the* definition; a mode nobody has specified gets built as
a colour change.

### 3.13 MINOR — what parents will misunderstand

That this teaches phonics (the tile names claim it; the docs deny it). That the
EYFS/KS1 mapping table means *coverage* — eighteen activities touch perhaps four
of seventeen ELGs, so ship a "what this does **not** do" paragraph beside it.
That 25 minutes is an evidenced threshold; say it is a precaution. That drawing
practises handwriting; it does not (05 §4.7). That "Library" contains books.

---

## 4. What I would do in the first twenty minutes

Not a demo — a normal Reception "new resource" introduction, parent behind and
quiet.

- **0–2 min, machine off.** "This computer is yours. It has a sun on it. When
  the sun goes down it's finished — and then we're going outside." The
  transition is won here, off the screen, not at T−2.
- **2–4 min.** He presses his own tile. Say nothing else; watch whether he looks
  at the sun unprompted (H1). At "What's next after?" I'd show three pictures,
  not eight, and repeat his choice back once.
- **4–12 min. Free play, no instructions, hands off.** Count to ten before
  helping. Record: which tile first; hovers-and-listens or clicks straight away;
  burst-clicks; double-click and right-click attempts (he will try both);
  whether he touches the keyboard.
- **The one thing I'd steer:** if Draw is unopened by minute eight I open it
  *with* him and withdraw — a first session with an empty Journal tests nothing.
  Then watch the toolbar: I expect misses on the tool column and stamps to
  swallow him. Note whether he ever changes colour.
- **T−6, ending offer.** No adult word. Score upset 1–5 at each of the three
  steps — the measurement that matters most.
- **T−2, Put away.** Where I expect the failure: Tux Paint's tick. Time how long
  he takes to hit it and whether "press the tick" was enough.
- **Goodbye and after.** Watch him move to his chosen next thing. Then five
  minutes in My Things: "Tell me about this one." That conversation is the
  point, and it demonstrates why §3.7 should ship. Then stop; ask Again-Again
  tomorrow, not today.

---

## 5. Three questions to the team

1. **Where does the child's voice live?** Is the "tell me about it" recorder in
   v0.1, and if not, what is ahead of it?
2. **Can the shelf follow the school?** Can a parent set, once, "he is on Phase
   3, numbers to 10" and have every letter and number activity obey? Matching his
   actual phonics phase is the difference between supporting his class teacher
   and quietly competing with her.
3. **Who owns the honesty line at the surfaces a parent sees?** The research
   documents are scrupulous; the tile names and goal strings are not. Which
   artefact is the source of truth for what kidnix claims to teach, and who
   reviews a tile name before it ships?
