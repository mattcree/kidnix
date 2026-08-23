"""The caption hook, across a process boundary.

The accessibility review's B2 is *nothing essential is audio-only*: every line
the shell speaks is also written down, for about four seconds, in the caption
strip under the band. The strip belongs to the **band window**, which belongs
to the shell, and during an activity that band is the only kidnix chrome on
screen -- so an activity that speaks without telling the shell has just made
its instructions audio-only for a deaf child, which is the whole finding again
with a new owner.

So there is a tiny local IPC, and it is deliberately the smallest one that can
work:

* **A datagram, not a stream.** ``AF_UNIX`` + ``SOCK_DGRAM`` at
  ``$XDG_RUNTIME_DIR/kidnix/captions.sock``. There is no connection to open,
  nothing to reconnect, no ordering to maintain and -- the property that
  actually matters -- **no way for a slow or dead listener to block a child's
  drawing program**. ``sendto`` to a missing path fails immediately with
  ``ENOENT``; to a full queue it fails immediately with ``EAGAIN``. Both are
  swallowed.
* **One JSON object per datagram**::

      {"speak": "Press the big button.", "source": "hello-draw"}

  ``speak`` is the line as it was said; ``source`` is the manifest id, so the
  shell's log can say who is talking. Unknown keys are reserved; a listener
  must ignore them rather than reject the message.
* **One voice, and it is the listener's.** A delivered datagram *is* the
  utterance: the shell shows the line in the strip and says it with the shell's
  own voice, and :mod:`kidnix_activity.speech` does not speak it here as well.
  08 section 3.6 is "one voice", and two speech-dispatcher connections saying
  the same sentence a beat apart -- neither able to cancel the other -- is
  worse than either alone. :meth:`CaptionClient.send` returning ``False`` is
  therefore the signal that this process must speak the line itself.
* **The socket is optional.** A missing socket is the normal state on a
  developer's desktop and during every headless test, and it costs the child
  nothing they can hear -- the activity speaks the line itself. It costs a deaf
  child the caption, which is why the shell-side listener
  (:mod:`kidnix_shell.captions`, ``docs/design/activity-sdk.md`` section 4.2)
  is part of the shell rather than a nice-to-have.

Nothing in this module needs a display, a GTK main loop or a running shell, so
all of it is unit-tested.
"""

from __future__ import annotations

import json
import logging
import os
import socket
from collections.abc import Callable, Mapping
from pathlib import Path

log = logging.getLogger(__name__)

#: ``$XDG_RUNTIME_DIR/kidnix/captions.sock``.
SOCKET_DIRNAME = "kidnix"
SOCKET_NAME = "captions.sock"

#: A datagram bigger than this is a bug, not a caption. The strip is **one**
#: line at 20 pt (``kidnix_shell.access.CAPTION_LINES``) and the longest thing
#: the shell itself ever says is 50 characters; 500 is room for an activity
#: with more to say than we do, and a bound the kernel will never argue with.
MAX_TEXT_CHARS = 500

#: How long we are willing to wait for the kernel to take the datagram. The
#: send is non-blocking in practice; the timeout is the belt to that brace, so
#: that a pathological listener cannot stall a five-year-old's main loop.
SEND_TIMEOUT_SECONDS = 0.05

#: What a sender is: ``(path, payload) -> delivered``. Injected by the tests,
#: which is how the whole of this module is provable without a socket.
Sender = Callable[[Path, bytes], bool]


def socket_path(env: Mapping[str, str] | None = None) -> Path | None:
    """Where the shell's caption listener is, or ``None`` if it cannot be.

    ``None`` means "there is no ``$XDG_RUNTIME_DIR``", which is a session
    without a user runtime directory -- a build container, a cron job, a test.
    It is not an error and it is not logged at warning: an activity is allowed
    to run somewhere that has no shell.
    """
    environ = os.environ if env is None else env
    runtime = environ.get("XDG_RUNTIME_DIR", "").strip()
    if not runtime:
        return None
    return Path(runtime) / SOCKET_DIRNAME / SOCKET_NAME


