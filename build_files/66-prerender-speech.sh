#!/usr/bin/bash
# Pre-rendered speech: Kokoro's voice on the strings a child actually hears,
# for ~4 MB of image and no runtime cost at all.
#
# WHY THIS STAGE EXISTS, AND WHY IT IS NOT A SYNTHESISER
# -----------------------------------------------------
# docs/spikes/tts-kokoro.md measured Kokoro-82M end to end and said NO to
# running it as an engine on the reference ThinkPad: 460 MB of image, 415 MB
# resident (920 MB peak), and a hover label landing 650-830 ms after the pointer
# settles -- past the 700 ms threshold docs/spikes/tts.md 2.3 used to reject the
# one-shot CLI. There is no cheaper tier to fall back to either: fp16 and int8
# are both *slower* than fp32 on a conv-heavy decoder.
#
# What it said YES to is 7.1, and this is it. The shell's speech is a nearly
# closed vocabulary -- tile labels, band prompts, the resting sequence, the
# greeting -- so render it ONCE, here, and ship the audio instead of the model.
# The child hears bf_emma fifty times a day; the image carries no onnxruntime,
# no numpy, no 325 MB graph and no resident server; and every string that is
# NOT in the catalogue (anything with a {placeholder} in it) still goes to
# Piper exactly as it does today. A missing clip is inaudible, not fatal.
#
# WHY THE LICENCE STORY IS BETTER THAN PIPER'S, NOT WORSE
# ------------------------------------------------------
# `kokoro-onnx` (MIT) depends on `phonemizer` (GPL-3.0-or-later) and
# `espeakng-loader` (NO licence metadata at all, and it redistributes a
# prebuilt libespeak-ng.so plus 18 MB of espeak-ng-data). Neither is installed
# here. Kokoro needs only the 114-entry phoneme vocabulary, a 510x1x256 float32
# style array, onnxruntime, numpy and IPA -- so the IPA comes out of *Fedora's*
# espeak-ng(1) as a subprocess, the same arm's-length call ADR-0008's fallback
# voice already makes. docs/spikes/tts-kokoro.md 4.2 checked the two
# phonemisations against each other on eleven real shell strings: 11/11
# identical. Net, the whole stage is Apache-2.0 + MIT + BSD with no
# redistributed GPL binary anywhere -- strictly cleaner than route (a) in
# docs/spikes/tts.md 1.1, which would have been GPL-3.0 piper1-gpl.
#
# WHY WHEELS BY CURL AND NOT pip install
# --------------------------------------
# A wheel is a zip. `pip install` would need python3-pip in the image (the
# thing 65-tts.sh's header explicitly does not want in a child's OS) and a
# `dnf remove` afterwards that can cascade, and it would give us no checksum to
# pin. Two curls and a zipfile.extractall give us both, and the whole tree is a
# mktemp -d that this script deletes on the way out -- so `python3 -c "import
# onnxruntime"` fails in the shipped image, which tests/image/test_prerender.sh
# asserts.
set -euo pipefail

log() { printf '  -- %s\n' "$*"; }
die() { printf '66-prerender-speech: ERROR: %s\n' "$*" >&2; exit 1; }

SPEECH_DIR="/usr/share/kidnix/speech"
LANG_TAG="en_GB"
OUT_DIR="${SPEECH_DIR}/${LANG_TAG}"

# bf_emma is the only one of the eight British Kokoro voices upstream grades
# above C (B-, 10-100 h; the other seven are C or D on 10-100 MINUTES). If it
# ever needs re-trying, this is the one line to change -- no patch required.
VOICE="${KIDNIX_PRERENDER_VOICE:-bf_emma}"

