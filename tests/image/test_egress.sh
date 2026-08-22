#!/usr/bin/bash
# Static gates on "the child session has no network egress" (AGENTS.md
# non-negotiable #5, docs/research/03 §3, audit item 9).
#
#   just test-image egress
#   podman run --rm -v ./tests/image:/tests:ro,z --entrypoint /bin/bash \
#       localhost/kidnix:latest /tests/test_egress.sh
#
# This is the CI gate that runs on every build, in seconds, with no VM. It
# proves the lockdown is *installed and internally consistent*. It CANNOT prove
# a packet is dropped -- nothing here is booted and a container has no netfilter
# hook of its own. That claim belongs to the packet capture in
# tests/boot/bcvk_boot_test.py, and the evidence is in docs/spikes/egress-proof.md.
#
# Deliberately narrower and louder than test_lockdown.sh, which covers the whole
# child lockdown: everything in this file is about one sentence a parent is told.
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

# assert_grep <regex> <file> <description>
assert_grep() {
    if grep -Eq "$1" "$2" 2>/dev/null; then ok "$3"; else no "$3" "no match for /$1/ in $2"; fi
}

# assert_cmd <description> <command...>
assert_cmd() {
    local name="$1"; shift
    if "$@" >/dev/null 2>&1; then ok "${name}"; else no "${name}" "command failed: $*"; fi
}

section() { printf '\n\033[1m%s\033[0m\n' "$1"; }

readonly NFT_RULESET=/usr/lib/kidnix/nftables/kidnix-egress.nft
readonly EGRESS_UNIT=/usr/lib/systemd/system/kidnix-egress.service
readonly FLATPAK_SEED=/usr/share/kidnix/flatpak/overrides-global

printf '\033[1mkidnix egress gate\033[0m -- %s\n' "$(sed -n 's/^PRETTY_NAME="\(.*\)"$/\1/p' /usr/lib/os-release)"

# -----------------------------------------------------------------------------
section "1. the nftables ruleset"
# -----------------------------------------------------------------------------

if [[ -f "${NFT_RULESET}" ]]; then ok "ruleset ${NFT_RULESET} is shipped"; else
    no "ruleset ${NFT_RULESET} is shipped" "missing"
fi

# `nft -c` initialises a netlink cache even in check mode, which needs
# CAP_NET_ADMIN over a netns. `unshare -rn` gives us a throwaway one where we
# are root -- the same trick build_files/40-lockdown.sh uses, and the reason
# this test can run rootless. It still rejects real syntax errors; verified by
# feeding it a broken ruleset below.
if unshare -rn nft -c -f "${NFT_RULESET}" >/dev/null 2>&1; then
    ok "the ruleset parses (unshare -rn nft -c -f)"
else
    no "the ruleset parses (unshare -rn nft -c -f)" "$(unshare -rn nft -c -f "${NFT_RULESET}" 2>&1 | head -1)"
fi

# A parser that always says yes proves nothing. Prove it says no.
broken="$(mktemp)"
printf 'table inet kidnix_broken {\n  chain c { meta skuid "definitely-no-such-user" drop; }\n}\n' >"${broken}"
if unshare -rn nft -c -f "${broken}" >/dev/null 2>&1; then
    no "the parse check can actually fail" "it accepted a ruleset naming a nonexistent user"
else
    ok "the parse check can actually fail (rejects an unknown username)"
fi
rm -f "${broken}"

assert_grep '^[[:space:]]*meta skuid 1000 .*reject' "${NFT_RULESET}" \
    "uid 1000 is rejected, not merely counted"

# `reject`, not `drop`: a child's activity must error out immediately rather
# than hang for two minutes on a TCP timeout. The boot test asserts the
# consequence (every attempt fails in well under a second).
assert_grep 'reject with icmpx type admin-prohibited' "${NFT_RULESET}" \
    "the reject is icmpx admin-prohibited, so failures are instant"

assert_grep '^[[:space:]]*counter|counter reject|reject.*counter|meta skuid 1000 counter' "${NFT_RULESET}" \
    "the rule carries a counter, so an attempt is visible in \`nft list ruleset\`"

