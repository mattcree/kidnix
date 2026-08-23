> **Status 2026-08-23 (later):** the fix in §4.1 now SHIPS as
> `system_files/usr/lib/greenboot/red.d/10-kidnix-boot-counter.sh`; `just test-rollback`
> passes 11/11 on the shipped image. The body below records the finding as it was.

# Spike: does a bad update actually roll itself back?

**Status: the claim is FALSE on the disks kidnix builds today.** A deployment
whose required health check fails does **not** roll back. The machine reboots
itself every ~8 seconds, for ever, and never returns to the deployment that
worked. There is no manual intervention available either: the boot is too short
to log in.

This is AGENTS.md non-negotiable #8 ("cannot be broken"), the largest untested
claim in the product (FLOWS.md B16/C3), and research 07 §4 risk 4. It is now
tested, the failure is understood down to the line of GRUB script that does not
run, and a 15-line fix is proposed and **verified in a VM**.

Everything below was observed on a real booted machine, not reasoned about.
Serial logs are in `output/rollback/`; reproduce with `just test-rollback`.

---

## 1. What the test does

`just test-rollback` → `tests/boot/rollback_test.py`.

1. `just build-selftest-broken` builds `localhost/kidnix:selftest-broken` — the
   shipped image plus **one** extra file, an always-failing required greenboot
   check at `/usr/lib/greenboot/check/required.d/99-kidnix-selftest-broken.sh`.
   It comes from `--build-arg KIDNIX_SELFTEST_BREAK_HEALTH=1`; every normal
   build omits it and `tests/image/test_lockdown.sh` asserts it is absent, so it
   cannot reach a shipped image by accident.
2. `just push-selftest-broken` serves it from the throwaway local registry the
   fast loop already uses (`localhost:5000`, reachable from the guest at
   `10.0.2.2:5000`).
3. The harness makes a **qcow2 overlay** of `output/qcow2/disk.qcow2` and boots
   *that*. This test cannot use `-snapshot` like the other boot tests, and it
   cannot pass `-no-reboot`: the entire subject is state that has to survive
   reboots — the staged deployment, and `boot_counter` in `/boot/grub2/grubenv`
   — and the guest has to be free to restart itself as often as it likes.
4. Root SSH and two probe units are injected with **SMBIOS system credentials**
   (the trick from `docs/spikes/e2e-scenario.md`); nothing in the image is
   modified to make it testable. One injected unit prints a single line per boot
   on the serial console — which deployment booted, and the whole of grubenv —
   and a drop-in forces greenboot's own verdict onto the console too.
5. `bootc switch --transport registry 10.0.2.2:5000/kidnix:selftest-broken`,
   reboot, and watch.

Two useful side-findings from step 5:

- **No signature-policy escape hatch is needed.** `bootc switch` succeeded with
  the image's real `/etc/containers/policy.json`, because the base image's
  default `docker: ""` scope is `insecureAcceptAnything` and only
  `ghcr.io/mattcree/kidnix` demands a signature. `just vm-upgrade` passes
  `--enforce-container-sigpolicy=false` and docs/BUILDING.md says it is
  required; it is not. (The harness still falls back to it and reports which
  path it took.)
- The **insecure-registry** drop-in *is* needed (plain HTTP), and is written
  into the running guest's `/etc` at test time. The image ships no insecure
  registry config and must not.

Cost: **~4 minutes to a verdict**, not the 10–15 budgeted — a bricked machine
declares itself quickly, and a healthy recovery took 3.7 minutes. Most of that
is the two full boots at either end; the failing boots are 8 seconds each.

---

## 2. What happens (measured)

```
boot 1  ORIGINAL  grubenv: greenboot_rollback_trigger=1                    -> healthy, KIDNIX_BOOT_OK
        bootc switch --> 10.0.2.2:5000/kidnix:selftest-broken   (37 s, staged)
boot 2  BROKEN    grubenv: ... boot_success=1                   greenboot: required check failed
boot 3  BROKEN    grubenv: ... boot_success=0 boot_counter=3     "Boot counter is 3, rebooting to try again"
boot 4  BROKEN    grubenv: ... boot_success=0 boot_counter=3     "Boot counter is 3, rebooting to try again"
boot 5  BROKEN    grubenv: ... boot_success=0 boot_counter=3     ...
   ... 12 boots of the broken deployment in 2.4 minutes, one every ~8 s.
       The harness stopped it. The machine would not have.
```

