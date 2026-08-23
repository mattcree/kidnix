# Review: kidnix from a Reception/Year 1 classroom

**Reviewer:** early years teacher and SENCO (EYFS, validated SSP phonics, maths
mastery, EHCPs, autism/ADHD/DLD in mainstream). GCompris, Tux Paint and tablets
used in class since 2016.
**Date:** 2026-08-23.
**Read:** AGENTS.md §3; SYNTHESIS §2 B/E, §4; 05 §3–§4; the GCompris curation
spike plus the shipped `curated.toml`/`CURATION.md`; all ten activity manifests;
the Tux Paint heredoc in `50-activities.sh`; shell-v0.1 §7a–7c; ACTIVITY-IDEAS;
CHILD-TEST-PROTOCOL; the screenshots, including `e2e-contact-sheet.png`.

---

## 1. Verdict

**Conditional pass.** The *shape* is better than anything I have used in a
classroom. The session ritual, the machine-owned ending, the pre-chosen "what's
next", no points and no streaks, the artefact-as-reward — that is the model I
would design if someone gave me an OS, and it is not on the market. The curation
spike is the most honest piece of edtech reasoning I have read: it names the
phonics deviation instead of hiding it.

It is not yet ready to sit in front of a Reception child unaccompanied, for
three reasons, none of them architectural: the parent-facing copy contradicts
the curation and over-promises phonics; the machine runs in American English;
and the save step of the ending ritual is a 20-pixel tick inside Tux Paint that
nobody has measured. Days of work, not months.

The deeper curricular gap — the interesting one — is that a system built for
four- to six-year-olds has nowhere for the child to *talk*. See §3.7.

---

## 2. Five strengths

1. **The ending ritual is classroom-correct.** T−6 offer, T−2 put away, goodbye
   with the artefact, machine-owned, no "are you sure". That is the tidy-up
   sequence a good Reception class runs, and D2 ("never 'your mum said stop'") is
   the most useful line in the document set. Most families lose twenty minutes a
   day to that argument.
2. **"What's next after?" is a now-and-next board** — chosen at the start, shown
   back at the end. Now/next boards are the most-used visual support in EYFS SEND
   practice and this reinvents one without being told to. Strongest inclusion
   feature in the product, and the team may not realise it.
3. **The refusal to gamify.** No stars, streaks, scores or badges. I spend real
   energy undoing what star-chart apps do to children's motivation; E1 is worth
   more than any activity on the shelf.
4. **The curation reasoning.** Spike §4.1 — "`click_on_letter` teaches letter
   names, Reception teaches sounds, we ship it anyway and here is the copy
   constraint" — is the standard I would want. Likewise rejecting double-click
   and right-click activities because the OS itself forbids them.
5. **`smallnumbers` and the dice-pip argument.** Somebody read the 2021 ELG
   revision, noticed subitising was *added*, and chose plain pips over countable
   cartoons. A better call than most published maths apps make.

---

## 3. Ranked concerns

### 3.1 BLOCKER — shipped parent-facing copy contradicts the curation

**Evidence.** `system_files/usr/share/kidnix/activities/gcompris.toml` ships
today with:

```
name = "Letters & numbers"
goal = "About 190 small learning games. Not curated yet -- some are pitched well above five."
```

Spike §6 confirms nothing reads `curated.toml` yet. So the machine a parent
boots has one tile opening the full 198-activity menu, and its own goal line
admits it, while `curated.toml` carries eighteen EYFS/KS1 mappings no child can
reach.

Separately, `klettres.toml` is called **"Letter sounds"** — and its own notes say
nobody has checked whether en_GB KLettres says the letter's *name* or its
*sound*. A tile named "Letter sounds" is a phonics claim, made before any prose
gets the chance to disclaim it (05 §4.5).

**Recommendation.** Do not ship the GCompris tile until the shell reads
`curated.toml`; if the shelf slips, hide the tile rather than expose the menu.
Rename KLettres to **"Letters"** until someone has listened to it; goal: "Hear a
letter and find it. This is not your school's phonics scheme."

### 3.2 BLOCKER — the system locale is not en_GB

