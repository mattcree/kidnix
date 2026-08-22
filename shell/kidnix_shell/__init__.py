"""kidnix activity shell.

The full-screen surface a child sees. See docs/design/shell-v0.1.md.

Module map:

  Pure logic (no GTK, unit-tested headless)
    metrics     mm <-> px, DPI-aware sizing
    activities  activity manifest loading/validation (spec section 4)
    journal     the Journal storage contract (spec section 5)
    session     session timing and policy (spec section 6)
    state       the shell state machine (spec section 2)
    speech      read-aloud queue and backends (spec section 3)
    launcher    activity subprocess lifecycle (spec section 2, S3)
    settings    XDG paths, parent config, PIN hashing, profiles

  GTK
    app         Adw.Application, window, wiring
    band        the persistent 96 px band and the sun
    widgets     shared child-facing widgets (speaking button, tile, card)
    screens/*   S1-S9
    demo        --demo fake activities
"""

__version__ = "0.1.0"
