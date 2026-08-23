# Review: children's online safety and privacy-by-design

**Reviewer:** external safety/privacy specialist (ICO Children's Code, 5Rights,
eSafety background). **Date:** 2026-08-23. **Scope:** the review packet named in
the brief, read against `docs/research/03` §3's 41-item checklist. Read-only;
this file is the only thing I wrote.

---

## 1. Verdict

**Conditionally excellent.** The *enforcement* is better than almost anything I
review commercially: the "no egress" claim is not a policy sentence, it is a
kernel filter with a packet capture and a control window behind it, and the team
went looking for the hole (DNS via `systemd-resolved`) rather than waiting to be
told. Non-negotiables 1, 3, 5 and 6 are visible in the code, not just the
constitution. There is no telemetry, no profiling, no account, no browser, no
generative AI, no covert capture, and no engagement machinery anywhere — I
grepped for it and it genuinely is not there.

The gaps are all on the **rights** side rather than the security side, and they
cluster in one place: **the child's data has no exit.** Nothing can be deleted,
nothing can be exported, nothing has a retention rule, siblings share one store,
and the child is never told any of it. For Matt's own household that is a
correctable omission. For the second family it is the difference between a
privacy-by-design product and a well-defended archive of a child that nobody can
empty.

Verdict for the current posture (one household, the author's own child): **ship
it, keep testing.** Verdict for distribution to any other family: **not yet —
see §4.**

---

## 2. Five strengths

1. **The egress proof is exemplary, including the part where it failed.**
   `docs/spikes/egress-proof.md` §5 — the instrument under-reported and was
   caught only because the root control window was a required assertion, not a
   diagnostic — is the single best paragraph in this repository. Checklist item
   #1 asks for a 30-minute capture; you have seven mechanisms, IPv6, a
   `systemd-run` path that bypasses the probe shell, an in-kernel counter *and*
   an on-the-wire observer, and a differential that proves the rule is what is
   doing the work. Very few products I assess can demonstrate their headline
   privacy claim at all.

2. **The DNS finding was published before it was fixed.** A low-bandwidth
   two-way channel that nobody would ever have noticed was written up, given a
   test constant (`EGRESS_RESOLVED_DNS_STILL_ESCAPES`) that goes red when the
   fix lands, and then closed with the `authselect custom/kidnix` profile so the
   lookup happens as the child's own uid where `skuid` can see it. Checklist
   item #9 of §4 ("do not claim compliance you have not tested") is being lived.

3. **Nothing on this machine phones home, and someone checked each one by
   name.** `rpm-ostree-countme.timer` masked with the reasoning written out —
   *"it is deliberately privacy-preserving, and it is still an unrequested
   outbound connection from a five-year-old's computer"* — is the correct
   instinct. `gnome-remote-desktop` (an RDP *and* VNC server, arriving as a weak
   dependency) and `rygel` being found and removed is exactly the third-party
   drift that Apitor and Disney were fined over.

4. **The absence of engagement machinery is real, not claimed.** No streaks, no
   variable reward, no notification to the child (`show-banners=false`), no
   autoplay, no dwell-time ranking. `metrics.py` is display geometry, not
   analytics. `goodbye.py` says out loud that the reward is the artefact.
   Checklist items #10–#16 pass on inspection.

5. **The honesty conventions.** Every spike carries a "NOT verified" section
   that reads like it was written by someone who expects to be quoted against
   it. ADR-0010 records deliberate deviations *including the uncomfortable one*
   (#4: "the child cannot delete"). Documented deviation with a named revisit
   trigger is what a regulator actually wants to see; undocumented compliance is
   worth less.

---

## 3. Concerns, ranked

### Threat table

| Threat | Mitigation | Status |
|---|---|---|
| Child reaches a VT / terminal | 102 mutter keybindings blanked incl. `switch-to-session-1..12`; `NAutoVTs=0`/`ReserveVT=0`; `disable-command-line` | Structurally verified; **not verified on hardware** (lockdown §3.1) |
| Child reaches the network | `nft inet` reject on `skuid 1000`, Flatpak `--unshare=network`, polkit NM deny | **Proven** — 0 bytes on the wire, 13 packets rejected, control window positive |
| Child leaks a label via DNS | uid-53 rejects *before* the `lo` accept + authselect profile without `nss-resolve` | **Closed and re-proven**; `.local` via avahi is a documented residual |
| Child reaches the parent session | GDM autologin to `kid`; `disable-log-out`/`user-switching`; `login1.*` denied; no browser in the image | Good. Floor is the parent's password strength |
| Child mounts/reads a USB stick | `udisks2` polkit deny, `automount=false`, `autorun-never`, removable media read-only | Good; untested with real hardware |
| Sibling reads another child's work | **none** | **Open** — see B2 |
| Parent covertly monitors the child | No screenshot, keylogger or audio capture anywhere; parent panel unbuilt | Good in design; hover/gate logging is the exception (B4) |
| Data leaves the device | Zero telemetry; countme/makecache/rpm-ostreed/flatpak-update timers masked | Strong; Flathub retry timer is the one recurring outbound (M4) |
| A hostile image is pushed as an update | cosign keyless signing in CI | **No verification on the machine** — B3 |
| Laptop is lost, sold or handed on | none | **Open** — M2 |

### Blockers

**B1 — The child's data has no exit: no delete, no export, no retention rule.**
*Evidence:* `journal.py:19` states the contract as *"Nothing is ever deleted"*;
there is no `delete`, `export`, `rmtree` or `unlink` anywhere in
`shell/kidnix_shell/`. Checklist #7 (documented maximum retention, no
"indefinite"), #8 (one-action export **and** one-action real delete), #9 (child
can delete their own entries) and #20 (per-entry visibility from v1) are all
unmet. ADR-0010 #4 knowingly defers the *child's* delete with a good reason and
a resolution path ("Put away", recoverable for ≥30 days) — that is legitimate.
What is not covered by any ADR is that the **parent** cannot delete or export
either, and that "kept forever" is now a property of the code rather than a
decision anyone made. *Recommendation:* before the parent panel, ship three
things in `journal.py` — `export_all(dest)` (the tree is already open formats;
this is `shutil.copytree` plus a manifest), `delete_entry(id)` writing to a
30-day `.putaway/` shelf, and `delete_all()` that really unlinks. Write the
retention rule per data class into `docs/design/shell-v0.1.md` §5.

