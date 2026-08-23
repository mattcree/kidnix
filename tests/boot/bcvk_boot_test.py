#!/usr/bin/env python3
"""Rootless boot test: boot the kidnix *container image* as a VM with bcvk.

This is the fast loop. `bcvk ephemeral` boots the OCI image directly under
QEMU/KVM -- the container's filesystem is exported over virtiofs as the VM's
root, so there is no disk image to build and, crucially, **no sudo anywhere**.
A cold run takes well under a minute against an already-built image.

    just build && just test-boot

What it proves: the machine reaches graphical.target, GDM autologs `kid` in,
that session is a *Wayland* session, `gnome-kiosk` is actually running as
`kid`, kid's `graphical-session.target` is active (so the portals start), the
activity shell is running and comes back when it is killed, and `kid` genuinely
cannot reach the network while root can. That is the whole point of kidnix, and
none of it is visible to `just test-image`.

What it does NOT prove: anything about the bootloader, the composefs root,
partitioning, or first-boot units gated on real hardware -- `bcvk ephemeral`
boots the kernel directly and roots on virtiofs. `just test-boot-qcow2` is the
full-fidelity counterpart; run it before believing an image will install.

Python 3.9+, standard library only, deliberately: this runs unchanged on a CI
runner and on a dev laptop with nothing installed.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

# bcvk lands here when installed by `just bcvk-install`; a distro package on
# PATH is preferred if one exists.
LOCAL_BIN = Path.home() / ".local" / "bin"

PROBE_BEGIN = "KIDNIX_PROBE_BEGIN"
PROBE_END = "KIDNIX_PROBE_END"

# systemd is chatty in colour and pipes through a pager even over ssh; both
# corrupt the key=value block we parse. Belt and braces: strip ANSI in Python.
ANSI = re.compile(r"\x1b\[[0-9;:]*[A-Za-z]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)")

# `systemctl is-system-running` after a healthy boot. 'degraded' is accepted
# on purpose: under bcvk there is no ESP, so bootloader-update.service always
# fails. Individual units we care about are asserted by name instead.
HEALTHY_SYSTEM_STATES = frozenset({"running", "degraded"})

# Units allowed to be failed without failing the test, with the reason why.
# Keep this list short and justified -- it is the place a real regression hides.
EXPECTED_FAILED_UNITS = {
    "bootloader-update.service": "no ESP: bcvk ephemeral boots the kernel directly",
    # Same root cause, one layer up: bcvk roots the VM on virtiofs and never
    # mounts /boot, so greenboot's "am I allowed to mark this boot good"
    # bookkeeping (`Failed to check boot mount state: Failed to read mount
    # info`) cannot run. The health *checks* themselves pass -- the journal
    # shows all three required.d scripts succeeding. A disk boot
    # (`just test-boot-qcow2`) is where greenboot can actually be judged.
    "greenboot-healthcheck.service": "no /boot mount: bcvk ephemeral roots on virtiofs",
    "greenboot-set-rollback-trigger.service": "no /boot mount: bcvk ephemeral roots on virtiofs",
    # Hardware, not us. mcelog refuses to run on AMD ("Please use the
    # edac_mce_amd module instead") and exits non-zero, so this unit fails on
    # any AMD host and is invisible on an Intel one -- which is exactly the
    # difference between a GitHub runner (EPYC) and the developer's machine.
    # Masking it in the image would be tidier; that is system_files/, not the
    # test harness's to change.
    "mcelog.service": "mcelog does not support AMD CPUs; fails on AMD hosts only",
}

# `bcvk ephemeral ssh` does NOT return an error while the guest is still
# booting -- it blocks inside bcvk until sshd answers. So each poll attempt can
# legitimately outlive the whole boot, and a fixed per-attempt timeout is a lie
# about what we are measuring. This is only how often we come up for air to
# re-check that the VM container is still alive and to print progress; the real
# ceiling is --timeout. (A fixed 30 s slice here, with TimeoutExpired escaping
# the retry loop, is exactly what made this test fail on GitHub Actions in 31 s
# while claiming a 360 s budget. See tests/README.md, "In CI".)
SSH_POLL_SECONDS = 60

# How long the shell gets to come back after we kill it. kidnix-shell.service
# is Restart=always / RestartSec=1, so this is generous by an order of
# magnitude; it is a ceiling, not a target.
SHELL_RESTART_BUDGET_SECONDS = 10

# --- the egress proof (docs/spikes/egress-proof.md) -------------------------
# How many different ways kid must be shown to fail to get out. Seven are coded
# in the probe (HTTP by IP, HTTPS by name, raw UDP, ICMP, IPv6, a raw TCP
# connect, and a systemd-spawned unit); the floor is the count, so removing one
# is a deliberate edit rather than a silent weakening.
EGRESS_MIN_ATTEMPTS = 7

# Each attempt must fail on the `reject` (an instant ICMP admin-prohibited or
# EACCES), not on curl's 5 s timeout. A timeout would mean the packet went out
# and no reply came back -- a much weaker claim than the one we make to parents.
EGRESS_FAIL_FAST_SECONDS = 3.0

# The uid-1000 counter must move by at least this much across the attempts.
# Some attempts cost more than one packet (curl retries, IPv6 tries both
# addresses), none cost fewer than one, so the floor is the attempt count.
# Observed on a healthy run: +13.
EGRESS_MIN_COUNTER_DELTA = 7

# --- a KNOWN GAP, proven by this test rather than argued about --------------
#
# `getent hosts <name>` as kid succeeds and the query really does leave the
# machine. The rule is not broken: the packet is sent by systemd-resolved
# (uid 990) over its own socket, after kid reached it through the LOOPBACK
# socket the ruleset deliberately accepts. `meta skuid` matches the socket's
# owner, and that socket is not kid's.
#
# So "the child session has no network egress" is true of every direct socket
# and false of DNS. It is a low-bandwidth two-way channel: arbitrary labels go
# out in the question, addresses come back in the answer.
#
# This is asserted as the CURRENT state, not as an acceptable one. When the
# ruleset grows the one line that closes it --
#
#     meta skuid 1000 udp dport 53 reject   (before the `oif "lo" accept`)
#
# -- this test goes red and points here. Flip the constant in the same commit.
# docs/spikes/egress-proof.md §4 has the full write-up and the options.
EGRESS_RESOLVED_DNS_STILL_ESCAPES = False

# Runs inside the guest as root. Emits one key=value block we can parse, then
# a human-readable dump for the log. Must not use `sudo` (it decorates output
# with OSC sequences) and must not fail the ssh session on a missing tool.
GUEST_PROBE = r"""
set +e
export SYSTEMD_COLORS=0 SYSTEMD_PAGER=cat SYSTEMD_URLIFY=0 SYSTEMD_LESS=

# Block until the boot transaction settles, bounded by our own caller timeout.
systemctl is-system-running --wait >/dev/null 2>&1

# ...but `--wait` only covers the SYSTEM manager. Everything this probe cares
# about lives in kid's per-user manager, which GDM starts afterwards, so wait
# for the session to settle too. Without this every assertion below races the
# login: plymouth holds the console for the first ~10 s, and gnome-session has
# a great deal more to do than v0.1's `exec gnome-kiosk` did.
uctl() { systemctl --user -M kid@ "$@" 2>/dev/null; }

tries=0
while [ "$tries" -lt 90 ]; do
    [ "$(uctl is-active kidnix-shell.service)" = "active" ] && break
    sleep 1
    tries=$(( tries + 1 ))
done

scan_kid_session() {
    kid_session=""; kid_type=""; kid_active=""
    for s in $(loginctl list-sessions --no-legend --no-pager 2>/dev/null | awk '{print $1}'); do
        name=$(loginctl show-session "$s" -p Name --value 2>/dev/null)
        [ "$name" = "kid" ] || continue
        type=$(loginctl show-session "$s" -p Type --value 2>/dev/null)
        # Prefer a graphical session if the user also has a manager session.
        if [ -z "$kid_session" ] || [ "$type" = "wayland" ]; then
            kid_session="$s"; kid_type="$type"
            kid_active=$(loginctl show-session "$s" -p Active --value 2>/dev/null)
        fi
    done
}

tries=0
while [ "$tries" -lt 60 ]; do
    scan_kid_session
    [ "$kid_type" = "wayland" ] && [ "$kid_active" = "yes" ] && break
    sleep 1
    tries=$(( tries + 1 ))
done

# The portals are D-Bus activated and are the LAST thing in the session to
# settle -- xdg-desktop-portal sits in 'activating' until
# xdg-desktop-portal-gnome has claimed its name. On a 2-core CI runner that is
# still happening when everything else is up, so sample them only once they
# have stopped moving. Waiting here is not weakening the assertion: 'active' is
# still required, this only stops us photographing the race.
tries=0
while [ "$tries" -lt 90 ]; do
    [ "$(uctl is-active xdg-desktop-portal.service)" = "active" ] \
        && [ "$(uctl is-active xdg-desktop-portal-gnome.service)" = "active" ] && break
    sleep 1
    tries=$(( tries + 1 ))
done

kiosk_pid=$(pgrep -x gnome-kiosk 2>/dev/null | head -1)
kiosk_user=""
[ -n "$kiosk_pid" ] && kiosk_user=$(ps -o user= -p "$kiosk_pid" 2>/dev/null | tr -d ' ')

# --- kid's own systemd user manager -----------------------------------------
# `uctl` (defined above) is how root reaches kid's per-user manager; nothing
# below is visible any other way. graphical-session.target being ACTIVE is the
# whole point of routing the session through gnome-session: the portals carry
# `Requisite=graphical-session.target`, which fails instantly if it is not.
kid_graphical_session=$(uctl is-active graphical-session.target)
kid_session_target=$(uctl is-active gnome-session@kidnix.target)
kid_kiosk_target=$(uctl is-active org.gnome.Kiosk.target)
kid_portal=$(uctl is-active xdg-desktop-portal.service)
kid_portal_gnome=$(uctl is-active xdg-desktop-portal-gnome.service)
kid_shell_unit=$(uctl is-active kidnix-shell.service)

