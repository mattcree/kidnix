"""The keyboard, and the one place the SDK's focus ring stands aside.

The bug this exists to make impossible: ``ActivityKeyboard`` consumes Space to
press the focused control, so on the one screen in the suite with a text box a
child typing ``i luv u`` would get ``iluvu`` and a button press per word.
"""

from __future__ import annotations

from letters_to_family.keys import (
    ACTIVATE,
    BACKSPACE,
    ESCAPE,
    KEYVALS,
    MOVE,
    RING_ALWAYS,
    guard_ring,
    ring_consumes,
)


class FakeRing:
    """As much of ``ActivityKeyboard`` as :func:`guard_ring` touches."""

    def __init__(self) -> None:
        self.seen: list[tuple[int, bool]] = []

    def key(self, keyval: int, shift: bool = False) -> bool:
        self.seen.append((keyval, shift))
        return ring_consumes(keyval, shift)


# -- not typing: the ring drives everything ---------------------------------


def test_the_ring_takes_tab_and_the_arrows_when_nobody_is_typing():
    for name in ("Tab", "Left", "Right", "Up", "Down", "ISO_Left_Tab"):
        assert ring_consumes(KEYVALS[name]) is True, name


def test_the_ring_takes_enter_and_space_when_nobody_is_typing():
    for name in ("Return", "KP_Enter", "space"):
        assert ring_consumes(KEYVALS[name]) is True, name


def test_shift_tab_still_walks_the_ring_backwards():
    assert ring_consumes(KEYVALS["Tab"], shift=True) is True


# -- typing: the entry gets its keys back ------------------------------------


def test_space_reaches_a_text_box_because_it_is_a_word_separator():
    """The whole reason this module exists."""
    assert ring_consumes(KEYVALS["space"], typing=True) is False


def test_the_arrows_reach_a_text_box_so_the_caret_can_move():
    for name in ("Left", "Right", "Up", "Down"):
        assert ring_consumes(KEYVALS[name], typing=True) is False, name


def test_enter_reaches_a_text_box_so_it_can_commit():
    for name in ("Return", "KP_Enter", "ISO_Enter"):
        assert ring_consumes(KEYVALS[name], typing=True) is False, name


def test_tab_stays_the_ring_s_even_while_typing_so_there_is_a_way_out():
    """A6: the keyboard must be able to reach *and leave* every surface. If Tab
    went to the entry there would be no way off it without a mouse."""
    assert ring_consumes(KEYVALS["Tab"], typing=True) is True
    assert ring_consumes(KEYVALS["ISO_Left_Tab"], typing=True) is True
    assert ring_consumes(KEYVALS["Tab"], shift=True, typing=True) is True


# -- what is never ours ------------------------------------------------------


def test_escape_is_never_consumed_typing_or_not():
    """Back is the shell's, one screen up, in a fixed place (SDK section 3.4).
    An activity that handled Escape would have invented a second way out that
    is invisible, unlabelled and unspoken."""
    assert ring_consumes(ESCAPE) is False
    assert ring_consumes(ESCAPE, typing=True) is False


def test_backspace_is_never_consumed_typing_or_not():
    assert ring_consumes(BACKSPACE) is False
    assert ring_consumes(BACKSPACE, typing=True) is False


def test_an_ordinary_letter_key_is_never_the_ring_s():
    for keyval in (ord("a"), ord("z"), ord("I"), ord("!")):
        assert ring_consumes(keyval) is False
        assert ring_consumes(keyval, typing=True) is False


# -- the wrapper -------------------------------------------------------------


def test_the_guard_only_stands_aside_while_somebody_is_typing():
    ring = FakeRing()
    typing = {"now": False}
    guard_ring(ring, lambda: typing["now"])

    assert ring.key(KEYVALS["space"]) is True
    assert ring.seen == [(KEYVALS["space"], False)]

    typing["now"] = True
    assert ring.key(KEYVALS["space"]) is False
    # The original was never called for the key it stood aside on.
    assert ring.seen == [(KEYVALS["space"], False)]


def test_the_guard_still_lets_tab_through_to_the_ring_while_typing():
    ring = FakeRing()
    guard_ring(ring, lambda: True)
    assert ring.key(KEYVALS["Tab"]) is True
    assert ring.seen == [(KEYVALS["Tab"], False)]


def test_the_guard_can_be_taken_off_again():
    ring = FakeRing()
    original = ring.key
    restore = guard_ring(ring, lambda: True)
    assert ring.key != original
    restore()
    # A bound method is a fresh object on every access, so `is` would never
    # hold; what matters is that the instance attribute has gone and the
    # class's own method is what answers again.
    assert "key" not in vars(ring)
    assert ring.key == original


def test_the_move_and_activate_sets_do_not_overlap():
    assert not (MOVE & ACTIVATE)
    assert RING_ALWAYS <= MOVE
    assert ESCAPE not in MOVE and ESCAPE not in ACTIVATE
    assert BACKSPACE not in MOVE and BACKSPACE not in ACTIVATE


# -- and the other thing this machine must never do --------------------------


def test_kidnix_speech_off_silences_the_earcons_as_well_as_the_voice(monkeypatch):
    """AGENTS.md section 5: never make a sound on a developer's machine.

    ``KIDNIX_SPEECH`` already gives the shell a null voice. The earcons are a
    *second* audio path -- GStreamer straight to PipeWire -- and they do not read
    it, so the activity does: one variable, both channels. This is checked here,
    in a headless test, because the failure mode is somebody's speakers rather
    than a red test.
    """
    from letters_to_family.env import quiet

    for value in ("off", "OFF", "0", "false", "none", "null", " off "):
        monkeypatch.setenv("KIDNIX_SPEECH", value)
        assert quiet() is True, value
    for value in ("on", "1", "", "piper"):
        monkeypatch.setenv("KIDNIX_SPEECH", value)
        assert quiet() is False, value
    monkeypatch.delenv("KIDNIX_SPEECH", raising=False)
    assert quiet() is False