**Evidence.** No `/etc/locale.conf`, no `LANG=`, no `glibc-langpack-en_GB`
anywhere in `build_files/` or `system_files/`. Only GCompris gets
`locale=en_GB.UTF-8`, in its own config. The proof is in your own screenshot:
Tux Paint's status bar reads *"Pick a **color** and a brush shape to draw with."*
A machine whose job is helping a UK five-year-old with letters and spelling
cannot show him American spellings.

**Recommendation.** Install `glibc-langpack-en_GB`, write `LANG=en_GB.UTF-8` to
`/etc/locale.conf`, set Tux Paint's `lang=` to its British English value (confirm
with `tuxpaint --lang list`), and add an image test asserting no child-facing
binary starts in `C`/`en_US`.

### 3.3 BLOCKER — the Put-away ritual depends on an unmeasured 20 px tick

**Evidence.** Contact sheet panel 7: Tux Paint's own dialogue, *"Do you really
want to quit? / Yes, I'm done! / No, take me back!"*, at roughly 12 pt with tick
and cross targets around 20 px. Shell §7c makes that dialogue the save step —
only the tick writes the file.

Against your own numbers (18 mm floor; a four-year-old hits 16 px 43% of the
time) this is the smallest and most consequential target in the product, and it
asks a pre-reader to answer two sentences of text. Worse: in a classroom you
never ask a five-year-old to *confirm* the end of an activity. You save it for
them and show them the result. The confirm shape is wrong even at 18 mm.

**Recommendation.** Measure the tick in millimetres at 1366×768 on the real
laptop before v0.1. Under 18 mm, the ritual will eat drawings. Longer term,
treat that dialogue as a bug to route around, not as the save step.

### 3.4 MAJOR — the number strand has no spoken instruction for a pre-reader

**Evidence.** `intro_voice_en_GB = false` for `learn_digits`,
`learn_quantities`, `learn_additions`, `adjacent_numbers`,
`memory-case-association` and `frieze` — the *entire* counting-and-adding half of
the shelf. Spike §4.2 hands the job to the shell's `audio_label`, but those
labels are not instructions a five-year-old can act on: *"Show how many the
number means"* is not a sentence a Reception child parses.

**Recommendation.** Rewrite those six as imperative, ≤12 words, in the register
a teacher uses on the carpet:
- `learn_digits` → "Here is a number. Put that many things in the box."
- `learn_quantities` → "Count the oranges. Then click the same number."
- `learn_additions` → "Put the two groups together. How many now?"
- `adjacent_numbers` → "Which number goes in the gap?"
- `memory-case-association` → "Find the big letter and the little letter that
  go together."
- `frieze` → "Look at the pattern. Make it carry on."
Then check each against B5 (audio-first, ≤2 sentences) and re-record.

### 3.5 MAJOR — GCompris picks: three I would swap

The shelf is good. Four arguments with it:

- **Drop `clockgame` from v0.1.** Time to the hour is Year 1 Measurement and in
  practice lands in the summer term; most Reception children cannot yet hold
  "the long hand means minutes". It also needs a precise mouse drag on a clock
  hand. Matt's own idea (a)/(c) in ACTIVITY-IDEAS — play with the clock,
  day-routine scenes, "how long is a minute", sharing the sun's visual
  language — is better pedagogy *and* better sequencing: duration and routine
  language ("before lunch", "after tea") come years before hands on a dial.
- **Three pointer activities is a lot of eighteen.** `erase`, `erase_clic` and
  `clickgame` are right at four and largely solved by five and a half. Strongest
  case for the per-age-band question in spike §7.1: band it, or this child
  spends a sixth of his shelf on skills he already has.
- **Add `number_sequence` (join-the-dots):** 1★, no reading, counting order, and
  it *makes a picture* — the only counting activity that would produce
  something. Reconsider `smallnumbers2` too: two dice is composition of number,
  the ELG line the shelf under-serves.
- **`gletters` is what I would cut second.** Falling letters on a timer, for a
  child who cannot locate a key, is a losing race — the soft-failure shape the
  constitution is wary of. If it stays, pin it to level 1 lowercase.

On the phonics honesty question (spike §7 Q4): **keep `click_on_letter`, but do
not put it in a group called "Letters and sounds".** Letter names are a
respectable predictor and nothing better exists in the suite — the group name is
the claim, not the activity. Call it **"Letters"**. The one thing that would
truly align this with school is a phoneme→grapheme activity (hear /a/, find `a`)
with the phase set once by the parent, and no GCompris activity does it.

