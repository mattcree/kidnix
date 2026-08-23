#!/usr/bin/bash
# Pre-rendered speech: what is in the image, and what must NOT be.
#
#   podman run --rm -v "$PWD/tests/image:/tests:ro,z" \
#       --entrypoint /bin/bash localhost/kidnix:latest /tests/test_prerender.sh
#
# The whole bargain of build_files/66-prerender-speech.sh is that the image
# gains AUDIO and not a machine-learning stack: docs/spikes/tts-kokoro.md 6
# rejected the resident Kokoro server at 460 MB of image and 415 MB resident,
# and 7.1 accepted the clips at ~4 MB and nothing resident. Half of this file
# checks the clips arrived; the other half checks the 460 MB did not.
#
# What it cannot prove: that a clip ever reaches a speaker. There is no audio
# device and no user session inside a container -- that is `just test-boot`,
# which counts the shell's own "played clip" journal lines.
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
ok() { _report ok "$1"; }
no() { _report no "$1" "${2:-}"; }
section() { printf '\n\033[1m%s\033[0m\n' "$1"; }

SPEECH=/usr/share/kidnix/speech
LANG_DIR="${SPEECH}/en_GB"
INDEX="${LANG_DIR}/index.json"
MANIFEST=/usr/share/kidnix/THIRD-PARTY.tsv

#: docs/spikes/tts-prerender.md: the tree yields ~314 today. The floor is well
#: below that so ordinary churn never trips it, and a collapsed enumeration
#: always does.
MIN_CLIPS=200
#: The brief's ceiling. Measured at ~4.3 MB, so there is room to grow.
MAX_BYTES=$(( 20 * 1024 * 1024 ))

printf '\033[1mkidnix pre-rendered speech\033[0m\n'

# -----------------------------------------------------------------------------
section "1. the catalogue is there"
# -----------------------------------------------------------------------------

if [[ -f "${INDEX}" ]]; then
    ok "the image ships ${INDEX}"
else
    no "the image ships ${INDEX}" "missing -- run 'just build'"
    printf '\n\033[1m==> %d passed, %d failed\033[0m\n' "${pass}" "${fail}"
    exit 1
fi

clips="$(find "${LANG_DIR}" -maxdepth 1 -name '*.ogg' -type f | wc -l)"
if (( clips >= MIN_CLIPS )); then
    ok "${clips} clips on disk (floor ${MIN_CLIPS})"
else
    no "at least ${MIN_CLIPS} clips on disk" "only ${clips}"
fi

bytes="$(du -sb "${SPEECH}" | cut -f1)"
if (( bytes <= MAX_BYTES )); then
    ok "the catalogue is $(( bytes / 1024 / 1024 )) MB, inside the $(( MAX_BYTES / 1024 / 1024 )) MB budget"
else
    no "the catalogue is inside the $(( MAX_BYTES / 1024 / 1024 )) MB budget" "$(( bytes / 1024 / 1024 )) MB"
fi

