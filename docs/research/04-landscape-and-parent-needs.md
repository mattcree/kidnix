# 04 — The Landscape and What Parents Actually Need

Research note for **kidnix**: an immutable Linux OS for children aged 4–8 (centred on 5–6), UK family context.

**Compiled:** 22 August 2026. **Author:** research worker (Claude). **Status:** primary-source research pass; confidence flags inline.

---

## 1. Scope and method

Two questions are answered here.

**Part A — Landscape.** What already exists for children's computing: platform parental-control ecosystems, kid-first hardware, screen-free audio devices, kid phones, school device stacks, the graveyard of children's Linux distributions, and the "slow tech" movement. For each: the business model, the child's experience, the parent's controls, pricing and lock-in, privacy posture, and well-documented complaints.

**Part B — Parent needs.** What parents actually do, say and buy, from primary survey data: Ofcom's UK tracker (2025 and 2026 editions), the Common Sense Census 0–8 (2025), Pew (October 2025), FOSI (Spring 2025), Internet Matters Pulse (2025), the UK Education Committee (2024), and the academic literature on parental-control abandonment.

**Method.** Roughly 60 distinct sources were read, weighted toward primary documents. Where possible I pulled the actual PDFs and extracted text rather than relying on press summaries — the Ofcom 2026 report (7.9 MB), the Ofcom 2025 report, the full Common Sense Census, and the FOSI survey were all read in full text. Vendor documentation was read directly. Reputable journalism, DistroWatch release records and Semantic Scholar metadata fill the gaps.

**Limitations and assumptions, stated up front.**

- The session's web-search budget was exhausted partway through; the second half of the work was direct URL fetching. Several sites (Internet Matters, eSafety Australia, Taylor & Francis, The Verge for some fetch paths, Reddit, PIRG, CDT, amazon.co.uk) block automated retrieval. Figures sourced only from search abstracts rather than full text are flagged.
- Several 2026-dated events (the UK under-16 ban, Amazon's UK Kids+ repricing, Google's climb-down on 13-year-old supervision) come from recent trade and news reporting rather than from statute or company filings. They are marked **[verify before quoting externally]**.
- US and UK data are mixed. Where a number is US-only (Common Sense, Pew, FOSI) it is labelled. UK numbers (Ofcom, Internet Matters, DfE) should carry more weight for kidnix's target market.
- "Screen time" figures across sources are not comparable — different instruments, ages, and definitions. Trends within a single source are meaningful; cross-source comparisons are not.

---

## 2. The landscape

### 2.1 Comparison table

| Product / platform | Model | Kid UX | Parent controls | Price / lock-in | Privacy | Headline complaint |
|---|---|---|---|---|---|---|
| **Amazon Fire Kids + Kids+** | Cheap hardware as funnel for content subscription | Full-screen Amazon Kids launcher, per-child profiles, curated carousels | Parent Dashboard (web + app): daily/weekly time caps by activity type, **Learn First**, age slider, app approval, web modes | Hardware ~$70–$220; Kids+ $4.99–$7.99/mo US; **UK annual Prime plan raised £38 → £59.99 (5 Aug 2026)** [verify]. Total content lock-in | COPPA-covered inside Kids+; **$25m DOJ/FTC Alexa penalty, May 2023** for indefinite retention of children's voice + location data | Ads/upsell, slow hardware, blocklist-not-allowlist, kids reaching the browser |
| **Apple Screen Time / Child Accounts** | Free feature bundled with premium hardware | Normal iOS/macOS; **Guided Access** = single-app kiosk; **Assistive Access** = radically simplified shell | Downtime, App Limits, Communication Limits/Safety, Content & Privacy Restrictions, Ask to Buy, Ask to Browse | Free; hardware-priced. Lock-in is the device | Strongest on paper: on-device nudity detection, **age bands not birth dates** (Declared Age Range API, iOS 26) | **The most-criticised control system in tech**: URL-bar bypass unfixed for 3 years, Downtime silently resetting, post-reboot enforcement gap, passcode reverting |
| **Google Family Link / Kids Space** | Free, account-centric; ecosystem is the product | Kids Space launcher (Home/Play/Read/Watch/Make) on OEM tablets; otherwise standard Android | Daily + per-app limits, Downtime, School Time, install approval, Chrome/Play/YouTube/Search filters, location | Free. Lock-in = Google account | **$170m YouTube COPPA settlement, 4 Sep 2019** ($136m FTC + $34m NY AG) | Enormous documented bypass surface (WebViews, Secure Folder, cloned apps, ADB); the **age-13 cliff** and Google emailing 12-year-olds about it |
| **Microsoft Family Safety** | Free, Microsoft-365-adjacent | Standard Windows child account | Screen time (Windows/Xbox/Android), app + game age filters, web filter, activity reports, spending | Free | No comparable enforcement action | **Web filtering only works in Edge**; other browsers are blocked from launching. **Edge Kids Mode killed in Edge 117, 15 Sep 2023** with a one-line notice |
| **Nintendo Switch / Switch 2** | Free, **enforced in console firmware** | Games only; no general-purpose OS underneath | Standalone phone app: per-weekday play limits (max 6h), bedtime, **soft vs hard stop**, +5/15/30/60 min grants, per-user play reports; **GameChat per-friend and per-room camera approval** (Switch 2) | Free; console lock-in | Parents see **metadata not content** ("You will not have access to the conversations") | **Restriction level is per-console, not per-user** — the 11-year-old's ceiling applies to the 5-year-old |
| **LeapFrog / VTech** | Proprietary hardware + cartridges + store | Bespoke kid UI, later a skinned Android tablet (Epic, 2015) | Basic; parent-managed content | LeapPad ~£100 + ~£20 cartridges. Total lock-in | **VTech breach Nov 2015: 4.9m parent accounts, 6.4m children's profiles, photos, chat logs, voice recordings, 190 GB unencrypted.** FTC fine $650,000 (Jan 2018) | Killed by cheap general tablets; FY2014 **net loss $124m on sales of $145m**; sold to VTech for **$72m (Apr 2016)** |
| **Osmo** | Physical manipulatives + tablet camera reflector | Screen as *referee for physical play* — hands on wooden tiles | Minimal | Starter kits from $79, add-ons $29; **no UK storefront** | Not a notable issue | Hostage to Byju's collapse ($22bn valuation → founder saying it is "worth zero", Oct 2024) |
| **Yoto Player / Mini** | Screen-free audio player; **cards are the razor blades** | Insert card, chunky buttons, twist dial. **No reading, no account, no parent needed** | Parent app for setup, purchases, daily limits, night light | Player £89.99 / Mini £59.99; cards ~£10–15 each. FY2024 revenue **£94.8m, +86%**, EBITDA-positive 3 years | No child-side account; offline after download | Content cost is the real price; app + Wi-Fi still required for the parent; Yoto Club redemption changes upset users |
| **Toniebox / tonies** | Same, with figurines | Place figurine on box; ears are volume | mytonies app | Box £104.99, figurine £14.99. **FY2025 revenue €630.3m (+31%), 11.8m boxes, 156m figurines, >1m UK installed base**; figurines = 71% of revenue | Similar | Proprietary figurines; e-waste; unilateral feature moves into the app |
| **Pinwheel / Bark / Gabb / Troomi** | Locked-down Android + subscription | Curated app list (Pinwheel: 1,000+ vetted apps), contact safelist | Extensive; **Bark scans every message** | Bark $39–$104/mo all-in; Gabb $12.99–$17.99/mo; Gabb Watch 3e $149 | **Bark is a surveillance product by design** | Cost; for under-9s the industry has converged on a *watch* or, in 2026, **Pinwheel Home — a landline** |
| **Light Phone III** | Deliberately incapable premium phone (LightOS, Android-based) | Calls, texts, tools. No app store, no feed | n/a (adult product) | **$599 preorder / $799 retail** (27 Mar 2025) | Minimal by design | Proof that **constraint is now a premium good** |
| **School Chromebook stack** (Google for Education + GoGuardian/Securly/Gaggle/Smoothwall) | Institutional management + monitoring | Managed Chrome | Total admin control; teacher live screen viewing | Institutional | **GoGuardian monitors ~27m students**; EFF's Red Flag Machine found mass false positives on college, LGBTQ and health sites | **89% of teachers say their district monitors; 78% say it's used for discipline vs 54% for connecting students to help; ~50% of students self-censor** |
| **OLPC XO + Sugar** | Non-profit, constructionist, $100 laptop | **Journal instead of files, Activities instead of apps**, full-screen, no windows, no double-click | None (by design) | XO-1 shipped at ~$180, never $100 | Excellent | Collapsed on logistics, teacher training, repair and politics. **2012 Peru RCT found no maths or language gains.** ~3m units total |
| **Kano OS** | Raspberry Pi kit + custom OS + Kano World | Assemble-it-yourself, Make Art / Kano Code | n/a | Kit ~£250 | n/a | Raised >$30m across Kickstarter, Breyer, HSBC, Microsoft; **entered administration June 2023**; Kano World wound up 2025 |
| **Endless OS** | Immutable OSTree Debian derivative + Flatpak, offline-first, for emerging markets | GNOME, phone-like, preloaded encyclopaedia and educational content | GNOME parental controls | Free; hardware from $79 | Good | Technically the **closest existing thing to kidnix**; the kid-specific **Hack** product is gone (hack-computer.com now redirects to endlessglobal.com) |
| **Qimo 4 Kids** | Ubuntu remix for 3+ | Big icons, GCompris et al | None | Free | n/a | **Discontinued. Last release 2.0, 27 May 2010** |
| **DoudouLinux** | Debian remix for young children | LXDE, ~50 educational apps | None | Free | n/a | **Discontinued. Last release 2.1, 6 Dec 2013** |
| **Sugar on a Stick** | Live USB Sugar | Sugar shell | None | Free | n/a | Stuck on **Sugar 0.118 / Fedora 35** (2021). Sugar Labs: 100+ volunteers, **zero paid staff** |
| **Edubuntu** | Official Ubuntu flavour, killed 2014, **revived 2023** | GNOME + education metapackages | GNOME parental controls | Free | Good | **Alive: Edubuntu 26.04 LTS.** But it is a package set, not a child UX |
| **Escuelas Linux** | Bodhi/Moksha-based, Mexican, preschool→high school | Moksha desktop + education suite | Minimal | Free | Good | **Alive: 9.0, 20 May 2026.** Teacher-facing, not 4–8-facing |
| **GNOME Parental Controls (malcontent)** | The Linux desktop's only built-in answer; written and funded by **Endless** | n/a | App allow/block, OARS age-rating ceiling, block installation, restrict browsers — and **as of GNOME 50 (18 Mar 2026): screen-time limits, bedtime schedules, per-child usage charts, and a web-filter backend** | Free | Good | Its own README: *"a sufficiently technically advanced user may always work around these parental controls… not a mandatory access control system"*. Flatpak-only app filtering; web-filter **UI** not yet shipped; **no per-app time limits**; **KDE and Cinnamon implement none of it** |
| **Kid launcher apps** (Kids Place, Samsung Kids, Kids Mode) | Userspace launcher over an adult OS | Whitelist behind a PIN | PIN-gated app list, timers | Free–£3/mo | Weak | **CVE-2023-28153: Kids Place (5m installs) — "parental control bypass", the child could remove restrictions without notifying the parent** |

