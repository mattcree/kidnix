set shell := ["bash", "-euo", "pipefail", "-c"]

# --- configuration -----------------------------------------------------------

image := "kidnix"
registry := "localhost"
tag := "latest"
image_ref := registry / image + ":" + tag
date_tag := `date -u +%Y%m%d`
version := "0.1.0"

base_image := "ghcr.io/ublue-os/base-main"
base_tag := "44"

output_dir := justfile_directory() / "output"
disk_config := output_dir / "config.toml"
qcow2 := output_dir / "qcow2/disk.qcow2"

# Local registry used by the push-local / vm-upgrade fast loop.
local_registry_port := "5000"
local_registry := "localhost:" + local_registry_port

# VM settings. bcvk takes "4G"; qemu and boot_test.py take MiB.
vm_ram := "4096"
vm_ram_h := "4G"
vm_cpus := "4"
vm_ssh_port := "2222"

# bcvk -- "bootc virtualization kit", the rootless VM driver for the fast loop.
# Not packaged by Homebrew; `just bcvk-install` drops a checksummed upstream
# release binary here. A distro package on PATH wins over this copy.
bcvk_version := "0.18.0"
bcvk_bin := home_directory() / ".local/bin/bcvk"
bcvk := `command -v bcvk 2>/dev/null || echo "$HOME/.local/bin/bcvk"`

# Containerised linters -- nothing is installed on the host.
shellcheck_image := "docker.io/koalaman/shellcheck:stable"
hadolint_image := "docker.io/hadolint/hadolint:latest-alpine"
yamllint_image := "docker.io/pipelinecomponents/yamllint:latest"

# Disk-image builders. `bootc-image-builder` was archived on 18 June 2026 and
# merged into osbuild/image-builder; quay.io/centos-bootc/bootc-image-builder
# has had no push since that day. ghcr.io/osbuild/image-builder is the live
# successor (rebuilt daily; `image-builder-cli` is the same digest). Digest-
# pinned so a disk build is reproducible; bump it deliberately.
ib_image := "ghcr.io/osbuild/image-builder@sha256:110aef206d18258b2241a5f4f2dbbbf193c937b67363ba5ce64d4e45fcf464b2"
bib_image := "quay.io/centos-bootc/bootc-image-builder:latest"

_default:
    @just --list --unsorted

# --- lint --------------------------------------------------------------------

# Run every linter (shellcheck, hadolint, yamllint, just --fmt).
lint: lint-shell lint-containerfile lint-yaml lint-just lint-python

# shellcheck every tracked shell script.
lint-shell:
    @echo "==> shellcheck"
    @mapfile -t scripts < <(just _shell-files); \
    podman run --rm -v "{{ justfile_directory() }}:/mnt:z" -w /mnt \
        {{ shellcheck_image }} --color=always "${scripts[@]}"

# List every file shellcheck should see (shebang-based, so nothing is missed).
_shell-files:
    @cd "{{ justfile_directory() }}"; \
    find build_files system_files tests -type f \
        \( -name '*.sh' -o -name '*.bash' \) -print; \
    grep -rlE '^#!.*(bash|/bin/sh)' system_files/usr/bin system_files/usr/libexec 2>/dev/null || true

lint-containerfile:
    @echo "==> hadolint"
    podman run --rm -i -v "{{ justfile_directory() }}/.hadolint.yaml:/.hadolint.yaml:z" \
        {{ hadolint_image }} hadolint --config /.hadolint.yaml - < Containerfile

lint-yaml:
    @echo "==> yamllint"
    podman run --rm -v "{{ justfile_directory() }}:/code:z" -w /code \
        {{ yamllint_image }} yamllint -c .yamllint.yaml .github/

lint-just:
    @echo "==> just --fmt --check"
    just --unstable --fmt --check

# ruff via uv; skipped cleanly if uv is unavailable.
lint-python:
    @echo "==> ruff"
    @if command -v uv >/dev/null 2>&1; then \
        uvx ruff check tests/ && uvx ruff format --check tests/; \
    else \
        echo "    uv not found, skipping"; \
    fi

# Auto-fix what can be auto-fixed.
fmt:
    just --unstable --fmt
    @command -v uv >/dev/null 2>&1 && uvx ruff format tests/ || true

