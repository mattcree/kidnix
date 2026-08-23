"""Read a Qt ``.rcc`` resource bundle without Qt.

WHY THIS EXISTS
---------------
GCompris ships its recorded voices as Qt resource archives --
``/usr/share/gcompris-qt/rcc/data3/voices-ogg/voices-en_GB-*.rcc`` -- and the
files inside one are the only human recordings of English speech kidnix
already redistributes. ``docs/design/sounds-and-words.md`` §12.6 wants them on
disk. There is no supported way to get them out:

* ``rcc --reverse`` does not exist. Qt's ``rcc`` is a *compiler*; Qt 6 has no
  extraction mode at all, and never had one.
* ``QResource``/``QFile`` can read a registered bundle, but that means running
  a Qt program, and the build container has PyQt for nothing else.
* ``bsdtar``/``7z`` do not know the format.

So we parse it. The format is small, stable since Qt 5.0, and documented by
``qtbase/src/corelib/io/qresource.cpp`` (the reader) and
``qtbase/src/tools/rcc/rcc.cpp`` (the writer). Everything below is that
format, big-endian throughout.

    header      "qres", u32 version, u32 tree offset, u32 data offset,
                u32 name offset, and (version >= 3) u32 overall flags
    tree        a flat array of fixed-size nodes, index 0 is the root
    node        u32 name offset, u16 flags, then either
                  directory:  u32 child count, u32 first child index
                  file:       u16 country, u16 language, u32 data offset
                and (version >= 2) u64 last-modified, milliseconds
    names       u16 length in UTF-16 code units, u32 hash, then UTF-16BE
    data        u32 length, then that many bytes

``flags`` is a bitfield: 0x01 zlib-compressed, 0x02 directory, 0x04
zstd-compressed. A zlib payload is what ``qCompress`` produces -- four bytes of
big-endian *uncompressed* size, then a zlib stream -- so the four bytes are
skipped and used as a check.

Tested by ``build_files/lib/test_rcc.py``, which builds bundles with a writer
of its own and round-trips them, and which the image build runs before this
module is trusted with anything.
"""

from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass
from pathlib import Path

__all__ = ["RccBundle", "RccEntry", "RccError"]

MAGIC = b"qres"

FLAG_COMPRESSED = 0x01
FLAG_DIRECTORY = 0x02
FLAG_COMPRESSED_ZSTD = 0x04

#: Node size by format version. Version 2 added the 8-byte mtime.
_NODE_SIZE = {1: 14, 2: 22, 3: 22}

#: Refuse a bundle claiming to be enormous rather than trying to index it. The
#: biggest thing kidnix reads this way is GCompris' 13 MiB en_GB voice set.
MAX_BUNDLE_BYTES = 512 * 1024 * 1024


class RccError(Exception):
    """The bundle is not a bundle, or is one this reader does not understand."""


@dataclass(frozen=True)
class RccEntry:
    """One file inside a bundle."""

    #: Absolute resource path, e.g. ``/gcompris/data/voices-ogg/en_GB/a.ogg``.
    path: str
    #: Bytes as stored -- compressed if ``compression`` is not ``"none"``.
    stored_size: int
    #: ``"none"``, ``"zlib"`` or ``"zstd"``.
    compression: str

    @property
    def name(self) -> str:
        return self.path.rsplit("/", 1)[-1]


