# Spike: is Kokoro-82M the natural voice Piper isn't?

**Status:** evaluated, measured end-to-end on this host and *inside the real
kidnix image*; **nothing installed, nothing changed in `build_files/`,
`system_files/` or the shell.** Artefacts: `tools/spikes/kokoro/` (scripts) and
`output/tts-samples/kokoro/` (8 voices × 10 lines + a 55 s comparison reel).

**Recommendation: NO-GO as a replacement for Piper on the reference ThinkPad —
but a conditional GO for a cheaper shape that gets Kokoro's voice onto the
strings a child actually hears, for ~12 MB of image and no runtime cost at
all.** §6 is the decision, §7 is the build sketch for either route.

The one-line reason: on four pinned cores Kokoro is **≈3× slower than
`cori-high` and ≈15× slower than `cori-medium` by real-time factor**, holds
**415 MB resident against Piper's 208 MB**, adds **≈460 MB to the image**, and
of its eight British voices upstream grades exactly **one** (`bf_emma`) above C.
None of that is fatal on its own. All of it together is, unless a human ear
says `bf_emma` is *decisively* better than `cori` — which is a question this
spike has deliberately set up (`output/tts-samples/kokoro/README.md`) and
cannot answer.

Read `docs/spikes/tts.md` first; this document assumes it, and reuses its
vocabulary (resident server, `sd_generic`, the 700 ms threshold).

---

## 1. What was actually tested

| | |
|---|---|
| Model | `hexgrad/Kokoro-82M` v1.0, 82 M params, StyleTTS 2 + ISTFTNet, Apache-2.0 |
| Runtime route | **ONNX** (`kokoro-onnx` 0.6.1, MIT) on onnxruntime 1.29.0, CPU only. The PyTorch route (`kokoro` + `misaki` + torch) was not measured: torch alone is >2 GB of image on top of everything below, which fails the constraint before it starts. |
| Variants | `kokoro-v1.0.onnx` fp32 (325.5 MB), `.fp16` (163.5 MB), `.int8` (114.1 MB) |
| Voices | all eight British: `bf_emma bf_isabella bf_alice bf_lily bm_george bm_lewis bm_daniel bm_fable` |
| G2P | **Fedora's own** `espeak-ng-1.52.0-3.fc44`, not the prebuilt copy the `espeakng-loader` wheel bundles (§4.2) |
| CPU budget | `taskset -c 0-3`, `intra_op_num_threads=4`, `inter_op=1`, sequential — four cores, to stand in for the T480's 4C/8T i5 |
| Where | a podman container on the dev host (`tools/spikes/kokoro/Containerfile`), plus the *real* `localhost/kidnix:latest` for §5.2 |

Everything below was measured on 2026-08-23. The dev host is a 2026 desktop and
is **shared with other work**, so every latency is reported as the *minimum* of
five to nine warm runs — the honest estimate of an uncontended figure — with the median
alongside so the spread is visible.

### 1.1 A correction to the brief

The brief assumed `kokoro-onnx` uses `misaki` and falls back to espeak-ng. It
does not. `kokoro-onnx` 0.6.1 depends on `espeakng-loader`, `numpy`,
`onnxruntime` and **`phonemizer`** — espeak-ng is its *only* G2P. `misaki` is
what the **PyTorch** `kokoro` package uses. This matters for §4: `misaki[en]`
would have dragged in `phonemizer-fork` (GPL-3.0), `spacy`,
`spacy-curated-transformers` and `num2words` (LGPL), and we never have to
consider it, because the route we would actually take never touches it.

---

## 2. Numbers

Three utterances, chosen to bracket what the shell says: a hover label, the
longest real sentence in the UI, and a three-sentence paragraph.

| | text |
|---|---|
| word | `Draw` |
| sentence | `The sun is going down. Finish this one, or one last little thing?` |
| paragraph | `You drew two pictures today. The first one has a big yellow sun in the corner and a house with a red door. Shall we show it to Mum before we tidy up?` |

### 2.1 The three Kokoro variants

