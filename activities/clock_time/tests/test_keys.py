"""What a key press means. A table, so nobody has to guess.

SYNTHESIS A6 -- the keyboard is never *required* -- and the SDK's own rule that
Escape belongs to the shell (``docs/design/activity-sdk.md`` section 3.4). Both
are assertions here rather than comments, because the second one is a rule an
activity can break by accident and a child would never find the second way out
it invented.
"""

from __future__ import annotations

import pytest

from clock_time.keys import KEY_NAMES, Action, Screen, action_for


@pytest.mark.parametrize("name", ["Right", "KP_Right", "Up", "KP_Up"])
def test_right_and_up_move_the_minute_hand_forwards(name):
    assert action_for(name, Screen.CLOCK) is Action.MINUTE_FORWARD


@pytest.mark.parametrize("name", ["Left", "KP_Left", "Down", "KP_Down"])
def test_left_and_down_move_it_back(name):
    assert action_for(name, Screen.CLOCK) is Action.MINUTE_BACK


def test_space_is_now_on_the_clock_screen():
    assert action_for("space", Screen.CLOCK) is Action.NOW
    assert action_for("KP_Space", Screen.CLOCK) is Action.NOW


def test_space_starts_and_stops_on_the_minute_screen():
    assert action_for("space", Screen.MINUTE) is Action.START_OR_STOP


def test_the_arrows_are_not_the_minute_screens():
    """There is nothing round to step on that screen, so they fall through to
    the SDK's ring."""
    for name in ("Left", "Right", "Up", "Down"):
        assert action_for(name, Screen.MINUTE) is None


def test_escape_is_never_ours_on_either_screen():
    """Back is a band button, in another process, and it is the only way out of
    an activity by design (spec S3)."""
    for screen in Screen:
        assert action_for("Escape", screen) is None


def test_backspace_is_not_ours_either():
    for screen in Screen:
        assert action_for("BackSpace", screen) is None


def test_tab_stays_with_the_ring_so_nothing_becomes_unreachable():
    """Taking the arrows costs arrow-key ring navigation. A6 survives because
    Tab and Shift-Tab still walk every control."""
    for screen in Screen:
        assert action_for("Tab", screen) is None
        assert action_for("ISO_Left_Tab", screen) is None


def test_enter_stays_with_the_ring_too():
    for screen in Screen:
        assert action_for("Return", screen) is None
        assert action_for("KP_Enter", screen) is None


@pytest.mark.parametrize("name", ["a", "F1", "Shift_L", "", "Menu", "Control_L"])
def test_anything_else_is_not_ours(name):
    assert action_for(name, Screen.CLOCK) is None


def test_the_declared_table_is_the_whole_table():
    """KEY_NAMES exists so a test can check completeness without importing Gdk."""
    claimed = {name for name in KEY_NAMES if action_for(name, Screen.CLOCK) is not None}
    assert claimed == set(KEY_NAMES)


def test_the_default_screen_is_the_clock():
    assert action_for("space") is Action.NOW