class RccBundle:
    """A parsed ``.rcc``. Reads the whole file; they are tens of megabytes."""

    def __init__(self, blob: bytes, *, origin: str = "<bytes>") -> None:
        self.origin = origin
        self._blob = blob
        if len(blob) < 20:
            raise RccError(f"{origin}: too short to be a Qt resource bundle ({len(blob)} bytes)")
        if blob[:4] != MAGIC:
            raise RccError(f"{origin}: magic is {blob[:4]!r}, expected {MAGIC!r}")
        version, tree, data, names = struct.unpack(">4I", blob[4:20])
        if version not in _NODE_SIZE:
            raise RccError(
                f"{origin}: format version {version} is not one this reader knows "
                f"({sorted(_NODE_SIZE)})"
            )
        for label, offset in (("tree", tree), ("data", data), ("name", names)):
            if offset >= len(blob):
                raise RccError(f"{origin}: {label} offset {offset} is past the end of the file")
        self.version = version
        self._tree = tree
        self._data = data
        self._names = names
        self._node_size = _NODE_SIZE[version]
        self._index: dict[str, tuple[int, int]] = {}  # path -> (flags, data offset)
        self._walk()

    # -- construction ------------------------------------------------------

    @classmethod
    def open(cls, path: str | Path) -> RccBundle:
        path = Path(path)
        size = path.stat().st_size
        if size > MAX_BUNDLE_BYTES:
            raise RccError(f"{path}: {size} bytes is larger than this reader will index")
        return cls(path.read_bytes(), origin=str(path))

    # -- the three sections ------------------------------------------------

    def _name_at(self, offset: int) -> str:
        base = self._names + offset
        if base + 6 > len(self._blob):
            raise RccError(f"{self.origin}: name offset {offset} runs off the end")
        (length,) = struct.unpack(">H", self._blob[base : base + 2])
        start = base + 6  # 2 bytes length + 4 bytes hash
        raw = self._blob[start : start + length * 2]
        if len(raw) != length * 2:
            raise RccError(f"{self.origin}: truncated name at offset {offset}")
        return raw.decode("utf-16-be")

    def _node(self, index: int) -> tuple[str, int, int, int]:
        """``(name, flags, a, b)``; for a directory ``a`` is the first child."""
        base = self._tree + index * self._node_size
        if base + 14 > len(self._blob):
            raise RccError(f"{self.origin}: node {index} runs off the end of the tree")
        name_offset, flags = struct.unpack(">IH", self._blob[base : base + 6])
        a, b = struct.unpack(">II", self._blob[base + 6 : base + 14])
        if flags & FLAG_DIRECTORY:
            child_count, first_child = a, b
            return self._name_at(name_offset), flags, first_child, child_count
        # a file: u16 country, u16 language, then u32 data offset
        return self._name_at(name_offset), flags, b, 0

    def _walk(self) -> None:
        """Depth-first from the root, recording every file's flags and offset.

        Iterative, and every node is visited at most once: a bundle whose tree
        pointed at itself would otherwise be an infinite loop inside a build.
        """
        total = max(0, (len(self._blob) - self._tree) // self._node_size)
        seen: set[int] = set()
        stack: list[tuple[int, str, int]] = [(0, "", 0)]
        while stack:
            index, prefix, depth = stack.pop()
            if index in seen or index >= total:
                continue
            seen.add(index)
            name, flags, a, count = self._node(index)
            # The root node's name field is not its name.
            path = prefix if depth == 0 else f"{prefix}/{name}"
            if flags & FLAG_DIRECTORY:
                for child in range(count):
                    stack.append((a + child, path, depth + 1))
            else:
                self._index[path] = (flags, a)

    # -- the public surface ------------------------------------------------

    def entries(self, prefix: str = "") -> list[RccEntry]:
        """Every file whose path starts with ``prefix``, sorted by path."""
        out = []
        for path in sorted(self._index):
            if prefix and not path.startswith(prefix):
                continue
            flags, offset = self._index[path]
            out.append(
                RccEntry(
                    path=path,
                    stored_size=self._stored_size(offset),
                    compression=_compression(flags),
                )
            )
        return out

    def __contains__(self, path: str) -> bool:
        return path in self._index

    def _stored_size(self, offset: int) -> int:
        base = self._data + offset
        (length,) = struct.unpack(">I", self._blob[base : base + 4])
        return length

    def read(self, path: str) -> bytes:
        """The decompressed contents of one file."""
        try:
            flags, offset = self._index[path]
        except KeyError:
            raise RccError(f"{self.origin}: no such resource {path!r}") from None
        base = self._data + offset
        if base + 4 > len(self._blob):
            raise RccError(f"{self.origin}: {path}: data offset {offset} is past the end")
        (length,) = struct.unpack(">I", self._blob[base : base + 4])
        payload = self._blob[base + 4 : base + 4 + length]
        if len(payload) != length:
            raise RccError(f"{self.origin}: {path}: truncated payload")
        if flags & FLAG_COMPRESSED:
            if length < 4:
                raise RccError(f"{self.origin}: {path}: compressed payload has no size header")
            (expected,) = struct.unpack(">I", payload[:4])
            out = zlib.decompress(payload[4:])
            if len(out) != expected:
                raise RccError(
                    f"{self.origin}: {path}: inflated to {len(out)} bytes, header said {expected}"
                )
            return out
        if flags & FLAG_COMPRESSED_ZSTD:
            try:
                from compression import zstd  # Python 3.14+
            except ImportError as exc:  # pragma: no cover - depends on the image's python
                raise RccError(
                    f"{self.origin}: {path} is zstd-compressed and this python has no zstd"
                ) from exc
            return zstd.decompress(payload)
        return payload

    def extract(self, prefix: str, dest: str | Path) -> list[Path]:
        """Write every file under ``prefix`` into ``dest``, flat, by basename.

        Flat because every caller so far wants one directory of clips, and a
        bundle that held two files with the same basename under one prefix is
        a bundle we do not understand -- so that is an error, not a silent
        overwrite.
        """
        dest = Path(dest)
        dest.mkdir(parents=True, exist_ok=True)
        written: list[Path] = []
        taken: set[str] = set()
        for entry in self.entries(prefix):
            if entry.name in taken:
                raise RccError(f"{self.origin}: two files named {entry.name!r} under {prefix!r}")
            taken.add(entry.name)
            target = dest / entry.name
            target.write_bytes(self.read(entry.path))
            written.append(target)
        return written


def _compression(flags: int) -> str:
    if flags & FLAG_COMPRESSED:
        return "zlib"
    if flags & FLAG_COMPRESSED_ZSTD:
        return "zstd"
    return "none"
