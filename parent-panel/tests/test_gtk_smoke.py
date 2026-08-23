"""Widget construction smoke tests. Needs a display; skips without one.

**Run these under Broadway, never on a desktop** (AGENTS.md §5)::

    gtk4-broadwayd :10 &
    GDK_BACKEND=broadway BROADWAY_DISPLAY=:10 uv run pytest tests/test_gtk_smoke.py

They build every page against a made-up household and assert the things that
only exist once a widget tree does: that each tab has rows, that the
"keep the grid the same" switch is the shell's ``show_everything``, that the
banner appears when something is unsaved and blocks Apply when something is
wrong, and that the update button is disabled when the machine cannot verify a
signature.

Nothing here forks a process: :class:`PanelState` is handed a runner that
returns a canned answer, which is the reason it is an argument at all.
"""

from __future__ import annotations

import os
from dataclasses import replace

import pytest

gi = pytest.importorskip("gi")

if not (
    os.environ.get("WAYLAND_DISPLAY")
    or os.environ.get("DISPLAY")
    or os.environ.get("BROADWAY_DISPLAY")
):
    pytest.skip("no display; skipping GTK widget tests", allow_module_level=True)

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk  # noqa: E402

if not Gtk.init_check():  # pragma: no cover - display present but unusable
    pytest.skip("GTK could not open the display", allow_module_level=True)

Adw.init()

from kidnix_parent_panel import catalogue, system  # noqa: E402
from kidnix_parent_panel import model as M  # noqa: E402
from kidnix_parent_panel.ui import activities as activities_tab  # noqa: E402
from kidnix_parent_panel.ui import children as children_tab  # noqa: E402
from kidnix_parent_panel.ui import family as family_tab  # noqa: E402
from kidnix_parent_panel.ui import sound as sound_tab  # noqa: E402
from kidnix_parent_panel.ui import things as things_tab  # noqa: E402
from kidnix_parent_panel.ui import timing as time_tab  # noqa: E402
from kidnix_parent_panel.ui import updates as updates_tab  # noqa: E402
from kidnix_parent_panel.ui.app import ParentPanelApplication, ParentPanelWindow  # noqa: E402
from kidnix_parent_panel.ui.state import PanelState  # noqa: E402

MANIFEST = """\
schema = 1
id = "tuxpaint"
name = "Draw"
goal = "Making pictures -- no right answers."
order = 10
icon = "kidnix-act-tuxpaint"
icon_kind = "icon-name"
category = "make"
age_min = 3
age_max = 10
exec = ["tuxpaint"]
"""

OLDER = """\
schema = 1
id = "tuxmath"
name = "Number game"
goal = "Arithmetic against a clock."
order = 20
category = "learn"
age_min = 6
age_max = 10
exec = ["tuxmath"]
"""


def stub_runner(argv, stdin=None, timeout=0):
    return system.Completed(0, "wrote /etc/kidnix/parent.toml\n")


@pytest.fixture
def state(tmp_path):
    (tmp_path / "tuxpaint.toml").write_text(MANIFEST)
    (tmp_path / "tuxmath.toml").write_text(OLDER)
    panel = M.PanelModel()
    panel.add_child("Rosie", age_band="4-5")
    panel.add_child("Sam", age_band="6-8")
    return PanelState(
        panel=panel,
        activities=catalogue.load(tmp_path),
        runner=stub_runner,
        etc=tmp_path,
        usr=tmp_path,
        # Inline: pytest has no GTK main loop, so a thread's answer would never
        # come back and every assertion after a button press would race it.
        synchronous=True,
    )


def rows(widget) -> list:
    """Every descendant of ``widget``, flattened. Cheap, and enough."""
    out = []
    child = widget.get_first_child()
    while child is not None:
        out.append(child)
        out.extend(rows(child))
        child = child.get_next_sibling()
    return out


def titles(page) -> list[str]:
    return [
        w.get_title() for w in rows(page) if isinstance(w, Adw.PreferencesRow) and w.get_title()
    ]


# --- the pages build --------------------------------------------------------


def test_children_page_lists_every_child(state):
    page = children_tab.ChildrenPage(state)
    assert "Rosie" in titles(page)
    assert "Sam" in titles(page)


def test_children_page_shows_removed_children_separately(state):
    state.panel.retire_child("sam")
    page = children_tab.ChildrenPage(state)
    assert any("their things are kept" in (t or "").lower() for t in _subtitles(page))


def test_time_page_has_the_four_numbers(state):
    page = time_tab.TimePage(state)
    found = " ".join(titles(page))
    assert "How long a sitting lasts" in found
    assert "The shortest sitting there is" in found
    assert "Minutes a day" in found
    assert "Stops at" in found


def test_time_page_shows_the_budget_arithmetic(state):
    page = time_tab.TimePage(state)
    text = " ".join(w.get_label() for w in rows(page) if isinstance(w, Gtk.Label) and w.get_label())
    assert "2 full 25-minute sittings" in text


def test_time_page_says_the_windows_are_not_read_yet(state):
    page = time_tab.TimePage(state)
    text = " ".join(w.get_label() for w in rows(page) if isinstance(w, Gtk.Label) and w.get_label())
    assert "Not switched on yet" in text


