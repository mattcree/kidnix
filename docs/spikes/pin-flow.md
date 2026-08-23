# Spike: setting the grown-up PIN from the only session this machine shows

**Status:** implemented. Green in `just test-image` (`test_lockdown.sh`,
`test_hardening.sh`, `test_egress.sh`), asserted at build time in
`build_files/40-lockdown.sh` and `70-hardening.sh`, and proved on a booted
machine by `tests/boot/bcvk_boot_test.py` (`assert_pin`), which is the only
place polkitd itself answers the question.

**Owner:** the polkit rules and policy, `/usr/bin/kidnix-set-pin`, and the
first-run instructions in `docs/PARENTS.md`. Not the shell: how the PIN pad
looks and what it says is `shell/kidnix_shell/screens/grownup.py`.

---

## 1. The problem this closes

The image ships `/etc/kidnix/parent.toml` with **no `pin_hash` and no
`pin_salt`** (spec 7d #11). That was the right call — a documented default of
1234 is not a PIN, it is a rumour — and it made `ParentConfig.must_set_pin`
true on every fresh machine, so the grown-up sheet opens on "Choose a grown-up
PIN" with nothing else reachable until it is done.

Then the chosen PIN had nowhere to go.

`parent.toml` is root-owned, and it has to be: a child-writable PIN is not a
PIN. The shell runs as `kid`. So the pad ran `pkexec /usr/bin/kidnix-set-pin
--stdin` — and `40-kidnix-kid.rules` denied the `kid` account **every** action
whose id begins `org.kidnix.`, because that is the rule that stops a child
authorising `kidnix-wipe`. pkexec asks for the *annotated* action id, so the
denial covered set-pin too. The sheet degraded to holding the PIN for the
session and printing the command that would make it permanent — a command
typed in an account the parent may never have opened.

`docs/design/shell-v0.1-implementation-notes.md` §23.4 called that "the honest
limit". Honest, but the outcome was a machine that asked for a PIN every boot
and forgot it every boot: the gate that ruling closed was open again by
morning.

## 2. What changed

**One polkit id, granted, exactly.** `40-kidnix-kid.rules` gained a
`GRANTED_IDS` array checked *before* the deny list, holding one **exact** id
(never a prefix):

```js
var GRANTED_IDS = [
    "org.kidnix.set-pin"
];
```

and returning `polkit.Result.YES` for `kid`. `org.kidnix.parent-tools` — the
action behind `kidnix-export` and `kidnix-wipe` — stays denied, along with the
whole `org.kidnix.` prefix around it and `org.freedesktop.policykit.exec`
besides. `org.kidnix.set-pin.evil` and `org.kidnix.set-pinned` are asserted to
be `NO` in three places, because the near-misses are the assertion that
matters: a stray dot turning the exact match back into a prefix would hand a
five-year-old `kidnix-wipe`, and nothing else in the file would look wrong.

`YES`, not a fall-through to the policy default. The default for that action is
`auth_admin_keep` — a wheel password — and there is nobody to type one at the
moment a laptop is handed to a child.

**The authorisation is not the authority.** Saying YES grants the right to
*ask*. `/usr/bin/kidnix-set-pin` decides, and it was rewritten around four
rules:

1. **First set is open.** No `pin_hash` in the file → anybody at the gate may
   choose the first PIN. Four numbers a grown-up chose beat no numbers.
2. **A change costs the current PIN.** Once a hash exists, nothing is written
   unless the caller proves the current PIN (stdin line 2, or a prompt on a
   tty). So a child can never *change* the PIN that fences them in.
3. **`--reset` and a path argument are for grown-ups.** Both are refused unless
   the caller is root or in `wheel`; `kid` is neither. The caller is identified
   by `PKEXEC_UID` (which pkexec sets and scrubs the environment around, so it
   cannot be forged) then `SUDO_UID`, then the real uid. The path check is the
   one that would have been a real hole: this process runs as root, and without
   it a child could aim a root-owned write at any file on the machine.
4. **Wrong guesses cost time.** Two seconds each, five a minute, counted in
   `/var/lib/kidnix/set-pin.failures` (root-owned, 0600, machine-local so a
   reboot does not clear it). 10 000 possible PINs at that rate is a day and a
   half of somebody sitting at the laptop. A successful set clears the counter,
   so an honest mistake never lands the parent mid-lockout.

Exit codes are part of the contract, because the shell reads them: `0` written,
`3` wrong current PIN or locked out, `4` a PIN is already set and none was
proved, `1` refused, `64` usage. `--check` is a no-op probe that answers "may I,
and is a PIN set?" without changing anything — it exists so the boot test can
ask whether the child's session can reach the helper at all.

The PIN itself is never in `argv` (world-readable in `/proc`) and never in an
environment variable: both PINs travel over the verifying python process's
**stdin**. Nothing logs a digit, a length, or a first character — a log line a
child can shoulder-surf is the same failure as an echoed one. The hashing and
the in-place edit are `kidnix_shell.settings.hash_pin` / `rewrite_pin`, so the
file format and the shell's reader cannot drift apart, and the rewrite is
comment-preserving: two lines change, the other ninety do not.

## 3. The threat model, honestly

**A child alone with a brand-new machine can set the first PIN.** This is real
and it is not fixable inside the machine. Whoever reaches the gate first on an
unconfigured install chooses the four numbers; if that is the six-year-old, the
parent is locked out of the sheet until they run `sudo kidnix-set-pin --reset`
from their own account.

Three things make that the right trade:

* The alternative is strictly worse. Before this change the child could not set
  a PIN *and neither could anybody else without a terminal*, so the gate stayed
  open on every machine whose parent never opened one. An open gate is worse
  than a gate whose key is briefly in the wrong hand.
* The recovery is one command, needs no reinstall and loses nothing:
  `sudo kidnix-set-pin --reset` from the parent account (wheel, their own
  password). It is documented in `docs/PARENTS.md` next to the instruction that
  avoids ever needing it.
* **First-run instructions are the mitigation.** `docs/PARENTS.md` now opens
  the PIN section by telling the installing parent to hold the corner tile and
  choose the PIN *before the child touches the laptop*, and to do it where the
  child cannot watch their fingers. That second half was always the actual
  threat here (a six-year-old who has seen you type four buttons has your PIN),
  and it is unchanged by any of this.

**A child cannot escalate through the carve-out.** They may run one program as
root, with a fixed path, whose entire behaviour is "write two lines into
`/etc/kidnix/parent.toml`, or refuse". No path argument, no `--reset`, no shell,
no environment they control (pkexec scrubs it), and the one write it does is
atomic and mode 0644 root:root.

**What this does not defend against, and never claimed to.** The gate is a
*usability* boundary, not a safe: the disk is not encrypted, `parent.toml` is
world-readable by design (the shell must read the hash to check a PIN), and
anyone older and determined has better routes than guessing four digits. The
structural guarantees on this machine are nftables (egress), the immutable
image, and the shell only knowing about the activities we ship. The PIN keeps a
five-year-old out of settings.

**`kid` and non-seat sessions.** The rule deliberately does not test
`subject.active`. `sshd_config.d/10-kidnix.conf` carries `DenyUsers kid`, so
there is no non-seat session for `kid` to arrive from, and making the verdict
depend on session state would make the dry-run checker
(`kidnix-polkit-check`) and polkitd disagree about the single rule that most
needs proving.

## 4. Where each claim is proved

| Claim | Proved by |
| --- | --- |
| kid gets `YES` for `org.kidnix.set-pin`, `NO` for everything else of ours, near-misses included | `build_files/40-lockdown.sh`, `tests/image/test_lockdown.sh` |
| exactly one `org.kidnix.*` id is in the grant list, and nothing under `org.freedesktop.` | `tests/image/test_lockdown.sh`, `tests/image/test_egress.sh` |
| first set open; change needs the current PIN; kid may not `--reset` or name a file; the rewrite keeps the rest of the file; the PIN is not stored | `build_files/70-hardening.sh`, `tests/image/test_hardening.sh` |
| two seconds a guess, five a minute, sixth refused immediately | `tests/image/test_hardening.sh` |
| polkitd (not the evaluator) authorises the real kid session, and refuses it `kidnix-wipe` | `tests/boot/bcvk_boot_test.py::assert_pin` |
| `pkexec kidnix-set-pin --stdin` as `kid` really writes `/etc/kidnix/parent.toml` on a booted machine, once | `tests/boot/bcvk_boot_test.py::assert_pin` |

### 4.1 The bug the boot test caught, and what it changed

The first run of `assert_pin` against a real VM failed with `pkexec` exit 127
for `org.kidnix.set-pin` while every dry-run check was green. The cause was in
the `.policy` file, not the rules: the long comment explaining *why* the child
may set a PIN contained a **double hyphen**, which XML comments may not, so
polkitd refused to parse the file and the action was never registered. An
unregistered action makes pkexec fail with "not authorized" — which is
indistinguishable, from the outside, from the lockdown working correctly.

`kidnix-polkit-check` cannot see this: it evaluates the rules file, and the
rules file was fine. So the parse is now asserted in two more places
(`build_files/40-lockdown.sh` and `tests/image/test_lockdown.sh`, both via
minidom, both also checking the id and the `exec.path` annotation), and the
file carries a note for editors that its option names must be spelled out in
words. It is worth stating plainly: **every static check in this repo passed a
policy file that the machine ignored.** The boot test earned its runtime here.

## 5. Open, and deliberately left open

**The shell still sends one line.** `grownup.py` runs `pkexec kidnix-set-pin
--stdin` with the new PIN only, so the *first* set from the sheet now persists
and a later **change** from the sheet is refused (exit 4) and falls back to the
session-scoped PIN it already had. The stdin protocol has line 2 waiting for
it: the parent typed the current PIN at the gate two screens earlier, so the
sheet already knows it and a shell-side wave can pass it through. That is a
`shell/` change and is not made here.

**Nothing rate-limits the *first* set**, because there is nothing to guess: an
unconfigured machine has no secret to get wrong. A stale lockout from a
previous PIN can still be in force, which is a minute of waiting in a case that
needs a `--reset` anyway.