# --- the shell process -------------------------------------------------------
# Ask systemd for the PID rather than pgrep. `pgrep -f kidnix-shell-app` also
# matches THIS SCRIPT -- the probe text is the command line of the shell
# running it -- and killing that instead of the real shell is a silent, total
# failure (the probe dies before it prints anything). Learned the hard way.
shell_main_pid() { uctl show kidnix-shell.service -p MainPID --value; }

shell_pid=$(shell_main_pid)
[ "$shell_pid" = "0" ] && shell_pid=""
shell_user=""
[ -n "$shell_pid" ] && shell_user=$(ps -o user= -p "$shell_pid" 2>/dev/null | tr -d ' ')
# -u kid keeps the root-owned probe out of the match for the same reason.
session_leader=$(pgrep -u kid -f 'gnome-session-service --session=kidnix' 2>/dev/null | head -1)

# DCONF_PROFILE has to reach processes the *user manager* started, not merely
# children of the session wrapper (docs/spikes/lockdown.md section 3, item 2).
kiosk_dconf=""
[ -n "$kiosk_pid" ] && kiosk_dconf=$(tr '\0' '\n' < "/proc/${kiosk_pid}/environ" 2>/dev/null \
    | sed -n 's/^DCONF_PROFILE=//p' | head -1)
shell_dconf=""
[ -n "$shell_pid" ] && shell_dconf=$(tr '\0' '\n' < "/proc/${shell_pid}/environ" 2>/dev/null \
    | sed -n 's/^DCONF_PROFILE=//p' | head -1)

# --- egress (docs/spikes/lockdown.md section 3, item 3) ----------------------
# The single most important boot assertion the lockdown spike asked for: prove
# the nftables rule drops a real packet, not just that it loaded.
nft_table=absent
nft list table inet kidnix_egress >/dev/null 2>&1 && nft_table=loaded
curl -s -o /dev/null -m 5 http://1.1.1.1/ >/dev/null 2>&1
egress_root=$?
runuser -u kid -- curl -s -o /dev/null -m 5 http://1.1.1.1/ >/dev/null 2>&1
egress_kid=$?

# --- egress proof, with a packet capture (docs/spikes/egress-proof.md) -------
#
# The block above is a differential: kid's curl fails, root's succeeds. That is
# necessary and not sufficient -- a curl can fail for a dozen reasons that have
# nothing to do with our rule, and "no reply came back" is not the same claim
# as "no packet left the machine". A parent is being told the second one.
#
# So this section puts an OBSERVER on the wire (tcpdump on the uplink, the
# same interface and the same capture filter for both windows) and runs two
# windows through it:
#
#   window A -- eight different egress attempts as uid 1000, by eight
#               different mechanisms. Expected: zero packets captured.
#   window B -- one root curl to the same address. Expected: packets.
#
# Window B is what makes window A mean anything: it proves the observer was
# watching the right interface with a filter that does catch traffic. Without
# it, "tcpdump saw nothing" is indistinguishable from "tcpdump was misconfigured".
#
# Then three mechanism checks: the rule survives `firewall-cmd --reload`, kid
# cannot flush it, and deleting it as root *unblocks* kid -- which is the only
# way to show that the nftables rule is the thing doing the blocking, and not
# some accident of the VM's networking. The table is reloaded from the shipped
# file afterwards and kid is re-tested, so the machine is left as it was found.

egress_tcpdump=$(rpm -q tcpdump 2>/dev/null || echo absent)
egress_uplink=$(ip -o -4 route show default 2>/dev/null | awk '{print $5}' | head -1)
[ -n "$egress_uplink" ] \
    || egress_uplink=$(ip -o link show 2>/dev/null | awk -F': ' '$2 != "lo" {print $2; exit}')

# Addresses nothing else on this machine talks to, so a packet matching this
# filter can only have come from an attempt below. Deliberately NOT the DNS
# resolver or the slirp gateway, which carry unrelated background chatter.
EGRESS_FILTER="not port 22 and (host 1.1.1.1 or host 8.8.8.8 or host 9.9.9.9 or host 203.0.113.9 or host 2606:4700:4700::1111)"

# nc is not in the image (nmap-ncat/netcat are not installed), so the raw UDP
# and raw TCP attempts are done with python3's socket module instead -- same
# syscalls, no extra package in a child's OS.
cat >/tmp/kidnix-egress-udp.py <<'PYEOF'
import socket, sys
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.settimeout(3)
try:
    s.sendto(b"kidnix-egress-probe", (sys.argv[1], int(sys.argv[2])))
except OSError as exc:
    print(exc)
    sys.exit(1)
sys.exit(0)
PYEOF

cat >/tmp/kidnix-egress-tcp.py <<'PYEOF'
import socket, sys
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(4)
try:
    s.connect((sys.argv[1], int(sys.argv[2])))
except OSError as exc:
    print(exc)
    sys.exit(1)
sys.exit(0)
PYEOF
chmod 0644 /tmp/kidnix-egress-udp.py /tmp/kidnix-egress-tcp.py

# Sum of every kid counter in the table: the general reject plus the two DNS
# rejects that sit before the loopback accept. A by-name attempt now dies on the
# DNS rule and never reaches the general one, so only the total is meaningful.
nft_counter() {
    nft list table inet kidnix_egress 2>/dev/null \
        | sed -n 's/.*counter packets \([0-9][0-9]*\) .*/\1/p' \
        | awk '{ s += $1 } END { print s + 0 }'
}

# `-U` (packet-buffered) and the drain wait in stop_capture are both load-
# bearing, and both were bought with a wrong answer. Without them tcpdump
# reports "0 packets captured, 9 packets received by filter" for traffic that
# demonstrably went out: the packets are sitting in the kernel ring buffer when
# SIGINT arrives and tcpdump exits without draining it. A capture that silently
# under-reports is the worst possible instrument for this particular claim --
# it would have turned "kid sent nothing" into a PASS for the wrong reason.
# The root control window exists to catch exactly that, and did.
start_capture() {
    rm -f "$1"
    tcpdump -i "$egress_uplink" -n -p -U -s 128 -w "$1" "$2" \
        >/tmp/kidnix-tcpdump.log 2>&1 &
    capture_pid=$!
    # tcpdump has to open the socket and install the BPF program before it can
    # miss nothing; the file appearing is the earliest honest signal.
    tries=0
    while [ "$tries" -lt 40 ]; do
        [ -f "$1" ] && break
        sleep 0.25
        tries=$(( tries + 1 ))
    done
    sleep 1
}

stop_capture() {
    sleep 2
    kill -INT "$capture_pid" 2>/dev/null
    wait "$capture_pid" 2>/dev/null
    sleep 0.5
}

count_capture() {
    tcpdump -r "$1" -n 2>/dev/null | wc -l | tr -d ' '
}

egress_attempts=0
egress_attempts_failed=0
egress_attempt_max=0
egress_attempt_rcs=""

# `runuser -u kid --` is the default runner; one attempt goes through
# `systemd-run --uid=1000` instead, because a transient unit is spawned by PID 1
# rather than inherited from this shell -- if `meta skuid` were somehow matching
# something inherited rather than the socket's owner, that is where it would show.
try_kid() {
    label="$1"; shift
    t0=$(date +%s.%N)
    "$@" >/dev/null 2>&1
    rc=$?
    t1=$(date +%s.%N)
    d=$(awk -v a="$t0" -v b="$t1" 'BEGIN { printf "%.2f", b - a }')
    egress_attempts=$(( egress_attempts + 1 ))
    [ "$rc" != "0" ] && egress_attempts_failed=$(( egress_attempts_failed + 1 ))
    egress_attempt_max=$(awk -v a="$egress_attempt_max" -v b="$d" \
        'BEGIN { print (b > a) ? b : a }')
    egress_attempt_rcs="${egress_attempt_rcs}${egress_attempt_rcs:+ }${label}:rc=${rc}/${d}s"
}

as_kid() { runuser -u kid -- "$@"; }

egress_counter_before=$(nft_counter)

start_capture /tmp/kid.pcap "$EGRESS_FILTER"

# 1. plain HTTP by IP -- no DNS involved, so a failure is the filter and
#    nothing else. curl exit 7 = "failed to connect to host".
try_kid http-v4      as_kid curl -s -o /dev/null -m 5 http://1.1.1.1/
# 2. HTTPS by name -- the whole stack: resolver, TCP, TLS.
try_kid https-name   as_kid curl -s -o /dev/null -m 5 https://example.com/
# 3. raw UDP to a nameserver, bypassing libc's resolver entirely.
try_kid udp-53       as_kid python3 /tmp/kidnix-egress-udp.py 8.8.8.8 53
# 4. ICMP. `ping` on Fedora 44 uses a datagram socket (net.ipv4.ping_group_range),
#    not a raw socket and not setuid -- so `meta skuid` still sees uid 1000.
try_kid icmp         as_kid ping -c 1 -W 2 1.1.1.1
# 5. IPv6, on the theory that a v4-shaped lockdown is a classic hole. The table
#    is `inet`, so it hooks both families -- this is where that gets proven.
try_kid http-v6      as_kid curl -s -o /dev/null -m 5 'http://[2606:4700:4700::1111]/'
# 6. a raw TCP connect() from python to a documentation address (TEST-NET-3),
#    to be certain nothing curl-specific is doing the work.
try_kid tcp-connect  as_kid python3 /tmp/kidnix-egress-tcp.py 203.0.113.9 80
# 7. spawned by PID 1 as uid 1000 rather than forked from this root shell.
try_kid systemd-run  systemd-run --quiet --pipe --wait --collect \
    --uid=1000 --gid=1000 -- curl -s -o /dev/null -m 5 http://9.9.9.9/

