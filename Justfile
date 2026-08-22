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

# VM settings.
vm_ram := "4096"
vm_cpus := "4"
vm_ssh_port := "2222"

# Containerised linters -- nothing is installed on the host.
shellcheck_image := "docker.io/koalaman/shellcheck:stable"
hadolint_image := "docker.io/hadolint/hadolint:latest-alpine"
yamllint_image := "docker.io/pipelinecomponents/yamllint:latest"
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
test-image: _require-image
    @echo "==> test-image"
    podman run --rm \
        -v "{{ justfile_directory() }}/tests/image:/tests:ro,z" \
        --entrypoint /bin/bash \
        "{{ image_ref }}" /tests/test_image.sh

# Re-run bootc's own image lint against the built image.
lint-image: _require-image
    podman run --rm --entrypoint /usr/sbin/bootc "{{ image_ref }}" container lint

_require-image:
    @podman image exists "{{ image_ref }}" || { \
        echo "error: {{ image_ref }} not found -- run 'just build' first" >&2; exit 1; }

# lint + build + test-image. What CI runs.
ci: lint build test-image

# --- disk images (THE ONLY RECIPES THAT NEED sudo) ---------------------------

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
    @echo "  │ password. It is the only part of the build that does.           │"
    @echo "  │ Building: {{ kind }}"
    @echo "  └─────────────────────────────────────────────────────────────────┘"
    @echo ""

# Copy the rootless image into rootful storage so bootc-image-builder can see
# it. bib runs as root and reads /var/lib/containers/storage, which rootless
# podman does NOT write to -- this is the step everyone trips over.
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
        echo "==> copying {{ image_ref }} into rootful storage (streams ~6GB, takes a minute)"; \
        podman save "{{ image_ref }}" | sudo podman load; \
    fi

# Build a bootable qcow2 (needs sudo).
build-qcow2 *ARGS: (_sudo-warning "qcow2") disk-config _stage-rootful
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

# Build an installable Anaconda ISO (needs sudo).
build-iso *ARGS: (_sudo-warning "anaconda-iso") disk-config _stage-rootful
    @mkdir -p "{{ output_dir }}"
    sudo podman run --rm --privileged --pull=newer \
        --security-opt label=type:unconfined_t \
        -v "{{ output_dir }}:/output" \
        -v /var/lib/containers/storage:/var/lib/containers/storage \
        -v "{{ disk_config }}:/config.toml:ro" \
        {{ bib_image }} \
        --type anaconda-iso --rootfs btrfs --local {{ ARGS }} "{{ image_ref }}"
    sudo chown -R "$(id -u):$(id -g)" "{{ output_dir }}"

# --- run ---------------------------------------------------------------------

_require-qcow2:
    @test -f "{{ qcow2 }}" || { \
        echo "error: {{ qcow2 }} not found -- run 'just build-qcow2' (needs sudo)" >&2; exit 1; }

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

# Headless boot test: boots the qcow2, waits for the readiness marker on the
# serial console, screenshots the framebuffer, exits non-zero on failure.
test-boot *ARGS: _require-qcow2
    @mkdir -p "{{ output_dir }}"
    python3 tests/boot/boot_test.py \
        --qcow2 "{{ qcow2 }}" \
        --output-dir "{{ output_dir }}" \
        --ssh-port {{ vm_ssh_port }} \
        --memory {{ vm_ram }} --cpus {{ vm_cpus }} \
        {{ ARGS }}

# Validate the boot test without any disk image (what CI-less dev boxes run).
test-boot-dry:
    python3 -m py_compile tests/boot/boot_test.py
    python3 tests/boot/boot_test.py --dry-run --qcow2 /nonexistent

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
    podman image prune -f

# Also drop the kidnix images themselves.
clean-all: clean registry-stop
    -podman rmi -f "{{ image_ref }}" "{{ registry }}/{{ image }}:{{ date_tag }}" \
        "{{ registry }}/{{ image }}:{{ version }}"
