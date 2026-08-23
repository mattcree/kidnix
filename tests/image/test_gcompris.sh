#!/usr/bin/bash
# GCompris is 198 activities; a kidnix child sees 18. This asserts the shelf and
# the settings that make it safe, INSIDE the built image:
#
#   podman run --rm -v "$PWD/tests/image:/tests:ro,z" \
#       --entrypoint /bin/bash localhost/kidnix:latest /tests/test_gcompris.sh
#
# What it can prove: the curated list is the size the research asks for, every
# id on it is an id GCompris actually recognises, every one is within the age
# band by GCompris' own star rating, the settings file is in the dialect
# QSettings reads, the en_GB voices those activities play are on disk, and the
# seeding fragment points at the kid's real config path.
#
# What it cannot prove: that a child can play any of them. That needs a session
# (tests/boot) and, in the end, a five-year-old. See
# docs/spikes/gcompris-curation.md and .../gcompris/CURATION.md.
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

# assert_grep <regex> <file> <description>
assert_grep() {
    if grep -Eq "$1" "$2" 2>/dev/null; then
        _report ok "$3"
    else
        _report no "$3" "no match for /$1/ in $2"
    fi
}

# assert_no_grep <regex> <file> <description>
assert_no_grep() {
    if grep -Eq "$1" "$2" 2>/dev/null; then
        _report no "$3" "unexpected match for /$1/ in $2"
    else
        _report ok "$3"
    fi
}

# assert_py <description> <python source>
assert_py() {
    local description="$1"; shift
    local output
    if output="$(python3 -c "$1" 2>&1)"; then
        _report ok "${description}${output:+ (${output})}"
    else
        _report no "${description}" "${output}"
    fi
}

# assert_cmd <description> <command...>
assert_cmd() {
    local description="$1"; shift
    local output
    if output="$("$@" 2>&1)"; then
        _report ok "${description}${output:+ (${output})}"
    else
        _report no "${description}" "${output}"
    fi
}

section() { printf '\n\033[1m%s\033[0m\n' "$1"; }

readonly GCOMPRIS_DIR=/usr/share/kidnix/gcompris
readonly CONF="${GCOMPRIS_DIR}/gcompris-qt.conf"
readonly SHELF="${GCOMPRIS_DIR}/curated.toml"
readonly VOICES=/usr/share/gcompris-qt/rcc/data3/voices-ogg

# GCompris writes a settings file on exit and wants a cache dir; keep both in
# /tmp so this test cannot mutate the image it is inspecting.
export QT_QPA_PLATFORM=offscreen
export HOME=/tmp/gcompris-test
export XDG_CONFIG_HOME=/tmp/gcompris-test/config
mkdir -p "${XDG_CONFIG_HOME}"

# -----------------------------------------------------------------------------

section "the curated shelf is shipped"
assert_file "${CONF}"
assert_file "${SHELF}"
assert_file "${GCOMPRIS_DIR}/CURATION.md"
assert_file "${GCOMPRIS_DIR}/GENERATION"
assert_file /usr/lib/tmpfiles.d/kidnix-gcompris.conf

# One settings file, not two. 50-activities.sh's earlier draft is superseded by
# a symlink; if it ever becomes a real file again there are two things to review
# and they will drift.
if [[ -L /usr/share/kidnix/activities/gcompris-qt.conf.default ]] &&
   [[ "$(readlink -f /usr/share/kidnix/activities/gcompris-qt.conf.default)" == "${CONF}" ]]; then
    _report ok "the old activities/ default resolves to the curated config"
else
    _report no "the old activities/ default resolves to the curated config" \
        "expected a symlink to ${CONF}"
fi

section "the settings file is in the dialect QSettings actually reads"
# GCompris does beginGroup("General") on a QSettings::IniFormat file. QSettings
# reserves the literal [General] for top-level keys and escapes a real group of
# that name to [%General]. A file written with [General] parses cleanly and is
# then ignored in full -- the single most dangerous mistake available here.
assert_grep '^\[%General\]$' "${CONF}" "settings use the [%General] group"
assert_no_grep '^\[General\]$'  "${CONF}" "settings do NOT use a literal [General] group"
assert_grep '^\[Favorite\]$'    "${CONF}" "settings carry a [Favorite] group"