# Flatpak: the global override is `--unshare=network`, so a sandboxed app has no
# network namespace to send from at all. Nothing is installed in an ephemeral VM
# (the flatpaks land on first boot of a real install), so this reports rather
# than asserts -- see docs/spikes/egress-proof.md.
egress_flatpak_app=$(flatpak list --app --columns=application 2>/dev/null | head -1)
egress_flatpak_rc=""
if [ -n "$egress_flatpak_app" ]; then
    try_kid flatpak as_kid flatpak run --command=sh "$egress_flatpak_app" \
        -c 'curl -s -o /dev/null -m 5 http://1.1.1.1/'
    egress_flatpak_rc=$rc
fi

stop_capture
egress_kid_packets=$(count_capture /tmp/kid.pcap)
egress_counter_after=$(nft_counter)

# --- the control window: same interface, same filter, root instead of kid ----
start_capture /tmp/root.pcap "$EGRESS_FILTER"
curl -s -o /dev/null -m 5 http://1.1.1.1/ >/dev/null 2>&1
egress_control_rc=$?
stop_capture
egress_root_packets=$(count_capture /tmp/root.pcap)

# --- the hole this exercise found: DNS via systemd-resolved -----------------
#
# `getent hosts example.com` as kid SUCCEEDS, and the query leaves the machine.
# Nothing above is broken -- the rule is doing exactly what it says. The path
# simply does not go through a socket kid owns:
#
#     kid -> nss-resolve -> (varlink/D-Bus, a LOOPBACK socket, which the rule
#     deliberately accepts) -> systemd-resolved, running as uid 990 -> the
#     nameserver.
#
# `meta skuid` matches the socket owner, and the socket that carries the packet
# off the machine belongs to systemd-resolved, not to uid 1000. So a child (or
# anything running as the child) can cause a DNS query carrying arbitrary
# attacker-chosen labels to leave the machine, and can read the answer back.
# It is a low-bandwidth two-way channel, not "no egress".
#
# This window PROVES it rather than reasoning about it: capture port 53 on the
# uplink while kid resolves a name that cannot be in any cache, and count the
# packets that leave.
egress_dns_name="kidnix-egress-probe-$$.example.com"
start_capture /tmp/kid-dns.pcap "port 53"
runuser -u kid -- getent hosts "$egress_dns_name" >/dev/null 2>&1
egress_resolved_rc=$?
runuser -u kid -- getent hosts example.com >/dev/null 2>&1
egress_resolved_real_rc=$?
stop_capture
egress_dns_packets=$(count_capture /tmp/kid-dns.pcap)
# Other things on the box may legitimately resolve names during this window
# (the Flatpak first-boot timer, resolved's own refreshes), so the proof is
# whether KID'S label appears on the wire, not the raw port-53 count.
egress_dns_label_hits=$(tcpdump -r /tmp/kid-dns.pcap -A -n 2>/dev/null | grep -c "kidnix-egress-probe" || true)
egress_resolved_active=$(systemctl is-active systemd-resolved 2>/dev/null)

# --- does the rule survive firewalld reloading its own ruleset? -------------
egress_firewalld=$(systemctl is-active firewalld 2>/dev/null)
egress_reload_table=skipped
egress_reload_kid=""
if [ "$egress_firewalld" = "active" ]; then
    firewall-cmd --reload >/dev/null 2>&1
    sleep 1
    egress_reload_table=absent
    nft list table inet kidnix_egress >/dev/null 2>&1 && egress_reload_table=loaded
    runuser -u kid -- curl -s -o /dev/null -m 5 http://1.1.1.1/ >/dev/null 2>&1
    egress_reload_kid=$?
fi

# --- can kid take the rule away? --------------------------------------------
runuser -u kid -- nft flush ruleset >/dev/null 2>&1
egress_kid_flush_rc=$?
egress_after_kid_flush=absent
nft list table inet kidnix_egress >/dev/null 2>&1 && egress_after_kid_flush=loaded

# --- and is the rule really what is doing the blocking? ---------------------
# Delete it as root and watch kid get straight out. This is the control for the
# whole section: if kid still could not reach the network with the table gone,
# every PASS above would be measuring something else.
nft delete table inet kidnix_egress >/dev/null 2>&1
egress_after_root_delete=absent
nft list table inet kidnix_egress >/dev/null 2>&1 && egress_after_root_delete=loaded
runuser -u kid -- curl -s -o /dev/null -m 5 http://1.1.1.1/ >/dev/null 2>&1
egress_kid_unblocked=$?

nft -f /usr/lib/kidnix/nftables/kidnix-egress.nft >/dev/null 2>&1
egress_restored=absent
nft list table inet kidnix_egress >/dev/null 2>&1 && egress_restored=loaded
runuser -u kid -- curl -s -o /dev/null -m 5 http://1.1.1.1/ >/dev/null 2>&1
egress_kid_reblocked=$?

# --- the grown-up PIN, from the child's session (docs/spikes/pin-flow.md) ----
#
# The image ships /etc/kidnix/parent.toml with no pin_hash, so the gate opens
# on "choose a grown-up PIN" -- in the CHILD'S session, because that is the
# only session this machine ever shows anybody. Until 2026-08-23 that PIN
# could not be saved: 40-kidnix-kid.rules denied `kid` every "org.kidnix."
# action, so the chosen PIN lasted until the next restart. The rules file now
# grants exactly one id, org.kidnix.set-pin, and /usr/bin/kidnix-set-pin
# enforces the rule that makes that safe. Both halves are checked here, and
# only a booted machine can check them: polkitd is the thing answering.
pin_hash_at_boot=$(sed -n 's/^pin_hash *= *"\(.*\)"/\1/p' /etc/kidnix/parent.toml 2>/dev/null | head -1)

pin_rules_setpin=$(/usr/libexec/kidnix-polkit-check kid org.kidnix.set-pin 2>/dev/null)
pin_rules_tools=$(/usr/libexec/kidnix-polkit-check kid org.kidnix.parent-tools 2>/dev/null)

# pkcheck asks POLKITD, about a real process in kid's live graphical session --
# the dry-run evaluator above only asks the file. The pid,start-time,uid triple
# is the non-racy spelling of --process.
pin_pkcheck_setpin=""
pin_pkcheck_tools=""
if [ -n "$kiosk_pid" ] && [ -r "/proc/${kiosk_pid}/stat" ]; then
    pk_subject="${kiosk_pid},$(awk '{print $22}' "/proc/${kiosk_pid}/stat"),$(stat -c %u "/proc/${kiosk_pid}")"
    pkcheck --action-id org.kidnix.set-pin --process "$pk_subject" >/dev/null 2>&1
    pin_pkcheck_setpin=$?
    pkcheck --action-id org.kidnix.parent-tools --process "$pk_subject" >/dev/null 2>&1
    pin_pkcheck_tools=$?
fi

# And the thing the shell's PIN pad actually runs. </dev/null and a timeout on
# every one of these: a DENIED pkexec must fail immediately, and a hang here
# would mean polkit had gone looking for an authentication agent, which is
# itself the bug.
timeout 20 runuser -u kid -- pkexec /usr/bin/kidnix-set-pin --check </dev/null >/dev/null 2>&1
pin_pkexec_check=$?
# kidnix-wipe carries no exec.path annotation of its own, so pkexec falls back
# to org.freedesktop.policykit.exec; the helper it wraps DOES carry one
# (org.kidnix.parent-tools). Both routes must be shut to kid, so both are tried.
timeout 20 runuser -u kid -- pkexec /usr/bin/kidnix-wipe --check </dev/null >/dev/null 2>&1
pin_pkexec_wipe=$?
timeout 20 runuser -u kid -- pkexec /usr/libexec/kidnix-parent-tools wipe --check </dev/null >/dev/null 2>&1
pin_pkexec_tools=$?

# 1. THE FIRST SET, which is the whole reason the carve-out exists.
printf '2468\n' | timeout 30 runuser -u kid -- pkexec /usr/bin/kidnix-set-pin --stdin >/dev/null 2>&1
pin_first_rc=$?
pin_hash_after_first=$(sed -n 's/^pin_hash *= *"\(.*\)"/\1/p' /etc/kidnix/parent.toml 2>/dev/null | head -1)

# 2. A SECOND ATTEMPT WITH NO CURRENT PIN, which is a child changing the PIN
#    that fences them in. Expected: refused (exit 4), file untouched.
printf '1357\n' | timeout 30 runuser -u kid -- pkexec /usr/bin/kidnix-set-pin --stdin >/dev/null 2>&1
pin_second_rc=$?
pin_hash_after_second=$(sed -n 's/^pin_hash *= *"\(.*\)"/\1/p' /etc/kidnix/parent.toml 2>/dev/null | head -1)

# 3. A wrong current PIN: refused too, and it costs two seconds.
pin_wrong_start=$(date +%s)
printf '1357\n9999\n' | timeout 30 runuser -u kid -- pkexec /usr/bin/kidnix-set-pin --stdin >/dev/null 2>&1
pin_wrong_rc=$?
pin_wrong_seconds=$(( $(date +%s) - pin_wrong_start ))

# 4. The current PIN, typed: allowed. (A parent standing at the gate.)
printf '1357\n2468\n' | timeout 30 runuser -u kid -- pkexec /usr/bin/kidnix-set-pin --stdin >/dev/null 2>&1
pin_proved_rc=$?
pin_hash_after_proved=$(sed -n 's/^pin_hash *= *"\(.*\)"/\1/p' /etc/kidnix/parent.toml 2>/dev/null | head -1)

# 5. The way back for a parent who forgot it needs wheel, so kid may not.
printf '4321\n' | timeout 30 runuser -u kid -- pkexec /usr/bin/kidnix-set-pin --stdin --reset >/dev/null 2>&1
pin_kid_reset_rc=$?
pin_hash_after_reset=$(sed -n 's/^pin_hash *= *"\(.*\)"/\1/p' /etc/kidnix/parent.toml 2>/dev/null | head -1)

