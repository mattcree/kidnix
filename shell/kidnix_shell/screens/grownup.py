"""S9 -- the grown-up sheet.

Reached by a three-second hold on the plain corner tile, then a PIN
(SYNTHESIS G2). Adult typography, adult density, no characters, no read-aloud:
this surface is not for the child and should not look like it is.

v0.1 actions: start a session, end the session now, add 5/15/30 minutes, set
the default session length, open the parent panel (a stub about-window), and
log out to GDM.
"""

from __future__ import annotations

import logging
from datetime import datetime

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk, Pango  # noqa: E402

from ..context import ShellContext  # noqa: E402
from ..session import MAX_SESSION_MINUTES, MIN_SESSION_MINUTES  # noqa: E402

log = logging.getLogger(__name__)

PIN_LENGTH = 4
GRANTS = (5, 15, 30)

LENGTH_SUBTITLE = "Minutes. No number here is evidence-based; 25 is the precaution."
READ_ONLY_SUBTITLE = (
    "Kept for this boot only: /etc/kidnix/parent.toml is root-owned, "
    "which is what keeps the PIN out of the child's hands."
)


def no_cut(row: Adw.PreferencesRow) -> Adw.PreferencesRow:
    """Let an adult row's title and subtitle wrap instead of ellipsising.

    The sheet is the one adult surface in the shell, but "never cut a label"
    is not a children's rule -- a parent reading "Kept for this boot only:
    /etc/kidnix/pare..." has been told nothing. libadwaita defaults these rows
    to a single ellipsised line; both are unbounded here, and the sheet
    scrolls.
    """
    row.set_title_lines(0)
    row.set_use_markup(False)
    if isinstance(row, Adw.ActionRow):
        row.set_subtitle_lines(0)
    return row


def wrapping_button(label: str) -> Gtk.Button:
    """A sheet button whose text wraps rather than being cut to fit."""
    button = Gtk.Button(label=label)
    child = button.get_child()
    if isinstance(child, Gtk.Label):
        child.set_wrap(True)
        child.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        child.set_ellipsize(Pango.EllipsizeMode.NONE)
        child.set_justify(Gtk.Justification.CENTER)
    return button


