"""The window an activity gets, and everything that comes with it.

:class:`ActivityApplication` is the whole of the GTK side of the SDK. An
activity says what it is called, fills a box, and says what to save; the
application does the rest, and the rest is the list of things that were
otherwise going to be re-derived, wrongly, once per activity:

* one ``Adw.ApplicationWindow``, full-screen under gnome-kiosk, sized to the
  rectangle **below the band** (:class:`~kidnix_activity.metrics.ContentArea`);
* the shell's ``theme.css`` and then the SDK's ``activity.css``, so an activity
  is the same object as the shell rather than a lookalike;
* ``[access]`` from the root-owned ``parent.toml`` -- calm mode's reduced
  motion, the volume, mute -- applied to the voice and the earcons;
* one voice (:class:`~kidnix_activity.speech.ActivitySpeech`), which speaks
  through speech-dispatcher *and* sends the caption to the shell;
* the earcons, from the shell's own generated set, so "kept" sounds the same
  everywhere;
* a keyboard ring that does not touch Escape
  (:mod:`kidnix_activity.keyboard`);
* and a SIGTERM handler that calls ``on_finish()`` once and exits
  (:mod:`kidnix_activity.lifecycle`).

**What the activity does not do**, and cannot do from here: draw the band,
handle Back or Escape, end the session, show a quit dialogue, reach the
network, or decide when it is finished. All six belong to the shell, and five
of them are the shell's *only* because a five-year-old must find them in the
same place in every activity.

The window is not full-screen by request. gnome-kiosk's ``window-config.ini``
places every window that is not the band into ``0,band_height W x
(H - band_height)`` (impl. notes section 18.2), and a window that *also* asks
for the whole monitor gets an answer neither side agrees on -- measured in the
VM at 1280x741 against a compositor-constrained 1280x708. So the SDK asks for
exactly the rectangle it expects and lets the compositor be right.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gtk  # noqa: E402

import kidnix_shell  # noqa: E402
from kidnix_shell.access import AccessConfig  # noqa: E402
from kidnix_shell.journal import Entry  # noqa: E402
from kidnix_shell.settings import ParentConfig  # noqa: E402
from kidnix_shell.sound import KEEP, TAP, Earcons  # noqa: E402
from kidnix_shell.widgets import SpeechUI  # noqa: E402

from .env import LaunchEnv  # noqa: E402
from .journal import save_entry  # noqa: E402
from .keyboard import ActivityKeyboard  # noqa: E402
from .lifecycle import FinishHandler, glib_installer  # noqa: E402
from .metrics import ContentArea  # noqa: E402
from .speech import ActivitySpeech  # noqa: E402

log = logging.getLogger(__name__)

__all__ = ["ActivityApplication", "ActivityWindow", "application_id_for"]

#: Where the SDK's own stylesheet lives, beside this file.
ACTIVITY_CSS = Path(__file__).parent / "activity.css"
#: The shell's, which is loaded first and never modified.
SHELL_CSS = Path(kidnix_shell.__path__[0]) / "theme.css"

#: The prefix every first-party activity's GApplication id takes.
APP_ID_PREFIX = "org.kidnix.activity"


def application_id_for(activity_id: str) -> str:
    """``hello-draw`` -> ``org.kidnix.activity.hello_draw``.

    A GApplication id is dot-separated and each element must start with a
    letter; a manifest id is a slug and may contain hyphens and dots. The
    mapping is total and lossy in exactly one direction, which is fine -- the
    id here identifies the *process* to the session bus, and the manifest id
    remains the identity everywhere it matters (the Journal, the log, resume).
    """
    cleaned = "".join(char if char.isalnum() else "_" for char in activity_id.strip())
    cleaned = cleaned.strip("_") or "activity"
    if not cleaned[0].isalpha():
        cleaned = f"a{cleaned}"
    return f"{APP_ID_PREFIX}.{cleaned}"


class ActivityWindow(Adw.ApplicationWindow):
    """One window, one content box, sized in millimetres.

    ``add()`` is the only layout API on purpose: an activity that needs
    something more elaborate builds it and adds the one widget, and the SDK
    stays out of the way. What the SDK insists on is the margin and the gap --
    both come from :class:`ContentArea` and both are floors.
    """

    def __init__(
        self,
        application: Adw.Application,
        *,
        title: str,
        area: ContentArea,
        speech: ActivitySpeech,
        calm: bool = False,
    ) -> None:
        super().__init__(application=application)
        self.set_title(title)
        self.add_css_class("kidnix")
        self.add_css_class("kidnix-activity")
        if calm:
            self.add_css_class("calm")

        self.area = area
        self.speech = speech
        self.keys = ActivityKeyboard()

        self.content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=area.gap)
        self.content.add_css_class("surface")
        margin = area.margin
        for setter in (
            self.content.set_margin_top,
            self.content.set_margin_bottom,
            self.content.set_margin_start,
            self.content.set_margin_end,
        ):
            setter(margin)
        self.set_content(self.content)

        if area.known:
            # Exactly the rectangle the compositor is going to give us. See the
            # module docstring: asking for the monitor instead is how the two
            # sides come to disagree about what happened.
            self.set_default_size(area.width, area.height)

        self.keys.attach(self)

    def add(self, widget: Gtk.Widget) -> Gtk.Widget:
        """Put ``widget`` in the content box and keep the ring current."""
        self.content.append(widget)
        self.keys.set_content(self.content)
        return widget

    def clear(self) -> None:
        """Empty the content box -- a new round, a new screen."""
        child = self.content.get_first_child()
        while child is not None:
            following = child.get_next_sibling()
            self.content.remove(child)
            child = following
        self.keys.forget()
        self.keys.set_content(self.content)

    def speak(self, text: str) -> bool:
        """Say one line, and show it under the band. The activity's own voice."""
        return self.speech.speak(text)


