#!/usr/bin/bash
# Install the activities kidnix writes itself -- today, Sounds & Words.
#
# This is the counterpart of 60-shell.sh for the other side of the SDK
# contract: 60 installs `kidnix_activity`, this installs a program that *uses*
# it. Same reasoning about `cp -a` rather than pip (that file's header has it in
# full: hatchling and pip would have to be installed into a child's OS and
# removed again to produce a tree that is byte-for-byte the same as a copy),
# and the same habit of asserting every claim at the bottom.
#
# It runs at 64 because it needs three things that are already true by then:
# GCompris' voice bundles (50), the shell and the SDK's `kidnix-activity
# validate` (60), and the manifest directory the shell reads (60). It does NOT
# need Piper (65) -- see section 4, which is about a sound this image does not
# ship.
#
# WHERE THE DATA GOES, and why it is not obvious.
# `sounds_and_words.corpus.data_dir()` resolves `__file__/../../data`, which is
# right in the source tree (`activities/sounds_and_words/data/`) and wrong in
# any installed layout, including a wheel's -- pyproject.toml force-includes
# `data` at `sounds_and_words/data`. Its docstring names the way out:
# "KIDNIX_SOUNDS_AND_WORDS_DATA overrides, which is how the image build and the
# tests point at a different tree". So the image ships the wheel layout and the
# console script exports that variable. Asserted in section 5 and again in
# tests/image/test_first_party.sh.
set -euo pipefail

log() { printf '  -- %s\n' "$*"; }
die() { printf 'ERROR: 64-first-party-activities: %s\n' "$*" >&2; exit 1; }

SRC=/tmp/activities/sounds_and_words
LIB="${BUILD_FILES_DIR:-/tmp/build_files}/lib"

[[ -d "${SRC}/sounds_and_words" ]] \
    || die "${SRC}/sounds_and_words is missing -- the Containerfile must COPY activities/ /tmp/activities/"
[[ -d "${SRC}/data" ]] || die "${SRC}/data is missing"
[[ -f "${LIB}/rcc.py" ]] || die "${LIB}/rcc.py is missing"

VERSION="$(sed -n 's/^version = "\(.*\)"$/\1/p' "${SRC}/pyproject.toml" | head -1)"
[[ -n "${VERSION}" ]] || die "could not read version from ${SRC}/pyproject.toml"

