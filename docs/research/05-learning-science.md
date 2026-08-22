# 05 — Learning science for 4–8 year olds, as it applies to software

*Research note for the kidnix project. Compiled 22 August 2026.*

---

## 1. Scope & method

**Question.** What is actually evidence-backed about how 4–8 year olds (UK Reception / Year 1 / Year 2, centred on 5–6) learn, and what does that imply for the design of kidnix's activities?

**Sources.** ~100 distinct sources, prioritised in this order: meta-analyses and systematic reviews; RCTs; statutory and evidence-panel documents (DfE, EEF, IES/What Works Clearinghouse); smaller quasi-experimental and qualitative work; and — clearly marked — vendor claims and design rationale where no independent evidence exists. Retrieved via OpenAlex, Crossref, Europe PMC, Semantic Scholar, gov.uk, EEF and IES, and read in full where reachable.

**Evidence tags** used inline: `[META]` meta-analysis · `[SR]` systematic review · `[RCT]` randomised trial · `[QE]` quasi-experimental · `[OBS]` observational · `[QUAL]` small qualitative · `[GUID]` expert-panel guidance from a formal evidence review · `[CURR]` statutory curriculum · `[VENDOR]` maker's own unverified claim · `[RATIONALE]` design reasoning with no empirical test · `[absent]` searched for, not found.

**Three standing caveats.**

1. **Media-comparison studies are weak evidence.** "App versus no app" confounds the software with extra instructional time, novelty and adult attention. Richard Clark's [1983 argument](https://doi.org/10.3102/00346543053004445) — media are "mere vehicles that deliver instruction" — still constrains what any "digital technology works!" headline is worth `[SR]`. The useful questions are *which design features*, *for which children*, *replacing what*.
2. **Effect sizes here are inflated by small samples, researcher-made outcome measures and publication bias.** Treat anything above g ≈ 0.8 from a handful of small studies as provisional.
3. **kidnix is not a school intervention.** Almost every good study below had a teacher present. kidnix runs at home, usually without an adult alongside. That gap is the biggest threat to transferring these findings and it recurs throughout.

**Assumptions** (flagged because they shape the recommendations): UK families; the child's school does the systematic phonics teaching; kidnix's job is *practice, application, creation and pleasure*, not first teaching; sessions are bounded (20–40 min); no internet, store or feed; a parent is reachable but usually not co-seated.

---

## 2. Findings by domain

### 2a. Literacy

#### The UK baseline is not negotiable

England's statutory position is specific enough to design against directly, and a UK product that contradicts it will be rejected by parents and teachers.

