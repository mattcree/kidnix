# kidnix -- an immutable Linux for 4-8 year olds, built bootc/Universal Blue style.
#
# base-main is Universal Blue's *headless* Fedora Atomic base (no GNOME, no GDM).
# We add the GNOME kiosk plumbing ourselves rather than starting from
# silverblue-main, because a child never sees a full desktop and every package
# in the image is attack surface a parent has to trust. See docs/BUILDING.md.
#
# The tag is pinned to the Fedora major (44) rather than `latest`, so a new
# Fedora release is an explicit, reviewed bump instead of a surprise at 3am.
ARG BASE_IMAGE="ghcr.io/ublue-os/base-main"
ARG BASE_TAG="44"

FROM ${BASE_IMAGE}:${BASE_TAG}

ARG KIDNIX_VERSION="0.1.0"
ARG KIDNIX_PRETTY_VERSION="0.1.0"

# The overlay is copied to / verbatim; see system_files/ for the layout.
COPY system_files/ /

COPY build_files/ /tmp/build_files/

# The activity shell is a source tree, not a package: build_files/60-shell.sh
# installs it into the image's site-packages. .containerignore keeps the venv
# and the caches out of the build context.
COPY shell/ /tmp/shell/

# The parent panel is a second source tree, installed the same way by
# build_files/62-parent-panel.sh. It is separate from shell/ because it runs in
# a different session as a different user: the child's shell is on the kiosk,
# this is a libadwaita app on the parent's stock GNOME (ADR-0005).
COPY parent-panel/ /tmp/parent-panel/

# The build-time speech pre-renderer (build_files/66-prerender-speech.sh). It
# is a BUILD tool and ships nothing: it loads Kokoro-82M in a throwaway tree,
# writes ~4 MB of Ogg/Opus into /usr/share/kidnix/speech, and is deleted with
# the rest of /tmp before the layer commits. See docs/spikes/tts-prerender.md.
COPY tools/prerender/ /tmp/prerender/

# The first-party activities, for the same reason and by the same route:
# build_files/64-first-party-activities.sh copies `sounds_and_words` and its
# corpus into site-packages beside the SDK it is written against. Only the
# packages themselves travel -- .containerignore drops every venv and cache.
COPY activities/ /tmp/activities/

RUN --mount=type=cache,dst=/var/cache/libdnf5,sharing=locked \
    KIDNIX_VERSION="${KIDNIX_VERSION}" \
    KIDNIX_PRETTY_VERSION="${KIDNIX_PRETTY_VERSION}" \
    /tmp/build_files/build.sh && \
    rm -rf /tmp/build_files /tmp/shell /tmp/parent-panel /tmp/activities /tmp/prerender && \
    ostree container commit

# The cache mount above keeps /var/cache/libdnf5 busy for the whole of that
# RUN, so it cannot delete itself. Sweep it in a layer that has no mount.
RUN rm -rf /var/cache/* /var/tmp/* && rmdir /var/cache || true

# --- self-test hook: a deliberately unhealthy image (DEFAULT OFF) ------------
#
# "Cannot be broken" (AGENTS.md non-negotiable #8) rests on greenboot marking a
# bad deployment red and GRUB's boot_counter rolling it back. Proving that needs
# an image whose *required* health check fails on purpose, so `just test-rollback`
# builds one with:
#
#     podman build --build-arg KIDNIX_SELFTEST_BREAK_HEALTH=1 ...
#
# Every other build leaves the image untouched; tests/image/test_lockdown.sh
# asserts the file is absent, so a shipped image can never carry it.
#
# The ARG is declared HERE rather than at the top on purpose: a build argument
# only invalidates the cache from the line that first uses it, so the broken
# variant is a few hundred bytes stacked on the *same layers* as the shipped
# image -- which means a VM already running kidnix pulls one tiny layer instead
# of re-fetching ~7 GB. See docs/spikes/rollback.md.
ARG KIDNIX_SELFTEST_BREAK_HEALTH=""
RUN if [ "${KIDNIX_SELFTEST_BREAK_HEALTH}" = "1" ]; then \
        check=/usr/lib/greenboot/check/required.d/99-kidnix-selftest-broken.sh; \
        printf '%s\n' \
            '#!/usr/bin/bash' \
            '# SELF-TEST ONLY. Installed by --build-arg KIDNIX_SELFTEST_BREAK_HEALTH=1' \
            '# so tests/boot/rollback_test.py can prove a bad update rolls itself back.' \
            '# A required check that exits non-zero makes the boot RED.' \
            'echo "kidnix: SELFTEST broken required health check (deliberate)" >&2' \
            'exit 1' > "$check"; \
        chmod 0755 "$check"; \
        echo "WARNING: installed $check -- THIS IMAGE IS DELIBERATELY UNHEALTHY"; \
    fi

# Fails the build on bootc/OCI layout problems (writable /var content, missing
# kernel, bad /etc symlinks) that would otherwise only show up at install time.
RUN bootc container lint

LABEL org.opencontainers.image.title="kidnix"
LABEL org.opencontainers.image.description="An immutable, kid-safe Linux for 4-8 year olds"
LABEL org.opencontainers.image.source="https://github.com/mattcree/kidnix"
LABEL org.opencontainers.image.licenses="Apache-2.0"
LABEL org.opencontainers.image.version="${KIDNIX_VERSION}"
LABEL containers.bootc="1"
