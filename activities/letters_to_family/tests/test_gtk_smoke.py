"""The window, under Broadway, on a machine that has one.

**Never on the developer's desktop.** The SDK says so
(``docs/design/activity-sdk.md`` section 10), AGENTS.md says it twice, and this
module enforces it: it starts its own ``gtk4-broadwayd`` on a private display,
points GDK at it before GTK is initialised, and skips the whole file if the
daemon is not there or will not come up.

Headless tests are the floor and these are the ceiling: everything worth
proving is in the pure modules and is asserted without a display. What is here
is the wiring -- that each screen builds, that every target clears the 20 mm
floor, that the caption box really does get Space back from the focus ring, and
the end-to-end the SDK asks every activity for: launch, make one thing, find it
in My Things.
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import time
from pathlib import Path

import pytest

from conftest import HAVE_SDK

pytestmark = pytest.mark.skipif(not HAVE_SDK, reason="kidnix_activity is not importable here")

#: A display number nothing else is likely to be on. Broadway listens on
#: 8080 + N, which is why the port is what gets probed below.
DISPLAY = 114
PORT = 8080 + DISPLAY


def _listening() -> bool:
    with socket.socket() as probe:
        probe.settimeout(0.2)
        return probe.connect_ex(("127.0.0.1", PORT)) == 0


@pytest.fixture(scope="session")
def broadway():
    """One daemon for the whole run, torn down after it."""
    binary = shutil.which("gtk4-broadwayd")
    if binary is None:
        pytest.skip("gtk4-broadwayd is not installed")
    process = subprocess.Popen(
        [binary, f":{DISPLAY}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    for _ in range(50):
        if _listening():
            break
        time.sleep(0.1)
    else:  # pragma: no cover - a machine where broadwayd will not start
        process.terminate()
        pytest.skip("gtk4-broadwayd did not come up")
    os.environ["GDK_BACKEND"] = "broadway"
    os.environ["BROADWAY_DISPLAY"] = f":{DISPLAY}"
    yield f":{DISPLAY}"
    process.terminate()
    process.wait(timeout=5)


@pytest.fixture(scope="session")
def gtk(broadway):
    """GTK, initialised against that display, or a skip."""
    import gi

    gi.require_version("Gtk", "4.0")
    from gi.repository import Gtk

    if not Gtk.init_check():  # pragma: no cover - a display that will not open
        pytest.skip("GTK would not initialise against Broadway")
    return Gtk


def activate(app) -> None:
    """Build the window **without** ``Gio.Application.run()``.

    ``run()`` registers the application on the session bus first, and a machine
    with no reachable bus -- a build container, a sandboxed test runner, a
    developer's terminal outside their own session -- spends the D-Bus default
    timeout (25 seconds, measured here) failing to and then returns *without
    activating at all*. That is 25 seconds a test, and no window at the end of
    it.

    ``do_activate()`` is the half this file is actually about: it loads the CSS,
    builds the :class:`ActivityWindow`, wires the speech bridge, arms the signal
    handler and calls the activity's ``build``. It is the same code path the
    shell takes on the machine, minus the bus and minus the main loop.
    """
    app.do_activate()


FAMILY = None


def family():
    from letters_to_family.recipients import Recipient

    return [
        Recipient(id="grandad", name="Grandad", relation="Grandpa"),
        Recipient(id="nanna", name="Nanna", relation="Grandma"),
    ]


def silent_earcons():
    """A disabled earcon set. **Never a real one, in any test in this file.**

    `conftest` already sets ``KIDNIX_SPEECH=off``, which gives the voice a null
    backend -- but the earcons are a second audio path (GStreamer straight to
    PipeWire) and they do not read that variable. A test that pressed a tile
    would tap through the speakers of the machine somebody is working on
    (AGENTS.md section 5).
    """
    from kidnix_shell.sound import Earcons

    return Earcons(enabled=False)


def letters_in(journal: Path) -> list[Path]:
    """The **letter** entries in a Journal, ignoring anything else in it.

    The fixture seeds one ordinary drawing so there is something to send, so
    "did posting keep something?" has to ask what kind of thing each entry is.
    ``meta.json`` is where an SDK activity's own ``kind`` lives -- ``entry.json``
    is written by the shell's dataclass and would drop any key we added
    (docs/design/activity-sdk.md section 8).
    """
    found = []
    for entry in sorted(journal.glob("*/*/*/*/entry.json")):
        meta = entry.parent / "meta.json"
        if not meta.is_file():
            continue
        if json.loads(meta.read_text()).get("kind") == "letter":
            found.append(entry)
    return found


def a_journal_picture(root: Path, entry_id: str = "aaa") -> Path:
    """One image entry in a Journal the child could send from."""
    directory = root / "2026" / "08" / "20" / entry_id
    directory.mkdir(parents=True, exist_ok=True)
    picture = directory / "v001.png"
    import cairo

    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 40, 40)
    surface.write_to_png(str(picture))
    shutil.copy(picture, directory / "thumb.png")
    (directory / "entry.json").write_text(
        json.dumps(
            {
                "id": entry_id,
                "activity_id": "hello-draw",
                "created": "2026-08-20T10:00:00",
                "updated": "2026-08-20T10:00:00",
                "title": "My dinosaur",
                "source_path": "",
                "mime": "image/png",
                "versions": [
                    {"filename": "v001.png", "imported": "2026-08-20", "size": 1, "sha256": "x"}
                ],
            }
        )
    )
    return picture


@pytest.fixture
def built(gtk, tmp_path):
    """One activity, built into a real window on a real display."""
    from kidnix_activity.app import ActivityApplication
    from kidnix_shell.voice import FakeRecorder

    from letters_to_family import ACTIVITY_ID, TITLE
    from letters_to_family.activity import LettersActivity

    home = tmp_path / "home"
    env = {
        "HOME": str(home),
        "XDG_DATA_HOME": str(home / ".local" / "share"),
        "XDG_STATE_HOME": str(home / ".local" / "state"),
        "KIDNIX_ACTIVITY_ID": ACTIVITY_ID,
        "KIDNIX_PROFILE_ID": "sam",
    }
    journal = home / ".local" / "share" / "kidnix" / "profiles" / "sam" / "journal"
    a_journal_picture(journal)

    app = ActivityApplication(ACTIVITY_ID, TITLE, env=env, earcons=silent_earcons())
    activity = LettersActivity(
        app,
        recipients=family(),
        journal_root=journal,
        outbox_root=tmp_path / "outbox",
        inbox_root=tmp_path / "inbox",
        scratch=tmp_path / "scratch",
        recorder=FakeRecorder(),
    )
    app.set_build(activity.build)
    app.set_on_finish(activity.finish)
    activate(app)
    activity.paths = {"home": home, "journal": journal, "outbox": tmp_path / "outbox"}
    return activity


# --- the keyvals agree with GTK ---------------------------------------------


def test_every_keyval_is_the_gdk_constant_it_is_named_after(gtk):
    """`keys.py` writes them out as integers so it runs with no GTK at all.
    This is the one place the two are checked against each other."""
    from gi.repository import Gdk

    from letters_to_family.keys import KEYVALS

    for name, value in KEYVALS.items():
        assert value == getattr(Gdk, f"KEY_{name}"), name


# --- who for? ---------------------------------------------------------------


def test_the_first_screen_is_a_face_for_every_recipient(built):
    from letters_to_family.letter import Step

    assert built.step is Step.WHO
    assert set(built.tiles) == {"grandad", "nanna"}


def test_a_recipient_with_no_photo_gets_the_drawn_placeholder(built):
    tile = built.tiles["grandad"]
    assert tile.path == built.placeholder()
    assert tile.path.is_file()


def test_a_recipient_with_a_photo_shows_the_photo(gtk, tmp_path, built):
    from letters_to_family.recipients import Recipient

    photo = tmp_path / "grandad.jpg"
    photo.write_bytes(b"jpeg")
    built.people = [Recipient(id="g", name="Grandad", photo=str(photo))]
    built.build_who(built.window)
    assert built.tiles["g"].path == photo


def test_every_face_says_the_name_and_is_at_least_the_floor(built):
    area = built.window.area
    for person in built.people:
        tile = built.tiles[person.id]
        assert tile.speak_text == person.name
        width, height = tile.get_size_request()
        assert width >= area.min_target
        assert height >= area.min_target


def test_with_nobody_in_the_family_list_there_is_a_card_and_no_journal_entry(
    gtk, tmp_path
):
    """A card in My Things for a session in which nobody could write to anybody
    would be a record of a failure."""
    from kidnix_activity.app import ActivityApplication
    from kidnix_activity.widgets import GrownUpTurn
    from kidnix_shell.voice import FakeRecorder

    from letters_to_family import ACTIVITY_ID, TITLE
    from letters_to_family.activity import LettersActivity
    from letters_to_family.letter import Step

    home = tmp_path / "empty-home"
    env = {
        "HOME": str(home),
        "XDG_DATA_HOME": str(home / ".local" / "share"),
        "KIDNIX_ACTIVITY_ID": ACTIVITY_ID,
        "KIDNIX_PROFILE_ID": "sam",
    }
    app = ActivityApplication(ACTIVITY_ID, TITLE, env=env, earcons=silent_earcons())
    activity = LettersActivity(
        app,
        recipients=[],
        journal_root=tmp_path / "journal",
        outbox_root=tmp_path / "outbox",
        inbox_root=tmp_path / "inbox",
        scratch=tmp_path / "scratch2",
        recorder=FakeRecorder(),
    )
    app.set_build(activity.build)
    activate(app)

    assert activity.step is Step.NOBODY
    cards = [
        child
        for child in _children(activity.window.content)
        if isinstance(child, GrownUpTurn)
    ]
    assert len(cards) == 1

    activity.finish()
    assert letters_in(tmp_path / "journal") == []


def _children(widget):
    """Every widget under ``widget``, depth first."""
    found = []
    child = widget.get_first_child()
    while child is not None:
        found.append(child)
        found.extend(_children(child))
        child = child.get_next_sibling()
    return found


# --- the picture ------------------------------------------------------------


def test_choosing_a_face_goes_straight_to_the_picture_step(built):
    from letters_to_family.letter import Step

    built.tiles["grandad"].fire()
    assert built.step is Step.PICTURE
    assert built.letter is not None
    assert built.letter.recipient.name == "Grandad"


def test_the_picture_step_offers_the_child_s_own_recent_drawings(built):
    built.choose_recipient(built.people[0])
    assert "aaa" in built.tiles


def test_choosing_a_journal_picture_copies_it_out_of_the_journal(built):
    """A letter pointing into a Journal entry would break the day the shell
    rewrote that entry, which it does every time a child stars something."""
    from letters_to_family.letter import PictureSource, Step

    built.choose_recipient(built.people[0])
    built.tiles["aaa"].fire()
    assert built.step is Step.WORDS
    assert built.letter.picture_source is PictureSource.JOURNAL
    assert built.letter.picture.is_file()
    assert "journal" not in built.letter.picture.parts


def test_drawing_offers_three_crayons_and_an_undo(built):
    built.choose_recipient(built.people[0])
    built.start_drawing()
    assert {"crayon-teal", "crayon-pink", "crayon-black"} <= set(built.tiles)
    assert built.canvas is not None


def test_the_canvas_draws_on_press_and_undo_takes_the_line_back(built):
    built.choose_recipient(built.people[0])
    built.start_drawing()
    built.canvas._on_begin(None, 10.0, 10.0)
    built.canvas._on_update(None, 20.0, 20.0)
    built.canvas._on_end(None, 20.0, 20.0)
    assert built.scribble.stroke_count == 1
    built.undo_stroke()
    assert built.scribble.stroke_count == 0


def test_a_crayon_changes_the_colour_and_shows_which_one_is_in_your_hand(built):
    built.choose_recipient(built.people[0])
    built.start_drawing()
    built.tiles["crayon-pink"].fire()
    assert built.scribble.colour.key == "pink"
    assert built.tiles["crayon-pink"].has_css_class("chosen")
    assert not built.tiles["crayon-teal"].has_css_class("chosen")


def test_finishing_a_drawing_renders_it_and_moves_on(built):
    from letters_to_family.letter import PictureSource, Step

    built.choose_recipient(built.people[0])
    built.start_drawing()
    built.canvas._on_begin(None, 5.0, 5.0)
    built.canvas._on_end(None, 30.0, 30.0)
    built.finish_drawing()
    assert built.step is Step.WORDS
    assert built.letter.picture_source is PictureSource.DRAWING
    assert built.letter.picture.is_file()


# --- the words --------------------------------------------------------------


def test_the_words_step_offers_writing_saying_and_asking_a_grown_up(built, gtk):
    from kidnix_shell.widgets import ChildButton

    built.choose_recipient(built.people[0])
    built.tiles["aaa"].fire()
    spoken = {
        child.speak_text
        for child in _children(built.window.content)
        if isinstance(child, ChildButton)
    }
    assert "Write it" in spoken
    assert "Say it" in spoken
    assert "Ask a grown-up to write it" in spoken
    assert "Post it" in spoken


def test_with_no_microphone_there_is_no_say_it_button(gtk, tmp_path, built):
    """A mic button that does nothing teaches a child that buttons lie."""
    from kidnix_shell.voice import FakeRecorder, VoiceNote
    from kidnix_shell.widgets import ChildButton

    built.voice = VoiceNote(recorder=FakeRecorder(available=False))
    built.choose_recipient(built.people[0])
    built.tiles["aaa"].fire()
    spoken = {
        child.speak_text
        for child in _children(built.window.content)
        if isinstance(child, ChildButton)
    }
    assert "Say it" not in spoken
    assert "Write it" in spoken


def test_the_caption_box_asks_for_lower_case_and_no_spell_check(built, gtk):
    from gi.repository import Gtk

    built.choose_recipient(built.people[0])
    built.tiles["aaa"].fire()
    built.show_caption()
    hints = built.caption_entry.get_input_hints()
    assert hints & Gtk.InputHints.LOWERCASE
    assert hints & Gtk.InputHints.NO_SPELLCHECK


def test_what_the_child_types_reaches_the_letter_byte_for_byte(built):
    """The rule the whole activity exists to keep: invented spelling *is* the
    Year One curriculum, and nothing here tidies it."""
    from letters_to_family.letter import CaptionSource

    built.choose_recipient(built.people[0])
    built.tiles["aaa"].fire()
    built.show_caption()
    built.caption_entry.set_text("i sor a dinosor  at the parc")
    assert built.letter.caption == "i sor a dinosor  at the parc"
    assert built.letter.caption_source is CaptionSource.CHILD


def test_a_grown_up_s_words_are_recorded_as_a_grown_up_s(built):
    from kidnix_activity.widgets import GrownUpTurn

    from letters_to_family.letter import CaptionSource

    built.choose_recipient(built.people[0])
    built.tiles["aaa"].fire()
    built.show_grownup()
    cards = [c for c in _children(built.window.content) if isinstance(c, GrownUpTurn)]
    assert len(cards) == 1
    built.grownup_entry.set_text("We went to the park with Nanna.")
    assert built.letter.caption_source is CaptionSource.GROWNUP


def test_the_caption_box_takes_the_space_bar_back_from_the_focus_ring(built):
    """Without the guard, Space presses the focused button and a child typing
    "i luv u" gets "iluvu"."""
    from letters_to_family.keys import KEYVALS

    built.choose_recipient(built.people[0])
    built.tiles["aaa"].fire()
    built.show_caption()
    built.caption_entry.grab_focus()
    assert built._typing() is True
    assert built.window.keys.key(KEYVALS["space"]) is False
    # And Tab is still the ring's, so there is a way off the box (A6).
    assert built.window.keys.key(KEYVALS["Tab"]) is True


def test_with_no_box_focused_the_ring_has_the_space_bar_as_usual(built):
    from letters_to_family.keys import KEYVALS

    assert built._typing() is False
    assert built.window.keys.key(KEYVALS["space"]) is True


def test_the_voice_note_is_the_shell_s_own_twenty_second_one(built):
    built.choose_recipient(built.people[0])
    built.tiles["aaa"].fire()
    built.toggle_voice()
    assert built.voice.recording is True
    assert built.level_bar is not None
    built.toggle_voice()
    assert built.voice.recording is False
    assert built.letter.voice is not None
    assert built.letter.voice.is_file()


# --- posting ----------------------------------------------------------------


def test_posting_keeps_a_letter_in_my_things_and_a_copy_for_the_grown_up(built):
    """The end-to-end the SDK asks every activity for: launch, make one thing,
    find it in My Things."""
    from letters_to_family.letter import STATUS_WAITING, Step

    built.choose_recipient(built.people[0])
    built.tiles["aaa"].fire()
    built.show_caption()
    built.caption_entry.set_text("i luv u grandad")
    built.post()

    assert built.step is Step.POSTED
    entries = letters_in(built.paths["journal"])
    assert len(entries) == 1
    written = json.loads(entries[0].read_text())
    assert written["activity_id"] == "letters"
    # A short caption becomes the card's title -- the child's own words, which
    # is what My Things reads aloud.
    assert written["title"].lower() == "i luv u grandad"
    # caption.txt is the child's own spelling. The SDK's writer ends the file
    # with a newline (kidnix_activity.journal); the *characters* are theirs and
    # nothing has been cased, stripped or corrected. The outbox copy, which this
    # package writes itself, is byte for byte -- asserted below.
    assert (entries[0].parent / "caption.txt").read_text().rstrip("\n") == "i luv u grandad"

    meta = json.loads((entries[0].parent / "meta.json").read_text())
    assert meta["kind"] == "letter"
    assert meta["meta"]["recipient"]["name"] == "Grandad"
    assert meta["meta"]["status"] == STATUS_WAITING

    outboxes = list((built.paths["outbox"] / "sam").iterdir())
    assert len(outboxes) == 1
    assert outboxes[0].name.endswith("-grandad")
    assert (outboxes[0] / "letter.png").is_file()
    assert (outboxes[0] / "caption.txt").read_text() == "i luv u grandad"


def test_pressing_post_with_nothing_made_asks_for_a_picture_rather_than_erroring(built):
    from letters_to_family.letter import Step

    built.choose_recipient(built.people[0])
    built.post()
    assert built.step is Step.PICTURE
    assert letters_in(built.paths["journal"]) == []


def test_finishing_after_posting_keeps_nothing_more(built):
    built.choose_recipient(built.people[0])
    built.tiles["aaa"].fire()
    built.post()
    built.finish()
    assert len(letters_in(built.paths["journal"])) == 1


def test_put_away_keeps_the_work_but_puts_nothing_in_the_outbox(built):
    """The session ended mid-letter. The child's work is theirs; the grown-up
    was never asked to send anything."""
    from letters_to_family.letter import STATUS_UNPOSTED

    built.choose_recipient(built.people[0])
    built.tiles["aaa"].fire()
    built.finish()

    entries = letters_in(built.paths["journal"])
    assert len(entries) == 1
    meta = json.loads((entries[0].parent / "meta.json").read_text())
    assert meta["meta"]["status"] == STATUS_UNPOSTED
    assert not (built.paths["outbox"] / "sam").exists()


def test_finishing_without_choosing_anybody_keeps_nothing(built):
    built.finish()
    assert letters_in(built.paths["journal"]) == []


# --- the shelf --------------------------------------------------------------


def test_a_reply_in_the_inbox_puts_a_shelf_button_on_the_first_screen(gtk, built, tmp_path):
    from kidnix_shell.widgets import ChildButton

    folder = tmp_path / "inbox" / "sam" / "grandad"
    folder.mkdir(parents=True)
    import cairo

    cairo.ImageSurface(cairo.FORMAT_ARGB32, 20, 20).write_to_png(str(folder / "photo.png"))

    built.replies = __import__(
        "letters_to_family.mailbox", fromlist=["inbox_replies"]
    ).inbox_replies("sam", tmp_path / "inbox")
    built.build_who(built.window)
    spoken = {
        child.speak_text
        for child in _children(built.window.content)
        if isinstance(child, ChildButton)
    }
    assert "Letters for you" in spoken


def test_the_shelf_shows_one_tile_for_each_reply(gtk, built, tmp_path):
    import cairo

    from letters_to_family.letter import Step
    from letters_to_family.mailbox import inbox_replies

    for name in ("grandad", "nanna"):
        folder = tmp_path / "inbox" / "sam" / name
        folder.mkdir(parents=True)
        cairo.ImageSurface(cairo.FORMAT_ARGB32, 20, 20).write_to_png(str(folder / "photo.png"))

    built.replies = inbox_replies("sam", tmp_path / "inbox")
    built.build_shelf()
    assert built.step is Step.SHELF
    assert len(built.tiles) == 2
    assert all("from" in tile.speak_text for tile in built.tiles.values())


def test_opening_a_reply_shows_it_and_writes_nothing_back(gtk, built, tmp_path):
    import cairo

    from letters_to_family.mailbox import inbox_replies

    folder = tmp_path / "inbox" / "sam" / "grandad"
    folder.mkdir(parents=True)
    cairo.ImageSurface(cairo.FORMAT_ARGB32, 20, 20).write_to_png(str(folder / "photo.png"))
    (folder / "words.txt").write_text("Thank you for the dinosaur!")

    replies = inbox_replies("sam", tmp_path / "inbox")
    before = sorted(p.name for p in folder.iterdir())
    built.replies = replies
    built.open_reply(replies[0])
    assert sorted(p.name for p in folder.iterdir()) == before


# --- it fits ----------------------------------------------------------------


@pytest.mark.parametrize(
    "screen", ["who", "picture", "drawing", "words", "shelf"]
)
def test_no_screen_is_bigger_than_the_rectangle_below_the_band(built, gtk, screen):
    """gnome-kiosk gives an activity the rectangle *below* the band, and GTK
    will not go under a widget's minimum -- so the minimum of the whole tree is
    what has to fit, in both directions."""
    from gi.repository import Gtk

    if screen != "who":
        built.choose_recipient(built.people[0])
    if screen == "drawing":
        built.start_drawing()
    if screen == "words":
        built.tiles["aaa"].fire()
    if screen == "shelf":
        built.build_shelf()

    area = built.window.area
    if not area.known:
        return
    wide, _n, _mb, _nb = built.window.content.measure(Gtk.Orientation.HORIZONTAL, -1)
    assert wide <= area.width
    tall, _n, _mb, _nb = built.window.content.measure(Gtk.Orientation.VERTICAL, area.width)
    assert tall <= area.height
