#!/usr/bin/bash
# Neural read-aloud: Piper + the en_GB "alba" and "cori" voices.
#
# ADR-0008 makes speech-dispatcher the one voice API and espeak-ng the
# guaranteed fallback. This stage adds the *good* voice on top: Piper, behind
# speech-dispatcher's `sd_generic` module, fed by a resident server so the
# 114 MB model is loaded once per session instead of once per utterance.
#
# WHY A VENDORED 2023 BINARY AND NOT A PYTHON PACKAGE
# ---------------------------------------------------
# Three routes were measured on 2026-08-22 against the real F44 image
# (docs/spikes/tts.md has the numbers):
#
#   (a) `pip install piper-tts` (OHF-Voice/piper1-gpl 1.7.0, GPL-3.0). The
#       wheel itself is fine -- cp39-abi3, so it works on Fedora 44's Python
#       3.14 -- but it needs onnxruntime. Fedora 44 *does* have
#       python3-onnxruntime 1.22.2 (docs/research/07 §2.4 says it is F45-only;
#       that is wrong for onnxruntime, right for python3-piper-tts). Installing
#       it costs **256 MiB and 21 packages** with weak deps off (sympy 84 MiB,
#       openblas-openmp 44 MiB, numpy 42 MiB) and **1 GiB / 432 packages** with
#       the image's default weak deps on -- which drags in TeX Live and Ruby.
#       Plus pip, which we would rather not have in a child's OS.
#
#   (b) The archived `rhasspy/piper` 2023.11.14-2 release binary. Self-
#       contained C++: piper + libpiper_phonemize + a bundled libonnxruntime.
#       **22 MiB** once trimmed, no RPM dependencies, no Python, MIT
#       throughout. This is what we ship.
#
#   (c) Wait for Fedora 45's python3-piper-tts. Not a today answer.
#
# The trim is the interesting part. Upstream's tarball is 52 MiB because it
# also carries a prebuilt libespeak-ng.so.1.52.0.1 and a 19 MiB
# espeak-ng-data/. We drop both and link against Fedora's espeak-ng 1.52.0
# instead, which is already in the image for the fallback voice. Verified at
# build time below and again in tests/image/test_tts.sh: with
# --noise_scale 0 --noise_w 0 the WAV produced against Fedora's data is
# **byte-identical** to the one produced against the bundled data, so this is
# not an approximation. It also removes the only GPL-3.0 binary we would have
# been redistributing without corresponding source (espeak-ng), leaving the
# vendored tree MIT-only. libtashkeel_model.ort (10 MiB, Arabic diacritics)
# goes for the same reason: unused weight.
set -euo pipefail

die() { echo "65-tts: $*" >&2; exit 1; }

# --- 1. the piper runtime ----------------------------------------------------

PIPER_RELEASE="2023.11.14-2"
PIPER_BASE="https://github.com/rhasspy/piper/releases/download/${PIPER_RELEASE}"
PIPER_PREFIX="/usr/lib/kidnix/piper"

# Pinned per architecture. A silent asset re-upload must fail the build, not
# ship an unreviewed binary into a five-year-old's computer.
case "$(uname -m)" in
    x86_64)
        PIPER_ASSET="piper_linux_x86_64.tar.gz"
        PIPER_SHA256="a50cb45f355b7af1f6d758c1b360717877ba0a398cc8cbe6d2a7a3a26e225992"
        ;;
    aarch64)
        PIPER_ASSET="piper_linux_aarch64.tar.gz"
        PIPER_SHA256="fea0fd2d87c54dbc7078d0f878289f404bd4d6eea6e7444a77835d1537ab88eb"
        ;;
    *)
        die "no pinned piper build for $(uname -m)"
        ;;
esac

workdir="$(mktemp -d)"
trap 'rm -rf "${workdir}"' EXIT

echo "==> piper runtime: ${PIPER_ASSET} (${PIPER_RELEASE})"
curl -fsSL --retry 3 --retry-delay 2 -o "${workdir}/${PIPER_ASSET}" \
    "${PIPER_BASE}/${PIPER_ASSET}"
echo "${PIPER_SHA256}  ${workdir}/${PIPER_ASSET}" | sha256sum -c - >/dev/null \
    || die "checksum mismatch for ${PIPER_ASSET}"

tar -xzf "${workdir}/${PIPER_ASSET}" -C "${workdir}"

