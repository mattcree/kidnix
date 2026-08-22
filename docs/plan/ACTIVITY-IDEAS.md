# Activity ideas backlog

Ideas not yet scheduled. Each needs: the evidence/curriculum hook, what it
produces for the Journal, and whether it's curation (upstream app) or ours.

| Idea | Hook | Journal artefact | Build or curate | Source |
|---|---|---|---|---|
| **Clock & time** — (a) *Play with the clock*: drag hands, scene changes (sun/moon, this family's routine pictures), speaks "half past three", real-time mode showing *now* inside the day's routine; (b) *What time is it?* practice — curate GCompris "learning clock"; (c) *Timers you can see*: "how long is a minute", sand-timer races, same visual language as the session sun so the sun becomes legible | Y1/Y2 maths: time to hour/half, quarter, 5 min; 02 §2.7 immature duration judgement; makes the session timer meaningful; household routine = the thing that actually ends screen time (02 #18) | a photo of "my clock" + the routine strip | (a),(c) ours; (b) curate | Matt, 2026-08-22 |
| Read-to-me / I-read-to-you recording loop | 05 §3 additional #1 | audio of the child reading | ours | 05 |
| Subitising & number bonds to 5/10 built to the ELG | 05 §3 additional #2 | — | ours (or curate GCompris) | 05 |
| Printable unplugged companions (sequence cards, floor grid) | 05: physicality g=0.72 vs 0.44 | printed sheet | ours | 05 |
| Dialogic prompt layer over the library | 05: prompts induced dialogic reading in untrained parents | — | ours | 05 |
| Oral storytelling recorder with picture prompts | 05 §3 additional #5 | audio story | ours | 05 |
| "Listen" screen-off story mode, family-recorded stories | 04 §5.7 (Yoto/tonies) | — | ours | 04 |
| Flip-to-see-how-it-works (Endless Hack) for one activity | 04 §5.10 | — | ours | 04 |
| **Android apps via Waydroid** (curated APK shelf) — verified 2026-08-22: Fedora 44 kernel has `CONFIG_ANDROID_BINDER_IPC=y`/binderfs; `waydroid` 1.6.3 is in Fedora repos. Sandbox: LXC container + own netns behind `waydroid0` → nftables drop-all on that bridge; vanilla (no GAPPS) image, no Play/IAP; sideloaded APKs only; runs as kid in kiosk, one app fullscreen, launched from a manifest tile. Unlocks ScratchJr (no Linux build), Khan Kids, Teach Your Monster, Sago Mini. Spike: bundle system image offline (~1 GB, licence), root `waydroid-container.service` surface, apps that need Play, perf on 4 GB | 05 (ScratchJr evidence), 04 (allowlist-first; ecosystem not apps is the problem), 03 (no egress) | app-dependent | ours (integration) | Matt, 2026-08-22 |