# --- crash recovery ----------------------------------------------------------
# kidnix-shell.service is Restart=always/RestartSec=1, which replaced the bash
# supervisor. Kill the shell and time how long the child would stare at an
# empty compositor. Done last, because it perturbs the machine; `failed_units`
# below is therefore measured after it has settled.
shell_restart_pid=""
shell_restart_seconds=""
if [ -n "$shell_pid" ]; then
    kill -9 "$shell_pid" 2>/dev/null
    tries=0
    while [ "$tries" -lt 40 ]; do
        sleep 0.5
        tries=$(( tries + 1 ))
        candidate=$(shell_main_pid)
        if [ -n "$candidate" ] && [ "$candidate" != "0" ] && [ "$candidate" != "$shell_pid" ]; then
            shell_restart_pid="$candidate"
            shell_restart_seconds=$(awk "BEGIN{printf \"%.1f\", ${tries}/2}")
            break
        fi
    done
fi

# The unit passes through `deactivating` on its way back; wait for it to settle
# rather than photographing the restart mid-flight.
kid_shell_unit_after=""
tries=0
while [ "$tries" -lt 20 ]; do
    kid_shell_unit_after=$(uctl is-active kidnix-shell.service)
    [ "$kid_shell_unit_after" = "active" ] && break
    sleep 0.5
    tries=$(( tries + 1 ))
done

echo "KIDNIX_PROBE_BEGIN"
echo "system_running=$(systemctl is-system-running 2>/dev/null)"
echo "default_target=$(systemctl get-default 2>/dev/null)"
echo "gdm_enabled=$(systemctl is-enabled gdm 2>/dev/null)"
echo "gdm_active=$(systemctl is-active gdm 2>/dev/null)"
echo "kid_session=${kid_session}"
echo "kid_session_type=${kid_type}"
echo "kid_session_active=${kid_active}"
echo "kiosk_pid=${kiosk_pid}"
echo "kiosk_user=${kiosk_user}"
echo "kiosk_cmdline=$(tr '\0' ' ' < /proc/${kiosk_pid:-0}/cmdline 2>/dev/null)"
echo "kid_graphical_session=${kid_graphical_session}"
echo "kid_session_target=${kid_session_target}"
echo "kid_kiosk_target=${kid_kiosk_target}"
echo "kid_portal=${kid_portal}"
echo "kid_portal_gnome=${kid_portal_gnome}"
echo "kid_shell_unit=${kid_shell_unit}"
echo "kid_shell_unit_after=${kid_shell_unit_after}"
echo "shell_pid=${shell_pid}"
echo "shell_user=${shell_user}"
echo "session_leader=${session_leader}"
echo "kiosk_dconf=${kiosk_dconf}"
echo "shell_dconf=${shell_dconf}"
echo "shell_restart_pid=${shell_restart_pid}"
echo "shell_restart_seconds=${shell_restart_seconds}"
echo "nft_table=${nft_table}"
echo "egress_root=${egress_root}"
echo "egress_kid=${egress_kid}"
echo "egress_tcpdump=${egress_tcpdump}"
echo "egress_uplink=${egress_uplink}"
echo "egress_attempts=${egress_attempts}"
echo "egress_attempts_failed=${egress_attempts_failed}"
echo "egress_attempt_max=${egress_attempt_max}"
echo "egress_attempt_rcs=${egress_attempt_rcs}"
echo "egress_counter_before=${egress_counter_before}"
echo "egress_counter_after=${egress_counter_after}"
echo "egress_kid_packets=${egress_kid_packets}"
echo "egress_root_packets=${egress_root_packets}"
echo "egress_control_rc=${egress_control_rc}"
echo "egress_resolved_active=${egress_resolved_active}"
echo "egress_resolved_rc=${egress_resolved_real_rc}"
echo "egress_dns_packets=${egress_dns_packets}"
echo "egress_dns_label_hits=${egress_dns_label_hits}"
echo "egress_flatpak_app=${egress_flatpak_app}"
echo "egress_flatpak_rc=${egress_flatpak_rc}"
echo "egress_firewalld=${egress_firewalld}"
echo "egress_reload_table=${egress_reload_table}"
echo "egress_reload_kid=${egress_reload_kid}"
echo "egress_kid_flush_rc=${egress_kid_flush_rc}"
echo "egress_after_kid_flush=${egress_after_kid_flush}"
echo "egress_after_root_delete=${egress_after_root_delete}"
echo "egress_kid_unblocked=${egress_kid_unblocked}"
echo "egress_restored=${egress_restored}"
echo "egress_kid_reblocked=${egress_kid_reblocked}"
echo "pin_hash_at_boot=${pin_hash_at_boot}"
echo "pin_rules_setpin=${pin_rules_setpin}"
echo "pin_rules_tools=${pin_rules_tools}"
echo "pin_pkcheck_setpin=${pin_pkcheck_setpin}"
echo "pin_pkcheck_tools=${pin_pkcheck_tools}"
echo "pin_pkexec_check=${pin_pkexec_check}"
echo "pin_pkexec_wipe=${pin_pkexec_wipe}"
echo "pin_pkexec_tools=${pin_pkexec_tools}"
echo "pin_first_rc=${pin_first_rc}"
echo "pin_hash_after_first=${pin_hash_after_first}"
echo "pin_second_rc=${pin_second_rc}"
echo "pin_hash_after_second=${pin_hash_after_second}"
echo "pin_wrong_rc=${pin_wrong_rc}"
echo "pin_wrong_seconds=${pin_wrong_seconds}"
echo "pin_proved_rc=${pin_proved_rc}"
echo "pin_hash_after_proved=${pin_hash_after_proved}"
echo "pin_kid_reset_rc=${pin_kid_reset_rc}"
echo "pin_hash_after_reset=${pin_hash_after_reset}"
echo "failed_units=$(systemctl list-units --state=failed --no-legend --plain \
    --no-pager 2>/dev/null | awk '{print $1}' | paste -sd, -)"
echo "os_id=$(. /etc/os-release && echo "$ID")"
echo "os_version=$(. /etc/os-release && echo "$VERSION_ID")"
echo "kernel=$(uname -r)"
echo "hypervisor=$(systemd-detect-virt 2>/dev/null)"
echo "boot_time=$(systemd-analyze time 2>/dev/null | head -1)"
echo "graphical_target=$(systemd-analyze critical-chain graphical.target 2>/dev/null \
    | grep -o '@[0-9.]*m\?s' | head -1)"
echo "mem_used_mb=$(free -m | awk '/^Mem:/{print $3}')"
echo "mem_total_mb=$(free -m | awk '/^Mem:/{print $2}')"
echo "KIDNIX_PROBE_END"

echo "--- the egress ruleset as the kernel holds it ---"
nft list table inet kidnix_egress 2>&1
echo "--- packet capture: kid's window (${egress_kid_packets} packets, want 0) ---"
ls -l /tmp/kid.pcap 2>&1
tcpdump -r /tmp/kid.pcap -n 2>&1 | head -20
echo "--- packet capture: root's control window (${egress_root_packets} packets, want >0) ---"
tcpdump -r /tmp/root.pcap -n 2>&1 | head -10
echo "--- packet capture: kid's DNS via systemd-resolved (${egress_dns_packets} packets) ---"
tcpdump -r /tmp/kid-dns.pcap -n 2>&1 | head -10
echo "--- systemd-analyze blame (top 10) ---"
systemd-analyze blame --no-pager 2>/dev/null | head -10
echo "--- loginctl ---"
loginctl list-sessions --no-pager 2>/dev/null
echo "--- processes owned by kid ---"
ps -u kid -o pid,user,args --no-headers 2>/dev/null | head -30
echo "--- kid session units ---"
uctl list-units --state=failed --no-legend --plain 2>/dev/null
echo "--- the shell's own log ---"
journalctl -b _SYSTEMD_USER_UNIT=kidnix-shell.service --no-pager 2>/dev/null | tail -25
"""


class BootTestError(RuntimeError):
    """A failure to report cleanly rather than as a traceback."""


# --------------------------------------------------------------------------- #
# plumbing
# --------------------------------------------------------------------------- #


def find_bcvk() -> str:
    """bcvk from PATH, else the copy `just bcvk-install` drops in ~/.local/bin."""
    found = shutil.which("bcvk")
    if found:
        return found
    local = LOCAL_BIN / "bcvk"
    if local.is_file() and os.access(local, os.X_OK):
        return str(local)
    raise BootTestError(
        "bcvk not found on PATH or in ~/.local/bin.\nInstall it with: just bcvk-install"
    )


def kvm_available() -> bool:
    return os.path.exists("/dev/kvm") and os.access("/dev/kvm", os.R_OK | os.W_OK)


def clean(text: str) -> str:
    return ANSI.sub("", text)


def elide(text: str, max_line: int = 400, max_lines: int = 120) -> str:
    """Keep a diagnostic readable in a CI job log.

    A dump nobody scrolls through is worth nothing, and one base64 blob on a
    single line will hide everything above it.
    """
    lines = [
        ln if len(ln) <= max_line else ln[:max_line] + " ...[truncated]" for ln in text.splitlines()
    ]
    if len(lines) > max_lines:
        dropped = len(lines) - max_lines
        lines = [*lines[:max_lines], f"...[{dropped} more lines truncated]"]
    return "\n".join(lines)


def run(cmd: list[str], timeout: float, check: bool = False) -> subprocess.CompletedProcess:
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        stdin=subprocess.DEVNULL,
    )
    if check and proc.returncode != 0:
        raise BootTestError(
            f"command failed ({proc.returncode}): {' '.join(cmd)}\n{clean(proc.stderr).strip()}"
        )
    return proc


def parse_probe(text: str) -> dict[str, str]:
    """Pull the key=value block out of the guest probe's output."""
    body = clean(text)
    if PROBE_BEGIN not in body or PROBE_END not in body:
        raise BootTestError(
            "the guest probe did not produce a result block; the VM likely never "
            "became reachable.\n--- probe output ---\n" + body.strip()[-2000:]
        )
    block = body.split(PROBE_BEGIN, 1)[1].split(PROBE_END, 1)[0]
    values: dict[str, str] = {}
    for line in block.splitlines():
        if "=" in line:
            key, _, value = line.partition("=")
            values[key.strip()] = value.strip()
    return values


