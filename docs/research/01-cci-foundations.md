# Child–Computer Interaction (CCI): State of the Art for 4–8 Year Olds

Research brief for **kidnix** — topic 01 of the research programme.
Compiled 2026-08-22. Author: research worker (Claude).

---

## 1. Scope & method

This brief covers Child–Computer Interaction (CCI) as it bears on designing an OS shell for children aged 4–8 (core 5–6), UK family context. Primary sources were read directly, not from snippets: Hourcade's *Child-Computer Interaction, 2nd ed.* (2022) in full text — the field's standard synthesis; the Hourcade/Bederson/Druin TOCHI pointing experiments; NN/g's children's UX programme; IDC proceedings and calls 2020–2026; the Fun Toolkit / Smileyometer literature including a 2025 *Interacting with Computers* re-evaluation; the TIDRC framework; Hiniker et al.'s CHI 2016 screen-transition study (from the PDF, with statistics); child-speech-recognition evidence; and CCI ethics/rights work. Claims resting on small lab studies or expert opinion are tagged **[evidence: …]**. Two assumptions: (a) kidnix runs primarily on a laptop/desktop with **mouse or trackpad and keyboard**, touchscreen secondary — this matters, because most 2015–2026 CCI empirical work is touchscreen-based while the older mouse literature is more directly applicable; (b) kidnix is a *shell*, so navigation, session structure, error recovery and instructions are ours to control. Caveat: the session's shared web-search budget was exhausted partway through, so later sources were reached by direct URL fetch, biasing 2026 coverage toward what conference indexes enumerate.

---

## 2. Key findings by theme

### 2.1 The field: IDC, its venues, and what it currently cares about

