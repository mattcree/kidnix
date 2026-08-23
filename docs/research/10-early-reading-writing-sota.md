# 10 — Early reading and writing at 4–6: state of the art, and a design for "Sounds & Words"

*Research note for the kidnix project. Compiled 23 August 2026. Extends `05-learning-science.md` §2a/§2b/§3/§4 and `SYNTHESIS.md` §4 with UK-specific primary sources retrieved and read in full.*

**Evidence tags** (same scheme as `05`): `[META]` meta-analysis · `[SR]` systematic review · `[RCT]` randomised trial · `[QE]` quasi-experimental · `[OBS]` observational · `[GUID]` evidence-panel guidance · `[CURR]` statutory · `[VENDOR]` maker's claim · `[RATIONALE]` design reasoning, untested · `[absent]` searched for, not found.

---

## 1. What England actually does, 2024–2026

### 1.1 The policy stack got *denser*, not looser

Three documents landed after `05` was written and all three matter:

- **The DfE [Writing Framework](https://www.gov.uk/government/publications/the-writing-framework) (8 July 2025, 150 pp.)** `[GUID]` — the writing counterpart to the Reading Framework, and the first UK statement of position on typing at primary. Read below; it is unexpectedly favourable to what kidnix wants to build.
- **Ofsted, ['Strong foundations in the first years of school'](https://www.gov.uk/government/publications/strong-foundations-in-the-first-years-of-school) (8 October 2024)** `[GUID]` — Reception-focused. Its sharpest finding is about writing: "teaching handwriting only in phonics sessions… means that children do not learn the basics of letter formation that establish the foundations for speedy and fluent handwriting later on". Also: "if the Reception curriculum is not clear enough about what all children need to learn, it can become merely a list of activities."
- **Ofsted, ['Telling the story: the English education subject report'](https://www.gov.uk/government/publications/subject-report-series-english/telling-the-story-the-english-education-subject-report) (5 March 2024)** `[GUID]` — phonics is the part of English that is working; **writing, spelling and spoken language are not**. Recommends pupils "practise word reading using decodable books that match the sounds they know", that early writers "practise transcription skills in isolation", and notes teachers **rarely use dictation** despite its value.

Add the [Curriculum and Assessment Review final report](https://assets.publishing.service.gov.uk/media/690b96bbc22e4ed8b051854d/Curriculum_and_Assessment_Review_final_report_-_Building_a_world-class_curriculum_for_all.pdf) (DfE, Nov 2025) `[CURR]`, which **retains the Phonics Screening Check** ("we consider it important that the check remains") and reports **80% meeting the standard in 2024/25** against a pre-pandemic 82%. Writing is the identified national weakness: 28% miss the expected standard at KS2 writing.

**Reading for kidnix: phonics is settled UK policy through at least 2027's revised curriculum. Writing is the open wound. An activity that produces *more writing practice with a real audience* is aimed at the gap the state itself has named.**

### 1.2 The validated-SSP regime

The DfE's [list of validated phonics teaching programmes](https://www.gov.uk/government/publications/choosing-a-phonics-teaching-programme/list-of-phonics-teaching-programmes) `[CURR]` (last updated **16 February 2026**) names **45 programmes**, including Little Wandle Letters and Sounds Revised, Read Write Inc., Sounds-Write, Essential Letters and Sounds, Unlocking Letters and Sounds, Twinkl Phonics, Jolly Phonics, Letterland, Bug Club Phonics, Floppy's Phonics, Monster Phonics, Phonics Shed, Song of Sounds, Supersonic Phonic Friends. Validation requires "all that's essential to teach SSP… in the reception and key stage 1 years", plus "a structured route for most children to meet or exceed" the screening-check benchmark.

**Letters and Sounds (2007) was removed from that list** — but the document itself is still published on gov.uk under **Crown copyright and the Open Government Licence v3.0** ([publication page](https://www.gov.uk/government/publications/letters-and-sounds); [214-page PDF](https://assets.publishing.service.gov.uk/media/5a7aa7b6e5274a34770e630c/Letters_and_Sounds_-_DFES-00281-2007.pdf)). That distinction is the single most useful licensing fact in this note and §5 builds on it: *removed from the validated list* ≠ *withdrawn* ≠ *unlicensed*. Every one of the 45 validated programmes is a paid, closed product; L&S 2007 is the only complete, openly-licensed English GPC progression with published word banks, caption banks and phase criteria.

### 1.3 What the Reading Framework says that software people usually get wrong

The [Reading Framework](https://www.gov.uk/government/publications/the-reading-framework-teaching-the-foundations-of-literacy) (updated 22 September 2023, 171 pp.) `[GUID]` is more specific than its reputation. Read in full, six statements bear directly on interaction design:

1. **Letter names come *after* sounds, and are not optional.** "Programmes teach that each lower-case letter has a corresponding capital letter; they share the letter name and represent the same sound… **Some programmes teach the names of letters only once pupils have learnt to say the sounds.**" Note the framing: names are taught, just not first. See §2.4.
2. **Sound buttons and underlines are an official convention, not a vendor gimmick.** On `ff`, `ll`, `ss`, `ck`: "it is a good idea to **draw a line underneath both letters** to show that they represent one phoneme (e.g. `hill`, `pick`)… and encourage children to do so in their writing" (Letters and Sounds, p. 70 — carried through in current practice).
3. **Decodable books should run "alongside or a little behind" the teaching**, never ahead. "A book that includes the word 'play' should be placed so that children are not asked to read it until the digraph 'ay' has been taught."
4. **Dictation is "a vital part of a phonics session"** — "Writing simple dictated sentences that include words taught so far gives children opportunities to practise and apply their spelling, **without their having to think about what it is they want to say**."
5. **Do not drill pseudo-words.** "Teachers should not ask pupils to read lots of pseudo-words to prepare for the phonics check." The check is 20 real + 20 pseudo-words, ~5 minutes, Year 1, re-screened in Year 2. Pseudo-words are "the purest measure of decoding ability" but are a *measurement* device, not a *teaching* device.
6. **Phonically-plausible spelling is expected and should not be corrected.** The Framework's own worked example of acceptable Reception writing is: *"me and my frens went in a cafai and had caix"*.

Two more from the **Writing Framework (2025)**: teachers should not teach lead-in strokes or cursive in Reception, and — the sentence kidnix should quote to parents verbatim —

> "For primary schools, it would be most appropriate to introduce [typing] formally in upper key stage 2… **Before this, familiarisation with keyboards in computing appears to be sufficient.** … For most pupils, teaching typing should therefore not be prioritised at the expense of teaching handwriting."

That is DfE policy explicitly endorsing "find the key" over "learn to type" at 5–6, and explicitly protecting handwriting. kidnix's keyboard activity is now *aligned with published guidance* rather than merely defensible.

---

## 2. What the evidence supports, ranked by strength

### Tier 1 — strong, replicated, and policy-anchored

| Finding | Evidence | Size |
|---|---|---|
| **Systematic synthetic phonics improves word reading.** | [EEF Toolkit, phonics strand](https://educationendowmentfoundation.org.uk/education-evidence/teaching-learning-toolkit/phonics) `[META]` — **228 studies**, security rated high (one padlock deducted "because a large percentage of the studies were not independently evaluated"). | **+5 months**, very low cost. 1:1 +8 months, small groups +4. |
| **PA instruction *with letters* beats PA instruction without.** | [WWC Foundational Skills](https://ies.ed.gov/ncee/wwc/PracticeGuide/21) `[GUID]` Strong Evidence, 17 studies; Ehri et al. (2001) NRP `[META]`, quoted inside L&S itself. | — |
| **Children must read connected decodable text, not just word lists.** | WWC `[GUID]` Moderate (22 studies); [Murphy Odo 2024](https://onlinelibrary.wiley.com/doi/10.1111/lit.12368) `[META, 16 studies]`. | g = 0.20 word reading; g = 0.30 pseudoword decoding. |
| **Narrated storybooks with congruent multimedia beat plain adult reading; hotspots and embedded games *hurt*.** | [Takacs, Swart & Bus 2015](https://doi.org/10.3102/0034654314566989) `[META, 43 studies, 2,147 children]`. | g+ = 0.17 comprehension, 0.20 expressive vocabulary. |
| **Oral language intervention works at national scale.** | [West et al. 2021, NELI](https://doi.org/10.1111/jcpp.13415) `[RCT, 193 schools, 5,879 screened, 1,140 randomised]`; [2025 follow-up](https://doi.org/10.1111/jcpp.14157). | d = .26 (standardised), .32 (app-administered). |
| **Distributed practice.** | [Cepeda et al. 2006](https://doi.org/10.1037/0033-2909.132.3.354) `[META, 839 assessments]`. | Among the most robust effects in psychology. |

### Tier 2 — good evidence, important caveats

| Finding | Evidence | Size |
|---|---|---|
| **Set for variability ("try the other sound") is a bigger predictor of word reading than phonemic awareness, and is teachable.** | [Steacy et al. 2022](https://doi.org/10.1002/rrq.475) `[OBS, N=489]` — SfV explains **15% unique variance**, PA only **1%**; [Savage et al. 2018](https://doi.org/10.1080/10888438.2018.1427753) `[RCT, n=201]` — Direct Mapping + SfV beat best-practice small-group programmes at post-test **and** 5-month delayed post-test. | Genuinely actionable and almost absent from consumer phonics apps. |
| **Invented spelling is a *causal route in*, not a tolerated error.** | [Ouellette & Sénéchal 2017](https://doi.org/10.1037/dev0000179) `[OBS, N=171, path model]`; [Ouellette, Sénéchal & Haley 2013](https://doi.org/10.1080/00220973.2012.699903) `[RCT, n=40, 16 sessions]` — guided invented spelling **beat phonological-awareness instruction** on word reading. Both cited in the DfE Writing Framework's own reference list. | — |
| **Combined letter-name-and-sound instruction beats sound-only for letter-sound acquisition.** | [Piasta, Purpura & Wagner 2010](https://doi.org/10.1007/s11145-009-9174-x) `[RCT, n=58, 34 lessons]` — "Results suggest benefits of combined letter name and sound instruction in promoting children's letter sound acquisition. Benefits did not generalize to other emergent literacy skills." | Directly contradicts a naive "never show letter names" rule. See §2.4. |
| **Dialogic/shared reading moves vocabulary.** | [Mol et al. 2008](https://doi.org/10.1080/10409280701838603) `[META]`; [Noble et al. 2019](https://doi.org/10.1016/j.edurev.2019.100290) `[META]`. | Small-to-moderate; the mechanism is adult talk, not the book. |
| **Guidance helps most for the youngest.** | [Lazonder & Harmsen 2016](https://doi.org/10.3102/0034654315627366) `[META, 72 studies]`. | d = 0.50–0.71. |

### Tier 3 — the digital evidence, which is worse than the marketing

This is the section that should govern kidnix's promises.

| Product / class | Best evidence | Result |
|---|---|---|
| **GraphoGame / GraphoLearn** | [McTigue, Solheim, Zimmer & Uppstad 2019, *RRQ*](https://doi.org/10.1002/rrq.256) `[SR + META, 28 studies, meta n=19]` | **g = −0.02 overall.** The one significant moderator was **adult interaction**: high-adult-interaction studies averaged **g = 0.48**. |
| **GraphoGame Rime (UK)** | [EEF efficacy trial](https://educationendowmentfoundation.org.uk/projects-and-evaluation/projects/graphogame-rime) `[RCT, 398 pupils, 15 schools, Year 2]`, evaluated by NFER | **−1 month, very high security.** "The trial found no evidence that GraphoGame Rime improves pupils' reading or spelling test scores." Teachers found it "highly engaging, motivational and enjoyable" — engagement and effect fully decoupled. |
| **Lexia Core5** | [O'Callaghan et al. 2016, *BJEP*](https://doi.org/10.1111/bjep.12122) `[RCT, n=98, ages 4–6, N. Ireland]`; [Cockerill et al. 2024, *JADP*](https://doi.org/10.1016/j.appdev.2024.101726) `[RCT, 620 pupils, 57 schools, England]` | ηp² = .070 (small) on phonological skills, but **35% of the intervention group made no progress**; England trial **+0.08 overall, +0.18 low-SES**. |
| **ABRACADABRA** | [Piquette, Savage & Abrami 2014](https://doi.org/10.3389/fpsyg.2014.01413) `[RCT, n=203]` | d = 0.66 letter–sound, 0.52 blending, 0.52 word reading — **delivered as teacher-led whole-class instruction**, not solo play. |
| **Digital reading interventions in general** | [Pasqualotto et al. 2025, *J Cogn Enhancement*](https://doi.org/10.1007/s41465-025-00336-2) `[META, 41 studies / k=194 poor readers; 15 / k=69 general]` | **g = 0.433** poor readers, **g = 0.256** general readers. Reading-specific skills (decoding, comprehension) worked; domain-general "brain training" only helped poor readers. |
| **App effects generally** | [Kim, Gilbert, Yu & Gale 2021](https://doi.org/10.1177/23328584211004183) `[META, 36 studies, 285 ES]` | +0.31 SD, **shrinking** for standardised outcomes, older children, and unconstrained skills. |
| **Teach Your Monster to Read, Reading Eggs, Nessy, Phonics Hero, Headsprout, Bookbot, Starfall, Khan Academy Kids** | searched OpenAlex, Crossref, Europe PMC, EEF project index | **No independent RCT of early-reading outcomes located for any of them** `[absent]`. TYMTR remains evidence-*informed*, not evidence-*proven*. |

And the sentence that should be printed above the developer's desk, from the EEF Toolkit phonics strand itself:

> **"Approaches using digital technology tend to be less successful than those led by a teacher or teaching assistant."**

**The reconciliation across Tier 3 is not "software fails". It is that software's effect is a function of the adult beside it (g = −0.02 alone → g = 0.48 with high adult interaction; ABRA's d = 0.66 came from a teacher using it as a whiteboard). kidnix's structural weakness — a child alone at home — is precisely the moderator that zeroes the effect.** Everything in §3 is therefore designed to *recruit an adult into the loop at low cost*, and kidnix's honest claim remains: *this practises what your school is teaching, in a way children want to do.*

### 2.4 Letter names: the rule in `05` needs amending

`05` §3 and the GCompris curation spike both treat letter names as a deviation to be apologised for. The evidence does not support that framing.

- Piasta, Purpura & Wagner 2010 `[RCT]`: **letter names + sounds > sounds only** for letter-sound acquisition.
- Letters and Sounds itself teaches an **alphabet song in Phase Three, weeks 1–2** — i.e. letter names are introduced roughly six weeks after letter sounds, by the DfE's own programme.
- The Reading Framework: "Some programmes teach the names of letters **only once** pupils have learnt to say the sounds" — sequencing, not prohibition.

**Correct rule: sounds are the route to decoding and must be the only thing used inside blending and segmenting. Letter names belong in a separate, later, clearly-labelled mode (alphabet, "what's this letter called?", finding things in an index), and are *positively* supported once sounds are secure.** GCompris `click_on_letter` is therefore fine on the shelf — it just must never be presented as phonics, exactly as `CURATION.md` §4.1 already says, and it should be gated behind "the school has taught most Phase 2 sounds".

---

## 3. What software can do, what must stay human or on paper

| Job | Verdict | Why |
|---|---|---|
| Rehearse GPC recognition (see grapheme → say sound) | **Software, well** | Constrained skill; Kim et al.'s moderator analysis says this is where apps actually move. Cheap to space and retrieve. |
| Find a grapheme given a sound (screen or keyboard) | **Software, well** | It *is* an L&S Phase 2 success criterion ("find any Phase Two letter, from a display, when given the sound"). |
| Blend to read a decodable word | **Software, adequately** | Sound buttons + audio scaffold work; the child must say it aloud, which software cannot verify (child ASR is not good enough — see below). |
| Segment to spell (invented spelling) | **Software, adequately** | A phoneme frame plus letter tiles is a faithful digital magnetic-letters board. Never auto-correct. |
| Read a decodable sentence/book | **Software, well — if narration only** | Takacs et al. `[META]`: narration + congruent illustration helps; hotspots/games/dictionaries hurt. |
| Dictation practice (adult reads, child writes) | **Software, partly** | Recorded/synthesised sentence dictation is legitimate; the Reading Framework calls dictation "vital". But checking the child's attempt needs a human or a tile-based input. |
| Hear whether the child read the word correctly | **Human. Do not attempt.** | General ASR on 5-year-old UK-accented reading is unreliable; an offline model is worse. Any product that grades a child's oral reading will be wrong often enough to be harmful. |
| Rich, contingent talk about the story | **Human.** | The dialogic-reading effect *is* the adult. Software can only prompt one. |
| Handwriting / letter formation | **Paper. Explicitly disclaim.** | Kiefer et al. `[RCT]`; James & Engelhardt `[QE]`; Ofsted 2024 on formation basics; DfE Writing Framework 2025. |
| Deciding which GPC comes next | **The school. Never kidnix.** | Reading Framework fidelity clause; showing an untaught GPC actively undermines the programme. |
| Correcting spelling | **Nobody, at 5.** | Phonically-plausible attempts are the ELG. |

---

## 4. "Sounds & Words": the proposed suite

### 4.1 Modules × interactions × evidence

| # | Module | Core interaction | Journal artefact | Evidence anchor |
|---|---|---|---|---|
| **A** | **Hear it** | Play a phoneme; child picks which of 3 pictures starts (or ends) with it. Oral blending: "I'm thinking of a … /c/–/a/–/t/". No letters on screen. | none (warm-up) | WWC Strong Evidence, seg. of sounds `[GUID]`; L&S Phase 1 |
| **B** | **Find it** | Say /s/ → child taps the grapheme among 4 on screen **or presses the key**. Lowercase always. Digraphs = a two-key sequence that visually fuses into one tile. | none | L&S Phase 2 criterion `[CURR]`; DfE Writing Framework on keyboard familiarisation `[GUID]` |
| **C** | **Blend it** | Decodable word appears with **sound buttons** (dot under single-letter graphemes, **bar under digraphs/trigraphs** — the L&S underline convention). Child taps each button (it speaks the phoneme), then a "push together" slider merges them and the word is spoken. Then the child says it aloud to nobody in particular. | word list read today | Ehri/NRP `[META]`; L&S p. 70 convention `[CURR]` |
| **C+** | **Try the other one** | For known-tricky items, after a correct-but-wrong-vowel decode: "you said /wɒsp/… try the other sound". Explicit set-for-variability drill on a small, curated list. | — | Savage et al. 2018 `[RCT]`; Steacy et al. 2022 `[OBS]` |
| **D** | **Spell it** | Picture + spoken word → empty **phoneme frame** (one box per phoneme) + letter tiles limited to taught GPCs. Any phonically-plausible answer is accepted and celebrated; the conventional spelling is then shown alongside, unremarked, as "grown-ups write it like this". | the child's spelling, kept as typed | Ouellette et al. 2013 `[RCT]`; EYFS Writing ELG `[CURR]` |
| **E** | **Read it** | A 4–8 sentence decodable text, one sentence per screen, illustrated. **Optional** narration with word-by-word highlighting. **Zero hotspots, zero mini-games, zero tap-a-word dictionary.** Congruent, gentle illustration motion only. | "I read *Shark Facts*" + optional child-read recording | Takacs et al. 2015 `[META]`; WWC connected text `[GUID]`; Murphy Odo 2024 `[META]` |
| **F** | **Write it** | After reading: "write something about it." Type it (keyboard, lowercase, no autocorrect, no red squiggle) **or** record a voice note **or** "ask a grown-up to write it for me". Optional dictation mode: kidnix reads a sentence made only of taught GPCs, child types it, then compares. | caption/voice note → Journal, sendable via letters-to-family | Reading Framework: dictation "vital" `[GUID]`; EEF purpose-and-audience `[GUID]` |
| **G** | **My name** | The child's own name, first: its sounds, its capital, finding its letters on the keyboard, writing it as a signature on anything he makes. | his signature on artefacts | L&S: teachers should respond to a child's own name as a phonics opportunity (the "George/`ge`" example) `[CURR]`; own-name advantage is one of the oldest findings in emergent literacy `[OBS]` |

**A → G is one 8–12 minute loop, in that order, never a menu of seven games.** The DfE screen-use guidance ("slow-paced, repetitive and predictable") and the four pillars both push toward one predictable shape rather than a shelf of modes.

### 4.2 The GPC progression

**Anchor: Letters and Sounds (2007), Crown copyright, OGL v3.** It is the only complete, openly-licensed English SSP progression with published word banks. It is *not* on the DfE's validated list, and kidnix must not describe it as a validated programme. It is used here as a **default ordering and a licensed word corpus**, with a parent-set mapping to whatever the school actually uses (§4.5).

| Phase | Set | GPCs introduced | Example decodable words (all from the L&S OGL word banks) | Tricky words (read) |
|---|---|---|---|---|
| 2 | 1 | `s a t p` | sat, pat, tap, sap, at, as | — |
| 2 | 2 | `i n m d` | it, in, sit, pin, tin, man, mat, map, dad, did, and | — |
| 2 | 3 | `g o c k` | tag, gap, pig, dig, got, on, top, dog, can, cat, cot, kid, kit | — |
| 2 | 4 | `ck e u r` | kick, sock, pack, pocket, get, pen, ten, neck, up, mum, run, cup, rim, rat, rocket | **to, the** |
| 2 | 5 | `h b f ff l ll ss` | had, him, hot, hug, but, big, bed, bus, rabbit, if, off, puff, lap, leg, bell, fill, less, hiss, kiss, fusspot | **no, go, I** (+ *into*) |
| 3 | 6 | `j v w x` | jam, van, wig, box, fix, jet, wet | — |
| 3 | 7 | `y z zz qu` | yes, zip, buzz, quit, quiz | **he, she** |
| 3 | — | `ch sh th ng` | chip, chop, shop, fish, thin, that, ring, song | **we, me, be** |
| 3 | — | `ai ee igh oa oo(long) oo(short)` | rain, week, night, coat, moon, book | **was** |
| 3 | — | `ar or ur ow oi` | farm, fork, turn, cow, coin | **my, you** |
| 3 | — | `ear air ure er` | hear, hair, sure, letter | **her, they, all, are** |
| 4 | — | *no new GPCs* — adjacent consonants: CVCC, CCVC, CCVCC, CCCVC | went, help, just, lamp, milk, hand, best, from, stop, frog, trip, grab, spin, flag, champ, chest, shift, paint, roast, think, stand, crisp, crunch; polysyllables: children, sandpit, windmill, lunchbox, sandwich | **said, so, have, like, some, come, were, there, little, one, do, when, out, what** |
| 5 | — | `ay ou ie ea oy ir ue aw wh ph ew oe au` + split digraphs `a-e e-e i-e o-e u-e` + alternative pronunciations of known graphemes | day, out, tie, sea, boy, girl, blue, saw, when, phone, new, toe, Paul, make, these, time, home, rule | **oh, their, people, Mr, Mrs, looked, called, asked, could** |

Cross-check against the **statutory** Year 1 common exception word list, [National Curriculum English Appendix 1 (Spelling)](https://assets.publishing.service.gov.uk/government/uploads/system/uploads/attachment_data/file/239784/English_Appendix_1_-_Spelling.pdf) `[CURR]`, which kidnix should treat as the authoritative superset:

> the, a, do, to, today, of, said, says, are, were, was, is, his, has, I, you, your, they, be, he, me, she, we, no, go, so, by, my, here, there, where, love, come, some, one, once, ask, friend, school, put, push, pull, full, house, our

The Reading Framework's own worked demonstration of *what a Reception child can and cannot decode* (its Appendix 7) is the acceptance test for kidnix's text generator: a child who knows the alphabet's single letters plus `ck sh th ng ee oo or ar` and the exception words `to, the, we` can read *"Look up! A ship! Will it land?… A thing with three legs and six arms got off."* but **cannot** read *"A bird likes to eat worms"* or *"Josh and Alex got their boots."* If kidnix's generator produces the latter for that phase, it is broken.

### 4.3 Mastery and spacing, with no AI

A deliberately dumb, inspectable, deterministic model. It lives in one file in the child's home; a parent can read it in a text editor.

**Two separate concepts, never conflated:**

- **The ceiling** = the phase the parent set. kidnix **never** introduces a GPC above it. This is a hard gate, not an input to the model.
- **The schedule** = which of the *already-permitted* GPCs get rehearsed today.

**Per-GPC state:** a Leitner box (0–5) with fixed intervals `0, 1, 2, 4, 8, 16` days. Correct-first-attempt promotes; any error demotes to box 1 (never to 0 — a demotion to zero re-teaches, which is the school's job). "Mastered" = box 4 or above **and** 3 consecutive first-attempt correct **across at least 2 different days** — the two-day rule prevents same-session repetition from faking mastery, which is the standard failure of in-app mastery bars.

**Session composition** is fixed and boring: 60% due-for-review, 20% newest permitted GPC, 20% oldest mastered (interleaving). If nothing is due, the session is shorter — kidnix does not manufacture work.

**Word selection** is a filter, not a model: every word in the corpus is tagged with its GPC set, and only words whose every GPC is ≤ ceiling and whose target GPC is due are eligible. Sentences the same. This is a SQL `WHERE` clause, not adaptivity.

**Justification for keeping it this dumb:** the cleanest test of adaptivity in this literature — the [Norwegian GraphoGame RCT](https://doi.org/10.1016/j.learninstruc.2018.05.004), whose *only* difference between arms was adaptivity — found **no difference**; [Steenbergen-Hu & Cooper](https://doi.org/10.1037/a0032447) `[META]` found g = 0.01–0.09 for adaptive tutoring in K–12 maths; and [van Rijthoven et al. 2023](https://doi.org/10.7717/peerj.15499) `[RCT]` found game benefits concentrated in already-strong children, i.e. **adaptivity widened the gap**. Spacing, by contrast, is Tier 1. Spend the engineering on the schedule, not the model.

### 4.4 Showing progress honestly

**To the child: nothing numeric, ever.** No score, no stars, no percentage, no streak, no "level". What he sees at the end is *the thing he made* — the words he read today shown as a little pile, his spelling of "cafai", his recording. `05` §2f: informational, never controlling.

**To the parent, in the parent panel, three panes and no scores:**

1. **"What the school has taught"** — the phase/GPC list the parent set. Editable. This is presented as *the parent's statement*, not kidnix's assessment.
2. **"What we've seen him read here"** — a grid of graphemes with three states: *not tried* / *tried* / *read correctly on 3 different days*. Plus, verbatim: *"This is what happened on this computer. It is not an assessment, and it is not a substitute for what his teacher sees. Children read differently for a machine than for a person."*
3. **"What he made"** — recordings, spellings, captions, with dates. This is the pane parents will actually look at, and it is the one that recruits them into the loop (the McTigue moderator).

**Never:** percentiles, ages ("reading age 5y7m"), comparison to other children, predicted screening-check outcome, or a green/amber/red flag. kidnix has no normative data and must not imply it does. If a parent needs a red flag, the correct output is "talk to his teacher".

### 4.5 Co-existing with school

1. **First-run parent question, once:** *"Which phonics programme does his school use?"* — a picker over the 45 validated programmes plus "I don't know". Then: *"What's the most recent sound they've taught?"* with a grapheme grid, not phase jargon (parents know "he brought home 'ai' this week", not "Phase 3 week 4").
2. **A mapping table**, shipped as data, from L&S sets/phases to Little Wandle / RWI / Sounds-Write / ELS / Unlocking L&S phase names, used **only to translate the parent's answer into a ceiling**. Where a scheme's order genuinely differs (Sounds-Write and RWI both diverge substantially from L&S), the mapping is conservative: take the **intersection**, i.e. only permit GPCs taught by *both* orderings up to that point. Under-permitting is harmless; over-permitting undermines the school.
3. **"I don't know" defaults to L&S Phase 2 Set 1** and a nudge to ask the teacher. Starting too low costs nothing; a 5-year-old re-reading `sat, pat, tap` is not harmed.
4. **A monthly re-ask**, not a silent auto-advance. kidnix must never infer that the school has moved on because the child got good at something.
5. **No contradiction of terminology.** Scheme-specific jargon ("Fred talk") is trademarked and off-limits; so is teaching a competing term. Use plain words: *"say the sounds, then push them together."*
6. **Homework mode, deliberately not built.** Do not import the school's weekly word list; do not claim to be the school's app. The moment kidnix looks like homework, `05` §2f's motivation findings turn against it.

### 4.6 What NOT to do

1. **Do not invent a progression** and do not show an untaught GPC in a decodable context. (Unchanged from `05` #1, now with the Appendix-7 acceptance test to enforce it.)
2. **Do not build hotspots, tap-to-animate, embedded mini-games or tap-a-word dictionaries into the reading module.** The clearest negative finding available `[META]`.
3. **Do not build a reward economy.** No stars, streaks, badges, leaderboards, coins, pets, or unlockable characters. Deci et al. `[META]`; Schiefele et al. `[SR]`. The GraphoGame Rime trial is the cautionary case: teachers rated it "highly engaging, motivational and enjoyable" and it produced **−1 month**.
4. **Do not use letter names inside blending or segmenting** — but *do* teach them, later, in a labelled mode (§2.4). "No letter names" as a blanket rule is not evidence-based.
5. **Do not drill pseudo-words** to prepare for the screening check. The Reading Framework says so explicitly. A small number of "silly names" (L&S's own term — *ip, ug, ock*) inside blending practice is fine; a pseudo-word test is not.
6. **Do not use ASR to judge oral reading.** No child-facing speech grading, full stop. Record-and-keep is the safe design.
7. **Do not auto-correct, spell-check, or silently fix.** No red squiggles in any child-facing text field.
8. **Do not claim to teach reading, or to raise screening-check scores.** No product in this space has that evidence, and two of the best-funded attempts produced −1 month and +0.08.
9. **Do not teach handwriting, letter formation, cursive or lead-in strokes** — and say so to parents in the same screen where the keyboard activity is introduced.
10. **Do not make multisensory or "sky-writing" claims.** The multisensory-instruction literature is dominated by programme-branded, non-independent studies; no meta-analysis isolating a multisensory *component* at 5–6 was located `[absent]`. Actions and mnemonics can be shipped as *pleasant*, never as *proven*.
11. **Do not use US content unmodified.** US GPC orders, /æ/ in "bath", "mom", `-ize` spellings and rhotic vowels all break a UK phonics progression. This disqualifies most free American decodables from the "books I can read" shelf (see §5).
12. **Do not gate on time or streaks.** Bounded sessions plus spaced review are the design; a streak punishes the family for a weekend away.

---

## 5. Licensing: what we can actually ship

| Asset | Source | Licence | Verified | Notes / risk |
|---|---|---|---|---|
| **GPC progression, phase criteria, word banks, caption & sentence banks, 100 HFW list** | [Letters and Sounds (DFES-00281-2007)](https://assets.publishing.service.gov.uk/media/5a7aa7b6e5274a34770e630c/Letters_and_Sounds_-_DFES-00281-2007.pdf) | **Crown copyright, OGL v3.0** | ✅ gov.uk page states OGL v3 | The single most valuable open asset for this project. **Residual risk:** its word/HFW tables are credited to the *Children's Printed Word Database* (ESRC R00023406); the tables as published are inside an OGL document, but a cautious build should treat the *derived frequency ranking* as third-party and cite it. Must carry OGL attribution. Must **not** be described as a "validated programme". |
| **Year 1 statutory common exception words; Y1 spelling/reading/handwriting requirements** | [NC English Appendix 1](https://assets.publishing.service.gov.uk/government/uploads/system/uploads/attachment_data/file/239784/English_Appendix_1_-_Spelling.pdf) | **OGL v3.0** | ✅ | Authoritative superset for tricky words. |
| **Reading Framework 2023 / Writing Framework 2025 / EYFS** | gov.uk | **OGL v3.0** | ✅ | Quotable in parent-facing copy. Good for the "why we don't teach handwriting" page. |
| **Phonics screening check past papers / sample materials** | STA, gov.uk | OGL v3 *with exceptions* | ⚠️ not verified | Irrelevant anyway — we must not drill them. |
| **Font: Andika 7.000** | [SIL](https://software.sil.org/andika/) | **SIL OFL 1.1** | ✅ | Purpose-built for literacy learners. **Rendered and inspected:** single-storey `a` and `g`, plain `l`, **serifed capital `I`** — the three things that matter at 5. ⚠️ **Use the SIL release, not the Google Fonts subset** — the GF build exposes only `ccmp/liga/locl`, i.e. the alternate-glyph features are stripped. |
| **Fonts: ABeeZee, Didact Gothic** | Google Fonts | **SIL OFL 1.1** | ✅ rendered | Both single-storey `a`/`g` with serifed `I`. Good fallbacks. |
| **Fonts to avoid** | Nunito, Quicksand, Baloo 2, Sniglet | OFL | ✅ rendered | Single-storey `a`/`g` but **`l` and `I` are identical bare stems** — actively confusing for a beginning reader. |
| **Recorded phoneme audio, a–z, en_GB** | GCompris `voices-en_GB` `.rcc` (`alphabet/U0061.ogg`…) | **CC-BY-SA-4.0** (per `docs/LICENSES.md` §, KDE) | ✅ already in the image | Covers every single-letter grapheme. **Gap: no digraph/trigraph recordings** — `ai ee igh oa oo ar or ur ow oi ear air ure` must be recorded (or licensed) separately. That is ~20 clips: a morning's work with one adult and a decent mic, and the recordings become kidnix's own CC-BY-SA asset. |
| **Narration (sentences, books, instructions)** | Piper `en_GB-cori-high` / `-medium` | **public domain** (MODEL_CARD) | ✅ already pinned in `LICENSES.md` | Good for sentences. **Bad for isolated phonemes** — TTS reliably adds a schwa ("suh" not "sss"), which is the classic phonics error. Never synthesise a phoneme. |
| **Additional recorded words, en-GB speakers** | [Lingua Libre](https://lingualibre.org) (Wikimedia) | **CC BY-SA 4.0** | ✅ | Crowd-recorded; quality varies; accent must be filtered to en-GB. |
| **Picture prompts / symbols** | [Mulberry Symbols](https://mulberrysymbols.org/) | **CC BY-SA 4.0** | ✅ | UK-made AAC symbol set, ~3,400 symbols. Ideal for module A/D picture choices. |
| **Clip art** | Openclipart | **CC0** | ✅ (well-established) | No attribution burden. |
| **Picture books for the "books to me" shelf** | [Book Dash](https://bookdash.org/books/) | **CC BY 4.0** | ✅ | ~200 illustrated books, fully open, adaptable. Not decodable — right shelf, wrong module. |
| | [Global Digital Library](https://digitallibrary.io/) | CC BY / CC BY-NC per book | ✅ (site-level statement) | Levelled readers; per-book licence check required. |
| | StoryWeaver / African Storybook / Pratham | mostly CC BY 4.0 | ⚠️ per-book | Same caveat. |
| | Project Gutenberg | public domain (US rules) | ✅ | Nursery rhymes, traditional tales. |
| **Decodable readers (open)** | [CKLA Skills readers](https://www.coreknowledge.org/curriculum/download-curriculum/), Core Knowledge Foundation | **CC BY-NC-SA 4.0** ("use, adapt, and share (with attribution), but no one is permitted to sell either the original program, an adaptation of it, or lesson plans that reproduce any part of it") | ✅ site statement | The only substantial open decodable corpus found. **Two blockers: (a) US GPC order, US spellings and rhotic pronunciation — heavy adaptation; (b) the NC clause**, which is fine for a free OS image but forecloses any future paid product. Treat as a fallback, not a plan. |
| **UK open decodable texts** | searched: UKLO, Oak National Academy, Twinkl, Phonics Bug, Bloom Library, GDL | — | — | **`[absent]`.** No CC-licensed, UK-progression decodable book set was found. **Conclusion: kidnix must author its own**, which the L&S OGL word/caption/sentence banks make entirely tractable — the banks already contain the vocabulary, and the Reading Framework's Appendix 7 supplies four worked exemplar texts (themselves OGL). ~40 short texts across Phases 2–5 is a realistic authoring job. |
| **Word-frequency data** | SUBTLEX-UK, Children's Printed Word Database, BEEP, britfone | ⚠️ **unverified / research-only in places** | ❌ | Do not ship any of these until each licence is read. We do not need them: L&S's own lists are OGL and are matched to the progression, which is what actually matters. |

---

## 6. Keyboard and letter-forms at 5–6

**The policy position improved in our favour.** The DfE Writing Framework (2025) states that formal typing belongs in upper KS2 and that "before this, **familiarisation with keyboards in computing appears to be sufficient**". The NCCE Y1 unit is *Exploring the keyboard → Adding and removing text → … → Pencil or keyboard*. `05` §2b's conclusion stands and is now backed by named guidance rather than an absence.

**The literacy framing is the strong one.** "Press the key that makes /s/" is not typing practice; it is *find-the-grapheme-from-a-sound*, which is a stated Letters and Sounds Phase 2 success criterion. Reframed that way:

- The keyboard is a **display of 26 graphemes that never moves** — a fixed spatial index, which is exactly the kind of stable layout a 5-year-old can build a map of.
- **Digraphs are the interesting design problem.** `ai` is one sound and two keys. The interaction must show the two letters travelling into a single tile with a single sound button under it. Getting this right is the difference between the keyboard reinforcing the alphabetic principle and confusing it.
- **Lock output to lowercase in phonics modules.** Never require Shift. Never show a capital except in the name module and at the start of sentences in reading.
- **No home row, no finger assignment, no posture correction, no WPM, no timer.** d = 0.27 for formal training at population scale ([Dhakal et al. 2018](https://acris.aalto.fi/ws/portalfiles/portal/21495207/ELEC_Dhakal_et_al_Observations_CHI2018.pdf) `[OBS, 168k participants]`), no RCT of any tutor below age 8 `[absent]`.

**Lowercase keycaps: still no evidence, in either direction** `[absent]`. Re-searched; nothing since `05`. Google's Chromebook rationale remains pure UX reasoning `[RATIONALE]`. The practical move: **ship a printable lowercase keycap sticker sheet** (a physical, unplugged artefact — cheap, reversible, and consistent with the DfE's "screens should not replace" clause), and record what happens with our one child. This is one of the few places kidnix could contribute a genuinely novel observation.

---

## 7. Scope

### 7.1 v1 — one developer, 4–6 weeks

Ship **A, B, C, E** plus the ceiling, the schedule and the parent pane. Nothing else.

| Week | Deliverable |
|---|---|
| 1 | **Corpus + gate.** Transcribe the L&S OGL sets, word banks, caption banks and tricky words into TOML. Tag every word/sentence with its GPC set. Implement the ceiling filter and the Appendix-7 acceptance test as a unit test (the Reading Framework's own four exemplar books become four fixtures: Books 1–2 must be *rejected* at the stated phase, Books 3–4 *accepted*). Parent setting: scheme + last grapheme → ceiling, with the conservative-intersection mapping for RWI/Sounds-Write. |
| 2 | **Module B, "Find it"** — screen and keyboard, lowercase, audio from the GCompris a–z bundle. Record the ~20 missing digraph clips. |
| 3 | **Module C, "Blend it"** — sound buttons with the dot/bar convention, the push-together slider, word selection from the corpus. |
| 4 | **Module E, "Read it"** — author ~12 decodable texts across Phases 2–3 from the OGL banks; narration via Piper; optional word highlighting; **no** interactive elements. Journal artefact. |
| 5 | **Schedule + parent pane.** Leitner boxes, the two-day mastery rule, session composition. The three-pane parent view with the honesty paragraph. |
| 6 | **Module A** (if time), accessibility pass, TTS integration, image tests, and the "what this is not" parent page (no handwriting, no assessment, no claim to teach reading). |

**Deliberately deferred:** D (spell it), C+ (set for variability), F (write it), G (my name), the second shelf of the library, dialogic prompts, letters-to-family integration, printable unplugged pack, any second scheme's native ordering. F and G in particular belong with story-maker and letters-to-family and should be built once, there, not twice.

**v1 acceptance test, in one line:** *a Reception child whose parent has said "they've done up to `ck`" can find a grapheme, blend six words and read one four-sentence book, and never sees a grapheme past `ck`.*

### 7.2 What we'd learn from one child

n=1 gives usability and harm-absence, not efficacy. Say so in the write-up. The only design with any causal purchase is a **within-child multiple baseline across GPC sets**: pick three sets the school has taught but kidnix has not yet scheduled; probe all three weekly (parent-administered, 60 seconds, "say the sound for each of these"); introduce them into kidnix's schedule staggered a fortnight apart. If the probe curve bends when — and only when — kidnix starts scheduling a set, that is real, if fragile, evidence. If it doesn't, that is also real.

Alongside:
- **Instrumentation, not scoring:** first-attempt accuracy and latency per GPC, session length, abandonment point, which module he opens given the choice. Never shown to him.
- **Falsifiers stated in advance.** (a) He cannot find a key from a sound without help by session 5. (b) The sound buttons produce sound-by-sound reading that never merges. (c) He taps through Module E to the end without reading. (d) He stops returning within two weeks — `05` §5 #9, and the sharpest one.
- **Behavioural observations that matter more than any log:** does he read a sentence aloud to someone unprompted? Does he ask a grown-up what a word says? Does he go and find a paper book afterwards? Those are the outcomes we want, and no telemetry can capture them.
- **The lowercase-keycap n=1.** Stickers on, stickers off, a fortnight each; record time-to-find for a fixed 10-grapheme set.

---

## 8. Open questions

1. **Can we get the adult-interaction moderator without the adult?** McTigue et al.'s g = −0.02 → 0.48 split is the central threat to this whole product. Prompts that *recruit* a parent (Zhang et al. `[RCT]`) are the only lead we have, and nobody has tested them for phonics rather than shared reading.
2. **Do sound buttons help or entrench sound-by-sound reading?** Universal in UK classrooms, apparently never isolated experimentally `[absent]`.
3. **Does synchronised word highlighting help on its own?** Still unresolved (`05` §5 #2), still A/B-able inside kidnix.
4. **Is set-for-variability teachable to a 5-year-old by software?** Savage et al. 2018 was experimenter-delivered, small-group, at Grade 1. The mechanism is a *flexible* response to a mismatch — plausibly the hardest thing on this list to do without a human.
5. **Does a phoneme frame with tiles produce the same benefit as invented spelling with a pencil?** Ouellette et al. used pencils. The transcription mode may be the active ingredient (cf. Seyll & Content on visual analysis).
6. **What does the conservative-intersection mapping cost?** If a Read Write Inc. child is under-permitted by six weeks' worth of GPCs, does the product become boring? Untested.
7. **Is there any UK-progression open decodable corpus we missed?** The `[absent]` in §5 is a strong claim and worth one more sweep before committing to authoring 40 texts.
8. **Digraph audio.** Can one non-professional adult produce ~20 clean, schwa-free digraph recordings that a 5-year-old finds acceptable? If not, this is a small commissioning cost, not a research question.

---

## 9. Sources

### Statutory, policy and evidence-panel guidance

1. DfE — [Letters and Sounds (2007), DFES-00281-2007](https://www.gov.uk/government/publications/letters-and-sounds) · [PDF](https://assets.publishing.service.gov.uk/media/5a7aa7b6e5274a34770e630c/Letters_and_Sounds_-_DFES-00281-2007.pdf) — **Crown copyright, OGL v3** `[CURR]`
2. DfE — [The Reading Framework](https://www.gov.uk/government/publications/the-reading-framework-teaching-the-foundations-of-literacy) (upd. 22 Sep 2023) · [PDF](https://assets.publishing.service.gov.uk/media/664f600c05e5fe28788fc437/The_reading_framework_.pdf) `[GUID]`
3. DfE — [The Writing Framework](https://www.gov.uk/government/publications/the-writing-framework) (8 Jul 2025) · [PDF](https://assets.publishing.service.gov.uk/media/68bec95444fd43581bda1c86/The_writing_framework_092025.pdf) `[GUID]`
4. DfE — [List of validated phonics teaching programmes](https://www.gov.uk/government/publications/choosing-a-phonics-teaching-programme/list-of-phonics-teaching-programmes) (upd. 16 Feb 2026, 45 programmes) `[CURR]`
5. DfE — [National Curriculum English Appendix 1: Spelling](https://assets.publishing.service.gov.uk/government/uploads/system/uploads/attachment_data/file/239784/English_Appendix_1_-_Spelling.pdf) `[CURR]`
6. DfE — [EYFS statutory framework](https://www.gov.uk/government/publications/early-years-foundation-stage-framework--2) `[CURR]`; [Children's screen use guidance](https://help-for-early-years-providers.education.gov.uk/safeguarding-and-welfare/screen-use) `[GUID]`
7. Francis et al. — [Curriculum and Assessment Review final report](https://assets.publishing.service.gov.uk/media/690b96bbc22e4ed8b051854d/Curriculum_and_Assessment_Review_final_report_-_Building_a_world-class_curriculum_for_all.pdf), DfE, Nov 2025 `[CURR]`
8. Ofsted — [Telling the story: the English education subject report](https://www.gov.uk/government/publications/subject-report-series-english/telling-the-story-the-english-education-subject-report) (5 Mar 2024) `[GUID]`
9. Ofsted — [Strong foundations in the first years of school](https://www.gov.uk/government/publications/strong-foundations-in-the-first-years-of-school) (8 Oct 2024) `[GUID]`
10. Ofsted — [Curriculum research review series: English](https://www.gov.uk/government/publications/curriculum-research-review-series-english) (2022) `[GUID]`
11. EEF — [Teaching and Learning Toolkit: Phonics](https://educationendowmentfoundation.org.uk/education-evidence/teaching-learning-toolkit/phonics) — +5 months, 228 studies `[META]`
12. EEF — [Improving Literacy in Key Stage 1](https://educationendowmentfoundation.org.uk/education-evidence/guidance-reports/literacy-ks-1) (2nd edn, 2020) `[GUID]`; [Preparing for Literacy](https://educationendowmentfoundation.org.uk/education-evidence/guidance-reports/preparing-for-literacy) (2018) `[GUID]`
13. WWC — [Foundational Skills to Support Reading for Understanding in K–3](https://ies.ed.gov/ncee/wwc/PracticeGuide/21) `[GUID]`; [Teaching Elementary School Students to Be Effective Writers](https://ies.ed.gov/ncee/wwc/PracticeGuide/17) `[GUID]`
14. NCCE — [Teach Computing Curriculum, KS1](https://teachcomputing.org/curriculum/key-stage-1) `[CURR]`

### Trials, meta-analyses and reviews

15. McTigue, Solheim, Zimmer & Uppstad (2019) — [Critically Reviewing GraphoGame Across the World](https://doi.org/10.1002/rrq.256), *RRQ* — **g = −0.02; g = 0.48 with high adult interaction** `[SR+META]`
16. EEF/NFER (2018) — [GraphoGame Rime efficacy trial](https://educationendowmentfoundation.org.uk/projects-and-evaluation/projects/graphogame-rime) — **−1 month, 398 pupils, very high security** `[RCT]`
17. O'Callaghan, McIvor, McVeigh & Rushe (2016) — [RCT of Lexia Reading Core5 with 4–6 year olds](https://doi.org/10.1111/bjep.12122), *BJEP* `[RCT, n=98]`
18. Cockerill et al. (2024) — [Computer-assisted learning for struggling readers in England](https://doi.org/10.1016/j.appdev.2024.101726), *JADP* — **+0.08 / +0.18 low-SES, 620 pupils** `[RCT]`
19. Pasqualotto, Cunningham, Holman, Bediou & Bavelier (2025) — [Digital Tools for Reading Success: Meta-analyses of Digital Interventions](https://doi.org/10.1007/s41465-025-00336-2) — **g = 0.433 poor readers, 0.256 general** `[META]`
20. Savage, Georgiou, Parrila & Maiorino (2018) — [Preventative Reading Interventions Teaching Direct Mapping and Set-for-Variability](https://doi.org/10.1080/10888438.2018.1427753) `[RCT, n=201]`
21. Steacy et al. (2022) — [Set for Variability as a Critical Predictor of Word Reading](https://doi.org/10.1002/rrq.475) `[OBS, N=489]`; [Steacy et al. 2019](https://doi.org/10.1080/10888438.2019.1620749); [Tunmer & Chapman 2012](https://doi.org/10.1080/10888438.2010.542527)
22. Ouellette & Sénéchal (2017) — [Invented Spelling in Kindergarten as a Predictor](https://doi.org/10.1037/dev0000179), *Dev. Psych.* `[OBS, N=171]`
23. Ouellette, Sénéchal & Haley (2013) — [Guiding Children's Invented Spellings: A Gateway Into Literacy Learning](https://doi.org/10.1080/00220973.2012.699903) `[RCT, n=40]`
24. Piasta, Purpura & Wagner (2010) — [Fostering Alphabet Knowledge Development](https://doi.org/10.1007/s11145-009-9174-x), *Reading & Writing* `[RCT, n=58]` ([full text](https://pmc.ncbi.nlm.nih.gov/articles/PMC2885812/))
25. Roberts, Vadasy & Sanders (2018) — [Preschoolers' alphabet learning: letter name and sound instruction](https://doi.org/10.1016/j.ecresq.2018.04.011) `[RCT]`
26. Vadasy & Sanders (2020) — [Introducing GPCs: rate and complexity in phonics instruction](https://doi.org/10.1007/s11145-020-10064-y) `[RCT]`
27. West, Snowling, Lervåg et al. (2021) — [NELI at scale](https://doi.org/10.1111/jcpp.13415), *JCPP* `[RCT, 193 schools]`; [2025 follow-up](https://doi.org/10.1111/jcpp.14157)
28. Murphy Odo (2024) — [The use of decodable texts: a meta-analysis](https://onlinelibrary.wiley.com/doi/10.1111/lit.12368), *Literacy* `[META]`
29. Takacs, Swart & Bus (2015) — [Benefits and Pitfalls of Multimedia and Interactive Features in Technology-Enhanced Storybooks](https://doi.org/10.3102/0034654314566989), *RER* `[META]`
30. Kim, Gilbert, Yu & Gale (2021) — [Measures Matter](https://doi.org/10.1177/23328584211004183), *AERA Open* `[META]`
31. Piquette, Savage & Abrami (2014) — [ABRACADABRA replication](https://doi.org/10.3389/fpsyg.2014.01413) `[RCT]`; [Savage et al. 2013](https://doi.org/10.1037/a0031025) `[RCT, 1,067]`
32. Solheim et al. (2018) — [Adaptive vs non-adaptive GraphoGame](https://doi.org/10.1016/j.learninstruc.2018.05.004) `[RCT]`; van Rijthoven et al. (2023) — [Digital game-based literacy training](https://doi.org/10.7717/peerj.15499) `[RCT]`
33. Messer & Nash (2017) — [Evaluation of a computer-assisted reading intervention using visual mnemonics](https://doi.org/10.1111/1467-9817.12107) `[RCT, n=78, age 7]`
34. Castles, Rastle & Nation (2018) — [Ending the Reading Wars](https://journals.sagepub.com/doi/10.1177/1529100618772271), *PSPI* `[SR]`
35. Wyse & Bradbury (2022) — [Reading wars or reading reconciliation?](https://doi.org/10.1002/rev3.3314) `[SR]`; replies: [Teaching phonics and reading effectively: 'a balancing act'](https://doi.org/10.1002/rev3.3429) (2023); [Bowers — There is still little or no evidence…](https://doi.org/10.1002/rev3.3432) (2023); [Bowers 2020](https://doi.org/10.1007/s10648-019-09515-y)
36. Mol, Bus & de Jong (2008) — [Added Value of Dialogic Parent–Child Book Readings](https://doi.org/10.1080/10409280701838603) `[META]`; Noble et al. (2019) — [Shared book reading and language](https://doi.org/10.1016/j.edurev.2019.100290) `[META]`
37. Ehri (2014) — [Orthographic Mapping in the Acquisition of Sight Word Reading](https://doi.org/10.1080/10888438.2013.819356) `[SR]`
38. Dhakal, Feit, Kristensson & Oulasvirta (2018) — [Observations on Typing from 136 Million Keystrokes](https://acris.aalto.fi/ws/portalfiles/portal/21495207/ELEC_Dhakal_et_al_Observations_CHI2018.pdf), CHI `[OBS]`
39. Steenbergen-Hu & Cooper (2013) — [ITS effectiveness in K–12](https://doi.org/10.1037/a0032447) `[META]`; Deci, Koestner & Ryan (2001) — [Extrinsic rewards and intrinsic motivation](https://doi.org/10.3102/00346543071001001) `[META]`; Cepeda et al. (2006) — [Distributed practice](https://doi.org/10.1037/0033-2909.132.3.354) `[META]`

### Content and licences

40. SIL — [Andika](https://software.sil.org/andika/) (OFL 1.1); [SIL Open Font License](https://openfontlicense.org/)
41. [Mulberry Symbols](https://mulberrysymbols.org/) (CC BY-SA 4.0); [Openclipart](https://openclipart.org/) (CC0); [Lingua Libre](https://lingualibre.org) (CC BY-SA 4.0)
42. [Book Dash](https://bookdash.org/books/) (CC BY 4.0); [Global Digital Library](https://digitallibrary.io/); [StoryWeaver](https://storyweaver.org.in/); [African Storybook](https://africanstorybook.org/)
43. [Core Knowledge Language Arts — Download Free Curriculum](https://www.coreknowledge.org/curriculum/download-curriculum/) (CC BY-NC-SA 4.0)
44. kidnix — `docs/LICENSES.md` (GCompris `.rcc` voice bundles CC-BY-SA-4.0; Piper `en_GB-cori-high/medium` public domain)

### Absences worth recording

`[absent]` — no independent early-reading RCT for Teach Your Monster to Read, Reading Eggs, Nessy, Phonics Hero, Headsprout, Bookbot, Starfall or Khan Academy Kids · no CC-licensed UK-progression decodable book corpus · no study of lowercase vs uppercase keycaps for early readers · no isolated experimental test of sound buttons · no isolated test of synchronised word highlighting · no meta-analysis isolating a multisensory *component* at 5–6 · no RCT of any typing tutor below age 8 · no trial of any solo, unsupervised, at-home early-literacy tool.

---

*Compiled for the kidnix project, 23 August 2026. Primary sources were retrieved and read in full where reachable; effect sizes are quoted with their design and sample size so the reader can discount appropriately. Amendments to `05-learning-science.md`: §2.4 above revises `05` §3's implicit "no letter names" rule, and §1.3 supplies the DfE's own 2025 endorsement of keyboard familiarisation (as distinct from typing instruction) at primary.*
