# kidnix v0.1.6 — accessibility and inclusive-design review

> Reviewer: accessibility & inclusive-design specialist for children's technology
> (WCAG 2.2 / EN 301 549, AT-SPI/GTK, switch access, autism- and ADHD-informed
> design, SEND schools). 2026-08-23. Read-only review.

**Method.** I ran the shell here (`--demo --windowed --screen 1280x800@102`),
captured four surfaces, and probed the **live AT-SPI tree** with `Atspi`
(`org.a11y.Bus` is up on this host) — so roles, names, states and pixel extents
below are measured. I recomputed every colour literal in `theme.css` and
simulated the profile palettes under deuteranopia/protanopia (Viénot 1999).
**Not verified:** anything needing synthetic input (real Tab order), the earcons
on speakers, Piper's voice, and behaviour under gnome-kiosk — this host has no
kiosk, so `--windowed` placed both windows itself.

---

## 1. Verdict

**Conditional fail for a disabled child's first session; a strong pass on the
things most children's products get wrong.** The type, the target sizes, the
outline-not-grey rule, the physical-mm layout system and the computed-contrast
test suite are better than anything I audited for the charity, commercial
products with accessibility teams included. But the shell is **not operable
without a pointer** — the CCI audit's "MET" on 03 #33 is wrong — and
**read-aloud, explicitly the whole accessibility strategy (06 §4.5), has no
fallback for a child who cannot hear it.** Together those exclude switch users,
keyboard-only users and deaf/HoH pre-readers from the first session. Calm mode,
reduced motion and any language other than en-GB are absent. Fix the five in §4
and this becomes the most accessible thing in its category.

---

## 2. Five strengths

1. **Physical-unit layout with real floors.** `metrics.py` sizes in millimetres
   from the monitor's geometry; `fit` shrinks *preferences* while
   `MIN_TARGET_MM`, `GAP_FLOOR_MM` and `TILE_LABEL_MIN_PT` are exempt. Measured
   on the reference panel: tiles **170×170 px = 42.3 mm**, four times the WCAG
   2.2 AAA floor. Almost nobody does this; most products ship CSS pixels.
2. **Labels are never cut, and the rule is tested headless.** `labels.py` wraps,
   shrinks in 1 pt steps, then adds a third line — never ellipsises, never
   hyphenates. `test_labels.py` proves the shipped names fit at 96/102/118 dpi
   with no display. For a child matching shape to word a half-word is a failed
   match, and this is the only codebase I have seen treat that as a correctness
   property.
3. **Contrast is computed and regression-tested.** `test_theme_css.py` reparses
   the stylesheet and recomputes the ratios; the 1.5:1 border was caught this
   way. Ink on paper **16.62:1**, sleeping palette 12.71:1, PIN error 6.12:1 —
   all confirmed independently.
4. **Never grey out.** `.not-allowed` is a dashed `#5a5f6a` outline (5.99:1 on
   paper), the disabled pager is `opacity: 0`, unavailable activities get no
   tile. Grey-as-disabled survives neither greyscale nor CVD nor pre-literacy.
5. **Accessible names are real, and are the same string the shell speaks.** The
   AT-SPI tree shows `[button] 'Scribble. Draw with the mouse.'`,
   `[button] 'Lots of time left.'` One source of truth for AT, read-aloud and
   tests. Input also fires on **press**, from **any** mouse button, with a 150 ms
   debounce — three motor accommodations most products get wrong individually.

---

## 3. Ranked concerns

### B1 — BLOCKER: nothing in the band is reachable without a pointer

**Evidence.** Since v0.1.5 the band is a **separate toplevel**. AT-SPI confirms
two frames under one application: `[frame] 'kidnix-content'` and
`[frame] 'kidnix-band'`. Tab does not cross toplevels, and
`build_files/40-lockdown.sh` blanks **all 102** `wm/mutter` keybindings —
`switch-windows` included, with an image test asserting `close` is blank. There
is no `Gtk.EventControllerKey` anywhere in the shell except the PIN pad
(`screens/grownup.py:134`). So Back, Undo, My Things, the Ear, the sun and the
gate have **no keyboard route at all**, on any surface, ever — and once inside
an activity a keyboard/switch-only child cannot leave it except by waiting for
the timer. That breaks SYNTHESIS A6 and C1–C3.