# The floor. If the enumeration in tools/prerender/vocabulary.py silently
# breaks, the image still builds and the shell still talks -- in the wrong
# voice, for everything. This is the tripwire for that, and it is deliberately
# far below the ~314 the tree yields today so that ordinary churn never trips
# it and a collapse always does.
MIN_CLIPS=200
# docs/spikes/tts-kokoro.md 5.4 budgeted ~12 MB for WAV. Ogg/Opus at 48 kbps
# comes in far under that; the brief's ceiling is 20 MB and this is the gate.
MAX_BYTES=$(( 20 * 1024 * 1024 ))

workdir="$(mktemp -d -p /var/tmp prerender.XXXXXX)"
# EVERYTHING below is inside this directory, so the trap is what guarantees the
# runtime image gains nothing: the model, both wheels, and every intermediate
# WAV go with it. 90-cleanup.sh sweeps /var/tmp again afterwards.
trap 'rm -rf "${workdir}"' EXIT

# --- 1. the Python the renderer needs, vendored into a throwaway tree ---------
#
# Pinned per architecture and per interpreter: these are cp314 wheels and
# Fedora 44 is Python 3.14. A silent re-upload must fail the build rather than
# run unreviewed native code inside it.
case "$(uname -m)" in
    x86_64)
        ORT_WHEEL="onnxruntime-1.29.0-cp314-cp314-manylinux_2_28_x86_64.whl"
        ORT_URL="https://files.pythonhosted.org/packages/65/54/9f197c578d3d3d7bea16971e233e5483981228eec73748585cf7b5933403/${ORT_WHEEL}"
        ORT_SHA256="6c0c37b92f67ed68dd36221ce0403e1d9bd4f7efce724439978a2597848530e5"
        NUMPY_WHEEL="numpy-2.5.2-cp314-cp314-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl"
        NUMPY_URL="https://files.pythonhosted.org/packages/c7/99/461bd36dbdfac6c1c53efa370bd55a83227542d0d118f1677dbf1a3dacd5/${NUMPY_WHEEL}"
        NUMPY_SHA256="318b9a4c845dbea06708a29c84ee429cc3065048db34cdb799047643492050ee"
        ;;
    aarch64)
        # NOT MEASURED. docs/spikes/tts-kokoro.md 8 item 5 records that Kokoro
        # has never been built or run on ARM; these are the wheels that exist,
        # pinned so an ARM build is at least reviewable rather than floating.
        ORT_WHEEL="onnxruntime-1.29.0-cp314-cp314-manylinux_2_28_aarch64.whl"
        ORT_URL="https://files.pythonhosted.org/packages/4e/17/c75e78ddc1fe69b6ebaef7fe88ac83f29bfe10955e3a0d2436d93473c91c/${ORT_WHEEL}"
        ORT_SHA256="939e5d65f332e6d399774b2bd0d3559fd8fa629c1e77833db29d968d2384f23d"
        NUMPY_WHEEL="numpy-2.5.2-cp314-cp314-manylinux_2_27_aarch64.manylinux_2_28_aarch64.whl"
        NUMPY_URL="https://files.pythonhosted.org/packages/c4/3b/ecd49dd90033cceb2704d88ca905d4d7d89b0e8c739608754ffd325fa820/${NUMPY_WHEEL}"
        NUMPY_SHA256="50e500dc868e9313530ce12ba470fe50ff3afe3d62993ed6eff652dacd555b65"
        ;;
    *)
        die "no pinned onnxruntime/numpy wheel for $(uname -m)"
        ;;
esac

PYDIR="${workdir}/py"
install -d "${PYDIR}"
for entry in "${ORT_URL}|${ORT_WHEEL}|${ORT_SHA256}" "${NUMPY_URL}|${NUMPY_WHEEL}|${NUMPY_SHA256}"; do
    IFS='|' read -r url filename sha <<<"${entry}"
    log "wheel: ${filename}"
    curl -fsSL --retry 3 --retry-delay 2 -o "${workdir}/${filename}" "${url}"
    echo "${sha}  ${workdir}/${filename}" | sha256sum -c - >/dev/null \
        || die "checksum mismatch for ${filename}"
    # A wheel is a zip. No pip, no python3-pip, nothing left behind.
    python3 -c "
