#!/usr/bin/env python3
"""The same three utterances through the *shipping* Piper, on the same budget.

docs/spikes/tts.md measured Piper without pinning, so its numbers and this
spike's are not directly comparable. This runs the image's own vendored piper
under the identical `taskset -c 0-3` so the Kokoro/Piper ratio is honest.

Run inside localhost/kidnix, with output/voice-cache mounted at /voices.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import wave

TEXTS = [
    ("word", "Draw"),
    ("sentence", "The sun is going down. Finish this one, or one last little thing?"),
    (
        "paragraph",
        "You drew two pictures today. The first one has a big yellow sun in "
        "the corner and a house with a red door. Shall we show it to Mum "
        "before we tidy up?",
    ),
]

PIPER = "/usr/lib/kidnix/piper/piper"
ESPEAK_DATA = "/usr/share/espeak-ng-data"


def rss_mb(pid: int) -> float:
    try:
        with open(f"/proc/{pid}/status") as handle:
            for line in handle:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) / 1024
    except OSError:
        pass
    return 0.0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--outdir", default="/tmp/piper-out")
    parser.add_argument("--length-scale", default="1.100")
    parser.add_argument("--repeats", type=int, default=9)
    parser.add_argument("--json-out", default=None)
    args = parser.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    t0 = time.perf_counter()
    proc = subprocess.Popen(
        [
            PIPER,
            "--model",
            args.model,
            "--espeak_data",
            ESPEAK_DATA,
            "--output_dir",
            args.outdir,
            "--length_scale",
            args.length_scale,
            "--sentence_silence",
            "0.25",
            "--quiet",
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
    )
    report: dict = {
        "model": os.path.basename(args.model),
        "bytes": os.path.getsize(args.model),
        "utterances": {},
    }

    for label, text in TEXTS:
        times: list[float] = []
        audio_s = 0.0
        for _ in range(args.repeats):
            start = time.perf_counter()
            proc.stdin.write(text.encode() + b"\n")
            proc.stdin.flush()
            path = proc.stdout.readline().decode().strip()
            times.append((time.perf_counter() - start) * 1000)
            with wave.open(path) as handle:
                audio_s = handle.getnframes() / handle.getframerate()
            os.unlink(path)
        warm = sorted(times[1:]) or times
        best, median = warm[0], warm[len(warm) // 2]
        report["utterances"][label] = {
            "chars": len(text),
            "audio_s": round(audio_s, 3),
            "first_ms": round(times[0], 1),
            "warm_min_ms": round(best, 1),
            "warm_median_ms": round(median, 1),
            "rtf_min": round(best / 1000 / audio_s, 3),
            "rtf_median": round(median / 1000 / audio_s, 3),
        }
        print(
            f"  {label:9s} -> {audio_s:5.2f}s audio | first {times[0]:7.1f} ms "
            f"(includes model load) | warm min {best:6.1f} / median {median:6.1f} ms "
            f"| RTF {report['utterances'][label]['rtf_min']}",
            flush=True,
        )

    report["piper_rss_mb"] = round(rss_mb(proc.pid), 1)
    report["spawn_to_last_wav_s"] = round(time.perf_counter() - t0, 2)
    print(f"  piper RSS {report['piper_rss_mb']:.0f} MB", flush=True)
    proc.stdin.close()
    proc.wait(timeout=10)

    if args.json_out:
        with open(args.json_out, "w") as handle:
            json.dump(report, handle, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
