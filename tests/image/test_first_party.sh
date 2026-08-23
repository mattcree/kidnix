#!/usr/bin/bash
# Static assertions about the activities kidnix writes itself -- today, Sounds
# & Words. Runs INSIDE the built container, same shape and same helpers as
# test_shell.sh:
#
#   just test-image first_party
#
# What it can prove: the package is installed where the image's Python finds
# it, the corpus travelled with it, the console script the manifest names runs,
# the manifest validates against the SDK's rules and not just the shell's, the
# tile sorts where it is supposed to, the parent's ceiling file behaves as a
# shipped default, and the phoneme audio is exactly as honest on the disk as
# the design note says it is.
#
# What it cannot prove: that any of it draws. That needs a session --
# tests/boot/ and tests/e2e/.
#
# Background: docs/spikes/first-party-install.md, docs/design/sounds-and-words.md.
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

assert_absent() {
    if [[ ! -e "$1" ]]; then _report ok "absent $1"; else _report no "absent $1" "should not exist"; fi
}

assert_grep() {
    if grep -Eq "$1" "$2" 2>/dev/null; then
        _report ok "$3"
    else
        _report no "$3" "no match for /$1/ in $2"
    fi
}

# assert_run <description> <command...> -- the command must exit 0
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

PURELIB="$(python3 -c 'import sysconfig; print(sysconfig.get_path("purelib", "posix_prefix", vars={"base": "/usr", "platbase": "/usr"}))' 2>/dev/null)"
PKG="${PURELIB}/sounds_and_words"
DATA="${PKG}/data"
MANIFEST=/usr/share/kidnix/activities/sounds-and-words.toml
PHONEMES=/usr/share/kidnix/phonemes/en_GB

# The child's own account. Everything below that a child would do is done as
# them, because "the shell can import it" and "the kid can import it" are
# different claims and only the second one matters at 7am.
as_kid() {
    if id kid >/dev/null 2>&1; then
        runuser -u kid -- "$@"
    else
        "$@"
    fi
}

# -----------------------------------------------------------------------------

section "the package"

assert_file "${PKG}/__init__.py"
assert_file "${PKG}/activity.py"
assert_file "${PKG}/phonemes.py"

# cd / so a stray CWD cannot make an import pass against a source tree.
assert_run "sounds_and_words imports as the child, from /usr/lib" \
    as_kid python3 -c '
import sys
import sounds_and_words
sys.exit(0 if sounds_and_words.__file__.startswith("/usr/lib/") else 1)'

# The split the whole activity rests on: the half that proves a child is never
# shown an untaught grapheme must be importable with no display and no GTK.
assert_run "the pure half imports without pulling in gi" \
    as_kid python3 -c '
import sys
import sounds_and_words.ceiling, sounds_and_words.corpus, sounds_and_words.phonemes  # noqa: F401
sys.exit("importing the corpus pulled in gi" if "gi" in sys.modules else 0)'

assert_run "the GTK half imports (GTK4, libadwaita, and the SDK it is written against)" \
    python3 -c '
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk  # noqa: F401
import kidnix_activity  # noqa: F401
import sounds_and_words.activity  # noqa: F401'

# Byte-compiled with unchecked-hash, like the shell: /usr is read-only at
# runtime, so an image with no .pyc re-parses the activity on every launch.
if compgen -G "${PKG}/__pycache__/activity.*.pyc" >/dev/null 2>&1; then
    _report ok "the package is byte-compiled"
else
    _report no "the package is byte-compiled" "no .pyc beside activity.py"
fi

# The metadata a wheel install would have left behind.
assert_run "importlib.metadata knows the version" \
    python3 -c '
from importlib.metadata import version
version("kidnix-sounds-and-words")'

section "the corpus"

for name in graphemes.toml words.toml tricky_words.toml lexicon.toml parent_text.toml sources.toml; do
    assert_file "${DATA}/${name}"
done

