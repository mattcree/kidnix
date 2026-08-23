#!/usr/bin/bash
# Static assertions about the child-account lockdown (milestone M1).
#
#   just test-lockdown
#   podman run --rm -v ./tests/image:/tests:ro,z --entrypoint /bin/bash \
#       localhost/kidnix:latest /tests/test_lockdown.sh
#
# Same shape and helpers as test_image.sh: runs INSIDE the built container,
# rootless, no VM, a couple of seconds. It proves the lockdown is *installed
# and internally consistent*; it cannot prove the lockdown is *in force*,
# because nothing here is booted. The things it deliberately does not cover --
# VT switching on real hardware, keybindings inside a live gnome-kiosk, the
# audio ceiling, greenboot actually rolling a deployment back -- are listed in
# docs/spikes/lockdown.md and belong to tests/boot/.
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

# assert_file <path> -- exists and is a regular file
assert_file() {
    if [[ -f "$1" ]]; then _report ok "file $1"; else _report no "file $1" "missing"; fi
}

# assert_exec <path> -- exists and is executable
assert_exec() {
    if [[ -x "$1" ]]; then _report ok "executable $1"; else _report no "executable $1" "missing or not +x"; fi
}

# assert_rpm <name>
assert_rpm() {
    if rpm -q "$1" >/dev/null 2>&1; then
        _report ok "package $1 ($(rpm -q --qf '%{VERSION}-%{RELEASE}' "$1"))"
    else
        _report no "package $1" "not installed"
    fi
}

# assert_no_rpm <name> <why>
assert_no_rpm() {
    if rpm -q "$1" >/dev/null 2>&1; then
        _report no "package $1 is absent" "$2"
    else
        _report ok "package $1 is absent ($2)"
    fi
}

# assert_grep <regex> <file> <description>
assert_grep() {
    if grep -Eq "$1" "$2" 2>/dev/null; then
        _report ok "$3"
    else
        _report no "$3" "no match for /$1/ in $2"
    fi
}

# assert_cmd <description> <command...>
assert_cmd() {
    local name="$1"; shift
    if "$@" >/dev/null 2>&1; then _report ok "${name}"; else _report no "${name}" "command failed: $*"; fi
}

# assert_eq <description> <expected> <actual>
assert_eq() {
    if [[ "$2" == "$3" ]]; then _report ok "$1"; else _report no "$1" "expected '$2', got '$3'"; fi
}

section() { printf '\n\033[1m%s\033[0m\n' "$1"; }

# -----------------------------------------------------------------------------

section "packages"
assert_rpm nftables
assert_rpm polkit
assert_rpm dconf
assert_rpm greenboot
assert_rpm gjs
# greenboot-default-health-checks ships 01_repository_dns_check.sh in
# required.d. kidnix is offline by design, so that check would fail every boot,
# mark it red and roll a good deployment back after three tries.
assert_no_rpm greenboot-default-health-checks \
    "its DNS health check would red-boot an offline machine"

section "network egress: nftables"
assert_file /usr/lib/kidnix/nftables/kidnix-egress.nft
assert_file /usr/lib/systemd/system/kidnix-egress.service
assert_grep '^[[:space:]]*meta skuid 1000 .*reject' \
    /usr/lib/kidnix/nftables/kidnix-egress.nft "ruleset rejects egress from uid 1000 (kid)"
assert_grep '^[[:space:]]*oif "lo" accept$' \
    /usr/lib/kidnix/nftables/kidnix-egress.nft "loopback stays open (local TTS + parent-panel IPC)"
assert_grep '^delete table inet kidnix_egress$' \
    /usr/lib/kidnix/nftables/kidnix-egress.nft "ruleset reloads idempotently"
# The rule filters uid 1000 numerically because `kid` does not exist in the
# image; sysusers must therefore really pin kid to 1000.
assert_grep '^u[[:space:]]+kid[[:space:]]+1000:1000[[:space:]]' \
    /usr/lib/sysusers.d/kidnix.conf "sysusers pins kid to uid 1000, which is what the ruleset filters"

# `nft -c` initialises a netlink cache and so needs CAP_NET_ADMIN, which a
# rootless test container does not have. `unshare -rn` builds a throwaway
# user+network namespace where we are root over our own (empty) netns, which is
# all the parser needs. On the real machine greenboot runs plain `nft -c`.
if unshare -rn nft -c -f /usr/lib/kidnix/nftables/kidnix-egress.nft >/dev/null 2>&1; then
    _report ok "nft -c accepts the egress ruleset"