# --------------------------------------------------------------------------- #
# the VM
# --------------------------------------------------------------------------- #


class EphemeralVM:
    """A detached `bcvk ephemeral` VM, cleaned up on exit."""

    def __init__(self, bcvk: str, image: str, name: str, args: argparse.Namespace) -> None:
        self.bcvk = bcvk
        self.image = image
        self.name = name
        self.args = args
        self.started = False

    def __enter__(self) -> EphemeralVM:
        cmd = [
            self.bcvk,
            "ephemeral",
            "run",
            "--detach",
            # Deliberately NOT --rm. If the VM container dies -- which is what
            # a broken host looks like: bcvk's entrypoint fails before QEMU
            # ever starts, so there is no console.txt and no journal either --
            # then `podman logs` is the only record of why, and `--rm` throws
            # it away microseconds before we ask. We remove the container
            # ourselves in __exit__ instead.
            "--ssh-keygen",
            "--name",
            self.name,
            "--memory",
            self.args.memory,
            "--vcpus",
            str(self.args.cpus),
            # `journal` as well as `console`: the guest streams its journal out
            # over vsock as it boots, so journal.json exists even when sshd
            # never answers -- which is the only case where you actually need
            # it. console.txt alone stops at the SeaBIOS banner.
            "--log-dir",
            f"journal,console={self.args.output_dir}",
            self.image,
        ]
        print(f"==> {' '.join(cmd)}", flush=True)
        run(cmd, timeout=180, check=True)
        self.started = True
        return self

    def __exit__(self, *_exc) -> None:
        if not self.started or self.args.keep:
            if self.args.keep:
                print(
                    f"\n==> VM left running as '{self.name}'.\n"
                    f"    shell in:  bcvk ephemeral ssh {self.name}\n"
                    f"    remove:    podman rm -f {self.name}"
                )
            return
        subprocess.run(
            ["podman", "rm", "-f", self.name],
            capture_output=True,
            check=False,
            timeout=120,
        )

    def ssh(self, script: str, timeout: float) -> subprocess.CompletedProcess:
        return run(
            [self.bcvk, "ephemeral", "ssh", self.name, "--", script],
            timeout=timeout,
        )

    def wait_for_ssh(self, deadline: float) -> float:
        """Poll until sshd answers. Returns seconds waited.

        `bcvk ephemeral ssh` blocks until the guest answers rather than failing
        fast, so a "poll" here is really "block for a while, then come up for
        air". Coming up for air matters: it is the only place we notice the VM
        container died, and the only place we can print progress. What must NOT
        happen is a `subprocess.TimeoutExpired` escaping this loop -- that turns
        "the guest is still booting" into "the test crashed".
        """
        start = time.monotonic()
        last = "none"
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            if not self.is_running():
                raise BootTestError(
                    f"the VM container '{self.name}' exited before ssh came up "
                    f"({self.exit_state()}).\nThat is bcvk's entrypoint failing, not "
                    f"the guest: look at `podman logs` in "
                    f"{self.args.output_dir}/diagnostics.txt, not at console.txt."
                )
            try:
                proc = self.ssh("echo ready", timeout=min(remaining, SSH_POLL_SECONDS))
            except subprocess.TimeoutExpired:
                waited = time.monotonic() - start
                last = f"still no answer after {waited:.0f}s"
                print(
                    f"    ... still waiting for sshd ({waited:.0f}s of {self.args.timeout}s used)",
                    flush=True,
                )
                continue
            if proc.returncode == 0 and "ready" in clean(proc.stdout):
                return time.monotonic() - start
            lines = clean(proc.stderr).strip().splitlines()
            last = lines[-1] if lines else f"exit {proc.returncode} with no stderr"
            time.sleep(2)
        raise BootTestError(
            f"the VM never became reachable over ssh within {self.args.timeout}s. "
            f"Last error: {last}\n"
            f"See {self.args.output_dir}/console.txt and journal.json"
        )

    def is_running(self) -> bool:
        """True only while the container is actually running.

        Not `podman container exists`: that is true of a container that exited
        thirty seconds ago, which is precisely the case we need to catch.
        """
        proc = run(
            ["podman", "inspect", self.name, "--format", "{{.State.Running}}"],
            timeout=30,
        )
        return proc.returncode == 0 and clean(proc.stdout).strip() == "true"

    def exit_state(self) -> str:
        proc = run(
            [
                "podman",
                "inspect",
                self.name,
                "--format",
                "status={{.State.Status}} exit={{.State.ExitCode}} error={{.State.Error}}",
            ],
            timeout=30,
        )
        return clean(proc.stdout).strip() or "unknown (container is gone)"

    def diagnostics(self) -> str:
        """Everything worth knowing when the VM never answered.

        Written to output/diagnostics.txt *before* the container is removed --
        after `podman rm -f` there is nothing left to ask. `podman logs` is the
        one that matters: bcvk's entrypoint (virtiofsd, then QEMU) writes its
        failures there, and a QEMU that never started is invisible everywhere
        else, including in console.txt, which QEMU itself would have created.
        """
        probes: list[tuple[str, list[str]]] = [
            ("bcvk --version", [self.bcvk, "--version"]),
            ("bcvk ephemeral ps", [self.bcvk, "ephemeral", "ps"]),
            ("podman ps -a", ["podman", "ps", "-a"]),
            (
                f"podman logs {self.name} (last 200 lines)",
                ["podman", "logs", "--tail", "200", self.name],
            ),
            (
                f"podman inspect {self.name} (state)",
                [
                    "podman",
                    "inspect",
                    self.name,
                    "--format",
                    "status={{.State.Status}} exit={{.State.ExitCode}} "
                    "oom={{.State.OOMKilled}} error={{.State.Error}}",
                ],
            ),
            (
                "processes inside the VM container",
                ["podman", "exec", self.name, "ps", "-eo", "pid,etime,comm"],
            ),
            (
                # One argument per line, and drop -smbios: bcvk passes the ssh
                # key and three systemd units through it as base64, which is
                # kilobytes of noise that answers no question anyone has.
                "qemu command line inside the VM container (-smbios elided)",
                [
                    "podman",
                    "exec",
                    self.name,
                    "sh",
                    "-c",
                    "tr '\\0' '\\n' < /proc/$(pgrep -f qemu-system | head -1)/cmdline"
                    " | grep -v '^type=11'",
                ],
            ),
            (
                "ls -l /dev/kvm /dev/vhost-vsock (host)",
                ["ls", "-l", "/dev/kvm", "/dev/vhost-vsock"],
            ),
            (
                "ls -l /dev/kvm /dev/vhost-vsock (in the VM container)",
                ["podman", "exec", self.name, "ls", "-l", "/dev/kvm", "/dev/vhost-vsock"],
            ),
            ("id", ["id"]),
            (
                # bcvk's entrypoint unshares a user namespace (bwrap). Ubuntu
                # 24.04 forbids that for unconfined processes by default, which
                # kills the container before QEMU exists.
                "unprivileged user namespaces",
                [
                    "sh",
                    "-c",
                    "for f in /proc/sys/kernel/apparmor_restrict_unprivileged_userns "
                    "/proc/sys/user/max_user_namespaces "
                    "/proc/sys/kernel/unprivileged_userns_clone; do "
                    'printf "%s=" "$f"; cat "$f" 2>&1 || true; done',
                ],
            ),
            (
                "podman info (host)",
                [
                    "podman",
                    "info",
                    "--format",
                    "rootless={{.Host.Security.Rootless}} runtime={{.Host.OCIRuntime.Name}} "
                    "cgroups={{.Host.CgroupsVersion}}/{{.Host.CgroupManager}} "
                    "apparmor={{.Host.Security.AppArmorEnabled}} "
                    "selinux={{.Host.Security.SELinuxEnabled}} "
                    "net={{.Host.NetworkBackend}} cpus={{.Host.CPUs}} "
                    "kernel={{.Host.Kernel}}",
                ],
            ),
            ("free -m", ["free", "-m"]),
            ("df -h .", ["df", "-h", "."]),
        ]

        chunks = []
        for label, cmd in probes:
            try:
                proc = run(cmd, timeout=60)
                body = (clean(proc.stdout) + clean(proc.stderr)).strip() or "(no output)"
            except (OSError, subprocess.TimeoutExpired) as exc:
                body = f"(could not run: {exc})"
            chunks.append(f"$ {' '.join(cmd)}\n# {label}\n{elide(body)}\n")
        return ("\n" + "-" * 72 + "\n").join(chunks)

    def qemu_used_kvm(self) -> bool | None:
        """Read the QEMU command line inside the VM container. None = unknown."""
        proc = run(
            [
                "podman",
                "exec",
                self.name,
                "sh",
                "-c",
                "tr '\\0' '\\n' < /proc/$(pgrep -f qemu-system | head -1)/cmdline",
            ],
            timeout=60,
        )
        if proc.returncode != 0:
            return None
        return "-enable-kvm" in proc.stdout


# --------------------------------------------------------------------------- #
# assertions
# --------------------------------------------------------------------------- #