# The Open Government Licence attribution has to be in the image, not only in
# the repository (AGENTS.md §5): the corpus is Crown copyright.
assert_file "${PKG}/LICENSES.md"
assert_grep 'Open Government Licence' "${DATA}/graphemes.toml" \
    "the generated corpus carries its OGL attribution"

assert_run "the corpus loads from where the console script points" \
    env KIDNIX_SOUNDS_AND_WORDS_DATA="${DATA}" python3 -c '
import sys
from sounds_and_words.corpus import load_corpus
c = load_corpus()
sys.exit(0 if c.gpcs and c.words and c.lexicon else "the corpus loaded empty")'

section "the console script"

assert_exec /usr/bin/kidnix-sounds-and-words
assert_grep 'KIDNIX_SOUNDS_AND_WORDS_DATA' /usr/bin/kidnix-sounds-and-words \
    "the console script points the corpus at the installed data"
# --help parses and exits before any window is realised, which is as far as a
# container with no display can go.
assert_run "kidnix-sounds-and-words --help runs as the child" \
    as_kid /usr/bin/kidnix-sounds-and-words --help

# --ceiling is a development override. It must exist (screenshots need it) and
# the shipped manifest must not use it.
assert_run "--ceiling is a development override and the manifest does not pass it" \
    python3 - "${MANIFEST}" <<'PY'
import sys, tomllib
data = tomllib.loads(open(sys.argv[1]).read())
if any("--ceiling" in arg for arg in data["exec"]):
    sys.exit("the shipped manifest passes --ceiling")
PY

section "the tile"

assert_file "${MANIFEST}"
assert_run "the manifest validates against the SDK's rules, not just the shell's" \
    /usr/bin/kidnix-activity validate "${MANIFEST}"

assert_run "the tile says the honest things: signal quit, no network, learn, 4-6" \
    python3 - "${MANIFEST}" <<'PY'
import sys, tomllib
d = tomllib.loads(open(sys.argv[1]).read())
want = {
    "id": "sounds-and-words",
    "kind": "activity",
    "quit": "signal",
    "network_required": False,
    "category": "learn",
    "age_band": "4-6",
    "exec": ["/usr/bin/kidnix-sounds-and-words"],
}
for key, value in want.items():
    if d.get(key) != value:
        sys.exit(f"{key} is {d.get(key)!r}, want {value!r}")
if "reading programme" not in d["goal"]:
    sys.exit("the goal no longer refuses the claim it exists to refuse")
if d["audio_label"].strip() == d["name"].strip():
    sys.exit("audio_label says nothing the written label does not")
PY

# The icon is a path, and the file at the end of it exists and is a drawing.
assert_file /usr/share/kidnix/icons/sounds-and-words.svg
assert_run "the tile icon is a path the shell's loader can open" \
    python3 - "${MANIFEST}" <<'PY'
import pathlib, sys, tomllib
d = tomllib.loads(open(sys.argv[1]).read())
if d.get("icon_kind") != "path":
    sys.exit(f"icon_kind is {d.get('icon_kind')!r}")
icon = pathlib.Path(d["icon"])
if not icon.is_absolute() or not icon.is_file():
    sys.exit(f"{icon} is not an absolute path to a file")
if "<svg" not in icon.read_text()[:400]:
    sys.exit(f"{icon} is not an SVG")
PY

# Draw stays the first tile on Home. tests/e2e/test_scenario.py opens the first
# cell of the first row and asserts the launcher started Tux Paint, so a
# re-ordered manifest has to fail here rather than there.
assert_run "Draw is still the first tile and Sounds & words is the second" \
    python3 - <<'PY'
import pathlib, sys, tomllib
order = {}
for path in sorted(pathlib.Path("/usr/share/kidnix/activities").glob("*.toml")):
    d = tomllib.loads(path.read_text())
    order[d["id"]] = d.get("order", 1_000_000)
