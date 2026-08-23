#!/usr/bin/bash
# Install the activities kidnix writes itself: Sounds & Words, Numbers, Clock,
# Letters.
#
# This is the counterpart of 60-shell.sh for the other side of the SDK
# contract: 60 installs `kidnix_activity`, this installs the programs that *use*
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
# ONE LOOP, NOT FOUR COPIES. Until 2026-08-23 this file installed exactly one
# activity and every step was written out by hand. Four activities in, the
# steps are the same steps -- copy the package, write the dist-info a wheel
# would have left, byte-compile, write the console script, install the icon,
# then prove all of it -- and the differences fit in a table. `FIRST_PARTY`
# below is that table, and it has already paid for itself: Letters landed as
# one row, not another two hundred lines of this. What is genuinely specific
# to one activity stays out of the loop and says so: only Sounds & Words has a
# data corpus and a phoneme ledger.
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
#
# WHAT DOES NOT COME FROM HERE. The tile a child presses is an overlay file in
# `system_files/usr/share/kidnix/activities/`, and the grown-up's settings file
# is an overlay file in `system_files/etc/kidnix/`. Both are checked here --
# every tile has to validate against the SDK's stricter rules and agree with the
# activity's own manifest, and every settings file has to be read by the
# activity as "nobody has answered yet" -- but neither is written here. An
# overlay file is in the image before any of this runs, which is what lets
# `bootc` diff and roll it back.
set -euo pipefail

log() { printf '  -- %s\n' "$*"; }
die() { printf 'ERROR: 64-first-party-activities: %s\n' "$*" >&2; exit 1; }

ACTIVITIES=/tmp/activities
LIB="${BUILD_FILES_DIR:-/tmp/build_files}/lib"
TILES=/usr/share/kidnix/activities
ICONS=/usr/share/kidnix/icons

[[ -d "${ACTIVITIES}" ]] \
    || die "${ACTIVITIES} is missing -- the Containerfile must COPY activities/ /tmp/activities/"
[[ -f "${LIB}/rcc.py" ]] || die "${LIB}/rcc.py is missing"

