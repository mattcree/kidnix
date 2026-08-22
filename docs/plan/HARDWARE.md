# Target hardware

Decided 2026-08-22 with Matt; evidence in `docs/research/06 §2–3`.

## Reference device: refurbished ThinkPad convertible (touch + real keyboard)

- **First choice:** ThinkPad **X13 Yoga** (Gen 1–4) or **X1 Yoga**; ~£250–400
  refurbished. 360° hinge (tent mode for touch-only play, laptop mode for
  keyboard activities), 13", touch, stylus (secondary only), spill-resistant
  keyboard, LVFS firmware, Lenovo-published Linux guide for X13 Yoga Gen 4.
- **Budget ladder (Matt wants the cheaper end, 2026-08-22; prices are
  approximate UK refurb, unverified — web budget exhausted):**
  1. **ThinkPad Yoga 11e (Gen 5/6)** ~£80–150 — the *schools* model:
     rubber bumpers, reinforced ports/hinge, spill-resistant, 11.6" touch,
     360°. Celeron/Pentium-class, often 4 GB soldered + eMMC → insist on an
     8 GB / SSD unit if possible. Slow but GNOME kiosk + GCompris/Tux Paint
     are fine. Physically the best fit for a 5-year-old.
  2. **L380 Yoga / L390 Yoga** ~£120–220 — 13.3" FHD IPS touch, 8th-gen
     i3/i5, RAM upgradeable, NVMe, pen garage. **Best value "proper laptop"**
     — the recommended sweet spot.
  3. **X380 Yoga** ~£150–250 — same generation, lighter/better build.
  4. X390 Yoga / L13 Yoga Gen 1–2 ~£180–280; X13 Yoga ~£250–400.
  Buying checklist: 8 GB RAM, SSD not eMMC, FHD IPS where offered, touch
  digitizer and hinge tested, battery health, charger included; all are
  Intel-integrated graphics and well supported by Fedora/GNOME.
- Floor 4 GB / 64 GB; recommended 8 GB / 128 GB.
- Stylus is *not* a primary input (06: kindergarten stylus < pencil and
  keyboard); handwriting stays on paper.

## Consequences for kidnix (to do)

- [ ] Kid session: disable 3/4-finger and edge swipes; touch targets ≥ 18 mm
      (already), input on press (already), no multi-touch.
- [ ] **Lock screen rotation** in the kid session (iio-sensor-proxy /
      mutter orientation lock) — the UI must not spin when the laptop tips.
- [ ] Tablet-mode switch: in tent/tablet mode hide keyboard-only affordances;
      offer the on-screen keyboard (gnome-kiosk-a11y / gnome-shell OSK) only
      inside activities that need text.
- [ ] Hardware test matrix for this model: touch, rotation, sleep/lid,
      audio cap, webcam, wifi (parent only), printer, stylus in Tux Paint.
- [ ] Child test #1 on this device, in tent mode first.
