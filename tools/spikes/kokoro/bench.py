#!/usr/bin/env python3
"""Measure Kokoro-82M ONNX on a CPU budget that stands in for the T480.

Run inside the spike container (tools/spikes/kokoro/Containerfile) under
`taskset -c 0-3` so onnxruntime sees four cores, the same count as the
reference ThinkPad. Nothing here is installed into the kidnix image.

Reports, per model variant:
  * session creation (the cold model load a resident server pays once)
  * RSS after load and after the first utterance
  * phonemisation time and inference time per utterance, separately, because
    only the second scales with sentence length
  * real-time factor against the audio actually produced
"""

from __future__ import annotations

import argparse
import json
import os
import resource
import sys
import time

import numpy as np
import onnxruntime as rt
from kokoro_onnx import Kokoro
from kokoro_onnx.config import EspeakConfig

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


def rss_mb() -> float:
    with open("/proc/self/status") as handle:
        for line in handle:
            if line.startswith("VmRSS:"):
                return int(line.split()[1]) / 1024
    return 0.0


def session(model_path: str, threads: int, arena: bool = True) -> rt.InferenceSession:
    opts = rt.SessionOptions()
    # fp16 graphs have no CPU kernel for several nodes and log a warning per
    # node at load; 3 = error and above.
    opts.log_severity_level = 3
    opts.intra_op_num_threads = threads
    opts.inter_op_num_threads = 1
    opts.execution_mode = rt.ExecutionMode.ORT_SEQUENTIAL
    opts.graph_optimization_level = rt.GraphOptimizationLevel.ORT_ENABLE_ALL
    # The CPU arena never returns memory to the allocator, so a long-lived
    # server keeps whatever the longest utterance needed. --no-arena trades
    # some speed for a resident set that tracks the model rather than the peak.
    opts.enable_cpu_mem_arena = arena
    return rt.InferenceSession(model_path, opts, providers=["CPUExecutionProvider"])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", nargs="+", required=True)
    parser.add_argument("--voices", required=True)
    parser.add_argument("--voice", default="bf_emma")
    parser.add_argument("--lang", default="en-gb")
    parser.add_argument("--speed", type=float, default=1.0)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--espeak-lib", default=None)
    parser.add_argument("--espeak-data", default=None)
    parser.add_argument("--json-out", default=None)
    parser.add_argument("--no-arena", action="store_true")
    args = parser.parse_args()

    espeak = None
    if args.espeak_lib or args.espeak_data:
        espeak = EspeakConfig(lib_path=args.espeak_lib, data_path=args.espeak_data)

    report: dict = {
        "threads": args.threads,
        "affinity": sorted(os.sched_getaffinity(0)),
        "onnxruntime": rt.__version__,
        "numpy": np.__version__,
        "voice": args.voice,
        "cpu_mem_arena": not args.no_arena,
        "speed": args.speed,
        "models": {},
    }

    for model_path in args.models:
        name = os.path.basename(model_path)
        print(f"\n=== {name} ({os.path.getsize(model_path) / 1e6:.1f} MB)", flush=True)
        base_rss = rss_mb()

        t0 = time.perf_counter()
        sess = session(model_path, args.threads, arena=not args.no_arena)
        load_s = time.perf_counter() - t0
        kokoro = Kokoro.from_session(sess, args.voices, espeak_config=espeak)
        ready_s = time.perf_counter() - t0
        loaded_rss = rss_mb()
        print(
            f"  session load {load_s * 1000:.0f} ms, ready {ready_s * 1000:.0f} ms, "
            f"RSS {loaded_rss:.0f} MB (+{loaded_rss - base_rss:.0f})",
            flush=True,
        )

        entry: dict = {
            "bytes": os.path.getsize(model_path),
            "session_load_ms": round(load_s * 1000, 1),
            "ready_ms": round(ready_s * 1000, 1),
            "rss_after_load_mb": round(loaded_rss, 1),
            "utterances": {},
        }

        for label, text in TEXTS:
            phon_ms: list[float] = []
            infer_ms: list[float] = []
            audio_s = 0.0
            for _ in range(args.repeats):
                t = time.perf_counter()
                phonemes = kokoro.tokenizer.phonemize(text, args.lang)
                phon_ms.append((time.perf_counter() - t) * 1000)

                t = time.perf_counter()
                audio, sr = kokoro.create(
                    phonemes,
                    voice=args.voice,
                    speed=args.speed,
                    lang=args.lang,
                    is_phonemes=True,
                )
                infer_ms.append((time.perf_counter() - t) * 1000)
                audio_s = len(audio) / sr

            total = [p + i for p, i in zip(phon_ms, infer_ms)]
            warm = sorted(total[1:]) if len(total) > 1 else total
            # This host is shared with other work, so the *minimum* warm run is
            # the honest estimate of an uncontended latency; the median is kept
            # so the spread is visible.
            best, median = warm[0], warm[len(warm) // 2]
            entry["utterances"][label] = {
                "chars": len(text),
                "phonemes": len(phonemes),
                "audio_s": round(audio_s, 3),
                "cold_total_ms": round(total[0], 1),
                "warm_total_ms": [round(v, 1) for v in total[1:]],
                "warm_min_ms": round(best, 1),
                "warm_median_ms": round(median, 1),
                "phonemize_min_ms": round(min(phon_ms), 1),
                "infer_min_ms": round(min(infer_ms), 1),
                "rtf_min": round(best / 1000 / audio_s, 3) if audio_s else None,
                "rtf_median": round(median / 1000 / audio_s, 3) if audio_s else None,
            }
            print(
                f"  {label:9s} {len(text):3d} chars -> {audio_s:5.2f}s audio | "
                f"cold {total[0]:7.1f} ms | warm min {best:7.1f} / median "
                f"{median:7.1f} ms (phon {min(phon_ms):.1f} + infer "
                f"{min(infer_ms):.1f}) | RTF {entry['utterances'][label]['rtf_min']}"
                f" / {entry['utterances'][label]['rtf_median']}",
                flush=True,
            )

        entry["rss_after_synth_mb"] = round(rss_mb(), 1)
        entry["maxrss_mb"] = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)
        print(
            f"  RSS after synthesis {entry['rss_after_synth_mb']:.0f} MB "
            f"(process max {entry['maxrss_mb']:.0f} MB)",
            flush=True,
        )
        report["models"][name] = entry
        del kokoro, sess

    if args.json_out:
        with open(args.json_out, "w") as handle:
            json.dump(report, handle, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
