# Letters — a picture, a few words and your voice, for somebody real

`docs/research/05-learning-science.md` §3 calls this, on balance, **the
strongest activity in the kidnix list**, and gives the reason in one line:
*purpose and audience are the EEF's named mechanism*. A five-year-old writes
because somebody they love is going to read it.

    Who for?  →  Make it  →  Post it            (+ Letters for you)

- **A real, named recipient** from the `[[family]]` blocks a grown-up wrote in
  the parent panel. A photo and a name; **never an address** — there is no
  address field anywhere in this package.
- **Picture + caption + voice.** The picture is the only required part: a
  drawing from the Journal or a quick scribble. The words are the child's own,
  or a grown-up's, or none. The voice is the shell's own twenty-second note.
- **No spelling correction.** Invented spelling *is* the Year 1 curriculum. The
  caption is never stripped, cased, checked or shortened — byte for byte from
  the box to `caption.txt`, to the rendered card, to the outbox.
- **Nothing leaves the machine.** The child session has no egress (SYNTHESIS
  H1). The letter is written to `/var/lib/kidnix/outbox/<profile>/` marked
  *waiting for a grown-up to send*, and a grown-up carries it.
- **The reply comes back.** A grown-up drops what came back into
  `/var/lib/kidnix/inbox/<profile>/`; the **Letters for you** shelf shows it and
  plays it. Importing a reply into the Journal is the documented follow-up.

The design note, the data contracts and what is deliberately not built yet are
in [`docs/design/letters-to-family.md`](../../docs/design/letters-to-family.md).

## What is where

| | |
|---|---|
| `recipients.py` | the `[[family]]` list, from `/etc/kidnix/parent.toml` |
| `letter.py` | what a letter is; the caption rule; the two statuses |
| `scribble.py` | the quick drawing: three colours, one undo |
| `draw.py` | cairo: the placeholder face, the scribble, the letter card |
| `journal_read.py` | a minimal **read-only** reader of the child's Journal |
| `mailbox.py` | the outbox and the inbox |
| `assemble.py` | posting: Journal first, outbox second |
| `words.py` | every spoken line |
| `keys.py` | the keyboard, and where the SDK's focus ring stands aside |
| `env.py` | `KIDNIX_SPEECH=off` — one switch, voice *and* earcons |
| `activity.py` | the window (the only module that imports GTK) |

## Working on it

```bash
just setup            # venv with --system-site-packages
just test-headless    # the CI floor: no display, no SDK needed
just test-gtk         # under Broadway, never on your desktop
just lint validate
just run              # Broadway again; Ctrl-C runs the save
just screenshots
```

`just ci` is what CI runs.

**Never open a window on the developer's desktop** — `just run`, `just test-gtk`
and `just screenshots` all start their own `gtk4-broadwayd`
(AGENTS.md; `docs/design/activity-sdk.md` §10).

**Never make a sound on the developer's machine** (AGENTS.md §5). Every recipe
exports `KIDNIX_SPEECH=off`, and this activity reads it for the **earcons** as
well as the voice — they are a separate audio path and the host's speakers do
not care which of the two woke them up. `tests/conftest.py` sets it for every
test in the package.
