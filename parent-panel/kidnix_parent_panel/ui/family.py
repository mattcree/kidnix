"""Family: who a letter goes to, and how it actually gets there.

SYNTHESIS F3 names Print / Send to family / Put away as the three actions on a
Journal card, and G1 lists "family recipients" among the things a parent sets.
This list is live: the **Letters** activity reads ``[[family]]`` out of
``parent.toml`` and shows exactly these people, in this order, as the faces on
its "Who is your letter for?" screen (``letters_to_family.recipients``).

**The delivery is a person, and this tab says so.** The child session has no
network egress (SYNTHESIS H1), so a posted letter is written into
``/var/lib/kidnix/outbox/<profile>/`` and waits for a grown-up to send it by
their own means; a reply is a folder a grown-up drops into
``/var/lib/kidnix/inbox/<profile>/``, which the child meets on the "Letters for
you" shelf. Until 2026-08-23 this tab said "'send to family' is not built" and
named neither directory, so the sneakernet was documented nowhere a parent
looks and a child's letters piled up in a folder nobody had been told about.

The outbox is ``0750 kid:kid`` and the inbox ``0750 parent:kid``
(``tmpfiles.d/kidnix-letters.conf``): a grown-up writes replies directly, and
reads the outbox through ``kidnix-export`` (Their things) rather than by
loosening a child's directory.

Everything here stays on the laptop. There is no address book, no account, no
email field and nowhere for one to be uploaded to -- a name and, if you like, a
photo file the child would recognise.
"""

from __future__ import annotations

import os
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib, Gtk  # noqa: E402

from .. import system  # noqa: E402
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
                "This list is what the Letters activity shows your child: they "
                "press a face, draw something, say or write a line, and press "
                "Post it. Nobody here is written to a list with an address on it "
                "-- a name and a face is all the machine knows."
            )
        )
        group.add(
            common.note_row(
                "YOU ARE THE POSTMAN. Nothing leaves this computer by itself: your "
                "child's account cannot reach the internet at all. A posted letter "
                "is written into /var/lib/kidnix/outbox/ -- one folder per child, "
                "one folder per letter, with the whole letter as a picture you can "
                "attach or print -- and it waits there until you send it however "
                "you normally would. Nothing marks it sent and nothing deletes it.\n\n"
                "That folder belongs to your child and this account cannot open it "
                "without your password. The easy way in is Their things -> "
                '"Save to my home folder", which now puts the letters in the '
                "copy alongside the drawings.",
                warning=True,
            )
        )
        group.add(
            common.note_row(
                "Replies come back the same way, by hand, and this half you can do "
                "in Files: put what Granny sends -- a photo, a sound file, a line "
                "of text -- into a new folder under /var/lib/kidnix/inbox/<child>/ "
                "and it appears on your child's 'Letters for you' shelf the next "
                "time they open Letters. That folder is yours to write to; your "
                "child can read it and cannot put anything in it, so nothing on "
                "that shelf is ever something the machine made up."
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

        photo = Adw.ActionRow(title="Photograph", subtitle=_photo_state(recipient))
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
            if picture is None or not picture.get_path():
                return
            path = Path(picture.get_path())
            # Said now, not after Apply. A file on a USB stick, or one inside
            # another account's home, is a real thing to pick by accident and
            # the failure it used to produce was invisible: the path was
            # stored, the child's screen could not open it, and a drawn face
            # appeared where Granny should have been.
            if not path.is_file() or not os.access(path, os.R_OK):
                self._complain(
                    "That file cannot be read",
                    f"{path} could not be opened from this account, so it was "
                    "not used. Pick a picture that is on this computer, in a "
                    "folder you can open.",
                )
                return
            if path.suffix.lower() not in system.PHOTO_SUFFIXES:
                self._complain(
                    "That is not a kind of picture this machine can show",
                    "Choose a "
                    + ", ".join(s.lstrip(".") for s in system.PHOTO_SUFFIXES)
                    + " file.",
                )
                return
            self._edit(recipient_id, photo=str(path))
            self.refresh()

        dialog.open(self.get_root(), None, chosen)

    def _complain(self, heading: str, body: str) -> None:
        dialog = Adw.AlertDialog(heading=heading, body=body)
        dialog.add_response("ok", "All right")
        dialog.set_default_response("ok")
        dialog.set_close_response("ok")
        dialog.present(self)


def _photo_state(recipient) -> str:
    """What the Photograph row says, and it says which of four states this is.

    The copy under ``/var/lib/kidnix/photos`` is the only one the *child's*
    account can open, so "chosen" and "your child can see it" are genuinely
    different states and the row is where the difference has to be visible.
    """
    if not recipient.photo.strip():
        return "None chosen. Your child sees a drawn face for this person."
    path = Path(recipient.photo)
    if not path.is_file():
        return f"{path} is not there any more. Choose another one."
    if path.parent == system.PHOTO_DIR:
        return f"{path} — your child's screen can open this."
    return f"{path} — copied where your child can see it when you press Apply."


__all__ = ["FamilyPage"]
