#!/usr/bin/bash
# Static + synthesis assertions about read-aloud. Runs INSIDE the container:
#
#   podman run --rm -v "$PWD/tests/image:/tests:ro,z" \
#       --entrypoint /bin/bash localhost/kidnix:latest /tests/test_tts.sh
#
# What it can prove: the Piper runtime and both voice models are on disk with
# the exact bytes we reviewed the licences for, the vendored binary links
# against Fedora's espeak-ng and actually synthesises, the speech-dispatcher
# module is registered and is the default, the resident server is enabled for
# the child session, and the espeak-ng fallback still works.
#
# What it cannot prove: that any of it reaches a speaker. There is no audio
# device, no PipeWire and no user session inside a container -- that is
# `just test-boot` / docs/spikes/tts.md 4, which is where the end-to-end
# `spd-say -o kidnix-piper` result lives.
set -uo pipefail

pass=0
fail=0

_report() {
    local status="$1" name="$2" detail="${3:-}"
    if [[ "${status}" == ok ]]; then
        printf '  \033[32mPASS\033[0m  %s\n' "${name}"
        pass=$(( pass + 1 ))
    else
        printf '  \033[31mFAIL\033[0m  %s%s\n' "${name}" "${detail:+ -- ${detail}}"
        fail=$(( fail + 1 ))
    fi
}

assert_file() {
    if [[ -f "$1" ]]; then _report ok "file $1"; else _report no "file $1" "missing"; fi
}

assert_exec() {
    if [[ -x "$1" ]]; then _report ok "executable $1"; else _report no "executable $1" "missing or not +x"; fi
}

assert_rpm() {
    if rpm -q "$1" >/dev/null 2>&1; then
        _report ok "package $1 ($(rpm -q --qf '%{VERSION}-%{RELEASE}' "$1"))"
    else
        _report no "package $1" "not installed"
    fi
}

assert_grep() {
    if grep -Eq "$1" "$2" 2>/dev/null; then
        _report ok "$3"
    else
        _report no "$3" "no match for /$1/ in $2"
    fi
}

# assert_sha256 <path> <expected> <description>
assert_sha256() {
    local got
    got="$(sha256sum "$1" 2>/dev/null | cut -d' ' -f1)"
    if [[ "${got}" == "$2" ]]; then
        _report ok "$3"
    else
        _report no "$3" "want $2, got ${got:-<unreadable>}"
    fi
}

assert_run() {
    local name="$1"; shift
    local out
    if out="$("$@" 2>&1)"; then
        _report ok "${name}"
    else
        _report no "${name}" "${out##*$'\n'}"
    fi
}

section() { printf '\n\033[1m%s\033[0m\n' "$1"; }

PIPER=/usr/lib/kidnix/piper/piper
VOICES=/usr/share/kidnix/voices
SPEECHD_CONF=/etc/speech-dispatcher/speechd.conf
MODULE_CONF=/etc/speech-dispatcher/modules/kidnix-piper.conf
WORK="$(mktemp -d)"
trap 'rm -rf "${WORK}"' EXIT

# -----------------------------------------------------------------------------

section "the Piper runtime (vendored, MIT, build_files/65-tts.sh)"

assert_exec "${PIPER}"
assert_file /usr/lib/kidnix/piper/libonnxruntime.so.1.14.1
assert_file /usr/lib/kidnix/piper/libpiper_phonemize.so.1.2.0

# Upstream's tarball bundles a prebuilt libespeak-ng.so (GPL-3.0) and 19 MB of
# espeak-ng-data. We deliberately ship neither: the build proved the WAVs are
# byte-identical against Fedora's espeak-ng 1.52.0, and not redistributing a
# GPL binary without its source is the point.
if [[ -e /usr/lib/kidnix/piper/libespeak-ng.so.1 ]]; then
    _report no "no vendored libespeak-ng" "the GPL binary we deliberately dropped is back"
else
    _report ok "no vendored libespeak-ng (Fedora's is used instead)"
fi
if [[ -d /usr/lib/kidnix/piper/espeak-ng-data ]]; then
    _report no "no vendored espeak-ng-data" "19 MB duplicate of Fedora's data"
else
    _report ok "no vendored espeak-ng-data (Fedora's is used instead)"
fi

# The whole trim rests on this resolving. `ldd` is the cheap half.
if ldd "${PIPER}" 2>/dev/null | grep -q "not found"; then
    _report no "piper's shared libraries all resolve" \
        "$(ldd "${PIPER}" 2>&1 | grep 'not found' | head -1)"
