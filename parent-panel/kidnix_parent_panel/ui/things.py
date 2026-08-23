"""Their things: the way out for a child's work.

Three of the four parents arrived here on their own, in the same words --
drawings on the fridge, a picture posted to a grandparent, a thing that leaves
the screen -- and the review's fourth ask is exactly this tab. The safety
review's first blocker was that the child's data had no exit *and* the parent
could not delete it either: "kept forever became a property of the code rather
than a decision anyone made."

Four buttons and no dashboard. There is deliberately nothing here that counts
minutes, ranks activities or charts a week: SYNTHESIS G1 rules out engagement
metrics and G4's "see, export and delete" means their pictures, not a report
about them.

**Why everything starts with an export.** ``/var/home/kid`` is mode 0700
``kid:kid`` so that nothing on the machine can read a child's work -- and that
includes the parent's own account. Rather than loosen the child's home, the
parent borrows root for the length of one copy, through polkit, and gets a file
they own. So "open their things in Files" is: run ``kidnix-export`` into a
folder you own, then open that folder. It is one extra step and it is the step
that keeps the child's home private from everything else on the machine.
"""

from __future__ import annotations

from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib, Gtk  # noqa: E402

from .. import system  # noqa: E402
from . import common, tasks  # noqa: E402
from .state import PanelState  # noqa: E402

TITLE = "Their things"
ICON = "folder-pictures-symbolic"

#: The word the second confirmation makes a parent type. The same word
#: ``kidnix-wipe`` itself asks for, so the panel is not inventing a second
#: ceremony for the same act.
CONFIRM_WORD = "DELETE"


