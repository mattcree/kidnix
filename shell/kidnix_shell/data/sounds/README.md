# Earcons

08-shell-ux-patterns section 3.6 specifies a six-sound set, each <= 400 ms,
distinguished by pitch contour rather than timbre so they survive cheap
laptop speakers:

| Event | Character | File (TODO) |
|---|---|---|
| Focus / hover a tile | very quiet single rising note | `focus.ogg` |
| Commit / open | two-note rising, brighter | `open.ogg` |
| Back / close | two-note falling | `back.ogg` |
| Kept in the Journal | soft click-chime, the only bell | `keep.ogg` |
| Ask sent | warm, longer -- this must feel like an event | `ask.ogg` |
| Session phase change | one three-note motif, a tone lower each phase | `phase.ogg` |

**Not shipped in v0.1.** These need composing, not generating: a synthesised
sine-pair is worse than silence for a sound a child hears two hundred times a
day, and the licensing ledger (`docs/LICENSES.md`, SYNTHESIS H5) wants a real
provenance entry per file rather than "Claude made it with numpy".

`kidnix_shell.sound.Earcons` already has the call sites and the volume/duck
policy; it is a no-op until these files exist, and logs once at debug level.
Rules that apply when they land: never more than one earcon per 250 ms, and
earcons duck under speech.