else
    _report no "nft -c accepts the egress ruleset" \
        "$(unshare -rn nft -c -f /usr/lib/kidnix/nftables/kidnix-egress.nft 2>&1 | head -3)"
fi

for unit_dir in /etc/systemd/system/multi-user.target.wants /etc/systemd/system/graphical.target.wants; do
    if [[ -L "${unit_dir}/kidnix-egress.service" ]]; then
        _report ok "kidnix-egress.service enabled in $(basename "${unit_dir}")"
    else
        _report no "kidnix-egress.service enabled in $(basename "${unit_dir}")" "no symlink"
    fi
done

section "network egress: flatpak"
assert_file /usr/share/kidnix/flatpak/overrides-global
assert_grep '^shared=!network;$' /usr/share/kidnix/flatpak/overrides-global \
    "flatpak global override unshares the network"
assert_grep '^C /var/lib/flatpak/overrides/global ' /usr/lib/tmpfiles.d/kidnix-lockdown.conf \
    "tmpfiles seeds the flatpak override on first boot (/var is machine-local)"
assert_cmd "kidnix-lockdown tmpfiles config parses" systemd-tmpfiles --cat-config
# /var must stay empty in the image or `bootc container lint` fails the build.
if [[ -e /var/lib/flatpak ]]; then
    _report no "no flatpak state shipped in /var" "/var/lib/flatpak exists in the image"
else
    _report ok "no flatpak state shipped in /var"
fi

section "polkit lockdown for kid"
assert_file /usr/share/polkit-1/rules.d/40-kidnix-kid.rules
assert_exec /usr/libexec/kidnix-polkit-check
assert_file /usr/share/kidnix/polkit-eval.js
# polkitd on F44 embeds duktape (ES5.1). A rules file it cannot parse is
# ignored, which fails OPEN -- so ES6 syntax is a security bug, not a style
# nit. Comments are stripped first: the prose legitimately mentions `let`.
# (Captured rather than piped into `grep -q`: under `set -o pipefail` grep -q
# exits on its first match, sed takes SIGPIPE, and the pipeline reports failure
# exactly when a violation *was* found -- inverting the test.)
polkit_code="$(sed 's://.*::' /usr/share/polkit-1/rules.d/40-kidnix-kid.rules 2>/dev/null || true)"
if grep -Eq '=>|\blet\b|\bconst\b|`|\.\.\.|\.includes\(|\bclass\b' <<<"${polkit_code}"; then
    _report no "polkit rules are ES5 (duktape cannot parse ES6)" "found ES6+ syntax"
else
    _report ok "polkit rules are ES5 (duktape cannot parse ES6)"
fi
# Rules must sort before Fedora's 50-default.rules, which grants wheel
# AUTH_ADMIN_KEEP, and before the unnumbered vendor files.
if [[ -f /usr/share/polkit-1/rules.d/50-default.rules ]]; then
    _report ok "kidnix rules sort before 50-default.rules (40- < 50-)"
else
    _report no "kidnix rules sort before 50-default.rules (40- < 50-)" "50-default.rules is gone"
fi

# Behavioural: load the real rules file and ask it real questions. Each of
# these is a distinct assertion on purpose -- a regression should name the
# action it broke.
polkit_denies() {
    if /usr/libexec/kidnix-polkit-check kid "$1" NO 2>/dev/null; then
        _report ok "kid is denied $1"
    else
        _report no "kid is denied $1" \
            "verdict $(/usr/libexec/kidnix-polkit-check kid "$1" 2>/dev/null || echo '<error>')"
    fi
}
polkit_allows() {
    local user="$1" action="$2"
    if /usr/libexec/kidnix-polkit-check "${user}" "${action}" NOT_HANDLED 2>/dev/null; then
        _report ok "${user} is not constrained for ${action}"
    else
        _report no "${user} is not constrained for ${action}" \
            "verdict $(/usr/libexec/kidnix-polkit-check "${user}" "${action}" 2>/dev/null || echo '<error>')"
    fi
}