### 2.2 Per-product notes that matter

**Amazon Fire Kids.** The one genuinely original feature in the whole market is **Learn First**: the parent sets a daily educational goal (e.g. 30 minutes reading) and entertainment stays locked until it is met. Also worth noting: the device, not the parent, delivers the "time's up" screen — Amazon's own marketing sells this as the tablet taking the blame. Both ideas are directly transferable. The rest is a subscription trap: content is licensed and evaporates on cancellation, the store is blocklist-based so new content is available by default, and reported UK annual pricing jumped ~58% in a single step in August 2026 [verify].
Sources: [aboutamazon.com Fire Kids buying guide](https://www.aboutamazon.com/news/devices/fire-kids-tablet-buying-guide-find-out-which-device-is-right-for-you), [TechCrunch on Kids+ repricing (2022)](https://techcrunch.com/2022/06/08/amazon-is-simplifying-the-pricing-structure-for-its-kids-all-in-one-subscription-service/), [DOJ press release on the $25m Alexa penalty](https://www.justice.gov/archives/opa/pr/amazon-agrees-injunctive-relief-and-25-million-civil-penalty-alleged-violations-childrens).

**Apple.** Two features deserve study and one deserves fear. **Guided Access** is a real single-app kiosk mode. **Assistive Access** (iOS 17, 2023) is the best mainstream example anywhere of a radically reduced OS shell — huge icons, high contrast, a cut-down app set, grid or row layout — and is the closest prior art to a kidnix activity shell. What deserves fear is Screen Time's reliability record: a Safari URL-bar bypass that security researchers reported three years before the WSJ forced a fix; Downtime settings silently resetting; a 30–60 second window after reboot in which restrictions are simply not active; the Screen Time passcode reverting to a previous value. The iOS 26 (June 2025) wave — child-appropriate defaults applied even on abandoned setup, correctable birth dates, the **Declared Age Range** API giving apps an age *band* rather than a birth date, and App Store ratings expanding from three tiers to five (4+/9+/13+/16+/18+) — is a genuine improvement and is broadly read as pre-empting US state app-store age-verification laws.
Sources: [Apple Newsroom, 11 June 2025](https://www.apple.com/newsroom/2025/06/apple-expands-tools-to-help-parents-protect-kids-and-teens-online/), [Macworld on Screen Time flaws](https://www.macworld.com/article/2359164/ios-screen-time-flaws-loopholes-update.html), [Michael Tsai's Sept 2025 round-up](https://mjtsai.com/blog/2025/09/24/screen-time-brokenness/).

**Google.** Family Link is feature-rich and structurally leaky. Bitdefender's catalogue of bypasses is the single most useful document for anyone designing enforcement: ADB tooling, hidden WebViews reached through "Help" or "Terms of Service" links inside Google Play Services, app cloning on OEM skins, Samsung Secure Folder and Android Private Space (encrypted areas Family Link cannot see into), DeX mode ignoring limits, the emergency dialer re-exposing the home screen, the accessibility menu re-activating restricted apps, clock manipulation, clearing Play Store data to wipe settings. Their diagnosis is the important sentence: *"many controls are enforced locally on the device rather than remotely,"* and OEM additions create holes Google never designed for. Separately, Google emailed children approaching their 13th birthday previewing the tools they would unlock — effectively inviting them to switch supervision off — which drew an FTC complaint in October 2025 and a subsequent climb-down requiring explicit parental permission [verify].
Sources: [families.google/familylink](https://families.google/familylink/), [Bitdefender: Family Link bypasses](https://www.bitdefender.com/en-us/blog/hotforsecurity/family-link-bypass-android-2025), [Al Jazeera, 14 Jan 2026](https://www.aljazeera.com/economy/2026/1/14/child-rights-org-says-google-undermines-parental-control-of-child-accounts), [YouTube COPPA settlement](https://blog.youtube/news-and-events/an-update-on-kids/).

**Nintendo — why it is the one people praise.** Four reasons, all architectural rather than cosmetic. (1) Enforcement lives in console firmware; there is no general-purpose OS underneath to attack, so the entire bypass catalogue above simply does not apply. (2) The controls live in a **standalone app**, not buried six levels into system settings. (3) The app is oriented toward **reporting** — what was played, by whom, for how long, with monthly summaries — rather than pure restriction; Kotaku's framing was that it "just gives you visibility... without interrupting their game." (4) It offers **soft stop or hard stop** as an explicit choice, plus one-tap grants of +5/+15/+30/+60 minutes, which respects the reality that a bounded session sometimes needs 90 more seconds. Switch 2's GameChat goes further: per-friend approval, per-room camera consent, a parent-chosen video scope (face only / person only / full), and an explicit statement that parents get session metadata, not conversation content. Its one serious flaw — content restriction is set **per console, not per user** — is precisely the flaw a multi-child household hits first.
Sources: [Nintendo Parental Controls app](https://www.nintendo.com/us/mobile-apps/parental-controls/), [Nintendo support: Switch 2 GameChat controls](https://en-americas-support.nintendo.com/app/answers/detail/a_id/68384), [Kotaku (2018)](https://kotaku.com/the-nintendo-switchs-parental-controls-are-amazing-1824301547).

**Yoto and Toniebox — the most important comparables in this document.** Ignore the fact that they are audio devices; the transferable thing is the *interaction contract*. A physical token maps to exactly one piece of content. There is no feed, no autoplay, no "up next", no recommendation, no account, no reading requirement — and crucially **no parent required in the moment**. The choice space is bounded by what is physically on the shelf, which is a boundary a five-year-old can see and reason about. This is a large business: tonies SE reported **FY2025 group revenue of €630.3m, up 31%**, with **11.8 million Tonieboxes and 156 million figurines sold cumulatively**, a **UK installed base past one million**, and Rest-of-World (UK-led) growing 64%; Yoto reported **FY2024 revenue of £94.8m, up 86%**, EBITDA-positive for three consecutive years. Note the economics: **figurines are 71% of tonies' revenue** and hardware only 26%, roughly 13 figurines per box. Note also the criticisms, which are the same ones kidnix must avoid — content cost is the real price, the parent still needs a smartphone app and Wi-Fi so "screen-free" applies only to the child, and unilateral changes to subscription redemption rules upset the installed base. And note the escape valve: **Yoto's Make Your Own cards and tonies' Creative-Tonies** let a family load its own audio — a grandparent reading a story, a holiday diary, a child's own recording. That single feature converts a vending machine into a family medium, defuses the lock-in critique, and means the hardware survives the vendor. For an open platform this should be the *default*, not an add-on.
Sources: [tonies FY2025 results](https://www.mynewsdesk.com/us/tonies/pressreleases/tonies-continues-profitable-growth-with-record-results-in-2025-expects-strong-momentum-for-full-year-2026-expansion-of-ecosystem-around-toniebox-2-proves-a-global-success-3442746), [tonies UK store](https://tonies.com/en-gb/), [Yoto UK](https://uk.yotoplay.com/yoto-player), [Music Ally on Yoto's 2024 growth](https://musically.com/2025/08/27/childrens-speakers-startup-yoto-saw-sales-grow-by-86-in-2024/), [Wikipedia: tonies](https://en.wikipedia.org/wiki/Tonies_(company)).

**Kid phones and the convergent form factor.** Bark, Gabb, Pinwheel and Troomi all sell locked-down Android with contact allowlists and curated app stores; Bark additionally scans every message a child sends and flags bullying and self-harm content. For 4–8s, though, the striking 2026 datapoint is that **Pinwheel — an Android phone company — spent the year launching Pinwheel Home, a landline**, explicitly marketed as "the ideal voice phone for kids age 5–10". Meanwhile Gabb's under-12 product is a *watch*, not a phone. Nobody serious is selling a pocket general-purpose computer to a six-year-old. And the Light Phone III at **$599–$799** (launched 27 March 2025) demonstrates that constraint sells at the top of the market, not the bottom.
Sources: [bark.us](https://www.bark.us/bark-phone/), [gabb.com](https://gabb.com/), [pinwheel.com](https://www.pinwheel.com/), [Wikipedia: Light Phone](https://en.wikipedia.org/wiki/Light_Phone).

**School stacks — the cautionary tale about management-as-safety.** GoGuardian alone monitors roughly **27 million students across 10,000 schools**. EFF's *Red Flag Machine* project analysed the sites GoGuardian classified as explicit and concluded it is "a red flag machine — its false positives heavily outweigh its ability to accurately determine whether the content of a site is harmful", with tens of thousands of students flagged for visiting **university application sites, LGBTQ information, sexual health resources, drug-abuse education, medical sites and news outlets**. The Center for Democracy & Technology's survey (1,606 parents, 1,008 teachers, spring 2022) found **89% of teachers say their district uses monitoring software**, **78% say it has been used for disciplinary purposes** against **54%** who say it connected a student to a counsellor, **13% of students report LGBTQ+ peers being outed without consent**, and **about half of students say they do not share their true thoughts because they know they may be monitored**. Separately, PIRG's *Chromebook Churn* (April 2023) documented pandemic-era Chromebooks bricked by Auto Update Expiration regardless of physical condition; public pressure forced Google to extend ChromeOS updates to **10 years** in September 2023 — a genuine precedent that vendor support windows are negotiable.
Sources: [EFF: How GoGuardian invades student privacy](https://www.eff.org/deeplinks/2023/10/how-goguardian-invades-student-privacy), [redflagmachine.com](https://redflagmachine.com/), [Education Week on the CDT survey](https://www.edweek.org/technology/software-that-monitors-students-may-hurt-some-its-meant-to-help/2022/08), [EFF: Spying on Students](https://www.eff.org/wp/school-issued-devices-and-student-privacy).

**The Linux end of the market — and a window that just opened.** Until 2026 the honest answer was that Linux had no session model. GNOME's Parental Controls (malcontent), written and maintained by Endless, offered only an app allow/block list, an OARS content-rating ceiling and an installation block, with its documentation stating the limits plainly — *"Parental Controls requires applications to be installed via Flatpak or Flathub"* and *"Existing applications (which are not installed via Flatpak) will not appear in this list."* No time limits, no schedules, no reporting.

**That changed in March 2026.** Philip Withnall's backend work landed in November 2025 — a stateless `malcontent-timerd` daemon ingesting usage from gnome-shell, reading parent-set daily allowances from accounts-service and computing an estimated session end with advance warnings — and **GNOME 50 "Tokyo" (18 March 2026)** shipped it. The release notes: *"GNOME's parental controls have made a massive leap forward in GNOME 50. For the first time it is now possible for parents and guardians to monitor screen time and set limits for child accounts, including bedtime schedules."* A web-filtering **backend** also landed, explicitly designed to work without breaking web security and without depending on curated blocklists; the UI is still to come. The work was sponsored by the Endless Foundation. GNOME 50 is the default desktop for **Ubuntu 26.04 LTS and Fedora 44**. Still missing: per-app time limits, the web-filter UI, and any enforcement guarantee — malcontent's own README says *"a sufficiently technically advanced user may always work around these parental controls… [it] is not a mandatory access control system like AppArmor or SELinux."* **KDE Plasma has no parental controls at all** (there is an open Discuss thread requesting them), and **Linux Mint/Cinnamon ignores malcontent even when installed.** Note also for anyone tempted by cheap hardware: **ChromeOS Flex cannot be governed by Family Link** — supervised Flex devices expose only remote lock/unlock, not app restrictions or screen-time limits.

**Endless OS remains the closest technical relative to kidnix** — immutable OSTree root, Flatpak app delivery, modified GNOME, offline-first with preloaded content bundles, ~3 million installs across 60 countries, first release July 2014, 6.0 in May 2024. Its kid product **Hack** ($299 ASUS laptop, ages 8–14, announced 4 November 2018) is gone; hack-computer.com redirects to the parent foundation, and Endless's own retrospective says they *"sunset the Hack Computer project in order to redirect our focus towards disconnected communities, device access, and game-making learning."* Hack's **Flip-to-Hack** idea — every app carrying an affordance that flips it over to reveal and let you edit the code behind the thing you are playing — is the best unexploited idea in this entire survey.

**The most important single quote for kidnix's architecture** comes from Endless's January 2026 post on Endless OS 7, built with Codethink on BuildStream: Rob McQueen, *"About 95 percent of what we ship is GNOME OS. We focus our effort on the few things that really give value."* And: *"If your OS development cycle is measured in years, you're always behind."* The organisation with the most money, the best technology and a decade's head start in exactly this niche concluded that maintaining a heavily-customised desktop is what kills you.

**The survivors and the dead follow one rule.** Alive: **Edubuntu** (killed 2014, revived 2022–23, now **26.04 LTS, April 2026**, with software organised into Preschool / Primary / Secondary / Tertiary learning profiles and classroom controls including disabling terminal shortcuts for non-admin users — but still no parental controls); **Debian Edu / Skolelinux** (~75 school applications and 17 pre-configured network services, continuously released since 2001, **13.6.0 on 11 July 2026**); **Escuelas Linux** (**9.0, 20 May 2026**, notable for **RestoreUser/ReinstateUser** — resetting a wrecked child account to defaults with a button rather than with permissions); **GCompris** (197 activities for ages 2–10, **26.1 released 10 March 2026**). Dead: **Qimo 4 Kids** (last release 27 May 2010; maintainer Michael Hall closed it in January 2016 saying the team no longer had time "to keep pace with GNU/Linux"), **DoudouLinux** (last release 6 December 2013, despite an extraordinary 44-language localisation), **LinuxKidX**, **Ubermix**. **Sugar on a Stick** is frozen on Fedora 35 / Sugar 0.118; Sugar desktop's last stable release was **0.121, 6 February 2024**, and Sugar Labs' real activity has moved to the web version, Sugarizer, and to Music Blocks.

**The rule:** every survivor is a *thin, well-scoped layer over a giant upstream* — an official Ubuntu flavour, a Debian Pure Blend, a KDE application. Every corpse was a *separately maintained derivative*. Endless reached the same conclusion with a decade of funding behind it.

**And the field is empty.** There is no new children's Linux distribution in 2025–26. "Best Linux distros for kids (2026)" listicles still recommend Qimo (dead 2010), DoudouLinux (dead 2013), Kano OS (company liquidated 2023) and Ubermix (dormant since ~2015) as live options. No kid-oriented image exists in the atomic/immutable ecosystem — Universal Blue ships Bluefin, Aurora and Bazzite but no kids edition. Nobody has combined the atomic-image model with a child persona. The competitive flank is elsewhere: the 2025–26 money in the 4–10 band is going to **screen-free voice AI** (e.g. Wippi, $1.2m seed led by 12 Flags, for screen-free conversational AI products for children aged 4–10).

Sources: [GNOME Help: parental controls](https://help.gnome.org/users/gnome-help/stable/parental-controls.html.en), [GNOME 50 release notes](https://release.gnome.org/50/), [Withnall on the screen-time backend (Nov 2025)](https://tecnocode.co.uk/2025/11/19/parental-controls-screen-time-limits-backend/), [malcontent](https://github.com/endlessm/malcontent), [Endless OS](https://www.endlessglobal.com/foundation/access/operating-system), [Endless: "a conversation about what's changing"](https://access.endlessstudios.com/blog/endless-os-a-conversation-about-whats-changing-and-why-it-matters), [Endless: Hack Computer chronicles](https://access.endlessstudios.com/blog/hack-computer-chronicles), [Edubuntu 26.04 LTS](https://discourse.ubuntu.com/t/edubuntu-26-04-lts-released/80831), [DistroWatch: Debian Edu](https://distrowatch.com/table.php?distribution=debianedu), [DistroWatch: Escuelas Linux](https://distrowatch.com/table.php?distribution=escuelas), [DistroWatch: Qimo](https://distrowatch.com/table.php?distribution=qimo), [DistroWatch: DoudouLinux](https://distrowatch.com/table.php?distribution=doudou), [KDE parental-control request thread](https://discuss.kde.org/t/parental-control-application/957), [Family Link cannot restrict ChromeOS Flex](https://support.google.com/chromeosflex/thread/214605352/familylink-can-t-limit-apps-or-device-time-for-chromeos-flex-devices).

**UK regulatory context, 2026.** The Online Safety Act 2023 received royal assent on 26 October 2023; the July 2025 age-assurance deadline forced Bluesky, Discord, Reddit, X and others to age-gate. In 2026 the government announced a **social media ban for under-16s** (15 June 2026) and **curfews for 16- and 17-year-olds** (15 July 2026), and legislated a **statutory school phone ban in England** (announced April 2026, in force from around 30 June) [all verify]. Australia's equivalent under-16 ban took effect 10 December 2025 and by mid-2026 was being reported as failing, with the eSafety Commissioner describing the implementation as *"very thin scaffolding"*. The instructive part is the *shape* of the criticism aimed at bans — over-blocking, the privacy cost of mass age verification, exclusion of vulnerable children, and entrenching incumbents. **A device that achieves constraint locally, with no identity verification and nothing transmitted, sidesteps all four objections.** That is a real positioning advantage for kidnix in the UK right now.

---

## 3. Lessons from the dead

### OLPC and Sugar (2005–2014, technically still alive)

OLPC is the most instructive failure because it failed for reasons that had almost nothing to do with the quality of its software ideas.

**What went wrong.** The $100 price was announced before a manufacturer was signed; the machine shipped at ~$180. The hand crank — the emblem of the whole project — was dropped almost immediately because winding stressed the case and demanded energy poor children could not spare. Deployments failed on teacher training, maintenance, repair parts, mains power and content localisation, not on the interface. Peru bought nearly a million units into schools with spotty electricity and minimal teacher support; a controlled study in 2012 found **no improvement in maths or language skills**. Total lifetime shipments were roughly **3 million** against an original ambition of hundreds of millions. Walter Bender's own retrospective is the sharpest line in the whole literature: *"we set an expectation around price, rather than an expectation around what this machine was really for."* Morgan Ames's diagnosis — *"The utopianism set unrealistic expectations around what the laptops should be able to accomplish"* — is the second sharpest.

More evidence accumulated later and it is uniformly negative. A home-use RCT in Lima (~1,000 XOs) found **+0.8 SD on XO-specific proficiency and zero effect on academic achievement or Raven's** (*AEJ: Applied* 7(2), 2015). A long-run follow-up across 531 rural schools over 2009–2019 (*Journal of Public Economics*, 2025) **ruled out effects above 0.05 SD in maths and 0.03 SD in reading**, and found grade progression **1.0pp worse** (p<0.05). Morgan Ames's ethnography *The Charisma Machine* (MIT Press, 2019), based on seven months of fieldwork in Paraguay, found that **over half the children who received an XO simply were not interested in using it**, that roughly 15% had broken machines, and that those who did use them mostly **"surf the Internet, watch movies, listen to music, and play simple games"** and **"more often played video games than programmed them."** Her central thesis is the one to internalise: the XO was designed for the **"technically precocious boy"** — an idealised younger version of its developers — rather than for the children who actually received it.

**What was right, and matters directly to kidnix.** Sugar's design principles are still the best-articulated in children's computing: no desktop, no folders, no windows; activities run full-screen; double-clicking is not used; menus show icons; *"limit the controls to those immediately relevant to the task at hand."* The **zoom metaphor** — Neighbourhood → Group → Home → Activity — gave a child four coherent scales of "where am I" with no window management at all. The **Journal** is precisely the model kidnix proposes, and the original design documents are better than their reputation. Entries are created **implicitly** (every activity launch, photo, message) or explicitly; auto-metadata records time, sharing scope, participants, size, view count and revision count; "Keep" snapshots *state*, so resuming restores what you were doing rather than opening a file. Implicit versioning makes the Journal double as a **portfolio**. The HIG's rationale is worth quoting: *"the traditional 'open' and 'save' model commonly used for files today will fade away"* — a child drawing on paper never "saves". Bender's description of the whole system is worth keeping on the wall: *"It was very tool-oriented: tools for doing things, for making things. It wasn't curriculum-oriented. It wasn't a bunch of exercises."*

**Where the Journal actually broke.** The design anticipated its own failure modes and the mitigations never arrived. Clutter was to be solved by **"temporal falloff"** (age × view count × recency) suggesting deletions; data loss was to be solved by **school backup servers**. In deployments neither reliably existed, so on a 1 GB flash device the Journal degraded into an undifferentiated infinite reverse-chronological scroll. Retrieval depended on **child-authored tags** (a five-year-old will not write them) and **OR-logic text search** (on a device where the child has no keyboard fluency). And the most-repeated community complaint was the absence of a conventional alternative: *"it would have helped if Sugar 1.5 had incorporated some standard features, such as a file management system alongside the 'journal' approach."*

**The adults were the real failure.** A 2012 field study (Paz & Gibson, interviews in the US and Uruguay) identified three root causes and none of them concerned children: no administrative sponsorship, no usable training, and adults unable to self-teach an unfamiliar paradigm. A Birmingham, Alabama teacher reported that *"the failure to properly train teachers how to use the Sugar operating system created an environment of animosity toward the laptops"*, that *"students who had been exposed to Windows struggled to learn the XO laptop and the Sugar system, and the teachers did not have the knowledge to teach them"*, and — most damning — that *"even teachers who are comfortable with computers find Sugar difficult and counter-intuitive compared to their everyday Windows."* Negroponte himself later called building Sugar as a custom OS rather than a layer over a standard Linux desktop **"one of the biggest mistakes OLPC made."**

**The honest caveat.** There is still no rigorous published usability evaluation of the Journal specifically with children — whether they understood it, whether it stayed navigable after a year, whether the lack of hierarchy hurt. **The single most-copied idea in kid computing has never been properly evaluated in public.** kidnix should plan its own usability testing rather than assume Sugar validated it.

**Uruguay's Ceibal** is the one durable OLPC descendant and is a lesson in its own right: launched by decree in April 2007 with ~420,000–450,000 XOs, it has since migrated to conventional Windows 10/11 laptops (240,000+ managed via Intune/Autopilot) and Android tablets for pre-schoolers. Sugar is gone from it.

Sources: [The Verge, "OLPC's $100 laptop was going to change the world — then it all went wrong" (16 Apr 2018)](https://www.theverge.com/2018/4/16/17233946/olpcs-100-laptop-education-where-are-they-now), [Sugar HIG: The Journal](https://wiki.sugarlabs.org/go/Human_Interface_Guidelines/The_Laptop_Experience/The_Journal), [Sugar HIG: Zoom metaphor](https://wiki.sugarlabs.org/go/Human_Interface_Guidelines/The_Laptop_Experience/Zoom_Metaphor), [Paz & Gibson, *The XO Laptop and Usability Issues* (2012)](https://wiki.sugarlabs.org/images/5/56/Teacher_Needs_&_Sugar-Usability_Report.pdf), [Ames, *The Charisma Machine* (MIT Press, 2019)](https://mitpress.mit.edu/9780262537445/the-charisma-machine/), [IDB Peru evaluation](https://publications.iadb.org/publications/english/document/Technology-and-Child-Development-Evidence-from-the-One-Laptop-per-Child-Program.pdf), [long-run follow-up, *J. Public Economics* 2025](https://www.sciencedirect.com/science/article/abs/pii/S0047272725002373), [Negroponte on Sugar being a mistake](https://liliputing.com/negroponte-sugar-os-was-olpcs-biggest-mistake/), [Wikipedia: Ceibal](https://en.wikipedia.org/wiki/Ceibal_project).

### Kano (2013–2023)

Kano raised **$1.5m on Kickstarter (Nov 2013)**, **$15m Series A (May 2015, Breyer Capital)**, a second Kickstarter of **$643,030 (2016)**, **£14m from HSBC (Apr 2019)** and **£800k from Microsoft (Jul 2020)** — over $30m all-in for a company selling a Raspberry Pi in a nice box with a good story. It pivoted from Kano OS (its own Raspberry Pi–based system) to the **Kano PC running Windows 10** in 2019, which is the tell: the custom OS was abandoned in favour of being a hardware skin on someone else's platform. It then pivoted again into licensed novelty (Harry Potter wand, Star Wars/Frozen sensors) and finally into a Kanye West music player. It **entered administration in June 2023**; assets went to Ashdust LLP, connected to the CEO; Kano World was spun out and wound up in 2025.

The reviews are worth reading together. PCWorld: *"The Kano Computer Kit Complete aims to teach kids about PC hardware and coding in a fun and engaging way, and it knocks it out of the park"* — the reviewer's daughter *"absolutely adores it."* Digital Trends, on the same product: at $250 *"you are essentially paying for the 10.1-inch screen"* since Kano OS is free and a Pi 3 is $35, and *"we were surprised there was no direction of how to start using the device"* once assembly finished. **The build was the product, and Day 2 was empty.** That onboarding cliff — a spectacular first-run experience followed by nothing — is the retention failure kidnix will face in the same shape.

**The lesson that matters most: the cloud dependency bricked the toys.** After liquidation, buyers found that *"all the servers are offline. Meaning you can't create an account or login, making the device effectively useless."* Retail stock was still on shelves and being sold to families as functional product that could not complete first-run setup. Children's saved creations on Kano World went dark with the company. Kano's only successor is Kano itself: a February 2025 announcement of a revival with AstroSafe and FINH, promising "much-needed maintenance" and a subscription model. It has not visibly relaunched.

**Lesson.** A children's computing product that depends on a venture-funded company's survival — and worse, on its servers being up — is a bet the family cannot hedge. Kano's OS was the interesting part and it was the first thing abandoned when growth pressure arrived.
Sources: [Wikipedia: Kano Computing](https://en.wikipedia.org/wiki/Kano_Computing), [Companies House insolvency record, company 08375450](https://find-and-update.company-information.service.gov.uk/company/08375450/insolvency), [PCWorld review](https://www.pcworld.com/article/407848/kano-computer-kit-complete-review.html), [Digital Trends review](https://www.digitaltrends.com/computing/kano-computer-kit-complete-review/), [Kano × AstroSafe (Feb 2025)](https://www.kano.me/blog/kano-x-astrosafe).

### The kid distros: Qimo, DoudouLinux, LinuxKidX

These died quietly, and the pattern is identical in each case: a single maintainer or tiny team assembled a package selection and a theme on top of a mainstream distribution, shipped a few releases, and stopped. Qimo's last release was **27 May 2010**; DoudouLinux's was **6 December 2013**; LinuxKidX is not even in DistroWatch's database any more.

Michael Hall's closing note on Qimo is the epitaph for the whole category: *"All good things must come to an end. I learned so much making Qimo, and have been honored to have been able to touch so many lives in the process."* The stated reason was simply that the team no longer had the time to keep pace with GNU/Linux; the last build was still on Ubuntu 12.04. DoudouLinux is the more painful case because it was *better*: activity-chooser modes rather than a desktop, DansGuardian filtering, DuckDuckGo by default, a usage-monitoring tool, and **44 languages** — an extraordinary achievement for a volunteer project, and precisely the load that sank it.

**Lesson.** A children's Linux distribution that is *a theme plus a package list* has no defensible reason to exist and no mechanism to survive its maintainer. The reason kidnix might be different is that its value is in the **shell, the session model, the journal and the parent controls** — software that must be written and maintained, not merely selected. That is a higher bar, but it is also the only bar worth clearing. The corollary is that **the maintenance burden must be designed down** from day one: immutable base, small surface area, no per-application patching.

### The survival rule: layer, don't fork

Set the survivors against the dead and one variable explains almost everything.

| Survived | Structural reason |
|---|---|
| **Edubuntu** (26.04 LTS, Apr 2026) | An **official Ubuntu flavour** — inherits Canonical's archive, builders, mirrors, LTS cadence and security updates. The maintainers own only the seed and the artwork |
| **Debian Edu / Skolelinux** (13.6.0, Jul 2026; continuous since 2001) | A **Debian Pure Blend** — metapackages and defaults *inside* Debian, not a fork |
| **Escuelas Linux** (9.0, May 2026) | Small team, Ubuntu base, narrow scope, one genuinely original idea (RestoreUser) |
| **GCompris** (26.1, Mar 2026) | A **KDE application**, not an OS |
| **Died** | |
| Qimo, DoudouLinux, LinuxKidX, Ubermix | Separately maintained derivatives with no upstream leverage |
| Sugar desktop / Sugar on a Stick | A custom desktop environment maintained by 100+ volunteers and **zero paid staff** |

Endless — the best-funded participant in this field — reached the same conclusion in January 2026 and said it out loud: **"About 95 percent of what we ship is GNOME OS. We focus our effort on the few things that really give value."** And: **"If your OS development cycle is measured in years, you're always behind."** Having already shed its hardware (2020), its commercial entity (2020) and its kids' laptop (2020), it finally shed its custom desktop.

### Endless Hack, and Edubuntu's death and resurrection

Endless built **Hack**, a genuinely thoughtful kids' computer ($299, ages 8–14, announced November 2018) organised around five pathways — Art, Games, Makers, the Operating System, and the Web — in which **the OS itself was an explicit learning subject rather than a substrate to be hidden**, and in which every app carried a **Flip-to-Hack** affordance revealing the code behind the running thing so a child could change the game from inside it, using real tools in a real Linux environment. It was well reviewed and it is gone. Edubuntu was killed as an official flavour in 2014 and revived in 2023. The two together make the point: **kid-focused software gets abandoned first when an organisation is under pressure, and the things that come back are the ones with the lowest maintenance cost.**

### Microsoft Edge Kids Mode

Worth recording as the cleanest case of big-tech abandonment: a shipped, marketed, kid-branded browsing mode removed in **Edge 117.0.2045.31 on 15 September 2023**, with the stated rationale of simplifying a menu, no migration path, and a support page that still says only "Kids Mode has been deprecated" with no date and no alternative. Users were still discovering the removal in forum posts in May 2025.

### The meta-lesson

Every dead project in this section died of one of five causes, and only one of them is technical:

1. **Dependence on a company** (Kano, LeapFrog, Osmo, Hack, Kids Mode).
2. **Dependence on a single maintainer** (Qimo, DoudouLinux, LinuxKidX, Ubermix, and Sugar on a Stick's stall on Fedora 35).
3. **Dependence on a server** (Kano's kits bricked at first-run when the servers went dark; Sugar's Journal design assumed school backup servers that mostly did not exist).
4. **Selling a price or a story rather than a capability** (OLPC's $100, Kano's "build your own computer").
5. **Solving the wrong layer** — a fork instead of a layer, a theme over a distro, or a launcher over an adult OS.

And one non-technical cause outranks all of them: **the adults could not use it.** OLPC's field research says so directly, Kano's Day 2 was empty, and 75% of US parents use no screen-time tool at all. Whatever kidnix ships, the parent must be able to set it up in minutes and understand it without learning a new paradigm.

---

## 4. What parents actually need: the numbers

### 4.1 Where children of this age actually are

**UK, Ofcom 2026** (published 21 May 2026; 5,008 interviews with parents of children aged 6 months–17, 3,426 with children aged 8–17):

- **88% of children aged 3–7 go online**; 99% of 8–17s; **65% of children aged 6 months–2 years**, and **85% of that youngest group ever look at a screen**.
- **The tablet is the most common online device for every age group below 13.** 77% of 8–9s use a tablet to go online. For 6-months-to-2s, the smart TV leads (40%), then tablets (36%).
- **65% of 3–7s use digital devices to make drawings or pictures or use colouring apps**; 20% make animations. Overall **80% of 3–17s do at least one creative activity** on a device.
- **37% of parents of 3–7s say their child plays games online.** 88% of 3–17s game on some device.
- **76% of all children listen to audio**, and **3–7s are the age group most likely to listen to audiobooks (32%)** — higher than any other band.
- **52% of parents of 3–7s who do creative activities say their child has used AI while doing them**; 16% say often.
- Reasons parents give for the youngest children's screen use: **entertainment 67%, supporting learning 63%, "because they enjoy it" 52%, and to occupy the child while the parent does other tasks 49%.**

**UK, Ofcom 2025** (published May 2025, fieldwork 2024): **37% of parents of 3–5s reported their child used at least one social media app**, up from 29% in 2023 — Instagram 16%, Snapchat 15%, Facebook 13%. Of those, 36% of parents use it *on the child's behalf*, 42% use it *together*, but **19% say the child uses it independently**.

**US, Common Sense Census 2025** (fielded 5–29 August 2024, n = 1,578 parents of children aged 0–8, MoE ±2.9%):

- Daily screen media: **2:27 overall**; under-2s 1:03; 2–4s 2:08; **5–8s 3:28**.
- **Income gap: <$50k households 3:48/day vs >$100k households 1:52/day.**
- **Tablet ownership: 40% by age 2, 58% by age 4, 62% by age 6, 68% by age 8.** 47% overall own a tablet; **51% of 0–8s own some mobile device**.
- **Gaming up 65% in four years**, 23 → 38 minutes/day; 5–8s now play **1:04/day**.
- **9% of 0–8s have their own phone; of those, 19% have a limited/no-app phone (Pinwheel, Gabb, Troomi, Bark).**
- **Daily reading among 5–8s fell from 64% (2017) and 63% (2020) to 52% (2024)** — while it *rose* for under-2s from 43% to 55%.
- 39% of 0–8s listen to music daily (33 min/day); 34% listen to audiobooks at least occasionally; **49% of households own a smart speaker; 11% of 0–8s have their own.**
- Only **23% of parents have ever had a paediatrician discuss their child's media use.**

**US, Pew** (published 8 October 2025; n = 3,054 parents of children aged ≤12, fielded 13–26 May 2025): 90% of children watch TV, **68% use a tablet**, 61% use a smartphone, 50% use gaming devices. Roughly **80% of 5–7s use tablets**; **12% of 5–7s own a smartphone**; **3% of 5–7s have used an AI chatbot**. **85% of children ≤12 watch YouTube; 51% daily; 74% of parents co-view.**

### 4.2 The central finding: parents own the tools and don't use them

This is the most important cluster of numbers in the document.

| Finding | Figure | Source |
|---|---|---|
| Parents of 0–8s who use **no tools or settings at all** to limit screen time | **75%** | Common Sense 2025 |
| Parents of 0–8s who do **not restrict content types** | **51%** | Common Sense 2025 |
| Parents of 5–8s who use software to limit screen time | **30%** (vs 4% of under-2 parents) | Common Sense 2025 |
| UK parents aware of at least one technical tool/control | **93%** | Ofcom 2025 |
| UK parents who **use** at least one | **76%** (83% of parents of 3–12s; 62% of 13–17s) | Ofcom 2025 |
| UK parents using **manufacturer built-in** parental controls | **37%** overall; **50% among parents of 6–7s** (up from 36% in 2023) | Ofcom 2025 |
| UK parents who say they **use parental controls** (2026 wording) | **35%** | Ofcom 2026 |
| UK parents who say they use **device management tools** incl. controls and screen-time limits | **77%** | Ofcom 2026 |
| Filter-aware UK parents who say they **"trust their child to be sensible"** instead | **43%** | Ofcom 2025 |
| Filter-aware UK parents who **prefer talking and setting rules** instead | **43%** | Ofcom 2025 |
| US parental-control adoption by device | **51% tablets → 35% game consoles**; >50% of parents use none on each device tested | FOSI Spring 2025 (n=1,000 parents + 1,000 children 10–17, Feb–Mar 2025) |
| Households using each control type who find it effective | **>4 in 5** — but **time limits rated significantly less useful** than other types | FOSI Spring 2025 |

Two things follow. First, **non-adoption is not an awareness problem** — 93% of UK parents know the tools exist. It is a friction, trust and effort problem. Second, **parents of 6–7s are the peak adopters** (50% using built-in controls, up 14 points in a year), which is exactly kidnix's window.

The academic literature explains the mechanism. Wisniewski et al. (CSCW 2017) analysed 75 Android parental-control apps and 42 safety features and found they "strongly favoured features that promote parental control through monitoring and restricting" over collaborative approaches. Ghosh et al. (CHI 2018), *Safety vs. Surveillance: What Children Have to Say about Mobile Apps for Parental Control*, is the canonical study of what children say about these tools. "Protection or Punishment?" (2021) analysed 58 Android apps and **3,264 app reviews**, identifying granularity, feedback/transparency and parent–child communication as the axes that determine whether a tool is perceived as protection or punishment. A 2025 arXiv position paper, *Moving Beyond Parental Control*, summarises the failure modes: teens circumvent, surveillance erodes trust, and abandonment follows. A 2023 rapid evidence review in the *Journal of Children and Media* concluded that outcomes are mixed, with both beneficial and adverse effects, and that **parents valued controls when embedded in broader mediation and a good parent–child relationship** rather than as a substitute for it.

For 4–8s specifically, the literature on teen circumvention is only partly relevant — but the *design* finding transfers exactly: tools that read as punishment get abandoned; tools that read as shared structure get kept.

### 4.3 What parents do instead: supervision, rules and conversation

- **93% of UK parents do some form of supervision** (Ofcom 2026). 78% use "ongoing supervision" (checking history, asking to be shown); **77% use device management tools**; only **46% do real-time supervision** (sitting with the child).
- **59% of parents of 3–5s sit beside their child while they are online** (Ofcom 2025), falling to 17% by age 10–12. Being nearby and regularly checking peaks at **75–76% among parents of 6–7s and 8–9s**.
- Asked which single approach they rely on, **59% of parents of 3–5s say "directly supervise"** — up from 46% the year before — against 19% "talk to" and only **7% "trust child to be sensible"** (Ofcom 2025).
- **91% of UK parents whose child games have rules about it**; most common are how much time (56%), when (51%) and appropriate content (50%) (Ofcom 2026).
- **71% of parents of 6–7s have rules about downloading apps**, up from 49% in 2023 (Ofcom 2025).
- **86% of US parents have screen rules — but only 19% stick to them all the time**; 55% "most of the time" (Pew 2025).
- **66% of UK parents talk to their child about online safety at least every few months**, but only **53% of parents of children under 5** do so monthly (Ofcom 2026).

### 4.4 What parents are afraid of — the 4 Cs

The standard framework (Livingstone & Stoilova, CO:RE, 2021) sorts risk into **Content** (child as recipient), **Contact** (child as target of an adult), **Conduct** (child as actor among peers) and **Contract/Commerce** (child as consumer). The survey data maps onto it cleanly, and the ordering is different for young children than for teens.

**Content — the top fear, and it peaks at exactly kidnix's age.**
- **69% of UK parents are concerned about their child seeing adult or sexual content; 44% "very" concerned. This peaks among parents of 6–7-year-olds at 77% concerned and 56% very concerned**, then declines with age (61%/24% among parents of 16–17s) (Ofcom 2026).
- **76% of US parents of 0–8s worry about sexual content; 75% about violent content** (Common Sense 2025).
- 66% of UK parents worry about the child not knowing what is real or fake (Ofcom 2026).

**Contact.**
- **64% of UK parents of gaming children are concerned about their child talking to strangers while gaming** — the top gaming concern — and 60% about being bullied by other players. Yet only **43% have rules about who their child can play with** (Ofcom 2026). That gap is a product opportunity.
- **64% of UK parents worry about online bullying; concern peaks among parents of 3–7s, 41% of whom are "very" concerned** — higher than parents of teenagers (23%) (Ofcom 2026).

**Conduct.** Less salient for 4–8s in the data; 15% of 3–7s reportedly upload videos (Ofcom 2026), which is itself alarming.

**Contract / commerce.**
- **73% of US parents of 0–8s worry about data collection by companies; 72% about advertising and materialism in screen media** (Common Sense 2025).
- 48% of UK parents of gamers have rules about purchasing or in-app purchases (Ofcom 2026).
- Children's ability to recognise advertising is poor: only **42% of 8–17s who use search engines knew the top four results were paid adverts** (Ofcom 2026). Under-8s are worse.

**Cross-cutting: time and balance.**
- **32% of UK parents agree they find it hard to control their child's screen time** — but only **35% of parents of children aged 6 months–2** think their child's screen time is too high, and **78% of parents of under-8s say their child has a good balance** (Ofcom 2026). The anxiety is real but not yet acute at this age.
- **80% of US parents of 0–8s worry about excessive screen time and 79% about its effect on attention spans** (Common Sense 2025).
- **42% of US parents think they could do a better job**, rising with child age — 25% (under 2), 40% (2–4), **43% (5–7)**, 47% (8–12) (Pew 2025).
- **86% of US parents call managing screen time a day-to-day priority, but only 42% one of their biggest priorities** — behind manners (77%), sleep (75%), physical activity (61%) and reading (54%) (Pew 2025). **This is a crucial calibration: screen management is important but not top-five. A product that demands much parental effort will lose.**
- **33% of US parents feel judged** about their screen decisions — 38% of mothers vs 27% of fathers; 40% of lower-income vs 30% of middle/upper-income parents (Pew 2025).
- **65% of US parents say they themselves spend too much time on their phones** (Pew 2025).

### 4.5 What parents are enthusiastic about

Parents are not anti-technology. **91% of UK parents whose child goes online say it helps in at least one way** (Ofcom 2026); for 3–7s the top-cited benefits are **creative skills (57%)** and **reading and numeracy (56%)**. **56% of parents say the benefits of gaming outweigh the risks; 66% say so for information-gathering** (against only 46% for social media). US parents echo this: **75% are excited about their child learning new things, 72% about positive messages, 72% about exploring new interests, 63% about creative use** (Common Sense 2025).

**The market kidnix is entering is not "parents who fear screens". It is parents who want the good version and cannot find it.**

### 4.6 Multi-child households, shared devices and the reality of family logistics

- **30% of UK parents of school-aged children say their child does not have continuous access to a suitable learning device at home**, rising to **39% among parents of primary-school children**. Of those, **61% say the child shares devices with other household members** (Ofcom 2025).
- In the US, **13% of families whose child uses a tablet or laptop say the device came from the school; among 5–8s that rises to 19%** (Common Sense 2025).
- **Nintendo's per-console (not per-user) restriction level** is the single most-cited structural complaint about the most-praised system in the market — a direct signal that multi-child support is under-served.

### 4.7 Screens as a parenting tool — the demand nobody designs for

- **66% of US parents use screen media at least sometimes to occupy their child while they get things done**; 57% to help the child learn something new; 56% to bond or relax together; **47% to reward good behaviour**; 44% to occupy the child in public; 25% to help a child calm down (Common Sense 2025).
- **17% of parents say their child sometimes or often uses a device to calm down when angry or upset**; **20% of 0–8s (26% of 5–8s) use a device to fall asleep most nights** (Common Sense 2025).
- **49% of UK parents of children under 3 say screens are used to occupy the child while the parent does other tasks** (Ofcom 2026).

The relevant CHI work here is Hiniker et al., *Screen Time Tantrums* (2016, 151 citations), on how families manage transitions off screens for toddlers and preschoolers — the ending is the hard part, not the starting.

### 4.8 Synthesised priority list of parent needs

Ordered by strength of supporting evidence and by relevance to a 4–8 product.

1. **Content safety that actually holds, without me configuring it.** — 77% of parents of 6–7s concerned about adult/sexual content (Ofcom 2026); 76%/75% US sexual/violent (Common Sense 2025); yet 75% of US parents use no tools (Common Sense 2025) and 93%-aware/76%-use in the UK (Ofcom 2025). *Implication: safe-by-default, allowlist-first, zero setup required.*
2. **A bounded session that ends without me being the villain.** — 32% find screen time hard to control (Ofcom 2026); 86% have rules but 19% keep them (Pew 2025); time limits rated the *least* useful control type (FOSI 2025). *Implication: the device ends the session, with a soft stop and a visible countdown, as Amazon and Nintendo both do.*
3. **Very low parental effort.** — Only 42% call screen management a top priority, behind manners, sleep, activity and reading (Pew 2025); 33% feel judged (Pew 2025). *Implication: setup must be minutes, defaults must be right, and there must be no ongoing admin.*
4. **Visibility, not surveillance.** — Nintendo is praised for reporting rather than restricting; 78% of teachers say school monitoring is used for discipline vs 54% for support and ~50% of students self-censor (CDT 2022). *Implication: a per-session summary of what was made and played, kept locally, with nothing transmitted.*
5. **Creative-first, not consumption-first.** — 65% of 3–7s draw/colour on devices (Ofcom 2026); parents of 3–7s cite creative skills (57%) as the top benefit (Ofcom 2026); 63% of US parents are excited about creative use (Common Sense 2025). *Implication: the shell's default state should be a making tool, not a library.*
6. **Multi-child and shared-device support.** — 39% of UK primary parents lack a dedicated device, 61% of those share (Ofcom 2025); Nintendo's per-console flaw. *Implication: per-child profiles with independent policy, fast switching, no re-login friction.*
7. **No commerce inside the child's world.** — 73% worry about data collection, 72% about advertising and materialism (Common Sense 2025). *Implication: no store, no IAP, no ads, no "ask to buy" — and say so loudly.*
8. **No contact surface by default.** — 64% of gaming parents fear strangers, but only 43% set who-can-play rules (Ofcom 2026). *Implication: no chat, no multiplayer, no friend lists at launch; if ever added, Nintendo's per-friend parental approval model.*
9. **Audio and stories as first-class content.** — 3–7s are the age group most likely to listen to audiobooks (32%, Ofcom 2026); tonies at €630m and Yoto at £94.8m prove the demand. *Implication: an audio/story mode that works with the screen off.*
10. **Family-added content — the escape valve.** — Yoto MYO and Creative-Tonies are the most-praised features in that category. *Implication: let a parent drop in their own audio, photos, and books; let the child's own creations become first-class objects.*
11. **A device that lasts, and that I can still use if the vendor disappears.** — LeapFrog, Kano, Osmo, Hack, Edge Kids Mode; Chromebook AUE forcing Google to 10 years of updates. *Implication: open formats, exportable journal, no server dependency for core function.*
12. **A path to real computer literacy.** — 56% of parents of 3–7s cite reading and numeracy as an online benefit (Ofcom 2026); the author's own brief. *Implication: real keyboard, real mouse, real file-ish concepts introduced gradually — the anti-tablet argument.*

---

## 5. Gap analysis: what nobody does well

**1. Nobody does allowlist-first for 4–8s.** Amazon blocklists (so new store content is available by default). Apple restricts by App Store rating. Google filters by category. Nintendo gates by age rating. What a five-year-old needs is a **small, finite, hand-curated set** — twelve activities, not twelve thousand. No mainstream product ships that.

**2. Enforcement is universally in the wrong layer.** Family Link, Screen Time, Family Safety and every kid launcher enforce policy inside an OS designed for adults, which is why the bypass catalogues are so long — WebViews, accessibility menus, secure folders, clock changes, reboot windows, recovery mode. Kiddoware's **CVE-2023-28153 ("parental control bypass", 5m installs)** is the reductio. Nintendo is praised precisely because there is no general-purpose OS underneath. **An immutable OS with the policy engine below the user session, and no reachable escape hatch, is the single most defensible technical claim kidnix can make.**

**3. The web is the hole in every system.** Every filter in this survey is defeated by an embedded browser, an in-app WebView, or a self-sent link. Any product that ships a general HTML renderer inherits the problem. The only thing that survives is a strict allowlist enforced at the network layer.

**4. Linux has *just* acquired a session model, and nobody has built a child product on it.** As of **GNOME 50 (18 March 2026)** — default in Ubuntu 26.04 LTS and Fedora 44 — screen-time limits, bedtime schedules and per-child usage charts exist upstream for the first time, with a web-filtering backend landed and its UI still unwritten. There is still no open-source equivalent of the Nintendo parent app, no per-app limits, no journal, no activity shell, and **no kids edition anywhere in the atomic/immutable ecosystem** (Universal Blue ships Bluefin, Aurora and Bazzite; none is for children). This is a genuinely narrow, genuinely open window: the primitives now exist, and no one has assembled them into a product. kidnix should consume and extend them — and could plausibly contribute the missing web-filter UI back — rather than reinvent the stack.

**5. Nobody separates constraint from surveillance.** The market offers either total permissiveness or Bark-style message scanning and GoGuardian-style screen watching. There is no widely available product that is **tightly constrained and not watching** — local policy, transparent to the child, nothing transmitted. Given that 73% of US parents worry about corporate data collection, this is an underserved position rather than a niche one.

**6. Nobody handles multiple children on one device well.** The best system in the market gets it wrong (Nintendo, per-console). 39% of UK primary families are sharing.

**7. Nobody serves the "screen off, story on" case on a computer.** Yoto and tonies proved a large market for it in a dedicated appliance; no general-purpose child computer offers a comparable mode.

**8. Family-authored content is a paid add-on or absent.** Make Your Own is Yoto's most-loved feature and a commercial afterthought. On an open platform it should be free and central.

**9. Nobody has published usability evidence for the journal model.** Sugar invented it twenty years ago; nobody has shown that children understand it or that it scales past a few hundred entries. Sugar's own design anticipated the problem (temporal falloff, school backup servers) and shipped neither. For 4–8s the retrieval affordances must be **visual and non-textual** — thumbnails, "today / yesterday / before that", activity colour — with automatic falloff and a small bounded "favourites shelf" the child chooses, plus a boring conventional file view for the adult, whose absence was the single most repeated complaint about Sugar.

**10. Nobody has revived Flip-to-Hack.** Endless's Hack let a child flip any running app over to see and edit what made it work, in a real Linux environment with real tools. It is the best unexploited idea in this entire survey, it costs nothing to prototype, and it is the only mechanism anyone has demonstrated for turning a bounded kid shell into a genuine on-ramp to computing rather than a nicer walled garden.

**11. Longevity is nobody's promise.** Every product in this survey either died, was acquired, was deprecated, or is one strategy meeting from it. "This will still work in ten years and your child's work is in an open format on your own disk" is a claim only an open, immutable, offline-capable system can credibly make — and it is exactly what a parent who bought a LeapPad, a Kano kit or a 2020 Chromebook now wants to hear.

---

## 6. Things NOT to do

1. **Do not build a theme plus a package list.** That is Qimo, DoudouLinux and LinuxKidX, all dead. The value must be in the shell, the session model, the journal and the parent app.
2. **Do not build a launcher over an adult OS.** That is Kids Place with a CVE for "parental control bypass". If the child can reach a shell, a recents switcher, an accessibility menu or a settings WebView, the product is decorative.
3. **Do not ship a general web browser.** Every filter in this document is defeated through one. If web content is needed, it must be a fixed allowlist enforced at the network layer, not a browser with a filter.
4. **Do not sell a price or a story.** OLPC sold "$100" and shipped at $180 and never recovered from the gap. Kano sold "build your own computer" and abandoned its OS within six years.
5. **Do not build surveillance.** Bark scans every message; GoGuardian's false positives flag university and health sites and half of monitored students self-censor. A four-to-eight-year-old does not need message scanning, and building it would forfeit kidnix's single clearest differentiator.
6. **Do not require ongoing parental administration.** Only 42% of parents rank screen management in their top priorities and 33% already feel judged. Anything requiring weekly attention will be abandoned like the 75% of US parents who use no tools at all.
7. **Do not make time limits the primary control.** FOSI found time limits rated significantly less useful than every other control type. Bounded *sessions* with a soft stop and grants (Nintendo's +5/+15/+30/+60) beat abstract daily budgets.
8. **Do not build a content store, in-app purchases, ads, or an "ask to buy" flow.** 73% and 72% of parents worry about data collection and advertising respectively. Commerce inside a child's world is the thing Amazon is most criticised for.
9. **Do not depend on a server for core function.** Yoto and tonies need Wi-Fi for the parent app; Endless and OLPC deliberately worked offline. A child's session must work with the router unplugged.
10. **Do not enable any contact surface at launch** — no chat, no multiplayer, no accounts, no friend lists. 64% of parents fear stranger contact via games. If it ever ships, copy Nintendo's per-friend parental approval and per-room camera consent.
11. **Do not proprietise the child's work.** The journal must export. Yoto's DRM is its most-criticised property; VTech responded to leaking 6.4 million children's profiles by rewriting its T&Cs to disclaim responsibility.
12. **Do not assume the child gets their own device.** 39% of UK primary families are sharing. Profile switching must be trivial and instant.
13. **Do not promise educational outcomes.** OLPC's Peru RCT found none, and the resulting credibility damage outlasted the project. Promise a *good experience of computing*, not test scores.
14. **Do not build an age-verification or identity system.** The 2026 criticism of the UK and Australian bans is precisely about mass ID verification, over-blocking and excluding vulnerable children. Local, verification-free constraint sidesteps all of it.
15. **Do not fork the desktop.** Every separately maintained kid distribution died in three to six years; every survivor is a thin layer over a large upstream. Endless said it plainly after a decade and tens of millions of dollars: *"About 95 percent of what we ship is GNOME OS."* Build the shell, the session, the journal and the parent app — and take everything else from upstream, including GNOME 50's new parental-control primitives.
16. **Do not build an interface the adult cannot use.** Sugar's fatal wound was that *"even teachers who are comfortable with computers find Sugar difficult and counter-intuitive."* kidnix needs a conventional adult mode on the same machine, reachable from the same login screen, with no reinstall and no jargon.
17. **Do not assume the child will create.** Ames found over half of XO recipients simply were not interested, and most who used them consumed. Design the guardrails for consumption first, then make creation the easy adjacent step. Any success metric premised on "children will program it" is measuring the designers' childhood, not the users'.
18. **Do not design a first run that outshines Day 2.** Kano's build experience was superb and reviewers noted there was "no direction of how to start using the device" afterwards. Budget more design effort for week three than for the unboxing.
19. **Do not promise enforcement you cannot deliver.** malcontent's own README says a technically advanced user can work around it. If kidnix tells parents the controls hold, the immutable base, the absent shell, the Flatpak-only app surface and the network-layer allowlist have to actually make that true.

---

## 7. Top ten takeaways

1. **Parents are not unaware; they are unserved.** 93% of UK parents know parental controls exist and only 35–37% use the built-in ones; 75% of US parents of 0–8s use no screen-time tool at all. The problem is friction and trust, not education.
2. **Ages 6–7 are the peak-adoption window.** Use of built-in manufacturer controls among parents of 6–7s jumped from 36% to 50% in one year, and rules about app downloads from 49% to 71%. Concern about adult content also peaks here (77%). kidnix's target age is the moment parents are most willing to act.
3. **The most-praised system in the market wins on architecture, not features.** Nintendo enforces in firmware, presents controls in a standalone app, leads with reporting rather than restriction, and offers soft-stop plus quick grants. Its worst flaw — per-console rather than per-user restriction — is exactly what a multi-child household hits first.
4. **Every general-purpose OS leaks, and the leak list is public.** WebViews, accessibility menus, secure folders, cloned apps, clock changes, post-reboot windows, ADB. Enforcement below the user session in an immutable OS is the strongest technical claim available.
5. **"Physical token = one thing" is the proven interaction model for this age.** tonies at €630m revenue and 11.8m boxes and Yoto at £94.8m growing 86% both work because a four-year-old can pick up a card without reading, without an account, and without a parent.
6. **Content lock-in is where the money is — and where the complaints are.** Figurines are 71% of tonies' revenue; Amazon reportedly raised UK Kids+ by 58% in one step. Family-authored content (Make Your Own) is the feature that defuses this, and on an open platform it should be free and central.
7. **Constraint sells at a premium now.** Light Phone III at $599–$799, Toniebox 2 at £104.99, Pinwheel launching a *landline* for 5–10s. "Does less" is a positioning, not an apology.
8. **Kid software is what gets abandoned first.** Edge Kids Mode killed with a one-line notice; Screen Time under-invested since iOS 13; Hack gone; Kano in administration; LeapFrog sold for $72m after a $124m annual loss. Longevity and openness are a genuine, evidence-backed pitch.
9. **Separate constraint from surveillance and say so.** School monitoring's documented harms — mass false positives on health and LGBTQ resources, discipline outpacing support 78% to 54%, half of students self-censoring — plus 73% of parents worrying about corporate data collection, make "tightly bounded, watching nothing, sending nothing" a differentiated and defensible position.
10. **Creative and audio are the underserved wins.** 65% of 3–7s already draw on devices; 3–7s are the age group most likely to listen to audiobooks; parents of 3–7s name creative skills as the top benefit of being online. A shell whose default state is *making something* — and which works with the screen off for stories — matches what both children and parents already do.

**Bonus, and possibly the most actionable finding of all: the timing window is now.** GNOME 50 shipped child screen-time limits and bedtime schedules in March 2026 and is the default in Ubuntu 26.04 LTS and Fedora 44; no kids edition exists anywhere in the atomic/immutable ecosystem; the UK's Online Safety Act children's duties have made parents fluent in device-level safety; and the public information about "Linux for kids" is so stale that 2026 listicles still recommend software that died in 2010. Build a **thin layer** — shell, session, journal, parent app — over an upstream that now supplies the primitives, and ship it while the field is empty.

---

## 8. Sources

### Primary survey and government reports

- Ofcom, *Children and Parents: Media Use and Attitudes Report*, published 21 May 2026 (full PDF read; n=5,008 parents of 6mo–17s, 3,426 children 8–17) — https://www.ofcom.org.uk/siteassets/resources/documents/research-and-data/media-literacy-research/children/2026-children-and-parents-report/children-and-parents-media-use-and-attitudes-report-2025-6.pdf
- Ofcom, *Children and Parents: Media Use and Attitudes Report 2025*, published 7 May 2025 (full PDF read) — https://www.ofcom.org.uk/siteassets/resources/documents/research-and-data/media-literacy-research/children/childrens-media-use-and-attitudes-report-2025/childrens-media-literacy-report-2025.pdf
- Ofcom, report landing page and interactive data — https://www.ofcom.org.uk/media-use-and-attitudes/media-habits-children/children-and-parents-media-use-and-attitudes-report-2025
- Ofcom, *Top trends from our latest look at UK children's online lives* — https://www.ofcom.org.uk/media-use-and-attitudes/media-habits-children/top-trends-from-our-latest-look-at-uk-childrens-online-lives
- Common Sense Media, *The Common Sense Census: Media Use by Kids Zero to Eight, 2025* (full PDF read; fielded 5–29 Aug 2024, n=1,578) — https://www.commonsensemedia.org/sites/default/files/research/report/2025-common-sense-census-web-2.pdf
- Common Sense Media press release, "Digital Childhood Starts at Age Two" — https://www.commonsensemedia.org/press-releases/digital-childhood-starts-at-age-two-landmark-study-shows-evolution-of-young-childrens-media-use
- Pew Research Center, *How Parents Manage Screen Time for Kids*, 8 October 2025 — https://www.pewresearch.org/internet/2025/10/08/how-parents-manage-screen-time-for-kids/
- Pew Research Center, *How parents approach their kids' screen time* — https://www.pewresearch.org/internet/2025/10/08/how-parents-approach-their-kids-screen-time/
- Pew Research Center, *How parents describe their kids' tech use* — https://www.pewresearch.org/internet/2025/10/08/how-parents-describe-their-kids-tech-use/
- Family Online Safety Institute, *Connected and Protected: Insights from FOSI's 2025 Online Safety Survey* (full PDF read; Feb–Mar 2025) — https://fosi.org/wp-content/uploads/2025/05/Connected-and-Protected-Insights-from-FOSIs-2025-Online-Safety-Survey.pdf
- UK Parliament Education Committee, *Screen time: impacts on education and wellbeing*, 25 May 2024 — https://publications.parliament.uk/pa/cm5804/cmselect/cmeduc/118/summary.html
- GOV.UK, Kids Online Safety campaign — parental controls — https://kidsonlinesafety.campaign.gov.uk/parental-controls/
- Internet Matters, *Pulse* survey (Oct–Nov 2025, n=1,000 children 9–17 + 2,000 parents 3–17; accessed via search abstract, site blocks fetching) — https://www.internetmatters.org/pulse/
- eSafety Commissioner (Australia), *Growing up online: parenting young children aged 3 to 10*, and *Connected, curious, cautious* (accessed via search abstracts; site blocks fetching) — https://www.esafety.gov.au/research/growing-up-online-parenting-young-children-aged-3-to-10-in-the-digital-age
- Computing at School, summary of Ofcom's 2025 report for ages 3–11 — https://www.computingatschool.org.uk/forum-news-blogs/2025/may/understanding-media-use-among-children-aged-3-11-key-insights-from-ofcom-s-2025-media-literacy-report/

### Academic

- Ghosh, Badillo-Urquiola, Guha, LaViola, Wisniewski (2018), *Safety vs. Surveillance: What Children Have to Say about Mobile Apps for Parental Control*, CHI. 180 citations.
- Wisniewski, Ghosh, Xu, Rosson, Carroll (2017), *Parental Control vs. Teen Self-Regulation: Is there a middle ground for mobile online safety?*, CSCW. 218 citations.
- *Protection or Punishment? Relating the Design Space of Parental Control Apps and Perceptions about Them* (2021) — 58 Android apps, 3,264 app reviews.
- Hiniker, Suh, Cao, Kientz (2016), *Screen Time Tantrums: How Families Manage Screen Media Experiences for Toddlers and Preschoolers*, CHI. DOI 10.1145/2858036.2858278. 151 citations.
- *Moving Beyond Parental Control toward Community-based Approaches to Adolescent Online Safety* (2025) — https://arxiv.org/pdf/2503.22995
- *Do parental control tools fulfil family expectations for child protection? A rapid evidence review*, Journal of Children and Media (2023) — https://www.tandfonline.com/doi/full/10.1080/17482798.2023.2265512 (403 to automated fetch; findings via search abstract)
- Lueks, Dreyer, Federrath, Simon (2026), *Assessing Age Assurance Technologies: Effectiveness, Side-Effects, and Acceptance* — https://arxiv.org/abs/2603.25695
- Livingstone & Stoilova (2021), *The 4Cs: Classifying Online Risk to Children*, CO:RE short report.
- Ames, M. (2019), *The Charisma Machine: The Life, Death, and Legacy of One Laptop per Child*, MIT Press.

### Platform documentation and journalism

- Amazon: https://www.aboutamazon.com/news/devices/fire-kids-tablet-buying-guide-find-out-which-device-is-right-for-you · https://techcrunch.com/2022/06/08/amazon-is-simplifying-the-pricing-structure-for-its-kids-all-in-one-subscription-service/ · https://www.justice.gov/archives/opa/pr/amazon-agrees-injunctive-relief-and-25-million-civil-penalty-alleged-violations-childrens · https://apps.apple.com/us/app/amazon-kids-parent-dashboard/id6471528064
- Apple: https://www.apple.com/newsroom/2025/06/apple-expands-tools-to-help-parents-protect-kids-and-teens-online/ · https://www.apple.com/uk/families/ · https://www.macworld.com/article/2359164/ios-screen-time-flaws-loopholes-update.html · https://mjtsai.com/blog/2025/09/24/screen-time-brokenness/ · https://developer.apple.com/videos/play/wwdc2025/299/
- Google: https://families.google/familylink/ · https://support.google.com/kidsspace/answer/9990724 · https://support.google.com/chromebook/answer/7680868 · https://www.bitdefender.com/en-us/blog/hotforsecurity/family-link-bypass-android-2025 · https://www.aljazeera.com/economy/2026/1/14/child-rights-org-says-google-undermines-parental-control-of-child-accounts · https://blog.youtube/news-and-events/an-update-on-kids/
- Microsoft: https://www.microsoft.com/en-gb/microsoft-365/family-safety · https://support.microsoft.com/en-us/edge/kids-mode-no-longer-supported-in-microsoft-edge · https://learn.microsoft.com/en-us/deployedge/microsoft-edge-relnote-archive-stable-channel#version-1170204531-september-15-2023
- Nintendo: https://www.nintendo.com/us/mobile-apps/parental-controls/ · https://en-americas-support.nintendo.com/app/answers/detail/a_id/22508 · https://en-americas-support.nintendo.com/app/answers/detail/a_id/68384 · https://kotaku.com/the-nintendo-switchs-parental-controls-are-amazing-1824301547 · https://www.protectyoungeyes.com/devices/nintendo-switch-2-parental-controls

### Kid hardware, audio and phones

- tonies FY2025 results — https://www.mynewsdesk.com/us/tonies/pressreleases/tonies-continues-profitable-growth-with-record-results-in-2025-expects-strong-momentum-for-full-year-2026-expansion-of-ecosystem-around-toniebox-2-proves-a-global-success-3442746
- https://tonies.com/en-gb/ · https://en.wikipedia.org/wiki/Tonies_(company)
- https://uk.yotoplay.com/yoto-player · https://musically.com/2025/08/27/childrens-speakers-startup-yoto-saw-sales-grow-by-86-in-2024/ · https://busybusylearning.com/is-yoto-worth-it-honest-2026-parent-review-pros-cons/
- https://en.wikipedia.org/wiki/LeapFrog_Enterprises · https://en.wikipedia.org/wiki/VTech
- https://www.playosmo.com/en-gb/ · https://en.wikipedia.org/wiki/Byju%27s
- https://www.bark.us/bark-phone/ · https://gabb.com/ · https://www.pinwheel.com/ · https://en.wikipedia.org/wiki/Light_Phone · https://techcrunch.com/2025/03/13/minimalist-light-phone-iii-launches-march-27/
- https://www.smartphonefreechildhood.org/ · https://en.wikipedia.org/wiki/The_Anxious_Generation
- https://en.wikipedia.org/wiki/Online_Safety_Act_2023 · https://en.wikipedia.org/wiki/Online_Safety_Amendment_(Social_Media_Minimum_Age)_Act_2024

### School stacks

- https://www.eff.org/wp/school-issued-devices-and-student-privacy
- https://www.eff.org/deeplinks/2023/10/how-goguardian-invades-student-privacy · https://redflagmachine.com/
- https://www.edweek.org/technology/software-that-monitors-students-may-hurt-some-its-meant-to-help/2022/08
- https://www.gov.uk/government/publications/keeping-children-safe-in-education--2

### Linux, OLPC and the graveyard

**OLPC / Sugar**
- https://www.theverge.com/2018/4/16/17233946/olpcs-100-laptop-education-where-are-they-now
- https://wiki.sugarlabs.org/go/Human_Interface_Guidelines/The_Laptop_Experience/The_Journal · https://wiki.sugarlabs.org/go/Human_Interface_Guidelines/The_Laptop_Experience/Zoom_Metaphor · https://wiki.sugarlabs.org/go/Human_Interface_Guidelines/The_Sugar_Interface
- https://wiki.sugarlabs.org/images/5/56/Teacher_Needs_&_Sugar-Usability_Report.pdf (Paz & Gibson, 25 Feb 2012)
- https://mitpress.mit.edu/9780262537445/the-charisma-machine/ (Ames, 2019)
- https://publications.iadb.org/publications/english/document/Technology-and-Child-Development-Evidence-from-the-One-Laptop-per-Child-Program.pdf · https://www.aeaweb.org/articles?id=10.1257%2Fapp.20130267 · https://www.sciencedirect.com/science/article/abs/pii/S0047272725002373
- https://liliputing.com/negroponte-sugar-os-was-olpcs-biggest-mistake/
- https://en.wikipedia.org/wiki/Sugar_(desktop_environment) · https://en.wikipedia.org/wiki/Sugar_Labs · https://wiki.sugarlabs.org/go/Sugar_on_a_Stick · https://github.com/sugarlabs/sugar/releases
- https://en.wikipedia.org/wiki/Ceibal_project

**Kano**
- https://en.wikipedia.org/wiki/Kano_Computing · https://find-and-update.company-information.service.gov.uk/company/08375450/insolvency
- https://www.pcworld.com/article/407848/kano-computer-kit-complete-review.html · https://www.digitaltrends.com/computing/kano-computer-kit-complete-review/
- https://www.kano.me/blog/kano-x-astrosafe · https://www.kano.me/faq

**Endless**
- https://www.endlessglobal.com/foundation/access/operating-system · https://en.wikipedia.org/wiki/Endless_OS_Foundation
- https://access.endlessstudios.com/blog/hack-computer-chronicles · https://access.endlessstudios.com/blog/endless-os-a-conversation-about-whats-changing-and-why-it-matters · https://blog.endlessglobal.com/blog-1/endless-2-0
- https://www.phoronix.com/news/Endless-Hack-Computer · https://support.endlessos.org/en/endless-key

**Distros**
- https://www.edubuntu.org/ · https://discourse.ubuntu.com/t/edubuntu-26-04-lts-released/80831 · https://discourse.ubuntu.com/t/announcing-edubuntu-revival/32929
- https://distrowatch.com/table.php?distribution=debianedu · https://distrowatch.com/table.php?distribution=escuelas · https://escuelaslinux.sourceforge.io/english/
- https://distrowatch.com/table.php?distribution=qimo · https://news.softpedia.com/news/qimo-the-popular-ubuntu-based-linux-operating-system-for-kids-closes-shop-499820.shtml
- https://distrowatch.com/table.php?distribution=doudou · https://en.wikipedia.org/wiki/DoudouLinux · https://distrowatch.com/table.php?distribution=ubermix
- https://distroscout.com/usage/kids/ (illustrative of how stale the category's public information is) · https://universal-blue.org/ · https://fedoraproject.org/wiki/FedoraForKids

**Linux parental controls**
- https://help.gnome.org/users/gnome-help/stable/parental-controls.html.en · https://github.com/endlessm/malcontent
- https://release.gnome.org/50/ · https://tecnocode.co.uk/2025/07/24/a-brief-parental-controls-update/ · https://tecnocode.co.uk/2025/11/19/parental-controls-screen-time-limits-backend/
- https://discuss.kde.org/t/parental-control-application/957
- https://support.google.com/chromeosflex/thread/214605352/familylink-can-t-limit-apps-or-device-time-for-chromeos-flex-devices · https://support.google.com/families/answer/9116646
- https://www.bleepingcomputer.com/news/security/parental-control-app-with-5-million-downloads-vulnerable-to-attacks/ (Kids Place / CVE-2023-28153)

**Raspberry Pi, apps, new entrants**
- https://www.raspberrypi.com/for-home/ · https://static.raspberrypi.org/files/about/Code_Club_annual_survey_report_2025.pdf · https://forums.raspberrypi.com/viewtopic.php?t=299127 · https://raspberrytips.com/most-common-raspberry-pi-issues/
- https://apps.kde.org/gcompris/ · https://planet.kde.org/gcompris-2026-03-10-release-gcompris-26-1/
- https://entrepreneur.economictimes.indiatimes.com/news/funding/wippi-raises-1-2-mn-seed-funding-led-by-12-flags-to-build-screen-free-ai-products-for-children/133170389
- https://www.gov.uk/government/news/keeping-children-safe-online-changes-to-the-online-safety-act-explained · https://www.ofcom.org.uk/online-safety/protecting-children/new-rules

**Sourcing caution.** Two further OLPC figures surfaced during research but were **deliberately excluded** from the body because they traced back only to an AI-generated encyclopaedia: a reported ~70% XO hardware-failure rate within six months in Birmingham, Alabama, and a ~21.5% daily in-school usage rate in Uruguay. Both would strengthen the argument if true; verify against primary sources before using them. Everything quoted above — the RCT results, the Paz & Gibson field interviews, the Ames findings, and the Negroponte, Bender and McQueen quotations — comes from named primary or peer-reviewed sources.

**Items flagged [verify] in the body**, all 2026-dated and sourced from recent trade or news reporting rather than statute or filings: the Amazon UK Kids+ price rise from £38 to £59.99 (5 Aug 2026); Google's climb-down on newly-13 supervision after the October 2025 FTC complaint; the UK under-16 social media ban (announced 15 June 2026), the 16–17 curfews (15 July 2026), and the statutory England school phone ban (announced April 2026, in force from ~30 June 2026). Check each against a primary source before it appears in anything external.