ranked = [k for k, _ in sorted(order.items(), key=lambda kv: (kv[1], kv[0]))]
if ranked[:2] != ["tuxpaint", "sounds-and-words"]:
    sys.exit(f"Home starts {ranked[:3]}, want Draw then Sounds & words")
PY

assert_run "every shipped manifest still validates through the shell's own loader" \
    /usr/bin/kidnix-shell-app --validate-manifests /usr/share/kidnix/activities

section "the parent's ceiling"

assert_file /etc/kidnix/sounds_and_words.toml

# Shipped fully commented out on purpose. A file that set the ceiling would be
# kidnix's guess handed back to a parent as their own answer -- the activity
# has to be able to say "nobody has told us yet".
assert_run "the shipped ceiling is a template: valid TOML, and it sets nothing" \
    python3 -c '
import sys, tomllib
doc = tomllib.load(open("/etc/kidnix/sounds_and_words.toml", "rb"))
sys.exit(f"it sets {sorted(doc)}" if doc else 0)'

assert_run "with nobody having answered, the ceiling is the built-in floor" \
    env KIDNIX_SOUNDS_AND_WORDS_DATA="${DATA}" python3 -c '
import sys
from sounds_and_words.settings import DEV_DEFAULT_LAST_GRAPHEME, load_parent_ceiling
p = load_parent_ceiling()
if not p.is_default:
    sys.exit(f"read as a grown-up answer, from {p.source}")
if p.last_grapheme != DEV_DEFAULT_LAST_GRAPHEME:
    sys.exit(f"last_grapheme is {p.last_grapheme!r}")'

assert_run "the built-in floor still yields a session's worth of words" \
    env KIDNIX_SOUNDS_AND_WORDS_DATA="${DATA}" python3 -c '
import sys
from sounds_and_words.ceiling import allowed_words
from sounds_and_words.corpus import load_corpus
from sounds_and_words.settings import load_parent_ceiling, resolve
c = load_corpus()
ceiling = resolve(c, load_parent_ceiling())
words = allowed_words(c, ceiling)
if len(ceiling) < 12 or len(words) < 40:
    sys.exit(str(len(ceiling)) + " GPCs and " + str(len(words)) + " words is not a session")'

# The one thing this activity may never do, asserted against the image own
# copy of the corpus rather than against a checkout: every word the gate lets
# through is spelled entirely out of graphemes the ceiling allows, and a word
# needing one it does not is refused by name.
assert_run "the gate refuses a word needing an untaught grapheme, on the image own corpus" \
    env KIDNIX_SOUNDS_AND_WORDS_DATA="${DATA}" python3 -c '
import sys
from sounds_and_words.ceiling import allowed_words, check_word
from sounds_and_words.corpus import load_corpus
from sounds_and_words.settings import load_parent_ceiling, resolve
c = load_corpus()
ceiling = resolve(c, load_parent_ceiling())
for w in allowed_words(c, ceiling):
    verdict = check_word(c, w.text, ceiling)
    if not verdict.allowed:
        sys.exit(w.text + " is offered and refused at the same time")
# "hat" needs h, which Phase 2 set 3 has not taught. It must come back refused
# with the grapheme named -- a refusal that cannot say why is not a gate.
hat = check_word(c, "hat", ceiling)
if hat.allowed or "h" not in hat.blocked_by:
    sys.exit("hat was not refused for h: " + repr(hat))'

section "the phoneme audio, and the ledger that says it is a placeholder"

assert_file "${PHONEMES}/phonemes.toml"
assert_run "the ledger is valid TOML and knows its schema" \
    python3 -c '
import sys, tomllib
d = tomllib.load(open("/usr/share/kidnix/phonemes/en_GB/phonemes.toml", "rb"))
sys.exit(0 if d.get("schema") == 1 and d.get("language") == "en_GB" else "bad header")'

assert_run "there is one ledger row per GPC in the shipped corpus" \
    env KIDNIX_SOUNDS_AND_WORDS_DATA="${DATA}" python3 -c '
