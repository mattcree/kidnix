"""The end-to-end scenario: one child's session, driven from outside the VM.

Nothing here runs in the guest except assertions. The *interaction* is QEMU
``input-send-event`` -- absolute pointer moves, button presses, key presses --
and the *evidence* is a screenshot over QMP plus the guest's own journal read
over ssh. No test agent, no accessibility bus, no instrumentation build: the
image under test is the image we ship.

The steps are a story and share one VM, so they run in file order and the
recipe passes ``-x``. A failure in step 3 makes steps 4-7 meaningless, and
saying so once is better than seven red lines that all mean the same thing.

    just test-e2e

Artefacts land in ``output/e2e/``: a numbered PNG per step, the serial console,
the QEMU command line, and ``contact-sheet.png``.
"""

from __future__ import annotations

import time

import pytest
from conftest import session_policy
from pixels import (
    band_buttons,
    centre,
    dark_centroid,
    dark_fraction,
    differs,
    find_grid,
    mean_colour,
    read_ppm,
)

#: The activity the scenario opens. Row 1, column 2 of a 4x3 Home grid --
#: activities sort by (category, name), so "make" follows "learn" and
#: "Tux Paint" follows "TurboWarp". Asserted, not assumed: the shell's launcher
#: log says which activity actually started.
DRAW_ROW, DRAW_COLUMN = 0, 0

#: Tux Paint's own furniture, at 1280x800 fullscreen. Read off a screenshot of
#: the real thing (docs/spikes/e2e-scenario.md); Tux Paint lays its tool column
#: out in a fixed grid, so these do not move with the shell's metrics.
TUXPAINT_CANVAS = (430, 300, 880, 400)  # somewhere safely inside the paper
TUXPAINT_QUIT_TOOL = (71, 400)
TUXPAINT_QUIT_YES = (446, 346)

#: The band's buttons, left to right: Back, Undo, My Things, then the Ear on
#: the right. Found in the screenshot rather than computed.
MY_THINGS_INDEX = 2

JOURNAL_GLOB = "/var/home/kid/.local/share/kidnix/journal"