class ThingsPage(Adw.PreferencesPage):
    def __init__(self, state: PanelState, toast=None) -> None:
        super().__init__(title=TITLE, icon_name=ICON)
        self.state = state
        self._toast = toast
        self._last_export: Path | None = None
        self.refresh()

    def refresh(self) -> None:
        for group in list(getattr(self, "_groups", [])):
            self.remove(group)
        self._groups: list[Adw.PreferencesGroup] = []
        self._build()

    def _build(self) -> None:
        get = Adw.PreferencesGroup(
            title="Getting their work off this machine",
            description=(
                "Everything your child has made lives in their own account, which "
                "nothing else on the computer can read -- not even you. That is on "
                "purpose, and it is why there is a copy button rather than a "
                "folder you can browse to.\n\n"
                "The copy contains the drawings, the journal of what they did and "
                "any voice notes, as ordinary files. There is no backup of any "
                "kind: if the laptop dies, this is all there was."
            ),
        )

        export = Adw.ActionRow(
            title="Copy everything to a folder",
            subtitle=(
                "Makes one file you own, in your home folder or on a USB stick. "
                "The machine will ask for your password, not your child's PIN."
            ),
        )
        home = common.button("Save to my home folder", css="suggested-action")
        home.connect("clicked", lambda _b: self._export(None))
        elsewhere = common.button("Choose a folder…")
        elsewhere.connect("clicked", lambda _b: self._choose_folder())
        export.add_suffix(elsewhere)
        export.add_suffix(home)
        get.add(export)

        open_row = Adw.ActionRow(
            title="Open the copy in Files",
            subtitle="Opens the folder the last copy went to.",
        )
        open_button = common.button("Open")
        open_button.set_sensitive(self._last_export is not None)
        open_button.connect("clicked", lambda _b: self._open_last())
        open_row.add_suffix(open_button)
        get.add(open_row)

        print_row = Adw.ActionRow(
            title="Print a picture",
            subtitle=(
                "Pick a picture out of a copy you have already made; it opens in "
                "the image viewer, where Print is on the menu. Nothing prints "
                "straight from your child's account."
            ),
        )
        print_button = common.button("Choose a picture…")
        print_button.connect("clicked", lambda _b: self._choose_picture())
        print_row.add_suffix(print_button)
        get.add(print_row)
        self._add(get)

        self._add(self._delete_group())

    def _delete_group(self) -> Adw.PreferencesGroup:
        children = (
            ", ".join(common.escape(c.name) for c in self.state.panel.active_children)
            or "your child"
        )
        group = Adw.PreferencesGroup(
            title="Deleting it",
            description=(
                "This is the only thing on the machine that deletes a child's "
                "work. Removing a face on the Children tab does not: their "
                "drawings stay where they are."
            ),
        )
        row = Adw.ActionRow(
            title="Delete everything they have made",
            subtitle=(
                f"Permanent, and it covers everybody on this machine ({children}) "
                "rather than one child at a time. Their accounts and the computer "
                "itself are left alone. Make a copy first."
            ),
        )
        wipe = common.button("Delete everything…", css="destructive-action")
        wipe.connect("clicked", lambda _b: self._confirm_wipe_first())
        row.add_suffix(wipe)
        group.add(common.plain(row))
        return group

    # -- actions --

    def _export(self, destination: Path | None) -> None:
        self._say("Copying\u2026 the machine will ask for your password.")

        def finished(result: object) -> None:
            if isinstance(result, Exception) or not getattr(result, "ok", False):
                self._say(
                    str(result)
                    if isinstance(result, Exception)
                    else (result.message or "The copy did not happen.")
                )
                return
            path = _archive_path(result.stdout)
            self._last_export = path.parent if path is not None else destination
            self._say(f"Copied to {path}" if path is not None else "Copied.")
            self.refresh()

        tasks.run_async(
            lambda: system.export_to(destination, self.state.runner),
            finished,
            synchronous=self.state.synchronous,
        )

    def _choose_folder(self) -> None:
        dialog = Gtk.FileDialog()
        dialog.set_title("Where should the copy go?")

        def chosen(source: Gtk.FileDialog, result: Gio.AsyncResult) -> None:
            try:
                folder = source.select_folder_finish(result)
            except GLib.Error:
                return
            if folder is not None and folder.get_path():
                self._export(Path(folder.get_path()))

        dialog.select_folder(self.get_root(), None, chosen)

    def _choose_picture(self) -> None:
        dialog = Gtk.FileDialog()
        dialog.set_title("Which picture?")
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
                system.open_with_desktop(Path(picture.get_path()), self.state.runner)

        dialog.open(self.get_root(), None, chosen)

    def _open_last(self) -> None:
        if self._last_export is None:
            return
        system.open_with_desktop(self._last_export, self.state.runner)

    def _confirm_wipe_first(self) -> None:
        """First confirmation: what is about to go, offered a copy instead.

        It deliberately does **not** run the helper to produce a live listing.
        Doing so would put a password prompt in front of a parent who has only
        pressed the first of two confirmations -- teaching them to type their
        password at a dialogue that says "delete everything" is exactly the
        habit not to teach. The list below is what
        ``/usr/libexec/kidnix-parent-tools`` actually removes, written down.
        """
        dialog = Adw.AlertDialog(
            heading="Delete everything your child has made?",
            body=(
                "This removes every drawing, every journal entry and every voice "
                "note on this machine, for every child, and it cannot be undone.\n\n"
                "There is no backup anywhere.\n\n"
                "What goes: their scrapbook and its pictures and voice notes, "
                "the drawings Tux Paint saved, everything in their Pictures "
                "folder, how much of today they have used, and how many "
                "sessions they have finished.\n\n"
                "What stays: their account, their name and colour, the "
                "activities you have chosen, and the machine itself."
            ),
        )
        dialog.add_response("cancel", "Keep it all")
        dialog.add_response("copy", "Make a copy first")
        dialog.add_response("go", "Continue")
        dialog.set_response_appearance("go", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_close_response("cancel")

        def answered(_dialog: Adw.AlertDialog, response: str) -> None:
            if response == "copy":
                self._export(None)
            elif response == "go":
                self._confirm_wipe_second()

        dialog.connect("response", answered)
        dialog.present(self)

    def _confirm_wipe_second(self) -> None:
        """Second confirmation: type the word. The same word the helper asks for."""
        dialog = Adw.AlertDialog(
            heading="Type DELETE to confirm",
            body=(
                "This is the last step. After this the drawings are gone from "
                "this computer for good."
            ),
        )
        entry = Gtk.Entry()
        entry.set_placeholder_text(CONFIRM_WORD)
        entry.set_margin_top(8)
        entry.set_margin_start(12)
        entry.set_margin_end(12)
        dialog.set_extra_child(entry)
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("delete", "Delete everything")
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_response_enabled("delete", False)
        dialog.set_close_response("cancel")
        entry.connect(
            "changed",
            lambda widget: dialog.set_response_enabled(
                "delete", widget.get_text().strip() == CONFIRM_WORD
            ),
        )

        def answered(_dialog: Adw.AlertDialog, response: str) -> None:
            if response != "delete" or entry.get_text().strip() != CONFIRM_WORD:
                return
            self._say("Deleting\u2026 the machine will ask for your password.")
            tasks.run_async(
                lambda: system.wipe(self.state.runner),
                lambda result: self._say(
                    "Everything your child made has been deleted."
                    if getattr(result, "ok", False)
                    else (getattr(result, "message", "") or str(result) or "Nothing was deleted.")
                ),
                synchronous=self.state.synchronous,
            )

        dialog.connect("response", answered)
        dialog.present(self)

    def _say(self, text: str) -> None:
        if self._toast is not None:
            self._toast(text)

    def _add(self, group: Adw.PreferencesGroup) -> None:
        self.add(group)
        self._groups.append(group)


def _archive_path(stdout: str) -> Path | None:
    """``kidnix-export`` prints ``Saved to: <path>``. Find it, or give up."""
    for line in stdout.splitlines():
        if line.strip().startswith("Saved to:"):
            candidate = line.split(":", 1)[1].strip()
            if candidate:
                return Path(candidate)
    return None


__all__ = ["CONFIRM_WORD", "ThingsPage"]
