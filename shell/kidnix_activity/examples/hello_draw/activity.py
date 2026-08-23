"""hello_draw: one button, one square, one Journal entry.

The window, and only the window. Everything the activity *knows* is in
:mod:`~kidnix_activity.examples.hello_draw.logic`, which imports no GTK and is
tested headless -- that split is the first thing to copy out of this example.

Note what is **not** here: no score, no stars, no streak, no "well done!", no
level, no timer, and no dialogue on the way out. SUITE section 5 says no reward
economy, and an example that shipped one would teach it to every activity that
was copied from it.
"""

from __future__ import annotations

import logging

from kidnix_activity.app import ActivityApplication, ActivityWindow
from kidnix_activity.journal import JournalError
from kidnix_activity.widgets import BigButton, GrownUpTurn, Prompt

from . import ACTIVITY_ID, TITLE
from .logic import (
    BUTTON_LABEL,
    BUTTON_SPEAK,
    GROWNUP_BODY,
    LOST_LINE,
    PROMPT,
    HelloDraw,
    make_and_keep,
)

log = logging.getLogger(__name__)


def build(window: ActivityWindow, state: HelloDraw, app: ActivityApplication) -> None:
    """Fill the window. Three widgets, all of them from the SDK."""
    area = window.area
    prompt = Prompt(PROMPT, speech=window.speech, area=area)
    window.add(prompt)

    def pressed() -> None:
        try:
            entry, caption = make_and_keep(state, app.save_entry)
        except JournalError as exc:
            # The one failure that is not survivable is losing the child's
            # work, so it is said out loud in the child's words and put in the
            # parent's journal in ours (SYNTHESIS C3).
            log.error("could not keep the square: %s", exc)
            window.speak(LOST_LINE)
            return
        log.info("kept %s", entry.id)
        prompt.set_text(f"{caption}. Press again for another.")
        window.speak(f"{caption}. It is in My Things.")

    window.add(
        BigButton(
            BUTTON_LABEL,
            speak_text=BUTTON_SPEAK,
            on_activate=pressed,
            speech=window.speech,
            area=area,
        )
    )
    window.add(GrownUpTurn(GROWNUP_BODY, speech=window.speech, area=area))
    window.speak(PROMPT)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    state = HelloDraw()
    app = ActivityApplication(ACTIVITY_ID, TITLE)
    app.set_build(lambda window: build(window, state, app))
    # SIGTERM: every square is kept the moment it is made, so there is nothing
    # left to write. Said out loud in a log line rather than left as an empty
    # function, because "there is nothing to save" is a claim, and a claim
    # should be visible.
    app.set_on_finish(lambda: log.info("finishing: %d square(s) already kept", state.made))
    return app.run(argv)