import sys, tomllib
from sounds_and_words.corpus import load_corpus
d = tomllib.load(open("/usr/share/kidnix/phonemes/en_GB/phonemes.toml", "rb"))
c = load_corpus()
if {r["id"] for r in d["gpc"]} != {g.id for g in c.gpcs}:
    sys.exit("the ledger and the corpus disagree about which GPCs exist")
if d["summary"]["gpcs"] != len(c.gpcs):
    sys.exit("the summary count is wrong")'

assert_run "every ledger row names a source the code knows how to resolve" \
    python3 -c '
import sys, tomllib
d = tomllib.load(open("/usr/share/kidnix/phonemes/en_GB/phonemes.toml", "rb"))
bad = [r["id"] for r in d["gpc"] if r["source"] not in ("recorded", "spelled")]
sys.exit(f"unknown source on {bad}" if bad else 0)'

# The honesty gate. Every row that claims a recording must have the file, and
# every .ogg in the directory must have a row -- in either direction, a
# mismatch means the ledger is lying about what a child hears.
assert_run "no ledger row claims a clip that is not on the disk, and none is missed" \
    python3 -c '
import pathlib, sys, tomllib
root = pathlib.Path("/usr/share/kidnix/phonemes/en_GB")
d = tomllib.load(open(root / "phonemes.toml", "rb"))
claimed = {r["clip"] for r in d["gpc"] if r["clip"]}
on_disk = {p.name for p in root.glob("*.ogg")}
sys.exit(f"{claimed ^ on_disk}" if claimed != on_disk else 0)'

assert_run "the activity itself agrees with the ledger about what is still a placeholder" \
    env KIDNIX_SOUNDS_AND_WORDS_DATA="${DATA}" python3 -c '
import sys, tomllib
from sounds_and_words.corpus import load_corpus
from sounds_and_words.phonemes import CLIP_DIR, missing_recordings
d = tomllib.load(open(CLIP_DIR / "phonemes.toml", "rb"))
still = missing_recordings(load_corpus().gpcs)
if len(still) != d["summary"]["placeholder"]:
    sys.exit("activity says " + str(len(still)) + ", ledger says " + str(d["summary"]["placeholder"]))'

# The 26 clips unpacked out of GCompris' voices-en_GB. They are the letters'
# NAMES, which is why they are here and not one directory up: playing "ess" for
# /s/ teaches a child the opposite of what their school did.
assert_run "the 26 GCompris letter-name clips unpacked, and are real Ogg streams" \
    python3 -c '
import pathlib, string, sys
root = pathlib.Path("/usr/share/kidnix/phonemes/en_GB/letter-names")
missing = [c for c in string.ascii_lowercase if not (root / f"{c}.ogg").is_file()]
if missing:
    sys.exit(f"missing {missing}")
for c in string.ascii_lowercase:
    blob = (root / f"{c}.ogg").read_bytes()
    if blob[:4] != b"OggS" or len(blob) < 2000:
        sys.exit(f"{c}.ogg is {len(blob)} bytes starting {blob[:4]!r}")'

assert_run "the ledger records the letter-name clips as NOT phonemes, with checksums" \
    python3 -c '
import pathlib, hashlib, sys, tomllib
root = pathlib.Path("/usr/share/kidnix/phonemes/en_GB")
d = tomllib.load(open(root / "phonemes.toml", "rb"))
if d["letter_names"]["are_phonemes"]:
    sys.exit("the ledger claims the letter names are phonemes")
if d["letter_names"]["licence"] != "CC-BY-SA-4.0":
    sys.exit("the letter-name clips have lost their licence")
if len(d["letter_name"]) != 26:
    sys.exit(str(len(d["letter_name"])) + " letter_name rows, expected 26")
for row in d["letter_name"]:
    blob = (root / row["clip"]).read_bytes()
    if hashlib.sha256(blob).hexdigest() != row["sha256"]:
        sys.exit(row["clip"] + " does not match its recorded checksum")'