section "language: this is a UK household and a UK school"
assert_grep '^locale=en_GB\.UTF-8$' "${CONF}" "locale is en_GB.UTF-8"

section "no network: the child session has no egress"
assert_grep '^enableAutomaticDownloads=false$' "${CONF}" \
    "automatic asset downloads disabled (no cdn.kde.org dialog a child cannot read)"

section "no way out, and no dialogs a pre-reader cannot answer"
assert_grep '^kiosk=true$'             "${CONF}" "kiosk mode on"
assert_grep '^exitConfirmation=false$' "${CONF}" "no 'do you really want to quit?' prompt"
assert_grep '^homeButtonVisible=false$' "${CONF}" "no home button back into the 198-activity menu"
assert_grep '^sectionVisible=false$'    "${CONF}" "no section/category bar"
assert_grep '^fullscreen=true$'         "${CONF}" "runs fullscreen"

section "sound: voices are the instructions, music is not"
assert_grep '^enableAudioVoices=true$'      "${CONF}" "spoken voices on (pre-reader first)"
assert_grep '^enableAudioEffects=true$'     "${CONF}" "audio effects on"
# 05 §3 / SYNTHESIS §4: no background music under narration. GCompris ships this
# on by default, so it is an override, not an inherited value.
assert_grep '^enableBackgroundMusic=false$' "${CONF}" "background music OFF (no music under speech)"
assert_grep '^backgroundMusicVolume=0$'     "${CONF}" "background music volume zeroed as well"

section "age band, type and input"
assert_grep '^filterLevelMin=1$' "${CONF}" "difficulty floor is 1 star"
assert_grep '^filterLevelMax=2$' "${CONF}" "difficulty ceiling is 2 stars (the 2-6 band)"
assert_grep '^virtualKeyboard=false$' "${CONF}" "real keyboard, no on-screen one"
assert_grep '^font=Andika-R\.ttf$' "${CONF}" "Andika, a literacy face for emergent readers"
assert_grep '^baseFontSize=2$' "${CONF}" "font size raised for a 4-6 year old"
# Deliberate: AllLowercase (2) would break memory-case-association, whose whole
# job is the uppercase/lowercase mapping. See CURATION.md.
assert_grep '^fontCapitalization=0$' "${CONF}" \
    "capitalisation left MixedCase on purpose (AllLowercase would break case-association)"

section "the shelf: 18 of 198, and every id has to be real"
assert_py "curated.toml parses and is 12-20 activities in populated groups" "
import pathlib, sys, tomllib
shelf = tomllib.loads(pathlib.Path('${SHELF}').read_text())
if shelf.get('schema') != 1: sys.exit('bad schema')
acts = shelf['activities']; groups = {g['id'] for g in shelf['groups']}
if not 12 <= len(acts) <= 20: sys.exit(f'{len(acts)} activities, want 12-20')
ids = [a['id'] for a in acts]
if len(ids) != len(set(ids)): sys.exit('duplicate id')
used = {a['group'] for a in acts}
if used != groups: sys.exit(f'group mismatch: {sorted(groups ^ used)}')
print(f'{len(acts)} activities, {len(groups)} groups')
"

# The load-bearing one. --launch with an id GCompris does not recognise does NOT
# fail -- it silently falls through to the full 198-activity menu. A typo here
# is a lockdown hole, so it is checked against GCompris' own list.
gcompris-qt --list-activities >/tmp/gcompris-test/all.txt 2>/dev/null
assert_py "every curated id exists in gcompris-qt --list-activities" "
import pathlib, sys, tomllib
have = set(pathlib.Path('/tmp/gcompris-test/all.txt').read_text().split())
if len(have) < 150: sys.exit(f'--list-activities returned only {len(have)}')
ids = [a['id'] for a in tomllib.loads(pathlib.Path('${SHELF}').read_text())['activities']]
missing = [i for i in ids if i not in have]
if missing: sys.exit(f'unknown to gcompris: {missing}')
print(f'{len(ids)} of {len(have)}')
"

