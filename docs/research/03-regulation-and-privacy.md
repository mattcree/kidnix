# 03 — Regulation, Privacy, Safety-by-Design and Children's Rights

Research note for **kidnix**: an immutable, open-source Linux OS for children aged roughly 4–8 (centred on 5–6), UK family context, full-screen activity shell, journal instead of files, bounded sessions, read-aloud UI, curated activities, strong parent controls, zero telemetry, no browser/store/feeds by default.

**Status:** research note, not legal advice. Written August 2026.

---

## 1. Scope & method

### 1.1 What this note covers

The regulatory, rights-based and standards landscape a children's operating system built in 2026 sits inside, and the concrete, testable design defaults each framework implies.

Sources are primary where reachable (ICO, Ofcom, European Commission, FTC, eSafety, OHCHR, UNICEF, 5Rights, ISO, IEEE, W3C) and specialist law-firm analysis where primary sites blocked automated retrieval — ICO pages return HTTP 403 to non-browser clients, so the 15 standards are reconstructed from a faithful secondary summary. Full list in §7.

### 1.2 The critical framing: which kidnix are we regulating?

Almost every framework below turns on *what kidnix is legally*, and the answer changes as the project grows. Three postures:

| Posture | Description | Regulatory exposure |
|---|---|---|
| **A. Private household** | Author builds it, runs it on his own children's device, no distribution | Near-zero. GDPR Art. 2(2)(c) household exemption applies to the *parent's* processing; no controller/processor relationship with anyone else. Not an "information society service". Not COPPA. Not OSA. |
| **B. Distributed artefact** | Source + images published on the internet, free, no accounts, no servers, no telemetry | Still no personal-data controller relationship (no data reaches the author). Not an "online service" in the ICO/COPPA sense. But: product-liability/product-safety and EU Cyber Resilience Act questions become live, accessibility law becomes relevant if procured by a public body, and licensing compliance for bundled content becomes mandatory. |
| **C. Service-attached product** | Any of: account system, journal sync, content store, crash reporting, LLM/TTS API calls, update telemetry | Full weight. ICO Children's Code, UK GDPR + DUAA 2025 children's provisions, GDPR Art. 8, COPPA (if US users), DSA Art. 28 (if it becomes an "online platform"). |

**The governing assumption for this note:** kidnix should be designed to satisfy posture C's requirements while shipping in posture B. This costs almost nothing at design time (the requirements *are* the good design), and it is very expensive to retrofit. Every requirement in §3 is written to that standard.

A second assumption: **the ICO Children's Code is the right master spec even though it does not strictly bind a hobby OS.** It is the most detailed, most child-development-literate design code in existence, it is the one UK parents' expectations have been calibrated against, and it is now indirectly backed by statute (§2.2). Building to it is the cheapest way to be defensible in every other jurisdiction.

---

## 2. Framework-by-framework findings

### 2.1 UK Age Appropriate Design Code / ICO Children's Code

**Tag: BINDING as a statutory code of practice for in-scope services (ICO must take it into account in enforcement; UK GDPR fines up to 4% global turnover); GUIDANCE/BEST-PRACTICE for kidnix in postures A–B.**

