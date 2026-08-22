# Child Development, Screen Use, and Digital Wellbeing (2022–2026)

**Research topic 02 for kidnix.** What the current evidence says, and what it implies for how a children's operating system should structure use.

---

## 1. Scope & method

### 1.1 Question

kidnix targets children aged 4–8, centred on 5–6, in a UK family context: a full-screen activity shell with a journal instead of files, bounded sessions with a timer, read-aloud UI, curated creative and learning activities, strong parent controls, zero telemetry, and no browser, store or feed.

This document asks: **given the 2022–2026 evidence base, how should such a system structure a child's use of it?** How long should a session be, how should it end, what feedback and reward are defensible, how should co-use be afforded, and which design patterns are contraindicated.

### 1.2 Method and limits

Sources were gathered by web search and direct retrieval, preferring peer-reviewed papers, official guidance and major institutional reports over journalism. Where a primary source was paywalled (notably the AAP's February 2026 *Pediatrics* policy statement) the finding is reported from the issuing body's own public pages plus corroborating coverage, and flagged as such.

Every finding carries an **evidence-quality tag**:

| Tag | Meaning |
|---|---|
| `META` | Systematic review / meta-analysis |
| `RCT` | Randomised controlled trial |
| `LONG` | Longitudinal / prospective cohort |
| `X-SEC` | Cross-sectional or correlational |
| `QUAL` | Qualitative / interview / diary |
| `GUIDE` | Official guidance or expert consensus |
| `OPINION` | Commentary, advocacy, or reasoned inference |

**Two honest caveats up front.** First, the great majority of the developmental evidence concerns children *under five*, because that is where research funding and policy attention have concentrated. kidnix's core users are 5–6, at the upper edge or just past it. Some extrapolation is unavoidable and is marked where it occurs. Second, effect sizes in this field are small, the designs are overwhelmingly observational, and reverse causation is a live and often unaddressed possibility. Anyone who tells you the science is settled — in either direction — is overselling.

### 1.3 An assumption worth stating

kidnix is not a study in whether children should use screens. It assumes a child will spend some bounded time with a computer and asks how to make that time as good as it can be. That reframing matters, because most of the guidance literature is written to help parents *reduce* screen use, and its recommendations have to be translated before they apply to the design of the thing on the screen.

---

## 2. Key findings by theme

### 2.1 The guidance has moved from hour-counts to context — but not uniformly

The single biggest change in this period is the **American Academy of Pediatrics' January 2026 policy statement and technical report, "Digital Ecosystems, Children, and Adolescents"** ([policy statement](https://publications.aap.org/pediatrics/article/157/2/e2025075320/206129/Digital-Ecosystems-Children-and-Adolescents-Policy), [technical report](https://publications.aap.org/pediatrics/article/157/2/e2025075321/206128/Digital-Ecosystems-Children-and-Adolescents), *Pediatrics* 157(2)) `GUIDE`. It retires the two-hours-or-less framing that had anchored AAP advice for a decade and replaces it with a socio-ecological model plus a **child-centred design** lens — explicitly asking what platform features do to behaviour, not just how many minutes elapsed.

The consumer-facing distillation is the **5 Cs of Media Use** ([AAP](https://www.aap.org/en/patient-care/media-and-children/center-of-excellence-on-social-media-and-youth-mental-health/5cs-of-media-use/), [HealthyChildren](https://www.healthychildren.org/English/family-life/Media/Pages/kids-and-screen-time-how-to-use-the-5-cs-of-media-guidance.aspx)) `GUIDE`:

- **Child** — this child's temperament, age and needs; how *they* respond to media.
- **Content** — quality shapes whether the relationship with media is positive or negative.
- **Calm** — whether the child has non-screen routes to managing emotion and sleep.
- **Crowding out** — what the screen displaces: sleep, physical activity, family time, free play.
- **Communication** — co-viewing, talking about content, adult modelling.

AAP's own framing is that the old hour limits "don't address all of the things children and teens need to have a healthy relationship with media." Co-author Libby Milkovich, quoted in [EdSurge](https://www.edsurge.com/news/2026-02-05-new-aap-screen-time-recommendations-focus-less-on-screens-more-on-family-time), puts it as: "It's not 'how to regulate screen time,' but it's how to use them as a family." AAP's stated aim includes taking "the shame" off parents when the problem is systemic.

**But the retreat from hour-counts is not universal, and it is important not to overstate it.** Coverage of the AAP update ([The Conversation](https://theconversation.com/screen-time-guidelines-for-kids-and-adolescents-have-shifted-as-research-paints-a-more-nuanced-picture-281300)) reports that AAP still advises avoiding screens under 18 months, interaction-oriented content only at 18–24 months, and for ages 2–5 solo use only with high-quality material built around learning goals, with recreational use around an hour a day. The hour did not vanish for young children; it stopped being the headline.

Meanwhile the other major bodies **kept numeric limits**:

- **WHO** ([Guidelines on physical activity, sedentary behaviour and sleep for children under 5](https://www.who.int/publications/i/item/9789241550536), [recommendations](https://www.ncbi.nlm.nih.gov/books/NBK541173/)) `GUIDE`: no sedentary screen time under 2; "no more than 1 hour; less is better" at 2–4; 10–13 hours' sleep and ≥180 minutes' activity at 3–4. WHO rates its own **evidence quality "very low"** while making the recommendations **"strong"** — a candid admission that this is precaution, not proof.
- **Canadian Paediatric Society**, [Screen time and preschool children](https://cps.ca/en/documents/position/screen-time-and-preschool-children) `GUIDE`: four principles — **minimise, mitigate, mindfully use, model**. Under 2, nothing except video chat; 2–5, about an hour or less; no screens an hour before bed. "Mindful use" means choosing content "'at this time', 'for this reason'."
- **Australia**: the [24-Hour Movement Guidelines](https://www.health.gov.au/topics/physical-activity/24-hour-movement-guidelines-for-all-australians) `GUIDE` keep no screens under 2, ≤1 hour at 2–5, ≤2 hours recreational at 5–17; the [eSafety Commissioner](https://www.esafety.gov.au/parents/issues-and-advice/screen-time) `GUIDE` adds a family plan, no screens an hour before bed, and limit-setting tools. Compliance is poor — up to 83% of preschoolers exceed the limits.

### 2.2 The UK position (2026) is the most directly relevant, and the most carefully hedged

The **Early Years Screen Time Advisory Group (EYSTAG)**, co-chaired by Professor Russell Viner and Children's Commissioner Dame Rachel de Souza, reported in March 2026 ([full report, GOV.UK](https://assets.publishing.service.gov.uk/media/69c53daf4a06660f085442a7/EYSTAG_report.pdf)) `GUIDE`, informing new parent guidance on [Best Start in Life](https://beststartinlife.gov.uk/screen-time-under-5s/). [RCPCH](https://www.rcpch.ac.uk/news-events/news/2026-01/rcpch-update-screen-time-online-harms) fed into it via a [consultation response](https://www.rcpch.ac.uk/sites/default/files/2026-02/rcpch_response_to_dfe_early_years_screen_time_and_usage_consultation_february_2026.pdf).

EYSTAG explicitly adopts **the precautionary principle**, stating that "there is currently scientific uncertainty about the nature and extent of the risk," and that "the evidence available on harms and benefits of screen use in young children is emerging and often of low-quality; findings are mixed and some major gaps remain."

Its seven recommendation clusters, compressed:

1. **Who uses screens with children, and how, matters.** Responsive adult interaction during screen use "improves language and thinking skills, and reduces the risks seen with solo and non-interactive receptive screen use."
2. **Time still matters,** precautionarily: under 2 avoid except shared bonding activities; 2–5 "no more than an hour a day, ideally through short chunks (30 minutes or less) and not during mealtimes or near to bedtime."
3. **What children watch is important** — see §2.4.
4. **Safety is paramount** — including a striking line that parents "should not let young children use AI tools, toys or chatbots (even those aimed at young children) until the present state of knowledge improves."
5. **Parents' own screen use** shapes children's; parental phone use in front of young children is associated with worse child outcomes.
6. **Parents need better help identifying quality material.**
7. **Parents should trust their instincts**, supported by evidence.

On thresholds, EYSTAG is unusually blunt: "**None of the literature we identified provided convincing evidence for specific thresholds of screen time**," and studies testing published thresholds "found little difference between those over and under limits" (Przybylski & Weinstein 2019) `X-SEC`. It nonetheless concludes: "we found no convincing evidence that short periods of screen use, of up to 30 minutes, were in and of themselves harmful for young children aged two and over."

It also notes **non-linearity**: harms appear to accelerate past a point rather than accruing evenly. A New Zealand longitudinal cohort (Gath et al., 2026) `LONG` found language and socio-emotional problems rising above ~1.5 h/day at age 2 and peer problems above ~2.5 h/day at age 4. An English birth cohort (Campbell & Cooper 2026; Fish et al. 2026) `LONG` found that nine-month-olds with **up to two hours** of daily screen use were *more* likely to experience daily pretend play, turn-taking and singing than those with **none** — with the picture reversing above three hours; and language associations at age two emerged mainly above ~86 minutes.

That last finding deserves emphasis, because it cuts against the simple dose-response story: **at low doses, screen use in this cohort tracked with *more* rich interaction, not less.** The plausible reading is confounding by engaged, media-literate parenting — but it should make anyone cautious about "less is always better" as a design philosophy.

### 2.3 Passive vs active vs creative use: the type of use moderates almost everything

**The LSAC n=4013 study** (Sanders et al., *IJBNPA* 2019, [Springer](https://link.springer.com/article/10.1186/s12966-019-0881-7)) `LONG` is the canonical citation: children initially aged 10–11 assessed every two years 2010–2014, using **time-use diaries** (better than recall) categorising screen use as social, passive, interactive, educational or other. Total screen time showed **linear** negative associations with all outcomes. But by type: **passive** (TV) was worse across the board; **educational** (e.g. computer for homework) showed **positive** educational outcomes and **no** negative relations with anything else; **interactive** (video games) was positive for educational outcomes and **negative** for others. Effects were **small** — "the small effects of screen time on children's outcomes appear to be moderated by the type of screen time."

Note the awkward result for anyone wanting a clean "interactive good, passive bad" story: interactive use was mixed. **Educational use was the only category positive-or-neutral throughout.**

**Attention.** [Nustad & Abrahamsson, *Frontiers in Psychology* 2026](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2026.1737937/full) `META (mini-review)` synthesises 13 publications on 3–5 year-olds. Passive screen time shows consistent negative association with attention, with neuroimaging evidence of "disrupted attentional network integration." Active screen time *splits*: improved **bottom-up and orienting** attention, **weaker top-down / executive** attention. Content pacing moderates — fast-paced passive content intensifies harms to sustained attention; educational apps supported sustained attention where entertainment content did not. The authors are candid about the field's mess: attention was "defined using seven different frameworks and measured using eight distinct assessment methods," and most studies are correlational.

**Language.** [Madigan et al., *JAMA Pediatrics* 2020](https://pubmed.ncbi.nlm.nih.gov/32202633/) `META` — over 42,000 children. Greater screen quantity → lower language skills; earlier onset → lower language skills. Crucially the moderators flip the sign: **high-quality educational programming and adult co-viewing predicted *better* language outcomes.**

**The contrary longitudinal result.** A 2026 analysis of **Growing Up in Scotland** (n=3,786, ages 5/10/15; [summary](https://www.news-medical.net/news/20260812/The-screen-time-story-gets-more-complicated-as-children-grow-up.aspx)) `LONG` found **no association between total daily screen time and above-average difficulties at ages 5 or 10**. At 15, only very heavy gaming (5+ h/day) correlated with elevated difficulties, and the longitudinal link from 5+ h/day at 5 to difficulties at 10 "was not robust across sensitivity analyses." Guidelines "focusing solely on screen exposure duration may not accurately reflect the complex relationship."

**ABCD.** [Nagata et al., *BMC Public Health* 2024](https://bmcpublichealth.biomedcentral.com/articles/10.1186/s12889-024-20102-x) `LONG` (n=9,538) found higher total screen time associated with all mental health symptoms, strongest for depressive symptoms. A [2025 review of ABCD findings](https://pubmed.ncbi.nlm.nih.gov/40172268/) `META` reports moderate associations with worse mental health, behaviour, academic performance and sleep — but **"effect sizes were modest, with socioeconomic status more strongly associated with each outcome measure."** That last clause is the most useful sentence in the ABCD literature for a designer: it sizes the screen effect, and warns that much of what looks like a screen effect may be a poverty effect wearing a screen's clothes.

### 2.4 Pacing, over-stimulation, and "seductive details"

EYSTAG's fast-vs-slow content box is the most directly actionable piece of official guidance produced in this period, and it is worth reproducing in substance `GUIDE`:

> **Fast-paced visual** content includes frequent scene cuts, camera pans, vivid colours, characters and objects moving on-screen. Good visual composition "should include slow, static shots with limited movement."
>
> **Fast-paced auditory** content includes rapid speech, multiple characters talking at once, dense backing tracks. "Young brains struggle to separate speech from background noise, so character speech presented against a backdrop of silence is easier for young brains to process."
>
> **Fast-paced narrative** includes complex multi-layered stories, frequent topic and scene changes, many characters. Good content contains "repeated sequences and narrative elements that reoccur across episodes."

EYSTAG's derived recommendations: choose content "slower-paced than the equivalent for older viewers," focused on faces, limited movement, simple backgrounds, repetition; avoid "lengthy periods of simple receptive watching, flipping or scrolling"; avoid background TV, which "distract[s] young children's attention from playful, fun and learning activities."

This converges with the learning-science literature. [Hirsh-Pasek et al., "Putting Education in 'Educational' Apps," *Psychological Science in the Public Interest* 2015](https://kathyhirshpasek.com/wp-content/uploads/sites/9/2019/07/apps.pdf) `META (synthesis of experimental work)` establishes **four pillars**: learning happens when children are (1) **active and minds-on**, (2) **engaged** and on-task, (3) finding **meaning** beyond the app, and (4) in **high-quality social interaction** — all "within a context that provides a clear learning goal."

Their negative findings matter as much as the positive ones:

- "Tapping a finger or swiping a screen does not qualify as the kinds of minds-on activity that underpins learning... there must be more than mindless, stimulus-response reactions to on-screen actions." Physical activity is not mental activity.
- Mayer's **coherence principle**: "people learn more deeply when extraneous material is excluded," and extraneous processing "drain[s] limited cognitive processing capacity."
- Parish-Morris et al. (2013) `EXPERIMENTAL` — "bells and whistles" in an e-book "often distracted 3-year-olds from understanding and remembering the story."
- Fisher, Godwin & Seltman (2014) `RCT` — kindergartners in a **highly decorated classroom** were more distracted, more off-task, and had fewer learning gains than those in a less visually busy room.
- Kannass & Colombo (2007) `EXPERIMENTAL` — for 3.5-year-olds, **any** distraction impaired task performance; for 4-year-olds, only continuous distraction did. Distraction resistance is still under construction at kidnix's target age.
- Schmidt et al. (2008) `EXPERIMENTAL` — background TV disrupts play: shorter toy engagement, lower focused attention, even on brief glances.
- The positive counterpoint: **contingent interaction**. "When each touch or swipe is met with an immediate response, children feel in control, maintain their focus, and continue the interaction." Contingency, not stimulation, is what makes interactivity valuable — as in video-chat studies where 24–30-month-olds learn words from contingent partners that they cannot learn from non-contingent video.

Also relevant: Kidd et al. (2012)'s "Goldilocks effect" — information "needs to be appropriate to the age of the growing child, not too complex and not too simple, to maintain a child's interest."

### 2.5 Displacement: sleep, physical activity, and parent–child interaction

Displacement — "crowding out" in the AAP's vocabulary — has the most coherent evidence of any mechanism here, largely because it is arithmetic. A 24-hour day is a closed budget.

- [Janssen et al., *Sleep Medicine Reviews* 2020](https://pubmed.ncbi.nlm.nih.gov/31778942/) `META`: screen time is associated with poorer sleep in infants and toddlers but **not** in preschoolers; physical activity and especially outdoor play were favourably associated with most sleep outcomes in toddlers and preschoolers.
- A [2025 meta-analysis of outdoor play and 24-hour movement behaviours](https://www.sciencedirect.com/science/article/pii/S2095254625001231) `META` finds favourable outcomes for sedentary behaviour, screen time and sleep; compositional analysis makes the closed-budget point explicit — increasing outdoor play "invariably displaces time from other domains."
- EYSTAG `GUIDE`: "Screen use becomes particularly problematic when it crowds out sleep, physical activity, parent-child interaction, creative play, household routines, real-world exploration or learning." It recommends screen-free bedrooms, no screens in the hour before bed, screen-free mealtimes, and (citing the UK CMOs) three hours' daily physical activity for under-fives.
- **Technoference** (parental device use in front of children): EYSTAG cites Chong et al. 2023, Mallawaarachchi et al. 2024, Toledo-Vargas et al. 2025 and Braune-Krickau et al. 2021 `META/LONG` for associations with child emotional and behavioural problems and lower attention, executive function and self-regulation — mechanisms being children escalating to regain attention, and reduced scaffolding. Notably, "**parents using their phones occasionally and for short periods appears to be less disruptive** than phone use over longer time periods": duration, not presence, is the variable.
- CPS `GUIDE`: background television "reduce[s] the amount and quality of parent–child interaction and distract[s] children from play"; "the highest cost of too much screen time for young children is the loss of opportunities for social learning and practice."
- On free play: a 2025 *Journal of Intelligence* review `META` (25 studies) found loose-parts play significantly enhances problem-solving, divergent thinking and academic readiness; a 2025 scoping review (35 studies) `META` documents a clear decline in unstructured free play among 8–10 year-olds.

### 2.6 Co-use and joint media engagement

This is where nearly every source converges, and it is the strongest positive design lever available. Madigan's meta-analysis `META` found co-viewing predicted **better** language outcomes, flipping the sign of the screen-time association. EYSTAG `GUIDE` describes co-viewing — "adults talking, responding to children's interests, asking questions, taking turns, and engaging with the content" — as improving language and thinking skills and reducing "the risks seen with solo and non-interactive receptive screen use"; its first recommendation is literally "think about how you read a book with your child." CPS `GUIDE`: "Preschoolers learn expressive language and vocabulary best from live, direct, and dynamic interactions with caring adults." AAP's fifth C is **Communication**.

**But the JME literature is more equivocal than the guidance implies.** [Ewin et al., *Human Behavior and Emerging Technologies* 2021](https://onlinelibrary.wiley.com/doi/abs/10.1002/hbe2.203) `META` found the impact of joint media engagement on "language quantity, warmth, scaffolding and the overall parent–child relationship was **inconsistent**." Measurement has only recently been standardised ([Koch et al., Joint Media Engagement Scale, *BJDP* 2025](https://bpspsychub.onlinelibrary.wiley.com/doi/10.1111/bjdp.12526) `X-SEC`).

There is also a hard practical constraint. CPS notes co-viewing is **declining** as devices multiply and become portable. Ewin notes parents "are less likely to co-engage with their children when using digital technologies compared to more traditional technologies such as books and television," and that "digital engagement tends to fill a gap for parents rather than becoming a focal point of parent-child interaction." EYSTAG heard the same: "screens are often used to occupy a young child whilst the parent" does something else.

**This is the central design tension for kidnix.** The evidence says co-use is the most protective single factor; the observed reality is that screens are deployed *precisely when the adult is unavailable*. A design that only works well under co-use will fail at the moment it is most used — and will quietly penalise families with less adult time, which correlates with disadvantage.

### 2.7 The psychology of ending screen time

The best evidence here is a decade old and remains the most design-relevant paper in the entire corpus: [Hiniker, Suh, Cao & Kientz, "Screen Time Tantrums: How Families Manage Screen Media Experiences for Toddlers and Preschoolers," *CHI 2016*](https://faculty.washington.edu/alexisr/ScreenTimeTantrums.pdf) `QUAL + X-SEC diary`.

Method: interviews with 27 parents of 1–5 year-olds, then a **separate** diary study of 28 families logging **380 screen-time transitions** over two weeks. Children were 14–66 months (mean 38). Sample was affluent, Seattle-area, all-mother, 86% White — an important limitation.

Findings:

- **93% of parents** reported tantrums, whining or resistance at least occasionally; **37%** said screen time "almost always ends with a fight." Diary base rates were gentler — 59% of transitions neutral, 20% positive, 22% negative — so tantrums are "a non-dominant but routine occurrence."
- **Parents underestimate self-stopping.** Interviewees said children almost never stop unprompted ("rare, really rare"), yet **25% of logged transitions were child-initiated**, the second-most-common trigger.
- **Routine helped**, but cost minutes. Routine periods ended significantly less upsettingly than ad hoc ones (F(1,331)=16.75, p<.001, η²=.048) — but lasted significantly longer (40.0 vs 29.5 min, p=.008).
- **The two-minute warning made things worse.** Children were significantly *more* upset when warned (mean 3.35) than not (3.03); F(1,331)=20.34, p<.001, **η²=.058**, holding after excluding child-initiated transitions (F(1,238)=10.21, p=.002, η²=.041). 21 of 27 parents used warnings anyway, mostly unsure they worked: "the warning doesn't always register," "he knows it, but that doesn't mean he's happy."
- **The dominant trigger was context** (39%): the haircut finished, dinner was ready, time to leave.
- **Technology-mediated transitions were significantly more successful than parent-mediated ones.** Natural stopping points — end of an episode or playlist, a dead battery, lost Wi-Fi — made endings smoother, and parents wanted the technology to take the blame: "If you could be like 'Ope! Computer turned off! Sorry, I can't help you!' it would be nice."
- **Autoplay was the villain.** Eleven of 27 parents named Netflix or YouTube autoplay as something they must actively fight, timing an interruption "at the exact moment when one video ends." One preferred a service requiring deliberate action to continue: "it gives a natural stopping point and the continuity is broken." Another: "Sometimes it does [autostart] ... She'll usually throw a fit."

The authors' conclusion is a direct commission for a project like kidnix: the design community "has the power to make this experience better for parents and children by creating technologies that facilitate boundary-setting and respect families' self-defined limits."

**How much weight should the two-minute-warning finding carry?** Moderate, not decisive. It is a single 2016 study, non-experimental (parents chose when to warn), small and unrepresentative, and the obvious confound is that **parents warn when they anticipate trouble**. The authors attempted to control for child-initiated transitions but could not randomise. The defensible reading is not "never warn" but "**a warning delivered by an adult, interrupting an absorbing experience, is not reliably helpful** — whereas an ending the child can see coming *inside the experience* is."

### 2.8 Self-regulation at 4–8, and children's grasp of time

- Executive function — inhibitory control, working memory, cognitive flexibility — "emerge[s] rapidly during the preschool years" and continues developing into adolescence ([review evidence](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8762317/)) `LONG/EXPERIMENTAL`. A 4–8 year-old is in the middle of building the machinery kidnix will be asking them to use.
- Parenting style matters measurably: children of parents who were "more supportive, were less intrusive, and asked more open-ended questions displayed better inhibitory control" ([study of 4–8 year-olds](https://pubmed.ncbi.nlm.nih.gov/29024846/)) `X-SEC`. *Less intrusive* is a striking finding for anyone designing supervision features.
- Hiniker's own developmental rationale: as children approach 24 months, "their sense of autonomy and internal control systems for language, memory, and inhibitory control all become more sophisticated, leading to independent thinking and goal-setting."
- **Time is abstract and late-developing.** Temporal cognition develops gradually; young children have little reliable sense of duration, and "1, 5, or 10 minutes feels the same way to them." Visual timers are widely recommended in classroom and therapy settings because they render an abstraction concrete — children "see time 'disappear' as the disk elapses." `OPINION/practice literature` — the primary evidence is thin. The closest quantitative work is [a 2025 study of visual timers and anticipatory anxiety in elementary maths assessments](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12731990/) `RCT/quasi-experimental`, which reports effects on anticipatory anxiety, performance and on-task behaviour — but that is an assessment context, not a play context, and it warns that a visible countdown can itself generate anticipatory anxiety. Broader developmental work on [time perception in children](https://www.sciencedirect.com/science/article/abs/pii/S0028393212003958) `EXPERIMENTAL` establishes that duration judgement is immature and highly susceptible to emotional and attentional state — an absorbed child genuinely experiences less elapsed time.

**Design consequence:** a timer for a 5-year-old is not an information display. It is an emotional object. Whether it reduces or manufactures distress depends entirely on its framing.

### 2.9 Reward loops, gamification, and manipulative design

**The prevalence data are damning.** [Radesky et al., *JAMA Network Open* 2022, "Prevalence and Characteristics of Manipulative Design in Mobile Applications Used by Children"](https://www.semanticscholar.org/paper/c7f01914a8807c515f5e022bef8a6f5a24852fa7) `X-SEC` analysed the apps actually used by **160 children aged 3–5**. **80% of apps** contained manipulative design; only 20% had none, and **~99% of children** met at least one. The categories: **parasocial relationship pressure** (a character begging the child not to leave), **fabricated time pressure** (countdown timers with no real stake), **navigation constraints**, **attractive lures** to extend play or prompt purchase, **return incentives** ("come back tomorrow and get a dragon"), **idle-state prompting**, **reward accumulation**, and **ads requiring 20+ seconds before a close option appears**. There was a **socioeconomic gradient** — these designs were disproportionately in apps used by children whose parents had not completed college. Radesky: "design features created to serve the interests of technology companies over children is common and we need more regulations in place." ([Michigan Medicine](https://www.michiganmedicine.org/health-lab/design-tricks-commonly-used-monetize-young-childrens-app-use), [EurekAlert](https://www.eurekalert.org/news-releases/956153))

**Persuasive design at scale.** 5Rights Foundation's [*Disrupted Childhood: The Cost of Persuasive Design*](https://5rightsfoundation.com/wp-content/uploads/2024/08/5rights_DisruptedChildhood_G.pdf) (2018, updated 2023) `OPINION/advocacy synthesis` documents how persuasive design deployed to maximise data collection affects children's social, mental and physical development, making 24 recommendations across industry, government, parents and investors. Its core claim: the digital environment's "dependence on persuasive design ... can increase risk, limit creativity and even stifle development."

5Rights' [**Infinite Scroll**](https://5rightsfoundation.com/infinite-scroll-groundbreaking-study-reveals-tiktokisation-of-children-online/) study `QUAL + telemetry` captured minute-by-minute device data from 21 UK children on TikTok: **~708 videos per day**, about **half watched for ≤5 seconds**, **76% used the app between midnight and 6am**, ads roughly every fifth video. Children reported struggling to disengage, losing track of time, difficulty concentrating on longer content, and feelings of guilt and tiredness. Alongside: 63% of parents say infinite scroll makes boundaries harder; 47% of children reported a video autostarting that made them feel worried or confused; 57% "kept watching anyway." 5Rights argues regulators should target **the mechanisms**, not access alone.

**The intrinsic-motivation problem with points.** [Deci, Koestner & Ryan (1999)](https://depts.washington.edu/techdocs/papers/deciExtrinsicRewardsAndIntrinsicMotivation99.pdf) `META` remains canonical: **tangible, expected, contingent rewards substantially undermine intrinsic motivation** — the overjustification effect. Cognitive Evaluation Theory supplies the moderator: rewards conveying **information about competence** can *increase* intrinsic motivation; rewards experienced as **controlling** decrease it. A real, designable distinction.

**Where the evidence is genuinely weak:** there is remarkably little direct evidence that variable-ratio reinforcement schedules specifically harm *young children*. The dopamine-loop literature is drawn largely from adult free-to-play gaming and is often commercial or low-quality. The case against streaks and variable rewards in a 5-year-old's OS rests on the overjustification meta-analysis, the Radesky prevalence data plus a plausible mechanism, and precaution — not on demonstrated causal harm. Say so.

### 2.10 Rights-based design frameworks

Two frameworks translate the above into design obligations.

**[Child Rights by Design](https://childrightsbydesign.5rightsfoundation.com/page/child-rights-by-design/)** (Livingstone & Pothong, Digital Futures Commission / 5Rights, 2023; [LSE record](https://eprints.lse.ac.uk/119724/)) `GUIDE` — 11 UNCRC-derived principles: Equity and Diversity, Best Interests, Consultation, Age Appropriate, Responsible, Participation, Privacy, Safety, **Wellbeing**, **Development**, **Agency**. Associated [CHI 2024 research](https://dl.acm.org/doi/fullHtml/10.1145/3628516.3655789) `QUAL` found designers commonly believe children's rights are satisfied by protection from risk alone, neglecting rights to provision and participation — a trap kidnix should consciously avoid.

**[Designing for Children's Rights](https://childrensdesignguide.org/)** (D4CR) `GUIDE` — 10 principles from 70+ contributors, grouped under Inclusion, Play & Learning, and Safety & Sustainability: gather and respect children's views; everyone can use; use communication children can understand; allow and support exploration; encourage children to play with others; **create a balanced environment**; keep children safe; do not misuse children's data; help children recognise commercial activities; design for future.

---

## 3. Design principles for kidnix

**1. Default a session to 20–30 minutes for 5–6 year-olds, parent-configurable 10–45; treat one hour a day as the soft ceiling.** EYSTAG found "no convincing evidence that short periods of screen use, of up to 30 minutes, were in and of themselves harmful" for over-2s, and recommends "short chunks (30 minutes or less)"; WHO/CPS/Australia converge on ~1 h/day at 2–5; Hiniker's observed mean session was 33 minutes. `GUIDE` + `X-SEC`. **State honestly** that no specific number has an evidential basis — this is precaution plus convergent consensus, and the parent must be able to override it.

**2. Build every activity as a bounded unit with a real completion state.** The strongest transition finding in the corpus is that **natural stopping points make endings smoother** (Hiniker `QUAL/X-SEC`). Activities must *finish* — a painting is done, a story ends, a puzzle set completes. The session timer should **round to the nearest activity boundary rather than cut mid-activity**.

**3. Let the machine own the ending, not the adult.** Technology-mediated transitions were significantly more successful than parent-mediated ones, and parents explicitly wanted the device to take the blame (Hiniker `QUAL`). kidnix should end the session itself, visibly and impersonally. Corollary: **the parent must never have to be the one who taps "stop."**

**4. Make the ending predictable and in-experience, not an interruption.** Routine reduced transition distress (η²=.048); adult-delivered warnings *increased* it (η²=.058) (Hiniker `X-SEC`). The child should see the ending approaching **as part of the activity's own state** — a continuously depleting visual budget, a "last activity" that is visibly last — rather than a modal alert two minutes out that stops the experience to announce that the experience will stop.

**5. Use a continuous analogue time display, not digits, and give it a wind-down phase.** Under-8s' duration judgement is immature and emotionally labile `EXPERIMENTAL`; visual timers make the abstraction concrete (`OPINION`/practice, modest quasi-experimental support). Use a depleting shape or "how many things are left." Because visible countdowns can generate anticipatory anxiety, frame the final phase as **"time to finish up and put your work in the journal,"** not as time draining away.

**6. End with a ritual the child performs, and make saving the child's act.** Hiniker's parents describe rituals — the tablet into its case, plugged in to recharge — as what helps. A 10–20 second closing sequence where the child watches their work land in the journal and puts the machine to sleep converts an interruption into a completion. **Autosave continuously anyway**: a tantrum about lost work is a tantrum kidnix caused. `QUAL` + `OPINION`.

**7. Hand the child back to the physical world at the end.** Displacement is the best-evidenced mechanism `META`. The closing screen should offer one concrete offline continuation tied to what the child just did — "you drew a fox; can you find something fox-coloured in the garden?" — not a generic "go and play." The cheapest way to make a session a bridge rather than a substitute.

**8. Reward only with the artefact and with informational feedback about competence.** Deci, Koestner & Ryan `META`: tangible expected rewards undermine intrinsic motivation; **informational** feedback about competence supports it. Permissible: the thing the child made, visible in the journal; specific descriptive feedback ("you used five different colours"); unlocking genuinely more interesting capability as skill grows. Prohibited: points, coins, stars, badges, levels, collectibles.

**9. No time-based or attendance-based reward of any kind.** Streaks, daily-login bonuses, "come back tomorrow" incentives and idle-state prompting are precisely the manipulative-design taxonomy Radesky found in 80% of preschool apps `X-SEC`. They reward *returning* rather than *doing*. **The system must have no interest in whether the child comes back.**

**10. Give the child a genuine, low-friction way to stop early.** 25% of Hiniker's logged transitions were child-initiated — far more than parents believed — and children were "generally happy about the transitions they initiated" `X-SEC`; agency is also a Child Rights by Design principle. An always-available "I'm finished" that runs the same dignified closing ritual, and never nags, never asks "are you sure?", never bribes the child to stay.

**11. Design co-use as an invitation, never a requirement.** Co-viewing is the strongest protective moderator in the literature (Madigan `META`; EYSTAG, CPS, AAP `GUIDE`), but it is declining, unevenly available, and least present exactly when screens are most used (Ewin `META`; EYSTAG `QUAL`). Build explicit **grown-up turn** moments, conversation prompts in the child's words, natural two-player modes, and a journal designed to be *shown* — but every activity must work fully solo. Requiring co-use penalises families with least adult time: a fairness failure, not just a usability one.

**12. Make the journal the co-use surface.** "Think about how you read a book with your child" (EYSTAG `GUIDE`). The highest-leverage co-use moment for a busy family is probably **after** the session: five minutes looking through what the child made, with the child narrating. Design the journal for that — chronological, child-narratable, no adult-facing analytics, no scores.

**13. Apply EYSTAG's slow-content rules to the OS chrome itself, not just to content.** `GUIDE` No auto-rotating carousels, no ambient looping animation, no simultaneous voice and music, no more than one thing moving at once, consistent screen furniture in consistent places. The shell should be visually **quiet**.

**14. Strip extraneous stimulation — the coherence principle.** "People learn more deeply when extraneous material is excluded"; decorated classrooms reduced learning; e-book bells and whistles impaired 3-year-olds' comprehension (Hirsh-Pasek `META`; Fisher `RCT`; Kannass & Colombo `EXPERIMENTAL`). Every celebratory animation, sound effect and mini-game must justify itself against the activity's goal. Default to none.

**15. Make interaction contingent and consequential, never merely responsive.** "Tapping a finger or swiping a screen does not qualify as the kinds of minds-on activity that underpins learning," yet immediate contingent response is what makes a child "feel in control, maintain their focus, and continue the interaction" (Hirsh-Pasek `META`). Respond instantly to every input, but make inputs *choices with consequences* rather than stimulus-response taps.

**16. Every activity should have a stated learning or creative goal, visible to the parent.** The fifth element of the four-pillars framework is "a supported learning goal," and EYSTAG identified parents' inability to judge quality as an unmet need `GUIDE`. One honest line per activity — including "this one is just for fun" where true.

**17. Protect sleep structurally.** No screens in the hour before bed (EYSTAG, CPS, eSafety `GUIDE`); screen time is associated with poorer sleep in infants and toddlers `META`. A parent-set bedtime lockout that makes the machine simply unavailable, with warmer, dimmer treatment as it approaches — not a nag, an unavailability.

**18. Reflect real-world context, since context is what actually ends screen time.** 39% of transitions ended because the situation changed `X-SEC`. Support parent-set schedule windows (before school, after tea) so the session boundary coincides with a real household boundary.

**19. Prefer educational and creative activity types; treat purely receptive content as a minority mode.** LSAC `LONG` found educational screen time positively associated with educational outcomes and *not* negatively associated with anything else — the only category with that profile. Passive was uniformly worse; interactive was mixed. Frontiers 2026 `META` found educational apps supported sustained attention where entertainment content did not.

**20. Keep parent controls low-intrusion.** Children of "less intrusive" parents showed better inhibitory control `X-SEC`; AAP aims to reduce parental shame; EYSTAG's final recommendation is that parents trust their instincts. Controls should set the *shape* of the sandbox — session length, schedule, available activities — then get out of the way. Given zero telemetry there is nothing to report anyway: no surveillance dashboard, no engagement metrics, no "screen time score."

---

## 4. Things the evidence says NOT to do

1. **No autoplay, "up next," or continuous playback.** The most consistently named villain in the transition literature; parents describe actively fighting it and attribute tantrums to it directly (Hiniker `QUAL`).
2. **No infinite or endlessly-replenishing feeds.** 5Rights' data (708 videos/day, half watched under five seconds) is what removing stopping points does `QUAL/telemetry`.
3. **No algorithmic recommendation or personalised surfacing.** A fixed, parent-visible library — not a system that learns what holds this child longest.
4. **No streaks, daily-login rewards, or "come back tomorrow" incentives** — documented manipulative-design categories `X-SEC` that optimise for return frequency, which is not a child-welfare goal.
5. **No fabricated time pressure.** Countdown timers with no real stake are a named manipulative pattern `X-SEC`. The session timer is real; nothing else should imitate it.
6. **No parasocial pressure.** Characters must never plead with the child to stay, express sadness at being left, or "miss" them — a documented preschool-app pattern that manipulates attachment machinery a 5-year-old cannot yet discount `X-SEC`.
7. **No notifications or any mechanism that summons a child back.** kidnix should be inert when not in use.
8. **No advertising, in-app purchase, branded content, or commercial persuasion** — Radesky `X-SEC`, D4CR principle 9, EYSTAG's safeguarding section.
9. **No leaderboards, scores, social comparison, or public counts.** AAP cites reducing public "like" counts as a design change that eases pressure `GUIDE`.
10. **No open-ended chatbot or generative AI conversational partner for this age group.** EYSTAG is unusually direct: parents "should not let young children use AI tools, toys or chatbots (even those aimed at young children) until the present state of knowledge improves" `GUIDE`. Deterministic, curated read-aloud is a different thing and is fine.
11. **No abrupt mid-activity termination that loses work.** Children resist endings; that is no reason to punish them with one.
12. **No modal adult-voiced "2 minutes left!" interruption** — the only quantitative evidence on this pattern says it makes things worse `X-SEC`, with the caveats in §2.7.
13. **No ambient motion, background music under speech, or simultaneous voices** — contrary to EYSTAG's pacing guidance and the coherence principle `GUIDE` + `META`.
14. **No engagement metrics anywhere**, including in parent controls. What gets measured gets optimised, and no version of "time on device" is a health outcome.
15. **Do not require co-use for core function.** Equity failure; see §2.6.

---

## 5. Open questions and contested areas

**5.1 The effect-size war is unresolved, and both camps overclaim.** Orben & Przybylski's [time-use-diary analyses](https://journals.sagepub.com/doi/10.1177/0956797619830329) `X-SEC/specification-curve` found the average association between screen use and adolescent wellbeing roughly the size of the association with wearing glasses. Twenge et al.'s [commentary](https://pmc.ncbi.nlm.nih.gov/articles/PMC7040178/) `X-SEC` replicated the specification curve, then argued that lumping TV in with social media dilutes real effects and that dismissing retrospective measures discards usable signal. Both are right about something: analytic flexibility really can manufacture whichever answer you want, *and* "screen time" as a construct really is nearly meaningless. **Neither side's headline supports designing around a minute count** — which is, ironically, where the AAP landed.

**5.2 Guidance bodies now disagree.** AAP has dropped hour-limits as a headline; WHO, the UK, Canada and Australia all keep ~1 h/day for 2–5s. A genuine, unresolved divergence. kidnix should implement a configurable limit and document that the number is precautionary.

**5.3 "Active good, passive bad" is too simple.** LSAC found interactive screen time positive for *educational* outcomes and negative for everything else; Frontiers 2026 found active use improving bottom-up attention while *weakening* top-down/executive attention. A creative shell is probably on the right side of this, but "it's interactive so it's fine" is not what the evidence says.

**5.4 Reverse causation is under-addressed.** EYSTAG cites evidence that "a child struggling to maintain focus on activities is as likely to influence that child's screen use as screen use is to influence attention" (Jourdren et al. 2023), plus vicious cycles with anger problems (Fitzpatrick et al. 2024) `LONG`. Radesky's work `LONG` supports bidirectionality: difficult behaviour increases device use as caregivers reach for a calming tool.

**5.5 The low-dose finding is unexplained.** English birth-cohort data showing nine-month-olds with up to two hours' screen use experiencing *more* pretend play, turn-taking and singing than those with none `LONG` is either confounding or a real signal about engaged families. Nobody knows which.

**5.6 The two-minute-warning finding needs replication.** Single study, 2016, n=28 families, homogeneous sample, non-randomised. It is the best evidence on this exact question and it is not strong evidence. Designing around it is reasonable; treating it as settled is not.

**5.7 Visual timers for young children are under-evidenced.** The practice literature is confident; the empirical literature is thin and mostly from assessment or special-education contexts. Whether a visible depleting timer *reduces* end-of-session distress or *manufactures* clock-watching in a 5-year-old is an open empirical question — one kidnix is unusually well placed to answer.

**5.8 Variable-ratio reinforcement harms in young children are assumed, not demonstrated.** The prohibition in §4 rests on the overjustification meta-analysis, prevalence data, mechanism plausibility and precaution — not a clean causal study in 4–8 year-olds. Right call, honest reasons.

**5.9 Read-aloud UI has no wellbeing evidence base.** No source found here evaluates text-to-speech for pre-readers as a developmental intervention. The case is one of **autonomy and access** — D4CR principle 3, Child Rights by Design's Agency principle — not wellbeing outcomes, and should be argued on those grounds.

**5.10 Interventions to reduce screen time mostly don't work.** Jones et al. (2021) `META` found no significant impact on reducing screen time in under-fives. A warning about kidnix's theory of change: a well-designed environment may improve the *quality* of a child's time without changing the *quantity*, and that may be the realistic win.

---

## 6. Top 10 takeaways

1. **The field has moved from "how long?" to "what, with whom, instead of what, and designed how?"** — AAP's 5 Cs and EYSTAG's recommendation ordering both put *how screens are used* ahead of *how much*.
2. **Nobody can evidence a specific time threshold.** EYSTAG says so explicitly; WHO rates its own evidence "very low" while making a strong recommendation. Every number in circulation is precaution.
3. **The defensible number, if you need one, is ~30-minute chunks within ~1 hour a day** for this age — the point of convergence between WHO, CPS, Australia, EYSTAG and observed session lengths.
4. **Natural stopping points are the highest-leverage design intervention available** for the ending problem, and autoplay is its direct negation.
5. **Let the machine end the session, not the parent** — technology-mediated transitions are measurably smoother, and parents actively want this.
6. **Adult-delivered warnings made transitions worse in the only study that measured it.** Predictable, in-experience endings are the better bet.
7. **Co-use is the strongest protective factor in the literature and the least reliably available in practice.** Afford it richly; never require it.
8. **80% of the apps preschoolers actually use contain manipulative design.** The bar kidnix has to clear is embarrassingly low, and clearing it deliberately is itself a product feature.
9. **Points, streaks and badges are the wrong reward.** Tangible expected rewards undermine intrinsic motivation; informational feedback about competence supports it. The artefact in the journal is the reward.
10. **Displacement is the mechanism with the best evidence, so design for handoff.** Sleep protection, real-household schedule boundaries, and an offline continuation at the end of every session do more good than any amount of on-screen quality.

---

## 7. Full source list

### Official guidance and institutional reports
1. American Academy of Pediatrics — [*Digital Ecosystems, Children, and Adolescents: Policy Statement*](https://publications.aap.org/pediatrics/article/157/2/e2025075320/206129/Digital-Ecosystems-Children-and-Adolescents-Policy), *Pediatrics* 157(2), e2025075320, Feb 2026. `GUIDE`
2. AAP — [*Digital Ecosystems, Children, and Adolescents: Technical Report*](https://publications.aap.org/pediatrics/article/157/2/e2025075321/206128/Digital-Ecosystems-Children-and-Adolescents), *Pediatrics* 157(2), e2025075321. `GUIDE`
3. AAP — [The 5 Cs of Media Use](https://www.aap.org/en/patient-care/media-and-children/center-of-excellence-on-social-media-and-youth-mental-health/5cs-of-media-use/). `GUIDE`
4. AAP HealthyChildren — [Kids & Screen Time: How to Use the 5 C's of Media Guidance](https://www.healthychildren.org/English/family-life/Media/Pages/kids-and-screen-time-how-to-use-the-5-cs-of-media-guidance.aspx). `GUIDE`
5. AAP — [Understanding the New AAP Digital Media Guidelines](https://www.aap.org/en/patient-care/media-and-children/center-of-excellence-on-social-media-and-youth-mental-health/understanding-the-new-AAP-digital-media-guidelines/) (updated 20 Jan 2026). `GUIDE`
6. AAP News — [Beyond screen time: Policy discusses how to approach immersive digital ecosystem](https://publications.aap.org/aapnews/news/34088/Beyond-screen-time-Policy-discusses-how-to). `GUIDE`
7. WHO — [*Guidelines on physical activity, sedentary behaviour and sleep for children under 5 years of age*](https://www.who.int/publications/i/item/9789241550536) (2019); [recommendations detail](https://www.ncbi.nlm.nih.gov/books/NBK541173/). `GUIDE`
8. Early Years Screen Time Advisory Group — [*Screen use by children aged under five: independent report*](https://assets.publishing.service.gov.uk/media/69c53daf4a06660f085442a7/EYSTAG_report.pdf), DfE/DHSC, March 2026. `GUIDE`
9. UK Government — [Baby and toddler screen time guidance, Best Start in Life](https://beststartinlife.gov.uk/screen-time-under-5s/), 27 March 2026. `GUIDE`
10. RCPCH — [Update on screen time and online harms](https://www.rcpch.ac.uk/news-events/news/2026-01/rcpch-update-screen-time-online-harms), Jan 2026. `GUIDE`
11. RCPCH — [Response to DfE early years screen time consultation](https://www.rcpch.ac.uk/sites/default/files/2026-02/rcpch_response_to_dfe_early_years_screen_time_and_usage_consultation_february_2026.pdf), Feb 2026. `GUIDE`
12. Canadian Paediatric Society — [*Screen time and preschool children: Promoting health and development in a digital world*](https://cps.ca/en/documents/position/screen-time-and-preschool-children). `GUIDE`
13. Australian Government Department of Health — [24-hour movement guidelines](https://www.health.gov.au/topics/physical-activity/24-hour-movement-guidelines-for-all-australians). `GUIDE`
14. eSafety Commissioner (Australia) — [Screen time: how much is too much?](https://www.esafety.gov.au/parents/issues-and-advice/screen-time). `GUIDE`
15. Ofcom — *Children and Parents: Media Use and Attitudes Report 2025* (cited via EYSTAG). `X-SEC`

### Peer-reviewed empirical studies and reviews
16. Sanders, T. et al. — [Type of screen time moderates effects on outcomes in 4013 children: evidence from the Longitudinal Study of Australian Children](https://link.springer.com/article/10.1186/s12966-019-0881-7), *IJBNPA* 2019. `LONG`
17. Nustad & Abrahamsson — [Passive and active screen time relate differently to attention in preschool children](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2026.1737937/full), *Frontiers in Psychology* 2026. `META (mini-review)`
18. Madigan, S. et al. — [Associations Between Screen Use and Child Language Skills: A Systematic Review and Meta-analysis](https://pubmed.ncbi.nlm.nih.gov/32202633/), *JAMA Pediatrics* 2020. `META`
19. Growing Up in Scotland screen-use analysis (Edinburgh / Imperial, n=3,786) — [summary](https://www.news-medical.net/news/20260812/The-screen-time-story-gets-more-complicated-as-children-grow-up.aspx), 2026. `LONG`
20. Nagata, J. et al. — [Screen time and mental health: a prospective analysis of the ABCD Study](https://bmcpublichealth.biomedcentral.com/articles/10.1186/s12889-024-20102-x), *BMC Public Health* 2024. `LONG`
21. [What we know about screen time and social media in early adolescence: a review of ABCD findings](https://pubmed.ncbi.nlm.nih.gov/40172268/), 2025. `META`
22. Hiniker, A., Suh, H., Cao, S. & Kientz, J. — [Screen Time Tantrums: How Families Manage Screen Media Experiences for Toddlers and Preschoolers](https://faculty.washington.edu/alexisr/ScreenTimeTantrums.pdf), *CHI 2016*. `QUAL + X-SEC`
23. Radesky, J. et al. — [Prevalence and Characteristics of Manipulative Design in Mobile Applications Used by Children](https://www.semanticscholar.org/paper/c7f01914a8807c515f5e022bef8a6f5a24852fa7), *JAMA Network Open* 2022; [Michigan Medicine summary](https://www.michiganmedicine.org/health-lab/design-tricks-commonly-used-monetize-young-childrens-app-use). `X-SEC`
24. Hirsh-Pasek, K., Zosh, J., Golinkoff, R. et al. — [Putting Education in "Educational" Apps: Lessons From the Science of Learning](https://kathyhirshpasek.com/wp-content/uploads/sites/9/2019/07/apps.pdf), *Psychological Science in the Public Interest* 16(1), 2015. `META`
25. Deci, E., Koestner, R. & Ryan, R. — [A Meta-Analytic Review of Experiments Examining the Effects of Extrinsic Rewards on Intrinsic Motivation](https://depts.washington.edu/techdocs/papers/deciExtrinsicRewardsAndIntrinsicMotivation99.pdf), *Psychological Bulletin* 1999. `META`
26. Ewin, C. et al. — [The impact of joint media engagement on parent–child interactions: A systematic review](https://onlinelibrary.wiley.com/doi/abs/10.1002/hbe2.203), *Human Behavior and Emerging Technologies* 2021. `META`
27. Koch, F.-S. et al. — [The Joint Media Engagement Scale (JMES)](https://bpspsychub.onlinelibrary.wiley.com/doi/10.1111/bjdp.12526), *British Journal of Developmental Psychology* 2025. `X-SEC`
28. Janssen, X. et al. — [Associations of screen time, sedentary time and physical activity with sleep in under 5s: A systematic review and meta-analysis](https://pubmed.ncbi.nlm.nih.gov/31778942/), *Sleep Medicine Reviews* 2020. `META`
29. [A systematic review and meta-analyses of the relationships between active outdoor play and 24-hour movement behaviors](https://www.sciencedirect.com/science/article/pii/S2095254625001231), 2025. `META`
30. Orben, A. & Przybylski, A. — [Screens, Teens, and Psychological Well-Being: Evidence From Three Time-Use-Diary Studies](https://journals.sagepub.com/doi/10.1177/0956797619830329), *Psychological Science* 2019. `X-SEC`
31. Twenge, J. et al. — [Commentary on Orben & Przybylski](https://pmc.ncbi.nlm.nih.gov/articles/PMC7040178/). `X-SEC`
32. [Attentional control and executive functioning in school-aged children: Linking self-regulation and parenting strategies](https://pubmed.ncbi.nlm.nih.gov/29024846/), 2017. `X-SEC`
33. [Inhibitory Control in Children 4–10 Years of Age: fNIRS Task-Based Observations](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8762317/), 2022. `EXPERIMENTAL`
34. Droit-Volet, S. — [Time perception in children: A neurodevelopmental approach](https://www.sciencedirect.com/science/article/abs/pii/S0028393212003958), *Neuropsychologia* 2013. `EXPERIMENTAL`
35. [Time on Their Side: How Visual Timers Affect Anticipatory Anxiety, Performance, and On-Task Behavior in Elementary Math Assessments](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12731990/), *EJIHPE* 2025. `RCT/quasi-experimental`
36. [Applying children's rights to digital products: Exploring competing priorities in design](https://dl.acm.org/doi/fullHtml/10.1145/3628516.3655789), *CHI 2024*. `QUAL`
37. Studies cited via EYSTAG: Gath et al. 2026 (NZ longitudinal thresholds) `LONG`; Campbell & Cooper 2026 and Fish et al. 2026 (English birth cohort) `LONG`; Chong et al. 2023, Mallawaarachchi et al. 2024, Toledo-Vargas et al. 2025, Braune-Krickau et al. 2021 (technoference) `META/LONG`; Jourdren et al. 2023, Fitzpatrick et al. 2024 (reverse causation) `LONG`; Przybylski & Weinstein 2019 (threshold testing) `X-SEC`; Kidd et al. 2012 (Goldilocks effect) `EXPERIMENTAL`.
38. Studies cited via Hirsh-Pasek et al. 2015: Fisher, Godwin & Seltman 2014 (classroom visual distraction) `RCT`; Parish-Morris et al. 2013 (e-book "bells and whistles") `EXPERIMENTAL`; Schmidt et al. 2008 (background TV and play) `EXPERIMENTAL`; Kannass & Colombo 2007 (distraction in 3.5–4 year-olds) `EXPERIMENTAL`; Roseberry, Hirsh-Pasek & Golinkoff 2014 (contingent video interaction) `RCT`.
39. Jones, A. et al. (2021) — meta-analysis of interventions to reduce screen time in under-5s, cited via [Psychology Today](https://www.psychologytoday.com/us/blog/the-whimsical-child/202601/growing-up-digital-and-the-implications-of-screen-use). `META`
40. Loose-parts play systematic review, *Journal of Intelligence* 2025 (25 studies) `META`; scoping review of free-play decline in 8–10 year-olds, 2025 (35 studies) `META`.

### Design frameworks and advocacy reports
41. Livingstone, S. & Pothong, K. — [*Child Rights by Design: Guidance for Innovators of Digital Products and Services Used by Children*](https://childrightsbydesign.5rightsfoundation.com/page/child-rights-by-design/), Digital Futures Commission / 5Rights Foundation, 2023; [LSE record](https://eprints.lse.ac.uk/119724/). `GUIDE`
42. Designing for Children's Rights (D4CR) — [10 design principles](https://childrensdesignguide.org/). `GUIDE`
43. 5Rights Foundation — [*Disrupted Childhood: The Cost of Persuasive Design*](https://5rightsfoundation.com/wp-content/uploads/2024/08/5rights_DisruptedChildhood_G.pdf), 2018, updated 2023. `OPINION`
44. 5Rights Foundation — [*Infinite Scroll*](https://5rightsfoundation.com/infinite-scroll-groundbreaking-study-reveals-tiktokisation-of-children-online/), 2025/26. `QUAL + telemetry`

### Secondary coverage used for corroboration
45. [Screen time guidelines for kids and adolescents have shifted as research paints a more nuanced picture](https://theconversation.com/screen-time-guidelines-for-kids-and-adolescents-have-shifted-as-research-paints-a-more-nuanced-picture-281300), *The Conversation*, 2026.
46. [UK government recommends maximum one hour of screen time for younger children: what the evidence says](https://theconversation.com/uk-government-recommends-maximum-one-hour-of-screen-time-for-younger-children-what-the-evidence-says-275752), *The Conversation*, 2026.
47. [New AAP 'Screen Time' Recommendations Focus Less on Screens, More on Family Time](https://www.edsurge.com/news/2026-02-05-new-aap-screen-time-recommendations-focus-less-on-screens-more-on-family-time), *EdSurge*, Feb 2026.
48. [AAP calls for system-level changes to improve children's digital media environments](https://www.contemporarypediatrics.com/view/aap-calls-for-system-level-changes-to-improve-children-s-digital-media-environments), *Contemporary Pediatrics*, 2026.
49. [Two-minute warnings make kids' 'screen time' tantrums worse](https://www.washington.edu/news/2016/05/05/two-minute-warnings-make-kids-screen-time-tantrums-worse/), University of Washington, 2016.
50. [Design tricks commonly used to monetize young children's app use](https://www.eurekalert.org/news-releases/956153), EurekAlert / University of Michigan, 2022.

---

*Assumptions and limitations of this review: the AAP February 2026 policy statement and technical report were paywalled and are reported from AAP's own public materials plus corroborating coverage. The LSAC and several PMC-hosted papers were behind access controls and are reported from abstracts and indexed summaries. Most developmental evidence concerns under-5s and has been extrapolated to kidnix's 5–8 band where noted. Search was conducted in August 2026; the guidance landscape in this area is currently changing faster than the underlying evidence.*