`bf_emma`, `speed 1.0`, four pinned cores. Time is text-in to audio-out,
phonemisation included — and because the resident-server contract hands back a
**complete** WAV (as `kidnix-piperd` already does), *latency to first audio and
total synthesis time are the same number*. Phonemisation is never more than
0.5 ms of it; all of the rest is inference.

| | fp32 325.5 MB | fp16 163.5 MB | int8 114.1 MB |
|---|---|---|---|
| session load (cold) | **612 ms** | 828 ms | 569 ms |
| RSS after load | 434 MB | 499 MB | 227 MB |
| word (0.55 s audio) | **175 ms** | 346 ms | 966 ms |
| sentence (3.85 s audio) | **1090 ms** | 1431 ms | 5997 ms |
| paragraph (7.85 s audio) | **2118 ms** | 2705 ms | 11 429 ms |
| real-time factor | **0.27–0.32** | 0.34–0.80 | **1.46–1.75** |
| RSS after the paragraph | 766 MB | 791 MB | 585 MB |

**The quantised variants are worse, not better.** fp16 has no CPU kernel for
several nodes in the ISTFTNet decoder (onnxruntime logs one warning per node at
load and inserts casts), and dynamic int8 on a conv-heavy decoder is
**5.6× slower than fp32** — an RTF above 1.0 means it cannot even keep up with
the speech it is producing. **There is no small-and-fast Kokoro.** The 325 MB
fp32 graph is the only usable one, so the 460 MB image cost in §5.3 has no
cheaper tier to fall back to, the way `cori-high` has `cori-medium`.

### 2.2 Head to head with what we ship today

`docs/spikes/tts.md` §2.1 measured Piper *unpinned*, so its numbers and these
were not comparable. `tools/spikes/kokoro/piper-compare.py` re-runs the image's
own vendored `piper` on the identical `taskset -c 0-3`, same three texts, same
host, same afternoon.

| warm, four cores | Kokoro fp32 `bf_emma` | Piper `cori-high` | Piper `cori-medium` |
|---|---|---|---|
| word | 175 ms | **74 ms** | **18 ms** |
| sentence | 1090 ms | **577 ms** | **101 ms** |
| paragraph | 2118 ms | **1045 ms** | **186 ms** |
| real-time factor | 0.27–0.32 | 0.087–0.113 | 0.017–0.021 |
| resident (steady) | **415 MB** | 208 MB | 154 MB |
| model on disk | 325.5 MB | 114.2 MB | 63.5 MB |
| sample rate | 24 000 Hz | 22 050 Hz | 22 050 Hz |

Kokoro is **1.9–2.4× slower than `cori-high` per utterance** and **2.8–3.1×
slower by RTF** (it also says less per second, which is why the two ratios
differ). Against `cori-medium` — the tier a T480 would realistically run — it is
**10–11× slower per utterance, 15–16× by RTF**.

### 2.3 What that means on the actual laptop

`docs/spikes/tts.md` §2 divides dev-host throughput by 2–3 for the T480. Using
the same factor — **this is an estimate, not a measurement; nobody has run
Kokoro on a T480**:

| on a T480, warm | Kokoro fp32 | `cori-high` | `cori-medium` |
|---|---|---|---|
| hover label ("Draw") | **350–530 ms** | 150–220 ms | 36–54 ms |
| sentence | **2.2–3.3 s** | 1.2–1.7 s | 0.2–0.3 s |
| paragraph | **4.2–6.4 s** | 2.1–3.1 s | 0.4–0.6 s |
| cold model load at session start | 1.2–1.8 s | 0.5–0.8 s | 0.3–0.5 s |

The shell speaks after a 300 ms hover dwell. A 350–530 ms label puts first
sound **650–830 ms** after the pointer settles — at or past the 700 ms
threshold `docs/spikes/tts.md` §2.3 used to reject the one-shot CLI. And a
sentence at 2.2–3.3 s is not a threshold question, it is a different product:
the child asks, and three seconds later the computer answers.

Streaming would help the sentence and not the label. `kokoro-onnx` chunks at
sentence boundaries, so line 5 ("The sun is going down. / Finish this one…")
could start after its first clause — roughly halving the wait to ~1.5 s on a
T480. It cannot help the one-word case, which is the case the shell hits most.