else
    _report ok "piper's shared libraries all resolve (incl. Fedora libespeak-ng.so.1)"
fi

assert_rpm espeak-ng
assert_rpm speech-dispatcher
assert_rpm speech-dispatcher-espeak-ng
assert_rpm python3-speechd
if [[ -d /usr/share/espeak-ng-data ]]; then
    _report ok "directory /usr/share/espeak-ng-data (piper's phonemiser reads it)"
else
    _report no "directory /usr/share/espeak-ng-data" "missing"
fi

section "the voice models (public domain -- docs/LICENSES.md 6)"

assert_file "${VOICES}/en_GB-cori-high.onnx"
assert_file "${VOICES}/en_GB-cori-high.onnx.json"
assert_file "${VOICES}/en_GB-cori-medium.onnx"
assert_file "${VOICES}/en_GB-cori-medium.onnx.json"

# The exact bytes whose MODEL_CARD was read and whose licence is recorded. A
# CDN rotation must fail here, not ship an unreviewed model to a child.
assert_sha256 "${VOICES}/en_GB-cori-high.onnx" \
    470b4dd634c98f8a4850d7626ffc3dfc90774628eeef6605a6dd8f88f30a5903 \
    "en_GB-cori-high.onnx is the reviewed model (sha256)"
assert_sha256 "${VOICES}/en_GB-cori-high.onnx.json" \
    9e7fb5b5671612c22f3c81cbe46c1ae87b031a4632bcb509e499dad6f1e2adec \
    "en_GB-cori-high.onnx.json is the reviewed config (sha256)"
assert_sha256 "${VOICES}/en_GB-cori-medium.onnx" \
    1899f98e5fb8310154f3c2973f4b8a929ba7245e722b3d3a85680b833d95f10d \
    "en_GB-cori-medium.onnx is the reviewed model (sha256)"

# The card is the licence evidence and must travel with the model.
assert_file "${VOICES}/en_GB-cori-high.MODEL_CARD"
assert_grep 'License: public domain' "${VOICES}/en_GB-cori-high.MODEL_CARD" \
    "the high voice's own model card says public domain"
assert_grep 'License: public domain' "${VOICES}/en_GB-cori-medium.MODEL_CARD" \
    "the medium voice's own model card says public domain"

# 22,050 Hz for medium/high is what docs/research/07 2.4 predicted; assert it
# rather than trust it, because the player is told nothing about format.
assert_run "the high voice is a 22050 Hz single-speaker model" python3 -c "
import json
config = json.load(open('${VOICES}/en_GB-cori-high.onnx.json'))
assert config['audio']['sample_rate'] == 22050, config['audio']
assert config['num_speakers'] == 1, config['num_speakers']
assert config['language']['code'] == 'en_GB', config['language']
"

section "licence texts carried with the vendored binaries (AGENTS.md 5)"

assert_file /usr/share/licenses/kidnix-piper/LICENSE.piper.md
assert_file /usr/share/licenses/kidnix-piper/LICENSE.piper-phonemize.md
assert_file /usr/share/licenses/kidnix-piper/LICENSE.onnxruntime
assert_file /usr/share/licenses/kidnix-piper/README.kidnix
assert_grep 'MIT License' /usr/share/licenses/kidnix-piper/LICENSE.piper.md \
    "piper is still MIT"
assert_grep 'MIT License' /usr/share/licenses/kidnix-piper/LICENSE.onnxruntime \
    "onnxruntime is still MIT"

section "speech-dispatcher wiring"

assert_file "${MODULE_CONF}"
assert_exec /usr/lib64/speech-dispatcher-modules/sd_generic
assert_grep '^AddModule "kidnix-piper" "sd_generic" "kidnix-piper.conf"$' "${SPEECHD_CONF}" \
    "kidnix-piper is registered as a generic module"
assert_grep '^DefaultModule kidnix-piper$' "${SPEECHD_CONF}" \
    "kidnix-piper is the default voice"
# ADR-0008: "a kid session is never mute even if Piper is missing".
assert_grep '^AddModule "espeak-ng"' "${SPEECHD_CONF}" \
    "espeak-ng is still registered as the fallback module"
assert_grep '^DefaultLanguage "en-GB"$' "${SPEECHD_CONF}" \
    "the default language is en-GB (06 7.5 #29)"
assert_grep '^DefaultRate -10$' "${SPEECHD_CONF}" \
    "the default rate is slower than the voice's natural pace (06 7.5 #30)"
assert_grep 'kidnix-piper-say' "${MODULE_CONF}" \
    "GenericExecuteSynth runs kidnix-piper-say"