# Loopback must be accepted BEFORE the uid rule or speech-dispatcher, the Piper
# server and the parent-panel socket all die with the network. Ordering, not
# mere presence, is the assertion.
lo_line="$(grep -n 'oif "lo" accept' "${NFT_RULESET}" | head -1 | cut -d: -f1)"
uid_line="$(grep -n 'meta skuid 1000 counter reject with icmpx' "${NFT_RULESET}" | head -1 | cut -d: -f1)"
if [[ -n "${lo_line}" && -n "${uid_line}" && "${lo_line}" -lt "${uid_line}" ]]; then
    ok "loopback is accepted before the uid rule (line ${lo_line} < ${uid_line})"
else
    no "loopback is accepted before the uid rule" "lo at '${lo_line:-none}', uid at '${uid_line:-none}'"
fi

# The rule is numeric because `kid` does not exist inside a build container.
# That is only safe while sysusers really does pin the account to 1000.
assert_grep '^u[[:space:]]+kid[[:space:]]+1000:1000[[:space:]]' /usr/lib/sysusers.d/kidnix.conf \
    "sysusers pins kid to uid 1000, which is what the ruleset filters"

# The whole table is `inet`, not `ip` -- otherwise IPv6 would be an open door.
assert_grep '^table inet kidnix_egress$' "${NFT_RULESET}" \
    "the table is 'inet', so IPv6 is filtered too, not only IPv4"

# -----------------------------------------------------------------------------
section "2. the unit that loads it"
# -----------------------------------------------------------------------------

assert_grep '^ExecStart=/usr/sbin/nft -f /usr/lib/kidnix/nftables/kidnix-egress\.nft$' \
    "${EGRESS_UNIT}" "the unit loads the shipped ruleset"

# Ordered ahead of anything that can route a packet. network-pre.target is the
# documented hook for exactly this; DefaultDependencies=no is what lets us sit
# in front of basic.target without an ordering cycle.
assert_grep '^Before=.*network-pre\.target' "${EGRESS_UNIT}" \
    "the unit is ordered Before=network-pre.target"
assert_grep '^DefaultDependencies=no$' "${EGRESS_UNIT}" \
    "DefaultDependencies=no, so it really can be first"

# `systemctl enable` at build time writes the wants link into /etc, which is
# where an installed machine reads it from; the unit itself is image-owned
# under /usr. Both roots are searched so a future preset-based enable is not a
# spurious failure.
for target in multi-user graphical; do
    if [[ -e "/etc/systemd/system/${target}.target.wants/kidnix-egress.service" \
       || -e "/usr/lib/systemd/system/${target}.target.wants/kidnix-egress.service" ]]; then
        ok "kidnix-egress.service is enabled in ${target}.target"
    else
        no "kidnix-egress.service is enabled in ${target}.target" \
            "no wants link in /etc or /usr for ${target}.target"
    fi
done

# graphical.target is where a child's session actually lands, so the wants link
# above is the one that matters most; assert the unit is not merely present.
assert_cmd "systemctl is-enabled kidnix-egress.service" \
    systemctl is-enabled kidnix-egress.service

# A boot where the ruleset silently failed to load must be a *failed* boot.
if [[ -x /usr/lib/greenboot/check/required.d/20-kidnix-egress.sh ]]; then
    ok "greenboot re-asserts the egress rule on every boot (required.d)"
else
    no "greenboot re-asserts the egress rule on every boot (required.d)" \
        "20-kidnix-egress.sh missing or not executable"
fi

# -----------------------------------------------------------------------------
section "3. Flatpak: no network namespace to send from"
# -----------------------------------------------------------------------------

assert_grep '^shared=!network;$' "${FLATPAK_SEED}" \
    "the global Flatpak override unshares the network"
assert_grep '/var/lib/flatpak/overrides/global' /usr/lib/tmpfiles.d/kidnix-lockdown.conf \
    "tmpfiles seeds that override into the system installation on first boot"

# -----------------------------------------------------------------------------
section "4. polkit: kid may not touch the network stack"
# -----------------------------------------------------------------------------

