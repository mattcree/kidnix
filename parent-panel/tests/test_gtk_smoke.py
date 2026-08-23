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

FLATPAK = """\
schema = 1
id = "turbowarp"
name = "Make a game"
goal = "Blocks that make something move."
order = 30
category = "make"
age_min = 6
age_max = 10
exec = ["flatpak", "run", "org.turbowarp.TurboWarp"]
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
        photo_dir=tmp_path / "photos",
        # This laptop has neither Tux Paint nor TuxMath, and the Activities tab
        # now draws a note instead of a switch for a program that is not there.
        # Which is right on a real machine and useless in a widget test, so the
        # fixture answers the question itself. `installed_check` below is where
        # the other half is asserted.
        installed=lambda entry: True,
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


def test_time_page_says_what_a_schedule_window_actually_does(state):
    """It used to say "Not switched on yet ... setting one changes nothing
    today". The shell has read `[[windows]]` for some time, and that sentence
    is the dangerous kind of stale: a parent who believes it sets one
    carelessly and locks their child out of the machine."""
    page = time_tab.TimePage(state)
    text = " ".join(w.get_label() for w in rows(page) if isinstance(w, Gtk.Label) and w.get_label())
    assert "Not switched on yet" not in text
    assert "no windows set" in text.lower()

    state.panel.time = replace(
        state.panel.time,
        windows=(M.ScheduleWindow(days=M.WEEKEND, start="09:30", end="12:00"),),
    )
    page.refresh()
    text = " ".join(w.get_label() for w in rows(page) if isinstance(w, Gtk.Label) and w.get_label())
    assert "These are in force" in text
    assert "will not start a session at all" in text


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


def test_family_page_names_the_outbox_and_the_inbox(state):
    """It used to say "'send to family' is not built". Letters ships, this list
    is what it reads, and the sneakernet -- a folder a grown-up posts from and
    a folder they drop replies into -- was documented nowhere a parent looks."""
    page = family_tab.FamilyPage(state)
    text = " ".join(w.get_label() for w in rows(page) if isinstance(w, Gtk.Label) and w.get_label())
    assert "not built" not in text
    assert "/var/lib/kidnix/outbox/" in text
    assert "/var/lib/kidnix/inbox/" in text
    assert "YOU ARE THE POSTMAN" in text


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


def test_roll_back_is_dead_until_there_is_something_to_roll_back_to(state, monkeypatch):
    """The page already worked out `can_roll_back` and drew a live-looking
    button beside it either way. On a machine that has never been updated
    bootc names no rollback, so the press failed with bootc's own words at the
    exact moment a parent is pressing it because something is wrong."""
    monkeypatch.setattr(system, "bootc_status", lambda *a, **k: system.BootcStatus(raw_ok=True))
    page = updates_tab.UpdatesPage(state)
    assert page._rollback_button is not None
    assert not page._rollback_button.get_sensitive()
    assert "nothing to go back to" in page._rollback_row.get_subtitle()


def test_roll_back_wakes_up_when_the_previous_version_is_on_the_disk(state, monkeypatch):
    monkeypatch.setattr(
        system,
        "bootc_status",
        lambda *a, **k: system.BootcStatus(
            booted_image="ghcr.io/mattcree/kidnix:latest",
            rollback_image="ghcr.io/mattcree/kidnix:latest",
            rollback_version="0.1.0",
            raw_ok=True,
        ),
    )
    page = updates_tab.UpdatesPage(state)
    assert page._rollback_button.get_sensitive()
    assert "0.1.0" in page._rollback_row.get_subtitle()


def test_an_activity_that_is_not_installed_is_a_note_and_not_a_switch(tmp_path):
    """TurboWarp is a Flatpak that installs on first boot, so between the image
    being written and that finishing there is a manifest for a program that is
    not there. A switch over it says "this is yours to decide" when there is
    nothing yet to decide."""
    (tmp_path / "tuxpaint.toml").write_text(MANIFEST)
    (tmp_path / "turbowarp.toml").write_text(FLATPAK)
    panel = M.PanelModel()
    panel.add_child("Rosie", age_band="4-5")
    missing = PanelState(
        panel=panel,
        activities=catalogue.load(tmp_path),
        runner=stub_runner,
        etc=tmp_path,
        usr=tmp_path,
        synchronous=True,
        installed=lambda entry: entry.id != "turbowarp",
    )
    page = activities_tab.ActivitiesPage(missing)
    assert _row_titled(page, "Draw") is not None
    assert _row_titled(page, "Make a game") is None
    text = " ".join(w.get_label() for w in rows(page) if isinstance(w, Gtk.Label) and w.get_label())
    assert "Make a game is not on this machine" in text
    assert "installs itself the first time" in text


def test_the_installed_check_is_the_real_one_by_default(tmp_path):
    """The seam above must not be the only implementation: `catalogue` really
    does answer the question, and it is the same two questions the shell asks
    (`exec[0]` on PATH, plus `flatpak info` for a flatpak)."""
    entry = catalogue.parse_manifest(
        {"id": "x", "name": "X", "exec": ["flatpak", "run", "org.example.App"]}, tmp_path / "x.toml"
    )
    assert entry.flatpak_ref == "org.example.App"
    assert catalogue.is_installed(entry, which=lambda _p: None, flatpak=lambda _r: True) is False
    assert (
        catalogue.is_installed(entry, which=lambda _p: "/usr/bin/flatpak", flatpak=lambda _r: False)
        is False
    )
    assert (
        catalogue.is_installed(entry, which=lambda _p: "/usr/bin/flatpak", flatpak=lambda _r: True)
        is True
    )


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