install -d -m 0755 "${PIPER_PREFIX}"
# Only the three MIT artefacts. Everything else in the tarball is either a
# duplicate of a Fedora package or dead weight -- see the header.
install -m 0755 "${workdir}/piper/piper" "${PIPER_PREFIX}/piper"
install -m 0644 "${workdir}/piper/libonnxruntime.so.1.14.1" "${PIPER_PREFIX}/"
install -m 0644 "${workdir}/piper/libpiper_phonemize.so.1.2.0" "${PIPER_PREFIX}/"
# `piper` has RUNPATH=$ORIGIN and NEEDED entries for the sonames, so the two
# symlinks are what makes the vendored tree self-locating with no
# LD_LIBRARY_PATH anywhere.
ln -sfn libonnxruntime.so.1.14.1 "${PIPER_PREFIX}/libonnxruntime.so"
ln -sfn libpiper_phonemize.so.1.2.0 "${PIPER_PREFIX}/libpiper_phonemize.so.1"

# --- 2. the voices -----------------------------------------------------------
#
# Two speakers ship. /etc/kidnix/tts.env picks which one loads, with one line.
#
#   alba  (medium, 63 MB)  CC-BY-4.0.  THE DEFAULT since 2026-08-23.
#   cori  (high 114 MB / medium 63 MB)  public domain.  The alternative.
#
# WHY THE DEFAULT MOVED. cori was picked on 2026-08-22 purely because its card
# says public domain -- it was the only en_GB voice with no attribution to
# carry, and at that point nobody in the loop could hear any of them
# (docs/spikes/tts.md 8.7 says so in as many words). A human has now listened,
# and cori was judged bad. That is the only test that ever mattered, so it
# wins over the convenience of owing no attribution.
#
# The cost of alba is exactly one obligation: CC-BY-4.0 attribution, written
# out below into /usr/share/licenses/kidnix-voices/ATTRIBUTION and recorded in
# docs/LICENSES.md 6. AGENTS.md 5 allows this -- it asks for redistributable
# and recorded, not for zero-obligation. What is still refused is unchanged:
# semaine is CC-BY-NC-SA-4.0 (non-commercial, disqualified outright), and
# alan/jenny_dioco state "See URL", which is not a licence.
#
# cori stays in the image rather than being deleted. It is public domain, it
# costs 178 MB, and it is the escape hatch if alba turns out to be wrong too --
# a parent switches back by editing one line, with no rebuild and no network.
VOICE_BASE="https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB"
VOICE_DIR="/usr/share/kidnix/voices"

# relative-url|filename|sha256
#
# Pinned on 2026-08-22 (cori) and 2026-08-23 (alba). Re-checked against a fresh
# fetch from the HF mirror at pin time, and again in tests/image/test_tts.sh: a
# CDN rotation must fail the build, not ship an unreviewed model to a child.
VOICE_FILES=(
    "alba/medium/en_GB-alba-medium.onnx|en_GB-alba-medium.onnx|401369c4a81d09fdd86c32c5c864440811dbdcc66466cde2d64f7133a66ad03b"
    "alba/medium/en_GB-alba-medium.onnx.json|en_GB-alba-medium.onnx.json|aa965a2f02ecced632c2694e1fc72bbff6d65f265fab567ca945918c73dd89f4"
    "alba/medium/MODEL_CARD|en_GB-alba-medium.MODEL_CARD|fa166b1779404c470b0b6b4ba0238bc4a35bf89d2cd130c6788f697188b737d6"
    "cori/high/en_GB-cori-high.onnx|en_GB-cori-high.onnx|470b4dd634c98f8a4850d7626ffc3dfc90774628eeef6605a6dd8f88f30a5903"
    "cori/high/en_GB-cori-high.onnx.json|en_GB-cori-high.onnx.json|9e7fb5b5671612c22f3c81cbe46c1ae87b031a4632bcb509e499dad6f1e2adec"
    "cori/high/MODEL_CARD|en_GB-cori-high.MODEL_CARD|136e7bd168b6c35b4a5df01a0253297e5773b5775ceae0af5160f264aa58208f"
    "cori/medium/en_GB-cori-medium.onnx|en_GB-cori-medium.onnx|1899f98e5fb8310154f3c2973f4b8a929ba7245e722b3d3a85680b833d95f10d"
    "cori/medium/en_GB-cori-medium.onnx.json|en_GB-cori-medium.onnx.json|e262c16d7f192f69d4edd6b4ef8a5915379e67495fcc402f1ab15eeb33da3d36"
)

