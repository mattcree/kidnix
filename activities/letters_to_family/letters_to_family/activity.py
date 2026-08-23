"""The window: four screens, forwards, and a shelf off to one side.

    Who for?  ->  Make it  ->  Post it        (+ Letters for you)

That is the whole navigation. There is no menu, no tab bar, no back button of
our own (Back is the shell's, one screen up, in a fixed place -- SDK section
3.4) and no way to reach a screen out of order. B1's flat, spatially stable
layout for a pre-reader is the reason, and a five-year-old who has pressed
Grandad's face should be looking at pictures, not at choices.

Everything this module does that is worth proving is proved somewhere else:
:mod:`letters_to_family.recipients` knows who may be written to,
:mod:`letters_to_family.letter` knows what a letter is,
:mod:`letters_to_family.mailbox` knows where it goes,
:mod:`letters_to_family.keys` knows what a key means, and
:mod:`letters_to_family.draw` draws every picture without a display. What is
here is the wiring, and ``tests/test_gtk_smoke.py`` walks it under Broadway.

Three things in here are worth reading before changing anything:

**The caption box turns the SDK's focus ring off while it has the caret.**
``ActivityKeyboard`` consumes Space to press the focused control, which on a
screen with a text box would mean a caption with no spaces in it.
:func:`letters_to_family.keys.guard_ring` is the exception, and Tab still walks
the ring so there is always a way out (A6).

**The voice note is the shell's own** (``kidnix_shell.voice.VoiceNote``): one
press starts, a second stops, twenty seconds stops it anyway, a level meter
while it runs, and **the button is simply not there when there is no
microphone** -- a mic button that does nothing teaches a child that buttons lie.

**Put-away keeps the work and posts nothing.** ``on_finish`` writes the Journal
entry with :data:`~letters_to_family.letter.STATUS_UNPOSTED` and no outbox copy.
A grown-up must not find something in the folder they send things out of that
nobody asked them to send.
"""

from __future__ import annotations

import argparse
import logging
from collections.abc import Callable, Sequence
from datetime import datetime
from pathlib import Path
from tempfile import mkdtemp

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # noqa: E402
from kidnix_activity.app import ActivityApplication, ActivityWindow  # noqa: E402
from kidnix_activity.journal import save_entry  # noqa: E402
from kidnix_activity.widgets import BigButton, GrownUpTurn, PictureTile, Prompt  # noqa: E402
from kidnix_shell.sound import KEEP, TAP, Earcons  # noqa: E402
from kidnix_shell.voice import MAX_SECONDS, VoiceNote  # noqa: E402

from . import ACTIVITY_ID, TITLE, draw, words  # noqa: E402
from .assemble import post_letter  # noqa: E402
from .env import quiet  # noqa: E402
from .journal_read import recent_pictures  # noqa: E402
from .keys import guard_ring  # noqa: E402
from .letter import (  # noqa: E402
    STATUS_UNPOSTED,
    CaptionSource,
    Letter,
    PictureSource,
    Step,
)
from .mailbox import Reply, inbox_replies  # noqa: E402
from .recipients import Recipient, load_recipients  # noqa: E402
from .scribble import COLOURS, Colour, Scribble  # noqa: E402

log = logging.getLogger(__name__)

__all__ = ["LettersActivity", "ScribbleCanvas", "main"]

#: Where this activity's own stylesheet lives. Loaded third, after the shell's
#: and the SDK's, and it only adds (see the file's own header).
ACTIVITY_CSS = Path(__file__).parent / "activity.css"

#: How many of the child's own recent pictures are offered. Four, plus "draw
#: one" -- five controls, which is B2's ceiling for a choice screen.
JOURNAL_PICTURES = 4

#: The scribble canvas, in millimetres of real panel. Big enough to draw on
#: with a finger and small enough to leave the crayons and the prompt on screen.
CANVAS_MM = 90.0


# -- the canvas --------------------------------------------------------------


