"""Time: how long a sitting is, how much of a day there is, and when.

Four groups, in the order a parent thinks about them:

* **One sitting** -- the length, and the floor. The floor is shown rather than
  hidden because it is the thing that makes "+10 minutes on a rainy Saturday"
  safe: a grant too short to be a session used to start a sitting already
  inside "put your things away", which is the kindest control a parent has
  breaking the afternoon (forum #14, #46, #59).
* **A whole day** -- the budget, with the arithmetic shown. "60 minutes"
  divided by "25 minutes" is two sittings and a refusal, and a parent should be
  able to see that before their child does.
* **Bedtime** -- one wrap-around window, exactly as the shell reads it.
* **When it may be used at all** -- ``[[windows]]``. New, and honestly labelled:
  the panel writes it and the shell does not read it yet.

The ending ritual's two windows are here too, under an expander, because
Dan asked to lengthen them ("can I make the ending longer?") and because they
are the one pair of numbers in this tab that are **ceilings** rather than
settings -- the real windows are 20% and 10% of what was actually granted.
"""

from __future__ import annotations

from dataclasses import replace

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk  # noqa: E402

from .. import model as M  # noqa: E402
from . import common  # noqa: E402
from .state import PanelState  # noqa: E402

TITLE = "Time"
ICON = "alarm-symbolic"


