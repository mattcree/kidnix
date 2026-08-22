# Spike: proving the egress claim with a packet capture

**Status:** done, green, and it found something.

`docs/design/cci-compliance-audit-2026-08-22.md` top-ten item 9 asked for this
in one sentence: *"Prove the egress claim with a packet capture in the VM and
make it a CI assertion. We are about to put this machine in front of a child and
tell a parent it holds."* `docs/spikes/lockdown.md` §3 item 3 had the same thing
as "the single most important boot-test assertion to add", and the audit's §3.2
listed "no CI gate on egress, licences, or dependencies" as a deviation that
happened *by accident*.

This is the record of what was measured, on a real booted kidnix, on
2026-08-22. Every block below is pasted from the run, not reconstructed.

**The headline: six of the seven claims hold, exactly as designed, and one does
not.** DNS escapes. See §4 — it is the most important paragraph in this file.

---

## 1. What is now proven, and how

The proof lives in `tests/boot/bcvk_boot_test.py` (guest probe + twelve
assertions) and runs on every `just test-boot`, i.e. on every push and PR
through `.github/workflows/boot-test.yml`.

The shape of it matters more than the count. A differential ("kid's curl fails,
root's succeeds") is *not* a proof of the sentence we tell parents. A curl fails
for a dozen reasons, and "no reply came back" is a much weaker claim than "no
packet left the machine". So the probe puts an observer on the wire and runs
three windows through it, all with the same interface and the same capture
filter:

| window | who | what is run | expected |
|---|---|---|---|
| A | `kid` (uid 1000) | seven egress attempts by seven mechanisms | **zero packets** |
| B | `root` | one `curl http://1.1.1.1/` | **packets** — proves the observer works |
| C | `kid` | one `getent hosts <unique-name>` | see §4 |

Window B is the one that makes window A mean anything. Without it, "tcpdump saw
nothing" is indistinguishable from "tcpdump was misconfigured" — and that is not
hypothetical, see §5.

### The seven attempts

Each is a different way to get a packet out, chosen so that no single mechanism
in the image is doing all the work:

| # | attempt | why this one |
|---|---|---|
| 1 | `curl http://1.1.1.1/` | TCP by IP; no DNS involved, so a failure is the filter and nothing else |
| 2 | `curl https://example.com/` | the whole stack: resolver, TCP, TLS |
| 3 | `python3` raw UDP `sendto 8.8.8.8:53` | bypasses libc's resolver entirely (`nc` is not in the image) |
| 4 | `ping -c1 1.1.1.1` | ICMP. Fedora 44's `ping` is a datagram socket via `ping_group_range` — not setuid, no `cap_net_raw` — so `skuid` still sees uid 1000 |
| 5 | `curl -6 http://[2606:4700:4700::1111]/` | IPv6; a v4-shaped lockdown is the classic hole. The table is `inet`, which is what this checks |
| 6 | `python3` raw `connect()` to `203.0.113.9:80` | nothing curl-specific is doing the work |
| 7 | `systemd-run --uid=1000 -- curl http://9.9.9.9/` | spawned by PID 1, not forked from the root probe shell |

Flatpak is the eighth mechanism and is **not** exercised in the VM: no Flatpak is
installed in a `bcvk ephemeral` boot (they land on first boot of a real install).
`--unshare=network` is asserted statically instead, by
`tests/image/test_egress.sh`. The boot test prints a NOTE saying so rather than
quietly passing.

---

## 2. The evidence

Pasted from `just test-boot --verbose`, 2026-08-22. The captures themselves are
written to `output/pcap/{kid,root,kid-dns}.pcap` and uploaded as CI artifacts,
so the raw evidence outlives the job log.

**The ruleset, as the kernel actually holds it:**

```
table inet kidnix_egress {
	chain output {
		type filter hook output priority filter; policy accept;
		oif "lo" accept
		meta skuid 1000 counter packets 1 bytes 60 reject with icmpx admin-prohibited
	}
}
```

**Window A — kid's seven attempts:**

```
egress_attempt_rcs=http-v4:rc=7/0.09s https-name:rc=7/1.59s udp-53:rc=1/0.08s
                   icmp:rc=1/1.10s http-v6:rc=7/1.13s tcp-connect:rc=1/0.06s
                   systemd-run:rc=7/0.10s
egress_counter_before=1   egress_counter_after=14      (+13 packets rejected)
egress_kid_packets=0

--- packet capture: kid's window (0 packets, want 0) ---
-rw-r--r-- 1 tcpdump tcpdump 24 Aug 22 13:41 /tmp/kid.pcap
reading from file /tmp/kid.pcap, link-type EN10MB (Ethernet), snapshot length 128
```

24 bytes is a pcap file header and nothing else. Seven attempts, thirteen
packets counted by the rule, **zero bytes on the wire**.

**Window B — the same observer, root instead of kid:**

```
--- packet capture: root's control window (11 packets, want >0) ---
13:41:17.207760 IP 10.0.2.15.56748 > 1.1.1.1.http: Flags [S], seq 1281357574, ...
13:41:17.224598 IP 1.1.1.1.http > 10.0.2.15.56748: Flags [S.], seq 4416001, ...
13:41:17.224729 IP 10.0.2.15.56748 > 1.1.1.1.http: Flags [P.], ... HTTP: GET / HTTP/1.1
13:41:17.243741 IP 1.1.1.1.http > 10.0.2.15.56748: Flags [P.], ... HTTP/1.1 301 Moved Permanently
```

**The mechanism checks:**

```
egress_firewalld=active        egress_reload_table=loaded   egress_reload_kid=7
egress_kid_flush_rc=1          egress_after_kid_flush=loaded
egress_after_root_delete=absent  egress_kid_unblocked=0
egress_restored=loaded           egress_kid_reblocked=7
```

Read that middle-to-bottom, because it is the part that makes the whole section
falsifiable:

- `firewall-cmd --reload` runs and the table is still loaded, and kid is still
  blocked (exit 7). The reasoning in `lockdown.md` §1.1 — firewalld's nftables
  backend only ever names its own tables — is now a measurement.
- kid's `nft flush ruleset` exits 1 and the table is still there.
- **root deletes the table and kid's curl immediately exits 0.** This is the
  control for everything above it. If kid still could not reach the network with
  the rule gone, every other PASS in this section would be measuring something
  other than our rule.
- reloading the shipped `.nft` file blocks kid again (exit 7), so the machine is
  left as it was found.

**The final tally:**

```
PASS  36 checks, kidnix booted into the kiosk.
```

Twelve of those thirty-six are the egress proof.

---

## 3. What the image lacks, and what it turned out to have

- **`tcpdump` is in the image** (`tcpdump-4.99.6-3.fc44.x86_64`), so the
  observer is a real observation and no package had to be added. It requires
  root, and `kid` cannot become root — `tests/image/test_egress.sh` asserts both
  halves of that.
- **`nc` / `ncat` / `netcat` are NOT in the image.** The raw UDP and raw TCP
  attempts use `python3`'s socket module instead — the same syscalls, and no
  extra package in a child's OS. Nothing was added to the image for this spike,
  deliberately.
- **`conntrack` is not in the image either.** Not needed: the nft counter is the
  in-kernel observer and the pcap is the on-the-wire one.

---

## 4. The gap this found: DNS escapes via systemd-resolved

**`getent hosts <anything>` as `kid` succeeds, and the query leaves the machine.**

Window C proves it rather than arguing about it. Capture port 53 on the uplink
while kid resolves a name that cannot be in any cache:

```
--- packet capture: kid's DNS via systemd-resolved (4 packets) ---
13:41:21.143712 IP 10.0.2.15.42537 > 10.0.2.3.domain: 17519+ [1au] AAAA? kidnix-egress-probe-1973.example.com. (65)
13:41:21.166086 IP 10.0.2.3.domain > 10.0.2.15.42537: 17519 0/1/1 (127)
13:41:21.167427 IP 10.0.2.15.51136 > 10.0.2.3.domain: 28595+ [1au] A? kidnix-egress-probe-1973.example.com. (65)
13:41:21.189894 IP 10.0.2.3.domain > 10.0.2.15.51136: 28595 0/1/1 (127)
```

A label chosen by a process running as the child is on the wire, leaving the
machine, and an answer is coming back.

**Nothing is broken.** The rule is doing exactly what it says. The path simply
does not go through a socket kid owns:

```
kid  ->  nss-resolve  ->  varlink/D-Bus over LOOPBACK, which the ruleset
                          accepts on purpose (oif "lo" accept)
                      ->  systemd-resolved, running as uid 990
                      ->  the nameserver
```

`meta skuid` matches the *socket owner*, and the socket that carries the packet
off the machine belongs to `systemd-resolved`, not to uid 1000. The same is true
of `dig`, which talks to the stub listener on `127.0.0.53` — also loopback, also
accepted.

**Why it matters.** "The child session has no network egress by default"
(AGENTS.md non-negotiable #5) is true of every direct socket and false of DNS.
It is a low-bandwidth **two-way** channel: arbitrary labels go out in the
question, addresses come back in the answer. Against the actual threat model —
a five-year-old, and second-order, an activity with a bug — it is a small risk.
Against the sentence we print for a parent, it is a caveat that must be either
closed or written down. It is now written down, and this is the third place it
appears (here, `AGENTS.md`'s claim, and the test itself).

**The fix is one line**, in `system_files/usr/lib/kidnix/nftables/kidnix-egress.nft`,
*before* the loopback accept:

```nft
meta skuid 1000 udp dport 53 counter reject with icmpx type admin-prohibited
meta skuid 1000 tcp dport 53 counter reject with tcp reset
```

kid's packet to `127.0.0.53:53` **is** owned by uid 1000, so the rule sees it.
That closes the channel at the point where the child's own socket exists, which
is the only place `skuid` can act. Cost: `getent`/`dig` stop working for the
child. Since the child session is meant to be offline and the shell offers no
affordance that resolves a name, that cost looks like zero — but it is a
behaviour change to a shipped file, so it is a decision for the thinker, not
something a test author should slip in.

**Until then the test asserts the gap is still open**, via
`EGRESS_RESOLVED_DNS_STILL_ESCAPES = True` in `tests/boot/bcvk_boot_test.py`.
When the ruleset gains those lines, that assertion goes RED and points at the
constant — so the fix and the test flip in one commit, and nobody has to
remember.

*(Options considered and rejected: masking `systemd-resolved` breaks the
parent's session; `DNSStubListener=no` only moves the socket; denying kid the
varlink socket by file mode is not enforceable while `nss-resolve` is in
`nsswitch.conf`. The nft rule is the only one that acts where the uid is
visible.)*

---

## 5. The instrument lied first, and that is the lesson

The first green-looking run of this test reported **"NOT ONE PACKET from kid's
attempts reached enp0s4 (captured 0)"** — and it was worthless, because the
control window also captured 0 while root's curl demonstrably succeeded.

`tcpdump` was reporting `0 packets captured, 9 packets received by filter`: the
packets were sitting in the kernel ring buffer when `SIGINT` arrived, and
tcpdump exited without draining it. Two changes fixed it, and both are in
`start_capture`/`stop_capture` with a comment saying why:

- `-U` (packet-buffered writes)
- a 2 s drain before the kill

**The point:** a capture that silently under-reports is the worst possible
instrument for exactly this claim, because its failure mode is a PASS. The only
reason it was caught is that the control window is a required assertion rather
than a diagnostic. Any future test of the form "we looked and saw nothing" needs
the same companion — *and we looked the same way and saw something*.

---

## 6. The static half, and the other two gates

The audit named three missing CI gates. All three now exist.

**`tests/image/test_egress.sh` — 33 assertions, rootless, ~2 s.** Runs in
`just test-image` on every build. It proves the lockdown is installed and
internally consistent, and it is where the `skuid` known-gap reasoning is kept
honest:

- the ruleset parses (`unshare -rn nft -c -f`) — *and the parse check is itself
  checked*, by feeding it a ruleset naming a nonexistent user and requiring a
  rejection;
- the rule rejects uid 1000 with `icmpx admin-prohibited` (fail fast, not
  `drop`), carries a counter, and loopback is accepted **before** it (line
  order, not mere presence);
- the table is `inet`, so IPv6 is filtered;
- sysusers still pins `kid` to 1000, which is what the numeric rule filters;
- the unit is `DefaultDependencies=no`, `Before=network-pre.target`, and enabled
  in both `multi-user` and `graphical`; greenboot re-asserts it every boot;
- the Flatpak global override unshares the network and tmpfiles seeds it;
- polkit denies kid five NetworkManager/FirewallD actions and leaves the parent
  alone;
- **the setuid section**, which is where `lockdown.md`'s "known gap" is kept
  theoretical: 19 setuid-root binaries in `/usr`, none of them network-capable
  (30 names checked); `ping` is neither setuid nor `cap_net_raw`; and nothing is
  both setuid-root *and* `cap_net_raw`, which is the one combination `skuid`
  cannot see through. `arping`, `clockdiff` and `mtr-packet` carry `cap_net_raw`
  and that is fine — a file capability does not change the euid, so a raw socket
  opened by one of them for kid is still owned by uid 1000 and still hits the
  rule;
- kid has no sudoers entry, no supplementary groups, no `pkexec`, and sshd
  denies kid outright.

**`tests/image/test_licenses.sh` + `just licenses` — 18 assertions.** The image
now ships `/usr/share/kidnix/THIRD-PARTY.tsv`, one row (path, licence, source,
origin) per file that did **not** arrive inside an RPM. The gate cross-checks it
three ways: every row has a file, every file in the vendored trees has a row,
and every row is accounted for in `docs/LICENSES.md`. It also screens all 445
distinct `%{LICENSE}` strings across 1,615 packages against a
NonCommercial/proprietary denylist, with one reviewed exception (Fedora's
`LicenseRef-Callaway-Redistributable-no-modification-permitted` firmware tag) —
and asserts the exception still matches a real package, so a stale allow-list
entry cannot sit there waving things through.

Writing it found two real ledger gaps: **the kidnix wallpaper and the shell's
icon/earcon assets were shipped and not recorded at all.** Both are ours and
Apache-2.0, so nothing was wrong — but "we ship it and the ledger does not know"
is precisely the drift `docs/LICENSES.md` open question #4 predicted, arriving
within a fortnight of the file being written.

**`just packages-check` + `tests/image/packages.lock`.** 1,615 packages,
committed. A *removed* package fails the build (something the image depended on
has gone and the lock is the only record it was ever there); ordinary additions
and version bumps pass but are printed; anything matching
`tests/image/packages.deny` fails outright. The denylist is a policy statement
with a reason per group: web browsers (ADR-0005 makes "no browser" a property of
the machine — `base-main` ships Firefox and `70-hardening.sh` removes it, and
this is what notices if it comes back as somebody's weak dependency), remote
access, chat clients, torrent clients, and network reconnaissance tools.
`openssh-server` and `tcpdump` are deliberately **not** on it, with the reason
written next to them. Update with `just packages-lock`, read the diff, commit it
with the change that caused it.

---

## 7. What is still NOT proven

Honesty section, in the style of `lockdown.md` §3.

1. **The Flatpak sandbox's network isolation, at runtime.** Asserted statically
   only. Needs a `just test-boot-qcow2` run against a real install where the
   first-boot Flatpaks exist.
2. **A physical NIC.** Everything here is a virtio-net uplink under slirp. The
   filter is a kernel `output` hook and is device-independent by construction,
   but that is reasoning, not evidence.
3. **Wi-Fi association.** kid is denied NetworkManager by polkit and the boot
   test does not try to join a network, because a `bcvk ephemeral` VM has no
   radio.
4. **A parent who deliberately re-shares a Flatpak's network.** Documented as a
   supported action (`flatpak override --share=network`); nothing tests what a
   child can then do inside that app. The nft rule still holds, which is the
   point of having it underneath.
5. **Anything about a compromised root.** Out of scope. `nft flush` as root
   removes the table, as §2 shows — that is the design, not a finding.

## Addendum (thinker, same day): the DNS gap is closed

Two changes, both verified in the VM by the boot test (`0 port-53 packets`,
`getent` exits 2, kid counters +11 across the three uid rules):

1. `kidnix-egress.nft`: `meta skuid 1000 udp dport 53` and `tcp dport 53`
   rejects placed **before** the loopback accept, so a kid query to the
   127.0.0.53 stub is refused at the source.
2. glibc's `nss-resolve` reaches systemd-resolved over varlink, not port 53,
   so it had to go: `build_files/40-lockdown.sh` now selects an authselect
   **custom profile** (`custom/kidnix`, based on `local`, hosts line without
   `resolve [!UNAVAIL=return]`). Editing the generated `nsswitch.conf` was not
   enough — `authselect-apply-changes.service` re-renders it on every boot.
   Lookups now go `files → myhostname → mdns4_minimal → dns`, i.e. UDP/53 to
   the stub as the calling uid, where the table decides. Parent is unaffected
   (resolved still answers on the stub). Residual: `mdns4_minimal` can
   resolve `.local` names via avahi (LAN multicast only) — accepted, noted.