class ActivityApplication(Adw.Application):
    """What ``main()`` builds. One window, one voice, one save.

    ::

        app = ActivityApplication("hello-draw", "Hello draw")
        app.set_build(build)          # fills the window
        app.set_on_finish(save)       # called on SIGTERM, once
        return app.run(argv)
    """

    def __init__(
        self,
        activity_id: str,
        title: str,
        *,
        build: Callable[[ActivityWindow], None] | None = None,
        on_finish: Callable[[], None] | None = None,
        env: Mapping[str, str] | None = None,
        access: AccessConfig | None = None,
        screen: Any = None,
        speech: ActivitySpeech | None = None,
        earcons: Earcons | None = None,
    ) -> None:
        super().__init__(application_id=application_id_for(activity_id))
        self.activity_id = activity_id
        self.title = title
        self.launch = LaunchEnv.from_env(env)
        if not self.launch.launched_by_shell:
            log.info(
                "not launched by the kidnix shell (%s is unset); the Journal writer "
                "will need an activity id of its own",
                "KIDNIX_ACTIVITY_ID",
            )
        log.info("launch environment: %s", self.launch.describe())

        # `[access]` is the child's, not ours: the same root-owned parent.toml
        # the shell reads, so calm mode and the volume are one setting for the
        # whole machine rather than one per program.
        self.access = access if access is not None else ParentConfig.discover().access
        self.area = ContentArea.detect(screen, captions=self.access.captions)
        log.info("content area: %s", self.area.describe())

        self.speech = (
            speech
            if speech is not None
            else ActivitySpeech(activity_id, access=self.access, env=env)
        )
        self.earcons = (
            earcons
            if earcons is not None
            else Earcons(cache_dir=self.launch.paths.sounds_cache, access=self.access)
        )
        #: What :meth:`run` will return once the main loop has come back.
        self.exit_code: int | None = None
        #: **Not** ``sys.exit``. Raising ``SystemExit`` from inside a GLib
        #: callback does not end a GTK application: PyGObject catches it at the
        #: callback boundary, the main loop carries straight on, and the shell
        #: is left waiting for a process that has already saved and thinks it
        #: has gone. (Measured: ``timeout 6 python -m ...hello_draw`` logged
        #: "saved on the way out" and then had to be killed.) So the exiter
        #: quits the loop, ``run()`` returns, and the exit code comes back out
        #: through ``main()`` the ordinary way.
        self.finish = FinishHandler(on_finish, exiter=self._stop)

        self._build: Callable[[ActivityWindow], None] | None = build
        self.window: ActivityWindow | None = None
        self._signals_armed = False

    def _stop(self, code: int) -> None:
        self.exit_code = code
        self.quit()

    def run(self, argv: list[str] | None = None) -> int:
        """The main loop. Returns the code the finish handler decided, if any."""
        status = super().run(argv)
        return self.exit_code if self.exit_code is not None else int(status)

    # -- the two things an activity supplies --

    def set_build(self, build: Callable[[ActivityWindow], None]) -> None:
        """What fills the window. Called once, with the window, on activate."""
        self._build = build

    def set_on_finish(self, on_finish: Callable[[], None] | None) -> None:
        """What to save when the shell says finish. Called **once**, on SIGTERM."""
        self.finish.set_on_finish(on_finish)

    # -- convenience the activity would otherwise re-derive --

    def speak(self, text: str) -> bool:
        """One line, spoken and captioned."""
        return self.speech.speak(text)

    def play(self, earcon: str = TAP) -> bool:
        """One of the shell's five earcons, at the child's own volume."""
        return self.earcons.play(earcon)

    def save_entry(
        self,
        kind: str,
        files: Sequence[Path],
        caption: str | None = None,
        voice: Path | None = None,
        meta: Mapping[str, Any] | None = None,
        *,
        keep_sound: bool = True,
    ) -> Entry:
        """Keep what the child made, and make the sound that says so.

        The earcon is the point of the wrapper: "something was kept" is the one
        sound in kidnix that reports an *outcome* rather than punctuating an
        action, it is the one calm mode keeps, and an activity that saved
        silently would be the only place in the product where a child is not
        told that their work is safe.
        """
        entry = save_entry(
            kind,
            files,
            caption,
            voice,
            meta,
            activity_name=self.title,
            launch=self.launch,
        )
        if keep_sound:
            self.earcons.play(KEEP)
        return entry

    # -- GTK lifecycle --

    def do_activate(self) -> None:
        if self.window is not None:
            self.window.present()
            return
        self._load_css()
        self.window = ActivityWindow(
            self,
            title=self.title,
            area=self.area,
            speech=self.speech,
            calm=self.access.reduced_motion(_animations_enabled()),
        )
        # One bridge, created here, so every widget shares a registry and the
        # read-aloud ring lands on the control that is actually speaking.
        self.speech.ui = SpeechUI(self.speech.manager)
        self._arm_signals()
        if self._build is not None:
            self._build(self.window)
        self.window.keys.set_content(self.window.content)
        self.window.present()
        self.window.keys.focus_first()

    def _arm_signals(self) -> None:
        """SIGTERM and SIGINT, through the main loop rather than from a handler."""
        if self._signals_armed:
            return
        self._signals_armed = True
        self.finish.install(glib_installer())

    def _load_css(self) -> None:
        """The shell's stylesheet, then ours. In that order, and never edited."""
        display = Gdk.Display.get_default()
        if display is None:  # pragma: no cover - no display, no styling
            return
        for index, path in enumerate((SHELL_CSS, ACTIVITY_CSS)):
            if not path.is_file():  # pragma: no cover - a broken install
                log.warning("stylesheet %s is missing; the activity will look wrong", path)
                continue
            provider = Gtk.CssProvider()
            provider.load_from_path(str(path))
            Gtk.StyleContext.add_provider_for_display(
                display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + index
            )

    def do_shutdown(self) -> None:
        self.speech.close()
        self.earcons.close()
        Adw.Application.do_shutdown(self)


def _animations_enabled() -> bool:
    """``gtk-enable-animations``: the desktop's own reduced-motion answer.

    A parent who turned motion off system-wide should not have to find a second
    switch inside every activity.
    """
    try:  # pragma: no cover - requires a display
        settings = Gtk.Settings.get_default()
        if settings is None:
            return True
        return bool(settings.get_property("gtk-enable-animations"))
    except Exception:  # pragma: no cover
        return True
