# 08 — UI/UX patterns and visual/interaction design for children's shells

Research note for **kidnix**. Topic: what already exists in children's shells, launchers and apps; what the evidence says; and concrete, buildable guidance for the kidnix activity shell.

---

## 1. Scope & method

**Question.** kidnix needs a full-screen "activity shell" for children aged 4–8 (design centre: 5–6, UK family, pre- and early readers). No desktop metaphor, no windows, no file browser. It needs: a Journal, a visible session timer with a gentle ending, read-aloud everywhere, an "ask a grown-up" affordance, multi-child profiles, and a parent panel. This note covers the interaction and visual design of that shell — not the activity content itself, and not the underlying OS plumbing.

**Method.** Web research over roughly two working sessions, prioritising primary sources: original design-guideline documents (OLPC/Sugar Human Interface Guidelines, Sesame Workshop's *Best Practices*, BBC GEL), peer-reviewed CCI papers (IDC, CHI, IJCCI), product documentation, and named retrospectives. Where only secondary or vendor-marketing material exists (Amazon Kids, Google Kids Space, Osmo, PBS Kids), that is flagged. Full source list in §9.

**Evidence tags** used throughout:

| Tag | Meaning |
|---|---|
| **[A]** | Peer-reviewed empirical study with reported method and numbers |
| **[B]** | Published design guideline from an organisation with a formative-research programme (Sesame, BBC, NN/g) — expert consensus grounded in unpublished testing |
| **[C]** | Primary project documentation / design rationale (OLPC HIG, Sugarizer docs) — states intent, not outcomes |
| **[D]** | Vendor marketing, press coverage, blog retrospective, or my own design judgement |

**Assumptions I have made** (flagged so they can be overturned):
- Primary input is a laptop/desktop with **mouse or trackpad and keyboard**, possibly a touchscreen. Most children's-app research is touch-first, so I translate target sizes into physical millimetres rather than trusting pixel numbers.
- The device is **shared**, family-owned, offline-capable, and a parent is usually in the same room but not at the screen.
- English (UK), one language, left-to-right.
- kidnix is **not** trying to be a classroom deployment. Sugar's collaboration/mesh model is therefore mostly out of scope; its Journal model is very much in scope.

**What I could not verify.** Amazon Kids and Google Kids Space have no published design guidelines; my notes are from product docs, press and user reports. LEGO's internal digital design guidelines for children are not public — I have substituted the *Designing for Children's Rights* guide, which covers similar ground and is open. Kano OS design documentation is no longer online; my note is from press coverage. PBS Kids and Nintendo have no public design system for children's UI.

---

## 2. Existing shells, launchers and children's apps

### 2.1 OLPC Sugar — the most serious attempt at a child's shell, and the most instructive failure

Sugar (2006–) is the only widely deployed operating-system shell designed from first principles for children. Its Human Interface Guidelines are the single richest primary document in this space and worth reading in full. **[C]**

**Core ideas.** "There are no software applications in the traditional sense on the laptop. The laptop focuses children around 'activities.'" Objects, not files: "instead of a sound file, we have an actual sound; instead of a text file, a story." The guiding mantra is **"Low floor, no ceiling."** **[C]**

**Structure — the zoom metaphor.** Four discrete "zoom levels": **Neighbourhood** (everyone on the mesh) → **Groups** (friends/class) → **Home** (your activities and your ring of running activities) → **Activity** (full-screen). Keyboard keys and Frame buttons jump directly between levels. Activities are always full-screen and single-tasking; the HIG justifies this on both screen-size and attention grounds: "it naturally focuses efforts on a specific task." **[C]**

**The Frame.** Rather than a persistent menu bar (which "reduces the screen space available for activities"), Sugar has a frame that slides in from the screen edges, invoked by **hot corners** ("As Fitts' Law implies, the corners are the easiest part of the screen to hit"). Left/top/right edges hold *nouns* (people, places, things); the bottom edge holds *actions* (activities, invitations, notifications). The left edge doubles as a clipboard stack. **[C]**

**The Journal — why it replaced files.** This is the most transferable idea in Sugar and the design rationale is unusually explicit:

- **"The Notion of 'Keeping'."** "We believe that the traditional 'open' and 'save' model commonly used for files today will fade away, and with it the familiar floppy disk icon." Saving is automatic and incremental; activities may declare "keep-hints" that trigger a snapshot before a risky operation (the HIG's example: a drawing activity keeps before an *erase* that immediately follows a *select all*).
- **Opening is replaced by resuming.** "This eliminates the need to 'open' a file from within an activity, replacing the act of opening with the act of resuming a previous activity instance."
- **"Deprecating Hierarchy."** "The laptops will drastically minimize the hierarchical filesystem as a means for organization, replacing it with a temporally organized list of activities and events." The justification is cognitive: "humankind's intrinsic relationship to time gives them, at the very least, a relative notion of 'how long ago' something happened."
- **Portfolio, not storage.** "As a record of things a child has done — not just the things a child has saved — the Journal will read much like a portfolio or scrapbook history."
- **Falloff.** Old, rarely-viewed entries are algorithmically nominated for deletion on a logarithmic "temporal granularity" model that mimics human memory, with the child reviewing before erasure.
- **Implicit versioning.** Incremental keeps give a versioned filesystem for free; revision histories can be collapsed to reclaim space. **[C]**

**Recoverability as a first-class principle.** "Recoverability is fundamental to encouraging exploration… When children know they have a fallback plan — a way back to the current state of things — they will much more frequently go beyond their comfortable boundaries." Undo is named as "the primary and essential means"; OLPC even considered a dedicated undo/redo key. **[C]**

**Visual system.** A **16 × 12 grid of 75 × 75 px cells** on the 1200 × 900 display, each cell subdivided into a 5 × 5 array of 15 px subcells; icons are drawn to fit "loosely within the 3 × 3 icon-safe subcell." Icons are **SVG, two-tone (stroke + fill)**, with stroke weights that deliberately do *not* scale linearly:

| Icon size | Scale factor | Stroke weight |
|---|---|---|
| XS | 0.5 | 2.25 px |
| S (canonical) | 1.0 | 3.5 px |
| M | 1.5 | 4.0 px |
| L | 2.0 | 4.5 px |
| XL | 2.75 | 6.0 px |

**Colour carries identity, not function.** "Colors used in the interface represent the individuals who are interacting within the mesh, not the activities or objects they are using." Each child picks a stroke/fill pair (their "XO colours"); everything they make wears those colours, even on someone else's machine. System icons stay greyscale so that "the icon's form … clearly indicate[s] its function." Disabled state is **never** grey-out (the display had a greyscale mode) — instead, inactive controls render as a white outline with no fill. **[C]**

Other concrete numbers: default UI font DejaVu LGC Sans at 7 pt on a 200 dpi display; black text on white for fine text, colour on white for large print; rollover/palette animation staged at 0.1 s background change → 0.3 s primary rollover → 1.0 s secondary rollover. **[C]**

**Retrospectives and critiques.** Sugar is widely judged a usability failure even by sympathetic observers. Nicholas Negroponte later said that building Sugar was "one of the biggest mistakes OLPC made," arguing the XO should have shipped a conventional Linux desktop with Sugar as an application layer on top **[D]**. OSnews's contemporaneous critique named the specific complaints that recur everywhere: closing an activity is "incredibly non-obvious"; unlabelled icons amount to "mystery meat navigation"; mandatory full-screen is inflexible; and children reared on Sugar are disadvantaged when they meet a normal computer **[D]**. Practical deployments frequently ended up dual-booting Sugar and a conventional desktop. Paul Dubroy's sympathetic review still flags that activities must be *explicitly* managed to free RAM, exposing an OS-level concern (the "activity ring" showing memory use) directly to children **[D]**.

**My reading of why Sugar failed, and what survives.** Three of Sugar's four big bets were wrong for the wrong reasons, and one was right:

1. **Wrong:** the zoom metaphor. Four levels of nested "where am I" for a five-year-old, with the two outermost levels devoted to a mesh network, is a lot of navigation to buy very little.
2. **Wrong:** the Frame. An invisible, hot-corner-invoked, four-edge, mode-bearing control surface is a discoverability disaster for pre-readers, and hot corners conflict with the child's habit of resting a hand at the screen edge.
3. **Wrong:** unlabelled abstract icons everywhere, in the name of internationalisation, with no audio layer to compensate. Sugar was designed before ubiquitous TTS was cheap; kidnix has no such excuse.
4. **Right, and still under-copied:** the **Journal**. Auto-keep, resume-not-open, temporal ordering, implicit versioning, and the portfolio framing are all excellent, evidence-consonant ideas that no mainstream child product has since matched.

**Sugarizer** (the HTML5/JS reimplementation, still actively developed) kept the Journal and the buddy-colour identity, but quietly dropped or softened the hardest parts. Its stated principles are Performance, Simplicity, Usability, Adaptability, Recoverability and Security; its structure is **three** components, not four zoom levels — Home page (activity icons, personal favourites pinned), Journal, Network view. The Journal is opened by an icon directly beneath the child's central XO avatar; entries are ordered by most-recent, can be renamed in place, starred as favourites, and filtered/sorted/searched from a top bar. Hovering an activity on Home shows its recent instances so you can *resume* or *start new*. Icons are "simple, stylized, and recognizable in both black and white and color." **[C]**

That simplification — **fewer levels, a discoverable Journal button, keep the colour identity** — is essentially the right correction, and kidnix should start from Sugarizer's shape rather than Sugar's.

### 2.2 Commercial kids' shells

**Amazon Kids (Fire tablets).** A child profile boots to "a curated home screen filled with the apps and content they are allowed to use," drawn from an allow-list the parent curates plus the Amazon Kids+ catalogue. Parents get time limits, a device bedtime, and "Learn First" gating (educational content before entertainment), all managed from a separate web/app dashboard rather than on the device. Exiting the child profile means tapping a deliberately dull "Grownups" icon and entering a PIN. **[D]**
*Notable:* the parent dashboard being **off-device** is a good pattern — it removes the parent-configuration surface from the child's environment entirely. *Notable in the other direction:* parents in public forums consistently complain that the Fire kids home screen is a **store-like content grid** that surfaces things the child does not have, is redesigned without warning, and is dense with carousels — i.e. it optimises for catalogue consumption, not for making things.

**Google Kids Space.** Four tabs — **Play / Read / Watch / Make** — over expert-curated content, with a child-made avatar and recommendations seeded by the child picking interests. Parental controls live in a separate Family Link app on the parent's phone. Google states it consulted education academics for age-appropriateness. **[D]**
*Notable:* the **verb-based top-level taxonomy** (four words, four icons) is much better for pre-readers than a category or brand taxonomy, and "Make" being a peer of "Watch" is the right politics. *Notable:* it is still fundamentally a consumption library, and there is no journal — nothing the child makes has a home.

**Apple Guided Access.** Not a shell but a lock: pins the device to a single app, lets an adult disable screen regions by drawing on them, disable hardware buttons, and set a session time limit; exit requires a passcode or biometric. **[D]** *Relevance:* it is the minimal viable "kid mode" and shows the value of a **hard, physical-feeling boundary** the child cannot argue with. Its weakness is that it is a cage with no positive content and no ending ritual — the session just stops.

**Nintendo.** The Switch home is a single horizontal row of large square game tiles with no folders by default — arguably the most successful "no file system, one row of big pictures" launcher ever shipped. Parental controls are a **separate phone app** that reports play time and enforces limits, and the console shows a full-screen "time's up" alert. **[D]** *Steal:* one row, huge tiles, zero nesting; parent controls on the parent's own device.

**Endless OS.** A GNOME derivative aimed at low-resource and education markets: a paged **app grid as the desktop itself** (arrows/scroll/two-finger swipe between pages, dot page indicator), a dash of favourites, "just start typing to search," and an emphasis on minimising distraction. **[D]** It is the closest mainstream Linux analogue to what kidnix needs, and confirms that a paged icon grid over a GNOME base is a workable technical shape — but it is still a desktop with windows underneath.

**Kano OS.** Shipped on a build-it-yourself Raspberry Pi kit, with a narrative "story mode" onboarding that framed setting the computer up as a quest, and a levelling/XP system over the OS itself. **[D]** *Steal:* onboarding as narrative, and making the act of assembling and configuring the computer part of the play. *Avoid:* XP/levels attached to the operating system, which is exactly the extrinsic-motivation trap §4.9 argues against.

### 2.3 Children's apps whose design decisions are documented

**ScratchJr** is the best-documented design process for a 5–7 tool anywhere, and its findings map almost one-to-one onto kidnix's problems. **[A]**

Design themes (Flannery et al., IDC 2013): **Low Floor and (Appropriately) High Ceiling; Wide Walls; Tinkerability; Conviviality** — the last defined as "Make the interface feel friendly, joyful, inviting, and playful, with a positive spirit of exploration and learning."

Concrete decisions and the evidence behind them:
- **Text was the single largest barrier.** "The largest barrier to young children on Scratch was the platform's reliance on words. Thus a main design choice for ScratchJr was eliminating the reliance on text and creating simple commands with universal symbols" (Blake-West & Bers, 2023). In baseline testing, second-graders could find Scratch blocks by text label; kindergarteners and first-graders could not.
- **Every action must have a visible outcome, and must take time.** "It became clear that programming actions must not only have a visible output but also take time to run." Blocks with no visible effect stopped children forming cause–effect associations.
- **Unbounded controls are harmful.** Scratch let children type absurd numeric parameters; they were drawn to that instant-feedback novelty and away from their actual goal, then could not debug the result. ScratchJr bounded the ranges and added a **countable grid** so movement units are concrete.
- **Destructive actions were deliberately made hard.** Deleting a character "was purposely made difficult at the time to avoid accidental deletions" — and that then showed up as a thing children needed adult help with. This is the real tension: accident-proofing costs discoverability.
- **What children reliably learned:** finding block categories, dragging and snapping blocks, choosing characters and settings, drawing new ones, adding pages, pressing play, **and saving/opening projects**.
- **What they struggled with:** meta-level instructions with no immediate output, switching between characters, coordinating multiple scripts, choosing numeric parameters, deleting things, **acquiring a shared vocabulary for interface elements**, and choosing a strategy when stuck.
- **Scale of testing:** ~40 K–2 children in baseline Scratch work, 18 children in the first prototype pilot, then ~100 children across five classrooms in Phase 2, with video, audio and screen capture per child. Later evaluation (Blake-West & Bers 2023) confirms no floor effect for 5-year-olds — they *can* enter the environment unaided — but that engagement "was optimized with curricular support," i.e. an adult still matters.

The blocks palette is "centrally located, brightly colored… icon-based," with six categories shown one at a time, and the stage and scripting area "visually emphasized through size, position, and color." **[A]**

**Toca Boca / Sago Mini — "digital toys."** The philosophy is explicit: these are software *toys*, not games — no objectives, no victory conditions, no fail states, no score, no timers, minimal or zero text, no dialogue, no ads, no IAP. CEO Björn Jeffrey's stated rationale: before roughly age nine, children "are much less concerned with objectives and are content to simply play for the sake of playing." Interactions are limited to tapping and swiping. Characters *react* emotionally (concern, pleasure) so there is feedback without judgement. **[D]** Studio practice: small teams of 6–8 including dedicated "**play designers** rather than game designers"; a house style that resists over-polish — "things shouldn't be too perfect, there is still dirt in the corners, and there is always a weird, quirky element." **[D]**

**Khan Academy Kids.** Ages 2–8; five character guides including a narrator bear; either free exploration of a library or a personalised path; everything is read aloud; no ads, no subscription, no third-party tracking. **[D]** The pattern worth stealing is the **narrator-as-guide**: a single consistent voice that reads the interface, not just the content.

**Sesame Workshop, *Best Practices: Designing Touch Tablet Experiences for Preschoolers* (2012).** Distilled from "over 40 years of children's media testing… including more than 50+ touch screen studies." This is the densest set of concrete numbers available and I quote it heavily in §3 and §4. **[B]**

**BBC GEL, *How to design for children*.** Two generations: nine principles (2016, archived) and seven pillars (2020). The 2020 pillars are: give positive feedback and create moments of joy; **be visual, reduce text**; make the goal immediately clear; **be heard** (audio); animate with personality; **craft a character-led experience**; **forgiving design**. The 2016 version carries the concrete numbers and the extra principles (surprise, challenge/balance, natural discovery, consistency) that the 2020 rewrite dropped. **[B]**

Note the BBC's own example of character-led navigation: "The iPlayer Kids TV app has created a character first navigation. Whilst children may not be able to read at this age, they can recognise their favourite CBeebies and CBBC characters." **[B]** That is a strong argument for kidnix's activity tiles being **recognisable characters or scenes rather than abstract glyphs**.

**Osmo.** iPad + reflector + physical pieces; the camera reads real objects on the table. Marketed 6+. **[D]** Relevance to kidnix is limited but the principle is worth naming: *the best "no-UI" for a five-year-old is often no screen UI at all* — a webcam activity that reads a drawing on paper beats a drawing activity with a tool palette.

**Duolingo ABC.** Free literacy app for ~3–8, fully narrated, short lessons, no ads. Notably, Duolingo's flagship streak/XP machinery is **toned down** in ABC. **[D — could not verify directly; product page did not render]**

### 2.4 "Steal this / avoid this"

| Source | Steal this | Avoid this |
|---|---|---|
| **Sugar** | Journal-as-portfolio; auto-keep + keep-hints; resume-not-open; implicit versioning; colour = child identity, shape = function; two-tone SVG icon system with non-linear stroke scaling; "recoverability first"; never grey-out (use outline) | Four-level zoom metaphor; hidden Frame on hot corners; unlabelled abstract icons with no audio; exposing RAM/activity-ring to children; mesh-first architecture |
| **Sugarizer** | Three surfaces (Home / Journal / [Family]); Journal button under the child's own avatar; hover-to-see-instances (resume vs new); star-as-favourite | Still assumes reading for search/sort |
| **Amazon Kids** | Off-device parent dashboard; per-profile allow-lists; "Learn First" style content gating | Store-like grid that shows content the child can't have; carousel density; surprise redesigns |
| **Google Kids Space** | Four verb-tabs (Play/Read/Watch/Make); child-built avatar; parent controls on the parent's phone | Consumption-first library with no home for what the child made |
| **Guided Access** | A hard, unarguable boundary the child cannot negotiate with | Ending with a dead stop and no ritual |
| **Nintendo Switch** | One row of huge tiles, no nesting; time's-up as a full-screen event; parent app on parent's phone | — |
| **Endless OS** | Paged app grid *as* the shell; page dots; type-to-search | Windows and a real desktop underneath |
| **Kano OS** | Narrative onboarding; setting up the machine is part of the play | XP/levels attached to the OS itself |
| **ScratchJr** | Icon-only commands; every action has a visible, time-taking effect; bounded parameters; concrete countable units; a persistent Play control | Making destructive actions *so* hard that children need an adult; meta-level controls with no visible effect |
| **Toca Boca** | No score, no fail state, no timer inside activities; characters react rather than judge; "play designer" role; deliberate imperfection in the art | — (their model is close to ideal for kidnix's activities) |
| **Khan Academy Kids** | One consistent narrator voice reading the *interface*; optional path alongside free exploration | — |
| **Sesame** | Almost everything in §3–§4 | — |
| **BBC GEL** | Character-led navigation; forgiving hit areas and drag targets; audio for every state change; reward effort | The 2020 rewrite's loss of concrete numbers — use the 2016 version for specifics |

---

## 3. Visual & interaction design guidance (with numbers)

### 3.1 Targets, spacing and pointing

The single most-cited number: NN/g recommend **"at least 2 cm × 2 cm touch targets for young children (4 times bigger than the 1 cm × 1 cm recommended target size for adult users)."** **[B]** BBC GEL specifies **"large hit areas, minimum 64 px (based on a medium density screen) 9.6 mm on all interactive elements."** **[B]** WCAG 2.2 sets an absolute floor of **24 × 24 CSS px** (SC 2.5.8 Minimum, AA) with a 44 × 44 enhanced level (2.5.5, AAA); platform HIGs land at 44 pt (Apple) and 48 dp (Material). **[B]**

**kidnix recommendation.** Work in millimetres, then convert.

| Element | Physical | CSS px @96 dpi | Notes |
|---|---|---|---|
| Primary child-facing target (activity tile, Journal card, big action) | **≥ 20 mm** | **≥ 76 px** (use **80**) | NN/g floor |
| Secondary child-facing target (tool, colour swatch) | ≥ 14 mm | ≥ 53 px (use **56**) | Only where an accident is cheap |
| Minimum gap between adjacent targets | **≥ 8 mm** | **≥ 30 px** (use **32**) | Sesame: hot spots "must be large and adequately isolated" |
| Destructive / irreversible control | ≥ 20 mm **and** ≥ 24 mm from anything else | — | Isolation is the accident-proofing, not a dialogue |
| Adult-facing control inside the parent panel | ≥ 9 mm | ≥ 34 px | Normal adult standards apply |

Also from Sesame **[B]**:
- **Register input on touch-down, not on lift** — "children tend to tap the screen too hard, long, or multiple times… until they see evidence that their interaction has registered." The equivalent for mouse is: fire the affordance (highlight + sound) on *press*, commit on *release*, and make press-then-drag-away cancel harmlessly.
- **Gesture ranking:** tap (most intuitive) → draw/move finger → swipe → drag → slide; then the hard ones: pinch, tilt/shake, multi-touch, flick, double-tap. Children "have difficulty with finger-on-screen continuity" for drag and trace, so **support partial completion**.
- **Double-tap is only ever appropriate as an intentional barrier** — "we suggest only using double tap to prevent a child from accidental navigation (e.g. leaving an activity, accessing parent content)." That is directly useful for kidnix's exit and parent-gate design.
- **Keep active controls away from the bottom edge**, where children rest their wrists and "bump" out of the activity.

For mouse/trackpad specifically, NN/g's development table says 3–5s have "very limited" fine motor skill and prefer touchscreens; 6–8s can manage trackpad clicking and simple keyboard, but **dragging** is a 9+ skill on a mouse. **[B]** Assal et al. found children "tend to accidentally drag and double-click" with a mouse and recommend touch input where possible. **[A]**

→ **kidnix must never require a drag to accomplish anything essential.** Every drag interaction needs a tap-tap (pick up, put down) equivalent, and every drop target must be generously oversized relative to its graphic — BBC GEL: "Ensure that drag targets are sufficiently forgiving by increasing their area outside the dimensions of the underlying graphic." **[B]**

### 3.2 Layout and grid

Sugar's 16 × 12 grid of 75 px cells with 15 px subcells is a sound model. **[C]** For kidnix on modern displays:

- **Base unit: 8 px.** All spacing is a multiple of 8.
- **Tile unit: 160 × 160 px** for an activity tile at 1080p (icon safe area 96 × 96 centred, label band 40 px). At 1366 × 768 use 128 × 128.
- **Home grid: at most 3 rows × 4 columns = 12 activity tiles, one page, no scrolling.** Sesame: "Scrolling vertically below a page fold is conceptually difficult for children"; NN/g: avoid scrolling entirely for 3–5s. If a family installs more than 12 activities, **page** horizontally with large arrows and page dots (the Endless pattern) rather than scrolling — Sesame notes horizontal scrolling "is more intuitive (e.g. a film strip)." **[B]**
- **Everything important is on screen at first paint.** Sesame: "all important interactive elements should be on screen upon initial load."
- **Scan order is left-to-right, top-to-bottom.** Put the most important thing top-left.
- **Reserve a persistent, never-moving chrome band.** Unlike Sugar's hidden Frame, kidnix should have a *visible*, unmoving strip. See §5.

### 3.3 Typography

Pre-readers do not read the interface — but *early* readers (6–8) do, they read slowly, and reading a word they half-know is a moment of pride. Type therefore needs to be readable, not absent.

**Typeface.** Two strong candidates, both open-licensed:
- **Andika** (SIL) — designed explicitly for literacy learners: single-storey **a** and **g** matching handwriting, capital I / lowercase l / numeral 1 made visually distinct, "rn" made not to look like "m", sans-serif, large well-positioned diacritics, and thousands of glyphs subtly differentiated so "readers' brains distinguish between similar characters." **[C]** This is the correct default for child-facing text in a system aimed at 4–8s in the UK.
- **Atkinson Hyperlegible** (Braille Institute) — designed for low vision: unambiguous letterforms, clear uprights, distinct pairs (E/F, p/q), open counters, spurs and tails. **[C/D — the vendor cites adoption numbers and awards, not controlled legibility studies.]** Good as the *parent-panel* face and as an accessibility alternative.

**Sesame's guidance** is different and worth noting as a dissent: child-facing text should approximate **Zaner-Bloser** (the US school handwriting model), "Fonts should not include serifs." **[B]** The UK equivalent would be a **cursive-precursor infant font** (e.g. the Sassoon family, or a comic/print-script). Andika is the closest freely licensable approximation and I would not chase a UK handwriting model at v0.1.

**Sizes** (CSS px at typical laptop viewing distance ~50–60 cm; scale up on larger/further displays):

| Role | Size | Weight |
|---|---|---|
| Activity tile label / any single word a child must read | **40 px** | Semibold |
| Primary sentence read aloud + shown (e.g. ending ritual) | **32 px** | Regular |
| Journal entry title | **32 px** | Semibold |
| Secondary child-facing text (dates, counts) | **28 px** | Regular |
| Absolute minimum any child-facing glyph | **24 px** | — |
| Parent panel body | 16–18 px | Regular |

Line length for early readers: **≤ 40 characters**. Line height 1.5. Never justify. Never all-caps for words a child is decoding (lowercase word shapes carry information).

**Word-by-word highlighting** during read-aloud is expected by parents in story contexts, and should be **toggleable off** so a parent can read at their own pace (Sesame). **[B]** kidnix should apply the same to the shell's read-aloud: highlight the word being spoken.

### 3.4 Colour and contrast

- **Adopt Sugar's split:** *colour = whose it is; shape = what it is.* Each child chooses a two-colour identity at profile creation; their avatar, their Journal cards, their tile highlights and their cursor all wear it. Activity icons stay in a restrained system palette so that form does the work of identification. **[C]** This solves multi-child switching almost for free (§4.4).
- **Contrast:** child-facing text at **≥ 7:1** (WCAG AAA), non-text/UI boundaries at **≥ 4.5:1** (one level above the 3:1 minimum). Reserve pure black text on white or near-white for anything being decoded — the OLPC HIG's reasoning about black-on-white legibility still holds on LCDs. **[C]**
- **Never encode meaning in hue alone.** ~1 in 12 boys has a colour vision deficiency and a 5-year-old cannot self-diagnose it.
- **A single reserved highlight colour.** Sesame: "Highlight color should be considered early… It should be distinct from other colors in the activity (e.g. bright yellow or neon green)." **[B]** kidnix should reserve one colour (I suggest a warm yellow) that *only ever* means "this is the thing you can touch right now" — used for focus rings, read-aloud word highlight, and the shell's hint glow. Nothing else may use it.
- **Never grey-out to disable.** Sugar's alternative — outline-only, no fill — is better because it survives greyscale, high-contrast modes and colour blindness. Better still for kidnix: **don't show controls that aren't available.** A pre-reader cannot interpret "disabled."

### 3.5 Motion

BBC GEL is unambiguous that motion is a benefit, not a cost, for this audience: use "physical weight and inertia," exaggeration, arcs of motion, and easing to avoid "abrupt and awkward ends." "Characterless or poor quality animation can have negative effects on how immersive an experience is." Transitions specifically earn their keep as orientation: "Showing the journey between two places makes it much easier for our young users to work out where they are, where they've come from and where they're going." **[B]**

Against that, WCAG 2.3.3 and the vestibular-disorder literature: motion triggered by interaction must be disableable, because reactions include "nausea, migraine headaches, and potentially needing bed rest." Parallax and large-area background motion are the worst offenders; the recommended mechanism is `prefers-reduced-motion`. **[B]**

**kidnix recommendation:**
- **Durations:** micro-feedback 80–150 ms; UI state change 200–300 ms; **spatial transition between shell surfaces 350–450 ms** (long enough to be legible as a journey to a five-year-old; anything under ~250 ms reads as a cut).
- **Easing:** ease-out for entrances, ease-in-out for moves; a small overshoot (5–8%) on entrances is the cheapest way to buy "personality."
- **Cap concurrency:** at most one large motion at a time on the shell surfaces. Activities may be busier.
- **Reduced motion:** honour `prefers-reduced-motion` *and* surface it in the parent panel as a plain-English switch ("Calm mode — less movement and quieter sounds"). In reduced mode, cross-fade instead of translate, drop overshoot, keep durations, and **keep the earcons** (they are the child's orientation cue).
- **The timer must not be an anxiety animation.** No pulsing, no red, no accelerating tick. See §4.6.

### 3.6 Sound, earcons and read-aloud

Audio is the load-bearing accessibility layer for a pre-reader, and both major guideline sets say so.

BBC GEL: "Associate sound FX to UI elements to help with cognitive understanding. Provide a sound equivalent to any transitional states such as loading bars or scene changes… Implemented well, immersive audio can open up new worlds for children with visual impairments, allowing them to play games or navigate UIs with the use of audio cues alone." Also: "Be judicious in the tone of FX ensuring that repeated play doesn't irritate." **[B]**

Sesame, more specifically **[B]**:
- **"Children typically do not pay attention to audio instructions alone."** Audio must always be paired with a visual. This is the single most important audio finding and it cuts against a naive "just read everything out" design.
- **"Put the specific instructions at the end of the sentence, not at the beginning"** — e.g. *"To give Elmo a crayon, tap on the X!"* Children act on the last thing they heard.
- **Interruptibility:** make non-essential prompts interruptible, "especially on replay." (Story text is the exception — uninterruptible narration can aid comprehension.)
- **Sound effects confirm input registration** — children expect immediate feedback from a touch.
- **A consistent sound (or music change) should mark the transition from watching to doing.**
- **Idle time-outs:** re-prompt after **3–5 s of inactivity for stories, 6–8 s for games**, as "a concise suggestion for what to do next."
- **Background music:** enhances engagement but "monitor volume"; keep it under speech.

**kidnix earcon set (proposal).** Keep it tiny — six sounds, each ≤ 400 ms, distinguished by pitch contour rather than timbre so they survive cheap speakers:

| Event | Character |
|---|---|
| Focus / hover a tile | Very quiet single note, rising |
| Commit / open | Two-note rising, brighter |
| Back / close | Two-note falling |
| Something was kept in the Journal | Soft "click-chime", the *only* sound with a bell character |
| Ask-a-grown-up sent | Distinct, warm, slightly longer (this must feel like an event) |
| Session phase change (10 min / 2 min / end) | A three-note motif, same motif each time, dropping a tone each phase |

Rules: never more than one earcon per 250 ms; earcons duck under speech; a global volume control in the parent panel plus a child-facing mute that is *visible* (a speaker tile), because a muted machine that looks broken is worse than a loud one.

**Read-aloud design.** kidnix's requirement is "read-aloud for everything." Concretely:
- **Focus-follows-speech.** Whenever an element receives focus (hover after ~600 ms dwell, keyboard focus, or touch-down without release), speak its label. This is the "audio hover" pattern and it is how a pre-reader explores a screen safely — you can hear what a thing is *before* committing to it. Touch-down-to-hear / lift-to-activate is the touchscreen analogue (and is exactly VoiceOver's explore-by-touch model).
- **Always pair with a visual.** Highlight the element and show the word in the reserved highlight colour while speaking it.
- **Speak the noun, not the sentence.** Tile labels are one or two words. Save sentences for the ending ritual and the ask-a-grown-up flow.
- **One voice.** Khan Academy Kids' narrator-bear model: a single consistent voice reads the *shell*. Activities may have their own voices; the shell must not.
- **Offline TTS.** Given kidnix is offline-capable, use a local engine (Piper or similar) with a UK English child-friendly voice, and **pre-render the fixed shell strings to audio files** so the shell never waits on synthesis.

### 3.7 Icons, skeuomorphism and characters

**Icons for pre-readers.** BBC GEL: "Icons for children should be designed so they represent actions or objects in a recognisable manner. They need to be easily distinguishable from each other, be recognised as interactive and separate from the background. Also have no more visual complexity than that required to accomplish their task." **[B]** Sesame: "use consistent, representational icons that follow standard convention," and interactive elements must be "visually distinct (e.g. color, line weight, art style) from the rest of the screen." **[B]** ScratchJr's finding is the strongest version: replacing text labels with "simple commands with universal symbols" was the change that opened the tool to 5-year-olds. **[A]**

The recurring word is **representational**. Abstract glyphs (a gear, a hamburger, three dots, a floppy disk) are learned conventions that a five-year-old has not learned. Concrete depictions of *the thing itself* are not. So:

| Instead of | Use |
|---|---|
| Gear / settings glyph | A grown-up's face or a key |
| Hamburger menu | Nothing — there is no menu |
| Floppy-disk save | Nothing — saving is automatic |
| Folder | Nothing — there is no file system |
| Pencil "edit" glyph | A picture of the actual thing, tapped to resume |
| Abstract "back" chevron | A large arrow *plus* a shrunken thumbnail of where you're going back to |

**Skeuomorphism vs flat.** There is no controlled study I could find that settles this for 5-year-olds, so this is judgement **[D]**: flat design's core problem is that it removes the affordance cues (bevel, shadow, edge) that signal "this is a thing you can press," and a pre-reader has no compensating convention knowledge. Sesame's guidance is effectively pro-affordance — "Objects should only look touchable when they are touchable," and use "a strong visual highlight (typically yellow) behind an active icon." I would therefore build **flat-with-depth**: flat, high-contrast illustration for the *content* of an icon, but every interactive surface gets a real elevation cue (a 2–4 px offset shadow and a 2 px darker bottom edge) and a visible press state that moves it. Nothing non-interactive gets that treatment. Add BBC GEL's "subtle animation" idle cue on the primary action.

**Characters and mascots.** Sesame is emphatic: characters are used "as 'hosts' or 'guides' throughout the learning process… it is critical to build on this relationship in digital media experiences" **[B]**. BBC GEL makes character-led navigation one of seven pillars, and reports that the iPlayer Kids app is navigated by character recognition because children cannot yet read **[B]**. Khan Academy Kids uses five characters with one narrator **[D]**.

The wider evidence on **pedagogical agents** is more equivocal than the children's-media industry implies: meta-analyses in multimedia learning generally find small positive effects that are driven by *social cues and voice* rather than by the on-screen body, and there is a real risk of the agent becoming a source of extraneous load or of distraction. I could not retrieve a meta-analysis specific to 4–8s during this research **[gap]**.

**kidnix recommendation:** have **one** character, use it as the *voice* and as the *messenger for transitions* (arriving to say hello, waving at the end, carrying the ask-a-grown-up note), and keep it **out of the working canvas** entirely. Do not let it comment on the child's work, and do not let it be the reward. A character that turns up only at boundaries is a ritual object; a character that hovers is an interruption.

---

## 4. Pattern catalogue

Each pattern: best examples → what evidence says → recommended kidnix design.

### 4.1 Onboarding without text

**Best examples.** Kano's narrative "story mode" onboarding **[D]**. Sesame: "Most content begins with a character or friendly adult narrator greeting the user," and for app-specific experiences "adults tend not to use tutorials located in the 'Help' sections. It is better to embed them in an initial startup screen and/or overlay" **[B]**. BBC GEL: "If you have ever seen a child open a new toy, they very rarely read the instructions. So treat your experience as a toy, that children should be able to pick up and play" **[B]**.

**Evidence.** ScratchJr's floor study shows 5-year-olds *can* enter a well-designed environment with **no instruction at all** — but that engagement was "optimized with curricular support" **[A]**. Children skip written instructions reliably and across decades (NN/g observed the same behaviour in studies eight years apart) **[B]**.

**kidnix design.** No tutorial. First boot runs a **60-second ritual, not a lesson**:
1. Character appears, says hello, asks the child to **choose their colours** (a 3 × 3 grid of colour pairs — this is the identity choice, and it is also the first success).
2. Character asks the child to **choose a picture of themselves** (avatar from ~12 illustrated options, or take a webcam photo).
3. Character says "This is your place. Everything you make lives here" and the Journal button pulses once.
4. Straight into Home. Nothing else.

The *real* onboarding is the shell being explorable: audio-on-focus (§3.6) means a child can hear every tile without committing to any. If a child idles on Home for 8 seconds, the character gives one short contextual hint naming a specific tile ("You could do some drawing!") and then goes quiet for 60 seconds. Sesame's 6–8 s idle window is for in-game prompts; the shell should be slightly more patient.

### 4.2 Read-aloud and audio hover

Covered in §3.6. Two additional patterns:

- **A read-aloud "ear" control.** Some children will want to re-hear a thing. A single persistent, always-in-the-same-place ear/speaker button that **repeats the last thing said** is more useful and more learnable than per-element replay affordances.
- **Speech is never a gate.** Nothing should be un-actionable until narration completes. Sesame's interruptibility rule applies: tapping through the voice is normal child behaviour, not an error.

### 4.3 The Journal

**Best examples.** Sugar's Journal (the design rationale in §2.1) and Sugarizer's simplification. **[C]**

**Evidence.** There is no controlled study showing children navigate temporal stores better than hierarchical ones — Sugar's claim rests on a cognitive-plausibility argument, and Sugar's own field record is not a success story. What *is* solidly supported: children cannot manage file hierarchies, cannot spell reliably enough to search, and pre-readers cannot read a file list at all. The Journal's real justification for kidnix is not "children understand time" but "**there is nothing else for them to understand**."

**kidnix design — "My Things."**
- **Auto-keep only.** No save button anywhere in the system. Every activity keeps on a timer (60 s), on activity switch, on session end, and on activity-declared *keep-hints* before destructive operations (Sugar's model — keep before a clear-canvas, before a delete-all). **[C]**
- **Entries are pictures.** A Journal card is a **thumbnail of the thing**, at ≥ 20 mm, with the activity's icon in the corner and a date band. No text is required to identify anything.
- **Newest first, grouped by day**, with day headers rendered as words *and* an illustration ("Today", "Yesterday", "Saturday"). No infinite scroll — page it.
- **Resume, don't open.** Tapping a card resumes that instance in its activity. This is Sugar's best idea and it removes the entire open/save mental model.
- **Star = favourite**, and starred things appear in a "My favourites" strip at the top of the Journal (Sugarizer's pattern). **[C]**
- **No deletion by the child, ever.** A child can *hide* a thing (it goes to a "put away" area visible only in the parent panel). Deletion is a parent action. This inverts ScratchJr's problem — they made deletion hard and children needed adults; kidnix should make it *impossible* and not pretend otherwise.
- **No falloff at v0.1.** Sugar's temporal-falloff garbage collection is elegant and premature; disk is cheap now. Revisit only if storage becomes a real constraint.
- **Implicit versioning is worth keeping** if cheap: keeping every auto-keep as a diff gives you an "undo the whole day" affordance in the parent panel that will pay for itself the first time a child paints over a drawing they loved.

### 4.4 Profiles and logging in

**Best examples.** Sesame: "we recommend designing logins so that children can recognize their own profile (such as their name and a unique icon)" and assume adult assistance for registration **[B]**. Sugar/Sugarizer's buddy colours give each child a whole-system identity **[C]**. Google Kids Space and Amazon Kids both use avatar-per-profile **[D]**.

**Evidence.** Assal, Imran & Chiasson tested three PassTiles graphical-password variants with **25 children aged 7–12 (mean 9.5)** and adults: children were most successful with **Objects** PassTiles (images of distinct objects) and least with word tiles; both groups preferred graphical passwords to their existing schemes; but **login success rates were "less than desirable"** even for the best scheme, with most failures being near-misses. Their recommendations include using familiar objects from the child's world, touchscreen over mouse input, **shorter passwords for children**, and threshold/typo-tolerant matching. **[A]** Choong, Theofanos & Renaud surveyed 189 US children in grades 3–8 on password practice **[A]**. Ratakonda et al.'s *KidsPic* is a further image-based scheme designed with children **[A — metadata only, not read in full]**.

The clear implication: **children aged 5–6 cannot reliably authenticate, and should not be asked to.** The threat model for a family laptop does not require it.

**kidnix design.**
- **"Who's here?" screen** at boot and after any session end. Big avatar tiles (≥ 30 mm), one per child, plus a small, visually dull **"Grown-up"** tile. Each child tile is drawn in that child's chosen colours. Speak each name on focus.
- **No password for children.** Tapping a face is logging in. Children switching between each other's profiles is a social problem, not a security problem, and a shared family machine has no secrets worth a PIN.
- **Optional "my picture code"** for a 7–8-year-old who wants privacy: pick 3 objects from a 4 × 4 grid of familiar illustrated objects (Assal et al.'s Objects finding, shortened per their R2). Store it as a preference, allow the parent to bypass, and **never** lock a child out — three failures just logs them in with a "shall I get a grown-up?" nudge.
- **Identity is worn everywhere.** The child's two colours tint the shell chrome, the Journal cards, the cursor and the timer. A child who walks up to the machine can tell at a glance whose session it is — which matters far more than authentication.

### 4.5 The parent gate

**Best examples.** Sesame: parent-directed content "must live in a 'Parents' section that is not easily accessed by a child. **The icon for this section must not be enticing to a child**," and purchase links need "a 'baby gate' (i.e. an additional popup that asks for confirmation)" **[B]**. Amazon Kids uses a dull "Grownups" icon + PIN **[D]**. Guided Access uses a passcode **[D]**. Sesame separately notes double-tap's *only* good use is "to prevent a child from accidental navigation (e.g. leaving an activity, accessing parent content)" **[B]**.

**Evidence on efficacy.** I found no empirical study measuring bypass rates for the common gate types (arithmetic questions, "swipe in this direction", spelled-out numbers, long-press). **[gap]** What is known qualitatively: arithmetic gates are trivially beaten by 8-year-olds and increasingly by 6-year-olds; instruction-following gates ("press and hold the button for three seconds") fail against children who watch a parent do it once; PINs are the only gate whose difficulty does not decay with the child's development, and they fail against shoulder-surfing, which is the dominant attack in a family.

**kidnix design.** Layer three things and be honest that none is strong:
1. **Unenticing entry.** The grown-up affordance is a small, low-saturation button in a fixed corner of the shell chrome, labelled with a plain adult face and the word "Grown-up." It never animates, never glows, and is never announced by the character. Sesame's rule.
2. **A friction gate, not a security gate:** press-and-hold for **3 seconds** with a visible progress ring. This defeats accidental entry and small hands' impatience, which is 90% of the actual need.
3. **A 4–6 digit PIN** behind that, with keypad digits in a **shuffled layout each time** (cheap mitigation against a child memorising finger positions rather than digits).

Additionally: **the parent panel should not be the main parent surface.** Follow Amazon and Google — the substantive controls (time budgets, which activities exist, reviewing the Journal, approving "ask a grown-up" requests) should be reachable from a **separate device on the local network**, so that a parent never has to take the machine off a child to change a setting, and so that the on-device panel can stay tiny.

### 4.6 The visible session timer

**Best examples.** Time Timer's red disc, which depletes as an area rather than counting digits — legible to a child with no numeracy. Nintendo's full-screen "time's up." Amazon's per-day limits and bedtime. **[D]**

**Evidence.** Children's ability to discriminate durations improves markedly through ages 3–5 and continues developing; 5-year-olds significantly outperform younger children on temporal bisection tasks, and discrimination is poor when intervals are close together **[A]**. Practically: a 5-year-old has *some* relative sense of "a long time" versus "a short time" and essentially no absolute sense of "twelve minutes." Time Timer cites a Florida Atlantic University study of 2–4-year-olds at risk of developmental delay reporting increased engagement and improved independence/accuracy in self-regulation with a visual timer **[D — vendor-summarised, small n, at-risk population; do not over-claim]**. A 2025 study of visual timers in elementary maths assessment exists but I could not retrieve it (403) **[gap]**.

**kidnix design.**
- **A depleting shape, not a number.** A ring or a sand-glass whose *filled area* shrinks. Numerals may appear only for a child in the 7–8 band, off by default.
- **Slow, non-alarming.** No colour change to red, no pulse, no acceleration. The most defensible metaphor for a UK 5-year-old is a **setting sun**: a sky that moves from bright day through gold to dusk over the session, with the timer ring as the sun's position. It is legible peripherally, it is inherently calm, and it maps onto a daily rhythm children already know.
- **Always present, never central.** Fixed position in the chrome band; it never moves, never overlaps content, and is never the thing being animated when something else is happening.
- **The child can look, but not change.** Tapping the timer speaks the remaining time in child terms ("about as long as one story") — mapping duration to a *familiar activity length* is far more meaningful than minutes.

### 4.7 The ending ritual — the most evidence-rich pattern here

**Evidence (strong).** Hiniker et al., *Screen Time Tantrums* (CHI 2016): interviews with 27 parents plus a diary study with a separate 28 families, yielding 380 logged transitions from children aged 1–5 (mean 38 months). **[A]** Findings:

1. **Parent warnings made things worse, not better.** 21 of 27 parents routinely used advance warnings. In the diary data, children were "significantly more upset about transitions when they were warned by parents that screen time would be ending (mean = 3.35, sd = .71, 95% CI [3.22, 3.49]) than when they were not warned (mean = 3.03, sd = 0.81), **F(1, 331) = 20.34, p < .001, η² = .058**." Re-running the analysis controlling for who or what triggered the transition, the effect persisted: 3.36 vs 3.06, F(1, 238) = 10.21, p = .002, η² = .041. The authors combed the qualitative data for a confound and "were unable to identify any significant differences that might account for children's negative response to warnings." Their interpretation: a transition warning may "serve as an unwelcome" assertion of control — it threatens the child's sense of autonomy.
2. **Technology-triggered endings were significantly gentler than parent-triggered ones.** Comparing 43 technology-triggered transitions ("The DVD ended", "The iPad battery ran out") with 55 parent-triggered ones, children were less upset when "the technology turned itself off" (mean = 2.98, sd = .74) than when the parent turned it off (mean = 3.47, sd = .79), **F(1, 69) = 8.104, p = .006, η² = .105** — and a small but significant effect survived controlling for session duration (F(1, 68) = 6.780, p = .011).
3. **Routine helped.** Transitions ending a *routine, predictable* period of screen time were smoother (mean 2.84) than ad hoc ones (mean 3.10), F(1, 331) = 16.751, p < .001. But routine screen time also lasted **longer** (40.0 min vs 29.5 min, p = .008) — a real trade-off.
4. **Natural stopping points matter.** Families turn screens off "when parents are ready to give their child their full attention **and** technology presents a natural stopping point." The authors' design recommendations: remove autoplay and suggested-content features; prompt families to set goals; "ask at natural stopping points if they would like to continue or take a break"; offer suggested next activities; and ask the child how many more minutes they'd like.

This is directly counter to the naive design ("warn at 5 minutes, warn at 1 minute, cut off"), and it is the most important single finding in this whole note for kidnix.

**kidnix design — the ending ritual.**

- **The machine ends the session, and it is visibly the machine's decision, never the parent's.** The parent sets the budget once, out of sight, on another device. The child never sees a parent press anything. This buys the p = .006 effect.
- **Make the session's shape predictable.** Same length by default every day (routine effect), with the sun's position readable from across the room. Accept the trade-off that routine sessions may run slightly longer than ad hoc ones — the calmness is worth it.
- **Do not use bare countdown warnings.** Replace "5 minutes left" with **an offer at a natural stopping point**. Concretely, at roughly T−6 minutes the character appears *between* actions (never mid-stroke, never mid-note) and asks a **choice** question: *"The sun's going down. Do you want to finish this one, or start one last little thing?"* Two large picture buttons. This preserves autonomy, which is the mechanism Hiniker et al. implicate.
- **T−2 minutes: "let's put your thing away."** The character helps the child *complete* rather than abandon — the Journal card for the current work animates from the canvas into the Journal, with the keep earcon. The point is that the last thing that happens is a **success**, not a removal.
- **The goodbye screen.** Full-screen, calm, quiet. It shows **what the child made today** as a small row of Journal thumbnails, names it ("You made three things today"), and offers exactly two things: **"Show a grown-up"** and **"Goodnight."** Then the machine goes to the "Who's here?" screen. No countdown, no lock icon, no red.
- **A "one more?" is allowed once, and is the parent's to grant, asynchronously.** If the child presses "Ask for more time," it goes into the ask-a-grown-up queue (§4.10). It does not extend the session by itself. If the parent grants it from their phone, the sun rises a little. If not, nothing happens and no one has to say no.
- **Never end mid-creation.** The activity API should let an activity declare "I am at a natural boundary" (page finished, note released, drawing stroke complete) and the shell should always wait for the next boundary within a small grace window.

### 4.8 Error prevention, recovery, undo, confirmation

**Evidence and guidance.** Sugar: "Recoverability is fundamental to encouraging exploration… undo is the primary and essential means" **[C]**. BBC GEL: "Reversibility of actions is important to encourage exploration. Allowing a child to step back from an action gives them confidence to continue" **[B]**. NN/g: reduce cognitive load, prevent errors, use self-explanatory interfaces **[B]**. ScratchJr: making deletion hard produced adult dependence **[A]**.

The dissent on confirmations comes from Sesame, which *does* recommend them for genuinely destructive acts: "It is a good idea to require confirmation when a major program consequence will result, such as deleting a picture… an additional confirmation overlay (e.g. Are you sure? Yes or No) that is color-coded and utilizes recognizable icons (e.g. green check mark and red 'X')." **[B]**

**kidnix design.**
- **Prefer undo over confirmation, always.** A confirmation dialogue asks a five-year-old to predict a consequence — a theory-of-mind and executive-function task they are demonstrably bad at (NN/g **[B]**). Undo asks them to notice a consequence, which they can do.
- **A single, permanent, always-in-the-same-place undo.** Big (≥ 20 mm), in the chrome band, with a *representational* icon (an arrow curling backwards over a small thumbnail of the previous state) — not a glyph. Long, deep undo stacks (≥ 50 steps), persisted across resume.
- **Design the destructive actions out of existence.** No delete in the child's shell. No overwrite (auto-keep is versioned). No "clear all" without a keep-hint snapshot first (Sugar's model).
- **Where a confirmation is genuinely unavoidable** (I can think of one: leaving an activity that cannot resume), follow Sesame exactly: two large picture buttons, green tick / red cross, with the consequence shown as a picture, read aloud, and with the *safe* option in the position of the child's dominant reach.
- **Forgive imprecision.** Snapping (BBC GEL's jigsaw example), oversized drop zones, partial-completion acceptance for traces and drags, and no penalty for tapping the same thing twice.

### 4.9 Feedback and reward

**Evidence.** BBC GEL 2020, pillar 1: "**Recognise and celebrate effort and achievements** to help build a growth mindset… Children also see an animation when they get a question wrong, but we design them to encourage — not demoralise." **[B]** BBC GEL 2016: rewards "don't always need to be grand gestures… Where appropriate, reward the user for each interaction, however small," and toddlers "are less likely to understand the concept of scoring and performance." **[B]** Sesame: correct-answer "payoffs" should "reflect the curricular concept and user choice (e.g. 'Nice job choosing the letter A!')" with a sound effect and a visual; and for open activities with no right answer, "feedback is still necessary in the forms of encouragement and reaction to user input." **[B]** Toca Boca: no score, no objectives, no fail states at all — characters *react* rather than evaluate **[D]**.

The broader psychology (Dweck's process-praise work; Lepper's overjustification effect) points the same way: praising effort/process rather than ability supports persistence, and extrinsic rewards can undermine intrinsic interest in an already-interesting activity. **[A — cited from prior knowledge; not re-verified in this research pass.]**

**kidnix design.**
- **No points, no XP, no levels, no streaks, no badges, no leaderboards. Anywhere. Ever.** A streak is a mechanism for making a child anxious about a day off. This is the one place where kidnix should be dogmatic.
- **The reward is the artefact.** The Journal filling up is the progression system. The goodbye screen showing "you made three things today" is the celebration.
- **Micro-feedback everywhere.** Every interaction gets a sound + a small motion (BBC GEL). This is what "reward for each interaction, however small" means at the shell level — it is responsiveness, not scoring.
- **When language is used, describe rather than praise.** "You used a lot of blue!" over "Well done!" — this is the process-praise finding, and it is also what makes the character feel like a companion rather than a judge.
- **No fail states in the shell.** Nothing a child can do to the shell is wrong. If an action can't happen, the shell does something else pleasant rather than saying no (see §4.10).

### 4.10 "Ask a grown-up" — replacing silent denial

**Best examples.** There is no good prior art. Every kids' shell I examined either silently disables things (Amazon's allow-list) or blocks with an adult-facing message (Family Link). Sesame's "baby gate" is the closest, and it is a *barrier*, not a *request*. **[gap — this is genuinely novel territory for kidnix.]**

**Why it matters.** Silent denial teaches a pre-reader that the machine is arbitrary. A five-year-old cannot read "This app is not allowed," and cannot form the plan "go and find Mum." An explicit, low-cost request channel converts every boundary from a wall into a social act — and it gives the parent a stream of signal about what the child actually wants.

**kidnix design.**
- **Everything the child cannot do still appears**, drawn in outline-only (Sugar's inactive treatment — never greyed) with a small "grown-up" mark. Tapping it does not fail; it opens the ask flow.
- **The ask flow is three taps, no typing.**
  1. The character says "Shall I ask a grown-up?" with a **Yes** picture button and a **Not now** picture button.
  2. If yes: "What shall I say?" with 3–4 pre-composed picture options (*"Can I play this?"*, *"Can I have more time?"*, *"Can I show you something?"*, *"I need help"*) plus a **"Say it yourself"** option that records **up to 10 seconds of the child's voice**. Voice is the right input modality here: it is the one thing a five-year-old can produce fluently.
  3. Sent. A distinct earcon, and the request appears as a small envelope in the chrome band with the child's colours. **The child goes back to what they were doing.** The request never blocks.
- **The parent answers asynchronously** on their own device (or from the on-device panel). Yes / No / Later, plus an optional recorded voice reply. A recorded parent voice saying "not today, but tomorrow after school" is dramatically kinder than a grey dialogue, and costs nothing to build.
- **A "no" is delivered as a note, never as a modal.** The envelope opens, the parent's voice plays, and the character offers something else concrete.
- **Rate-limit gently and invisibly** — collapse repeats of the same request rather than telling the child off.

### 4.11 Help for pre-readers

**Evidence.** Sesame: "Since preschool-aged children typically cannot read, we do not find text-based 'Help' sections useful. Instead, we recommend help in the form of **context-specific dialogue and visual reinforcement**. We suggest including a thorough 'How-To' section aimed at parents." **[B]** BBC GEL: "If they lose their way offer a helping hand in the form of a **contextual hint**. Things are so much more rewarding when we figure it out for ourselves." **[B]** ScratchJr found that "when stuck, choosing a problem-solving strategy that allows continued work" was itself one of the hardest things for kindergarteners **[A]**.

**kidnix design.** There is **no help section**. There are three mechanisms:
1. **Audio-on-focus** (§3.6) — the ambient help layer. You can hear what everything is without doing anything.
2. **Idle contextual hints** — after ~8 s idle on a chooser surface, or ~10 s of no progress in an activity, one short spoken hint naming one specific next action, paired with a visual glow on that element (Sesame's "glow or sparkle as a time-out after instructions"). Then silence for 60 s. Never stack hints.
3. **"I need help"** in the ask-a-grown-up flow — because the honest answer for a five-year-old who is stuck is a person.
4. A **parents' "How it works"** page, text-heavy and unashamedly adult, in the parent panel — Sesame's recommendation.

### 4.12 Showing work, printing, and sending to family

**Evidence.** Thin. Sesame notes that "Record Your Own Voice" features are enjoyed by both children and parents **[B]**; the OLPC HIG lists printing as a per-entry Journal action **[C]**. Nothing empirical.

**kidnix design.**
- **"Show a grown-up"** is a first-class verb, available on every Journal card and on the goodbye screen. It puts the artefact full-screen with all controls removed — a *presentation* mode. This is the cheapest and most valuable sharing feature and it requires no network at all.
- **Printing** is one button on a Journal card, with an unmistakable representational icon (a printer with paper coming out) and an animation of the page emerging. Physical output is disproportionately motivating for this age and it is the thing that ends up on the fridge. Handle "no printer" by *not showing the button* rather than by failing.
- **Letters to family** should be composed of exactly three things: a picture (drawn or from the Journal), a recorded voice message, and a recipient chosen from a small grid of **photographs of people** (never names). Sending goes into a parent-approval queue — this is an ask-a-grown-up request with an attachment.
- **No open sharing, no accounts, no feeds.** Recipients are a fixed list configured by a parent.

### 4.13 Multi-child switching

**kidnix design.** Covered largely by §4.4. Additional points: switching is available from the chrome band as a small "Who's here?" button showing all the family avatars; switching **ends** the current child's session cleanly (auto-keep, Journal card, goodbye is skipped) rather than suspending it; each child's timer budget is independent; and the shell's colours change *visibly and with a transition* on switch, so both children can see whose turn it now is. Two children using the machine together should be supported by a **"two of us"** mode that attributes the session's Journal entries to both — collaboration is common at this age and forcing a single owner creates arguments.

---

## 5. Proposed information architecture and screen inventory — kidnix shell v0.1

### 5.1 Architecture

Three surfaces and one persistent band. That is the whole shell.

```
                 ┌──────────────────────────────────┐
   [boot] ─────► │        WHO'S HERE?               │
                 │   (profile chooser)              │
                 └──────────────┬───────────────────┘
                                │ tap a face
                                ▼
        ┌───────────────────────────────────────────────┐
        │                   HOME                        │  ◄── the only "root"
        │        (activity tiles, one page)             │
        └───┬───────────────────────┬───────────────────┘
            │ tap a tile            │ tap My Things
            ▼                       ▼
   ┌──────────────────┐    ┌────────────────────┐
   │    ACTIVITY      │◄───┤    MY THINGS       │  (resume from a card)
   │  (full screen)   │    │   (the Journal)    │
   └──────────────────┘    └────────────────────┘

   Always present, all three surfaces:  THE BAND
   [ Back ] [ Undo ] [ My Things ] ······ [ sun/timer ] ······ [ Ear ] [ Ask ] [ Grown-up ]

   Session end ──► ENDING OFFER ──► PUT AWAY ──► GOODBYE ──► WHO'S HERE?
```

There is **no** neighbourhood view, **no** frame, **no** hot corners, **no** search, **no** settings visible to the child, **no** window management, **no** app installer, **no** notifications other than the Ask envelope.

### 5.2 The band

A fixed 96 px strip at the **top** of the screen (top, not bottom — Sesame's finding that children rest wrists at the bottom edge and bump controls). It never hides, never scrolls, never reorders. It is tinted in the active child's colours.

```
┌───────────────────────────────────────────────────────────────────────────────┐
│ ( ← )  ( ↺ )  (▣ My Things)          ☀ ~~~~~~~~~~~         (👂) (✉) (  🧑  ) │
│  Back   Undo    Journal            sun / session           Ear  Ask  Grown-up │
└───────────────────────────────────────────────────────────────────────────────┘
```
- Back and Undo are ≥ 80 px, ≥ 32 px apart.
- The sun sits dead centre and moves left→right across the band over the session, descending as it goes.
- The Ear repeats the last spoken thing.
- Ask (envelope) is the child's channel; it shows a badge when a reply is waiting.
- Grown-up is small, desaturated, in the far corner, and requires a 3-second hold.

### 5.3 Screen inventory

**S1 — Who's here?**
```
┌───────────────────────────────────────────────────────────┐
│                     Who's here?                           │
│                                                           │
│    ┌────────┐      ┌────────┐      ┌────────┐             │
│    │  ( ⌣ ) │      │  ( ⌣ ) │      │  ( ⌣ ) │             │
│    │  ROSA  │      │  SAM   │      │ BOTH   │             │
│    └────────┘      └────────┘      └────────┘             │
│      teal/pink       green/gold      (two of us)          │
│                                                           │
│                                        ┌──────────┐       │
│                                        │ Grown-up │       │
│                                        └──────────┘       │
└───────────────────────────────────────────────────────────┘
```
Avatar tiles ≥ 30 mm, drawn in each child's colours, name spoken on focus. "Both of us" for shared sessions. The grown-up tile is deliberately plain.

**S2 — Home**
```
┌───────────────────────────────────────────────────────────────┐
│ BAND                                                          │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│   ┌─────┐   ┌─────┐   ┌─────┐   ┌─────┐                       │
│   │ 🖌  │   │ 🎹  │   │ 📖  │   │ 📷  │                       │
│   │Draw │   │Music│   │Books│   │Photo│                       │
│   └─────┘   └─────┘   └─────┘   └─────┘                       │
│                                                               │
│   ┌─────┐   ┌─────┐   ┌─────┐   ┌─────┐                       │
│   │ 🧩  │   │ ⌨  │   │ 📚  │   │ ✉  │                       │
│   │Games│   │Keys │   │Story│   │Post │                       │
│   └─────┘   └─────┘   └─────┘   └─────┘                       │
│                                                               │
│   ┌─────┐   ┌ ─ ─ ┐                                           │
│   │ 🧱  │   │ 🎬  │  ← outline-only: needs a grown-up          │
│   │Build│   │Films│                                           │
│   └─────┘   └ ─ ─ ┘                                           │
│                                                               │
│                                                        ● ○    │
└───────────────────────────────────────────────────────────────┘
```
Max 12 tiles, one page (page dots bottom-right if more). Tiles 160 × 160 with a 40 px label. Not-allowed activities render outline-only and open the Ask flow. Tiles the child has used recently carry a small thumbnail of their most recent work in the corner — the Sugarizer "hover to resume" idea made ambient.

**S3 — Activity.** Full-screen, band on top, everything else the activity's business. The shell guarantees: auto-keep, Undo routed to the activity, the sun, and a natural-boundary protocol for session end.

**S4 — My Things (Journal)**
```
┌───────────────────────────────────────────────────────────────┐
│ BAND                                                          │
├───────────────────────────────────────────────────────────────┤
│  ★ My favourites                                              │
│  ┌──────┐ ┌──────┐ ┌──────┐                                   │
│  │ img  │ │ img  │ │ img  │                                   │
│  └──────┘ └──────┘ └──────┘                                   │
│                                                               │
│  Today                                                        │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐                  │
│  │  img   │ │  img   │ │  img   │ │  img   │                  │
│  │ 🖌  ☆  │ │ 🎹  ★  │ │ 📷  ☆  │ │ 🖌  ☆  │                  │
│  └────────┘ └────────┘ └────────┘ └────────┘                  │
│                                                               │
│  Yesterday                                                    │
│  ┌────────┐ ┌────────┐                                        │
│  │  img   │ │  img   │                                        │
│  └────────┘ └────────┘                                        │
└───────────────────────────────────────────────────────────────┘
```
Cards ≥ 20 mm, thumbnail-dominant, activity icon + star in the corner. Tap = resume. Long-press (or a card-level "…" that is itself representational) offers **Show a grown-up / Print / Send to family / Put away**. Day headings spoken.

**S5 — Ending offer** (T−6 min, at a natural boundary)
```
┌───────────────────────────────────────────────────────────────┐
│                                                               │
│              🌇   "The sun is going down."                    │
│                                                               │
│      ┌───────────────────┐     ┌───────────────────┐          │
│      │   Finish this     │     │  One last little  │          │
│      │      one          │     │       thing       │          │
│      └───────────────────┘     └───────────────────┘          │
│                                                               │
│                     ( Ask for more time )                     │
└───────────────────────────────────────────────────────────────┘
```

**S6 — Put away** (T−2 min). No buttons. The current work animates into the Journal with the keep earcon; the character says "Let's keep that."

**S7 — Goodbye**
```
┌───────────────────────────────────────────────────────────────┐
│                                                               │
│              You made three things today                      │
│                                                               │
│        ┌──────┐    ┌──────┐    ┌──────┐                       │
│        │ img  │    │ img  │    │ img  │                       │
│        └──────┘    └──────┘    └──────┘                       │
│                                                               │
│    ┌────────────────────┐      ┌──────────────────┐           │
│    │  Show a grown-up   │      │    Goodnight     │           │
│    └────────────────────┘      └──────────────────┘           │
└───────────────────────────────────────────────────────────────┘
```

**S8 — Ask a grown-up.** Three steps as in §4.10, each a full screen with at most three large picture buttons.

**S9 — Parent panel** (behind hold + PIN). Adult typography, adult density, no characters. Tabs: *Children* (profiles, colours, avatars), *Time* (daily budget, session length, bedtime), *Activities* (which tiles exist per child), *Requests* (the Ask queue), *Their things* (browse/print/delete/restore the Journal, including version history), *Family* (recipients for letters), *How it works*, *Calm mode* (reduced motion + quiet audio).

### 5.4 State model

Exactly five shell states: `CHOOSING` (S1) → `HOME` → `IN_ACTIVITY` ⇄ `JOURNAL` → `ENDING` (S5–S7) → back to `CHOOSING`. Every transition is animated as a spatial move so the child can see the journey (BBC GEL). There is no state a child can reach that has no visible way back to `HOME`.

---

## 6. How to test it with children

**Method sources.** Hanna, Risden & Alexander's *Guidelines for usability testing with children* (interactions, 1997) remains the canonical protocol reference **[A — metadata retrieved; full text paywalled and not read in this pass]**. Read's *Fun Toolkit* is the standard instrument set for measuring children's experience **[A/B]**. Druin's cooperative inquiry positions children as design partners **[A — from prior knowledge]**.

**The Fun Toolkit and its limits.** Four instruments — **Smileyometer** (5-point smiley visual analogue scale), **Funometer**, **Again-Again table** (would you do this again? yes/maybe/no, per activity), and **Fun Sorter** (rank items against constructs). Read & Horton's 2025 review is candid about the biases **[A]**:
- **Ceiling effect** is the dominant problem: "if comparing two versions and the first is rated highly then the second cannot go higher — even if it is better." Children aged 6–9 show "a large tendency to score as Brilliant."
- Younger children cluster at the top and discriminate less; older children (13–14) score lower and discriminate more.
- Mitigations they recommend: introduce the scale with **practice questions spanning the range**; use **spoken** administration with visual support for pre-readers; take **before and after** ratings (expected vs experienced fun) and analyse the *difference*; report means *and* medians; watch for order effects.
- Their conclusion is reassuring on one point: young children *can* use Smileyometers with support, contrary to earlier assumptions.

**For kidnix specifically, a practical protocol:**

1. **Sessions of 20–30 minutes maximum**, one child at a time, in a familiar room, with a parent visible but not in the child's eyeline. Have a clear "you can stop whenever you like" statement at the start, and honour it instantly.
2. **Do not use classical think-aloud.** Concurrent verbalisation is a dual-task load that 5-year-olds cannot carry; it depresses performance and produces confabulation. Use instead:
   - **Peer tutoring / two-child pairs** — a child explaining to a friend produces natural talk without the artificial "keep talking" instruction. (This is also how children will actually use kidnix.)
   - **Retrospective prompting** over a screen recording: "what were you looking for here?"
   - **Silent observation with behavioural coding** as the primary data.
3. **Code behaviour, not opinion.** The reliable measures at this age are: time to first meaningful action; number of unprompted recoveries after a wrong tap; number of adult appeals; whether the child returns to the Journal unprompted; and **affect at the transition** — was the child upset when the session ended (this is the metric that matters most, and Hiniker et al. give you a 5-point upset scale precedent).
4. **Wizard-of-Oz the expensive bits first.** The ask-a-grown-up flow, the ending ritual and the character's voice can all be run by an adult with a laptop and a second screen before a line of production code exists. The ending ritual in particular is a *social* design, and the only way to know whether the "finish this one / one last thing" offer works is to run it on a real child at a real bedtime.
5. **Run the Again-Again table daily rather than the Smileyometer once.** "Do you want to do that again tomorrow?" over 10 consecutive days is a far better signal than a single 5-face rating, and it dodges the ceiling problem.
6. **Longitudinal diary from the parent.** Hiniker et al.'s design — a short structured diary entry per session covering trigger, duration, and how upset the child was — is cheap, gives you the transition metric, and can run for weeks.

**Ethics when your own child is the participant.** This deserves explicit care:
- **Consent is continuous, not one-off.** A 5-year-old cannot consent, but they can assent and can withdraw; treat any reluctance as withdrawal, immediately, with no persuasion.
- **The power asymmetry is total.** Your child will tell you they like it. This is the strongest possible ceiling effect, and it means **you cannot be the person who collects opinion data about your own product from your own child.** Get behaviour data yourself; get opinion data from other people's children, or have another adult run the sessions.
- **Do not instrument the child.** Analytics that a child cannot understand and did not agree to, on a machine in their bedroom, is not acceptable even from a parent. Keep telemetry local, aggregate, and reviewable in the parent panel.
- **Separate the roles in time.** "We're testing the computer" sessions should be visibly different from "you're playing" sessions, so that ordinary play does not become surveilled.
- **Recruit beyond the household early.** A design tuned to one child, by that child's parent, will overfit badly. Two or three other families at 4, 6 and 8 will tell you more than a hundred sessions with one child.

**Metrics worth tracking in the product (locally, privately):**

| Metric | Why |
|---|---|
| Time-to-first-creation from boot | The floor test (ScratchJr's method) |
| Sessions ending at a natural boundary vs. forced | Direct measure of the ending design |
| Child-reported upset at ending (parent diary, 1–5) | The Hiniker et al. outcome measure |
| Ask-a-grown-up requests sent / answered / median latency | Whether the channel is real or theatre |
| Undo uses per session | Rising = exploration; a sudden fall may mean the child has stopped experimenting |
| Journal entries created vs. resumed | Resume rate is the test of whether the Journal metaphor landed |
| Adult appeals per session (observational) | The discoverability metric that matters |

---

## 7. Things NOT to do

1. **Don't build a zoom metaphor, a Frame, or hot corners.** Sugar's navigation innovations are the parts that failed. Three surfaces, one visible band.
2. **Don't use abstract glyphs without audio and without a label.** Mystery-meat navigation was the single most-repeated criticism of Sugar. If a five-year-old has to have learned a convention, it is the wrong icon.
3. **Don't require dragging for anything essential.** Under-9s on a mouse cannot drag reliably; even on touch, "finger-on-screen continuity" fails.
4. **Don't put controls at the bottom edge of the screen.**
5. **Don't grey things out.** Outline them, or don't show them.
6. **Don't use confirmation dialogues as your safety net.** Use undo, versioning, and removing the destructive action entirely. Reserve confirmations for the one or two genuinely irreversible cases, and make them pictorial.
7. **Don't count down at the child.** Parent-style warnings measurably *increase* upset (p < .001). Offer choices at natural stopping points instead, and let the machine — never a visible parent action — end the session.
8. **Don't ship points, XP, streaks, badges, levels or leaderboards.** Not in the shell, not in activities. Streaks in particular punish a day off, and this is a product for a five-year-old.
9. **Don't scroll vertically on any child-facing surface.** Page horizontally.
10. **Don't put the parent's configuration surface in front of the child.** Off-device where possible; behind a dull, unenticing, non-animated control where not.
11. **Don't let the character live on the canvas.** Boundaries only — hello, hints, transitions, goodbye. A commenting mascot is an interruption and a judge.
12. **Don't deny silently.** Every wall is an ask-a-grown-up request.
13. **Don't ask a child to authenticate.** Faces, not passwords. Even the best graphical scheme tested had poor login success rates with 7–12s.
14. **Don't build a search box.** A five-year-old cannot spell; the Journal must be navigable entirely by picture and by day.
15. **Don't expose system state to children.** Sugar showed RAM usage in the activity ring. Nothing about storage, memory, updates, battery percentage, or network should ever reach the child's surfaces.
16. **Don't optimise the home screen for content the child doesn't have.** The Fire tablet failure mode: a store dressed as a home.
17. **Don't build a settings screen for the child.** The only child-facing preferences are their colours, their avatar, and mute.
18. **Don't trust your own child's opinion of your own product.**

---

## 8. Top 10 takeaways

1. **The Journal is Sugar's one great surviving idea, and no commercial kids' product has copied it.** Auto-keep, resume-not-open, temporal ordering, versioning, portfolio framing. Build this first — it is kidnix's differentiator and it eliminates the file system rather than hiding it.
2. **Colour means *whose*; shape means *what*.** Sugar's identity system solves multi-child switching, ownership and personalisation in one move, for almost no implementation cost.
3. **Warnings from a parent make endings worse; endings triggered by the machine make them better** (Hiniker et al., 380 transitions, p = .006). Design the ending as the machine's decision, offered as a *choice* at a natural boundary, ending with a success and a goodbye — never as a countdown and a cut.
4. **Audio is not an accessibility afterthought; it is the primary label layer** — but Sesame's finding that "children typically do not pay attention to audio instructions alone" means every spoken thing must be paired with a visual highlight.
5. **20 mm minimum targets, 8 mm minimum gaps, no essential drags, input registered on press.** These four numbers will prevent most of the frustration a 5-year-old will experience.
6. **Representational icons, not glyphs; character-led navigation where possible.** BBC found children navigate iPlayer Kids by recognising characters because they cannot read; ScratchJr found removing text was the change that opened the tool to 5-year-olds.
7. **Undo everywhere; confirmation almost nowhere; no delete at all.** Recoverability is what licenses exploration. Confirmation dialogues ask a five-year-old to do the one thing they are developmentally worst at — predicting a consequence.
8. **No scores, no streaks, no fail states.** Toca Boca's "digital toy" position is the correct one for 4–8, and the reward should be the artefact in the Journal, not a number.
9. **Replace every silent denial with an ask-a-grown-up request** — three taps, a voice recording, non-blocking, answered asynchronously by a parent's recorded voice. This is genuinely novel and it is the humane answer to the parental-controls problem.
10. **Sugar failed on navigation, not on philosophy.** Take the Journal, the auto-keep, the recoverability principle, the colour identity and the icon system; leave the zoom metaphor, the Frame, the hot corners and the unlabelled icons in 2007.

---

## 9. Full source list

**Primary design documentation**
1. OLPC, *OLPC Human Interface Guidelines* (2006–), archived — http://wiki.laptop.org/go/OLPC_Human_Interface_Guidelines (via web.archive.org) **[C]**
2. OLPC HIG — *The Sugar Interface: Icons, Colors, Text and Fonts, Layout Guidelines, Toolbars, Rollovers, Controls* (same document) **[C]**
3. Sugar Labs, *Human Interface Guidelines* — https://wiki.sugarlabs.org/go/Human_Interface_Guidelines **[C]**
4. Sugarizer, *Design* — https://sugarizer.org/docs/articles/design_en.html **[C]**
5. Sugarizer, *The Journal* — https://sugarizer.org/docs/articles/journal_en.html **[C]**
6. Sugarizer project site — https://sugarizer.org/ **[C]**
7. Sesame Workshop, *Best Practices: Designing Touch Tablet Experiences for Preschoolers* (2012) — https://joanganzcooneycenter.org/wp-content/uploads/2020/02/SesameWorkshop-2012.pdf **[B]**
8. BBC GEL, *How to design for children* (2020, 7 pillars) — https://www.bbc.co.uk/gel/features/how-to-design-for-children-2 **[B]**
9. BBC GEL, *How to design for children* (2016, 9 principles, archived) — https://www.bbc.co.uk/gel/features/how-to-design-for-children **[B]**
10. NN/g, *Children's UX: Cognitive Development* — https://www.nngroup.com/articles/kids-cognition/ **[B]**
11. NN/g, *Children's UX: Physical Development* — https://www.nngroup.com/articles/children-ux-physical-development/ **[B]**
12. NN/g, *Children's Websites: Usability Issues* — https://www.nngroup.com/articles/childrens-websites-usability-issues/ **[B]**
13. Designing for Children's Rights (D4CR) — https://d4cr.org/ **[B/D]**
14. W3C, *Understanding SC 2.5.8 Target Size (Minimum)*, WCAG 2.2 — https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html **[B]**
15. W3C, *Understanding SC 2.3.3 Animation from Interactions* — https://www.w3.org/WAI/WCAG22/Understanding/animation-from-interactions.html **[B]**
16. SIL, *Andika: Design* — https://software.sil.org/andika/design/ **[C]**
17. Braille Institute, *Atkinson Hyperlegible* — https://www.brailleinstitute.org/freefont/ **[C/D]**

**Peer-reviewed research**
18. Flannery, Kazakoff, Bontá, Silverman, Bers & Resnick, *Designing ScratchJr: Support for Early Childhood Learning Through Computer Programming*, IDC 2013 — https://sites.bc.edu/devtech/wp-content/uploads/sites/181/2018/02/scratchjr_idc_2013.pdf **[A]**
19. Blake-West & Bers, *ScratchJr design in practice: Low floor, high ceiling*, IJCCI 37 (2023) 100601 — https://doi.org/10.1016/j.ijcci.2023.100601 **[A]**
20. Hiniker, Suh, Cao & Kientz, *Screen Time Tantrums: How Families Manage Screen Media Experiences for Toddlers and Preschoolers*, CHI 2016 — https://faculty.washington.edu/alexisr/ScreenTimeTantrums.pdf **[A]**
21. UW CHiLL Lab, *Screen Time Transitions* research programme — https://depts.washington.edu/chilllab/research/screen-time-transitions/ **[A]**
22. Read & Horton, *Using the Smileyometer to measure UX with children*, Interacting with Computers (2025), doi:10.1093/iwc/iwaf016 — https://academic.oup.com/iwc/advance-article/doi/10.1093/iwc/iwaf016/8131678 **[A]**
23. Experience Research Society, *Fun Toolkit* method page — https://experienceresearchsociety.org/ux-methods/fun-toolkit/ **[B]**
24. Assal, Imran & Chiasson, *An Exploration of Graphical Password Authentication for Children*, IJCCI (2018); preprint https://arxiv.org/pdf/1610.09743 **[A]**
25. Ratakonda, Mehrpouyan & Fails, *"Pictures are easier to remember than spellings!": Designing and evaluating KidsPic*, IJCCI (2022), doi:10.1016/j.ijcci.2022.100515 **[A — metadata only]**
26. Choong, Theofanos & Renaud, *"Passwords protect my stuff" — a study of children's password practices*, J. Cybersecurity (2019), doi:10.1093/cybsec/tyz015 **[A — metadata only]**
27. Hanna, Risden & Alexander, *Guidelines for usability testing with children*, interactions 4(5), 1997, doi:10.1145/264044.264045 **[A — metadata only, paywalled]**
28. Frontiers in Psychology (2021), *time perception in 3–5 year olds* (temporal bisection) — https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2021.688165/full **[A]**

**Products, retrospectives and press**
29. Wikipedia, *Sugar (software)* — https://en.wikipedia.org/wiki/Sugar_(software) **[D]**
30. Dubroy, *The innovative interface of the OLPC laptop* — https://dubroy.com/blog/the-innovative-interface-of-the-olpc-laptop/ **[D]**
31. OSnews, *The OLPC Sugar Interface: Don't Do It* — https://www.osnews.com/story/16582/the-olpc-sugar-interface-dont-do-it/ **[D]**
32. Liliputing, *Negroponte: Sugar OS was OLPC's biggest mistake* — https://liliputing.com/negroponte-sugar-os-was-olpcs-biggest-mistake/ **[D]**
33. ICTworks, *OLPC's Predictable Failure* — https://www.ictworks.org/olpc-predictable-failure/ **[D]**
34. Google, *Kids Space* — https://families.google/kidsspace/ **[D]**
35. Amazon, *How to set up a Fire tablet for kids* — https://www.aboutamazon.com/news/devices/set-up-fire-tablet-kids **[D]**
36. Endless OS Help Center, *Shell introduction* — https://helpcenter.endlessos.org/latest/C/shell-introduction.html **[D]**
37. Khan Academy Kids — https://www.khanacademy.org/kids **[D]**
38. EdSurge, *Understanding the Toca Boca Phenomenon* (2015) — https://www.edsurge.com/news/2015-09-18-understanding-the-toca-boca-phenomenon **[D]**
39. Motionographer, *The design process behind Toca Boca's infectious apps* (2016) — https://motionographer.com/2016/04/27/the-design-process-behind-toca-bocas-infectious-apps/ **[D]**
40. Scratch Foundation, *ScratchJr Interface Guide* — https://www.scratchfoundation.org/learn/learning-library/scratchjr-interface **[D]**
41. Good Design, *Osmo by Tangible Play* — https://good-design.org/projects/osmo-by-tangible-play-inc/ **[D]**
42. PBS Kids Video app — https://pbskids.org/apps/pbs-kids-video **[D]**
43. Time Timer, *Research in education* — https://timetimer.eu/research-in-education/ **[D]**
44. Dezeen, *Microsoft and Kano build-your-own PC* (2019) — https://www.dezeen.com/2019/06/26/microsoft-kano-build-your-own-pc-technology/ **[D — 403 on fetch; listed for follow-up]**

**Known gaps for a follow-up pass**
- LEGO's internal digital design guidelines for children (not public).
- A meta-analysis of pedagogical agents specific to ages 4–8.
- Empirical bypass rates for parental-gate designs.
- Controlled comparison of skeuomorphic vs flat affordances with pre-readers.
- Full text of Hanna et al. 1997 and of the 2025 visual-timer study in elementary maths assessment.
- Duolingo ABC's design decisions (product page did not render).
