"""Family: who a drawing could go to, one day.

SYNTHESIS F3 names Print / Send to family / Put away as the three actions on a
Journal card, and G1 lists "family recipients" among the things a parent sets.
Nothing on this machine sends anything anywhere yet, and this tab says so at the
top rather than offering a Send button that does nothing.

Writing the names down now is not busywork. When "send to Granny" lands it
should land on a machine that already knows who Granny is; the alternative is a
feature that begins with a form, at the moment a child is holding up a picture.

Everything here stays on the laptop. There is no address book, no account, no
email field and nowhere for one to be uploaded to -- a name and, if you like, a
photo file the child would recognise.
"""

from __future__ import annotations

from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib, Gtk  # noqa: E402

from . import common  # noqa: E402
from .state import PanelState  # noqa: E402

TITLE = "Family"
ICON = "contact-new-symbolic"


class FamilyPage(Adw.PreferencesPage):
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

    def _build(self) -> None:
        group = Adw.PreferencesGroup(
            title="People a picture could be sent to",
            description=(
                "A name your child would recognise, and a photograph if you have "
                "one. It is written down on this machine and nowhere else: there "
                "is no address book, no account, and no email address to type."
            ),
        )
        add = common.button("Add someone", css="suggested-action")
        add.connect("clicked", self._on_add)
        group.set_header_suffix(add)

        group.add(
            common.note_row(
                "Nothing sends anything yet. This machine has no way to reach the "
                "internet from your child's account, and 'send to family' is not "
                "built. What you write here will be waiting for it.",
                warning=True,
            )
        )

        if not self.state.panel.family:
            group.add(
                common.note_row(
                    "Nobody yet. Grandparents are the usual answer, and the reason "
                    "three of four parents asked for this at all."
                )
            )
        for recipient in self.state.panel.family:
            group.add(self._row(recipient))
        self.add(group)
        self._groups.append(group)

    def _row(self, recipient) -> Adw.PreferencesRow:
        row = Adw.ExpanderRow()
        common.plain(row, recipient.name, recipient.relation or "on this machine only")
        if recipient.photo and Path(recipient.photo).is_file():
            row.add_prefix(common.image_from(Path(recipient.photo), common.AVATAR))
        else:
            avatar = Gtk.Image.new_from_icon_name("avatar-default-symbolic")
            avatar.set_pixel_size(common.AVATAR)
            row.add_prefix(avatar)

        name = Adw.EntryRow(title="Name")
        name.set_text(recipient.name)
        name.connect(
            "changed", lambda entry, rid=recipient.id: self._edit(rid, name=entry.get_text())
        )
        row.add_row(name)

        relation = Adw.EntryRow(title="Who they are")
        relation.set_text(recipient.relation)
        relation.connect(
            "changed",
            lambda entry, rid=recipient.id: self._edit(rid, relation=entry.get_text()),
        )
        row.add_row(relation)

        photo = Adw.ActionRow(title="Photograph", subtitle=recipient.photo or "None chosen")
        choose = common.button("Choose…")
        choose.connect("clicked", lambda _b, rid=recipient.id: self._choose_photo(rid))
        photo.add_suffix(choose)
        row.add_row(photo)

        remove_row = Adw.ActionRow(title="Remove")
        remove = common.button("Remove", css="destructive-action")
        remove.connect("clicked", lambda _b, rid=recipient.id: self._remove(rid))
        remove_row.add_suffix(remove)
        row.add_row(remove_row)
        return common.plain(row)

    # -- edits --

    def _on_add(self, _button: Gtk.Button) -> None:
        dialog = Adw.AlertDialog(
            heading="Add someone",
            body="What does your child call them? 'Granny', not a full name.",
        )
        entry = Gtk.Entry()
        entry.set_placeholder_text("Granny")
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
            if response != "add" or not entry.get_text().strip():
                return
            self.state.panel.add_recipient(entry.get_text())
            self.state.touch()
            self.refresh()

        dialog.connect("response", answered)
        dialog.present(self)

    def _edit(self, recipient_id: str, **changes) -> None:
        from dataclasses import replace

        for index, recipient in enumerate(self.state.panel.family):
            if recipient.id == recipient_id:
                self.state.panel.family[index] = replace(recipient, **changes)
                self.state.touch()
                return

    def _remove(self, recipient_id: str) -> None:
        if self.state.panel.remove_recipient(recipient_id):
            self.state.touch()
            self.refresh()

    def _choose_photo(self, recipient_id: str) -> None:
        dialog = Gtk.FileDialog()
        dialog.set_title("A photograph")
        filters = Gio.ListStore.new(Gtk.FileFilter)
        pictures = Gtk.FileFilter()
        pictures.set_name("Pictures")
        pictures.add_mime_type("image/png")
        pictures.add_mime_type("image/jpeg")
        filters.append(pictures)
        dialog.set_filters(filters)

        def chosen(source: Gtk.FileDialog, result: Gio.AsyncResult) -> None:
            try:
                picture = source.open_finish(result)
            except GLib.Error:
                return
            if picture is not None and picture.get_path():
                self._edit(recipient_id, photo=picture.get_path())
                self.refresh()

        dialog.open(self.get_root(), None, chosen)


__all__ = ["FamilyPage"]
