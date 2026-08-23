"""Sound and calm: Dan's third question, answered in one place.

    "Can I turn all the sound down in one place?"

Until 2026-08-23 the answer was no: the machine had an unbypassable 70%
*ceiling* in hardware, which is a ceiling and not a control, and "calm mode"
was a roadmap item. This tab is the control.

Four things, and the order is the order they matter to the child who needs them
most:

* **Calm** -- one switch that owns reduced motion, a smaller soundscape and a
  slower voice, because the children it serves are not four different settings.
* **Captions** -- on by default, and the panel refuses to let a parent turn
  both the sound and the captions off. Muted-with-captions is quiet; muted
  without them is broken, and a pre-reader is told nothing at all.
* **Volume and mute.**
* **The voice** -- which of the two shipped models, and how fast it reads.
"""

from __future__ import annotations

from dataclasses import replace

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk  # noqa: E402

from .. import model as M  # noqa: E402
from . import common  # noqa: E402
from .state import PanelState  # noqa: E402

TITLE = "Sound & calm"
ICON = "audio-volume-high-symbolic"


class SoundPage(Adw.PreferencesPage):
    def __init__(self, state: PanelState) -> None:
        super().__init__(title=TITLE, icon_name=ICON)
        self.state = state
        self._groups: list[Adw.PreferencesGroup] = []
        self._pace_note: Gtk.Label | None = None
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
        sound = self.state.panel.sound

        calm = Adw.PreferencesGroup(
            title="One switch for a hard day",
            description=(
                "Calm mode slows things down all at once: screens cut instead of "
                "sliding, only the 'kept it' sound plays, and the voice reads a "
                "little slower. It is one setting rather than four because the "
                "children it helps -- autistic, sensory-defensive, anxious, or "
                "simply tired -- do not need four."
            ),
        )
        row = Adw.SwitchRow(title="Calm mode")
        row.set_subtitle(
            "This also follows the desktop's own 'reduce animation' setting, so "
            "if you have turned motion off system-wide you do not have to find "
            "it here as well."
        )
        row.set_active(sound.calm)
        row.connect("notify::active", lambda sw, _p: self._set(calm=sw.get_active()))
        calm.add(row)
        self._add(calm)

        heard = Adw.PreferencesGroup(
            title="Being heard, and being read",
            description=(
                "Read-aloud is how a child who cannot read yet is told what to "
                "do. Captions are what is left when they cannot hear it."
            ),
        )
        captions = Adw.SwitchRow(title="Show every spoken line as writing")
        captions.set_subtitle(
            "A strip under the buttons, for about four seconds. Leave it on: "
            "about one child in a thousand is deaf, and far more have glue ear "
            "at five -- intermittent, and undiagnosed for months. The line that "
            "costs most is 'Draw is asking if you're done', because without it a "
            "deaf child does not know the question is theirs and loses the "
            "drawing.\n\nTurning it off takes effect at the next start."
        )
        captions.set_active(sound.captions)
        captions.connect("notify::active", lambda sw, _p: self._set(captions=sw.get_active()))
        heard.add(captions)

        mute = Adw.SwitchRow(title="Silence")
        mute.set_subtitle(
            "No sounds and no speaking. Safe because the captions are on -- the "
            "computer still shows every line it would have said."
        )
        mute.set_active(sound.mute)
        mute.connect("notify::active", lambda sw, _p: self._set_mute(sw.get_active()))
        heard.add(mute)

        volume = Adw.ActionRow(title="Volume")
        volume.set_subtitle("On top of the machine's own 70% ceiling, which cannot be raised.")
        scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 5)
        scale.set_value(round(sound.sound_volume * 100))
        scale.set_size_request(220, -1)
        scale.set_draw_value(True)
        scale.set_value_pos(Gtk.PositionType.RIGHT)
        scale.set_valign(Gtk.Align.CENTER)
        scale.set_sensitive(not sound.mute)
        scale.connect(
            "value-changed",
            lambda widget: self._set(sound_volume=round(widget.get_value() / 100.0, 2)),
        )
        volume.add_suffix(scale)
        heard.add(volume)

        if sound.mute and not sound.captions:
            heard.add(
                common.note_row(
                    "With the sound off and the captions off, a child who cannot "
                    "read is told nothing at all. Turn one of them back on before "
                    "saving.",
                    warning=True,
                )
            )
        self._add(heard)

        self._add(self._voice_group(sound))

    def _voice_group(self, sound: M.SoundSettings) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup(
            title="The voice",
            description=(
                "Both voices are the same reader -- a British English voice "
                "trained on public-domain recordings, on this machine, offline. "
                "They differ only in size and therefore in how quickly they "
                "answer."
            ),
        )
        row = Adw.ComboRow(title="Which voice")
        names = Gtk.StringList()
        for _value, label, detail in M.VOICES:
            names.append(f"{label} — {detail}")
        row.set_model(names)
        values = [value for value, _label, _detail in M.VOICES]
        row.set_selected(values.index(sound.voice) if sound.voice in values else 0)
        row.connect(
            "notify::selected",
            lambda combo, _p: self._set_voice(values[combo.get_selected()]),
        )
        group.add(row)

        pace = Adw.ComboRow(title="How fast it reads")
        rates = Gtk.StringList()
        for _rate, label in M.READ_ALOUD_RATES:
            rates.append(label)
        pace.set_model(rates)
        rate_values = [rate for rate, _label in M.READ_ALOUD_RATES]
        pace.set_selected(
            rate_values.index(sound.speech_rate) if sound.speech_rate in rate_values else 1
        )
        pace.connect(
            "notify::selected",
            lambda combo, _p: self._set(speech_rate=rate_values[combo.get_selected()]),
        )
        group.add(pace)

        self._pace_note = Gtk.Label()
        self._pace_note.set_wrap(True)
        self._pace_note.set_xalign(0.0)
        self._pace_note.add_css_class("dim-label")
        self._pace_note.set_margin_start(6)
        self._pace_note.set_margin_top(4)
        holder = Adw.PreferencesRow()
        holder.set_activatable(False)
        holder.set_child(self._pace_note)
        group.add(holder)
        self._update_pace_note()

        group.add(
            common.note_row(
                "In force. The child's screen reads this pace out of the settings "
                "and sets the voice to it. Calm mode is a floor on it: with calm mode on, "
                "the voice reads at whichever of the two is slower. Some of what "
                "the machine says is pre-recorded at the normal pace -- change "
                "the pace and it stops using those recordings and speaks "
                "everything instead, which is a shade less pretty and does what "
                "you asked."
            )
        )
        return group

    # -- edits --

    def _set(self, **changes) -> None:
        self.state.panel.sound = replace(self.state.panel.sound, **changes)
        self.state.touch()
        self._update_pace_note()

    def _set_mute(self, mute: bool) -> None:
        self._set(mute=mute)
        self.refresh()

    def _set_voice(self, voice: str) -> None:
        self._set(voice=voice)

    def _update_pace_note(self) -> None:
        if self._pace_note is None:
            return
        sound = self.state.panel.sound
        self._pace_note.set_label(
            f"The reader will be asked for {sound.length_scale:.2f} times its "
            "ordinary pace. Between 1.05 and 1.15 sounds unhurried to a "
            "five-year-old without sounding like a slowed-down recording."
        )

    def _add(self, group: Adw.PreferencesGroup) -> None:
        self.add(group)
        self._groups.append(group)


__all__ = ["SoundPage"]