install -d -m 0755 "${VOICE_DIR}"
for entry in "${VOICE_FILES[@]}"; do
    IFS='|' read -r relurl filename sha <<<"${entry}"
    echo "==> voice: ${filename}"
    curl -fsSL --retry 3 --retry-delay 2 -o "${VOICE_DIR}/${filename}" \
        "${VOICE_BASE}/${relurl}"
    echo "${sha}  ${VOICE_DIR}/${filename}" | sha256sum -c - >/dev/null \
        || die "checksum mismatch for ${filename}"
    chmod 0644 "${VOICE_DIR}/${filename}"
done

# The medium card is the same text with "medium" in it; write it rather than
# spending another round trip on the CDN.
cat >"${VOICE_DIR}/en_GB-cori-medium.MODEL_CARD" <<'EOF'
# Model card for cori (medium)

* Language: en_GB (English, Great Britain)
* Speakers: 1
* Quality: medium
* Samplerate: 22,050Hz

## Dataset

* URL: https://librivox.org
* License: public domain

## Training

See: https://brycebeattie.com/files/tts/

UK English female voice. Single Speaker. Trained from scratch on medium
quality settings for 640 epochs. I put together the dataset, which ended up
with about 24 hours of recordings. All recordings came from LibriVox.org.
EOF
chmod 0644 "${VOICE_DIR}/en_GB-cori-medium.MODEL_CARD"

# --- 2a. the CC-BY-4.0 attribution alba obliges us to carry -------------------
#
# alba's MODEL_CARD names its dataset and its licence URL, and nothing else in
# the image says who to credit. CC-BY-4.0 3(a)(1) wants the creator identified,
# the title, a licence URI, and an indication that the work was modified -- so
# all four are written here rather than left implicit in a DOI.
#
# The wording is the dataset's OWN citation string, copied verbatim from
# datashare.ed.ac.uk/handle/10283/3270, not a paraphrase. The moral-rights
# sentence is likewise verbatim from the corpus's license_text.txt: it is not
# part of CC-BY, the depositors added it, and dropping it would be editing
# someone's licence notice.
#
# "Modified" is the honest word: the shipped .onnx is not the corpus. Piper
# finetuned a U.S. English lessac model on it, and we then resample nothing but
# feed it a different length_scale. The card states the finetune; we state it
# here too so a reader never has to open the card to learn it.
LIC_VOICES="/usr/share/licenses/kidnix-voices"
install -d -m 0755 "${LIC_VOICES}"
cat >"${LIC_VOICES}/ATTRIBUTION" <<'EOF'
Attribution for the voice models in /usr/share/kidnix/voices.

Written by build_files/65-tts.sh. The ledger a human reads is docs/LICENSES.md
section 6 in the kidnix source; the machine-readable one is
/usr/share/kidnix/THIRD-PARTY.tsv.


en_GB-alba-medium  --  CC BY 4.0, ATTRIBUTION REQUIRED
-----------------------------------------------------

This is the voice kidnix speaks in by default.

The model was trained by the Piper project by finetuning the U.S. English
"lessac" medium voice on the Alba speech corpus. Model:

    https://huggingface.co/rhasspy/piper-voices/tree/main/en/en_GB/alba/medium

The corpus, which is where the CC BY 4.0 obligation comes from, is credited
with its depositors' own citation:

    Valentini-Botinhao, Cassia; Yamagishi, Junichi. (2019). Alba speech
    corpus, [dataset]. University of Edinburgh.
    https://doi.org/10.7488/ds/2506.

    https://datashare.ed.ac.uk/handle/10283/3270

Licensed under the Creative Commons Attribution 4.0 International Licence:

    https://creativecommons.org/licenses/by/4.0/

The work has been MODIFIED: kidnix redistributes a neural model finetuned from
those recordings, not the recordings themselves, and synthesises speech with it
at a slower pace than the model's default.

The corpus licence adds a condition that is not part of CC BY, quoted here in
full because it travels with the recordings:

    "The Creative Commons licence does not affect the moral rights of the voice
    talent with respect to the recordings. Any use derogatory to the voice
    talent is prohibited."


en_GB-cori-high, en_GB-cori-medium  --  public domain, no attribution owed
-------------------------------------------------------------------------