class ScribbleCanvas(Gtk.DrawingArea):
    """Press to draw. Three colours, one undo, and no tool modes.

    The model is :class:`letters_to_family.scribble.Scribble` and the points it
    holds are 0..1 of the canvas, so what is drawn at 320 px renders identically
    onto a 720 px letter card. The gesture is a plain ``Gtk.GestureDrag`` --
    press, move, release -- which is the one place in the product a drag is the
    right verb (A5: drags are short and have a state cue; the cue here is the
    line appearing under the finger).
    """

    def __init__(self, scribble: Scribble, width: int, height: int) -> None:
        super().__init__()
        self.scribble = scribble
        self.add_css_class("scribble-canvas")
        self.set_size_request(width, height)
        self.set_hexpand(True)
        self.set_vexpand(True)
        self.set_draw_func(self._on_draw)
        #: Called after every change, so the screen can enable "That's it".
        self.on_changed: Callable[[], None] | None = None

        drag = Gtk.GestureDrag.new()
        drag.set_button(0)  # every button does the same thing (A2)
        drag.connect("drag-begin", self._on_begin)
        drag.connect("drag-update", self._on_update)
        drag.connect("drag-end", self._on_end)
        self.add_controller(drag)
        self._origin = (0.0, 0.0)

    # -- input --

    def _normalise(self, x: float, y: float) -> tuple[float, float]:
        width = max(1, self.get_width() or self.get_size_request()[0] or 1)
        height = max(1, self.get_height() or self.get_size_request()[1] or 1)
        return x / width, y / height

    def _on_begin(self, _gesture: Gtk.GestureDrag, x: float, y: float) -> None:
        self._origin = (x, y)
        self.scribble.start(*self._normalise(x, y))
        self._changed()

    def _on_update(self, _gesture: Gtk.GestureDrag, dx: float, dy: float) -> None:
        self.scribble.extend(*self._normalise(self._origin[0] + dx, self._origin[1] + dy))
        self._changed()

    def _on_end(self, _gesture: Gtk.GestureDrag, dx: float, dy: float) -> None:
        self.scribble.extend(*self._normalise(self._origin[0] + dx, self._origin[1] + dy))
        self.scribble.end()
        self._changed()

    def _changed(self) -> None:
        self.queue_draw()
        if self.on_changed is not None:
            self.on_changed()

    def undo(self) -> bool:
        took = self.scribble.undo()
        self._changed()
        return took

    # -- drawing --

    def _on_draw(self, _area: Gtk.DrawingArea, ctx, width: int, height: int) -> None:
        ctx.set_source_rgb(*draw.PAPER)
        ctx.rectangle(0, 0, width, height)
        ctx.fill()
        draw.draw_scribble(ctx, self.scribble, width, height)


# -- the activity ------------------------------------------------------------


