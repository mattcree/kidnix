#!/usr/bin/bash
# Boot the rootless qcow2 in a KVM window *with a way in as the parent*.
#
# `bcvk to-disk` takes no blueprint, so the rootless disk has no `parent`
# password and no SSH key -- fine for the boot test, useless for a human who
# wants the grown-up desktop and the parent panel. This script does what
# tests/e2e/vm.py does: it hands PID 1 a one-shot unit over SMBIOS type 11
# credentials that runs before gdm/sshd, sets parent's password and drops an
# ephemeral root key. -snapshot means nothing persists.
#
#   tools/vm-dev.sh [qcow2] [ssh-port] [display]
#   parent password: kidnix   root ssh: ssh -i output/vm-dev/id -p <port> root@localhost
set -euo pipefail

qcow2="${1:-output/qcow2/disk.qcow2}"
port="${2:-2222}"
display="${3:-gtk}"
pw="${KIDNIX_DEV_PARENT_PASSWORD:-kidnix}"
keydir="output/vm-dev"

test -f "${qcow2}" || { echo "error: ${qcow2} not found -- run 'just build-qcow2-rootless'" >&2; exit 1; }
mkdir -p "${keydir}"
if [ ! -f "${keydir}/id" ]; then
    ssh-keygen -q -t ed25519 -N '' -f "${keydir}/id"
fi
pub="$(cat "${keydir}/id.pub")"

b64() { base64 -w0; }

unit="$(printf '%s\n' \
    '[Unit]' \
    'Description=kidnix dev: parent password + root key (host-injected, ephemeral)' \
    'After=systemd-sysusers.service' \
    'Before=sshd.service gdm.service' \
    'ConditionPathExists=/run/credentials/@system/kidnix-dev-setup' \
    '' \
    '[Service]' \
    'Type=oneshot' \
    'RemainAfterExit=yes' \
    'ExecStart=/usr/bin/bash /run/credentials/@system/kidnix-dev-setup' \
    'StandardOutput=journal+console' \
    'StandardError=journal+console' | b64)"
dropin="$(printf '%s\n' '[Unit]' 'Wants=kidnix-dev.service' | b64)"
script="$(printf '%s\n' \
    'set -eu' \
    'install -d -m 0700 /root/.ssh' \
    "echo '${pub}' >/root/.ssh/authorized_keys" \
    'chmod 0600 /root/.ssh/authorized_keys' \
    "echo 'parent:${pw}' | chpasswd" \
    'echo KIDNIX_DEV_SETUP_OK >/dev/console' | b64)"

echo "==> booting ${qcow2} (snapshot; parent password '${pw}'; root ssh -i ${keydir}/id -p ${port})"
exec qemu-system-x86_64 \
    -machine q35,accel=kvm -cpu host -smp "${VM_CPUS:-4}" -m "${VM_RAM:-4096}" -snapshot \
    -bios /usr/share/OVMF/OVMF_CODE.fd \
    -drive "file=${qcow2},if=virtio,format=qcow2" \
    -netdev "user,id=net0,hostfwd=tcp::${port}-:22" -device virtio-net-pci,netdev=net0 \
    -device virtio-vga-gl -display "${display},gl=on" -device virtio-rng-pci \
    -smbios "type=11,value=io.systemd.credential.binary:systemd.extra-unit.kidnix-dev.service=${unit}" \
    -smbios "type=11,value=io.systemd.credential.binary:systemd.unit-dropin.multi-user.target=${dropin}" \
    -smbios "type=11,value=io.systemd.credential.binary:kidnix-dev-setup=${script}" \
    -serial "file:${keydir}/serial.log"
