"""The window: Find it, Blend it, and the card at the end.

Everything this activity *knows* is in the pure modules beside this one --
:mod:`~sounds_and_words.ceiling` (what a child may be shown),
:mod:`~sounds_and_words.distractors` (which three wrong tiles),
:mod:`~sounds_and_words.keys` (what a key press meant),
:mod:`~sounds_and_words.blend` (dots and bars),
:mod:`~sounds_and_words.loop` (the order and the two attempts) -- none of which
imports GTK, all of which is tested headless. This module is wiring, and wiring
is the part that needs a display to test.

That split is not tidiness. The guarantee this activity carries is *"never show
a child a grapheme the school has not taught"*, and a guarantee that can only be
exercised by pressing a button is a guarantee nobody can check.

What the SDK is doing underneath every control here
---------------------------------------------------

:class:`~kidnix_activity.widgets.BigButton` and
:class:`kidnix_shell.widgets.ChildButton` bring the input rules with them
(SYNTHESIS A2/A3): every mouse button does the same thing, the press fires on
*press*, eight clicks a second produce one action, and there is no double-click,
right-click, long-press or drag anywhere -- the push-together control is a
button you tap, not a slider you drag (A5's click-move-click, with the move
taken out entirely). Sizes come from :class:`~kidnix_activity.metrics.
ContentArea`, so a grapheme tile is 40 mm of real panel and a sound button is
never under 20 mm on any monitor. Calm mode, the volume and the captions arrive
already applied.

And what it deliberately does not do: no score, no star, no streak, no timer,
no "well done", no buzzer, no red, and no way out of its own -- Back is the
band's, one screen up, in every activity (``docs/design/activity-sdk.md`` 3.4).
"""

from __future__ import annotations

import argparse
import logging
import random
import tempfile
from datetime import date
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, GLib, Gtk  # noqa: E402
from kidnix_activity.app import ActivityApplication, ActivityWindow  # noqa: E402
from kidnix_activity.journal import JournalError  # noqa: E402
from kidnix_activity.metrics import ContentArea  # noqa: E402
from kidnix_activity.widgets import BigButton, GrownUpTurn, Prompt  # noqa: E402

# ChildButton rather than a fourth SDK widget: docs/design/activity-sdk.md 6 --
# "all four are ChildButton underneath, which is where SYNTHESIS 2A lives and
# where it stays". A sound button is a control shape the SDK does not have, and
# building it on anything else would be building one that can double-fire.
from kidnix_shell.widgets import ChildButton, fit_gtk_label, next_key  # noqa: E402

from . import ACTIVITY_ID, TITLE  # noqa: E402
from .blend import BlendState, Mark, Stage, blend_word  # noqa: E402
from .ceiling import Ceiling, ceiling_for_grapheme  # noqa: E402
from .corpus import Corpus, Gpc, load_corpus  # noqa: E402
from .distractors import find_it_options  # noqa: E402
from .keys import BoardKeys, Press  # noqa: E402
from .loop import Outcome, Plan, SessionRunner, plan_session  # noqa: E402
from .phonemes import phoneme_for, say_label, yes_line  # noqa: E402
from .schedule import Item, ItemKind  # noqa: E402
from .settings import (  # noqa: E402
    PROGRESS_NAME,
    Progress,
    load_parent_ceiling,
    load_progress,
    progress_dir,
    resolve,
    save_progress,
)
from .summary import Summary  # noqa: E402

log = logging.getLogger(__name__)

__all__ = ["SoundsAndWords", "build_blend_it", "build_find_it", "main"]

#: Our own stylesheet, loaded after the shell's and the SDK's.
ACTIVITY_CSS = Path(__file__).parent / "activity.css"
#: The three interface drawings (the pictures for words are in ``pictures/``).
ICON_DIR = Path(__file__).parent / "icons"

#: How long a correct tile stays lit before the next item. Long enough to see
#: what happened and hear the sound named; short enough that a child who is
#: going quickly is not made to wait for the computer.
SETTLE_MS = 1400
#: How long the keyboard holds a grapheme that is both an answer and the start
#: of a longer one (``a`` on a board that also has ``ai``). See
#: :meth:`sounds_and_words.keys.BoardKeys.settle`.
KEY_SETTLE_MS = 900

