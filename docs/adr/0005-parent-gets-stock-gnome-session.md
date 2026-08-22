# ADR-0005: The parent gets a stock GNOME session on the same login screen

- Status: accepted
- Date: 2026-08-22

## Context

ADR-0001/0003 put kidnix on the headless `base-main`, so the parent's
desktop is no longer free. Research is unambiguous that this matters: Sugar's
fatal wound was that adults could not use it (*04 "don't" #16*); Endless
concluded "95% of what we ship is GNOME OS" (*04*); GNOME 50 ships child
screen-time limits, bedtime schedules and a web-filter backend that kidnix
should consume rather than rebuild (*04 §5.4, 07 §2.3*). Alternatives: a
parent-panel-only kiosk session (smaller, but the parent can't fix wifi, add a
printer, or understand the machine), or admin from another device only.

## Decision

- `parent` (wheel) logs into a **stock GNOME Shell session** from the same
  GDM greeter (the `kid` account is autologin; the parent reaches GDM by
  logging the kid session out via the Grown-up gate, or from the greeter after
  a reboot/switch-user).
- The image installs `gnome-shell`, `gnome-session`, `gnome-control-center`,
  `nautilus`, `gnome-terminal`/`ptyxis`, `malcontent-control` and the
  minimal supporting set — not the full Silverblue payload. Measure the delta.
- The kidnix **parent panel** is a libadwaita app launched from that session
  (and later from the Grown-up gate inside the kid session). It owns
  kidnix-specific policy (children, activities, Ask queue, Journal browsing,
  updates) and defers to GNOME Settings → Parental Controls for what GNOME
  already does well (time limits, bedtime), recording policy in malcontent.

## Consequences

- Image grows (estimate +400–700 MB); acceptable for v0.1, measured in CI.
- The parent experience is familiar, documented, and maintained upstream.
- The kid session must still be unable to reach the parent session: GDM
  user-switch/greeter access is gated by the kiosk (no VT switch, no
  `gnome-kiosk` shortcuts) — see the lockdown spike.