Worse, `band.py`'s `HoldButton` ends with
`self.connect("clicked", lambda _b: None)` under a comment promising a keyboard
hold. The **grown-up gate's keyboard route is a literal no-op**: a parent with a
tremor, a switch, or one hand cannot open the parent sheet.

Nothing calls `grab_focus()` anywhere, so no screen has initial focus; the
AT-SPI dump shows **zero** nodes with `FOCUSED` after a fresh Home.

**Recommendation.** (a) One shell-level key controller on *both* toplevels:
arrows move within a region, `Tab`/`Shift+Tab` crosses between band and content,
`Enter`/`Space` activates. (b) `grab_focus()` on the first control of every
screen in `on_enter()` — free read-aloud-on-entry too. (c) A real key-hold on
the gate. (d) With (a)–(c) done a two-switch scan is ~20 lines, and 06 §4.4 says
switch access follows for free once everything is keyboard-reachable.
(e) Correct audit row 03 #33 from MET to FAIL.

### B2 — BLOCKER: read-aloud is the accessibility strategy and has no deaf/HoH fallback

**Evidence.** 13 spoken-only messages in `app.py` with no on-screen counterpart
— `"That one didn't open. Let's try something else."` (1219), `"That one isn't
here any more."` (1194), `"Nothing to undo."` (1533), `"You're home."` (1476).
The critical one is `"{name} is asking if you're done."` (1315), whose own
docstring says *"nothing on screen tells a pre-reader that the question is
theirs to answer, so the shell says so out loud"* — at put-away, where only
pressing the activity's tick saves the drawing. A deaf child loses the work.

The same architecture is stated as a design win in `band.py:set_offer_mode`:
the two ending choices are *"pictures, not words… the audio is the channel that
carries the sentence."* At the most consequential choice of the session, a
deaf/HoH pre-reader gets two unlabelled 20 mm glyphs that differ from the two
they replaced only by a 1 px heavier border.

AGENTS.md §3.4 says "nothing essential is text-only". The inverse — nothing
essential is audio-only — is nowhere in the constitution and is now violated
systematically. ~1 in 1,000 UK children is deaf; far more have glue ear at five,
which is intermittent and undiagnosed for months.

**Recommendation.** A caption strip in the band (or immediately under it) that
renders the last utterance as large text plus its icon for ~4 s, driven off the
same `SpeechManager` hook that drives the highlight ring. It costs one widget,
serves deaf children, serves a broken speech-dispatcher, serves a noisy room,
and serves the emerging reader. Add "nothing essential is audio-only" to §3.4.

### B3 — BLOCKER: no calm mode, no reduced motion, no sound control

**Evidence.** `grep -rin "enable-animations\|reduced\|calm\|mute\|volume"` over
`shell/` returns **nothing** in code — only "calm mode" in the parent-panel
stub's prose. Transitions are 400 ms and the keep-flight 1100 ms,
unconditionally. SYNTHESIS H6 requires reduced motion honoured and **one calm
mode**; WCAG 2.2 SC 2.3.3 requires interaction-triggered motion to be
disableable. `10-input` sets `enable-animations=true`; the shell never reads it.

Sound: `sound.py`'s earcons attack in **0.4–4.0 ms** (`FADE_MS = 6.0`; only
`sleep` has 90 ms), against 06 §7.4 #26's "all audio fades in over ≥ 150 ms" —
written because *sudden unexpected sound is the most frequently identified
auditory sensory trigger* for autistic children (06 §4.3). `tap` fires on every
press. There is a genuine unbypassable 70% hardware ceiling
(`usr/libexec/kidnix-audio-cap` + soft-mixer) — good engineering — but a ceiling
is not a control: no mute, no soft mode, nothing in the grown-up sheet.

