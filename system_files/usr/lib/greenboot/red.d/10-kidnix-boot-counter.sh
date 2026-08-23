#!/usr/bin/bash
# /usr/lib/greenboot/red.d/10-kidnix-boot-counter.sh
#
# GRUB cannot write /boot/grub2/grubenv when /boot is btrfs, so the
# `decrement boot_counter` in bootupd's 08_greenboot.cfg never happens and
# greenboot's own rollback -- which fires when the counter reaches 0 -- is
# never reached. Without this the machine reboot-loops on a bad update for
# ever (docs/spikes/rollback.md). greenboot runs red.d before it looks at the
# counter, so decrementing it here closes the gap. It only ever decrements a
# counter greenboot already set, so it cannot arm a rollback on a machine that
# is not already in an update attempt. If GRUB ever *can* write the env (an
# ext4 /boot) the counter drops by two per failed boot -- shorter, not broken.
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
