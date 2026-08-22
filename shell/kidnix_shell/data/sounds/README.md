# Earcons

Spec §7a rules **four** sounds, not the six of 08-shell-ux-patterns §3.6, and
rules them *generated*:

| Event | Character | File |
|---|---|---|
| A child-facing control fired | one soft tick (A5) | `tap.wav` |
| Back / close | two notes falling (D5 → G4) | `back.wav` |
| Kept in the Journal | two notes rising (E5 → B5) | `keep.wav` |
| The session is over | low and slow (E4 → A3) | `sleep.wav` |

They are **not committed**. `kidnix_shell/sound.py` renders them from
`EARCONS` — sine tones with an exponential decay and 6 ms fades, 16-bit mono
44.1 kHz, peaking at 0.45 (≈ −14 LUFS by construction, not by meter) — either

* at image build time: `python -m kidnix_shell.sound [DIR]`, or
* on first run, into `$XDG_CACHE_HOME/kidnix/sounds`, because `/usr` is
  read-only on the image.

No binary blobs in git, nothing for `docs/LICENSES.md` to track, and the code
and the sound cannot drift apart. Playback is GStreamer `playbin`, built
lazily; anything missing (no GStreamer, no sink, no sound card in a VM) logs
once and the shell runs silent.

Rules that still apply: never more than one earcon per 250 ms, and earcons duck
under speech. There is no reward chime and there never will be
(AGENTS.md non-negotiable 1).