polkit_denies() {
    if /usr/libexec/kidnix-polkit-check kid "$1" NO >/dev/null 2>&1; then
        ok "polkit denies kid $1"
    else
        no "polkit denies kid $1" "expected NO"
    fi
}

polkit_denies org.freedesktop.NetworkManager.enable-disable-wifi
polkit_denies org.freedesktop.NetworkManager.enable-disable-network
polkit_denies org.freedesktop.NetworkManager.settings.modify.system
polkit_denies org.freedesktop.NetworkManager.network-control
# firewalld's action ids live under org.fedoraproject., not org.freedesktop.
polkit_denies org.fedoraproject.FirewallD1.all

# ...and does not touch the parent, who has to be able to set the Wi-Fi up.
if /usr/libexec/kidnix-polkit-check parent \
        org.freedesktop.NetworkManager.settings.modify.system NOT_HANDLED >/dev/null 2>&1; then
    ok "polkit leaves the parent's NetworkManager access alone"
else
    no "polkit leaves the parent's NetworkManager access alone" "expected NOT_HANDLED"
fi

# -----------------------------------------------------------------------------
section "5. the known gap: setuid, and why it stays closed"
# -----------------------------------------------------------------------------
#
# `meta skuid` matches the EFFECTIVE uid of the socket's owner. A setuid-root
# network helper launched by kid would therefore appear to netfilter as uid 0
# and walk straight out. docs/spikes/lockdown.md records this as the one known
# gap in the mechanism; these assertions are what keep it theoretical.
#
# File *capabilities* are a different matter and are fine: cap_net_raw does not
# change the euid, so a raw socket opened by a capability-carrying binary that
# kid ran is still owned by uid 1000 and still hits the rule. That is why
# arping/clockdiff/mtr-packet below are allowed to exist.