class GrownupSheet(Adw.Dialog):
    """PIN pad, then the actions. Closing it returns the child where they were."""

    def __init__(self, ctx: ShellContext) -> None:
        super().__init__()
        self.ctx = ctx
        self._pin = ""
        self.set_title("Grown-up")
        self.set_content_width(560)
        self.set_content_height(640)
        self.add_css_class("grownup")

        self._stack = Gtk.Stack()
        self._stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT)
        self._stack.add_named(self._pin_page(), "pin")
        self._stack.add_named(self._actions_page(), "actions")

        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        header.set_title_widget(Adw.WindowTitle.new("Grown-up", ""))
        toolbar.add_top_bar(header)
        toolbar.set_content(self._stack)
        self.set_child(toolbar)

        self.connect("closed", lambda _d: ctx.host.close_grownup())

    # -- PIN --

    def _pin_page(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(24)
        box.set_margin_bottom(24)
        box.set_margin_start(24)
        box.set_margin_end(24)
        box.set_valign(Gtk.Align.CENTER)

        title = Gtk.Label(label="Enter the grown-up PIN")
        title.add_css_class("title")
        title.set_wrap(True)
        title.set_justify(Gtk.Justification.CENTER)
        box.append(title)

        self._display = Gtk.Label(label="_ _ _ _")
        self._display.add_css_class("pin-display")
        box.append(self._display)

        self._error = Gtk.Label(label="")
        self._error.add_css_class("pin-error")
        self._error.set_wrap(True)
        self._error.set_justify(Gtk.Justification.CENTER)
        box.append(self._error)

        pad = Gtk.Grid(row_spacing=8, column_spacing=8)
        pad.add_css_class("pin-pad")
        pad.set_halign(Gtk.Align.CENTER)
        for index in range(9):
            pad.attach(self._digit(str(index + 1)), index % 3, index // 3, 1, 1)
        clear = wrapping_button("Clear")
        clear.connect("clicked", lambda _b: self._reset_pin())
        pad.attach(clear, 0, 3, 1, 1)
        pad.attach(self._digit("0"), 1, 3, 1, 1)
        cancel = wrapping_button("Cancel")
        cancel.connect("clicked", lambda _b: self.close())
        pad.attach(cancel, 2, 3, 1, 1)
        box.append(pad)

        # The PIN is also typeable: an adult with a keyboard should not have to
        # click twelve buttons.
        keys = Gtk.EventControllerKey.new()
        keys.connect("key-pressed", self._on_key)
        self.add_controller(keys)
        return box

    def _digit(self, digit: str) -> Gtk.Button:
        button = Gtk.Button(label=digit)
        button.connect("clicked", lambda _b, d=digit: self._push(d))
        return button

    def _on_key(self, _c: Gtk.EventControllerKey, keyval: int, _code: int, _state: int) -> bool:
        if self._stack.get_visible_child_name() != "pin":
            return False
        if 0x30 <= keyval <= 0x39:  # GDK_KEY_0 .. GDK_KEY_9
            self._push(chr(keyval))
            return True
        if keyval in (0xFF08, 0xFF1B):  # BackSpace, Escape
            self._reset_pin()
            return True
        return False

    def _push(self, digit: str) -> None:
        if len(self._pin) >= PIN_LENGTH:
            return
        self._pin += digit
        self._display.set_label(
            " ".join("*" * len(self._pin) + "_" * (PIN_LENGTH - len(self._pin)))
        )
        if len(self._pin) == PIN_LENGTH:
            self._check()

    def _reset_pin(self) -> None:
        self._pin = ""
        self._display.set_label("_ _ _ _")

    def _check(self) -> None:
        """One attempt. Free, un-penalised, unvoiced, and logged (G2).

        **No penalty of any kind**: no lockout, no growing delay, no attempt
        counter, no sound. A five-year-old poking at a keypad is expected
        behaviour, not an intrusion, and punishing it would teach them that the
        machine is angry with them. The RCT (n=554, mean age 4.3) says a lock
        is a speed bump either way; the wall is the lockdown under the session,
        not this pad.

        **Logged for the parent, never the digits.** The line names the time
        and the outcome so a grown-up who wants to know how often the gate is
        being tried can read it in their own journal -- and a PIN that appeared
        in a log would be a PIN stored in plaintext by another route.
        """
        accepted = self.ctx.config.check_pin(self._pin)
        self._reset_pin()
        log.info(
            "grown-up gate: PIN attempt %s at %s",
            "accepted" if accepted else "rejected",
            datetime.now().isoformat(timespec="seconds"),
        )
        if accepted:
            self._error.set_label("")
            self._refresh_actions()
            self._stack.set_visible_child_name("actions")
        else:
            # Adult typography, adult surface: the grown-up who mistyped is
            # told so in writing. Nothing is spoken -- the gate is not voiced.
            self._error.set_label("That PIN is not right.")

    # -- actions --

    def _actions_page(self) -> Gtk.Widget:
        page = Adw.PreferencesPage()

        session_group = Adw.PreferencesGroup(title="This session")
        self._status = no_cut(Adw.ActionRow(title="Session"))
        session_group.add(self._status)

        start = no_cut(Adw.ActionRow(title="Start a session", subtitle="Uses the default length"))
        start_button = wrapping_button("Start")
        start_button.add_css_class("suggested-action")
        start_button.set_valign(Gtk.Align.CENTER)
        start_button.connect("clicked", lambda _b: self._start())
        start.add_suffix(start_button)
        start.set_activatable_widget(start_button)
        session_group.add(start)

        grants = no_cut(Adw.ActionRow(title="Add time", subtitle="Bounded by today's budget"))
        grant_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        grant_box.set_valign(Gtk.Align.CENTER)
        for minutes in GRANTS:
            button = wrapping_button(f"+{minutes}")
            button.connect("clicked", lambda _b, m=minutes: self._grant(m))
            grant_box.append(button)
        grants.add_suffix(grant_box)
        session_group.add(grants)

        end = no_cut(
            Adw.ActionRow(
                title="End the session now",
                subtitle="Runs the same put-away and goodbye the child knows",
            )
        )
        end_button = wrapping_button("End now")
        end_button.add_css_class("destructive-action")
        end_button.set_valign(Gtk.Align.CENTER)
        end_button.connect("clicked", lambda _b: self._end())
        end.add_suffix(end_button)
        end.set_activatable_widget(end_button)
        session_group.add(end)
        page.add(session_group)

        settings_group = Adw.PreferencesGroup(title="Settings")
        length = no_cut(Adw.SpinRow.new_with_range(MIN_SESSION_MINUTES, MAX_SESSION_MINUTES, 5))
        length.set_title("Default session length")
        length.set_subtitle(LENGTH_SUBTITLE)
        length.set_value(self.ctx.config.default_session_minutes)
        length.connect("notify::value", self._on_length_changed)
        self._length_row = length
        settings_group.add(length)

        if self.ctx.config.is_default:
            warning = no_cut(
                Adw.ActionRow(
                    title="This machine has no parent config",
                    subtitle=(
                        "The gate is on the development PIN 1234 and every activity is "
                        "allowed. Write /etc/kidnix/parent.toml as root to fix that."
                    ),
                )
            )
            warning.add_css_class("pin-error")
            settings_group.add(warning)

        panel = no_cut(
            Adw.ActionRow(
                title="Parent panel", subtitle="Allow-lists, budgets, their things -- not in v0.1"
            )
        )
        panel_button = wrapping_button("Open")
        panel_button.set_valign(Gtk.Align.CENTER)
        panel_button.connect("clicked", lambda _b: self._open_panel())
        panel.add_suffix(panel_button)
        panel.set_activatable_widget(panel_button)
        settings_group.add(panel)
        page.add(settings_group)

        exit_group = Adw.PreferencesGroup()
        logout = no_cut(Adw.ActionRow(title="Log out", subtitle="Back to the login screen"))
        logout_button = wrapping_button("Log out")
        logout_button.set_valign(Gtk.Align.CENTER)
        logout_button.connect("clicked", lambda _b: self._logout())
        logout.add_suffix(logout_button)
        logout.set_activatable_widget(logout_button)
        exit_group.add(logout)
        page.add(exit_group)

        return page

    def _refresh_actions(self) -> None:
        session = self.ctx.session
        if session.running:
            left = session.remaining(datetime.now()) // 60
            self._status.set_subtitle(f"Running, about {left} minutes left")
        else:
            self._status.set_subtitle("Not running")
        spent = session.usage.seconds // 60
        budget = session.policy.daily_budget // 60
        self._status.set_title(f"Used {spent} of {budget} minutes today")

    def _start(self) -> None:
        self.ctx.host.start_session(self.ctx.config.default_session_minutes)
        self.close()

    def _grant(self, minutes: int) -> None:
        self.ctx.host.add_minutes(minutes)
        self._refresh_actions()

    def _end(self) -> None:
        self.ctx.host.finish_now()
        self.close()

    def _on_length_changed(self, row: Adw.SpinRow, _param: object) -> None:
        minutes = int(row.get_value())
        self.ctx.config.default_session_minutes = minutes
        if self.ctx.config.read_only:
            # The parent config is root-owned on purpose (a child-writable PIN
            # is not a PIN), and the shell runs as the child. The change holds
            # for this boot; making it permanent is the parent panel's job,
            # from the parent's own account.
            row.set_subtitle(READ_ONLY_SUBTITLE)
            log.info("session length set to %d minutes for this boot only", minutes)
            return
        try:
            self.ctx.config.save()
        except OSError as exc:
            log.warning("could not save parent config: %s", exc)

    def _open_panel(self) -> None:
        about = Adw.AboutDialog(
            application_name="kidnix parent panel",
            application_icon="preferences-system",
            version="not yet built",
            comments=(
                "The parent panel is not in shell v0.1. It will hold children, "
                "time, activities, requests, their things, family and calm mode. "
                "Until then, the Journal is a plain directory tree under "
                "~/.local/share/kidnix/journal that you can open in Files."
            ),
            license_type=Gtk.License.APACHE_2_0,
        )
        about.present(self)

    def _logout(self) -> None:
        self.ctx.host.logout()
        self.close()
