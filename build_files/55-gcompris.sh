#!/usr/bin/bash
# Turn GCompris from "198 activities" into a shelf of 18.
#
# 50-activities.sh installs gcompris-qt and bakes in its offline voice/word/music
# bundles. This stage is about what the child is allowed to *see*, and it is
# almost entirely assertion: the shelf itself is version-controlled overlay
# content under system_files/usr/share/kidnix/gcompris/, because a curriculum
# mapping belongs in a reviewed file, not in a heredoc.
#
# WHY THIS STAGE EXISTS AT ALL. GCompris has no configuration key that disables
# an activity. ActivityInfoTree::filterEnabledActivities() removes entries whose
# ActivityInfo::enabled() is false, and that is a QML property compiled into the
# binary -- not something a .conf can reach. The only levers are:
#
#   * filterLevelMin/filterLevelMax -- the 1-6 star display filter
#   * the [Favorite] group          -- soft, only affects the menu's first tab
#   * --launch <id>                 -- start one activity, skip the menu entirely
#
# kidnix uses all three, but --launch is the one doing the work. And --launch is
# unforgiving in exactly the wrong direction: given an id GCompris does not
# recognise it does NOT fail, it silently falls through to the full menu. So a
# typo in curated.toml is a lockdown hole that would only show up as a child
# suddenly holding 198 activities. Every id is therefore checked against
# `gcompris-qt --list-activities` here, at build time.
#
# See docs/spikes/gcompris-curation.md for the mechanism write-up and
# system_files/usr/share/kidnix/gcompris/CURATION.md for the shelf itself.
set -euo pipefail

GCOMPRIS_DIR=/usr/share/kidnix/gcompris

# --- 1. the overlay must actually be there -----------------------------------

for file in gcompris-qt.conf curated.toml CURATION.md GENERATION; do
    test -f "${GCOMPRIS_DIR}/${file}" \
        || { echo "missing ${GCOMPRIS_DIR}/${file} from the overlay" >&2; exit 1; }
done
test -f /usr/lib/tmpfiles.d/kidnix-gcompris.conf \
    || { echo "missing the gcompris seeding tmpfiles fragment" >&2; exit 1; }

# --- 2. one source of truth for the settings file ----------------------------
#
# 50-activities.sh parked an earlier draft at
# /usr/share/kidnix/activities/gcompris-qt.conf.default. It is superseded, and
# it was also wrong in a way worth recording: it used a literal [General] group.
# GCompris does m_config.beginGroup("General") on a QSettings::IniFormat file,
# and QSettings reserves [General] for top-level keys -- a real group of that
# name is escaped to [%General] on write and looked for as [%General] on read.
# Everything under a literal [General] parses without error and is then ignored.
# Demonstrated in the image: locale=fr_FR.UTF-8 under [%General] makes
# `gcompris-qt --export-activities-as-sql` emit French activity titles; the same
# line under [General] leaves them in English.
#
# Replaced with a symlink rather than deleted, so the older activity manifests
# and tests/image/test_activities.sh keep resolving the path they know while
# there is exactly one file to review.
install -d /usr/share/kidnix/activities
ln -sfn "${GCOMPRIS_DIR}/gcompris-qt.conf" \
    /usr/share/kidnix/activities/gcompris-qt.conf.default

# --- 3. the curated ids must all exist ---------------------------------------
#
# --list-activities needs a QPA platform; offscreen keeps it off any display.
# HOME/XDG_CONFIG_HOME are redirected so this probe cannot leave a settings file
# behind in the image (GCompris writes one on every exit).
export QT_QPA_PLATFORM=offscreen
export HOME=/tmp/gcompris-probe
export XDG_CONFIG_HOME=/tmp/gcompris-probe/config
mkdir -p "${XDG_CONFIG_HOME}"

gcompris-qt --list-activities >/tmp/gcompris-probe/activities.txt 2>/dev/null

available="$(wc -l </tmp/gcompris-probe/activities.txt)"
echo "==> gcompris-qt reports ${available} activities"
[[ "${available}" -ge 150 ]] \
    || { echo "only ${available} activities listed: --list-activities broke?" >&2; exit 1; }

# tomllib is in base-main's python3, so this is free.
python3 - <<'PY'
import pathlib, sys, tomllib

shelf = tomllib.loads(
    pathlib.Path("/usr/share/kidnix/gcompris/curated.toml").read_text())
available = set(
    pathlib.Path("/tmp/gcompris-probe/activities.txt").read_text().split())

failed = []
def bad(message):
    failed.append(message)

if shelf.get("schema") != 1:
    bad(f"curated.toml schema {shelf.get('schema')!r}, expected 1")

