"""The one mutable thing the window and its six pages share.

A page never writes a file and never forks: it changes :attr:`PanelState.panel`
and calls :meth:`PanelState.touch`. The window owns the save banner, the
validation run and the single call to ``kidnix-config``. That keeps "what does
this control mean" (the page) apart from "what happens when a parent presses
Apply" (the window), which is the only structure that survives six tabs.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

from .. import catalogue, config_io, system
from .. import model as M
from .. import validate as V

log = logging.getLogger(__name__)

#: The sentence every save ends with. It is the honest one: the shell reads
#: ``parent.toml`` and ``session.toml`` when a session starts, so a change made
#: while a child is mid-sitting does not reach them until the next one.
APPLIED_NOTE = "Saved. It takes effect at your child's next session."


class PanelState:
    """The model, the catalogue, and who wants to know when they change."""

    def __init__(
        self,
        panel: M.PanelModel | None = None,
        activities: catalogue.Catalogue | None = None,
        runner: system.Runner = system.run,
        etc: Path = config_io.ETC,
        usr: Path = config_io.USR,
        synchronous: bool = False,
        photo_dir: Path = system.PHOTO_DIR,
        installed: Callable[[catalogue.Entry], bool] = catalogue.is_installed,
    ) -> None:
        #: Run privileged helpers inline rather than on a thread. True in the
        #: tests and under ``--screenshot``, where there is no main loop for a
        #: thread's answer to come back to.
        self.synchronous = synchronous
        self.etc = etc
        self.usr = usr
        #: Where family photographs are copied so the CHILD can read them. An
        #: argument so a test never writes outside its tmp_path.
        self.photo_dir = photo_dir
        #: "Is the program this manifest names actually on the machine?" An
        #: argument for the same reason ``runner`` is: the real answer forks
        #: ``flatpak info`` and depends on what this laptop happens to have
        #: installed, and a widget test must not.
        self.installed = installed
        self.runner = runner
        self.panel = panel if panel is not None else config_io.load_model(etc, usr)
        self.activities = (
            activities if activities is not None else catalogue.load(catalogue.SYSTEM_ACTIVITY_DIR)
        )
        self._listeners: list[Callable[[], None]] = []
        self._dirty = False
        #: Set while a page is rebuilding itself from the model, so that the
        #: widget callbacks that rebuilding fires do not count as edits. Without
        #: it, opening the panel marks it dirty and the banner appears before a
        #: parent has touched anything.
        self.loading = False

    # -- change notification --

    def subscribe(self, listener: Callable[[], None]) -> None:
        self._listeners.append(listener)

    def touch(self) -> None:
        """A parent changed something."""
        if self.loading:
            return
        self._dirty = True
        for listener in list(self._listeners):
            listener()

    @property
    def dirty(self) -> bool:
        return self._dirty

    def clear_dirty(self) -> None:
        self._dirty = False
        for listener in list(self._listeners):
            listener()

    # -- validation and saving --

    def problems(self) -> list[V.Problem]:
        return V.validate(self.panel, self.activities.ids)

    def can_save(self) -> bool:
        return V.ok(self.problems())

    def save(self) -> system.ApplyResult:
        """One call to ``kidnix-config``, one polkit prompt, one answer.

        Everything goes together on purpose: a parent who changed the session
        length *and* added a child should type their password once and get one
        sentence back, not two prompts and an ambiguous half-saved machine.

        **One thing happens before the payload is built**: every family
        photograph is copied into ``/var/lib/kidnix/photos`` and the model is
        rewritten to point at the copy. It happens here, unprivileged, as the
        grown-up who chose the file -- not in the root helper, which must never
        be asked to copy a path its caller named and could not read. See
        :func:`kidnix_parent_panel.system.install_photo`.
        """
        problems = V.fatal(self.problems())
        if problems:
            return system.ApplyResult(False, (), problems[0].message)
        self.panel.family, photo_notes = system.install_photos(self.panel.family, self.photo_dir)
        result = system.apply_settings(self.panel.to_payload(), self.runner)
        if result.ok:
            self.clear_dirty()
            if photo_notes:
                # A save that worked, with something the parent has to know:
                # one of their photographs did not make it to where the child
                # can see it, and silence there is what the whole bug was.
                return replace(result, message=" ".join(photo_notes))
        return result

    def reload(self) -> None:
        """Throw away unsaved edits and re-read the machine."""
        self.panel = config_io.load_model(self.etc, self.usr)
        self.clear_dirty()


__all__ = ["APPLIED_NOTE", "PanelState"]