assert_grep '^GenericCmdDependency "/usr/libexec/kidnix-piper-say"$' "${MODULE_CONF}" \
    "the module names the helper it needs (documentation -- 0.12.1 does not enforce it)"
assert_grep '^AddVoice "en-GB"' "${MODULE_CONF}" \
    "the module advertises an en-GB voice"

section "the resident server"

assert_exec /usr/libexec/kidnix-piperd
assert_exec /usr/libexec/kidnix-piper-say
assert_file /usr/lib/systemd/user/kidnix-piper.service
assert_file /usr/lib/systemd/user/kidnix-piper.socket
assert_file /etc/kidnix/tts.env

# Enabled with `systemctl --global`, because `kid` does not exist at build time.
if [[ -L /etc/systemd/user/sockets.target.wants/kidnix-piper.socket ]]; then
    _report ok "kidnix-piper.socket is enabled for every user session"
else
    _report no "kidnix-piper.socket is enabled for every user session" \
        "no /etc/systemd/user/sockets.target.wants/kidnix-piper.socket"
fi
# ...and the *service* only follows the child's shell, so the parent's GNOME
# session never loads a 114 MB model.
if [[ -L /etc/systemd/user/kidnix-shell.service.wants/kidnix-piper.service ]]; then
    _report ok "kidnix-piper.service is pulled in by the kid's shell (and only there)"
else
    _report no "kidnix-piper.service is pulled in by the kid's shell" \
        "no /etc/systemd/user/kidnix-shell.service.wants/kidnix-piper.service"
fi
if [[ -L /etc/systemd/user/default.target.wants/kidnix-piper.service ]]; then
    _report no "the piper service is not in every session's default.target" \
        "the parent's GNOME session would load the model too"
else
    _report ok "the piper service is not in every session's default.target"
fi

assert_grep '^ListenStream=%t/kidnix/piper.sock$' \
    /usr/lib/systemd/user/kidnix-piper.socket \
    "the socket is a UNIX socket in the runtime dir, not a TCP port"
assert_grep '^SocketMode=0600$' /usr/lib/systemd/user/kidnix-piper.socket \
    "the socket is private to its own user"
assert_grep '^EnvironmentFile=/etc/kidnix/tts.env$' \
    /usr/lib/systemd/user/kidnix-piper.service \
    "the voice is chosen by one file a parent can edit"
assert_grep '^KIDNIX_PIPER_MODEL=/usr/share/kidnix/voices/en_GB-cori-high.onnx$' \
    /etc/kidnix/tts.env \
    "the default voice is en_GB-cori-high"

assert_run "kidnix-piperd compiles" python3 -c "
import sys
path = '/usr/libexec/kidnix-piperd'
compile(open(path).read(), path, 'exec')
"
assert_run "kidnix-piper-say compiles" python3 -c "
import sys
path = '/usr/libexec/kidnix-piper-say'
compile(open(path).read(), path, 'exec')
"
assert_run "kidnix-piper-say --help" /usr/libexec/kidnix-piper-say --help

section "it actually synthesises"

# Deterministic settings, so this is a real regression test on the phoneme
# tables and not a coin toss: if a future Fedora espeak-ng changes what
# /usr/share/espeak-ng-data means, the audio length changes and this notices.
if printf 'Shall we make a picture together?\n' \
    | "${PIPER}" --model "${VOICES}/en_GB-cori-high.onnx" \
        --espeak_data /usr/share/espeak-ng-data \
        --noise_scale 0 --noise_w 0 \
        --output_file "${WORK}/piper.wav" --quiet >/dev/null 2>"${WORK}/piper.err"
then
    _report ok "piper synthesises with the high voice"
else
    _report no "piper synthesises with the high voice" "$(tail -1 "${WORK}/piper.err")"
fi

assert_run "the high voice produced a plausible WAV" python3 -c "
import wave
with wave.open('${WORK}/piper.wav') as handle:
    assert handle.getframerate() == 22050, handle.getframerate()
    assert handle.getnchannels() == 1, handle.getnchannels()
    assert handle.getsampwidth() == 2, handle.getsampwidth()
    seconds = handle.getnframes() / handle.getframerate()
    assert 1.0 < seconds < 5.0, seconds
"

if printf 'Shall we make a picture together?\n' \
    | "${PIPER}" --model "${VOICES}/en_GB-cori-medium.onnx" \
        --espeak_data /usr/share/espeak-ng-data \
        --output_file "${WORK}/medium.wav" --quiet >/dev/null 2>&1