activities = shelf.get("activities", [])
groups = {g["id"]: g for g in shelf.get("groups", [])}

# 05 §3 says 12-20. Below 12 the shelf is thin enough that GCompris is not worth
# its 500 MiB; above 20 it stops being a shelf and starts being a menu again.
if not 12 <= len(activities) <= 20:
    bad(f"{len(activities)} activities on the shelf, want 12-20 (05 §3)")

ids = [a["id"] for a in activities]
if len(ids) != len(set(ids)):
    bad("duplicate id on the shelf")

for a in activities:
    where = a.get("id", "<no id>")
    for key in ("id", "group", "title", "audio_label", "difficulty",
                "curriculum", "exec", "intro_voice_en_GB"):
        if key not in a:
            bad(f"{where}: missing {key!r}")
    # The whole point of this stage: --launch with an unknown id silently opens
    # the full 198-activity menu instead of failing.
    if a["id"] not in available:
        bad(f"{where}: not in gcompris-qt --list-activities")
    if a.get("group") not in groups:
        bad(f"{where}: group {a.get('group')!r} is not declared")
    # 1-2 stars is the 2-6 band, and it is what filterLevelMax=2 enforces.
    if a.get("difficulty") not in (1, 2):
        bad(f"{where}: difficulty {a.get('difficulty')!r}, want 1 or 2")
    exec_argv = a.get("exec", [])
    if exec_argv[:2] != ["gcompris-qt", "--launch"] or exec_argv[2:3] != [a["id"]]:
        bad(f"{where}: exec must be gcompris-qt --launch {a['id']} ...")
    # Belt and braces against a corrupted per-user config handing over the menu.
    if "--hide-home-button" not in exec_argv:
        bad(f"{where}: exec must pass --hide-home-button")

empty = [g for g in groups if not any(a.get("group") == g for a in activities)]
if empty:
    bad(f"groups with no activities: {sorted(empty)}")

if failed:
    for message in failed:
        print(f"curated.toml: {message}", file=sys.stderr)
    sys.exit(1)

print(f"validated {len(activities)} curated activities in {len(groups)} groups")
PY

# --- 4. the settings file and the shelf must agree ---------------------------
#
# [Favorite] is the only config-level expression of "these ones" GCompris has.
# It is a soft filter, but a stale one would put the wrong activities in front
# of a child on the day the menu ever does get reached.
python3 - <<'PY'
import configparser, pathlib, sys, tomllib

conf_path = pathlib.Path("/usr/share/kidnix/gcompris/gcompris-qt.conf")
# QSettings' ini dialect, not Python's: no interpolation, keys are case
# sensitive, and the group really is spelled with a leading '%'.
parser = configparser.RawConfigParser()
parser.optionxform = str
parser.read_string(conf_path.read_text())

shelf = tomllib.loads(
    pathlib.Path("/usr/share/kidnix/gcompris/curated.toml").read_text())
curated = {a["id"] for a in shelf["activities"]}

problems = []

if not parser.has_section("%General"):
    problems.append("no [%General] section -- a literal [General] is ignored "
                    "by QSettings and every setting would silently do nothing")

favourites = {k for k, v in parser.items("Favorite")} \
    if parser.has_section("Favorite") else set()
if favourites != curated:
    problems.append(f"[Favorite] != curated.toml; "
                    f"only in conf: {sorted(favourites - curated)}, "
                    f"only in shelf: {sorted(curated - favourites)}")

# The settings that make this safe for a child with no network and no reading.
required = {
    "locale": "en_GB.UTF-8",
    "enableAudioVoices": "true",
    "enableBackgroundMusic": "false",   # no music under speech (05 §3)
    "enableAutomaticDownloads": "false",  # the child session has no egress
    "kiosk": "true",
    "exitConfirmation": "false",        # a pre-reader cannot answer a dialog
    "homeButtonVisible": "false",
    "sectionVisible": "false",
    "fullscreen": "true",
    "filterLevelMin": "1",
    "filterLevelMax": "2",
    "virtualKeyboard": "false",
}
for key, want in required.items():
    got = parser.get("%General", key, fallback=None)
    if got != want:
        problems.append(f"[%General] {key}={got!r}, want {want!r}")

if problems:
    for problem in problems:
        print(f"gcompris-qt.conf: {problem}", file=sys.stderr)
    sys.exit(1)

print(f"gcompris-qt.conf agrees with the shelf ({len(curated)} favourites)")
PY

