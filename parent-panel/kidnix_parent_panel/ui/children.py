"""Children: the tab that answers Priya.

    "Two named children, each with their own colour, time budget and My
    Things -- set up from a screen, not a file."

One row per child: their colour pair with the shape badge, their name, their
age band, and the two arrows that decide the order the faces appear in on
"Who's here?". Add, rename, reorder, remove.

**Remove is not delete, and the row says so.** Removing a child takes their
face off "Who's here?" and leaves every drawing exactly where it is
(``[[retired_profiles]]``; see :mod:`kidnix_parent_panel.model`). The only
thing on this machine that deletes a child's work is ``kidnix-wipe``, on the
Their-things tab, behind two confirmations and a typed word. A parent who meant
"they have outgrown this" must not lose four years of pictures to a button.
"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk  # noqa: E402

from .. import model as M  # noqa: E402
from . import common  # noqa: E402
from .state import PanelState  # noqa: E402

TITLE = "Children"
ICON = "system-users-symbolic"


class ChildrenPage(Adw.PreferencesPage):
    """One group of active children, one of removed ones, one Add button."""

    def __init__(self, state: PanelState) -> None:
        super().__init__(title=TITLE, icon_name=ICON)
        self.state = state
        self._groups: list[Adw.PreferencesGroup] = []
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
        panel = self.state.panel
        active = panel.active_children

        group = Adw.PreferencesGroup(
            title="Who uses this computer",
            description=(
                "Each child gets their own face on the first screen, their own "
                "colour and shape, their own drawings and their own daily total. "
                "The order here is the order the faces appear in."
            ),
        )
        add = common.button("Add a child", css="suggested-action")
        add.connect("clicked", self._on_add)
        group.set_header_suffix(add)

        if not active:
            group.add(
                common.note_row(
                    "Nobody is set up yet. Until you add someone, the computer "
                    "shows one face of its own called 'Me'.",
                    warning=True,
                )
            )
        for index, child in enumerate(active):
            group.add(self._child_row(child, index, len(active)))
        self.add(group)
        self._groups.append(group)

        retired = panel.retired_children
        if retired:
            removed = Adw.PreferencesGroup(
                title="Removed",
                description=(
                    "These children no longer appear on 'Who's here?'. Nothing "
                    "they made has been deleted -- their drawings are still on "
                    "this machine and you can put the face back at any time. "
                    "To delete the work for good, use Wipe on the Their things tab."
                ),
            )
            for child in retired:
                removed.add(self._retired_row(child))
            self.add(removed)
            self._groups.append(removed)

    def _child_row(self, child: M.Child, index: int, total: int) -> Adw.PreferencesRow:
        row = Adw.ExpanderRow()
        common.plain(row, child.name, self._subtitle(child))
        row.add_prefix(common.identity_badge(child))

        up = common.icon_button("go-up-symbolic", "Move this child earlier")
        up.set_sensitive(index > 0)
        up.connect("clicked", lambda _b, cid=child.id: self._move(cid, -1))
        down = common.icon_button("go-down-symbolic", "Move this child later")
        down.set_sensitive(index < total - 1)
        down.connect("clicked", lambda _b, cid=child.id: self._move(cid, 1))
        row.add_suffix(up)
        row.add_suffix(down)

        name = Adw.EntryRow(title="Name")
        name.set_text(child.name)
        name.connect("changed", lambda entry, cid=child.id: self._rename(cid, entry.get_text()))
        row.add_row(name)

        band = Adw.ComboRow(title="Age")
        band.set_subtitle(
            "Activities outside this age get no picture at all -- there is "
            "nothing for a four-year-old to ask a grown-up for."
        )
        bands = Gtk.StringList()
        for _value, label in M.AGE_BANDS:
            bands.append(label)
        band.set_model(bands)
        values = [value for value, _label in M.AGE_BANDS]
        band.set_selected(values.index(child.age_band) if child.age_band in values else 0)
        band.connect(
            "notify::selected",
            lambda combo, _p, cid=child.id: self._set_band(cid, values[combo.get_selected()]),
        )
        row.add_row(band)

        colour = Adw.ComboRow(title="Colour and shape")
        colour.set_subtitle(
            "Colour says whose computer this is; the shape says it again for a "
            "child who cannot tell two colours apart."
        )
        colours = Gtk.StringList()
        for pair, badge in zip(M.PROFILE_COLOURS, M.PROFILE_BADGES, strict=False):
            colours.append(f"{_colour_name(pair)} · {badge}")
        colour.set_model(colours)
        colour.set_selected(_colour_index(child))
        colour.connect(
            "notify::selected",
            lambda combo, _p, cid=child.id: self._set_colour(cid, combo.get_selected()),
        )
        row.add_row(colour)

        skip = Adw.SwitchRow(title="Ask 'what's next after?'")
        skip.set_subtitle(
            "Before the pictures appear, the computer asks what happens when it "
            "is finished -- outside, a book, a snack -- and reminds them at the "
            "end. This is the part of kidnix that parents like most; turn it off "
            "only if it gets in your child's way."
        )
        skip.set_active(not child.skip_next_choice)
        skip.connect(
            "notify::active",
            lambda sw, _p, cid=child.id: self._set_skip(cid, not sw.get_active()),
        )
        row.add_row(skip)

        remove_row = Adw.ActionRow(
            title="Remove this child",
            subtitle="Takes the face away. Keeps every drawing.",
        )
        remove = common.button("Remove", css="destructive-action")
        remove.connect("clicked", lambda _b, c=child: self._confirm_remove(c))
        remove_row.add_suffix(remove)
        row.add_row(remove_row)
        return common.plain(row)

    def _retired_row(self, child: M.Child) -> Adw.PreferencesRow:
        row = Adw.ActionRow()
        common.plain(row, child.name, f"Their things are kept at profiles/{child.id}")
        row.add_prefix(common.identity_badge(child, size=28))
        restore = common.button("Put the face back")
        restore.connect("clicked", lambda _b, cid=child.id: self._restore(cid))
        row.add_suffix(restore)
        return common.plain(row)

    @staticmethod
    def _subtitle(child: M.Child) -> str:
        band = dict(M.AGE_BANDS).get(child.age_band, child.age_band or "no age set")
        allowed = child.allowed_activity_ids
        which = "everything on the machine" if not allowed else f"{len(allowed)} chosen activities"
        return f"Ages {band} · {which}"

    # -- edits --

    def _on_add(self, _button: Gtk.Button) -> None:
        dialog = Adw.AlertDialog(
            heading="Add a child",
            body="What do they call themselves? This is the name under their face.",
        )
        entry = Gtk.Entry()
        entry.set_placeholder_text("Rosie")
        entry.set_margin_top(8)
        entry.set_margin_start(12)
        entry.set_margin_end(12)
        dialog.set_extra_child(entry)
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("add", "Add")
        dialog.set_response_appearance("add", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("add")
        dialog.set_close_response("cancel")

        def answered(_dialog: Adw.AlertDialog, response: str) -> None:
            if response != "add":
                return
            name = entry.get_text().strip()
            if not name:
                return
            self.state.panel.add_child(name)
            self.state.touch()
            self.refresh()

        dialog.connect("response", answered)
        dialog.present(self)

    def _confirm_remove(self, child: M.Child) -> None:
        dialog = Adw.AlertDialog(
            heading=f"Remove {child.name}?",
            body=(
                f"{child.name}'s face will not appear on 'Who's here?' any more.\n\n"
                "Nothing they have made is deleted. Their drawings, their journal "
                "and their voice notes stay on this machine, and you can put the "
                "face back whenever you like."
            ),
        )
        dialog.add_response("cancel", "Keep them")
        dialog.add_response("remove", "Remove the face")
        dialog.set_response_appearance("remove", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_close_response("cancel")

        def answered(_dialog: Adw.AlertDialog, response: str) -> None:
            if response != "remove":
                return
            self.state.panel.retire_child(child.id)
            self.state.touch()
            self.refresh()

        dialog.connect("response", answered)
        dialog.present(self)

    def _rename(self, child_id: str, name: str) -> None:
        # The id is NOT re-derived. It is the Journal's directory name, and a
        # rename that moved it would orphan every drawing the child has made.
        self.state.panel.update_child(child_id, name=name.strip())
        self.state.touch()

    def _set_band(self, child_id: str, band: str) -> None:
        self.state.panel.update_child(child_id, age_band=band)
        self.state.touch()

    def _set_colour(self, child_id: str, index: int) -> None:
        child = self.state.panel.child(child_id)
        if child is None:
            return
        primary, secondary = M.PROFILE_COLOURS[index % len(M.PROFILE_COLOURS)]
        self.state.panel.update_child(
            child_id,
            colour_primary=primary,
            colour_secondary=secondary,
            badge=M.PROFILE_BADGES[index % len(M.PROFILE_BADGES)],
        )
        self.state.touch()
        self.refresh()

    def _set_skip(self, child_id: str, skip: bool) -> None:
        self.state.panel.update_child(child_id, skip_next_choice=skip)
        self.state.touch()

    def _move(self, child_id: str, delta: int) -> None:
        if self.state.panel.move_child(child_id, delta):
            self.state.touch()
            self.refresh()

    def _restore(self, child_id: str) -> None:
        self.state.panel.restore_child(child_id)
        self.state.touch()
        self.refresh()


def _colour_index(child: M.Child) -> int:
    pair = (child.colour_primary, child.colour_secondary)
    return M.PROFILE_COLOURS.index(pair) if pair in M.PROFILE_COLOURS else 0


def _colour_name(pair: tuple[str, str]) -> str:
    return {
        M.PROFILE_COLOURS[0]: "Teal and pink",
        M.PROFILE_COLOURS[1]: "Navy and butter",
        M.PROFILE_COLOURS[2]: "Violet and cyan",
        M.PROFILE_COLOURS[3]: "Rust and leaf",
    }.get(pair, pair[0])


__all__ = ["ChildrenPage"]
