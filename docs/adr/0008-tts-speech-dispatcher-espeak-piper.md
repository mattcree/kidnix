# ADR-0008: Read-aloud via speech-dispatcher; espeak-ng guaranteed, Piper as the quality voice

- Status: accepted
- Date: 2026-08-22

## Context

Read-aloud is the primary label layer for pre-readers (*01 #14–16, 06 §d,
08 §3.6*). *07 §2.4* found: Piper (rhasspy) archived Oct 2025 →
`OHF-Voice/piper1-gpl` (GPL-3.0, thin maintenance); no Fedora 44 RPM; the
native speech-dispatcher Piper module is master-only; `en_GB-cori-high` is
the only public-domain high-tier en_GB voice. *03* warns that voice-model
licensing is the likeliest real legal trap (XTTS/CPML, F5-TTS/CC-BY-NC).
speech-dispatcher 0.12.1 + espeak-ng are packaged and work today.

## Decision

- The shell talks to **speech-dispatcher** (python3-speechd). Utterance
  policy: new cancels old; one "Ear" control repeats the last utterance.
- **espeak-ng en-GB** is installed and is the guaranteed fallback voice.
- **Piper `en_GB-cori-high`** is the intended default child voice, served by
  a resident local process behind the `sd_generic` module, enabled by a flag
  once the spike proves it end-to-end (rate slightly below default).
- Every voice model and its licence go in `docs/LICENSES.md`; no
  non-commercial or CPML-licensed models are shipped.
- No speech *input* (ADR-0009).

## Consequences

- A kid session is never mute even if Piper is missing.
- Spike done 2026-08-22 (`docs/spikes/tts.md`): vendored MIT piper binary +
  `en_GB-cori-high` (default) and `cori-medium` (switch in /etc/kidnix/tts.env),
  resident per-user server behind sd_generic as DefaultModule; 96–260 ms warm
  latency, ~165 MB RSS, +192 MiB image. Open: a human must listen and choose
  high vs medium; real-hardware audio unverified.
