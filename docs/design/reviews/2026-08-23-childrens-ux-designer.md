# Review — children's UX / visual design

**Persona:** senior designer of children's digital products (BBC GEL-for-children /
CBeebies, Sesame-style formative design, Toca-Boca-style digital toys, ScratchJr-era
pre-reader interfaces). **Date:** 2026-08-23. Read-only except this file.

**Packet:** `08-shell-ux-patterns.md` §3–§5, §7; `shell-v0.1.md` (+§7a–7c); impl. notes
§16–§20; `theme.css`, `metrics.py`, `sun.py`, `band.py`, `sound.py`, `data/icons/*.svg`;
every PNG in `docs/design/screenshots/`, `docs/spikes/screenshots/`, `output/e2e/`. Plus my
own runs of `kidnix-shell --demo` at `1280x800@102` and `1920x1080@96`, captured at
choosing / next-after / home / goodbye, and two long runs to reach the live T−6 ending offer
and T−2 put-away.

---

## 1. Verdict

**Structurally right, visually unfinished, and two screens are broken on the panel we ship
for.** The IA is the best I have seen in a children's shell — three surfaces, one band, no
settings, no scores, no delete, a Journal instead of a file system — and the reasoning
behind it beats most commercial teams. But a five-year-old does not experience reasoning;
they experience a screen, and what is on the screen is a **developer's rendering of a good
design** rather than the design. Every child-facing surface is grey-bordered cream boxes
containing words. The picture layer — the only layer a pre-reader can use — is either an
upstream vendor logo, or missing, or the smallest thing on the page. No character, no
visible motion, no delight.

Fixable, cheaply: ~10 icons, one layout pass over five ritual screens, two rendering bugs, a
motion budget. None of it needs new research. I would **not** put this in front of a child
yet — the test would measure the missing icons rather than the design.

---

## 2. Five strengths

1. **The band is right, and executed with restraint.** Top edge (Sesame's wrist-rest
   finding), never hides, never reorders, and it survives *over a running activity*
   (`output/e2e/11-in-activity.png`). Almost nobody ships this. §18.5's "nothing moves"
   when the offer arrives is exactly the right instinct.
2. **"What's next after?" is the best-designed screen in the build.**
   `output/e2e/02-next-after.png`: eight tiles, one construction rule, one warm accent
   each, instantly readable — the apple, the bath with a duck, the pan with a spoon. This
   is a house style, and it proves the team can draw.
3. **"Flat-with-depth" is implemented properly.** Every interactive surface gets a 6 px
   bottom border, a 4 px offset shadow and a press state that *moves*; the sun correctly
   gets none of it. Real affordance for a pre-reader, applied consistently.
4. **Typography discipline is exemplary.** Andika, an 18 pt floor `fit` cannot touch,
   wrap-never-cut, one type size per page, "shrink before spilling". `labels.py` giving the
   unused second label line back to the *icon* is a designer's decision made by an engineer.
5. **Colour governance.** Edges as solid hex with computed ratios and a test that recomputes
   them; `.not-allowed` outline-only rather than greyed.

---

## 3. Ranked concerns

### BLOCKERS

**B1 — Activity icons are vendor logos, drawn at the icon floor.**
*Evidence:* `output/e2e/03-home.png`, `e2e-contact-sheet.png` panel 3. "Draw" is Tux
Paint's penguin; **"Letter sounds" is a blue UN flag**; "Letters & numbers" is GCompris's
brand swirl; "Copy the lights" is a KDE palette. Every manifest sets
`icon_kind = "icon-name"`. A penguin does not mean draw; a flag means nothing, or "a
country". *Size compounds it:* `Metrics.for_screen(1280, 800, dpi=102)` gives
`tile 170 px, icon 62 px` — squeezed to `TILE_ICON_MIN_FRACTION` (0.36) by two reserved
label lines. A **15.4 mm** picture under a **24 pt** word, where 08 §3.2 budgets a 96/160
icon (60%). The grid reads text-first to an audience that cannot read.
*Fix:* ten depictive SVGs at `icon_kind="path"` (brief in §4); raise the icon floor to
**0.46 of the tile** by reserving one label line where the name fits on one (six of ten do).