polkit_denies org.freedesktop.Flatpak.app-install
polkit_denies org.freedesktop.Flatpak.configure-remote
polkit_denies org.freedesktop.Flatpak.override-parental-controls
polkit_denies org.freedesktop.NetworkManager.settings.modify.system
polkit_denies org.freedesktop.NetworkManager.enable-disable-wifi
polkit_denies org.freedesktop.login1.reboot
polkit_denies org.freedesktop.login1.power-off
polkit_denies org.freedesktop.login1.suspend
polkit_denies org.freedesktop.login1.chvt
polkit_denies org.freedesktop.systemd1.manage-units
polkit_denies org.freedesktop.systemd1.manage-unit-files
polkit_denies org.freedesktop.accounts.user-administration
polkit_denies org.freedesktop.udisks2.filesystem-mount
polkit_denies org.projectatomic.rpmostree1.deploy
polkit_denies org.projectatomic.rpmostree1.upgrade
polkit_denies org.freedesktop.policykit.exec
polkit_denies com.endlessm.ParentalControls.AppFilter.ChangeOwn
polkit_denies org.freedesktop.Malcontent.SessionLimits.Extend
polkit_denies org.freedesktop.hostname1.set-static-hostname

# kidnix's own actions. The child may not export or erase their own machine's
# data, and the near-misses are what prove the one carve-out below is an EXACT
# id and not a prefix: a stray dot in 40-kidnix-kid.rules would hand a
# five-year-old kidnix-wipe.
polkit_denies org.kidnix.parent-tools
polkit_denies org.kidnix.set-pin.evil
polkit_denies org.kidnix.set-pinned

# THE ONE THING THE CHILD'S SESSION MAY AUTHORISE: choosing the grown-up PIN.
# YES rather than NOT_HANDLED, because the policy default is a wheel password
# and there is nobody to type one at the moment the laptop is handed over, and
# because the image ships with no PIN at all -- so without this the mandatory
# "choose a grown-up PIN" screen could only ever hold its answer for one boot.
# What stops it being a hole is /usr/bin/kidnix-set-pin, asserted in
# test_hardening.sh: it writes only on a machine with no PIN, or for a caller
# who typed the current one. docs/spikes/pin-flow.md is the threat model.
polkit_grants() {
    if /usr/libexec/kidnix-polkit-check kid "$1" YES 2>/dev/null; then
        _report ok "kid may authorise $1 (and only this one)"
    else
        _report no "kid may authorise $1 (and only this one)" \
            "verdict $(/usr/libexec/kidnix-polkit-check kid "$1" 2>/dev/null || echo '<error>')"
    fi
}
polkit_grants org.kidnix.set-pin

# The rules file constrains `kid` and nobody else: a grown-up meets the policy
# default (auth_admin_keep) for the same action.
polkit_allows parent org.kidnix.set-pin

# The carve-out is one line in one file, so assert the file says so too -- a
# YES from the evaluator with no id next to it in the source would be a rule
# somebody widened by editing the wrong array.
if grep -Eq '^ *"org\.kidnix\.set-pin"$' /usr/share/polkit-1/rules.d/40-kidnix-kid.rules \
    && [[ "$(grep -cE '^ *"org\.kidnix\.[a-z-]+"$' \
        /usr/share/polkit-1/rules.d/40-kidnix-kid.rules)" == 1 ]]; then
    _report ok "exactly one org.kidnix.* id is granted in the rules file"
else
    _report no "exactly one org.kidnix.* id is granted in the rules file" \
        "$(grep -E '^ *"org\.kidnix\.[a-z-]+"$' \
            /usr/share/polkit-1/rules.d/40-kidnix-kid.rules | tr '\n' ' ')"
fi

section "the PIN helper behind that carve-out"
assert_exec /usr/bin/kidnix-set-pin
assert_file /usr/share/polkit-1/actions/org.kidnix.set-pin.policy
# pkexec matches a program to an action by this annotation, so a typo here is
# the difference between "the child may set the first PIN" and "the child gets
# org.freedesktop.policykit.exec, which is denied".
assert_grep '<annotate key="org.freedesktop.policykit.exec.path">/usr/bin/kidnix-set-pin</annotate>' \
    /usr/share/polkit-1/actions/org.kidnix.set-pin.policy \
    "the set-pin action points at /usr/bin/kidnix-set-pin"
assert_grep '<action id="org.kidnix.set-pin">' \
    /usr/share/polkit-1/actions/org.kidnix.set-pin.policy \
    "the action id matches the one the rules file grants"

# ...and it has to PARSE. An unregistered action makes pkexec fail with "not
# authorized" (127), which is indistinguishable from the lockdown working --
# a boot test caught exactly that, from a double hyphen inside the XML comment
# that explains why the child may set a PIN at all. XML comments may not
# contain one; nothing else in the image would have said so.
if python3 - <<'PY' >/dev/null 2>&1
import xml.dom.minidom