class Checks:
    def __init__(self) -> None:
        self.results: list[tuple[bool, str, str]] = []

    def check(self, ok: bool, name: str, detail: str = "") -> bool:
        self.results.append((ok, name, detail))
        return ok

    @property
    def failed(self) -> int:
        return sum(1 for ok, _, _ in self.results if not ok)

    @property
    def passed(self) -> int:
        return sum(1 for ok, _, _ in self.results if ok)

    def report(self) -> None:
        for ok, name, detail in self.results:
            mark = "\033[32mPASS\033[0m" if ok else "\033[31mFAIL\033[0m"
            print(f"  {mark}  {name}" + (f" -- {detail}" if detail else ""))


def assert_session(probe: dict[str, str], checks: Checks) -> None:
    """The gnome-session-shaped kid session, and the portals it finally allows.

    v0.1 exec'd gnome-kiosk directly, so `graphical-session.target` never
    activated and every `xdg-desktop-portal*` unit died on its
    `Requisite=graphical-session.target`. Routing the session through
    `gnome-session --session=kidnix` is the fix; these are the assertions that
    say so. See docs/spikes/session-integration.md.
    """
    for key, unit in (
        ("kid_graphical_session", "graphical-session.target"),
        ("kid_session_target", "gnome-session@kidnix.target"),
        ("kid_kiosk_target", "org.gnome.Kiosk.target"),
        ("kid_portal", "xdg-desktop-portal.service"),
        ("kid_portal_gnome", "xdg-desktop-portal-gnome.service"),
    ):
        state = probe.get(key, "")
        checks.check(state == "active", f"kid's {unit} is active (got '{state or 'unknown'}')")

    checks.check(
        bool(probe.get("session_leader")),
        "gnome-session is running the kidnix session",
        "" if probe.get("session_leader") else "no `gnome-session-service --session=kidnix`",
    )

    # The child's dconf profile has to reach processes the *user manager*
    # started, not merely children of /usr/bin/kidnix-shell. This is
    # docs/spikes/lockdown.md section 3 item 2, which could not be proven
    # anywhere but in a booted session.
    for key, who in (("kiosk_dconf", "gnome-kiosk"), ("shell_dconf", "the shell")):
        value = probe.get(key, "")
        checks.check(value == "kid", f"DCONF_PROFILE=kid reached {who} (got '{value or 'unset'}')")


def assert_shell(probe: dict[str, str], checks: Checks) -> None:
    """The activity shell is up, is kid's, and comes back when it is killed."""
    state = probe.get("kid_shell_unit", "")
    checks.check(state == "active", f"kidnix-shell.service is active (got '{state or 'unknown'}')")

    pid = probe.get("shell_pid", "")
    checks.check(bool(pid), "the activity shell is running", "" if pid else "no kidnix-shell-app")
    checks.check(
        probe.get("shell_user") == "kid",
        f"the activity shell runs as kid (got '{probe.get('shell_user') or 'nobody'}')",
    )

    # AGENTS.md non-negotiable 8, "crash-proof shell": SIGKILL the shell and
    # watch systemd put it back. This is what replaced the bash supervisor.
    restarted = probe.get("shell_restart_pid", "")
    seconds = probe.get("shell_restart_seconds", "")
    within = False
    try:
        within = bool(restarted) and float(seconds) <= SHELL_RESTART_BUDGET_SECONDS
    except ValueError:
        within = False
    checks.check(
        within,
        f"the shell comes back within {SHELL_RESTART_BUDGET_SECONDS}s of being killed"
        + (f" (took {seconds}s, pid {pid} -> {restarted})" if restarted else ""),
        "" if restarted else "it never came back",
    )

    after = probe.get("kid_shell_unit_after", "")
    checks.check(
        after == "active",
        f"kidnix-shell.service is active again after the kill (got '{after or 'unknown'}')",
    )


def assert_egress(probe: dict[str, str], checks: Checks) -> None:
    """AGENTS.md non-negotiable 5: the child session has no network egress.

    docs/spikes/lockdown.md section 3 item 3 called this "the single most
    important boot-test assertion to add" -- the image tests can only prove the
    ruleset *loads*, never that it drops a packet.
    """
    checks.check(
        probe.get("nft_table") == "loaded",
        f"nft table inet kidnix_egress is loaded (got '{probe.get('nft_table') or 'unknown'}')",
    )

    root_rc = probe.get("egress_root", "")
    kid_rc = probe.get("egress_kid", "")

    if root_rc != "0":
        # No route out of the VM at all: the differential is meaningless and a
        # "kid cannot reach the network" pass would be worthless. Say so.
        print(
            f"  \033[33mNOTE\033[0m  egress differential skipped -- root's own "
            f"`curl http://1.1.1.1` exited {root_rc or '?'}, so this VM has no "
            f"outbound network to be blocked from."
        )
        return

    checks.check(
        kid_rc not in ("", "0"),
        f"kid cannot reach the network (curl exited {kid_rc or '?'}; root got out fine)",
    )

    assert_egress_proof(probe, checks)