class TimePage(Adw.PreferencesPage):
    def __init__(self, state: PanelState) -> None:
        super().__init__(title=TITLE, icon_name=ICON)
        self.state = state
        self._groups: list[Adw.PreferencesGroup] = []
        self._budget_note: Gtk.Label | None = None
        self.refresh()

    def refresh(self) -> None:
        for group in self._groups:
            self.remove(group)
        self._groups = []
        self.state.loading = True
        try:
            self._build()
        finally:
            self.state.loading = False

    # -- building --

    def _build(self) -> None:
        time = self.state.panel.time

        sitting = Adw.PreferencesGroup(
            title="One sitting",
            description=(
                "How long the computer stays on once it starts. The computer "
                "ends it, not you: a warning first, then 'put your things away', "
                "then goodbye."
            ),
        )
        sitting.add(
            self._spin(
                "How long a sitting lasts",
                f"{M.MIN_SESSION_MINUTES} to {M.MAX_SESSION_MINUTES} minutes. "
                "25 is a precaution, not a scientific threshold -- nobody knows "
                "the right number.",
                time.length_minutes,
                M.MIN_SESSION_MINUTES,
                M.MAX_SESSION_MINUTES,
                lambda v: self._set_time(length_minutes=v),
            )
        )
        sitting.add(
            self._spin(
                "The shortest sitting there is",
                "Below this the computer will not start at all -- it says a warm "
                "no at the door instead of beginning a session that opens inside "
                "its own ending. This is also the smallest amount of extra time "
                "the grown-up gate will add. Never below "
                f"{M.ABSOLUTE_FLOOR_MINUTES} minutes.",
                time.min_session_minutes,
                M.ABSOLUTE_FLOOR_MINUTES,
                M.MAX_SESSION_MINUTES,
                lambda v: self._set_time(min_session_minutes=v),
            )
        )
        self._add(sitting)

        day = Adw.PreferencesGroup(
            title="A whole day",
            description=(
                "The ceiling across the day, per child. It refills at 4 in the "
                "morning, not at midnight: a child awake at half past twelve is "
                "still having last night's evening."
            ),
        )
        day.add(
            self._spin(
                "Minutes a day",
                "",
                time.daily_budget_minutes,
                M.MIN_DAILY_BUDGET_MINUTES,
                M.MAX_DAILY_BUDGET_MINUTES,
                lambda v: self._set_time(daily_budget_minutes=v),
                step=5,
            )
        )
        self._budget_note = Gtk.Label()
        self._budget_note.set_wrap(True)
        self._budget_note.set_xalign(0.0)
        self._budget_note.add_css_class("dim-label")
        self._budget_note.set_margin_start(6)
        self._budget_note.set_margin_top(4)
        row = Adw.PreferencesRow()
        row.set_activatable(False)
        row.set_child(self._budget_note)
        day.add(row)
        self._update_budget_note()
        self._add(day)

        bedtime = Adw.PreferencesGroup(
            title="Bedtime",
            description=(
                "Between these two times the computer shows a sleeping screen "
                "instead of starting. A grown-up can still unlock it from the PIN "
                "gate. Set both to the same time to switch bedtime off."
            ),
        )
        bedtime.add(
            self._clock(
                "Stops at",
                time.bedtime_start,
                lambda v: self._set_time(bedtime_start=v),
            )
        )
        bedtime.add(
            self._clock(
                "Starts again at",
                time.bedtime_end,
                lambda v: self._set_time(bedtime_end=v),
            )
        )
        if time.bedtime_off:
            bedtime.add(common.note_row("Bedtime is switched off on this machine."))
        self._add(bedtime)

        self._add(self._windows_group())
        self._add(self._ending_group())

    def _windows_group(self) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup(
            title="When it may be used at all",
            description=(
                "Weekday and weekend windows -- 'after school but before tea', "
                "'weekends after lunch'. Outside them the computer rests, the "
                "same way it does at bedtime."
            ),
        )
        add = common.button("Add a window")
        add.connect("clicked", self._on_add_window)
        group.set_header_suffix(add)

        group.add(
            common.note_row(
                "Not switched on yet. The panel writes these down and the child's "
                "screen does not read them yet, so setting one changes nothing "
                "today -- it will start working with an update, without you "
                "having to set it up again. Bedtime above is in force now.",
                warning=True,
            )
        )
        for index, window in enumerate(self.state.panel.time.windows):
            group.add(self._window_row(index, window))
        return group

    def _window_row(self, index: int, window: M.ScheduleWindow) -> Adw.PreferencesRow:
        row = Adw.ExpanderRow()
        common.plain(row, window.label or _window_title(window), f"{window.start} to {window.end}")
        remove = common.icon_button("user-trash-symbolic", "Remove this window")
        remove.connect("clicked", lambda _b, i=index: self._remove_window(i))
        row.add_suffix(remove)

        days = Adw.ActionRow(title="Days")
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        box.set_valign(Gtk.Align.CENTER)
        for day in M.DAYS:
            toggle = Gtk.ToggleButton(label=day[:1].upper() + day[1:])
            toggle.set_active(day in window.days)
            toggle.add_css_class("flat")
            toggle.connect(
                "toggled",
                lambda button, i=index, d=day: self._toggle_day(i, d, button.get_active()),
            )
            box.append(toggle)
        days.add_suffix(box)
        row.add_row(days)

        row.add_row(
            self._clock("From", window.start, lambda v, i=index: self._set_window(i, start=v))
        )
        row.add_row(self._clock("Until", window.end, lambda v, i=index: self._set_window(i, end=v)))
        if window.spans_midnight:
            row.add_row(
                common.note_row(
                    "This window ends the following morning. Bedtime still applies "
                    "on top of it and the stricter of the two wins."
                )
            )
        return common.plain(row)

    def _ending_group(self) -> Adw.PreferencesGroup:
        time = self.state.panel.time
        group = Adw.PreferencesGroup(
            title="How the ending goes",
            description=(
                "Two beats, always the same, in the same words: the computer "
                "offers to finish, then asks for things to be put away, then says "
                "goodbye and reminds your child what comes next.\n\n"
                "Both numbers are ceilings, not fixed points. The real warnings "
                "are a fifth and a tenth of the sitting that was actually granted, "
                "so a short session gets a short ending rather than spending half "
                "of itself saying goodbye."
            ),
        )
        group.add(
            self._spin(
                "At most, warn this many minutes before the end",
                "",
                time.ending_offer_minutes,
                1,
                10,
                lambda v: self._set_time(ending_offer_minutes=v),
            )
        )
        group.add(
            self._spin(
                "At most, ask to put things away this many minutes before",
                "",
                time.put_away_minutes,
                1,
                10,
                lambda v: self._set_time(put_away_minutes=v),
            )
        )
        return group

    # -- widgets --

    def _spin(
        self,
        title: str,
        subtitle: str,
        value: int,
        low: int,
        high: int,
        setter,
        step: int = 1,
    ) -> Adw.SpinRow:
        row = Adw.SpinRow.new_with_range(low, high, step)
        row.set_title(title)
        if subtitle:
            row.set_subtitle(subtitle)
        row.set_value(value)
        row.connect("notify::value", lambda spin, _p: setter(int(spin.get_value())))
        return common.plain(row)

    def _clock(self, title: str, value: str, setter) -> Adw.EntryRow:
        row = Adw.EntryRow(title=title)
        row.set_text(value)
        row.set_show_apply_button(False)

        def changed(entry: Adw.EntryRow) -> None:
            text = entry.get_text().strip()
            if M.parse_clock(text) is None:
                entry.add_css_class("error")
                return
            entry.remove_css_class("error")
            setter(text)

        row.connect("changed", changed)
        return common.plain(row)

    def _add(self, group: Adw.PreferencesGroup) -> None:
        self.add(group)
        self._groups.append(group)

    # -- edits --

    def _set_time(self, **changes) -> None:
        self.state.panel.time = replace(self.state.panel.time, **changes)
        self.state.touch()
        self._update_budget_note()

    def _update_budget_note(self) -> None:
        if self._budget_note is None:
            return
        time = self.state.panel.time
        sittings = time.sittings_in_budget()
        left = time.daily_budget_minutes - sittings * time.length_minutes
        if sittings <= 0:
            text = (
                "That is less than one whole sitting, so every session will be "
                "cut short by the day's total."
            )
        else:
            tail = (
                f" and {left} minutes over, which is less than the {time.min_session_minutes}-minute "
                "floor, so it is refused rather than handed out as a stub of a session"
                if 0 < left < time.min_session_minutes
                else f" and {left} minutes over"
                if left
                else ""
            )
            plural = "" if sittings == 1 else "s"
            text = (
                f"{time.daily_budget_minutes} minutes is {sittings} full "
                f"{time.length_minutes}-minute sitting{plural}{tail}."
            )
        self._budget_note.set_label(text)

    def _on_add_window(self, _button: Gtk.Button) -> None:
        existing = self.state.panel.time.windows
        weekend = any(set(w.days) == set(M.WEEKEND) for w in existing)
        window = (
            M.ScheduleWindow(days=M.WEEKDAYS, start="15:30", end="18:00", label="After school")
            if not existing
            else M.ScheduleWindow(days=M.WEEKEND, start="09:00", end="18:00", label="Weekends")
            if not weekend
            else M.ScheduleWindow(days=(), start="09:00", end="18:00")
        )
        self.state.panel.time = replace(self.state.panel.time, windows=(*existing, window))
        self.state.touch()
        self.refresh()

    def _remove_window(self, index: int) -> None:
        windows = list(self.state.panel.time.windows)
        if 0 <= index < len(windows):
            del windows[index]
            self.state.panel.time = replace(self.state.panel.time, windows=tuple(windows))
            self.state.touch()
            self.refresh()

    def _set_window(self, index: int, **changes) -> None:
        windows = list(self.state.panel.time.windows)
        if not 0 <= index < len(windows):
            return
        windows[index] = replace(windows[index], **changes)
        self.state.panel.time = replace(self.state.panel.time, windows=tuple(windows))
        self.state.touch()

    def _toggle_day(self, index: int, day: str, on: bool) -> None:
        windows = list(self.state.panel.time.windows)
        if not 0 <= index < len(windows):
            return
        days = set(windows[index].days)
        days.add(day) if on else days.discard(day)
        ordered = tuple(d for d in M.DAYS if d in days)
        windows[index] = replace(windows[index], days=ordered)
        self.state.panel.time = replace(self.state.panel.time, windows=tuple(windows))
        self.state.touch()


def _window_title(window: M.ScheduleWindow) -> str:
    days = set(window.days)
    if days == set(M.WEEKDAYS):
        return "Weekdays"
    if days == set(M.WEEKEND):
        return "Weekends"
    if days == set(M.DAYS):
        return "Every day"
    if not days:
        return "No days chosen"
    return ", ".join(d.title() for d in M.DAYS if d in days)


__all__ = ["TimePage"]