mapfile -t setuid_bins < <(find /usr -xdev -perm -4000 -type f 2>/dev/null | sort)
printf '  ...  %d setuid-root binaries in /usr: %s\n' \
    "${#setuid_bins[@]}" "$(printf '%s ' "${setuid_bins[@]##*/}")"

# Anything here going setuid-root would hand kid an unfiltered socket.
NETWORK_TOOLS=(
    ping ping6 traceroute traceroute6 tracepath arping clockdiff mtr mtr-packet
    curl wget nc ncat netcat socat telnet ftp ssh scp sftp rsync
    tcpdump nmap dig host nslookup getent nft iptables ip
)
setuid_network=()
for bin in "${setuid_bins[@]}"; do
    for tool in "${NETWORK_TOOLS[@]}"; do
        [[ "${bin##*/}" == "${tool}" ]] && setuid_network+=("${bin}")
    done
done
if (( ${#setuid_network[@]} == 0 )); then
    ok "no network-capable binary is setuid-root (${#NETWORK_TOOLS[@]} names checked)"
else
    no "no network-capable binary is setuid-root" "${setuid_network[*]}"
fi

# Fedora 44's ping uses a datagram socket via net.ipv4.ping_group_range rather
# than setuid or cap_net_raw. Assert BOTH, because either would reopen the gap.
if [[ -u /usr/bin/ping ]]; then
    no "ping is not setuid" "$(ls -l /usr/bin/ping)"
else
    ok "ping is not setuid (Fedora 44 uses ping_group_range datagram sockets)"
fi
ping_caps="$(getcap /usr/bin/ping 2>/dev/null)"
if [[ -z "${ping_caps}" ]]; then
    ok "ping carries no file capabilities either"
else
    no "ping carries no file capabilities either" "${ping_caps}"
fi

# capsh is the documented way to read a capability set; assert it is present so
# the check above is a real read and not a silently-empty one.
assert_cmd "capsh/getcap are available, so the capability check is real" \
    bash -c 'command -v getcap && command -v capsh'

# Belt and braces on the reasoning above: nothing may be setuid-root AND carry
# cap_net_raw, which is the one combination the rule cannot see through.
raw_and_suid=()
while read -r path caps; do
    [[ -n "${path}" ]] || continue
    [[ "${caps}" == *cap_net_raw* ]] || continue
    [[ -u "${path}" ]] && raw_and_suid+=("${path}")
done < <(getcap -r /usr 2>/dev/null)
if (( ${#raw_and_suid[@]} == 0 )); then
    ok "no binary is both setuid-root and cap_net_raw (the one combination skuid cannot see)"
else
    no "no binary is both setuid-root and cap_net_raw" "${raw_and_suid[*]}"
fi

# -----------------------------------------------------------------------------
section "6. kid has no way to become someone the rule does not match"
# -----------------------------------------------------------------------------

# sudo would make uid 1000 into uid 0, and the rule matches uid, not user.
if grep -rqE '^[[:space:]]*kid[[:space:]]' /etc/sudoers /etc/sudoers.d/* 2>/dev/null; then
    no "kid has no sudoers entry" "$(grep -rnE '^[[:space:]]*kid[[:space:]]' /etc/sudoers /etc/sudoers.d/* 2>/dev/null | head -1)"
else
    ok "kid has no sudoers entry"
fi

# /etc/sudoers grants %wheel; kid must therefore not be in wheel. The account
# does not exist inside a build container, so sysusers is the source of truth.
if grep -qE '^m[[:space:]]+kid[[:space:]]' /usr/lib/sysusers.d/kidnix.conf; then
    no "kid is in no supplementary groups" \
        "$(grep -E '^m[[:space:]]+kid[[:space:]]' /usr/lib/sysusers.d/kidnix.conf)"
else
    ok "kid is in no supplementary groups (sysusers adds only parent to wheel)"
fi

# polkit's pkexec is the other route to uid 0.
assert_cmd "polkit denies kid org.freedesktop.policykit.exec (pkexec)" \
    /usr/libexec/kidnix-polkit-check kid org.freedesktop.policykit.exec NO

# ssh is a network service that would run code as kid from off-machine.
assert_grep '^DenyUsers kid$' /etc/ssh/sshd_config.d/10-kidnix.conf \
    "sshd denies kid outright"

# DNS is the one thing that must be rejected BEFORE loopback: systemd-resolved
# listens on 127.0.0.53 and re-sends kid's queries as uid 990, so the uplink
# rule never sees them (docs/spikes/egress-proof.md §4).
dns_line="$(grep -n 'meta skuid 1000 udp dport 53' "${NFT_RULESET}" | head -1 | cut -d: -f1)"
if [[ -n "${dns_line}" && -n "${lo_line}" && "${dns_line}" -lt "${lo_line}" ]]; then
    ok "kid's DNS (udp/53) is rejected before loopback is accepted (line ${dns_line} < ${lo_line})"
else
    no "kid's DNS (udp/53) is rejected before loopback is accepted" "dns at '${dns_line:-none}', lo at '${lo_line:-none}'"
fi
if grep -q 'meta skuid 1000 tcp dport 53' "${NFT_RULESET}"; then
    ok "kid's DNS over tcp/53 is rejected too"
else
    no "kid's DNS over tcp/53 is rejected too" "no tcp dport 53 rule"
fi

# nss-resolve talks to systemd-resolved over varlink, not port 53, so glibc
# lookups must not use it: the image drops `resolve` from the hosts line and
# lets glibc's `dns` module send to the stub, where the uid rule catches it.
if grep -E '^hosts:' /etc/nsswitch.conf | grep -qw resolve; then
    no "nsswitch hosts line does not use nss-resolve" "$(grep -E '^hosts:' /etc/nsswitch.conf)"
else
    ok "nsswitch hosts line does not use nss-resolve ($(grep -E '^hosts:' /etc/nsswitch.conf | tr -s ' '))"
fi

# -----------------------------------------------------------------------------
printf '\n\033[1m==> %d passed, %d failed\033[0m\n' "${pass}" "${fail}"
if (( fail > 0 )); then
    printf '\nThe egress claim is the one AGENTS.md non-negotiable a parent is told\n'
    printf 'in plain words. Do not ship a red build here.\n' >&2
    exit 1
fi
exit 0