path = "/usr/share/polkit-1/actions/org.kidnix.set-pin.policy"
doc = xml.dom.minidom.parse(path)
actions = doc.getElementsByTagName("action")
assert len(actions) == 1
assert actions[0].getAttribute("id") == "org.kidnix.set-pin"
annotations = {
    a.getAttribute("key"): a.firstChild.nodeValue
    for a in actions[0].getElementsByTagName("annotate")
}
assert annotations["org.freedesktop.policykit.exec.path"] == "/usr/bin/kidnix-set-pin"
PY
then
    _report ok "the set-pin action is well-formed XML (polkitd will register it)"
else
    _report no "the set-pin action is well-formed XML (polkitd will register it)" \
        "minidom rejected it, or the id/annotation drifted"
fi

# Carve-outs the session actually needs.
polkit_allows kid org.freedesktop.login1.inhibit-block-idle
polkit_allows kid com.endlessm.ParentalControls.AppFilter.ReadOwn
polkit_allows kid org.freedesktop.RealtimeKit1.acquire-high-priority
# The parent is an admin, not a suspect (AGENTS.md non-negotiable #6).
polkit_allows parent org.freedesktop.Flatpak.app-install
polkit_allows parent org.freedesktop.login1.reboot
polkit_allows parent org.projectatomic.rpmostree1.deploy
polkit_allows root org.freedesktop.systemd1.manage-units

section "dconf profile for the child session"
assert_file /etc/dconf/profile/kid
assert_file /usr/share/kidnix/dconf/kid.compiled
assert_file /usr/share/kidnix/dconf/kid.d/00-lockdown
assert_file /usr/share/kidnix/dconf/kid.d/10-input
assert_file /usr/share/kidnix/dconf/kid.d/50-keybindings
assert_file /usr/share/kidnix/dconf/kid.d/locks/00-lockdown
assert_file /usr/share/kidnix/dconf/kid.d/locks/50-keybindings
assert_grep '^file-db:/usr/share/kidnix/dconf/kid.compiled$' /etc/dconf/profile/kid \
    "kid profile points at the compiled system database"
assert_grep '^user-db:user$' /etc/dconf/profile/kid \
    "kid profile keeps a writable user database for unlocked keys"
# The shell has to select the profile, or none of this applies.
assert_grep '^export DCONF_PROFILE=kid$' /usr/bin/kidnix-shell \
    "kidnix-shell selects the kid dconf profile"

export HOME="${HOME:-/tmp}"
dconf_is() {
    local schema="$1" key="$2" want="$3" got
    got="$(DCONF_PROFILE=kid gsettings get "${schema}" "${key}" 2>/dev/null || echo '<error>')"
    assert_eq "kid: ${schema} ${key}" "${want}" "${got}"
}
dconf_locked() {
    local schema="$1" key="$2" got
    got="$(DCONF_PROFILE=kid gsettings writable "${schema}" "${key}" 2>/dev/null || echo '<error>')"
    assert_eq "kid: ${schema} ${key} is locked" "false" "${got}"
}
# GVariant prints doubles with whatever precision round-trips, so 1.3 can come
# back as "1.3" or "1.3000000000000000". Match the prefix rather than pin the
# formatting of a floating-point literal.
dconf_starts() {
    local schema="$1" key="$2" want="$3" got
    got="$(DCONF_PROFILE=kid gsettings get "${schema}" "${key}" 2>/dev/null || echo '<error>')"
    if [[ "${got}" == "${want}"* ]]; then
        _report ok "kid: ${schema} ${key} ~= ${want}"
    else
        _report no "kid: ${schema} ${key} ~= ${want}" "got '${got}'"
    fi
}

# Lockdown keys (all verified to exist in GNOME 50's schemas).
dconf_is org.gnome.desktop.lockdown disable-command-line true
dconf_is org.gnome.desktop.lockdown disable-lock-screen true
dconf_is org.gnome.desktop.lockdown disable-log-out true
dconf_is org.gnome.desktop.lockdown disable-user-switching true
dconf_is org.gnome.desktop.lockdown user-administration-disabled true
dconf_is org.gnome.desktop.lockdown mount-removable-storage-devices-as-read-only true
dconf_locked org.gnome.desktop.lockdown disable-command-line
dconf_locked org.gnome.desktop.lockdown mount-removable-storage-devices-as-read-only

# No password to type, but idle blank/dim survives.
dconf_is org.gnome.desktop.screensaver lock-enabled false
dconf_is org.gnome.desktop.screensaver idle-activation-enabled false
dconf_is org.gnome.desktop.session idle-delay "uint32 900"
dconf_is org.gnome.settings-daemon.plugins.power idle-dim true
dconf_is org.gnome.settings-daemon.plugins.power sleep-inactive-ac-type "'nothing'"
dconf_locked org.gnome.desktop.screensaver lock-enabled