#: Grapheme tiles: 40 mm, ADR-0011's primary target, and the task asks for it
#: explicitly. Sound buttons inside a word: smaller, but never under the floor.
TILE_MM = 40.0
SOUND_MM = 22.0


# -- small helpers ----------------------------------------------------------


def _letter_label(area: ContentArea, text: str, points: float) -> Gtk.Label:
    """A grapheme, set in Andika at a size derived from millimetres.

    The point size is computed here rather than in CSS because a millimetre is
    a physical fact about the panel and a CSS pixel is not; ``fit_gtk_label``
    then guarantees the whole of it is visible and that nothing is ever
    ellipsised.
    """
    label = Gtk.Label()
    label.add_css_class("grapheme-letter")
    fit_gtk_label(
        label,
        text,
        width=max(40, int(points * 2.4 * len(text))),
        base_pt=points,
        floor_pt=area.points(18.0),
        points=points,
        max_lines=1,
    )
    # A grapheme is never wrapped and never hyphenated. ``fit_gtk_label`` turns
    # wrapping on because every other label in kidnix is a phrase; "ng" broken
    # across two lines as "n-" / "g" would be showing a child two sounds where
    # there is one, which is the exact confusion the bar exists to prevent.
    label.set_wrap(False)
    return label


def _mark(area: ContentArea, mark: Mark, width: int) -> Gtk.Box:
    """The dot or the bar. L&S p.70, and the reason it is not a decoration.

    A dot is round and one letter wide. A bar spans the whole grapheme, which
    is the entire visual claim that ``sh`` is *one* sound -- so its width comes
    from the tile it sits under rather than from a constant.
    """
    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
    box.set_halign(Gtk.Align.CENTER)
    box.add_css_class("sound-mark")
    box.add_css_class("dot" if mark is Mark.DOT else "bar")
    thickness = max(10, area.mm_floor(3.0))
    if mark is Mark.DOT:
        # Round, and one letter wide. A dot that spanned the tile would be a
        # short bar, which says "this is more than one letter" -- the opposite
        # of what it is for.
        box.set_size_request(thickness, thickness)
    else:
        box.set_size_request(max(width, thickness * 2), thickness)
    return box


def _picture(area: ContentArea, path: Path) -> Gtk.Picture:
    """The drawing beside a word. Not a control: it does not speak or press."""
    picture = Gtk.Picture()
    picture.add_css_class("word-picture")
    picture.set_can_shrink(True)
    picture.set_content_fit(Gtk.ContentFit.CONTAIN)
    picture.set_filename(str(path))
    size = area.target(34.0)
    picture.set_size_request(size, size)
    picture.set_valign(Gtk.Align.CENTER)
    return picture


def _icon_button(
    window: ActivityWindow,
    icon: str,
    label: str,
    speak: str,
    on_activate,
    *,
    size_mm: float = TILE_MM,
) -> BigButton:
    """A primary control with one of our own drawings on it.

    Picture **and** word **and** a sentence in the ear, every time (SYNTHESIS
    B4). A pre-reader must be able to use this screen with the labels covered.
    """
    return BigButton(
        label,
        icon=str(ICON_DIR / f"{icon}.svg"),
        speak_text=speak,
        on_activate=on_activate,
        speech=window.speech,
        area=window.area,
        icon_kind="path",
        size_mm=size_mm,
    )


# -- Find it ----------------------------------------------------------------