# A named sample, so the test names a real file rather than "some file".
# sha1("Who's here?") is what shell/kidnix_shell/prerendered.py will look for
# on the first screen of every session.
sample="$(python3 -c "
import hashlib
print(hashlib.sha1(\"Who's here?\".encode(), usedforsecurity=False).hexdigest())
")"
if [[ -f "${LANG_DIR}/${sample}.ogg" ]]; then
    ok "the greeting's own clip is present (${sample:0:12}....ogg)"
else
    no "the greeting's own clip is present" "no ${sample}.ogg"
fi

if head -c 4 "${LANG_DIR}/${sample}.ogg" 2>/dev/null | grep -q OggS; then
    ok "the clips are real Ogg streams"
else
    no "the clips are real Ogg streams" "no OggS magic"
fi

# -----------------------------------------------------------------------------
section "2. the index agrees with the disk, and with the shell"
# -----------------------------------------------------------------------------

index_report="$(python3 - "${INDEX}" "${LANG_DIR}" <<'PY'
import hashlib, json, pathlib, sys

index = json.loads(pathlib.Path(sys.argv[1]).read_text())
directory = pathlib.Path(sys.argv[2])
checks = []

checks.append((index.get("version") == 1, "index.json is schema version 1"))
checks.append((index.get("language") == "en_GB", f"index language is en_GB (got {index.get('language')!r})"))
checks.append((bool(index.get("voice")), f"index names its voice ({index.get('voice')!r})"))
checks.append((index.get("sample_rate") == 24000, "index records Kokoro's 24 kHz"))
# The one number prerendered.py gates on: a clip is paced for speech-dispatcher
# rate -20 and no other, so calm mode falls back to Piper rather than playing a
# recording at the wrong tempo.
checks.append((index.get("speechd_rate") == -20, f"index records speechd_rate -20 (got {index.get('speechd_rate')!r})"))

named = {entry["file"] for entry in index["clips"].values()}
on_disk = {path.name for path in directory.glob("*.ogg")}
checks.append((not (named - on_disk), f"every index entry has a file ({len(named - on_disk)} missing)"))
checks.append((not (on_disk - named), f"no clip is orphaned ({len(on_disk - named)} orphans)"))

# The filename must actually be the sha1 of the text, or the index is the only
# thing tying the two together and a rename could silently mis-speak a label.
wrong = [
    text for text, entry in index["clips"].items()
    if entry["file"] != hashlib.sha1(text.encode(), usedforsecurity=False).hexdigest() + ".ogg"
]
checks.append((not wrong, f"every filename is sha1(text) ({len(wrong)} wrong)"))

# No clip may be for a template: "You {verb} {count} {noun}" as a recording
# would say the words "verb", "count" and "noun" out loud.
templates = [text for text in index["clips"] if "{" in text or "}" in text]
checks.append((not templates, f"no clip is a placeholder template ({templates[:2]})"))

# The lines a child hears most. These are hand-picked because a regression here
# is the least audible: everything still speaks, just in the other voice.
for wanted in ("Who's here?", "Say it again", "Back", "Ready to go outside?"):
    checks.append((wanted in index["clips"], f"the catalogue has {wanted!r}"))

for good, name in checks:
    print(f"  \033[32mPASS\033[0m  {name}" if good else f"  \033[31mFAIL\033[0m  {name}")
# The bash half adds these to its own tally rather than carrying a hardcoded
# count that would drift the moment a check is added here.
print(f"COUNTS {sum(1 for g, _ in checks if g)} {sum(1 for g, _ in checks if not g)}")
PY
)"
printf '%s\n' "${index_report}" | grep -v '^COUNTS '
read -r _ index_pass index_fail \
    <<<"$(printf '%s\n' "${index_report}" | grep '^COUNTS ' || echo 'COUNTS 0 1')"
pass=$(( pass + index_pass ))
fail=$(( fail + index_fail ))

# The shell must be able to read its own catalogue. This is the real contract:
# the module that ships does the lookup, not a reimplementation of it in bash.
if python3 -c "
import sys
from pathlib import Path
from kidnix_shell.prerendered import select_prerendered
voice = select_prerendered(root=Path('${SPEECH}'), language='en-GB')
assert voice is not None, 'the shell found no catalogue'
assert voice.lookup(\"Who's here?\") is not None, 'the shell cannot find the greeting'
assert voice.lookup('nothing says this') is None, 'a miss should be a miss'
assert voice.catalogue.speechd_rate == -20
" 2>/dev/null; then
    ok "kidnix_shell.prerendered loads the shipped catalogue and finds the greeting"
else
    no "kidnix_shell.prerendered loads the shipped catalogue" \
        "$(python3 -c "
from pathlib import Path
from kidnix_shell.prerendered import select_prerendered
print(select_prerendered(root=Path('${SPEECH}'), language='en-GB'))" 2>&1 | tail -1)"
fi

# A Welsh profile must find nothing: Kokoro v1.0 has no Welsh voice, and an
# English clip on a Welsh label would mispronounce the very letters ADR-0012
# exists to get right.
if [[ ! -e "${SPEECH}/cy" && ! -e "${SPEECH}/pl" ]]; then
    ok "no catalogue for cy or pl (Kokoro has neither voice; they use Piper/espeak-ng)"
else
    no "no catalogue for cy or pl" "an unshipped-language catalogue appeared"
fi

# -----------------------------------------------------------------------------
section "3. what the image must NOT have gained"
# -----------------------------------------------------------------------------
#
# This is the half that makes the trade worth making. If any of it fails, the
# image is paying the 460 MB docs/spikes/tts-kokoro.md 6 rejected.

for module in onnxruntime numpy; do
    if python3 -c "import ${module}" 2>/dev/null; then
        no "python3 cannot import ${module}" "the build-only tree leaked into the image"
    else
        ok "python3 cannot import ${module} (build-only, deleted with its mktemp -d)"
    fi
done

leaked="$(find /usr /opt -name 'onnxruntime*' -o -name 'kokoro*' 2>/dev/null \
    | grep -v '/usr/share/kidnix/speech' | head -3)"
if [[ -z "${leaked}" ]]; then
    ok "no onnxruntime or kokoro tree anywhere in /usr or /opt"
else
    no "no onnxruntime or kokoro tree in /usr or /opt" "${leaked}"
fi

# The 325 MB graph is the single biggest thing that must not have survived.
big="$(find / -xdev -name '*.onnx' -size +200M 2>/dev/null | head -3)"
if [[ -z "${big}" ]]; then
    ok "no .onnx over 200 MB in the image (the Kokoro graph did not survive)"
else
    no "no .onnx over 200 MB in the image" "${big}"
fi

# 65-tts.sh's header is explicit that pip does not belong in a child's OS, and
# this stage was written to avoid needing it.
if rpm -q python3-pip >/dev/null 2>&1; then
    no "python3-pip is not in the image" "the wheel route was supposed to avoid it"
else
    ok "python3-pip is still not in the image (wheels are unzipped, not pip-installed)"
fi

# -----------------------------------------------------------------------------
section "4. playback, and the fallback that must still work"
# -----------------------------------------------------------------------------

# The clips are useless without a decoder, and the decoder is the same
# GStreamer the earcons already use -- no new package at run time either.
for element in oggdemux opusdec playbin; do
    if gst-inspect-1.0 "${element}" >/dev/null 2>&1; then
        ok "GStreamer has ${element}"
    else
        no "GStreamer has ${element}" "a clip would be silence"
    fi
done

# Piper is not replaced. It speaks every composite sentence, every language
# Kokoro has no voice for, and everything at all if a parent changed the rate.
if [[ -x /usr/lib/kidnix/piper/piper ]]; then
    ok "Piper is still the voice for everything not in the catalogue"
else
    no "Piper is still installed" "the fallback for dynamic text is gone"
fi

# -----------------------------------------------------------------------------
section "5. the licence rows"
# -----------------------------------------------------------------------------
#
# Kokoro's weights are Apache-2.0 with no attribution obligation -- better than
# the Piper voice table, where the default voice owes CC-BY-4.0. Two credits
# ARE owed for the training set, and one provenance caveat is recorded because
# it is NOT a licence question and a silence would be worse.

if [[ -f "${SPEECH}/ATTRIBUTION" ]]; then
    ok "the clips carry ${SPEECH}/ATTRIBUTION"
else
    no "the clips carry ${SPEECH}/ATTRIBUTION" "missing"
fi

for needle in \
    "Apache-2.0" \
    "Koniwa" "CC BY 3.0" \
    "SIWIS" "CC BY 4.0" \
    "synthetic audio" \
    "BUILD OUTPUT" \
    "phonemizer"
do
    if grep -qF "${needle}" "${SPEECH}/ATTRIBUTION" 2>/dev/null; then
        ok "the attribution names ${needle}"
    else
        no "the attribution names ${needle}" "a tidy-up dropped an obligation"
    fi
done

# The machine-readable ledger. The clips themselves are build output rather
# than redistributed third-party files -- kidnix synthesised them from its own
# UI strings -- so the tree is recorded once, through the file that carries its
# provenance, rather than as 314 identical rows nobody would read.
if grep -qF "${SPEECH}/ATTRIBUTION"$'\t' "${MANIFEST}" 2>/dev/null; then
    ok "THIRD-PARTY.tsv records the pre-rendered speech tree"
else
    no "THIRD-PARTY.tsv records the pre-rendered speech tree" \
        "no row for ${SPEECH}/ATTRIBUTION"
fi

if grep -F "${SPEECH}/ATTRIBUTION"$'\t' "${MANIFEST}" 2>/dev/null | grep -q "Apache-2.0"; then
    ok "...as Apache-2.0"
else
    no "...as Apache-2.0" "$(grep -F "${SPEECH}" "${MANIFEST}" 2>/dev/null | head -1)"
fi

if grep -qF "${INDEX}"$'\t' "${MANIFEST}" 2>/dev/null; then
    ok "THIRD-PARTY.tsv records the index"
else
    no "THIRD-PARTY.tsv records the index" "no row for ${INDEX}"
fi

printf '\n\033[1m==> %d passed, %d failed\033[0m\n' "${pass}" "${fail}"
(( fail == 0 ))
