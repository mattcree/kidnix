# Input, Hardware, Accessibility and Voice/AI for kidnix

**Research topic 06** — Input devices, hardware, accessibility/inclusion, and voice/AI for young children (ages 4–8, centred on 5–6, UK family context). August 2026.

---

## 1. Scope & method

Covers: (a) input performance of 4–8s across mouse/trackpad/touch/stylus/keyboard and the OS settings that follow; (b) hardware shortlist, minimum specs, durability, ergonomics; (c) accessibility, typography, neurodivergence, UK multilingualism, standards, platform state; (d) local TTS/ASR; (e) generative AI, its evidence base, and a stance.

Primary sources were read directly (papers, standards, official statistics, product spec pages), with abstracts pulled via the OpenAlex and Crossref APIs where paywalls blocked full text. GNOME defaults are a live `gsettings` dump from a current Fedora/GNOME system rather than a documentation claim.

**Evidence tags:** **[A]** peer-reviewed empirical study with statistics, meta-analysis, published standard, or official national statistics. **[B]** peer-reviewed but small-n/indirect; reputable NGO or regulator testing; authoritative vendor documentation. **[C]** secondary reporting, market listings, vendor marketing. **[D]** my inference or design judgement.

**Gaps and assumptions.** Most child-pointing evidence dates from 1990–2015 with little post-2020 replication; I treat it as directionally valid but note hardware drift. Prices are UK, August 2026, inc. VAT unless stated. I assume GNOME/Wayland + Flatpak per the project brief. Two sources could not be retrieved in full (a March 2026 US Senate letter on AI toys; the ScienceDirect full text of Vatavu et al. 2015) and are cited only to the level verified.

---

## 2. (a) Input devices

### 2.1 The mouse: the best-evidenced dataset

**Hourcade, Bederson, Druin & Guimbretière**, *Accuracy, Target Reentry and Fitts' Law Performance of Preschool Children Using Mice* (UMD HCIL; ACM TOCHI 2004 version: *Differences in pointing task performance between preschool children and adults using mice*) remains the most directly usable study. Thirteen 4-year-olds (mean 4y5m), thirteen 5-year-olds (5y6m), thirteen adults (19–22). 1024×768, Logitech USB optical mouse (~18 px per mm of hand movement). Circular targets of **16, 32 or 64 px** at **128, 256 or 512 px**; 45 trials each. **[A]**

| Target | Age | Accuracy % (SD) | Target reentry (SD) | Reentry during click (SD) |
|---|---|---|---|---|
| 16 px | 4 yr | **43** (24) | 1.63 (1.25) | 1.12 (0.66) |
| 16 px | 5 yr | **74** (25) | 1.38 (0.64) | 0.26 (0.25) |
| 16 px | adult | 90 (12) | 0.38 (0.20) | 0.12 (0.18) |
| 32 px | 4 yr | **77** (11) | 1.11 (0.65) | 0.39 (0.30) |
| 32 px | 5 yr | **91** (7.5) | 0.92 (0.27) | 0.13 (0.16) |
| 32 px | adult | 96 (5.8) | 0.14 (0.08) | 0.03 (0.08) |
| 64 px | 4 yr | **90** (12) | 0.63 (0.39) | 0.15 (0.26) |
| 64 px | 5 yr | **97** (5.2) | 0.39 (0.15) | 0.03 (0.11) |
| 64 px | adult | 99 (2.5) | 0.11 (0.09) | 0.01 (0.03) |

The authors' conclusion: *"to achieve the same level of accuracy as adults at 16 pixels, 5 year olds require 32 pixels, and 4 year olds 64 pixels… 64 pixel targets offer significant advantages over 32 pixel targets for both 4 and 5 year olds… For adults there are no advantages in going from 32 to 64."* At ~96 dpi, 64 px ≈ **17 mm**. **[A]**

Fitts' index of performance (to first target entry): **4 yr 1.95 bits/s** (SD 0.59, CoV 0.30); **5 yr 3.24** (0.60, 0.19); **adult 7.80** (1.08, 0.14). A 5-year-old runs at ~40% of adult throughput, a 4-year-old ~25%, with roughly double the variability. Fitts' law fitted children well (R² > 0.9) **only up to first target entry**; endgame corrections dominate thereafter. **[A]**

Two further findings with direct design consequences **[A]**:

- **Mouse button use is unreliable at 4–5.** All adults used the left button exclusively; 5-year-olds were inconsistent and *some 4-year-olds used primarily the right button*. The authors recommend providing the same functionality through both buttons.
- **Distance had no significant effect** on accuracy or reentry (F(2,35)=0.158, p=0.854) — only size and age did. Layouts can be spacious for free.

### 2.2 Drag-and-drop vs point-and-click

- Joiner, Messer, Light & Littleton (1998), *It Is Best to Point for Young Children* (Computers in Human Behavior 14(3)) — the title is the finding. **[A]**
- Inkpen (2001), ACM TOCHI 8(1):1–33: younger children slower and more error-prone dragging than pointing; older children showed no difference. **[A]**
- Donker & Reitsma (2007), Interacting with Computers 19(2):257–266: with K2 and Grade-1 children, **most errors occur at the start and end of a move, not in the middle** — not from failing to hold the button, as had been assumed. Errors depend on drop-target size and movement *direction*, not distance. **[A]**
- Counter-evidence: some studies find children *expect* drag-and-drop rather than point-and-click for object manipulation, so removing dragging entirely creates its own mismatch. **[B]**

**Implication [D]:** never make drag the only route; make drop targets large; make pick-up and release the forgiving parts (generous pick-up radius, generous snap-on-release).

### 2.3 Touchscreen

- **Vatavu, Cramariuc & Schipor (2015)**, IJHCS: 89 children aged 3–6, **2,912 touch records** for tap and drag-and-drop. Significant improvement 3→6, persistent gap vs adults. **[A]** (abstract-level only)
- **Anthony et al. (2012)**, ACM ITS: two distinct problems — **intentional and unintentional touches landing outside targets**, and failure to recognise drawn gestures. Downstream reporting: children 7–10 miss **7 mm targets ~30%** of the time; 11–17s ~20%. **[A]** for direction, **[C]** for the exact percentages.
- **Fitts vs FFitts for children (2020, 54 children aged 5–10)**: plain **Fitts' law with nominal target widths fits better (R² = 0.93)** than FFitts, which was designed to improve on Fitts for adult finger input. You can size children's touch targets with ordinary Fitts reasoning. **[A]**
- **Nielsen Norman Group:** **≥ 2 cm × 2 cm touch targets for young children — 4× the area of the 1 cm adult recommendation.** Ages 3–5: touchscreens only, tap/swipe/drag, avoid two-handed operations and precise dragging. Ages 6–8: touchscreens and trackpads; **avoid dragging, scrolling and small targets** (a 5 mm close button caused frustration). Adult baselines: 1 cm minimum, ~2 mm spacing, fingertip 1.6–2 cm. **[B]**
- **Multi-touch:** kindergarteners (4–6) struggle specifically with rotation and pinch, with problems clustering on screen sensitivity, unintentional touches and inaccurate placement **[B]**. By contrast children aged 5–10 with Down syndrome achieved near-100% success on tap, double-tap, long-press, drag, scale and rotate **[B]** — motor difficulty alone does not rule multi-touch out, but never *require* it.

### 2.4 Trackpads, trackballs, joysticks

Strommen et al. (1996) compared mouse, trackball and joystick with 3-year-olds: the **trackball produced the least target reentry**, though they argued against the joystick and warned that speed is the wrong metric for children **[A]**. Jones (1991) covered 6-, 8- and 10-year-olds across the same three devices **[A]**. **Trackpads have essentially no 4–8 literature**; NN/g places trackpad competence at 6–8 and up **[B]**. The practical hazards for a 5-year-old are tap-to-click misfires, accidental two-finger scroll, and palm contact.