then
    _report ok "piper synthesises with the medium (low-CPU) voice"
else
    _report no "piper synthesises with the medium (low-CPU) voice" "see build_files/65-tts.sh"
fi

# The fallback that makes ADR-0008's "never mute" true.
if espeak-ng -v en-gb --stdout "fallback" >"${WORK}/espeak.wav" 2>/dev/null \
    && [[ -s "${WORK}/espeak.wav" ]]; then
    _report ok "espeak-ng still speaks (the guaranteed fallback voice)"
else
    _report no "espeak-ng still speaks" "no audio produced"
fi

# End to end through the client, with no server running: it must fall back to
# espeak-ng rather than emit nothing. This is the failure mode that matters.
if printf 'no server here\n' \
    | KIDNIX_PIPER_SOCKET=/nonexistent/piper.sock \
      /usr/libexec/kidnix-piper-say --stdout 2>/dev/null >"${WORK}/fallback.wav" \
    && [[ -s "${WORK}/fallback.wav" ]] \
    && head -c 4 "${WORK}/fallback.wav" | grep -q RIFF
then
    _report ok "kidnix-piper-say falls back to espeak-ng when the server is absent"
else
    _report no "kidnix-piper-say falls back to espeak-ng when the server is absent" \
        "no WAV on stdout"
fi

# ...and the fallback WAV must have a *correct* header. espeak-ng's --stdout
# writes a streaming header with a placeholder length, which makes every reader
# guess; `kidnix-piper-say` uses `-w` for this reason and this is the check that
# it stays that way.
assert_run "the fallback WAV declares its real length (not a streaming header)" python3 -c "
import wave
with wave.open('${WORK}/fallback.wav') as handle:
    seconds = handle.getnframes() / handle.getframerate()
    assert 0.3 < seconds < 8.0, seconds
"

# ...and with the server running, over the real socket. A container has no
# session bus and no audio, but it does have a filesystem and a CPU, which is
# everything this path needs.
# Reading it here is also the check that it is valid EnvironmentFile syntax:
# systemd's parser is KEY=value with no expansion, so exporting the non-comment
# lines is a faithful stand-in and avoids sourcing image data as shell.
mapfile -t tts_env < <(grep -E '^[A-Z_]+=' /etc/kidnix/tts.env)
for entry in "${tts_env[@]}"; do export "${entry?}"; done
# ...and *after* it, so these win: a 900 s idle timeout would keep the test
# container alive for fifteen minutes.
export XDG_RUNTIME_DIR="${WORK}"
export KIDNIX_PIPER_SOCKET="${WORK}/piper.sock"
export KIDNIX_PIPER_IDLE_EXIT=20
/usr/libexec/kidnix-piperd >"${WORK}/piperd.log" 2>&1 &
piperd_pid=$!
for _ in $(seq 1 60); do
    [[ -S "${KIDNIX_PIPER_SOCKET}" ]] && break
    sleep 0.25
done

if [[ -S "${KIDNIX_PIPER_SOCKET}" ]]; then
    _report ok "kidnix-piperd creates its socket when run without systemd"
else
    _report no "kidnix-piperd creates its socket when run without systemd" \
        "$(tail -1 "${WORK}/piperd.log" 2>/dev/null)"
fi

if printf 'Shall we make a picture together?\n' \
    | /usr/libexec/kidnix-piper-say --rate -20 --stdout 2>"${WORK}/say.err" \
        >"${WORK}/served.wav" \
    && [[ -s "${WORK}/served.wav" ]] \
    && ! grep -q "falling back" "${WORK}/say.err"
then
    _report ok "kidnix-piper-say gets a WAV from the resident server (not the fallback)"
else
    _report no "kidnix-piper-say gets a WAV from the resident server" \
        "$(tail -1 "${WORK}/say.err" 2>/dev/null)"
fi

# The regression test for the bug that made the first VM run mute: `spd-say`
# with no -l sends `SET SELF LANGUAGE C`, sd_generic passes that through as
# $LANGUAGE, and "C" is not a language. It must be read as "no opinion" and get
# the image's own voice -- not routed past Piper into `espeak-ng -v c`, which
# fails. docs/spikes/tts.md 6.1.
if printf 'no locale here\n' \
    | /usr/libexec/kidnix-piper-say --language C --stdout 2>"${WORK}/langc.err" \
        >"${WORK}/langc.wav" \
    && [[ -s "${WORK}/langc.wav" ]] \
    && ! grep -q "no voice could produce audio" "${WORK}/langc.err"
