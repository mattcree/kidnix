# ADR-0004: The activity shell is GTK4 + libadwaita in Python (PyGObject)

- Status: accepted (revisit trigger below)
- Date: 2026-08-22

## Context

The shell is a full-screen, pre-reader UI: big tiles, a persistent band,
read-aloud on focus/hover, a Journal grid, a sun/timer, spatial transitions,
and it must launch and foreground other programs under gnome-kiosk. Options
evaluated in *07 §2.6*: GTK4/libadwaita (Python, Rust, Vala), Qt/QML, a web
shell (WebKitGTK / Chromium kiosk / Tauri), Flutter, Godot.

## Decision

GTK4 + libadwaita via PyGObject, running as the gnome-kiosk session's single
always-present window. Rationale:
- Native Wayland, native XDG portals, D-Bus integration with logind/
  AccountsService/malcontent, `python3-speechd` for TTS — no bridging layer.
- AT-SPI accessibility tree for free → testable (and usable by switch access
  later).
- Smallest image delta (GTK4/libadwaita/Python are already in the image);
  fastest iteration for Opus implementers; pytest-friendly.
- libadwaita's animation vocabulary (AdwSpringAnimation, AdwCarousel,
  AdwNavigationView transitions, custom GskRenderNode drawing) is enough for
  tile-scale spatial motion; the BBC-GEL "see the journey" transitions do not
  require a game engine.

Runner-up: a WebKitGTK-hosted web shell (Playwright testability, richer
motion). Revisit trigger: if the child tests in M2 show the UI needs motion
or rendering GTK can't give, or if AT-SPI in a kiosk session proves unusable
for test automation and QMP+ydotool is insufficient.

## Consequences

- Repo gets `shell/` (Python package `kidnix_shell`, GTK4/Adw, `uv`, ruff,
  mypy, pytest); installed into the image as an RPM-less tree under
  `/usr/lib/kidnix/` with a launcher, or packaged later.
- Tests: unit tests headless (GTK under `GDK_BACKEND=broadway`/offscreen or
  mocked), integration via bcvk VM + QMP screendump + ydotool.
- Activities remain separate processes (RPM/Flatpak); the shell is a launcher,
  Journal and session manager, not a host for activity code.