**B2 — Multi-child separation does not exist; the profiles are cosmetic.**
*Evidence:* `Paths.journal_root`, `Paths.usage_state` and `Paths.progress_state`
carry no profile component; `app.py:323` takes `config.profiles[0]`. Every child
runs as uid 1000, so "Who's here?" selects a name and a colour and nothing else.
A second child opens My Things and sees the first child's drawings; they share
one 60-minute daily budget and one progressive-disclosure counter. Research 03
§5 Q5 flags this as unresolved *policy*; the code has already resolved it, in
the direction of no separation, silently. *Recommendation:* make the profile id
a path segment for all three files now, while the corpus is small, and take the
"can a sibling see another's work?" question to the family as a setting with a
default of *no*.

**B3 — The update channel advertises a trust it does not enforce.**
*Evidence:* `build_files/10-branding.sh:45` writes
`"image-ref": "ostree-image-signed:docker://ghcr.io/mattcree/kidnix"`;
`.github/workflows/build.yml` does a keyless `cosign sign`; and there is **no**
`/etc/containers/policy.json`, no `registries.d`, no pinned certificate identity
anywhere in `system_files/`. Nothing on a running machine checks a signature
before `bootc upgrade` replaces the entire operating system as root. Checklist
#37 and the whole supply-chain argument in §6 takeaway 9 rest on this.
*Recommendation:* ship a `policy.json` that requires a sigstore signature for
`ghcr.io/mattcree/kidnix` pinned to the workflow's certificate identity and
issuer, assert it in `test_hardening.sh`, and add a greenboot check. If that is
too much for v0.1, remove the `ostree-image-signed:` string so the image does
not claim it.

**B4 — A research instrument is shipped on by default, and it records the
child.** *Evidence:* `speech.py` `_flush_hover_log` emits one INFO line per
hover utterance — `hover-speech: id=… dwell_ms=… selected=…` — and
`screens/grownup.py::_check` logs every PIN attempt with a wall-clock timestamp.
Both go to the systemd journal, which is persistent by default and has no
retention cap configured. Taken together this is a continuous, timestamped trace
of where a five-year-old's pointer hesitated and whether they followed through —
a behavioural record in the shape checklist #10 (no behavioural user model) and
#19 (no covert monitoring capability) exist to prevent. The comments are candid
that it exists for protocol P5, and P5 is good research; the problem is that the
research default and the shipped default are the same file, the child is not
told, the parent is not told, and a future "delete everything" in the Journal
will not touch it. *Recommendation:* gate it behind
`[research] hover_instrumentation = false` in `parent.toml`; drop `selected=`
unless a study is actually running (the follow-through boolean is the
profiling-shaped half); ship a `journald.conf.d` retention cap; and state in the
data page that the gate-attempt line exists and why.

### Major

**M1 — The child is never told what a grown-up can see.** Checklist #18 and ICO
standard 11 are the standards that *permit* parental visibility, and they permit
it on condition the child is told in terms they understand. Grep finds nothing:
no first-run moment, no on-demand explanation, no per-entry marker. This is
cheap to fix and it is the one item on the list that is about the child's
dignity rather than their security. *Recommendation:* one spoken, pictorial
screen after "Who's here?" on first run, repeatable from the Journal — *"the
things you make are kept here, and your grown-up can see them."*

**M2 — Nothing is encrypted, and there is no hand-over path.** Checklist #6 is
unmet: no LUKS, no FDE, no mention in `BUILDING.md` or `disk_config/`. `kid` is
passwordless with GDM autologin (`etc/gdm/custom.conf`), so possession of the
laptop is possession of the child's entire journal. There is also no
"give this machine away" action — no wipe of `/var/home/kid`, no PIN/parent
reset. On refurbished-laptop hardware that changes hands, this matters.