then
    _report ok "a client with no locale (LANGUAGE=C) still gets the Piper voice"
else
    _report no "a client with no locale (LANGUAGE=C) still gets the Piper voice" \
        "$(tail -1 "${WORK}/langc.err" 2>/dev/null)"
fi

# ...and an unknown language must still make a sound rather than a silence.
if printf 'unknown tongue\n' \
    | /usr/libexec/kidnix-piper-say --language zz-ZZ --stdout 2>/dev/null \
        >"${WORK}/langzz.wav" \
    && [[ -s "${WORK}/langzz.wav" ]]
then
    _report ok "an unknown language falls through to a voice that exists"
else
    _report no "an unknown language falls through to a voice that exists" "silence"
fi

# A helper that exits non-zero leaves speech-dispatcher stuck on "already
# speaking" and silences everything after it, so it must not, ever.
if printf 'x\n' | /usr/libexec/kidnix-piper-say --language zz-ZZ --stdout >/dev/null 2>&1; then
    _report ok "kidnix-piper-say exits 0 even when it cannot speak (speechd wedges otherwise)"
else
    _report no "kidnix-piper-say exits 0 even when it cannot speak" "non-zero exit"
fi

# dotconf rejects empty-string arguments, and a rejected line is a warning in
# the module log on every single start.
if grep -qE '^\s*Generic(Punct(None|Some|Most|All)|StripPunctChars|RecodeFallback)\s+""\s*$' "${MODULE_CONF}"; then
    _report no "no empty-string arguments in the module config" \
        "dotconf logs 'Missing argument to option ...' for each"
else
    _report ok "no empty-string arguments in the module config (dotconf rejects them)"
fi

assert_run "the served WAV is 22050 Hz mono 16-bit, as the module config assumes" python3 -c "
import wave
with wave.open('${WORK}/served.wav') as handle:
    assert (handle.getframerate(), handle.getnchannels(), handle.getsampwidth()) == (22050, 1, 2), \
        handle.getparams()
"

# Rate really moves: -60 must be audibly longer than +60. This is the only
# check that the speechd rate the shell sends survives the whole chain.
if printf 'Shall we make a picture together?\n' | /usr/libexec/kidnix-piper-say \
        --rate -60 --stdout >"${WORK}/slow.wav" 2>/dev/null \
    && printf 'Shall we make a picture together?\n' | /usr/libexec/kidnix-piper-say \
        --rate 60 --stdout >"${WORK}/fast.wav" 2>/dev/null \
    && python3 -c "
import sys, wave
def seconds(path):
    with wave.open(path) as handle:
        return handle.getnframes() / handle.getframerate()
slow, fast = seconds('${WORK}/slow.wav'), seconds('${WORK}/fast.wav')
# Measured 2.335 s vs 1.662 s (ratio 1.40). The ratio is diluted by the fixed
# 0.35 s sentence pause, so 1.25 is the bar: comfortably above an unchanged
# rate (ratio 1.0) and comfortably below what a working rate produces.
sys.exit(0 if slow > fast * 1.25 else 1)
"
then
    _report ok "speechd rate reaches Piper (rate -60 is much slower than +60)"
else
    _report no "speechd rate reaches Piper" "the two renderings are the same length"
fi

kill "${piperd_pid}" 2>/dev/null
wait "${piperd_pid}" 2>/dev/null

section "hygiene"

# Nothing may land in /var: bootc container lint fails the build on it, and a
# voice model in /var would not be covered by `bootc upgrade`/rollback.
if compgen -G "/var/lib/kidnix/voices*" >/dev/null 2>&1; then
    _report no "no voice data in /var" "voices must be in /usr to be part of the image"
else
    _report ok "no voice data in /var (the image owns the voice, not the machine)"
fi

# The pip/onnxruntime route we rejected: 256 MB of numpy/sympy/openblas, or a
# gigabyte with the image's weak deps on. If it ever creeps back in, say so.
if rpm -q python3-onnxruntime >/dev/null 2>&1; then
    _report no "no python3-onnxruntime" "256 MB of numpy/sympy/openblas we chose not to ship"
else
    _report ok "no python3-onnxruntime (the vendored 22 MB runtime is used instead)"
fi
if rpm -q python3-pip >/dev/null 2>&1; then
    _report no "no pip in a child's OS" "installed"
else
    _report ok "no pip in a child's OS"
fi

# -----------------------------------------------------------------------------

printf '\n\033[1m%d passed, %d failed\033[0m\n' "${pass}" "${fail}"
[[ "${fail}" -eq 0 ]]