# --- 5. GCompris must actually be able to read what we ship ------------------
#
# Static checks cannot prove QSettings parses this file the way GCompris will.
# So: seed the real file into a throwaway XDG_CONFIG_HOME, ask GCompris to dump
# its activity table, and check the dump came back in en_GB. The locale can only
# have come from [%General] locale=en_GB.UTF-8, which means the file parsed and
# the group name is right. "analogue clock" is en_GB; upstream's source string
# is "analog clock".
mkdir -p "${XDG_CONFIG_HOME}/gcompris"
install -m 0600 "${GCOMPRIS_DIR}/gcompris-qt.conf" \
    "${XDG_CONFIG_HOME}/gcompris/gcompris-qt.conf"

gcompris-qt --export-activities-as-sql >/tmp/gcompris-probe/activities.sql 2>/dev/null
grep -q 'analogue clock' /tmp/gcompris-probe/activities.sql || {
    echo "gcompris did not honour locale=en_GB from the shipped config" >&2
    exit 1
}
echo "==> shipped config parsed by gcompris: activity titles came back en_GB"

# GCompris rewrites the settings file through QSettings, which regenerates the
# whole ini (comments and all) rather than patching lines. Confirm our values
# came back out of that round-trip unchanged, and that the [Favorite] group -- a
# group GCompris itself never writes unless a star is clicked -- was preserved
# rather than dropped as unrecognised.
#
# filterLevelMin/Max are deliberately NOT checked here: --export-activities-as-sql
# widens them to 1-6 on purpose so that it can export every activity, and writes
# that back. That is an artefact of this probe, not of normal use -- three real
# `gcompris-qt --launch clockgame` runs against this same file left 1-2 in place,
# along with every other key below. It is also the reason the probe runs against
# a copy in /tmp and never against the file in /usr.
python3 - <<'PY'
import configparser, os, pathlib, sys
parser = configparser.RawConfigParser()
parser.optionxform = str
parser.read_string(
    pathlib.Path(os.environ["XDG_CONFIG_HOME"], "gcompris",
                 "gcompris-qt.conf").read_text())
for key, want in (("locale", "en_GB.UTF-8"), ("kiosk", "true"),
                  ("enableBackgroundMusic", "false"),
                  ("enableAutomaticDownloads", "false"),
                  ("exitConfirmation", "false"),
                  ("homeButtonVisible", "false"),
                  ("baseFontSize", "2")):
    got = parser.get("%General", key, fallback=None)
    if got != want:
        sys.exit(f"{key} came back {got!r} after a gcompris run, want {want!r}")
if not parser.has_section("Favorite"):
    sys.exit("gcompris dropped the [Favorite] group on write")
print("settings round-trip through a real gcompris run: clean")
PY

rm -rf /tmp/gcompris-probe

# --- 6. the voices the shelf depends on --------------------------------------
#
# Half of this shelf is unusable by a pre-reader without spoken instructions.
# 50-activities.sh downloads the en_GB bundle; this asserts it contains the
# directories the curated activities actually draw on. The .rcc name table is
# UTF-16BE, which is why this is a decode rather than a grep.
python3 - <<'PY'
import pathlib, re, sys, tomllib

root = pathlib.Path("/usr/share/gcompris-qt/rcc/data3/voices-ogg")
bundles = sorted(root.glob("voices-en_GB-*.rcc"))
if not bundles:
    sys.exit("no en_GB voice bundle: 50-activities.sh did not run or failed")

names = set(re.findall(
    r"[A-Za-z0-9_.-]{3,60}",
    bundles[0].read_bytes().decode("utf-16-be", "ignore")))

# alphabet/ carries the per-letter recordings click_on_letter and gletters play;
# misc/ the feedback sounds; colors/ everything the colors activity says.
for needed in ("alphabet", "colors", "misc", "intro", "words"):
    if needed not in names:
        sys.exit(f"en_GB voice bundle has no {needed}/ directory")

# Lowercase a-z must be there, because the shelf ships the lowercase letter
# activities and nothing else (UK phonics teaches lowercase first).
missing = [chr(c) for c in range(0x61, 0x7B)
           if "U%04X.ogg" % c not in names]
if missing:
    sys.exit(f"en_GB alphabet voices missing lowercase: {missing}")

shelf = tomllib.loads(
    pathlib.Path("/usr/share/kidnix/gcompris/curated.toml").read_text())
for activity in shelf["activities"]:
    claimed = activity["intro_voice_en_GB"]
    actual = (activity["id"] + ".ogg") in names
    if claimed != actual:
        sys.exit(f"{activity['id']}: intro_voice_en_GB={claimed} "
                 f"but the bundle says {actual}")

voiced = sum(a["intro_voice_en_GB"] for a in shelf["activities"])
print(f"en_GB voices verified; {voiced}/{len(shelf['activities'])} curated "
      f"activities have a spoken introduction")
PY