class FindIt:
    """One Find it board: a sound, four tiles, and the key that does the same.

    The child has two routes to the same answer and neither is privileged --
    tap the tile, or press the key. Research 10 section 6: the keyboard here is
    not typing practice, it is a display of twenty-six graphemes that never
    moves, and "press the key that makes /s/" is a Letters and Sounds Phase 2
    success criterion.
    """

    def __init__(self, owner: SoundsAndWords, target: Gpc, board: list[Gpc]) -> None:
        self.owner = owner
        self.target = target
        self.board = board
        self.keys = BoardKeys([gpc.grapheme for gpc in board])
        self.tiles: dict[str, BigButton] = {}
        self.answered = False
        self._settle_source: int | None = None

    # -- the widgets --

    def build(self, window: ActivityWindow) -> Gtk.Widget:
        area = window.area
        column = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=area.gap)
        column.set_vexpand(True)

        self.prompt = Prompt(
            self.owner.find_it_line(self.target),
            speech=window.speech,
            area=area,
            on_replay=self.say_sound,
        )
        column.append(self.prompt)

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=area.gap)
        row.set_halign(Gtk.Align.CENTER)
        row.set_valign(Gtk.Align.CENTER)
        row.set_vexpand(True)
        for gpc in self.board:
            tile = BigButton(
                "",
                speak_text=say_label(gpc),
                on_activate=lambda g=gpc: self.choose(g.grapheme),
                speech=window.speech,
                area=area,
                size_mm=TILE_MM,
                css_classes=("grapheme",),
                key=next_key("grapheme"),
            )
            # BigButton's own label box is for a word under a picture; a
            # grapheme *is* the picture, so it is set at tile size instead.
            tile.set_child(_letter_label(area, gpc.grapheme, area.points(64.0)))
            self.tiles[gpc.grapheme] = tile
            row.append(tile)
        column.append(row)
        return column

    # -- what it says --

    def say_sound(self) -> None:
        """Play or speak the phoneme. The prompt's replay does exactly this."""
        self.owner.say_phoneme(self.target)

    def announce(self) -> None:
        """The line the round opens with: the instruction, then the sound."""
        self.owner.window.speak(self.prompt.text)

    # -- what the child did --

    def choose(self, grapheme: str) -> None:
        """A tile was pressed, or a key finished a grapheme. One code path."""
        if self.answered:
            return
        correct = grapheme == self.target.grapheme
        outcome = self.owner.runner.attempt(correct)
        if correct:
            self.answered = True
            tile = self.tiles.get(grapheme)
            if tile is not None:
                tile.add_css_class("correct")
            self.owner.window.speak(yes_line(self.target))
            self.owner.after(SETTLE_MS, self.owner.next_item)
            return

        # Wrong. No buzzer, no red, no comment on the tile they pressed: the
        # *correct* tile pulses, gently, and the sound plays again.
        right = self.tiles.get(self.target.grapheme)
        if right is not None:
            right.add_css_class("pulse")
        self.owner.say_phoneme(self.target)
        if outcome is Outcome.MOVE_ON:
            self.answered = True
            self.owner.after(SETTLE_MS, self.owner.next_item)

    def key(self, letter: str) -> bool:
        """One key press. Returns True when this screen consumed it."""
        if self.answered:
            return False
        result = self.keys.press(letter)
        if result.press is Press.CHOSE and result.chosen:
            self._cancel_settle()
            self.choose(result.chosen)
            return True
        if result.press is Press.PENDING:
            # Half a digraph: show the letters travelling towards one tile, and
            # arm the settle in case this *is* the whole answer.
            self._highlight_pending(result.pending)
            self._arm_settle()
            return True
        if result.press is Press.UNKNOWN:
            # A key that is not on this board is not a wrong answer. Say the
            # sound again -- that is the only useful thing to do with it.
            self.say_sound()
            return True
        return False

    def _highlight_pending(self, pending: str) -> None:
        for grapheme, tile in self.tiles.items():
            if grapheme.startswith(pending) and len(grapheme) > len(pending):
                tile.add_css_class("pulse")
            else:
                tile.remove_css_class("pulse")

    def _arm_settle(self) -> None:
        self._cancel_settle()
        self._settle_source = self.owner.after(KEY_SETTLE_MS, self._settle)

    def _cancel_settle(self) -> None:
        if self._settle_source is not None:
            GLib.source_remove(self._settle_source)
            self._settle_source = None

    def _settle(self) -> None:
        self._settle_source = None
        result = self.keys.settle()
        if result.press is Press.CHOSE and result.chosen:
            self.choose(result.chosen)


def build_find_it(window: ActivityWindow, owner: SoundsAndWords, target: Gpc) -> FindIt:
    """Put one Find it board on the screen. Returns it, for the tests."""
    board = find_it_options(owner.corpus, owner.ceiling, target, rng=owner.rng)
    screen = FindIt(owner, target, board)
    window.clear()
    window.add(screen.build(window))
    window.keys.set_content(window.content)
    return screen


# -- Blend it ---------------------------------------------------------------