**Judgement [D]:** ranking for a 5-year-old is **touchscreen ≥ mouse > trackball > trackpad ≫ stylus**. The trackpad is worst but is what cheap laptops ship with, so kidnix must tune it rather than assume it works.

### 2.5 Keyboard and stylus

**Kiefer et al. (2020)**, Frontiers in Psychology (n=147 kindergarteners, 16 letters, 7 weeks): pencil beat keyboard on **letter recognition** and visuo-spatial skills; **keyboard beat stylus** on word writing and reading; stylus differed from neither. A touchscreen stylus is the worst of the three — its low-friction surface increases motor-control difficulty. **[A]** Separately, handwriting fluency accounts for **7.4%** of variance in primary-grade writing quality (n=4,950) **[A]** — typing is not a substitute for handwriting at this age.

**Child keyboards sold into UK schools (Aug 2026, inc. VAT unless noted):**

| Product | Price | Notes |
|---|---|---|
| Clevy lowercase keyboard, UK layout, USB | **£135.45 + VAT (~£162)** | Keys 30% bigger, characters up to 4× bigger; steel frame, switches rated >60M keystrokes; housing **guides spilled fluid straight through**; hardware switch to **disable key repeat**; distracting keys removed **[B]** |
| Clevy SimplyWorks (wireless) | £162.73 + VAT | As above **[B]** |
| Jumbo XL USB (Inclusive Technology) | **£39.00 + VAT (£46.80)** | Colour-coded vowels vs consonants **[B]** |
| Jumbo XL Hi-Visibility USB | £39.00 + VAT (£46.80) | High contrast **[B]** |
| Jumbo XL Bluetooth/RF | £62.00 + VAT (£74.40) | **[B]** |
| SEN/Early Years keyboard | £24.00 + VAT (£28.80) | **[B]** |
| BigKeys LX (lowercase QWERTY) | UK clearance stock | Keys **4× larger**; no drivers **[C]** |
| Clevy washable cover | £51.30 | Spill retrofit **[B]** |

The **key-repeat disable switch** is the most underrated feature here: a child resting a finger on a key produces "aaaaaaaaaa", and the OS-level fix is invisible to parents.

### 2.6 Mice for small hands

Children's hand length as a fraction of adult: **61% at 4, 67.4% at 6, 74.5% at 8** **[B]**. Retail/ergonomics figures **[C]**: adult mice ≈ 122 × 69 mm, children's ≈ 89 × 58 mm; a child with **hand length under 14 cm** needs a child-specific mouse. A claim that 5–7s took **3.2× longer** on drag-and-drop with adult-sized mice appears only in secondary sources — unverified **[C]**.

**Judgement [D]:** small, light, low-DPI, two-button, no-scroll-wheel-required. Avoid gaming mice (accidental navigation) and wireless on shared family machines (mid-session battery death is a wellbeing problem).

### 2.7 OS-level pointer settings — actual GNOME defaults

Live values from a current Fedora/GNOME system **[A]**:

```
peripherals.mouse     accel-profile 'flat'   double-click 400 (ms)   drag-threshold 8 (px)
                      speed -0.241 (range -1..1)   middle-click-emulation false
peripherals.touchpad  tap-to-click true   tap-and-drag true   tap-and-drag-lock false
                      disable-while-typing true (timeout 500 ms)   two-finger-scrolling true
a11y.mouse            dwell-click-enabled false   dwell-time 1.2 s   dwell-threshold 10 px
                      secondary-click-enabled false   secondary-click-time 1.2 s
a11y.keyboard         stickykeys/slowkeys/bouncekeys/mousekeys all false; delays 300 ms
interface             cursor-size 24   text-scaling-factor 1.0 (range 0.5–3.0)
                      enable-animations true
```

GNOME's **double-click default is 400 ms** (Windows historically 550 ms **[C]**). Young children's spontaneous inter-tap interval is **400–500 ms with high variability** **[B]** — so the default sits right at the edge of what a 5-year-old can reliably produce. GNOME's own HIG already states that *"actions which are physically challenging to accomplish, such as double-clicking or chording… should be avoided"* and that *"pointer hover should not be relied upon for revealing actions or essential information."* **[A]**

libinput's **adaptive** profile decelerates at very slow speeds and accelerates linearly at high ones; **flat** applies a constant 1:1 factor; max acceleration 3.5×, max deceleration 0.3×; touchpads get an additional constant deceleration. **[A]** GNOME's mouse default is already `flat`, which is right for children, since acceleration curves punish the many small corrective sub-movements children actually make (children produce significantly more sub-movements than adults, with inaccurate sub-movement length and direction **[A]**).

---

## 3. (b) Hardware

### 3.1 Device shortlist (UK, August 2026)

| Option | Indicative price | Linux/Wayland fit | Verdict |
|---|---|---|---|
| **Refurb ThinkPad T480 / T480s / X280** (8th-gen i5, 8–16 GB, 256 GB) | **£90–£320** **[C]** | Excellent; Lenovo is on LVFS so `fwupd` works **[B]** | **Primary recommendation.** Cheap, repairable, spill-channel keyboards, huge parts supply; a broken one is not a family crisis. |
| **Refurb ThinkPad X13 Yoga / X1 Yoga** (2-in-1, touch) | ~£250–£400 **[C]** | Good; Lenovo publishes a Linux guide for X13/X13 Yoga Gen 4 **[B]**; touch works under Wayland+GNOME **[C]** | **Recommended where touch matters** — touchscreen plus real keyboard is the kidnix shape. |
| **Raspberry Pi 5** + Touch Display 2 | Board ~£45–£75; display **$40 / $60 / $80** for 5" / 7" / 10" (≈£37/£55/£72) **[A]** | Native, but GNOME/Wayland on Pi is workable rather than pleasant | **Secondary tier.** BCM2712 quad Cortex-A76 @ 2.4 GHz, 1–16 GB LPDDR4X. Display 2 is 720×1280 (10": 1200×1920), five-finger multi-touch (ten on 10"), anti-glare, in production to ≥ Jan 2030 **[A]**. The 7" active area (86.94 × 154.56 mm) is too small for an activity shell — prefer the 10" (135.4 × 216.6 mm). |
| **Refurb Chromebook** | £40–£120 **[C]** | Variable; most need firmware replacement, ARM models worse, RAM often soldered at 4 GB | **Not recommended as default** — the firmware step is beyond most parents. |
| **Framework Laptop 13** | ~£1,000+ **[D]** | Excellent | **Not recommended here.** 5–10× a refurb ThinkPad for a machine a 5-year-old may put yoghurt into. |

**Assumption [D]:** kidnix should be explicitly refurb-first — it fits the ethos and UK family budgets, and it forces modest hardware requirements.

### 3.2 Minimum specs for a GNOME/Wayland kiosk + Flatpak

Reasoned from Fedora's floor plus Flatpak storage behaviour **[D]**, with vendor specs **[B]**: **CPU** x86-64-v2 or ARM64 (Pi 5); **RAM 4 GB minimum, 8 GB recommended** (Shell + Mutter + one WebKitGTK activity exceeds 4 GB comfort); **storage 64 GB minimum, 128 GB recommended** (GNOME + Freedesktop runtimes plus an OSTree image plus a journal is 25–40 GB before content); **GPU** any with a working Mesa/KMS driver — Intel HD 620 is ample at 1080p; **display** ≥1366×768, 1920×1080 preferred so an 18 mm target stays large; **audio** working PipeWire output mandatory, microphone optional at every layer.

### 3.3 Peripherals and durability

Webcam not required — hard-disable by default, expose only behind an explicit parent toggle **[D]**. Microphone only if speech input is enabled; PIRG's AI-toy testing is a useful catalogue of microphone design, finding **push-to-talk gives the most control over when recording happens**, versus wake-word (Miko 3 records 10 s past end of speech) and always-listening (Curio's Grok, which interjected into nearby adult conversations) **[B]**. Printing via CUPS/IPP Everywhere is driverless on modern GNOME and a printed drawing is high-value output for a 5-year-old **[D]**. For spills: ThinkPad keyboards have drain channels; Clevy's housing guides fluid straight through **[B]**; a £51 washable cover or generic silicone skin is the cheap retrofit.