Eight seconds is not enough to log in, so "manual intervention" is not on the
table either: the only recovery is a GRUB menu the child's machine does not
show and a parent would not know to use.

greenboot behaves perfectly. From the serial console:

```
greenboot::greenboot > running required check .../99-kidnix-selftest-broken.sh
greenboot::greenboot > required script .../99-kidnix-selftest-broken.sh failed!
greenboot            > required health-check failed, skipping remaining scripts
greenboot            > Remounting /boot as rw for operation
greenboot::grub      > Set grubenv: boot_success=0
greenboot            > Boot counter is 3, rebooting to try again
greenboot::handler   > restarting the system
```

**`boot_counter` never moves.** It is set to 3 once, by
`greenboot-set-rollback-trigger.service`, and stays 3 through every subsequent
boot. Nothing else in the chain can ever fire, so the machine loops.

---

## 3. Why — the actual root cause

Decrementing the counter is **GRUB's** job, not greenboot's. bootupd ships
`/usr/lib/bootupd/grub2-static/configs.d/08_greenboot.cfg` and it is genuinely
present in the installed `/boot/grub2/grub.cfg` (verified, lines 72–92):

```
insmod increment
if [ -n "${boot_counter}" -a "${boot_success}" = "0" ]; then
  if  [ "${boot_counter}" = "0" -o "${boot_counter}" = "-1" ]; then
    set default=1
    set boot_counter=-1
  else
    decrement boot_counter
  fi
  save_env boot_counter
fi
set boot_success=0
save_env boot_success
```

So the snippet is installed, and the image test that asserts its presence passes
— and it is still useless here, because **`save_env` cannot write this
filesystem**:

```
# findmnt -no SOURCE,FSTYPE /boot
/dev/vda3[/boot]   btrfs
```

`/boot` is a **btrfs subvolume of the root partition**. GRUB can *read* btrfs
but cannot write it; `save_env` needs a plain, non-CoW, non-sparse file it can
overwrite in place. Every `save_env` in that snippet is a no-op.

The proof is in the very first probe line of a *healthy* boot: after GRUB has
supposedly run `set boot_success=0; save_env boot_success`, the guest reads
grubenv and finds **no `boot_success` key at all**. Later boots show
`boot_success=0` only because *greenboot* wrote it from Linux, where writing
btrfs is unremarkable.

`/boot` is btrfs because that is how kidnix builds disks:
`just build-qcow2-rootless` passes `bcvk to-disk --filesystem btrfs`, and
`just build-qcow2` passes `--bootc-default-fs btrfs`; neither carves out a
separate `/boot`. `env_block=512+1` in grubenv is CoreOS's blocklist trick for
exactly this problem, and it does not save us either.

### 3.1 Research 07 §4 risk 4 resolves the other way round

Research 07 (and `docs/spikes/lockdown.md` §1.5) recorded "greenboot-rs does not
call `bootc rollback`; the mechanism is GRUB-level". **That is wrong for
greenboot 0.16.3.** The binary contains, and the flow uses:

```
Boot counter exhausted and rollback trigger is set - initiating rollback
Rollback with 'bootc rollback'
Rollback successful
Rollback not initiated as boot_counter is <N>
System is unhealthy but boot_counter is not set, manual intervention required
Container environment detected; skipping reboot and rollback handling
```

greenboot-rs reads `/run/ostree-booted`, parses `bootc status --booted --json`,
and calls **`bootc rollback`** itself when the counter is exhausted. So the
userspace half of the mechanism is *already* implemented and already correct.
The only thing missing is the decrement — the one step that was delegated to a
bootloader that cannot perform it.

That is a much better position than it looked: kidnix does not need to
reimplement rollback, it needs to move one arithmetic operation out of GRUB.

---

## 4. The fix

### 4.1 Decrement the counter from Linux (recommended, verified)

greenboot runs every script in `red.d` when a boot goes red, and — verified in
§5 — it runs them *before* it decides what to do about the counter. A script
there closes the gap:

