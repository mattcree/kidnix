"""The one development switch this activity reads, and why it is not two.

``KIDNIX_SPEECH=off`` is the rule in AGENTS.md section 5: **never make a sound
on a developer's machine.** ``kidnix_shell.speech`` already honours it and hands
back a null voice, so a shell or an activity run from a terminal is silent.

The **earcons are a second audio path** -- ``kidnix_shell.sound.Earcons`` builds
a GStreamer pipeline straight to PipeWire -- and nothing in the SDK reads that
variable on their behalf. So a run with the voice off would still tap, chime and
"keep" through the speakers of the machine somebody is working on, which is the
same failure wearing a different hat. :func:`quiet` closes it: one variable,
both channels, read once in ``main()``.

Two things this is **not**:

* It is not the child's volume control. Mute, volume and calm mode's shorter
  earcon set are ``[access]`` in the root-owned ``parent.toml``, they are applied
  by the SDK, and they are a parent's settings rather than a developer's.
* It is not read on a real machine. A kiosk session never sets
  ``KIDNIX_SPEECH``, so :func:`quiet` is False there and the activity has its
  ordinary voice and its ordinary sounds.

It lives in its own module, with no GTK and no cairo in it, so the test that
pins it is part of the headless floor -- which matters here more than usual,
because the failure mode is somebody's speakers rather than a red test.
"""

from __future__ import annotations

import os

__all__ = ["QUIET_VALUES", "SPEECH_VAR", "quiet"]

#: The variable, spelled as ``kidnix_shell.speech`` spells it.
SPEECH_VAR = "KIDNIX_SPEECH"

#: What counts as "be quiet". The same set the shell reads, so one value means
#: one thing everywhere rather than "off" silencing the voice and "0" silencing
#: half of it.
QUIET_VALUES = frozenset({"off", "0", "false", "none", "null"})


def quiet(env: dict[str, str] | None = None) -> bool:
    """Is this run under orders not to make a sound?"""
    source = os.environ if env is None else env
    return source.get(SPEECH_VAR, "").strip().lower() in QUIET_VALUES