### 2.4 Memory, and the arena

onnxruntime's CPU arena never returns memory, so a resident server keeps the
high-water mark of the longest thing it ever said. Measured with
`tools/spikes/kokoro/kidnix-kokorod-proto`, five utterances in a row:

| | arena on (default) | `enable_cpu_mem_arena = False` |
|---|---|---|
| after load | 423 MB | **412 MB** |
| after a 4.9 s sentence | 519 MB | 619 MB |
| after a 9.3 s paragraph | 635 MB | 923 MB |
| **back to a one-word label** | **635 MB — stays** | **413 MB — released** |
| latency cost | — | +2–4% |

So the honest resident figure for a shipping `kidnix-kokorod` is
**≈415 MB steady with a ~920 MB transient** while a long paragraph is in
flight, against Piper's flat 208 MB. On an 8 GB machine also running GNOME,
a GTK4 shell and a Flatpak activity, a ~920 MB spike is not free — it is
roughly a third of what is realistically available. `MemoryMax=` on the unit
would have to be ~1.2 GB, four times what `kidnix-piper.service` asks for.

---

## 3. How it sounds

Unanswered, and unanswerable from here. `output/tts-samples/kokoro/` has the
same ten shell lines in all eight British voices, at the same pace and sentence
pause as the Piper clips next door, plus **`all-kokoro-line5.wav`** (55 s, each
voice names itself then says line 5) to play back-to-back with the existing
`output/tts-samples/all-voices-line5.wav`.

Two measured things worth knowing before listening:

1. **Only `bf_emma` is graded above C** by upstream (B−, 10–100 h of training
   data). The other seven are C or D on 10–100 minutes. If Kokoro wins, it wins
   as *one voice*, not as a family — so the "pick a voice you like" story is
   thinner than the Piper table's, not richer.
2. **`bf_emma` has the flattest pitch contour of the eight** (f0 sd 23.8 Hz,
   against `bf_alice` 51.5 and `cori-high` 53.5). By the only objective
   "is it flat" number available, the best-trained British Kokoro voice is
   *less* melodic than the voice we ship today. That is not a verdict —
   naturalness is not pitch variance — but it is the opposite of what "more
   natural than Piper" would predict, and it is the first thing to check by ear.

Upstream also warns that Kokoro is weak below 10–20 tokens. The shell's most
frequent utterances are one and two words. Listen to clips 02 and 03 first.

---

## 4. Licensing

### 4.1 The weights are genuinely clean

| Artefact | Licence | Verified |
|---|---|---|
| `hexgrad/Kokoro-82M` model + **all 54 voices** | **Apache-2.0** | HF model card front-matter `license: apache-2.0`; the voices live in the same repo with no separate terms |
| `onnx-community/Kokoro-82M-v1.0-ONNX` (the ONNX export) | **Apache-2.0** | HF card front-matter |
| `kokoro-onnx` 0.6.1 | **MIT** | GitHub `thewh1teagle/kokoro-onnx` licence field |
| Fedora `espeak-ng-1.52.0-3.fc44` | GPL-3.0+, **already in the image**, used at arm's length | ADR-0008 already does this |

This is a real improvement on the Piper voice table, where three of ten en_GB
voices were unshippable (`See URL`, CC-BY-NC) and three more owed
attribution or share-alike. Kokoro's British eight are one licence, no
attribution, no share-alike.

Two attributions *are* owed for the model as a whole, and they are cheap — the
model card lists **Koniwa `tnc` (CC BY 3.0, <1 h)** and **SIWIS (CC BY 4.0,
<11 h)** as CC-BY audio in the v1.0 training set. Two lines in
`docs/LICENSES.md`.

### 4.2 The Python dependencies are not clean, and do not have to be

This is the part the brief asked about, and the answer is better than expected:

| Dependency | Licence | Verdict |
|---|---|---|
| `phonemizer` 3.4.0 (a hard dep of `kokoro-onnx`) | **GPL-3.0-or-later** | in-process import; would make `kidnix-kokorod` a GPL work |
| `phonemizer-fork` (via `misaki[en]`) | **GPL-3.0-or-later** | same |
| `espeakng-loader` 0.2.4 | **no licence metadata at all** — and it ships a *prebuilt* `libespeak-ng.so.1.52.0` plus 18 MB of `espeak-ng-data` | redistributing someone else's GPL binary with no corresponding source: exactly the trap `docs/spikes/tts.md` §1.2 already made `build_files/65-tts.sh` delete out of the Piper tarball |
| `misaki` | Apache-2.0 itself, but `misaki[en]` pulls `phonemizer-fork` + `num2words` (LGPL) + `spacy` | not needed; see §1.1 |
| `onnxruntime` 1.29.0 wheel, `numpy` | MIT / BSD-3 | fine |

**None of them is required at runtime.** Measured, in the real image
(`tools/spikes/kokoro/kidnix-kokorod-proto`): everything Kokoro needs is the
114-entry phoneme vocabulary (which `hexgrad/Kokoro-82M/config.json` carries in
2.3 KB, and which the `kokoro-onnx` release export also embeds in its own ONNX
metadata under `kokoro_config`), a `(510, 1, 256)` float32 style array per
voice, onnxruntime, numpy, and IPA. So the server shells out to **Fedora's
`espeak-ng(1)`**, exactly as ADR-0008's fallback voice already does.

That is only allowed if the phonemes are the same, and they are, exactly.
`espeak-ng -q --ipa -v en-gb` plus punctuation re-insertion, filtered to the
model vocabulary, against `phonemizer.phonemize(..., preserve_punctuation=True,
with_stress=True)` on the same libespeak-ng:

```
SAME  "Who's here?"
SAME  'Draw'
SAME  'Potato faces'
SAME  "What's next after?"
SAME  'The sun is going down. Finish this one, or one last little thing?'
SAME  "Let's keep that - press the tick"
SAME  'Tell me about it'
SAME  'You drew two pictures.'
SAME  'Ready to go outside?'
SAME  'All done. Time to rest.'
SAME  'You drew two pictures today. The first one has a big yellow sun ...'
11/11 identical
```

(`--ipa`, not `--ipa=1`: the `=1` form inserts `_` between phonemes, which is
not in the vocabulary. A shipping version needs the same
deterministic-synthesis assertion in `tests/image/` that `test_tts.sh` already
carries for Piper, so the day Fedora's espeak-ng moves its phoneme table the
build notices instead of a child hearing a wrong accent.)

**Net: a Kokoro read-aloud stack can be Apache-2.0 + MIT + BSD throughout, with
zero redistributed GPL binaries** — strictly cleaner than route (a) in
`docs/spikes/tts.md` §1.1, which would have been GPL-3.0 piper1-gpl.

### 4.3 The caveat that is not a licence question

The model card says, in as many words, that v1.0's training data includes:

> Synthetic audio generated by closed TTS models from large providers

with a footnote to the US Copyright Office's AI policy guidance, and a second
footnote clarifying "no synthetic audio from open TTS models or custom voice
clones". Circumstantially this is what it looks like: five of Kokoro's American
voice names — `af_alloy`, `af_nova`, `am_echo`, `am_onyx`, `bm_fable` — are the
names of OpenAI's original six TTS voices.

Nothing about that changes the Apache-2.0 grant, and the copyright argument
(machine output is not itself copyrightable) is the one the card is gesturing
at. But the *contract* argument is separate and unresolved: large TTS providers
generally forbid using their outputs to train competing models, and that is a
claim against hexgrad rather than against us. For a project that writes down
where every asset came from and expects to be redistributed, this belongs in
`docs/LICENSES.md` as a recorded caveat, not as a silence. It is also, honestly,
part of the answer to "why does Kokoro sound better than Piper".

`en_GB-cori-high` — public-domain LibriVox — has no equivalent question.

---

## 5. What integration would look like

### 5.1 `kidnix-kokorod`, on the existing pattern