Trained by https://brycebeattie.com/files/tts/ on LibriVox recordings; the
voice's own MODEL_CARD states the dataset licence is public domain. Kept in the
image as the switchable alternative to alba. Credited here as a courtesy, not
as an obligation.

    https://huggingface.co/rhasspy/piper-voices/tree/main/en/en_GB/cori
EOF
chmod 0644 "${LIC_VOICES}/ATTRIBUTION"

# The obligation is only discharged if the credit actually names the people.
# A future edit that tidies this into "University of Edinburgh" fails here.
for _needle in "Valentini-Botinhao" "Yamagishi" \
    "creativecommons.org/licenses/by/4.0" "10.7488/ds/2506" "MODIFIED"; do
    grep -qF "${_needle}" "${LIC_VOICES}/ATTRIBUTION" \
        || die "the alba attribution no longer names ${_needle}; CC-BY-4.0 3(a)(1) is not satisfied"
done

# --- 3. licence texts --------------------------------------------------------
#
# The vendored binaries arrive as a tarball, not an RPM, so nothing else puts
# their licences under /usr/share/licenses. AGENTS.md §5 says we carry them.
LIC_DIR="/usr/share/licenses/kidnix-piper"
install -d -m 0755 "${LIC_DIR}"

curl -fsSL --retry 3 -o "${LIC_DIR}/LICENSE.piper.md" \
    "https://raw.githubusercontent.com/rhasspy/piper/${PIPER_RELEASE}/LICENSE.md"
curl -fsSL --retry 3 -o "${LIC_DIR}/LICENSE.piper-phonemize.md" \
    "https://raw.githubusercontent.com/rhasspy/piper-phonemize/master/LICENSE.md"
curl -fsSL --retry 3 -o "${LIC_DIR}/LICENSE.onnxruntime" \
    "https://raw.githubusercontent.com/microsoft/onnxruntime/v1.14.1/LICENSE"
