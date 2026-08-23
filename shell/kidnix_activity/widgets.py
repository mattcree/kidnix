"""The four widgets an activity is built from.

They are all :class:`kidnix_shell.widgets.ChildButton` underneath, which is
where SYNTHESIS section 2A's input rules live and where they stay:

* **A2** every mouse button does the same thing. No double-click, no
  right-click, no long-press, no scroll, no modifiers.
* **A3** the affordance fires on *press*, and eight clicks a second produce one
  action rather than eight (a 150 ms debounce, not a queue).
* **B4** icon + label + audio, always. Every control carries ``speak_text``,
  speaks it on hover dwell, on focus and on activation, and exposes the same
  string as its accessible name -- which is also what the tests assert on.

Inheriting rather than re-implementing is the whole point: an activity cannot
accidentally ship a control that double-fires, because there is no code path
here that could.

What is added on top is size. Everything comes from
:class:`~kidnix_activity.metrics.ContentArea`, so a control is 20 mm of real
panel on every monitor kidnix ships for, and a label is never under 18 pt.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # noqa: E402

from kidnix_shell.labels import LabelFit  # noqa: E402
from kidnix_shell.widgets import (  # noqa: E402
    ChildButton,
    SpeechUI,
    fit_gtk_label,
    icon_image,
    next_key,
)

from .metrics import BIG_BUTTON_MM, PICTURE_TILE_MM, ContentArea  # noqa: E402
from .speech import ActivitySpeech  # noqa: E402

__all__ = ["BigButton", "GrownUpTurn", "PictureTile", "Prompt"]

#: What the replay control says when it is focused or hovered. The Ear in the
#: band says the same thing about the shell's own last line; this one is about
#: the prompt it sits next to, which is a different sentence and a different
#: button, deliberately: a child should not have to work out whose voice the
#: Ear is repeating.
REPLAY_SPEAK = "Say it again."
#: The icon on the replay control. Falls back to the shell's bundled set, then
#: to the icon theme, then to nothing visible -- but the accessible name and
#: the spoken string are always there.
REPLAY_ICON = "kidnix-ear"

#: The grown-up card's own words, when the activity does not give its own.
GROWNUP_TITLE = "Your turn, grown-up"
GROWNUP_DONE = "Done"


def _ui(speech: ActivitySpeech | None, speech_ui: SpeechUI | None) -> SpeechUI | None:
    """The one widget bridge: the caller's, else the voice's, else none."""
    if speech_ui is not None:
        return speech_ui
    return speech.ui if speech is not None else None


class BigButton(ChildButton):
    """The primary control: a picture, a word under it, and a sentence in the ear.

    40 mm square by preference (ADR-0011's primary target), never under 20 mm,
    with the label fitted rather than ellipsised -- ``fit_gtk_label`` steps the
    point size down to the 18 pt floor and then adds a line, and cuts nothing,
    ever. A pre-reader who cannot read "Go" can still see the arrow and still
    hears the sentence.
    """

    def __init__(
        self,
        label: str,
        icon: str = "",
        speak_text: str = "",
        *,
        on_activate: Callable[[], None] | None = None,
        speech: ActivitySpeech | None = None,
        speech_ui: SpeechUI | None = None,
        area: ContentArea | None = None,
        icon_kind: str = "icon-name",
        size_mm: float = BIG_BUTTON_MM,
        css_classes: tuple[str, ...] = (),
        key: str | None = None,
    ) -> None:
        self.area = area
        size = area.target(size_mm) if area is not None else None
        super().__init__(
            speak_text=speak_text or label,
            on_activate=on_activate,
            speech_ui=_ui(speech, speech_ui),
            css_classes=("big", *css_classes),
            key=key or next_key("big"),
            size=size,
        )
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_valign(Gtk.Align.CENTER)
        box.set_halign(Gtk.Align.CENTER)

        self.icon_image: Gtk.Image | None = None
        if icon:
            # Half the button, which leaves the label room without letting the
            # picture become a decoration. ADR-0011's 45% floor is about a
            # *tile* whose label box is reserved; a big button's label is one
            # short word, so a straight half is the honest split.
            pixels = max(24, int((size or 96) * 0.5))
            self.icon_image = icon_image(icon, icon_kind, pixels)
            box.append(self.icon_image)

        self.label = Gtk.Label()
        self.label.add_css_class("big-button-label")
        self.fit: LabelFit | None = None
        if label:
            width = max(24, (size or 160) - 24)
            self.fit = fit_gtk_label(
                self.label,
                label,
                width=width,
                base_pt=area.points(24.0) if area is not None else 24.0,
                floor_pt=area.points(18.0) if area is not None else 18.0,
                max_lines=2,
            )
            box.append(self.label)
        self.set_child(box)


class PictureTile(ChildButton):
    """One picture among several to choose between.

    A file, not an icon name: a picture tile shows the child's own work, a
    photograph or an authored image, which is never in the icon theme. 30 mm by
    preference, and a target like everything else -- the picture *is* the
    control, so the whole of it is pressable.
    """

    def __init__(
        self,
        picture: Path | str,
        speak_text: str,
        *,
        label: str = "",
        on_activate: Callable[[], None] | None = None,
        speech: ActivitySpeech | None = None,
        speech_ui: SpeechUI | None = None,
        area: ContentArea | None = None,
        size_mm: float = PICTURE_TILE_MM,
        css_classes: tuple[str, ...] = (),
        key: str | None = None,
    ) -> None:
        self.area = area
        self.path = Path(picture)
        size = area.target(size_mm) if area is not None else None
        super().__init__(
            speak_text=speak_text,
            on_activate=on_activate,
            speech_ui=_ui(speech, speech_ui),
            css_classes=("picture-tile", *css_classes),
            key=key or next_key("picture"),
            size=size,
        )

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_valign(Gtk.Align.CENTER)
        box.set_halign(Gtk.Align.CENTER)

        self.picture = Gtk.Picture()
        self.picture.add_css_class("picture-frame")
        self.picture.set_can_shrink(True)
        self.picture.set_content_fit(Gtk.ContentFit.CONTAIN)
        if self.path.is_file():
            self.picture.set_filename(str(self.path))
        inner = max(24, int((size or 120) * (0.62 if label else 0.86)))
        self.picture.set_size_request(inner, inner)
        box.append(self.picture)

        self.label: Gtk.Label | None = None
        if label:
            self.label = Gtk.Label()
            self.label.add_css_class("big-button-label")
            fit_gtk_label(
                self.label,
                label,
                width=max(24, (size or 120) - 20),
                base_pt=area.points(20.0) if area is not None else 20.0,
                floor_pt=area.points(18.0) if area is not None else 18.0,
                max_lines=2,
            )
            box.append(self.label)
        self.set_child(box)


class Prompt(Gtk.Box):
    """A spoken instruction, written down, with a way to hear it again.

    The activity's equivalent of the shell's Ear, and it exists for the same
    reason: a child who missed the sentence must be able to get it back without
    asking anybody, and a child who cannot hear it must be able to read it.
    B2's rule -- *nothing essential is audio-only* -- applies to the sentence
    that tells a child what to do more than to any other line in the product.

    :meth:`say` speaks it. The replay button re-speaks **this** prompt rather
    than the last thing said, which is not the same thing as soon as the
    activity has said anything else in between.
    """

    def __init__(
        self,
        text: str,
        *,
        speech: ActivitySpeech | None = None,
        speech_ui: SpeechUI | None = None,
        area: ContentArea | None = None,
        on_replay: Callable[[], None] | None = None,
        replay: bool = True,
        css_classes: tuple[str, ...] = (),
    ) -> None:
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL)
        self.area = area
        self.speech = speech
        self.text = " ".join((text or "").split())
        self.set_spacing(area.gap if area is not None else 12)
        for css in ("prompt", *css_classes):
            self.add_css_class(css)

        self.label = Gtk.Label()
        self.label.add_css_class("prompt-line")
        self.label.set_hexpand(True)
        self.label.set_xalign(0.0)
        points = area.prompt_points if area is not None else 26.0
        floor = area.points(18.0) if area is not None else 18.0
        width = area.width - (area.gap * 4) if area is not None and area.known else 0
        self.fit = fit_gtk_label(
            self.label,
            self.text,
            width=width if width > 0 else 800,
            base_pt=points,
            floor_pt=floor,
            max_lines=3,
        )
        self.append(self.label)

        self.replay: ChildButton | None = None
        if replay:
            self.replay = ChildButton(
                speak_text=REPLAY_SPEAK,
                on_activate=on_replay or self._replay,
                speech_ui=_ui(speech, speech_ui),
                css_classes=("replay",),
                key=next_key("replay"),
                size=area.min_target if area is not None else None,
            )
            self.replay.set_child(
                icon_image(
                    REPLAY_ICON, "icon-name", max(24, int((area.min_target if area else 48) * 0.6))
                )
            )
            self.replay.set_valign(Gtk.Align.CENTER)
            self.append(self.replay)

    def say(self) -> bool:
        """Speak the prompt. Also emits the caption, like every other line."""
        if self.speech is None:
            return False
        return self.speech.speak(self.text)

    def _replay(self) -> None:
        """What the replay button calls. Whether the voice was there is not
        the button's business -- a control that reported failure to a child
        would be reporting something they cannot act on."""
        self.say()

    def set_text(self, text: str) -> None:
        """Change what the prompt says. Does **not** speak it -- the activity
        decides when a child is interrupted."""
        self.text = " ".join((text or "").split())
        points = self.area.prompt_points if self.area is not None else 26.0
        floor = self.area.points(18.0) if self.area is not None else 18.0
        width = (
            self.area.width - (self.area.gap * 4)
            if self.area is not None and self.area.known
            else 0
        )
        self.fit = fit_gtk_label(
            self.label,
            self.text,
            width=width if width > 0 else 800,
            base_pt=points,
            floor_pt=floor,
            max_lines=3,
        )


class GrownUpTurn(Gtk.Box):
    """ "Your turn, grown-up" -- the co-use affordance (SUITE section 3).

    The evidence behind the whole literacy vertical is that the adult is the
    active ingredient: GraphoGame's meta-analysis is g = -0.02 overall and
    **0.48** with high adult interaction. So every loop has a moment that is
    addressed to the grown-up, and this is what it looks like.

    It is deliberately the **least child-like object on the screen**: adult
    typography, adult density, a dimmed ground and a rule down the leading edge.
    A four-year-old who cannot read a word of it can still see that this block
    is not for them, which is what stops it from being one more thing to press.

    It is **not** a dialogue and it is **not** modal: it never covers the
    child's work, it takes no keyboard focus away, and if nobody ever presses
    ``Done`` the activity carries on. An adult who has walked away must not be
    able to strand a child in front of a locked screen.
    """

    def __init__(
        self,
        body: str,
        *,
        title: str = GROWNUP_TITLE,
        done_label: str = GROWNUP_DONE,
        on_done: Callable[[], None] | None = None,
        speech: ActivitySpeech | None = None,
        speech_ui: SpeechUI | None = None,
        area: ContentArea | None = None,
    ) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.area = area
        self.speech = speech
        self.title_text = " ".join((title or "").split())
        self.body_text = " ".join((body or "").split())
        self.set_spacing(8)
        self.add_css_class("grownup-turn")

        self.title = Gtk.Label(label=self.title_text)
        self.title.add_css_class("title")
        self.title.set_xalign(0.0)
        self.title.set_wrap(True)
        self.append(self.title)

        self.body = Gtk.Label(label=self.body_text)
        self.body.add_css_class("body")
        self.body.set_xalign(0.0)
        self.body.set_wrap(True)
        self.append(self.body)

        self.done: ChildButton | None = None
        if on_done is not None:
            # An *adult's* control: 08 section 3.1e's 9 mm rather than the
            # child's 20, and quiet, because being unenticing is the point
            # (08 section 4.5). It is still a ChildButton, so it still fires on
            # press and still cannot double-fire.
            self.done = ChildButton(
                speak_text=done_label,
                on_activate=on_done,
                speech_ui=_ui(speech, speech_ui),
                key=next_key("grownup-done"),
                height=area.mm_floor(9.0) if area is not None else None,
            )
            self.done.set_child(Gtk.Label(label=done_label))
            self.done.set_halign(Gtk.Align.END)
            self.append(self.done)

    def announce(self) -> bool:
        """Say the card out loud, once, when it appears.

        The child is told *whose turn it is* -- that is information they need
        and cannot read. What the grown-up is being asked to do is on the card,
        for the grown-up, and is not read to a five-year-old.
        """
        if self.speech is None:
            return False
        return self.speech.speak(self.title_text)