**M3 — The shipped `parent.toml` makes an unconfigured machine look
configured.** `hardening.md` §6 is right that "still 1234 means unconfigured" —
but `ParentConfig.is_default` is only true when *no* `pin_hash` was found
(`settings.py:349`, `__post_init__`), and `/etc/kidnix/parent.toml` ships **with
the 1234 hash and a public salt**. So the grown-up sheet's "This machine has no
parent config" warning does **not** appear on a stock install. The one signal
that the gate is open is suppressed by the file that opens it. *Recommendation:*
ship no `pin_hash` at all (let `__post_init__` supply it and flag
`is_default`), or add an explicit `pin_is_default = true` key.

**M4 — The Flathub first-boot timer retries forever.**
`kidnix-flatpaks-firstboot.timer` is `OnUnitActiveSec=30min`, `Persistent=true`,
conditioned only on a stamp file. A machine that stays offline — the normal
state for this product — reaches for the network every thirty minutes for the
life of the deployment. Nothing identifies the device, so it is not telemetry;
it is still an unbounded, unrequested outbound attempt on a child's computer,
and on a metered hotspot it is a repeated large download attempt. *Cap the
retries or move it behind a parent action in the panel.*

### Minor

- **m1 — `.local` still resolves.** The egress addendum accepts `mdns4_minimal`
  via avahi as a residual. It is LAN-only and low-risk, but the parent-facing
  sentence now has an asterisk again; add a window-D capture and one line to the
  data page.
- **m2 — Documentation drift.** `docs/LICENSES.md` §2 still lists Firefox as
  shipped and calls removal "an open question for M2"; `70-hardening.sh` removed
  it a day earlier. Meanwhile 183 MiB of WebKit *is* on the image
  (`hardening.md` §3.1) and does not appear in the parent-facing ledger. Both
  directions of that drift will bite a plain-English data page (checklist #41).
- **m3 — Progressive disclosure is keyed on session count.** `HomeConfig`
  reveals one tile every two completed sessions. The code and comments are
  careful (never shown, never resets, cannot widen the allow-list) and SYNTHESIS
  B2 grounds it — but "content unlocks with number of sessions" is literally the
  shape checklist #11 forbids, and a regulator will ask. Record the distinction
  in the CRIA rather than defending it later.
- **m4 — Process artefacts are missing.** No CRIA (#38), no eSafety Safety by
  Design self-assessment (#40), no SBOM or `SECURITY.md` (#37), no two-level
  plain-English data page (#41). Days of work, and per takeaway 10 they are the
  credibility that lets another family trust this.
- **m5 — Console residuals.** `getty@tty1` stays enabled, `kid`'s shell is
  `/bin/bash`, and `kernel.sysrq` is untouched (lockdown §4.8). All defensible;
  all still the residual physical path, and lockdown §3.1 (a child mashing
  Ctrl+Alt+F3 on real hardware) is unverified.

---

## 4. The minimum before any other family uses it

1. **A data exit.** Parent export in one action, parent delete-all in one
   action, child-level "put away" with a 30-day shelf, and a written retention
   rule per data class. (B1)
2. **Per-profile journal, usage and progress paths.** (B2)
3. **Signature verification on the update path**, pinned to the CI identity —
   or the removal of the `ostree-image-signed` claim. (B3)
4. **Hover and gate instrumentation off by default**, plus a journald retention
   cap. (B4)
5. **A first-run flow that forces a parent PIN and a parent password** and
   refuses to start a session on 1234. (M3, and the dev password in
   `disk_config/`.)
6. **One spoken screen telling the child what a grown-up can see.** (M1)
7. **`SECURITY.md`, a published CRIA, and a two-level "what kidnix does with
   your data" page** that matches the machine — including the WebKit libraries
   and the `.local` residual. (m2, m4)
8. **A documented hand-over: wipe the child, reset the parent** — and either
   FDE or an explicit statement that the disk is not encrypted. (M2)

---

## 5. Three questions

1. **Whose journal is it?** Today the parent sees everything and no one can
   delete anything. What is the plan for this child at 8, and at 10–12 when
   research 03 §5 Q2 says the default should shift? Is the mechanism
   (a `visibility` field in `entry.json`, unused for now) built while the corpus
   is a hundred drawings, or retrofitted when it is ten thousand?

2. **Is the hover instrumentation research or product?** When P5 concludes, what
   removes it — and who decides? Right now nothing distinguishes "we are running
   a study on our own child" from "this build records where children look."

3. **What is kidnix's posture the day the second family installs it?** A signed
   image on ghcr, an update channel and an issue tracker start to look like a
   service with a controller behind it, whatever the README says. Which of the
   41 items becomes *legal* rather than *best practice* on that day, and is
   anyone prepared to be the named contact in `SECURITY.md`?