chmod 0644 "${LIC_DIR}"/*

for lic in LICENSE.piper.md LICENSE.piper-phonemize.md LICENSE.onnxruntime; do
    grep -qi "MIT License" "${LIC_DIR}/${lic}" \
        || die "${lic} is no longer the MIT text we reviewed"
done

cat >"${LIC_DIR}/README.kidnix" <<'EOF'
Vendored by build_files/65-tts.sh, not by RPM.

  piper                        MIT  rhasspy/piper 2023.11.14-2 (archived)
  libpiper_phonemize.so.1      MIT  rhasspy/piper-phonemize
  libonnxruntime.so.1.14.1     MIT  microsoft/onnxruntime v1.14.1

The voice models in /usr/share/kidnix/voices are a separate matter, and
they are NOT all on the same footing:

  en_GB-alba-medium    CC BY 4.0   the default voice; ATTRIBUTION REQUIRED
  en_GB-cori-high      public domain
  en_GB-cori-medium    public domain

Each model's own MODEL_CARD ships next to it as the licence evidence. The
credit alba obliges us to carry is at
/usr/share/licenses/kidnix-voices/ATTRIBUTION. See docs/LICENSES.md in the
kidnix source for the ledger.

espeak-ng is NOT vendored here. Piper's phonemiser links against Fedora's
espeak-ng (GPL-3.0-or-later, /usr/share/licenses/espeak-ng/) and reads
/usr/share/espeak-ng-data. Upstream's tarball bundles its own copy; we
delete it precisely so that no GPL binary is redistributed without its
corresponding source.
EOF
chmod 0644 "${LIC_DIR}/README.kidnix"

# --- 4. speech-dispatcher wiring ---------------------------------------------
#
# /etc/speech-dispatcher/speechd.conf is %config(noreplace) and owned by the
# speech-dispatcher RPM, so it cannot live in system_files/ (the dnf
# transactions in earlier stages would fight it). Same reasoning as
# /etc/tuxpaint/tuxpaint.conf in 50-activities.sh: it is written here, and the
# rationale is version-controlled in this comment.
#
# The module *definition* does live in system_files/, at
# /etc/speech-dispatcher/modules/kidnix-piper.conf -- that path is not owned by
# any package, so an overlay file is safe and reviewable.
SPEECHD_CONF="/etc/speech-dispatcher/speechd.conf"
MODULE_CONF="/etc/speech-dispatcher/modules/kidnix-piper.conf"

[[ -f "${SPEECHD_CONF}" ]] || die "${SPEECHD_CONF} missing (speech-dispatcher not installed?)"
[[ -f "${MODULE_CONF}" ]] || die "${MODULE_CONF} missing (system_files overlay not applied?)"
grep -q '^AddModule "espeak-ng"' "${SPEECHD_CONF}" \
    || die "espeak-ng is no longer registered in ${SPEECHD_CONF}; the fallback voice would be gone"

if ! grep -q '^# --- kidnix ---' "${SPEECHD_CONF}"; then
    cat >>"${SPEECHD_CONF}" <<'EOF'

# --- kidnix ---
#
# Appended by build_files/65-tts.sh. Everything above this line is Fedora's.
#
# Order matters: AddModule for espeak-ng is above, so it stays registered and
# `spd-say -o espeak-ng` keeps working. ADR-0008: "a kid session is never mute
# even if Piper is missing".
AddModule "kidnix-piper" "sd_generic" "kidnix-piper.conf"

# The child's voice.
DefaultModule kidnix-piper

# This is a UK household and the phonics matter (docs/research/06 §7.5 #29).
DefaultLanguage "en-GB"

# 06 §5.1: adult oral reading averages 183 wpm and children's comprehension
# rates are lower; §7.5 #30 asks for ~130 wpm. speechd rate is -100..100 and
# the shell asks for -20 on its own connection (shell/kidnix_shell/speech.py);
# -10 is the baseline for everything else that speaks -- spd-say, Orca, the
# parent panel -- so nothing on this machine talks at full tilt at a
# five-year-old.
DefaultRate -10
EOF
fi

# --- 5. enable the resident server for the child session ---------------------
#
# `--global` because `kid` does not exist yet -- systemd-sysusers creates it on
# first boot (build_files/20-users.sh), so there is no home directory to enable
# a user unit into at build time.
#
# The socket goes to sockets.target: it is just a listening socket in
# $XDG_RUNTIME_DIR, costs nothing, and its existence is what stops the very
# first utterance racing the server's startup.
#
# The service's own [Install] is WantedBy=kidnix-shell.service, so the model is
# loaded eagerly when the *child's* shell starts and not at all in the parent's
# GNOME session. That is deliberate: socket activation alone would make the
# first thing a child hears 380 ms late.
systemctl --global enable kidnix-piper.socket
systemctl --global enable kidnix-piper.service

# --- 6. assertions -----------------------------------------------------------

[[ -x "${PIPER_PREFIX}/piper" ]] || die "piper binary missing"
[[ -x /usr/libexec/kidnix-piperd ]] || die "kidnix-piperd missing"
[[ -x /usr/libexec/kidnix-piper-say ]] || die "kidnix-piper-say missing"
[[ -f /usr/lib/systemd/user/kidnix-piper.service ]] || die "kidnix-piper.service missing"
[[ -f /usr/lib/systemd/user/kidnix-piper.socket ]] || die "kidnix-piper.socket missing"
[[ -f /etc/kidnix/tts.env ]] || die "/etc/kidnix/tts.env missing"

# The load-bearing claim of the whole trim: the vendored piper must resolve
# libespeak-ng.so.1 against Fedora's copy. `ldd` with no "not found" is the
# cheap half; actually synthesising is the honest half.
if ldd "${PIPER_PREFIX}/piper" | grep -q "not found"; then
    ldd "${PIPER_PREFIX}/piper" >&2
    die "vendored piper has unresolved libraries"
fi

# Deterministic synthesis (noise off) against Fedora's espeak-ng data. If a
# future Fedora ships an espeak-ng whose phoneme table has moved, the audio
# would silently change; this is the tripwire.
#
# 3ec01a...: sha256 of the WAV for the sentence below with --noise_scale 0
# --noise_w 0, computed on 2026-08-22 against espeak-ng-1.52.0-3.fc44 AND
# against upstream's own bundled espeak-ng-data -- the two were byte-identical,
# which is the evidence for dropping the bundled copy.
probe_wav="${workdir}/probe.wav"
printf 'The quick brown fox jumps over the lazy dog.\n' \
    | "${PIPER_PREFIX}/piper" \
        --model "${VOICE_DIR}/en_GB-cori-high.onnx" \
        --espeak_data /usr/share/espeak-ng-data \
        --noise_scale 0 --noise_w 0 \
        --output_file "${probe_wav}" --quiet \
    || die "vendored piper could not synthesise"

probe_size="$(stat -c %s "${probe_wav}")"
(( probe_size > 40000 )) || die "piper produced only ${probe_size} bytes of audio"
head -c 4 "${probe_wav}" | grep -q RIFF || die "piper output is not a WAV"

# ...and the same for the voice the child will actually hear. The probe above
# is the espeak-ng-data tripwire and stays on cori because that is the model
# its hash was measured against; this one is the far duller question of whether
# the DEFAULT model in tts.env loads at all. A build that ships an alba the
# runtime cannot open would boot into espeak-ng and sound fine to every check
# that only asks whether something was said.
alba_wav="${workdir}/alba.wav"
printf 'The quick brown fox jumps over the lazy dog.\n' \
    | "${PIPER_PREFIX}/piper" \
        --model "${VOICE_DIR}/en_GB-alba-medium.onnx" \
        --espeak_data /usr/share/espeak-ng-data \
        --output_file "${alba_wav}" --quiet \
    || die "vendored piper could not synthesise with the default (alba) voice"
(( "$(stat -c %s "${alba_wav}")" > 40000 )) || die "alba produced no audio"

# The one line that decides what a child hears, checked against the file that
# has to exist for it to mean anything.
_default_model="$(sed -n 's/^KIDNIX_PIPER_MODEL=//p' /etc/kidnix/tts.env)"
[[ "${_default_model}" == "${VOICE_DIR}/en_GB-alba-medium.onnx" ]] \
    || die "tts.env's default voice is '${_default_model}', not alba"
[[ -f "${_default_model}" ]] || die "tts.env points at ${_default_model}, which is not in the image"

# espeak-ng must still be able to speak on its own -- it is the fallback both
# inside kidnix-piper-say and as a separate speech-dispatcher module.
espeak-ng -v en-gb --stdout "fallback check" >"${workdir}/espeak.wav" 2>/dev/null \
    || die "espeak-ng cannot synthesise"
(( "$(stat -c %s "${workdir}/espeak.wav")" > 1000 )) || die "espeak-ng produced no audio"

# The speech-dispatcher module config must name the sd_generic binary that
# actually exists in this Fedora, and our AddModule must point at the conf.
[[ -x /usr/lib64/speech-dispatcher-modules/sd_generic ]] \
    || die "sd_generic is not where Fedora 44 put it"
grep -q '^AddModule "kidnix-piper" "sd_generic" "kidnix-piper.conf"$' "${SPEECHD_CONF}" \
    || die "kidnix-piper is not registered in ${SPEECHD_CONF}"
grep -q '^DefaultModule kidnix-piper$' "${SPEECHD_CONF}" \
    || die "kidnix-piper is not the default module"

# dotconf has no floats, so sd_generic reads Generic*Multiply as HUNDREDTHS:
# `1` is x0.01, not x1.0. Shipping `GenericRateMultiply 1` meant every client's
# rate was multiplied by 0.01 and then truncated to 0 by ForceInteger, so the
# image spoke every sentence at piper's default length_scale 1.000 -- adult
# pace -- instead of the 1.10 the shell asks for, and speech-dispatcher's
# volume was flattened to 1 the same way. Nothing in the container could see
# it; it took a booted VM logging the helper's argv (docs/spikes/tts.md 8).
# Fail the build rather than ship a mute rate control again.
for _scale in Rate Volume Pitch; do
    grep -q "^Generic${_scale}Multiply 100\$" "${MODULE_CONF}" \
        || die "Generic${_scale}Multiply must be 100 (dotconf hundredths: 100 == x1.0); \
speech-dispatcher's ${_scale,,} would never reach piper"
done

# Python is the only runtime the server and client need; both are stdlib-only.
python3 -c 'import array, json, socket, wave' || die "stdlib pieces the TTS server needs are missing"
# Syntax check without py_compile: these files have no .py suffix, so
# py_compile would scatter cache files next to them in the image.
for helper in /usr/libexec/kidnix-piperd /usr/libexec/kidnix-piper-say; do
    python3 -c "import sys; compile(open(sys.argv[1]).read(), sys.argv[1], 'exec')" \
        "${helper}" || die "${helper} does not compile"
done

printf '==> piper %s, voices %s, runtime %s\n' \
    "${PIPER_RELEASE}" \
    "$(du -sh "${VOICE_DIR}" | cut -f1)" \
    "$(du -sh "${PIPER_PREFIX}" | cut -f1)"