# GCompris' own star rating, straight out of its activity table, rather than our
# say-so: nothing on the shelf may be rated above 2 stars.
gcompris-qt --export-activities-as-sql >/tmp/gcompris-test/all.sql 2>/dev/null
assert_py "every curated activity is 1-2 stars by GCompris' own rating" "
import pathlib, re, sys, tomllib
stars = {}
for line in pathlib.Path('/tmp/gcompris-test/all.sql').read_text().splitlines():
    m = re.match(r\"INSERT INTO activities VALUES\(\d+, '([^/]+)/[^']*', '[^']*', '.*?', (\d), \", line)
    if m: stars[m.group(1)] = int(m.group(2))
bad = []
for a in tomllib.loads(pathlib.Path('${SHELF}').read_text())['activities']:
    actual = stars.get(a['id'])
    if actual is None: bad.append(f\"{a['id']}: not in the activity table\")
    elif actual > 2: bad.append(f\"{a['id']}: {actual} stars\")
    elif actual != a['difficulty']: bad.append(f\"{a['id']}: says {a['difficulty']}, gcompris says {actual}\")
if bad: sys.exit('; '.join(bad))
print('max 2 stars')
"

assert_py "every exec is gcompris-qt --launch <own id> --hide-home-button" "
import pathlib, sys, tomllib
bad = []
for a in tomllib.loads(pathlib.Path('${SHELF}').read_text())['activities']:
    argv = a['exec']
    if argv[:3] != ['gcompris-qt', '--launch', a['id']]: bad.append(a['id'])
    elif '--hide-home-button' not in argv: bad.append(a['id'] + ' (no --hide-home-button)')
if bad: sys.exit(str(bad))
"

assert_py "[Favorite] in the settings file matches the shelf exactly" "
import configparser, pathlib, sys, tomllib
p = configparser.RawConfigParser(); p.optionxform = str
p.read_string(pathlib.Path('${CONF}').read_text())
fav = {k for k, _ in p.items('Favorite')}
cur = {a['id'] for a in tomllib.loads(pathlib.Path('${SHELF}').read_text())['activities']}
if fav != cur: sys.exit(f'only in conf {sorted(fav-cur)}, only in shelf {sorted(cur-fav)}')
if not all(v == 'true' for _, v in p.items('Favorite')): sys.exit('a favourite is not true')
print(f'{len(fav)} favourites')
"

section "what the shelf deliberately leaves out"
# The kidnix shell makes every mouse button do the same thing and never requires
# a double-click (01 #4-#5, dconf-locked). An activity that trains the opposite
# would contradict the OS the child is holding.
assert_py "nothing on the shelf needs a right-click, double-click or scroll wheel" "
import pathlib, sys, tomllib
banned = {'left_right_click', 'penalty', 'erase_2clic', 'mining', 'clickanddraw'}
ids = {a['id'] for a in tomllib.loads(pathlib.Path('${SHELF}').read_text())['activities']}
hit = ids & banned
if hit: sys.exit(f'present: {sorted(hit)}')
"
# UK phonics teaches lowercase first, and nothing on the shelf may show a child
# whole words from a list with no phase control (05 §2a).
assert_py "no uppercase-first letter activity and no uncontrolled word list" "
import pathlib, sys, tomllib
banned = {'click_on_letter_up', 'letter-in-word', 'alphabet-sequence', 'ordering_alphabets'}
ids = {a['id'] for a in tomllib.loads(pathlib.Path('${SHELF}').read_text())['activities']}
hit = ids & banned
if hit: sys.exit(f'present: {sorted(hit)}')
"
# Drawing belongs to Tux Paint, which is far better at it (05 §3).
assert_py "no drawing activity on the shelf (Tux Paint owns drawing)" "
import pathlib, sys, tomllib
banned = {'simplepaint', 'sketch', 'drawing_wheels', 'drawletters', 'drawnumbers'}
ids = {a['id'] for a in tomllib.loads(pathlib.Path('${SHELF}').read_text())['activities']}
hit = ids & banned
if hit: sys.exit(f'present: {sorted(hit)}')
"
# The four strands the shelf exists to cover. `clockgame` used to be the fourth
# -- Matt asked for clocks and KS1 Y1 Measurement asks for them too -- and came
# off at generation 2 on the early-years teacher's advice; the number strand
# gained `number_sequence` in its place. See the "generation 2" section below.
assert_py "the shelf covers pointer skills, letters, counting and number order" "
import pathlib, sys, tomllib
ids = {a['id'] for a in tomllib.loads(pathlib.Path('${SHELF}').read_text())['activities']}
for needed in ('erase', 'click_on_letter', 'learn_digits', 'number_sequence'):
    if needed not in ids: sys.exit(f'{needed} missing')
"

section "en_GB voices: half this shelf is mute to a pre-reader without them"
assert_py "en_GB bundle carries the alphabet, colours, words and intro voices" "
import pathlib, re, sys
b = sorted(pathlib.Path('${VOICES}').glob('voices-en_GB-*.rcc'))
if not b: sys.exit('no en_GB bundle')
names = set(re.findall(r'[A-Za-z0-9_.-]{3,60}', b[0].read_bytes().decode('utf-16-be','ignore')))
for d in ('alphabet','colors','misc','intro','words'):
    if d not in names: sys.exit(f'no {d}/ in the bundle')
print(f'{b[0].name}')
"
assert_py "en_GB has a recording for every lowercase letter a-z" "
import pathlib, re, sys
b = sorted(pathlib.Path('${VOICES}').glob('voices-en_GB-*.rcc'))[0]
names = set(re.findall(r'[A-Za-z0-9_.-]{3,60}', b.read_bytes().decode('utf-16-be','ignore')))
missing = [chr(c) for c in range(0x61, 0x7B) if 'U%04X.ogg' % c not in names]
if missing: sys.exit(f'missing {missing}')
"
# The shelf records which activities have a spoken introduction, because the
# ones that do not are exactly where the shell's own TTS label has to carry the
# whole instruction. A wrong claim here would hide that gap.
assert_py "intro_voice_en_GB on each activity matches the bundle" "
import pathlib, re, sys, tomllib
b = sorted(pathlib.Path('${VOICES}').glob('voices-en_GB-*.rcc'))[0]
names = set(re.findall(r'[A-Za-z0-9_.-]{3,60}', b.read_bytes().decode('utf-16-be','ignore')))
acts = tomllib.loads(pathlib.Path('${SHELF}').read_text())['activities']
wrong = [a['id'] for a in acts if a['intro_voice_en_GB'] != ((a['id'] + '.ogg') in names)]
if wrong: sys.exit(f'wrong claim: {wrong}')
print(f\"{sum(a['intro_voice_en_GB'] for a in acts)}/{len(acts)} voiced\")
"

section "seeding into the kid account"
# GCompris' only config path is $XDG_CONFIG_HOME/gcompris/gcompris-qt.conf
# (src/core/main.cpp, GenericConfigLocation). There is no system-wide fallback,
# so /var/home/kid has to be seeded at boot.
assert_grep '^C /var/home/kid/\.config/gcompris/gcompris-qt\.conf .* /usr/share/kidnix/gcompris/gcompris-qt\.conf$' \
    /usr/lib/tmpfiles.d/kidnix-gcompris.conf \
    "tmpfiles seeds the settings file into the kid's real config path"
assert_grep '^C /var/home/kid/\.config/gcompris/\.kidnix-generation ' \
    /usr/lib/tmpfiles.d/kidnix-gcompris.conf \
    "tmpfiles seeds a generation marker beside it"
# `C` and not `C+`: an upgrade must never wipe a child's level progress.
assert_no_grep '^C\+ ' /usr/lib/tmpfiles.d/kidnix-gcompris.conf \
    "seeding uses C, not C+ (never clobbers a child's saved progress)"
assert_grep '^d /var/home/kid/\.config/gcompris 0700 kid kid' \
    /usr/lib/tmpfiles.d/kidnix-gcompris.conf \
    "the config directory is created kid-owned and private"
assert_grep '^[0-9]+$' "${GCOMPRIS_DIR}/GENERATION" "GENERATION is a plain integer"
assert_py "curated.toml's generation matches the GENERATION marker" "
import pathlib, sys, tomllib
g = int(pathlib.Path('${GCOMPRIS_DIR}/GENERATION').read_text().strip())
t = tomllib.loads(pathlib.Path('${SHELF}').read_text())['generation']
if g != t: sys.exit(f'GENERATION={g} but curated.toml says {t}')
print(f'generation {g}')
"
# systemd-tmpfiles must be able to parse it at all; a bad line is silent at boot.
if systemd-tmpfiles --cat-config >/dev/null 2>&1; then
    _report ok "systemd-tmpfiles parses the shipped fragments"
else
    _report no "systemd-tmpfiles parses the shipped fragments"
fi

section "the shelf is wired to the tile"
# The 2026-08-23 early-years-teacher review's BLOCKER: "the tile a parent boots
# opens the full 198-activity menu while 18 detailed EYFS/KS1 mappings sit
# unreachable." These assertions are that sentence, inverted.
readonly SHELF_TILE=/usr/share/kidnix/activities/gcompris.toml
readonly CHILDREN=/usr/share/kidnix/activities/gcompris

assert_file "${SHELF_TILE}"
assert_cmd "the children directory exists" test -d "${CHILDREN}"
assert_py "the tile declares itself a shelf pointing at the children directory" "
import pathlib, sys, tomllib
m = tomllib.loads(pathlib.Path('${SHELF_TILE}').read_text())
if m.get('kind') != 'shelf': sys.exit(f\"kind is {m.get('kind')!r}\")
if m.get('children_dir') != 'gcompris': sys.exit(f\"children_dir is {m.get('children_dir')!r}\")
print('kind=shelf children_dir=gcompris')
"
assert_py "there is one child manifest per curated activity, and the ids line up" "
import pathlib, sys, tomllib
curated = {a['id'] for a in tomllib.loads(pathlib.Path('${SHELF}').read_text())['activities']}
children = sorted(pathlib.Path('${CHILDREN}').glob('*.toml'))
ids = {tomllib.loads(p.read_text())['id'] for p in children}
want = {f'gcompris.{i}' for i in curated}
if ids != want: sys.exit(f'only in files: {sorted(ids-want)}; only in curated.toml: {sorted(want-ids)}')
print(f'{len(children)} children')
"
assert_py "every child manifest carries what a tile needs to be drawn and spoken" "
import pathlib, sys, tomllib
bad = []
for p in sorted(pathlib.Path('${CHILDREN}').glob('*.toml')):
    d = tomllib.loads(p.read_text())
    if d['id'] != p.stem: bad.append(f'{p.name}: id != filename')
    for key in ('name','audio_label','goal','icon','age_band','exec','category'):
        if not d.get(key): bad.append(f'{p.name}: no {key}')
    # The instruction a pre-reader hears has to be an instruction, not a label:
    # 'Count the dots on the dice, then press that number', never 'Dice dots'.
    if len(d.get('audio_label','')) < 12: bad.append(f'{p.name}: audio_label too short to instruct')
    if len(d.get('goal','')) < 40: bad.append(f'{p.name}: goal too short to inform a parent')
if bad: sys.exit('; '.join(bad))
print('18 tiles have name, spoken instruction, goal, icon and band')
"
# The number strand is where a pre-reader most needs telling what to DO -- the
# review's example was 'Count the ducks and press the number'. Every counting
# and numbers tile must read like an instruction: a verb, first word.
assert_py "every counting/numbers tile's spoken label starts with a verb" "
import pathlib, sys, tomllib
VERBS = {'count','listen','find','put','tidy','join','make','drag','press','type','show'}
bad = []
n = 0
for p in sorted(pathlib.Path('${CHILDREN}').glob('*.toml')):
    d = tomllib.loads(p.read_text())
    if d.get('shelf_group') not in ('counting', 'numbers'): continue
    n += 1
    first = d['audio_label'].split()[0].lower().strip(',')
    if first not in VERBS: bad.append(f\"{d['id']}: starts with {first!r}\")
if n < 6: sys.exit(f'only {n} number-strand tiles, expected at least 6')
if bad: sys.exit('; '.join(bad))
print(f'{n} number-strand tiles')
"
# The load-bearing one, restated over the generated files: nothing in this
# image can start gcompris-qt without --launch, so the 198-activity menu is
# not reachable from any tile, including the shelf tile's own fallback.
assert_py "no manifest anywhere starts gcompris-qt without --launch" "
import pathlib, sys, tomllib
bad = []
for p in list(pathlib.Path('/usr/share/kidnix/activities').glob('*.toml')) + \
         list(pathlib.Path('${CHILDREN}').glob('*.toml')):
    d = tomllib.loads(p.read_text())
    argv = d.get('exec', [])
    if argv and argv[0] == 'gcompris-qt' and '--launch' not in argv:
        bad.append(p.name)
if bad: sys.exit(f'these open the full menu: {bad}')
print('every gcompris exec is --launch')
"
assert_py "every child exec is --launch <its own id> --hide-home-button" "
import pathlib, sys, tomllib
bad = []
for p in sorted(pathlib.Path('${CHILDREN}').glob('*.toml')):
    d = tomllib.loads(p.read_text())
    want = d['id'].split('.', 1)[1]
    argv = d['exec']
    if argv[:3] != ['gcompris-qt', '--launch', want]: bad.append(d['id'])
    elif '--hide-home-button' not in argv: bad.append(d['id'] + ' (no --hide-home-button)')
if bad: sys.exit(str(bad))
"
# The children are in a SUBdirectory precisely so they cannot become 18 extra
# tiles on Home: the shell globs *.toml in one directory and does not recurse.
assert_py "the children do not leak onto Home" "
import pathlib, sys
top = {p.stem for p in pathlib.Path('/usr/share/kidnix/activities').glob('*.toml')}
leaked = sorted(t for t in top if t.startswith('gcompris.'))
if leaked: sys.exit(f'{leaked} are in the Home directory')
print(f'{len(top)} Home manifests, none of them shelf children')
"
# The shell's own loader, not tomllib: this is the parse that actually happens.
assert_cmd "the shell's manifest loader accepts every child" \
    /usr/bin/kidnix-shell-app --validate-manifests "${CHILDREN}"

section "generation 2: the clock came off the shelf"
# The early-years teacher: "Time to the hour is Year 1 Measurement, in practice
# the summer term; most Reception children cannot yet hold 'the long hand means
# minutes', and it needs a precise mouse drag on a clock hand." Telling the time
# is not dropped from kidnix -- it stops being GCompris'.
assert_py "clockgame is gone and number_sequence replaced it" "
import pathlib, sys, tomllib
ids = [a['id'] for a in tomllib.loads(pathlib.Path('${SHELF}').read_text())['activities']]
if 'clockgame' in ids: sys.exit('clockgame is still on the shelf')
if 'number_sequence' not in ids: sys.exit('number_sequence is not on the shelf')
print(f'{len(ids)} activities')
"
assert_no_grep '^clockgame=' "${CONF}" "clockgame is not a favourite any more"
assert_grep '^number_sequence=true$' "${CONF}" "number_sequence is"
# The group name is where a phonics claim would be made, so it is asserted
# here and not left to prose: "the group name is the claim, not the activity."
assert_py "the letters group is called 'Letters', not 'Letters and sounds'" "
import pathlib, sys, tomllib
groups = {g['id']: g['name'] for g in tomllib.loads(pathlib.Path('${SHELF}').read_text())['groups']}
if groups.get('letters') != 'Letters': sys.exit(f\"letters group is {groups.get('letters')!r}\")
if any('sound' in n.lower() for n in groups.values()):
    sys.exit(f'a group name still claims sounds: {groups}')
print(', '.join(groups.values()))
"

section "bootc hygiene"
# Everything here must live in /usr so bootc ships and can roll it back. A build
# stage that wrote under /var would have its work discarded at install time.
if [[ -z "$(find /var -mindepth 1 -maxdepth 1 ! -name lib ! -name home -print -quit 2>/dev/null)" ]]; then
    _report ok "/var carries no gcompris content"
else
    _report no "/var carries no gcompris content" \
        "found: $(find /var -mindepth 1 -maxdepth 1 ! -name lib ! -name home -printf '%f ' 2>/dev/null)"
fi

rm -rf /tmp/gcompris-test

# -----------------------------------------------------------------------------

printf '\n\033[1m%d passed, %d failed\033[0m\n' "${pass}" "${fail}"
[[ "${fail}" -eq 0 ]]
