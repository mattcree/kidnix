# 05 — Learning science for 4–8 year olds, as it applies to software

*Research note for the kidnix project. Compiled 22 August 2026.*

---

## 1. Scope & method

**Question.** What is actually evidence-backed about how 4–8 year olds (UK Reception / Year 1 / Year 2, centred on 5–6) learn, and what does that imply for the design of the activities kidnix will ship?

**Sources.** ~55 distinct sources: meta-analyses and systematic reviews first; then randomised controlled trials; then government/statutory curriculum documents (DfE, EEF, IES/What Works Clearinghouse); then smaller quasi-experimental and qualitative studies; then, clearly marked, design rationale and vendor claims where no independent evidence exists. Retrieved via OpenAlex, gov.uk, EEF, IES/WWC, publisher sites and project pages, and read in full where the full text was reachable.

**Evidence tags** used inline throughout:

| Tag | Meaning |
|---|---|
| `[META]` | Meta-analysis with pooled effect sizes |
| `[SR]` | Systematic review, narrative or vote-count |
| `[RCT]` | Randomised (often cluster-randomised) controlled trial |
| `[QE]` | Quasi-experimental / matched comparison |
| `[OBS]` | Observational, correlational, or descriptive |
| `[QUAL]` | Small qualitative or case study |
| `[GUID]` | Expert-panel guidance grounded in a formal evidence review (EEF, WWC, DfE) |
| `[CURR]` | Statutory or official curriculum document |
| `[VENDOR]` | Claim made by the product's own maker, not independently verified |
| `[RATIONALE]` | Design reasoning with no direct empirical test |

**Three standing caveats.**

1. **Media-comparison studies are weak evidence.** "App versus no app" answers almost nothing, because the app is confounded with extra instructional time, novelty, and teacher attention. Richard Clark's [1983 argument](https://doi.org/10.3102/00346543053004445) — that media are "mere vehicles that deliver instruction but do not influence student achievement" — still constrains how much any "digital technology works!" headline is worth `[SR]`. The useful questions are *which design features*, *for which children*, *replacing what*.
2. **Effect sizes in early-years edtech are inflated by small samples and publication bias.** Treat anything above g ≈ 0.8 from a handful of small studies as provisional.
3. **kidnix is not a school intervention.** Almost all the good evidence comes from classroom trials with a teacher present. kidnix runs at home, largely without an adult sitting alongside. That gap is the single biggest threat to transferring these findings, and it recurs throughout this note.

**Assumptions made** (flagged because they shape the recommendations): kidnix targets UK families; children have a school doing the systematic phonics teaching; kidnix's job is *practice, application, creation and pleasure*, not first teaching; sessions are bounded (20–40 min); there is no internet, no store, no feed; a parent is reachable but usually not co-seated.

---

## 2. Findings by domain

### 2a. Literacy: phonics, decodable text, read-aloud, writing

#### The UK baseline is not negotiable, and kidnix should match it exactly

England's statutory position is unusually specific, and any UK product that contradicts it will be rejected by parents and teachers.