# CC-BY-SA-4.0. Inside the .rcc the attribution travelled with the bundle;
# unpacked into loose files it has to travel with them.
assert_file /usr/share/kidnix/phonemes/en_GB/letter-names/ATTRIBUTION
assert_grep 'CC-BY-SA-4.0|creativecommons.org/licenses/by-sa/4.0' \
    /usr/share/kidnix/phonemes/en_GB/letter-names/ATTRIBUTION \
    "the unpacked clips carry their CC-BY-SA-4.0 notice"
assert_grep 'GCompris' /usr/share/kidnix/phonemes/en_GB/letter-names/ATTRIBUTION \
    "the unpacked clips credit GCompris by name"

# Nothing may resolve a letter name as if it were a phoneme. The activity's own
# resolver is the only thing that turns a GPC into audio, so asking it directly
# is stronger than grepping for a string.
assert_run "no GPC resolves to a letter-name clip, or to any clip at all" \
    env KIDNIX_SOUNDS_AND_WORDS_DATA="${DATA}" python3 -c '
import sys
from sounds_and_words.corpus import load_corpus
from sounds_and_words.phonemes import Source, phoneme_for
for gpc in load_corpus().gpcs:
    p = phoneme_for(gpc)
    if p.clip is not None:
        sys.exit(gpc.id + " resolved to " + str(p.clip))
    if p.source is not Source.SPELLED or not p.is_placeholder:
        sys.exit(gpc.id + " claims source " + p.source.value)'

# ...and the letter-name directory is not on any path the activity searches.
assert_run "the letter-name directory is one level below the phoneme directory, not in it" \
    python3 -c '
import sys
from sounds_and_words.phonemes import CLIP_DIR
names = CLIP_DIR / "letter-names"
if not names.is_dir():
    sys.exit("the letter-name clips are missing")
if list(CLIP_DIR.glob("*.ogg")):
    sys.exit("an .ogg has appeared in the phoneme directory without a ledger row")'

section "licensing"

assert_file /usr/share/kidnix/THIRD-PARTY.tsv
for path in /usr/share/kidnix/phonemes/en_GB/letter-names \
            /usr/share/kidnix/icons/sounds-and-words.svg; do
    if grep -qF "${path}" /usr/share/kidnix/THIRD-PARTY.tsv; then
        _report ok "THIRD-PARTY.tsv has a row for ${path}"
    else
        _report no "THIRD-PARTY.tsv has a row for ${path}" "no row"
    fi
done
assert_grep 'Open Government Licence|OGL-UK-3.0' /usr/share/kidnix/THIRD-PARTY.tsv \
    "the Letters and Sounds corpus is declared under the OGL"

section "build hygiene"

# The source tree the Containerfile copied in must not survive.
assert_absent /tmp/activities
# Nor may a developer's venv, cache or test suite have travelled with it.
assert_absent "${PKG}/.venv"
assert_absent "${PURELIB}/sounds_and_words/tests"
if find "${PKG}" -name '.pytest_cache' -o -name '.ruff_cache' | grep -q .; then
    _report no "no developer caches in the installed package"
else
    _report ok "no developer caches in the installed package"
fi
# Activities live in /usr, which bootc ships and can roll back.
assert_absent /var/lib/kidnix/sounds-and-words

printf '\n\033[1mfirst-party payload\033[0m\n'
printf '  %-28s %s\n' "sounds_and_words" "$(du -sh "${PKG}" 2>/dev/null | cut -f1)"
printf '  %-28s %s\n' "phonemes/en_GB" "$(du -sh "${PHONEMES}" 2>/dev/null | cut -f1)"

# -----------------------------------------------------------------------------

printf '\n\033[1m%d passed, %d failed\033[0m\n' "${pass}" "${fail}"
[[ "${fail}" -eq 0 ]]