PURELIB="$(python3 -c 'import sysconfig; print(sysconfig.get_path("purelib", "posix_prefix", vars={"base": "/usr", "platbase": "/usr"}))')"
[[ "${PURELIB}" == /usr/lib/* ]] || die "refusing to install outside /usr: ${PURELIB}"
PKG="${PURELIB}/sounds_and_words"
DATA="${PKG}/data"
log "site-packages: ${PURELIB}"

# -----------------------------------------------------------------------------
# 0. The build's own library has to pass its own tests first
# -----------------------------------------------------------------------------
#
# build_files/lib/rcc.py parses a binary format by hand. It is about to be
# pointed at a 13 MiB file downloaded from a CDN, and a reader that silently
# mis-indexed it would produce plausible-looking rubbish rather than an error.
# The tests build bundles with a writer of their own and round-trip them, which
# is the only way to check a reader without a second implementation.
log "unit-testing the build's Qt resource reader"
( cd "${LIB}" && python3 -m unittest discover -p 'test_*.py' -v ) \
    || die "build_files/lib tests failed"

# -----------------------------------------------------------------------------
# 1. The Python package
# -----------------------------------------------------------------------------

# A developer checkout carries __pycache__ compiled by whatever Python they
# have. Those must never travel: the image's Python could import them.
find /tmp/activities -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
find /tmp/activities -name '*.py[co]' -delete 2>/dev/null || true

install -d "${PURELIB}"
rm -rf "${PKG:?}"
cp -a "${SRC}/sounds_and_words" "${PKG}"

# The corpus, in the layout a wheel would have produced (pyproject.toml:
# [tool.hatch.build.targets.wheel.force-include] "data" = "sounds_and_words/data").
rm -rf "${DATA:?}"
cp -a "${SRC}/data" "${DATA}"

# The activity's own licence file travels with it: the corpus is Crown
# copyright under the Open Government Licence and the attribution has to be
# *in the image*, not only in the repository (AGENTS.md §5).
install -m 0644 "${SRC}/LICENSES.md" "${PKG}/LICENSES.md"

# The metadata a wheel install would have left behind.
DISTINFO="${PURELIB}/kidnix_sounds_and_words-${VERSION}.dist-info"
rm -rf "${DISTINFO}"
install -d "${DISTINFO}"
cat >"${DISTINFO}/METADATA" <<EOF
Metadata-Version: 2.1
Name: kidnix-sounds-and-words
Version: ${VERSION}
Summary: Sounds & Words -- the kidnix literacy activity
License: Apache-2.0
Requires-Python: >=3.11
EOF
printf 'kidnix-image-build\n' >"${DISTINFO}/INSTALLER"
printf 'sounds_and_words\n' >"${DISTINFO}/top_level.txt"

# /usr is read-only at runtime; without .pyc files the whole activity is
# re-parsed on every launch and the result can never be cached. `unchecked-hash`
# keeps the .pyc valid regardless of mtimes, which is what an ostree commit needs.
python3 -m compileall -q -f --invalidation-mode unchecked-hash "${PKG}" \
    || die "byte-compiling sounds_and_words failed"

# -----------------------------------------------------------------------------
# 2. The console script
# -----------------------------------------------------------------------------
#
# pyproject.toml declares `kidnix-sounds-and-words = "sounds_and_words.activity:main"`
# and the shipped manifest's `exec` names this path. It exports the data
# directory (see the header) with `setdefault`, so a developer can still point
# it at a checkout without editing the image.
cat >/usr/bin/kidnix-sounds-and-words <<EOF
#!/usr/bin/python3
# The \`kidnix-sounds-and-words\` console script from
# activities/sounds_and_words/pyproject.toml.
# Generated by build_files/64-first-party-activities.sh -- do not edit in the image.
import os
import sys

# sounds_and_words.corpus.data_dir() resolves __file__/../../data, which is the
# source tree's layout and not an installed one. Point it at the corpus this
# image actually ships. setdefault, so a developer's override still wins.
os.environ.setdefault("KIDNIX_SOUNDS_AND_WORDS_DATA", "${DATA}")

from sounds_and_words.activity import main

if __name__ == "__main__":
    sys.exit(main())
EOF
chmod 0755 /usr/bin/kidnix-sounds-and-words

# -----------------------------------------------------------------------------
# 3. The icon
# -----------------------------------------------------------------------------
#
# The drawing belongs to the activity, so it lives in the activity's package
# (`sounds_and_words/icon.svg`) rather than in the shell's own bundled set --
# the shell's `data/icons/` is the shell's, and an activity reaching into it
# would be the wrong ownership. The manifest names an absolute path and
# `kidnix_shell.widgets.icon_image` loads `icon_kind = "path"` with
# `Gtk.Image.new_from_file`, so a stable path outside site-packages is what it
# needs: site-packages has a Python version in it and a manifest must not.
install -d -m 0755 /usr/share/kidnix/icons
install -m 0644 "${PKG}/icon.svg" /usr/share/kidnix/icons/sounds-and-words.svg

# -----------------------------------------------------------------------------
# 4. The phoneme clips, and the ledger that says there are none
# -----------------------------------------------------------------------------
#
# docs/design/sounds-and-words.md §12.6: "Every phoneme a child hears today is
# a placeholder." This section is the attempt to end that, and the record of
# why it did not.
#
# GCompris ships `voices-en_GB-*.rcc`, CC-BY-SA-4.0, with 26 clips under
# `alphabet/`, and 55-gcompris.sh already asserts they are there. Getting them
# out needed a reader for the Qt resource format (`build_files/lib/rcc.py`;
# `rcc` is a compiler and has no --reverse). They came out fine -- and they are
# the letters' NAMES, not their sounds. Measured on 2026-08-23, three ways:
#
#   * the tail of b c d e g p t v is one shared vowel /i:/ (cosine similarity
#     0.987-0.997 against the 'e' clip), and z is NOT in that group (0.949) --
#     which is exactly right for en_GB, where z is "zed" and not "zee";
#   * w is the only clip in the set with more than one energy burst in it,
#     because "double-you" has three syllables and /w/ has none;
#   * the fricative letters are vowel-dominated (spectral centroid 2.1-2.4 kHz,
#     high/low energy ratio 0.28-0.37), where a pure /s/ or /f/ would be noise
#     above 4 kHz.
#
# The same directory also holds the digits 0-9 and the words ten to twenty,
# which settles it: it is the set click_on_letter and click_on_number read
# character names out of, not a phonics set.
#
# So they are not phonemes and they are not installed as phonemes. A child
# taught to blend who is played "ess ay tee" for `sat` has been told the
# opposite of what their teacher told them -- worse than the "sss" placeholder,
# not better. They ship under letter-names/ labelled as what they are, so that
# the claim above can be checked on the machine that makes it, and so that
# whoever records the real clips has the comparison to hand.
#
# THEY ARE NOT SYNTHESISED EITHER, and Piper is why not. Rendering "sss"
# through Piper at build time produces the same audio the shell already speaks
# live for the same string, so it buys nothing; the SDK has no clip player yet,
# so it would be unplayable; and a synthesised clip landing in this directory
# would make phonemes.missing_recordings() return empty, which is the one
# signal the design note has that the audio is still a placeholder. Design note
# §9 states the rule directly: never synthesise a phoneme.
#
# What ends this is ~20 recordings, one adult, one morning (research 10 §5).

PHONEME_DIR=/usr/share/kidnix/phonemes/en_GB
rm -rf /usr/share/kidnix/phonemes
install -d -m 0755 "${PHONEME_DIR}" "${PHONEME_DIR}/letter-names"

PYTHONPATH="${LIB}" KIDNIX_SOUNDS_AND_WORDS_DATA="${DATA}" \
python3 - "${PHONEME_DIR}" <<'PY'
import hashlib
import pathlib
import sys

from rcc import RccBundle, RccError

from sounds_and_words.corpus import load_corpus
from sounds_and_words.phonemes import Source, missing_recordings, phoneme_for

dest = pathlib.Path(sys.argv[1])
names_dir = dest / "letter-names"

# -- 1. unpack the GCompris a-z clips ---------------------------------------

bundles = sorted(
    pathlib.Path("/usr/share/gcompris-qt/rcc/data3/voices-ogg").glob("voices-en_GB-*.rcc")
)
if not bundles:
    sys.exit("no en_GB voice bundle: 50-activities.sh did not run or failed")
bundle = RccBundle.open(bundles[0])

PREFIX = "/gcompris/data/voices-ogg/en_GB/alphabet/"
letters = {}
for code in range(0x61, 0x7B):
    resource = PREFIX + f"U{code:04X}.ogg"
    try:
        blob = bundle.read(resource)
    except RccError as exc:
        sys.exit(f"{bundle.origin}: {exc}")
    if blob[:4] != b"OggS":
        sys.exit(f"{resource}: unpacked to something that is not an Ogg stream")
    letter = chr(code)
    (names_dir / f"{letter}.ogg").write_bytes(blob)
    letters[letter] = (len(blob), hashlib.sha256(blob).hexdigest())

if len(letters) != 26:
    sys.exit(f"unpacked {len(letters)} letter-name clips, expected 26")

# -- 2. the ledger -----------------------------------------------------------

corpus = load_corpus()
gpcs = sorted(corpus.gpcs, key=lambda g: g.order)

# Computed against what is actually on disk, in the directory the activity
# reads, so this file can never claim a clip that is not there.
resolved = [(gpc, phoneme_for(gpc, clip_dir=dest)) for gpc in gpcs]
recorded = [gpc.id for gpc, ph in resolved if ph.source is Source.RECORDED]
missing = missing_recordings(gpcs, clip_dir=dest)


def q(text):
    return '"' + str(text).replace("\\", "\\\\").replace('"', '\\"') + '"'


out = ['''# GENERATED AT BUILD TIME by build_files/64-first-party-activities.sh.
# Do not edit in the image; edit that file and rebuild.
#
# WHAT A CHILD ACTUALLY HEARS when Sounds & Words says a letter sound, one row
# per grapheme-phoneme correspondence in the corpus, and where that sound came
# from. It is generated by resolving every GPC through
# sounds_and_words.phonemes.phoneme_for() against THIS directory, so it cannot
# claim a recording that is not on the disk beside it.
#
#   source = "recorded"   a real person saying that phoneme. `clip` names it.
#   source = "spelled"    a PLACEHOLDER: the corpus's kidnix-safe spelling
#                         ("sss", "shh", "ay") spoken by the ordinary voice.
#                         Honest for `sss`, thin for `ck`.
#
# There are no recordings yet, and this file is the record of why. The only
# English phoneme recordings kidnix already redistributes are GCompris'
# voices-en_GB, and the a-z clips in it turned out to be the letters' NAMES --
# "ay bee see", the alphabet song -- and not their sounds. See [letter_names]
# below, and the header of build_files/64-first-party-activities.sh for the
# measurements. Nothing here is synthesised: a text-to-speech engine says an
# isolated consonant with a schwa on the end ("suh" for /s/), a child who
# blends "suh-a-tuh" does not get "sat", and their teacher then has to un-teach
# it (docs/design/sounds-and-words.md §9).
#
# What ends this is about twenty recordings: one adult, one morning, one
# microphone, released CC-BY-SA-4.0 as kidnix's own asset.
schema = 1
language = "en_GB"''']
out.append("")
out.append("[summary]")
out.append(f"gpcs = {len(gpcs)}")
out.append(f"recorded = {len(recorded)}")
out.append(f"placeholder = {len(missing)}")
out.append("")
out.append('''# The 26 clips unpacked out of GCompris' voices-en_GB bundle, kept so that the
# claim above can be checked by ear on the machine that makes it. They are
# letter NAMES. Sounds & Words does not read this directory, and no code in
# kidnix does: a name is not a sound, and playing one where the other belongs
# would teach a child the opposite of what their school did.''')
out.append("[letter_names]")
out.append('directory = "letter-names"')
out.append('licence = "CC-BY-SA-4.0"')
out.append('origin = "GCompris voices-en_GB (cdn.kde.org/gcompris/data3/voices-ogg)"')
out.append(f"count = {len(letters)}")
out.append('are_phonemes = false')
out.append('rejected_because = "these are the letters\' names, not their sounds"')
out.append("")
for letter in sorted(letters):
    size, digest = letters[letter]
    out.append("[[letter_name]]")
    out.append(f"letter = {q(letter)}")
    out.append(f"clip = {q('letter-names/' + letter + '.ogg')}")
    out.append(f"bytes = {size}")
    out.append(f"sha256 = {q(digest)}")
    out.append("")

for gpc, phoneme in resolved:
    out.append("[[gpc]]")
    out.append(f"id = {q(gpc.id)}")
    out.append(f"grapheme = {q(gpc.grapheme)}")
    out.append(f"order = {gpc.order}")
    out.append(f"ipa = {q(gpc.ipa)}")
    out.append(f"spoken_label = {q(phoneme.label)}")
    out.append(f"stretchable = {'true' if gpc.stretchable else 'false'}")
    out.append(f"source = {q(phoneme.source.value)}")
    out.append(f"clip = {q(phoneme.clip.name if phoneme.clip else '')}")
    out.append("")

ledger = dest / "phonemes.toml"
ledger.write_text("\n".join(out) + "\n")

# Read it straight back: a generator that emitted invalid TOML would otherwise
# be found by whoever debugs the audio, months from now.
import tomllib  # noqa: E402

data = tomllib.loads(ledger.read_text())
if data["summary"]["gpcs"] != len(gpcs):
    sys.exit("ledger summary disagrees with the corpus")
if len(data["gpc"]) != len(gpcs):
    sys.exit("ledger has the wrong number of rows")
if len(data["letter_name"]) != 26:
    sys.exit("ledger does not list all 26 letter-name clips")
if data["letter_names"]["are_phonemes"]:
    sys.exit("the ledger claims the letter names are phonemes")
if any(row["source"] not in ("recorded", "spelled") for row in data["gpc"]):
    sys.exit("a ledger row has a source nothing knows how to read")
if data["summary"]["recorded"] != sum(1 for r in data["gpc"] if r["source"] == "recorded"):
    sys.exit("ledger summary disagrees with its own rows")

print(
    f"phonemes: {len(gpcs)} GPCs, {len(recorded)} recorded, {len(missing)} still "
    f"placeholders; {len(letters)} GCompris letter-NAME clips kept as evidence"
)
PY

# CC-BY-SA-4.0 attribution. Inside the .rcc it travelled with the bundle
# (docs/LICENSES.md §4: "attribution carried by the bundles"); unpacked into
# loose files it does not, so we carry it, beside the clips rather than in
# /usr/share/licenses where nobody looking at an .ogg would find it.
cat >"${PHONEME_DIR}/letter-names/ATTRIBUTION" <<'EOF'
These 26 Ogg Vorbis files are recordings of an English (en_GB) speaker saying
the NAMES of the letters a to z -- "ay", "bee", "see" -- and not their sounds.

They are the work of the GCompris project and its volunteer voice recorders,
taken unmodified from the bundle

    voices-en_GB-*.rcc
    https://cdn.kde.org/gcompris/data3/voices-ogg/

which the image also ships whole at
/usr/share/gcompris-qt/rcc/data3/voices-ogg/. kidnix unpacked them at build
time with build_files/lib/rcc.py; nothing about the audio was changed.

    (c) The GCompris project and contributors
    https://gcompris.net/
    Licensed under the Creative Commons Attribution-ShareAlike 4.0
    International Licence (CC-BY-SA-4.0)
    https://creativecommons.org/licenses/by-sa/4.0/

WHY THEY ARE HERE. Sounds & Words needs recordings of letter *sounds* --
/s/, /a/, /t/ -- and these are not those. They are kept beside the (empty)
phoneme directory so that the claim in ../phonemes.toml can be checked by ear
on the machine that makes it, and so that whoever records the real clips has
the comparison to hand. No code in kidnix plays them.
EOF

chmod 0644 "${PHONEME_DIR}/phonemes.toml" \
    "${PHONEME_DIR}/letter-names/ATTRIBUTION" \
    "${PHONEME_DIR}"/letter-names/*.ogg

# -----------------------------------------------------------------------------
# 5. Assert the whole thing actually works
# -----------------------------------------------------------------------------

log "verifying the install"

# Import from a directory that is definitely not the source tree, so a stray
# CWD cannot make this pass by accident.
( cd / && python3 -c '
import sys
import sounds_and_words
sys.exit(0 if sounds_and_words.__file__.startswith("/usr/lib/") else 1)
' ) || die "sounds_and_words does not import from /usr/lib"

# The pure half must stay importable with no GTK on the path -- that split is
# the whole reason the ceiling can be proved without a display
# (docs/design/sounds-and-words.md §12). A subprocess, because `gi` may already
# be imported by something else in this shell.
( cd / && python3 -c '
import sys
import sounds_and_words.corpus, sounds_and_words.ceiling, sounds_and_words.phonemes  # noqa: F401
if "gi" in sys.modules:
    sys.exit("importing the corpus pulled in gi")
' ) || die "the pure half of sounds_and_words drags in GTK"

# The corpus loads, through the same environment the console script sets.
( cd / && KIDNIX_SOUNDS_AND_WORDS_DATA="${DATA}" python3 -c '
import sys
from sounds_and_words.corpus import data_dir, load_corpus
corpus = load_corpus()
if not corpus.gpcs or not corpus.words:
    sys.exit("the corpus loaded empty")
print(f"    corpus: {len(corpus.gpcs)} GPCs, {len(corpus.words)} words from {data_dir()}")
' ) || die "the corpus does not load from ${DATA}"

# The GTK half imports. There is no display in a build container, so this
# realises no window -- but a missing import here is a child tapping a tile and
# getting nothing at all.
( cd / && python3 -c '
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk  # noqa: F401
import sounds_and_words.activity  # noqa: F401
' ) || die "sounds_and_words.activity cannot import GTK4/libadwaita/kidnix_activity"

# The console script runs and does what its name says. `--help` exits before
# any window is realised, which is the only smoke test a build container can run.
( cd / && /usr/bin/kidnix-sounds-and-words --help >/dev/null ) \
    || die "/usr/bin/kidnix-sounds-and-words --help failed"

# The stricter of the two validators (docs/design/activity-sdk.md §9): the
# shell's parser, plus quit="signal", network_required=false, a goal, an
# audio_label, an icon and kind="activity".
MANIFEST=/usr/share/kidnix/activities/sounds-and-words.toml
[[ -f "${MANIFEST}" ]] || die "${MANIFEST} is missing from the overlay"
( cd / && /usr/bin/kidnix-activity validate "${MANIFEST}" >/dev/null ) \
    || die "${MANIFEST} does not validate against the SDK's rules"

# The shipped tile and the activity's own manifest must not have drifted apart
# on anything a child or a parent can perceive. `order` and `icon` are allowed
# to differ -- they are facts about the image, not about the activity.
( cd / && python3 - <<PY
import sys, tomllib
with open("${MANIFEST}", "rb") as fh:
    shipped = tomllib.load(fh)
with open("${SRC}/manifest.toml", "rb") as fh:
    theirs = tomllib.load(fh)
for key in ("id", "name", "audio_label", "goal", "category", "age_band", "exec",
            "quit", "network_required"):
    if shipped.get(key) != theirs.get(key):
        sys.exit(f"{key}: image has {shipped.get(key)!r}, activity says {theirs.get(key)!r}")
PY
) || die "the shipped tile disagrees with the activity's own manifest"

# Everything the manifest points at has to exist. A tile is a promise.
[[ -x /usr/bin/kidnix-sounds-and-words ]] || die "the console script is not executable"
[[ -f /usr/share/kidnix/icons/sounds-and-words.svg ]] || die "the tile icon is missing"

# Draw stays the first tile on Home: tests/e2e/test_scenario.py opens the first
# cell of the first row and asserts the launcher started Tux Paint.
( cd / && python3 - <<'PY'
import pathlib, sys, tomllib
orders = {}
for path in sorted(pathlib.Path("/usr/share/kidnix/activities").glob("*.toml")):
    data = tomllib.loads(path.read_text())
    orders[data["id"]] = data.get("order", 1_000_000)
first = min(orders, key=lambda k: (orders[k], k))
if first != "tuxpaint":
    sys.exit(f"Home's first tile is now {first!r} (order {orders[first]}), not Draw")
print(f"    Home order: {sorted(orders.items(), key=lambda kv: kv[1])[:3]}")
PY
) || die "an activity now sorts ahead of Draw on Home"

# The parent's ceiling file, and the promise it makes: shipped commented out,
# so a machine nobody has configured uses the built-in Phase 2 set 3 floor and
# the parent pane can honestly say "nobody has told us yet".
CEILING=/etc/kidnix/sounds_and_words.toml
[[ -f "${CEILING}" ]] || die "${CEILING} is missing from the overlay"
( cd / && KIDNIX_SOUNDS_AND_WORDS_DATA="${DATA}" python3 - <<PY
import sys, tomllib
with open("${CEILING}", "rb") as fh:
    doc = tomllib.load(fh)
if doc:
    sys.exit(f"the shipped ceiling is not fully commented out: {sorted(doc)}")
from sounds_and_words.settings import DEV_DEFAULT_LAST_GRAPHEME, load_parent_ceiling
parent = load_parent_ceiling()
if not parent.is_default:
    sys.exit(f"the shipped ceiling was read as a grown-up's answer, from {parent.source}")
if parent.last_grapheme != DEV_DEFAULT_LAST_GRAPHEME:
    sys.exit(f"the default ceiling is {parent.last_grapheme!r}")
from sounds_and_words.corpus import load_corpus
from sounds_and_words.settings import resolve
corpus = load_corpus()
ceiling = resolve(corpus, parent)
allowed = [w for w in corpus.words if set(w.graphemes) <= ceiling.gpc_ids]
if not allowed or len(ceiling) < 12:
    sys.exit(f"the default ceiling gives {len(ceiling)} GPCs and {len(allowed)} words")
print(f"    default ceiling: {ceiling.label}, {len(ceiling)} GPCs, {len(allowed)} words")
PY
) || die "${CEILING} does not behave as the shipped default"

# The audio, stated honestly: with no clips installed, every GPC must resolve
# to the placeholder. A build that shipped a clip without a ledger row, or a
# ledger row without a clip, is a build that lies about what a child hears.
( cd / && KIDNIX_SOUNDS_AND_WORDS_DATA="${DATA}" python3 - <<'PY'
import pathlib, sys, tomllib
from sounds_and_words.corpus import load_corpus
from sounds_and_words.phonemes import CLIP_DIR, CLIP_LEDGER, missing_recordings

corpus = load_corpus()
if not CLIP_DIR.is_dir():
    sys.exit(f"{CLIP_DIR} was not created")
if not CLIP_LEDGER.is_file():
    sys.exit(f"{CLIP_LEDGER} was not written")
ledger = tomllib.loads(CLIP_LEDGER.read_text())
on_disk = {p.stem for p in CLIP_DIR.glob("*.ogg")}
claimed = {row["clip"].removesuffix(".ogg") for row in ledger["gpc"] if row["clip"]}
if on_disk != claimed:
    sys.exit(f"clips on disk {sorted(on_disk)} != clips in the ledger {sorted(claimed)}")
still = missing_recordings(corpus.gpcs)
if len(still) != ledger["summary"]["placeholder"]:
    sys.exit("the ledger's placeholder count is not what the activity computes")
names = sorted(p.name for p in (CLIP_DIR / "letter-names").glob("*.ogg"))
if len(names) != 26:
    sys.exit(f"{len(names)} letter-name clips, expected 26")
print(f"    phonemes: {len(still)}/{len(corpus.gpcs)} still placeholders, "
      f"{len(names)} letter-NAME clips kept as evidence")
PY
) || die "the phoneme ledger and the clips on disk disagree"

rm -rf /tmp/activities

log "kidnix-sounds-and-words ${VERSION} installed into ${PURELIB}"