- **EYFS (Reception).** The [statutory framework applying from 1 September 2026](https://www.gov.uk/government/publications/early-years-foundation-stage-framework--2) `[CURR]` sets the Word Reading ELG as: "Say a sound for each letter in the alphabet and at least 10 digraphs; Read words consistent with their phonic knowledge by sound-blending; Read aloud simple sentences and books that are consistent with their phonic knowledge, including some common exception words." The Writing ELG: "Write recognisable letters, most of which are correctly formed; Spell words by identifying sounds in them and representing the sounds with a letter or letters; Write simple phrases and sentences that can be read by others."
- **KS1 English** `[CURR]` requires Year 1 pupils to "apply phonic knowledge and skills as the route to decode words", and to compose by "saying out loud what they are going to write about; composing a sentence orally before writing it."
- **The [DfE Reading Framework](https://www.gov.uk/government/publications/the-reading-framework-teaching-the-foundations-of-literacy)** (2021, updated 2023) `[GUID]` pushes fidelity to a single validated systematic synthetic phonics programme, decodable books matched to the phonics taught so far, and daily story time. It says essentially nothing about digital tools.

**Consequence: kidnix must not invent its own phonics progression, and must never show a child a word containing a grapheme–phoneme correspondence (GPC) they may not have been taught.** Showing "night" to a Reception child in week 4 actively undermines the school's programme.

#### Does systematic phonics work?

The [WWC practice guide *Foundational Skills to Support Reading for Understanding in K–3*](https://ies.ed.gov/ncee/wwc/PracticeGuide/21) `[GUID]` rates two of four recommendations **Strong Evidence**: "Develop awareness of the segments of sounds in speech and how they link to letters" (17 studies) and "Teach students to decode words, analyze word parts, and write and recognize words" (18 studies). "Ensure that each student reads connected text every day" is **Moderate** (22 studies). Academic language / vocabulary is only **Minimal** — a useful corrective to the assumption that vocabulary apps are obviously good.

Against that, [Bowers (2020)](https://doi.org/10.1007/s10648-019-09515-y) `[SR]` reviewed 12 meta-analyses and argued phonics' superiority over alternatives is not established, and [Wyse & Bradbury (2022)](https://doi.org/10.1002/rev3.3314) `[SR]` synthesised 55 trials and criticised England's single-method policy. Neither argues for whole language; both argue for **phonics plus meaning, from the start**. So: practise GPCs *and* always land in a real sentence within the same activity — never a pure isolated-grapheme drill loop.

#### Decodable text: real but modest

[Murphy Odo's 2024 meta-analysis](https://onlinelibrary.wiley.com/doi/10.1111/lit.12368) `[META]` pooled 16 experimental studies (821 screened): **g = 0.20** word reading (95% CI 0.07–0.31), **g = 0.30** pseudoword decoding (0.15–0.45), with moderate-to-serious risk of bias in most. Decodables help, are not sufficient alone, and belong alongside other text. The WWC's operational steps are narrower and more usable: have children read decodable words "in isolation and in text", and introduce essential non-decodable words as whole words while "limiting the number… because learning them holistically places considerable demands on students' memory" `[GUID]`.

#### Read-aloud and narration: the best-evidenced digital literacy feature

[Takacs, Swart & Bus (2015)](https://doi.org/10.3102/0034654314566989) `[META, 43 studies, 2,147 children]` is the single most design-relevant finding in this note:

- Small but significant **additional** benefit of technology over ordinary adult storybook reading: **g+ = 0.17** story comprehension, **g+ = 0.20** expressive vocabulary.
- **Multimedia matching the story — animated pictures, music, congruent sound effects — was beneficial.**
- **Interactive elements — hotspots, embedded games, dictionaries — were distracting**, especially for at-risk children.

[Bus, Takacs & Kegel (2015)](https://doi.org/10.1016/j.dr.2014.12.004) `[SR]` reach the same split: congruent multimedia helps integrate verbal and non-verbal information; extraneous interactivity taxes working memory. Eye-tracking shows [motion in illustrations reliably attracts 4–6 year olds' attention](https://doi.org/10.3389/fpsyg.2016.01591) `[QE]` and, when matched to the text, guides them to comprehension-relevant regions.

Two dissents keep this honest: [simple irrelevant interaction was not worse than relevant](https://doi.org/10.3389/fpsyg.2018.02733) `[RCT]` when it was only a non-disruptive page-turn tap; and [*All Tapped Out*](https://doi.org/10.3389/fpsyg.2017.00578) `[QE]` found compulsive tapping mainly in 2-year-olds with low self-regulation, much less at 4–6. Reconciliation: **interaction that interrupts meaning is bad; trivial non-disruptive interaction is neutral; risk falls with age.**

On synchronised **word highlighting** specifically, the direct evidence is far thinner than its ubiquity suggests — it is almost always bundled inside "narration" conditions rather than isolated. Treat it as `[RATIONALE]` consistent with the multimedia-congruence finding, not as proven.

#### Phonics games with actual trial evidence

- **GraphoGame** is the best-evidenced of the genre, and instructively inconsistent. The [Norwegian group-randomised trial](https://doi.org/10.1016/j.learninstruc.2018.05.004) `[RCT, 744 screened, 140 at-risk]` found significant reading and spelling impact — but **no difference between adaptive and non-adaptive versions**. The [Portuguese trial](https://doi.org/10.17239/jowr-2020.12.01.02) `[RCT, n=45]` showed spelling and phonological-awareness benefits. A [Polish crossover trial](https://doi.org/10.17239/l1esll-2013.01.05) `[RCT]` found **no** advantage over a maths game. The UK GraphoGame Rime cohort (398 children, 6–7) is described in [Ríos-López et al.](https://doi.org/10.3389/feduc.2021.639294) `[RCT]`. Net: real effects, strongest on the most proximal outcomes, weakest on fluency.
- **ABRACADABRA (ABRA)** has two Canadian cluster RCTs: the [pan-Canadian trial](https://doi.org/10.1037/a0031025) `[RCT, 1,067 children]` and its [replication](https://doi.org/10.3389/fpsyg.2014.01413) `[RCT, 203 children, 10–12h]`, which found **d = +0.66 letter–sound knowledge, +0.52 phonological blending, +0.52 word reading**. Both delivered ABRA as *whole-class teacher-led instruction*, not solo play.
- A [Dutch/Flemish cluster RCT](https://doi.org/10.7717/peerj.15499) `[RCT, 247 Grade 1 children]` improved letter knowledge classroom-wide, but the fluency benefit concentrated in children who already had strong phonological awareness — **the game widened rather than narrowed the gap**.
- **Teach Your Monster to Read** was developed with University of Roehampton academics `[VENDOR]`. Despite its reputation, **no published independent RCT of its effect on reading outcomes surfaced** `[absent]`. It is evidence-*informed*, not evidence-*proven*. **Reading Eggs, Starfall, Khan Academy Kids and Bookbot**: likewise no independent early-reading RCT located `[absent]`.

**The honest claim kidnix can make is "this practises what your school is teaching, in a way children want to do" — not "this teaches your child to read."**

#### Handwriting vs typing at 5–7

Genuinely contested, with overreach on both sides.

*For handwriting:* [Kiefer et al.](https://doi.org/10.5709/acp-0178-7) `[RCT]` — 16 matched letter-learning sessions with German kindergarteners; the pen group beat the keyboard group. [James & Engelhardt](https://can.lab.indiana.edu/publications/pub-files/2012-james-engelhardt.pdf) `[QE, fMRI]` — in five-year-olds, the "reading circuit" was recruited "only after handwriting—not after typing or tracing experience". [Kersey & James](https://doi.org/10.3389/fpsyg.2013.00567) `[QE]` — active writing recruited the sensorimotor letter-perception network in 7-year-olds; watching an adult write did not. [Mayer et al.](https://pmc.ncbi.nlm.nih.gov/articles/PMC6987467/) `[RCT, n=147, 7 weeks]` is best-powered and most nuanced: the pencil group led on letter recognition and visuo-spatial skills, **but keyboard training beat stylus-on-tablet for word writing and reading**, and stylus-on-glass was the *worst* condition.

*Against a simple "handwriting wins":* [Seyll & Content](https://doi.org/10.3389/fpsyg.2021.726454) `[experiment]` found visual *analysis* of letter structure — without graphomotor action — matched handwriting and beat typing, implying the mechanism may be forced visual analysis rather than motor production. The widely-cited [EEG studies](https://doi.org/10.3389/fpsyg.2020.01810) `[QE]` used 12-year-olds and adults, n ≈ 24, measuring brain correlates rather than learning; [Pinet & Longcamp (2024)](https://doi.org/10.3389/fpsyg.2024.1517235) push back on over-reading them. [Feng et al.'s meta-analysis](https://link.springer.com/article/10.1007/s11145-017-9749-x) `[META]` gives handwriting fluency ES 0.300 and **keyboarding fluency 0.550** for writing quality — **transcription automaticity in either mode is the mechanism.**

The reconciliation: **handwriting is the better route for learning letter forms at 4–6; the keyboard is the better route for composition volume once letters are known**, because transcription cost throttles young writers ([Dockrell et al.](https://doi.org/10.1177/001440290907500403); [Sumner & Connelly](https://doi.org/10.1007/s11145-018-9859-0) `[OBS]`). The EEF frames transcription as including keyboards — pupils "must learn to form letters and spell words correctly… **and use a keyboard**" `[GUID]` — and the [WWC writing guide](https://ies.ed.gov/ncee/wwc/PracticeGuide/17) `[GUID]` rates building "handwriting, spelling, sentence construction, **typing, and word processing**" as **Moderate Evidence**.

**kidnix should not try to replace handwriting, should not claim to teach letter formation, and should treat the keyboard as a composition aid — and say all three to parents explicitly.**

#### Dictation for emergent writers

Direct trial evidence with 5–7 year olds is sparse `[absent]`, but the theoretical case is strong: Berninger's simple view of writing and [McCutchen's review](https://doi.org/10.17239/jowr-2011.03.01.3) `[SR]` both hold that transcription consumes working memory that would otherwise go to ideas. The KS1 curriculum already institutionalises it, requiring Year 1 pupils to compose "a sentence orally before writing it" `[CURR]`, and the EEF treats adult scribing as a standard scaffold `[GUID]`.

Two hard constraints: **general ASR is poor on 5-year-old UK-accented speech**, and an offline on-device model will be worse; and transcribing speech into *correctly spelled* text deletes the invented-spelling practice the curriculum requires.

#### What makes writing motivating for 5–7s

The EEF is direct: "Achieving the necessary quantity of practice requires pupils to be motivated and fully engaged in improving their writing", and names the mechanism — "Writing requires the consideration of purpose and audience" `[GUID]`. [Schiefele et al.'s review](https://doi.org/10.1002/rrq.030) `[SR]` finds intrinsic motivation dimensions (curiosity, involvement) predict reading behaviour and competence, while extrinsic ones (competition, recognition, grades, compliance) contribute weakly or negatively. **A real recipient beats a star rating.**

---

### 2b. Keyboarding

**The most important finding is an absence.** The KS1 [computing programme of study](https://www.gov.uk/government/publications/national-curriculum-in-england-computing-programmes-of-study) `[CURR]` contains *typing*, *keyboard*, *keyboarding* and *touch typing* **zero times**; the nearest statement is "use technology purposefully to create, organise, store, manipulate and retrieve digital content". The [Curriculum and Assessment Review final report (DfE, November 2025)](https://assets.publishing.service.gov.uk/media/690b96bbc22e4ed8b051854d/Curriculum_and_Assessment_Review_final_report_-_Building_a_world-class_curriculum_for_all.pdf) `[CURR]` — 196 pages, revised curriculum due 2027 — also contains zero instances of "keyboard", "handwriting" or "touch typing". **No UK policy body is currently proposing keyboarding at KS1.**

What English schools actually do comes from the non-statutory [NCCE Teach Computing Curriculum](https://teachcomputing.org/curriculum/key-stage-1) `[CURR]`, whose Year 1 unit runs: *Exploring the keyboard → Adding and removing text → Exploring the toolbar → Making changes to text → Explaining my choices → Pencil or keyboard.* That is **key-location familiarisation plus a modality comparison, explicitly not touch-typing instruction.**

The US anchors sit above this band. [Common Core](https://corestandards.org/wp-content/uploads/2023/09/ELA_Standards1.pdf) `[CURR]` says nothing about keyboarding for K–2; it first appears at **W.3.6** (Grade 3, age 8–9), with a page-per-sitting fluency target at W.4.6. The [ISTE Standards for Students](https://iste.org/standards/students) `[GUID]` mention keyboarding nowhere.

**Is there an age floor?** No. The claim that under-7s "can't reach the home row" appears to be an **untested practitioner heuristic** — a search for children's hand-anthropometry-versus-key-pitch studies returned nothing `[absent]`. The one genuine RCT nearby, [McGlashan et al. (2017)](https://pmc.ncbi.nlm.nih.gov/articles/PMC5716426/) `[RCT]`, used ages 8–10, randomised 28 children, and measured *manual dexterity* rather than typing speed.

**Touch typing vs hunt-and-peck.** [Dhakal, Feit, Kristensson & Oulasvirta (CHI 2018)](https://acris.aalto.fi/ws/portalfiles/portal/21495207/ELEC_Dhakal_et_al_Observations_CHI2018.pdf) `[OBS, 168,000 participants]`: formally trained typists managed 54.4 WPM against 49.0 untrained — **d = 0.27, a small effect** — with near-identical error rates. Mean finger count was 6.95; finger count correlated with speed only moderately (r = 0.38). [Feit et al.](https://dl.acm.org/doi/10.1145/2858036.2858233) `[OBS]` found untrained typists reaching speeds "comparable to, or greater than, that of touch typists". **No study shows childhood hunt-and-peck impairs later touch-typing acquisition** `[absent]`.

**Typing tutors have essentially no evidence here.** BBC **Dance Mat Typing** has been defunct since Flash retired on 31 December 2020 and was never rebuilt. TypingClub, Typing.com, Tux Typing, Doorway Online and Nessy Fingers have no reachable efficacy studies `[absent]`; [KAZ Type](https://kaz-type.com/product/children) claims it teaches touch typing "in minutes instead of hours" citing nothing `[VENDOR]`. **There is no RCT of any typing tutor with children aged 5–7.** Nor is there any study of **lowercase vs uppercase keycaps** for early readers `[absent]`, despite the real tension (phonics teaches lowercase first; keycaps are engraved uppercase) — [Google's rationale for the lowercase Chromebook keyboard](https://blog.google/products-and-platforms/devices/chromebooks/chromebooks-lowercase-keyboard/) is pure UX reasoning `[RATIONALE]`.

---

### 2c. Maths

#### What the UK asks for

The [EYFS Number ELG](https://www.gov.uk/government/publications/early-years-foundation-stage-framework--2) `[CURR]` is unusually concrete: "deep understanding of numbers to 10, including the composition of each number; **subitise (recognise quantities without counting) up to 5**; automatically recall… number bonds up to 5 (including subtraction facts) and some number bonds to 10, including double facts." The 2021 reform *dropped* Shape/Space/Measure and *added* subitising — a target almost no consumer app addresses. [KS1 maths](https://www.gov.uk/government/publications/national-curriculum-in-england-mathematics-programmes-of-study) `[CURR]` then wants counting to 100, number bonds to 20, and ×2/5/10 in Year 2, within a mastery frame.

#### The field-level picture is sobering

[Outhwaite, Early, Herodotou & Van Herwegen (2023)](https://repec-cepeo.ucl.ac.uk/cepeow/cepeowp23-02.pdf) `[SR]`: **50 studies, 77 apps, 23,981 children aged 4–7**, 20 RCTs. 92% report *some* positive effect — but only 14 of 50 used a standardised outcome, effect sizes ranged d = 0.05 to 3.34, and **9 of the 11 studies with d ≥ 1 had n < 250**. Only **three** studies combined an RCT, n > 250 *and* a standardised measure. Usage–effect correlation r = .30, n.s. Of 5 studies with delayed post-tests, **2 showed fade-out within 1–2 months**. *Rule of thumb: treat any maths-app effect above ~0.5 on a researcher-made test as an artefact until proven otherwise.*

#### The apps with real evidence

- **onebillion** is the best-evidenced early-years maths app, and was tested in England. The [EEF efficacy trial](https://d2tic4wvo1iusb.cloudfront.net/production/documents/projects/onebillion.pdf) `[RCT]` randomised **113 schools, 1,089 Year 1 pupils** in the lower half of the class to 12 weeks × 4 × 30 min of TA-supervised use: **g = 0.24 (95% CI 0.12–0.36), "+3 months", 5/5 padlocks**. But the FSM subgroup was **g = −0.10, "−2 months"**. Critically for kidnix: pupils did better **when the supervising TA saw their role as teaching rather than merely supervising**. [Pitchford's Malawi RCT](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2015.00485/full) `[RCT, n=283]` found larger effects but in one school with a tablet-delivered post-test favouring the tablet group.
- **Bedtime Math.** [Berkowitz et al. 2015, *Science*](https://doi.org/10.1126/science.aac7427) `[RCT, 587 first-graders]` is much weaker than its reputation: the ITT effect for children of high-maths-anxious parents was **b = 5.25, p = 0.048**; no effect for low-anxiety parents (p = .79); the **anxiety × app interaction was only p = 0.06**; and the headline dose–response is correlational within the randomised arm. [Frank's Comment](https://doi.org/10.1126/science.aad8008) `[critique]` argues the subgroup split looks data-dependent, and **no independent replication exists**. The transferable insight is not "maths apps work" but that *a shared parent–child maths conversation, structured by a prompt, moved the outcome*.
- **Math Shelf** has two RCTs (n=100, d=0.57; n=433, d=0.94) `[RCT]` — but the developer is first author on both and the outcomes are researcher-developed.
- **ST Math** (Grades 2–5, only the top edge here): [Evidence for ESSA](https://www.evidenceforessa.org/program/st-math-spatial-temporal-math/) `[META]` pools 4 studies and **346,248 students** to **+0.07**; a [WestEd matched-schools study](https://www.wested.org/resource/st-math-evaluation/) `[QE, 474 schools]` gave 0.17 SD. **This is what honest edtech looks like at scale.**
- **DragonBox.** The much-cited Washington "Algebra Challenge" (4,192 students, "92.9% mastery") has **no control group, no pre/post test, no peer review**, and "mastery" means in-game equations `[VENDOR]`. Real evidence exists only for DragonBox 12+ with Grade 7s: [Decker-Woodrow et al. 2023](https://doi.org/10.1177/23328584231165919) `[RCT, N=1,850]`, **g = 0.24–0.27** — and notably an "immediate feedback" condition was **not** better than no feedback (g = 0.12, n.s.). **No study of DragonBox Numbers or of DragonBox with 4–8 year olds exists** `[absent]`.
- **Khan Academy Kids**: [Evidence for ESSA lists "No studies met inclusion requirements"](https://www.evidenceforessa.org/program/khan-academy/) `[absent]`. **GCompris**: only small descriptive classroom reports `[absent]`. **Numberblocks, Zorbit's, Teachley, Motion Math**: no outcome evaluation for 4–8 `[absent]`.

#### What actually works

The [WWC guide *Teaching Math to Young Children*](https://ies.ed.gov/ncee/wwc/PracticeGuide/18) `[GUID]` rates only "teach number and operations using a developmental progression" as **Moderate**; its other four recommendations are **Minimal**. The [WWC Building Blocks report](https://files.eric.ed.gov/fulltext/ED635243.pdf) `[META, 3 cluster-RCTs, N=3,221]` gives pooled **ES 0.58**, with documented fade-out to 0.22–0.51 by Grade 1. The [EEF's early maths guidance](https://d2tic4wvo1iusb.cloudfront.net/production/eef-guidance-reports/early-maths/EEF_Maths_EY_KS1_Guidance_Report.pdf) `[GUID]` recommends manipulatives and representations, dedicated time, building on prior knowledge, and targeted support — and specifically endorses storybooks and board games. [Nelson & McMaster](https://doi.org/10.1037/edu0000334) `[META, 33 studies]` find **g = 0.63** overall but **g = 0.35 on distal measures**.

**Linear number board games** are the cheapest well-supported mechanic: Siegler & Ramani's series `[RCT, small]` found number-line linearity **d ≈ 1.6** after ~1 hour of "The Great Race", and [magnitude comparison d = 0.99, counting 0.74, numeral ID 0.69 in 124 Head Start children](https://doi.org/10.1111/j.1467-8624.2007.01131.x), holding at 9 weeks with decay; a [linear board beat a circular one, d = 0.65](https://siegler.tc.columbia.edu/wp-content/uploads/2019/02/sieg-ram09.pdf). Caveats: experimenter-delivered 1:1, proximal outcomes, and [independent replications](https://doi.org/10.1016/j.jecp.2020.105060) find counting but not magnitude gains.

#### Two negative findings that should change the design

1. **Do not build approximate-number-system "dot cloud" training.** [Schneider et al.](https://doi.org/10.1111/desc.12372) `[META, 284 ES, N=17,201]`: symbolic comparison correlates with maths more strongly (r = .30) than non-symbolic (r = .24). [Szűcs & Myers](https://doi.org/10.1016/j.tine.2016.11.002) `[SR]`: "no conclusive evidence that specific ANS training improves symbolic arithmetic". [Szkudlarek et al.](https://doi.org/10.1016/j.cognition.2020.104521) `[RCT, N=318]` failed to replicate transfer.
2. **Perceptual richness hurts.** [Kaminski & Sloutsky (2013)](https://eric.ed.gov/?id=EJ1007940) `[experiment, 6–8 year olds]` found graphs made of countable pictures caused children to count the pictures and miss the strategy — "extraneous perceptual information substantially attenuated learning". [Carbonneau et al.](https://doi.org/10.1037/a0031084) `[META, 55 studies, N=7,237]` find manipulatives help most for retention, least for transfer, moderated by guidance and perceptual richness. [Fyfe et al.](https://eric.ed.gov/?id=EJ1036777) `[SR]` recommend **concreteness fading**. **Ten-frames and plain counters, not cartoon cupcakes.**

#### Adaptivity, feedback and timed practice

Adaptive tutoring in K–12 maths is weaker than marketed: [Steenbergen-Hu & Cooper](https://doi.org/10.1037/a0032447) `[META, 34 samples]` found **g = 0.01–0.09**, *smaller for low achievers and for year-long use*. On feedback, [Kluger & DeNisi](https://doi.org/10.1037/0033-2909.119.2.254) `[META, 607 ES]` found d = .41 overall but **more than a third of feedback interventions *reduced* performance** — the harmful ones directing attention to the self rather than the task; [Wisniewski, Zierer & Hattie](https://doi.org/10.3389/fpsyg.2019.03087) `[META, 435 studies]` find d = 0.48 with task and process *information* content mattering most.

On timed practice: Boaler's widely-repeated claim that timed testing causes maths anxiety `[opinion]` rests on a [correlational study](https://doi.org/10.1080/15248372.2012.664593) that never manipulated or measured timed tests. **No experimental evidence that timed practice causes maths anxiety in young children was found** `[absent]`; conversely [Codding, Burns & Lukito](https://doi.org/10.1111/j.1540-5826.2010.00323.x) `[META]` found "drill and practice with modeling produced the largest effect sizes" for fact fluency. Honest position: **brief, low-stakes, self-competitive retrieval practice is supported; public high-stakes timed tests are unsupported in either direction.**

---

### 2d. Computational thinking

**The KS1 curriculum is the design brief** `[CURR]`: understand that "programs execute by following precise and unambiguous instructions"; **create and debug simple programs**; use logical reasoning to predict behaviour. Note that *debugging* is statutory at age 5–7, and that nothing requires a text language, a screen, or a specific tool.

**Does programming transfer?** Partially. [Scherer, Siddiq & Sánchez Viveros' meta-analysis of transfer](https://doi.org/10.1037/edu0000314) `[META, 105 studies, 539 ES]`: overall **g = 0.49**, near transfer **g = 0.75**, far transfer **g = 0.47**, with gains in creative thinking, mathematical skills, metacognition, spatial skills and reasoning. Their [companion meta-analysis](https://doi.org/10.1016/j.chb.2020.106349) `[META, 139 interventions]` found **g = 0.81** for learning programming itself, **g = 0.44** for visualisation and **g = 0.72** for *physicality* interventions — **tangible/embodied approaches outperform purely on-screen ones**. Two qualifications: these are dominated by older learners, and far-transfer claims in this literature have a bad historical record (the 1980s Logo transfer claims largely failed to replicate). Treat g = 0.47 as an upper bound.

**ScratchJr** is the reference implementation, built by [Bers' DevTech group](https://sites.bc.edu/devtech/papers/) for 5–7 year olds who cannot yet read fluently, and framed as expressive literacy rather than vocational training ([*Coding as Another Language*](https://doi.org/10.1016/j.ecresq.2023.05.002) `[QE]`). [Papadakis's review of coding apps](https://doi.org/10.3389/feduc.2021.657895) `[SR, 21 studies]` concludes all four reviewed apps positively affect CT skills, but **none demonstrably supports "computational fluency"** — expressive, self-directed creation — except ScratchJr, credited specifically for its **sandbox approach**. [Pugnali, Sullivan & Bers](https://doi.org/10.28945/3768) `[QE, n=28, ages 4–7]` found **tangible interfaces produced more positive interpersonal behaviour; the graphical interface produced better concept mastery.** Note that much widely-cited "ScratchJr impact" work is [Google Analytics usage data](https://doi.org/10.28945/4437) `[OBS]`, not outcome data.

**Unplugged and tangible approaches are, if anything, better evidenced.** [Lu et al.'s systematic review and meta-analysis](https://doi.org/10.1186/s40594-023-00434-7) `[META]` (49 studies reviewed; 13 meta-analysed) found **Hedges' g = 1.028** (95% CI 0.641–1.415) — large, though from few studies. A [cluster-RCT with 47 preschoolers](https://doi.org/10.3390/educsci13090858) `[RCT]` combining unplugged coding and robotics found transfer to plugged coding and to executive functions. [Bee-Bot work](https://doi.org/10.3389/feduc.2022.757627) `[QE]` shows scaffolding type moderates sequencing and decomposition gains — the adult matters more than the robot.

---

### 2e. Creativity, arts, music and photography

#### Drawing

Lowenfeld's stages still frame the field, and a [2025 study of 218 drawings by 3–5 year olds](https://doi.org/10.3390/educsci15060681) `[QE]` confirmed the *sequence* (ρ = .661) while showing the *ages* drift widely. A 5-year-old does not want realism; they want **a recognisable symbol they can name and tell you about**.

The key study is [Couse & Chen's videotaped observation of 41 children aged 3.1–6.3 drawing on stylus tablets](https://files.eric.ed.gov/fulltext/EJ898529.pdf) `[QE, no control]`: **75.6% reached the highest coded level in the very first session** (four planned acclimatisation sessions were cut to one), rising to 98%; teachers rated **66% of tablet drawings as typical of the child's paper work and 20% above expectation**; sustained attention averaged 24.1 min, but 3-year-olds fell to 13 min while 4s and 5s held ~23.7 min (p < .01) — **engagement rises sharply between 3 and 4**. Demand stayed high after two months, ruling out pure novelty.

A [finger-vs-stylus-vs-pen experiment with 69 children](https://doi.org/10.3389/fpsyg.2022.806093) `[QE]` found originality of finger 4.00 > stylus 3.69 > pen 2.30 (ηp² = .57), finger beating pen significantly for the youngest. **Do not gate drawing behind stylus ownership.**

Do stamps and fill-buckets suppress creative effort? **No controlled study exists either way** `[absent]`. The defensible argument for a sparse palette is different: [Anthony et al.](https://doi.org/10.1145/2858036.2858200) `[QE]` found **interface complexity measurably degrades children's touch accuracy** through visual salience. [NAEYC](https://www.naeyc.org/sites/default/files/globally-shared/downloads/PDFs/resources/topics/PS_technology_WEB.pdf) `[GUID]` adds the boundary: touchscreen drawing "can add to children's graphic representational experiences" but "should not replace paints, markers, crayons".

**Drawing as a route into writing** is well supported: [Mackenzie & Veresov](https://doi.org/10.1177/183693911303800404) `[QUAL]` argue drawing alongside writing "allows children to create meaningful texts of a complexity that they may not be able to create using conventional print forms alone" — supplying planning and rehearsal that emergent writers cannot hold in working memory. **A canvas that accepts a picture plus a caption is doing real literacy work; one that only exports a PNG is not.**

#### Music: the transfer claim is dead; make music anyway

- [Sala & Gobet (2017)](https://doi.org/10.1016/j.edurev.2016.11.005) `[META, 38 studies, >3,000 children]`: d = 0.16 overall, **shrinking as study quality rose**.
- [Sala & Gobet (2020)](https://doi.org/10.3758/s13421-020-01060-2) `[META, N=6,984, k=254]` is decisive: "Once the quality of study design is controlled for, the overall effect of music training programs is null (ḡ ≈ 0)." The small positive effect appears **only** without random allocation and active controls.
- [Mehr, Schachner, Katz & Spelke](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0082007) `[RCT, n=29 and 45, 4-year-olds]`: no consistent transfer; apparent differences "would not have survived correction for multiple comparisons".

Mehr et al. supply the honest justification themselves: the benefit of music education "is self-evident: to improve the musical skills and repertoire." **That is sufficient.**

What a 4–6 year old can do: in a call-and-response drumming study, **84% held a steady beat, 79% of improvised responses were exactly four beats, 86% started on beat 1** `[QUAL, n=6]`. Brophy's three-year collection of 558 improvisations from 62 children used alto xylophone **in C pentatonic** within an Orff rondo `[OBS]`. **Four-beat phrases and a pentatonic constraint are the operating envelope.**

On "no wrong notes": **no controlled evidence that constrained scales improve creative output** `[absent]`. It is Orff convention — Orff xylophones have removable bars precisely so the fourth and seventh can be taken out — with a plausible mechanism and a strong practical track record. Build it; label it `[RATIONALE]`. [Chrome Music Lab](https://musiclab.chromeexperiments.com/About/), Incredibox, Groove Pizza, Bandlab and [Sugar's TamTam suite](https://wiki.sugarlabs.org/go/Activities/TamTam) all have strong design rationale and **zero peer-reviewed evaluation with under-8s** `[VENDOR/absent]`.

#### Photography

The strong work is methodological. [Sturges](http://dx.doi.org/10.1080/03004430.2023.2235908) `[QUAL, 20 children aged 3–4]` found child-led photography "offered children the opportunity to participate, express themselves, and share their place stories", and that *relationships* dominated what they chose to photograph. [Cappello's photo-elicitation work](https://eric.ed.gov/?q=Cappello+photography+data+generation) `[QUAL, 40 children aged 6–9]` showed children say far more when interviewed *about their own photographs* than when questioned directly. This sits inside Clark & Moss's Mosaic Approach `[GUID]`. **There is no RCT showing cameras improve language outcomes** `[absent]`; the claim that survives is that *a photograph gives a 5-year-old a concrete referent to talk and write about* — the same mechanism as drawing-before-writing.

#### The maker framing: good theory, weak evidence

Papert's constructionism and Resnick's **four Ps — Projects, Passion, Peers, Play** `[GUID]` are the right design frame, and the most operationally useful text is [*Designing for Tinkerability*](https://web.media.mit.edu/~mres/papers/designing-for-tinkerability.pdf) `[RATIONALE]`: **immediate feedback** ("a very short interval of time between making a change and seeing its effect"), **fluid experimentation** ("easy to get started… without spending a lot of time setting up"), and **open exploration** — plus the warning that institutions often "introduce making into the curriculum in a way that saps all the spirit from the activity". But [Vossoughi, Hooper & Escudé](https://doi.org/10.17763/0017-8055.86.2.206) `[critique]` advance "a critique of branded, culturally normative definitions of making" and caution "against their uncritical adoption into the educational sphere", and systematic reviews find the makerspace literature dominated by small qualitative studies with almost nothing on young children `[SR]`. **Use the design principles; don't cite the movement as evidence.**

Similarly on creativity claims: [Zeng, Proctor & Salvendy](https://doi.org/10.1080/10400419.2011.545713) `[critique]` catalogue six weaknesses of divergent-thinking tests including "poor predictive, ecological, and discriminant validities". **kidnix should not claim to increase creativity** — only to give children materials, time and no wrong answers.

**Digital storytelling** shows consistent speaking-skill gains in a [PRISMA review of 45 studies](https://doi.org/10.3390/su13179829) `[SR]` — but almost entirely at primary level and above. ScratchJr usage analysis of [4,352,802 sessions](http://dx.doi.org/10.1007/s11423-021-10011-w) `[OBS]` found home users spent more time on advanced blocks **and on the paint editor** than school users — an argument for shipping a good drawing tool *inside* the coding activity. **Book Creator, Storybird and Puppet Pals have marketing, not evaluations** `[VENDOR]`.

---

### 2f. General learning principles

#### The four pillars

[Hirsh-Pasek, Zosh, Golinkoff, Gray, Robb & Kaufman (2015)](https://doi.org/10.1177/1529100615569721) `[SR]` remains the best design filter. An app is educational when it supports learning that is **active** (minds-on, not just fingers-on), **engaged** (attention held *by* the content, not stolen by it — they warn specifically against "seductive details" and background media competing for attention), **meaningful** (connected to what the child knows), and **socially interactive** — all "within the context of a supported learning goal". Their content analysis of top-selling children's apps found few met the bar.

This maps well onto kidnix's stated design. **The weakest pillar for kidnix is social interaction**, because the product is for a child alone. That is the pillar to engineer around deliberately.

#### The DfE now effectively regulates this

Since the current EYFS framework, England has a **statutory cross-reference** to [DfE guidance on children's screen use](https://help-for-early-years-providers.education.gov.uk/safeguarding-and-welfare/screen-use) `[GUID]`, which providers "must have regard to":

- Under 2: avoid screens. **Ages 2–5: "screen time should be limited to 1 hour a day, less if possible."**
- **"You should not allow children to access or use screens alone or with other children without adult co-engagement."**
- Content should be "slow-paced, repetitive and predictable" and **"advert-free"**; avoid "fast-paced, over-stimulating" material with excessive cuts, movement or flashing.
- Screens must not be used "for routine management or to calm children", "to occupy children", or to "manage their behaviour" — this "undermines self-regulation".

This is the closest thing to a UK regulatory design spec for kidnix, and kidnix satisfies several clauses by construction.

#### Rewards, stars and badges

[Deci, Koestner & Ryan](https://doi.org/10.3102/00346543071001001) `[META]` established that **tangible rewards contingent on engagement, completion or performance substantially undermine intrinsic motivation** for already-interesting tasks — while **verbal, informational, non-controlling feedback does not undermine and often enhances it.** The line is *controlling* versus *informational*. [Schiefele et al.](https://doi.org/10.1002/rrq.030) `[SR]` find the same split in reading. Gamification research is mostly theoretical: [Krath et al.'s systematic review](https://doi.org/10.1016/j.chb.2021.106963) `[SR]` found **118 different theories** invoked across the field, and **no meta-analysis isolating badges/stars/points for under-8s exists** `[absent]`.

**Show a child what they made and what they can now do, not how many stars they have.** Progress artefacts are informational; leaderboards, streaks and star economies are controlling — and streaks pair badly with bounded sessions.

#### Guidance, scaffolding, failure and adaptivity

[Lazonder & Harmsen's meta-analysis](https://doi.org/10.3102/0034654315627366) `[META, 72 studies]` found **guidance helps at every age** (d = 0.66 learning activities, 0.71 performance success, 0.50 learning outcomes) and that **younger learners need more explicit guidance**. [Kirschner, Sweller & Clark](https://doi.org/10.1207/s15326985ep4102_1) `[SR]` make the cognitive-load case: guidance only stops helping once learners can guide themselves — which a 5-year-old never can. The EEF operationalises fading: modelling and structured support "gradually reduced as a child progresses until the child is capable of completing the activity independently" `[GUID]`.

**Productive failure** is a poor fit. [Kapur's classroom experiments](https://escholarship.org/uc/item/7761h4h2) `[QE]` use secondary students learning formal concepts, and the mechanism requires enough prior knowledge to generate candidate solutions. **No evidence base at 5–7** `[absent]`, and the DfE's "slow-paced, repetitive and predictable" points the other way. Design for low-stakes failure that is immediately recoverable, not deliberate struggle.

**Adaptive difficulty** is weaker in practice than in theory. The cleanest test is the [Norwegian reading RCT](https://doi.org/10.1016/j.learninstruc.2018.05.004), where the *only* difference between arms was adaptivity — and there was **no significant difference**. The [Dutch literacy game trial](https://doi.org/10.7717/peerj.15499) found benefits concentrated in already-strong children. Do it simply and cheaply; it can widen gaps.

#### Spacing, retrieval, and co-play

[Cepeda et al.'s synthesis of 839 assessments across 317 experiments](https://doi.org/10.1037/0033-2909.132.3.354) `[META]` makes distributed practice one of psychology's most robust findings, and it replicates in children ([Lipowski et al.](https://doi.org/10.3389/fpsyg.2016.00350) `[QE, n=88]`). **kidnix's bounded-session architecture is an asset here** — short daily sessions revisiting yesterday's GPCs or number facts are structurally spaced practice. Make the revisit automatic and invisible.

On co-play: every framework says an adult alongside materially improves learning, and [Zhang et al.'s RCT of dialogic prompt pages in shared e-book reading](https://doi.org/10.1016/j.compedu.2022.104622) `[RCT, 107 dyads]` is the transferable case — the prompts improved story comprehension and retelling **without training the parents at all**. kidnix cannot conjure a parent, but it can **design moments that recruit one**.

---

### 2g. Recent systematic reviews and meta-analyses

**The headline number, and why to discount it.** [Kim, Gilbert, Yu & Gale (2021), *Measures Matter*, *AERA Open*](https://doi.org/10.1177/23328584211004183) `[META]` synthesised **36 studies and 285 effect sizes** for preschool–Grade 3 literacy and maths apps: **mean weighted effect +0.31 SD**, comparable in both subjects. But three significant moderators each cut the number down — effects were larger **for preschool than K–3**, larger **for researcher-developed than standardised outcomes**, and larger **for constrained than unconstrained skills**.

Read together: *apps reliably move narrow, bounded, masterable skills (letter–sound knowledge, numeral identification, counting) as measured by tests written by the app's builders; they move broad, open-ended competence much less.* That constrained-skills zone is exactly where kidnix should aim — phonics practice, key location, number bonds — and not "learns to read".

[Griffith, Hagan, Heymann, Heflin & Bagner (2020), *Pediatrics*](https://doi.org/10.1542/peds.2019-1579) `[SR]` screened 1,447 studies and included 35 with children under 6: "Evidence of a learning benefit… **particularly for early mathematics learning in typically developing children**", no effect for social-communication apps in ASD, and the caveat that "Risk of bias was unclear for many studies because of inadequate reporting."

**Game-based learning: design matters more than medium.** [Clark, Tanner-Smith & Killingsworth (2016), *RER*](https://doi.org/10.3102/0034654315582065) `[META]` usefully separates two questions — **media comparisons** (game vs non-game): **g = 0.33** (k = 57); **value-added comparisons** (augmented vs standard game design): **g = 0.34** (k = 20). Improving a game's *design* buys as much as adding a game at all; their conclusion highlights "the key role of design beyond medium." [Wouters et al.](https://doi.org/10.1037/a0031311) `[META, k=77, N=5,547]` found **d = 0.29** for serious games versus conventional instruction, with larger gains "when the game was supplemented with other instruction methods, when multiple training sessions were involved, and when players worked in groups" — all three pointing away from solo, one-off, standalone play. They also found **little support for the assumption that serious games are more motivating.**

[Escueta, Quan, Nichols & Oreopoulos's NBER review](https://doi.org/10.3386/w23744) `[SR of RCTs]` reaches the same shape: computer-assisted learning shows the most consistent effects, especially in maths, and especially where it provides personalised practice rather than substituting for teaching. The EEF's **Toolkit "Digital technology" strand** and its guidance report [*Using Digital Technology to Improve Learning*](https://educationendowmentfoundation.org.uk/education-evidence/guidance-reports/digital) `[GUID]` say the same: consider how technology will improve teaching *before* introducing it; use it to improve explanation and modelling, to increase the **quality and quantity of practice**, and to improve assessment and feedback. *(The live toolkit figures could not be retrieved — the EEF site is JavaScript-rendered and blocks automated retrieval — so verify the months'-progress figure before quoting it publicly.)*

**Three questions to ask of any edtech claim:** what was the outcome measure (researcher-made measures inflate effects); what did the control group do (no-treatment controls measure time-on-task, active controls measure design); and did the effect survive a delay (2 of 5 early-years maths follow-ups showed fade-out within two months).

---

## 3. Per-activity: "evidence says → design it like this"

### Draw / paint
*Evidence: Couse & Chen `[QE]`; finger ≥ stylus at 5–6 `[QE]`; interface complexity degrades touch accuracy `[QE]`; drawing scaffolds writing `[QUAL]`; NAEYC `[GUID]`.*

- Big canvas, ≤8 tools visible at once, large targets. Every extra palette item costs touch accuracy.
- Finger-first, stylus optional; pressure/velocity → line width where hardware allows.
- **Ship a caption field and a "tell me about it" voice recorder on every drawing.** Cheapest literacy win in the product.
- Undo and auto-save always. Never a "discard changes?" dialog — a 5-year-old cannot read it.
- Stamps and clip art one level down, not on the default surface. No grading; there is no correct drawing.

### GCompris (and the activity-suite pattern)
*Evidence: 100+ activities, ages 2–10; its own site claims no evaluation; no RCT located `[absent]`.*

- Treat it as a **curated shelf, not a whole product**. Hand-pick 12–20 activities mapped to EYFS/KS1 objectives; hide the rest behind a parent control.
- Group by what the child is *doing*, not by subject.
- Localise to en-GB and check every letter activity against a UK phonics progression before exposing it — GCompris is not built to Letters-and-Sounds phases.
- Market it as "the ones we picked", never "100 activities!".

### Keyboard game
*Evidence: no UK requirement at KS1 `[CURR]`; d = 0.27 for formal training at population scale `[OBS]`; no RCT below age 8 `[absent]`; handwriting advantage for letter learning `[QE]`.*

- **Target: find the key that makes this sound, fast.** Not home row, not WPM, not finger assignment.
- Show the **lowercase** grapheme on screen to match phonics; say the phoneme in phonics mode, letter names in a separate mode.
- Accept any finger; never scold posture. Optionally *suggest* using more fingers as a challenge, never as a gate.
- Gate on interest, not age — there is no evidenced lower bound.
- **Tell parents explicitly this does not replace handwriting, and why.** No WPM leaderboard, no streak.

### Story-maker
*Evidence: transcription cost throttles composition `[OBS]`; oral rehearsal is statutory `[CURR]`; purpose and audience are the motivational mechanism `[GUID]`; ScratchJr home users live in the paint editor `[OBS]`.*

- **Picture first, words second.** Draw or photograph, then caption. This is how the child already composes.
- **Three caption routes, child's choice:** type it, say it (audio kept as-is), or ask a grown-up to scribe. A recording is a legitimate published text at this age and it removes the transcription bottleneck entirely.
- If dictation-to-text ever ships, treat it as a draft the child fixes, and **never let it silently correct spelling** — that deletes the practice the curriculum requires. Given poor ASR on 5-year-old UK-accented speech offline, recording-as-artefact is the safer primary design.
- One-line oral rehearsal prompt: "Say your sentence out loud first."
- Finish with **publish to somebody**. A story with no reader is a worksheet.

### Music
*Evidence: transfer is null (ḡ ≈ 0) `[META]`; 4–5s hold a steady beat and phrase in fours `[QUAL]`; pentatonic is convention with no controlled evidence `[RATIONALE]`.*

- **No notation.** Pitch set constrained to a pentatonic (or diatonic with 4th and 7th removable, like an Orff xylophone). Nothing a child presses sounds wrong.
- **Loops of 4 or 8 beats.** Sound the *instant* a control is touched.
- 3–5 visible layers. A DAW timeline is the wrong metaphor.
- Record and keep — the saved song in the journal is the artefact.
- **Marketing must not claim cognitive benefit.** Claim joy and musicianship.

### Block coding
*Evidence: "create and debug" is statutory `[CURR]`; g = 0.81 on programming, g = 0.49 transfer `[META]`; physicality g = 0.72 vs screen 0.44 `[META]`; unplugged g = 1.03 `[META]`; ScratchJr's sandbox is what reviews credit `[SR]`.*

- Pictorial blocks, no reading required. 3–8 blocks is a complete program at this age.
- **Sandbox over level ladder** — the goal is a story or animation the child wanted, not a puzzle with one right answer.
- **Build and celebrate the debugging loop explicitly:** "it did something different from what you expected — let's find out why." Never show a red error.
- Put the paint editor inside the coding activity.
- **Ship printable unplugged companions** (sequence cards, floor grid, "program the grown-up"). The physicality effect is the strongest number in this domain and printing costs nothing.
- Promise "makes things happen on purpose", not "learns to code".

### Photos
*Evidence: child-led photography elicits far more talk than direct questioning `[QUAL]`; children photograph relationships `[QUAL]`; no RCT on language outcomes `[absent]`.*

- One enormous shutter target. No mode switching. No filters as a headline feature.
- **Instant visible result** — the Polaroid effect — landing straight in the journal where it can be captioned or narrated.
- No destructive delete without a grown-up. No face detection, no auto-tagging, no cloud.
- Prompt cards ("photograph something exactly your favourite colour"; "three things older than you") — photo-elicitation in product form.

### Letters to family
*Evidence: on balance **the strongest activity in the kidnix list.** Purpose and audience are the EEF's named mechanism `[GUID]`; extrinsic recognition predicts literacy weakly or negatively `[SR]`; social interaction is the four pillars' weakest link for a solo product `[SR]`; embedded prompts improved outcomes without training the adult `[RCT]`.*

- A real, named recipient from a parent-approved list. The child sees a photo and a name, never an address.
- Picture + caption + voice. A 5-year-old's letter is legitimately a drawing, three words, and a recorded "I love you Grandad."
- **Show the reply.** A one-way outbox is not an audience; the reply must come back *into the child's journal* and be announced.
- A few prompt scaffolds ("tell them one thing that happened today") without templating the letter.
- **No spelling correction** — invented spelling *is* the Year 1 curriculum.

### Offline library
*Evidence: daily connected text is **Moderate Evidence** `[GUID]`; decodables g = 0.20/0.30 `[META]`; narration beats plain adult reading g+ = 0.17/0.20 **but hotspots, games and dictionaries were distracting** `[META]`; intrinsic reading motivation predicts competence, extrinsic does not `[SR]`.*

- **Two clearly separate shelves.** (1) *Books I can read* — decodable, filtered by a phonics phase the parent sets once, no untaught GPCs. (2) *Books to me* — no decodability constraint, richer language than the child can decode. Both are necessary; conflating them wastes both.
- Narration with congruent illustration and optional word highlighting. **Zero hotspots, zero embedded mini-games, zero tap-the-word dictionaries.** This is the clearest single instruction the meta-analytic evidence gives.
- Gentle *congruent* motion in illustrations is supported, not merely tolerated. Decorative bouncing is not.
- Child chooses the book — choice is the autonomy lever and it is free.
- **No "books read" counter, no reading streak.** Extrinsic reading motivation is the dimension that predicts *worse* outcomes.

### Additional activities the evidence supports that are missing

1. **A "read to me / I read to you" recording loop.** The child records themselves reading a decodable book; it lands in the journal; family can hear it. Combines daily connected-text reading (WWC Moderate), an authentic audience (EEF) and the social-interaction pillar, at almost no cost beyond what letters-to-family already needs.
2. **A subitising / number-bonds activity built to the actual ELG.** Subitising to 5 and bonds to 5 are named in the statutory ELG and almost no consumer app targets them directly.
3. **Printable unplugged companions.** The physicality effect (g = 0.72 vs 0.44) and the unplugged CT meta-analysis (g = 1.03) both point this way, and it directly answers the DfE's "screens should not replace" clause.
4. **A dialogic prompt layer over the library.** Embedded prompts induced dialogic reading in *untrained* parents — a proven mechanism for recruiting the missing fourth pillar.
5. **An oral-storytelling activity with no writing at all.** Year 1 composition begins orally and the expressive-arts ELGs are about inventing and recounting narratives. A "tell me a story" recorder with a picture prompt is developmentally *ahead* of a typing-based story tool for a 5-year-old.

---

## 4. Things NOT to do

1. **Do not invent a phonics progression.** Match a validated UK SSP scheme and never show an untaught GPC in a decodable context. Getting this wrong undermines the school.
2. **Do not build hotspots, tap-to-animate objects, embedded mini-games or tap-a-word dictionaries into storybooks.** The most direct, best-evidenced negative finding available `[META]` — and the most common design mistake in children's reading apps.
3. **Do not build star economies, streaks, leaderboards or badge collections.** Tangible contingent rewards undermine intrinsic motivation `[META]`, and extrinsic reading motivation predicts *worse* reading `[SR]`.
4. **Do not claim cognitive transfer.** Not from music (ḡ ≈ 0), not from coding beyond a modest and probably-inflated g = 0.47, not from "creativity" (the instruments cannot bear it). Every such claim is a hostage to fortune and none is needed.
5. **Do not claim to teach reading.** No consumer product in this space has the evidence.
6. **Do not teach home-row touch typing to 5–7 year olds.** d = 0.27 at population scale, no tutor trialled below age 8, and the time is better spent on letter–sound work.
7. **Do not let software displace handwriting** — and say so to parents.
8. **Do not over-engineer adaptive difficulty.** The one clean test found **no difference**, and game benefits have been shown to concentrate in already-strong children.
9. **Do not design for productive failure or deliberate struggle.** No evidence base at 5–7, and it contradicts both the guidance-helps meta-analysis and the DfE's "slow-paced, repetitive and predictable".
10. **Do not position kidnix as a way to occupy or calm a child.** The statutorily-referenced DfE guidance forbids exactly this. A marketing constraint as much as a design one.
11. **Do not put 100+ undifferentiated activities in front of a 5-year-old.**
12. **Do not add background music under narration, decorative animation loops, or ambient sound competing with speech.** "Seductive details" and competing background media are named explicitly in both the four-pillars review and the DfE guidance.
13. **Do not auto-correct a child's spelling.**

---

## 5. Open questions

1. **Does any of the classroom evidence survive the move to unsupervised home use?** Every RCT here had a teacher present. Nobody has trialled a solo-play early-literacy tool at home. This is kidnix's largest unknown and is not answerable from the literature.
2. **Does synchronised word highlighting help on its own?** Universal in reading apps, almost never isolated as a variable. A within-product A/B would contribute genuinely new evidence.
3. **Lowercase vs uppercase keycaps for early readers.** No study exists; kidnix could run the first one.
4. **Can offline ASR handle 5-year-old UK-accented speech** well enough to support dictation without correcting spelling? The answer determines whether story-maker gets a dictation route.
5. **Does a "reply arrives in the journal" loop measurably increase writing volume?** Well attested as a classroom mechanism, never tested as a software feature.
6. **What is the right session length for 5–6s?** DfE says ≤1 hour/day for 2–5s in settings; Couse & Chen observed ~24 minutes of sustained engagement. 20–25 minutes looks defensible but is an inference.
7. **Do curated subsets outperform full suites?** Plausible and untested in early-years software.
8. **Does bounded-session architecture produce a real spacing benefit?** Structurally it should; nobody has measured it.
9. **Does removing all extrinsic reward reduce voluntary return?** The motivation literature predicts not; commercial intuition says otherwise. The sharpest tension in the whole design.
10. **Where does generative AI belong, if anywhere?** No evidence base exists for under-8s in 2026 — itself an argument for keeping it out of v1.

---

## 6. Top 10 takeaways

1. **Match the school, don't compete with it.** UK statutory documents are specific enough to design against directly. kidnix's job is practice, application and pleasure — not first teaching.
2. **The best-evidenced digital literacy feature is narrated storybooks with congruent illustration** (g+ = 0.17 comprehension, g+ = 0.20 expressive vocabulary). Build that well before anything cleverer.
3. **Hotspots, embedded games and tap-a-word dictionaries in storybooks are measurably harmful** — the clearest negative finding available, and the most commonly ignored.
4. **Rewards must be informational, never controlling.** Show what the child made and what they can now do. No stars, streaks, leaderboards or badges.
5. **Purpose and audience are the motivational engine for writing at 5–7.** Letters to family is the strongest concept in the activity list — provided the reply comes back.
6. **Guidance helps at every age and helps the youngest most** (d ≈ 0.50–0.71). Scaffold heavily, fade deliberately, and do not design for struggle.
7. **Typing at 5–7 means finding keys, not touch typing.** No UK requirement, no RCT below age 8, d = 0.27 for formal training. Protect handwriting and say so.
8. **Tangible and unplugged beat screen-only for computational thinking** (g = 0.72 vs 0.44; unplugged g = 1.03). Ship printable companions — cheap, and the better-evidenced half.
9. **Apps move constrained skills, not unconstrained ones** (Kim et al.'s moderators). Aim at phonics, key location and number bonds; do not promise comprehension or composition.
10. **Social interaction is kidnix's structural weakness, and it is engineerable.** Embedded dialogic prompts improved outcomes without training parents at all. Design moments that recruit an adult — show-someone, send-to-someone, record-for-someone. The DfE's statutory screen-use guidance now effectively requires it.

---

## 7. Full source list

### Statutory and curriculum documents

1. DfE — [EYFS statutory framework, group and school-based providers](https://www.gov.uk/government/publications/early-years-foundation-stage-framework--2) (from 1 Sep 2026) `[CURR]`
2. DfE — [Help for early years providers: Children's screen use](https://help-for-early-years-providers.education.gov.uk/safeguarding-and-welfare/screen-use) `[GUID]`
3. DfE — [National curriculum: English programmes of study](https://www.gov.uk/government/publications/national-curriculum-in-england-english-programmes-of-study/national-curriculum-in-england-english-programmes-of-study) `[CURR]`
4. DfE — [National curriculum: Computing programmes of study](https://www.gov.uk/government/publications/national-curriculum-in-england-computing-programmes-of-study) `[CURR]`
5. DfE — [National curriculum: Mathematics programmes of study](https://www.gov.uk/government/publications/national-curriculum-in-england-mathematics-programmes-of-study) `[CURR]`
6. DfE — [The Reading Framework](https://www.gov.uk/government/publications/the-reading-framework-teaching-the-foundations-of-literacy) (2021, upd. 2023) `[GUID]`
7. Francis et al. — [Curriculum and Assessment Review final report](https://assets.publishing.service.gov.uk/media/690b96bbc22e4ed8b051854d/Curriculum_and_Assessment_Review_final_report_-_Building_a_world-class_curriculum_for_all.pdf), DfE, Nov 2025 `[CURR]`
8. NCCE — [Teach Computing Curriculum, KS1](https://teachcomputing.org/curriculum/key-stage-1) `[CURR]`
9. NCETM — [Numberblocks at home](https://www.ncetm.org.uk/classroom-resources/ey-numberblocks-at-home/) `[CURR]`
10. NGA/CCSSO — [Common Core ELA Standards](https://corestandards.org/wp-content/uploads/2023/09/ELA_Standards1.pdf) `[CURR]`
11. ISTE — [Standards for Students](https://iste.org/standards/students) `[GUID]`

### Evidence-panel guidance

12. EEF — [Improving Literacy in Key Stage 1](https://educationendowmentfoundation.org.uk/education-evidence/guidance-reports/literacy-ks-1) ([full text](https://files.eric.ed.gov/fulltext/ED612212.pdf)) `[GUID]`
13. EEF — [Improving Mathematics in the Early Years and KS1](https://d2tic4wvo1iusb.cloudfront.net/production/eef-guidance-reports/early-maths/EEF_Maths_EY_KS1_Guidance_Report.pdf) `[GUID]`
14. EEF — [Using Digital Technology to Improve Learning](https://educationendowmentfoundation.org.uk/education-evidence/guidance-reports/digital) + Toolkit "Digital technology" strand `[GUID]`
15. WWC — [Foundational Skills to Support Reading for Understanding in K–3](https://ies.ed.gov/ncee/wwc/PracticeGuide/21) `[GUID]`
16. WWC — [Teaching Elementary School Students to Be Effective Writers](https://ies.ed.gov/ncee/wwc/PracticeGuide/17) `[GUID]`
17. WWC — [Teaching Math to Young Children](https://ies.ed.gov/ncee/wwc/PracticeGuide/18) `[GUID]`
18. WWC — [Building Blocks intervention report](https://files.eric.ed.gov/fulltext/ED635243.pdf) (2023) `[META]`
19. NAEYC & Fred Rogers Center — [Technology and Interactive Media as Tools in Early Childhood Programs](https://www.naeyc.org/sites/default/files/globally-shared/downloads/PDFs/resources/topics/PS_technology_WEB.pdf) `[GUID]`

### Meta-analyses and systematic reviews

20. Kim, Gilbert, Yu & Gale (2021) — [Measures Matter](https://doi.org/10.1177/23328584211004183), *AERA Open* `[META]`
21. Griffith et al. (2020) — [Apps As Learning Tools](https://doi.org/10.1542/peds.2019-1579), *Pediatrics* `[SR]`
22. Takacs, Swart & Bus (2015) — [Benefits and Pitfalls of Multimedia and Interactive Features in Technology-Enhanced Storybooks](https://doi.org/10.3102/0034654314566989), *RER* `[META]`
23. Bus, Takacs & Kegel (2015) — [Affordances and limitations of electronic storybooks](https://doi.org/10.1016/j.dr.2014.12.004) `[SR]`
24. Clark, Tanner-Smith & Killingsworth (2016) — [Digital Games, Design, and Learning](https://doi.org/10.3102/0034654315582065), *RER* `[META]`
25. Wouters et al. (2013) — [A meta-analysis of the cognitive and motivational effects of serious games](https://doi.org/10.1037/a0031311), *JEP* `[META]`
26. Scherer, Siddiq & Sánchez Viveros (2018) — [The cognitive benefits of learning computer programming](https://doi.org/10.1037/edu0000314), *JEP* `[META]`
27. Scherer et al. (2020) — [A meta-analysis of teaching and learning computer programming](https://doi.org/10.1016/j.chb.2020.106349), *CHB* `[META]`
28. Lu et al. (2023) — [Fostering computational thinking through unplugged activities](https://doi.org/10.1186/s40594-023-00434-7) `[META]`
29. Murphy Odo (2024) — [The use of decodable texts: a meta-analysis](https://onlinelibrary.wiley.com/doi/10.1111/lit.12368), *Literacy* `[META]`
30. Outhwaite et al. (2023) — [Can Maths Apps Add Value to Learning?](https://repec-cepeo.ucl.ac.uk/cepeow/cepeowp23-02.pdf), UCL CEPEO `[SR]`
31. Nelson & McMaster (2019) — [Early numeracy interventions meta-analysis](https://doi.org/10.1037/edu0000334) `[META]`
32. Schneider et al. (2017) — [Symbolic and non-symbolic magnitude processing and maths](https://doi.org/10.1111/desc.12372) `[META]`
33. Szűcs & Myers (2017) — [Critical analysis of the ANS training literature](https://doi.org/10.1016/j.tine.2016.11.002) `[SR]`
34. Carbonneau, Marley & Selig (2013) — [Teaching mathematics with concrete manipulatives](https://doi.org/10.1037/a0031084) `[META]`
35. Fyfe et al. (2014) — [Concreteness fading](https://eric.ed.gov/?id=EJ1036777) `[SR]`
36. Steenbergen-Hu & Cooper (2013) — [ITS effectiveness in K–12 maths](https://doi.org/10.1037/a0032447) `[META]`
37. Ma et al. (2014) — [Intelligent tutoring systems and learning outcomes](https://doi.org/10.1037/a0037123) `[META]`
38. Kluger & DeNisi (1996) — [Effects of feedback interventions on performance](https://doi.org/10.1037/0033-2909.119.2.254) `[META]`
39. Wisniewski, Zierer & Hattie (2020) — [The power of feedback revisited](https://doi.org/10.3389/fpsyg.2019.03087) `[META]`
40. Deci, Koestner & Ryan (2001) — [Extrinsic Rewards and Intrinsic Motivation in Education](https://doi.org/10.3102/00346543071001001) `[META]`
41. Lazonder & Harmsen (2016) — [Meta-Analysis of Inquiry-Based Learning](https://doi.org/10.3102/0034654315627366) `[META]`
42. Cepeda et al. (2006) — [Distributed practice in verbal recall tasks](https://doi.org/10.1037/0033-2909.132.3.354) `[META]`
43. Sala & Gobet (2017) — [When the music's over](https://doi.org/10.1016/j.edurev.2016.11.005) `[META]`
44. Sala & Gobet (2020) — [Cognitive and academic benefits of music training: a multilevel meta-analysis](https://doi.org/10.3758/s13421-020-01060-2) `[META]`
45. Codding, Burns & Lukito (2011) — [Maths fact fluency interventions](https://doi.org/10.1111/j.1540-5826.2010.00323.x) `[META]`
46. Barroso et al. (2021) — [Math anxiety and achievement](https://doi.org/10.1037/bul0000307) `[META]`
47. Papadakis et al. (2021) — [Coding apps and young children's CT: a literature review](https://doi.org/10.3389/feduc.2021.657895) `[SR]`
48. Escueta et al. (2017) — [Education Technology: An Evidence-Based Review](https://doi.org/10.3386/w23744), NBER `[SR]`
49. Bowers (2020) — [Reconsidering the Evidence That Systematic Phonics Is More Effective](https://doi.org/10.1007/s10648-019-09515-y) `[SR]`
50. Wyse & Bradbury (2022) — [Reading wars or reading reconciliation?](https://doi.org/10.1002/rev3.3314) `[SR]`
51. Feng, Lindner, Ji & Joshi (2019) — [Handwriting and keyboarding in writing: a meta-analytic review](https://link.springer.com/article/10.1007/s11145-017-9749-x) `[META]`
52. Clark (1983) — [Reconsidering Research on Learning from Media](https://doi.org/10.3102/00346543053004445) `[SR/critique]`
53. PRISMA review (2021) — [Digital storytelling and speaking skills](https://doi.org/10.3390/su13179829) `[SR]`

### Trials and empirical studies

54. Nunes et al. (2019) — [onebillion EEF efficacy trial](https://d2tic4wvo1iusb.cloudfront.net/production/documents/projects/onebillion.pdf) `[RCT]`
55. Pitchford (2015) — [Tablet maths intervention, Malawi](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2015.00485/full) `[RCT]`
56. Berkowitz et al. (2015) — [Math at home adds up to achievement in school](https://doi.org/10.1126/science.aac7427), *Science*; [Frank's Comment](https://doi.org/10.1126/science.aad8008); [authors' response](https://doi.org/10.1126/science.aad8555); [Grade 3 follow-up](https://doi.org/10.1037/xge0000490) `[RCT + critique]`
57. Savage et al. (2013) — [Pan-Canadian cluster RCT of ABRACADABRA](https://doi.org/10.1037/a0031025) `[RCT]`
58. Piquette, Savage & Abrami (2014) — [ABRACADABRA replication](https://doi.org/10.3389/fpsyg.2014.01413) `[RCT]`
59. Solheim et al. (2018) — [Early reading intervention, semi-transparent orthography](https://doi.org/10.1016/j.learninstruc.2018.05.004) `[RCT]`
60. van Rijthoven et al. (2023) — [Digital game-based literacy training in beginning readers](https://doi.org/10.7717/peerj.15499), *PeerJ* `[RCT]`
61. Ríos-López et al. (2021) — [GraphoGame Rime, UK cohort](https://doi.org/10.3389/feduc.2021.639294) `[RCT]`
62. Ribeiro et al. (2020) — [Portuguese GraphoGame](https://doi.org/10.17239/jowr-2020.12.01.02) `[RCT]`
63. Ramani & Siegler (2008) — [Number board games with Head Start children](https://doi.org/10.1111/j.1467-8624.2007.01131.x); [Siegler & Ramani 2009](https://siegler.tc.columbia.edu/wp-content/uploads/2019/02/sieg-ram09.pdf) `[RCT]`
64. Schacter et al. (2016), [*EE&D*](https://doi.org/10.1080/10409289.2015.1057462); Schacter & Jo (2017), [*MERJ*](https://doi.org/10.1007/s13394-017-0203-9) — Math Shelf `[RCT, developer-run]`
65. Decker-Woodrow et al. (2023) — [Impacts of three educational technologies on algebraic understanding](https://doi.org/10.1177/23328584231165919) `[RCT]`
66. Szkudlarek et al. (2020) — [Approximate arithmetic training failure to replicate](https://doi.org/10.1016/j.cognition.2020.104521) `[RCT]`
67. Mehr, Schachner, Katz & Spelke (2013) — [Two randomized trials: no consistent nonmusical benefits](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0082007) `[RCT]`
68. Zhang et al. (2022) — [Bilingual discussion prompts in shared e-book reading](https://doi.org/10.1016/j.compedu.2022.104622) `[RCT]`
69. Kiefer et al. (2015) — [Handwriting or Typewriting?](https://doi.org/10.5709/acp-0178-7) `[RCT]`
70. Mayer et al. (2019) — [Pencil vs stylus vs keyboard in kindergarteners](https://pmc.ncbi.nlm.nih.gov/articles/PMC6987467/) `[RCT-style]`
71. James & Engelhardt (2012) — [Handwriting experience and functional brain development](https://can.lab.indiana.edu/publications/pub-files/2012-james-engelhardt.pdf) `[QE, fMRI]`
72. Kersey & James (2013) — [Active self-production vs passive observation of letters](https://doi.org/10.3389/fpsyg.2013.00567) `[QE]`
73. Longcamp, Zerbato-Poudou & Velay (2005) — [Writing practice and letter recognition in preschoolers](https://doi.org/10.1016/j.actpsy.2004.10.019) `[experiment]`
74. Seyll & Content (2021) — [Are letters processed as motor programs?](https://doi.org/10.3389/fpsyg.2021.726454) `[experiment]`
75. Wiley & Rapp (2021) — [The effects of handwriting experience on literacy learning](https://journals.sagepub.com/doi/abs/10.1177/0956797621993111) `[RCT, adults]`
76. Ose Askvik, van der Weel & van der Meer (2020) — [Cursive handwriting over typewriting, HD-EEG](https://doi.org/10.3389/fpsyg.2020.01810) `[QE, small N]`; [Pinet & Longcamp critique (2024)](https://doi.org/10.3389/fpsyg.2024.1517235)
77. McGlashan et al. (2017) — [Typing games and manual dexterity in children](https://pmc.ncbi.nlm.nih.gov/articles/PMC5716426/) `[RCT]`
78. Dhakal, Feit, Kristensson & Oulasvirta (2018) — [Observations on Typing from 136 Million Keystrokes](https://acris.aalto.fi/ws/portalfiles/portal/21495207/ELEC_Dhakal_et_al_Observations_CHI2018.pdf), CHI `[OBS]`
79. Feit, Weir & Oulasvirta (2016) — [How We Type](https://dl.acm.org/doi/10.1145/2858036.2858233), CHI `[OBS]`
80. Couse & Chen (2010) — [A Tablet Computer for Young Children?](https://files.eric.ed.gov/fulltext/EJ898529.pdf), *JRTE* `[QE]`
81. Anthony et al. (2016) — [Children's touch and gesture input on mobile devices](https://doi.org/10.1145/2858036.2858200), CHI `[QE]`
82. Kaminski & Sloutsky (2013) — [Extraneous perceptual information interferes with children's maths learning](https://eric.ed.gov/?id=EJ1007940) `[experiment]`
83. Pugnali, Sullivan & Bers (2017) — [The Impact of User Interface on Young Children's Computational Thinking](https://doi.org/10.28945/3768) `[QE]`
84. Di Lieto et al. (2023) — [Combined unplugged and robotics training in preschoolers](https://doi.org/10.3390/educsci13090858) `[RCT]`
85. Bers et al. (2023) — [Coding as another language](https://doi.org/10.1016/j.ecresq.2023.05.002), *ECRQ* `[QE]`
86. Bers (2019) — [Computer Science Education in Early Childhood: The Case of ScratchJr](https://doi.org/10.28945/4437) `[OBS]`
87. Unahalekhaka & Bers (2021) — [ScratchJr usage in home and school settings](http://dx.doi.org/10.1007/s11423-021-10011-w), 4.35m sessions `[OBS]`
88. Bee-Bot scaffolding study (2023) — [Gender and scaffolding in preschool CT](https://doi.org/10.3389/feduc.2022.757627) `[QE]`
89. Lipowski, Pyc, Dunlosky & Rawson (2016) — [Retrieval practice in elementary school children](https://doi.org/10.3389/fpsyg.2016.00350) `[QE]`
90. Sumner & Connelly (2018) — [Individual and gender differences in early writing](https://doi.org/10.1007/s11145-018-9859-0) `[OBS]`
91. Dockrell, Lindsay & Connelly (2009) — [Impact of SLI on written text](https://doi.org/10.1177/001440290907500403) `[OBS]`
92. McCutchen (2011) — [From Novice to Expert: Language and Memory Processes in Writing](https://doi.org/10.17239/jowr-2011.03.01.3) `[SR]`
93. Frontiers in Psychology (2022) — [Finger vs stylus vs pen and drawing originality](https://doi.org/10.3389/fpsyg.2022.806093) `[QE]`
94. Bus group (2016) — [Motion in animated storybooks: eye-tracking](https://doi.org/10.3389/fpsyg.2016.01591) `[QE]`
95. Fletcher-Watson et al. (2019) — [Simple irrelevant eBook features are not necessarily worse](https://doi.org/10.3389/fpsyg.2018.02733) `[RCT]`
96. Russo-Johnson et al. (2017) — [All Tapped Out: touchscreen interactivity and word learning](https://doi.org/10.3389/fpsyg.2017.00578) `[QE]`
97. Sturges (2023) — [Child-led photography in preschool place research](http://dx.doi.org/10.1080/03004430.2023.2235908) `[QUAL]`
98. Cappello (2001) — [Photo-elicitation with children](https://eric.ed.gov/?q=Cappello+photography+data+generation) `[QUAL]`
99. Mackenzie & Veresov (2013) — [How drawing supports writing acquisition](https://doi.org/10.1177/183693911303800404) `[QUAL]`
100. Educ. Sci. (2025) — [Empirical test of Lowenfeld's drawing stages](https://doi.org/10.3390/educsci15060681) `[QE]`

### Theory, frameworks and critique

101. Hirsh-Pasek et al. (2015) — [Putting Education in "Educational" Apps](https://doi.org/10.1177/1529100615569721), *PSPI* — the four pillars `[SR]`
102. Kirschner, Sweller & Clark (2006) — [Why Minimal Guidance During Instruction Does Not Work](https://doi.org/10.1207/s15326985ep4102_1) `[SR]`
103. Schiefele et al. (2012) — [Dimensions of Reading Motivation](https://doi.org/10.1002/rrq.030), *RRQ* `[SR]`
104. Resnick (2017) — [*Lifelong Kindergarten*](https://direct.mit.edu/books/book/3134/Lifelong-KindergartenCultivating-Creativity); Resnick & Rosenbaum — [*Designing for Tinkerability*](https://web.media.mit.edu/~mres/papers/designing-for-tinkerability.pdf) `[RATIONALE]`
105. Vossoughi, Hooper & Escudé (2016) — [Making Through the Lens of Equity and Justice](https://doi.org/10.17763/0017-8055.86.2.206) `[critique]`
106. Zeng, Proctor & Salvendy (2011) — [Can divergent thinking tests be trusted?](https://doi.org/10.1080/10400419.2011.545713) `[critique]`
107. Krath, Schürmann & von Korflesch (2021) — [Revealing the theoretical basis of gamification](https://doi.org/10.1016/j.chb.2021.106963) `[SR]`
108. Kapur — [Classroom-based Experiments in Productive Failure](https://escholarship.org/uc/item/7761h4h2) `[QE]`
109. Boaler — [*Fluency Without Fear*](https://www.youcubed.org/evidence/fluency-without-fear/) `[opinion]`, resting on [Ramirez et al. (2013)](https://doi.org/10.1080/15248372.2012.664593) `[OBS]`
110. DevTech Research Group — [publications index](https://sites.bc.edu/devtech/papers/)

### Products with no independent evidence located

111. [Teach Your Monster to Read](https://www.teachyourmonster.org/teach-your-monster-to-read/) — Roehampton-developed, evidence-informed, no published independent RCT `[VENDOR]`
112. [GCompris](https://gcompris.net/index-en.html) — 100+ activities, ages 2–10; site makes no evaluation claim `[VENDOR/absent]`
113. [Chrome Music Lab](https://musiclab.chromeexperiments.com/About/); [Sugar Labs TamTam](https://wiki.sugarlabs.org/go/Activities/TamTam) `[VENDOR/RATIONALE]`
114. [KAZ Type](https://kaz-type.com/product/children) — strong unevidenced efficacy claims `[VENDOR]`
115. [Google: why Chromebook keyboards are lowercase](https://blog.google/products-and-platforms/devices/chromebooks/chromebooks-lowercase-keyboard/) `[RATIONALE]`
116. [DragonBox Algebra Challenge](https://dragonbox.com/about/algebra-challenge) — no control, no pre/post, not peer reviewed `[VENDOR]`
117. Evidence for ESSA — [ST Math](https://www.evidenceforessa.org/program/st-math-spatial-temporal-math/); [Khan Academy](https://www.evidenceforessa.org/program/khan-academy/) ("No studies met inclusion requirements") `[META/absent]`
118. [WestEd ST Math evaluation](https://www.wested.org/resource/st-math-evaluation/) `[QE]`
119. [onebillion evidence page](https://onebillion.org/impact/evidence/) `[VENDOR over genuine studies]`

---

*Compiled for the kidnix project, 22 August 2026. Where an effect size is quoted, the design and sample size are given so the reader can discount appropriately. Where no evidence exists, this note says so rather than substituting plausible reasoning for data — the absences (typing tutors under 8, lowercase keycaps, GCompris, Teach Your Monster, most music and drawing software, word highlighting in isolation) are as decision-relevant as the positive findings.*