### 3.6 MAJOR — SuperTux and TuxMath contradict E1 and D-series rules

`tuxmath.toml` ships timed arithmetic with a score and a game-over;
`supertux.toml` ships lives and a GAME OVER screen and its own manifest asks the
question. E1 says no points, no scores, no levels. A Reception child hitting GAME
OVER on a machine whose premise is "you cannot fail here" is a tonal break, and
it will produce the first week's tears. Check `blinken` for the same thing (it
keeps a high-score table).

**Recommendation.** Park both outside the 4–6 default allow-list. Keep
`supertux` as a parent-enabled tile for the 7+ end; drop `tuxmath` — timed drill
is against maths mastery pedagogy as well as against E1.

### 3.7 MAJOR — nothing in kidnix records the child's voice

The biggest curricular gap and the cheapest to close. EYFS leads with
Communication and Language; Year 1 composition *begins orally*; 05 §3 calls a
"tell me about it" recorder on every drawing "the cheapest literacy win in the
product", and names an oral-storytelling recorder as developmentally *ahead* of a
typing story tool at five. None ship; the Journal has no audio.

Twenty seconds of recording on the "Let's keep that" screen would be the single
best thing in this product, would give the Journal something to co-use, and needs
no new activity. **Put it in v0.1. It is one screen.**

### 3.8 MAJOR — Tux Paint's own UI is the least age-appropriate surface you ship

**Evidence.** Contact-sheet panels 5–6: ~20 tool buttons in a two-wide column, a
brush column of similar density, 20 colour swatches, all well under 18 mm. 05 §3
says "≤8 tools visible at once; every extra palette item costs touch accuracy".
The config heredoc sets seven sensible things and touches none of this.

**Recommendation** (all available at build time):
- ship a reduced brush set and reduced magic-plugin set (delete the rest from
  `/usr/share/tuxpaint/brushes` and the plugin dir);
- `colorfile=` with ~10 named colours, used as vocabulary;
- `simpleshapes=yes` (no rotate step), `nomagiccontrols`/`nostampcontrols`,
  `noshortcuts` (no accidental Ctrl-surprises in a kiosk);
- decide Print — wire it to the Journal's Print action or `noprint=yes`. A dead
  Print button is a button that lies;
- evaluate `--mouse-accessibility`: click-move-click instead of drag, which is
  rule A5 handed to you free;
- test `nobuttondistinction` rather than omitting it for being undocumented;
  A2 requires it.

On the open question **"`uppercase=yes` for Tux Paint?" — no.** Reception teaches
lowercase graphemes; the child meets uppercase on keycaps and on the first letter
of his name and copes fine. The spike's `fontCapitalization=0` reasoning for
GCompris is right for the same reason. The one place a capital belongs is his own
name.

### 3.9 MINOR/MAJOR — no name, no name-writing

"Who's here?" shows a tile labelled **"Me"** with a smiley. Name recognition and
name writing are the most-practised literacy skills in Reception; a photo and
"Alfie" (capital A, rest lowercase, in Andika) on that tile is free, and it is
the child's first daily reading. A "sign your picture" step on the keep screen
would be worth more than half the shelf.

### 3.10 MINOR — choice screens, wording, and a moon at four in the afternoon

- The "What's next after?" screen shows **eight** options. B2 says ≤5; §7b says
  6–9. In practice a choice board runs 2–4 pictures; at eight a four-year-old
  picks the last one he heard. Resolve the contradiction at 4.
- **"Goodnight"** on the goodbye screen and a **moon** on "All done"/"Sleeping":
  at 4 p.m. that reads as bedtime. Use "Bye for now" and a non-nocturnal image
  (a closed door, a packed-away tray).
- The `goal` lines are written for a technical parent. Compare "Drag-and-drop
  play. Every part is spoken aloud…" with what a parent wants: *"Making faces.
  Practises listening, naming things and using a mouse. No reading needed."*
  Every goal should answer: what will he do, what does it practise, does he need
  to read.
- `ktuberling.audio_label = "Make a potato face"` is the model — the spoken label
  says what you **do**. `gcompris.audio_label = "Letters and numbers"` does not.
  Apply the KTuberling rule everywhere.