import sys, zipfile
with zipfile.ZipFile(sys.argv[1]) as archive:
    archive.extractall(sys.argv[2])
" "${workdir}/${filename}" "${PYDIR}" || die "could not unpack ${filename}"
    rm -f "${workdir}/${filename}"
done

# --- 2. the model, from the repos with an explicit Apache-2.0 front-matter ----
#
# NOT from thewh1teagle/kokoro-onnx's GitHub release assets, which are a
# different (unlabelled) artefact. docs/spikes/tts-kokoro.md 7 verified that
# onnx-community's per-voice .bin is byte-for-byte the same array as the
# corresponding entry in that release's 28 MB voices-v1.0.bin bundle, so
# nothing is lost by preferring the licensed copy.
#
# onnx-community's export carries no `kokoro_config` metadata, so the 114-entry
# phoneme vocabulary has to come separately, out of hexgrad's own config.json.
MODELDIR="${workdir}/model"
install -d "${MODELDIR}"

ONNX_URL="https://huggingface.co/onnx-community/Kokoro-82M-v1.0-ONNX/resolve/main/onnx/model.onnx"
ONNX_SHA256="8fbea51ea711f2af382e88c833d9e288c6dc82ce5e98421ea61c058ce21a34cb"
VOCAB_URL="https://huggingface.co/hexgrad/Kokoro-82M/resolve/main/config.json"
VOCAB_SHA256="5abb01e2403b072bf03d04fde160443e209d7a0dad49a423be15196b9b43c17f"
VOICE_URL="https://huggingface.co/onnx-community/Kokoro-82M-v1.0-ONNX/resolve/main/voices/${VOICE}.bin"

# Pinned per voice. An override via KIDNIX_PRERENDER_VOICE that is not in this
# table is fetched and *loudly* unpinned: it is a developer trying another
# voice, not something a shipped build may do silently.
case "${VOICE}" in
    bf_emma)   VOICE_SHA256="669fe0647f9dd04fcab92f1439a40eeb4c8b4ab1f82e4996fe3d918ce4a63b73" ;;
    bm_george) VOICE_SHA256="c4b235a4c1f2cd3b939fed08b899ce9385638b763f7b73a59616c4fc9bd6c9bc" ;;
    *)         VOICE_SHA256="" ;;
esac

fetch() {  # url path sha256|""
    local url="$1" path="$2" sha="$3"
    curl -fsSL --retry 3 --retry-delay 2 -o "${path}" "${url}" \
        || die "could not fetch ${url}"
    if [[ -n "${sha}" ]]; then
        echo "${sha}  ${path}" | sha256sum -c - >/dev/null \
            || die "checksum mismatch for $(basename "${path}")"
    else
        printf '  !! UNPINNED: %s sha256 %s\n' \
            "$(basename "${path}")" "$(sha256sum "${path}" | cut -d' ' -f1)" >&2
    fi
}

log "model: Kokoro-82M v1.0 ONNX (325 MB, build-only)"
fetch "${ONNX_URL}"  "${MODELDIR}/model.onnx"        "${ONNX_SHA256}"
log "voice: ${VOICE}"
fetch "${VOICE_URL}" "${MODELDIR}/${VOICE}.bin"      "${VOICE_SHA256}"
log "vocabulary: hexgrad config.json (114 entries)"
fetch "${VOCAB_URL}" "${MODELDIR}/config.json"       "${VOCAB_SHA256}"