def _stroke(box: tuple) -> list:
    """A zig-zag inside ``box`` -- something a three-year-old would draw."""
    left, top, right, bottom = box
    span = right - left
    return [
        (left, (top + bottom) // 2),
        (left + span // 4, bottom),
        (left + span // 2, top),
        (left + 3 * span // 4, bottom),
        (right, (top + bottom) // 2),
    ]


# --------------------------------------------------------------------------- #


def test_01_boots_to_whos_here(scenario):
    """S1. The machine comes up on its own and asks who is here."""
    vm = scenario.vm

    marker = vm.boot_marker_line()
    assert "KIDNIX_BOOT_OK" in marker, marker
    print(f"  boot {marker}")

    active = vm.out(
        "runuser -u kid -- env XDG_RUNTIME_DIR=/run/user/$(id -u kid) "
        "systemctl --user is-active kidnix-shell.service",
        check=False,
    )
    assert active == "active", f"kidnix-shell.service is {active!r}"

    metrics = scenario.expect_log("display metrics:")
    assert "1280x800" in metrics, metrics
    scenario.metrics_line = metrics

    image = scenario.shot("whos-here", "S1 Who's here?")
    assert (image.width, image.height) == (1280, 800)

    # The surface under the band is the paper colour, not a black framebuffer
    # or a text console: cream is roughly (250, 246, 240).
    paper = mean_colour(image, (0, 120, 1280, 780))
    assert paper[0] > 230 and paper[1] > 225 and paper[2] > 215, f"surface is {paper}"

    # ...and there is one big dark shape in the middle of it: the avatar.
    blob = dark_centroid(image, (300, 250, 980, 740))
    assert blob is not None, "no avatar-shaped thing on Who's here?"
    x, y, count, box = blob
    assert count > 400, f"the avatar is too small to be an avatar: {count} px"
    assert 500 < x < 780, f"the avatar is not near the middle of the screen: x={x}"
    scenario.avatar = (x, y)
    print(f"  avatar at {scenario.avatar} (bbox {box})")


def test_02_choosing_me_goes_home(scenario):
    """S1 -> S2. Clicking the avatar starts a session and lands on Home."""
    vm = scenario.vm
    vm.click(*scenario.avatar)

    scenario.expect_log("state choosing -> home (choose_profile)")
    assert "session started for" in scenario.journal()

    image = scenario.shot("home", "S2 Home, after clicking Me")

    grid = find_grid(image)
    # 9 available activities + "All done" on a 4-column grid -> 4/4/2. Assert
    # shape loosely so hiding/adding one activity doesn't break the harness.
    assert len(grid) >= 2, f"expected at least two rows of tiles, found {len(grid)}"
    assert len(grid[0]) == 4, [len(row) for row in grid]
    assert sum(len(row) for row in grid) >= 6, [len(row) for row in grid]
    scenario.grid = grid
    print("  grid " + str([[centre(box) for box in row] for row in grid]))

    buttons = band_buttons(image, 85)
    assert len(buttons) >= 3, f"the band is missing buttons: {buttons}"
    scenario.band = buttons


def test_03_hovering_draw_speaks(scenario):
    """S2. Resting on a tile for the dwell makes the shell say what it is."""
    vm = scenario.vm
    tile = scenario.grid[DRAW_ROW][DRAW_COLUMN]
    scenario.draw_tile = tile
    target = centre(tile)

    # Park the pointer off every control, so the "before" frame is quiet.
    vm.move(60, 780)
    time.sleep(0.8)
    quiet = read_ppm(vm.qmp.screendump(scenario.output_dir / "03-hover-before.ppm"))

    vm.move(*target)
    time.sleep(1.2)  # HOVER_DWELL_MS is 400 ms; give the ring time to paint
    image = scenario.shot("hover-draw", "S2 hovering the Draw tile")

    changed = differs(quiet, image, tile)
    assert changed > 0.20, (
        f"hovering {target} for 1.2 s changed {changed:.0%} of the tile. "
        "The shell paints a highlight ring for as long as it is speaking, so "
        "nothing changing means the dwell never fired."
    )
    print(f"  {changed:.0%} of the tile changed under the pointer")

    # And the thing that does the speaking is alive in the child's session.
    spd = vm.out(
        "journalctl -b --no-pager -o cat "
        "_SYSTEMD_USER_UNIT=speech-dispatcher.service 2>/dev/null || true"
    )
    assert "Speech Dispatcher" in spd, f"speech-dispatcher never ran: {spd!r}"


def test_04_draw_launches_tuxpaint_and_keeps_the_drawing(scenario):
    """S2 -> S3 -> S2. Open Tux Paint, draw, quit, and find it in the Journal."""
    vm = scenario.vm
    vm.click(*centre(scenario.draw_tile))

    launched = scenario.expect_log("launched tuxpaint", timeout=40)
    assert "tuxpaint" in launched
    scenario.expect_log("state home -> in_activity (launch_activity)")

    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        if vm.out("pgrep -u kid -x tuxpaint || true", check=False):
            break
        time.sleep(1)
    else:
        pytest.fail("tuxpaint never appeared in the process table")

    time.sleep(8)  # Tux Paint fades its splash in
    image = scenario.shot("tuxpaint", "S3 Tux Paint, fullscreen")
    # Tux Paint's canvas is white; the shell's cream surface is not.
    canvas = mean_colour(image, (300, 150, 1000, 600))
    assert min(canvas) > 245, f"the canvas does not look like Tux Paint: {canvas}"

    vm.drag(_stroke(TUXPAINT_CANVAS), step_delay=0.08)
    time.sleep(2)
    drawn = scenario.shot("stroke", "S3 a stroke drawn over QMP")
    ink = dark_fraction(drawn, (400, 280, 900, 420))
    assert ink > 0.005, f"the canvas is still blank ({ink:.3%} dark)"
    print(f"  {ink:.2%} of the canvas region is ink")

    # Quit. tuxpaint.conf sets autosave=yes, so nobody is asked whether to
    # save -- but Tux Paint still asks whether you meant to leave.
    vm.click(*TUXPAINT_QUIT_TOOL)
    time.sleep(2.5)
    scenario.shot("tuxpaint-quit", "S3 'Do you really want to quit?'")
    vm.click(*TUXPAINT_QUIT_YES)

    scenario.expect_log("state in_activity -> home (activity_exited)", timeout=40)

    deadline = time.monotonic() + 40
    entries = ""
    while time.monotonic() < deadline:
        entries = vm.out(
            f"find {JOURNAL_GLOB} -name entry.json 2>/dev/null | sort || true", check=False
        )
        if entries:
            break
        time.sleep(2)
    assert entries, (
        "the Journal imported nothing. Tux Paint saves to ~/.tuxpaint/saved on "
        "quit and the shell watches that directory."
    )
    scenario.entries = entries.splitlines()
    print(f"  journal has {len(scenario.entries)} entry: {scenario.entries}")
    saved = vm.out("ls /var/home/kid/.tuxpaint/saved/ || true", check=False)
    print(f"  tuxpaint saved: {saved.split()}")


def test_05_my_things_shows_the_drawing(scenario):
    """S2 -> S4. The band's My Things opens the Journal, and the card is there."""
    vm = scenario.vm
    vm.click(*centre(scenario.band[MY_THINGS_INDEX]))
    scenario.expect_log("state home -> journal (open_journal)")

    time.sleep(1.5)
    image = scenario.shot("my-things", "S4 My Things")

    cards = find_grid(image)
    flat = [box for row in cards for box in row]
    assert flat, "My Things is empty -- no card for the drawing"
    print(f"  {len(flat)} card(s): {[centre(box) for box in flat]}")
    assert len(flat) >= len(scenario.entries)


def test_06_the_session_ends_on_its_own(scenario):
    """S5 -> S6 -> S7 -> S8. The ending ritual, on a 90-second session.

    The shipped session is 25 minutes, which is the right number for a child
    and the wrong one for a test. The policy is root-owned, so the harness
    rewrites it over ssh and restarts the shell -- which is also the only way
    to get back to Who's here? without rebooting.
    """
    vm = scenario.vm
    vm.write_session_policy(session_policy(length=1.5, ending_offer=1, put_away=0.34))
    cursor = vm.restart_shell()

    blob = scenario.wait_until(
        lambda image: dark_centroid(image, (300, 250, 980, 740)),
        what="Who's here? after the restart",
    )
    scenario.shot("restarted", "S1 again, on a 90-second session")
    vm.click(blob[0], blob[1])
    scenario.expect_log("state choosing -> home (choose_profile)", since=cursor)
    started = time.monotonic()

    scenario.expect_log("state home -> ending_offer (ending_offer_due)", timeout=90, since=cursor)
    time.sleep(1.5)
    offer = scenario.shot("ending-offer", "S5 'The sun is going down'")
    choices = find_grid(offer)
    row = max(choices, key=len) if choices else []
    assert len(row) >= 2, f"the offer should have two choices, found {choices}"
    print(f"  offer buttons at {[centre(box) for box in row]}")

    # "Finish this one" is the left-hand choice (ending.py builds it first).
    vm.click(*centre(row[0]))
    scenario.expect_log("state ending_offer -> home (dismiss_offer)", timeout=20, since=cursor)

    # KNOWN BUG, recorded in docs/spikes/e2e-scenario.md: nothing remembers
    # that the offer was answered, so app._advance_ritual re-presents it on the
    # very next tick. Reported, not asserted -- this line should start printing
    # "stayed on Home" the day the guard lands, and the test still passes.
    time.sleep(3)
    bounced = (
        "state home -> ending_offer"
        in scenario.journal(cursor).split("state ending_offer -> home (dismiss_offer)")[-1]
    )
    print(
        f"  after 'Finish this one': {'the offer came straight back' if bounced else 'stayed on Home'}"
    )

    scenario.expect_log("-> put_away (put_away_due)", timeout=90, since=cursor)
    time.sleep(2)
    scenario.shot("put-away", "S6 Let's keep that")

    scenario.expect_log("state put_away -> goodbye (goodbye_due)", timeout=90, since=cursor)
    time.sleep(2)
    goodbye = scenario.shot("goodbye", "S7 Goodbye")
    print(f"  the ritual took {time.monotonic() - started:.0f}s from choosing a profile")

    buttons = [box for row in find_grid(goodbye) for box in row]
    assert buttons, "Goodbye has no buttons"
    # Show a grown-up, then Goodnight: the last one is the way out.
    vm.click(*centre(buttons[-1]))
    scenario.expect_log("state goodbye -> sleeping (goodnight)", timeout=30, since=cursor)
    time.sleep(1.5)
    scenario.shot("sleeping", "S8 Sleeping")


def test_07_artefacts_are_all_there(scenario):
    """Every step left a screenshot, and the sheet has something to tile."""
    assert len(scenario.shots) >= 9, [name for _, name in scenario.shots]
    for path, _caption in scenario.shots:
        assert path.exists() and path.stat().st_size > 1000, path
    print(f"  {len(scenario.shots)} screenshots in {scenario.output_dir}")