class LettersActivity:
    """The four screens and the letter being made. One instance per run."""

    def __init__(
        self,
        app: ActivityApplication,
        *,
        recipients: Sequence[Recipient] | None = None,
        journal_root: Path | None = None,
        outbox_root: Path | None = None,
        inbox_root: Path | None = None,
        scratch: Path | None = None,
        recorder: object | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.app = app
        self.clock = clock or datetime.now
        self.people: list[Recipient] = list(
            recipients if recipients is not None else load_recipients()
        )
        self.journal_root = (
            journal_root if journal_root is not None else app.launch.journal_root
        )
        self.outbox_root = outbox_root
        self.inbox_root = inbox_root
        self.profile_id = app.launch.profile_id
        self.scratch = scratch if scratch is not None else Path(mkdtemp(prefix="kidnix-letter-"))

        self.window: ActivityWindow | None = None
        self.prompt: Prompt | None = None
        self.step: Step = Step.WHO
        self.letter: Letter | None = None
        self.posted = False
        self.scribble = Scribble()
        self.canvas: ScribbleCanvas | None = None
        self.caption_entry: Gtk.Entry | None = None
        self.grownup_entry: Gtk.Entry | None = None
        self.post_button: BigButton | None = None
        self.tiles: dict[str, PictureTile] = {}
        self.replies: list[Reply] = []

        #: The shell's own recorder, or a fake in a test. ``available`` is False
        #: on a machine with no microphone, and then the button is not drawn.
        self.voice = VoiceNote(recorder=recorder) if recorder is not None else VoiceNote()
        self.voice.on_state = self._on_recording_state
        self.voice.on_level = self._on_level
        self.voice.on_saved = self._on_voice_saved
        self.level_bar: Gtk.LevelBar | None = None
        self.voice_button: BigButton | None = None

        self._placeholder: Path | None = None
        self._restore_ring: Callable[[], None] | None = None

    # -- helpers --------------------------------------------------------

    @property
    def area(self):
        return self.window.area if self.window is not None else self.app.area

    def speak(self, text: str) -> bool:
        return self.app.speak(text)

    def save_entry(self, kind, files, caption=None, voice=None, meta=None, **kwargs):
        """The SDK's Journal writer, called directly rather than through the app.

        ``ActivityApplication.save_entry`` is the convenience wrapper and it
        pins ``activity_name`` to the window title -- "Letters". This activity
        needs to choose it per entry, because a letter with no written words
        gets the title **"A letter for Grandad"**, which tells a pre-reader on
        the shelf the one fact the whole activity is about. So the wrapper is
        unwrapped here, and the earcon it would have played is played by
        :meth:`post` instead, where a child pressing **Post it** is the moment
        that deserves the "it is kept" sound.
        """
        return save_entry(
            kind, files, caption, voice, meta, launch=self.app.launch, **kwargs
        )

    def placeholder(self) -> Path:
        """The drawn face, made once per run and shared by every recipient.

        One file, because it is one drawing: see
        :func:`letters_to_family.draw.draw_placeholder` for why it is not
        per-person.
        """
        if self._placeholder is None:
            self._placeholder = draw.draw_placeholder(self.scratch / "face.png")
        return self._placeholder

    def _fresh(self) -> Gtk.Box:
        """Clear the window and give back a box the screen builds into."""
        assert self.window is not None
        self.window.clear()
        self.tiles = {}
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=self.area.gap)
        box.set_vexpand(True)
        self.window.add(box)
        return box

    def _row(self, spacing: int | None = None) -> Gtk.Box:
        row = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=self.area.gap if spacing is None else spacing,
        )
        row.set_halign(Gtk.Align.CENTER)
        return row

    def _set_prompt(self, text: str, *, say: bool = True) -> Prompt:
        assert self.window is not None
        prompt = Prompt(text, speech=self.app.speech, area=self.area)
        self.prompt = prompt
        if say:
            prompt.say()
        return prompt

    def _refresh_ring(self) -> None:
        if self.window is not None:
            self.window.keys.set_content(self.window.content)
            self.window.keys.focus_first()

    def _typing(self) -> bool:
        """Is the caret in a text box? The one question the ring guard asks.

        Asked of the **window's** focus rather than of the entry, because a
        ``Gtk.Entry`` is a composite widget: what actually holds the focus is
        the ``Gtk.Text`` inside it, so ``entry.has_focus()`` is False the whole
        time somebody is typing into it. Measured under Broadway; it is the
        difference between the guard working and the guard never firing.
        """
        if self.window is None:
            return False
        focus = self.window.get_focus()
        if focus is None:
            return False
        for entry in (self.caption_entry, self.grownup_entry):
            if entry is None:
                continue
            if focus is entry or focus.is_ancestor(entry):
                return True
        # Belt to that brace: the only editable widgets this activity builds
        # are those two, so anything editable holding the focus is one of them.
        return isinstance(focus, Gtk.Editable)

    # -- build ----------------------------------------------------------

    def build(self, window: ActivityWindow) -> None:
        """The SDK's one entry point. Chooses the first screen and no other."""
        self.window = window
        _load_css()
        self._restore_ring = guard_ring(window.keys, self._typing)
        self.replies = inbox_replies(self.profile_id, self.inbox_root)
        if not self.people:
            self.build_nobody(window)
            return
        self.build_who(window)

    # -- screen zero: nobody to write to yet -----------------------------

    def build_nobody(self, window: ActivityWindow) -> None:
        """A friendly card, one spoken line, and nothing kept.

        Deliberately not an error and not a dead end that looks like a bug: the
        child is told, in words they can act on, that the next step is to fetch
        a grown-up, and the grown-up is told exactly where to go. **Nothing is
        written to the Journal** -- a card in My Things for a session in which
        nobody could write to anybody would be a record of a failure.
        """
        self.step = Step.NOBODY
        box = self._fresh()
        box.append(self._set_prompt(words.NOBODY_YET))
        card = GrownUpTurn(
            words.GROWNUP_NO_FAMILY_BODY,
            title=words.GROWNUP_NO_FAMILY_TITLE,
            speech=self.app.speech,
            area=self.area,
        )
        card.set_valign(Gtk.Align.START)
        box.append(card)
        if self.replies:
            box.append(self._shelf_button())
        self._refresh_ring()

    # -- screen one: who for? -------------------------------------------

    def build_who(self, window: ActivityWindow) -> None:
        self.step = Step.WHO
        box = self._fresh()
        box.append(self._set_prompt(words.WHO_FOR))

        grid = Gtk.Grid(column_spacing=self.area.gap, row_spacing=self.area.gap)
        grid.set_halign(Gtk.Align.CENTER)
        grid.set_valign(Gtk.Align.CENTER)
        grid.set_vexpand(True)
        columns = self.area.columns_for(self.area.picture_tile, len(self.people))
        for index, person in enumerate(self.people):
            tile = PictureTile(
                person.photo_path if person.has_photo else self.placeholder(),
                person.speak_text,
                label=person.name,
                on_activate=lambda p=person: self.choose_recipient(p),
                speech=self.app.speech,
                area=self.area,
                css_classes=("recipient",),
            )
            self.tiles[person.id] = tile
            grid.attach(tile, index % columns, index // columns, 1, 1)
        box.append(grid)

        if self.replies:
            box.append(self._shelf_button())
        self._refresh_ring()

    def choose_recipient(self, person: Recipient) -> None:
        """One press. From here on, every screen says their name."""
        self.letter = Letter(recipient=person, created=self.clock())
        self.app.play(TAP)
        if self.window is not None:
            self.build_picture(self.window)

    # -- screen two: the picture ----------------------------------------

    def build_picture(self, window: ActivityWindow) -> None:
        self.step = Step.PICTURE
        assert self.letter is not None
        box = self._fresh()
        name = self.letter.recipient.name
        box.append(
            self._set_prompt(f"{words.your_letter_for(name)} {words.CHOOSE_PICTURE}")
        )

        row = self._row()
        row.set_vexpand(True)
        row.set_valign(Gtk.Align.CENTER)
        for picture in recent_pictures(self.journal_root, JOURNAL_PICTURES):
            tile = PictureTile(
                picture.tile_image,
                picture.speak_text,
                on_activate=lambda p=picture: self.choose_journal_picture(p),
                speech=self.app.speech,
                area=self.area,
            )
            self.tiles[picture.entry_id] = tile
            row.append(tile)
        row.append(
            BigButton(
                words.DRAW_ONE,
                icon="kidnix-draw",
                speak_text=words.DRAW_ONE,
                on_activate=self.start_drawing,
                speech=self.app.speech,
                area=self.area,
            )
        )
        box.append(row)
        self._refresh_ring()

    def choose_journal_picture(self, picture) -> None:
        """Copy it out of the Journal and move on. **Copy, never link.**

        The Journal entry is the shell's and it is rewritten every time the
        child stars it; a letter pointing into it would break. The copy lives in
        this run's scratch directory until it is written into the letter's own
        entry.
        """
        assert self.letter is not None
        target = self.scratch / f"picture{picture.picture.suffix or '.png'}"
        try:
            target.write_bytes(picture.picture.read_bytes())
        except OSError as exc:
            log.warning("could not copy %s (%s); offering a drawing instead", picture.picture, exc)
            self.start_drawing()
            return
        self.letter.picture = target
        self.letter.picture_source = PictureSource.JOURNAL
        self.app.play(TAP)
        if self.window is not None:
            self.build_words(self.window)

    def start_drawing(self) -> None:
        """Swap the choice row for the canvas. Same screen, same prompt place.

        Three rows and no more: the prompt, the paper, and **one** row with the
        crayons and the two buttons in it. A column of crayons beside the paper
        is the obvious layout and it does not fit -- three 20 mm targets stacked
        with 12 mm gaps is 315 px of a 618 px rectangle before the paper has had
        any, and what falls off the bottom under gnome-kiosk is the row with
        "That's it" on it, which is the only way forward.
        """
        assert self.letter is not None and self.window is not None
        box = self._fresh()
        box.append(self._set_prompt(words.PICK_A_COLOUR))

        self.canvas = ScribbleCanvas(self.scribble, *self._canvas_size())
        box.append(self.canvas)

        controls = self._row()
        for colour in COLOURS:
            controls.append(self._crayon(colour))
        controls.append(
            BigButton(
                "Undo",
                icon="kidnix-undo",
                speak_text="Take the last line off.",
                on_activate=self.undo_stroke,
                speech=self.app.speech,
                area=self.area,
            )
        )
        controls.append(
            BigButton(
                "That's it",
                icon="kidnix-keep",
                speak_text="That's my picture.",
                on_activate=self.finish_drawing,
                speech=self.app.speech,
                area=self.area,
            )
        )
        box.append(controls)
        self._refresh_ring()

    def _canvas_size(self) -> tuple[int, int]:
        """As big as 90 mm, or as big as what is left. Never bigger.

        gnome-kiosk gives an activity the rectangle *below* the band, and what
        falls off the bottom of an over-tall window is the row with "That's it"
        on it -- the only way forward. So the canvas yields, and the prompt and
        the buttons keep their floors. (Measured: a fixed 90 mm canvas wanted
        659 px of a 618 px rectangle on the 1024x768 panel the tests run on.)
        """
        area = self.area
        width = area.target(CANVAS_MM)
        if area.known:
            # The crayon column and the gaps around it come off the width.
            width = min(width, area.width - area.min_target - area.gap * 3)
        # **The height asked for is a floor, not a size.** The canvas is the one
        # widget on this screen that can be any size at all, so it is the one
        # that yields: it requests 20 mm and expands into whatever is left after
        # the prompt and the buttons have taken their own floors. Asking for
        # 90 mm here instead wanted 659 px of the 618 px rectangle the tests run
        # on, and what falls off the bottom under gnome-kiosk is the row with
        # "That's it" on it -- the only way forward.
        return max(area.min_target, width), area.min_target

    def _crayon(self, colour: Colour) -> BigButton:
        button = BigButton(
            "",
            speak_text=colour.speak_text,
            on_activate=lambda c=colour: self.choose_colour(c),
            speech=self.app.speech,
            area=self.area,
            size_mm=20.0,
            css_classes=("crayon", colour.key),
        )
        if colour is self.scribble.colour:
            button.add_css_class("chosen")
        self.tiles[f"crayon-{colour.key}"] = button  # type: ignore[assignment]
        return button

    def choose_colour(self, colour: Colour) -> None:
        self.scribble.choose(colour)
        for key, button in self.tiles.items():
            if key.startswith("crayon-"):
                button.remove_css_class("chosen")
        chosen = self.tiles.get(f"crayon-{colour.key}")
        if chosen is not None:
            chosen.add_css_class("chosen")

    def undo_stroke(self) -> None:
        if self.canvas is not None:
            self.canvas.undo()

    def finish_drawing(self) -> None:
        """Render the scribble and move on. An empty page is still a picture.

        A four-year-old who pressed "That's it" without drawing anything meant
        to, and being sent back to draw more would be the program marking their
        work. Plain paper it is.
        """
        assert self.letter is not None
        target = draw.render_scribble(self.scratch / "picture.png", self.scribble)
        self.letter.picture = target
        self.letter.picture_source = PictureSource.DRAWING
        self.app.play(TAP)
        if self.window is not None:
            self.build_words(self.window)

    # -- screen three: the words ----------------------------------------

    def build_words(self, window: ActivityWindow) -> None:
        self.step = Step.WORDS
        assert self.letter is not None
        box = self._fresh()
        box.append(self._set_prompt(words.TELL_THEM))

        choices = self._row()
        choices.append(
            BigButton(
                words.WRITE_IT,
                icon="kidnix-word",
                speak_text=words.WRITE_IT,
                on_activate=self.show_caption,
                speech=self.app.speech,
                area=self.area,
            )
        )
        if self.voice.available:
            # No microphone means no button at all: a mic button that does
            # nothing teaches a child that buttons lie (kidnix_shell.voice).
            self.voice_button = BigButton(
                words.SAY_IT,
                icon="kidnix-ear",
                speak_text=words.SAY_IT,
                on_activate=self.toggle_voice,
                speech=self.app.speech,
                area=self.area,
            )
            choices.append(self.voice_button)
        choices.append(
            BigButton(
                "Grown-up",
                icon="kidnix-grownup",
                speak_text=words.ASK_A_GROWNUP,
                on_activate=self.show_grownup,
                speech=self.app.speech,
                area=self.area,
            )
        )
        box.append(choices)

        self.slot = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=self.area.gap)
        self.slot.set_vexpand(True)
        box.append(self.slot)

        self.post_button = BigButton(
            words.POST_IT,
            icon="kidnix-keep",
            speak_text=words.POST_IT,
            on_activate=self.post,
            speech=self.app.speech,
            area=self.area,
        )
        self.post_button.set_halign(Gtk.Align.CENTER)
        box.append(self.post_button)
        self._refresh_ring()

    def _clear_slot(self) -> None:
        child = self.slot.get_first_child()
        while child is not None:
            following = child.get_next_sibling()
            self.slot.remove(child)
            child = following
        self.caption_entry = None
        self.grownup_entry = None
        self.level_bar = None

    def show_caption(self) -> None:
        """The child's own box. **Lowercase, no autocorrect, no squiggle.**

        ``InputHints.LOWERCASE`` asks an on-screen keyboard for lower case,
        which is what a phonics classroom teaches and what the child is looking
        at on the physical keys. ``NO_SPELLCHECK`` and no completion is the
        05 section 3 rule made mechanical: there is nothing in this program that
        could underline a five-year-old's spelling in red, because none of it is
        turned on.
        """
        self._clear_slot()
        entry = Gtk.Entry()
        entry.add_css_class("caption")
        entry.set_hexpand(True)
        entry.set_input_purpose(Gtk.InputPurpose.FREE_FORM)
        entry.set_input_hints(
            Gtk.InputHints.LOWERCASE | Gtk.InputHints.NO_SPELLCHECK | Gtk.InputHints.NO_EMOJI
        )
        entry.set_enable_undo(True)
        entry.set_max_length(0)
        if self.letter is not None and self.letter.caption:
            entry.set_text(self.letter.caption)
        entry.connect("changed", self._on_caption_changed)
        self.caption_entry = entry
        self.slot.append(entry)
        entry.grab_focus()
        self._refresh_ring()
        entry.grab_focus()

    def _on_caption_changed(self, entry: Gtk.Entry) -> None:
        """Take the text as it is. The **only** place a child's words are read.

        ``get_text()`` and straight onto the letter: no strip, no case change,
        no substitution. Everything downstream -- ``caption.txt``, the rendered
        card, the outbox -- gets these bytes.
        """
        if self.letter is not None:
            self.letter.set_caption(entry.get_text(), CaptionSource.CHILD)

    def show_grownup(self) -> None:
        """The co-use route: a grown-up writes down what the child said.

        A ``GrownUpTurn`` card (adult typography, adult density, a 9 mm button)
        with a plain adult text box in it. It is not modal and it takes nothing
        away: a child who fetched nobody can press Write it or Post it instead
        and the card just sits there.
        """
        self._clear_slot()
        card = GrownUpTurn(
            words.GROWNUP_WRITE_BODY,
            title=words.GROWNUP_WRITE_TITLE,
            speech=self.app.speech,
            area=self.area,
        )
        entry = Gtk.Entry()
        entry.add_css_class("grownup")
        entry.set_hexpand(True)
        entry.set_input_hints(Gtk.InputHints.NO_EMOJI)
        if self.letter is not None and self.letter.caption:
            entry.set_text(self.letter.caption)
        entry.connect("changed", self._on_grownup_changed)
        self.grownup_entry = entry
        card.append(entry)
        self.slot.append(card)
        card.announce()
        self._refresh_ring()

    def _on_grownup_changed(self, entry: Gtk.Entry) -> None:
        if self.letter is not None:
            self.letter.set_caption(entry.get_text(), CaptionSource.GROWNUP)

    # -- the voice note --------------------------------------------------

    def toggle_voice(self) -> None:
        """One press starts, a second stops, twenty seconds stops it anyway."""
        if self.level_bar is None:
            self._clear_slot()
            bar = Gtk.LevelBar.new_for_interval(0.0, 1.0)
            bar.add_css_class("voice-level")
            bar.set_hexpand(True)
            self.level_bar = bar
            self.slot.append(bar)
            self._refresh_ring()
        self.voice.toggle(self.scratch)

    def _on_recording_state(self, recording: bool) -> None:
        if self.voice_button is None:
            return
        if recording:
            self.voice_button.add_css_class("recording")
        else:
            self.voice_button.remove_css_class("recording")

    def _on_level(self, level: float) -> None:
        if self.level_bar is not None:
            self.level_bar.set_value(max(0.0, min(1.0, level)))

    def _on_voice_saved(self, path: Path) -> None:
        if self.letter is not None:
            self.letter.voice = path
        log.info("voice note kept (%s, up to %.0f seconds)", path.name, MAX_SECONDS)

    # -- posting ---------------------------------------------------------

    def post(self) -> None:
        """One press. Journal, then outbox, then say who is going to get it."""
        if self.letter is None or not self.letter.can_post():
            # Nothing to post is not an error and does not get an error: the
            # child is simply asked for the missing half.
            if self.window is not None:
                self.build_picture(self.window)
            return
        if self.voice.recording:
            self.voice.stop()

        result = post_letter(
            self.letter,
            self.save_entry,
            self.scratch / "posting",
            self.profile_id,
            outbox_root=self.outbox_root,
        )
        self.posted = True
        # The one sound in kidnix that reports an *outcome* rather than
        # punctuating an action, and the one calm mode keeps: an activity that
        # saved silently would be the only place in the product where a child
        # is not told their work is safe.
        self.app.play(KEEP)
        log.info(
            "letter for %s kept as %s (outbox: %s)",
            self.letter.recipient.name,
            result.entry_id,
            result.outbox or "not written",
        )
        if self.window is not None:
            self.build_posted(self.window, result.card)

    def build_posted(self, window: ActivityWindow, card: Path) -> None:
        """The letter, big, and one sentence naming who is going to get it.

        No confetti, no chime beyond the shell's own "kept" earcon, no badge and
        no "well done" (E1/E2). The reward is the artefact, and the sentence is
        the audience.
        """
        self.step = Step.POSTED
        assert self.letter is not None
        box = self._fresh()
        box.append(self._set_prompt(words.posted_line(self.letter.recipient.name)))

        if card.is_file():
            picture = Gtk.Picture.new_for_filename(str(card))
            picture.add_css_class("posted-card")
            picture.set_can_shrink(True)
            picture.set_content_fit(Gtk.ContentFit.CONTAIN)
            picture.set_vexpand(True)
            box.append(picture)

        if self.replies:
            box.append(self._shelf_button())
        self._refresh_ring()

    # -- the shelf -------------------------------------------------------

    def _shelf_button(self) -> BigButton:
        button = BigButton(
            words.SHELF_TITLE,
            icon="kidnix-journal",
            speak_text=words.shelf_button(len(self.replies)),
            on_activate=self.build_shelf,
            speech=self.app.speech,
            area=self.area,
        )
        button.set_halign(Gtk.Align.CENTER)
        return button

    def build_shelf(self, *_args) -> None:
        """"Letters for you" -- read-only, and the reply path made visible.

        v1 shows what a grown-up dropped in the inbox and plays it. It does not
        import it into the Journal, delete it, or mark it read: those are the
        follow-up in ``docs/design/letters-to-family.md`` section 7, and the
        shelf is here now so that the reply half of 05 section 3 -- "a one-way
        outbox is not an audience" -- is real from the first release rather than
        a promise on a roadmap.
        """
        assert self.window is not None
        self.step = Step.SHELF
        box = self._fresh()
        box.append(self._set_prompt(words.SHELF_TITLE if self.replies else words.SHELF_EMPTY))

        row = self._row()
        row.set_vexpand(True)
        row.set_valign(Gtk.Align.CENTER)
        for reply in self.replies:
            tile = PictureTile(
                reply.picture if reply.has_picture else self.placeholder(),
                reply.speak_text,
                label=reply.from_name,
                on_activate=lambda r=reply: self.open_reply(r),
                speech=self.app.speech,
                area=self.area,
                css_classes=("reply",),
            )
            self.tiles[str(reply.path)] = tile
            row.append(tile)
        box.append(row)
        self._refresh_ring()

    def open_reply(self, reply: Reply) -> None:
        """Show one reply big, and say who it is from. Read-only."""
        assert self.window is not None
        box = self._fresh()
        box.append(self._set_prompt(words.reply_line(reply.from_name)))

        if reply.has_picture and reply.picture is not None:
            picture = Gtk.Picture.new_for_filename(str(reply.picture))
            picture.set_can_shrink(True)
            picture.set_content_fit(Gtk.ContentFit.CONTAIN)
            picture.set_vexpand(True)
            box.append(picture)
        if reply.words:
            label = Gtk.Label(label=reply.words)
            label.set_wrap(True)
            label.add_css_class("big-line")
            box.append(label)

        buttons = self._row()
        if reply.has_voice and reply.voice is not None:
            buttons.append(
                BigButton(
                    "Listen",
                    icon="kidnix-ear",
                    speak_text="Hear it.",
                    on_activate=lambda: self.play_reply(reply),
                    speech=self.app.speech,
                    area=self.area,
                )
            )
        buttons.append(
            BigButton(
                words.SHELF_TITLE,
                icon="kidnix-journal",
                speak_text=words.SHELF_TITLE,
                on_activate=self.build_shelf,
                speech=self.app.speech,
                area=self.area,
            )
        )
        box.append(buttons)
        self._refresh_ring()

    def play_reply(self, reply: Reply) -> bool:
        """Play the voice in a reply, through the shell's own player.

        Uses ``Earcons`` because it is the one audio path the SDK already gives
        an activity and it already honours the child's volume and mute. It
        degrades to False and silence rather than raising: a reply that will not
        play is a picture the child can still look at.
        """
        if reply.voice is None:
            return False
        try:
            return bool(self.app.earcons.player.play(reply.voice))
        except Exception as exc:  # pragma: no cover - no audio on this machine
            log.info("could not play %s (%s)", reply.voice, exc)
            return False

    # -- the end ---------------------------------------------------------

    def finish(self) -> None:
        """SIGTERM: keep the work, post nothing, never ask.

        Three cases and each is deliberate:

        * **Already posted** -- nothing to do. A second entry would be the same
          letter twice on the shelf.
        * **A picture but no Post it** -- kept in the Journal with
          :data:`STATUS_UNPOSTED` and **no outbox copy**, so nothing appears in
          the folder a grown-up sends things out of that they were not asked to
          send.
        * **Nothing made** -- nothing kept. A card in My Things for a session in
          which nobody chose anybody is a claim about a person that is not true.
        """
        if self.voice.recording:
            self.voice.stop()
        if self.posted or self.letter is None or not self.letter.can_post():
            log.info("nothing new to keep on the way out")
            return
        result = post_letter(
            self.letter,
            self.save_entry,
            self.scratch / "putaway",
            self.profile_id,
            status=STATUS_UNPOSTED,
            to_outbox=False,
            outbox_root=self.outbox_root,
        )
        log.info("kept the unposted letter as %s", result.entry_id)


