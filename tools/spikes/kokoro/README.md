# Kokoro-82M spike harness

Everything here is a **spike artefact**. Nothing in this directory is installed
into the kidnix image, referenced by `build_files/`, or run by CI. The
conclusions it produced are in `docs/spikes/tts-kokoro.md`; the audio it
produced is in `output/tts-samples/kokoro/`.

| File | What it does |
|---|---|
| `Containerfile` | the throwaway evaluation image: Fedora 44, `python3.13`, Fedora's `espeak-ng`, `kokoro-onnx` 0.6.1 in a venv |
| `fetch.sh` | downloads and checksums the model artefacts — both the `kokoro-onnx` GitHub release assets and the Apache-2.0-labelled HF ones `docs/spikes/tts-kokoro.md` §7 recommends |
| `bench.py` | cold load, RSS, phonemisation vs inference time, and RTF for one or more ONNX variants |
| `piper-compare.py` | the same three utterances through the **image's own** vendored `piper`, so the Kokoro/Piper ratio is measured rather than inferred across two different spikes |
| `gen-samples.py` | the ten shell lines in all eight British voices, plus `all-kokoro-line5.wav` |
| `kidnix-kokorod-proto` | a resident server on the `kidnix-piperd` socket pattern that needs **neither `kokoro-onnx` nor `phonemizer`** — the licence-clean route of §4.2 |

## Reproducing

```bash
SPIKE=/var/tmp/kokoro                 # ~630 MB of models, do not put it in the repo
podman build -t kokoro-spike -f tools/spikes/kokoro/Containerfile tools/spikes/kokoro
tools/spikes/kokoro/fetch.sh "$SPIKE"

# latency / memory, four cores to stand in for the T480
podman run --rm -v "$SPIKE":/models:z -v "$PWD/tools/spikes/kokoro":/t:z kokoro-spike \
  taskset -c 0-3 /venv/bin/python /t/bench.py \
  --models /models/kokoro-v1.0.onnx --voices /models/voices-v1.0.bin --repeats 9

# the same three utterances through the shipping Piper
podman run --rm -v "$PWD/output/voice-cache":/voices:z \
  -v "$PWD/tools/spikes/kokoro":/t:z localhost/kidnix:latest \
  taskset -c 0-3 /usr/bin/python3 /t/piper-compare.py --model /voices/en_GB-cori-high.onnx

# the listening samples
podman run --rm -v "$SPIKE":/models:z -v "$PWD/tools/spikes/kokoro":/t:z \
  -v "$PWD/output/tts-samples/kokoro":/out:z kokoro-spike \
  /venv/bin/python /t/gen-samples.py --model /models/kokoro-v1.0.onnx \
  --voices-bin /models/voices-v1.0.bin --out /out \
  --espeak-lib /usr/lib64/libespeak-ng.so.1 --espeak-data /usr/share/espeak-ng-data
```

The prototype server runs in the **real** image, which is the point of it —
vendored onnxruntime and numpy wheels on `PYTHONPATH`, Fedora's `espeak-ng`,
and nothing else:

```bash
podman run --rm -v "$SPIKE"/vendor:/vendor:z registry.fedoraproject.org/fedora:44 \
  sh -c 'dnf -y -q install python3-pip &&
         pip install -q --no-deps --target /vendor onnxruntime==1.29.0 numpy==2.4.6'

podman run --rm -e PYTHONPATH=/vendor -e KIDNIX_KOKORO_ARENA=0 \
  -v "$SPIKE":/models:z -v "$SPIKE"/vendor:/vendor:z \
  -v "$PWD/tools/spikes/kokoro":/t:z localhost/kidnix:latest \
  taskset -c 0-3 /usr/bin/python3 /t/kidnix-kokorod-proto \
  --model /models/hf/model.onnx --voices /models/hf/bf_emma.bin \
  --vocab /models/hf/config.json --voice bf_emma --outdir /tmp \
  --say "Draw" "The sun is going down. Finish this one, or one last little thing?"
```