# --- 3. render ---------------------------------------------------------------
#
# The vocabulary is derived from the shell rather than kept beside it: an AST
# walk over every gettext literal in kidnix_shell and kidnix_activity, the
# activity manifests' name/audio_label, and two closed-set expansions the shell
# defines itself (next_after's eight phrases, resting's seven weekday words).
# Anything with a {placeholder} in it is skipped by design and spoken by Piper.
#
# WHICH TREES GET WALKED, AND WHY NOT /tmp/shell.
#
# 60-shell.sh deletes its own /tmp/shell at the end, so by the time this stage
# runs the only copy of the shell is the INSTALLED one -- which is the better
# source anyway: it is literally the code that will execute on the machine.
#
# The set is discovered rather than listed. Both 60-shell.sh and
# 64-first-party-activities.sh write a .dist-info with `INSTALLER =
# kidnix-image-build` and a `top_level.txt`, so every first-party Python
# package announces itself and a NEW first-party activity is picked up here
# with no edit to this file. That matters: an activity whose labels are missing
# from the catalogue is one tile that changes voice, which nobody would notice.
#
# The one deliberate exclusion is kidnix_parent_panel. It is a libadwaita app in
# the PARENT's GNOME session (ADR-0005); it never speaks to the child, its
# accessibility story is Orca's, and rendering its strings would spend image
# size on audio nothing plays.
TOOLS=/tmp/prerender
[[ -d "${TOOLS}" ]] || die "${TOOLS} is missing -- the Containerfile must COPY tools/prerender/"
command -v espeak-ng >/dev/null || die "espeak-ng is not installed; 65-tts.sh should have ensured it"
command -v gst-launch-1.0 >/dev/null || die "gst-launch-1.0 is missing; nothing can encode Opus"

PURELIB="$(python3 -c 'import sysconfig; print(sysconfig.get_path("purelib", "posix_prefix", vars={"base": "/usr", "platbase": "/usr"}))')"
[[ -d "${PURELIB}/kidnix_shell" ]] || die "${PURELIB}/kidnix_shell is missing (60-shell.sh did not run?)"