**B2 — The recent-work thumbnail replaces the tile's icon.**
*Evidence:* `e2e-contact-sheet.png` panel 8 — after one use "Draw" is a faint grey zigzag,
not a penguin. *Shape = what it is* cannot survive a tile whose shape changes after first
use. *Fix:* corner badge at ≤ 0.30 of the tile, bottom-right, 2 px `@kid-edge` frame —
which is what §5.3's own wireframe says. Never in the icon slot.

**B3 — Two screens are broken at 1280×800@102.** Both reproduced on this host.
- **S5 ending offer:** "Ask for more time" is **clipped by the bottom edge**, border and
  shadow cut.
- **S8 Sleeping** (`output/e2e/16-sleeping.png`): the content window paints **cream**, with
  a small dark rectangle floating in the middle and "Sleeping" **clipped at the box edge**.
  §18.6 painted the *band's* toplevel `#171b2c`; `.sleeping` is a child box, not the
  surface.
*Fix:* extend `_check_measured_fit` past Home+band to the ritual screens; set the sleeping
background on `window.kidnix`. A screen that looks broken at the moment a child is told it
is over reads as *the computer broke*, not *it is finished* — the exact affect the ritual
exists to prevent.

**B4 — The ending ritual has no picture in it, and three different suns.**
*Evidence:* my S5/S6 captures plus `output/e2e/14-put-away.png`.
- **S5** offers two *identical cream rectangles containing words*. 08 §4.7 asks for "two
  large picture buttons"; there is nothing to discriminate on. The tertiary "Ask for more
  time" is the widest, roundest button on screen — visually the primary.
- **S6** is "Let's keep that." on an empty screen. The beat whose whole purpose is *"the
  last thing that happens is a success"* shows the child **nothing being kept**.
- **Three suns** within four minutes: the band's disc sinking behind a horizon; S5's bright
  **midday** sun with rays (contradicting its own spoken line and the band beside it);
  `kidnix-finish.svg`'s setting sun.
*Fix:* one sun drawing from `sun.py` at three sizes, used everywhere. Put the real
thumbnail on S6 and fly it into My Things (400 ms ease-in-out, ending on the keep earcon) —
promised in the spec, absent from the build. A picture on every ritual button.

### MAJORS

