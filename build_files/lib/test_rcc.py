"""Tests for the Qt resource reader in ``rcc.py``.

Stdlib only, and runnable three ways -- ``python3 -m unittest``, ``pytest``, or
``python3 build_files/lib/test_rcc.py`` -- because the image build runs them
inside the container before it trusts the reader with GCompris' voice bundle,
and there is no pytest in the container.

Nothing here needs a fixture file. ``_write_rcc`` below is a **writer** for the
same format, so every test is a round-trip: if the reader and the writer agreed
on a wrong format the real bundle would fail, and ``test_real_bundle`` runs
against that real bundle whenever it happens to be on the machine.
"""

from __future__ import annotations

import struct
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from rcc import (
    FLAG_COMPRESSED,
    FLAG_DIRECTORY,
    RccBundle,
    RccError,
)

#: Where the image keeps GCompris' voice bundles. Absent on a developer's
#: laptop, present inside the build container and inside the built image.
GCOMPRIS_VOICES = Path("/usr/share/gcompris-qt/rcc/data3/voices-ogg")


def _write_rcc(
    tree: dict[str, bytes], *, version: int = 2, compress: set[str] | None = None
) -> bytes:
    """Build a ``.rcc`` from ``{"/a/b.ogg": b"..."}``. The mirror of the reader.

    Deliberately simple-minded: it lays the tree out breadth-first and does not
    sort children by hash the way Qt's ``rcc`` does, because the reader walks
    children by index and never binary-searches. That is exactly the property
    worth pinning -- a reader that depended on Qt's ordering would break on the
    first bundle produced by a different Qt version.
    """
    compress = compress or set()
    node_size = 14 if version < 2 else 22

    # --- names ---------------------------------------------------------------
    names = bytearray()
    name_offsets: dict[str, int] = {}

    def name_offset(text: str) -> int:
        if text not in name_offsets:
            name_offsets[text] = len(names)
            names.extend(struct.pack(">HI", len(text), 0))
            names.extend(text.encode("utf-16-be"))
        return name_offsets[text]

    # --- the directory tree --------------------------------------------------
    children: dict[str, list[str]] = {"": []}
    for path in sorted(tree):
        parts = path.strip("/").split("/")
        for depth in range(len(parts)):
            parent = "/" + "/".join(parts[:depth]) if depth else ""
            here = "/" + "/".join(parts[: depth + 1])
            children.setdefault(parent, [])
            children.setdefault(here, [])
            if here not in children[parent]:
                children[parent].append(here)

    order = [""]
    index_of: dict[str, int] = {"": 0}
    queue = [""]
    while queue:
        node = queue.pop(0)
        for child in children[node]:
            index_of[child] = len(order)
            order.append(child)
            queue.append(child)

    # --- data ----------------------------------------------------------------
    data = bytearray()
    data_offsets: dict[str, int] = {}
    flags_of: dict[str, int] = {}
    for path in sorted(tree):
        blob = tree[path]
        if path in compress:
            payload = struct.pack(">I", len(blob)) + zlib.compress(blob)
            flags_of[path] = FLAG_COMPRESSED
        else:
            payload = blob
            flags_of[path] = 0
        data_offsets[path] = len(data)
        data.extend(struct.pack(">I", len(payload)))
        data.extend(payload)

    # --- nodes ---------------------------------------------------------------
    nodes = bytearray()
    for path in order:
        name = path.rsplit("/", 1)[-1] if path else ""
        if path in tree:
            nodes.extend(struct.pack(">IH", name_offset(name), flags_of[path]))
            nodes.extend(struct.pack(">HHI", 0, 0, data_offsets[path]))
        else:
            kids = children[path]
            first = index_of[kids[0]] if kids else 0
            nodes.extend(struct.pack(">IH", name_offset(name), FLAG_DIRECTORY))
            nodes.extend(struct.pack(">II", len(kids), first))
        if version >= 2:
            nodes.extend(struct.pack(">Q", 0))
    assert len(nodes) == len(order) * node_size

    header_size = 20 + (4 if version >= 3 else 0)
    data_offset = header_size
    name_offset_abs = data_offset + len(data)
    tree_offset = name_offset_abs + len(names)
    out = bytearray(b"qres")
    out.extend(struct.pack(">4I", version, tree_offset, data_offset, name_offset_abs))
    if version >= 3:
        out.extend(struct.pack(">I", 0))
    out.extend(data)
    out.extend(names)
    out.extend(nodes)
    return bytes(out)


