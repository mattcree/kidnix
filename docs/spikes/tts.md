# Spike: making read-aloud sound good (M2)

**Status:** implemented; green in `just tag=tts test-image` (66 assertions),
`just tag=tts lint-image` (`bootc container lint`, 13 checks), `just lint-shell`,
and **verified in a booted VM as the `kid` user** — `spd-say` through the
`kidnix-piper` module returns 0, and the shell's own `python3-speechd` path
speaks a tile label in **under 200 ms** (§4). What is **only structurally
verified** is the last hop, "and then a speaker moves": no machine in this loop
has an audio device, so the VM run writes into a PipeWire null sink. Nobody has
listened to the voice. See §6 before quoting §2 — **and §8 before quoting §2.4
or §4**, which a booted qcow2 VM has since corrected: speech-dispatcher's rate
never reached piper at all, so every measurement of speaking *pace* above
describes a code path the running image did not take.

**Owner of this milestone:** the Piper half of ADR-0008. The shell half
(`shell/kidnix_shell/speech.py`) needed **no changes at all** — see §5.

Everything below was measured against the actual image
(`localhost/kidnix:tts`, Fedora 44, `podman run` and a bcvk VM), not against
memory or the research docs. Where *docs/research/07 §2.4* was wrong, it says so.

---

## 1. What was decided, and what it cost

| | |
|---|---|
| Engine | `rhasspy/piper` **2023.11.14-2**, the archived standalone C++ release, vendored to `/usr/lib/kidnix/piper/` |
| Voice | **`en_GB-cori-high`** (default) and `en_GB-cori-medium` (low-CPU), both **public domain** |
| Plumbing | speech-dispatcher `sd_generic` module `kidnix-piper` → `/usr/libexec/kidnix-piper-say` → resident server `/usr/libexec/kidnix-piperd` over a UNIX socket |
| Fallback | espeak-ng, inside the client, so a dead server degrades the *voice* and never the *speech* |
| Image delta | **≈ 200 MB** (22 MB runtime + 178 MB of voices) |
| Warm latency | **96–260 ms** in a VM for real UI strings (high); ≈ 40 ms (medium) |
| Resident memory | **160 MB** (high) / **114 MB** (medium), plus 3.4 MB for the Python server |

### 1.1 Why the archived 2023 binary and not `pip install piper-tts`

Three routes were costed on 2026-08-22 against the real F44 image.

**(a) `pip install --prefix=/usr piper-tts`** — OHF-Voice/piper1-gpl 1.7.0,
released 2026-08-15, GPL-3.0-or-later. The wheel is better than *07 §2.4*
implies: it is `cp39-abi3`, so it works unmodified on Fedora 44's Python 3.14,
and it is only 34 MB. The problem is `onnxruntime`.