**M1 — Goodbye's hierarchy is inverted.** `output/e2e/15-goodbye.png`. The child's own
chosen next thing — the Coco's payoff — is a 24 mm icon beside a 22 pt `quiet-line`, placed
*last*, *below* the buttons, and **clipped by the bottom edge**. The headline about counting
artefacts gets 40 pt. The sun above it is full and yellow. *Fix:* chosen picture ≥ 45 mm and
central, `big-line` phrase, Goodnight below, thumbnails as a quiet top strip, sun at
`fraction = 1.0`. (Agrees with forum #7, #24.)

**M2 — The band's offer swap is invisible.** `output/e2e/12-band-offer.png`: Undo and My
Things silently become a sun and a teal/pink square — same size, same place, no motion, no
colour change. No *event* for a child looking at their drawing. And `@kid-highlight` is
reserved for "the thing you can touch right now"; this is the one moment that literally is
that, and `.band button.offer` spends a heavier grey border on it. *Fix:* 350 ms scale-in
from 0.85 with 6% overshoot plus the reserved ring for 3 s. Everything else stays fixed.

**M3 — Two shell icons depict nothing.** `kidnix-one-more.svg` is a 28 px teal square beside
an 18 px pink square — an abstract diagram of "an item plus another", the learned convention
§3.7 forbids. `kidnix-my-things.svg` at 20 mm reads as a lunchbox. *Fix:* one-more = a small
brick being placed on a short stack; My Things = a scrapbook page with a drawing peeking out
and a turned corner.

**M4 — There is no character, anywhere.** §3.7, §4.1 and §7 #11 all specify one, at
boundaries only, and the spec writes character lines ("The sun is going down"). Nothing on
any screen is one, so the shell speaks from nowhere and the warmest surfaces (Who's here,
Goodbye, Sleeping) are the emptiest. *Fix:* decide it rather than default it. Minimally —
one non-anthropomorphic companion (a bird, or a moth that follows the sun), five poses, no
lipsync, on S1/S1b/S5–S8 and the idle hint only, never on Home or a canvas. If the answer
is no, the ritual screens need a compensating visual; right now they are type on cream.

**M5 — The band icons are not one family.** Back is a solid teal arrow with a 4 px outline;
Undo is a **purple stroke-only** curl with no outline or fill; the Ear is a peach ear; the
Grown-up is a grey-and-brown bust; My Things is a yellow tray. Five construction rules and
four palettes in a 102 px strip the child looks at all session. *Fix:* one rule — 3.5 px
`@kid-ink` outline, one flat fill from a four-colour system palette, no stroke-only glyphs.
Undo redrawn as a *filled* arrow curling back over a small page (§3.7's own prescription).

**M6 — The sun is not glanceable and its "loss of quantity" cue is invisible.** At 1280 the
sun is a **46 px** disc on a 1280 px band, sitting on a 570 × 4 px white rule — from two
metres, *a progress bar with a dot on it*, an adult idiom. The faint start-outline that
`sun.py` calls "what makes the shrinking legible as a loss" is `rgba(1,1,1,0.30)` on teal
and is invisible in every capture until T−2. *Fix:* a fixed ≥ 120 px stage rather than all
the spare width; horizon only as wide as that stage; ghost ring at `rgba(255,255,255,0.55)`
and **dashed**, so it survives greyscale. (See also forum #22: 2.98:1, dropping to 1.99:1
when warm.)

**M7 — Empty pages read as broken.** `demo-all-done.png` is Home page two: **two tiles**
adrift in cream, a giant pager arrow clipped at its left edge, two 14 px page dots.
`output/e2e/09-my-things.png` is one card at 15% of the screen with "Today" **63 px
off-centre** from the card it labels. *Fix:* never paginate to a page with less than a full
row; centre short day-groups under their heading; page dots ≥ 20 px with a 44 px hit area
(they are currently under every target floor in the document, and they are the only sign
that page two exists).

### MINORS

- **m1** The avatar is an ink blot (`01-whos-here.png`): a black disc with white eyes and
  grin. `kidnix-child.svg` — a peach face — is only the fallback. Use it, tinted in the
  child's colours.
- **m2** The band shows Back / Undo / My Things on "Who's here?" and on Goodbye, where they
  do nothing or contradict the ritual. Spatial stability is worth a lot; a control that lies
  is worth less.
- **m3** "Finishing mode" ghosts My Things to a teal silhouette (`14-put-away.png`) — that
  is greying-out by another route, forbidden everywhere else in the codebase.
- **m4** Home's page container is a visible box: a cream seam at x≈94 / x≈1186
  (`demo-home-firstrun.png`).
- **m5** "Ready to / go outside?" wraps mid-phrase (`demo-goodbye-choice.png`; §17.9 #3).
  Put the picture above the line and it never wraps.
- **m6** No motion anywhere, and none in `theme.css`. §3.5 gives durations, easing and a
  5–8% overshoot budget; GTK4 will not produce it for free. Minimum: 400 ms surface moves,
  250 ms tile-open, the keep-fly — all behind `prefers-reduced-motion`.
- **m7** Earcons are well-designed on paper and unheard. The designer's gap: **there is no
  open/commit sound**. `TAP` fires on every press, so opening an activity sounds exactly
  like focusing a page dot. §3.6 lists "commit / open — two-note rising, brighter" as a
  separate earcon. Add it.
- **m8** What reads "adult / developer-ish": the horizon as a progress bar; a saturated
  teal strip with a 4 px pink rule under it (a title bar); `#7e838c` borders on cream (a
  form); "Grown-up" as grey text in a grey rectangle bottom-right (a Cancel button);
  pagination chrome larger than its content; and screens composed entirely of *centred
  heading, centred control, nothing else*.

---

## 4. Visual-polish backlog and icon brief

| # | Item | Size |
|---|---|---|
| 1 | Ten depictive activity icons at `icon_kind="path"`; drop every `icon-name` (B1) | 1–2 d |
| 2 | Fix Sleeping's background and S5's clipped button; extend measured-fit to S5–S8 (B3) | 0.5 d |
| 3 | S6 gets the thumbnail flying into My Things + keep earcon; S5 gets picture buttons; one sun (B4) | 1 d |
| 4 | Goodbye re-laid out: chosen picture ≥ 45 mm and central, sun held at 1.0 (M1) | 0.5 d |
| 5 | Thumbnail → corner badge; icon floor raised to 0.46 of the tile (B2, B1) | 0.5 d |
| 6 | Band icon family unified; redraw Undo, My Things, one-more (M3, M5) | 1 d |
| 7 | Band offer arrives with motion + the reserved highlight for 3 s (M2) | 0.25 d |
| 8 | Sun given a fixed stage, a dashed ghost ring, a contrast-passing warm (M6) | 0.5 d |
| 9 | Motion budget, gated on `prefers-reduced-motion` (m6) | 1 d |
| 10 | Empty-state / alignment pass: page dots ≥ 20 px, no half-empty pages, day heading centred, drawn avatar, container seam (M7, m1, m4) | 0.5 d |

**Icon brief — the ten activity tiles.** Match `kidnix-next-*.svg` exactly: 64×64 viewBox,
flat fills, 3.5 px `#16181d` outline, round joins, no gradients, shadows, text, digits or
brand marks. Palette `#0f8a8a` / `#f06292` / `#f9a825` / `#2e7d32` / `#f6c9a8`, **max three
fills each**. Each must survive as a silhouette at 62 px and in greyscale, and must be
distinguishable from the other nine at a glance — the hard constraint, because four of the
ten are "learning" and will collapse into each other if drawn as books.

| Activity | Now | Draw instead |
|---|---|---|
| `tuxpaint` Draw | penguin | Fat amber **paintbrush on a diagonal**, teal bristles, one wet pink stroke already on the paper beneath. (Not a pencil — that is `next-draw`, i.e. paper.) |
| `ktuberling` Potato faces | KDE potato-man | Round brown **potato with stick-on eyes and a nose sitting askew**, one loose ear beside it. The askew placement is the activity. |
| `gcompris` Letters & numbers | brand swirl | Three **play-blocks**, two-and-one: `a`, `3`, blank. Letterforms in Andika. |
| `klettres` Letter sounds | UN flag | **Mouth in profile with a sound-arc**, a lowercase `a` riding the arc. (Rename the tile too — forum #12. If it is letter *names*, draw the letter being pointed at.) |
| `blinken` Copy the lights | KDE palette | **Four lamps in a 2×2**, one lit amber with a short glow ring, three dark. |
| `tuxmath` Number game | Tux + rocket | **Three counting beads on a wire**, two pushed left, one right. No arithmetic symbols. |
| `kolf` Mini golf | KDE golf | **Ball, short putter, flag in a hole**, side-on, ball mid-roll with two motion ticks. |
| `supertux` Jump and run | SuperTux | **Simple running figure mid-stride over a gap**, a platform under each foot. A figure, not a mascot. |
| `turbowarp` Make a game | TW logo | **Two interlocking instruction blocks** (teal + pink), a small arrow leaving the lower one. ScratchJr's own solution; it reads. |
| `kiwix` Library | dictionary glyph | **Three books leaning on a shelf, one pulled half-out**, a picture on its cover. Not a magnifying glass. |

Plus: reuse `kidnix-make` / `-learn` / `-play` as a 14 px badge at 40% opacity, top-left, so
kind is visible without reading. And **`image-missing.svg` must never reach a child** — an
activity whose icon fails to load should draw no tile at all.

---

## 5. Three questions

1. **Is there a character, or is there not?** The research says one, at boundaries only; the
   spec writes character lines; the build has none and no plan. It is the largest unresolved
   *design* decision in the product and it changes the brief for S1, S1b and S5–S8. Decide
   it before the icon work.
2. **Who draws the ten icons, and against what acceptance test?** Drawing is a day; judging
   is the part that fails. My proposal: print them at 15 mm, hand them to four children aged
   4–6 with no labels and no sound, ask "what would happen if you pressed this?" Below 3/4,
   redraw. That test costs an afternoon and is the only one in this product that can run
   before the machine works.
3. **How much delight is this product allowed?** No scores, rewards, streaks, or character
   on the canvas; "the sun is state, not a warning". I agree with each decision
   individually; their sum is a screen a five-year-old has no reason to look forward to.
   Toca Boca's restraint is not the absence of delight — it is delight relocated into
   *responsiveness*, things that squash, wobble and behave like objects. Where is kidnix's
   version allowed to live? Mine: the press states (already there), one idle breath on the
   sun, and the moment a thing is kept. Someone has to decide, or this ships correct and
   joyless.

---

*Posted to the panel forum as #36 (broken ritual screens), #45 (no picture in the ending,
three suns), #50 (agreeing with cci-researcher #19, adding the icon-size and
thumbnail-replacement findings) and #55 (agreeing with accessibility-specialist #21 on the
unlabelled band offer).*
