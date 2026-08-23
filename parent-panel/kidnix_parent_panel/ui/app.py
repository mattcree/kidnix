"""The window: six tabs, one Apply, one sentence back.

Deliberately **not** a preferences dialogue that saves on every keystroke.
``/etc/kidnix/parent.toml`` is root-owned, so every save is a polkit prompt, and
a machine that asked a parent for their password each time they nudged a spin
button would be a machine nobody would finish setting up. So edits accumulate, a
banner says there is something to save, and one press writes everything at once.

The banner's sentence is the one the review asked for and it is the true one:
the shell reads these files when a session **starts**, so a change made while a
child is mid-sitting reaches them at the next one.
"""

from __future__ import annotations

import logging

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, Gtk  # noqa: E402

from .. import __version__  # noqa: E402
from .. import validate as V  # noqa: E402
from . import activities as activities_tab  # noqa: E402
from . import children as children_tab  # noqa: E402
from . import family as family_tab  # noqa: E402
from . import sound as sound_tab  # noqa: E402
from . import tasks  # noqa: E402
from . import things as things_tab  # noqa: E402
from . import timing as time_tab  # noqa: E402
from . import updates as updates_tab  # noqa: E402
from .state import APPLIED_NOTE, PanelState  # noqa: E402

log = logging.getLogger(__name__)

APP_ID = "org.kidnix.ParentPanel"
STYLE = (__file__.rsplit("/", 1)[0]) + "/style.css"

#: 1180x760 is the smallest window in which the Activities tab shows a picture,
#: a name and a goal line without wrapping the goal to four lines, measured on
#: the 1280x800 panel kidnix ships for. Below that libadwaita's own adaptive
#: behaviour takes over and nothing breaks; this is a default, not a minimum.
DEFAULT_WIDTH = 1180
DEFAULT_HEIGHT = 760