# --- build -------------------------------------------------------------------

# Build the OS image rootlessly and tag it latest + <date> + <version>.
build:
    @echo "==> building {{ image_ref }} from {{ base_image }}:{{ base_tag }}"
    podman build \
        --build-arg BASE_IMAGE="{{ base_image }}" \
        --build-arg BASE_TAG="{{ base_tag }}" \
        --build-arg KIDNIX_VERSION="{{ version }}" \
        --build-arg KIDNIX_PRETTY_VERSION="{{ version }}-{{ date_tag }}" \
        --tag "{{ image_ref }}" \
        --tag "{{ registry }}/{{ image }}:{{ date_tag }}" \
        --tag "{{ registry }}/{{ image }}:{{ version }}" \
        -f Containerfile .
    @just _image-size

_image-size:
    @printf '==> image size: %s\n' "$(podman image inspect {{ image_ref }} --format '{{{{ .Size }}' | numfmt --to=iec)"

# --- test --------------------------------------------------------------------

# Assert the built image contains what it should (rootless, no VM needed).
#
# Each runs in its own throwaway container so one script cannot leave state
# behind for the next. Adding a test file is the whole of "adding a test" --
# there is no list to keep in sync. A FILTER argument matches by substring.
# Run every tests/image/test_*.sh inside the built image (rootless, ~2s).
test-image *FILTER: _require-image
    @echo "==> test-image"
    @cd "{{ justfile_directory() }}/tests/image"; \
    shopt -s nullglob; \
    scripts=(test_*{{ FILTER }}*.sh); \
    if (( ${#scripts[@]} == 0 )); then \
        echo "error: no tests/image/test_*{{ FILTER }}*.sh to run" >&2; exit 1; \
    fi; \
    failed=(); \
    for script in "${scripts[@]}"; do \
        printf '\n\033[1m--- %s ---\033[0m\n' "$script"; \
        podman run --rm \
            -v "{{ justfile_directory() }}/tests/image:/tests:ro,z" \
            --entrypoint /bin/bash \
            "{{ image_ref }}" "/tests/$script" || failed+=("$script"); \
    done; \
    printf '\n\033[1m==> %d/%d image test scripts passed\033[0m\n' \
        "$(( ${#scripts[@]} - ${#failed[@]} ))" "${#scripts[@]}"; \
    if (( ${#failed[@]} )); then \
        printf '    failed: %s\n' "${failed[*]}" >&2; exit 1; \
    fi

# Re-run bootc's own image lint against the built image.
lint-image: _require-image
    podman run --rm --entrypoint /usr/sbin/bootc "{{ image_ref }}" container lint

_require-image:
    @podman image exists "{{ image_ref }}" || { \
        echo "error: {{ image_ref }} not found -- run 'just build' first" >&2; exit 1; }

# lint + build + test-image. What CI runs.
ci: lint build test-image

# --- bcvk: rootless VMs ------------------------------------------------------

# Why not a package: Homebrew has no bcvk formula (checked), and the host is
# Bluefin, where `rpm-ostree install` means a reboot for a dev tool. The
# upstream release ships a static-ish x86_64 binary plus a .sha256, which is
# the reproducible option that needs no privileges at all.
# Install bcvk (rootless VM driver) into ~/.local/bin, checksum-verified.
bcvk-install version=bcvk_version:
    @set -euo pipefail; \
    if command -v bcvk >/dev/null 2>&1; then \
        echo "==> bcvk already on PATH: $(command -v bcvk) ($(bcvk --version))"; \
        exit 0; \
    fi; \
    tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT; \
    base="https://github.com/bootc-dev/bcvk/releases/download/v{{ version }}"; \
    asset="bcvk-x86_64-unknown-linux-gnu.tar.gz"; \
    echo "==> downloading $asset v{{ version }}"; \
    curl -fsSL -o "$tmp/$asset" "$base/$asset"; \
    curl -fsSL -o "$tmp/$asset.sha256" "$base/$asset.sha256"; \
    ( cd "$tmp" && sha256sum -c "$asset.sha256" ); \
    tar -xzf "$tmp/$asset" -C "$tmp"; \
    install -D -m 0755 "$tmp/bcvk-x86_64-unknown-linux-gnu" "{{ bcvk_bin }}"; \
    echo "==> installed {{ bcvk_bin }} ($("{{ bcvk_bin }}" --version))"; \
    case ":$PATH:" in *":$HOME/.local/bin:"*) ;; \
        *) echo "    NOTE: add ~/.local/bin to PATH" ;; esac

_require-bcvk:
    @command -v bcvk >/dev/null 2>&1 || test -x "{{ bcvk_bin }}" || { \
        echo "error: bcvk not found -- run 'just bcvk-install'" >&2; exit 1; }

# No sudo, no disk image: bcvk exports the container's filesystem over virtiofs
# as the VM's root and boots its kernel directly. Ctrl-D destroys the VM.
#
# Headless by design -- bcvk runs QEMU with `-nographic`. For a window, use
# `just vm-graphical` (libvirt + SPICE) or `just vm` (qcow2 + qemu gtk).
# Boot the image as a throwaway VM and drop into a root shell (no sudo, headless).
vm-ephemeral *ARGS: _require-bcvk _require-image
    {{ bcvk }} ephemeral run-ssh \
        --memory {{ vm_ram_h }} --vcpus {{ vm_cpus }} \
        "{{ image_ref }}" {{ ARGS }}

# The CI shape:  just vm-exec 'systemctl is-active gdm'
#
# [positional-arguments] rather than `{{ CMD }}`: interpolating the command
# into the recipe body lets the *host* shell expand `$FOO` and `$(...)` before
# the VM ever sees them, which silently rewrites any script you pass. As `$*`
# the text travels through untouched, newlines included.
# Run one command inside a fresh ephemeral VM and exit with its status.
[positional-arguments]
vm-exec +CMD: _require-bcvk _require-image
    @{{ bcvk }} ephemeral run-ssh \
        --memory {{ vm_ram_h }} --vcpus {{ vm_cpus }} \
        "{{ image_ref }}" -- "$*"

alias vm-ssh-ephemeral := vm-exec

# List ephemeral VMs left behind by --keep or a crash.
vm-list: _require-bcvk
    {{ bcvk }} ephemeral ps

# --force: rm-all prompts otherwise, which hangs a CI job on closed stdin.
# Remove every ephemeral VM bcvk is holding.
vm-clean: _require-bcvk
    -{{ bcvk }} ephemeral rm-all --force

# A GRAPHICAL window onto the kiosk, rootless, via libvirt qemu:///session.
# bcvk installs the image to a libvirt volume, so this is a real disk boot
# (bootloader, composefs, the lot) unlike `vm-ephemeral`.
#
#   just vm-graphical            # create + start, SPICE console
#   virt-viewer --connect qemu:///session kidnix     # open the window
#   just vm-graphical-shot       # PNG of the framebuffer via virsh
#   just vm-graphical-rm         # destroy it
# Create a persistent libvirt VM with a SPICE console -- the graphical window.
vm-graphical name="kidnix" *ARGS: _require-bcvk _require-image
    @echo "==> creating libvirt domain '{{ name }}' (qemu:///session, no sudo)"
    {{ bcvk }} libvirt run --graphical-console \
        --name "{{ name }}" --memory {{ vm_ram_h }} \
        {{ ARGS }} "{{ image_ref }}"
    @echo "==> open the window with:  virt-viewer --connect qemu:///session {{ name }}"

# SSH into the libvirt VM (bcvk injected the key when it created the domain).
vm-graphical-ssh name="kidnix" *ARGS: _require-bcvk
    {{ bcvk }} libvirt ssh "{{ name }}" {{ ARGS }}

# The one screenshot path that works without a disk-image build -- see
# `just test-boot` for why the ephemeral VMs cannot be screenshotted.
# Screenshot the libvirt VM's framebuffer via virsh.
vm-graphical-shot name="kidnix":
    @mkdir -p "{{ output_dir }}"
    virsh --connect qemu:///session screenshot "{{ name }}" "{{ output_dir }}/{{ name }}.ppm"
    @echo "==> {{ output_dir }}/{{ name }}.ppm"

# Destroy the libvirt VM and its volume.
vm-graphical-rm name="kidnix": _require-bcvk
    -{{ bcvk }} libvirt rm "{{ name }}"

# --- boot tests --------------------------------------------------------------

# Boots the container image as a VM with bcvk and asserts the machine reached
# graphical.target with the kid Wayland session and gnome-kiosk actually running.
# THE boot test: boot the image with bcvk and assert the kiosk came up (~30s, no sudo).
test-boot *ARGS: _require-bcvk _require-image
    @mkdir -p "{{ output_dir }}"
    python3 tests/boot/bcvk_boot_test.py \
        --image "{{ image_ref }}" \
        --output-dir "{{ output_dir }}" \
        --memory {{ vm_ram_h }} --cpus {{ vm_cpus }} \
        --timeout 360 \
        {{ ARGS }}

# Costs nothing; run it on every PR so a typo in either script fails fast.
# Validate both boot harnesses without booting anything.
test-boot-dry:
    python3 -m py_compile tests/boot/bcvk_boot_test.py tests/boot/boot_test.py
    python3 tests/boot/bcvk_boot_test.py --dry-run --image "{{ image_ref }}"
    python3 tests/boot/boot_test.py --dry-run --qcow2 /nonexistent

# Exercises the bootloader, composefs root and first-boot units that
# `test-boot` cannot see. Needs a disk image first (`just build-qcow2-rootless`).
# Full-fidelity boot test against the real qcow2 (slower; the only one that screenshots).
test-boot-qcow2 *ARGS: _require-qcow2
    @mkdir -p "{{ output_dir }}"
    python3 tests/boot/boot_test.py \
        --qcow2 "{{ qcow2 }}" \
        --output-dir "{{ output_dir }}" \
        --ssh-port {{ vm_ssh_port }} \
        --memory {{ vm_ram }} --cpus {{ vm_cpus }} \
        {{ ARGS }}

# --- disk images -------------------------------------------------------------

# Build a bootable qcow2 WITHOUT sudo, using bcvk's in-VM installer.
#
# bcvk boots a helper VM that runs `bootc install to-disk` against a virtio
# disk, so nothing on the host needs privileges and the image is read straight
# out of rootless podman storage. This is the disk image you want for
# `just test-boot-qcow2` and `just vm`.
#
# What it does NOT do is apply disk_config/config.toml -- there is no blueprint
# support here, so the resulting image has no `parent` password and no SSH key.
# For an image a human will log into, use `just build-qcow2` below.
# Build a bootable qcow2 with NO sudo (bcvk to-disk). No blueprint customisations.
build-qcow2-rootless *ARGS: _require-bcvk _require-image
    @mkdir -p "{{ output_dir }}/qcow2"
    @rm -f "{{ qcow2 }}"
    @echo "==> building {{ qcow2 }} rootlessly (bcvk to-disk; several minutes)"
    {{ bcvk }} to-disk --format qcow2 --filesystem btrfs --disk-size 20G \
        --karg console=tty0 --karg console=ttyS0,115200n8 \
        {{ ARGS }} "{{ image_ref }}" "{{ qcow2 }}"
    @echo "==> {{ qcow2 }}"

# Render disk_config/config.toml.example with the host's SSH public key.
disk-config ssh_key="~/.ssh/id_ed25519.pub":
    @mkdir -p "{{ output_dir }}"
    @key_path="$(eval echo {{ ssh_key }})"; \
    if [[ ! -f "$key_path" ]]; then \
        echo "error: no SSH public key at $key_path" >&2; \
        echo "       generate one with: ssh-keygen -t ed25519" >&2; exit 1; \
    fi; \
    KIDNIX_SSH_KEY="$(cat "$key_path")" \
        envsubst '$KIDNIX_SSH_KEY' < disk_config/config.toml.example > "{{ disk_config }}"; \
    echo "==> wrote {{ disk_config }} (gitignored; embeds $key_path)"

_sudo-warning kind:
    @echo ""
    @echo "  ┌─────────────────────────────────────────────────────────────────┐"
    @echo "  │ This step needs ROOTFUL podman and will prompt for your sudo    │"
    @echo "  │ password. Everything else in this Justfile is rootless --       │"
    @echo "  │ 'just build-qcow2-rootless' builds a bootable disk with none.   │"
    @echo "  │ Building: {{ kind }}"
    @echo "  └─────────────────────────────────────────────────────────────────┘"
    @echo ""

# Copy the rootless image into rootful storage so the disk builder can see it.
# The builder runs as root and reads /var/lib/containers/storage, which
# rootless podman does NOT write to -- this is the step everyone trips over.
#
# `podman save | sudo podman load` rather than the tidier `podman image scp`:
# scp needs working SSH to root@localhost, which GitHub runners do not have.
# The pipe streams (no temp file) and works identically everywhere.
#
# The copy is skipped only when the image IDs match exactly -- comparing by tag
# would happily build a disk from a stale image after a rebuild.
_stage-rootful: _require-image
    @local_id="$(podman image inspect "{{ image_ref }}" --format '{{{{ .Id }}')"; \
    root_id="$(sudo podman image inspect "{{ image_ref }}" --format '{{{{ .Id }}' 2>/dev/null || true)"; \
    if [[ "$local_id" == "$root_id" ]]; then \
        echo "==> {{ image_ref }} already staged in rootful storage (${local_id:7:12})"; \
    else \
        echo "==> copying {{ image_ref }} into rootful storage (streams ~7GB, takes a minute)"; \
        podman save "{{ image_ref }}" | sudo podman load; \
    fi

# Build a customised bootable qcow2 with osbuild's image-builder (needs sudo).
#
# Unlike build-qcow2-rootless this applies disk_config/config.toml, so the
# `parent` account gets a password and your SSH key.
# Build a customised bootable qcow2 with osbuild image-builder (needs sudo).
build-qcow2 *ARGS: (_sudo-warning "qcow2") disk-config _stage-rootful
    @mkdir -p "{{ output_dir }}"
    sudo podman run --rm --privileged --pull=newer \
        --security-opt label=type:unconfined_t \
        -v "{{ output_dir }}:/output" \
        -v /var/lib/containers/storage:/var/lib/containers/storage \
        -v "{{ disk_config }}:/config.toml:ro" \
        {{ ib_image }} \
        build qcow2 --output-dir /output \
        --bootc-ref "{{ image_ref }}" --bootc-default-fs btrfs \
        --blueprint /config.toml {{ ARGS }}
    sudo chown -R "$(id -u):$(id -g)" "{{ output_dir }}"
    @echo "==> look in {{ output_dir }} for the qcow2"

# Build an installable Anaconda ISO (needs sudo).
build-iso *ARGS: (_sudo-warning "anaconda-iso") disk-config _stage-rootful
    @mkdir -p "{{ output_dir }}"
    sudo podman run --rm --privileged --pull=newer \
        --security-opt label=type:unconfined_t \
        -v "{{ output_dir }}:/output" \
        -v /var/lib/containers/storage:/var/lib/containers/storage \
        -v "{{ disk_config }}:/config.toml:ro" \
        {{ ib_image }} \
        build anaconda-iso --output-dir /output \
        --bootc-ref "{{ image_ref }}" --bootc-default-fs btrfs \
        --blueprint /config.toml {{ ARGS }}
    sudo chown -R "$(id -u):$(id -g)" "{{ output_dir }}"

# Frozen since it was merged into osbuild/image-builder on 18 June 2026 (quay.io
# has had no push since that day). Use it only if `build-qcow2` regresses.
# Escape hatch: the archived bootc-image-builder (frozen 18 Jun 2026).
build-qcow2-bib *ARGS: (_sudo-warning "qcow2 (archived bootc-image-builder)") disk-config _stage-rootful
    @mkdir -p "{{ output_dir }}"
    sudo podman run --rm --privileged --pull=newer \
        --security-opt label=type:unconfined_t \
        -v "{{ output_dir }}:/output" \
        -v /var/lib/containers/storage:/var/lib/containers/storage \
        -v "{{ disk_config }}:/config.toml:ro" \
        {{ bib_image }} \
        --type qcow2 --rootfs btrfs --local {{ ARGS }} "{{ image_ref }}"
    sudo chown -R "$(id -u):$(id -g)" "{{ output_dir }}"
    @echo "==> {{ qcow2 }}"

# --- run ---------------------------------------------------------------------

_require-qcow2:
    @test -f "{{ qcow2 }}" || { \
        echo "error: {{ qcow2 }} not found -- run 'just build-qcow2-rootless'" >&2; exit 1; }

# Boot the qcow2 in a KVM window. -snapshot: the disk image stays pristine.
vm display="gtk": _require-qcow2
    @echo "==> booting {{ qcow2 }} (snapshot mode, ssh on localhost:{{ vm_ssh_port }})"
    qemu-system-x86_64 \
        -machine q35,accel=kvm -cpu host -smp {{ vm_cpus }} -m {{ vm_ram }} \
        -snapshot \
        -bios /usr/share/OVMF/OVMF_CODE.fd \
        -drive file="{{ qcow2 }}",if=virtio,format=qcow2 \
        -netdev user,id=net0,hostfwd=tcp::{{ vm_ssh_port }}-:22 \
        -device virtio-net-pci,netdev=net0 \
        -device virtio-vga-gl -display {{ display }},gl=on \
        -device virtio-rng-pci \
        -serial mon:stdio

# Same, but headless with the serial console on stdout.
vm-headless: _require-qcow2
    qemu-system-x86_64 \
        -machine q35,accel=kvm -cpu host -smp {{ vm_cpus }} -m {{ vm_ram }} \
        -snapshot -nographic \
        -bios /usr/share/OVMF/OVMF_CODE.fd \
        -drive file="{{ qcow2 }}",if=virtio,format=qcow2 \
        -netdev user,id=net0,hostfwd=tcp::{{ vm_ssh_port }}-:22 \
        -device virtio-net-pci,netdev=net0 \
        -device virtio-rng-pci \
        -serial mon:stdio

# SSH into a running `just vm` as the parent account.
vm-ssh *ARGS:
    ssh -p {{ vm_ssh_port }} \
        -o StrictHostKeyChecking=no \
        -o UserKnownHostsFile=/dev/null \
        -o LogLevel=ERROR \
        parent@localhost {{ ARGS }}
# --- fast "try the newest build" loop ----------------------------------------

# Start a throwaway OCI registry on :{{ local_registry_port }}.
registry:
    @if podman container exists kidnix-registry; then \
        podman start kidnix-registry >/dev/null; \
    else \
        podman run -d --name kidnix-registry -p {{ local_registry_port }}:5000 \
            docker.io/library/registry:2 >/dev/null; \
    fi
    @echo "==> registry listening on {{ local_registry }}"

registry-stop:
    -podman rm -f kidnix-registry

# Push the freshly built image to the local registry.
push-local: registry _require-image
    podman push --tls-verify=false \
        "{{ image_ref }}" "{{ local_registry }}/{{ image }}:{{ tag }}"
    @echo "==> pushed {{ local_registry }}/{{ image }}:{{ tag }}"

# Rebuild, push, and switch the RUNNING VM onto the new image. The whole point:
# a code change reaches a booted kidnix in one command, no disk rebuild.
#
# 10.0.2.2 is the QEMU user-networking alias for the host.
vm-upgrade: build push-local
    @echo "==> switching the running VM onto the new image"
    just vm-ssh "sudo bootc switch --transport registry \
        --enforce-container-sigpolicy=false \
        10.0.2.2:{{ local_registry_port }}/{{ image }}:{{ tag }}"
    @echo "==> reboot the VM to land on it:  just vm-ssh 'sudo systemctl reboot'"

# Pull the newest build of whatever the VM is already tracking.
vm-bootc-upgrade:
    just vm-ssh "sudo bootc upgrade"

# --- housekeeping ------------------------------------------------------------

# Remove build output and dangling images (keeps base-main and kidnix:latest).
clean:
    rm -rf "{{ output_dir }}"
    find . -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
    @# A qcow2 is 7 GB and an abandoned ephemeral VM pins a whole image layer
    @# stack; both are easy to leave behind and expensive to forget.
    -@{ command -v bcvk >/dev/null 2>&1 || test -x "{{ bcvk_bin }}"; } && {{ bcvk }} ephemeral rm-all --force 2>/dev/null || true
    podman image prune -f

# Also drop the kidnix images themselves.
clean-all: clean registry-stop
    -podman rmi -f "{{ image_ref }}" "{{ registry }}/{{ image }}:{{ date_tag }}" \
        "{{ registry }}/{{ image }}:{{ version }}"