The socket contract does not change. `tools/spikes/kokoro/kidnix-kokorod-proto`
speaks the same protocol as `/usr/libexec/kidnix-piperd` — one line of JSON in,
one complete RIFF/WAVE out, EOF on failure so `kidnix-piper-say` falls back to
espeak-ng — so switching engines is a change of server and of
`/etc/kidnix/tts.env`, not a rewrite of the speech-dispatcher wiring. The
`sd_generic` module, the `AddVoice` lines, the rate/volume mapping and the
`Multiply 100` lesson all carry over untouched.

Four real differences from `kidnix-piperd`:

1. **No child process, so no restart on rate change.** Kokoro takes `speed` as
   a graph *input*, not a command-line flag, so the `length_scale` quantisation
   and respawn logic in `kidnix-piperd` (its longest comment) simply deletes.
   `speed = 1 / length_scale`; the shell's rate −20 → `length_scale 1.10` →
   `speed 0.91`. Like Piper, Kokoro cannot change pitch.
2. **Start at session start, not on first utterance.** 1.2–1.8 s of model load
   on a T480 is too long to pay inside the first hover. `kidnix-piper.socket`
   already gets this right by being pulled in by `kidnix-shell.service`; the
   same wiring applies, and the idle-exit timer becomes more valuable, not
   less, because the thing being reclaimed is 415 MB rather than 160 MB.
3. **`enable_cpu_mem_arena = False`** (§2.4), or the server ratchets to its
   worst-case footprint and stays there for the session.
4. **A 510-phoneme window** (~400 characters). speech-dispatcher already chunks
   by sentence, and `kidnix-piperd`'s `MAX_TEXT = 4000` backstop would have to
   become a real splitter rather than a truncation.

### 5.2 Fedora packaging: measured, both routes

Against the actual `localhost/kidnix:latest`, `install_weak_deps=False`:

| Route | What it is | Installed |
|---|---|---|
| **RPM** — `dnf install python3-onnxruntime` | 20 packages: onnxruntime 14 MiB, **python3-sympy 84 MiB**, openblas-openmp 44 MiB, python3-numpy 42 MiB, flexiblas-netlib 16 MiB, … | **256 MiB** |
| **Vendored wheels** — `pip install --no-deps --target /usr/lib/kidnix/kokoro/py onnxruntime==1.29.0 numpy` | onnxruntime 66 MB + numpy 69 MB, self-contained, no RPM deps, no `python3-pip` left in the image | **134 MB** |

The RPM route confirms `docs/spikes/tts.md` §1.1's 256 MiB figure exactly, and
84 MiB of it is sympy, which onnxruntime's Python bindings import for symbolic
shape inference and which nothing else on the image wants. **Verified: the
onnxruntime wheel imports and runs inference with numpy as its only
dependency** — no sympy, no protobuf, no coloredlogs. So the vendored route is
half the size *and* smaller in surface area, and it is the same shape as the
vendored-piper decision already taken.

One caveat found on the way: `kokoro-onnx` 0.6.1's metadata caps itself at
`python_requires <3.14`, and Fedora 44 is Python 3.14. That cap is stale —
onnxruntime has published cp314 wheels since 1.29 — but it means
`pip install kokoro-onnx` fails on the image today. It does not matter for the
route in §4.2, which does not install `kokoro-onnx` at all.

**Verified inside `localhost/kidnix:latest`**, vendored wheels on `PYTHONPATH`,
Fedora's espeak-ng, four pinned cores, no `kokoro-onnx`, no `phonemizer`:

```
kidnix-kokorod: loaded model.onnx + bf_emma in 540 ms, RSS 435 MB
kidnix-kokorod: spoke   4 chars in  196 ms (0.75s audio, RTF 0.261)
kidnix-kokorod: spoke  65 chars in 1264 ms (4.88s audio, RTF 0.259)
kidnix-kokorod: spoke   4 chars in  193 ms (0.75s audio, RTF 0.258)
```

(One thing an implementer must handle: onnxruntime logs
`Failed to persist telemetry device ID` on a read-only `$HOME`. On Linux
onnxruntime's telemetry is a local UUID file and no network call — the egress
proof in `docs/spikes/egress-proof.md` should confirm that rather than trust
it — but the noise belongs behind `rt.disable_telemetry_events()` regardless.)