```bash
#!/usr/bin/bash
# /usr/lib/greenboot/red.d/10-kidnix-boot-counter.sh
#
# GRUB cannot write /boot/grub2/grubenv when /boot is btrfs, so the
# `decrement boot_counter` in bootupd's 08_greenboot.cfg never happens and
# greenboot's own rollback -- which fires when the counter reaches 0 -- is
# never reached. Without this the machine reboot-loops on a bad update for ever.
set -uo pipefail
GRUBENV=/boot/grub2/grubenv
counter="$(grub2-editenv "${GRUBENV}" list 2>/dev/null | sed -n 's/^boot_counter=//p')"
[[ "${counter}" =~ ^-?[0-9]+$ ]] || exit 0
(( counter <= 0 )) && exit 0
remounted=0
if findmnt -no OPTIONS /boot | tr ',' '\n' | grep -qx ro; then
    mount -o remount,rw /boot && remounted=1
fi
grub2-editenv "${GRUBENV}" set "boot_counter=$(( counter - 1 ))"
rc=$?
(( remounted )) && mount -o remount,ro /boot
echo "kidnix: boot_counter ${counter} -> $(( counter - 1 ))"
exit "${rc}"
```

Properties that matter:

- It only ever *decrements* a counter greenboot already set, so it cannot arm a
  rollback on a machine that is not already in an update attempt.
- **One thing to re-verify when landing it.** The run in §5 placed the script in
  `/etc/greenboot/red.d/` (the only path a host-injected file can use). It
  should *ship* in `/usr/lib/greenboot/red.d/`, image-owned, next to our checks:
  the greenboot binary carries both `/usr/lib/greenboot` and `/etc/greenboot` as
  roots and the README documents `/usr/lib` as the ostree location, but only the
  `/etc` path has actually been exercised. Land it, rerun `just test-rollback`
  with no flag, and the question answers itself.
- It never touches a machine with no `boot_counter` (the normal, steady state).
- It is idempotent per boot: greenboot runs `red.d` once.
- It leaves the decision to roll back where it belongs — with greenboot, which
  already knows how to call `bootc rollback` and how to tell a bootc system from
  an rpm-ostree one.
- If GRUB ever *can* write the env (an ext4 `/boot`, see 4.2), the counter drops
  by two per failed boot instead of one. That shortens the countdown, it does not
  break it. Worth a comment in the script.

**Verified**: `just test-rollback --with-proposed-fix` injects exactly this
script into the guest at boot and reruns the whole scenario. See §5.

**Not shipped.** The script belongs in `system_files/usr/lib/greenboot/red.d/`,
which is outside this spike's ownership, and landing it means rebuilding the
image and the qcow2 while other work is in flight. It is a one-commit change for
the thinker:

1. `system_files/usr/lib/greenboot/red.d/10-kidnix-boot-counter.sh` — the script
   above, verbatim (it is also the `FIX_SCRIPT` constant in
   `tests/boot/rollback_test.py`, which should then be deleted along with
   `--with-proposed-fix`).
2. `build_files/40-lockdown.sh` §8 — extend the existing `for check in …` loop
   to cover `/usr/lib/greenboot/red.d/*-kidnix-*.sh` so it is chmod 0755 and
   `bash -n` clean like the others.
3. `tests/image/test_lockdown.sh` — `assert_exec` it next to the four checks.
4. `docs/spikes/lockdown.md` §1.5 — correct the "how rollback actually fires"
   paragraph (see §6).

After that, `just test-rollback` passes with no flag, and it becomes the
regression test for all of it.

### 4.2 Give `/boot` a filesystem GRUB can write (complementary)

The root cause is a filesystem choice we make in the Justfile, so it can also be
fixed there: build disks with an **ext4 `/boot`** (a separate partition, as
Fedora and CoreOS do) and the stock snippet works as designed with no kidnix
code at all.

This is worth doing *as well*, but it is not sufficient on its own, because
kidnix ships an **image**, not only a disk: someone installing it with Anaconda,
or `bootc install to-disk` with their own layout, chooses their own filesystems.
An appliance for a five-year-old should not have "and hopefully /boot is ext4"
as a load-bearing assumption. 4.1 protects every install; 4.2 makes the standard
one belt-and-braces.

Not attempted here (it needs a disk rebuild, ~15 min, and belongs with whoever
owns `disk_config/`).

### 4.3 Rejected: a kidnix health-check unit that calls `bootc rollback`