# Input, from docs/research/06-input-accessibility-hardware-ai.md §7.1.
dconf_is org.gnome.desktop.peripherals.mouse double-click 700
dconf_is org.gnome.desktop.peripherals.mouse drag-threshold 16
dconf_is org.gnome.desktop.peripherals.mouse accel-profile "'flat'"
dconf_starts org.gnome.desktop.peripherals.mouse speed -0.4
dconf_is org.gnome.desktop.peripherals.touchpad tap-and-drag-lock true
dconf_is org.gnome.desktop.peripherals.touchpad disable-while-typing-timeout "uint32 1000"
dconf_is org.gnome.desktop.interface cursor-size 48
dconf_is org.gnome.desktop.interface enable-hot-corners false
dconf_starts org.gnome.desktop.interface text-scaling-factor 1.3
dconf_is org.gnome.desktop.a11y.mouse dwell-threshold 20
dconf_locked org.gnome.desktop.peripherals.mouse double-click
dconf_locked org.gnome.desktop.peripherals.mouse drag-threshold
dconf_locked org.gnome.desktop.interface cursor-size

# No automount, no autorun: a USB stick must do nothing on its own.
dconf_is org.gnome.desktop.media-handling automount false
dconf_is org.gnome.desktop.media-handling autorun-never true

section "keyboard shortcuts and VT switching"
# switch-to-session-N in org.gnome.mutter.wayland.keybindings is where mutter
# (and therefore gnome-kiosk) implements Ctrl+Alt+F<n> on Wayland. Blanking it
# is the real answer to research 07 risk #7, which recorded the mechanism as
# UNVERIFIED.
for n in 1 2 3 4 12; do
    dconf_is org.gnome.mutter.wayland.keybindings "switch-to-session-${n}" "@as []"
done
dconf_locked org.gnome.mutter.wayland.keybindings switch-to-session-2
dconf_is org.gnome.desktop.wm.keybindings close "@as []"                # Alt+F4
dconf_is org.gnome.desktop.wm.keybindings panel-run-dialog "@as []"     # Alt+F2
dconf_is org.gnome.desktop.wm.keybindings switch-to-workspace-right "@as []"
dconf_is org.gnome.desktop.wm.keybindings toggle-fullscreen "@as []"
dconf_locked org.gnome.desktop.wm.keybindings close