class ParentPanelWindow(Adw.ApplicationWindow):
    def __init__(self, application: Adw.Application, state: PanelState) -> None:
        super().__init__(application=application, title="kidnix — Parent Panel")
        self.state = state
        self.set_default_size(DEFAULT_WIDTH, DEFAULT_HEIGHT)

        self.toasts = Adw.ToastOverlay()
        toolbar = Adw.ToolbarView()
        self.toasts.set_child(toolbar)
        self.set_content(self.toasts)

        self.stack = Adw.ViewStack()
        self.pages = {
            "children": children_tab.ChildrenPage(state),
            "time": time_tab.TimePage(state),
            "activities": activities_tab.ActivitiesPage(state),
            "sound": sound_tab.SoundPage(state),
            "things": things_tab.ThingsPage(state, toast=self.say),
            "family": family_tab.FamilyPage(state),
            "updates": updates_tab.UpdatesPage(state, toast=self.say),
        }
        for name, page in self.pages.items():
            self.stack.add_titled_with_icon(
                page, name, page.get_title(), page.get_icon_name() or "preferences-system-symbolic"
            )

        header = Adw.HeaderBar()
        switcher = Adw.ViewSwitcher()
        switcher.set_stack(self.stack)
        switcher.set_policy(Adw.ViewSwitcherPolicy.WIDE)
        header.set_title_widget(switcher)

        self.apply_button = Gtk.Button(label="Apply")
        self.apply_button.add_css_class("suggested-action")
        self.apply_button.set_sensitive(False)
        self.apply_button.connect("clicked", self._on_apply)
        header.pack_end(self.apply_button)

        self.revert_button = Gtk.Button(label="Discard")
        self.revert_button.set_sensitive(False)
        self.revert_button.connect("clicked", self._on_revert)
        header.pack_end(self.revert_button)

        toolbar.add_top_bar(header)

        self.banner = Adw.Banner()
        self.banner.set_revealed(False)
        toolbar.add_top_bar(self.banner)

        toolbar.set_content(self.stack)

        bottom = Adw.ViewSwitcherBar()
        bottom.set_stack(self.stack)
        bottom.set_reveal(False)
        toolbar.add_bottom_bar(bottom)

        state.subscribe(self._on_state_changed)
        self._on_state_changed()

    # -- state --

    def _on_state_changed(self) -> None:
        problems = self.state.problems()
        blocking = V.fatal(problems)
        self.apply_button.set_sensitive(self.state.dirty and not blocking)
        self.revert_button.set_sensitive(self.state.dirty)

        if blocking:
            self.banner.set_title(blocking[0].message)
            self.banner.set_revealed(True)
            self.banner.add_css_class("error")
        elif self.state.dirty:
            notes = [p for p in problems if not p.fatal]
            self.banner.remove_css_class("error")
            self.banner.set_title(
                notes[0].message
                if notes
                else "Not saved yet. Press Apply — it takes effect at your child's next session."
            )
            self.banner.set_revealed(True)
        else:
            self.banner.set_revealed(False)

    def _on_apply(self, _button: Gtk.Button) -> None:
        # On a thread: pkexec blocks until a human has typed a password into an
        # agent that is a different process, and a settings window frozen
        # behind that dialogue is a settings window a parent force-quits.
        busy = tasks.Busy(self.apply_button, self.revert_button)
        self.say("Saving\u2026")

        def finished(result: object) -> None:
            busy.finish()
            self._on_state_changed()
            # Saving is the one thing that CHANGES the model rather than only
            # writing it out: it copies every family photograph into
            # /var/lib/kidnix/photos and rewrites the paths to point there. So
            # the Family tab is redrawn either way -- after a refusal too, when
            # the copy has happened and the write has not.
            self.pages["family"].refresh()
            if isinstance(result, Exception):
                self.say(f"The settings could not be saved: {result}")
            elif getattr(result, "ok", False):
                # A successful save carries a message only when something a
                # parent has to know happened alongside it -- today, a family
                # photograph that could not be copied where the child can see
                # it. Saying APPLIED_NOTE over that would be the silence the
                # photograph bug was made of.
                note = getattr(result, "message", "")
                self.say(f"{APPLIED_NOTE} {note}" if note else APPLIED_NOTE)
            else:
                self.say(getattr(result, "message", "") or "Nothing was saved.")

        tasks.run_async(self.state.save, finished, synchronous=self.state.synchronous)

    def _on_revert(self, _button: Gtk.Button) -> None:
        self.state.reload()
        for page in self.pages.values():
            page.refresh()
        self.say("Back to what is on the machine.")

    def say(self, text: str) -> None:
        if not text:
            return
        toast = Adw.Toast(title=text)
        toast.set_timeout(6)
        self.toasts.add_toast(toast)


class ParentPanelApplication(Adw.Application):
    def __init__(self, state: PanelState | None = None) -> None:
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.NON_UNIQUE)
        self._state = state
        self.window: ParentPanelWindow | None = None

    def do_startup(self) -> None:
        Adw.Application.do_startup(self)
        _load_style()

    def do_activate(self) -> None:
        if self.window is None:
            state = self._state if self._state is not None else PanelState()
            self.window = ParentPanelWindow(self, state)
        self.window.present()


def _load_style() -> None:
    display = Gdk.Display.get_default()
    if display is None:  # pragma: no cover - no display at all
        return
    provider = Gtk.CssProvider()
    try:
        provider.load_from_path(STYLE)
    except Exception as exc:
        log.warning("could not load %s (%s)", STYLE, exc)
        return
    Gtk.StyleContext.add_provider_for_display(
        display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )


def version_line() -> str:
    return f"kidnix-parent-panel {__version__}"


__all__ = [
    "APP_ID",
    "DEFAULT_HEIGHT",
    "DEFAULT_WIDTH",
    "ParentPanelApplication",
    "ParentPanelWindow",
    "version_line",
]
