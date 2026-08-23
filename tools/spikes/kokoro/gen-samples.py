#!/usr/bin/env python3
"""Render the shell's ten real lines with every British Kokoro voice.

Deliberately the same ten lines, the same sentence pause and the same
"slightly below default" pace as output/tts-samples/README.md, so the Kokoro
clips can be A/B-ed against the Piper ones without a confound.

Piper's speaking-rate knob is `length_scale` (bigger = slower) and Kokoro's is
`speed` (smaller = slower), so speech-dispatcher rate -20 is length_scale 1.10
there and speed 0.91 here.

Runs inside tools/spikes/kokoro/Containerfile. Nothing is installed on the host
and nothing here goes into the image.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import wave

import numpy as np
import onnxruntime as rt
from kokoro_onnx import Kokoro
from kokoro_onnx.config import EspeakConfig

LINES = [
    "Who's here?",
    "Draw",
    "Potato faces",
    "What's next after?",
    "The sun is going down. Finish this one, or one last little thing?",
    "Let's keep that - press the tick",
    "Tell me about it",
    "You drew two pictures.",
    "Ready to go outside?",
    "All done. Time to rest.",
]

VOICES = [
    "bf_emma",
    "bf_isabella",
    "bf_alice",
    "bf_lily",
    "bm_george",
    "bm_lewis",
    "bm_daniel",
    "bm_fable",
]

SPOKEN_NAME = {
    "bf_emma": "Emma.",
    "bf_isabella": "Isabella.",
    "bf_alice": "Alice.",
    "bf_lily": "Lily.",
    "bm_george": "George.",
    "bm_lewis": "Lewis.",
    "bm_daniel": "Daniel.",
    "bm_fable": "Fable.",
}


def write_wav(path: str, audio: np.ndarray, rate: int) -> float:
    pcm = np.clip(audio, -1.0, 1.0)
    pcm = (pcm * 32767.0).astype("<i2")
    with wave.open(path, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(pcm.tobytes())
    return len(pcm) / rate


def f0_stats(audio: np.ndarray, rate: int) -> tuple[float, float]:
    """Mean and sd of the fundamental, by autocorrelation.

    The same crude estimator the Piper sample README used, kept identical so
    the two tables are comparable. A larger sd means more melodic range; it is
    not a judgement of whether the voice is pleasant.
    """
    win = int(0.04 * rate)
    hop = int(0.01 * rate)
    lo, hi = int(rate / 400), int(rate / 70)
    values = []
    for start in range(0, max(0, len(audio) - win), hop):
        frame = audio[start : start + win].astype(np.float64)
        frame = frame - frame.mean()
        energy = np.sqrt((frame**2).mean())
        if energy < 0.02:
            continue
        corr = np.correlate(frame, frame, mode="full")[win - 1 :]
        if corr[0] <= 0:
            continue
        segment = corr[lo:hi]
        if not len(segment):
            continue
        peak = int(np.argmax(segment)) + lo
        if corr[peak] / corr[0] < 0.3:
            continue
        values.append(rate / peak)
    if not values:
        return 0.0, 0.0
    arr = np.array(values)
    return float(arr.mean()), float(arr.std())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--voices-bin", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--lang", default="en-gb")
    parser.add_argument("--speed", type=float, default=0.91)
    parser.add_argument("--sentence-pause", type=float, default=0.25)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--espeak-lib", default=None)
    parser.add_argument("--espeak-data", default=None)
    args = parser.parse_args()

    opts = rt.SessionOptions()
    opts.log_severity_level = 3
    opts.intra_op_num_threads = args.threads
    opts.inter_op_num_threads = 1
    sess = rt.InferenceSession(args.model, opts, providers=["CPUExecutionProvider"])

    espeak = None
    if args.espeak_lib or args.espeak_data:
        espeak = EspeakConfig(lib_path=args.espeak_lib, data_path=args.espeak_data)
    kokoro = Kokoro.from_session(sess, args.voices_bin, espeak_config=espeak)

    report: dict = {}
    combined: list[np.ndarray] = []
    rate = 24000

    for voice in VOICES:
        print(f"==> {voice}", flush=True)
        directory = os.path.join(args.out, voice)
        os.makedirs(directory, exist_ok=True)
        total = 0.0
        line5: np.ndarray | None = None

        for index, line in enumerate(LINES, 1):
            audio, rate = kokoro.create(
                line,
                voice=voice,
                speed=args.speed,
                lang=args.lang,
                sentence_pause=args.sentence_pause,
            )
            total += write_wav(os.path.join(directory, f"{index:02d}.wav"), audio, rate)
            if index == 5:
                line5 = audio

        name_audio, _ = kokoro.create(
            SPOKEN_NAME[voice], voice=voice, speed=args.speed, lang=args.lang
        )
        write_wav(os.path.join(directory, "00-name.wav"), name_audio, rate)

        mean, sd = f0_stats(line5, rate)
        report[voice] = {
            "total_seconds": round(total, 2),
            "line5_seconds": round(len(line5) / rate, 2),
            "samplerate": rate,
            "f0_mean_hz": round(mean, 1),
            "f0_sd_hz": round(sd, 1),
        }
        print(f"    {report[voice]}", flush=True)

        gap = np.zeros(int(0.6 * rate), dtype=np.float32)
        combined += [name_audio, gap, line5, gap]

    write_wav(
        os.path.join(args.out, "all-kokoro-line5.wav"),
        np.concatenate(combined),
        rate,
    )
    with open(os.path.join(args.out, "report.json"), "w") as handle:
        json.dump(report, handle, indent=1)
    print("DONE", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