- **EYFS (Reception).** The current [statutory framework, applying from 1 September 2026](https://www.gov.uk/government/publications/early-years-foundation-stage-framework--2) `[CURR]` sets the ELG for Word Reading as: "Say a sound for each letter in the alphabet and at least 10 digraphs; Read words consistent with their phonic knowledge by sound-blending; Read aloud simple sentences and books that are consistent with their phonic knowledge, including some common exception words." The Writing ELG: "Write recognisable letters, most of which are correctly formed; Spell words by identifying sounds in them and representing the sounds with a letter or letters; Write simple phrases and sentences that can be read by others."
- **KS1 English.** The [national curriculum programmes of study](https://www.gov.uk/government/publications/national-curriculum-in-england-english-programmes-of-study/national-curriculum-in-england-english-programmes-of-study) `[CURR]` require Year 1 pupils to "apply phonic knowledge and skills as the route to decode words" and to compose by "saying out loud what they are going to write about; composing a sentence orally before writing it."
- **The Reading Framework.** [DfE, first published July 2021, updated September 2023](https://www.gov.uk/government/publications/the-reading-framework-teaching-the-foundations-of-literacy) `[GUID]` pushes "fidelity" to a single validated systematic synthetic phonics (SSP) programme, decodable books matched to the phonics taught so far, and daily story time. It contains essentially nothing about digital tools.

The design consequence is blunt: **kidnix must not invent its own phonics progression, and must not present a child with a word containing a grapheme–phoneme correspondence (GPC) they may not have been taught.** A phonics activity that shows "night" to a Reception child in week 4 is actively harmful to the school's programme.

#### Does systematic phonics work? Yes, but the consensus has been poked

The mainstream position — reflected in the [WWC practice guide *Foundational Skills to Support Reading for Understanding in K–3*](https://ies.ed.gov/ncee/wwc/PracticeGuide/21) `[GUID]` — rates two of its four recommendations as **Strong Evidence**: "Develop awareness of the segments of sounds in speech and how they link to letters" (17 studies) and "Teach students to decode words, analyze word parts, and write and recognize words" (18 studies). Recommendation 4, "Ensure that each student reads connected text every day," is rated **Moderate Evidence** (22 studies). Recommendation 1 (academic language / vocabulary) is only **Minimal Evidence**, which is a useful corrective to the assumption that vocabulary apps are obviously good.

Against that, Bowers's [*Reconsidering the Evidence That Systematic Phonics Is More Effective Than Alternative Methods*](https://doi.org/10.1007/s10648-019-09515-y) `[SR]` reviewed 12 meta-analyses and argued the superiority of systematic phonics over alternatives is not established; and Wyse & Bradbury's [*Reading wars or reading reconciliation?*](https://doi.org/10.1002/rev3.3314) `[SR]` synthesised 55 experimental trials and criticised England's single-method policy. Neither argues for whole language. Both argue for **phonics plus meaning, from the start**.

**Design implication for kidnix:** teach/practise GPCs *and* always land in a real sentence or story within the same activity. Never build a pure isolated-grapheme drill loop as the whole activity.

#### Decodable text: real but modest

Murphy Odo's [2024 meta-analysis in *Literacy*](https://onlinelibrary.wiley.com/doi/10.1111/lit.12368) `[META]` pooled 16 experimental studies (from 821 screened): decodable texts gave **g = 0.20** for word reading (95% CI 0.07–0.31) and **g = 0.30** for pseudoword decoding (95% CI 0.15–0.45), with moderate-to-serious risk of bias in most studies. Conclusion: decodables help, are not sufficient alone, and should sit alongside other text.

The WWC guide's own step is narrower and more usable: "Have students read decodable words *in isolation and in text*," and separately, "Introduce non-decodable words that are essential to the meaning of the text as whole words" — while "limiting the number of these words introduced at a time, because learning them holistically places considerable demands on students' memory" `[GUID]`.

**Design implication:** kidnix's offline library needs a *decodable tier* keyed to a phonics phase the parent selects, and a *read-to-me tier* with no decodability constraint at all. Mixing them into one undifferentiated shelf wastes both.

#### Read-aloud, narration and word highlighting: the best-evidenced digital literacy feature

Takacs, Swart & Bus's [meta-analysis of technology-enhanced storybooks](https://doi.org/10.3102/0034654314566989) `[META]` (43 studies, 2,147 children) is the single most design-relevant finding in this whole note:

- Small but significant **additional** benefit of technology over ordinary adult storybook reading: **g+ = 0.17** for story comprehension, **g+ = 0.20** for expressive vocabulary.
- **Multimedia features that match the story — animated pictures, music, congruent sound effects — were beneficial.**
- **Interactive elements — hotspots, embedded games, dictionaries — were distracting**, especially for children at risk.

Bus, Takacs & Kegel's earlier review, [*Affordances and limitations of electronic storybooks*](https://doi.org/10.1016/j.dr.2014.12.004) `[SR]`, reaches the same split: multimedia that is *congruent* with the text helps integrate verbal and non-verbal information; extraneous interactivity taxes working memory. An eye-tracking study by the same group found [motion in animated illustrations reliably attracts 4–6 year olds' attention](https://doi.org/10.3389/fpsyg.2016.01591) `[QE]` and, when well matched to the text, guides them to comprehension-relevant parts of the picture.

There is a dissenting note: Fletcher-Watson and colleagues found [simple irrelevant interactive features were *not* worse than relevant ones](https://doi.org/10.3389/fpsyg.2018.02733) `[RCT]` when the interaction was only a page-turn tap that did not disrupt the narrative. And Russo-Johnson et al., [*All Tapped Out*](https://doi.org/10.3389/fpsyg.2017.00578) `[QE]`, found 2-year-olds with lower self-regulation tapped compulsively during instructional segments; 4–6 year olds tapped much less. The reconciliation: **interaction that interrupts meaning is bad; interaction that is trivial and non-disruptive is neutral; the risk falls with age and with self-regulation.**

On synchronised word highlighting specifically, the direct evidence is thinner than its ubiquity suggests — it is generally bundled inside "narration" conditions rather than isolated as a variable. Treat karaoke-style highlighting as `[RATIONALE]` supported by the broader multimedia-congruence finding, not as an independently proven feature. It is cheap, plausible, and consistent with the evidence; it is not proven.

**Design implication:** narration with congruent illustration is the highest-value literacy feature kidnix can build, and every tappable hotspot that is not the story is a cost.

#### Phonics games with actual trial evidence

- **GraphoGame** is the best-evidenced example of the genre. It has been tested in several languages: the [Norwegian group-randomised trial](https://doi.org/10.1016/j.learninstruc.2018.05.004) `[RCT]` (744 screened, 140 at-risk) found significant impact on reading and spelling — but **no significant difference between the adaptive and non-adaptive versions of the software**, which is a caution against over-investing in adaptivity. The [Portuguese trial](https://doi.org/10.17239/jowr-2020.12.01.02) `[RCT]` (n = 45) showed benefits for spelling and phonological awareness. A [Polish crossover trial](https://doi.org/10.17239/l1esll-2013.01.05) `[RCT]` found **no** advantage over a maths game. The UK GraphoGame Rime cohort (398 children, 6–7 years) is described in [Ríos-López et al.](https://doi.org/10.3389/feduc.2021.639294) `[RCT]`. Net read: real but inconsistent effects, strongest on the most proximal outcomes (letter–sound knowledge, phonological awareness), weakest on reading fluency.
- **ABRACADABRA (ABRA)**, a free web literacy system from Concordia, has two Canadian cluster RCTs. The [pan-Canadian trial](https://doi.org/10.1037/a0031025) `[RCT]` (1,067 children, 74 classes) found advantages in phonological blending and letter–sound knowledge; the [replication](https://doi.org/10.3389/fpsyg.2014.01413) `[RCT]` (203 children, 24 classes, 10–12 h of use) found **d = +0.66 letter–sound knowledge, +0.52 phonological blending, +0.52 word reading**. Note: both delivered ABRA as *whole-class teacher-led instruction*, not solo play.
- A [Dutch/Flemish cluster RCT of a literacy game](https://doi.org/10.7717/peerj.15499) `[RCT]` (247 Grade 1 children, ~28 sessions of 10–15 min) improved letter knowledge classroom-wide, with a small fluency benefit concentrated in children who already had strong phonological awareness — i.e. the game widened rather than narrowed the gap.
- **Teach Your Monster to Read** is the obvious UK reference point, developed with University of Roehampton academics `[VENDOR]`. Despite its reputation and 40m+ users, **I could find no published independent RCT of the game's effect on reading outcomes**. It is evidence-*informed* (its phonics progression is defensible) rather than evidence-*proven*. Do not cite it to a parent as proven.
- **Reading Eggs, Starfall, Khan Academy Kids, Bookbot**: no independent RCT of early-reading outcomes surfaced for any of them in this search. Khan Academy Kids and Starfall are free and pedagogically sane; that is not the same as effective.

**Design implication:** the honest claim kidnix can make is "this practises what your school is teaching, in a way children want to do." Not "this teaches your child to read."

#### Handwriting vs typing at 5–7

This is genuinely contested, and the strongest claims on both sides overreach.

Evidence that handwriting has a specific advantage:
- Kiefer et al., [*Handwriting or Typewriting?*](https://doi.org/10.5709/acp-0178-7) `[RCT]` — 16 training sessions with German kindergarteners on closely matched letter-learning games; the pen-based group outperformed the keyboard group on letter recognition and writing.
- Kersey & James, [brain activation from learning letter forms through active self-production vs passive observation](https://doi.org/10.3389/fpsyg.2013.00567) `[QE]` — in 7-year-olds, *active writing* recruited the sensorimotor network associated with letter perception; passive observation of an adult writing did not. The mechanism is self-produced motor variability, not the pen per se.
- Van der Weel & Van der Meer, [HD-EEG study of cursive vs typewriting](https://doi.org/10.3389/fpsyg.2020.01810) `[QE]` — theta-range synchronisation during handwriting in 12-year-olds and adults, interpreted as better conditions for memory encoding. Note: n = 24, EEG correlates, no learning outcome measured. This study is very widely over-cited.

Evidence on the other side:
- The EEF's own KS1 literacy guidance frames transcription as *including* keyboards: "Pupils must learn to form letters and spell words correctly, start to write in joined-up handwriting when appropriate, **and use a keyboard**" `[GUID]`.
- The WWC writing practice guide, [*Teaching Elementary School Students to Be Effective Writers*](https://ies.ed.gov/ncee/wwc/PracticeGuide/17) `[GUID]`, rates "build foundational skills — handwriting, spelling, sentence construction, **typing, and word processing**" as **Moderate Evidence**, and lists typing alongside handwriting rather than opposed to it.

The reconciliation that the evidence actually supports: **handwriting is the better route for *learning letter forms and letter identity* in the 4–6 window; the keyboard is the better route for *composition volume* once letters are known**, because transcription cost is what throttles young writers. Dockrell et al. showed [handwriting fluency directly constrains written composition](https://doi.org/10.1177/001440290907500403) `[OBS]`, and Sumner & Connelly's [study of 116 UK children aged 5:0–6:7](https://doi.org/10.1007/s11145-018-9859-0) `[OBS]` found transcription skill, not ideas, explained much of the variance in early composition quality.

**Design implication:** kidnix should *not* try to replace handwriting, should not claim to teach letter formation, and should treat the keyboard as a **composition aid** — a way for a 6-year-old to produce a longer, better story than their hand can currently manage. Both/and, framed explicitly for parents.

#### Dictation / speech-to-text for emergent writers

Direct trial evidence with 5–7 year olds is sparse; most speech-to-text writing research is with older or dysgraphic learners. But the theoretical case is strong and well grounded: Berninger's *simple view of writing* and McCutchen's [*From Novice to Expert*](https://doi.org/10.17239/jowr-2011.03.01.3) `[SR]` both hold that transcription consumes working memory that would otherwise go to ideas. Removing transcription cost should raise composition quality — and the KS1 national curriculum itself already institutionalises the practice, requiring Year 1 pupils to compose "a sentence orally before writing it" `[CURR]`, and the EEF describes the teacher scribing while the child dictates as a standard scaffold `[GUID]`.

Two hard constraints for kidnix, though. First, **general-purpose ASR is poor on 5-year-old speech** (high pitch, disfluency, regional accent), and an offline on-device model will be worse. Second, transcribing a child's speech into *correctly spelled* text removes the spelling practice the curriculum requires. Both are solvable by design (see §3), but not by simply bolting on dictation.

#### What makes writing motivating for 5–7 year olds

The EEF is unusually direct here: "Achieving the necessary quantity of practice requires pupils to be motivated and fully engaged in improving their writing" `[GUID]`, and it names purpose and audience as the mechanism: "Writing requires the consideration of purpose and audience... The coordination of these concepts is a complex, yet essential, skill that can be practised through purposeful speaking and listening activities for writing."

Guthrie/Schiefele's [review of reading motivation dimensions](https://doi.org/10.1002/rrq.030) `[SR]` finds intrinsic dimensions (curiosity, involvement) positively predict reading behaviour and competence, while extrinsic dimensions (competition, recognition, grades, compliance) contribute weakly or negatively. There is no reason to think writing differs.

**Design implication:** a real recipient beats a star rating. This is exactly why *letters to family* is the strongest activity concept in the kidnix list.

### 2b. Keyboarding: when and how to teach typing to 5–8s

**The single most important finding here is an absence.** There is no statutory UK requirement to teach typing at any key stage. The KS1 [computing programme of study](https://www.gov.uk/government/publications/national-curriculum-in-england-computing-programmes-of-study) `[CURR]` contains the words *typing*, *keyboard*, *keyboarding* and *touch typing* **zero times**; the closest statement is "use technology purposefully to create, organise, store, manipulate and retrieve digital content." The [Curriculum and Assessment Review final report (Francis et al., DfE, November 2025)](https://assets.publishing.service.gov.uk/media/690b96bbc22e4ed8b051854d/Curriculum_and_Assessment_Review_final_report_-_Building_a_world-class_curriculum_for_all.pdf) `[CURR]` — 196 pages, revised curriculum due 2027 for first teaching 2028 — also contains zero instances of "keyboard", "handwriting" or "touch typing". No UK policy body is currently proposing keyboarding at KS1.

What English schools actually do comes from the non-statutory NCCE [Teach Computing Curriculum](https://teachcomputing.org/curriculum/key-stage-1), whose Year 1 unit *Creating media – Digital writing* runs: **Exploring the keyboard → Adding and removing text → Exploring the toolbar → Making changes to text → Explaining my choices → Pencil or keyboard** `[CURR]`. That is **key-location familiarisation plus a modality comparison — explicitly not touch-typing instruction.**

The US anchors sit above this age band. Common Core's [ELA writing standards](https://corestandards.org/wp-content/uploads/2023/09/ELA_Standards1.pdf) `[CURR]` say nothing about keyboarding for K–2; keyboarding first appears at **W.3.6** ("using keyboarding skills", Grade 3, age 8–9) and a page-per-sitting fluency target only at W.4.6. The [ISTE Standards for Students](https://iste.org/standards/students) `[GUID]` mention keyboarding nowhere.

**Is there an age below which typing instruction is futile?** No — and the popular claim that under-7s "can't reach the home row" appears to be **an untested practitioner heuristic**. A search for children's hand-anthropometry-versus-key-pitch studies returned nothing. The one genuine RCT in the vicinity, [McGlashan et al. (2017)](https://pmc.ncbi.nlm.nih.gov/articles/PMC5716426/) `[RCT]`, chose ages 8–10, randomised only 28 children, and measured *manual dexterity* (MABC-2, significant improvement) rather than typing speed. The 7–8 threshold is convention, not evidence.

**Touch typing vs hunt-and-peck.** The best data is [Dhakal, Feit, Kristensson & Oulasvirta's CHI 2018 study of 136 million keystrokes](https://acris.aalto.fi/ws/portalfiles/portal/21495207/ELEC_Dhakal_et_al_Observations_CHI2018.pdf) `[OBS, n=168,000]`. Formally trained typists managed 54.4 WPM against 49.0 for the untrained — **d = 0.27, a small effect** — with near-identical error rates. Mean finger count was 6.95, and finger count correlated with speed only moderately (r = 0.38); fast typists averaged 8.4 fingers, slow typists 5.3. [Feit et al. (2016)](https://dl.acm.org/doi/10.1145/2858036.2858233) `[OBS]` found untrained typists reaching speeds "comparable to, or greater than, that of touch typists." **No study demonstrates that childhood hunt-and-peck impairs later touch-typing acquisition.** What predicts speed is a *consistent* finger-to-key mapping plus practice volume, not the canonical eight-finger system.

**Typing tutors have essentially no evidence for this age.** BBC **Dance Mat Typing** (aimed 7–11) has been **defunct since Flash was retired on 31 December 2020** and was never rebuilt — recommending it today recommends a dead product. TypingClub / TypingClub Jr, Typing.com, Tux Typing, Doorway Online and Nessy Fingers have no reachable published efficacy studies `[absent]`. [KAZ Type](https://kaz-type.com/product/children) claims it "teaches you how to touch type correctly in minutes instead of hours" and that touch typing is "PROVEN… FORMIDABLE and even LIFE CHANGING" for SEN learners, citing no study at all `[VENDOR]`. **There is no RCT of any typing tutor with children aged 5–7.**

**Keyboard hardware and lowercase keycaps: also unevidenced.** The tension is real — UK synthetic phonics teaches lowercase graphemes first while standard keycaps are engraved uppercase — but no study compares lowercase and uppercase keycaps on letter-finding speed or literacy outcomes. [Google's own explanation of the lowercase Chromebook keyboard](https://blog.google/products-and-platforms/devices/chromebooks/chromebooks-lowercase-keyboard/) is pure UX reasoning — "If you press a key, then that's what you'll get" — with no pedagogical evidence cited `[RATIONALE]`. Vendor claims that lowercase covers aid early readers cite nothing `[VENDOR]`. Treat large-key, colour-coded and lowercase keyboards as plausible usability choices, not proven interventions.

**Design implication:** kidnix's keyboard activity should target **key location, letter–sound linkage and text manipulation**, not home-row discipline. Show the lowercase letter on screen (matching phonics), accept any finger, reward finding the key that makes the sound. This is defensible as a terminal goal for 5–7 and costs nothing if the child later learns touch typing.

---


### 2c. Maths: number sense and early-number software

#### What the UK actually asks for at this age

The [EYFS Number ELG](https://www.gov.uk/government/publications/early-years-foundation-stage-framework--2) `[CURR]` is unusually concrete: "deep understanding of numbers to 10, including the composition of each number; **subitise (recognise quantities without counting) up to 5**; automatically recall (without reference to rhymes, counting or other aids) number bonds up to 5 (including subtraction facts) and some number bonds to 10, including double facts." The Numerical Patterns ELG adds verbal counting beyond 20, comparison to 10, and patterns within 10 (evens/odds, doubles, equal distribution). The 2021 reform *dropped* Shape/Space/Measure from the ELGs and *added* subitising — which almost no consumer app targets. [KS1 maths](https://www.gov.uk/government/publications/national-curriculum-in-england-mathematics-programmes-of-study) `[CURR]` then wants counting to 100, number bonds to 20, and ×2/5/10 in Year 2, inside a mastery frame (NCETM's five big ideas: coherence, representation and structure, variation, fluency, mathematical thinking) `[GUID]`.

#### The field-level picture is sobering

Outhwaite, Early, Herodotou & Van Herwegen's [*Can Maths Apps Add Value to Learning?*](https://repec-cepeo.ucl.ac.uk/cepeow/cepeowp23-02.pdf) `[SR]` is the best single overview: **50 studies, 77 apps, 23,981 children aged ~4–7 across 18 countries**, of which 20 were RCTs. 92% report *some* positive effect — but only 14 of 50 used a standardised maths outcome, within-subject effect sizes ranged d = 0.05 to 3.34, and **9 of the 11 studies with d ≥ 1 had n < 250**. Only **three** studies combined an RCT, n > 250 *and* a standardised measure. The correlation between usage and effect was r = .30, non-significant. Only 5 studies had delayed post-tests; **2 of those showed fade-out within 1–2 months.**

**Rule of thumb: treat any maths-app effect size above ~0.5 on a researcher-made test as an artefact until proven otherwise.**

#### The apps with real evidence

- **onebillion** (Maths 3–5 / 4–6) is the best-evidenced early-years maths app in existence, and it was tested in England. The [EEF efficacy trial (Nunes et al., Oxford, 2019)](https://d2tic4wvo1iusb.cloudfront.net/production/documents/projects/onebillion.pdf) `[RCT]` randomised **113 schools and 1,089 Year 1 pupils** in the lower half of the class to 12 weeks × 4 × 30 min of TA-supervised app use. Primary outcome (GL Progress Test in Maths): **g = 0.24 (95% CI 0.12–0.36), "+3 months", very high security (5 padlocks), 3% attrition.** But the FSM subgroup was **g = −0.10, "−2 months"**. An exploratory finding matters enormously for kidnix: **pupils did better when the supervising TA saw their role as teaching rather than merely supervising.** [Pitchford's Malawi RCT](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2015.00485/full) `[RCT, n = 283]` found larger effects (d up to 1.70 on curriculum measures) but in one school, with a tablet-delivered post-test that favoured the tablet group.
- **Bedtime Math.** [Berkowitz et al. 2015, *Science*](https://doi.org/10.1126/science.aac7427) `[RCT, 587 first-graders]` is the famous one, and the honest reading is much weaker than its reputation. The intention-to-treat effect for children of high-maths-anxious parents was **b = 5.25 W-score points, t = 1.99, p = 0.048**; no effect for low-anxiety parents (p = .79); and the anxiety × app **interaction was only p = 0.06**. The headline dose–response is correlational within the randomised arm. [Frank's published Comment](https://doi.org/10.1126/science.aad8008) `[critique]` argues the subgroup split looks data-dependent. The [Grade 3 follow-up](https://doi.org/10.1037/xge0000490) `[RCT follow-up, same team]` reports the gap stayed closed. **No independent replication exists.** The transferable insight is not "maths apps work" — it is *that a shared parent–child maths conversation, structured by a prompt, moved the outcome*.
- **Math Shelf** has two RCTs (n = 100, d = 0.57; n = 433, d = 0.94) `[RCT]` — but the developer is first author on both and the outcome measures are researcher-developed. Suggestive, not independent.
- **ST Math** targets Grades 2–5, so only the top edge of this range. [Evidence for ESSA](https://www.evidenceforessa.org/program/st-math-spatial-temporal-math/) `[META]` pools 4 studies and **346,248 students** to an **average ES of +0.07**; the cluster-RCTs gave +0.04 to +0.09. A [WestEd matched-schools study](https://www.wested.org/resource/st-math-evaluation/) `[QE, 474 schools]` gave 0.17 SD. A credible programme with small effects at scale — which is what honest edtech looks like.
- **DragonBox.** The much-cited Washington "Algebra Challenge" (4,192 students, "92.9% mastery after 1.5 hours") has **no control group, no pre/post test and no peer review**, and "mastery" means solving in-game DragonBox equations `[VENDOR]`. Real independent evidence exists only for DragonBox 12+ with Grade 7 students: [Decker-Woodrow et al. 2023, *AERA Open*](https://journals.sagepub.com/doi/full/10.1177/23328584231165919) `[RCT, N = 1,850]` found **g = 0.24–0.27** vs active control — and, importantly for kidnix, an "immediate feedback" condition was **not** significantly better than no feedback (g = 0.12, n.s.). **No peer-reviewed study of DragonBox Numbers, or of DragonBox with 4–8 year olds, exists.**
- **Khan Academy Kids**: [Evidence for ESSA lists Khan Academy with "No studies met inclusion requirements"](https://www.evidenceforessa.org/program/khan-academy/) `[absent]`.
- **GCompris**: ~280 records in OpenAlex, essentially all small descriptive classroom reports. **No RCT, quasi-experiment or standardised-outcome study** `[absent]`.
- **Numberblocks, Zorbit's, Teachley, Motion Math**: no outcome evaluation for the 4–8 band `[absent]`. Numberblocks has excellent [NCETM curriculum materials](https://www.ncetm.org.uk/classroom-resources/ey-numberblocks-at-home/) `[CURR]` and no evaluation.

#### What actually works in early maths

- **Developmental progressions are the one recommendation with real backing.** The [WWC practice guide *Teaching Math to Young Children*](https://ies.ed.gov/ncee/wwc/PracticeGuide/18) `[GUID]` rates only "teach number and operations using a developmental progression" as **Moderate**; its other four recommendations are **Minimal**. The WWC intervention report on [Building Blocks](https://files.eric.ed.gov/fulltext/ED635243.pdf) `[META, 3 cluster-RCTs, N = 3,221]` gives "potentially positive effects", pooled **ES 0.58** — with well-documented fade-out to g = 0.22–0.51 by Grade 1 without follow-through.
- **The EEF's [*Improving Mathematics in the Early Years and Key Stage 1*](https://d2tic4wvo1iusb.cloudfront.net/production/eef-guidance-reports/early-maths/EEF_Maths_EY_KS1_Guidance_Report.pdf)** `[GUID]` recommends: develop practitioner understanding of how children learn maths; dedicate time and integrate maths through the day; **use manipulatives and representations**; build on what children know; targeted support. It admits there is "little robust evidence" on parent-mediated intervention.
- **Linear number board games.** Siegler & Ramani's series `[RCT, small]` — [2008](https://siegler.tc.columbia.edu/wp-content/uploads/2019/02/sieg-ram08.pdf) (n = 36, ~1 hour of "The Great Race", number-line linearity **d = 1.62** vs a colour board); [Ramani & Siegler 2008](https://doi.org/10.1111/j.1467-8624.2007.01131.x) (n = 124 Head Start; magnitude comparison **d = 0.99**, counting 0.74, numeral ID 0.69, holding at 9 weeks with decay); [2009](https://siegler.tc.columbia.edu/wp-content/uploads/2019/02/sieg-ram09.pdf) (linear beats circular board, d = 0.65). Caveats: experimenter-delivered 1:1, proximal outcomes, ≤9 week follow-up, and [independent replications](https://doi.org/10.1016/j.jecp.2020.105060) find gains on counting but not magnitude. **A 1–10 linear track with count-on rules is cheap, plausible and worth building — expect modest, decaying effects.**
- **Nelson & McMaster's [meta-analysis of early numeracy interventions](https://doi.org/10.1037/edu0000334)** `[META, 33 studies]`: **g = 0.63** overall but **g = 0.35 on distal measures**, moderated by concrete–representational–abstract structure, duration, and explicit counting with one-to-one correspondence.

#### Two negative findings that should change the design

1. **Do not build approximate-number-system ("dot cloud") training.** [Schneider et al.'s meta-analysis](https://doi.org/10.1111/desc.12372) `[META, 284 effect sizes, N = 17,201]` finds symbolic comparison correlates with maths more strongly (r = .30) than non-symbolic (r = .24); [Szűcs & Myers](https://doi.org/10.1016/j.tine.2016.11.002) `[SR]` conclude there is "no conclusive evidence that specific ANS training improves symbolic arithmetic"; and [Szkudlarek et al. 2020](https://doi.org/10.1016/j.cognition.2020.104521) `[RCT, N = 318]` failed to replicate transfer. **Prioritise symbolic number.**
2. **Perceptual richness hurts.** [Kaminski & Sloutsky 2013](https://eric.ed.gov/?id=EJ1007940) `[experiment, 6–8 year olds, 4 studies]` found bar graphs made of countable pictures caused children to count the pictures and miss the strategy — "extraneous perceptual information substantially attenuated learning". [Carbonneau, Marley & Selig's meta-analysis](https://eric.ed.gov/?id=EJ1007941) `[META, 55 studies, N = 7,237]` finds manipulatives help most for retention and least for transfer, moderated by guidance and by perceptual richness. [Fyfe et al.](https://eric.ed.gov/?id=EJ1036777) `[SR]` recommend **concreteness fading** (concrete → iconic → symbolic). **Ten-frames and plain counters, not cartoon cupcakes.**

#### Adaptivity, feedback and timed practice

Adaptive tutoring in K–12 maths is weaker than the marketing: [Steenbergen-Hu & Cooper](https://doi.org/10.1037/a0032447) `[META, 34 samples]` found **g = 0.01–0.09**, *smaller for low achievers and for year-long use*. [Ma et al.](https://doi.org/10.1037/a0037123) `[META, 107 effect sizes]` found g = .42 against whole-class teaching but no advantage over human tutoring. Combined with the onebillion "TAs who teach get better results" finding, this argues strongly against unsupervised self-paced adaptivity for struggling 5-year-olds.

On feedback: [Kluger & DeNisi's classic meta-analysis](https://doi.org/10.1037/0033-2909.119.2.254) `[META, 607 effect sizes]` found d = .41 overall but **more than a third of feedback interventions *reduced* performance** — the harmful ones being those that direct attention to the self rather than the task. [Wisniewski, Zierer & Hattie](https://doi.org/10.3389/fpsyg.2019.03087) `[META, 435 studies]` find d = 0.48, with task and process *information* content mattering most.

On timed practice: Boaler's widely-repeated claim that timed testing causes maths anxiety in a third of students `[opinion]` rests on a correlational study ([Ramirez et al. 2013](https://doi.org/10.1080/15248372.2012.664593)) that never manipulated or measured timed tests. **No experimental evidence that timed practice causes maths anxiety in young children was found** `[absent]`. Conversely [Codding, Burns & Lukito](https://doi.org/10.1111/j.1540-5826.2010.00323.x) `[META, 17 single-case studies]` found "drill and practice with modeling produced the largest effect sizes" for fact fluency. Honest position: **brief, low-stakes, self-competitive retrieval practice is supported; public high-stakes timed tests are unsupported in either direction.**

**Design implication for kidnix.** A maths activity should: target subitising to 5 and number bonds to 10 explicitly (the ELG, and the gap in the market); use a short linear number track; render quantities as plain ten-frames and counters with concreteness fading; give task-focused rather than self-focused feedback ("that's 4 and 2 — try counting on from 4", never "you're so clever" or "wrong"); and offer optional beat-your-own-time practice with no public scoring. Keep the adaptive engine trivial.
### 2d. Computational thinking at 5–7

**The KS1 computing curriculum is the design brief.** Statutory requirements `[CURR]`: understand what algorithms are and that "programs execute by following precise and unambiguous instructions"; **create and debug simple programs**; use logical reasoning to predict the behaviour of simple programs. Note "debug" is statutory at age 5–7. Note also that nothing requires a text language, a screen, or a specific tool.

**Does learning to program produce transferable cognitive gains?** This is the claim that justifies most early-years coding products, and it is *partially* supported. Scherer, Siddiq & Sánchez Viveros's [three-level meta-analysis of transfer effects](https://doi.org/10.1037/edu0000314) `[META]` pooled **105 studies and 539 effect sizes**: overall transfer **g = 0.49** (95% CI 0.37–0.61), **near transfer g = 0.75**, **far transfer g = 0.47**, with positive transfer to creative thinking, mathematical skills, metacognition, spatial skills and reasoning. Their companion [meta-analysis of programming instruction itself](https://doi.org/10.1016/j.chb.2020.106349) `[META]` (139 interventions, 375 effect sizes) found **g = 0.81** for learning programming per se, **g = 0.44** for visualisation and **g = 0.72** for *physicality* interventions — i.e. tangible/embodied approaches outperform purely on-screen ones.

Two important qualifications. First, these are dominated by older learners, so the 5–7 figures are extrapolations. Second, the "far transfer" estimate sits in a literature with a bad historical record (the 1980s Logo transfer claims largely failed to replicate), so treat g = 0.47 as an upper bound.

**ScratchJr** is the reference implementation for this age. Bers and the [DevTech Research Group](https://sites.bc.edu/devtech/papers/) built it explicitly for 5–7 year olds who cannot yet read fluently, and their [*Coding as Another Language*](https://doi.org/10.1016/j.ecresq.2023.05.002) `[QE]` curriculum frames coding as expressive literacy rather than as vocational training. The empirical base is real but modest: [Papadakis's review of coding apps](https://doi.org/10.3389/feduc.2021.657895) `[SR, N=21 studies]` concludes all four reviewed apps positively affect CT skills, but that **none demonstrably supports "computational fluency"** — expressive, self-directed creation — except ScratchJr, credited specifically for its **sandbox approach**. [Pugnali, Sullivan & Bers](https://doi.org/10.28945/3768) `[QE, n=28, ages 4–7]` compared ScratchJr against the tangible KIBO robot and found interface type matters: **tangible interfaces produced more positive interpersonal behaviour; the graphical interface produced better mastery of some CT concepts.** Much of the widely-cited "ScratchJr impact" literature is in fact [Google Analytics usage data](https://doi.org/10.28945/4437) `[OBS]`, not outcome data — worth knowing before repeating the claim.

**Unplugged and tangible approaches are, if anything, better evidenced.** [Lu, Li, Yang et al.'s systematic review and meta-analysis of unplugged CT activities](https://doi.org/10.1186/s40594-023-00434-7) `[META]` (49 studies reviewed; 13 studies, 16 effect sizes meta-analysed) found **Hedges' g = 1.028** (95% CI 0.641–1.415) — a large effect, though from few studies with the usual small-study inflation risk. Board and card games were the most common format. A [cluster-randomised trial with 47 preschoolers](https://doi.org/10.3390/educsci13090858) `[RCT]` combining unplugged coding and robotics found transfer to plugged coding and to executive functions (planning, response inhibition, visuo-spatial skills). [Bee-Bot work](https://doi.org/10.3389/feduc.2022.757627) `[QE]` shows scaffolding type significantly moderates sequencing and decomposition gains — i.e. the adult/scaffold matters more than the robot.

**Design implication:** at 5–7 the developmentally appropriate CT activity is *sequencing a short program of concrete actions and watching it run, then fixing it*. Blocks should be pictorial, the program should be 3–8 steps, the result should be a story or an animation the child wanted to make, and there must be an explicit, celebrated "it did the wrong thing — let's fix it" loop, because debugging is the statutory bit and the transferable bit.

---


### 2e. Creativity, arts, music and photography

#### Drawing: digital is not a lesser medium, and the evidence is better than expected

Lowenfeld's developmental stages (scribbling → pre-schematic ~3–4 → schematic ~5–7 → dawning realism ~7–9) still frame the field, and a [2025 study of 218 drawings by 3–5 year olds](https://doi.org/10.3390/educsci15060681) `[QE]` confirmed the *sequence* (χ² = 104.92, p < .0001; ρ = .661) while showing the *ages* drift widely. Across 4–8 you are spanning tadpole figures through baseline-and-skyline schemas. A 5-year-old does not want realism; they want **a recognisable symbol they can name and tell you about**.

The key empirical study is Couse & Chen's [videotaped observation of 41 children aged 3.1–6.3 drawing self-portraits on stylus tablets](https://files.eric.ed.gov/fulltext/EJ898529.pdf) `[QE, no control group]`:

- **75.6% reached the highest coded level ("Create") in the very first session**, rising to 98%. The researchers had planned four acclimatisation sessions and cut it to one.
- Teachers rated **66% of tablet drawings as typical of the child's paper work and 20% as above expectation**.
- Sustained attention averaged 24.1 min initially; but 3-year-olds fell to 13 min while 4s and 5s held ~23.7 min (F(2,38) = 6.24, p < .01). **Engagement rises sharply between 3 and 4** — good news for kidnix's floor age.
- Children hit a mean 4.4 technical problems per session and *still* 57.3% of sessions produced zero frustration; 64.1% preferred tablet to paper. Novelty was checked: demand stayed high after two months.

Matthews & Jessel's earlier qualitative work found children use "the same basic media-independent strategies" on screen as on paper `[QUAL]`, and [Matthews & Seow](https://eric.ed.gov/?id=EJ776122) `[QUAL]` found stylus clearly beats mouse. But a direct [finger-vs-stylus-vs-pen experiment with 69 children](https://doi.org/10.3389/fpsyg.2022.806093) `[QE]` found originality scores of finger 4.00 > stylus 3.69 > pen 2.30 (F(2,130) = 85.43, ηp² = .57), with finger beating pen significantly for the youngest group. **Do not gate drawing behind stylus ownership.**

Do stamps, fill-buckets and clip art suppress creative effort? **I could find no controlled study either way** `[absent]` — anyone asserting it is over-claiming. The defensible argument for a sparse palette is different and better: [Anthony et al.'s CHI study of 30 children aged 5–10](https://doi.org/10.1145/2858036.2858200) `[QE]` found **interface complexity measurably degrades children's touch accuracy** through visual salience. Keep the palette small because small hands miss small targets on busy screens, not because of creativity theory. NAEYC's [joint position statement with the Fred Rogers Center](https://www.naeyc.org/sites/default/files/globally-shared/downloads/PDFs/resources/topics/PS_technology_WEB.pdf) `[GUID]` adds the sensible boundary: touchscreen drawing "can add to children's graphic representational experiences" but "should not replace paints, markers, crayons."

**Drawing as a route into writing** is one of the better-supported claims in this whole note. Mackenzie & Veresov argue from Vygotskian grounds that drawing alongside writing "allows children to create meaningful texts of a complexity that they may not be able to create using conventional print forms alone" ([2013](https://doi.org/10.1177/183693911303800404)) `[QUAL/theoretical]`. Drawing supplies the planning and rehearsal that emergent writers cannot hold in working memory. **A canvas that accepts a picture plus a caption — typed, scribed, or voice-recorded — is doing real literacy work. A canvas that only exports a PNG is not.**

#### Music: the transfer claim is dead; make music anyway

This needs saying bluntly, because it is the most over-marketed claim in children's software.

- Sala & Gobet's [2017 meta-analysis](https://doi.org/10.1016/j.edurev.2016.11.005) `[META, 38 studies, >3,000 children]` found d = 0.16 overall, **shrinking as study quality rose**.
- Their [2020 multilevel meta-analysis](https://doi.org/10.3758/s13421-020-01060-2) `[META, N = 6,984, k = 254]` is decisive: "Once the quality of study design is controlled for, the overall effect of music training programs is null (ḡ ≈ 0)." The small positive effect (ḡ ≈ 0.20) appears **only** in studies without random allocation and without active controls.
- Mehr, Schachner, Katz & Spelke ran [two RCTs with 4-year-olds](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0082007) `[RCT, n = 29 and 45]` on spatial, numerical and vocabulary outcomes: no consistent transfer, and the apparent Experiment 1 differences "would not have survived correction for multiple comparisons."

A [Finnish study of 66 five-to-six year olds](https://doi.org/10.1038/s41598-018-27126-5) `[QE]` did find gains in phoneme processing and vocabulary from weekly music playschool — but children were **not randomly assigned**, which is precisely the design flaw Sala & Gobet identify as inflating effects. Cite it honestly or not at all.

Mehr et al. supply the honest justification themselves: the benefit of music education "is self-evident: to improve the musical skills and repertoire." **That is sufficient. Build the music activity for joy and musicianship, and promise nothing about maths scores.**

What a 4–6 year old can actually do: in a call-and-response drumming study of six 4–5 year olds, **84% held a steady beat, 79% of improvised responses were exactly four beats long, 86% started on beat 1 and 80% ended on beat 4** ([Research & Issues in Music Education, 2010](https://commons.lib.jmu.edu/rime/vol8/iss1/3/)) `[QUAL, n=6]`. Brophy's three-year longitudinal collection of 558 improvisations from 62 children used alto xylophone **in C pentatonic** within an Orff rondo `[OBS, longitudinal]`. **Four-beat phrases and a pentatonic constraint are the operating envelope.**

On "no wrong notes": I found **no controlled evidence that constrained scales improve creative output or learning** `[absent]`. It is Orff Schulwerk convention — Orff xylophones have removable bars precisely so the fourth and seventh can be taken out — with a plausible mechanism (remove the failure mode so the first press is rewarded) and a strong practical demonstration in Brophy. Build it; label it `[RATIONALE]`.

Specific tools: [Chrome Music Lab](https://musiclab.chromeexperiments.com/About/) is widely used and its own About page carefully avoids claiming learning gains — **no published evaluation exists** `[VENDOR]`. The same for Incredibox, Groove Pizza and Bandlab: strong design rationale (loop-based, immediate sound, no notation), zero peer-reviewed evaluation with under-8s. Sugar/OLPC's [TamTam suite](https://wiki.sugarlabs.org/go/Activities/TamTam) is well documented technically with **no published outcome evidence** `[RATIONALE]` — though its design (Mini for immediate play, Jam for loops, Edit for arrangement) is a good architectural model.

#### Photography with young children

The strong work here is methodological rather than outcome-based. Sturges gave disposable cameras to [20 children aged 3–4 in two Australian preschools](http://dx.doi.org/10.1080/03004430.2023.2235908) `[QUAL]`: child-led photography "offered children the opportunity to participate, express themselves, and share their place stories", and *relationships* dominated what they chose to photograph. Cappello's [photo-elicitation work with 40 children aged 6–9](https://eric.ed.gov/?q=Cappello+photography+data+generation) `[QUAL]` showed children say far more when interviewed *about their own photographs* than when questioned directly. Byrnes & Wasik used classroom cameras to build vocabulary and retelling `[QUAL/practitioner]`. All of this sits inside Clark & Moss's Mosaic Approach, where children's photographs are one "voice" alongside drawings, tours and talk `[GUID]`.

**There is no RCT showing cameras improve language outcomes** `[absent]`. The claim that survives is narrower and still worth building for: *a photograph gives a 5-year-old a concrete referent to talk and write about* — the same mechanism as drawing-before-writing.

#### The maker framing: good design theory, weak evidence base

Papert's constructionism and Resnick's **four Ps — Projects, Passion, Peers, Play** ([*Lifelong Kindergarten*](https://direct.mit.edu/books/book/3134/Lifelong-KindergartenCultivating-Creativity)) `[GUID]` are the right design frame. The most operationally useful text is Resnick & Rosenbaum's [*Designing for Tinkerability*](https://web.media.mit.edu/~mres/papers/designing-for-tinkerability.pdf) `[RATIONALE]`, which names three concrete principles — **immediate feedback** ("a very short interval of time between making a change and seeing its effect"), **fluid experimentation** ("easy to get started… without spending a lot of time setting up"), and **open exploration** — and warns that institutions often "introduce making into the curriculum in a way that saps all the spirit from the activity." "Low floor, high ceiling" is Papert's; "**wide walls**" (many paths, not one) is Resnick's addition. Wide walls has been tested essentially once, in a [natural experiment on 14,000+ Scratch users](https://unmad.in/blog/2018/05/testing-the-wide-walls-design-principle-in-the-wild/) `[QE]`.

The critique deserves quoting: Vossoughi, Hooper & Escudé advance "a critique of branded, culturally normative definitions of making" and caution "against their uncritical adoption into the educational sphere" ([*Harvard Educational Review*, 2016](https://doi.org/10.17763/0017-8055.86.2.206)) `[critique]`. Systematic reviews of the makerspace literature find it dominated by small qualitative studies with almost nothing on young children ([TechTrends 2020](https://doi.org/10.1007/s11528-020-00566-5); [JOSTE 2023](https://doi.org/10.1007/s10956-023-10041-4)) `[SR]`. **Maker enthusiasm outruns its evidence by a wide margin.** Use the design principles; don't cite the movement as evidence.

#### Creativity measurement: treat "increases creativity" as unproven

Zeng, Proctor & Salvendy catalogue six weaknesses of divergent-thinking tests — "lack of construct validity; not testing the integrated general creative process; neglect of domain specificity and expertise; and poor predictive, ecological, and discriminant validities" ([2011](https://doi.org/10.1080/10400419.2011.545713)) `[critique]`. TTCT scores are noisy and were never designed to detect a six-week software effect on 5-year-olds. **kidnix should not claim to increase creativity.** It can honestly claim to give children materials, time and no wrong answers.

#### Digital storytelling and authoring tools

Thin but not empty. A [systematic review of 89 studies on digital technologies and young children's language and literacy](https://doi.org/10.1177/21582440241230850) `[SR]` found positive but heterogeneous effects with design quality the dominant caveat. A [PRISMA review of 45 digital-storytelling studies](https://doi.org/10.3390/su13179829) `[SR]` found consistent speaking-skill gains — **but almost entirely at primary level and above, not early years**. In early childhood the evidence is phenomenological `[QUAL]`.

ScratchJr is the best-instrumented tool in the space: analysis of [4,352,802 coding sessions](http://dx.doi.org/10.1007/s11423-021-10011-w) `[OBS]` found home users spent more time on advanced blocks **and on the paint editor** than school users — a direct argument for shipping a good drawing tool *inside* the coding activity. **Book Creator, Storybird and Puppet Pals have marketing, not evaluations** `[VENDOR]`.
### 2f. General learning principles

#### The four pillars — the most useful single framework

Hirsh-Pasek, Zosh, Golinkoff, Gray, Robb & Kaufman, [*Putting Education in "Educational" Apps: Lessons From the Science of Learning*](https://doi.org/10.1177/1529100615569721), *Psychological Science in the Public Interest* `[SR]`, remains the best design filter available. An app is educational when it supports learning that is:

1. **Active** — minds-on, not just fingers-on. Physical tapping is not activity; effortful thinking is.
2. **Engaged** — attention held *by the learning content*, not stolen by it. The authors warn specifically against "seductive details", background media competing for attention, and passive observation without response.
3. **Meaningful** — connected to what the child already knows and to real contexts.
4. **Socially interactive** — with a caregiver, a peer, or a genuinely contingent on-screen partner.

…all **"within the context of a supported learning goal."** Their content analysis of top-selling children's apps found few met the bar.

This framework maps almost perfectly onto kidnix's stated design (no feeds, no store, creation over consumption). The weakest pillar for kidnix is **socially interactive**, because the product is designed for a child alone. That is the pillar to engineer around deliberately — see §3.

#### The DfE now regulates this, and kidnix should read it as a spec

Since the current EYFS framework, England has a **statutory cross-reference** to [DfE guidance on children's screen use in early years settings](https://help-for-early-years-providers.education.gov.uk/safeguarding-and-welfare/screen-use) `[GUID]`. Providers "must have regard to" it. Its operative statements:

- Under 2: avoid screen time altogether. **Ages 2–5: "screen time should be limited to 1 hour a day, less if possible."**
- **"You should not allow children to access or use screens alone or with other children without adult co-engagement."**
- "Screens should not replace high quality educator–child interactions."
- Content should be "slow-paced, repetitive and predictable" and **"advert-free"**; avoid "fast-paced, over-stimulating" material with excessive cuts, movement or flashing.
- Screens must not be used "for routine management or to calm children", "to occupy children", or to "manage their behaviour", because this undermines self-regulation.

This is the closest thing to a UK regulatory design spec for a product like kidnix, and kidnix already satisfies several clauses by construction (advert-free, no feeds). The co-engagement clause and the "not to occupy children" clause are the ones that should shape the parent-facing framing.

#### Rewards, stars and badges: the evidence says be careful

Deci, Koestner & Ryan's meta-analysis and their [*Extrinsic Rewards and Intrinsic Motivation in Education: Reconsidered Once Again*](https://doi.org/10.3102/00346543071001001) `[META]` established that **tangible rewards contingent on engagement, completion or performance substantially undermine intrinsic motivation** for tasks that were already interesting. The countervailing finding is equally important: **verbal, informational, non-controlling feedback does not undermine and often enhances it.** The line is *controlling* versus *informational*.

Schiefele et al.'s [review of reading motivation](https://doi.org/10.1002/rrq.030) `[SR]` finds the same split in reading specifically: intrinsic dimensions predict reading amount and competence; extrinsic dimensions (competition, recognition, grades, compliance) contribute weakly or negatively.

Gamification research is mostly theoretical rather than causal — [Krath, Schürmann & von Korflesch's systematic review](https://doi.org/10.1016/j.chb.2021.106963) `[SR]` found 118 different theories invoked across the field, which is a fair proxy for "no settled mechanism." I found **no meta-analysis isolating badges/stars/points for children under 8.**

**Design implication:** kidnix should show a child *what they made* and *what they can now do*, not how many stars they have. Progress artefacts (the journal, the gallery, the recording of them reading) are informational feedback; leaderboards, streaks and star economies are controlling feedback. Streaks in particular pair badly with bounded sessions and with a wellbeing-first product.

#### Guidance, scaffolding and fading

Alfieri/Lazonder & Harmsen's [meta-analysis of inquiry-based learning](https://doi.org/10.3102/0034654315627366) `[META, 72 studies]` found **guidance helps at every age**: d = 0.66 for learning activities, 0.71 for performance success, 0.50 for learning outcomes — and that **younger learners need more explicit guidance**. Kirschner, Sweller & Clark's [*Why Minimal Guidance During Instruction Does Not Work*](https://doi.org/10.1207/s15326985ep4102_1) `[SR]` makes the cognitive-load case: guidance only stops helping once learners have enough prior knowledge to guide themselves. A 5-year-old never has that.

The EEF's KS1 guidance operationalises fading: modelling and structured support "which should be gradually reduced as a child progresses until the child is capable of completing the activity independently" `[GUID]`.

**Productive failure** (Kapur) is *not* a good fit here. Its [classroom experiments](https://escholarship.org/uc/item/7761h4h2) `[QE]` are with secondary students learning formal concepts, and the mechanism requires enough prior knowledge to generate candidate solutions. There is no evidence base for productive failure at 5–7 — and the DfE's "slow-paced, repetitive and predictable" guidance points the other way. **Design for low-stakes failure that is immediately recoverable, not for deliberate struggle.**

#### Adaptive difficulty

Attractive in theory, weaker in practice than expected. The strongest single data point is the [Norwegian reading RCT](https://doi.org/10.1016/j.learninstruc.2018.05.004) `[RCT]`, where the *only* difference between two intervention arms was whether the software adapted — and there was **no significant difference in outcomes**. Similarly the [Dutch literacy game trial](https://doi.org/10.7717/peerj.15499) `[RCT]` found benefits concentrated in children who were already strong. Adaptive difficulty is worth doing simply, at low cost; it is not worth a large engineering budget, and it can widen gaps.

#### Spacing and retrieval

The distributed-practice effect is one of the most robust findings in psychology — [Cepeda et al.'s synthesis of 839 assessments across 317 experiments](https://doi.org/10.1037/0033-2909.132.3.354) `[META]` — and it replicates in children: [Lipowski, Pyc, Dunlosky & Rawson](https://doi.org/10.3389/fpsyg.2016.00350) `[QE, n=88, ~age 10]` found robust retrieval-practice benefits in elementary children, independent of reading comprehension and processing speed. The 5–7 direct evidence is thinner, but the mechanism is domain-general.

**Design implication:** kidnix's bounded-session architecture is an *asset* here. Short daily sessions that revisit yesterday's GPCs or number facts are, structurally, spaced practice. Make the revisit automatic and invisible rather than a "revision" screen.

#### Co-play, and the honest problem with it

Every serious framework — the four pillars, the DfE screen guidance, joint-media-engagement research — says an adult alongside the child materially improves learning. [Zhang et al.'s RCT of bilingual discussion prompts in shared e-book reading](https://doi.org/10.1016/j.compedu.2022.104622) `[RCT, 107 dyads]` is a nice concrete case: adding *dialogic prompt pages* to an e-book improved story comprehension and retelling **without training the parents at all** — the prompts induced dialogic reading behaviour by themselves.

That is the transferable trick. kidnix cannot conjure a parent, but it can **design moments that recruit one**: an end-of-session "show someone what you made", a prompt card the child carries to an adult, a letter that must be sent to a real person, a recording made *for* someone.

### 2g. Recent systematic reviews and meta-analyses of educational apps for early years

#### The headline number, and why it should be discounted

The most directly relevant meta-analysis is **Kim, Gilbert, Yu & Gale (2021), [*Measures Matter: A Meta-Analysis of the Effects of Educational Apps on Preschool to Grade 3 Children's Literacy and Math Skills*, AERA Open](https://doi.org/10.1177/23328584211004183)** `[META]`. It synthesised **36 intervention studies and 285 effect sizes** using random-effects meta-regression with robust variance estimation:

- **Mean weighted effect size +0.31 SD** on overall achievement, comparable in maths and literacy.
- But three significant moderators, and each of them cuts the number down:
  - Effects were **larger for preschool than for K–3** students.
  - Effects were **larger for researcher-developed than for standardised outcomes**.
  - Effects were **larger for constrained than for unconstrained skills**.

Read the moderators together and the honest interpretation is: *educational apps reliably move narrow, bounded, closed-set skills (letter–sound knowledge, number identification, counting) as measured by tests written by the people who built the app; they move broad, open-ended competence (comprehension, composition, reasoning) much less, and possibly not at all.* "Constrained skills" is Paris's term — the small, finite, masterable sets (letter names, letter sounds, concepts of print). That is exactly the zone where software is good, and it maps almost perfectly onto what kidnix should attempt: phonics practice, key location, number bonds — not "learns to read."

**Griffith, Hagan, Heymann, Heflin & Bagner (2020), [*Apps As Learning Tools: A Systematic Review*, *Pediatrics*](https://doi.org/10.1542/peds.2019-1579)** `[SR]` screened 1,447 studies and included 35 with children under 6. Findings: "Evidence of a learning benefit of interactive app use for early academic skills was found across multiple studies, **particularly for early mathematics learning in typically developing children.**" No effect was found for apps aiming to improve social communication in children with ASD. Their limitation statement matters as much as the result: "Risk of bias was unclear for many studies because of inadequate reporting. Studies were highly heterogeneous in interventions, outcomes, and study design."

For maths specifically, [Outhwaite et al.'s 2023 UCL review](https://repec-cepeo.ucl.ac.uk/cepeow/cepeowp23-02.pdf) `[SR]` (50 studies, 77 apps, 23,981 children aged 4–7) is covered in §2c: 92% report a benefit, but only 3 studies combine an RCT, n > 250 and a standardised measure, and 2 of 5 follow-up studies showed **fade-out within 1–2 months**.

#### Game-based learning: design matters more than medium

Clark, Tanner-Smith & Killingsworth's [*Digital Games, Design, and Learning*, *Review of Educational Research*](https://doi.org/10.3102/0034654315582065) `[META]` is the best-structured meta-analysis in the field because it separates two questions:

- **Media comparisons** (game vs non-game): **g = 0.33** (95% CI 0.19–0.48, k = 57, n = 209).
- **Value-added comparisons** (augmented game design vs standard game design): **g = 0.34** (95% CI 0.17–0.51, k = 20, n = 40).

Their conclusion is the one to internalise: the results "highlight the affordances of games for learning as well as **the key role of design beyond medium**." Improving the *design* of a game buys as much as adding a game in the first place. That is a direct argument for kidnix spending its effort on activity design rather than on the fact of being software.

Wouters, van Nimwegen, van Oostendorp & van der Spek's [meta-analysis of serious games](https://doi.org/10.1037/a0031311) `[META, learning k = 77, N = 5,547]` found **d = 0.29** for learning versus conventional instruction — and, crucially, that learners gained more **"when the game was supplemented with other instruction methods, when multiple training sessions were involved, and when players worked in groups."** All three moderators point away from solo, one-off, standalone play. Notably, they found **little support for the assumption that serious games are more motivating** than conventional instruction.

#### The generic edtech picture

Escueta, Quan, Nichols & Oreopoulos's [NBER review of experimental evidence on education technology](https://doi.org/10.3386/w23744) `[SR of RCTs]` reaches the same shape of conclusion across access, computer-assisted learning, behavioural interventions and online learning: computer-assisted learning shows the most consistent positive effects, especially in maths, and especially where it provides personalised practice — not where it substitutes for teaching.

The EEF's **Teaching and Learning Toolkit "Digital technology" strand** `[META/GUID]` sits in the same place: a modest positive average (on the order of a few months' additional progress) at moderate cost, with the standing EEF caveat that *technology should supplement rather than replace teaching, and that impact depends far more on how it is used than on the technology itself.* Its companion guidance report, [*Using Digital Technology to Improve Learning*](https://educationendowmentfoundation.org.uk/education-evidence/guidance-reports/digital) `[GUID]`, organises its recommendations around exactly that: consider how technology will improve teaching and learning *before* introducing it; use it to improve explanation and modelling; use it to increase the **quality and quantity of pupil practice**; and use it to improve assessment and feedback. *(I was unable to retrieve the live toolkit figures — the EEF site is JavaScript-rendered and blocked automated retrieval — so the exact months'-progress figure should be checked against the site before being quoted publicly.)*

#### Why the whole "does it work?" question is partly malformed

Richard Clark's [*Reconsidering Research on Learning from Media*](https://doi.org/10.3102/00346543053004445) `[SR]` argued that media are "mere vehicles that deliver instruction but do not influence student achievement any more than the truck that delivers our groceries causes changes in our nutrition." Robert Kozma's reply (that some representational capabilities genuinely are medium-specific) is the right qualification, not a refutation. Forty years on, the Clark–Kozma frame still explains why "app vs no app" meta-analyses cluster around d = 0.3 regardless of subject: they are measuring the extra instructional time and attention, not the medium.

Three practical consequences for reading any edtech evidence claim:

1. **Ask what the outcome measure was.** Kim et al. quantified this: researcher-developed measures inflate effects.
2. **Ask what the control group did.** A no-treatment control measures time-on-task; an active control measures the design.
3. **Ask whether the effect survived a delay.** In early-years maths apps, 2 of 5 follow-ups showed fade-out within two months.

#### The statutory backdrop in England has tightened

Worth restating here because it changes what a UK early-years product may credibly claim: the current EYFS framework requires providers to "have regard to" [DfE guidance on children's screen use](https://help-for-early-years-providers.education.gov.uk/safeguarding-and-welfare/screen-use) `[GUID]`, which caps 2–5 year olds at "1 hour a day, less if possible", requires adult co-engagement ("You should not allow children to access or use screens alone… without adult co-engagement"), requires content to be "slow-paced, repetitive and predictable" and "advert-free", and forbids using screens "to occupy children" or "manage their behaviour". This is stricter than the marketing posture of most children's software, and kidnix is unusually well placed to comply with it.

---

## 3. Per-activity: "evidence says → design it like this"

### Draw / paint

**Evidence says.** Children reach their highest observed drawing level on a tablet within a single session, and teachers rate the output as typical of or better than their paper work (Couse & Chen `[QE]`). Finger input is fine and may beat stylus at 5–6 for originality `[QE]`. Interface complexity measurably degrades children's touch accuracy `[QE]`. Drawing is a genuine planning scaffold for writing `[QUAL]`. Digital should not displace physical media (NAEYC `[GUID]`).

**Design it like this.**
- Big canvas, ≤8 tools visible at once, large targets. Every extra palette item costs touch accuracy.
- Finger-first; stylus optional; pressure/velocity → line width if the hardware allows (Matthews & Seow).
- **Ship a caption field and a "tell me about it" voice recorder on every drawing.** This is the cheapest literacy win in the product.
- Undo, yes. Auto-save always. Never a "are you sure you want to discard?" dialog — a 5-year-old cannot read it.
- No clip-art stamp library as the default surface (unevidenced either way, but it competes for the palette slots that matter and drags the activity toward assembly rather than mark-making). If stamps exist, put them one level down.
- Do not gate or grade. There is no "correct" drawing.

### GCompris (and the "activity suite" pattern)

**Evidence says.** GCompris is a 100+ activity suite for ages 2–10, free, KDE-community-built, and its own site makes **no claim of educational evaluation** `[VENDOR/absent]`. I found no published RCT or independent evaluation of GCompris `[absent]`. The generic evidence on drill-and-practice software is that it produces real but small gains on the exact skill drilled, and that effect sizes are largest for the most proximal outcomes.

**Design it like this.**
- Treat GCompris as a **curated shelf, not a whole product**. 100+ activities of wildly varying quality and age-fit is an anti-pattern for a 5-year-old; the paradox-of-choice cost is real and the DfE screen guidance asks for "slow-paced, repetitive and predictable."
- Hand-pick perhaps 12–20 activities that map to EYFS/KS1 objectives, group them by what the child is doing rather than by subject, and hide the rest behind a parent control.
- Localise to en-GB and check every phonics activity against a UK synthetic-phonics progression before exposing it. GCompris's letter activities are not built to Letters-and-Sounds phases.
- Do not present it as "100 activities!" in marketing. Present it as "the ones we picked."

### Keyboard game

**Evidence says.** No statutory UK requirement at KS1 `[CURR]`. US formal keyboarding starts Grade 3 `[CURR]`. Formal touch-typing training buys only **d = 0.27** over self-taught typing at 168,000-participant scale `[OBS]`. No RCT of any typing tutor with under-8s `[absent]`. No evidence early hunt-and-peck causes harm `[absent]`. NCCE's actual Year 1 practice is key-location familiarisation, not finger discipline `[CURR]`. Handwriting retains an advantage for *letter learning* at this age `[QE, multiple]`.

**Design it like this.**
- **Target: find the key that makes this sound, fast.** Not home row, not WPM, not finger assignment.
- Show the **lowercase** grapheme on screen to match phonics teaching, even though the keycap is uppercase. Say the phoneme, not the letter name, in phonics mode; offer letter names as a separate mode.
- Accept any finger. Never scold posture. Optionally *suggest* using more than one finger (finger count correlates with speed at r = 0.38) as a fun challenge, never as a gate.
- Because there is no evidence for a lower age bound, gate on *interest*, not age: make it available and let it be ignored.
- **Explicitly tell parents this does not replace handwriting**, and say why. This builds trust and is true.
- Do not build a WPM leaderboard or a streak.

### Story-maker

**Evidence says.** Digital storytelling shows speaking-skill gains but mostly above early years `[SR]`. Drawing scaffolds composition `[QUAL]`. Transcription cost — not ideas — throttles 5–7 year olds' writing `[OBS]`. Oral rehearsal before writing is statutory in Year 1 `[CURR]`. Purpose and audience are what the EEF names as the motivational mechanism `[GUID]`. ScratchJr home users spend heavy time in the paint editor `[OBS]`.

**Design it like this.**
- **Picture first, words second.** Every page: draw or photograph, then caption. This matches how the child already composes.
- **Three input routes on every caption, child's choice:** type it, say it (recorded audio kept as-is, no transcription), or ask a grown-up to scribe. Recording their voice is not a lesser option — it is a legitimate published text at this age and it removes the transcription bottleneck entirely.
- If you offer speech-to-text at all, treat it as a *draft assist* that the child then fixes, and never let it silently correct spelling — that would delete the exact practice the curriculum requires. Given that ASR on 5-year-old UK-accented speech is poor and an offline model will be worse, **recording-as-artefact is the safer primary design and dictation-to-text a later experiment.**
- Oral rehearsal prompt before writing: "Say your sentence out loud first." One line, statutory, free.
- Finish with **publish to somebody** — read it aloud into the journal, or send it to a family member. A story with no reader is a worksheet.

### Music

**Evidence says.** Music training does **not** transfer to general cognition (ḡ ≈ 0 once design quality is controlled) `[META]`. Musical benefit is its own justification `[RCT authors' own framing]`. 4–5 year olds reliably hold a steady beat and phrase in fours `[QUAL]`. Pentatonic constraint is Orff convention with a good practical track record and no controlled evidence `[RATIONALE]`. No published evaluation of Chrome Music Lab, Incredibox, TamTam or similar `[VENDOR/absent]`.

**Design it like this.**
- **No notation.** Pitch set constrained to a pentatonic (or diatonic with the 4th and 7th removable, exactly like an Orff xylophone). Nothing a child presses should sound wrong.
- **Loops of 4 or 8 beats.** That is the unit children of this age actually track.
- Sound the *instant* a control is touched — Resnick's "immediate feedback" principle, and the thing that makes a music toy feel alive.
- Layer count visible and small (3–5 tracks). A DAW timeline is the wrong metaphor.
- Record and keep. A saved song in the journal is the artefact; a session with nothing kept teaches nothing about making.
- **Marketing must not claim cognitive benefit.** Claim joy and musicianship. It is both honest and, per Mehr et al., sufficient.

### Block coding

**Evidence says.** "Create and debug simple programs" is statutory at KS1 `[CURR]`. Programming instruction produces g = 0.81 on programming itself and g = 0.49 transfer, with far transfer g = 0.47 — an upper bound `[META]`. **Physicality/tangible interventions outperform screen-only (g = 0.72 vs 0.44)** `[META]`. Unplugged CT activities show g = 1.03 in a small meta-analysis `[META, few studies]`. ScratchJr uniquely supports open-ended "computational fluency" via its sandbox `[SR]`. Tangible interfaces produce better interpersonal behaviour; graphical produce better concept mastery `[QE]`.

**Design it like this.**
- Pictorial blocks, no reading required, ScratchJr-style. 3–8 blocks is a complete program at this age.
- **The goal is a story or an animation the child wanted, not a puzzle with one right answer.** Sandbox over level ladder — that is the one thing the review credits ScratchJr for.
- **Build the debugging loop explicitly and celebrate it.** "It did something different from what you expected — let's find out why" is the statutory skill *and* the transferable one. Never show a red error.
- Include the paint editor inside the coding activity; home users of ScratchJr demonstrably live in it.
- Ship **companion unplugged/printable activities** (sequence cards, a floor grid, a "program the grown-up" game). The physicality effect size is the strongest number in this domain, and it costs almost nothing to print.
- Do not promise "learns to code" or IQ benefits. Promise "makes things happen on purpose."

### Photos

**Evidence says.** Child-led photography reliably elicits far more talk than direct questioning `[QUAL]`; children photograph relationships, not objects `[QUAL]`; the Mosaic Approach treats children's photographs as a legitimate voice `[GUID]`. **No RCT shows cameras improve language outcomes** `[absent]`. Immediacy of result is repeatedly named as the decisive feature in classroom accounts.

**Design it like this.**
- One enormous shutter target. No mode switching. No filters as a headline feature.
- **Instant visible result** — the Polaroid effect. The photo appears in the journal immediately.
- Photos land somewhere they can be **captioned or narrated straight away**. A camera roll is not an activity; a camera plus a caption is.
- No destructive delete without a grown-up. No face detection, no auto-tagging, no cloud, nothing that inventories a child's home.
- Prompt cards ("photograph something that is exactly your favourite colour"; "photograph three things that are older than you") to give the shutter a purpose — this is the photo-elicitation mechanism in product form.

### Letters to family

**Evidence says.** This is, on the evidence, **the strongest activity in the kidnix list.** The EEF names purpose and audience as the mechanism that makes children willing to do the volume of writing practice they need `[GUID]`. Intrinsic and identified motivation predict literacy behaviour; extrinsic recognition and compliance predict it weakly or negatively `[SR]`. The four pillars' weakest link for a solo product is **social interaction** — and this activity is the one that supplies it `[SR]`. Adding contingent prompts to a shared-reading experience improved comprehension and retelling **without training the adult at all** `[RCT]`.

**Design it like this.**
- A real, named recipient chosen from a parent-approved list. The child sees the person's photo and name, not an address.
- Picture + caption + voice, exactly as the story-maker. A 5-year-old's letter is legitimately a drawing with three words and a recorded "I love you Grandad."
- **Show the reply.** A one-way outbox is not an audience. Whatever the transport (parent-mediated email, printed post, a sync when a parent connects a device), the reply must come back *into the child's journal* and be announced.
- Include a small number of prompt scaffolds ("tell them one thing that happened today") without templating the whole letter.
- No spelling correction. Invented spelling *is* the Year 1 curriculum ("spell words by identifying sounds in them and representing the sounds with a letter or letters").

### Offline library

**Evidence says.** Reading connected text every day is rated **Moderate Evidence** by WWC `[GUID]`. Decodable texts give g = 0.20 word reading / g = 0.30 decoding and should be *combined with* other material `[META]`. Technology-enhanced storybooks beat plain adult reading by g+ = 0.17 comprehension / g+ = 0.20 expressive vocabulary — **but only when multimedia is congruent with the text; hotspots, embedded games and dictionaries were distracting** `[META]`. Congruent motion in illustrations guides attention to comprehension-relevant regions `[QE]`. Intrinsic reading motivation predicts reading amount and competence; extrinsic does not `[SR]`. DfE requires decodable books matched to the phonics taught so far `[GUID]`.

**Design it like this.**
- **Two clearly separate shelves.** (1) *Books I can read* — decodable, filtered by a phonics phase the parent sets once, no untaught GPCs. (2) *Books to me* — anything, no decodability constraint, richer language than the child can decode. Both are necessary; conflating them wastes both.
- Read-aloud narration with congruent illustration and optional word highlighting. **Zero hotspots. Zero embedded mini-games. Zero tap-the-word dictionaries.** This is the clearest single design instruction the meta-analytic evidence gives.
- Gentle, congruent motion in illustrations is *supported*, not merely tolerated — it guides attention. Bouncing decorative animation is not.
- Child chooses the book. Choice is the autonomy lever and it is free.
- Track nothing publicly. No "books read" counter, no reading streak — extrinsic reading motivation is the dimension that predicts *worse* outcomes.

### Additional activities the evidence supports that are missing from the list

1. **A "read to me / I read to you" recording loop.** The child records themselves reading a decodable book; it lands in the journal; a family member can hear it. This combines daily connected-text reading (WWC Moderate), an authentic audience (EEF), and a social-interaction pillar — at almost no engineering cost beyond what letters-to-family already needs.
2. **A number-sense / subitising activity built to the actual ELG.** The EYFS Number ELG names subitising to 5 and number bonds to 5 explicitly; almost no consumer app targets subitising directly. See §2c.
3. **Printable / unplugged companions.** The physicality effect in CT (g = 0.72 vs 0.44) and the unplugged CT meta-analysis (g = 1.03) both point the same way, and a print-and-cut sheet is the cheapest thing kidnix can ship. Also directly answers the DfE's "screens should not replace" clause.
4. **A dialogic prompt layer over the library.** The bilingual-prompt RCT showed that *embedded discussion prompts induced dialogic reading behaviour in untrained parents*. One prompt page every few spreads, phrased for the child to ask an adult, is a proven mechanism for recruiting the missing fourth pillar.
5. **An oral-storytelling activity with no writing at all.** Statutory Year 1 composition begins orally; expressive-arts ELGs are about inventing and recounting narratives. A "tell me a story" recorder with a picture prompt is developmentally *ahead* of a typing-based story tool for a 5-year-old.

---

## 4. Things NOT to do

1. **Do not invent a phonics progression.** Match a validated UK SSP scheme (parent picks; default to a Letters-and-Sounds-style phase model) and never show an untaught GPC in a decodable context. Getting this wrong actively undermines the school.
2. **Do not build hotspots, tap-to-animate objects, embedded mini-games or tap-a-word dictionaries into storybooks.** This is the most direct, best-evidenced negative finding available (Takacs et al. `[META]`; Bus et al. `[SR]`), and it is the single most common design mistake in children's reading apps.
3. **Do not build star economies, streaks, leaderboards or badge collections.** Tangible contingent rewards undermine intrinsic motivation for tasks children already find interesting `[META]`, and extrinsic reading motivation predicts *worse* reading outcomes `[SR]`. Streaks additionally conflict with bounded sessions and with a wellbeing-first product.
4. **Do not claim cognitive transfer.** Not from music (ḡ ≈ 0 `[META]`), not from coding beyond a modest and probably-inflated g = 0.47 far-transfer estimate `[META]`, not from "creativity" (the instruments cannot support the claim `[critique]`). Every such claim is a hostage to fortune and none is needed to justify the product.
5. **Do not claim to teach reading.** No product in this space has the evidence. Teach Your Monster to Read, Reading Eggs, Starfall, Khan Academy Kids and Bookbot have no published independent RCT of reading outcomes `[absent]`. kidnix should claim *practice, application and pleasure*.
6. **Do not teach home-row touch typing to 5–7 year olds.** The gain over self-taught typing is d = 0.27 at population scale `[OBS]`, no tutor has been trialled below age 8 `[absent]`, and the time is better spent on letter–sound work.
7. **Do not let software displace handwriting** — and say so explicitly to parents. The letter-learning advantage for handwriting at 4–6 is one of the better-replicated findings in this note.
8. **Do not over-engineer adaptive difficulty.** The one clean test (adaptive vs non-adaptive arms of the same reading game) found **no difference** `[RCT]`, and game-based literacy benefits have been shown to concentrate in already-strong children, widening gaps `[RCT]`.
9. **Do not design for productive failure or deliberate struggle.** No evidence base at 5–7, and it contradicts both the guidance-helps meta-analysis `[META]` and the DfE's "slow-paced, repetitive and predictable" instruction `[GUID]`.
10. **Do not position kidnix as a way to occupy or calm a child.** The DfE guidance that the EYFS framework now statutorily references is explicit that screens must not be used "to occupy children" or "manage their behaviour", because it undermines self-regulation `[GUID]`. This is a marketing constraint as much as a design one.
11. **Do not put 100+ undifferentiated activities in front of a 5-year-old.** Curate hard; hide the rest behind parent controls.
12. **Do not add background music under narration, decorative animation loops, or ambient sound competing with speech.** "Seductive details" and competing background media are named explicitly in the four-pillars review `[SR]` and in the DfE's "fast-paced, over-stimulating" warning `[GUID]`.
13. **Do not auto-correct a child's spelling.** Invented spelling is the Year 1 statutory expectation.

---

## 5. Open questions

1. **Does anything in the classroom evidence survive the move to unsupervised home use?** Every RCT cited here (ABRA, GraphoGame, the Dutch literacy game, ScratchJr studies) had a teacher present. Nobody has trialled a solo-play early-literacy tool at home with no adult. This is the largest unknown for kidnix and is not answerable from the literature.
2. **Does synchronised word highlighting actually help, on its own?** It is universal in reading apps and almost never isolated as an experimental variable. A cheap within-product A/B (highlight on/off) would contribute genuinely new evidence.
3. **Lowercase vs uppercase keycaps for early readers.** No study exists. kidnix could run the first one.
4. **Can offline ASR be made good enough for 5-year-old UK-accented speech** to support dictation without correcting spelling? Unknown, and the answer determines whether story-maker gets a dictation route or stays recording-only.
5. **Does a "reply arrives in the journal" loop measurably increase writing volume?** The purpose-and-audience mechanism is well attested in classroom writing research but has never been tested as a software feature.
6. **What is the right session length for 5–6s?** DfE says ≤1 hour/day for 2–5s in settings; Couse & Chen observed ~24 minutes of sustained engagement with 4–5 year olds. 20–25 minutes looks defensible but is an inference, not a finding.
7. **Do curated subsets outperform full suites?** The paradox-of-choice argument for pruning GCompris is plausible and untested in early years software.
8. **Does bounded-session architecture produce a spacing benefit in practice?** Structurally it should. Nobody has measured it.
9. **Does removing all extrinsic reward reduce voluntary return?** The motivation literature predicts it should not, and might help — but consumer-product experience says otherwise. This is the sharpest tension between the evidence and commercial intuition in the whole design.
10. **Where does AI belong, if anywhere?** No evidence base exists for generative AI with 5–7 year olds in 2026. The absence is itself an argument for keeping it out of v1.

---

## 6. Top 10 takeaways

1. **Match the school, don't compete with it.** UK statutory documents (EYFS ELGs, KS1 English, the Reading Framework) are specific enough to design against directly. kidnix's job is practice, application and pleasure — not first teaching.
2. **The best-evidenced digital literacy feature is narrated storybooks with congruent illustration** (g+ = 0.17 comprehension, g+ = 0.20 expressive vocabulary over ordinary adult reading). Build that well before building anything cleverer.
3. **Hotspots, embedded games and tap-a-word dictionaries in storybooks are measurably harmful** — the clearest negative finding available, and the most commonly ignored.
4. **Rewards should be informational, never controlling.** Show what the child made and what they can now do. No stars, streaks, leaderboards or badge economies.
5. **Purpose and audience are the motivational engine for writing at 5–7.** Letters to family is, on the evidence, the strongest concept in the kidnix activity list — provided the reply comes back.
6. **Guidance helps at every age and helps youngest learners most** (d ≈ 0.50–0.71). Scaffold heavily and fade deliberately. Do not design for productive struggle at this age.
7. **Typing at 5–7 means finding keys, not touch typing.** No UK requirement, no RCT below age 8, and formal training buys only d = 0.27 at population scale. Protect handwriting and say so to parents.
8. **Tangible and unplugged beat screen-only for computational thinking** (g = 0.72 vs 0.44; unplugged g = 1.03). Ship printable companions — they are cheap and they are the better-evidenced half.
9. **Claim less than you could.** Music transfer is null. "Increases creativity" is unmeasurable. No early-reading app has a published independent RCT. Honest, narrow claims are also more defensible and more trustworthy.
10. **The fourth pillar — social interaction — is kidnix's structural weakness, and it is engineerable.** Embedded dialogic prompts induced better outcomes without training parents at all. Design moments that recruit an adult: show-someone, send-to-someone, record-for-someone. The DfE's statutory screen-use guidance now effectively requires it.

---

## 7. Full source list

### Statutory and official curriculum documents (UK)

1. DfE — [Early Years Foundation Stage statutory framework for group and school-based providers](https://www.gov.uk/government/publications/early-years-foundation-stage-framework--2) (applies from 1 September 2026). ELGs for Literacy, Mathematics, Expressive Arts and Design; characteristics of effective teaching and learning; statutory cross-reference to screen-use guidance. `[CURR]`
2. DfE — [Help for early years providers: Children's screen use](https://help-for-early-years-providers.education.gov.uk/safeguarding-and-welfare/screen-use). `[GUID]`
3. DfE — [National curriculum in England: English programmes of study](https://www.gov.uk/government/publications/national-curriculum-in-england-english-programmes-of-study/national-curriculum-in-england-english-programmes-of-study). `[CURR]`
4. DfE — [National curriculum in England: Computing programmes of study](https://www.gov.uk/government/publications/national-curriculum-in-england-computing-programmes-of-study). `[CURR]`
5. DfE — [National curriculum in England: Mathematics programmes of study](https://www.gov.uk/government/publications/national-curriculum-in-england-mathematics-programmes-of-study). `[CURR]`
6. DfE — [The Reading Framework](https://www.gov.uk/government/publications/the-reading-framework-teaching-the-foundations-of-literacy) (July 2021, updated September 2023). `[GUID]`
7. Francis et al. — [Curriculum and Assessment Review final report: *Building a world-class curriculum for all*](https://assets.publishing.service.gov.uk/media/690b96bbc22e4ed8b051854d/Curriculum_and_Assessment_Review_final_report_-_Building_a_world-class_curriculum_for_all.pdf), DfE, November 2025. `[CURR]`
8. NCCE — [Teach Computing Curriculum, Key Stage 1](https://teachcomputing.org/curriculum/key-stage-1), incl. Year 1 *Creating media – Digital writing*. `[CURR]`
9. NCETM — [Numberblocks at home classroom resources](https://www.ncetm.org.uk/classroom-resources/ey-numberblocks-at-home/). `[CURR]`
10. NGA/CCSSO — [Common Core State Standards for English Language Arts](https://corestandards.org/wp-content/uploads/2023/09/ELA_Standards1.pdf) (W.K.6–W.6.6 keyboarding progression). `[CURR]`
11. ISTE — [Standards for Students](https://iste.org/standards/students). `[GUID]`

### Evidence-panel guidance

12. EEF — [Improving Literacy in Key Stage 1](https://educationendowmentfoundation.org.uk/education-evidence/guidance-reports/literacy-ks-1) (2nd edition; [full text](https://files.eric.ed.gov/fulltext/ED612212.pdf)). `[GUID]`
13. EEF — [Improving Mathematics in the Early Years and Key Stage 1](https://d2tic4wvo1iusb.cloudfront.net/production/eef-guidance-reports/early-maths/EEF_Maths_EY_KS1_Guidance_Report.pdf). `[GUID]`
14. EEF — [Using Digital Technology to Improve Learning](https://educationendowmentfoundation.org.uk/education-evidence/guidance-reports/digital) and the Teaching & Learning Toolkit "Digital technology" strand. `[GUID]`
15. IES/WWC — [Foundational Skills to Support Reading for Understanding in Kindergarten Through 3rd Grade](https://ies.ed.gov/ncee/wwc/PracticeGuide/21). `[GUID]`
16. IES/WWC — [Teaching Elementary School Students to Be Effective Writers](https://ies.ed.gov/ncee/wwc/PracticeGuide/17). `[GUID]`
17. IES/WWC — [Teaching Math to Young Children](https://ies.ed.gov/ncee/wwc/PracticeGuide/18). `[GUID]`
18. IES/WWC — [Building Blocks intervention report](https://files.eric.ed.gov/fulltext/ED635243.pdf) (2023). `[META]`
19. NAEYC & Fred Rogers Center — [Technology and Interactive Media as Tools in Early Childhood Programs](https://www.naeyc.org/sites/default/files/globally-shared/downloads/PDFs/resources/topics/PS_technology_WEB.pdf). `[GUID]`

### Meta-analyses and systematic reviews

20. Kim, Gilbert, Yu & Gale (2021) — [Measures Matter: A Meta-Analysis of the Effects of Educational Apps on Preschool to Grade 3 Children's Literacy and Math Skills](https://doi.org/10.1177/23328584211004183), *AERA Open*. 36 studies, 285 ES, +0.31 SD. `[META]`
21. Griffith, Hagan, Heymann, Heflin & Bagner (2020) — [Apps As Learning Tools: A Systematic Review](https://doi.org/10.1542/peds.2019-1579), *Pediatrics*. 35 of 1,447 studies. `[SR]`
22. Takacs, Swart & Bus (2015) — [Benefits and Pitfalls of Multimedia and Interactive Features in Technology-Enhanced Storybooks](https://doi.org/10.3102/0034654314566989), *RER*. 43 studies, 2,147 children. `[META]`
23. Bus, Takacs & Kegel (2015) — [Affordances and limitations of electronic storybooks](https://doi.org/10.1016/j.dr.2014.12.004), *Developmental Review*. `[SR]`
24. Clark, Tanner-Smith & Killingsworth (2016) — [Digital Games, Design, and Learning](https://doi.org/10.3102/0034654315582065), *RER*. `[META]`
25. Wouters, van Nimwegen, van Oostendorp & van der Spek (2013) — [A meta-analysis of the cognitive and motivational effects of serious games](https://doi.org/10.1037/a0031311), *JEP*. `[META]`
26. Scherer, Siddiq & Sánchez Viveros (2018) — [The cognitive benefits of learning computer programming: A meta-analysis of transfer effects](https://doi.org/10.1037/edu0000314), *JEP*. 105 studies, 539 ES. `[META]`
27. Scherer, Siddiq & Sánchez Viveros (2020) — [A meta-analysis of teaching and learning computer programming](https://doi.org/10.1016/j.chb.2020.106349), *CHB*. `[META]`
28. Lu et al. (2023) — [Fostering computational thinking through unplugged activities: systematic review and meta-analysis](https://doi.org/10.1186/s40594-023-00434-7), *IJ STEM Education*. `[META]`
29. Murphy Odo (2024) — [The use of decodable texts in the teaching of reading: a meta-analysis](https://onlinelibrary.wiley.com/doi/10.1111/lit.12368), *Literacy*. 16 studies. `[META]`
30. Outhwaite, Early, Herodotou & Van Herwegen (2023) — [Can Maths Apps Add Value to Learning? A Systematic Review](https://repec-cepeo.ucl.ac.uk/cepeow/cepeowp23-02.pdf), UCL CEPEO WP 23-02. 50 studies, 23,981 children. `[SR]`
31. Nelson & McMaster (2019) — [The effects of early numeracy interventions: a meta-analysis](https://doi.org/10.1037/edu0000334), *JEP*. `[META]`
32. Schneider et al. (2017) — [Associations of non-symbolic and symbolic numerical magnitude processing with mathematical competence](https://doi.org/10.1111/desc.12372), *Developmental Science*. 284 ES, N = 17,201. `[META]`
33. Szűcs & Myers (2017) — [A critical analysis of design, facts, bias and inference in the approximate number system training literature](https://doi.org/10.1016/j.tine.2016.11.002). `[SR]`
34. Carbonneau, Marley & Selig (2013) — [A meta-analysis of the efficacy of teaching mathematics with concrete manipulatives](https://doi.org/10.1037/a0031084), *JEP*. 55 studies, N = 7,237. `[META]`
35. Fyfe, McNeil, Son & Goldstone (2014) — [Concreteness fading in mathematics and science instruction](https://eric.ed.gov/?id=EJ1036777). `[SR]`
36. Steenbergen-Hu & Cooper (2013) — [A meta-analysis of the effectiveness of intelligent tutoring systems on K–12 students' mathematical learning](https://doi.org/10.1037/a0032447), *JEP*. `[META]`
37. Ma, Adesope, Nesbit & Liu (2014) — [Intelligent tutoring systems and learning outcomes: a meta-analysis](https://doi.org/10.1037/a0037123), *JEP*. `[META]`
38. Kluger & DeNisi (1996) — [The effects of feedback interventions on performance](https://doi.org/10.1037/0033-2909.119.2.254), *Psychological Bulletin*. 607 ES. `[META]`
39. Wisniewski, Zierer & Hattie (2020) — [The power of feedback revisited](https://doi.org/10.3389/fpsyg.2019.03087), *Frontiers in Psychology*. 435 studies. `[META]`
40. Deci, Koestner & Ryan (2001) — [Extrinsic Rewards and Intrinsic Motivation in Education: Reconsidered Once Again](https://doi.org/10.3102/00346543071001001), *RER*. `[META]`
41. Lazonder & Harmsen (2016) — [Meta-Analysis of Inquiry-Based Learning: Effects of Guidance](https://doi.org/10.3102/0034654315627366), *RER*. 72 studies. `[META]`
42. Cepeda, Pashler, Vul, Wixted & Rohrer (2006) — [Distributed practice in verbal recall tasks](https://doi.org/10.1037/0033-2909.132.3.354), *Psychological Bulletin*. 839 assessments. `[META]`
43. Sala & Gobet (2017) — [When the music's over: Does music skill transfer to children's and young adolescents' cognitive and academic skills?](https://doi.org/10.1016/j.edurev.2016.11.005), *Educational Research Review*. `[META]`
44. Sala & Gobet (2020) — [Cognitive and academic benefits of music training with children: a multilevel meta-analysis](https://doi.org/10.3758/s13421-020-01060-2), *Memory & Cognition*. N = 6,984, k = 254. `[META]`
45. Codding, Burns & Lukito (2011) — [Meta-analysis of mathematic basic-fact fluency interventions](https://doi.org/10.1111/j.1540-5826.2010.00323.x). `[META]`
46. Barroso et al. (2021) — [A meta-analysis of the relation between math anxiety and math achievement](https://doi.org/10.1037/bul0000307), *Psychological Bulletin*. `[META]`
47. Papadakis et al. (2021) — [The Impact of Coding Apps to Support Young Children in Computational Thinking and Computational Fluency: A Literature Review](https://doi.org/10.3389/feduc.2021.657895). `[SR]`
48. Escueta, Quan, Nichols & Oreopoulos (2017) — [Education Technology: An Evidence-Based Review](https://doi.org/10.3386/w23744), NBER WP 23744. `[SR of RCTs]`
49. Bowers (2020) — [Reconsidering the Evidence That Systematic Phonics Is More Effective Than Alternative Methods of Reading Instruction](https://doi.org/10.1007/s10648-019-09515-y), *Educational Psychology Review*. `[SR]`
50. Wyse & Bradbury (2022) — [Reading wars or reading reconciliation?](https://doi.org/10.1002/rev3.3314), *Review of Education*. `[SR]`
51. Feng, Lindner, Ji & Joshi (2019) — [The roles of handwriting and keyboarding in writing: a meta-analytic review](https://link.springer.com/article/10.1007/s11145-017-9749-x), *Reading and Writing*. `[META]`
52. Clark (1983) — [Reconsidering Research on Learning from Media](https://doi.org/10.3102/00346543053004445), *RER*. `[SR/critique]`

### Randomised and quasi-experimental trials

53. Nunes et al. (2019) — [onebillion: EEF efficacy trial report](https://d2tic4wvo1iusb.cloudfront.net/production/documents/projects/onebillion.pdf). 113 schools, 1,089 Year 1 pupils, g = 0.24, 5 padlocks. `[RCT]`
54. Pitchford (2015) — [Development of early mathematical skills with a tablet intervention: a randomized control trial in Malawi](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2015.00485/full). `[RCT]`
55. Berkowitz et al. (2015) — [Math at home adds up to achievement in school](https://doi.org/10.1126/science.aac7427), *Science*; with [Frank's Comment](https://doi.org/10.1126/science.aad8008) and [the authors' response](https://doi.org/10.1126/science.aad8555); [Grade 3 follow-up](https://doi.org/10.1037/xge0000490). `[RCT + critique]`
56. Savage et al. (2013) — [A (Pan-Canadian) cluster randomized control effectiveness trial of the ABRACADABRA web-based literacy program](https://doi.org/10.1037/a0031025), *JEP*. 1,067 children. `[RCT]`
57. Piquette, Savage & Abrami (2014) — [A cluster randomized control field trial of ABRACADABRA: replication and extension](https://doi.org/10.3389/fpsyg.2014.01413). d = +0.52 to +0.66. `[RCT]`
58. Solheim, Frijters, Lundetræ & Uppstad (2018) — [Effectiveness of an early reading intervention in a semi-transparent orthography](https://doi.org/10.1016/j.learninstruc.2018.05.004), *Learning and Instruction*. Adaptive vs non-adaptive: no difference. `[RCT]`
59. van Rijthoven et al. (2023) — [Dynamic assessment of the effectiveness of digital game-based literacy training in beginning readers](https://doi.org/10.7717/peerj.15499), *PeerJ*. 247 Grade 1 children. `[RCT]`
60. Ríos-López et al. (2021) — [Neurocognitive Predictors of Response to Intervention With GraphoGame Rime](https://doi.org/10.3389/feduc.2021.639294). UK cohort, 398 children. `[RCT]`
61. Siegler & Ramani (2008, [2009](https://siegler.tc.columbia.edu/wp-content/uploads/2019/02/sieg-ram09.pdf)); [Ramani & Siegler (2008), *Child Development*](https://doi.org/10.1111/j.1467-8624.2007.01131.x) — linear number board games. `[RCT, small]`
62. Schacter et al. (2016), [*Early Education & Development*](https://doi.org/10.1080/10409289.2015.1057462); Schacter & Jo (2017), [*MERJ*](https://doi.org/10.1007/s13394-017-0203-9) — Math Shelf. `[RCT, developer-run]`
63. Decker-Woodrow et al. (2023) — [The Impacts of Three Educational Technologies on Algebraic Understanding](https://doi.org/10.1177/23328584231165919), *AERA Open*. N = 1,850. `[RCT]`
64. Mehr, Schachner, Katz & Spelke (2013) — [Two Randomized Trials Provide No Consistent Evidence for Nonmusical Cognitive Benefits of Brief Preschool Music Enrichment](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0082007), *PLoS ONE*. `[RCT]`
65. Zhang et al. (2022) — [The role of bilingual discussion prompts in shared E-book reading](https://doi.org/10.1016/j.compedu.2022.104622), *Computers & Education*. 107 dyads. `[RCT]`
66. Kiefer et al. (2015) — [Handwriting or Typewriting? The Influence of Pen- or Keyboard-Based Writing Training on Reading and Writing Performance in Preschool Children](https://doi.org/10.5709/acp-0178-7). `[RCT]`
67. Mayer et al. (2019) — [Handwriting or Typewriting? … kindergarteners](https://pmc.ncbi.nlm.nih.gov/articles/PMC6987467/), *Frontiers in Psychology*. n = 147. `[RCT-style training study]`
68. James & Engelhardt (2012) — [The effects of handwriting experience on functional brain development in pre-literate children](https://can.lab.indiana.edu/publications/pub-files/2012-james-engelhardt.pdf), *Trends in Neuroscience and Education*. `[QE, fMRI]`
69. Kersey & James (2013) — [Brain activation patterns resulting from learning letter forms through active self-production and passive observation](https://doi.org/10.3389/fpsyg.2013.00567). `[QE]`
70. Longcamp, Zerbato-Poudou & Velay (2005) — [The influence of writing practice on letter recognition in preschool children](https://doi.org/10.1016/j.actpsy.2004.10.019), *Acta Psychologica*. `[experiment]`
71. Seyll & Content (2021) — [Are Letters Processed as Motor Programs? … handwriting vs typing vs composition](https://doi.org/10.3389/fpsyg.2021.726454). Mechanism dissent. `[experiment]`
72. Wiley & Rapp (2021) — [The Effects of Handwriting Experience on Literacy Learning](https://journals.sagepub.com/doi/abs/10.1177/0956797621993111), *Psychological Science*. `[RCT, adults]`
73. Ose Askvik, van der Weel & van der Meer (2020) — [The Importance of Cursive Handwriting Over Typewriting for Learning in the Classroom](https://doi.org/10.3389/fpsyg.2020.01810). Small-N EEG. `[QE]`; see also [Pinet & Longcamp's 2024 critique](https://doi.org/10.3389/fpsyg.2024.1517235).
74. McGlashan et al. (2017) — [The effect of playing computer typing games on manual dexterity in children](https://pmc.ncbi.nlm.nih.gov/articles/PMC5716426/). n = 28 randomised, ages 8–10. `[RCT]`
75. Dhakal, Feit, Kristensson & Oulasvirta (2018) — [Observations on Typing from 136 Million Keystrokes](https://acris.aalto.fi/ws/portalfiles/portal/21495207/ELEC_Dhakal_et_al_Observations_CHI2018.pdf), CHI. 168,000 participants; trained vs untrained d = 0.27. `[OBS]`
76. Feit, Weir & Oulasvirta (2016) — [How We Type: Movement Strategies and Performance in Everyday Typing](https://dl.acm.org/doi/10.1145/2858036.2858233), CHI. `[OBS]`
77. Couse & Chen (2010) — [A Tablet Computer for Young Children? Exploring Its Viability for Early Childhood Education](https://files.eric.ed.gov/fulltext/EJ898529.pdf), *JRTE*. 41 children aged 3.1–6.3. `[QE]`
78. Anthony et al. (2016) — [Interaction and recognition challenges in interpreting children's touch and gesture input on mobile devices](https://doi.org/10.1145/2858036.2858200), CHI. `[QE]`
79. Kaminski & Sloutsky (2013) — [Extraneous perceptual information interferes with children's acquisition of mathematical knowledge](https://eric.ed.gov/?id=EJ1007940), *JEP*. `[experiment]`
80. Pugnali, Sullivan & Bers (2017) — [The Impact of User Interface on Young Children's Computational Thinking](https://doi.org/10.28945/3768). ScratchJr vs KIBO, n = 28. `[QE]`
81. Di Lieto et al. (2023) — [Combined Unplugged and Educational Robotics Training to Promote Computational Thinking and Cognitive Abilities in Preschoolers](https://doi.org/10.3390/educsci13090858). `[RCT]`
82. Bers et al. (2023) — [Coding as another language: Research-based curriculum for early childhood computer science](https://doi.org/10.1016/j.ecresq.2023.05.002), *ECRQ*. `[QE]`
83. Unahalekhaka & Bers (2021) — [Taking coding home: analysis of ScratchJr usage in home and school settings](http://dx.doi.org/10.1007/s11423-021-10011-w). 4,352,802 sessions. `[OBS]`
84. Lipowski, Pyc, Dunlosky & Rawson (2016) — [Retrieval-Based Learning: Positive Effects of Retrieval Practice in Elementary School Children](https://doi.org/10.3389/fpsyg.2016.00350). `[QE]`
85. Sumner & Connelly (2018) — [Exploring individual and gender differences in early writing performance](https://doi.org/10.1007/s11145-018-9859-0). 116 UK children aged 5:0–6:7. `[OBS]`
86. Dockrell, Lindsay & Connelly (2009) — [The Impact of Specific Language Impairment on Adolescents' Written Text](https://doi.org/10.1177/001440290907500403). Handwriting fluency constrains composition. `[OBS]`
87. Frontiers in Psychology (2022) — [finger vs stylus vs pen and children's drawing originality](https://doi.org/10.3389/fpsyg.2022.806093). 69 children. `[QE]`
88. Sturges (2023) — [Child-led photography in preschool place research](http://dx.doi.org/10.1080/03004430.2023.2235908), *Early Child Development and Care*. `[QUAL]`
89. Mackenzie & Veresov (2013) — [How drawing can support writing acquisition](https://doi.org/10.1177/183693911303800404), *AJEC*. `[QUAL]`
90. Educ. Sci. (2025) — [Empirical test of Lowenfeld's drawing stages in 3–5 year olds](https://doi.org/10.3390/educsci15060681). 218 drawings. `[QE]`

### Theory, design frameworks and critique

91. Hirsh-Pasek, Zosh, Golinkoff, Gray, Robb & Kaufman (2015) — [Putting Education in "Educational" Apps: Lessons From the Science of Learning](https://doi.org/10.1177/1529100615569721), *Psychological Science in the Public Interest*. The four pillars. `[SR]`
92. Kirschner, Sweller & Clark (2006) — [Why Minimal Guidance During Instruction Does Not Work](https://doi.org/10.1207/s15326985ep4102_1), *Educational Psychologist*. `[SR]`
93. Schiefele, Schaffner, Möller & Wigfield (2012) — [Dimensions of Reading Motivation and Their Relation to Reading Behavior and Competence](https://doi.org/10.1002/rrq.030), *RRQ*. `[SR]`
94. Resnick (2017) — [*Lifelong Kindergarten*](https://direct.mit.edu/books/book/3134/Lifelong-KindergartenCultivating-Creativity), MIT Press; and Resnick & Rosenbaum, [*Designing for Tinkerability*](https://web.media.mit.edu/~mres/papers/designing-for-tinkerability.pdf). `[RATIONALE]`
95. Vossoughi, Hooper & Escudé (2016) — [Making Through the Lens of Equity and Justice](https://doi.org/10.17763/0017-8055.86.2.206), *Harvard Educational Review*. `[critique]`
96. Zeng, Proctor & Salvendy (2011) — [Can Traditional Divergent Thinking Tests Be Trusted in Measuring and Predicting Real-World Creativity?](https://doi.org/10.1080/10400419.2011.545713) `[critique]`
97. Krath, Schürmann & von Korflesch (2021) — [Revealing the theoretical basis of gamification](https://doi.org/10.1016/j.chb.2021.106963), *CHB*. 118 theories. `[SR]`
98. Kapur — [Classroom-based Experiments in Productive Failure](https://escholarship.org/uc/item/7761h4h2). `[QE]`
99. Boaler — [*Fluency Without Fear*](https://www.youcubed.org/evidence/fluency-without-fear/) (youcubed), and its underlying citation [Ramirez, Gunderson, Levine & Beilock (2013)](https://doi.org/10.1080/15248372.2012.664593), which is correlational. `[opinion; underlying study OBS]`

### Product and vendor sources (no independent evidence located)

100. [Teach Your Monster to Read](https://www.teachyourmonster.org/teach-your-monster-to-read/) — Roehampton-developed, evidence-informed, no published independent RCT. `[VENDOR]`
101. [GCompris](https://gcompris.net/index-en.html) — 100+ activities, ages 2–10; site makes no evaluation claim; no RCT located. `[VENDOR/absent]`
102. [Chrome Music Lab](https://musiclab.chromeexperiments.com/About/); [Sugar Labs TamTam](https://wiki.sugarlabs.org/go/Activities/TamTam) — no published evaluation. `[VENDOR/RATIONALE]`
103. [KAZ Type](https://kaz-type.com/product/children) — strong unevidenced efficacy claims. `[VENDOR]`
104. [Google — why Chromebook keyboards are lowercase](https://blog.google/products-and-platforms/devices/chromebooks/chromebooks-lowercase-keyboard/) — UX rationale, no pedagogical evidence. `[RATIONALE]`
105. [DragonBox Algebra Challenge](https://dragonbox.com/about/algebra-challenge) — no control group, no pre/post, not peer reviewed. `[VENDOR]`
106. [Evidence for ESSA: ST Math](https://www.evidenceforessa.org/program/st-math-spatial-temporal-math/) and [Khan Academy](https://www.evidenceforessa.org/program/khan-academy/) ("No studies met inclusion requirements"). `[META/absent]`
107. [WestEd ST Math evaluation](https://www.wested.org/resource/st-math-evaluation/). `[QE]`
108. [onebillion evidence page](https://onebillion.org/impact/evidence/). `[VENDOR over genuine studies]`

---

*Compiled for the kidnix project, 22 August 2026. Where an effect size is quoted, the study design and sample size are given so that the reader can discount appropriately. Where no evidence exists, this note says so rather than substituting plausible reasoning for data — the absences (typing tutors under 8, lowercase keycaps, GCompris, Teach Your Monster, most music and drawing software) are as decision-relevant as the positive findings.*