Created under s.123 Data Protection Act 2018; in force 2 September 2020, enforcement from 2 September 2021. It applies to "information society services likely to be accessed by children" under 18 — a *likelihood* test, not an intent test. ([ICO](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/childrens-information/childrens-code-guidance-and-resources/age-appropriate-design-a-code-of-practice-for-online-services/), [Wikipedia summary](https://en.wikipedia.org/wiki/Children%27s_Code))

The **15 standards**, and what each concretely means for an OS:

1. **Best interests of the child** — a primary consideration in every design decision. Implies a written design rationale tying features to child development, not engagement.
2. **Data protection impact assessment** — a DPIA before launch. In posture B, do a **Child Rights Impact Assessment** instead (§2.10) and publish it in the repo.
3. **Age-appropriate application** — protections proportionate to age; where age is unknown, default to the most protective setting. kidnix knows its user is 4–8, so it should apply the *strictest* tier unconditionally, with no "older mode" escape hatch.
4. **Transparency** — privacy information "concise, prominent and in clear language suited to the age of the child". For 5-year-olds that means **spoken, illustrated, in-context**; a written policy is not transparency to a pre-reader.
5. **Detrimental use of data** — no processing demonstrably against children's wellbeing, including engagement-maximising design.
6. **Policies and community standards** — uphold your own published rules.
7. **Default settings** — **high privacy by default** absent a compelling contrary reason in the child's best interests. The most load-bearing standard for kidnix.
8. **Data minimisation** — only the minimum necessary for each discrete service element, with granular choice.
9. **Data sharing** — no disclosure absent a compelling reason.
10. **Geolocation** — off by default; visible indicator when on; **reset to off at end of session**.
11. **Parental controls** — if a parent can monitor, **tell the child, in age-appropriate terms, that they are being monitored**. Most often missed; directly governs the kidnix journal question (§2.12).
12. **Profiling** — off by default.
13. **Nudge techniques** — no nudging children into lowering privacy protections or supplying unnecessary data; per ICO commentary, no nudges that extend engagement against wellbeing.
14. **Connected toys and devices** — the code applies to physical devices; **no passive collection while in "listening" mode**. Directly relevant to any wake-word read-aloud.
15. **Online tools** — prominent, easy tools for children to exercise data rights.

**2026 status:** the ICO's Children's Code strategy has moved from engagement to enforcement — fines of £14.47m (Reddit) and £247,590 (MediaLab/Imgur) for children's-data failings, a targeted monitoring programme on services relying solely on self-declared age, and a May 2026 statement of expectations on effective age assurance. ([ICO strategy progress updates](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/childrens-information/childrens-code-guidance-and-resources/protecting-childrens-privacy-online-our-childrens-code-strategy/), [Bratby Law on ICO 2026 priorities](https://bratby.law/ico-2026-priorities-ai-biometrics-children-enforcement/))

### 2.2 Data (Use and Access) Act 2025 — the code gets statutory teeth

**Tag: BINDING (in force; data-protection provisions commenced 2025–26).**

DUAA 2025 inserts an express requirement that controllers providing information society services likely to be accessed by children take into account **"children's higher protection matters"** — how children can best be protected and supported, and the fact that children merit specific protection because they are less aware of risks. The ICO's position is that in-scope organisations are expected to comply with the Children's Code, and failure to do so makes UK GDPR compliance hard to demonstrate. The ICO updated its children's-data guidance on **15 May 2026** to reflect this. ([ICO DUAA guidance](https://ico.org.uk/about-the-ico/what-we-do/legislation-we-cover/data-use-and-access-act-2025/the-data-use-and-access-act-2025-what-does-it-mean-for-organisations/), [A&O Shearman](https://www.aoshearman.com/en/insights/ao-shearman-on-data/ico-updates-guidance-on-using-childrens-information))

**Implication:** the Children's Code has gone from "code of practice the ICO must consider" to "the operative interpretation of a statutory duty". If kidnix ever reaches posture C, the code is effectively binding.

### 2.3 UK Online Safety Act 2023 and Ofcom codes

**Tag: BINDING for regulated services — but kidnix is almost certainly out of scope.**

The OSA regulates **regulated user-to-user services** and **regulated search services** with links to the UK. An OS with no user-generated content shared between users and no search engine is not a regulated service. ([gov.uk explainer](https://www.gov.uk/government/publications/online-safety-act-explainer/online-safety-act-explainer), [Burges Salmon](https://www.burges-salmon.com/our-thinking/online-safety-act-who-does-it-apply-to/))

Status: Illegal Harms codes in force March 2025; **Protection of Children codes published 24 April 2025, children's risk assessments due 24 July 2025, measures in force from 25 July 2025**; full implementation running through 2026. ([Ofcom roadmap](https://www.ofcom.org.uk/online-safety/illegal-and-harmful-content/roadmap-to-regulation), [White & Case](https://www.whitecase.com/insight-alert/uk-online-safety-act-protection-children-codes-come-force), [Commons Library](https://commonslibrary.parliament.uk/research-briefings/cdp-2025-0043/))

**What matters to kidnix anyway:** the moment kidnix adds any feature where one user's content can be encountered by another user — shared sibling journals, "send a drawing to Grandma", a community gallery — it risks becoming a regulated U2U service. That is a hard architectural boundary. Separately, Ofcom's codes normalise assessing children's risk **by age band** and treating *design* (not just content) as a harm vector, and Ofcom's parental-controls material treats device- and OS-level controls as an expected layer of the stack — exactly where kidnix sits.

**2026 direction of travel:** DSIT's consultation **"Growing up in the online world"** (2 March – 26 May 2026) canvassed a statutory minimum social-media age, raising the digital age of consent above 13, **statutory daily time limits and overnight curfews for children**, restrictions on persuasive design (infinite scroll, autoplay), and **new obligations on AI chatbots and generative-AI services used by children** — including restricting design features that mimic friendship or empathy — with accelerated secondary legislation signalled. ([Covington/Inside Privacy](https://www.insideprivacy.com/online-safety/uk-government-launches-consultation-on-childrens-online-experiences-including-new-obligations-for-ai/), [LexisNexis](https://www.lexisnexis.com/en-gb/legal/news/dsit-consults-on-measures-to-protect-childrens-digital-wellbeing-across-social-media-gaming-ai))

kidnix's bounded sessions, no-feed, no-autoplay and no-companion-persona choices align with where UK policy is heading, not merely where it is.

### 2.4 EU GDPR Article 8 and children's data

**Tag: BINDING (EU/EEA).**

Art. 8 GDPR: where consent is the lawful basis for an information society service offered directly to a child, the child must be 16, or a parent must consent/authorise; Member States may lower the threshold to no less than 13. Controllers must make reasonable efforts to verify parental authorisation "taking into consideration available technology". ([Art. 8 GDPR](https://gdpr-info.eu/art-8-gdpr/), [EuConsent map of national ages](https://euconsent.eu/digital-age-of-consent-under-the-gdpr/))

**For kidnix:** the entire Art. 8 problem is avoided if you never rely on consent and never process personal data centrally. A parent-configured local device with no data egress is not offering an information society service to the child. **Design rule: no consent flows in the child UI at all.** Any lawful-basis question should be answerable with "there is no remote processing".

The **household exemption** (Art. 2(2)(c)) means a parent running kidnix on their own child's device is outside GDPR entirely — but note the well-established limit: the exemption covers the natural person doing the processing, *not* the entity providing the means. So the exemption protects the parent, and never the project once it operates a service. ([GDPRhub Art. 2](https://gdprhub.eu/Article_2_GDPR), [Irish DPC](https://www.dataprotection.ie/en/faqs/general/what-household-exemption))

### 2.5 EU Digital Services Act, Art. 28 and the 2025 minors guidelines

**Tag: Art. 28 BINDING for online platforms; the guidelines are GUIDANCE (non-binding but the Commission's compliance yardstick).**

Art. 28(1) DSA: online platforms accessible to minors must put in place appropriate and proportionate measures for a high level of privacy, safety and security of minors. Art. 28(2): no advertising based on profiling where the platform knows with reasonable certainty the recipient is a minor. ([DSA Art. 28](https://www.eu-digital-services-act.com/Digital_Services_Act_Article_28.html))

The Commission published **guidelines on the protection of minors on 14 July 2025**. Key recommended measures, each of which reads like a kidnix design brief: ([European Commission](https://digital-strategy.ec.europa.eu/en/library/commission-publishes-guidelines-protection-minors), [Taylor Wessing](https://www.taylorwessing.com/en/insights-and-events/insights/2025/07/rd-european-commission-guidelines-on-protection-of-minors-under-the-digital-services-act), [DSA Observatory critique](https://dsa-observatory.eu/2025/07/31/do-the-dsa-guidelines-on-protecting-minors-online-strike-the-right-balance/))

- **Minors' accounts private by default.**
- **Recommender systems** should prioritise the child's *explicit* stated preferences over behavioural/engagement signals, to avoid rabbit holes.
- **Disable engagement-maximising features by default**: streaks, ephemeral content, read receipts, **autoplay**, **push notifications**.
- **Age assurance** proportionate to risk, "accurate, reliable, robust, non-intrusive and non-discriminatory".
- **Safeguards on AI chatbots** integrated into services.
- **Minimum standards for parental controls**, plus usable reporting with prompt feedback.
- Micro and small enterprises are excluded from Art. 28(1).

kidnix is not an online platform. But "no autoplay, no notifications, no streaks, no behavioural recommender, explicit preferences only" is a directly transplantable specification.

### 2.6 EU AI Act

**Tag: BINDING. Art. 5 prohibitions in force since 2 February 2025.**

Art. 5(1)(b) prohibits AI systems that exploit vulnerabilities of a person or group **due to age**, disability, or social/economic situation, with the objective or effect of materially distorting behaviour in a manner likely to cause significant harm. Penalties up to €35m or 7% of global turnover. The canonical worked example in the literature is *an AI toy using conversational techniques to encourage children to disclose personal information*. ([Art. 5, AI Act](https://artificialintelligenceact.eu/article/5/), [EC AI Act Service Desk](https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-5), [5Rights](https://5rightsfoundation.com/ai-systems-that-exploit-the-vulnerabilities-of-children-are-now-illegal-in-the-eu/))

The 2026 Digital Omnibus on AI (provisional agreement 7 May 2026) adds prohibitions on AI-generated NCII and AI-generated CSAM, expected to apply from 2 December 2026.

**For kidnix:** if any LLM feature ships, the prohibition is the design constraint. A read-aloud assistant that answers "what does this word mean?" is fine. A persona that says "I missed you!", remembers the child's secrets, escalates emotional closeness, or asks the child questions about their family is squarely in Art. 5(1)(b) territory.

### 2.7 US COPPA and the 2025 Rule amendments

**Tag: BINDING for operators of commercial online services directed to US children under 13. Very likely inapplicable to kidnix.**

The amended COPPA Rule was published 22 April 2025, **effective 23 June 2025, full compliance required by 22 April 2026**. Key changes: biometric identifiers added to "personal information"; **separate verifiable parental consent required for disclosures not integral to the service — expressly including use of children's data for training AI**; mandatory written information-security programme; mandatory written data-retention policy with a prohibition on indefinite retention. ([Federal Register](https://www.federalregister.gov/documents/2025/04/22/2025-05904/childrens-online-privacy-protection-rule), [White & Case](https://www.whitecase.com/insight-alert/unpacking-ftcs-coppa-amendments-what-you-need-know), [Norton Rose on AI-training consent](https://www.dataprotectionreport.com/2025/06/ftcs-coppa-rule-changes-include-ai-training-consent-requirement/))

Two scope facts matter: COPPA reaches **commercial** websites and online services, and governs **online** collection only — offline/local collection is outside it. ([FTC COPPA FAQ](https://www.ftc.gov/business-guidance/resources/complying-coppa-frequently-asked-questions), [16 CFR 312](https://www.ecfr.gov/current/title-16/chapter-I/subchapter-C/part-312)) A free, non-commercial, purely local OS is not an operator.

Enforcement is still a useful mirror: **Apitor** (Sept 2025) — a children's robot-toy app that shared geolocation via a third-party SDK without notice or consent; **Disney** ($10m, approved Dec 2025) — mislabelled child-directed video leading to targeted ads. ([Mintz](https://www.mintz.com/insights-center/viewpoints/2826/2025-09-05-ftc-coppa-enforcement-still-alive-and-well), [Hunton](https://www.hunton.com/privacy-and-cybersecurity-law-blog/court-approves-disneys-10-million-ftc-settlement-resolving-coppa-enforcement-action)) The recurring failure mode is *a third-party component doing something the developer never audited* — the risk kidnix inherits from every bundled activity and dependency.

### 2.8 California AADC (CAADCA) and the US state layer

**Tag: Contested/partially BINDING; unstable.**

On **12 March 2026** the Ninth Circuit issued its second opinion in *NetChoice v. Bonta*, narrowing the injunction: NetChoice did **not** meet the facial First Amendment standard as to the Act's coverage definition or its **age-estimation** provision, but the **data-use restrictions and the dark-patterns prohibition are likely unconstitutionally vague**. Remanded on age estimation and severability. ([Ninth Circuit opinion PDF](https://netchoice.org/wp-content/uploads/2026/03/NetChoiice-v-Bonta-Ruling-Ninth-Circuit-March-12-2026.pdf), [Holland & Knight](https://www.hklaw.com/en/insights/publications/2026/03/ninth-circuit-issues-mixed-ruling-on-california-age-appropriate-design), [EPIC](https://epic.org/ninth-circuit-deals-another-blow-to-big-techs-campaign-for-broad-immunity-from-regulation-allows-parts-of-californias-design-code-to-go-into-effect/))

**Read-across:** the US First Amendment kills *content-adjacent* mandates and vague design prohibitions, but leaves *privacy and age-signalling* mandates standing. Expect US children's regulation to converge on plumbing (age signals, defaults) rather than content judgements.

Two US developments target kidnix's actual layer of the stack:

- **App Store Accountability Acts** (Utah — in force 7 May 2025, compliance by 6 May 2026; Texas; Louisiana): app stores must verify age at account creation, link minors to a verified parent account, and obtain verifiable parental consent before downloads/purchases. ([FPF comparison chart](https://fpf.org/wp-content/uploads/2026/06/FPF-Legislation-TX-UT-LA-App-Store-Accountability-Act-Comparison-Chart.pdf), [Wiley](https://www.wiley.law/alert-State-App-Store-Accountability-Acts-Introduce-New-Obligations-for-App-Developers))
- **California AB 1043, the Digital Age Assurance Act** — signed 13 October 2025, **effective 1 January 2027**. It obliges **operating system providers** to collect age information at device account setup and transmit a **coarse age-bracket signal** (under 13 / 13–15 / 16–17 / 18+) to applications. Apps get the bracket only, never a birthdate or documents. ([bill text](https://leginfo.legislature.ca.gov/faces/billTextClient.xhtml?bill_id=202520260AB1043), [Troutman analysis](https://www.troutmanprivacy.com/2025/10/analyzing-californias-digital-age-assurance-act/))

**This is the most architecturally interesting item in the whole note.** AB 1043 is a template for exactly the thing kidnix is uniquely well-placed to do well: the OS holds the age, the OS emits a minimal signal, applications never see identity. If kidnix ever supports third-party activities, a local, coarse, privacy-preserving age-bracket API is the right shape — and it is the shape regulators are converging on.

### 2.9 Australia: under-16 minimum age and Safety by Design

**Tag: BINDING in Australia (SMMA); Safety by Design is BEST-PRACTICE.**

The Online Safety Amendment (Social Media Minimum Age) Act 2024 took effect **10 December 2025**: age-restricted social media platforms must take "reasonable steps" to prevent under-16s holding accounts, with penalties to AUD $49.5m for systemic non-compliance, and **no penalties for children or parents**. eSafety expressly considers Discord, GitHub, Google Classroom, Messenger, Steam and YouTube Kids **out of scope**. ([eSafety](https://www.esafety.gov.au/about-us/industry-regulation/social-media-age-restrictions), [MinterEllison](https://www.minterellison.com/articles/australias-impending-social-media-minimum-age-obligations), [DLA Piper on the 2026 guidance](https://privacymatters.dlapiper.com/2026/02/australias-social-media-ban-and-the-esafety-commissioners-social-media-minimum-age-regulatory-guidance/))

kidnix is obviously out of scope. The transferable lesson is the **carve-out logic**: services excluded are those without open social feeds and stranger contact. Designing kidnix so it could never be an age-restricted platform is a permanent regulatory moat.

**eSafety Safety by Design** rests on three principles — **service provider responsibility** ("the burden of safety should never fall solely upon the user"), **user empowerment and autonomy**, and **transparency and accountability** — expanded into six foundations with free self-assessment tools for startups and enterprises. ([SbD principles](https://www.esafety.gov.au/industry/safety-by-design), [foundations](https://www.esafety.gov.au/industry/safety-by-design/foundations), [assessment tools](https://www.esafety.gov.au/industry/safety-by-design/assessment-tools)) Running the startup assessment and publishing the result is a cheap, high-credibility artefact for kidnix.

### 2.10 Children's rights: UNCRC GC25, UNICEF, D4CR, 5Rights

**Tag: GC25 is authoritative interpretation of a binding treaty (binding on states, not on developers). The rest are BEST-PRACTICE.**

- **UNCRC General Comment No. 25 (2021)** — the first authoritative international statement that children's rights apply online exactly as offline; developed with 700+ children in 27 countries. The root document everything else cites. ([OHCHR](https://www.ohchr.org/en/documents/general-comments-and-recommendations/general-comment-no-25-2021-childrens-rights-relation), [5Rights explainer](https://5rightsfoundation.com/resource/uncrc-general-comment-no-25-childrens-rights-apply-online/))
- **UNICEF Guidance on AI and Children** — v2.0 (2021) set requirements for child-centred AI; **v3.0 (2025)** adds generative AI, AI companions, AI supply chains and AI-generated CSAM, and retains the demand for **child rights impact assessment across the AI lifecycle**. ([UNICEF Innocenti](https://www.unicef.org/innocenti/reports/policy-guidance-ai-children))
- **Designing for Children's Rights (D4CR)**, with UNICEF as primary partner — 10 principles across Inclusion, Play & Learning, and Safety & Sustainability, updated against GC25. Principle 1 is "gather and respect children's views". ([d4cr.org](https://d4cr.org/principles/principle-1))
- **5Rights / Digital Futures Commission, "Child Rights by Design" (2023)** — 11 principles: Equity and Diversity, Best Interests, Consultation, Age Appropriate, Responsible, Participation, Privacy, Safety, Wellbeing, Development, Agency. ([Child Rights by Design](https://childrightsbydesign.5rightsfoundation.com/page/child-rights-by-design/))
- **Child Rights Impact Assessment (CRIA)** — the operational tool: forward-looking assessment against CRC rights, framed by General Comment No. 14 (best interests), with **consultation of children and independent experts** as a defining feature. UNICEF publishes a D-CRIA toolbox. ([UNICEF D-CRIA](https://www.unicef.org/childrightsandbusiness/workstreams/responsible-technology/D-CRIA), [Livingstone & Pothong 2025](https://onlinelibrary.wiley.com/doi/10.1002/poi3.70008))

What these add that privacy law does not: **children have participation and agency rights, not only protection rights**. A perfectly locked-down OS that never asks the child anything *underperforms* against this frame. "Consult the children" is literal, and at age 5 it means observation, play-testing, and real control over reversible things.

### 2.11 Technical standards: IEEE 2089, ISO/IEC 27566, EN 301 549 / WCAG 2.2

**Tag: BEST-PRACTICE (voluntary standards), except EN 301 549 which is BINDING where the EAA or public-procurement accessibility law applies.**

- **IEEE 2089-2021**, "Age Appropriate Digital Services Framework Based on the 5Rights Principles for Children" — UNCRC-informed lifecycle *processes*: recognising the user is a child; respecting children's capacity and rights; child-appropriate terms; age-appropriate presentation of information; and **validating design decisions**. Free in the IEEE reading room. ([IEEE SA](https://standards.ieee.org/standard/2089-2021.html), [PDF copy](https://ydd.lacity.gov/sites/g/files/wph2236/files/2025-02/IEEE%20Standard%20for%20an%20Age%20Appropriate%20Digital%20Services%20Framework%20Based%20on%20the%205Rights%20Principles%20for%20Children-%202021.pdf))
- **ISO/IEC 27566-1:2025**, "Age assurance systems — Part 1: Framework", published **December 2025** — the shared vocabulary: **age verification** (documentary), **age estimation** (e.g. facial analysis), **age inference** (behavioural), **successive validation** (ongoing in-session). The EC, ITU and AVPA successfully petitioned to make it freely available. ([ISO](https://www.iso.org/standard/88143.html), [Biometric Update](https://www.biometricupdate.com/202512/first-international-standard-on-age-assurance-sees-publication))
- **EN 301 549 / WCAG 2.2** — the **European Accessibility Act became enforceable 28 June 2025**; harmonised EN 301 549 v3.2.1 incorporates **WCAG 2.1 AA**, with **v4.1.1 (WCAG 2.2) expected in 2026**. EN 301 549 explicitly covers non-web software and operating systems. WCAG 2.2's nine new criteria are aimed substantially at cognitive, language and learning needs — target size, consistent help, redundant entry, accessible authentication. ([EN 301 549](https://www.deque.com/en-301-549-compliance/), [EAA](https://www.levelaccess.com/compliance-overview/european-accessibility-act-eaa/), [WCAG 2.2](https://www.w3.org/TR/WCAG22/))

**For kidnix:** the EAA does not bind a free hobby OS, but WCAG 2.2 AA is the right internal target — its cognitive criteria map almost one-to-one onto what a 5-year-old needs anyway (large targets, no timed interactions, consistent placement, no re-entry, no reliance on reading). Build to it for *design* reasons; compliance is a bonus.

### 2.12 Family and household data: the journal problem

**Tag: BEST-PRACTICE / ethics, with one BINDING hook (Children's Code standard 11).**

Standard 11 of the Children's Code is unambiguous: if a service allows a parent to monitor a child, it must **provide an age-appropriate obvious sign to the child when they are being monitored**. It also warns that parental controls must respect the child's own rights and evolving autonomy.

The research literature adds nuance that is directly actionable at ages 5–8. Monitoring is near-universal (77% of US parents check browsing history, up from 65% in 2006; ~33% of parents of 5–11s use GPS). Young children generally perceive parental awareness *positively* — as safety — but this flips with age, and by 7–8 children already evaluate tracking negatively in some contexts. Resentment and countermeasures are strongly associated with older children (~69% resent monitoring), which undermines effectiveness. The critical argument against covert monitoring is that privacy is a precondition for developing autonomy and trust. ([Digital Wellness Lab](https://digitalwellnesslab.org/research-briefs/safety-and-surveillance-software-practices-as-a-parent-in-the-digital-world/), [*Surveillance & Society*, family surveillance](https://ojs.library.queensu.ca/index.php/surveillance-and-society/article/download/15645/11067/44940))

**The design conclusion for kidnix's journal, at ages 4–8:** full parental visibility is developmentally appropriate and expected — but it must be **overt, symmetrical and named**, never silent. And the system must be built so that visibility can be *narrowed* as the child ages without rearchitecting: a per-entry "just for me" affordance that exists from day one and is honoured, plus an explicit design note that the default flips toward child-controlled visibility around 10–12. Getting the data model right now (per-entry visibility state, child-legible provenance) is cheap; retrofitting it at age 11 is not.

### 2.13 Licensing of bundled content

**Tag: BINDING (copyright/contract), and the most likely place kidnix actually gets into legal trouble.**

- **Fonts** — SIL OFL 1.1 permits bundling, embedding, redistribution and sale *with software*, provided the copyright notice, licence text and FONTLOG travel with it and Reserved Font Names are not reused by modified versions. FSF- and Debian-free. ([OSI](https://opensource.org/license/OFL-1.1), [FOSSA](https://fossa.com/blog/open-source-licenses-101-sil-open-font-license-ofl/)) Trap: fonts marketed "free for personal use" are not OFL and must not ship.
- **TTS voices** — the sharpest trap, because **engine licence and voice-model licence are separate artefacts**. Piper's engine was MIT (rhasspy/piper archived Oct 2025); active development moved to OHF-Voice/piper1-gpl under **GPL-3.0**, and Piper *voices* carry their own varying model-card/dataset terms. Coqui's code is MPL-2.0 but **XTTS v2 weights are under the non-commercial Coqui Public Model License** — and Coqui Inc. shut down in Jan 2024, so no commercial licence can be bought. F5-TTS is CC-BY-NC. Cleanly permissive: **Kokoro (Apache-2.0)**, **Chatterbox (MIT)**. ([licence survey](https://oakgen.ai/blog/free-text-to-speech-commercial-use), [XTTS/CPML](https://localaimaster.com/blog/xtts-coqui-commercial-license))
- **Educational content and images** — CC **NonCommercial** terms are *not* open source, are incompatible with GPL/MIT/Apache, and are notoriously ambiguous. Creative Commons itself advises against CC licences for software. A distro mixing NC assets into an image cannot honestly be called open source and cannot be redistributed by mirrors or vendors. ([OSI FAQ](https://opensource.org/faq), [Pitt libguide](https://pitt.libguides.com/openlicensing/cc-non-comerical), [Mifactori](https://mifactori.de/non-commercial-is-not-open-source/))

### 2.14 EU Cyber Resilience Act

**Tag: BINDING, phased: reporting obligations from September 2026, full application 11 December 2027.**

The CRA regulates products with digital elements. It creates a lighter-touch **"open source steward"** category — a legal person (foundation/company) providing systematic ongoing support to FOSS intended for commercial use — with obligations limited to a cybersecurity policy and reporting actively exploited vulnerabilities to ENISA/CSIRTs; **no CE marking, no conformity assessment**. Individual volunteers and non-commercial hobby projects are essentially out of scope. ([BCLP](https://www.bclplaw.com/en-US/events-insights-news/the-cyber-resilience-acts-obligations-for-open-source-software.html), [CRA open source guide](https://eu-cyber-laws.com/cra/open-source/))

**For kidnix:** posture B stays outside. But if kidnix ever forms a foundation, takes sponsorship, or is bundled by a hardware vendor selling child devices in the EU, steward or manufacturer obligations attach. Keeping an SBOM and a security.md from the beginning costs a day and future-proofs this entirely.

---

## 3. Consolidated requirements checklist for kidnix

Numbered, testable. **[Tag]** indicates the strongest source: **L** = legal driver, **G** = regulator guidance, **B** = best practice/standard.

### Network and data egress

1. **No network egress from a child session by default.** Testable: with the child shell running and no parent action, a packet capture over a 30-minute session shows zero outbound connections other than DHCP/NTP on the local link. **[L/G — Children's Code std 7, 8; DSA guidelines]**
2. **Deny-by-default egress policy at the OS level**, per-activity allowlist, enforced by firewall/namespace rather than by application good behaviour. Testable: an activity attempting an unlisted host fails and is logged. **[G]**
3. **Zero telemetry, zero crash reporting, zero update pings tied to a device identifier.** If update checking exists, it must be anonymous, batched, and parent-controlled. Testable: no stable device ID leaves the machine, ever. **[G — std 8/9]**
4. **No third-party SDKs, analytics libraries or ad identifiers anywhere in the image.** Testable: automated dependency scan in CI fails the build on a known analytics/ads package. **[L — the Apitor and Disney failure mode]**
5. **Geolocation absent by default; if ever added, off by default, visibly indicated while on, and reset to off at end of session.** **[G — std 10]**

### Data held on the device

6. **Everything the child creates stays local and is encrypted at rest** (full-disk or per-profile). **[B]**
7. **Written, published data-retention policy with defined maximum retention and no "indefinite".** Testable: every data class in the journal schema has a documented retention rule. **[L — COPPA 2025 amendments; G — std 8]**
8. **Parent can export all child data in an open, human-readable format in one action**, and **delete all of it in one action** with real deletion (not tombstoning). Testable: export produces readable files; post-delete disk scan finds no recoverable journal content. **[G — std 15; L — GDPR Arts. 15, 17 by analogy]**
9. **The child has age-appropriate access to their own data**: they can see everything in their journal, and can delete their own entries. Testable: a 5-year-old can find and delete a drawing unaided in user testing. **[G — std 15; B — 5Rights "Agency"]**
10. **No profiling. No behavioural user model.** Any adaptivity (difficulty, next-activity suggestion) must derive from explicit signals — the child's or parent's stated choices, or plain mastery records — never from inferred engagement or attention. Testable: no code path scores or ranks content by dwell time, session count or return rate. **[G — std 12; DSA guidelines on recommenders]**

### Design, engagement and wellbeing

11. **No time-based engagement rewards.** No streaks, no daily-login bonuses, no "come back tomorrow", no loss-framed counters. Testable: grep the codebase for streak/consecutive-day logic; must be empty. **[G — DSA guidelines; std 5, 13]**
12. **No autoplay, no infinite scroll, no feed.** Content ends. **[G — DSA guidelines; DSIT 2026 consultation direction]**
13. **No push notifications to the child.** Any parent-facing notification is on the parent's own surface. **[G — DSA guidelines]**
14. **Sessions end honestly.** A bounded session must give a predictable, comprehensible warning (visual + spoken, minutes-free for pre-readers — e.g. a shrinking shape), must not offer an "extend" nudge to the child, and must not punish ending. Testable: the end-of-session flow contains no child-actionable extend button. **[B — wellbeing; L — anticipates DSIT time-limit proposals]**
15. **No dark patterns of any kind**, including confirmshaming, pre-ticked boxes, and asymmetric button prominence. Testable: a design review checklist applied to every dialogue in the child UI. **[G — std 13; L — CAADCA, though vagueness contested]**
16. **No purchase, no store, no in-app currency, no upsell surface in the child session.** **[L/G]**

### Parent controls and transparency

17. **Parent settings are behind a real authentication boundary** (separate account/PIN with rate limiting), not a maths puzzle or a long-press. Testable: a determined 8-year-old cannot reach settings in a 20-minute adversarial test. **[B]**
18. **The child is told, in age-appropriate spoken and visual terms, what the parent can see.** This must be surfaced at first run and available on demand, not buried. Testable: a 6-year-old can correctly answer "can your grown-up see your drawings?" after onboarding. **[G — std 11, mandatory for in-scope services]**
19. **No covert monitoring capability exists in the codebase.** No screenshotting, no keystroke logging, no silent audio capture, no hidden location. If a capability could be used covertly, it must have an unsuppressable child-visible indicator. **[G — std 11; B — ethics]**
20. **Per-entry journal visibility exists from v1** ("share with grown-up" vs "just for me"), even if the default at ages 4–8 is full parental visibility. Document the intended default shift toward child control around 10–12. **[B — GC25, evolving capacities]**
21. **Parental controls are transparent and honest to the parent too**: the parent-facing UI states plainly what the OS does and does not collect, in plain English, with no marketing claims that outrun the implementation. **[G — std 4, 6]**

### Architecture boundaries (the "never becomes a regulated service" rules)

22. **No user-to-user content path.** No feature by which content created by one user can be encountered by another user of the service. Sharing, if ever built, must be an explicit parent-initiated export to a channel outside kidnix (e.g. saving a file), not an in-product delivery. Testable: architectural decision record forbidding it, plus a review gate. **[L — OSA scope; Australian SMMA carve-out logic]**
23. **No accounts, no server, no sync in v1.** If sync is ever added it must be end-to-end encrypted, parent-controlled, and opt-in — and that is the moment the full Children's Code applies. **[L]**
24. **No general-purpose browser and no arbitrary URL entry in the child session.** **[L/G]**
25. **If third-party activities are ever supported, expose only a coarse local age-bracket signal** (AB 1043 shape: under-13 / 13–15 / 16–17 / 18+), never a birthdate, name or identifier. Testable: the activity API surface contains no identity fields. **[L — California AB 1043, effective 1 Jan 2027; B — ISO/IEC 27566 vocabulary]**

### AI and read-aloud

26. **TTS runs fully on-device.** No cloud speech API in the child path. **[G — std 8]**
27. **No wake-word, no always-listening mode, no passive audio capture.** If speech input is ever added it must be explicit push-to-talk with a visible, unsuppressable indicator. **[G — std 14, connected toys]**
28. **If an LLM feature ships: on-device, non-persona, non-persistent, tool-shaped.** It answers bounded questions ("what does this word mean?", "read this to me") in a neutral register. It has **no name, no character, no memory of the child across sessions, no expressions of feeling toward the child, and never initiates conversation.** Testable: system prompt and eval suite explicitly forbid first-person affect and relationship language. **[L — EU AI Act Art. 5(1)(b); G — FTC 6(b) AI companion inquiry, Sept 2025; DSIT 2026 consultation]**
29. **No child data used for model training, ever, under any consent flow.** **[L — COPPA 2025 amendment requiring separate VPC for AI training; simplest compliance is a flat prohibition]**
30. **Any AI output shown to a child passes a content safety gate and is logged locally for parent review.** **[G — UNICEF AI & Children v3.0]**

### Accessibility

31. **WCAG 2.2 AA as the internal target for all child-facing UI**, with particular attention to Target Size (Minimum), Consistent Help, Redundant Entry, Focus Appearance and no timed interactions. **[B; L where EN 301 549 applies]**
32. **Every UI element that carries meaning is available non-textually** — spoken, iconic, or both. A non-reader must be able to operate the entire shell. Testable: complete a full session with all text rendered as blank boxes. **[B — WCAG 2.2 cognitive criteria; child-development necessity]**
33. **Full keyboard and switch-access operability; no interaction requiring fine motor precision or drag-only input.** **[B — EN 301 549 covers non-web software and OS]**

### Licensing and supply chain

34. **Every bundled asset — font, voice model, image, sound, educational text — has a recorded licence in a machine-readable manifest, and the licence permits redistribution with modification and commercial use.** Testable: CI fails if any asset lacks a manifest entry or carries an NC/ND/"personal use only" term. **[L — copyright]**
35. **TTS voice model licences are recorded separately from the TTS engine licence.** Prefer Apache-2.0/MIT-licensed models (e.g. Kokoro, Chatterbox) or explicitly permissive Piper voices; **exclude XTTS v2 weights (CPML, non-commercial) and CC-BY-NC models.** **[L]**
36. **OFL fonts ship with copyright notice, licence text and FONTLOG; no Reserved Font Name reuse in any modified font.** **[L]**
37. **Maintain an SBOM and a SECURITY.md with a vulnerability disclosure address from day one.** **[L — anticipates EU CRA, applicable Dec 2027 if kidnix ever gains a commercial steward]**

### Process artefacts

38. **Publish a Child Rights Impact Assessment in the repository** covering all 11 Child Rights by Design principles, updated per release. **[B — 5Rights/DFC, UNICEF D-CRIA; G — analogous to Children's Code std 2 DPIA]**
39. **Consult children.** Play-test with the target age group, record what they said, and let it change the product. Document it in the CRIA. **[B — GC25 participation rights; D4CR principle 1; IEEE 2089]**
40. **Complete the eSafety Safety by Design startup self-assessment and publish the result.** **[B]**
41. **Maintain a public, plain-English "what kidnix does with data" page written at two levels** — one for parents, one read aloud for children. **[G — std 4]**

---

## 4. Things NOT to do

1. **Do not add a child-to-child or child-to-adult messaging feature** — even between siblings, even offline-first. It converts kidnix from an unregulated OS into a potential regulated user-to-user service under the OSA, and imports the entire grooming/CSAM risk surface.
2. **Do not build an AI companion.** No name, no face, no persistent memory of the child, no affection. This is the single clearest red line across the EU AI Act Art. 5(1)(b), the FTC's 6(b) inquiry, UNICEF v3.0 and DSIT's 2026 proposals — all of which converged independently on the same conclusion within eighteen months.
3. **Do not use engagement metrics as a success measure**, internally or in the product. Once "minutes per session" is a KPI, standards 5 and 13 are lost regardless of intent.
4. **Do not collect a child's date of birth, real name, photograph, or voice recording** unless a specific feature genuinely cannot work without it — and then keep it local and deletable. Biometric identifiers are now personal information under COPPA and were always special-category-adjacent under GDPR.
5. **Do not ship covert monitoring.** No hidden screenshots, no keyloggers, no silent audio. If a parent needs it, kidnix is the wrong tool for them.
6. **Do not ship any CC-NonCommercial, ND, or "free for personal use" asset**, and do not ship XTTS v2 weights or other CPML/CC-BY-NC voice models. It makes the distro non-redistributable and the "open source" claim false.
7. **Do not build a store or any purchase surface in the child session** — and note that US App Store Accountability Acts now attach age-verification and parental-consent duties to app-store operators.
8. **Do not implement age *verification*.** kidnix has no need for it: the parent sets the device up. Adding documentary or biometric age checks would create a serious data risk in exchange for nothing.
9. **Do not claim compliance you have not tested.** "Zero telemetry" must be a packet-capture-verified property in CI, not a marketing sentence.
10. **Do not assume the household exemption protects the project.** It protects the parent doing the processing. The moment kidnix operates any service, the exemption is gone.
11. **Do not let a "just for the family" prototype accrete a server.** The architectural gap between posture B and posture C is the entire regulatory delta; crossing it accidentally is the main risk.

---

## 5. Open questions

1. **Should kidnix be an AB 1043-style age-signal provider?** Philosophically aligned (OS holds age, apps get a bracket) and a genuinely novel contribution from an open-source OS — but it only matters if third-party activities exist, itself unresolved.
2. **What is the right journal visibility default at age 8 vs 5?** Evidence says perceptions shift around 7–8. An age-graded default that flips automatically at a birthday feels more rights-respecting; requiring an explicit parent decision is more honest about parental authority.
3. **Should a local LLM ship in v1 at all?** A tool-shaped, non-persona, on-device assistant is defensible today, but DSIT may produce secondary legislation on child-facing generative AI in 2026–27 whose shape is unknowable. Deferring costs little.
4. **Are hard session cut-offs better than natural completion points for young children?** DSIT and the DSA guidelines are moving toward mandated time limits, but the developmental evidence is genuinely unsettled. Needs its own evidence review.
5. **Multiple children on one device** — separate profiles and journals, certainly; but can a sibling ever see another's work? The safest answer (never) may be socially wrong in a real family.
6. **What is the answer when a parent asks for screen recording?** Refusing costs users; providing it breaks requirement 19. Probably refuse, and document why publicly.
7. **Would forming a foundation trigger EU CRA steward obligations**, and is that a reason to stay unincorporated longer?
8. **Does WCAG 2.2 AA actually suffice for 4–8-year-olds**, or does kidnix need supplementary criteria (maximum concurrent choices, no reliance on colour naming or reading order)? Probably the latter; no standard covers it.

---

## 6. Top 10 takeaways

1. **Design to the ICO Children's Code even though it does not bind you.** Best-articulated child-centred design spec in existence, now the operative reading of a statutory duty via DUAA 2025, and every other regime is broadly a subset of it.
2. **The household exemption is not a strategy.** It protects the parent, not the project. Build for posture C, ship in posture B.
3. **The highest-value architectural commitment is "no user-to-user content path, ever."** It keeps kidnix outside the OSA, the Australian minimum-age regime, DSA Art. 28 and the entire grooming risk surface — permanently, for free.
4. **"High privacy by default" for an OS means no egress, not a settings panel.** Zero outbound packets in a 30-minute child session is stronger and simpler than any policy document.
5. **The anti-engagement design choices are now the regulated ones.** No autoplay, streaks, notifications, infinite scroll or behavioural recommender — named explicitly in both the EC's July 2025 DSA guidelines and DSIT's March 2026 consultation. Product instinct and regulatory direction have converged.
6. **AI companionship for children is the clearest red line of 2025–26.** EU AI Act Art. 5(1)(b), the FTC 6(b) inquiry, UNICEF v3.0 and DSIT all landed independently on the same prohibition inside eighteen months. A tool with no persona is fine; a friend is not.
7. **Children's Code standard 11 governs the journal:** parental monitoring is permitted, but the child must be told in terms they understand. Overt, named, symmetrical — with per-entry visibility built in from v1 so the model can age with the child.
8. **The most likely real legal failure is licensing, not privacy.** Voice models especially: engine and model licences are separate, and the most convenient models (XTTS v2, F5-TTS) are non-commercial. Automate the check in CI.
9. **Third-party code is the recurring enforcement story.** Apitor and Disney both failed on what a third party did with children's data. In an OS, every bundled activity is that risk; deny-by-default egress plus a dependency scan closes it.
10. **Publish the process artefacts** — a CRIA against the 11 Child Rights by Design principles, an eSafety Safety by Design self-assessment, an SBOM, and a two-level plain-English data page. Days of work, and they are both what every framework in §2 asks for and the credibility that lets other families trust the thing.

---

## 7. Full source list

**UK — ICO / data protection**
1. ICO — [Age appropriate design: a code of practice for online services](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/childrens-information/childrens-code-guidance-and-resources/age-appropriate-design-a-code-of-practice-for-online-services/)
2. ICO — [Introduction to the Children's code](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/childrens-information/childrens-code-guidance-and-resources/introduction-to-the-childrens-code/)
3. ICO — [FAQs on the 15 standards of the Children's code](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/childrens-information/childrens-code-guidance-and-resources/faqs-on-the-15-standards-of-the-children-s-code/)
4. ICO — [Protecting children's privacy online: our Children's code strategy](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/childrens-information/childrens-code-guidance-and-resources/protecting-childrens-privacy-online-our-childrens-code-strategy/) (progress updates Mar 2025, Dec 2025, Aug 2026)
5. ICO — [Data (Use and Access) Act 2025: what does it mean for organisations?](https://ico.org.uk/about-the-ico/what-we-do/legislation-we-cover/data-use-and-access-act-2025/the-data-use-and-access-act-2025-what-does-it-mean-for-organisations/)
6. ICO — [Children and the UK GDPR](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/childrens-information/children-and-the-uk-gdpr/)
7. A&O Shearman — [ICO updates guidance on using children's information](https://www.aoshearman.com/en/insights/ao-shearman-on-data/ico-updates-guidance-on-using-childrens-information) (May 2026)
8. Bratby Law — [ICO 2026 priorities: AI, biometrics, children, enforcement](https://bratby.law/ico-2026-priorities-ai-biometrics-children-enforcement/)
9. Evalian — [The ICO's Age-Appropriate Design Code: the 15 standards](https://evalian.co.uk/childrens-code/)
10. Wikipedia — [Children's Code](https://en.wikipedia.org/wiki/Children%27s_Code)

**UK — online safety**
11. Ofcom — [Approach to implementing the Online Safety Act (roadmap)](https://www.ofcom.org.uk/online-safety/illegal-and-harmful-content/roadmap-to-regulation)
12. gov.uk — [Online Safety Act explainer](https://www.gov.uk/government/publications/online-safety-act-explainer/online-safety-act-explainer)
13. White & Case — [Protection of Children Codes come into force](https://www.whitecase.com/insight-alert/uk-online-safety-act-protection-children-codes-come-force)
14. Reed Smith — [Ofcom updates children's codes and guidance](https://www.reedsmith.com/articles/uk-online-safety-act-ofcom-updates-childrens-codes-and-guidance/)
15. House of Commons Library — [Implementation of the Online Safety Act](https://commonslibrary.parliament.uk/research-briefings/cdp-2025-0043/)
16. Burges Salmon — [Online Safety Act: who does it apply to?](https://www.burges-salmon.com/our-thinking/online-safety-act-who-does-it-apply-to/)
17. Covington / Inside Privacy — [UK consultation on children's online experiences, including new obligations for AI](https://www.insideprivacy.com/online-safety/uk-government-launches-consultation-on-childrens-online-experiences-including-new-obligations-for-ai/) (Mar 2026)
18. LexisNexis — [DSIT consultation on children's digital wellbeing](https://www.lexisnexis.com/en-gb/legal/news/dsit-consults-on-measures-to-protect-childrens-digital-wellbeing-across-social-media-gaming-ai)

**EU**
19. [Art. 8 GDPR — conditions applicable to child's consent](https://gdpr-info.eu/art-8-gdpr/)
20. [Art. 2 GDPR — material scope / household exemption (GDPRhub)](https://gdprhub.eu/Article_2_GDPR); [Irish DPC on the household exemption](https://www.dataprotection.ie/en/faqs/general/what-household-exemption)
21. EuConsent — [Digital age of consent under the GDPR](https://euconsent.eu/digital-age-of-consent-under-the-gdpr/)
22. European Commission — [Guidelines on the protection of minors under the DSA](https://digital-strategy.ec.europa.eu/en/library/commission-publishes-guidelines-protection-minors) (14 July 2025)
23. [DSA Article 28 text](https://www.eu-digital-services-act.com/Digital_Services_Act_Article_28.html)
24. Taylor Wessing — [European Commission guidelines on protection of minors under the DSA](https://www.taylorwessing.com/en/insights-and-events/insights/2025/07/rd-european-commission-guidelines-on-protection-of-minors-under-the-digital-services-act)
25. DSA Observatory — [Do the DSA guidelines on protecting minors strike the right balance?](https://dsa-observatory.eu/2025/07/31/do-the-dsa-guidelines-on-protecting-minors-online-strike-the-right-balance/)
26. [EU AI Act Article 5 — prohibited practices](https://artificialintelligenceact.eu/article/5/); [EC AI Act Service Desk](https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-5)
27. 5Rights — [AI systems that exploit the vulnerabilities of children are now illegal in the EU](https://5rightsfoundation.com/ai-systems-that-exploit-the-vulnerabilities-of-children-are-now-illegal-in-the-eu/)
28. BCLP — [The Cyber Resilience Act's obligations for open source software](https://www.bclplaw.com/en-US/events-insights-news/the-cyber-resilience-acts-obligations-for-open-source-software.html); [CRA open source guide](https://eu-cyber-laws.com/cra/open-source/)

**US**
29. Federal Register — [Children's Online Privacy Protection Rule, final amendments](https://www.federalregister.gov/documents/2025/04/22/2025-05904/childrens-online-privacy-protection-rule) (22 Apr 2025)
30. FTC — [Complying with COPPA: FAQs](https://www.ftc.gov/business-guidance/resources/complying-coppa-frequently-asked-questions); [16 CFR Part 312](https://www.ecfr.gov/current/title-16/chapter-I/subchapter-C/part-312)
31. White & Case — [Unpacking the FTC's COPPA amendments](https://www.whitecase.com/insight-alert/unpacking-ftcs-coppa-amendments-what-you-need-know)
32. Norton Rose Fulbright — [COPPA Rule changes include AI training consent requirement](https://www.dataprotectionreport.com/2025/06/ftcs-coppa-rule-changes-include-ai-training-consent-requirement/)
33. FTC — [Inquiry into AI chatbots acting as companions](https://www.ftc.gov/news-events/news/press-releases/2025/09/ftc-launches-inquiry-ai-chatbots-acting-companions) (Sept 2025)
34. Mintz — [FTC COPPA enforcement: still alive and well](https://www.mintz.com/insights-center/viewpoints/2826/2025-09-05-ftc-coppa-enforcement-still-alive-and-well) (Apitor)
35. Hunton — [Court approves Disney's $10m FTC COPPA settlement](https://www.hunton.com/privacy-and-cybersecurity-law-blog/court-approves-disneys-10-million-ftc-settlement-resolving-coppa-enforcement-action)
36. Ninth Circuit — [NetChoice v. Bonta opinion, 12 March 2026 (PDF)](https://netchoice.org/wp-content/uploads/2026/03/NetChoiice-v-Bonta-Ruling-Ninth-Circuit-March-12-2026.pdf); [Holland & Knight analysis](https://www.hklaw.com/en/insights/publications/2026/03/ninth-circuit-issues-mixed-ruling-on-california-age-appropriate-design); [EPIC](https://epic.org/ninth-circuit-deals-another-blow-to-big-techs-campaign-for-broad-immunity-from-regulation-allows-parts-of-californias-design-code-to-go-into-effect/)
37. California — [AB 1043, Digital Age Assurance Act (bill text)](https://leginfo.legislature.ca.gov/faces/billTextClient.xhtml?bill_id=202520260AB1043); [Troutman analysis](https://www.troutmanprivacy.com/2025/10/analyzing-californias-digital-age-assurance-act/)
38. Future of Privacy Forum — [App Store Accountability Act comparison chart, TX/UT/LA (PDF)](https://fpf.org/wp-content/uploads/2026/06/FPF-Legislation-TX-UT-LA-App-Store-Accountability-Act-Comparison-Chart.pdf); [Wiley alert](https://www.wiley.law/alert-State-App-Store-Accountability-Acts-Introduce-New-Obligations-for-App-Developers)

**Australia**
39. eSafety Commissioner — [Social media age restrictions](https://www.esafety.gov.au/about-us/industry-regulation/social-media-age-restrictions)
40. eSafety Commissioner — [Safety by Design](https://www.esafety.gov.au/industry/safety-by-design), [foundations](https://www.esafety.gov.au/industry/safety-by-design/foundations), [assessment tools](https://www.esafety.gov.au/industry/safety-by-design/assessment-tools)
41. MinterEllison — [Australia's Social Media Minimum Age obligations](https://www.minterellison.com/articles/australias-impending-social-media-minimum-age-obligations); [DLA Piper, Feb 2026 regulatory guidance](https://privacymatters.dlapiper.com/2026/02/australias-social-media-ban-and-the-esafety-commissioners-social-media-minimum-age-regulatory-guidance/)

**Children's rights**
42. OHCHR — [General Comment No. 25 (2021) on children's rights in relation to the digital environment](https://www.ohchr.org/en/documents/general-comments-and-recommendations/general-comment-no-25-2021-childrens-rights-relation)
43. 5Rights — [UNCRC General Comment No. 25 explainer](https://5rightsfoundation.com/resource/uncrc-general-comment-no-25-childrens-rights-apply-online/)
44. 5Rights / Digital Futures Commission — [Child Rights by Design principles](https://childrightsbydesign.5rightsfoundation.com/page/child-rights-by-design/)
45. 5Rights — [Child Rights Impact Assessment report (PDF)](https://5rightsfoundation.com/wp-content/uploads/2024/09/CRIA-Report.pdf)
46. UNICEF Innocenti — [Guidance on AI and children](https://www.unicef.org/innocenti/reports/policy-guidance-ai-children); [Policy guidance on AI for children 2.0 (PDF)](https://www.unicef.org/innocenti/media/1341/file/UNICEF-Global-Insight-policy-guidance-AI-children-2.0-2021.pdf)
47. UNICEF — [Assessing child rights impacts in relation to the digital environment (D-CRIA)](https://www.unicef.org/childrightsandbusiness/workstreams/responsible-technology/D-CRIA); [BSR/UNICEF D-CRIA report (PDF)](https://www.bsr.org/reports/BSR_UNICEF_D6.pdf)
48. Livingstone & Pothong — [Child Rights Impact Assessment: a policy tool for a rights-respecting digital environment](https://onlinelibrary.wiley.com/doi/10.1002/poi3.70008), *Policy & Internet* (2025)
49. Designing for Children's Rights — [D4CR principles](https://d4cr.org/principles/principle-1)

**Standards**
50. IEEE — [2089-2021, Age Appropriate Digital Services Framework](https://standards.ieee.org/standard/2089-2021.html); [full text PDF copy](https://ydd.lacity.gov/sites/g/files/wph2236/files/2025-02/IEEE%20Standard%20for%20an%20Age%20Appropriate%20Digital%20Services%20Framework%20Based%20on%20the%205Rights%20Principles%20for%20Children-%202021.pdf)
51. ISO — [ISO/IEC 27566-1:2025, Age assurance systems — Part 1: Framework](https://www.iso.org/standard/88143.html); [Biometric Update on publication](https://www.biometricupdate.com/202512/first-international-standard-on-age-assurance-sees-publication)
52. W3C — [Web Content Accessibility Guidelines (WCAG) 2.2](https://www.w3.org/TR/WCAG22/)
53. Deque — [EN 301 549 explained](https://www.deque.com/en-301-549-compliance/); Level Access — [European Accessibility Act compliance](https://www.levelaccess.com/compliance-overview/european-accessibility-act-eaa/)

**Family data ethics**
54. Digital Wellness Lab — [Safety and surveillance software practices as a parent in the digital world](https://digitalwellnesslab.org/research-briefs/safety-and-surveillance-software-practices-as-a-parent-in-the-digital-world/)
55. *Surveillance & Society* — [Family surveillance: understanding parental monitoring, reciprocal practices, and digital resilience](https://ojs.library.queensu.ca/index.php/surveillance-and-society/article/download/15645/11067/44940)

**Licensing**
56. OSI — [SIL Open Font License 1.1](https://opensource.org/license/OFL-1.1); FOSSA — [Open source licenses 101: SIL OFL](https://fossa.com/blog/open-source-licenses-101-sil-open-font-license-ofl/)
57. OSI — [Open Source Definition FAQ](https://opensource.org/faq)
58. University of Pittsburgh — [CC NonCommercial guidance](https://pitt.libguides.com/openlicensing/cc-non-comerical); Mifactori — [Why CC-NC is not open source](https://mifactori.de/non-commercial-is-not-open-source/)
59. [Free TTS for commercial use: 2026 licence guide](https://oakgen.ai/blog/free-text-to-speech-commercial-use); [Is XTTS v2 / Coqui TTS free for commercial use?](https://localaimaster.com/blog/xtts-coqui-commercial-license)