The obvious alternative — our own unit that counts failures and calls
`bootc rollback` — duplicates logic greenboot 0.16.3 already has (rollback
trigger, bootc/rpm-ostree detection, container detection, MOTD, journal
inspection of the previous boot's attempt) and would have to race greenboot's
own `systemctl reboot`. One `red.d` script that supplies the single missing
operation is strictly smaller and strictly less surprising.

---

## 5. Evidence that the fix works

`just test-rollback --with-proposed-fix` injects the §4.1 script into the guest
at boot (as `/etc/greenboot/red.d/10-kidnix-boot-counter.sh`, via the same
credential mechanism that plants the SSH key — the *image* is still unmodified)
and reruns the identical scenario. **11/11 checks, 3.7 minutes, unattended:**

```
[  0.0m] booting the ORIGINAL deployment
[  0.5m] bootc switch --> 10.0.2.2:5000/kidnix:selftest-broken
[  1.1m] rebooting onto the broken deployment
[  2.1m] boot #2: BROKEN (boot_counter=-  boot_success=1)
[  2.2m] boot #3: BROKEN (boot_counter=3  boot_success=0)
[  2.4m] boot #4: BROKEN (boot_counter=2  boot_success=0)
[  2.5m] boot #5: BROKEN (boot_counter=1  boot_success=0)
[  3.4m] boot #6: ORIGINAL (boot_counter=- boot_success=0)

PASS  the broken deployment actually booted
PASS  GRUB's boot_counter is armed on the broken deployment -- seen: [None, '3', '2', '1']
PASS  boot_counter decrements on every failed boot -- [3, 2, 1]
PASS  the machine rolled ITSELF back -- after 4 boot(s) of the broken image
PASS  the booted deployment is the original one, not the broken one
PASS  bootc agrees it is the image we started from
PASS  greenboot is green again on the rolled-back deployment -- active
PASS  the child's shell is running again -- active
```

and from the guest's own console on the last failed boot:

```
greenboot::greenboot > required script .../99-kidnix-selftest-broken.sh failed!
kidnix: boot_counter 1 -> 0
greenboot            > Boot counter exhausted and rollback trigger is set - initiating rollback
greenboot            > Greenboot will now attempt to rollback to a previous deployment.
greenboot            > Rollback successful
greenboot::handler   > restarting the system
```

Three things this confirms beyond "it works":

- greenboot **does** run `red.d` scripts on a red boot, and it runs them
  **before** it evaluates the counter — so a decrement there lands in time.
- greenboot **clears `boot_counter` after a successful rollback** (the last
  probe shows no counter at all), so the recovered machine is not left one
  `save_env` away from bouncing back into the bad deployment.
- The rolled-back machine is genuinely usable, not merely booted: `bootc status`
  reports the original digest, greenboot is green, and
  `kidnix-shell.service` in the kid's user manager is `active`.

Time from "bad update rebooted" to "child's shell back on screen": **2.3
minutes**, four boots. Nobody had to touch it. The harness's last act is a
framebuffer screendump, and `output/rollback/rollback.png` is the kid's
"Who's here?" picker — the machine did not merely survive, it came home.

---

## 6. What this changes about what we claim

- `docs/spikes/lockdown.md` §1.5's "how rollback actually fires (honest
  version)" is now **wrong in both directions**: greenboot-rs *does* call
  `bootc rollback`, and the GRUB snippet it credits *cannot run* on our disks.
  It should be corrected, and its §3 item 5 ("greenboot rollback end-to-end,
  UNVERIFIED") is now verified — as a failure.
- Research 07 §4 risk 4 can be closed with the finding in §3.1.
- The image test's assertion that `08_greenboot.cfg` exists is a **false
  comfort**: the file being present says nothing about whether the bootloader
  can act on it. Keep it, but it is not evidence of rollback.
- `docs/BUILDING.md`'s claim that `--enforce-container-sigpolicy=false` is
  needed for the local registry is inaccurate (§1).

## 7. Running it

**`just test-rollback` exits 1 today, and that is the correct answer.** It is
red because the product claim is false, not because the harness is broken; the
verdict line points at this document. It goes green the moment §4.1 ships.

```sh
just test-rollback                      # ~4 min to a FAIL today, ~4 min to a PASS with the fix
just test-rollback --with-proposed-fix  # inject the §4.1 script and prove it works
just test-rollback --verbose            # the whole serial console on stdout
just rollback-clean                     # stop the registry, drop the unhealthy image
```

Artifacts land in `output/rollback/`: `serial.log` (every boot), `timeline.txt`,
`bootc-switch.log`, `final-state.txt` or `stuck-state.txt`, and a screenshot.

It is **nightly, not per-PR**: it wants `/dev/kvm`, a 8.4 GB qcow2 built by
`just build-qcow2-rootless`, a second image build and a registry push. The
harness has a `--dry-run` (wired into `just test-boot-dry`) that validates the
plumbing in milliseconds on every PR, including that the qemu command carries
neither `-snapshot` nor `-no-reboot`.