class BlendIt:
    """One word, its sound buttons, the arrow, and then a person.

    The three stages are :class:`~sounds_and_words.blend.Stage`, and none of
    them is a gate: the arrow works before any sound button has been pressed,
    because forcing every button first would answer research 10's open question
    2 -- do sound buttons entrench sound-by-sound reading? -- by construction
    and in the wrong direction.
    """

    def __init__(self, owner: SoundsAndWords, state: BlendState) -> None:
        self.owner = owner
        self.state = state
        self.buttons: list[ChildButton] = []
        self.row: Gtk.Box | None = None
        self.column: Gtk.Box | None = None

    def build(self, window: ActivityWindow) -> Gtk.Widget:
        area = window.area
        self.column = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=area.gap)
        self.column.set_vexpand(True)

        self.prompt = Prompt(
            self.owner.child_text("blend_it", "Say the sounds, then push them together."),
            speech=window.speech,
            area=area,
        )
        self.column.append(self.prompt)

        middle = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=area.gap * 2)
        middle.set_halign(Gtk.Align.CENTER)
        middle.set_valign(Gtk.Align.CENTER)
        middle.set_vexpand(True)

        if self.state.word.picture is not None:
            middle.append(_picture(area, self.state.word.picture))

        self.row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=area.gap)
        self.row.add_css_class("word-row")
        self.row.set_valign(Gtk.Align.CENTER)
        for button in self.state.word.buttons:
            self.row.append(self._sound_button(window, button))
        middle.append(self.row)
        self.column.append(middle)

        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=area.gap)
        controls.set_halign(Gtk.Align.CENTER)
        # One short word under the picture, and the whole sentence in the ear
        # (SYNTHESIS B4). "push together" wraps to three hyphenated lines on a
        # 40 mm button, and a hyphenated word is not something to put in front
        # of a child who is learning to read.
        self.push_button = _icon_button(
            window,
            "push",
            "push",
            "Push the sounds together.",
            self.push,
        )
        controls.append(self.push_button)
        self.column.append(controls)
        return self.column

    def _sound_button(self, window: ActivityWindow, button) -> ChildButton:
        area = window.area
        size = area.target(SOUND_MM)
        control = ChildButton(
            speak_text=button.label,
            on_activate=lambda index=button.index: self.sound(index),
            speech_ui=window.speech.ui,
            css_classes=("sound-button",),
            key=next_key("sound"),
        )
        control.set_size_request(size, size)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=max(6, area.mm_floor(2.0)))
        box.set_halign(Gtk.Align.CENTER)
        box.set_valign(Gtk.Align.CENTER)
        letter = _letter_label(area, button.grapheme, area.points(40.0))
        box.append(letter)
        box.append(_mark(area, button.mark, area.mm_floor(5.0) * len(button.grapheme)))
        control.set_child(box)
        self.buttons.append(control)
        return control

    # -- what the child did --

    def sound(self, index: int) -> None:
        """One sound button: say that phoneme, and only that phoneme."""
        button = self.state.sound(index)
        if button is None:  # pragma: no cover - index came from the widget
            return
        gpc = self.owner.corpus.gpc_by_id.get(button.gpc_id)
        if gpc is not None:
            self.owner.say_phoneme(gpc)

    def push(self) -> None:
        """The arrow: the tiles slide together and the whole word is said."""
        if self.state.stage is not Stage.SOUNDS:
            return
        self.state.push()
        if self.row is not None:
            self.row.set_spacing(0)
            self.row.add_css_class("blended")
        self.owner.window.speak(self.state.word.text)
        self.owner.runner.blend(self.state.word.text)
        self.owner.after(SETTLE_MS, self.say_it)

    def say_it(self) -> None:
        """Hand over. Software has finished with this word.

        No recording, no listening, no grading -- research 10 section 4.6 #6,
        and it is the flat rule the whole activity is built around. What
        happens next is a child reading a word to a person, which is the thing
        the evidence actually supports (McTigue: 0.48 with an adult, -0.02
        without).
        """
        if self.state.stage is Stage.SAY_IT or self.column is None:
            return
        self.state.hand_over()
        window = self.owner.window
        area = window.area

        self.push_button.set_sensitive(False)
        self.prompt.set_text(self.owner.child_text("say_it_aloud", "Now say it out loud."))
        window.speak(self.prompt.text)

        card = GrownUpTurn(
            self.owner.grown_up_body(),
            title=self.owner.grown_up_title(),
            speech=window.speech,
            area=area,
        )
        self.column.append(card)

        onwards = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=area.gap)
        onwards.set_halign(Gtk.Align.CENTER)
        onwards.append(
            _icon_button(window, "next", "next", "Next one.", self.owner.next_item)
        )
        self.column.append(onwards)
        window.keys.set_content(window.content)


