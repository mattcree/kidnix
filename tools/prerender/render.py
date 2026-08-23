"""Render the shell's closed vocabulary to Ogg/Opus, once, at image build time.

    python3 -m prerender.render --model model.onnx --voice-style bf_emma.bin \
        --vocab config.json --out /usr/share/kidnix/speech/en_GB

``docs/spikes/tts-kokoro.md`` §6 said no to Kokoro as a *synthesiser* -- 460 MB
of image, 415 MB resident, and a hover label that lands past the 700 ms
threshold on a T480 -- and yes to Kokoro as an *asset*: the shell's speech is a
nearly closed vocabulary, so render it once and ship the audio. This is that
stage. What ships is a directory of Ogg files and one index; what does not ship
is the 325 MB graph, onnxruntime, numpy, or a single line of the code in this
directory.

Three things it does that a loop over ``kidnix-kokorod-proto`` would not:

* **It refuses rather than truncates.** A string past the model's 510-row style
  table is recorded as skipped and left to the runtime backend. Half a label in
  a good voice is worse than all of it in the ordinary one.
* **It is deterministic.** Same tree, same model, same files: the vocabulary is
  sorted, the filename is ``sha1`` of the exact UTF-8 text, and Kokoro has no
  sampling noise to seed (unlike Piper, which has ``--noise_scale``).
* **It fails the build.** A string that phonemises but will not synthesise is
  an error, not a warning, because the failure mode of a warning here is one
  tile that quietly changes voice and nobody notices for a month.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from prerender import vocabulary as vocab_module
from prerender.kokoro import SAMPLE_RATE, Kokoro, PhonemeError, encode_opus

#: The shell asks speech-dispatcher for rate -20, which
#: ``/etc/speech-dispatcher/modules/kidnix-piper.conf`` turns into piper's
#: ``length_scale 1.100``. Kokoro's ``speed`` is that reciprocal, so a clip is
#: paced exactly as the live voice is and a fallback mid-session is a change of
#: timbre and not of tempo.
DEFAULT_SPEED = round(1.0 / 1.10, 4)

#: ``bf_emma`` is the only British Kokoro voice upstream grades above C
#: (``docs/spikes/tts-kokoro.md`` §3). Overridable at build time with
#: ``KIDNIX_PRERENDER_VOICE`` so a rebuild can try another one without a patch.
DEFAULT_VOICE = "bf_emma"

#: Index schema. Bump when the shape changes; ``prerendered.py`` refuses an
#: index it does not understand rather than guessing.
INDEX_VERSION = 1

INDEX_NAME = "index.json"


def clip_name(text: str) -> str:
    """``sha1`` of the exact UTF-8 bytes. The index is what maps text to file."""
    return hashlib.sha1(text.encode("utf-8"), usedforsecurity=False).hexdigest()


# --- the worker --------------------------------------------------------------
#
# One onnxruntime session per process, built once in the initialiser rather than
# once per string: loading the graph is ~600 ms and there are a few hundred
# strings. The arena is off (kokoro.py), so a worker holds ~420 MB steady
# instead of ratcheting to the longest sentence it ever rendered -- which is
# what makes a pool of four fit in a CI runner at all.

_ENGINE: Kokoro | None = None
_SETTINGS: dict[str, object] = {}


def _init(model: str, style: str, vocab: str, threads: int, speed: float, out: str) -> None:
    global _ENGINE
    _ENGINE = Kokoro(model, style, vocab, threads=threads)
    _SETTINGS.update(speed=speed, out=out)


def _render_one(text: str) -> dict[str, object]:
    """Render one string. Returns a result record; never raises."""
    assert _ENGINE is not None
    started = time.perf_counter()
    try:
        wav = _ENGINE.synth(text, float(_SETTINGS["speed"]))
    except PhonemeError as exc:
        return {"text": text, "ok": False, "skip": True, "error": str(exc)}
    except Exception as exc:
        return {"text": text, "ok": False, "skip": False, "error": f"{type(exc).__name__}: {exc}"}
    synth_ms = (time.perf_counter() - started) * 1000.0
    frames = (len(wav) - 44) // 2
    destination = Path(str(_SETTINGS["out"])) / f"{clip_name(text)}.ogg"
    try:
        encode_opus(wav, destination)
    except Exception as exc:
        return {"text": text, "ok": False, "skip": False, "error": f"opus: {exc}"}
    return {
        "text": text,
        "ok": True,
        "file": destination.name,
        "ms": round(frames * 1000 / SAMPLE_RATE),
        "bytes": destination.stat().st_size,
        "synth_ms": round(synth_ms),
    }


# --- driver ------------------------------------------------------------------


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, help="Kokoro v1.0 model.onnx")
    parser.add_argument("--voice-style", required=True, help="510x1x256 float32 .bin")
    parser.add_argument("--vocab", required=True, help="config.json with the 114-entry vocab")
    parser.add_argument("--out", required=True, help="directory for the clips and index.json")
    parser.add_argument(
        "--voice-name", default=os.environ.get("KIDNIX_PRERENDER_VOICE", DEFAULT_VOICE)
    )
    parser.add_argument("--language", default="en_GB")
    parser.add_argument("--speed", type=float, default=DEFAULT_SPEED)
    parser.add_argument("--jobs", type=int, default=0, help="0 = pick from nproc")
    parser.add_argument("--threads", type=int, default=0, help="intra-op threads per worker")
    parser.add_argument(
        "--python-root",
        action="append",
        default=[],
        type=Path,
        help="a package to walk for gettext literals (repeatable)",
    )
    parser.add_argument("--pot", type=Path, default=None)
    parser.add_argument("--manifest-dir", action="append", default=[], type=Path, help="repeatable")
    parser.add_argument("--min-clips", type=int, default=1, help="fail below this many")
    parser.add_argument("--max-bytes", type=int, default=20 * 1024 * 1024)
    parser.add_argument(
        "--dry-run", action="store_true", help="enumerate and print, render nothing"
    )
    args = parser.parse_args(argv)

    vocabulary = vocab_module.collect(
        python_roots=list(args.python_root),
        pot=args.pot,
        manifest_dirs=list(args.manifest_dir),
    )
    texts = vocabulary.texts
    print(
        f"==> vocabulary: {len(texts)} strings to render, "
        f"{len(vocabulary.skipped)} left to the runtime backend"
    )
    for text, reason in sorted(vocabulary.skipped.items()):
        print(f"    skip ({reason}): {text[:70]!r}")

    if args.dry_run:
        for text in texts:
            print(f"    {clip_name(text)[:12]}  {text[:70]!r}")
        return 0

    if len(texts) < args.min_clips:
        print(
            f"ERROR: only {len(texts)} strings found, wanted at least {args.min_clips} -- "
            "the enumeration is broken, not the vocabulary",
            file=sys.stderr,
        )
        return 1

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    # A rebuild must not leave last build's clips behind: the index would still
    # be right, but the directory would grow a fossil every time a label
    # changed, and `test_prerender.sh` counts files against the index.
    for stale in out.glob("*.ogg"):
        stale.unlink()

    jobs = args.jobs or max(1, min(4, (os.cpu_count() or 2)))
    threads = args.threads or max(1, (os.cpu_count() or 4) // jobs)
    print(
        f"==> rendering with {args.voice_name} at speed {args.speed} "
        f"({jobs} worker(s) x {threads} thread(s))"
    )

    started = time.perf_counter()
    init_args = (
        str(args.model),
        str(args.voice_style),
        str(args.vocab),
        threads,
        args.speed,
        str(out),
    )
    if jobs == 1:
        _init(*init_args)
        results = [_render_one(text) for text in texts]
    else:
        context = multiprocessing.get_context("spawn")
        with context.Pool(jobs, initializer=_init, initargs=init_args) as pool:
            results = pool.map(_render_one, texts, chunksize=4)
    elapsed = time.perf_counter() - started

    clips: dict[str, dict[str, object]] = {}
    failures: list[dict[str, object]] = []
    skips: list[dict[str, object]] = []
    total_ms = 0
    for record in results:
        if record["ok"]:
            text = str(record["text"])
            clips[text] = {"file": record["file"], "ms": record["ms"]}
            total_ms += int(record["ms"])  # type: ignore[arg-type]
        elif record["skip"]:
            skips.append(record)
        else:
            failures.append(record)

    for record in skips:
        print(f"    skip (model): {str(record['text'])[:60]!r} -- {record['error']}")
    for record in failures:
        print(f"    FAIL: {str(record['text'])[:60]!r} -- {record['error']}", file=sys.stderr)

    if failures:
        print(
            f"ERROR: {len(failures)} string(s) could not be rendered. A build that ships a "
            "partial catalogue ships a session that changes voice at random.",
            file=sys.stderr,
        )
        return 1
    if len(clips) < args.min_clips:
        print(f"ERROR: {len(clips)} clips is below the floor of {args.min_clips}", file=sys.stderr)
        return 1

    index = {
        "version": INDEX_VERSION,
        "language": args.language,
        "voice": args.voice_name,
        "engine": "kokoro-82m-v1.0",
        "model_sha256": sha256_of(Path(args.model)),
        "speed": args.speed,
        "sample_rate": SAMPLE_RATE,
        # The one number prerendered.py gates on: a clip is paced for this
        # speech-dispatcher rate and no other. See shell/kidnix_shell/access.py.
        "speechd_rate": -20,
        "clips": clips,
    }
    index_path = out / INDEX_NAME
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=1, sort_keys=True) + "\n")

    audio_bytes = sum(path.stat().st_size for path in out.glob("*.ogg"))
    total = audio_bytes + index_path.stat().st_size
    print(
        f"==> {len(clips)} clips, {total_ms / 1000:.0f}s of speech, "
        f"{total / 1e6:.2f} MB on disk (index {index_path.stat().st_size / 1024:.0f} kB), "
        f"rendered in {elapsed:.0f}s"
    )
    if skips:
        print(f"    {len(skips)} string(s) left to the runtime backend (over the model's window)")
    if total > args.max_bytes:
        print(
            f"ERROR: {total / 1e6:.1f} MB is over the {args.max_bytes / 1e6:.0f} MB budget",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
