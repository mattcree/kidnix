"""Kokoro-82M synthesis, build-time only, with no GPL Python in the loop.

This is the engine half of the pre-renderer. It exists so that
``docs/spikes/tts-kokoro.md`` §7.1 -- "pre-render the fixed strings, ship WAVs,
ship no model" -- can happen without the licence problem that makes the
*runtime* Kokoro route unattractive.

**The licence-clean path, in one paragraph.** ``kokoro-onnx`` (MIT) depends on
``phonemizer`` (GPL-3.0-or-later) and ``espeakng-loader`` (no licence metadata
at all, and it redistributes a prebuilt ``libespeak-ng.so`` plus 18 MB of
espeak-ng-data). Neither is needed. Kokoro wants exactly four things: the
114-entry phoneme vocabulary from ``hexgrad/Kokoro-82M/config.json``, a
``(510, 1, 256)`` float32 style array, onnxruntime, and IPA. So the IPA comes
out of **Fedora's own** ``espeak-ng(1)`` as a subprocess -- at arm's length,
exactly as ADR-0008's fallback voice already invokes it -- and the whole
pre-render stage is Apache-2.0 + MIT + BSD with no redistributed GPL binary.
``docs/spikes/tts-kokoro.md`` §4.2 checked the two phonemisations against each
other on eleven real shell strings and got 11/11 identical.

Nothing in this module ships. It runs inside the build container, writes Ogg
files, and is deleted with the rest of ``/tmp/build_files`` before the layer is
committed -- see ``build_files/66-prerender-speech.sh``.
"""

from __future__ import annotations

import io
import json
import os
import re
import subprocess
import wave
from dataclasses import dataclass
from pathlib import Path

#: Kokoro v1.0 emits 24 kHz mono float32.
SAMPLE_RATE = 24_000

#: The model's positional style table is 510 rows deep; a longer token sequence
#: has nowhere to index. Every string we render is a UI label or a single
#: sentence, so this is a guard rather than a splitter -- ``render_one`` refuses
#: rather than truncating, because a half-spoken label is worse than a
#: fallback to Piper.
MAX_PHONEMES = 510

#: espeak-ng drops punctuation in ``--ipa`` mode and Kokoro's vocabulary
#: contains ``.,!?;:`` and uses them for prosody. Phonemise between the marks
#: and put them back, which is what ``phonemizer``'s ``preserve_punctuation``
#: does and why the two agree.
_SPLIT = re.compile(r"([.,!?;:]+)")


class PhonemeError(RuntimeError):
    """espeak-ng gave us nothing usable for this string."""


