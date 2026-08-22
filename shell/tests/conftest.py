"""Shared fixtures. Everything here is headless: no display is required."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import pytest

from kidnix_shell.activities import Activity
from kidnix_shell.journal import Journal
from kidnix_shell.session import DailyUsage, Session, SessionPolicy
from kidnix_shell.settings import Paths

#: A fixed clock. Midday on a Tuesday, comfortably outside bedtime.
NOW = datetime(2026, 8, 18, 12, 0, 0)


@pytest.fixture
def paths(tmp_path: Path) -> Paths:
    home = tmp_path / "home"
    home.mkdir()
    return Paths(
        home=home,
        data_home=home / ".local" / "share",
        config_home=home / ".config",
        cache_home=home / ".cache",
        state_home=home / ".local" / "state",
    )


@pytest.fixture
def journal(paths: Paths) -> Journal:
    journal = Journal(paths.journal_root)
    journal.load()
    return journal


@pytest.fixture
def policy() -> SessionPolicy:
    return SessionPolicy.from_minutes()


@pytest.fixture
def session(policy: SessionPolicy) -> Session:
    return Session(policy=policy, usage=DailyUsage(day=date(2026, 8, 18)))


def make_activity(
    activity_id: str = "scribble",
    watch: list[Path] | None = None,
    **kwargs: object,
) -> Activity:
    """A minimal valid Activity for tests that do not care about manifests."""
    defaults: dict[str, object] = {
        "id": activity_id,
        "name": activity_id.capitalize(),
        "exec_argv": ("/bin/true",),
        "source_path": Path(f"/nowhere/{activity_id}.toml"),
        "audio_label": f"{activity_id}. Do the thing.",
        "journal_watch": tuple(watch or ()),
        "journal_glob": "*.png",
    }
    defaults.update(kwargs)
    return Activity(**defaults)  # type: ignore[arg-type]


def write_png(path: Path, colour: tuple[int, int, int] = (255, 0, 0), size: int = 8) -> Path:
    """A real, tiny PNG -- written by hand so tests need no image library."""
    import struct
    import zlib

    raw = b""
    for _ in range(size):
        raw += b"\x00" + bytes(colour) * size

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    header = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)
    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png)
    return path