> **Correction to `docs/research/07 §2.4`.** That section says Fedora has the
> Piper stack "in F45/rawhide only". That is right for `python3-piper-tts` and
> **wrong for onnxruntime**: `python3-onnxruntime 1.22.2-2.fc44` is in Fedora
> 44 today (`dnf5 repoquery` against the image's own repos). It is just very
> expensive:
>
> | | packages | installed size |
> |---|---|---|
> | `dnf5 install python3-onnxruntime python3-pathvalidate` | 432 | **1 GiB** — pulls TeX Live and Ruby through weak deps |
> | …with `install_weak_deps=False` | 21 | **256 MiB** — sympy 84 MiB, openblas-openmp 44 MiB, numpy 42 MiB, onnxruntime 53 MiB |
>
> Plus `python3-pip`, which is not something to leave lying in a child's OS.
> Route (a) is therefore ≈ 400 MB of image for the same 200 ms of audio.

**(b) The 2023 standalone binary — chosen.** Self-contained C++: `piper` +
`libpiper_phonemize` + a bundled `libonnxruntime`. No RPMs, no Python, no
numpy, MIT throughout. Upstream's tarball is 52 MB; **the shipped tree is
22 MB** after the trim in §1.2.

**(c) Wait for Fedora 45.** Not a today answer, and it would still drag the
256 MiB dependency tree.

The honest downside of (b): it is a frozen 2023 artefact from an archived
repository. It will never get a security fix. The mitigations are that it is a
local, offline, single-purpose process that reads text from a socket owned by
one user, that it is confined by `kidnix-piper.service`'s sandbox, and that
switching to route (a) later is a one-file change to `build_files/65-tts.sh`
with the same speech-dispatcher wiring on top.

### 1.2 The trim, and why it is a licensing decision as much as a size one

Upstream's tarball also carries a prebuilt `libespeak-ng.so.1.52.0.1`, 19 MB of
`espeak-ng-data`, and `libtashkeel_model.ort` (10 MB, Arabic diacritics).

espeak-ng is **GPL-3.0-or-later**. Redistributing someone else's prebuilt GPL
binary means owing its corresponding source, and the piper release does not
ship any. So `build_files/65-tts.sh` deletes it and links against **Fedora's**
espeak-ng — which is already in the image, because ADR-0008 makes espeak-ng the
fallback voice anyway.

That is only allowed if the phonemisation is identical, and it is, exactly:

```
$ piper -m en_GB-cori-high.onnx --noise_scale 0 --noise_w 0 \
        --espeak_data /usr/share/espeak-ng-data      -f fedora.wav
$ piper -m en_GB-cori-high.onnx --noise_scale 0 --noise_w 0 \
        --espeak_data ./piper/espeak-ng-data         -f bundled.wav
662e83113a316c7fc408a7974d8903802200faf8505aad5550d437933d7077f4  fedora.wav
662e83113a316c7fc408a7974d8903802200faf8505aad5550d437933d7077f4  bundled.wav
```

Byte-identical (Fedora `espeak-ng-1.52.0-3.fc44`; upstream bundled 1.52.0.1).
`tests/image/test_tts.sh` re-runs a deterministic synthesis on every build, so
the day a Fedora espeak-ng moves its phoneme table, the test notices instead of
a child hearing a subtly wrong accent.

Net result: **the vendored tree is MIT-only**. Nothing GPL is redistributed
without source anywhere in the read-aloud stack.

---

## 2. Numbers

Measured on the dev host (2026 desktop, x86_64) inside `localhost/kidnix:tts`.
The reference child machine in *docs/plan/HARDWARE.md* is a ThinkPad T480, so
divide throughput by roughly 2–3 for the shipping case.

### 2.1 Model load and inference

| | `cori-medium` | `cori-high` |
|---|---|---|
| `.onnx` on disk | 63.5 MB | 114.2 MB |
| resident (`VmRSS` of the piper child) | **114 MB** | **160 MB** |
| model load (first utterance) | 247 ms | 381 ms |
| warm, short utterance (4 samples) | **24 / 33 / 40 / 52 ms** | **111 / 170 / 218 / 295 ms** |
| real-time factor | ~0.03 | **0.118–0.213** |

### 2.2 The whole chain, socket included

`printf … | kidnix-piper-say --rate -20 --stdout`, `cori-high`, over the real
UNIX socket, inside the image:

```
kidnix-piperd: spoke 33 chars in 464 ms      0.49 s wall   <- includes model load
kidnix-piperd: spoke 33 chars in 203 ms      0.24 s wall
kidnix-piperd: spoke 33 chars in 199 ms      0.22 s wall
kidnix-piperd: spoke 33 chars in 204 ms      0.23 s wall
```

**≈ 220 ms** from process start to a complete WAV, of which ~200 ms is
inference and ~20 ms is Python startup plus the socket round trip. The shell
speaks after a 300 ms hover dwell, so the voice starts roughly half a second
after the pointer settles. On a T480 that becomes ~500–600 ms for `high` and
~100 ms for `medium`.

### 2.3 Which is why the one-shot CLI was rejected

Without the resident server, every utterance pays the model load:

```
0.54 s   maxRSS=194 MB
0.51 s   maxRSS=191 MB
0.77 s   maxRSS=195 MB
```

0.5–0.8 s on a fast desktop, so 1.3–2 s on a T480 — well past the 700 ms
threshold, and past the point where a five-year-old decides the tile is broken.
The resident server is the difference between "the computer is talking to me"
and "the computer is ignoring me".

### 2.4 Rate really moves

`cori-high`, same sentence, through the whole chain:

| speechd rate | piper `length_scale` | audio |
|---|---|---|
| −60 | 1.30 | 2.335 s |
| −20 (what the shell asks for) | 1.10 | 2.05 s |
| 0 | 1.00 | 1.95 s |
| +60 | 0.70 | 1.662 s |

The 2023 piper binary **ignores `length_scale` in `--json-input` lines** — three
requests at 2.0, 0.5 and default produced 1.198 s, 1.187 s and 1.164 s of audio.
Only the `--length_scale` command-line flag works. So `kidnix-piperd` restarts
its child when the requested rate changes (quantised to 0.05 so a jittery client
cannot thrash it). Cost: one model load, ~250–380 ms, once per session in
practice because the shell asks for −20 every time.

---

## 3. How it is wired

```
kidnix-shell (python3-speechd, SSIPClient, rate -20, en-GB, punctuation none)
   │  unix socket $XDG_RUNTIME_DIR/speech-dispatcher/speechd.sock
   ▼
speech-dispatcher 0.12.1        DefaultModule kidnix-piper
   │                            DefaultLanguage "en-GB"   DefaultRate -10
   ▼  /etc/speech-dispatcher/modules/kidnix-piper.conf
sd_generic  ──  printf %s '$DATA' | kidnix-piper-say -r $RATE -v $VOLUME -l $LANGUAGE
                     │
                     ├─ unix socket $XDG_RUNTIME_DIR/kidnix/piper.sock  ──►  kidnix-piperd
                     │                                                        └─ piper (model resident)
                     ├─ (socket unreachable, or non-English) ──►  espeak-ng --stdout
                     └─ WAV → runtime tmpfs → pw-play / paplay / aplay
```

Decisions inside that picture, and why:

- **`sd_generic`, not a native module.** speech-dispatcher master has
  `src/modules/cxxpiper.cpp`, but 0.12.1 does not, and Fedora 44 ships 0.12.1.
  There is no `sd_piper` binary on this image. Upstream's own worked example
  for this shape is `mimic3-generic.conf`, which sits next to our file.
- **A UNIX socket, not TCP on loopback.** *docs/spikes/lockdown.md §1.1* leaves
  `lo` open partly for "the (future) resident Piper TTS server", so loopback
  was available — but a mode-0600 socket in the per-user tmpfs is
  access-controlled by the kernel, needs no port, is unaffected by the nftables
  ruleset entirely, and is invisible to a Flatpak that does not have the
  runtime dir bound in. Strictly better; the loopback allowance is not needed
  for TTS after all.
- **The client plays the audio, not `$PLAY_COMMAND`.** `sd_generic` does export
  `$PLAY_COMMAND`, but its value depends on speech-dispatcher's configured
  audio method, and it would have to agree with *both* Piper (22 050 Hz) and
  the espeak-ng fallback. Writing a WAV — header and all — to the runtime
  tmpfs and handing the path to `pw-play` removes the whole class of
  sample-format bug for the cost of a ~100 KB tmpfs write.
- **The fallback is inside `kidnix-piper-say`, not in speech-dispatcher.**
  speech-dispatcher's idea of a module failing is "say nothing", and ADR-0008
  says a kid session is never mute. So the client itself falls back to
  espeak-ng when the socket is unreachable or the language is not English.
  `spd-say -o espeak-ng` still works separately for explicit selection.
- **`WantedBy=kidnix-shell.service`, not `default.target`.** The socket unit is
  enabled for every user session (it is just a listening socket, and its
  existence is what stops the first utterance racing the server). The *service*
  is pulled in only by the child's shell, so the parent's ordinary GNOME
  session never loads a 114 MB model.
- **`LANGUAGE C` is not a language.** The single most important thing the VM
  found. `spd-say` with no `-l` sends `SET SELF LANGUAGE C`, sd_generic passes
  that straight through as `$LANGUAGE`, and the first version of
  `kidnix-piper-say` read it as "not English": it skipped Piper and ran
  `espeak-ng -v c`, which exits non-zero without writing a file. The child heard
  nothing, the helper exited 1, and speech-dispatcher then sat on *"Continuing
  because already speaking"* for every subsequent utterance — one mute sentence
  turned into a permanently mute computer. Two fixes: an opinionless locale
  (`C`, `POSIX`, empty) now means "the language this image speaks", and the
  helper **always exits 0**, because a lost sentence is survivable and a wedged
  speech-dispatcher is not. `tests/image/test_tts.sh` covers both.
- **`GenericPunctNone ""` is rejected by dotconf.** Empty-string arguments log
  `Missing argument to option 'GenericPunctNone'` into the module log on every
  start. Upstream's own `mimic3-generic.conf` has the same bug. The defaults are
  already empty, so the four lines are simply gone.
- **`ProtectHome=read-only` needs `ReadWritePaths=%t`.** Found in the VM, not
  on paper: in a *user* unit `ProtectHome=read-only` remounts `/home`, `/root`
  **and `/run/user/`** read-only, so the server died on its first `mkdtemp`
  with `[Errno 30] Read-only file system: /run/user/1000/kidnix-piper-XXXX`
  and systemd rate-limited it out after five restarts. The child would still
  have had a voice — `kidnix-piper-say` fell back to espeak-ng exactly as
  designed — which is precisely why this had to be caught by a boot test and
  not by a container test.
- **Idle exit at 900 s.** The server gives its 160 MB back after fifteen minutes
  of silence and socket activation brings it straight back for the price of one
  model load. A child who paints for twenty minutes should not be paying rent
  on a voice nobody is using.
- **Volume attenuates but never amplifies.** speechd volume above 0 is ignored.
  Loudness safety on this machine is a hardware ceiling plus PipeWire
  (`/usr/libexec/kidnix-audio-cap`, `50-kidnix-soft-mixer.conf`); a TTS client
  able to push past unity gain would be a hole in it.

### 3.1 Files

| File | What it is |
|---|---|
| `build_files/65-tts.sh` | fetches + checksums the runtime and voices, trims, writes licences, appends the speechd config, enables the units, asserts it all synthesises |
| `system_files/etc/speech-dispatcher/modules/kidnix-piper.conf` | the `sd_generic` module definition |
| `system_files/usr/libexec/kidnix-piperd` | the resident server (stdlib Python, ~260 lines) |
| `system_files/usr/libexec/kidnix-piper-say` | the per-utterance client, incl. the espeak-ng fallback and the rate/volume mapping |
| `system_files/usr/lib/systemd/user/kidnix-piper.{socket,service}` | socket activation + the child-session binding |
| `system_files/etc/kidnix/tts.env` | **the one knob**: which voice, sentence pause, idle timeout |
| `tests/image/test_tts.sh` | **65 assertions**, including four real syntheses, the socket round trip and the fallback path |

`/etc/speech-dispatcher/speechd.conf` is `%config(noreplace)` and RPM-owned, so
it is appended to from the build script rather than overlaid from
`system_files/` — the same reasoning as `/etc/tuxpaint/tuxpaint.conf` in
`50-activities.sh`. The block is guarded by a `# --- kidnix ---` marker and is
idempotent.

---

## 4. Verified in a VM

A bcvk ephemeral VM (`just tag=tts vm-exec …`, 4 GB / 4 vCPU, Fedora 44,
GDM up, the kid session running), everything run **as `kid`**:

```bash
askid() { runuser -u kid -- env XDG_RUNTIME_DIR=/run/user/1000 \
    DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus "$@"; }

# a VM has no sound card, so give PipeWire something to write into.
# This is test scaffolding and is NOT shipped: on real hardware the sink
# is the real one, capped by /usr/libexec/kidnix-audio-cap.
askid pactl load-module module-null-sink sink_name=kidnix_test
```

| Check | Result |
|---|---|
| `askid spd-say -O` | `espeak-ng`, **`kidnix-piper`** — the module loaded |
| `askid spd-say -L` | `en_GB-cori-high` for `en-GB`, `en`, `en-US` |
| `askid systemctl --user is-enabled kidnix-piper.socket kidnix-piper.service` | `enabled`, `enabled` |
| `askid systemctl --user is-active …` | `active`, `active` — pulled in by `kidnix-shell.service` |
| **baseline** `askid spd-say -w -o espeak-ng -l en-GB "hello from espeak"` | **rc=0** |
| **`askid spd-say -w "one two three"`** (default module, no `-l`, no `-o`) | **rc=0**, 0.75 s |
| …twice more, to prove nothing wedged | **rc=0**, **rc=0** |
| **`askid spd-say -w -o kidnix-piper -l en-GB "Shall we make a picture together?"`** | **rc=0**, 2.76 s (≈2.2 s of that is the sentence playing) |
| `cat /run/user/1000/speech-dispatcher/log/kidnix-piper.log` | **empty** — no warnings, no errors |
| `askid systemctl --user stop kidnix-piper.service` | **0.09 s** |
| `askid spd-say -w "back again"` after that stop | **rc=0**, 2.4 s — socket activation reloaded the model |

**The shell's own path**, `python3-speechd` exactly as `speech.py` uses it
(`set_language("en-GB")`, `set_rate(-20)`, `PunctuationMode.NONE`, then
`cancel()` + `speak()` per utterance):

```
speak('Make')                             returned in 0 ms
speak('Learn')                            returned in 0 ms
speak('Play')                             returned in 0 ms
speak('Shall we make a picture together?') returned in 1 ms
```

and the server's journal for those same four utterances:

```
kidnix-piperd: spoke 4 chars in  96 ms
kidnix-piperd: spoke 5 chars in 115 ms
kidnix-piperd: spoke 4 chars in 195 ms
kidnix-piperd: spoke 33 chars in 260 ms
```

**Under 200 ms for a tile label, in a VM, with the `high` voice.** That is the
number that matters: it is what a child hears after the 300 ms hover dwell.

Memory in the same run:

```
piper           VmRSS  165 MB
kidnix-piperd   VmRSS   10 MB
kidnix-piper.service   MemoryCurrent=179.6 MB   MemoryPeak=198.3 MB (max 512 MB)
```

---

## 5. What the shell needs to do differently

**Nothing.** `shell/kidnix_shell/speech.py` opens an `SSIPClient` and sets
language, rate and punctuation; it deliberately does not name an output module,
so it inherits `DefaultModule kidnix-piper` from `/etc/speech-dispatcher/speechd.conf`.
The `spd-say` fallback backend inherits it the same way. **No line of the shell
changed for this spike**, and §4 shows that exact code path running against the
Piper voice in a VM: `speak()` returns in 0–1 ms and the audio starts 96–260 ms
later.

Three things the shell *could* do later, none of them required:

1. **Expose the voice choice.** The parent panel could write
   `KIDNIX_PIPER_MODEL` into a drop-in and `systemctl --user restart
   kidnix-piper` — "make the voice quicker" on an old laptop.
2. **Warm the voice explicitly.** The service is already pulled in by
   `kidnix-shell.service`, so the model is loading while GTK is still building
   the home screen. If the first utterance ever *does* feel late, speaking a
   zero-length string at startup would force it.
3. **Notice the fallback.** `kidnix-piper-say` logs `falling back to espeak-ng`
   to the journal. A greenboot check or the parent panel could surface "the
   good voice is not working" rather than leaving a parent to wonder why the
   computer sounds like 1998.

---

## 6. What is NOT verified

1. **Audio actually leaving a speaker.** Neither the build container nor the
   bcvk VM has a sound device, so every measurement here ends at "a correct
   22 050 Hz mono 16-bit WAV exists". `pw-play` has not been observed feeding
   real hardware. **This needs a human with a laptop**, and it is the single
   biggest gap in this spike.
2. **How it sounds.** No one has listened to `cori` yet. The licence, the
   sample rate and the durations are facts; "warm UK female read-aloud voice"
   is upstream's description, not a judgement anyone here has made. A
   five-year-old's opinion is the only test that matters and it has not
   happened.
3. **The interaction with the volume cap.** `kidnix-audio-cap` caps the
   hardware mixer at 70% and WirePlumber's soft-mixer keeps userspace off it.
   Piper's output is not normalised, so whether cori at 70% of a T480's
   speakers is *loud enough* in a real room is unknown. If it is not, the
   answer is a PipeWire filter-chain gain, not raising the cap.
4. **ARM / Raspberry Pi.** The aarch64 tarball is pinned in `65-tts.sh` and its
   sha256 is recorded, but nothing has been built or run on ARM. `cori-medium`
   is the near-certain default there; *docs/research/06 §5.1* claims Piper is
   real-time on a Pi 5 CPU, which is `[C]`-grade evidence and unmeasured here.
5. **Long-session memory behaviour.** The 160 MB figure is the RSS a few
   utterances in. Nobody has run a thousand utterances and looked for creep.
   `MemoryMax=512M` on the unit is the backstop: if piper leaks, the child
   loses the good voice and keeps espeak-ng, rather than the machine losing the
   session.
6. **Concurrency.** The server is deliberately sequential — ADR-0008's
   utterance policy is "new cancels old", so there is never a second thing to
   say. If some future activity wants a second voice at the same time, this
   design says no.

### 6.1 What the VM did catch

Three real bugs, none of which any container test could have found. They are
worth listing because they are the argument for boot-testing this feature.

1. **`ProtectHome=read-only` made `/run/user` read-only** in a *user* unit, so
   the server died on its first `mkdtemp` and systemd rate-limited it out after
   five restarts. Fixed with `ReadWritePaths=%t`.
2. **`LANGUAGE C` silenced the default module and then wedged
   speech-dispatcher** — see §3. This was the serious one: the failure was not
   "the good voice did not work", it was "nothing works from now on".
3. **`GenericPunctNone ""` is a dotconf parse error**, logged into the module
   log on every start.

All three are now covered by assertions in `tests/image/test_tts.sh`.

---

## 7. Open questions for the thinker

1. **Should `cori-medium` be the default instead?** It is 4–5× faster
   (24–52 ms vs 111–295 ms warm), 51 MB smaller resident, and
   *docs/research/06 §5.1* is explicit that the low/medium/high labels are
   **model size, not perceived quality**. `high` is the default today because
   ADR-0008 says so, and because the target hardware is a laptop rather than a
   Pi. This is a taste call that wants a human ear on both files, not another
   measurement. Flipping it is one line in `/etc/kidnix/tts.env`.
2. **Do we ship both?** 178 MB of the ~200 MB delta is voices, and the second
   one is only used if someone edits a config file. Shipping both is what makes
   "this laptop is too slow" a supported answer instead of a rebuild; dropping
   `medium` would save 64 MB.
3. **Welsh.** *06 §7.5 #31* asks for Welsh TTS. There is no public-domain
   Piper Welsh voice; espeak-ng has one. `kidnix-piper-say` already routes any
   non-`en*` language to espeak-ng, so Welsh works today — badly. Whether that
   is good enough is a product call.
4. **The archived-upstream risk.** Route (a) (`piper-tts` from PyPI, GPL-3.0,
   maintained) costs ~400 MB but is alive. If the image ever grows a real
   Python ML dependency for another reason, the calculus changes and this
   should be revisited.
5. **`docs/research/07 §2.4` needs a correction** recording that
   `python3-onnxruntime` *is* in Fedora 44 (§1.1 above), so the next person
   does not re-derive it.

---

## 8. 2026-08-23: "it sounds like Stephen Hawking"

A parent listened to a real qcow2 VM with a sound card and reported that
read-aloud sounded like espeak-ng. Everything above says it should not. This
section is what a day of looking found, because most of it contradicts §4.

### 8.1 It was not espeak. It was Piper, at the wrong speed.

Booted `output/qcow2/disk.qcow2` headless with a real HD-audio codec whose
output goes to a file (`-audiodev wav,... -device intel-hda -device
hda-duplex`), then asked the machine three independent questions:

| Question | Answer |
|---|---|
| `spd-say -O` as `kid` | `espeak-ng`, `kidnix-piper` |
| speech-dispatcher at `LogLevel 5`, for an utterance with no `-o` | `In queue_message desired output module is kidnix-piper` → `200 OK SPEAKING` on the generic module → `702 END` 1.77 s later |
| `kidnix-piperd`'s own journal | `spoke 22 chars in 200 ms` for that same utterance |
| PipeWire clients in kid's session | `speech-dispatcher-generic`, never `speech-dispatcher-espeak-ng` — until `spd-say -o espeak-ng` was run deliberately, at which point it appeared |
| the sink monitor, recorded with `pw-record` and cross-correlated against in-guest Piper and espeak-ng renderings of the same sentence | **0.72 against Piper, 0.48 against espeak-ng**; the recorded utterance is 1.77 s, Piper's is 1.72 s and espeak-ng's is 1.37 s |

So the espeak-ng module has not spoken a word in a booted kidnix session. What
*is* wrong is the pace, and it is wrong in a way §2.4 could never have caught.

### 8.2 The bug: `GenericRateMultiply 1` means ×0.01

`sd_generic` computes

```
value = speechd_value * (GenericRateMultiply / 100) + GenericRateAdd
```

because dotconf has no float type. Fedora's own `dtk-generic.conf` says so out
loud: *"These values are multiplied by 100, because DotConf currently doesn't
support floats. So you can write 0.85 as 85."* `kidnix-piper.conf` shipped
`GenericRateMultiply 1` meaning to say "pass it through untouched"; it actually
said ×0.01, and `GenericRateForceInteger 1` then truncated the result to zero.

Instrumenting `kidnix-piper-say` to log its own argv, inside the VM:

```
Multiply 1    kidnix-piper-say: ARGV ['--rate', '0',   '--volume', '1',   '--language', 'en-gb']
Multiply 100  kidnix-piper-say: ARGV ['--rate', '-20', '--volume', '100', '--language', 'en-gb']
```

and in `kidnix-piperd`'s journal, for the same two runs:

```
piper spawned: model=en_GB-cori-high.onnx length_scale=1.000
piper spawned: model=en_GB-cori-high.onnx length_scale=1.100
```

**Every sentence this image has ever spoken came out at `length_scale` 1.000 —
piper's own adult default — instead of the 1.10 the shell asks for.** The same
truncation flattened `$VOLUME` to 1, so `attenuate()` never attenuated, calm
mode's slower voice did nothing, and the shell's volume control was decorative.

Why §2.4 missed it: that table was measured by running
`kidnix-piper-say --rate -60 --stdout` **directly**, and so is
`tests/image/test_tts.sh`'s "rate really moves" check. Both bypass the one
component that was broken. The lesson generalises past TTS — a helper tested on
its own argv proves nothing about the config that builds that argv.

### 8.3 Two traps that make this failure class invisible

1. **`kidnix-piper-say`'s stderr does not go to the journal.** speech-dispatcher
   redirects a module's stderr into
   `$XDG_RUNTIME_DIR/speech-dispatcher/log/kidnix-piper.log`, so §5.3's claim
   that the helper "logs `falling back to espeak-ng` to the journal" was simply
   false. It is true now: `alert()` writes to `/run/systemd/journal/socket`
   directly (stdlib, ten lines, no `logger` process and no RPM) as well as to
   stderr, and `journalctl -t kidnix-piper-say` shows it.

2. **speech-dispatcher 0.12.1 has a hidden fallback module.** Startup logs

   ```
   Module kidnix-piper started successfully with message: Everything ok so far.
   Error: Module reported error in request from speechd (code 3xx):
       300-Opening sound device failed. Reason: server audio is not supported.
   Initializing output module espeak-ng-fallback with binary .../sd_espeak-ng
   ```

   The 300 is benign — `sd_generic` plays its own audio and always refuses
   speechd's server-audio handshake; `sd_dummy` does the same. But the string
   `espeak-ng-fallback` is **hardcoded in the speech-dispatcher binary** (there
   is no `FallbackModule` option to switch it off), and speechd routes to it
   whenever the desired module is not `working`, does not support the message's
   language, or cannot do sound icons. A module that dies once therefore turns
   the whole session robotic, silently, with `spd-say` still returning 0.

   That is the shape of the reported symptom even though it was not its cause,
   so `kidnix-piper.service` now carries `StartLimitIntervalSec=0`: without it,
   five crashes in ten seconds (an OOM against `MemoryMax=512M`, say) retire the
   unit for the rest of the session and every later utterance takes the espeak
   path. A child cannot restart a unit.

### 8.4 One more path that could have muted the machine for good

`main()` ended in `return play(wav)`. §3 is emphatic that a non-zero exit leaves
speech-dispatcher stuck on *"Continuing because already speaking"* — and on a
machine with no sink, `pw-play` exits non-zero. The last route from "no sound
card" to "permanently mute computer" is closed: the player's status is now an
`alert()` and a zero.

### 8.5 What is checked now

`tests/image/test_tts.sh` (78 assertions, was 73) gained the four hundreds, the
`StartLimitIntervalSec=0` line and the sentence pause. Against the image built
*before* this section it fails exactly five times and passes 73; against the
fixed files it is 78/0.

`tests/boot/bcvk_boot_test.py` gained `assert_read_aloud()`, which is about
**identity and pace, never success** — `spd-say` returns 0 whether Piper or
espeak-ng spoke, so an rc-based test proves nothing:

| Probe key | Assertion |
|---|---|
| `tts_modules` | `spd-say -O` offers `kidnix-piper` |
| `tts_socket` | `kidnix-piper.socket` is listening in kid's session |
| `tts_service_before` / `_after` | the service is active *before* the test speaks (the shell's greeting loaded the model) and still active after |
| `tts_spoke_before` / `_after` | **an utterance with no `-o` moved `kidnix-piperd`'s own "spoke N chars" counter** — the one check that distinguishes the good voice from the guaranteed one |
| `tts_fallbacks` | zero `falling back to espeak-ng` lines in the boot's journal |
| `tts_length_scale` | speechd rate −20 arrives at piper as `length_scale=1.100` |

Measured on the fixed image in the qcow2 VM:

```
tts_modules=OUTPUT MODULES espeak-ng kidnix-piper
tts_socket=active          tts_service_before=active   tts_service_after=active
tts_spoke_before=49        tts_spoke_after=50          tts_spd_rc=0
tts_length_scale=1.100     tts_fallbacks=0
```

and with `kidnix-piper.socket` stopped, to prove the checks can fail:

```
kidnix-piper-say[4314]: piper server unavailable ([Errno 2] No such file or
    directory); falling back to espeak-ng
tts_fallbacks=1            tts_spd_rc=0
```

### 8.6 Naturalness, now that the knobs are connected

- **`length_scale` 1.10** for the child (speechd rate −20, `SPEECH_RATE`), 1.05
  for everything else (`DefaultRate -10`). 1.05–1.15 is unhurried without
  sounding like a slowed-down recording.
- **`sentence_silence` 0.25 s**, down from 0.35. The gap a child hears between
  two sentences is not this number — `SpeechManager.speak_then()` leaves its own
  `SENTENCE_GAP_MS = 400` — so 0.35 stacked on top of that and made two-clause
  lines drag. This value only bites *within* one utterance.
- **`noise_scale` / `noise_w` left at piper's defaults (0.667 / 0.8)** and
  documented in `tts.env` as deliberately absent. Turning them down is what
  actually makes a neural voice sound like a robot; the only place kidnix sets
  them to 0 is the build-time determinism probe, where nobody is listening.
- **Pitch stays neutral.** A VITS model sings at the pitch it was trained at.

`/etc/kidnix/tts.env` now carries all of that as prose, including a
"knobs that are deliberately NOT in this file" section, because the next person
to be told the voice sounds wrong will open that file first.

### 8.7 Ten voices, for an ear that is not mine

`output/tts-samples/` has all ten en_GB Piper voices saying the shell's real
lines at the settings above, plus `all-voices-line5.wav` — 69 seconds, every
voice announcing itself in its own voice and then reading the Goodnight line.
`output/tts-samples/README.md` has the licences: only **cori** (today's default)
is public domain; alba, aru and vctk are CC-BY-4.0; the two OpenSLR voices are
CC-BY-SA-4.0; jenny and alan have no usable licence statement and semaine is
CC-BY-NC-SA, so those three are not shippable and are included only so the
comparison is honest.

Measured, not judged — nobody in this loop can hear. The one number worth
carrying: the pitch standard deviation over the Goodnight line is 53.5 Hz for
`cori-high` against 41 Hz for espeak-ng at 104 Hz mean, and 19.2 Hz for
`northern_english_male-medium`, which is the flattest of the ten. §6 item 2
still stands: **no one has listened**, and that is still the only test that
matters.

### 8.8 2026-08-23: a human listened, and the default voice changed

§8.7 ended on the only honest sentence available at the time: *"no one has
listened, and that is still the only test that matters."* Matt then listened to
`output/tts-samples/` and called `cori` awful.

That settles it. Every argument for cori was a licensing argument — it is the
one en_GB Piper voice whose `MODEL_CARD` says **public domain**, so it was the
only one that cost no attribution — and not one of them was an argument about
how it sounds, because nobody in the loop could hear. A measured `sd` of 53.5 Hz
over the Goodnight line told us cori had more melodic range than seven of the
other nine. It did not tell us anyone would want to be read to by it.

**The default is now `en_GB-alba-medium`.** cori stays in the image.

#### What it cost

| | |
|---|---|
| Licence | CC-BY-4.0, up from public domain |
| Obligation | one credit, at `/usr/share/licenses/kidnix-voices/ATTRIBUTION` |
| Image delta | **+63.2 MB** (`en_GB-alba-medium.onnx` 63,201,294 B, config 4,888 B, card 324 B) |
| Resident memory | **−54 MB** (~114 MB for a medium model against ~168 MB for `cori-high`) |
| Latency | **~4× faster** — a medium model is ~25–50 ms per short utterance against cori-high's ~110–300 ms |

The image grows and the running session gets *cheaper*, because the old default
was the `high` tier and the new one is `medium`. Nothing about the pace changed:
`length_scale` 1.10 for the child and `sentence_silence` 0.25 are exactly as
§8.6 left them, and both are still where §8.6 says they are — the pace knob is
speechd's rate, not this file.

#### Why not just swap cori out

Because the reason the default moved is that a claim about how something sounds
survived for a day without anyone testing it, and the fix for that is not a
different untested claim. All three models ship (178 MB of cori, 63 MB of alba)
and `/etc/kidnix/tts.env` chooses between them, so if alba also grates, the
answer is one line in one file — no rebuild, no network, no image pull. That
escape hatch is the mechanism this change was itself delivered through, which
is the best evidence available that it is worth its 178 MB.

#### On taking the attribution

`AGENTS.md` §5 asks for bundled voices to be **redistributable** and for their
licences to be **recorded**. It does not ask for zero-obligation. CC-BY-4.0 is
redistributable inside a commercial product; the price is a credit. The credit
is written out by `build_files/65-tts.sh` and names the depositors, the work,
the DOI, the licence URI and the fact that the model is a *modification* of the
corpus — CC-BY-4.0 §3(a)(1)(A–D), clause by clause — plus the moral-rights
sentence the Alba corpus attaches on its own account, quoted verbatim because
editing somebody's licence notice is not tidying.

What is still refused has not moved: `semaine` is CC-BY-NC-SA-4.0 and
non-commercial licences are disqualified outright; `alan` and `jenny_dioco` say
"See URL", and unresolved is unshippable.

#### What is checked now

`tests/image/test_tts.sh` gained: alba's three files present and pinned by
sha256; alba's card stating CC-BY-4.0; the six attribution clauses asserted
*separately*, because the file that discharges the obligation is inert text that
a tidy-up could delete without breaking a single thing that makes a noise; the
CC-BY-4.0 rows in `THIRD-PARTY.tsv`; the default in `tts.env` being alba **and
naming a file that exists**; and — the one that would have caught a bad swap —
`piper spawned: model=en_GB-alba-medium.onnx` in the resident server's own log.

That last one matters for the same reason §8.5 exists. A default pointing at an
absent model does not fail loudly: `kidnix-piperd` logs "voice model missing",
exits, and every utterance quietly takes the espeak-ng path. `spd-say` returns
0. The child is read to in the robot voice and nothing goes red. Grepping the
config file proves the string; only the server's log proves the model.

`build_files/65-tts.sh` fails the build if the attribution stops naming the
depositors, if `tts.env` names anything but alba, or if alba does not
synthesise. The cori determinism probe (`--noise_scale 0 --noise_w 0` against
Fedora's `espeak-ng-data`) is unchanged and still on cori, because that is the
model its hash was measured against.

#### Still true

Nobody has heard alba *on the machine* — the samples were rendered by the
image's own piper at the session's own settings, which is as close as an
offline render gets, but §6 item 2 stands. `output/tts-samples/default-alba/`
has three lines for exactly this purpose.
