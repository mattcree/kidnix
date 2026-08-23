"""Updates & safety: the PIN, the update button, and the honest page.

Three things a parent asked for, and the order matters.

**The PIN first.** Mags's worry was the review's single most-cited defect, and
the image now ships without a PIN at all so the child's own gate demands one.
That leaves the *change* case, which is this: type the current four numbers,
then the new ones twice. The panel never sees a hash and never keeps a PIN --
it hands both to ``kidnix-set-pin`` on stdin and reads an exit code.

**Then the verification, then the button.** Tom's update ask was reordered by
the review itself: "an update button that pulls from ghcr with no signature
policy on the device is a worse position than being unpatched. Policy and
pinned identity first, button second." So this tab checks
``/etc/containers/policy.json`` *before* it offers to update anything, shows
the answer in a sentence whichever way it goes, and refuses to install when the
machine cannot check who signed it.

**Then the honest page.** "What this machine does and doesn't send", in the
same words as ``docs/PARENTS.md`` -- including how to check the biggest claim
without trusting us. Mags asked for that: *"how do I know, for myself, that he
can't get onto the internet?"*
"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk  # noqa: E402

from .. import system  # noqa: E402
from . import common, tasks  # noqa: E402
from .state import PanelState  # noqa: E402

TITLE = "Updates & safety"
ICON = "software-update-available-symbolic"

#: The page a parent reads first, in the words PARENTS.md uses. Each entry is
#: (heading, body). Kept as data so ``tests`` can assert the four claims are
#: all still here -- they are the promises the whole project is built on and
#: none of them may quietly disappear from the parent's view.
WHAT_IT_SENDS: tuple[tuple[str, str], ...] = (
    (
        "Your child's session cannot reach the internet at all",
        "Not filtered, not blocked by a list that might have a hole in it: the "
        "firewall refuses every outgoing connection made by your child's "
        "account, by account, at the kernel. There is no browser on the machine "
        "for it to use even if it could.",
    ),
    (
        "Nothing is sent about your child. Ever",
        "No accounts, no analytics, no usage data, no crash reports, no "
        "adverts. The activities are all offline programs; their sounds and "
        "pictures are already on the disk.",
    ),
    (
        "The machine itself talks to the internet only when you ask it to",
        "To fetch an update, or the one first-time download that installs the "
        "Scratch-like activity. Nothing is scheduled and nothing runs overnight.",
    ),
    (
        "What is written down about your child stays on the laptop",
        "Their drawings, and a journal of what they opened and when. The system "
        "log keeps at most 30 days and no more than 200 MB.",
    ),
    (
        "Research recording is off",
        "kidnix has instrumentation in it for studying how children use it. It "
        "ships switched off, in /etc/kidnix/research.toml, and it stays off "
        "unless somebody deliberately turns it on.",
    ),
    (
        "How to check the first claim yourself, without trusting us",
        "While your child's session is running, open a terminal on your own "
        "account and run: sudo journalctl -u kidnix-egress. You will see the "
        "rule that refuses their account's traffic. Or simpler: there is no "
        "browser to open, and no activity on the machine has anywhere to type "
        "an address.",
    ),
    (
        "What is not true",
        "The disk is not encrypted, and nothing is backed up anywhere. Anyone "
        "who takes the laptop apart can read what is on it, and if the laptop "
        "dies the drawings are gone. Copy them off now and then.",
    ),
)


class UpdatesPage(Adw.PreferencesPage):
    def __init__(self, state: PanelState, toast=None) -> None:
        super().__init__(title=TITLE, icon_name=ICON)
        self.state = state
        self._toast = toast
        self._groups: list[Adw.PreferencesGroup] = []
        self._status_row: Adw.ActionRow | None = None
        self._check_row: Adw.ActionRow | None = None
        self._update_button: Gtk.Button | None = None
        self._rollback_row: Adw.ActionRow | None = None
        self._rollback_button: Gtk.Button | None = None
        self.verify = system.signature_policy()
        self.status = system.BootcStatus()
        self.refresh()

    def refresh(self) -> None:
        for group in self._groups:
            self.remove(group)
        self._groups = []
        self._build()

    def _build(self) -> None:
        self._add(self._pin_group())
        self._add(self._update_group())
        self._add(self._safety_group())

    # -- the PIN --

    def _pin_group(self) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup(
            title="The grown-up PIN",
            description=(
                "Four numbers that open the grown-up gate inside your child's "
                "screen. Changing it needs the current one, so a child cannot "
                "change the numbers that fence them in even if they got to the "
                "machine first.\n\n"
                "Do it somewhere your child cannot watch your fingers. A "
                "six-year-old who has seen you type four buttons has your PIN, "
                "and that is the actual risk here -- not a stranger guessing."
            ),
        )
        row = Adw.ActionRow(
            title="Change the PIN",
            subtitle="1234 is refused: it is what kidnix used to ship with.",
        )
        change = common.button("Change…")
        change.connect("clicked", lambda _b: self._change_pin())
        row.add_suffix(change)
        group.add(row)
        group.add(
            common.note_row(
                "Forgotten it? Open a terminal on this account and run "
                "'sudo kidnix-set-pin --reset'. It asks for your own password, "
                "not the old PIN, and nothing your child made is touched."
            )
        )
        return group

    def _change_pin(self) -> None:
        dialog = Adw.AlertDialog(
            heading="Change the grown-up PIN",
            body="Four numbers. Nothing is shown as you type and only a scrambled form of it is stored.",
        )
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_top(8)
        box.set_margin_start(12)
        box.set_margin_end(12)
        fields = {}
        for key, label in (
            ("current", "The PIN now"),
            ("new", "The new PIN"),
            ("again", "The new PIN again"),
        ):
            entry = Gtk.PasswordEntry()
            entry.set_show_peek_icon(True)
            entry.set_property("placeholder-text", label)
            box.append(entry)
            fields[key] = entry
        dialog.set_extra_child(box)
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("set", "Change it")
        dialog.set_response_appearance("set", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_close_response("cancel")

        def answered(_dialog: Adw.AlertDialog, response: str) -> None:
            if response != "set":
                return
            current = fields["current"].get_text()
            new = fields["new"].get_text()
            again = fields["again"].get_text()
            if new != again:
                self._say("Those two did not match. Nothing was changed.")
                return
            if not system.pin_is_four_digits(new):
                self._say("A PIN is four numbers. Nothing was changed.")
                return
            if new == system.REFUSED_PIN:
                self._say(
                    f"{system.REFUSED_PIN} is the PIN every kidnix used to ship "
                    "with, and it is written down in the instructions. Pick another."
                )
                return
            tasks.run_async(
                lambda: system.set_pin(new, current, self.state.runner),
                lambda result: self._say(
                    system.pin_message(result)
                    if isinstance(result, system.Completed)
                    else str(result)
                ),
                synchronous=self.state.synchronous,
            )

        dialog.connect("response", answered)
        dialog.present(self)

    # -- updates --

    def _update_group(self) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup(
            title="Updating the machine",
            description=(
                "kidnix does not update itself. Nothing happens on a timer, "
                "nothing reboots overnight, and nothing changes under your child "
                "without you. An update is written alongside the version you are "
                "running and takes effect the next time the laptop starts -- so "
                "if it turns out to be bad, the old one is still there."
            ),
        )

        verify = Adw.ActionRow(title="Are updates checked?")
        verify.set_subtitle(self.verify.sentence)
        icon = Gtk.Image.new_from_icon_name(
            "security-high-symbolic" if self.verify.verified else "dialog-warning-symbolic"
        )
        verify.add_prefix(icon)
        group.add(verify)

        self._status_row = Adw.ActionRow(title="What is running now")
        self._status_row.set_subtitle("Asking the machine…")
        group.add(self._status_row)

        self._check_row = Adw.ActionRow(title="Is there an update?")
        self._check_row.set_subtitle("Not looked yet. Looking needs the internet.")
        check = common.button("Check now")
        check.connect("clicked", lambda _b: self._check())
        self._check_row.add_suffix(check)
        group.add(self._check_row)

        install = Adw.ActionRow(
            title="Install the update",
            subtitle=(
                "Downloads it and writes it alongside what you are running. It "
                "starts being used the next time the laptop is switched on."
            ),
        )
        self._update_button = common.button("Update now", css="suggested-action")
        self._update_button.set_sensitive(self.verify.verified)
        if not self.verify.verified:
            self._update_button.set_tooltip_text(
                "This machine cannot check who signed an update, so it will not "
                "install one. That is the safe direction."
            )
        self._update_button.connect("clicked", lambda _b: self._upgrade())
        install.add_suffix(self._update_button)
        group.add(install)

        # The button is gated on there BEING a previous version. bootc reports
        # one only after an update has actually replaced something, so on a
        # freshly installed machine "Roll back" would fail with a message from
        # bootc rather than being honestly greyed out -- and a parent pressing
        # it in a hurry, because something is wrong, is the worst moment to
        # answer with an error. `_show_status` turns it on when the machine
        # says there is somewhere to go back to.
        self._rollback_row = Adw.ActionRow(
            title="Go back to the previous version",
            subtitle=(
                "If an update made something worse. A start-up that fails its "
                "own health checks already does this by itself, unattended."
            ),
        )
        self._rollback_button = common.button("Roll back")
        self._rollback_button.set_sensitive(False)
        self._rollback_button.set_tooltip_text("Asking the machine what it could go back to…")
        self._rollback_button.connect("clicked", lambda _b: self._rollback())
        self._rollback_row.add_suffix(self._rollback_button)
        group.add(self._rollback_row)

        self._refresh_status()
        return group

    def _refresh_status(self) -> None:
        """Ask bootc what is booted. Off the main loop: `bootc status` on a
        cold page cache is not instant, and this runs while the tab builds."""
        if self._status_row is None:
            return
        tasks.run_async(
            lambda: system.bootc_status(self.state.runner),
            self._show_status,
            synchronous=self.state.synchronous,
        )

    def _show_status(self, status: object) -> None:
        if self._status_row is None:
            return
        self.status = (
            status if isinstance(status, system.BootcStatus) else system.BootcStatus(raw_ok=False)
        )
        if not self.status.raw_ok:
            self._status_row.set_subtitle(
                "This machine could not say. That is not the same as 'up to "
                "date' -- try again, or ask whoever set it up."
            )
            self._show_rollback(
                False,
                "The machine could not say what it would go back to.",
            )
            return
        parts = [self.status.booted_image or "an image with no name"]
        if self.status.short_digest:
            parts.append(f"({self.status.short_digest})")
        if self.status.can_roll_back:
            parts.append("— the previous version is still on the disk")
        self._status_row.set_subtitle(" ".join(parts))
        self._show_rollback(
            self.status.can_roll_back,
            "There is nothing to go back to: this machine has not been updated "
            "yet, so the version it is running is the only one on the disk.",
        )

    def _show_rollback(self, possible: bool, why_not: str) -> None:
        """Turn "Roll back" on only when bootc named something to go back to."""
        if self._rollback_button is None or self._rollback_row is None:
            return
        self._rollback_button.set_sensitive(possible)
        self._rollback_button.set_tooltip_text("" if possible else why_not)
        if possible:
            self._rollback_row.set_subtitle(
                f"Back to {self.status.rollback_version or self.status.rollback_image}. "
                "It is already on the disk; the laptop starts on it next time. "
                "Nothing your child has made is touched."
            )
        else:
            self._rollback_row.set_subtitle(why_not)

    def _check(self) -> None:
        if self._check_row is not None:
            self._check_row.set_subtitle("Looking\u2026")

        def finished(answer: object) -> None:
            sentence = (
                answer.sentence
                if isinstance(answer, system.UpdateCheck)
                else f"The machine could not check: {answer}"
            )
            if self._check_row is not None:
                self._check_row.set_subtitle(sentence)
            self._say(sentence)

        tasks.run_async(
            lambda: system.check_for_updates(self.state.runner),
            finished,
            synchronous=self.state.synchronous,
        )

    def _upgrade(self) -> None:
        if not self.verify.verified:
            self._say("Refused: this machine cannot check who signed an update.")
            return
        dialog = Adw.AlertDialog(
            heading="Install the update?",
            body=(
                "It is checked against this machine's own signing key before "
                "anything is installed, written alongside the version you are "
                "running, and used from the next start-up. Nothing your child "
                "has made is touched, and nothing reboots on its own."
            ),
        )
        dialog.add_response("cancel", "Not now")
        dialog.add_response("go", "Install it")
        dialog.set_response_appearance("go", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_close_response("cancel")

        def answered(_dialog: Adw.AlertDialog, response: str) -> None:
            if response != "go":
                return
            self._say("Downloading\u2026 this can take several minutes.")

            def finished(result: object) -> None:
                self._say(
                    "Installed. It starts being used the next time the laptop is switched on."
                    if getattr(result, "ok", False)
                    else (
                        getattr(result, "message", "")
                        or str(result)
                        or "The update did not install."
                    )
                )
                self._refresh_status()

            tasks.run_async(
                lambda: system.upgrade(self.state.runner),
                finished,
                synchronous=self.state.synchronous,
            )

        dialog.connect("response", answered)
        dialog.present(self)

    def _rollback(self) -> None:
        if not self.status.can_roll_back:
            # Belt to the greyed-out button's braces: `_show_status` may not
            # have come back yet, or may have come back with nothing.
            self._say("There is no previous version on this machine to go back to.")
            return
        dialog = Adw.AlertDialog(
            heading="Go back to the previous version?",
            body=(
                "The laptop will start up on the version it was running before "
                "the last update. Nothing your child has made is touched."
            ),
        )
        dialog.add_response("cancel", "Stay here")
        dialog.add_response("go", "Go back")
        dialog.set_response_appearance("go", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_close_response("cancel")

        def answered(_dialog: Adw.AlertDialog, response: str) -> None:
            if response != "go":
                return

            def finished(result: object) -> None:
                self._say(
                    "Done. Restart the laptop to use the previous version."
                    if getattr(result, "ok", False)
                    else (getattr(result, "message", "") or str(result) or "It could not go back.")
                )
                self._refresh_status()

            tasks.run_async(
                lambda: system.rollback(self.state.runner),
                finished,
                synchronous=self.state.synchronous,
            )

        dialog.connect("response", answered)
        dialog.present(self)

    # -- the honest page --

    def _safety_group(self) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup(
            title="What this machine does and does not send",
            description=(
                "The same page as the one by the kettle (docs/PARENTS.md). "
                "Nothing here is a setting; it is what the machine is."
            ),
        )
        for heading, body in WHAT_IT_SENDS:
            row = Adw.ActionRow(title=heading, subtitle=body)
            row.set_subtitle_lines(0)
            row.set_title_lines(0)
            group.add(row)
        return group

    def _say(self, text: str) -> None:
        if self._toast is not None:
            self._toast(text)

    def _add(self, group: Adw.PreferencesGroup) -> None:
        self.add(group)
        self._groups.append(group)


__all__ = ["WHAT_IT_SENDS", "UpdatesPage"]