def build_blend_it(window: ActivityWindow, owner: SoundsAndWords, word: str) -> BlendIt:
    """Put one word on the screen with its sound buttons. Returns it, for tests."""
    model = blend_word(owner.corpus, word, owner.ceiling)
    screen = BlendIt(owner, BlendState(model))
    window.clear()
    window.add(screen.build(window))
    window.keys.set_content(window.content)
    return screen


# -- the activity -----------------------------------------------------------


class SoundsAndWords:
    """One session: the plan, the screens, and the card at the end."""

    def __init__(
        self,
        app: ActivityApplication,
        *,
        corpus: Corpus | None = None,
        ceiling: Ceiling | None = None,
        seed: int | None = None,
        today: date | None = None,
    ) -> None:
        self.app = app
        self.corpus = corpus if corpus is not None else load_corpus()
        self.parent = load_parent_ceiling()
        self.ceiling = ceiling if ceiling is not None else resolve(self.corpus, self.parent)
        log.info("ceiling: %s (%s)", self.ceiling.label, self.parent.describe())

        self.progress_path = progress_dir() / PROGRESS_NAME
        self.progress: Progress = load_progress(self.progress_path)
        self.today = today or date.today()
        self.day = self.progress.touch(self.today)

        self.rng = random.Random(seed if seed is not None else self.day)
        self.plan: Plan = plan_session(
            self.corpus, self.ceiling, self.progress.history, self.day, rng=self.rng
        )
        log.info("today's loop: %s", self.plan.describe())
        self.runner = SessionRunner(self.plan, self.progress.history)

        self.window: ActivityWindow | None = None
        self.screen: FindIt | BlendIt | None = None
        self._scratch: tempfile.TemporaryDirectory[str] | None = None
        self._saved = False
        #: The word list the Journal already holds a card for, so the done
        #: screen and SIGTERM cannot each keep one.
        self._kept_words: tuple[str, ...] = ()
        self._kept_path: Path | None = None

    # -- copy, from the corpus rather than from here ----------------------

    def child_text(self, key: str, fallback: str) -> str:
        """One of the child-facing lines in ``data/parent_text.toml``.

        The copy lives in the corpus because ``tests/test_parent_text.py``
        greps every string in it against the blacklist -- *score, level, star,
        streak, badge, percentile* -- and a line written inline here would be
        outside that net.
        """
        section = self.corpus.parent_text.get("child", {})
        return str(section.get(key) or fallback)

    def find_it_line(self, gpc: Gpc) -> str:
        return f"{self.child_text('find_it', 'Find the one that says')} {say_label(gpc)}."

    def grown_up_title(self) -> str:
        section = self.corpus.parent_text.get("grown_up_turn", {})
        return str(section.get("title") or "Your turn")

    def grown_up_body(self) -> str:
        section = self.corpus.parent_text.get("grown_up_turn", {})
        prompts = section.get("prompts") or []
        first = str(prompts[0]) if prompts else "Ask him to say the word out loud to you."
        return f"{section.get('invite', 'Sit with him for this bit.')} {first}"

    # -- speaking ---------------------------------------------------------

    def say_phoneme(self, gpc: Gpc) -> None:
        """Play the recorded clip if there is one; say the safe label if not.

        Never a synthesised phoneme in the ordinary sense: the label is
        *spelled* so an en-GB voice says the sound ("sss", "shh") rather than
        the schwa'd letter name ("suh"). That is a placeholder and
        :mod:`sounds_and_words.phonemes` says so; the recordings are the plan.
        """
        sound = phoneme_for(gpc)
        if self.window is None:
            return
        if sound.clip is not None:
            # There is no clip player in the SDK yet (the a-z recordings are
            # still inside GCompris's .rcc bundle -- see phonemes.py), so this
            # branch is unreachable on today's image and is here so the day a
            # clip appears the failure is a missing player and not a wrong
            # sound. The label is still spoken, so nothing is silent.
            log.info("clip %s is installed but there is no player yet", sound.clip)
        self.window.speak(sound.label)

    def after(self, milliseconds: int, callback) -> int:
        """Do something in a moment, on the main loop. Returns the source id."""

        def once() -> bool:
            callback()
            return GLib.SOURCE_REMOVE

        return GLib.timeout_add(milliseconds, once)

    # -- the loop ---------------------------------------------------------

    def build(self, window: ActivityWindow) -> None:
        self.window = window
        self._load_css()
        self._arm_keyboard(window)
        self.show_current()

    def show_current(self) -> None:
        """Draw whatever the runner is pointing at. The only screen switch."""
        window = self.window
        if window is None:  # pragma: no cover - build() has always run first
            return
        item = self.runner.current
        if item is None:
            self.show_done()
            return
        if item.kind is ItemKind.FIND_IT:
            self.show_find_it(item)
        elif item.kind is ItemKind.BLEND_IT:
            self.show_blend_it(item)
        else:  # pragma: no cover - loop.BUILT filters everything else out
            self.next_item()

    def show_find_it(self, item: Item) -> None:
        gpc = self.corpus.gpc_by_id.get(item.gpc_id or "")
        if gpc is None:  # pragma: no cover - a corrupt plan
            self.next_item()
            return
        screen = build_find_it(self.window, self, gpc)
        self.screen = screen
        screen.announce()
        self.after(SETTLE_MS, screen.say_sound)

    def show_blend_it(self, item: Item) -> None:
        try:
            screen = build_blend_it(self.window, self, item.payload)
        except ValueError as exc:  # pragma: no cover - the schedule chose it
            log.error("refusing to show %r: %s", item.payload, exc)
            self.next_item()
            return
        self.screen = screen
        self.window.speak(screen.prompt.text)

    def next_item(self) -> None:
        self.runner.advance()
        self.show_current()

    def show_done(self) -> None:
        """The end: the words read today, kept, and said out loud once."""
        window = self.window
        if window is None:  # pragma: no cover
            return
        self.screen = None
        window.clear()
        area = window.area

        summary = self.summary()
        entry_path = self.keep(summary)

        window.add(Prompt(self.child_text("done", "That's the lot for today."), speech=window.speech, area=area))
        if entry_path is not None:
            picture = Gtk.Picture()
            picture.add_css_class("word-picture")
            picture.set_can_shrink(True)
            picture.set_content_fit(Gtk.ContentFit.CONTAIN)
            picture.set_filename(str(entry_path))
            picture.set_vexpand(True)
            window.add(picture)
        window.add(
            GrownUpTurn(
                self.grown_up_body(),
                title=self.grown_up_title(),
                speech=window.speech,
                area=area,
            )
        )
        window.keys.set_content(window.content)
        window.speak(summary.caption if summary.words else self.child_text("done", "That's the lot for today."))

    # -- keeping it -------------------------------------------------------

    def summary(self) -> Summary:
        return Summary(
            words=self.runner.words_read(),
            gpcs=self.runner.gpcs_practised(),
            day=self.today,
            ceiling_label=self.ceiling.label,
        )

    @property
    def scratch(self) -> Path:
        """Somewhere to draw the card before the Journal copies it."""
        if self._scratch is None:
            self._scratch = tempfile.TemporaryDirectory(prefix="sounds-and-words-")
        return Path(self._scratch.name)

    def keep(self, summary: Summary | None = None) -> Path | None:
        """Write the card into the child's Journal. Returns the PNG, or ``None``.

        Everything degrades except this. A missing font, a dead voice, an
        unknown monitor -- the child carries on. Losing what they made is the
        one failure that is not survivable, so the error is loud in the log and
        the session's *history* is still written either way.
        """
        summary = summary or self.summary()
        if not summary.words:
            log.info("nothing was blended today; no card to keep")
            return None
        if summary.words == self._kept_words:
            # A child who reached the end and *then* had the session ended
            # would otherwise get two identical cards in My Things -- once from
            # the done screen and once from SIGTERM. Keeping again only makes
            # sense if more words have happened since.
            log.info("today's card is already kept; not keeping it twice")
            return self._kept_path
        try:
            path = summary.write(self.scratch / "read-today.png")
        except RuntimeError as exc:
            log.error("could not draw the summary card: %s", exc)
            return None
        try:
            entry = self.app.save_entry(
                "sounds",
                [path],
                caption=summary.caption,
                meta=summary.meta,
            )
        except JournalError as exc:
            log.error("could not keep the card: %s", exc)
            return path
        log.info("kept %s (%s)", entry.id, summary.caption)
        self._kept_words = summary.words
        self._kept_path = path
        return path

    def finish(self) -> None:
        """SIGTERM. Save the schedule and the card, once, and say nothing.

        There is no dialogue and no "are you sure?" -- ``quit = "signal"`` and
        ``docs/design/activity-sdk.md`` 3.3. A child at put-away time cannot be
        asked to read a question.
        """
        if self._saved:
            return
        self._saved = True
        try:
            save_progress(self.progress_path, self.progress)
            log.info("schedule saved to %s", self.progress_path)
        except OSError as exc:
            log.error("could not save the schedule: %s", exc)
        self.keep()

    # -- wiring -----------------------------------------------------------

    def _load_css(self) -> None:
        display = Gdk.Display.get_default()
        if display is None or not ACTIVITY_CSS.is_file():  # pragma: no cover
            return
        provider = Gtk.CssProvider()
        provider.load_from_path(str(ACTIVITY_CSS))
        Gtk.StyleContext.add_provider_for_display(
            display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 2
        )

    def _arm_keyboard(self, window: ActivityWindow) -> None:
        """Letters, in the bubble phase, after the SDK's ring has had its turn.

        The SDK owns Tab, the arrows, Enter and Space, and deliberately does not
        own Escape (that is the shell's Back, one screen up). Letters are ours,
        and only while a Find it board is showing.
        """
        controller = Gtk.EventControllerKey.new()
        controller.set_propagation_phase(Gtk.PropagationPhase.BUBBLE)
        controller.connect("key-pressed", self._on_key)
        window.add_controller(controller)

    def _on_key(self, _controller, keyval: int, _code: int, state: Gdk.ModifierType) -> bool:
        if state & (Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.ALT_MASK):
            return False
        if not isinstance(self.screen, FindIt):
            return False
        unicode_point = Gdk.keyval_to_unicode(keyval)
        if not unicode_point:
            return False
        return self.screen.key(chr(unicode_point))


