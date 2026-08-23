#!/usr/bin/bash
# Build the child-account lockdown into the image, and refuse to ship if any
# part of it is wrong.
#
# Milestone M1. Six mechanisms, deliberately layered, because none of them is
# individually sufficient and the failure of any one must not open the whole
# door:
#
#   1. nftables      -- no network egress for uid 1000, enforced in the kernel
#   2. Flatpak       -- --unshare=network as the global default
#   3. polkit        -- kid may not authorise networking, installs, power,
#                       accounts, mounts or unit management
#   4. dconf         -- locked GNOME lockdown keys, no keybindings, no VT
#                       switching, child-appropriate input defaults
#   5. logind        -- no virtual terminals to switch *to*
#   6. greenboot     -- a boot where 1/3/4 silently failed is a failed boot
#
# Everything here is asserted, not assumed: a build that produces a subtly
# broken lockdown is worse than a build that fails, because nobody finds out.
set -euo pipefail

log() { printf '  -- %s\n' "$*"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

# -----------------------------------------------------------------------------
# 0. Packages
# -----------------------------------------------------------------------------

# greenboot 0.16.3 on Fedora 44 is greenboot-rs, the Rust rewrite targeted at
# bootc (verified: /usr/libexec/greenboot/greenboot is an ELF binary and the
# shipped README is greenboot-rs's). The old shell implementation is
# deprecated.
#
# greenboot-default-health-checks is DELIBERATELY NOT INSTALLED. Its
# 01_repository_dns_check.sh sits in required.d and resolves the DNS names of
# the system's package repositories. kidnix is an offline appliance for a
# child; on a machine with no network that check fails every boot, marks every
# boot red, and rolls a perfectly good deployment back three boots later. Its
# other two checks (watchdog, update-platform reachability) are not worth that
# risk. Ours live in /usr/lib/greenboot/check/{required,wanted}.d instead.
PACKAGES=(
    nftables
    greenboot
)

dnf5 -y install "${PACKAGES[@]}"

command -v nft >/dev/null 2>&1 || die "nft is not on PATH after installing nftables"
test -x /usr/libexec/greenboot/greenboot || die "greenboot binary is missing"
rpm -q greenboot-default-health-checks >/dev/null 2>&1 \
    && die "greenboot-default-health-checks got pulled in; its DNS check would red-boot an offline machine"

# gjs is what validates the polkit rules (see /usr/share/kidnix/polkit-eval.js).
# It arrives with the GNOME stack; assert rather than install, so a base-image
# change that drops it fails here instead of silently disabling the check.
command -v gjs >/dev/null 2>&1 || die "gjs is missing; the polkit rules cannot be validated"
command -v dconf >/dev/null 2>&1 || die "dconf is missing; the child profile cannot be compiled"

# -----------------------------------------------------------------------------
# 1. nftables egress lockdown
# -----------------------------------------------------------------------------

readonly NFT_RULESET=/usr/lib/kidnix/nftables/kidnix-egress.nft
test -f "${NFT_RULESET}" || die "${NFT_RULESET} is missing from system_files/"

# The ruleset filters uid 1000 numerically because `kid` does not exist inside
# a build container. That is only safe if sysusers really does pin kid to 1000.
grep -Eq '^u[[:space:]]+kid[[:space:]]+1000:1000[[:space:]]' /usr/lib/sysusers.d/kidnix.conf \
    || die "sysusers no longer pins kid to uid 1000, but ${NFT_RULESET} filters uid 1000"
grep -Eq '^[[:space:]]*meta skuid 1000 ' "${NFT_RULESET}" \
    || die "${NFT_RULESET} has no 'meta skuid 1000' rule"

# `nft -c` still initialises a netlink cache, which needs CAP_NET_ADMIN over a
# network namespace. A build container does not have it; `unshare -rn` makes a
# throwaway user+network namespace where we are root and do. Same check the
# image test suite runs, and the same check greenboot runs on the real machine
# (where it is simply `nft -c` as root).
log "syntax-checking ${NFT_RULESET}"
if ! unshare -rn nft -c -f "${NFT_RULESET}"; then
    die "${NFT_RULESET} does not parse"
fi

systemctl enable kidnix-egress.service

# -----------------------------------------------------------------------------
# 2. polkit
# -----------------------------------------------------------------------------

readonly POLKIT_RULES=/usr/share/polkit-1/rules.d/40-kidnix-kid.rules
test -f "${POLKIT_RULES}" || die "${POLKIT_RULES} is missing from system_files/"

# polkitd embeds duktape (ECMAScript 5.1). gjs will happily run syntax duktape
# rejects, and a rules file duktape cannot parse is silently ignored -- which
# fails OPEN. Grep for the ES6+ constructs that are easy to write by accident.
log "checking ${POLKIT_RULES} for ES6 syntax duktape cannot parse"
# `sed 's://.*::'` strips line comments first -- the prose above the rules
# talks about `let` and backticks, and we are checking the code, not the
# commentary. Safe here because the file contains no string literal with "//"
# in it (an action id never does).
if sed 's://.*::' "${POLKIT_RULES}" \
        | grep -nE '=>|\blet\b|\bconst\b|`|\.\.\.|\.includes\(|\bclass\b|\bfor[[:space:]]*\([^;]*\bof\b'; then
    die "${POLKIT_RULES} uses ES6+ syntax; polkitd's duktape engine is ES5.1"
fi

# The .policy file the child's session depends on has to PARSE, and polkitd is
# the only thing that would otherwise tell us it does not -- an unregistered
# action makes pkexec fail with "not authorized" (127), which looks exactly
# like the lockdown working. XML comments may not contain a double hyphen, and
# that is a real bug this caught: the comment in the file below explains at
# length why the child may set a PIN, and one "--" in it silently unregistered
# the action on the machine.
python3 - <<'PY' || die "org.kidnix.set-pin.policy does not parse; polkitd would ignore it"
import sys
import xml.dom.minidom

path = "/usr/share/polkit-1/actions/org.kidnix.set-pin.policy"
doc = xml.dom.minidom.parse(path)
actions = doc.getElementsByTagName("action")
assert len(actions) == 1, f"{len(actions)} actions in {path}"
assert actions[0].getAttribute("id") == "org.kidnix.set-pin", actions[0].getAttribute("id")
annotations = {
    a.getAttribute("key"): a.firstChild.nodeValue
    for a in actions[0].getElementsByTagName("annotate")
}
# pkexec matches a program to an action by this annotation. A typo here is the
# difference between "the child may set the first PIN" and "the child gets
# org.freedesktop.policykit.exec", which is denied.
assert annotations.get("org.freedesktop.policykit.exec.path") == "/usr/bin/kidnix-set-pin", annotations
print("  -- org.kidnix.set-pin parses and annotates /usr/bin/kidnix-set-pin")
PY

# Behavioural check: load the real file and ask it real questions.
log "evaluating ${POLKIT_RULES}"
polkit_case() {
    /usr/libexec/kidnix-polkit-check "$1" "$2" "$3" \
        || die "polkit rule regression: $1 + $2 should be $3"
}

# kid is denied the things that matter...
polkit_case kid org.freedesktop.Flatpak.app-install                     NO
polkit_case kid org.freedesktop.Flatpak.configure-remote                NO
polkit_case kid org.freedesktop.Flatpak.override-parental-controls      NO
polkit_case kid org.freedesktop.NetworkManager.settings.modify.system   NO
polkit_case kid org.freedesktop.NetworkManager.enable-disable-wifi      NO
polkit_case kid org.freedesktop.login1.reboot                           NO
polkit_case kid org.freedesktop.login1.power-off                        NO
polkit_case kid org.freedesktop.login1.suspend                          NO
polkit_case kid org.freedesktop.login1.chvt                             NO
polkit_case kid org.freedesktop.systemd1.manage-units                   NO
polkit_case kid org.freedesktop.accounts.user-administration            NO
polkit_case kid org.freedesktop.udisks2.filesystem-mount                NO
polkit_case kid org.projectatomic.rpmostree1.deploy                     NO
polkit_case kid org.freedesktop.policykit.exec                          NO
polkit_case kid com.endlessm.ParentalControls.AppFilter.ChangeOwn       NO
polkit_case kid org.freedesktop.Malcontent.SessionLimits.Extend         NO

# kidnix's own helpers: the export/wipe action stays shut to the child, and the
# carve-out below it is EXACTLY one id wide. The near-misses are the assertion
# that matters -- a stray dot turning the exact match back into a prefix would
# hand a five-year-old kidnix-wipe.
polkit_case kid org.kidnix.parent-tools                                 NO
polkit_case kid org.kidnix.set-pin.evil                                 NO
polkit_case kid org.kidnix.set-pinned                                   NO

# ...and the ONE thing the child's session may authorise: choosing the grown-up
# PIN on a machine that has none. YES, not NOT_HANDLED: the policy default is a
# wheel password and there is no grown-up to type one at the moment the laptop
# is handed over. /usr/bin/kidnix-set-pin is what decides whether the write
# actually happens (first set only, or the current PIN proved) -- see
# docs/spikes/pin-flow.md.
polkit_case kid org.kidnix.set-pin                                      YES
polkit_case parent org.kidnix.set-pin                                   NOT_HANDLED

# ...and left alone for the things a session legitimately needs.
polkit_case kid org.freedesktop.login1.inhibit-block-idle               NOT_HANDLED
polkit_case kid com.endlessm.ParentalControls.AppFilter.ReadOwn         NOT_HANDLED
polkit_case kid org.freedesktop.RealtimeKit1.acquire-high-priority      NOT_HANDLED
polkit_case kid org.gnome.mutter.backlight-helper.save                  NOT_HANDLED

# parent is a normal admin: our rule must not touch them at all.
polkit_case parent org.freedesktop.Flatpak.app-install                  NOT_HANDLED
polkit_case parent org.freedesktop.login1.reboot                        NOT_HANDLED
polkit_case parent org.projectatomic.rpmostree1.deploy                  NOT_HANDLED
polkit_case root   org.freedesktop.systemd1.manage-units                NOT_HANDLED

# -----------------------------------------------------------------------------
# 3. dconf profile for the child session
# -----------------------------------------------------------------------------

readonly DCONF_SRC=/usr/share/kidnix/dconf/kid.d
readonly DCONF_DB=/usr/share/kidnix/dconf/kid.compiled
test -d "${DCONF_SRC}" || die "${DCONF_SRC} is missing from system_files/"
test -f /etc/dconf/profile/kid || die "/etc/dconf/profile/kid is missing from system_files/"

# Keybindings: generate rather than hand-write. mutter/gnome-kiosk gain and
# rename keybindings between GNOME releases, and a hand-maintained list would
# quietly stop covering the new ones -- which is precisely how a child ends up
# discovering a window-management shortcut. Everything in these three schemas
# is type `as` (verified in this image), so blanking them all is safe.
log "generating keybinding-disable keyfile from the live schemas"
keybinding_schemas=(
    org.gnome.desktop.wm.keybindings
    org.gnome.mutter.keybindings
    org.gnome.mutter.wayland.keybindings
)

keyfile="${DCONF_SRC}/50-keybindings"
lockfile="${DCONF_SRC}/locks/50-keybindings"

{
    echo "# GENERATED AT BUILD TIME by build_files/40-lockdown.sh -- do not edit."
    echo "#"
    echo "# Every keybinding in mutter's three keybinding schemas, blanked --"
    echo "# with exactly ONE exception, switch-applications, which is the child's"
    echo "# way out of an activity (see below, and docs/spikes/keyboard-escape.md)."
    echo "# gnome-kiosk implements almost no shortcuts itself, but it is mutter"
    echo "# underneath, and mutter's defaults include Alt+F4 (close), Alt+Tab,"
    echo "# Super, workspace switching and -- the important one --"
    echo "# org.gnome.mutter.wayland.keybindings switch-to-session-1..12, which"
    echo "# is where Ctrl+Alt+F<n> VT switching is actually implemented on"
    echo "# Wayland. Blanking that is a real answer to research 07 risk #7,"
    echo "# which recorded it as UNVERIFIED."
    echo
} >"${keyfile}"

{
    echo "# GENERATED AT BUILD TIME by build_files/40-lockdown.sh -- do not edit."
} >"${lockfile}"

generated_keys=0
for schema in "${keybinding_schemas[@]}"; do
    path="/${schema//./\/}"
    printf '[%s]\n' "${path#/}" >>"${keyfile}"
    while read -r key; do
        [[ -n "${key}" ]] || continue
        # Only blank keys that really are string arrays. `gsettings range`
        # prints "type as" for those; anything else (an enum, an int) must not
        # be handed "@as []" or dconf compile refuses the whole database.
        range="$(gsettings range "${schema}" "${key}" 2>/dev/null || true)"
        if [[ "${range%%$'\n'*}" != "type as" ]]; then
            log "skipping non-list key ${schema} ${key} (${range%%$'\n'*})"
            continue
        fi
        printf '%s=@as []\n' "${key}" >>"${keyfile}"
        printf '%s/%s\n' "${path}" "${key}" >>"${lockfile}"
        generated_keys=$(( generated_keys + 1 ))
    done < <(gsettings list-keys "${schema}" 2>/dev/null | sort)
    printf '\n' >>"${keyfile}"
done

(( generated_keys > 50 )) \
    || die "only generated ${generated_keys} keybinding overrides; the schemas look wrong"
log "blanked ${generated_keys} keybindings"

# The VT-switch bindings are the whole point; fail loudly if they vanish.
for n in 1 2 3 4 5 6 7 8 9 10 11 12; do
    grep -q "^switch-to-session-${n}=@as \[\]$" "${keyfile}" \
        || die "switch-to-session-${n} was not blanked (VT switching would still work)"
done
grep -q '^close=@as \[\]$' "${keyfile}" || die "Alt+F4 (close) was not blanked"

# --- the one keybinding a child is allowed to have --------------------------
#
# FLOWS A25: inside an activity the compositor gives the keyboard to the
# *activity's* toplevel, so the shell's "Escape is Back" never arrives and a
# child on a keyboard or a switch cannot leave a drawing at all -- the one step
# of a session they could not take. Blanking all 102 keybindings above is what
# shut that door; exactly one is opened again here, and only far enough to move
# the keyboard from the activity back to a window of the shell's, where Escape
# is Back and every band control is on the ring.
#
# Why this key. Measured on the image, in a real kid session, with Tux Paint
# running (docs/spikes/keyboard-escape.md): gnome-kiosk installs custom
# handlers for the keybindings it wants to neutralise, and switch-applications
# is NOT one of them, so mutter's own handler runs -- it activates the next
# window in the most-recently-used list and draws nothing at all. There is no
# switcher popup, no overview and no launcher in gnome-kiosk to expose. It is
# also the only mechanism available: gnome-settings-daemon's custom-keybindings
# are refused the grab under gnome-kiosk (docs/spikes/band-over-activity.md
# §3e) and gnome-kiosk has no window/shell D-Bus API.
#
# Why this chord. One chord, not two: <Super>Tab is what an adult or an
# assistive-technology switch interface sends on purpose and what a child does
# not hit by accident, and Super is a modifier no activity we ship uses.
# <Alt>Tab -- mutter's other stock default for this key -- stays blank, as does
# switch-applications-backward: one direction reaches every window of a
# two-window shell, and each extra chord is extra surface for nothing.
#
# It is LOCKED like everything else in this file, so nothing in the session can
# change it, clear it, or add a second chord to it.
escape_binding="switch-applications"
escape_chord="['<Super>Tab']"
blank_line="$(grep -c "^${escape_binding}=@as \[\]$" "${keyfile}" || true)"
(( "${blank_line:-0}" == 1 )) \
    || die "expected exactly one blanked ${escape_binding} to re-enable, found ${blank_line:-0}"
sed -i "s|^${escape_binding}=@as \[\]$|${escape_binding}=${escape_chord}|" "${keyfile}"
grep -qxF "${escape_binding}=${escape_chord}" "${keyfile}" \
    || die "${escape_binding} was not re-enabled; a keyboard-only child could not leave an activity"
grep -qxF "/org/gnome/desktop/wm/keybindings/${escape_binding}" "${lockfile}" \
    || die "${escape_binding} is not in the lock list; the session could clear the way out"
# ...and nothing else got a chord with it. `switch-panels` (Ctrl+Alt+Tab) is
# mutter's other focus-cycling family and stays shut; `close` is Alt+F4.
grep -q '^switch-applications-backward=@as \[\]$' "${keyfile}" \
    || die "switch-applications-backward must stay blank: one direction is enough"
for shut in switch-windows switch-windows-backward cycle-windows switch-group \
            switch-panels cycle-panels toggle-fullscreen panel-run-dialog; do
    grep -q "^${shut}=@as \[\]$" "${keyfile}" \
        || die "${shut} is not blank; ${escape_binding} is the only binding a child may have"
done
with_a_chord="$(grep -cE "^[a-z0-9-]+=\['" "${keyfile}" || true)"
(( "${with_a_chord:-0}" == 1 )) \
    || die "${with_a_chord:-0} keybindings have a chord; exactly one (${escape_binding}) may"
log "re-enabled ${escape_binding}=${escape_chord} -- the keyboard route out of an activity"

# Every key we set by hand must exist in a schema, or dconf silently stores a
# value nothing reads and the lockdown is decorative.
log "verifying every key in ${DCONF_SRC} exists in an installed schema"
# The key list is cached per schema in a plain newline-delimited string, not
# re-queried per key. Partly for speed (~110 keys), but mainly because
# `gsettings list-keys ... | grep -q ...` is a trap under `set -o pipefail`:
# grep -q exits the instant it matches, gsettings takes SIGPIPE, and the
# pipeline reports failure *because the key was found*. That produced a
# beautifully confusing one-key-at-random "does not exist" error.
unknown=0
current_schema=""
current_keys=""
for f in "${DCONF_SRC}"/*; do
    [[ -f "${f}" ]] || continue
    # Resolved before the loop: calling basename inside a body that redirects
    # from the same file makes shellcheck (reasonably) suspicious (SC2094).
    fname="$(basename "${f}")"
    while IFS= read -r line; do
        case "${line}" in
            \[*\])
                current_schema="${line#[}"
                current_schema="${current_schema%]}"
                current_schema="${current_schema//\//.}"
                if current_keys="$(gsettings list-keys "${current_schema}" 2>/dev/null)"; then
                    :
                else
                    echo "  unknown schema: ${current_schema} (in ${fname})" >&2
                    unknown=$(( unknown + 1 ))
                    current_schema=""
                    current_keys=""
                fi
                ;;
            \#*|"") ;;
            *=*)
                [[ -n "${current_schema}" ]] || continue
                key="${line%%=*}"
                if ! grep -qxF -- "${key}" <<<"${current_keys}"; then
                    echo "  unknown key: ${current_schema} ${key} (in ${fname})" >&2
                    unknown=$(( unknown + 1 ))
                fi
                ;;
        esac
    done <"${f}"
done
(( unknown == 0 )) || die "${unknown} dconf key(s)/schema(s) do not exist in this image"

# `dconf compile` (not `dconf update`) so the database is image-owned under
# /usr rather than sitting in /etc where every upgrade would 3-way-merge a
# binary blob. Same shape as gnome-kiosk's own
# /usr/share/gnome-kiosk/gnomekiosk.dconf.compiled.
log "compiling ${DCONF_SRC} -> ${DCONF_DB}"
dconf compile "${DCONF_DB}" "${DCONF_SRC}"
test -s "${DCONF_DB}" || die "${DCONF_DB} was not produced"

# Prove the compiled database actually answers, and that the locks bite.
log "verifying the compiled profile"
# dconf wants somewhere to look for the user database even though we only read
# the file-db half of the profile.
export HOME="${HOME:-/root}"
mkdir -p "${HOME}" 2>/dev/null || true
check_setting() {
    local schema="$1" key="$2" want="$3" got
    got="$(DCONF_PROFILE=kid gsettings get "${schema}" "${key}" 2>/dev/null || echo '<error>')"
    [[ "${got}" == "${want}" ]] \
        || die "kid profile: ${schema} ${key} is ${got}, expected ${want}"
}
check_locked() {
    local schema="$1" key="$2" writable
    writable="$(DCONF_PROFILE=kid gsettings writable "${schema}" "${key}" 2>/dev/null || echo '<error>')"
    [[ "${writable}" == "false" ]] \
        || die "kid profile: ${schema} ${key} is writable (${writable}); the lock did not take"
}

# EVERY key we set must actually read back as what we wrote. This is not
# belt-and-braces, it is the check that matters: `dconf compile` happily accepts
# a value whose GVariant type does not match the schema, stores it, and
# gsettings then silently ignores it and returns the stock default. That is how
# `disable-while-typing-timeout=1000` (int32) sat in the database looking
# correct while the touchpad kept GNOME's 500 ms, because the schema wants
# uint32. A lockdown that compiles but does not apply is the worst outcome
# available, so it is a build failure.
log "verifying every key reads back as written"
readback_mismatches=0
current_schema=""
current_path=""
for f in "${DCONF_SRC}"/*; do
    [[ -f "${f}" ]] || continue
    while IFS= read -r line; do
        case "${line}" in
            \[*\])
                current_path="${line#[}"
                current_path="${current_path%]}"
                current_schema="${current_path//\//.}"
                ;;
            \#*|"") ;;
            *=*)
                [[ -n "${current_schema}" ]] || continue
                key="${line%%=*}"
                want="${line#*=}"
                got="$(DCONF_PROFILE=kid gsettings get "${current_schema}" "${key}" 2>/dev/null || echo '<error>')"
                [[ "${got}" == "${want}" ]] && continue
                # GVariant prints doubles with whatever precision round-trips,
                # so 1.2 can come back as 1.2000000000000002. Compare
                # numerically when both sides are plain numbers.
                if [[ "${want}" =~ ^-?[0-9.]+$ && "${got}" =~ ^-?[0-9.]+$ ]] \
                   && awk -v a="${want}" -v b="${got}" 'BEGIN { exit !(a - b < 1e-9 && b - a < 1e-9) }'; then
                    continue
                fi
                echo "  ${current_schema} ${key}: wrote '${want}', reads back '${got}'" >&2
                readback_mismatches=$(( readback_mismatches + 1 ))
                ;;
        esac
    done <"${f}"
done
(( readback_mismatches == 0 )) \
    || die "${readback_mismatches} dconf key(s) do not read back as written (usually a GVariant type mismatch -- check whether the schema wants uint32)"

check_setting org.gnome.desktop.lockdown          disable-command-line true
check_setting org.gnome.desktop.lockdown          disable-lock-screen  true
check_setting org.gnome.desktop.peripherals.mouse double-click         700
check_setting org.gnome.desktop.peripherals.mouse drag-threshold       16
check_setting org.gnome.desktop.interface         cursor-size          48
check_setting org.gnome.desktop.wm.keybindings    close                "@as []"
check_setting org.gnome.mutter.wayland.keybindings switch-to-session-2 "@as []"
check_locked  org.gnome.desktop.lockdown          disable-command-line
check_locked  org.gnome.desktop.peripherals.mouse double-click
check_locked  org.gnome.mutter.wayland.keybindings switch-to-session-2

# The keyboard route out of an activity (FLOWS A25). Spelled out here as well
# as caught by the generic read-back loop, because a silent regression -- the
# chord cleared, or the key left writable -- is the difference between a child
# on a switch being able to leave a drawing and not.
check_setting org.gnome.desktop.wm.keybindings switch-applications          "['<Super>Tab']"
check_locked  org.gnome.desktop.wm.keybindings switch-applications
check_setting org.gnome.desktop.wm.keybindings switch-applications-backward "@as []"
check_setting org.gnome.desktop.wm.keybindings switch-windows               "@as []"
check_setting org.gnome.desktop.wm.keybindings switch-panels                "@as []"

# Trackpad hardening (research 09 Q7). The trackpad is the worst pointing
# device in the house for a five-year-old and the one cheap laptops ship with,
# so these are the keys that decide whether it is usable or a source of
# invisible misfires. Spelled out here as well as caught by the generic
# read-back loop above, because a silent regression to GNOME's adult defaults
# (tap-to-click on, click-method deferring to libinput's button-areas,
# two-finger scrolling on) looks like nothing at all in a diff.
check_setting org.gnome.desktop.peripherals.touchpad tap-to-click                false
check_setting org.gnome.desktop.peripherals.touchpad click-method                "'fingers'"
check_setting org.gnome.desktop.peripherals.touchpad two-finger-scrolling-enabled false
check_setting org.gnome.desktop.peripherals.touchpad edge-scrolling-enabled      false
check_setting org.gnome.desktop.peripherals.touchpad send-events                 "'enabled'"
check_setting org.gnome.desktop.peripherals.touchpad disable-while-typing        true
check_setting org.gnome.desktop.peripherals.touchpad middle-click-emulation      false
check_setting org.gnome.desktop.peripherals.touchpad accel-profile               "'flat'"
check_setting org.gnome.mutter                       edge-tiling                 false
check_setting org.gnome.settings-daemon.peripherals.touchscreen orientation-lock true
check_locked  org.gnome.desktop.peripherals.touchpad tap-to-click
check_locked  org.gnome.desktop.peripherals.touchpad click-method
check_locked  org.gnome.desktop.peripherals.touchpad two-finger-scrolling-enabled
check_locked  org.gnome.desktop.peripherals.touchpad send-events

# ...and the two that are deliberately NOT locked, because a parent has to be
# able to turn them: pointer speed for a specific child, and rotation for tent
# mode. A lock added here by accident would be silent and unrecoverable
# without a new image.
check_writable() {
    local schema="$1" key="$2" writable
    writable="$(DCONF_PROFILE=kid gsettings writable "${schema}" "${key}" 2>/dev/null || echo '<error>')"
    [[ "${writable}" == "true" ]] \
        || die "kid profile: ${schema} ${key} is locked (${writable}); the parent could not change it"
}
check_writable org.gnome.desktop.peripherals.touchpad speed
check_writable org.gnome.settings-daemon.peripherals.touchscreen orientation-lock

# The touchpad schema must be described in exactly one keyfile. Two keyfiles
# setting the same key is resolved by dconf compile in directory order, which
# is not something anyone should have to reason about, and the read-back loop
# above would blame whichever one lost.
# Anchored, so prose *about* the move (there is a pointer comment in 10-input)
# does not count as setting the schema. `-d skip` because locks/ is a
# directory, and `|| true` because grep exits non-zero when nothing matches,
# which under pipefail would abort the build with a far less useful message
# than the die below.
touchpad_files="$({ grep -lE -d skip '^\[org/gnome/desktop/peripherals/touchpad\]$' \
    "${DCONF_SRC}"/* || true; } | wc -l)"
(( touchpad_files == 1 )) \
    || die "the touchpad schema appears in ${touchpad_files} keyfiles; it must live only in 11-trackpad"

# And that the profile is inert for anyone who is not the child.
default_cursor="$(gsettings get org.gnome.desktop.interface cursor-size 2>/dev/null || echo '<error>')"
[[ "${default_cursor}" != "48" ]] \
    || die "the kid profile is leaking into the default profile"

# -----------------------------------------------------------------------------
# 4. logind: no VTs to switch to
# -----------------------------------------------------------------------------

readonly LOGIND_DROPIN=/usr/lib/systemd/logind.conf.d/10-kidnix-kiosk.conf
test -f "${LOGIND_DROPIN}" || die "${LOGIND_DROPIN} is missing from system_files/"

# systemd-analyze parses the whole drop-in chain, so a typo shows up now.
log "verifying the logind drop-in is picked up"
logind_config="$(systemd-analyze cat-config systemd/logind.conf 2>/dev/null || true)"
grep -q '^NAutoVTs=0$' <<<"${logind_config}" || die "NAutoVTs=0 is not in force"
grep -q '^ReserveVT=0$' <<<"${logind_config}" || die "ReserveVT=0 is not in force"

# The recovery path must survive: getty@tty1 is enabled by preset and is what a
# parent falls back to with `systemd.unit=multi-user.target` on the kernel
# command line. NAutoVTs only governs *autovt@* spawning, not this.
systemctl is-enabled getty@tty1.service >/dev/null 2>&1 \
    || die "getty@tty1.service is not enabled; there would be no recovery console"

# -----------------------------------------------------------------------------
# 5. Flatpak
# -----------------------------------------------------------------------------

readonly FLATPAK_OVERRIDE=/usr/share/kidnix/flatpak/overrides-global
test -f "${FLATPAK_OVERRIDE}" || die "${FLATPAK_OVERRIDE} is missing from system_files/"
grep -q '^shared=!network;$' "${FLATPAK_OVERRIDE}" \
    || die "${FLATPAK_OVERRIDE} does not unshare the network"
grep -q '/var/lib/flatpak/overrides/global' /usr/lib/tmpfiles.d/kidnix-lockdown.conf \
    || die "nothing seeds /var/lib/flatpak/overrides/global on first boot"

# The seed must say exactly what flatpak itself would write, so a parent
# running `flatpak override --show` sees something it recognises and a future
# `flatpak override` edit round-trips cleanly. Generating it here and diffing
# is how we find out when the format changes under us.
log "checking the flatpak override seed against flatpak's own output"
flatpak override --system --unshare=network
strip_comments() { grep -vE '^[[:space:]]*(#|$)' "$1"; }
if ! diff -u <(strip_comments "${FLATPAK_OVERRIDE}") \
             <(strip_comments /var/lib/flatpak/overrides/global); then
    die "${FLATPAK_OVERRIDE} no longer matches what 'flatpak override --system --unshare=network' writes"
fi
# /var is machine-local and 90-cleanup.sh wipes it; the tmpfiles rule is what
# actually puts this on the installed machine.
rm -rf /var/lib/flatpak

# -----------------------------------------------------------------------------
# 6. Updates: no surprise reboots
# -----------------------------------------------------------------------------

# bootc-fetch-apply-updates.timer checks daily and REBOOTS if it finds an
# update. Mid-activity, unannounced, on a child's computer. The parent panel
# will drive `bootc upgrade --check` / `--apply` at a moment the family chose.
systemctl mask bootc-fetch-apply-updates.timer
[[ "$(readlink -f /etc/systemd/system/bootc-fetch-apply-updates.timer)" == /dev/null ]] \
    || die "bootc-fetch-apply-updates.timer is not masked"

# -----------------------------------------------------------------------------
# 7. Audio ceiling
# -----------------------------------------------------------------------------

test -x /usr/libexec/kidnix-audio-cap || die "/usr/libexec/kidnix-audio-cap is missing"
test -f /usr/share/wireplumber/wireplumber.conf.d/50-kidnix-soft-mixer.conf \
    || die "the WirePlumber soft-mixer drop-in is missing"
systemctl enable kidnix-audio-cap.service

# -----------------------------------------------------------------------------
# 8. greenboot health checks
# -----------------------------------------------------------------------------

# /usr/lib/greenboot/check/... rather than /etc: image-owned, so an upgrade
# always brings the current checks and there is no merge to lose. This is where
# greenboot-default-health-checks puts its own scripts, and the greenboot-rs
# README documents it as "a read-only directory in ostree systems".
for check in /usr/lib/greenboot/check/required.d/*-kidnix-*.sh \
             /usr/lib/greenboot/check/wanted.d/*-kidnix-*.sh \
             /usr/lib/greenboot/red.d/*-kidnix-*.sh; do
    test -f "${check}" || die "expected greenboot check ${check} is missing"
    chmod 0755 "${check}"
    bash -n "${check}" || die "${check} is not valid bash"
done

# COPY from system_files does not guarantee the mode we want on every script.
chmod 0755 /usr/libexec/kidnix-audio-cap \
           /usr/libexec/kidnix-app-supervisor \
           /usr/libexec/kidnix-polkit-check

systemctl enable greenboot-healthcheck.service

test -f /usr/lib/bootupd/grub2-static/configs.d/08_greenboot.cfg \
    || die "bootupd is not shipping greenboot's GRUB boot_counter snippet; rollback would not fire"

# -----------------------------------------------------------------------------

log "lockdown installed"

# --- name resolution for kid must go through the uid filter -------------------
# glibc's nss-resolve module reaches systemd-resolved over a varlink socket, not
# UDP/53, so kid's lookups would bypass the per-UID nftables rule and leave the
# machine as resolved's own uid (packet capture: docs/spikes/egress-proof.md §4).
# Dropping `resolve` from the hosts line makes glibc use its `dns` module, which
# sends to the 127.0.0.53 stub over UDP/53 as the calling uid -- where the
# kidnix_egress table rejects it for kid and lets parent through. resolved keeps
# running; only the varlink shortcut is gone.
#
# authselect-apply-changes.service re-renders /etc/nsswitch.conf from the
# selected profile on EVERY boot, so editing the generated file is undone at
# first boot (found the hard way). The durable way is a custom profile.
log "authselect: custom profile without nss-resolve"
authselect create-profile kidnix --base-on local --symlink-meta --symlink-dconf --symlink-pam >/dev/null
KIDNIX_PROFILE=/etc/authselect/custom/kidnix
test -f "${KIDNIX_PROFILE}/nsswitch.conf"
sed -i -E 's/resolve[[:space:]]+\[!UNAVAIL=return\][[:space:]]*//' "${KIDNIX_PROFILE}/nsswitch.conf"
authselect select custom/kidnix with-silent-lastlog with-mdns4 --force >/dev/null
authselect check >/dev/null
grep -E '^hosts:' /etc/nsswitch.conf
if grep -E '^hosts:' /etc/nsswitch.conf | grep -qw resolve; then
    echo "nsswitch still routes hosts through nss-resolve" >&2
    exit 1
fi