class RoundTrip(unittest.TestCase):
    def test_flat_bundle(self):
        blob = _write_rcc({"/x/a.ogg": b"aaa", "/x/b.ogg": b"bbbb"})
        bundle = RccBundle(blob)
        self.assertEqual([e.path for e in bundle.entries()], ["/x/a.ogg", "/x/b.ogg"])
        self.assertEqual(bundle.read("/x/a.ogg"), b"aaa")
        self.assertEqual(bundle.read("/x/b.ogg"), b"bbbb")

    def test_nested_directories(self):
        tree = {
            "/gcompris/data/voices-ogg/en_GB/alphabet/a.ogg": b"A" * 40,
            "/gcompris/data/voices-ogg/en_GB/alphabet/b.ogg": b"B" * 41,
            "/gcompris/data/voices-ogg/en_GB/misc/good.ogg": b"G" * 42,
        }
        bundle = RccBundle(_write_rcc(tree))
        alphabet = bundle.entries("/gcompris/data/voices-ogg/en_GB/alphabet/")
        self.assertEqual([e.name for e in alphabet], ["a.ogg", "b.ogg"])
        self.assertEqual(len(bundle.entries()), 3)
        for path, blob in tree.items():
            self.assertEqual(bundle.read(path), blob)

    def test_compressed_payload(self):
        body = b"ogg-ish but compressible " * 200
        blob = _write_rcc({"/x/big.bin": body}, compress={"/x/big.bin"})
        bundle = RccBundle(blob)
        (entry,) = bundle.entries()
        self.assertEqual(entry.compression, "zlib")
        self.assertLess(entry.stored_size, len(body))
        self.assertEqual(bundle.read("/x/big.bin"), body)

    def test_every_format_version(self):
        for version in (1, 2, 3):
            with self.subTest(version=version):
                bundle = RccBundle(_write_rcc({"/x/a.ogg": b"hello"}, version=version))
                self.assertEqual(bundle.version, version)
                self.assertEqual(bundle.read("/x/a.ogg"), b"hello")

    def test_unicode_names_survive_the_utf16_name_table(self):
        # GCompris names its letter clips U0061.ogg, but other bundles do not
        # keep to ASCII, and the name table is UTF-16BE.
        bundle = RccBundle(_write_rcc({"/x/été.ogg": b"z"}))
        self.assertEqual([e.name for e in bundle.entries()], ["été.ogg"])

    def test_extract_writes_files_by_basename(self):
        tree = {"/x/y/a.ogg": b"1", "/x/y/b.ogg": b"22", "/x/z/c.ogg": b"333"}
        bundle = RccBundle(_write_rcc(tree))
        with tempfile.TemporaryDirectory() as tmp:
            written = bundle.extract("/x/y/", tmp)
            self.assertEqual(sorted(p.name for p in written), ["a.ogg", "b.ogg"])
            self.assertEqual((Path(tmp) / "b.ogg").read_bytes(), b"22")
            self.assertFalse((Path(tmp) / "c.ogg").exists())

    def test_membership(self):
        bundle = RccBundle(_write_rcc({"/x/a.ogg": b"1"}))
        self.assertIn("/x/a.ogg", bundle)
        self.assertNotIn("/x/nope.ogg", bundle)


class Rejections(unittest.TestCase):
    def test_bad_magic(self):
        with self.assertRaises(RccError):
            RccBundle(b"NOTQ" + bytes(64))

    def test_too_short(self):
        with self.assertRaises(RccError):
            RccBundle(b"qres")

    def test_unknown_version(self):
        blob = bytearray(_write_rcc({"/x/a.ogg": b"1"}))
        blob[4:8] = struct.pack(">I", 99)
        with self.assertRaises(RccError) as caught:
            RccBundle(bytes(blob))
        self.assertIn("99", str(caught.exception))

    def test_offset_past_the_end(self):
        blob = bytearray(_write_rcc({"/x/a.ogg": b"1"}))
        blob[8:12] = struct.pack(">I", 1 << 30)  # tree offset
        with self.assertRaises(RccError):
            RccBundle(bytes(blob))

    def test_missing_resource(self):
        bundle = RccBundle(_write_rcc({"/x/a.ogg": b"1"}))
        with self.assertRaises(RccError):
            bundle.read("/x/missing.ogg")

    def test_a_tree_that_points_at_itself_terminates(self):
        # A malformed bundle must fail or come back empty-handed, never spin.
        blob = bytearray(_write_rcc({"/x/a.ogg": b"1"}))
        _version, tree, _data, _names = struct.unpack(">4I", blob[4:20])
        # Make the root's first child be the root.
        blob[tree + 10 : tree + 14] = struct.pack(">I", 0)
        bundle = RccBundle(bytes(blob))
        self.assertEqual(bundle.entries(), [])


class RealBundle(unittest.TestCase):
    """Against the file the build actually reads, when it is there."""

    def setUp(self):
        if not GCOMPRIS_VOICES.is_dir():
            self.skipTest(f"{GCOMPRIS_VOICES} is not on this machine")
        bundles = sorted(GCOMPRIS_VOICES.glob("voices-en_GB-*.rcc"))
        if not bundles:
            self.skipTest("no en_GB voice bundle")
        self.bundle = RccBundle.open(bundles[0])

    def test_the_alphabet_clips_are_all_there_and_are_ogg(self):
        prefix = "/gcompris/data/voices-ogg/en_GB/alphabet/"
        names = {e.name for e in self.bundle.entries(prefix)}
        for code in range(0x61, 0x7B):
            self.assertIn(f"U{code:04X}.ogg", names)
        blob = self.bundle.read(prefix + "U0061.ogg")
        self.assertEqual(blob[:4], b"OggS")
        self.assertGreater(len(blob), 2000)

    def test_every_entry_reads_back_at_its_stored_size(self):
        for entry in self.bundle.entries("/gcompris/data/voices-ogg/en_GB/alphabet/"):
            blob = self.bundle.read(entry.path)
            if entry.compression == "none":
                self.assertEqual(len(blob), entry.stored_size, entry.path)
            self.assertEqual(blob[:4], b"OggS", entry.path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