@dataclass(frozen=True)
class Espeak:
    """IPA out of Fedora's ``espeak-ng``, punctuation preserved.

    ``--ipa``, **not** ``--ipa=1``: the ``=1`` form inserts ``_`` between
    phonemes, and ``_`` is not in Kokoro's vocabulary, so every token would be
    silently dropped and the model would speak the punctuation only.
    """

    binary: str = "espeak-ng"
    voice: str = "en-gb"

    def _run(self, text: str) -> str:
        if not text.strip():
            return ""
        result = subprocess.run(
            [self.binary, "-q", "--ipa", "-v", self.voice, "--", text],
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            raise PhonemeError(f"espeak-ng failed on {text!r}: {result.stderr.decode()[:200]}")
        return " ".join(result.stdout.decode("utf-8", "replace").split())

    def phonemize(self, text: str) -> str:
        out: list[str] = []
        for piece in _SPLIT.split(text.strip()):
            if not piece:
                continue
            if _SPLIT.fullmatch(piece):
                out.append(piece)
            else:
                phonemes = self._run(piece)
                if phonemes:
                    out.append(phonemes)
        return " ".join(out).replace(" ,", ",").replace(" .", ".").replace(" ?", "?")


class Kokoro:
    """One onnxruntime session and one voice's style table.

    Deliberately *not* a resident server: this is constructed once per worker
    process by ``render.py`` and thrown away when the build stage ends.
    """

    def __init__(
        self,
        model: str | Path,
        voice_style: str | Path,
        vocab: str | Path,
        threads: int = 4,
        espeak_voice: str = "en-gb",
    ) -> None:
        import numpy as np
        import onnxruntime as rt

        self._np = np
        options = rt.SessionOptions()
        options.log_severity_level = 3
        options.intra_op_num_threads = threads
        options.inter_op_num_threads = 1
        options.execution_mode = rt.ExecutionMode.ORT_SEQUENTIAL
        # onnxruntime's CPU arena never hands memory back. A build that renders
        # a few hundred short clips in a pool of workers would otherwise hold
        # every worker at the high-water mark of the longest clip in it.
        options.enable_cpu_mem_arena = False
        # A read-only $HOME in the build container makes onnxruntime warn about
        # a telemetry UUID file it cannot write. On Linux that file is the whole
        # of its telemetry -- no network call -- but the noise is not wanted in
        # a build log, and turning it off is one line.
        # The switch is on the MODULE, not the session, and it has to be thrown
        # before the session is built or the first call has already tried to
        # write the file. docs/spikes/tts-kokoro.md 5.2 found this warning in
        # the real image: on Linux onnxruntime's "telemetry" is a local UUID
        # file and no network call, but a read-only $HOME makes it complain once
        # per worker and a build log should not carry noise nobody can act on.
        disable = getattr(rt, "disable_telemetry_events", None)
        if disable is not None:
            disable()
        self.session = rt.InferenceSession(str(model), options, providers=["CPUExecutionProvider"])

        with open(vocab, encoding="utf-8") as handle:
            self.vocab: dict[str, int] = json.load(handle)["vocab"]

        # Two shapes are accepted, and they carry the same numbers:
        #   * onnx-community's per-voice `<voice>.bin` -- 510*256*4 raw float32
        #     bytes, and the artefact with an explicit Apache-2.0 licence on its
        #     HF repo. This is what the build stage fetches.
        #   * kokoro-onnx's `voices-v1.0.bin` -- a 28 MB npz of all 54 voices,
        #     used by tools/spikes/kokoro and accepted here so a developer can
        #     render from the cache they already have.
        path = Path(voice_style)
        if path.suffix == ".bin" and path.stat().st_size == 510 * 256 * 4:
            self.style = np.fromfile(path, dtype=np.float32).reshape(510, 1, 256)
        else:
            raise ValueError(
                f"{path} is not a 510x1x256 float32 style array; "
                "use load_bundled_voice() for voices-v1.0.bin"
            )
        self.espeak = Espeak(voice=espeak_voice)

    @staticmethod
    def extract_voice(bundle: str | Path, voice: str, out: str | Path) -> Path:
        """Pull one voice out of ``voices-v1.0.bin`` into a raw ``.bin``.

        Only used by the developer path (``--voices-bundle``); the image build
        fetches the per-voice file straight from the Apache-2.0 HF repo.
        """
        import numpy as np

        array = np.load(bundle)[voice].astype(np.float32).reshape(510, 1, 256)
        out = Path(out)
        out.write_bytes(array.tobytes())
        return out

    def tokens(self, text: str) -> list[int]:
        phonemes = self.espeak.phonemize(text)
        if not phonemes:
            raise PhonemeError(f"espeak-ng produced no phonemes for {text!r}")
        tokens = [self.vocab[p] for p in phonemes if p in self.vocab]
        if not tokens:
            raise PhonemeError(f"no phoneme of {phonemes!r} is in Kokoro's vocabulary")
        if len(tokens) > MAX_PHONEMES:
            raise PhonemeError(
                f"{text!r} is {len(tokens)} phonemes, over the model's {MAX_PHONEMES}-row "
                "style table; leave it to the runtime backend"
            )
        return tokens

    def synth(self, text: str, speed: float = 0.91) -> bytes:
        """One string in, one complete RIFF/WAVE out. 24 kHz, 16-bit, mono."""
        np = self._np
        tokens = self.tokens(text)
        style = self.style[len(tokens) - 1]
        outputs = self.session.run(
            None,
            {
                "input_ids": np.array([[0, *tokens, 0]], dtype=np.int64),
                "style": np.asarray(style, dtype=np.float32),
                "speed": np.array([speed], dtype=np.float32),
            },
        )
        audio = np.asarray(outputs[0]).ravel()
        if audio.size == 0:
            raise PhonemeError(f"the model returned no samples for {text!r}")
        pcm = (np.clip(audio, -1.0, 1.0) * 32767.0).astype("<i2")
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as handle:
            handle.setnchannels(1)
            handle.setsampwidth(2)
            handle.setframerate(SAMPLE_RATE)
            handle.writeframes(pcm.tobytes())
        return buffer.getvalue()


# --- Ogg/Opus ---------------------------------------------------------------
#
# WAV would work and would need no encoder at all, but 24 kHz 16-bit mono is
# 48 kB per second of speech: the catalogue below is ~5 minutes of audio, so WAV
# is ~14 MB and Opus at 48 kbps is ~1.8 MB. The encoder is GStreamer's `opusenc`
# -- already in the image, because `oggdemux ! opusdec` is what plays the clips
# back (shell/kidnix_shell/prerendered.py). No new package, at build or at run.

#: Mono speech at 24 kHz. 48 kbps is well above transparent for this material
#: and still an order of magnitude smaller than WAV; the budget is 20 MB and
#: this spends about a tenth of it, which leaves room for the vocabulary to grow.
OPUS_BITRATE = 48_000


def encode_opus(wav_bytes: bytes, destination: Path, bitrate: int = OPUS_BITRATE) -> Path:
    """WAV bytes to an Ogg/Opus file, atomically."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    source = destination.with_suffix(destination.suffix + ".wav.tmp")
    source.write_bytes(wav_bytes)
    try:
        result = subprocess.run(
            [
                "gst-launch-1.0",
                "-q",
                "filesrc",
                f"location={source}",
                "!",
                "wavparse",
                "!",
                "audioconvert",
                "!",
                "opusenc",
                f"bitrate={bitrate}",
                "!",
                "oggmux",
                "!",
                "filesink",
                f"location={temporary}",
            ],
            capture_output=True,
            check=False,
        )
        if result.returncode != 0 or not temporary.exists() or temporary.stat().st_size == 0:
            raise RuntimeError(
                f"gst-launch could not encode {destination.name}: "
                f"{result.stderr.decode('utf-8', 'replace')[:300]}"
            )
        temporary.replace(destination)
    finally:
        for leftover in (source, temporary):
            if leftover.exists():
                os.unlink(leftover)
    return destination
