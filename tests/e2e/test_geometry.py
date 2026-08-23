"""Unit tests for the pixel helpers. No VM, no disk image, no KVM.

The scenario test's hardest-working part is :mod:`pixels` -- if it mislocates a
tile the whole run clicks the wrong thing and blames the shell. These build
synthetic screenshots with the same structure theme.css gives real ones (paper
surface, thin top border, thick bottom border) and check the helpers find them.

They cost milliseconds, so CI can run them on every push even when there is no
disk image to boot.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pixels import (
    Image,
    band_buttons,
    boxes_in_band,
    centre,
    content_top,
    dark_centroid,
    dark_fraction,
    differs,
    find_grid,
    mean_colour,
    read_ppm,
)

PAPER = (251, 247, 239)
EDGE = (200, 197, 190)
BAND = (15, 138, 138)


class Canvas:
    """A tiny mutable RGB buffer that can be frozen into an :class:`Image`."""

    def __init__(self, width: int, height: int, fill: tuple = PAPER) -> None:
        self.width = width
        self.height = height
        self.data = bytearray(bytes(fill) * width * height)

    def rect(self, left: int, top: int, right: int, bottom: int, colour: tuple) -> None:
        for y in range(max(0, top), min(self.height, bottom + 1)):
            row = 3 * y * self.width
            for x in range(max(0, left), min(self.width, right + 1)):
                self.data[row + 3 * x : row + 3 * x + 3] = bytes(colour)

    def box(self, left: int, top: int, right: int, bottom: int) -> None:
        """A control, drawn the way theme.css draws one: light top, heavy foot."""
        self.rect(left, top, right, top + 1, EDGE)  # 2 px top border
        self.rect(left, bottom - 9, right, bottom, EDGE)  # 6 px border + shadow
        self.rect(left, top, left + 1, bottom, EDGE)
        self.rect(right - 1, top, right, bottom, EDGE)

    def image(self) -> Image:
        return Image(self.width, self.height, bytes(self.data))


def home_like() -> tuple:
    """A 4x3 grid of unevenly wide tiles under an 85 px band, as Home renders."""
    canvas = Canvas(1280, 800)
    canvas.rect(0, 0, 1279, 84, BAND)
    columns = ((136, 347), (390, 667), (710, 897), (940, 1143))
    rows = ((181, 345), (382, 546), (583, 747))
    expected = []
    for row_index, (top, bottom) in enumerate(rows):
        cells = columns if row_index < 2 else columns[:3]
        for left, right in cells:
            canvas.box(left, top, right, bottom)
        expected.append([(left, top, right, bottom) for left, right in cells])
    return canvas.image(), expected


def test_content_top_finds_the_bottom_of_the_band():
    image, _ = home_like()
    assert content_top(image) == 85


def test_find_grid_recovers_a_home_grid():
    image, expected = home_like()
    grid = find_grid(image)
    assert [len(row) for row in grid] == [4, 4, 3]
    for found_row, expected_row in zip(grid, expected):
        for found, wanted in zip(found_row, expected_row):
            # Borders are two pixels wide, so allow a couple either way.
            assert all(abs(a - b) <= 3 for a, b in zip(found, wanted)), (found, wanted)


def test_find_grid_finds_a_single_card():
    """One Journal card covers 21% of the width; the ladder has to reach it."""
    canvas = Canvas(1280, 800)
    canvas.rect(0, 0, 1279, 84, BAND)
    canvas.box(502, 200, 777, 378)
    grid = find_grid(canvas.image())
    assert len(grid) == 1 and len(grid[0]) == 1, grid
    assert centre(grid[0][0]) == pytest.approx((639, 289), abs=4)


def test_uneven_columns_are_not_assumed_even():
    """The reason this module exists: Gtk.Grid columns are not homogeneous."""
    image, _ = home_like()
    row = boxes_in_band(image, (181, 345))
    widths = [right - left for left, right in row]
    assert widths == [209, 275, 185, 201], widths
    assert len(set(widths)) > 1, "a uniform grid would not have caught the real bug"


def test_band_buttons_are_paper_on_colour():
    canvas = Canvas(1280, 800)
    canvas.rect(0, 0, 1279, 84, BAND)
    for left in (22, 127, 232, 1108):
        canvas.rect(left, 10, left + 52, 74, PAPER)
    found = band_buttons(canvas.image(), 85)
    assert [box[0] for box in found] == [22, 127, 232, 1108], found


def test_dark_centroid_finds_the_one_big_shape():
    canvas = Canvas(1280, 800)
    canvas.rect(560, 340, 720, 500, (26, 26, 26))
    blob = dark_centroid(canvas.image(), (300, 250, 980, 740))
    assert blob is not None
    x, y, count, _box = blob
    assert (x, y) == pytest.approx((639, 419), abs=6)
    assert count > 400


def test_dark_centroid_ignores_a_speck():
    canvas = Canvas(1280, 800)
    canvas.rect(600, 400, 604, 404, (0, 0, 0))
    assert dark_centroid(canvas.image(), (300, 250, 980, 740)) is None


def test_mean_and_dark_fraction():
    canvas = Canvas(100, 100)
    assert mean_colour(canvas.image()) == pytest.approx(PAPER, abs=1)
    assert dark_fraction(canvas.image()) == 0.0
    canvas.rect(0, 0, 99, 49, (0, 0, 0))
    assert dark_fraction(canvas.image()) == pytest.approx(0.5, abs=0.02)


def test_differs_measures_only_the_box_asked_about():
    before = Canvas(200, 200)
    after = Canvas(200, 200)
    after.rect(0, 0, 99, 199, (0, 0, 0))
    assert differs(before.image(), after.image(), (0, 0, 100, 200)) == pytest.approx(1.0, abs=0.02)
    assert differs(before.image(), after.image(), (100, 0, 200, 200)) == 0.0


def test_read_ppm_round_trips(tmp_path):
    canvas = Canvas(4, 3, (1, 2, 3))
    canvas.rect(1, 1, 2, 1, (250, 251, 252))
    raw = b"P6\n# a comment\n4 3\n255\n" + bytes(canvas.data)
    path = tmp_path / "frame.ppm"
    path.write_bytes(raw)
    image = read_ppm(path)
    assert (image.width, image.height) == (4, 3)
    assert image.pixel(0, 0) == (1, 2, 3)
    assert image.pixel(1, 1) == (250, 251, 252)


def test_read_ppm_rejects_a_png(tmp_path):
    path = tmp_path / "frame.png"
    path.write_bytes(b"\x89PNG\r\n\x1a\n")
    with pytest.raises(ValueError):
        read_ppm(path)


def test_the_gap_between_two_buttons_is_not_a_button():
    """83 px of paper between two ritual buttons used to read as a third."""
    canvas = Canvas(1280, 800)
    canvas.rect(0, 0, 1279, 84, BAND)
    canvas.box(135, 455, 540, 590)
    canvas.box(623, 455, 1143, 590)
    grid = find_grid(canvas.image())
    assert len(grid) == 1, grid
    assert [centre(box)[0] for box in grid[0]] == [337, 883], grid[0]


# --- the unpainted first frame ------------------------------------------
#
# `screendump` answers as soon as the request is queued, so a dump taken just
# after a state change can catch the framebuffer before the guest has painted
# into it. The first screenshot of a run came back fully black exactly this
# way, and it is the contact sheet -- the artefact the harness exists to
# produce -- that carried the hole.


def _ppm(path, width, height, colour):
    """Write a solid-colour P6, the way QEMU would."""
    body = bytes(colour) * (width * height)
    path.write_bytes(b"P6\n%d %d\n255\n" % (width, height) + body)
    return path


def test_an_unpainted_frame_is_told_apart_from_a_dim_screen():
    """The bedtime screen is the dimmest thing kidnix draws, and it is a
    colour. Only a framebuffer nobody has written to is uniformly 0,0,0."""
    from pixels import near_uniform_black

    assert near_uniform_black(Canvas(64, 48, (0, 0, 0)).image())

    sleeping = Canvas(64, 48, (26, 28, 44))  # theme.css `.sleeping`
    assert not near_uniform_black(sleeping.image())

    # A black screen with the band still on it is not "unpainted" either.
    banded = Canvas(64, 48, (0, 0, 0))
    banded.rect(0, 0, 63, 5, BAND)
    assert not near_uniform_black(banded.image())


def test_shot_asks_again_while_the_frame_is_black(tmp_path, monkeypatch, capsys):
    """Two black frames, then a painted one: the shot returned is the painted
    one, and the log says how many attempts it cost."""
    import conftest

    monkeypatch.setattr(conftest, "BLACK_FRAME_DELAY", 0.0)
    frames = [(0, 0, 0), (0, 0, 0), PAPER]

    class FakeQMP:
        # Both dumps go through the QMP client now -- the PNG a human looks at
        # and the PPM the assertions read -- and both land in *the story's*
        # directory rather than the VM's, so a second story (test_flows.py) can
        # keep its artefacts apart. The PNG is the one an attempt is counted by.
        def screendump(self, path):
            path = Path(path)
            if path.suffix == ".png":
                calls.append(path.name)
            return _ppm(path, 8, 8, frames[min(len(calls) - 1, len(frames) - 1)])

    calls = []

    class FakeVM:
        qmp = FakeQMP()

    story = conftest.Scenario(FakeVM(), tmp_path)
    image = story.shot("boots", "the first frame")

    assert len(calls) == 3  # one attempt plus two retries
    assert image.pixel(0, 0) == PAPER
    assert "2 retries" in capsys.readouterr().out


def test_shot_gives_up_after_the_agreed_number_of_tries(tmp_path, monkeypatch, capsys):
    """A screen that really is black must still produce a shot -- and say so,
    so it reads as a finding rather than as a mystery."""
    import conftest

    monkeypatch.setattr(conftest, "BLACK_FRAME_DELAY", 0.0)
    calls = []

    class FakeQMP:
        def screendump(self, path):
            path = Path(path)
            if path.suffix == ".png":
                calls.append(path.name)
            return _ppm(path, 8, 8, (0, 0, 0))

    class FakeVM:
        qmp = FakeQMP()

    story = conftest.Scenario(FakeVM(), tmp_path)
    image = story.shot("dark")

    assert len(calls) == conftest.BLACK_FRAME_RETRIES + 1
    assert image.pixel(0, 0) == (0, 0, 0)
    assert "still black" in capsys.readouterr().out