PURELIB="$(python3 -c 'import sysconfig; print(sysconfig.get_path("purelib", "posix_prefix", vars={"base": "/usr", "platbase": "/usr"}))')"
[[ "${PURELIB}" == /usr/lib/* ]] || die "refusing to install outside /usr: ${PURELIB}"
log "site-packages: ${PURELIB}"

# -----------------------------------------------------------------------------
# The table
# -----------------------------------------------------------------------------
#
# One row per activity kidnix wrote. Fields, `|`-separated, in the order the
# loop reads them:
#
#   checkout   the directory under activities/ -- a repository fact
#   package    the importable name, which is NOT always the directory
#              (activities/numbers holds `numbers_activity`, because `numbers`
#              would shadow nothing today and something tomorrow)
#   script     the console script under /usr/bin, and what the tile's `exec`
#              has to name
#   entry      module:function, copied from [project.scripts] in its pyproject
#   tile       the manifest in /usr/share/kidnix/activities. The stem IS the
#              manifest's `id` -- build_files/50-activities.sh rejects any
#              manifest where it is not -- which is why Clock's is
#              `clock-time.toml` and not `clock.toml`
#   icon       the basename under /usr/share/kidnix/icons. A stable path
#              outside site-packages, because site-packages has a Python
#              version in it and a manifest must not
#   config     the grown-up's settings file under /etc/kidnix, or `-` for an
#              activity that has none
#
# Adding the fourth is one row. Nothing below is written per-activity.
FIRST_PARTY=(
    "sounds_and_words|sounds_and_words|kidnix-sounds-and-words|sounds_and_words.activity:main|sounds-and-words.toml|sounds-and-words.svg|sounds_and_words.toml"
    "numbers|numbers_activity|kidnix-numbers|numbers_activity.activity:main|numbers.toml|numbers.svg|numbers.toml"
    "clock_time|clock_time|kidnix-clock-time|clock_time.activity:main|clock-time.toml|clock-time.svg|clock_time.toml"
    "letters_to_family|letters_to_family|kidnix-letters|letters_to_family.activity:main|letters.toml|letters.svg|-"
)

# Sounds & Words' corpus, which is the one payload no other activity has. The
# loop copies it because the row says to; everything that *reads* it -- the
# console script's environment variable, the phoneme ledger in section 4 -- is
# written out by name, because it is genuinely one activity's business.
SRC="${ACTIVITIES}/sounds_and_words"
PKG="${PURELIB}/sounds_and_words"
DATA="${PKG}/data"
[[ -d "${SRC}/data" ]] || die "${SRC}/data is missing"

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
# 1-3. The package, the console script and the icon -- once, for each of them
# -----------------------------------------------------------------------------

# A developer checkout carries __pycache__ compiled by whatever Python they
# have, and a .venv, and pytest's caches. None of it may travel: the image's
# Python could import a stale .pyc, and a venv in site-packages is a second
# interpreter's worth of symlinks pointing at a machine that is not this one.
find "${ACTIVITIES}" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
find "${ACTIVITIES}" -name '*.py[co]' -delete 2>/dev/null || true

install -d "${PURELIB}" "${ICONS}"

for row in "${FIRST_PARTY[@]}"; do
    IFS='|' read -r checkout package script entry tile icon config <<<"${row}"
    src="${ACTIVITIES}/${checkout}"
    dest="${PURELIB}/${package}"
    module="${entry%%:*}"
    function="${entry##*:}"

    [[ -d "${src}/${package}" ]] \
        || die "${src}/${package} is missing -- is the table's package name right?"
    [[ -f "${src}/pyproject.toml" ]] || die "${src}/pyproject.toml is missing"

    version="$(sed -n 's/^version = "\(.*\)"$/\1/p' "${src}/pyproject.toml" | head -1)"
    [[ -n "${version}" ]] || die "could not read version from ${src}/pyproject.toml"
    dist="$(sed -n 's/^name = "\(.*\)"$/\1/p' "${src}/pyproject.toml" | head -1)"
    [[ -n "${dist}" ]] || die "could not read the distribution name from ${src}/pyproject.toml"
    summary="$(sed -n 's/^description = "\(.*\)"$/\1/p' "${src}/pyproject.toml" | head -1)"

    # The console script the tile names has to be the one the activity declares.
    # A table that had drifted from a pyproject would otherwise install a
    # program under a name nothing calls, and the tile would open nothing.
    grep -Fq "${script} = \"${entry}\"" "${src}/pyproject.toml" \
        || die "${src}/pyproject.toml does not declare ${script} = \"${entry}\""

    log "installing ${dist} ${version} as ${package}"

    rm -rf "${dest:?}"
    cp -a "${src}/${package}" "${dest}"

    # Sounds & Words' corpus, in the layout a wheel would have produced
    # (pyproject.toml: [tool.hatch.build.targets.wheel.force-include]
    # "data" = "sounds_and_words/data"). Nothing else has one, and the `-d`
    # test is the whole of the special case.
    if [[ -d "${src}/data" ]]; then
        rm -rf "${dest:?}/data"
        cp -a "${src}/data" "${dest}/data"
    fi

    # An activity's own licence file travels with it when it has one: Sounds &
    # Words' corpus is Crown copyright under the Open Government Licence and the
    # attribution has to be *in the image*, not only in the repository
    # (AGENTS.md §5).
    if [[ -f "${src}/LICENSES.md" ]]; then
        install -m 0644 "${src}/LICENSES.md" "${dest}/LICENSES.md"
    fi

    # The metadata a wheel install would have left behind, so
    # `importlib.metadata.version()` answers and a later `pip list` in a debug
    # shell does not describe a machine that is not there.
    distinfo="${PURELIB}/${dist//-/_}-${version}.dist-info"
    rm -rf "${distinfo:?}"
    install -d "${distinfo}"
    cat >"${distinfo}/METADATA" <<EOF
Metadata-Version: 2.1
Name: ${dist}
Version: ${version}
Summary: ${summary}
License: Apache-2.0
Requires-Python: >=3.11
EOF
    printf 'kidnix-image-build\n' >"${distinfo}/INSTALLER"
    printf '%s\n' "${package}" >"${distinfo}/top_level.txt"

    # /usr is read-only at runtime; without .pyc files the whole activity is
    # re-parsed on every launch and the result can never be cached.
    # `unchecked-hash` keeps the .pyc valid regardless of mtimes, which is what
    # an ostree commit needs.
    python3 -m compileall -q -f --invalidation-mode unchecked-hash "${dest}" \
        || die "byte-compiling ${package} failed"

    # -- the console script --
    #
    # What [project.scripts] would have generated, written by hand because pip
    # is not in this image. Sounds & Words gets one extra line: its corpus
    # resolver looks beside `__file__` for a `data` directory that is only
    # there in a source tree, so the script points it at the installed one --
    # with `setdefault`, so a developer's override still wins.
    {
        printf '#!/usr/bin/python3\n'
        printf '# The %s console script, from [project.scripts] in activities/%s/pyproject.toml.\n' \
            "${script}" "${checkout}"
        printf '# Generated by build_files/64-first-party-activities.sh -- do not edit in the image.\n'
        printf 'import sys\n'
        if [[ "${package}" == "sounds_and_words" ]]; then
            printf 'import os\n\n'
            printf '# sounds_and_words.corpus.data_dir() resolves __file__/../../data, which is\n'
            printf '# the source tree layout and not an installed one. Point it at the corpus\n'
            printf '# this image actually ships. setdefault, so a developer override still wins.\n'
            printf 'os.environ.setdefault("KIDNIX_SOUNDS_AND_WORDS_DATA", "%s")\n' "${DATA}"
        fi
        printf '\nfrom %s import %s\n\n' "${module}" "${function}"
        printf 'if __name__ == "__main__":\n'
        printf '    sys.exit(%s())\n' "${function}"
    } >"/usr/bin/${script}"
    chmod 0755 "/usr/bin/${script}"

    # -- the icon --
    #
    # The drawing belongs to the activity, so it lives in the activity's package
    # (`<package>/icon.svg`) rather than in the shell's own bundled set -- the
    # shell's `data/icons/` is the shell's, and an activity reaching into it
    # would be the wrong ownership. The manifest names an absolute path and
    # `kidnix_shell.widgets.icon_image` loads `icon_kind = "path"` with
    # `Gtk.Image.new_from_file`, so a stable path outside site-packages is what
    # it needs: site-packages has a Python version in it and a manifest must not.
    [[ -f "${dest}/icon.svg" ]] || die "${package} ships no icon.svg"
    install -m 0644 "${dest}/icon.svg" "${ICONS}/${icon}"
done

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

# -- once per activity, from the table ----------------------------------------
for row in "${FIRST_PARTY[@]}"; do
    IFS='|' read -r checkout package script entry tile icon config <<<"${row}"
    module="${entry%%:*}"
    manifest="${TILES}/${tile}"

    # Import from a directory that is definitely not the source tree, so a
    # stray CWD cannot make this pass by accident.
    ( cd / && python3 -c "
import sys
import ${package}
sys.exit(0 if ${package}.__file__.startswith('/usr/lib/') else 1)
" ) || die "${package} does not import from /usr/lib"

    # The GTK half imports. There is no display in a build container, so this
    # realises no window -- but a missing import here is a child tapping a tile
    # and getting nothing at all.
    ( cd / && python3 -c "
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Adw, Gtk  # noqa: F401
import ${module}  # noqa: F401
" ) || die "${module} cannot import GTK4/libadwaita/kidnix_activity"

    # The metadata a wheel install would have left behind. A debug shell that
    # ran `pip list` in this image must not describe a machine that is not here.
    dist="$(sed -n 's/^name = "\(.*\)"$/\1/p' "${ACTIVITIES}/${checkout}/pyproject.toml" | head -1)"
    ( cd / && python3 -c "
from importlib.metadata import version
version('${dist}')
" ) || die "importlib.metadata does not know ${dist}"

    # The console script runs and does what its name says. `--help` exits
    # before any window is realised, which is the only smoke test a build
    # container can run.
    [[ -x "/usr/bin/${script}" ]] || die "/usr/bin/${script} is not executable"
    ( cd / && "/usr/bin/${script}" --help >/dev/null ) \
        || die "/usr/bin/${script} --help failed"

    # The stricter of the two validators (docs/design/activity-sdk.md §9): the
    # shell's parser, plus quit="signal", network_required=false, a goal, an
    # audio_label, an icon and kind="activity".
    [[ -f "${manifest}" ]] || die "${manifest} is missing from the overlay"
    ( cd / && /usr/bin/kidnix-activity validate "${manifest}" >/dev/null ) \
        || die "${manifest} does not validate against the SDK's rules"

    # Everything the manifest points at has to exist, and be what it says. A
    # tile is a promise: a child presses it and something happens.
    [[ -f "${ICONS}/${icon}" ]] || die "${ICONS}/${icon} is missing"
    ( cd / && python3 - "${manifest}" "/usr/bin/${script}" "${ICONS}/${icon}" <<'PY'
import pathlib, sys, tomllib
manifest, script, icon = (pathlib.Path(a) for a in sys.argv[1:4])
data = tomllib.loads(manifest.read_text())
if data["id"] != manifest.stem:
    sys.exit(f"id {data['id']!r} is not the filename {manifest.stem!r}")
if data["exec"] != [str(script)]:
    sys.exit(f"exec is {data['exec']!r}, not [{str(script)!r}]")
if data.get("icon_kind") != "path":
    sys.exit(f"icon_kind is {data.get('icon_kind')!r}")
if data["icon"] != str(icon):
    sys.exit(f"icon is {data['icon']!r}, not {str(icon)!r}")
if "<svg" not in icon.read_text()[:400]:
    sys.exit(f"{icon} is not an SVG")
if data.get("source") != "kidnix":
    sys.exit(f"source is {data.get('source')!r}, not 'kidnix'")
PY
    ) || die "${manifest} promises something the image does not have"

    # The shipped tile and the activity's own manifest must not have drifted
    # apart on anything a child or a parent can perceive. `order` and `icon`
    # are allowed to differ -- they are facts about the image, not about the
    # activity.
    ( cd / && python3 - "${manifest}" "${ACTIVITIES}/${checkout}/manifest.toml" <<'PY'
import sys, tomllib
with open(sys.argv[1], "rb") as fh:
    shipped = tomllib.load(fh)
with open(sys.argv[2], "rb") as fh:
    theirs = tomllib.load(fh)
for key in ("id", "name", "audio_label", "goal", "category", "age_band", "exec",
            "quit", "network_required"):
    if shipped.get(key) != theirs.get(key):
        sys.exit(f"{key}: image has {shipped.get(key)!r}, activity says {theirs.get(key)!r}")
PY
    ) || die "the shipped tile disagrees with ${checkout}'s own manifest"

    # The grown-up's file, and the promise it makes: shipped with every line
    # commented out, so a machine nobody has configured uses the built-in
    # default AND the activity can still say "nobody has told us yet". A file
    # that set a value would be kidnix's own guess handed back to a parent as
    # their answer.
    if [[ "${config}" != "-" ]]; then
        [[ -f "/etc/kidnix/${config}" ]] || die "/etc/kidnix/${config} is missing from the overlay"
        ( cd / && python3 -c "
import sys, tomllib
doc = tomllib.load(open('/etc/kidnix/${config}', 'rb'))
sys.exit(f'it sets {sorted(doc)}' if doc else 0)
" ) || die "/etc/kidnix/${config} is not fully commented out"
    fi
done

# -- Sounds & Words only ------------------------------------------------------

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

grep -q KIDNIX_SOUNDS_AND_WORDS_DATA /usr/bin/kidnix-sounds-and-words \
    || die "the console script does not point the corpus at the installed data"

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

# -- the whole shelf, together ------------------------------------------------

# Numbers and Clock read their grown-up's file the same way, and the same
# claim has to hold: an /etc file with every line commented out parses to
# nothing, and nothing is not an answer. `is_default` staying True is what lets
# a parent pane say "nobody has told us yet" instead of presenting kidnix's own
# defaults back to a grown-up as their statement.
( cd / && python3 - <<'PY'
import sys

from numbers_activity.settings import NumberRange, load_settings as numbers_settings
from clock_time.settings import load_settings as clock_settings
from clock_time.routine import DEFAULT_ROUTINE
from clock_time.words import Mode

numbers = numbers_settings()
if not numbers.is_default:
    sys.exit(f"the shipped numbers.toml was read as an answer, from {numbers.source}")
if numbers.range is not NumberRange.FIVE:
    sys.exit(f"the default range is {numbers.range}")

clock = clock_settings()
if not clock.is_default:
    sys.exit(f"the shipped clock_time.toml was read as an answer, from {clock.source}")
if clock.mode is not Mode.Y1:
    sys.exit(f"the default mode is {clock.mode}")
if clock.routine.items != DEFAULT_ROUTINE:
    sys.exit("the default day is not the built-in one")
print(f"    defaults: numbers={numbers.range.value}, clock={clock.mode.value}, "
      f"{len(clock.routine)} moments")
PY
) || die "a shipped /etc/kidnix settings file does not behave as a default"

# Draw stays the first tile on Home: tests/e2e/test_scenario.py opens the first
# cell of the first row and asserts the launcher started Tux Paint. With eleven
# tiles Home paginates, which is fine -- what must not change is which one is
# first.
( cd / && python3 - <<'PY'
import pathlib, sys, tomllib
orders = {}
for path in sorted(pathlib.Path("/usr/share/kidnix/activities").glob("*.toml")):
    data = tomllib.loads(path.read_text())
    orders[data["id"]] = data.get("order", 1_000_000)
# The tiebreak is the id, so a shared `order` still gives one arrangement and
# not a coin toss. ktuberling has sat at 20 since the first wave and Numbers
# joins it there; Home reads Draw, Sounds & words, Potato man, Numbers, Clock.
ranked = sorted(orders, key=lambda k: (orders[k], k))
if ranked[0] != "tuxpaint":
    sys.exit(f"Home's first tile is now {ranked[0]!r} (order {orders[ranked[0]]}), not Draw")
ours = ["sounds-and-words", "numbers", "clock-time", "letters"]
missing = [tile for tile in ours if tile not in orders]
if missing:
    sys.exit(f"first-party tiles missing from Home: {missing}")
if [tile for tile in ranked if tile in ours] != ours:
    sys.exit(f"the first-party tiles are out of order: {ranked}")
if ranked[1] != "sounds-and-words":
    sys.exit(f"Sounds & words is no longer second: {ranked[:4]}")
print(f"    Home order: {[(k, orders[k]) for k in ranked[:5]]} ({len(orders)} tiles)")
PY
) || die "the first-party tiles do not sit where they are supposed to on Home"

# Every tile in the directory, through the shell's own loader, after ours have
# landed. 60-shell.sh ran this before these three existed.
( cd / && /usr/bin/kidnix-shell-app --validate-manifests /usr/share/kidnix/activities >/dev/null ) \
    || die "a shipped manifest does not validate through the shell's own loader"

rm -rf /tmp/activities

for row in "${FIRST_PARTY[@]}"; do
    IFS='|' read -r _checkout package script _entry _tile _icon _config <<<"${row}"
    log "${package} installed into ${PURELIB}, ${script} on PATH"
done
