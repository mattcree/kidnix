"""A very small QEMU Machine Protocol client, plus synthetic input.

Everything the end-to-end scenario does to the guest goes through here:
QEMU's ``input-send-event`` for the mouse and keyboard, and ``screendump``
for pixels. Nothing is installed inside the VM to make this work -- from the
guest's point of view a person is sitting at the machine.

Standard library only, same rule as ``tests/boot/boot_test.py``: this has to
run on a CI runner with nothing but ``python3``.
"""

from __future__ import annotations

import json
import socket
import time
from pathlib import Path

#: QEMU normalises every absolute pointing device onto this range, whatever
#: the guest's resolution is (``qemu/ui/input.c``, ``INPUT_EVENT_ABS_MAX``).
ABS_MAX = 0x7FFF


class QMPError(RuntimeError):
    """A QMP command came back as an error, or the socket went away."""


class QMPClient:
    """Connect, negotiate capabilities, execute commands."""

    def __init__(self, path: str | Path, timeout: float = 60.0) -> None:
        self.path = str(path)
        self.timeout = timeout
        self._sock: socket.socket | None = None
        self._buf = b""

    # -- lifecycle --

    def connect(self) -> QMPClient:
        deadline = time.monotonic() + self.timeout
        last: Exception | None = None
        while time.monotonic() < deadline:
            try:
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.settimeout(self.timeout)
                sock.connect(self.path)
                self._sock = sock
                break
            except OSError as exc:  # QEMU has not created the socket yet
                last = exc
                time.sleep(0.2)
        else:
            raise QMPError(f"could not connect to QMP socket {self.path}: {last}")
        self._read_json()  # greeting
        self.execute("qmp_capabilities")
        return self

    def close(self) -> None:
        if self._sock is not None:
            try:
                self._sock.close()
            finally:
                self._sock = None

    def __enter__(self) -> QMPClient:
        return self.connect()

    def __exit__(self, *_exc: object) -> None:
        self.close()

    # -- protocol --

    def _read_json(self) -> dict:
        assert self._sock is not None
        while b"\n" not in self._buf:
            chunk = self._sock.recv(65536)
            if not chunk:
                raise QMPError("QMP connection closed unexpectedly")
            self._buf += chunk
        line, self._buf = self._buf.split(b"\n", 1)
        return json.loads(line)

    def execute(self, command: str, **arguments: object) -> object:
        assert self._sock is not None, "call connect() first"
        payload: dict[str, object] = {"execute": command}
        if arguments:
            payload["arguments"] = arguments
        self._sock.sendall(json.dumps(payload).encode() + b"\n")
        while True:
            message = self._read_json()
            if "return" in message:
                return message["return"]
            if "error" in message:
                raise QMPError(f"QMP {command} failed: {message['error']}")
            # else: an asynchronous event, keep reading.

    # -- pixels --

    def screendump(self, path: str | Path) -> Path:
        """Write the framebuffer to ``path`` (PNG when the name says so).

        ``screendump`` returns as soon as the request is queued, so the file
        can be missing or half-written when it comes back; wait for it to stop
        growing before handing it to a caller.
        """
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            target.unlink()
        arguments: dict[str, object] = {"filename": str(target)}
        if target.suffix.lower() == ".png":
            arguments["format"] = "png"
        self.execute("screendump", **arguments)

        previous = -1
        for _ in range(200):
            if target.exists():
                size = target.stat().st_size
                if size and size == previous:
                    return target
                previous = size
            time.sleep(0.05)
        if not target.exists() or not target.stat().st_size:
            raise QMPError(f"screendump produced nothing at {target}")
        return target

    # -- input --

    def _send(self, *events: dict) -> None:
        self.execute("input-send-event", events=list(events))

    def move_to(self, x: int, y: int, width: int, height: int) -> None:
        """Put the pointer at guest pixel ``(x, y)`` on a ``width x height`` screen."""
        self._send(
            {"type": "abs", "data": {"axis": "x", "value": _scale(x, width)}},
            {"type": "abs", "data": {"axis": "y", "value": _scale(y, height)}},
        )

    def button(self, down: bool, which: str = "left") -> None:
        self._send({"type": "btn", "data": {"down": down, "button": which}})

    def click(self, x: int, y: int, width: int, height: int, settle: float = 0.2) -> None:
        self.move_to(x, y, width, height)
        time.sleep(settle)
        self.button(True)
        time.sleep(0.08)
        self.button(False)

    def drag(
        self,
        points: list,
        width: int,
        height: int,
        step_delay: float = 0.04,
    ) -> None:
        """Press at the first point, move through the rest, release at the last."""
        if len(points) < 2:
            raise ValueError("a drag needs at least two points")
        first, rest = points[0], points[1:]
        self.move_to(first[0], first[1], width, height)
        time.sleep(0.25)
        self.button(True)
        for x, y in rest:
            self.move_to(x, y, width, height)
            time.sleep(step_delay)
        time.sleep(0.15)
        self.button(False)

    def key(self, *qcodes: str, hold: float = 0.05) -> None:
        """Press ``qcodes`` together (modifiers first) and release in reverse."""
        down = [{"type": "key", "data": {"down": True, "key": _qcode(code)}} for code in qcodes]
        up = [
            {"type": "key", "data": {"down": False, "key": _qcode(code)}}
            for code in reversed(qcodes)
        ]
        self._send(*down)
        time.sleep(hold)
        self._send(*up)


def _qcode(name: str) -> dict:
    return {"type": "qcode", "data": name}


def _scale(value: int, extent: int) -> int:
    """Guest pixel -> QEMU's absolute axis."""
    if extent <= 1:
        return 0
    return max(0, min(ABS_MAX, round(value * ABS_MAX / (extent - 1))))


# --------------------------------------------------------------------------- #
# A tiny command line, so `just vm-qmp-*` can poke a VM a human is watching.
# --------------------------------------------------------------------------- #


def main(argv: list | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Talk to a running QEMU over QMP.")
    parser.add_argument("--socket", default="output/e2e/qmp.sock", help="QMP unix socket")
    parser.add_argument("--width", type=int, default=1280, help="guest screen width")
    parser.add_argument("--height", type=int, default=800, help="guest screen height")
    sub = parser.add_subparsers(dest="action", required=True)

    shot = sub.add_parser("shot", help="screendump to a file")
    shot.add_argument("path", nargs="?", default="output/e2e/qmp-shot.png")

    click = sub.add_parser("click", help="click at guest pixel x y")
    click.add_argument("x", type=int)
    click.add_argument("y", type=int)

    move = sub.add_parser("move", help="move the pointer to guest pixel x y")
    move.add_argument("x", type=int)
    move.add_argument("y", type=int)

    key = sub.add_parser("key", help="press one or more qcodes together")
    key.add_argument("qcodes", nargs="+")

    run = sub.add_parser("run", help="execute a raw QMP command")
    run.add_argument("command")

    args = parser.parse_args(argv)
    with QMPClient(args.socket, timeout=10.0) as client:
        if args.action == "shot":
            print(client.screendump(args.path))
        elif args.action == "click":
            client.click(args.x, args.y, args.width, args.height)
        elif args.action == "move":
            client.move_to(args.x, args.y, args.width, args.height)
        elif args.action == "key":
            client.key(*args.qcodes)
        elif args.action == "run":
            print(json.dumps(client.execute(args.command), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