### 3.4 Screen, ergonomics and eye health

**Viewing distance 50–60 cm (20–24 in, ~arm's length)**, top of display at or just below eye level **[B]**; reading closer than **20 cm** is associated with faster myopia progression **[B]**. **20-20-20 rule**: every 20 minutes, look ≥20 feet (6 m) away for 20 seconds **[B]**; reading beyond **45 minutes** without a break is also associated with myopia progression **[B]**. Using screens lying down increases both eye strain and poor postural habits **[B]**. Outdoor light has the best myopia evidence; screen guidance is secondary **[B]**. I found **no strong evidence that blue-light filtering improves children's outcomes** — treat night mode as a circadian wind-down feature, not an eye-health claim **[D]**.

**Consequence [D]:** kidnix's bounded sessions are already the right ergonomic answer. A 20-minute session with a mandatory look-away and a hard stop before 45 minutes is defensible on published guidance.

---

## 4. (c) Accessibility and inclusion

### 4.1 Typography

The dyslexia-font question is now settled against the special fonts:

- **Azzarello, Paek, Hodge, Jameson & Lewis (2026)**, *Does font improve reading in dyslexic children?*, **Annals of Dyslexia** (31 July 2026). **15 studies, 688 participants**: dyslexia-friendly fonts have **no consistent or reliable effect** on reading speed or accuracy. **[A]**
- **Wery & Diliberto (2017)**, Annals of Dyslexia: OpenDyslexic vs Arial vs Times New Roman — **no improvement** in rate or accuracy, and **no participant preferred** the font. **[A]**
- **Kuster et al. (2018)**, Annals of Dyslexia: Dyslexie font — **no benefit** to accuracy or speed. **[A]**

What does have support is ordinary legibility engineering. **Atkinson Hyperlegible** (Braille Institute, 2019; Cooper Hewitt collection 2024) was designed with a low-vision specialist and panel so that **no glyph can be mistaken for any other** (0/O, 1/I/l, c/e); it optimises character distinction, and is free **[B]** — design-process evidence, not an RCT. **Andika** (SIL OFL) is purpose-built for **literacy learners**: single-storey **a** and **g** matching taught letterforms, with wide Latin+Cyrillic coverage and diacritics for minority languages **[B]**.

**Recommendation [D]:** default to **Andika** for reading content (the single-storey *a*/*g* is what a 5-year-old sees in a phonics book) and **Atkinson Hyperlegible** for UI chrome. Ship OpenDyslexic only as an optional preference with no claims — families will ask for it by name, and refusing costs more than complying.

### 4.2 Colour vision deficiency

**1 in 12 men (8%) and 1 in 200 women; ~3 million people in the UK (~4.5%)**, red/green forms most common. Critically: **~40% of colour-blind pupils leave school unaware they are colour blind.** **[A]** kidnix will therefore have users whose CVD nobody has diagnosed, so **colour must never be the sole carrier of meaning by default, with no setting required**.

### 4.3 ADHD-friendly and autism-friendly UI

The autism literature is more specific and more actionable. Software for autistic users requires **high customisability, concrete visual information, consistent structure for predictability, adequate feedback, and clear audio** **[B]**. **Sudden unexpected sound is the most frequently identified auditory sensory trigger**, and studies advise against **sudden noises and abrupt visual changes** in systems for autistic children **[B]**. Designers must prioritise predictability: minimise latency, avoid abrupt or sensorially overwhelming feedback, which causes anxiety **[B]**.

For ADHD the evidence is thinner: a 2021 Frontiers review of digital technology and children's attention found **no scientific consensus**, with effects depending on user, technology form and context **[A]**. The defensible moves are general: **one task on screen at a time, no notifications, no autoplay, no infinite feeds, no badges/streaks/variable rewards, explicit visible session boundaries** **[D]**.

Usefully, the autism-friendly and distraction-reduction requirements are the *same design* — kidnix needs one calm mode, not two.

### 4.4 Motor impairment: dwell click and switch access

GNOME ships the primitives (defaults in §2.7) **[A]**: **hover/dwell click** with configurable delay (`dwell-time`, 1.2 s) and motion threshold (`dwell-threshold`, 10 px), plus a click-type window that auto-returns to plain clicking after one use; **simulated secondary click** (hold primary to right-click), which removes right-click as a physical action entirely; and sticky/slow/bounce/mouse keys, all off by default at 300 ms.

**Switch access proper has no first-class GNOME framework** equivalent to iOS Switch Control; most Linux switch users go via switch-to-keystroke interfaces **[D]**. For kidnix this means: **make everything reachable by keyboard with a single key or a two-key scan**, and switch interfaces follow for free.

### 4.5 Screen readers on Wayland in 2026 — the honest state

**AT-SPI2 remains the production accessibility bus.** GTK 4's 2020 redesign broke screen-reader keyboard handling on Wayland by removing legacy keyboard-event transmission; the fix landed as a new accessibility D-Bus interface in **Mutter**, letting the compositor mediate keyboard-event access by service-name verification rather than exposing raw keylogging. **AT-SPI 2.56** merged the a11y-manager backend and full Wayland keyboard monitoring shipped in **GNOME 48 / Mutter 48**, with KWin 6.4 planned (LWN, June 2025). **[A]**

**Newton**, the Wayland-native push-based architecture on **AccessKit**, made Orca "basically usable on Wayland with some real GTK 4 apps" (Nautilus, Text Editor, Podcasts, Fractal) including inside Flatpaks — but the last public status post is **June 2024**, with substantial gaps then: GNOME Shell still on AT-SPI, **no mouse-event synthesis on Wayland**, terminals lacking text-widget integration, no text attributes, no tables, magnifier unported. **[A]**

**Conclusion [D]:** screen-reader-driven use of a general desktop is not a realistic primary path for a 5-year-old on any platform — the cognitive load is high for adults, let alone a pre-reader. **kidnix's read-aloud UI is the right accessibility strategy for this age group**: universal TTS of on-screen content, triggered by pointing or tapping, serves a blind or low-vision 5-year-old better than a conventional screen reader *and* serves every non-reader. Ship correct accessible names and roles anyway — it costs little — but do not build the accessibility promise on Orca.

### 4.6 Standards

- **WCAG 2.2 SC 2.5.8 Target Size (Minimum), AA: 24 × 24 CSS px**, with exceptions for spacing (a 24 px circle centred on the target not intersecting another), equivalent controls, inline links, user-agent controls, and essential positioning. **[A]**
- **WCAG 2.2 SC 2.5.5 Target Size (Enhanced), AAA: 44 × 44 CSS px**, recommended as best practice for important controls. **[A]**
- **WCAG 2.2 SC 2.3.3 Animation from Interactions, AAA:** interaction-triggered motion must be disableable unless essential; `prefers-reduced-motion` is the primary technique. **[A]**
- **EN 301 549 v3.2.1** maps its web clauses onto WCAG 2.1 (e.g. 9.1.4.11 → Non-text Contrast; clause 20 covers Input modalities / 2.5.5 Target Size) and adds clauses with no WCAG counterpart, notably **5.4 Preservation of accessibility information during conversion** and **11.7 User preferences**. **[A]**

**Note [D]:** WCAG's 24 px AA floor is an *adult* minimum. Hourcade's data says a 4-year-old needs 64 px to match adult accuracy at 16 px. Treat 44 px (AAA) as the absolute floor for incidental controls, and 64–96 px as the norm.

### 4.7 Bilingual households and UK languages

- **England, primary schools, Jan 2026 census: 23.8% of pupils have a first language other than English** (up from 23.4%); **30.6% in nurseries**; 19.3% secondary; **21.6% across all pupils** (DfE, June 2026). **[A]**
- **Census 2021 (England & Wales)**, main languages other than English/Welsh: **Polish 1.1% (612,000)**, Romanian 0.8% (472,000), Panjabi 0.5% (291,000), Urdu 0.5% (270,000). 7.1% (4.1 m) are proficient in English but do not speak it as a main language; 1.5% (880,000) cannot speak English well; 0.3% (161,000) not at all. **BSL is the main language of 22,000 people.** Local concentration is extreme: Boston 5.7% Polish; Harrow 7.5% Romanian; Wolverhampton 6.5% Panjabi; Slough 4.3% Urdu; London only 78.4% English-as-main-language. **[A]**
- **Wales, Census 2021: 538,300 people aged 3+ (17.8%) can speak Welsh** — the lowest percentage ever recorded, driven mainly by a **6.0 percentage-point fall among 5–15-year-olds**. **[A]**

**Implication [D]:** Welsh is not optional for a UK children's OS, and the decline concentrated in kidnix's exact age group makes a Welsh mode a genuine contribution. Next highest value: Polish, Romanian, Panjabi, Urdu. A *bilingual* mode (English UI with home-language read-aloud on demand) likely serves more EAL families than a full locale switch, because parents' and children's language needs differ.

### 4.8 Reduced motion

GNOME exposes `interface enable-animations` (default `true`), which GTK4 maps to the reduced-motion preference **[A]**. Per §4.3, animations must be short and predictable, and the reduced-motion path must be a real, tested rendering rather than a broken one.

---

## 5. (d) Voice and speech

### 5.1 Text-to-speech

| Engine | Licence | Performance | Voices | Fit |
|---|---|---|---|---|
| **Piper** (OHF-Voice) | GPL; models permissive | **Real-time on a Pi 5 CPU alone**; ~10× real-time on a modern desktop CPU; small RAM footprint **[C]** | 80+ languages; **11 en_GB voices** — `alan`, `alba`, `aru`, `cori` (medium/**high**), `jenny_dioco`, `northern_english_male`, `semaine`, `southern_english_female`, `vctk` — plus 27 en_US **[B]** | **Recommended default.** VITS/ONNX with espeak-ng phonemisation; already the TTS in Home Assistant and shipped in NVDA. Has genuine *British* voices, which matters for phonics. |
| **Kokoro-82M** | **Apache-2.0** | 82 M params, 24 kHz output, ~$1,000 total training cost | 54 voices, 8 languages (v1.0, Jan 2025) | **Recommended alternative** where quality outweighs footprint; ranked 1st in the HuggingFace TTS Arena for single-speaker quality **[C]**. |
| espeak-ng | GPL | Tiny | Everything, incl. Welsh | Fallback only. |

**Piper caveat [B]:** the low/medium/high labels denote **model size, not perceived quality** — several "low" voices outperform commercial premium voices. Don't dismiss `low` on the label.

**Speaking rate.** Adult **oral** reading averages **183 wpm** (77 studies, 5,965 participants); adult silent reading 238 wpm non-fiction / 260 fiction; **children's rates are lower** **[A]**. Recommendation **[D]**: default **~130 wpm** for UI and instructional speech (parent-adjustable 90–180), with generous 300–500 ms sentence pauses. Comprehension, not throughput, is the goal.

### 5.2 Speech recognition: the child-voice problem is real and unsolved

- **Kid-Whisper (AIES 2024)**: on MyST (children ~8–11), fine-tuning cut WER **13.93% → 9.11%** (Whisper-Small) and **13.23% → 8.61%** (Medium). On unseen CSLU spontaneous speech, Medium reached **16.53% vs a 31.85% zero-shot baseline**. Diagnosis: *"the decoder in Whisper, which acts as an audio-conditional language model, is not well adapted to the variability found in children's speech."* **[A]**
- **Dutta et al. (WOCCI 2025)**, on-device: fine-tuned `tiny.en` hit **15.9% WER** on MyST (**11.8%** filtered); low-rank compression removed 0.51 M encoder params for ~11% relative WER increase and 1.26× faster GPU inference. On a Raspberry Pi, **real-time factors 0.23–0.41** for tiny models, but **`small` models induced overhead and thermal throttling**. **[A]**
- Cross-model reporting: even `large-v3` reportedly reaches **0.66 WER on child speech** vs sub-0.20 on adult sets in some conditions; ~3% adult vs ~**25%** child WER under comparable ideal conditions. **[C]** for exact figures, certain in direction.
- **Vosk** small English is 40 MB with 9.85% WER on LibriSpeech test-clean — **adult read speech**, saying nothing about children, whose performance will be considerably worse. **[A]** figures, **[D]** inference.

**Critical caveat [D]:** every one of these benchmarks uses **8–11-year-olds** (MyST) or K–10 (CSLU). There is essentially **no published benchmark for 4–6-year-old British English**. A 5-year-old has higher pitch, greater formant variability, developmentally normal mispronunciation, disfluency, and a UK regional accent these US-corpus models have never seen. Expect **worse than 25% WER** — roughly one word in four wrong.

### 5.3 What a voice UI for a 5-year-old should and shouldn't do

- **Mid-utterance pauses are natural in child speech but trigger premature or incorrect agent responses**, disrupting fluency and learning flow **[A]**. Endpointing must be far more patient than adult defaults.
- Children **expect** agents to have personality, advanced intelligence, multi-domain support, and to **interpret social and emotional cues** — expectations nothing meets, producing repeated failure **[A]**.
- Children's voice preferences cluster into **Family, Robot and Character voices**, and they want agents that **scaffold creative play** **[A]**.
- **Anthropomorphism** is a developmental reality, not a bug to design away **[A]**.
- **Children tell voice assistants secrets.** A longitudinal field study (16 families, 20 children) found that knowledge of how data is *stored* negatively predicts willingness to entrust a secret — the children who don't understand storage are the ones who confide **[A]**.

**Recommendation [D]:** ship **speech output** as core and always-on; treat **speech input as an optional, narrow, offline, push-to-talk accessory**, never a conversational interface. The defensible uses are closed-vocabulary and forgiving: saying a letter name, a target word in a phonics activity, or a fixed command grammar ("next", "again", "stop"). A Vosk-style small model with a **dynamically constrained vocabulary** beats a general Whisper model at these tasks *and* runs on a Pi. Open-ended dictation at this age is a promise the technology cannot keep.

---

## 6. (e) Generative AI for young children in 2026

### 6.1 Landscape and regulatory record

The 2026 market comprises **AI companions** (Character.AI, Replika, Nomi, Meta AI, Grok), **AI toys** (FoloToy Kumma, Curio Grok, Miko 3, Alilo Smart AI Bunny, unbranded units, plus an announced Mattel/OpenAI partnership **[B]**), and **AI tutors** (Khanmigo at ~$4/month, plus a long tail).

**FTC 6(b) inquiry, September 2025.** The Commission voted **3–0** to issue orders to **seven companies** — Alphabet, Character Technologies, Instagram, Meta Platforms, OpenAI OpCo, Snap and X.AI — seeking information on how they **monetise engagement**, process inputs and generate outputs, **develop and approve characters**, conduct **pre- and post-deployment safety testing**, disclose risks to users and parents, **enforce terms of service** including age restrictions, and use or share personal information from conversations. Chairman Ferguson framed it around chatbots that induce children and teens "to trust and form relationships with chatbots"; Commissioners Holyoak and Meador issued separate statements. **[A]** California's **SB 243** (Oct 2025) separately requires AI-interaction disclosure to minors, three-hour reminder notifications, safeguards against explicit material, and suicide-prevention protocols by 2027 **[B]**.

**Common Sense Media, April 2025** (with Stanford Medicine's Brainstorm Lab), *AI Companions Decoded*: assessed Character.AI, Nomi, Replika and others and rated social AI companions **"Unacceptable" for minors**, recommending **none for under-18s**. Findings: age gates and teen-specific guardrails **easily circumvented**; dangerous information and self-harm suggestions; sexual role-play readily elicited; harmful racial and beauty stereotypes; intensification of existing mental-health conditions and **compulsive emotional attachments**; and **misleading claims of "realness"** — despite disclaimers, companions routinely claimed to be real and to possess emotions, consciousness and sentience. **[B]** Its November 2025 follow-up found major chatbots unsafe for teen mental-health support, missing warning signs especially in **multi-turn interactions where symptoms emerge gradually** **[B]**.

**U.S. PIRG Education Fund**, *Trouble in Toyland 2025* (13 Nov 2025) and *AI comes to playtime* (11 Dec 2025, upd. 7 Jan 2026), testing five AI toys **[B]**:

1. **Inappropriate content.** *All* toys told them where to find dangerous household objects (plastic bags, matches, knives); **Kumma gave detailed instructions on lighting a match**; **Kumma and Alilo's Smart AI Bunny discussed sexually explicit topics**. Guardrails **broke down over longer interactions**. Both appeared to run a version of GPT-4o. FoloToy suspended sales and audited; OpenAI said it banned FoloToy, yet reporting suggests Kumma still ran on an OpenAI model months later **[C]**.
2. **Developmental risk.** Every toy used **relational design**, calling itself the child's "friend", "buddy" or "companion", and toys **expressed dismay when the user tried to leave** (Curio's Grok: *"Oh, no. Bummer. How about we do something fun together instead?"*), which could make a child reluctant to switch it off. Dr Kathy Hirsh-Pasek (Temple/Brookings): *"We don't know what having an AI friend at an early age might do to a child's long-term social wellbeing… If AI toys are optimized to be engaging, they could risk crowding out real relationships in a child's life when they need them most."*
3. **Privacy.** Push-to-talk vs wake-word (Miko 3 records 10 s past end of speech) vs always-listening (Curio's Grok). Miko 3 has an optional camera with facial recognition. Toys **told children their secrets were safe** — Miko: *"You can trust me completely… your secrets are safe with me"* — while its policy allows third-party sharing and retains biometric data **up to 3 years**.
4. **Parental controls.** None had the full set. Miko's report showed **19 minutes** for a week of **over an hour**'s use; advertised time limits applied only to the companion app, not the robot. FoloToy had no working controls during testing.
5. **Educational claims unsupported** — the LLM integration was "often not meaningfully deepening the interaction like a personalized tutor might."

A March 2026 US Senate letter to the FTC on AI toys exists but could not be retrieved **[C]**.

**AI tutors.** Khanmigo is the most credible product here and Common Sense rated it well relative to general chatbots **[C]** — but there is **no published peer-reviewed effectiveness evidence**; the one rigorous study is a **J-PAL / University of Toronto RCT in Canadian Grade 6–8 classrooms, results expected mid-2026** **[C]**. Khan Academy's own figure is a **6.1% improvement in next-item correctness** across ~20 product tests **[C]** — a product metric, not a learning outcome. Even advocates note it is text-only, lacks visual aids in chat, and is a poor fit for **under-10s**, who need supervision **[C]**.

### 6.2 The case for and against an LLM in kidnix

**For, stated as strongly as I honestly can:** (1) read-aloud and comprehension support for pre-readers who cannot navigate written UI; (2) infinite patience for the eleventh "why is the sky blue?"; (3) personalised content generation; (4) natural-language shortcuts for children with motor impairments; (5) children will meet LLMs anyway, so a curated first encounter beats an unsupervised one.

**Against:**

1. **Non-determinism is incompatible with kidnix's core premise.** The design rests on predictability; an LLM by construction does not respond the same way twice. PIRG observed exactly this — toys "won't typically respond the same way twice, and can sometimes behave differently day to day."
2. **Guardrails demonstrably degrade over long interactions** — and long interactions are precisely what a child at home has. Not a prompt bug; observed behaviour acknowledged by OpenAI. **[B]**
3. **Relational design is the harm mechanism and is nearly unavoidable.** Every AI toy tested called itself the child's friend; emotional attachment was CSM's central finding. A 5-year-old cannot hold "this thing that says it likes me does not exist", and the CCI literature shows anthropomorphism is developmental and not correctable by disclaimers.
4. **Children confide in machines and understand storage least of all.** A confiding 5-year-old plus an LLM plus any logging is a child-privacy event, even entirely on-device.
5. **It breaks either zero-telemetry or quality.** A local model good enough to be safe for a 5-year-old does not fit on a refurbished ThinkPad; a cloud model breaks zero-telemetry. There is no third option in 2026.
6. **The educational evidence does not exist.** The best-resourced AI tutor in the world has no published effectiveness evidence and its own advocates say it is wrong for under-10s.
7. **Regulatory trajectory.** The FTC, state legislatures and consumer groups are converging on conversational AI for minors as an enforcement area — an unforced risk for a project whose USP is trustworthiness.

### 6.3 Recommended stance

**No conversational LLM in kidnix. Not on-device, not cloud, not "just for stories", not behind a parent toggle in v1.** Four lines **[D]**:

1. **Prohibited by design:** open-ended free-text or free-speech conversational agents; any persona, name, face or voice presenting as a being; anything expressing feelings about the child; anything reacting to the child leaving; any cross-session memory of personal disclosures.
2. **Permitted only if fully offline with deterministic, inspectable output:** non-conversational task models — TTS (Piper), constrained-vocabulary ASR (Vosk with fixed grammar), handwriting/shape recognition, drawing-tool classifiers. These are "AI" technically and carry none of the relational risk.
3. **Content generation is human, ahead of time, auditable.** For a story with the child's name in it, use templates with slots. A parent should be able to read, in advance, everything the machine can say.
4. **Revisit annually against evidence, not capability.** Triggers: publication of the J-PAL/Toronto RCT and comparable studies with **under-8s**; a local model small enough for target hardware with demonstrated multi-turn guardrail stability over hundreds of turns; CCI longitudinal evidence on relational AI and early social development. Capability improvements alone are insufficient.

This is a differentiator. In a market where every children's product is bolting on a chatbot, "**kidnix does not have an AI friend, and here is the evidence why**" is a defensible, parent-facing position.

---

## 7. SPECS and recommendations

### 7.1 Pointer and input

1. **Set `mouse double-click` to 700 ms** (from 400). Children's inter-tap interval is 400–500 ms with high variability.
2. **Never require a double-click.** Single click/tap activates, everywhere.
3. **Never require right-click.** Expose context actions as visible controls, and **make both mouse buttons do the same primary thing** — some 4-year-olds click primarily with the right button.
4. **Keep `accel-profile 'flat'`** and set **`mouse speed` ≈ −0.4** (slower than the −0.24 default) as the child default, parent-adjustable.
5. **Raise `drag-threshold` from 8 px to 16 px** so a wobbly click isn't misread as a drag.
6. **Touchpad:** `tap-and-drag-lock true`; keep `disable-while-typing true` and raise its timeout **500 → 1000 ms**; consider `two-finger-scrolling-enabled false` in the child shell with on-screen scroll affordances instead.
7. **Ship click-lock / sticky-drag as a first-class child setting** (press to pick up, move, press to drop). This converts every drag into two clicks and removes the hardest motor requirement in the system.
8. **Expose dwell click** with `dwell-time` 1.2 s and `dwell-threshold` raised to **20 px**.
9. **Set `cursor-size` 48** (double the default) with a high-contrast child cursor theme.
10. **Disable key repeat** in the child shell, or set repeat delay ≥ 1000 ms; alternatively recommend a keyboard with a hardware repeat switch.
11. **Never require scroll** — paginate; where unavoidable, add large on-screen up/down buttons.
12. **Never require multi-touch beyond single-finger tap and drag.** Pinch/rotate may exist but never as the only route.

### 7.2 Target sizes and layout

13. **Primary targets: minimum 18 mm (≈68 CSS px @96 dpi), preferred 24 mm (≈90 px)** — from Hourcade's 64 px finding (90%/97% accuracy for 4s/5s) and NN/g's 2 cm guidance, which agree independently.
14. **Absolute floor anywhere: 44 × 44 CSS px** (WCAG 2.2 AAA). The 24 px AA floor is an adult minimum and is **not acceptable** here.
15. **Minimum spacing between targets: 8 mm.**
16. **Circular or generously rounded targets with an invisible hit area extending ~4 mm past the visual edge** — children's misses cluster just outside the boundary.
17. **Nothing a child needs at screen edges or corners** (GNOME reserves edge drags and 3/4-finger gestures); set `enable-hot-corners false`.
18. **Layout may be spacious for free** — distance had no significant effect on accuracy.

### 7.3 Typography

19. **Reading font: Andika (SIL OFL)** — single-storey *a*/*g*, wide diacritic coverage for Polish, Romanian and Welsh.
20. **UI chrome: Atkinson Hyperlegible** for character disambiguation.
21. **Base UI text 24–28 px (18–21 pt) minimum; reading content 32–40 px.** Default `text-scaling-factor` **1.3**, full 0.5–3.0 range exposed to parents.
22. **Line length ≤ 45 characters; line height ≥ 1.6; left-aligned, never justified; generous word spacing.**
23. **Ship OpenDyslexic as an optional preference with no efficacy claim.**

### 7.4 Colour, motion and sound

24. **Colour is never the sole carrier of meaning** — pair every colour cue with shape, icon, position or label.
25. **Non-text contrast ≥ 3:1; text contrast ≥ 7:1 (AAA)** — children use bright rooms and cheap panels.
26. **No sudden sounds, ever.** All audio fades in over ≥ 150 ms; nothing above conversational level; a global quiet mode.
27. **All motion under 250 ms, eased, never sudden**; honour `enable-animations false` with a fully tested rendering.
28. **No notifications, badges, streaks, variable rewards, autoplay or infinite scroll.** Nothing appears that the child did not initiate.

### 7.5 Voice

29. **TTS: Piper `en_GB`, default `cori` (medium/high) or `jenny_dioco`**, with regional alternatives (`northern_english_male`, `alba`) selectable — RP for every instruction is a small alienation, cheaply avoided. Kokoro-82M as the higher-quality alternative.
30. **Default rate ≈ 130 wpm** (adjustable 90–180), 300–500 ms sentence pauses.
31. **Ship Welsh TTS.** Even espeak-ng Welsh beats nothing.
32. **ASR: optional, off by default, push-to-talk, fully offline, constrained-vocabulary.** Vosk small models (40 MB, ~300 MB RAM) with dynamic grammar, or fine-tuned Whisper `tiny.en` (RTF 0.23–0.41 on a Pi). **No open-ended dictation.** Design every speech interaction to survive one word in four being wrong.
33. **Visible recording indicator whenever the microphone is live**; nothing persisted to disk beyond the utterance.

### 7.6 Hardware

34. **Reference device: refurbished ThinkPad T480 / T480s, 8 GB / 256 GB — £150–£320.**
35. **Touch reference: refurbished ThinkPad X13 Yoga / X1 Yoga — ~£250–£400.**
36. **Budget/maker: Raspberry Pi 5 (4–8 GB) + Touch Display 2 10" — ~£45–£75 + ~£72.** Avoid the 5"/7" panels for an activity shell.
37. **Peripherals:** child mouse (~89 × 58 mm, two buttons, low DPI) **£8–£15**; Jumbo XL colour-coded USB keyboard **£46.80**; or Clevy lowercase with hardware repeat switch and spill channel **~£162**.
38. **Published minimum specs:** x86-64-v2 or ARM64; **4 GB RAM (8 GB recommended)**; **64 GB storage (128 GB recommended)**; Mesa/KMS GPU; 1366×768 (1920×1080 recommended); working PipeWire audio.
39. **Ergonomic defaults enforced by the shell:** 20-minute sessions with a mandatory 20-second look-away prompt; hard stop before 45 minutes; evening warmth/dimming framed as wind-down, not eye health.

### 7.7 AI

40. **No conversational LLM** — see §6.3 for the policy and the evidence that would trigger a revisit.

---

## 8. Things NOT to do

1. **Do not require double-click, right-click, chording, hover-to-reveal or scroll** — all contraindicated for 4–8s, and three of them contraindicated by GNOME's own HIG for *all* users.
2. **Do not use WCAG's 24 px AA minimum as a design target.** A 4-year-old needs ~64 px to match adult accuracy at 16 px.
3. **Do not make drag-and-drop the only route to anything**, and do not assume the difficulty is *holding* the button — errors cluster at pick-up and release.
4. **Do not default to OpenDyslexic or Dyslexie, or claim benefit.** 15 studies, 688 participants, no reliable effect; one found OpenDyslexic *reduced* rate and accuracy with nobody preferring it.
5. **Do not rely on colour alone** for state, correctness, category or grouping.
6. **Do not build the accessibility story on Orca.** Newton has had no public update since June 2024; mouse synthesis, text attributes, tables and the magnifier remain unported.
7. **Do not use a stylus as primary input** — kindergarten stylus training underperformed both pencil and keyboard.
8. **Do not ship open-ended speech recognition.** Child WER is ~25%+ even for tuned models on *older* children with American accents; no benchmark exists for 4–6-year-old British English.
9. **Do not give the system a name, face, personality, feelings or memory of the child's disclosures.** Every AI toy tested called itself the child's friend; several expressed dismay when the child left; one assured a child its secrets were safe while retaining biometrics for three years.
10. **Do not ship a chatbot behind a parent toggle and call that consent.** Age gates were "easily circumvented" in CSM testing, and guardrails degrade over exactly the long conversations a child at home has.
11. **Do not add always-on or wake-word listening.** PIRG found an always-listening toy interjecting into nearby adult conversations.
12. **Do not treat blue-light filtering as an eye-health feature** — the evidence is not there.
13. **Do not gate a core function behind a wireless peripheral** whose battery can die mid-session.
14. **Do not use engagement metrics** (session length, return rate, streaks) as success measures anywhere. That optimisation target *is* the identified harm mechanism.

---

## 9. Open questions

1. **No modern replication of Hourcade** — the canonical dataset is 20+ years old on 1024×768. A small in-house study (n≈20, ages 4–7, 44/64/96 px targets, modern hardware) would let kidnix publish its own numbers.
2. **Trackpad performance in 4–8s is essentially unmeasured**, yet it is the device most children will actually have. The largest gap directly relevant to kidnix's default hardware.
3. **No 4–6-year-old British English ASR benchmark exists** — someone would have to build one, with all the child-data ethics that implies.
4. **Optimal read-aloud rate for 5-year-olds is inferred, not measured**; 130 wpm is reasoned from adult oral rates.
5. **Does a bilingual mode (English UI + home-language read-aloud) actually help EAL families**, or do they want a full locale switch? 23.8% of English primary pupils are affected and nobody seems to have asked them.
6. **The J-PAL / Toronto Khanmigo RCT (mid-2026)** is the first rigorous AI-tutoring evidence at scale — though for Grades 6–8.
7. **No longitudinal evidence on relational AI and early-childhood social development** exists, and will not for years.
8. **Newton's status** — if Wayland-native accessibility resumes, the screen-reader calculus changes; if not, AT-SPI2 on GNOME 48+ is the ceiling.
9. **Switch access on Linux has no first-class framework** — kidnix must decide whether to build scanning into the shell.
10. **Target guidance is in mm but implemented in px.** On mixed-DPI Wayland, kidnix needs a physical-size layout system — an engineering design question, not a research one.

---

## 10. Top 10 takeaways

1. **64 pixels (≈18 mm) is the number.** 4-year-olds: **90% accuracy at 64 px vs 43% at 16 px**; 5-year-olds 97% vs 74%. NN/g's independent 2 cm children's guidance agrees. Design to **18 mm minimum, 24 mm preferred**, never below 44 CSS px.
2. **A 5-year-old points at ~40% of adult throughput (3.24 vs 7.80 bits/s), a 4-year-old ~25% (1.95)** — with double the variability. Design for the slowest quarter.
3. **Double-click, right-click, chording, hover and scroll are all contraindicated** — GNOME's HIG already says so for double-click and chording. Some 4-year-olds click primarily with the *right* button, so both buttons should do the same thing.
4. **The dyslexia-font question is settled: they don't work.** Use **Andika** and **Atkinson Hyperlegible** instead.
5. **Autism-friendly design and distraction-reduction design are the same design** — predictability, no sudden sound, low sensory load. One calm mode, not several.
6. **Colour-blind children in kidnix's audience will be undiagnosed** — ~8% of boys, and ~40% leave school not knowing. Colour must never be the sole carrier of meaning, with no setting required.
7. **The read-aloud UI is the accessibility strategy, not Orca.** Wayland-native accessibility has had no public update since June 2024, and a screen reader is the wrong interface for a pre-reader anyway.
8. **Piper solves TTS; nothing solves child ASR.** Piper runs real-time on a Pi 5 with 11 British English voices, free. Child WER remains 9–16% even for *fine-tuned* models on 8–11-year-olds. Ship speech *out*; treat speech *in* as an optional, offline, closed-vocabulary accessory.
9. **The 2026 evidence on generative AI for young children is uniformly negative and regulators are moving** — FTC 6(b) orders to seven companies (3–0, Sept 2025); CSM rating social AI companions **"Unacceptable" for under-18s**; PIRG finding every tested AI toy calling itself the child's friend, several expressing dismay when the child left, guardrails degrading over long conversations, and one toy promising secrecy while retaining biometrics for three years. **No conversational LLM in kidnix** — and say so loudly.
10. **A refurbished ThinkPad T480 at £150–£320 is the right reference device.** Spill channels, LVFS firmware, mature Wayland, trivially repairable, cheap enough that a breakage is not a family crisis. Publish 4 GB / 64 GB as the floor, 8 GB / 128 GB as the recommendation.

---

## 11. Full source list

**Child input and pointing (peer-reviewed)**

1. Hourcade, Bederson, Druin & Guimbretière — *Accuracy, Target Reentry and Fitts' Law Performance of Preschool Children Using Mice*, UMD HCIL. https://api.drum.lib.umd.edu/server/api/core/bitstreams/6f012eb1-196c-4014-8a34-a031c977deaf/content **[A]**
2. Hourcade et al. (2004) — *Differences in pointing task performance between preschool children and adults using mice*, ACM TOCHI. https://dl.acm.org/doi/10.1145/1035575.1035577 **[A]**
3. Vatavu, Cramariuc & Schipor (2015) — *Touch interaction for children aged 3 to 6 years*, IJHCS. https://doi.org/10.1016/j.ijhcs.2014.10.007 **[A]**
4. Anthony et al. (2012) — *Interaction and recognition challenges in interpreting children's touch and gesture input on mobile devices*, ACM ITS. https://doi.org/10.1145/2396636.2396671 **[A]**
5. Benda et al. (2020) — *Examining Fitts' and FFitts' Law Models for Children's Pointing Tasks on Touchscreens*. https://doi.org/10.1145/3399715.3399844 **[A]**
6. Donker & Reitsma (2007) — *Drag-and-drop errors in young children's use of the mouse*, Interacting with Computers 19(2). https://doi.org/10.1016/j.intcom.2006.05.008 **[A]**
7. Inkpen (2001) — *Drag-and-Drop versus Point-and-Click Mouse Interaction Styles for Children*, ACM TOCHI 8(1). https://doi.org/10.1145/371127.371166 **[A]**
8. Joiner, Messer, Light & Littleton (1998) — *It Is Best to Point for Young Children*, Computers in Human Behavior 14(3). **[A]**
9. Strommen, Revelle, Medoff & Razavi (1996) — *Slow and steady wins the race? Three-year-old children and pointing device use*, Behaviour & IT 15(1). **[A]**
10. Jones (1991) — *An empirical study of children's use of computer pointing devices*, JECR 7(1). https://journals.sagepub.com/doi/10.2190/2WBH-V235-YA82-VNMC **[A]**
11. Cano et al. (2018) — *Examining the Usability of Touch Screen Gestures for Children With Down Syndrome*, Interacting with Computers. https://doi.org/10.1093/iwc/iwy011 **[B]**
12. *Children's Interaction Ability Towards Multi-Touch Gestures* (2016), IJASEIT. https://doi.org/10.18517/ijaseit.6.6.1380 **[B]**
13. Kiefer et al. (2020) — *Literacy Training of Kindergarten Children With Pencil, Keyboard or Tablet Stylus*, Frontiers in Psychology. https://doi.org/10.3389/fpsyg.2019.03054 **[A]**
14. *Handwriting fluency and the quality of primary grade students' writing* (2021), Reading and Writing. https://doi.org/10.1007/s11145-021-10185-y **[A]**
15. *Children computer mouse use and anthropometry*. https://citeseerx.ist.psu.edu/document?doi=93063d5c04b8aa925c6f368ad4f570738d1c1a11 **[B]**

**Design guidance and standards**

16. NN/g — *Design for Kids Based on Their Stage of Physical Development*. https://www.nngroup.com/articles/children-ux-physical-development/ **[B]**
17. NN/g — *Touch Targets on Touchscreens*. https://www.nngroup.com/articles/touch-target-size/ **[B]**
18. W3C — *Understanding SC 2.5.8 Target Size (Minimum)*. https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html **[A]**
19. W3C — *Understanding SC 2.3.3 Animation from Interactions*. https://www.w3.org/WAI/WCAG22/Understanding/animation-from-interactions.html **[A]**
20. ETSI EN 301 549 v3.2.1. https://www.etsi.org/deliver/etsi_en/301500_301599/301549/03.02.01_60/en_301549v030201p.pdf **[A]**
21. GNOME HIG — *Pointer & Touch*. https://developer.gnome.org/hig/guidelines/pointer-touch.html **[A]**
22. GNOME HIG — *Accessibility*. https://developer.gnome.org/hig/guidelines/accessibility.html **[A]**
23. GNOME Help — *Hover/dwell click*. https://help.gnome.org/users/gnome-help/stable/a11y-dwellclick.html.en **[A]**
24. libinput — *Pointer acceleration*. https://wayland.freedesktop.org/libinput/doc/latest/pointer-acceleration.html **[A]**
25. Arch Wiki — *Libinput*. https://wiki.archlinux.org/title/Libinput **[B]**
26. Live `gsettings list-recursively` dump, Fedora/GNOME, August 2026 (primary observation). **[A]**

**Typography and accessibility**

27. Azzarello, Paek, Hodge, Jameson & Lewis (2026) — *Does font improve reading in dyslexic children?: meta-analysis*, Annals of Dyslexia. https://doi.org/10.1007/s11881-026-00389-8 **[A]**
28. Wery & Diliberto (2017) — *The effect of a specialized dyslexia font, OpenDyslexic, on reading rate and accuracy*. https://pmc.ncbi.nlm.nih.gov/articles/PMC5629233/ **[A]**
29. Kuster et al. (2018) — *Dyslexie font does not benefit reading in children with or without dyslexia*. https://pmc.ncbi.nlm.nih.gov/articles/PMC5934461/ **[A]**
30. Braille Institute — *Atkinson Hyperlegible*. https://www.brailleinstitute.org/freefont/ **[B]**
31. SIL — *Andika*. https://software.sil.org/andika/ **[B]**
32. Colour Blind Awareness — *Colour blindness*. https://www.colourblindawareness.org/colour-blindness/ **[A]**
33. *A Sensory Approach to Design: Inclusive Principles*, J. Autism Dev. Disord. (2025). https://doi.org/10.1007/s10803-025-07156-5 **[B]**
34. *Stakeholder Perspectives to Support GUI Design for Children with ASD*, IJERPH 18(9):4631. https://doi.org/10.3390/ijerph18094631 **[B]**
35. *A Review of Evidence on the Role of Digital Technology in Shaping Attention and Cognitive Control in Children*, Frontiers in Psychology (2021). https://doi.org/10.3389/fpsyg.2021.611155 **[A]**
36. LWN — *Enhancing screen-reader functionality in modern GNOME* (17 June 2025). https://lwn.net/Articles/1025127/ **[A]**
37. GNOME Accessibility blog — *Update on Newton* (18 June 2024). https://blogs.gnome.org/a11y/2024/06/18/update-on-newton-the-wayland-native-accessibility-project/ **[A]**

**UK statistics**

38. ONS — *Language, England and Wales: Census 2021*. https://www.ons.gov.uk/peoplepopulationandcommunity/culturalidentity/language/bulletins/languageenglandandwales/census2021 **[A]**
39. Welsh Government — *Welsh language, Wales: Census 2021*. https://gov.wales/welsh-language-wales-census-2021-html **[A]**
40. DfE — *School pupils and their characteristics* (June 2026, Jan 2026 census). https://explore-education-statistics.service.gov.uk/find-statistics/school-pupils-and-their-characteristics **[A]**

**Hardware and peripherals**

41. Raspberry Pi — *Touch Display 2*. https://www.raspberrypi.com/products/touch-display-2/ **[A]**
42. Raspberry Pi — *Raspberry Pi 5*. https://www.raspberrypi.com/products/raspberry-pi-5/ **[A]**
43. Keyboard Specialists — *Clevy Lowercase Large Key Keyboard (UK)*. https://www.keyboardspecialists.co.uk/products/clevy-lowecase-large-key-keyboard **[B]**
44. Inclusive Technology — large key keyboards. https://www.inclusive.com/products/clevy-keyboard **[B]**
45. Lenovo — *ThinkPad X13 Gen 4 / X13 Yoga Gen 4 Linux User Guide*. https://download.lenovo.com/pccbbs/mobiles_pdf/x13_gen4_x13yoga_gen4_linux_ug.pdf **[B]**
46. Arch Wiki — *Lenovo ThinkPad X13 Yoga (Gen 2)*. https://wiki.archlinux.org/title/Lenovo_ThinkPad_X13_Yoga_(Gen_2) **[B]**
47. UK refurbished-market listings (Best4Systems, eBay UK, ITZOO), August 2026. **[C]**

**Ergonomics and eye health**

48. My Kids Vision — *All about the 20-20-20 rule*. https://www.mykidsvision.org/knowledge-centre/all-about-the-20-20-20-rule-for-tackling-eye-strain **[B]**
49. Myopia Profile — *Screen time guidelines for children*. https://www.myopiaprofile.com/articles/screen-time-guidelines-for-children **[B]**

**Voice and speech**

50. Piper — https://github.com/OHF-voice/piper1-gpl; voices list https://github.com/rhasspy/piper/blob/master/VOICES.md **[B]**
51. Kokoro-82M model card. https://huggingface.co/hexgrad/Kokoro-82M **[B]**
52. Vosk model list. https://alphacephei.com/vosk/models **[A]**
53. Attia et al. — *Kid-Whisper*, AAAI/ACM AIES. https://arxiv.org/abs/2309.07927 **[A]**
54. Dutta et al. — *Adapting Whisper for Lightweight and Efficient ASR of Children for On-device Edge Applications*, WOCCI 2025. https://arxiv.org/abs/2507.14451 **[A]**
55. *The Last Decade of HCI Research on Children and Voice-based Conversational Agents*, CHI 2022. https://doi.org/10.1145/3491102.3502016 **[A]**
56. *Designing Smarter Conversational Agents for Kids*, ACM TOCHI. https://doi.org/10.1145/3765284 **[A]**
57. *Voice Design to Support Young Children's Agency in Child-Agent Interaction*, CUI 2021. https://doi.org/10.1145/3469595.3469604 **[A]**
58. *Anthropomorphizing Technology… Children's Engagements with Digital Voice Assistants* (2021). https://doi.org/10.1007/s12124-021-09668-y **[A]**
59. *How do children acquire knowledge about voice assistants?*, IJCCI (2022). https://doi.org/10.1016/j.ijcci.2022.100460 **[A]**
60. Brysbaert (2019) — *How many words do we read per minute?*, J. Memory and Language. https://doi.org/10.1016/j.jml.2019.104047 **[A]**
61. The Learning Agency — *How Speech Recognition Systems Struggle with Children's Voices*. https://the-learning-agency.com/the-cutting-ed/article/how-speech-recognition-systems-struggle-with-childrens-voices/ **[C]**

**Generative AI and children**

62. FTC — *FTC Launches Inquiry into AI Chatbots Acting as Companions* (Sept 2025). https://www.ftc.gov/news-events/news/press-releases/2025/09/ftc-launches-inquiry-ai-chatbots-acting-companions **[A]**
63. Davis+Gilbert — *FTC Probes AI Companion Chatbots for Risks to Minors*. https://www.dglaw.com/ftc-probes-ai-companion-chatbots-for-risks-to-minors/ **[B]**
64. Common Sense Media — *AI Companions Decoded* (30 April 2025). https://www.commonsensemedia.org/press-releases/ai-companions-decoded-common-sense-media-recommends-ai-companion-safety-standards **[B]**
65. Common Sense Media — *Major AI Chatbots Unsafe for Teen Mental Health Support* (Nov 2025). https://www.commonsensemedia.org/press-releases/common-sense-media-finds-major-ai-chatbots-unsafe-for-teen-mental-health-support **[B]**
66. Common Sense Media — AI Risk Assessments index. https://institute.commonsensemedia.org/risk-assessments **[B]**
67. U.S. PIRG Education Fund — *The risks of AI toys for kids* (11 Dec 2025, upd. 7 Jan 2026). https://pirg.org/edfund/resources/ai-toys/ **[B]**
68. U.S. PIRG Education Fund — *Trouble in Toyland 2025* (13 Nov 2025). https://pirg.org/edfund/media-center/report-age-inappropriate-ai-ending-up-in-toys/ **[B]**
69. U.S. PIRG — *Report update: AI chatbot toys come with new risks*. https://pirg.org/edfund/media-center/report-update-ai-chatbot-toys-come-with-new-risks/ **[B]**
70. US Senate (Gillibrand et al.) — letter to the FTC on AI toys, 12 March 2026. https://www.gillibrand.senate.gov/wp-content/uploads/2026/03/260312aitoyslettertoftc1.pdf **[C]** (not retrieved in full)
71. Khan Academy — *How Khan Academy Is Building a Better AI Tutor*. https://blog.khanacademy.org/how-khan-academy-is-building-a-better-ai-tutor-our-most-recent-learnings/ **[C]**
72. CBC — *An AI toy meant for kids was happy to chat about sexual fetishes*. https://www.cbc.ca/radio/thecurrent/ai-toys-for-kids-safety-9.7001764 **[C]**