# -- entry point ------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="kidnix-sounds-and-words", description=TITLE)
    parser.add_argument(
        "--screenshot",
        type=Path,
        help="write saw-find-it.png and saw-blend-it.png into this directory and exit",
    )
    parser.add_argument("--seed", type=int, help="fix the shuffle, for a screenshot or a demo")
    parser.add_argument(
        "--ceiling",
        metavar="GRAPHEME",
        help=(
            "DEVELOPMENT ONLY: use this grapheme as the ceiling instead of the "
            "one in /etc/kidnix/sounds_and_words.toml. For screenshots and "
            "demos. The shell never passes it -- the manifest's exec is the "
            "bare command -- and a child's session cannot reach it."
        ),
    )
    args, rest = parser.parse_known_args(argv[1:] if argv else None)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    app = ActivityApplication(ACTIVITY_ID, TITLE)

    ceiling = None
    if args.ceiling:
        # Said out loud, at warning level, because a ceiling that did not come
        # from a grown-up is the one thing this activity is built to refuse.
        log.warning(
            "DEVELOPMENT OVERRIDE: ceiling forced to %r from the command line, "
            "not from a grown-up's answer",
            args.ceiling,
        )
        ceiling = ceiling_for_grapheme(load_corpus(), args.ceiling)

    activity = SoundsAndWords(app, ceiling=ceiling, seed=args.seed)

    if args.screenshot is not None:
        from .screenshots import run_screenshots

        return run_screenshots(app, activity, args.screenshot)

    app.set_build(activity.build)
    app.set_on_finish(activity.finish)
    return app.run([argv[0] if argv else "kidnix-sounds-and-words", *rest])
