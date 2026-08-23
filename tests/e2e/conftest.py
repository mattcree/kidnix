"""Fixtures for the end-to-end scenario.

One VM for the whole module: booting the disk takes 20 s and the scenario is a
*story*, not a set of independent facts. The steps therefore run in file order
and share one machine, exactly as a child sitting down at it would.
"""

from __future__ import annotations

import datetime
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

REPO = HERE.parent.parent

from pixels import Image, near_uniform_black, read_ppm  # noqa: E402
from vm import GuestVM, require_tools  # noqa: E402

OUTPUT = REPO / "output" / "e2e"
CONTACT_SHEET = OUTPUT / "contact-sheet.png"
DOCS_COPY = REPO / "docs" / "design" / "screenshots" / "e2e-contact-sheet.png"

#: How many times :meth:`Scenario.shot` will ask again for a frame that came
#: back unpainted, and how long it waits between asks. Two and a half seconds
#: in the worst case, spent only on a frame that is already black.
BLACK_FRAME_RETRIES = 5
BLACK_FRAME_DELAY = 0.5


def session_policy(
    length: float = 25,
    ending_offer: float = 6,
    put_away: float = 2,
    budget: float = 600,
    min_session: float = 5,
) -> str:
    """A ``session.toml`` with the bedtime window moved out of the way.

    ``bedtime_start``/``bedtime_end`` default to 19:00-07:00, so a test run in
    the evening would be refused a session and the whole scenario would fail
    for a reason that has nothing to do with the code under test. The window is
    pinned to one minute, six hours from now, wherever "now" is.
    """
    far = (datetime.datetime.now() + datetime.timedelta(hours=6)).replace(second=0, microsecond=0)
    return (
        f"length_minutes = {length}\n"
        f"daily_budget_minutes = {budget}\n"
        f"ending_offer_minutes = {ending_offer}\n"
        f"put_away_minutes = {put_away}\n"
        f"min_session_minutes = {min_session}\n"
        f'bedtime_start = "{far:%H:%M}"\n'
        f'bedtime_end = "{(far + datetime.timedelta(minutes=1)):%H:%M}"\n'
    )


class Scenario:
    """The VM plus the bookkeeping every step shares."""

    def __init__(self, vm: GuestVM, output_dir: Path) -> None:
        self.vm = vm
        self.output_dir = output_dir
        self.shots: list = []
        self._step = 0
        #: Filled in by the steps as they discover the layout.
        self.grid: list = []

    # -- artefacts --

    def shot(self, name: str, caption: str = "") -> Image:
        """Screenshot to ``output/e2e/NN-name.png``; return it as pixels.

        Two dumps, not one: the PNG is the artefact a human looks at and the
        PPM is what the assertions read, because a P6 needs no image library.

        **Retried while the frame comes back black.** ``screendump`` returns as
        soon as the request is queued, so a dump taken moments after a state
        change can catch the framebuffer before the guest has painted into it:
        the first screenshot of a run was once fully black, and the contact
        sheet -- the artefact this whole harness exists to produce -- opened on
        a blank tile that no assertion could see. Asking again is the fix,
        because the condition clears in milliseconds; the retry count is
        printed so a *real* black screen shows up as five wasted attempts in
        the log rather than as a mystery.
        """
        self._step += 1
        stem = f"{self._step:02d}-{name}"
        retries = 0
        while True:
            png = self.vm.screenshot(f"{stem}.png")
            image = read_ppm(self.vm.qmp.screendump(self.output_dir / f"{stem}.ppm"))
            if not near_uniform_black(image) or retries >= BLACK_FRAME_RETRIES:
                break
            retries += 1
            time.sleep(BLACK_FRAME_DELAY)
        self.shots.append((png, caption or name))
        note = ""
        if retries:
            painted = "still black" if near_uniform_black(image) else "painted"
            note = f" [unpainted frame: {retries} retr{'y' if retries == 1 else 'ies'}, {painted}]"
        print(f"  shot {png.name}: {caption or name}{note}")
        return image

    def wait_until(self, predicate, timeout: float = 30.0, what: str = "the screen"):
        """Poll the framebuffer until ``predicate(image)`` is true.

        The shell logs that it has laid out well before gnome-kiosk has mapped
        and painted its window, so "the service is active" is not "there is
        something to click". Watching the pixels is the only honest wait.
        """
        scratch = self.output_dir / "waiting.ppm"
        deadline = time.monotonic() + timeout
        image = None
        while True:
            image = read_ppm(self.vm.qmp.screendump(scratch))
            result = predicate(image)
            if result:
                return result
            if time.monotonic() >= deadline:
                raise AssertionError(f"{what} never appeared within {timeout:.0f}s")
            time.sleep(1.0)

    # -- convenience --

    def journal(self, since: str = "") -> str:
        return self.vm.shell_journal(since)

    def expect_log(self, needle: str, timeout: float = 25.0, since: str = "") -> str:
        line = self.vm.wait_for_shell_log(needle, timeout=timeout, since_cursor=since)
        print(f"  log  {line}")
        return line