# The one exception, and the reason it exists (FLOWS A25,
# docs/spikes/keyboard-escape.md): inside an activity the compositor gives the
# keyboard to the activity's toplevel, so the shell's "Escape is Back" never
# arrives. switch-applications on <Super>Tab hands the keyboard back to a shell
# window -- mutter's own handler, no popup, no overview, nothing drawn -- and
# Escape is Back from there. Measured end to end on the image.
dconf_is org.gnome.desktop.wm.keybindings switch-applications "['<Super>Tab']"
dconf_locked org.gnome.desktop.wm.keybindings switch-applications
# ...and nothing came with it. One chord, one direction, everything else shut.
dconf_is org.gnome.desktop.wm.keybindings switch-applications-backward "@as []"
dconf_is org.gnome.desktop.wm.keybindings switch-windows "@as []"       # Alt+Tab
dconf_is org.gnome.desktop.wm.keybindings switch-windows-backward "@as []"
dconf_is org.gnome.desktop.wm.keybindings cycle-windows "@as []"
dconf_is org.gnome.desktop.wm.keybindings switch-group "@as []"
dconf_is org.gnome.desktop.wm.keybindings switch-panels "@as []"        # Ctrl+Alt+Tab
dconf_is org.gnome.desktop.wm.keybindings activate-window-menu "@as []"
# Exactly one binding in the generated keyfile has a chord at all. `grep -c`
# exits 1 on a zero count, hence `|| true` rather than `|| echo 0`.
with_a_chord="$(grep -cE "^[a-z0-9-]+=\['" /usr/share/kidnix/dconf/kid.d/50-keybindings || true)"
assert_eq "exactly one keybinding has a chord" "1" "${with_a_chord:-0}"

# The keybinding keyfile is generated from the live schemas at build time so a
# GNOME upgrade cannot quietly add a shortcut we forgot about.
# `grep -c` prints its count and exits 1 when the count is zero, so `|| true`
# rather than `|| echo 0` -- the latter would append a second line and turn the
# arithmetic below into a syntax error.
generated_bindings="$(grep -c '=@as \[\]$' /usr/share/kidnix/dconf/kid.d/50-keybindings 2>/dev/null || true)"
generated_bindings="${generated_bindings:-0}"
if (( generated_bindings >= 50 )); then
    _report ok "all ${generated_bindings} mutter keybindings are blanked"
else
    _report no "all mutter keybindings are blanked" "only ${generated_bindings} found"
fi

section "logind: no virtual terminals to land on"
assert_file /usr/lib/systemd/logind.conf.d/10-kidnix-kiosk.conf
logind_config="$(systemd-analyze cat-config systemd/logind.conf 2>/dev/null || true)"
if grep -q '^NAutoVTs=0$' <<<"${logind_config}"; then
    _report ok "NAutoVTs=0 is in force (no autovt@ttyN to switch to)"
else
    _report no "NAutoVTs=0 is in force" "not present in the merged logind config"
fi
if grep -q '^ReserveVT=0$' <<<"${logind_config}"; then
    _report ok "ReserveVT=0 is in force"
else
    _report no "ReserveVT=0 is in force" "not present in the merged logind config"
fi
# Recovery must survive: getty@tty1 is what a parent gets from
# `systemd.unit=multi-user.target` on the kernel command line.
assert_cmd "getty@tty1.service still enabled (recovery console)" \
    systemctl is-enabled getty@tty1.service

section "kiosk resilience"
assert_exec /usr/libexec/kidnix-app-supervisor
# The session no longer runs the payload under this bash supervisor: it runs
# the shell as kidnix-shell.service with Restart=always, which is the
# upstream-shaped version of the same promise (and the only shape that also
# gives us an active graphical-session.target and therefore portals). See
# docs/spikes/session-integration.md. The supervisor itself stays on the image
# for now, still tested below, until the thinker signs off on deleting it.
assert_grep '^Restart=always$' /usr/lib/systemd/user/kidnix-shell.service \
    "the kid session restarts the shell if it dies"
assert_cmd "kidnix-app-supervisor is valid bash" bash -n /usr/libexec/kidnix-app-supervisor
# A supervisor that gives up leaves a child staring at a black screen.
assert_grep 'while true' /usr/libexec/kidnix-app-supervisor \
    "supervisor never stops restarting the payload"
# Prove it actually restarts something, with a payload that fails instantly.
supervisor_log="$(timeout 6 /usr/libexec/kidnix-app-supervisor /usr/bin/false 2>&1 || true)"
starts="$(grep -c '^kidnix-app-supervisor: starting:' <<<"${supervisor_log}" || true)"
if (( starts >= 3 )); then
    _report ok "supervisor restarted a crashing payload ${starts}x in 6s with backoff"
else
    _report no "supervisor restarts a crashing payload" "only ${starts} start(s): ${supervisor_log:0:200}"
fi

section "audio ceiling"
assert_exec /usr/libexec/kidnix-audio-cap
assert_file /usr/lib/systemd/system/kidnix-audio-cap.service
assert_file /usr/share/wireplumber/wireplumber.conf.d/50-kidnix-soft-mixer.conf
assert_grep 'api\.alsa\.soft-mixer = true' \
    /usr/share/wireplumber/wireplumber.conf.d/50-kidnix-soft-mixer.conf \
    "PipeWire is told not to touch the hardware mixer"
assert_cmd "kidnix-audio-cap is valid bash" bash -n /usr/libexec/kidnix-audio-cap
# No sound card in a container: the cap must exit cleanly rather than fail the boot.
if /usr/libexec/kidnix-audio-cap >/dev/null 2>&1; then
    _report ok "kidnix-audio-cap exits 0 on a machine with no sound card"
else
    _report no "kidnix-audio-cap exits 0 on a machine with no sound card"
fi
if [[ -L /etc/systemd/system/multi-user.target.wants/kidnix-audio-cap.service ]]; then
    _report ok "kidnix-audio-cap.service enabled"
else
    _report no "kidnix-audio-cap.service enabled" "no symlink"
fi
# The filter-chain limiter is staged, not active -- see docs/spikes/lockdown.md.
assert_file /usr/share/kidnix/examples/pipewire-kidnix-limiter.conf
if compgen -G '/usr/share/pipewire/pipewire.conf.d/*kidnix*' >/dev/null; then
    _report no "the unverified filter-chain limiter is NOT active" "it is enabled"
else
    _report ok "the unverified filter-chain limiter is NOT active (staged only)"
fi

section "health checks and rollback"
for check in /usr/lib/greenboot/check/required.d/10-kidnix-accounts.sh \
             /usr/lib/greenboot/check/required.d/20-kidnix-egress.sh \
             /usr/lib/greenboot/check/required.d/30-kidnix-session.sh \
             /usr/lib/greenboot/check/wanted.d/10-kidnix-graphical.sh; do
    assert_exec "${check}"
    assert_cmd "$(basename "${check}") is valid bash" bash -n "${check}"
done

# The red.d hook that makes automatic rollback real on a btrfs /boot
# (docs/spikes/rollback.md): without it a bad update reboot-loops for ever.
assert_exec /usr/lib/greenboot/red.d/10-kidnix-boot-counter.sh \
    "greenboot red.d decrements boot_counter from Linux (btrfs /boot)"
assert_exec /usr/libexec/greenboot/greenboot
assert_file /usr/lib/systemd/system/greenboot-healthcheck.service

# The self-test hook (Containerfile: --build-arg KIDNIX_SELFTEST_BREAK_HEALTH=1)
# installs an always-failing REQUIRED check so `just test-rollback` can prove a
# bad update rolls itself back. A shipped image carrying it would red-boot on
# every single boot and roll itself back to nothing, so its absence is asserted
# here rather than trusted to the build argument's default.
if [[ -e /usr/lib/greenboot/check/required.d/99-kidnix-selftest-broken.sh ]]; then
    _report no "the rollback self-test's broken check is ABSENT" \
        "this image would fail every boot; it was built with KIDNIX_SELFTEST_BREAK_HEALTH=1"
else
    _report ok "the rollback self-test's broken check is ABSENT (test-only, see docs/spikes/rollback.md)"
fi
if [[ -L /etc/systemd/system/multi-user.target.wants/greenboot-healthcheck.service \
   || -L /etc/systemd/system/boot-complete.target.requires/greenboot-healthcheck.service ]]; then
    _report ok "greenboot-healthcheck.service enabled"
else
    _report no "greenboot-healthcheck.service enabled" "no symlink"
fi
# greenboot's rollback is GRUB-level: boot_counter reaches -1 and the
# bootloader picks entry 1. That snippet comes from bootupd, not greenboot.
assert_file /usr/lib/bootupd/grub2-static/configs.d/08_greenboot.cfg
assert_grep 'boot_counter' /usr/lib/bootupd/grub2-static/configs.d/08_greenboot.cfg \
    "GRUB carries greenboot's boot_counter fallback (how rollback actually fires)"

section "updates: no surprise reboots"
if [[ "$(readlink -f /etc/systemd/system/bootc-fetch-apply-updates.timer 2>/dev/null)" == /dev/null ]]; then
    _report ok "bootc-fetch-apply-updates.timer is masked"
else
    _report no "bootc-fetch-apply-updates.timer is masked" \
        "$(systemctl is-enabled bootc-fetch-apply-updates.timer 2>&1 | head -1)"
fi
# The parent panel will drive upgrades; bootc itself must still be there.
assert_exec /usr/sbin/bootc

section "bootc hygiene (lockdown files)"
# Everything the lockdown owns lives in /usr (image-owned, no 3-way merge)
# except the two-line dconf profile selector, which dconf only looks for in
# /etc.
if [[ -z "$(find /var -mindepth 1 -maxdepth 1 ! -name lib ! -name home -print -quit 2>/dev/null)" ]]; then
    _report ok "/var carries no lockdown content"
else
    _report no "/var carries no lockdown content" \
        "found: $(find /var -mindepth 1 -maxdepth 1 ! -name lib ! -name home -printf '%f ' 2>/dev/null)"
fi

section "trackpad hardening (research 09 Q7)"
# 09 Q7: the trackpad is the worst pointing device in the house for a
# five-year-old and the one cheap laptops ship with. "Optimise for mouse and
# touch; treat the trackpad as the degraded path, and harden it in software."
assert_file /usr/share/kidnix/dconf/kid.d/11-trackpad
assert_file /usr/share/kidnix/dconf/kid.d/locks/11-trackpad

# Accidental taps from a resting palm are the dominant failure mode; a
# physical click is required instead.
dconf_is org.gnome.desktop.peripherals.touchpad tap-to-click false
dconf_locked org.gnome.desktop.peripherals.touchpad tap-to-click
# 'fingers' = libinput clickfinger: pressing ANYWHERE with one finger is a
# left click. 'areas' (and 'default', which resolves to button-areas on every
# non-Apple touchpad) would make the bottom-right of the pad a right-click
# zone, i.e. a position-driven misfire for a child who presses wherever their
# finger lands.
dconf_is org.gnome.desktop.peripherals.touchpad click-method "'fingers'"
dconf_locked org.gnome.desktop.peripherals.touchpad click-method
# Both scroll booleans false is how you say "no scrolling" to mutter: it picks
# two-finger, else edge, else the disabled method. 06 §7.1 spec 11 says never
# require scroll, so nothing depends on it.
dconf_is org.gnome.desktop.peripherals.touchpad two-finger-scrolling-enabled false
dconf_is org.gnome.desktop.peripherals.touchpad edge-scrolling-enabled false
dconf_locked org.gnome.desktop.peripherals.touchpad two-finger-scrolling-enabled
dconf_locked org.gnome.desktop.peripherals.touchpad edge-scrolling-enabled
# The pointer must never silently die: 'disabled-on-external-mouse' would turn
# the trackpad off when a mouse appears, which a child cannot diagnose.
dconf_is org.gnome.desktop.peripherals.touchpad send-events "'enabled'"
dconf_locked org.gnome.desktop.peripherals.touchpad send-events
# Palm rejection, as far as GNOME exposes it.
dconf_is org.gnome.desktop.peripherals.touchpad disable-while-typing true
dconf_locked org.gnome.desktop.peripherals.touchpad disable-while-typing
dconf_is org.gnome.desktop.peripherals.touchpad middle-click-emulation false
dconf_is org.gnome.desktop.peripherals.touchpad accel-profile "'flat'"
dconf_starts org.gnome.desktop.peripherals.touchpad speed -0.2
# Nothing a child needs lives at a screen edge (06 §7.1 spec 17).
dconf_is org.gnome.mutter edge-tiling false
dconf_locked org.gnome.mutter edge-tiling
# Convertibles: no screen spinning because the machine got tilted.
dconf_is org.gnome.settings-daemon.peripherals.touchscreen orientation-lock true

# The two keys a parent must still be able to change. A lock here would be
# silent and unfixable without a new image.
dconf_writable() {
    local schema="$1" key="$2" got
    got="$(DCONF_PROFILE=kid gsettings writable "${schema}" "${key}" 2>/dev/null || echo '<error>')"
    assert_eq "kid: ${schema} ${key} stays parent-changeable" "true" "${got}"
}
dconf_writable org.gnome.desktop.peripherals.touchpad speed
dconf_writable org.gnome.settings-daemon.peripherals.touchscreen orientation-lock

# libmutter reads these keys itself, which is what makes them apply in a
# gnome-kiosk session with no gnome-settings-daemon in it.
mutter_libs=(/usr/lib64/libmutter-*.so.*)
mutter_lib=""
[[ -f "${mutter_libs[0]}" ]] && mutter_lib="${mutter_libs[0]}"
if [[ -n "${mutter_lib}" ]] && grep -qaF 'two-finger-scrolling-enabled' "${mutter_lib}"; then
    _report ok "libmutter reads the touchpad keys (they apply without gsd)"
else
    _report no "libmutter reads the touchpad keys (they apply without gsd)" \
        "not found in '${mutter_lib:-<no libmutter>}'"
fi
# gnome-kiosk binds no multi-finger gestures of its own -- mutter forwards
# touchpad swipes to the client as zwp_pointer_gestures_v1 and nothing in the
# session consumes them (gnome-shell's SwipeTracker is not running here).
# There is no gsettings key for gestures, so this is the only assertion
# available. See docs/spikes/lockdown.md §1.3b.
if grep -qaE 'swipe|gesture' /usr/bin/gnome-kiosk; then
    _report no "gnome-kiosk binds no swipe gestures" "gesture strings found in the binary"
else
    _report ok "gnome-kiosk binds no swipe gestures"
fi

# The touchpad schema must be described in exactly one keyfile: two keyfiles
# setting one key is resolved by dconf compile in directory order, which is
# not something anyone should have to reason about.
# Anchored so prose about the move does not count; -d skip because locks/ is a
# directory.
touchpad_files="$({ grep -lE -d skip '^\[org/gnome/desktop/peripherals/touchpad\]$' \
    /usr/share/kidnix/dconf/kid.d/* || true; } | wc -l)"
assert_eq "the touchpad schema lives in exactly one keyfile" "1" "${touchpad_files}"

# -----------------------------------------------------------------------------

printf '\n\033[1m%d passed, %d failed\033[0m\n' "${pass}" "${fail}"
[[ "${fail}" -eq 0 ]]