### 5.3 Image cost, all in

| | |
|---|---|
| `model.onnx` fp32 (no cheaper tier exists — §2.1) | **325.5 MB** |
| one voice, raw float32 `(510,1,256)` | **0.5 MB** |
| `config.json` (the 114-entry vocabulary) | 2.3 KB |
| vendored onnxruntime + numpy | **134 MB** |
| **Kokoro subtotal** | **≈460 MB** |
| Piper today, if kept as the fast/fallback tier | 200 MB |
| **both** | **≈660 MB** |

Kokoro-**only** (dropping Piper) is ≈460 MB against today's 200 MB, i.e.
**+260 MB**, and it costs the `cori-medium` escape hatch: there is no fast
Kokoro for a slow machine.

### 5.4 The hybrid, and the better idea

**"Piper for labels, Kokoro for sentences" is backwards.** Kokoro's deficit
grows with length — 175 ms for a word but 2118 ms for a paragraph — so routing
the long text to Kokoro routes the worst latency to the worst place. And a
child hearing two different voices in one session is a UX regression that no
licence table can offset.

The shape that *does* work follows from a fact about this product rather than
about the engine: **the shell's speech is a nearly closed vocabulary.** Tile
labels, band prompts, the resting sequence — these are fixed strings compiled
into `shell/kidnix_shell/`. They can be rendered **at image-build time**:

- 24 kHz 16-bit mono is 48 kB per second of audio (measured: the eight sample
  voices average ~1.05 MB for ~21 s of speech each).
- ~200 fixed strings averaging 1.2 s ≈ **11.5 MB** of WAV.
- Runtime cost: **zero** — no model, no onnxruntime, no 415 MB, no latency at
  all. The client plays a file.
- Dynamic text (counts, times, "You drew *two* pictures") still goes to
  espeak-ng or a retained Piper, which is a small minority of utterances and
  the only place the voice would change.

That gets `bf_emma` onto the strings a five-year-old hears fifty times a day,
for 11.5 MB and no runtime footprint, instead of 460 MB of image plus 415 MB of
RAM plus half a second of latency. It also sidesteps §2.3 entirely. Its costs
are real and should be stated: a build-time dependency on the model (not a
shipped one), a voice change on dynamic strings, and no way for a parent to
switch voices without a rebuild.

---

## 6. Go / no-go

**No-go on the resident-server route**, on these numbers:

| Claim | Kokoro | Today (`cori-high`) | Verdict |
|---|---|---|---|
| Hover label on a T480 | 350–530 ms → 650–830 ms after dwell | 150–220 ms | **fails** the 700 ms threshold |
| Sentence on a T480 | 2.2–3.3 s | 1.2–1.7 s | fails |
| Resident memory | 415 MB steady / 920 MB peak | 208 MB | costly on 8 GB |
| Image | +460 MB (+260 net) | 200 MB | costly |
| Fallback for a slow machine | none — int8/fp16 are *slower* | `cori-medium` | **fails** |
| Voice licensing | Apache-2.0, no attribution | public domain | **Kokoro wins** |
| Dependency licensing | clean, once §4.2's route is taken | clean | tie |
| Training-data provenance | recorded caveat (§4.3) | none | Piper wins |
| British voices above grade C | **1** | n/a | thin |
| Sounds better? | **unknown** | unknown | the only question that matters |

**Conditional go**, in this order:

1. **Matt listens** to `output/tts-samples/kokoro/all-kokoro-line5.wav` and then
   `output/tts-samples/all-voices-line5.wav`, and to clips 02/03 of `bf_emma`
   specifically (the short-label weak case).
2. If `bf_emma` is not *decisively* better than `cori-high`: **stop**. Nothing
   in §2 or §5 is worth paying for a marginal improvement.