**Recommendation.** One `calm = true` key in `parent.toml`: force
`gtk-enable-animations` off, drop earcons to a soft set or silence, lengthen
attacks to ≥ 60 ms, freeze progressive disclosure, dim the palette. Dan's post
(#9) asked for exactly this from the parent side.

### M1 — MAJOR: measured contrast failures, all on the band

Recomputed from `theme.css` literals and `band.py`'s cairo calls:

| Thing | Ratio | Needs |
|---|---|---|
| Focus ring `#ffd23f` on default band `#0f8a8a` | **2.90:1** | 3:1 (1.4.11) |
| Sun `#ffd64f` on band | **2.98:1** | 3:1 |
| **Warm** sun `#fa9e30` on band (last 6 min) | **1.99:1** | 3:1 |
| Sun's "ghost" start outline (white @30%) | **1.59:1** | 3:1 |
| Horizon line (white @55%) | 2.30:1 | 3:1 |
| Grown-up gate fill / border vs band | 1.72 / 1.57:1 | 3:1 |

The stylesheet's comment defends the ring by pairing it with an ink border —
true on the cream content window, **false on the band**, where
`outline-offset: 2px` places the yellow on teal with nothing behind it. And the
timer becomes *least* visible exactly when it matters most. The ghost outline at
1.59:1 is the reference that makes shrinking legible as *loss*; without it the
sun is merely small today.

**Recommendation.** A 2 px `@kid-ink` outer stroke around the ring on the band
(same reserved colour, one extra edge); a 2.5 px ink outline on the sun and
horizon; warm the sun by shape/texture as well as hue, or pick a warm value that
holds ≥ 3:1 on all four primaries.

### M2 — MAJOR: colour-as-identity collapses under CVD

`PROFILE_COLOURS` pairs 2 (`#2e7d32`/`#f9a825`) and 4 (`#bf360c`/`#ffb300`) are
**1.09:1** apart in luminance and simulate to `#6d6d35` vs `#757500` under
deuteranopia — indistinguishable. B6 says "colour = whose, shape = what", but
there is **no shape carrier for identity**: the band tint is the only per-child
signal on every screen after S1. ~8% of boys are colour-blind and ~40% leave
school not knowing (06 §4.2), so this bites an undiagnosed child in a two-child
household.

**Recommendation.** Add a per-profile **shape** token (a small badge — star,
leaf, moon, wave) drawn in the band and on Journal cards alongside the tint, and
choose the four primaries so every pair is ≥ 3:1 apart in luminance. Test in
`test_theme_css.py` the way the edges already are.

### M3 — MAJOR: the tiles do not depict what the child does

Every shipped manifest uses `icon_kind = "icon-name"` pointing at a vendor logo
(`tuxpaint`, `supertux2`, `tuxmath` — three penguins). Worse, when the theme
lacks the name `widgets.icon_image()` falls back to `category_icon(category)`,
one bundled image per category: my demo run shows Scribble, Splodge and Stamps
as the identical pencil and Letters and Counting as the identical book — five of
six tiles, two pictures. Under Flatpak that fallback is the likely path, not the
edge case. For a pre-reader with low vision, CVD or no English the icon is the
*only* persistent channel. (Agreeing with cci-researcher #19, adding the
fallback-collapse evidence; the S1b icons prove the team can do this well.)

**Recommendation.** Ten depictive activity icons, `icon_kind = "path"`, plus a
`--validate-manifests` check that fails when two visible tiles resolve to the
same image.

### M4 — MAJOR: the Sleeping screen is not dim

`sleeping.py` adds the `sleeping` CSS class to the Screen *box*, which is
`halign/valign CENTER`; `app.py:846` adds it only to the **band** window, so the
content window keeps `window.kidnix` (`#fbf7ef`). Rendered: full-brightness
cream, a small dark rectangle in the middle, a dark strip on top. The one
surface designed to be low-arousal is the brightest thing in the product — bad
for photophobia, migraine, sensory-defensive autism and a tired 4 pm generally.
One line: put the class on the window.

### M5 — MAJOR: en-GB only, in a country where 21.6% of pupils have another first language

`speech.SPEECH_LANGUAGE = "en-GB"` is a module constant with no `parent.toml`
key; only Piper `en_GB-cori` ships. No Welsh (06 §7.4 #31 — and the 6-point fall
among 5–15s is *this* age group), no bilingual read-aloud, no locale switch. The
early-years teacher's post (#3) shows the machine is not even in en-GB yet.
Andika was chosen partly for Polish/Romanian/Welsh diacritics; that investment
is unused. **For v0.2, not v0.1:** `voice`/`language` keys in `parent.toml`,
espeak-ng Welsh first, and the bilingual mode (English UI, home-language
read-aloud on the Ear) that 06 §9 Q5 flags as unmeasured.

### m1 — MINOR: band buttons are 17.2 mm wide, just under the floor

AT-SPI extents: band buttons are **69 × 77 px** at 102 dpi = **17.2 × 19.2 mm**.
`metrics.min_target` computes 72 px correctly, but `theme.css`'s
`.band button { margin: 0 4px }` is subtracted afterwards, so the hit area lands
4% under `MIN_TARGET_MM`. Budget the margin in `band_target`, or move the gap to
the container's `spacing`. (The gate at 13.7 mm is a deliberate adult target.)

### m2–m4 — MINOR, briefly

- **The band's identity swap.** `set_offer_mode` replaces Undo and My Things
  with the ending choices *in place*. "Nothing moves" is the right instinct, but
  a control that changes meaning without moving is harder for a child navigating
  by position than one that appears elsewhere. A child-test question, not a code
  change.
- **Eight choices on S1b.** SYNTHESIS B2 says ≤ 5 for choice screens; spec 7b's
  6–9 is a later ruling and the conflict is unrecorded. Eight is a lot for a
  child with weak visual filtering at the start of a session.
- **The grown-up sheet.** 12 pt Atkinson, no scaling control, no live-region
  announcement on the PIN display, wrong-PIN feedback text-only. Fine for most
  parents; nothing for a partially sighted or dyslexic one. The parent panel
  proper should not inherit this.

---

## 4. The five things to fix before a SEND child tries it

1. **Make everything keyboard-reachable, including across the two toplevels, and
   give the gate a real key-hold.** (B1) Without this, switch and keyboard users
   cannot use the product, and a disabled parent cannot open the parent sheet.
2. **Add a caption strip for every spoken line, and a picture for every
   spoken-only message — starting with put-away.** (B2) No deaf child should
   lose a drawing because the instruction was audio.
3. **Ship `calm = true`: reduced motion honoured, earcon attacks ≥ 60 ms, a
   sound-off switch, frozen grid.** (B3) This is the single switch that serves
   autistic, ADHD, sensory-defensive and anxious children at once.
4. **Fix the band's contrast — focus ring, sun, warm sun, ghost outline — and
   make the Sleeping screen actually dim.** (M1, M4) All are token-level or
   one-line changes with tests already in place to hold them.
5. **Draw ten depictive activity icons and add a per-profile shape badge.**
   (M2, M3) The tile picture is the only channel a pre-reader with low vision,
   CVD or no English has, and colour alone cannot say whose computer this is.

---

## 5. Three questions

1. **Is the pointer the assumed input, or the default one?** Hover dwell,
   press-to-fire, the 3 s hold, the sun tap and the sleeping-surface gesture are
   all mouse designs. If a SEND school or a switch user is in scope, that is an
   architectural decision to take now — one focus/scan model across both
   toplevels — not a v0.2 retrofit. If it is out of scope, say so in AGENTS.md
   §3 so nobody claims otherwise.
2. **What is the honest accessibility promise?** 06 §4.5 argues correctly that
   read-aloud beats Orca for a pre-reader. But the AT-SPI tree is good enough
   that Orca would half-work, and half-working is the worst state. Do we claim
   AT support, decline it explicitly, or test it once and publish the result?
3. **Who is the second child?** The safety reviewer (#18) shows profiles are
   cosmetic; I show colour-as-identity fails under CVD. If multi-child is real,
   identity needs a non-colour carrier and the Journal needs separation — both
   cheaper now than after a hundred drawings exist.