EXCLUDE_PACKAGES="kidnix_parent_panel"
roots=()
for distinfo in "${PURELIB}"/*.dist-info; do
    [[ -f "${distinfo}/INSTALLER" ]] || continue
    [[ "$(cat "${distinfo}/INSTALLER")" == "kidnix-image-build" ]] || continue
    [[ -f "${distinfo}/top_level.txt" ]] || continue
    while read -r package; do
        [[ -n "${package}" ]] || continue
        [[ " ${EXCLUDE_PACKAGES} " == *" ${package} "* ]] && continue
        [[ -d "${PURELIB}/${package}" ]] || continue
        roots+=(--python-root "${PURELIB}/${package}")
    done < "${distinfo}/top_level.txt"
done
(( ${#roots[@]} >= 2 )) \
    || die "found only ${#roots[@]} first-party package(s) to walk; the .dist-info discovery is broken"
log "walking $(( ${#roots[@]} / 2 )) first-party package(s) for spoken literals"

install -d -m 0755 "${SPEECH_DIR}" "${OUT_DIR}"

# `nproc` in a container respects the cgroup CPU quota, so a 2-core CI runner
# does not spawn eight 420 MB workers. Four is the ceiling because each worker
# holds its own onnxruntime session; measured at 175 s wall / 1.4 GB peak on
# four pinned cores for the ~314-string catalogue.
JOBS="${KIDNIX_PRERENDER_JOBS:-$(( $(nproc) < 4 ? $(nproc) : 4 ))}"

started=$(date +%s)
# No --pot: shell/po/kidnix.pot is not installed into the image, and it was
# measurably a STALE SUBSET of the source anyway (twelve N_-marked literals in
# resting.py, including the whole weekday table, were missing from it on
# 2026-08-23). The AST walk over the installed packages is a strict superset.
PYTHONPATH="${PYDIR}:${TOOLS%/*}:${PURELIB}" \
PYTHONDONTWRITEBYTECODE=1 \
    python3 -m prerender.render \
        --model "${MODELDIR}/model.onnx" \
        --voice-style "${MODELDIR}/${VOICE}.bin" \
        --vocab "${MODELDIR}/config.json" \
        --voice-name "${VOICE}" \
        --language "${LANG_TAG}" \
        --out "${OUT_DIR}" \
        "${roots[@]}" \
        --manifest-dir /usr/share/kidnix/activities \
        --manifest-dir /usr/share/kidnix/gcompris \
        --min-clips "${MIN_CLIPS}" \
        --max-bytes "${MAX_BYTES}" \
        --jobs "${JOBS}" \
    || die "the renderer failed; a partial catalogue would change voice at random"
elapsed=$(( $(date +%s) - started ))

# --- 4. the provenance the clips carry with them ------------------------------
#
# Kokoro's weights are Apache-2.0 with no attribution obligation, which is a
# real improvement on the Piper voice table (three of ten en_GB voices were
# unshippable). Two credits ARE owed for the v1.0 training set, and one caveat
# is worth recording precisely because it is not a licence question.
cat >"${SPEECH_DIR}/ATTRIBUTION" <<EOF
Pre-rendered speech clips in ${SPEECH_DIR}.

Written by build_files/66-prerender-speech.sh. These files are BUILD OUTPUT:
kidnix synthesised them here, from its own UI strings, using the model below.
They are not a redistributed corpus. The ledger a human reads is
docs/LICENSES.md; the machine-readable one is
/usr/share/kidnix/THIRD-PARTY.tsv.


THE MODEL -- Apache-2.0, no attribution required
------------------------------------------------

    hexgrad/Kokoro-82M v1.0, 82M params, StyleTTS 2 + ISTFTNet
    https://huggingface.co/hexgrad/Kokoro-82M
    ONNX export: https://huggingface.co/onnx-community/Kokoro-82M-v1.0-ONNX
    model.onnx sha256 ${ONNX_SHA256}
    voice "${VOICE}" and all 54 others ship under the same Apache-2.0 grant

The model itself is NOT in this image. It was fetched into a temporary
directory, used to render the clips beside this file, and deleted before the
layer was committed. Neither is onnxruntime, numpy, or any Python package.


THE TWO CREDITS THE MODEL CARD OWES
-----------------------------------

Kokoro v1.0's training set includes two CC-BY corpora, named on the model card.
They are credited here because the clips are derived from what the model learnt
from them:

    Koniwa (tnc) -- CC BY 3.0 -- https://github.com/koniwa/koniwa
    SIWIS French Speech Synthesis Database -- CC BY 4.0
    https://datashare.ed.ac.uk/handle/10283/2353


A RECORDED CAVEAT, WHICH IS NOT A LICENCE QUESTION
--------------------------------------------------

The Kokoro-82M model card states, in as many words, that v1.0's training data
includes "synthetic audio generated by closed TTS models from large providers",
footnoted to US Copyright Office AI policy guidance. Circumstantially this is
what it looks like: five of Kokoro's American voice names are the names of
OpenAI's original six TTS voices.

Nothing about that changes the Apache-2.0 grant, and the copyright argument
(machine output is not itself copyrightable) is the one the card is gesturing
at. The CONTRACT argument is separate and unresolved: large TTS providers
generally forbid using their outputs to train competing models, and that is a
claim against hexgrad rather than against kidnix. It is written down here
rather than left as a silence, because this project records where every asset
came from. See docs/LICENSES.md and docs/spikes/tts-kokoro.md 4.3.

The Piper voices in /usr/share/kidnix/voices have no equivalent question, and
they remain the voice for every string that is not in index.json.


G2P
---

Phonemes came from Fedora's own espeak-ng (GPL-3.0-or-later), invoked as a
SUBPROCESS at build time. No GPL library was linked and no GPL binary is
redistributed here. In particular this build does NOT use \`phonemizer\`
(GPL-3.0-or-later) or \`espeakng-loader\` (no licence metadata, and it bundles a
prebuilt libespeak-ng.so) -- see docs/spikes/tts-kokoro.md 4.2.
EOF
chmod 0644 "${SPEECH_DIR}/ATTRIBUTION"

# The credits are only discharged if they actually name the corpora. A future
# tidy-up that collapses this into "Apache-2.0, nothing owed" fails here.
for _needle in "Koniwa" "CC BY 3.0" "SIWIS" "CC BY 4.0" "synthetic audio" "Apache-2.0"; do
    grep -qF "${_needle}" "${SPEECH_DIR}/ATTRIBUTION" \
        || die "the Kokoro attribution no longer names ${_needle}"
done

# --- 5. assertions ------------------------------------------------------------

INDEX="${OUT_DIR}/index.json"
[[ -f "${INDEX}" ]] || die "no index.json was written"

clips_on_disk="$(find "${OUT_DIR}" -maxdepth 1 -name '*.ogg' -type f | wc -l)"
(( clips_on_disk >= MIN_CLIPS )) \
    || die "only ${clips_on_disk} clips rendered, wanted at least ${MIN_CLIPS}"

# The index and the directory must agree exactly: an entry with no file is a
# clip a child silently never hears, and a file with no entry is dead weight
# that still costs image size.
python3 - "${INDEX}" "${OUT_DIR}" <<'PY' || die "index.json does not match the clips on disk"
import json, pathlib, sys
index = json.loads(pathlib.Path(sys.argv[1]).read_text())
directory = pathlib.Path(sys.argv[2])
named = {entry["file"] for entry in index["clips"].values()}
on_disk = {path.name for path in directory.glob("*.ogg")}
missing, orphan = named - on_disk, on_disk - named
if missing or orphan:
    print(f"missing {sorted(missing)[:3]} orphan {sorted(orphan)[:3]}", file=sys.stderr)
    raise SystemExit(1)
print(f"  -- index: {len(named)} clips, voice {index['voice']}, rate {index['speechd_rate']}")
PY

# THE line the boot test looks for, and the one a child hears first every
# session. If the greeting is not in the catalogue the enumeration has broken
# in a way the counts above would not catch.
python3 - "${INDEX}" <<'PY' || die "the greeting is not in the catalogue"
import json, pathlib, sys
clips = json.loads(pathlib.Path(sys.argv[1]).read_text())["clips"]
for wanted in ("Who's here?", "Say it again", "Back"):
    if wanted not in clips:
        print(f"{wanted!r} is missing from index.json", file=sys.stderr)
        raise SystemExit(1)
PY

# Every clip must actually be an Ogg stream. A zero-byte or truncated file
# would be silence, and silence is the one failure this whole subsystem is
# designed to make impossible.
bad="$(find "${OUT_DIR}" -maxdepth 1 -name '*.ogg' -size -200c | head -3)"
[[ -z "${bad}" ]] || die "suspiciously small clips: ${bad}"
head -c 4 "$(find "${OUT_DIR}" -maxdepth 1 -name '*.ogg' | head -1)" | grep -q OggS \
    || die "the clips are not Ogg streams"

chmod 0644 "${OUT_DIR}"/*.ogg "${INDEX}"

# --- 6. and NOTHING of the renderer may survive -------------------------------
#
# The whole argument for this stage is that the runtime image gains audio and
# not a machine-learning stack. Check it here rather than only in
# tests/image/test_prerender.sh, so a broken trap fails the build that caused
# it instead of the test run afterwards.
rm -rf "${workdir}"
for forbidden in onnxruntime numpy; do
    if python3 -c "import ${forbidden}" 2>/dev/null; then
        die "${forbidden} is importable in the image; the build-only tree leaked"
    fi
done
if find /usr -maxdepth 6 -name 'onnxruntime*' -not -path '*/kidnix/piper/*' 2>/dev/null | grep -q .; then
    die "an onnxruntime tree survived into /usr"
fi
[[ ! -e "${MODELDIR}/model.onnx" ]] || die "the 325 MB model survived the build"

printf '==> pre-rendered speech: %s clips, %s, voice %s, %ss to render\n' \
    "${clips_on_disk}" "$(du -sh "${SPEECH_DIR}" | cut -f1)" "${VOICE}" "${elapsed}"