def tidy(text: str) -> str:
    """One line, no runaway length. What actually goes on the wire.

    The strip is a single line and a caption that wrapped would be clipped by
    the strip the compositor gave the band window (impl. notes section 22.2),
    so newlines and runs of whitespace become single spaces here rather than
    becoming somebody else's clipping bug.
    """
    return " ".join((text or "").split())[:MAX_TEXT_CHARS]


def encode(text: str, source: str) -> bytes:
    """The datagram. UTF-8 JSON, no trailing newline, no framing.

    ``ensure_ascii`` is off so that a caption with a curly quote in it stays
    one character wide in the strip rather than becoming ``\\u2019``.
    """
    return json.dumps({"speak": tidy(text), "source": source}, ensure_ascii=False).encode("utf-8")


def decode(payload: bytes) -> tuple[str, str] | None:
    """``(speak, source)`` from a datagram, or ``None`` if it is not one.

    The **shell side** of the wire, written here so that the two halves cannot
    drift and so that the listener, when it lands, has a tested parser to call
    rather than a fresh ``json.loads``. It is deliberately forgiving about
    everything except the one field that matters: a datagram with no ``speak``
    is not a caption, and a caption from an unknown source is still a caption.

    A listener must treat the result as **text, never as an instruction**: it
    arrives from another process and is only as trustworthy as that process.
    Display it, say it in the listener's own voice, and never execute it or
    log it as the child's own words.
    """
    try:
        data = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    speak = data.get("speak")
    if not isinstance(speak, str):
        return None
    text = tidy(speak)
    if not text:
        return None
    source = data.get("source")
    return text, str(source) if isinstance(source, str) else ""


def send_datagram(path: Path, payload: bytes) -> bool:
    """The real sender. Never raises, never blocks for long, never retries."""
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as sock:
            sock.settimeout(SEND_TIMEOUT_SECONDS)
            sock.sendto(payload, str(path))
        return True
    except OSError as exc:  # no socket, no listener, full queue, no permission
        log.debug("no caption listener at %s (%s)", path, exc)
        return False


class CaptionClient:
    """Sends every spoken line to the shell's caption strip. Best effort.

    Built to be *boring*: it holds no socket open, keeps no state that can go
    stale, and answers every failure the same way -- ``False``, one debug line,
    and the child hears the sentence anyway.

    The one piece of state is :attr:`missing_logged`, so that an activity
    running for twenty minutes with no shell behind it logs the fact once
    rather than on every utterance.
    """

    def __init__(
        self,
        source: str,
        path: Path | None = None,
        *,
        sender: Sender | None = None,
        env: Mapping[str, str] | None = None,
    ) -> None:
        self.source = source
        self.path = path if path is not None else socket_path(env)
        self._send: Sender = sender or send_datagram
        self.missing_logged = False
        #: The last line handed to :meth:`send`, whether or not it arrived.
        #: The test hook, and what an activity's own on-screen caption (if it
        #: ever grows one) would draw.
        self.last_text = ""

    @property
    def available(self) -> bool:
        """Is there a socket file to send to *right now*?

        Asked afresh every time rather than cached: the shell may be restarted
        under a running activity, and an activity that had decided once that
        captions were off would stay silent for the rest of the session.
        """
        if self.path is None:
            return False
        try:
            return self.path.is_socket()
        except OSError:  # pragma: no cover - a runtime dir that vanished
            return False

    def send(self, text: str) -> bool:
        """Show ``text`` under the band. Returns whether it got there."""
        line = tidy(text)
        self.last_text = line
        if not line:
            return False
        if self.path is None:
            self._note_missing("no XDG_RUNTIME_DIR")
            return False
        if not self.available:
            self._note_missing(f"no socket at {self.path}")
            return False
        delivered = self._send(self.path, encode(line, self.source))
        if not delivered:
            self._note_missing(f"the listener at {self.path} did not take it")
        return delivered

    def _note_missing(self, why: str) -> None:
        if self.missing_logged:
            return
        self.missing_logged = True
        # INFO, not WARNING: a developer running the activity on their own
        # desktop is not doing anything wrong, and a child's session with a
        # working shell never reaches this line at all.
        log.info("captions are not reaching the shell (%s); speaking anyway", why)