def _load_css() -> None:
    from gi.repository import Gdk

    display = Gdk.Display.get_default()
    if display is None or not ACTIVITY_CSS.is_file():  # pragma: no cover
        return
    provider = Gtk.CssProvider()
    provider.load_from_path(str(ACTIVITY_CSS))
    Gtk.StyleContext.add_provider_for_display(
        display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 2
    )


# -- entry point -------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="kidnix-letters", description=TITLE)
    parser.add_argument(
        "--screenshot",
        type=Path,
        help="write letters-who-for.png and letters-make.png here and exit",
    )
    args, rest = parser.parse_known_args(argv[1:] if argv else None)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    app = ActivityApplication(
        ACTIVITY_ID,
        TITLE,
        # None means "build your own"; a disabled set means silence. See
        # :func:`quiet` -- and note that this is a *development* switch: the
        # child's own volume, mute and calm mode are `[access]` in parent.toml
        # and are applied by the SDK either way.
        earcons=Earcons(enabled=False) if quiet() else None,
    )
    activity = LettersActivity(app)

    if args.screenshot is not None:
        from .screenshots import run_screenshots

        return run_screenshots(app, activity, args.screenshot)

    app.set_build(activity.build)
    app.set_on_finish(activity.finish)
    return app.run([argv[0] if argv else "kidnix-letters", *rest])