3. If it is decisively better: implement **§7.1** — pre-render the fixed
   strings. 11.5 MB, no runtime cost, no ADR change (ADR-0008's engine story is
   untouched; this is an asset, not a synthesiser).
   **This step is now built** — `docs/spikes/tts-prerender.md`,
   `build_files/66-prerender-speech.sh`. It came in at **4.3 MB rather than
   11.5** (Ogg/Opus, not WAV) for **333 strings**, and step 1 above is still the
   open question: `output/tts-samples/prerender-bf_emma/` exists so it can be
   answered. If the answer is no, the stage is one file to delete.
4. Only if dynamic text then turns out to sound jarringly different does §7.2 —
   the resident `kidnix-kokorod` — become worth its 460 MB, and it would need a
   new ADR superseding ADR-0008's Piper default and an explicit ruling on the
   §4.3 provenance caveat.

---

## 7. Build sketches, for whoever implements this

Both assume the artefacts below. They come from the **HF repos with explicit
Apache-2.0 front-matter**, not from a third party's GitHub release assets, and
`onnx-community`'s per-voice `.bin` was verified byte-for-byte equal to the
corresponding array in `kokoro-onnx`'s 28 MB `voices-v1.0.bin` bundle.

| File | Source | Bytes | sha256 |
|---|---|---|---|
| `model.onnx` | `onnx-community/Kokoro-82M-v1.0-ONNX/resolve/main/onnx/model.onnx` | 325 532 232 | `8fbea51ea711f2af382e88c833d9e288c6dc82ce5e98421ea61c058ce21a34cb` |
| `bf_emma.bin` | `…/resolve/main/voices/bf_emma.bin` | 522 240 | `669fe0647f9dd04fcab92f1439a40eeb4c8b4ab1f82e4996fe3d918ce4a63b73` |
| `bm_george.bin` | `…/resolve/main/voices/bm_george.bin` | 522 240 | `c4b235a4c1f2cd3b939fed08b899ce9385638b763f7b73a59616c4fc9bd6c9bc` |
| `config.json` (the vocabulary) | `hexgrad/Kokoro-82M/resolve/main/config.json` | 2 351 | *(fetch and pin; 114-entry `vocab` key)* |

`onnx-community`'s export carries **no** `kokoro_config` metadata and no
`duration` output, so the vocabulary must come from `config.json`. Inputs are
`input_ids` (int64), `style` (float32 `[1,256]`), `speed` (float32 `[1]`);
output `waveform` at 24 000 Hz. Verified running in the kidnix image.

For reference, the alternative source — `thewh1teagle/kokoro-onnx` release
`model-files-v1.1` — is `kokoro-v1.0.onnx` 325 505 369 B
`beb0d1848dee9a49da392cc3df26958d46cfa35d321edf434f52949153f0df3a`,
`kokoro-v1.0.int8.onnx` 114 119 327 B
`ae315a79b623f244700e4afb9246c46a26066782e049ba174bf3ba433970ee9c`,
`kokoro-v1.0.fp16.onnx` 163 527 961 B
`f3a290d384fbb27966d462905c71a46cef9e5fd00516b40df32a0b4afe77ac96`,
`voices-v1.0.bin` 28 214 398 B
`bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d`.
Its fp32 export *does* embed the vocabulary, which is convenient and is a
different (unlabelled) artefact from the Apache-2.0 HF one — prefer the HF
repos and pin the vocabulary separately.

### 7.1 The recommended stage: pre-rendered strings (~12 MB)

`build_files/66-tts-kokoro-strings.sh`, running **after** `65-tts.sh`:

1. In a throwaway builder layer only: fetch the four artefacts above,
   `sha256sum -c`, `pip install --no-deps --target $tmp onnxruntime numpy`.
2. Extract the string list from the shell — a `shell/kidnix_shell/` module that
   enumerates every fixed `speak()` argument, so the list is generated from the
   code rather than maintained beside it, and a shell test fails if a literal
   is added without a rendered clip.
3. Render each with `bf_emma`, `speed 0.91`, `sentence_pause 0.25`, into
   `/usr/share/kidnix/voice-clips/<sha1-of-string>.wav` plus an index JSON.