CCI has its own conference (IDC, ACM, annual since 2002, from a 2002 Eindhoven workshop run by Bekker and Markopoulos), its own journal (IJCCI), and overflow into CHI. Hourcade defines the field as "the design, evaluation, and implementation of interactive computer systems for children, and the wider impact of technology on children and society" ([Hourcade 2022](https://jphourcade.com/book/hourcade_cci_2nd_edition.pdf)) **[evidence: authoritative textbook synthesis]**. Read and Bekker's framing of what makes CCI different from adult HCI: the **rate of change of children**, the **frequent involvement of adults**, **different contexts of use**, and **contested cultural values about what is good for children**.

Recent conference themes show where attention sits:

- **IDC 2025** (Reykjavik, June 2025) took **"hope"** as its theme — explicitly framed around supporting children to remain "brave, hopeful, and kind" against a worrying world ([IDC 2025](https://idc.acm.org/2025/)). The programme skewed heavily to **AI literacy**, data literacy and agency, values-in-design, and school-age/teen participants; papers on under-8s were comparatively sparse ([IDC 2025 proceedings index](https://dblp.org/db/conf/acmidc/idc2025.html)) **[evidence: conference-programme observation]**.
- **IDC 2026** (Brighton, UK, June 2026) takes **"sustainable futures"**, with calls covering sustainability, EDI and social justice, and "designing the future of technology for and with children" ([IDC 2026](https://idc.acm.org/2026/)). Its proceedings include *ELLA: Generative AI-Powered Social Robots for Early Language Development at Home*, *Children Envision Future GenAI Chatbots that are Bounded, Helpful, and Safe*, *Where Does AI Leave a Footprint? Children's Reasoning About AI's Environmental Costs*, and *CuddleConnect: Designing Child-Initiated Emotive Communication and Mediated Hugs for Remote Parent-Child Connection* ([IDC 2026 index](https://dblp.org/db/conf/acmidc/idc2026.html)).

**Implication for kidnix:** the field in 2020–2026 is preoccupied with AI, sustainability, rights and adolescents. There is a genuine gap in fresh empirical work on plain interface mechanics for 4–8s. Much of the best evidence for our specific problem is 2004–2019 and still uncontradicted. Do not mistake "old" for "superseded."

**A note of caution about generalisation.** Hourcade explicitly warns that expertise can override age: young children who are experts in a domain can perform at older children's levels, and results from studies in the 1990s do not straightforwardly transfer to today's much more technology-experienced 5-year-olds. Two decades of drag-and-drop studies flip-flopped for exactly this reason (below). Any guideline here should be treated as a strong prior to be tested with actual kidnix users, not as a law.

### 2.2 Druin's roles of children in design, and cooperative inquiry

Allison Druin's 2002 framework is the field's organising idea for participation. Children can be involved as:

1. **User** — observed using existing technology; the design team learns from watching.
2. **Tester** — tries a prototype before release, gives feedback.
3. **Informant** — consulted at chosen points, in dialogue with the team.
4. **Design partner** — an equal stakeholder throughout, in the room, inventing.

([Druin, *The role of children in the design of new technology*, 2002 — 1,500+ citations](https://doi.org/10.1080/01449290110108659); summary of the roles and of KidsTeam practice at the [Joan Ganz Cooney Center](https://joanganzcooneycenter.org/2023/03/22/designing-with-kids/)) **[evidence: highly influential conceptual framework, not an experiment]**.

**Cooperative Inquiry** is the associated method set: intergenerational design teams of adults and children (canonically 7–11 year olds in Druin's KidsTeam), using low-tech prototyping ("bags of stuff"), sticky-note "likes / dislikes / design ideas", and big-paper brainstorming, deliberately structured to flatten the adult–child power gradient. Children are positioned as experts in *being children*.

Two important caveats for a 4–8 project:

- Druin's design-partner method was developed with roughly 7–11 year olds. **The literature is markedly thinner on genuine design partnership with 4–6 year olds**, who tire quickly, try to please adults, and struggle to articulate preferences (see §2.9) **[evidence: expert observation, e.g. Egloff on preschool usability studies, reported in Hourcade 2022]**.
- The CCI community has since criticised its own participation practice. Van Mechelen and colleagues' [*A Systematic Review of Empowerment in Child-Computer Interaction Research*](https://dl.acm.org/doi/10.1145/3459990.3460701) (IDC 2021, Honourable Mention) and the [*Manifesto for children's genuine participation in digital technology design and making*](https://www.sciencedirect.com/science/article/pii/S2212868921000908) (IJCCI, 2021) argue that much "participatory" work is tokenistic. Hourcade separately notes that **incorporating parents alongside children in the design process is an under-served area** — directly relevant to kidnix, which is a two-audience product (child + parent).

### 2.3 Motor control: pointing, targets, dragging, clicking, keyboard

This is the best-evidenced area, and the numbers are unambiguous.

**Pointing accuracy by target size (the single most important table for kidnix).** Hourcade, Bederson, Druin & Guimbretière ran a controlled point-and-click experiment with thirteen 4-year-olds, thirteen 5-year-olds and thirteen young adults, varying target size (16 / 32 / 64 px diameter) and distance ([*Accuracy, Target Reentry and Fitts' Law Performance of Preschool Children Using Mice*, ACM TOCHI 2004](https://dl.acm.org/doi/10.1145/1035575.1035577)) **[evidence: controlled lab experiment, n=39, small but well-designed and repeatedly replicated in direction]**:

| Target diameter | 4-year-olds | 5-year-olds | Adults |
|---|---|---|---|
| 16 px | **43%** accuracy | 74% | 90% |
| 32 px | 77% | **91%** | 96% |
| 64 px | **90%** | 97% | 99% |

Target size and age both had highly significant effects on accuracy and on target re-entry (p < 0.001); **distance to the target did not**. To reach 90% accuracy, 4-year-olds needed targets **four times the diameter** adults needed. In that study's display terms, the 64 px target was **23.7 mm on screen** (3.6 mm in motor/mouse space). Fitts' law modelled children well only for *first* target entry — children repeatedly overshot and re-entered targets, which is exactly the behaviour a UI must tolerate.

**Frustration behaviour.** Children who cannot hit a target do not slow down and aim; they **click rapidly and repeatedly**, or **tap the screen until something happens** (Hourcade et al. 2008; Anthony et al. 2012, both reported in Hourcade 2022). Any kidnix control must be idempotent and safe under a burst of 8 clicks in a second.

**Touch targets.** NN/g's recommendation from its children's studies is **2 cm × 2 cm minimum touch targets for young children — four times the area of the 1 cm × 1 cm adult recommendation** ([NN/g, *Design for Kids Based on Their Stage of Physical Development*](https://www.nngroup.com/articles/children-ux-physical-development/)) **[evidence: practitioner research programme, lab usability studies]**. Anthony et al. found 7–16 year olds achieved ~90% tap accuracy at 9.5 mm targets and >95% at 12.7 mm — and 4–8s are *below* that band, so 12.7 mm is a floor, not a target. Independent work reports children aged 7–10 **miss 7 mm targets almost 30% of the time**.

**Gesture success rates, ages 3–6.** Vatavu, Cramariuc & Schipor tested 89 children aged 3–6 on tablet and smartphone (targets 8 mm/20 mm with a generous 23 mm active area) ([*Touch interaction for children aged 3 to 6 years*, IJHCS 2015](https://www.sciencedirect.com/science/article/abs/pii/S1071581914001426)) **[evidence: lab study, n=89 — one of the larger CCI motor studies]**:

- Tap: **98.7%** completion
- Double-tap: **82.8%**
- Drag one item: **92.0%**
- Drag two items simultaneously: **53.7%**

Nacher et al. found 24–38-month-olds succeeded at tap, drag, scale and one-finger rotation but struggled with **double-tap, long-press, and two-finger rotation** — with very large targets. NN/g's developmental table agrees: 3–5s have mastered "tapping, swiping, dragging on touchscreens"; 6–8s have mastered "clicking with mouse & trackpad, simple keyboard use"; **dragging and scrolling with a mouse, and coordinated keyboard+mouse, are not mastered until 9–12**.

**Mouse buttons.** In Hourcade's study, all adults and 10/13 five-year-olds used the left button exclusively; **most 4-year-olds used a mix of left and right clicks**. Even in a later, more experienced cohort, 10% of children used the left button less than 90% of the time. The recommended mitigations are: make all mouse buttons do the same thing, or make only the left button do anything (with feedback on the others).

**Double-click is effectively out of reach.** It compounds the timing problem with the pointing problem; combined with the 82.8% double-*tap* rate at ages 3–6, there is no case for it in a 4–8 interface.

**Drag-and-drop vs click-move-click is genuinely contested.** Joiner et al. (1998) found 5–6s faster and more accurate with click-move-click, especially over long distances; Inkpen (2001) agreed for 9–13s; Donker & Reitsma (2007) found the **opposite** for 5–7s (drag-and-drop faster, fewer errors) and found distance did *not* matter; Barendregt & Bekker (2011) found children *expected* dragging and used it even when click-move-click was available. Hourcade's read of the whole history: **drag-and-drop is probably now the better choice**, because today's children have far more touch/drag experience and modern optical mice are better than 1990s ball mice. Donker & Reitsma's specific recommendation stands regardless: **change the cursor/object appearance to signal when an item can be picked up and when it can be dropped**.

**Bimanual coordination.** Two-handed simultaneous actions frustrate under-8s; NN/g observed 5-year-olds who "couldn't manage to get them to work together smoothly." No chords, no shift-click, no ctrl-drag.

**Keyboard.** Typing and spelling are a significant barrier and a source of frustration; the field's response has been to move children's programming languages from text to blocks (Hourcade 2022, citing Hourcade & Perry 2009 and Walter et al. 1996). NN/g notes slow typing and poor mouse control as the defining physical limits, and that spelling/search errors frustrate 5–11s such that **autocorrect becomes critical** ([NN/g, *Designing for Kids: Cognitive Considerations*](https://www.nngroup.com/articles/kids-cognition/)).

**Assistive pointing works.** Hourcade's **PointAssist** detects the slow, short sub-movements that precede a difficult target acquisition and transparently enters a precision (slowed-cursor) mode. It brought 4-year-olds' accuracy close to adult levels, requires no knowledge of where targets are (so it can run system-wide), and self-scaffolds — it stops triggering as the child improves ([PointAssist, IDC 2008](https://dl.acm.org/doi/10.1145/1463689.1463757)) **[evidence: lab study with an evaluated prototype]**. This is a genuinely appealing OS-level feature for kidnix.

### 2.4 Working memory, attention and problem solving

All from Hourcade (2022) unless noted; the underlying developmental sources are Flavell et al. and Dempster **[evidence: classic developmental psychology, synthesised]**.

- **Working memory**: ~4–5 chunks at age 5, ~6 at age 9, ~7 for adults (Dempster 1981). This directly bounds how many things a screen may ask a child to hold in mind.
- **Selective attention** is immature; children cannot *actively search* for objects until early elementary school, and process visual information more slowly than adults — so **visual complexity is doubly costly**.
- **Preschoolers (<7) focus on one aspect of a task and neglect others**, and attend to the *current* state without recalling what came before or anticipating what comes next. Critically, they **cannot mentally reverse actions** — reversibility arrives with concrete operations.
- **Hierarchies**: categorisation starts at ~14 months, but *reasoning with hierarchies* does not appear until the elementary years. Under-7s "do not have a good understanding of hierarchies" — the direct cause of menu failure (§2.6).
- **Symbolic representation**: by age 3 most children understand a symbol stands for something else — the developmental licence for icons. But they still struggle with *representational* conventions (red lines for roads that aren't red), so icons must be depictive, not abstract.
- **Scripts and narrative**: preschoolers *can* assemble scripts — ordered sequences of actions, locations and objects — which is why storytelling tools work for them.
- **Qualitative over quantitative**: preschoolers make qualitative assessments; 6–11s begin using quantitative ones. Feedback for the youngest should be a filled shape, not a score.
- **Patience**: "children will often be less patient than adults... Children need quick feedback and if they do not get it they are likely to move to another activity."

NN/g adds the Piagetian frame: under-7s have immature theory of mind and **cannot interpret subtle feedback or abstract connections between elements**; under-6s need **exaggerated expressions**; errors generate frustration faster than in adults.

### 2.5 Reading, icons and audio — designing for pre-readers

- **Minimise text**; for pre-readers and beginning readers, visual means of interacting are "crucial to the success of software" (Hourcade 2022, citing Druin et al. 2001, Walter et al. 1996). A side benefit: less text means easier adoption across languages.
- Icons should (i) represent the action/object recognisably, (ii) be easily distinguishable from each other, (iii) read as interactive and separate from the background, and (iv) have **no more visual complexity than needed to satisfy (i)–(iii)**.
- **Font size**: NN/g's guidance for beginning readers (6–8) is a **14-point minimum** ([NN/g, *Children's UX: Usability Issues*](https://www.nngroup.com/articles/childrens-websites-usability-issues/)). Ages 3–5 require visual navigation aids in place of text.
- **Instructions get skipped.** Children bypass long paragraphs of instructions (NN/g, citing a 2010 study). Hiniker et al.'s study of 2–5 year olds and in-app gesture instructions found **children under 3 needed an adult to model the gesture, while older preschoolers did best with audio instructions** ([Hiniker et al., IDC 2015](https://dl.acm.org/doi/10.1145/2771839.2771851)) **[evidence: lab study, small n]**. This is the strongest direct evidence for read-aloud/audio instruction over text for our age band.
- **Audio and animation are liked**, in contrast to adult users who often find them irritating. NN/g observed a pair of 8-year-olds spending *several minutes* trying to make a page play sound and animate.
- **Auditory icons** (non-speech sound) are recognised better as children get older (Jacko 1996) — so don't rely on abstract earcons alone for a 4-year-old; pair sound with a visual change.
- **Very little research exists on non-speech sound design for children.** Hourcade states this outright. Audio design in kidnix is an area where we will be extrapolating.
- **Multilayer / progressive disclosure**: present few actions and objects first; add more as the child becomes proficient (Shneiderman's multilayer strategy, endorsed in Hourcade's guidelines appendix). **[evidence: expert design principle, sparse direct evidence in children]**

### 2.6 Navigation, menus and error recovery

- **Menu navigation is a documented failure mode for children** (Druin et al. 2001; Hutchinson et al. 2006) and is "particularly dire" for under-7s because of the hierarchy problem. Even 10–13 year olds forgot menus that had to be summoned via a soft button (Danesh et al. 2001).
- **What does work**: "simple setups, such as those on tablet user interfaces where children can swipe through sets of icons and may remember the location of their favorite choices, appear to work well even for young children." Spatial memory for a stable, flat, always-visible set of icons is the mechanism.
- **Direct manipulation** — visibility of objects and actions, rapid/reversible/incremental actions, pointing instead of typed commands — is the recommended interaction style, with three riders: rapid feedback (children abandon otherwise), **reversibility** ("if an action can lead to children losing a drawing they worked on, it will cause a great deal of frustration and will likely lead them to quit using the technology unless they can reverse the action"), and incremental actions.
- **Scrolling**: NN/g says avoid it entirely for 3–5s, introduce it minimally for 6–8s, and only with strong cues that more content exists.
- **Back buttons**: children aged 3–5 do not reliably use the browser back button.
- **Search vs. saved locations**: under-9s rely on bookmarks/saved items far more than on search; search only becomes the main entry point for older children. For kidnix's journal, this argues for a visual, recency- and thumbnail-based journal rather than a search box.
- **Error recovery**: children struggle to interpret error messages; experienced children will try refresh / close-and-reopen / back; if a quick fix fails, **they abandon the product rather than troubleshoot**. Under-7s cannot mentally reverse actions, so they cannot reason their way back out of a bad state — the system has to do it for them.
- **Multiple simultaneous navigation options are "very confusing"** for young children; following standard, consistent UI conventions is preferred by children just as by adults.

### 2.7 Sessions, timers and ending gracefully

Hiniker, Suh, Cao & Kientz's CHI 2016 study is the most directly relevant empirical work to kidnix's bounded-session design ([*Screen Time Tantrums*, CHI 2016 — PDF](https://faculty.washington.edu/alexisr/ScreenTimeTantrums.pdf)) **[evidence: 27 parent interviews + diary study, 28 families, 380 logged transitions; correlational, not an RCT]**:

- **93%** of parents reported their child throws a tantrum, whines or resists ending screen time at least occasionally; **37%** said it "almost always" ends in a fight.
- **Technology-triggered endings were significantly less upsetting than parent-triggered endings**: mean upset 2.98 (tech) vs 3.47 (parent), F(1,69)=8.104, **p = .006, η² = .105**. The effect survived controlling for session duration. "Technology may be an effective third-party mediator for easing transition pain."
- **Routine helped**: transitions at the end of a routine, predictable period were smoother (2.84) than ad hoc ones (3.10), F(1,331)=16.751, **p < .001, η² = .048**. But routine sessions also ran significantly longer (40.0 min vs 29.5 min).
- **Counter-intuitive and important: parental warnings ("two more minutes") were associated with *worse* transitions** — 3.35 warned vs 3.03 unwarned, F(1,331)=20.34, **p < .001, η² = .058** — and the effect persisted (p = .002) after excluding child-initiated endings. The authors could find no contextual confound, but honestly flag the plausible one: **parents may warn precisely when they expect trouble**. This is correlational; it is not evidence that *in-app* visual countdowns are harmful, and it should not be over-read.
- **Autoplay was named repeatedly by parents as the villain** — content that starts the next item removes the natural stopping point. Eleven of 27 parents described actively fighting Netflix/YouTube autoplay.
- 25% of transitions were child-initiated (the child lost interest or chose something else) — much more common than parents believed.

**Time perception itself** is thinly evidenced in CCI. I found no strong CCI study on how 4–8s understand elapsed time in an interface. Visual/analogue timers (Time Timer-style shrinking discs) are widely recommended by SEN and early-years practitioners and are standard in autism-support practice, but the support is **[evidence: practitioner consensus / expert opinion, not controlled trials in this context]**. Treat "a visual, non-numeric depletion indicator is better than a clock for a 5-year-old" as a plausible, untested hypothesis for kidnix.

### 2.8 Fun, engagement, reward and evaluation instruments (Read, Markopoulos, Bekker)

The **Fun Toolkit** (Read, MacFarlane & Casey, 2002; validated Read 2008) is the standard CCI instrument set for children aged ~5–10:

- **Smileyometer** — a 5-point visual analogue scale of faces from "Awful" to "Brilliant", administered before (expectations) and after (experience).
- **Fun Sorter** — an ordinal card-sort ranking several experiences against constructs ("most fun", "easiest to learn"), pictures for younger children.
- **Again-Again table** — "would you do this again? yes / maybe / no" per activity, as an engagement/endurability proxy.

([Read, MacFarlane & Casey, *Endurability, Engagement and Expectations*](https://www.researchgate.net/publication/228870976_Endurability_Engagement_and_Expectations_Measuring_Children%27s_Fun); [Read, *Validating the Fun Toolkit*, 2008](https://doi.org/10.1007/s10111-007-0069-9))

**The known problem is ceiling effects.** MacFarlane et al. (2005) found Smileyometer ratings "not particularly useful as most children were overly enthusiastic about all the software titles they tried"; ranking yielded better data. Zaman et al. (2013), with 113 children aged 33–90 months, found the Smileyometer **unreliable** — extreme positive scores over-represented, results inconsistent with actual product preferences — while the forced-choice **"This or That"** method was reliable for children aged 4+. Hall et al. (2016) found that using a **smiley-only scale (dropping the sad faces)** mitigates the ceiling problem. **[evidence: several small-to-medium lab/field studies, consistent direction]**

**A 2025 corrective is worth knowing.** A new *Interacting with Computers* paper reviewing 129 papers plus two fresh case studies (117 usable paired ratings from **3–4 year olds** in preschool; 135 children aged 8–11) concludes that **young children *can* use Smileyometers with adult support**, and that children discriminated meaningfully — "only 4/135" gave everything a 5 — recommending procedural guidelines for preparation, administration and reporting rather than abandoning the tool ([*Using the Smileyometer to measure UX with children*, IwC 2025](https://academic.oup.com/iwc/advance-article/doi/10.1093/iwc/iwaf016/8131678)) **[evidence: literature review + 2 case studies; the strongest recent methodological source]**. The pragmatic reading: **Smileyometer for absolute rating is weak; forced-choice comparison and behavioural measures are strong; use both.**

Other instruments: **Giggle Gauge** (Dietz et al., 2020) is a validated engagement questionnaire specifically for **4–7 year olds** — the best age-matched instrument for kidnix. **[evidence: validation study]**

**Reward design.** Hourcade's guidance is that feedback must be immediate and, for actions that cannot be, must show progress and remain cancellable. On extrinsic reward specifically, CCI has less direct evidence than one might hope; the strongest adjacent source is Hirsh-Pasek et al.'s *Putting Education in "Educational" Apps* ([Psychological Science in the Public Interest, 2015](https://doi.org/10.1177/1529100615569721)), which sets out four pillars — **active** (minds-on, not just tapping), **engaged** (without distraction), **meaningful** (connected to the child's life), and **socially interactive** — and argues that most commercial "educational" apps fail on the first and last **[evidence: major expert review commissioned by APS; not an experiment]**.

### 2.9 Evaluating with 4–8 year olds

- **Preschool usability testing is hard**: Egloff reported that preschoolers could not sustain a task for long, **tried to please adults**, were easily distracted, and had difficulty expressing likes and dislikes (in Hourcade 2022). Creative alternatives beat adapted adult protocols.
- **Observation beats verbal report.** Donker & Reitsma, testing literacy software with 5–7s, "identified most problems by observing the children's behavior"; thinking aloud helped mainly to *rank* problem severity.
- **Active intervention** (the researcher asking questions during the task) elicited the most verbal comments from 6–7 year olds; co-discovery pairs worked *less* well in that comparison; think-aloud, peer tutoring and retrospection all worked better than co-discovery (van Kesteren et al. 2003). Note this contradicts the popular "always pair children" advice.
- **Pairing still has support**, but conditionally: Hanna et al. recommend pairing children with **good friends** and letting them work without an observer present; Als et al. found friend-pairs found more problems with less effort than stranger-pairs.
- **Peer tutoring** (one child teaches another) is a usable proxy for learnability, tried with children aged 5–9 (Höysniemi et al. 2003).
- **Session structure**: NN/g recommends sessions no longer than 60–90 minutes *with breaks* for minors generally, and shorter for younger children; recruit extra participants; prepare varied tasks; make the room child-appropriate; dress casually; use generic praise and friendly neutrality ([NN/g, *Usability Testing with Minors: 16 Tips*](https://www.nngroup.com/articles/usability-testing-minors/)). For 4–6s specifically, Hourcade's summary of the literature points to **20–30 minutes maximum**.
- **Consent and assent**: parents/guardians give legally binding written **consent**; the child gives verbal **assent** in plain language, with an explicit right to stop. For **ages 3–6, the parent may stay in the room but should sit behind the child and be coached in advance to stay quiet**; ages 7–12 are comfortable with a parent nearby or just outside ([NN/g, *UX Research with Minors: Consent vs. Assent*, Feb 2026](https://www.nngroup.com/articles/research-minors-consent/)).
- **Physiological measurement of children is contested** within CCI on ethical grounds; Hourcade et al. (2018) raised concerns about invasive data gathering and "the quantification of children."

### 2.10 Ethics, agency, rights and the "three plagues"

Hourcade's closing chapter names **three plagues** technology can inflict on children **[evidence: expert argument, well-reasoned, not empirical]** — and they map onto kidnix's premise almost line for line:

1. **Isolation** — computers replacing humans (play partners, family, teachers); tablets as child-sitters; hyper-personalisation leaving children with less in common with each other.
2. **Quantification** — the "unabated thirst for personal information," including via schools. Hourcade lists five distinct harms: long-term privacy loss; displacement of meaningful human interaction; mis-classification setting children on the wrong track; children feeling constantly judged and tying self-worth to systems that measure attendance and performance but never "creativity, kindness, or generosity"; and **desensitising children to surveillance so they will not question it as adults**.
3. **Widening inequality** — the digital divide (e.g. Pew 2020: 59% of lower-income US parents expected their children to face digital obstacles in remote schooling vs 10% of upper-income).

His proposed cure draws on the UTOPIA participatory-design principles: **quality (augment skills rather than replace them; design technology that encourages face-to-face interaction), democracy (children, parents and teachers participate in design decisions), and emancipation (do not exploit)**.

The community's ethics discourse has been audited and found wanting: across **18 years** of IDC and IJCCI, only **157 papers** even use the stem "ethic\*", and the literature is underdeveloped in definition, theoretical basis, reporting of formal approval, and design/participation ethics ([Van Mechelen et al., IDC 2020](https://dl.acm.org/doi/10.1145/3392063.3394407)) **[evidence: systematic literature review]**.

**The UK regulatory position is the strongest external constraint and the best-aligned one.** The ICO's **Age Appropriate Design Code** ("Children's Code"), in force since September 2021, is the world's first statutory code for children's data and sets **15 standards** for services likely to be accessed by children. Its headline design requirements — **best interests of the child as the primary consideration; data protection by default; data minimisation; no profiling by default; no "nudge techniques" that push children toward weaker privacy choices; no detrimental use of data** — have driven concrete changes: children's accounts defaulting to private, overnight notifications off, and a prohibition on profiling-based targeted advertising ([5Rights Foundation on the AADC's four-year impact](https://5rightsfoundation.com/uks-age-appropriate-design-code-four-years-of-global-impact-before-key-review/)) **[evidence: statutory code + advocacy analysis]**. Kidnix's zero-telemetry, no-store, no-feed posture is not just defensible; it is what the Code is asking for, taken to its logical conclusion.

### 2.11 Voice and speech interfaces

- **Automatic speech recognition still fails young children badly.** Reported word error rates: ~5% for adults in real-world settings; 11–18% for children 10+; 15–21% for children 6–10; **up to 35% for kindergarteners (4–6)** — a ~30 percentage point gap ([The Learning Agency, *Closing the Child Speech Recognition Gap*](https://the-learning-agency.com/guides-resources/closing-the-child-speech-recognition-gap-evidence-limitations-and-paths-forward/), synthesising Shivakumar et al. 2020, Kathania et al. 2022) **[evidence: literature synthesis of benchmark studies]**.
- A **2025 JASA Express Letters** study tested two Siri versions and Alexa on utterances from 2-, 3- and 5-year-olds and found that although Siri has improved, **both still struggle, and human listeners far outperformed the systems — especially with the youngest children** ([JASA-EL 2025](https://pubs.aip.org/asa/jel/article/5/3/035201/3338215/Voice-assistant-technology-continues-to)) **[evidence: controlled comparison study]**.
- A 2025 causal analysis of ASR errors across Wav2Vec2, HuBERT, Whisper and MMS found **age (physiological) is the highest-impact factor**, followed by number of words in the audio, background noise, pronunciation ability and vocabulary difficulty; fine-tuning on children's speech reduces sensitivity to physiological and cognitive factors but **not** to utterance length ([arXiv:2502.08587](https://arxiv.org/abs/2502.08587)) **[evidence: benchmark + causal inference study]**.
- Hourcade's summary is blunt: "recognising children's speech, in particular at young ages, continues to be problematic."
- On the *social* side, CCI has asked whether conversational agents change how children talk to people ([IDC 2021](https://dl.acm.org/doi/abs/10.1145/3459990.3460695)) and documented children's communication breakdowns and repair strategies with AI vs human partners.

**Implication for kidnix:** speech *output* (read-aloud, TTS) is a first-class accessibility feature for pre-readers and is technically low-risk. Speech *input* as a required interaction path for 4–6s is not viable in 2026 at acceptable reliability, and would additionally conflict with a zero-telemetry stance if it required cloud ASR.

### 2.12 Children and generative AI in CCI, 2023–2026

This is where the field's energy has gone, and it is mostly about children older than our band.

- **Children themselves want AI that is bounded.** IDC 2026 includes *Children Envision Future GenAI Chatbots that are Bounded, Helpful, and Safe* ([IDC 2026 index](https://dblp.org/db/conf/acmidc/idc2026.html)) — the framing is the finding.
- **Children fear over-reliance.** 37 fifth-graders (9–10) saw genAI as companion, collaborator and task-automator but voiced fears about "diminished learning, disciplinary consequences, and long-term failure" ([Dangol et al., arXiv:2505.16089](https://arxiv.org/abs/2505.16089)) **[evidence: qualitative pilot, n=37]**.
- **A design grammar for child-AI interfaces.** *Once Upon an AI* synthesises Piagetian theory with an analysis of 52 animated works into six scaffolds: visual animacy and clarity; musical/auditory scaffolding; **audiovisual synchrony**; sidekick personas; storyplay; and **predictable narrative structure** ([IJCCI 2025; arXiv:2504.08670](https://arxiv.org/abs/2504.08670)) **[evidence: analytical framework, no user study]**. The synchrony and predictable-structure points transfer usefully to a non-AI shell.
- **Parents want staged progression**: starting with **"closed" systems that constrain input**, then several "small and focused" tools, and only eventually open-ended chatbots ([CHI 2026](https://dl.acm.org/doi/full/10.1145/3772318.3790479)) **[evidence: qualitative study]**.
- **Safety benchmarking is immature** — *Safe-Child-LLM* ([arXiv:2506.13510](https://arxiv.org/pdf/2506.13510)) exists because the gap does. And **children attribute agency to AI more readily than experience** — it can *do*, they doubt it can *feel* ([ScienceDirect 2025](https://www.sciencedirect.com/science/article/pii/S2949882125000192)).

I found **no** credible CCI evidence supporting open-ended generative AI as a core interaction for 4–8 year olds. The trend line runs toward bounded, scaffolded, adult-supervised AI at older ages.

---

## 3. Design guidelines for kidnix

Numbered so they can be cited from ADRs and design docs.

**Targets, pointing and input**

1. **Minimum interactive target: 24 mm × 24 mm physical on-screen**, for both touch and mouse. This exceeds NN/g's 2 cm × 2 cm floor and matches the 23.7 mm at which Hourcade's 4-year-olds reached 90% accuracy. Compute in millimetres from the display's DPI, never in raw pixels.
2. **Primary activity tiles: 40–60 mm square**, with ≥12 mm of dead space between adjacent targets. Big, sparse, spatially stable.
3. **Ship a PointAssist-equivalent at the compositor/shell level**: detect the slow, short sub-movements that precede a difficult acquisition and transiently reduce pointer speed. It needs no knowledge of target locations and it fades out as the child improves.
4. **All mouse buttons do the same thing** on primary controls. No right-click menus anywhere in the shell. No middle-click.
5. **No double-click. No long-press as the sole route to any action. No two-finger or bimanual gestures. No modifier keys** (shift/ctrl/alt) required for anything a child does.
6. **Every control must be idempotent and safe under rapid repeated clicking** — assume 8 clicks in 1 second as a routine input. Debounce, don't queue.
7. **Where dragging is used** (drawing, block coding, sorting), (a) keep drag distances short — put the destination near the source; (b) change the cursor *and* the object's appearance at pick-up and at valid drop; (c) make a failed drop return the item gently with a visible animation rather than snapping it back invisibly; (d) always offer a click-move-click fallback for the same operation.
8. **No scrolling in the shell.** Paginate with large, obvious page dots and arrows. If an activity must scroll, scroll one screenful at a time via a big button, never free-scroll.
9. **Keyboard is never required** to reach or leave any part of the shell. Typing appears only inside activities that are *about* typing or writing, and always with an on-screen alternative (picture-picking, stickers, voice-free stamps).
10. **Autocorrect / forgiving matching everywhere text is entered**, including the child's own name.

**Layout, text and audio**

11. **Flat navigation, maximum one level deep**, with a fixed spatial arrangement so children can learn positions. No pull-down menus, no hamburgers, no nested folders, no soft-button-revealed menus. This is the single strongest navigation finding in the literature.
12. **Never show more than 5 primary choices on one screen** for the 4–6 band (working memory ≈ 4–5 chunks at 5). Prefer 3–4.
13. **Every screen has exactly one obvious "home" affordance in a fixed position** and one obvious "back". Do not rely on a hardware or browser back.
14. **Icon + label + audio, always three channels.** Icons depictive (a paintbrush, a camera), not abstract or conventional. Label in ≥18 pt at a normal viewing distance (NN/g's 14 pt is a floor for 6–8s; 4–5s need more). Tapping/hovering a label reads it aloud.
15. **Read-aloud is a first-class, always-available system service**, not a setting. Every label, button, prompt, error and journal entry has a voice. Include a persistent "read this to me" ear/speaker control with the same target size as everything else.
16. **Instructions are audio-first, ≤ 2 sentences, ≤ 12 words per sentence, in the imperative present** ("Pick a colour. Then draw."). Never a paragraph. Offer a replay control; never auto-repeat more than once.
17. **Demonstrate, don't describe.** For any new gesture or activity mechanic, show a short looping animation of the action being performed, with synchronised audio — audiovisual synchrony is one of the six child-AI scaffolds and is well-supported for young children generally.
18. **Feedback within 100 ms for every input**, visual *and* auditory. If an operation exceeds ~1 s, show an animated progress indicator that is itself pleasant to watch, keep the UI responsive, and allow cancellation.
19. **Feedback should be qualitative, not numeric**, for 4–6s: a shape filling, a character reacting, a sound — not "7/10" or "82%".
20. **Exaggerate emotional and state cues.** Under-6s cannot read subtle feedback; a "saved" state must be unmistakable, not a grey tick.
21. **Cap visual complexity**: one focal region, ≤ 2 animated elements at once, no ambient looping motion competing with the child's task. Use a multilayer approach — the first session shows fewer activities, more appear as the child uses the system.

**Errors, reversibility and safety**

22. **Nothing the child does is unrecoverable.** Universal undo across every creative activity, with an undo affordance in a fixed position. Under-7s cannot mentally reverse actions, so the system must reverse them.
23. **Autosave continuously to the journal**; never present a "do you want to save?" dialogue. A child should never lose work by walking away.
24. **No modal confirmation dialogues with text choices.** Where a genuinely destructive action exists (delete a drawing), make it a two-step *spatial* action (drag to a bin that then shows the item recoverable inside it) rather than a yes/no question. Keep a recoverable bin for at least 30 days.
25. **No error messages in the adult sense.** If something fails, the shell returns the child to a known-good state (the activity's start, or home) with a friendly audio line, and logs the detail for the parent view only. Children abandon products rather than troubleshoot, so recovery must be automatic.
26. **Design for the "burst-click frustration" signal**: if the shell detects repeated rapid clicking on a non-target, that is a usability alarm — offer help proactively (highlight the real target, replay the instruction) and record it as telemetry-free local diagnostics for the parent.

**Sessions, timers and ending**

27. **The system ends the session, not the parent.** Hiniker et al.'s finding that technology-triggered endings are significantly less upsetting (p = .006, η² = .105) is the strongest available evidence for kidnix's core session design. Make the ending feel like it comes from kidnix, with a consistent character/ritual — never a message that says "your mum said stop."
28. **Make sessions routine and predictable**: same daily slot, same length, same ending ritual. Routine endings were significantly smoother. Accept the trade-off the study also found — routine sessions ran longer — by fixing the length in the parent settings.
29. **No autoplay, ever, anywhere.** No "next activity" that starts by itself, no queued content, no infinite feed. Every continuation is a deliberate, effortful child action. Parents in the study named autoplay as the specific thing that destroys natural stopping points.
30. **Prefer a continuous, non-numeric visual depletion indicator** (a shrinking coloured arc, a filling jar, a sun crossing the sky) over a digital countdown, and let it be glanceable throughout rather than appearing as an interrupting warning. **Flagged as a hypothesis**: the Hiniker result on warnings is about *parental verbal* warnings and may not transfer, and the two designs should be A/B tested with real families.
31. **End on a completion beat, not mid-task.** Give the child a natural finishing action — put the drawing in the journal, wave goodbye to the character — so the last thing they do is an accomplishment, not an interruption.
32. **Support child-initiated endings.** 25% of real transitions are the child losing interest; make "I'm finished" a first-class, rewarded action rather than an escape hatch.

**Journal, content and structure**

33. **The journal is spatial and visual, not searchable.** Thumbnails, most-recent-first, on a fixed grid, with date shown as a picture cue (a sun/moon, a day-of-week colour) rather than a formatted date string. Under-9s rely on saved locations rather than search.
34. **Lean on narrative and scripts.** Preschoolers can hold ordered sequences of actions/locations/objects; frame multi-step activities (story-making, letters-to-family) as a short, predictable narrative with the same shape every time.
35. **Age-band the content, finely.** NN/g's studies found children are acutely sensitive to material pitched at younger children ("that's for babies, maybe 4 or 5"). Distinguish at minimum 4–5 and 6–8, and let the parent set the band. A 6-year-old shown 4-year-old visuals will reject the whole product.

**Parent-facing and rights**

36. **Best interests of the child as the primary design consideration**, explicitly, in writing — the ICO Children's Code's first standard. Where a child's interest and a parent's convenience conflict, document the resolution.
37. **Zero telemetry by default and by architecture**, not by setting. No profiling, no behavioural modelling, no scores that follow the child. Hourcade's second plague — children learning to accept surveillance and tying self-worth to systems that measure performance but never kindness — is a design risk, not just a privacy one.
38. **No nudge techniques** that push a child toward giving up privacy, spending more time, or extending a session. This is a Children's Code requirement and a design ethic.
39. **Design for the dyad.** CCI explicitly identifies parent-plus-child co-design as under-served. Build at least one activity (letters-to-family, photos) whose value is *shared* attention, and make the parent view legible to a non-technical adult.
40. **Recruit children as design partners, not just testers** — Druin's fourth role — while accepting that with 4–6s this means play-based sessions with adult co-designers, not the classic KidsTeam protocol.

**Evaluation programme**

41. **Test with 5–6 year olds in 20–30 minute sessions**, in a familiar setting, with varied short tasks, recruiting ~30% more participants than needed.
42. **Weight observation over self-report.** Code behaviour (target misses, burst-clicks, abandonment, help-seeking, time to first successful action); use verbal methods to rank severity, not to find problems.
43. **Use forced-choice comparison (This-or-That) and the Again-Again table as primary preference measures**; use the Smileyometer only with adult support and standard procedure, and never as the sole outcome. Consider the **Giggle Gauge**, which is validated specifically for 4–7 year olds.
44. **Use active intervention** (ask questions during the task) as the default facilitation style for 6–7s, and **peer tutoring** ("show your friend how to do it") as a learnability probe.
45. **Written parental consent plus verbal child assent** every time, with the parent seated behind the 4–6 year old and briefed to stay quiet; incentives as a choice from a toy box for under-9s.

---

## 4. What the evidence says NOT to do

- **Do not use pull-down, nested, or hidden menus.** Documented failure with children generally, and specifically dire for under-7s who lack hierarchy reasoning. Even 10–13s forget menus behind a soft button.
- **Do not require double-click, long-press, multi-finger gestures, drag-with-modifier, or any bimanual action.** Double-tap succeeds only ~83% of the time at ages 3–6; simultaneous two-item drag only ~54%.
- **Do not size targets in pixels.** Physical size is what matters, and high-DPI displays make pixel counts meaningless.
- **Do not put long-distance drags in the design.** Where two studies disagree about drag vs click-move-click, they agree that *long* drags are worse.
- **Do not write instructions as paragraphs.** They are skipped. Do not rely on text at all for 4–5s.
- **Do not rely on subtle feedback** — muted colours, small state changes, understated animation, quiet earcons. Under-6s cannot read them.
- **Do not use error messages, modal text dialogues, or "are you sure?" prompts.** Children cannot parse them, and if a quick fix fails they abandon the product entirely.
- **Do not build any free-scrolling surface** in the shell for 3–5s; keep it minimal and cued for 6–8s.
- **Do not put a search box where a young child needs it.** Under-9s use saved locations, not search; spelling failures compound it.
- **Do not implement autoplay, auto-advance, "up next", streaks, or any continuation that happens without a child's deliberate act.** Parents named this specifically as the thing that makes stopping impossible.
- **Do not make the parent the visible agent of the session ending.** Parent-triggered endings were significantly more upsetting than technology-triggered ones.
- **Do not rely on speech recognition as a required input path.** Kindergarten-age WERs reach ~35%; systems still underperform human listeners badly at ages 2–5.
- **Do not treat the Smileyometer as a sufficient outcome measure.** Ceiling effects are well documented; use forced-choice and behaviour.
- **Do not build open-ended generative AI chat into the child-facing shell.** No CCI evidence supports it for 4–8s; the field's own participants ask for AI that is *bounded*.
- **Do not collect, profile, or score the child.** Beyond the legal position under the ICO Children's Code, Hourcade's argument is that quantification teaches children to accept surveillance and to locate self-worth in metrics that never measure creativity or kindness.
- **Do not assume 4–8 is one audience.** Children reject content pitched even one band younger, and a 4-year-old needs targets twice the diameter a 5-year-old needs.

---

## 5. Open questions and contested areas

1. **Drag-and-drop vs click-move-click remains genuinely unresolved.** Joiner (1998) and Inkpen (2001) favour click-move-click; Donker & Reitsma (2007) favour drag-and-drop; Barendregt & Bekker (2011) found children *expect* dragging. Hourcade's tentative verdict favours dragging today, attributing the flip to children's greater experience and better mice. **Kidnix should test both in its drawing and block-coding activities.**
2. **Do in-app visual timers help or hurt?** Hiniker et al. found *parental* warnings correlated with worse transitions and could not explain it — but they flag the obvious confound (parents warn when they expect trouble). Whether a calm, always-visible, non-numeric depletion indicator inside the software behaves like a "warning" or like the smooth technology-triggered ending is **unknown and directly testable**.
3. **Children's time perception in interfaces is under-studied in CCI.** The visual-timer practice base comes from SEN/early-years practice, not controlled HCI trials.
4. **Non-speech audio design for children is nearly a blank.** Hourcade states outright that very little research exists. Kidnix's soundscape will be extrapolation from adult auditory-display research plus general developmental findings.
5. **Smileyometer reliability is actively contested.** Zaman et al. (2013) call it unreliable for young children; the 2025 IwC review argues 3–4 year olds can use it with support and that discrimination is better than reputed. Read the 2025 paper's procedural guidelines before using it.
6. **Does the field's evidence base still hold?** Much of the definitive motor evidence is 2004–2015, from cohorts with far less touchscreen exposure than a 2026 five-year-old. The direction of the age effects is robust; the absolute thresholds may be conservative — which is a safe way to be wrong.
7. **How to genuinely design *with* 4–6 year olds.** Druin's design-partner role was built with 7–11s; methods for real partnership with pre-readers are thin and the empowerment literature says most claimed participation is tokenistic.
8. **Assistive pointing on modern stacks.** PointAssist was demonstrated on 2008 hardware. Whether sub-movement-triggered cursor slowing works well with modern high-DPI displays, trackpads and Wayland pointer acceleration is an engineering unknown worth prototyping.
9. **The bounded-session premise itself.** No RCT establishes that a software-imposed session limit improves child wellbeing; the Hiniker evidence is about the *smoothness of the transition*, not long-term outcomes. Kidnix should be honest that the bounded-session design is supported on transition-friction grounds and on parental-preference grounds, not on demonstrated developmental benefit.
10. **The "isolation plague" cuts both ways for kidnix.** A single-child, full-screen, offline shell is exactly the kind of solo experience Hourcade warns about. The letters-to-family and photo activities are the mitigations; whether they are enough is a design question the team should keep in front of it.

---

## 6. Top 10 takeaways

- **Target size is the highest-leverage single decision.** Four-year-olds hit 16 px targets 43% of the time and 64 px (≈24 mm) targets 90% of the time. Specify in millimetres; 24 mm is the floor, 40–60 mm is the design intent for primary controls.
- **Flat, spatially stable, always-visible navigation, one level deep.** Under-7s cannot reason about hierarchies; menus are the field's best-documented failure mode; a fixed grid of icons children learn by position is the documented success.
- **Icon + label + audio on everything**, with read-aloud as a system service rather than a setting; instructions audio-first, two sentences, demonstrated by looping animation rather than described.
- **Nothing is unrecoverable.** Universal undo, continuous autosave, no save dialogues, no destructive confirmations — because under-7s cannot mentally reverse actions and abandon products that fail them.
- **The software must end the session, not the parent** (mean upset 2.98 vs 3.47, p = .006), on a routine schedule, with a completion beat — and there must be no autoplay anywhere.
- **Assume frustration is expressed as burst-clicking**, and treat repeated rapid clicks as both a thing to survive safely and a usability alarm worth responding to in the moment.
- **Ban double-click, long-press-only, multi-finger, bimanual and modifier-key interactions**; keep drags short, signal pick-up and drop states, and offer a click-move-click fallback.
- **Working memory at age 5 is ~4–5 chunks**: no more than 5 primary choices per screen, and use progressive disclosure so the first session is simpler than the tenth.
- **Evaluate by watching, not asking**: 20–30 minute sessions, observation-led coding, forced-choice preference methods and the Giggle Gauge, with the Smileyometer only as a supported secondary measure.
- **The zero-telemetry, no-store, no-feed, bounded posture is not eccentric — it is where the field's ethics and UK law already point.** Hourcade's "quantification" plague and the ICO Children's Code's best-interests, data-minimisation and no-nudge standards both land on the same design.

---

## 7. Full source list

**Books and field syntheses**

1. Juan Pablo Hourcade, *Child-Computer Interaction, Second Edition* (2022), self-published, free PDF — https://jphourcade.com/book/hourcade_cci_2nd_edition.pdf *(read in full text; the single most important source here)*
2. Juan Pablo Hourcade, *Interaction Design and Children*, Foundations and Trends in HCI 1(4), 2008 — https://www.nowpublishers.com/article/Details/HCI-006
3. Kathy Hirsh-Pasek et al., *Putting Education in "Educational" Apps: Lessons from the Science of Learning*, Psychological Science in the Public Interest, 2015 — https://doi.org/10.1177/1529100615569721

**Participation, roles and design methods**

4. Allison Druin, *The Role of Children in the Design of New Technology*, Behaviour & Information Technology 21(1), 2002 — https://doi.org/10.1080/01449290110108659
5. Joan Ganz Cooney Center, *Designing with Kids: How Children and Adults Can Co-create New Technology* (2023) — https://joanganzcooneycenter.org/2023/03/22/designing-with-kids/
6. Van Mechelen, Musaeus, Iversen, Dindler & Hjorth, *A Systematic Review of Empowerment in Child-Computer Interaction Research*, IDC 2021 — https://dl.acm.org/doi/10.1145/3459990.3460701
7. *Manifesto for children's genuine participation in digital technology design and making*, IJCCI, 2021 — https://www.sciencedirect.com/science/article/pii/S2212868921000908

**Motor control, pointing, touch**

8. Hourcade, Bederson, Druin & Guimbretière, *Accuracy, Target Reentry and Fitts' Law Performance of Preschool Children Using Mice*, ACM TOCHI, 2004 — https://dl.acm.org/doi/10.1145/1035575.1035577
9. Hourcade, Perry et al., *PointAssist: Helping Four Year Olds Point with Ease*, IDC 2008 — https://dl.acm.org/doi/10.1145/1463689.1463757
10. Vatavu, Cramariuc & Schipor, *Touch interaction for children aged 3 to 6 years: Experimental findings and relationship to motor skills*, IJHCS, 2015 — https://www.sciencedirect.com/science/article/abs/pii/S1071581914001426
11. Anthony, Brown, Nias, Tate & Mohan, *Interaction and Recognition Challenges in Interpreting Children's Touch and Gesture Input on Mobile Devices*, ITS 2012 — https://www.researchgate.net/publication/235410901
12. Anthony et al., *Examining the need for visual feedback during gesture interaction on mobile touchscreen devices for kids*, IDC 2013 — https://dl.acm.org/doi/10.1145/2485760.2485775
13. Soni, Aloba, Morga, Wisniewski & Anthony, *A Framework of Touchscreen Interaction Design Recommendations for Children (TIDRC)*, IDC 2019 — https://dl.acm.org/doi/10.1145/3311927.3323149
14. Inkpen, *Drag-and-Drop versus Point-and-Click Mouse Interaction Styles for Children*, ACM TOCHI, 2001
15. Donker & Reitsma, *Drag-and-drop errors in young children's use of the mouse*, Interacting with Computers, 2007
16. Barendregt & Bekker, *Children May Expect Drag-and-Drop Instead of Point-and-Click*, CHI EA 2011

**Practitioner guidance (Nielsen Norman Group)**

17. NN/g, *UX Design for Children (Ages 3–12), 4th Edition* — 156 guidelines, 399 pp., studies in the US, China and Israel across 80+ websites and 36 apps — https://www.nngroup.com/reports/children-on-the-web/
18. NN/g, *Children's UX: Usability Issues in Designing for Young People* (2019) — https://www.nngroup.com/articles/childrens-websites-usability-issues/
19. NN/g, *Design for Kids Based on Their Stage of Physical Development* (2018) — https://www.nngroup.com/articles/children-ux-physical-development/
20. NN/g, *Designing for Kids: Cognitive Considerations* (2018) — https://www.nngroup.com/articles/kids-cognition/
21. NN/g, *Usability Testing with Minors: 16 Tips* (2019) — https://www.nngroup.com/articles/usability-testing-minors/
22. NN/g, *UX Research with Minors: Consent vs. Assent* (Feb 2026) — https://www.nngroup.com/articles/research-minors-consent/

**Evaluation instruments**

23. Read, MacFarlane & Casey, *Endurability, Engagement and Expectations: Measuring Children's Fun*, IDC 2002 — https://www.researchgate.net/publication/228870976
24. Read, *Validating the Fun Toolkit: An instrument for measuring children's opinions of technology*, Cognition, Technology & Work, 2008 — https://doi.org/10.1007/s10111-007-0069-9
25. Read, Horton et al., *Using the Smileyometer to measure UX with children*, Interacting with Computers, 2025 — https://academic.oup.com/iwc/advance-article/doi/10.1093/iwc/iwaf016/8131678
26. Zaman, Vanden Abeele & De Grooff, *Measuring product liking in preschool children: An evaluation of the Smileyometer and This or That methods*, IJCCI, 2013
27. Sim & Horton, *Investigating Children's Opinions of Games: Fun Toolkit vs. This or That*, IDC 2012
28. Dietz et al., *Giggle Gauge: A Self-Report Instrument for Evaluating Children's Engagement with Technology*, IDC 2020 — https://dl.acm.org/doi/10.1145/3392063.3394393

**Design guidelines from developmental theory**

29. Gelderblom & Kotzé, *Designing Technology for Young Children: What we can learn from theories of cognitive development*, SAICSIT/IDC 2008 — https://dl.acm.org/doi/pdf/10.1145/1456659.1456668
30. Kotzé & Gelderblom, *Designing technology for young children: guidelines grounded in a literature investigation on child development and children's technology* — https://www.semanticscholar.org/paper/885f3a78d2ea5d17912e37e4334d8e9bcc483c6a

**Sessions, transitions and family context**

31. Hiniker, Suh, Cao & Kientz, *Screen Time Tantrums: How Families Manage Screen Media Experiences for Toddlers and Preschoolers*, CHI 2016 — https://faculty.washington.edu/alexisr/ScreenTimeTantrums.pdf
32. Hiniker, Sobel, Hong et al., *Touchscreen Prompts for Preschoolers: Designing Developmentally Appropriate Techniques for Teaching Young Children to Perform Gestures*, IDC 2015 — https://dl.acm.org/doi/10.1145/2771839.2771851

**Ethics, rights and regulation**

33. Van Mechelen, Baykal, Dindler, Eriksson & Iversen, *18 Years of Ethics in Child-Computer Interaction Research: A Systematic Literature Review*, IDC 2020 — https://dl.acm.org/doi/10.1145/3392063.3394407
34. ICO, *Age Appropriate Design Code (Children's Code)* — 15 standards, statutory, in force since Sept 2021 — https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/childrens-information/childrens-code-guidance-and-resources/
35. 5Rights Foundation, *UK's Age Appropriate Design Code: 4 years of global impact* (2025) — https://5rightsfoundation.com/uks-age-appropriate-design-code-four-years-of-global-impact-before-key-review/

**Voice and speech**

36. *Voice assistant technology continues to underperform on children's speech*, JASA Express Letters 5(3), 2025 — https://pubs.aip.org/asa/jel/article/5/3/035201/3338215/Voice-assistant-technology-continues-to
37. The Learning Agency, *Closing the Child Speech Recognition Gap: Evidence, Limitations, and Paths Forward* — https://the-learning-agency.com/guides-resources/closing-the-child-speech-recognition-gap-evidence-limitations-and-paths-forward/
38. *Causal Analysis of ASR Errors for Children*, arXiv:2502.08587, 2025 — https://arxiv.org/abs/2502.08587
39. *Can Conversational Agents Change the Way Children Talk to People?*, IDC 2021 — https://dl.acm.org/doi/abs/10.1145/3459990.3460695

**Children and generative AI (2023–2026)**

40. Dangol, Wolfe, Yoo, Thiruvillakkat, Chickadel & Kientz, *"If anybody finds out you are in BIG TROUBLE": Understanding Children's Hopes, Fears, and Evaluations of Generative AI*, arXiv:2505.16089, 2025 — https://arxiv.org/abs/2505.16089
41. *Once Upon an AI: Six Scaffolds for Child-AI Interaction Design, Inspired by Disney*, IJCCI 2025 / arXiv:2504.08670 — https://arxiv.org/abs/2504.08670
42. *Understanding Parents' Perspectives on Responsible AI for Children's Self-Directed Learning*, CHI 2026 — https://dl.acm.org/doi/full/10.1145/3772318.3790479
43. *When AI Gets It Wrong: Scaffolding AI Hallucination Detection for Children Through Chatbot Creation*, CHI 2026 — https://doi.org/10.1145/3772318.3791480
44. *Safe-Child-LLM: A Developmental Benchmark*, arXiv:2506.13510, 2025 — https://arxiv.org/pdf/2506.13510
45. *What makes children perceive or not perceive minds in generative AI?*, 2025 — https://www.sciencedirect.com/science/article/pii/S2949882125000192

**Conference venues**

46. IDC 2025 (24th ACM Interaction Design and Children, Reykjavik; theme "hope") — https://idc.acm.org/2025/ and proceedings https://dl.acm.org/doi/proceedings/10.1145/3713043
47. IDC 2026 (25th, Brighton UK, 22–25 June 2026; theme "sustainable futures") — https://idc.acm.org/2026/ and proceedings https://dl.acm.org/doi/proceedings/10.1145/3773077
48. IDC 2025 / 2026 paper indexes — https://dblp.org/db/conf/acmidc/idc2025.html and https://dblp.org/db/conf/acmidc/idc2026.html