@pytest.fixture(scope="session")
def scenario():
    qcow2 = REPO / "output" / "qcow2" / "disk.qcow2"
    if not qcow2.is_file():
        pytest.skip(f"no disk image at {qcow2} -- run `just build-qcow2-rootless`")
    require_tools()

    OUTPUT.mkdir(parents=True, exist_ok=True)
    for stale in OUTPUT.glob("*.ppm"):
        stale.unlink()
    for stale in OUTPUT.glob("*.png"):
        stale.unlink()

    vm = GuestVM(qcow2=qcow2, output_dir=OUTPUT, session_toml=session_policy())
    vm.start()
    vm.wait_for_ssh()
    story = Scenario(vm, OUTPUT)
    try:
        yield story
    finally:
        _contact_sheet(story)
        vm.stop()


def _contact_sheet(story: Scenario) -> None:
    """Tile every step's screenshot into one image, for the spike doc."""
    paths = [str(png) for png, _ in story.shots if Path(png).exists()]
    if not paths:
        return
    made = _sheet_with_pil(paths) or _sheet_with_magick(paths)
    if not made:
        print("contact sheet: no PIL and no ImageMagick; skipped")
        return
    DOCS_COPY.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(CONTACT_SHEET, DOCS_COPY)
    print(f"contact sheet: {CONTACT_SHEET} (copied to {DOCS_COPY})")


def _sheet_with_pil(paths: list) -> bool:
    try:
        from PIL import Image as PILImage
    except ImportError:
        return False
    thumbs = []
    for path in paths:
        image = PILImage.open(path).convert("RGB")
        image.thumbnail((420, 420))
        thumbs.append(image)
    columns = 3
    rows = (len(thumbs) + columns - 1) // columns
    pad = 10
    cell_w = max(t.width for t in thumbs) + pad
    cell_h = max(t.height for t in thumbs) + pad
    sheet = PILImage.new("RGB", (columns * cell_w + pad, rows * cell_h + pad), (24, 26, 32))
    for index, thumb in enumerate(thumbs):
        x = pad + (index % columns) * cell_w
        y = pad + (index // columns) * cell_h
        sheet.paste(thumb, (x, y))
    sheet.save(CONTACT_SHEET)
    return True


def _sheet_with_magick(paths: list) -> bool:
    for command in (["magick", "montage"], ["montage"]):
        if shutil.which(command[0]) is None:
            continue
        argv = [
            *command,
            "-background",
            "#181a20",
            "-geometry",
            "420x420+5+5",
            "-tile",
            "3x",
            *paths,
            str(CONTACT_SHEET),
        ]
        if subprocess.run(argv, capture_output=True, check=False).returncode == 0:
            return True
    return False
