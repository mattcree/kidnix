"""Activities: which pictures exist, and the switch that keeps them still.

Two things a parent came here for, and the second one is Dan's:

    "One switch called 'keep everything the same': a frozen grid, no activity's
    own dialogue reaching him, adjustable warning times -- and no config file to
    get it."

So **Keep the grid the same** is the first control on the tab, it is on by
default, and turning it *off* is what exposes the progressive-disclosure
settings. That is the inverse of how the shell's key reads (``show_everything``)
and it is the right way round for the person reading it: a parent is choosing
predictability, not choosing a research feature.

Under it, one tick-box per activity with the **picture the child actually sees**
and the manifest's own ``goal`` line, which is the schema's one sentence
written for a grown-up. Shelf children ("Letters and numbers" has eighteen)
hang under their shelf in an expander, so removing *Ballcatch* and keeping the
rest is possible without opening anything.
"""

from __future__ import annotations

from dataclasses import replace

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk  # noqa: E402

from .. import catalogue  # noqa: E402
from .. import model as M  # noqa: E402
from . import common  # noqa: E402
from .state import PanelState  # noqa: E402

TITLE = "Activities"
ICON = "view-grid-symbolic"


class ActivitiesPage(Adw.PreferencesPage):
    def __init__(self, state: PanelState) -> None:
        super().__init__(title=TITLE, icon_name=ICON)
        self.state = state
        self._groups: list[Adw.PreferencesGroup] = []
        #: Which child's list is being edited. Empty means the first one.
        self.child_id = ""
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
        self._add(self._grid_group())

        children = self.state.panel.active_children
        if not children:
            group = Adw.PreferencesGroup(title="Which pictures your child sees")
            group.add(
                common.note_row(
                    "Add a child on the Children tab first -- an allow-list belongs to somebody.",
                    warning=True,
                )
            )
            self._add(group)
            return

        if self.child_id not in {c.id for c in children}:
            self.child_id = children[0].id
        child = self.state.panel.child(self.child_id)
        assert child is not None

        self._add(self._who_group(children, child))
        self._add(self._tiles_group(child))

    def _grid_group(self) -> Adw.PreferencesGroup:
        home = self.state.panel.home
        group = Adw.PreferencesGroup(
            title="How the screen behaves",
            description=(
                "A new button appearing without warning is not a delight; for a "
                "child who navigates by position it is a ruined afternoon. This "
                "is on by default and most families should leave it on."
            ),
        )
        keep = Adw.SwitchRow(title="Keep the grid the same")
        keep.set_subtitle(
            "Every picture your child is allowed is on the screen from the first "
            "day, always in the same place. 'All done' keeps its own square in "
            "the corner and never moves, whatever this is set to."
        )
        keep.set_active(home.keep_the_grid_the_same)
        keep.connect("notify::active", self._on_keep_toggled)
        group.add(keep)

        if not home.keep_the_grid_the_same:
            group.add(
                common.note_row(
                    "The screen will grow. This suits a child meeting a computer "
                    "for the first time -- five things, learned, then a sixth -- "
                    "and suits almost nobody else.",
                    warning=True,
                )
            )
            row = Adw.SpinRow.new_with_range(2, 24, 1)
            row.set_title("Pictures on the first day")
            row.set_subtitle("Counting 'All done', which is always there.")
            row.set_value(home.initial_tiles)
            row.connect(
                "notify::value",
                lambda spin, _p: self._set_home(initial_tiles=int(spin.get_value())),
            )
            group.add(row)

            every = Adw.SpinRow.new_with_range(1, 20, 1)
            every.set_title("One more picture after every")
            every.set_subtitle(
                "Completed sessions. Nothing shows this count to your child, "
                "nothing resets it, and it is not a streak."
            )
            every.set_value(home.reveal_every_sessions)
            every.connect(
                "notify::value",
                lambda spin, _p: self._set_home(reveal_every_sessions=int(spin.get_value())),
            )
            group.add(every)
        return group

    def _who_group(self, children: list[M.Child], child: M.Child) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup(title="Whose list")
        row = Adw.ComboRow(title="Choosing for")
        names = Gtk.StringList()
        for candidate in children:
            names.append(candidate.name)
        row.set_model(names)
        row.set_selected([c.id for c in children].index(child.id))
        row.add_prefix(common.identity_badge(child, size=28))
        row.connect(
            "notify::selected",
            lambda combo, _p: self._pick_child(children[combo.get_selected()].id),
        )
        group.add(row)

        if self.state.panel.allow_list_is_shared:
            group.add(
                common.note_row(
                    "This machine has more than one child and they have been given "
                    "different lists. Until the child's screen learns to read a "
                    "list per child, it allows anything either of them is allowed. "
                    "Ages still apply separately, so the youngest does not see the "
                    "six-and-over activities.",
                    warning=True,
                )
            )
        return group

    def _tiles_group(self, child: M.Child) -> Adw.PreferencesGroup:
        allowed = set(child.allowed_activity_ids)
        everything = not allowed
        band = _band(child)

        group = Adw.PreferencesGroup(
            title=f"What {common.escape(child.name)} can open",
            description=(
                "Untick anything you would rather was not there. Unticking "
                "everything means everything is allowed -- a screen with nothing "
                "on it but 'All done' is not a setting anyone wants by accident."
            ),
        )
        toggle = common.button("Allow everything" if not everything else "Choose a few")
        toggle.connect("clicked", lambda _b, c=child: self._bulk(c, everything))
        group.set_header_suffix(toggle)

        if everything:
            group.add(
                common.note_row(
                    f"Everything this machine has, that suits ages "
                    f"{child.age_band or 'any'}, is on {common.escape(child.name)}'s screen."
                )
            )

        entries = [e for e in self.state.activities.top_level() if not e.is_shelf_child]
        if not entries:
            group.add(
                common.note_row(
                    "This machine has no activity manifests in "
                    f"{catalogue.SYSTEM_ACTIVITY_DIR}. That is normal on a "
                    "development laptop and a fault on a child's computer."
                )
            )
        for entry in entries:
            group.add(self._entry_row(entry, child, allowed, band))

        for path, why in self.state.activities.broken:
            group.add(common.note_row(f"{path.name} could not be read: {why}", warning=True))
        return group

    def _entry_row(
        self,
        entry: catalogue.Entry,
        child: M.Child,
        allowed: set[str],
        band: tuple[int, int] | None,
    ) -> Adw.PreferencesRow:
        suits = entry.suits(band)
        subtitle = entry.goal or entry.audio_label or entry.category_label()
        if not suits:
            subtitle = f"For ages {entry.age_band_label}, so it does not appear for {child.name}. {subtitle}"
        if entry.content_required:
            subtitle = f"{subtitle} There is nothing in it until a grown-up puts something in."

        children_of = self.state.activities.children_of(entry.id)
        row: Adw.PreferencesRow
        if children_of:
            row = Adw.ExpanderRow()
            common.plain(row, entry.name, subtitle)
            switch = Gtk.Switch()
            switch.set_valign(Gtk.Align.CENTER)
            switch.set_active(entry.id in allowed or not allowed)
            switch.set_sensitive(suits)
            switch.connect(
                "notify::active",
                lambda sw, _p, e=entry, c=child: self._toggle(c, e.id, sw.get_active()),
            )
            row.add_suffix(switch)
            for group_name, kids in _grouped(children_of):
                if group_name:
                    row.add_row(common.note_row(group_name))
                for kid in kids:
                    row.add_row(self._child_entry_row(kid, child, allowed, band))
        else:
            row = Adw.SwitchRow()
            common.plain(row, entry.name, subtitle)
            row.set_active(entry.id in allowed or not allowed)
            row.set_sensitive(suits)
            row.connect(
                "notify::active",
                lambda sw, _p, e=entry, c=child: self._toggle(c, e.id, sw.get_active()),
            )
        row.add_prefix(common.activity_image(entry))
        return common.plain(row)

    def _child_entry_row(
        self,
        entry: catalogue.Entry,
        child: M.Child,
        allowed: set[str],
        band: tuple[int, int] | None,
    ) -> Adw.PreferencesRow:
        row = Adw.SwitchRow()
        common.plain(row, entry.name, entry.goal or entry.audio_label or "")
        row.add_prefix(common.activity_image(entry, size=24))
        row.set_active(entry.id in allowed or not allowed)
        row.set_sensitive(entry.suits(band))
        row.connect(
            "notify::active",
            lambda sw, _p, e=entry, c=child: self._toggle(c, e.id, sw.get_active()),
        )
        return common.plain(row)

    # -- edits --

    def _on_keep_toggled(self, switch: Adw.SwitchRow, _param: object) -> None:
        self._set_home(keep_the_grid_the_same=switch.get_active())
        self.refresh()

    def _set_home(self, **changes) -> None:
        self.state.panel.home = replace(self.state.panel.home, **changes)
        self.state.touch()

    def _pick_child(self, child_id: str) -> None:
        self.child_id = child_id
        self.refresh()

    def _toggle(self, child: M.Child, activity_id: str, on: bool) -> None:
        if self.state.loading:
            return
        current = self.state.panel.child(child.id)
        if current is None:
            return
        allowed = set(current.allowed_activity_ids)
        if not allowed:
            # "Everything" is the empty list. The first untick has to turn that
            # into an explicit list of everything else, or unticking one thing
            # would silently allow only that thing.
            if on:
                return
            allowed = {e.id for e in self.state.activities.entries}
        allowed.add(activity_id) if on else allowed.discard(activity_id)
        if allowed == {e.id for e in self.state.activities.entries}:
            allowed = set()  # back to "everything", the way the shell reads it
        self.state.panel.set_allowed(child.id, tuple(allowed))
        self.state.touch()
        self.refresh()

    def _bulk(self, child: M.Child, everything: bool) -> None:
        if everything:
            # "Choose a few": start from what is on the screen now, so the first
            # thing a parent does is remove one rather than rebuild the lot.
            self.state.panel.set_allowed(
                child.id, tuple(e.id for e in self.state.activities.entries)
            )
        else:
            self.state.panel.set_allowed(child.id, ())
        self.state.touch()
        self.refresh()

    def _add(self, group: Adw.PreferencesGroup) -> None:
        self.add(group)
        self._groups.append(group)


def _band(child: M.Child) -> tuple[int, int] | None:
    text = (child.age_band or "").strip()
    if not text:
        return None
    try:
        parts = [int(p) for p in text.split("-")]
    except ValueError:
        return None
    if len(parts) == 1:
        return (parts[0], parts[0])
    if len(parts) == 2 and parts[0] <= parts[1]:
        return (parts[0], parts[1])
    return None


def _grouped(entries: list[catalogue.Entry]) -> list[tuple[str, list[catalogue.Entry]]]:
    """Shelf children under their own headings, in manifest order.

    A shelf of eighteen small games is six short answers rather than one long
    one, and the headings come off the child manifests themselves.
    """
    out: list[tuple[str, list[catalogue.Entry]]] = []
    for entry in entries:
        name = entry.group_name
        if out and out[-1][0] == name:
            out[-1][1].append(entry)
        else:
            out.append((name, [entry]))
    return out


__all__ = ["ActivitiesPage"]