def test_activities_page_shows_the_goal_line(state):
    page = activities_tab.ActivitiesPage(state)
    assert any("no right answers" in (s or "") for s in _subtitles(page))


def test_activities_page_greys_out_what_the_age_band_removes(state):
    page = activities_tab.ActivitiesPage(state)
    page.child_id = "rosie"
    page.refresh()
    number = _row_titled(page, "Number game")
    assert number is not None
    assert not number.get_sensitive()


def test_keep_the_grid_the_same_is_on_by_default(state):
    page = activities_tab.ActivitiesPage(state)
    keep = _row_titled(page, "Keep the grid the same")
    assert isinstance(keep, Adw.SwitchRow)
    assert keep.get_active()


def test_turning_the_grid_switch_off_reveals_the_disclosure_settings(state):
    page = activities_tab.ActivitiesPage(state)
    assert _row_titled(page, "Pictures on the first day") is None
    keep = _row_titled(page, "Keep the grid the same")
    keep.set_active(False)
    assert state.panel.home.show_everything is False
    assert _row_titled(page, "Pictures on the first day") is not None


def test_unticking_one_activity_leaves_the_others_allowed(state):
    page = activities_tab.ActivitiesPage(state)
    page.child_id = "sam"
    page.refresh()
    row = _row_titled(page, "Draw")
    row.set_active(False)
    allowed = state.panel.child("sam").allowed_activity_ids
    assert "tuxpaint" not in allowed
    assert "tuxmath" in allowed


def test_sound_page_has_calm_captions_and_a_voice(state):
    page = sound_tab.SoundPage(state)
    found = " ".join(titles(page))
    assert "Calm mode" in found
    assert "Show every spoken line as writing" in found
    assert "Which voice" in found
    assert "How fast it reads" in found


def test_sound_page_shows_the_length_scale(state):
    page = sound_tab.SoundPage(state)
    text = " ".join(w.get_label() for w in rows(page) if isinstance(w, Gtk.Label) and w.get_label())
    assert "1.10 times its ordinary pace" in text


def test_things_page_offers_copy_print_and_delete(state):
    page = things_tab.ThingsPage(state)
    found = " ".join(titles(page))
    assert "Copy everything to a folder" in found
    assert "Print a picture" in found
    assert "Delete everything they have made" in found


def test_family_page_says_nothing_sends_anything_yet(state):
    page = family_tab.FamilyPage(state)
    text = " ".join(w.get_label() for w in rows(page) if isinstance(w, Gtk.Label) and w.get_label())
    assert "Nothing sends anything yet" in text


def test_updates_page_carries_the_whole_honest_page(state):
    page = updates_tab.UpdatesPage(state)
    found = titles(page)
    for heading, _body in updates_tab.WHAT_IT_SENDS:
        assert heading in found


def test_the_update_button_is_disabled_when_nothing_can_be_verified(state, monkeypatch):
    monkeypatch.setattr(
        system,
        "signature_policy",
        lambda *a, **k: system.VerifyResult(False, reason="no key here"),
    )
    page = updates_tab.UpdatesPage(state)
    assert page._update_button is not None
    assert not page._update_button.get_sensitive()


def test_the_update_button_is_enabled_when_a_signature_would_be_checked(state, monkeypatch):
    monkeypatch.setattr(
        system,
        "signature_policy",
        lambda *a, **k: system.VerifyResult(True, key_path="/k.pub", key_present=True),
    )
    page = updates_tab.UpdatesPage(state)
    assert page._update_button.get_sensitive()


# --- the window ------------------------------------------------------------


def test_the_window_has_every_tab(state):
    app = ParentPanelApplication(state)
    window = ParentPanelWindow(app, state)
    assert set(window.pages) == {
        "children",
        "time",
        "activities",
        "sound",
        "things",
        "family",
        "updates",
    }


def test_apply_is_dead_until_something_changes(state):
    app = ParentPanelApplication(state)
    window = ParentPanelWindow(app, state)
    assert not window.apply_button.get_sensitive()
    state.touch()
    assert window.apply_button.get_sensitive()
    assert window.banner.get_revealed()


def test_a_bad_setting_blocks_apply_and_says_why(state):
    app = ParentPanelApplication(state)
    window = ParentPanelWindow(app, state)
    state.panel.time = replace(state.panel.time, length_minutes=999)
    state.touch()
    assert not window.apply_button.get_sensitive()
    assert "45 minutes" in window.banner.get_title()


def test_applying_clears_the_banner(state):
    app = ParentPanelApplication(state)
    window = ParentPanelWindow(app, state)
    state.touch()
    window._on_apply(window.apply_button)
    assert not state.dirty
    assert not window.banner.get_revealed()


def test_building_the_pages_does_not_mark_the_machine_dirty(state):
    app = ParentPanelApplication(state)
    window = ParentPanelWindow(app, state)
    assert not state.dirty
    assert not window.banner.get_revealed()


# --- helpers ---------------------------------------------------------------


def _subtitles(page) -> list[str]:
    out = []
    for widget in rows(page):
        getter = getattr(widget, "get_subtitle", None)
        if getter is not None:
            value = getter()
            if value:
                out.append(value)
    return out


def _row_titled(page, title: str):
    for widget in rows(page):
        if isinstance(widget, Adw.PreferencesRow) and widget.get_title() == title:
            return widget
    return None