4. Delete the model, the wheels and pip from the layer. **Nothing Kokoro ships
   except WAVs**, so there is no onnxruntime, no numpy and no 325 MB graph in
   the final image, and §4.3's provenance caveat applies to an asset the way
   the Piper voices' licences already do.
5. `shell/kidnix_shell/speech.py` gains a lookup: exact string hit in the index
   → play the file; miss → today's speech-dispatcher path unchanged. That is
   the *only* shell change, and the fallback is the current behaviour, so a
   missing clip is inaudible rather than fatal.
6. Record in `docs/LICENSES.md`: Kokoro-82M Apache-2.0, the Koniwa CC BY 3.0
   and SIWIS CC BY 4.0 attributions, and the §4.3 caveat.

Image delta ≈ **12 MB**. Runtime delta: **zero**.

### 7.2 The full route, if §6 step 4 is ever reached

`build_files/66-tts-kokoro.sh`:

1. Fetch + `sha256sum -c` the four artefacts into
   `/usr/share/kidnix/kokoro/` (326 MB).
2. `pip install --no-deps --target /usr/lib/kidnix/kokoro/py onnxruntime==1.29.0
   numpy==2.4.6` (134 MB), then remove `python3-pip` — the same
   don't-leave-pip-in-a-child's-OS rule as `65-tts.sh`.
3. `system_files/usr/libexec/kidnix-kokorod`, from
   `tools/spikes/kokoro/kidnix-kokorod-proto` plus what §5.1 lists: socket
   activation, idle exit, the 510-phoneme splitter,
   `enable_cpu_mem_arena=False`, `rt.disable_telemetry_events()`.
4. `system_files/etc/speech-dispatcher/modules/kidnix-kokoro.conf` — a copy of
   `kidnix-piper.conf` with the `AddVoice` names changed. **Keep
   `GenericRateMultiply 100`**; that bug is documented in the Piper conf and
   would silently return.
5. `kidnix-kokoro.{socket,service}` mirroring the Piper units, with
   `MemoryMax=1200M` (§2.4) and `ReadWritePaths=%t` (the `ProtectHome` lesson
   from `docs/spikes/tts.md` §6.1).
6. `/etc/kidnix/tts.env` gains `KIDNIX_TTS_ENGINE=kokoro|piper`, and
   `kidnix-piper-say` learns to try the Kokoro socket first, the Piper socket
   second, espeak-ng third — so a child is never mute, twice over.
7. `tests/image/test_tts_kokoro.sh`: the deterministic phoneme assertion from
   §4.2, a real synthesis, a socket round trip, and the fallback path.
8. A new ADR superseding ADR-0008's Piper default, ruling explicitly on §4.3.

---

## 8. What is NOT verified

1. **How any of it sounds.** Same gap as `docs/spikes/tts.md` §6 item 2, and the
   reason this spike cannot conclude on its own.
2. **T480 numbers.** §2.3 is a 2–3× division of dev-host figures, not a
   measurement. The division could be wrong in either direction; Kokoro is
   more memory-bandwidth-bound than Piper, and a 2018 laptop's memory is worse
   than its clock ratio suggests, so 2–3× may be optimistic.
3. **Long-session behaviour.** Five utterances, not a thousand. The arena
   finding in §2.4 came out of five; nobody has looked for creep.
4. **`misaki` G2P.** Everything here used espeak-ng, which is what
   `kokoro-onnx` does and what §4.2 requires. Upstream prefers `misaki`, so
   some of what an ear may dislike could be espeak's fault rather than
   Kokoro's — and we cannot use `misaki[en]` (§4.2), so that is a ceiling, not
   a to-do.
5. **ARM.** Not built, not run. onnxruntime publishes manylinux aarch64 wheels;
   nothing else is known.
6. **Whether §7.1's string enumeration is actually closed.** 148 speech call
   sites exist in `shell/`; how many pass a literal versus a formatted string
   was not counted. If the dynamic fraction is large, §7.1's advantage shrinks.
7. **onnxruntime's telemetry on Linux.** Believed to be a local UUID file and
   nothing more; it emitted a warning on a read-only `$HOME` in the image and
   was not put through `docs/spikes/egress-proof.md`.