### 3.11 MINOR — SEND: calm mode is named but not specified

Calm mode appears in H6 and G1 with no definition. From a SENCO's chair the
things that matter, in order: (1) a per-child switch that turns **hover-speech
off** — at 450 ms a child sweeping the pointer across twelve tiles gets a stream
of chatter that is noise to an autistic child and a distraction to an ADHD one,
while the Ear button covers the need on demand; (2) no unexpected sound and no
sound *under* speech (already policy — check Tux Paint's squeaks and GCompris'
background music actually obey it); (3) a fade rather than a cut into the dark
Sleeping screen; (4) the option to hide the sun for a child who fixates on it —
your P1 protocol will find this child; (5) reduced motion honoured inside
activities, not just the shell. Write these down as *the* definition of calm
mode and test them; a mode nobody has specified will be implemented as a colour
change.

### 3.12 MINOR — what parents will misunderstand

1. That this teaches phonics. The tile names claim it; the docs deny it.
2. That the EYFS/KS1 mapping table means coverage. Eighteen activities touch
   perhaps four of seventeen ELGs. Ship a "what this does **not** do" paragraph
   in the same place as the mapping.
3. That the 25-minute session is an evidenced threshold. Say plainly it is a
   precaution, not a finding.
4. That drawing practises handwriting. It does not, and 05 §4.7 asks you to say so.
5. That "Library" contains books. It contains nothing until they add a ZIM.
6. That `age_min = 6` tiles are "coming soon" rather than "not for him".

---

## 4. What I would do in the first twenty minutes

Not a demo — a normal Reception "new resource" introduction, parent behind and
quiet (your protocol already says this; it is right).

- **0–2 min, before the machine is on.** "This computer is yours. It has a sun
  on it. When the sun goes down it's finished — and then we're going outside."
  Set the expectation *off* the screen. The transition is won here, not at T−2.
- **2–3 min.** Boot to "Who's here?". Let him press his own tile. Say nothing
  else. Watch whether he looks at the sun unprompted (H1).
- **3–4 min.** "What's next after?" — narrowed to three pictures for a first
  session. Repeat his choice back once: "After the computer, outside." That is
  the now-and-next board doing its job.
- **4–12 min. Free play, no instructions, hands off.** Count to ten before
  helping. Record: which tile first; hovers-and-listens or clicks straight away;
  burst-clicks; every double-click and right-click attempt (he will try both);
  whether he touches the keyboard.
- **The one thing I would steer:** if Draw is unopened by minute eight, I open
  it *with* him and withdraw. Draw produces the artefact the ending ritual
  needs, and a first session with an empty Journal tests nothing.
- **12–14 min, in Draw.** Sit on my hands and watch the toolbar. I expect misses
  on the tool column and I expect stamps to swallow him. Note whether he ever
  changes colour, and how.
- **T−6, the ending offer.** No adult word. Score upset 1–5 at each of the three
  steps. This is the measurement that matters most.
- **T−2, Put away.** Where I expect the failure: Tux Paint's tick. Time how long
  he takes to hit it and whether the spoken "press the tick" was enough. If he
  cannot, §3.3 is confirmed and the ritual needs rebuilding.
- **Goodbye and after.** Watch the transition off the machine to his chosen next
  thing. Then five minutes in My Things: "Tell me about this one." That
  conversation is the point, and it demonstrates why §3.7 should ship.
- **Then stop.** No smileyometer, no "did you like it". Ask Again-Again
  tomorrow, not today.

---

## 5. Three questions to the team

1. **Where does the child's voice live?** EYFS leads with Communication and
   Language and there is currently nowhere in kidnix for a child to say
   anything. Is the "tell me about it" recorder in v0.1 or not, and if not, what
   is ahead of it?
2. **Can the shelf follow the school?** Can a parent set, once, "he is on
   Phase 3, numbers to 10" and have every letter and number activity obey — or
   is the shelf one fixed list for 4–6? Aligning to the child's actual phonics
   phase is the difference between supporting his class teacher and quietly
   competing with her.
3. **Who owns the honesty line at the surfaces a parent actually sees?** The
   research documents are scrupulous; the tile names and goal strings on the
   machine are not. Which artefact is the source of truth for what kidnix claims
   to teach, and who reviews a tile name before it ships?