def _as_int(value: str) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_float(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def assert_egress_proof(probe: dict[str, str], checks: Checks) -> None:
    """The packet-capture half: *no packet left the machine*, not merely
    *no reply came back*.

    Audit item 9 ("prove the egress claim with a packet capture in the VM and
    make it a CI assertion") and research 03 section 3. The differential above
    is necessary and not sufficient: a curl fails for many reasons, and a
    parent is being told something much stronger than "the connection failed".
    See docs/spikes/egress-proof.md for the evidence this section produced.
    """
    checks.check(
        probe.get("egress_tcpdump", "absent") != "absent",
        f"tcpdump is in the image, so the capture is a real observation "
        f"({probe.get('egress_tcpdump') or 'absent'})",
    )

    attempts = _as_int(probe.get("egress_attempts", "")) or 0
    failed = _as_int(probe.get("egress_attempts_failed", "")) or 0
    checks.check(
        attempts >= EGRESS_MIN_ATTEMPTS and failed == attempts,
        f"every kid egress attempt failed ({failed}/{attempts}, want {EGRESS_MIN_ATTEMPTS}+)",
        probe.get("egress_attempt_rcs", ""),
    )

    # `reject` rather than `drop` exists precisely so a child's activity errors
    # out instead of hanging. If an attempt took anything like the 5 s curl
    # timeout, the packet went somewhere and we waited for a reply that never
    # came -- which is a different, worse lockdown.
    slowest = _as_float(probe.get("egress_attempt_max", ""))
    checks.check(
        slowest is not None and slowest < EGRESS_FAIL_FAST_SECONDS,
        f"every attempt failed fast, not on a timeout "
        f"(slowest {slowest if slowest is not None else '?'}s, "
        f"budget {EGRESS_FAIL_FAST_SECONDS}s)",
    )

    before = _as_int(probe.get("egress_counter_before", ""))
    after = _as_int(probe.get("egress_counter_after", ""))
    delta = after - before if before is not None and after is not None else None
    checks.check(
        delta is not None and delta >= EGRESS_MIN_COUNTER_DELTA,
        f"the nft uid-1000 counter caught the attempts "
        f"(+{delta if delta is not None else '?'} packets, "
        f"want +{EGRESS_MIN_COUNTER_DELTA}; {before} -> {after})",
    )

    kid_packets = _as_int(probe.get("egress_kid_packets", ""))
    root_packets = _as_int(probe.get("egress_root_packets", ""))

    # The observer has to be shown to work before its silence means anything.
    checks.check(
        probe.get("egress_control_rc") == "0" and (root_packets or 0) > 0,
        f"the capture filter does see traffic -- root's control curl put "
        f"{root_packets if root_packets is not None else '?'} packets on "
        f"{probe.get('egress_uplink') or '?'} (exit {probe.get('egress_control_rc') or '?'})",
    )
    checks.check(
        kid_packets == 0,
        f"NOT ONE PACKET from kid's {attempts} attempts reached "
        f"{probe.get('egress_uplink') or 'the uplink'} "
        f"(captured {kid_packets if kid_packets is not None else '?'})",
    )

    if probe.get("egress_firewalld") == "active":
        checks.check(
            probe.get("egress_reload_table") == "loaded"
            and probe.get("egress_reload_kid") not in ("", "0"),
            "the rule survives `firewall-cmd --reload` "
            f"(table {probe.get('egress_reload_table') or '?'}, "
            f"kid's curl exited {probe.get('egress_reload_kid') or '?'})",
        )
    else:
        print(
            f"  \033[33mNOTE\033[0m  firewalld is "
            f"'{probe.get('egress_firewalld') or 'unknown'}', so the "
            f"`firewall-cmd --reload` survival check did not run."
        )

    checks.check(
        probe.get("egress_kid_flush_rc") not in ("", "0")
        and probe.get("egress_after_kid_flush") == "loaded",
        "kid cannot flush the ruleset "
        f"(nft exited {probe.get('egress_kid_flush_rc') or '?'}, "
        f"table {probe.get('egress_after_kid_flush') or '?'} afterwards)",
    )

    # The control that makes the whole section falsifiable: with the table
    # deleted by root, kid MUST get straight out. If it does not, everything
    # above was measuring something other than our rule.
    checks.check(
        probe.get("egress_after_root_delete") == "absent"
        and probe.get("egress_kid_unblocked") == "0",
        "root deleting the table is what unblocks kid -- the nft rule is the "
        f"mechanism (table {probe.get('egress_after_root_delete') or '?'}, "
        f"kid's curl exited {probe.get('egress_kid_unblocked') or '?'})",
    )
    checks.check(
        probe.get("egress_restored") == "loaded"
        and probe.get("egress_kid_reblocked") not in ("", "0"),
        "reloading the shipped ruleset blocks kid again "
        f"(table {probe.get('egress_restored') or '?'}, "
        f"kid's curl exited {probe.get('egress_kid_reblocked') or '?'})",
    )

    # The gap this exercise found. See EGRESS_RESOLVED_DNS_STILL_ESCAPES.
    dns_packets = _as_int(probe.get("egress_dns_packets", ""))
    dns_rc = probe.get("egress_resolved_rc", "")
    # The packets are the evidence, not the exit code: whether the name resolves
    # depends on what is upstream of the VM, but the query leaving the machine
    # does not. On a network with no resolver the answer never comes back and
    # `getent` still exits non-zero -- and the label has still left.
    label_hits = _as_int(probe.get("egress_dns_label_hits", ""))
    # Kid's unique label on the uplink is the escape; unrelated port-53 traffic
    # in the same window (flatpak timer, resolved refreshes) is not.
    dns_escapes = (label_hits or 0) > 0
    if EGRESS_RESOLVED_DNS_STILL_ESCAPES:
        checks.check(
            dns_escapes,
            "KNOWN GAP, still open: kid's DNS escapes via systemd-resolved "
            f"({dns_packets if dns_packets is not None else '?'} port-53 packets left "
            f"{probe.get('egress_uplink') or 'the uplink'}; getent exited {dns_rc or '?'}). "
            "If this FAILS the gap was closed -- flip EGRESS_RESOLVED_DNS_STILL_ESCAPES",
        )
        print(
            "  \033[33mNOTE\033[0m  systemd-resolved (uid 990) sends that query on its "
            "own socket after\n"
            "        kid reaches it over loopback, which the ruleset accepts on purpose.\n"
            "        `meta skuid` cannot see through it. docs/spikes/egress-proof.md §4."
        )
    else:
        checks.check(
            not dns_escapes,
            "kid's DNS no longer escapes via systemd-resolved "
            f"({label_hits if label_hits is not None else '?'} packets carrying kid's label, "
            f"{dns_packets if dns_packets is not None else '?'} port-53 packets in the window, "
            f"getent exited {dns_rc or '?'})",
        )

    app = probe.get("egress_flatpak_app", "")
    if app:
        checks.check(
            probe.get("egress_flatpak_rc") not in ("", "0"),
            f"a Flatpak run by kid cannot reach the network ({app}, "
            f"exit {probe.get('egress_flatpak_rc') or '?'})",
        )
    else:
        print(
            "  \033[33mNOTE\033[0m  no Flatpak is installed in an ephemeral VM "
            "(they land on first boot of a real install), so the sandboxed-app "
            "attempt did not run. `--unshare=network` is asserted statically by "
            "tests/image/test_egress.sh."
        )


def assert_pin(probe: dict[str, str], checks: Checks) -> None:
    """The mandatory first PIN, set from the child's session and no further.

    docs/spikes/pin-flow.md is the argument; this is the proof, and it needs a
    booted machine because polkitd is the thing being asked. Two claims, and
    they pull in opposite directions on purpose:

      * the child's session CAN write the first PIN -- otherwise the shipped
        "no PIN at all" state is a gate that never closes, because the only
        session this machine shows is the child's;
      * and it can do nothing else with that authorisation -- not change a PIN
        somebody chose, not reset one, and not reach kidnix-wipe.
    """
    checks.check(
        probe.get("pin_hash_at_boot", "") == "",
        "the machine boots with NO grown-up PIN (the gate asks for one)",
        f"parent.toml already carries {probe.get('pin_hash_at_boot', '')[:8]}...",
    )
    checks.check(
        probe.get("pin_rules_setpin") == "YES",
        f"the rules file grants kid org.kidnix.set-pin (got '{probe.get('pin_rules_setpin') or 'nothing'}')",
    )
    checks.check(
        probe.get("pin_rules_tools") == "NO",
        f"the rules file still denies kid org.kidnix.parent-tools (got '{probe.get('pin_rules_tools') or 'nothing'}')",
    )

    # polkitd's own answer about a real process in kid's live session. Only
    # asserted when the probe could form the subject triple.
    if probe.get("pin_pkcheck_setpin"):
        checks.check(
            probe.get("pin_pkcheck_setpin") == "0",
            "polkitd authorises org.kidnix.set-pin for kid's session"
            f" (pkcheck exit {probe.get('pin_pkcheck_setpin')})",
        )
    if probe.get("pin_pkcheck_tools"):
        checks.check(
            probe.get("pin_pkcheck_tools") != "0",
            "polkitd refuses org.kidnix.parent-tools for kid's session"
            f" (pkcheck exit {probe.get('pin_pkcheck_tools')})",
        )

    checks.check(
        probe.get("pin_pkexec_check") == "0",
        f"kid may run `pkexec kidnix-set-pin --check` (exit {probe.get('pin_pkexec_check')})",
    )
    checks.check(
        probe.get("pin_pkexec_wipe") not in ("0", None),
        f"kid may NOT run `pkexec kidnix-wipe` (exit {probe.get('pin_pkexec_wipe')})",
    )
    checks.check(
        probe.get("pin_pkexec_tools") not in ("0", None),
        "kid may NOT reach kidnix-parent-tools through pkexec either"
        f" (exit {probe.get('pin_pkexec_tools')})",
    )

    first = probe.get("pin_hash_after_first", "")
    checks.check(
        probe.get("pin_first_rc") == "0" and len(first) == 64,
        "kid's session can set the FIRST PIN, and it lands in /etc"
        f" (exit {probe.get('pin_first_rc')}, hash {len(first)} chars)",
    )
    checks.check(
        probe.get("pin_second_rc") == "4",
        "a second set with no current PIN is refused"
        f" (exit {probe.get('pin_second_rc')}, wanted 4)",
    )
    checks.check(
        probe.get("pin_hash_after_second", "") == first,
        "...and the refused attempt changed nothing on disk",
    )
    checks.check(
        probe.get("pin_wrong_rc") == "3",
        f"a WRONG current PIN is refused (exit {probe.get('pin_wrong_rc')}, wanted 3)",
    )
    checks.check(
        _as_int(probe.get("pin_wrong_seconds", "")) is not None
        and _as_int(probe.get("pin_wrong_seconds", "")) >= 2,
        f"...and costs the guesser 2 s (took {probe.get('pin_wrong_seconds')}s)",
    )
    proved = probe.get("pin_hash_after_proved", "")
    checks.check(
        probe.get("pin_proved_rc") == "0" and len(proved) == 64 and proved != first,
        "typing the current PIN buys a change (a parent at the gate)"
        f" (exit {probe.get('pin_proved_rc')})",
    )
    checks.check(
        probe.get("pin_kid_reset_rc") not in ("0", None)
        and probe.get("pin_hash_after_reset", "") == proved,
        f"kid may not --reset past the current PIN (exit {probe.get('pin_kid_reset_rc')})",
    )


def assert_probe(probe: dict[str, str], checks: Checks) -> None:
    state = probe.get("system_running", "")
    checks.check(
        state in HEALTHY_SYSTEM_STATES,
        f"system state is running/degraded (got '{state or 'unknown'}')",
    )

    target = probe.get("default_target", "")
    checks.check(
        target == "graphical.target",
        f"default target is graphical.target (got '{target or 'unknown'}')",
    )

    checks.check(
        probe.get("gdm_enabled") == "enabled",
        f"gdm is enabled (got '{probe.get('gdm_enabled', 'unknown')}')",
    )
    checks.check(
        probe.get("gdm_active") == "active",
        f"gdm is active (got '{probe.get('gdm_active', 'unknown')}')",
    )

    session = probe.get("kid_session", "")
    checks.check(bool(session), "user 'kid' has a logind session", "" if session else "none found")
    checks.check(
        probe.get("kid_session_type") == "wayland",
        f"kid's session Type=wayland (got '{probe.get('kid_session_type') or 'none'}')",
    )
    checks.check(
        probe.get("kid_session_active") == "yes",
        f"kid's session is active (got '{probe.get('kid_session_active') or 'none'}')",
    )

    checks.check(bool(probe.get("kiosk_pid")), "gnome-kiosk is running")
    checks.check(
        probe.get("kiosk_user") == "kid",
        f"gnome-kiosk runs as kid (got '{probe.get('kiosk_user') or 'nobody'}')",
    )

    assert_session(probe, checks)
    assert_shell(probe, checks)
    assert_egress(probe, checks)
    assert_pin(probe, checks)

    failed = [u for u in probe.get("failed_units", "").split(",") if u]
    unexpected = [u for u in failed if u not in EXPECTED_FAILED_UNITS]
    checks.check(
        not unexpected,
        "no unexpected failed units",
        ", ".join(unexpected),
    )
    for unit in failed:
        if unit in EXPECTED_FAILED_UNITS:
            print(f"  \033[33mNOTE\033[0m  {unit} failed -- {EXPECTED_FAILED_UNITS[unit]}")


# --------------------------------------------------------------------------- #
# main flow
# --------------------------------------------------------------------------- #


def capture_journal(vm: EphemeralVM, output_dir: Path) -> Path | None:
    """Save warning-and-worse journal from this boot -- the first thing to read."""
    proc = vm.ssh("export SYSTEMD_COLORS=0; journalctl -b -p warning --no-pager 2>&1", timeout=120)
    if proc.returncode != 0 and not proc.stdout.strip():
        print(f"warning: could not capture the journal: {clean(proc.stderr).strip()}")
        return None
    path = output_dir / "boot-journal.txt"
    path.write_text(clean(proc.stdout))
    return path


def capture_pcaps(vm: EphemeralVM, output_dir: Path) -> list[Path]:
    """Copy the egress proof's packet captures out before the VM is destroyed.

    The captures ARE the evidence for the one claim a parent is given in plain
    words, so they leave the machine as files rather than being reduced to a
    PASS line and thrown away with the VM. base64 over ssh because these are
    binary and small (hundreds of bytes to a few KB).
    """
    saved: list[Path] = []
    target = output_dir / "pcap"
    for name in ("kid.pcap", "root.pcap", "kid-dns.pcap"):
        proc = vm.ssh(f"base64 -w0 /tmp/{name} 2>/dev/null", timeout=60)
        blob = clean(proc.stdout).strip()
        if proc.returncode != 0 or not blob:
            continue
        try:
            data = base64.b64decode(blob, validate=True)
        except (ValueError, binascii.Error):
            continue
        target.mkdir(parents=True, exist_ok=True)
        path = target / name
        path.write_bytes(data)
        saved.append(path)
    return saved


def render_journal_stream(output_dir: Path) -> Path | None:
    """Turn bcvk's journal.json stream into something a human reads in CI.

    `--log-dir journal=...` writes one JSON object per journal entry, streamed
    out of the guest as it boots. That is the only record of a boot that never
    reached sshd, and nobody is going to read 1.7 MB of JSON in an artifact
    viewer, so flatten it to `boot-journal-stream.txt`.
    """
    entries = []
    for name in ("journal-initrd.json", "journal.json"):
        source = output_dir / name
        if not source.is_file():
            continue
        entries.append(f"===== {name} =====")
        for line in source.read_text(errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except ValueError:
                entries.append(line[:500])
                continue
            message = record.get("MESSAGE")
            if isinstance(message, list):  # binary payloads arrive as byte arrays
                message = bytes(message).decode("utf-8", "replace")
            who = record.get("SYSLOG_IDENTIFIER") or record.get("_COMM") or "?"
            entries.append(f"{who}: {message}")

    if not entries:
        return None
    path = output_dir / "boot-journal-stream.txt"
    path.write_text("\n".join(entries) + "\n")
    return path


def print_tail(path: Path, lines: int, why: str) -> None:
    """Print the end of a log file to the job log, so failures are readable
    without downloading an artifact."""
    if not path.is_file():
        print(f"\n--- {path} does not exist ({why}) ---", file=sys.stderr)
        return
    body = path.read_text(errors="replace").splitlines()
    print(f"\n--- last {min(lines, len(body))} lines of {path} ({why}) ---", file=sys.stderr)
    print("\n".join(body[-lines:]), file=sys.stderr)


def dump_failure_artifacts(vm: EphemeralVM, output_dir: Path) -> None:
    """Called while the VM is still alive; everything here dies with it."""
    path = output_dir / "diagnostics.txt"
    try:
        path.write_text(vm.diagnostics())
        print(f"\n==> wrote {path}", file=sys.stderr)
    except OSError as exc:  # pragma: no cover - best effort by definition
        print(f"warning: could not write {path}: {exc}", file=sys.stderr)

    stream = render_journal_stream(output_dir)
    print_tail(output_dir / "console.txt", 100, "serial console")
    if stream:
        print_tail(stream, 100, "guest journal, streamed live over vsock")
    else:
        print(
            "\n--- no journal.json: the guest never streamed a journal, so it "
            "probably never booted ---",
            file=sys.stderr,
        )
    print_tail(path, 120, "host-side diagnostics")


def note_no_screenshot() -> None:
    """Say plainly why there is no screenshot, so nobody re-investigates."""
    print(
        "\n  \033[33mSKIP\033[0m  screenshot -- `bcvk ephemeral` runs QEMU with\n"
        "        `-nographic -display none -monitor none`, so there is no QMP\n"
        "        socket and no VNC to screendump. gnome-kiosk does export\n"
        "        org.gnome.Shell.Screenshot, but it answers 'Access denied' even\n"
        "        to a caller running as `kid` inside kid's own session cgroup.\n"
        "        For pixels use:  just test-boot-qcow2   (QMP screendump)\n"
        "                     or:  just vm-graphical      (SPICE + virsh screenshot)"
    )


def run_boot_test(args: argparse.Namespace) -> int:
    bcvk = find_bcvk()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    proc = run(["podman", "image", "exists", args.image], timeout=60)
    if proc.returncode != 0:
        raise BootTestError(f"image not found: {args.image}\nRun: just build")

    if not kvm_available():
        print(
            "warning: /dev/kvm is not usable -- bcvk will fall back to software\n"
            "         emulation, which will not boot a GNOME stack inside the timeout.",
            file=sys.stderr,
        )

    name = args.name or f"kidnix-boot-{os.getpid()}"
    deadline = time.monotonic() + args.timeout
    checks = Checks()
    started = time.monotonic()

    with EphemeralVM(bcvk, args.image, name, args) as vm:
        # Any failure from here to the end of the block is a failure we cannot
        # investigate after the fact: `--rm` takes the container, and with it
        # `podman logs`, the QEMU process and the guest, on the way out.
        try:
            waited = vm.wait_for_ssh(deadline)
            print(f"==> ssh reachable after {waited:.1f}s")

            used_kvm = vm.qemu_used_kvm()

            # The probe has its own waits inside the guest (up to ~90 s for the
            # shell unit, ~60 s for the session, then the kill/restart), so it
            # gets a floor rather than whatever scraps of --timeout a slow boot
            # left behind. Cutting the probe off mid-flight reports "no result
            # block" -- a sentence that tells you nothing about the machine.
            remaining = max(300.0, deadline - time.monotonic())
            result = vm.ssh(GUEST_PROBE, timeout=remaining)
            if args.verbose:
                print(clean(result.stdout))

            probe = parse_probe(result.stdout)
            journal = capture_journal(vm, output_dir)
            pcaps = capture_pcaps(vm, output_dir)
        except (BootTestError, subprocess.TimeoutExpired):
            dump_failure_artifacts(vm, output_dir)
            raise

    elapsed = time.monotonic() - started
    stream = render_journal_stream(output_dir)

    print("\n" + "=" * 72)
    print(f"image      : {args.image}")
    print(
        f"os         : {probe.get('os_id', '?')} {probe.get('os_version', '?')} "
        f"kernel {probe.get('kernel', '?')}"
    )
    print(
        f"virt       : {probe.get('hypervisor', '?')}, "
        f"KVM used: {'yes' if used_kvm else 'no' if used_kvm is False else 'unknown'}"
    )
    print(f"boot       : {probe.get('boot_time', '?')}")
    if probe.get("graphical_target"):
        print(f"graphical  : reached at {probe['graphical_target'].lstrip('@')}")
    print(
        f"memory     : {probe.get('mem_used_mb', '?')} MiB used of "
        f"{probe.get('mem_total_mb', '?')} MiB"
    )
    print(f"kiosk      : {probe.get('kiosk_cmdline') or 'not running'}")
    print(f"shell      : pid {probe.get('shell_pid') or '-'} as {probe.get('shell_user') or '-'}")
    print(
        f"kid session: graphical-session={probe.get('kid_graphical_session', '?')} "
        f"portal={probe.get('kid_portal', '?')} shell={probe.get('kid_shell_unit', '?')}"
    )
    print(f"console log: {output_dir / 'console.txt'}")
    if journal:
        print(f"journal    : {journal}")
    if stream:
        print(f"boot stream: {stream}")
    if pcaps:
        print(f"pcaps      : {', '.join(str(p) for p in pcaps)}")
    print(f"wall clock : {elapsed:.1f}s")
    print("=" * 72)

    assert_probe(probe, checks)
    checks.report()
    note_no_screenshot()

    print()
    if checks.failed == 0:
        print(f"\033[32mPASS\033[0m  {checks.passed} checks, kidnix booted into the kiosk.")
        return 0

    print(
        f"\033[31mFAIL\033[0m  {checks.failed} of {checks.passed + checks.failed} checks failed.",
        file=sys.stderr,
    )
    if journal:
        print(f"\nFirst 30 lines of {journal}:", file=sys.stderr)
        print("\n".join(journal.read_text().splitlines()[:30]), file=sys.stderr)
    return 1


def dry_run(args: argparse.Namespace) -> int:
    """Everything we can validate without booting anything."""
    print("==> dry run (no VM is booted)")
    ok = True

    try:
        print(f"  PASS  bcvk: {find_bcvk()}")
    except BootTestError as exc:
        print(f"  FAIL  {exc}")
        ok = False

    if shutil.which("podman"):
        print("  PASS  podman on PATH")
    else:
        print("  FAIL  podman not found")
        ok = False

    print(f"  {'PASS' if kvm_available() else 'WARN'}  /dev/kvm usable: {kvm_available()}")

    if run(["podman", "image", "exists", args.image], timeout=60).returncode == 0:
        print(f"  PASS  image present: {args.image}")
    else:
        print(f"  WARN  image not built yet: {args.image} (run 'just build')")

    try:
        sample = (
            f"noise\n{PROBE_BEGIN}\nsystem_running=running\nkid_session_type=wayland\n"
            f"{PROBE_END}\ntail"
        )
        parsed = parse_probe(sample)
        assert parsed["system_running"] == "running"
        assert parsed["kid_session_type"] == "wayland"
        print(f"  PASS  probe parser ({len(parsed)} keys from a synthetic block)")
    except (BootTestError, AssertionError, KeyError) as exc:
        print(f"  FAIL  probe parser: {exc}")
        ok = False

    print("\n" + ("dry run OK" if ok else "dry run FAILED"))
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--image", default="localhost/kidnix:latest", help="image to boot")
    parser.add_argument("--output-dir", default="output", help="where logs are written")
    parser.add_argument("--timeout", type=int, default=360, help="overall seconds budget")
    parser.add_argument("--memory", default="4G", help="VM RAM (bcvk syntax, e.g. 4G)")
    parser.add_argument("--cpus", type=int, default=4, help="VM vCPUs")
    parser.add_argument("--name", default="", help="container name for the VM")
    parser.add_argument("--keep", action="store_true", help="leave the VM running afterwards")
    parser.add_argument("--verbose", action="store_true", help="print the raw guest probe")
    parser.add_argument("--dry-run", action="store_true", help="validate plumbing, boot nothing")
    args = parser.parse_args()

    try:
        return dry_run(args) if args.dry_run else run_boot_test(args)
    except BootTestError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except subprocess.TimeoutExpired as exc:
        print(f"error: timed out running {exc.cmd}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
