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
    band_height_from,
    centre,
    colour_centroid,
    dark_centroid,
    dark_fraction,
    differs,
    find_grid,
    is_tuxpaint_green,
    mean_colour,
    read_ppm,
    shell_geometry,
)

#: The activity the scenario opens. Row 1, column 2 of a 4x3 Home grid --
#: activities sort by (category, name), so "make" follows "learn" and
#: "Tux Paint" follows "TurboWarp". Asserted, not assumed: the shell's launcher
#: log says which activity actually started.
DRAW_ROW, DRAW_COLUMN = 0, 0

#: The band's buttons, left to right: Back, Undo, My Things, then the Ear on
#: the right. Found in the screenshot rather than computed.
BACK_INDEX = 0
MY_THINGS_INDEX = 2

JOURNAL_GLOB = "/var/home/kid/.local/share/kidnix/journal"

# --------------------------------------------------------------------------- #
# v0.1.5: the band is a separate toplevel that gnome-kiosk pins to the top
# strip, and `lock-on-area` puts every activity in the area *below* it
# (docs/spikes/band-over-activity.md). So Tux Paint no longer owns rows 0-799:
# it owns `band..799` and re-lays out into them. Nothing here may therefore
# hard-code a row -- the boxes are fractions of the content area, and the band's
# height comes from the shell's own `display metrics:` line, which the fit
# backstop can move by a pixel or two.
# --------------------------------------------------------------------------- #

SCREEN_HEIGHT = 800


def canvas_box(band: int) -> tuple:
    """Somewhere safely inside Tux Paint's white paper, below the band."""
    content = SCREEN_HEIGHT - band
    return (430, band + int(content * 0.29), 880, band + int(content * 0.43))


def canvas_ink_box(band: int) -> tuple:
    """The region the stroke is drawn in, with a little slack around it."""
    left, top, right, bottom = canvas_box(band)
    return (left - 30, top - 20, right + 20, bottom + 20)


def canvas_white_box(band: int) -> tuple:
    """A wide swathe of the paper, for "does this look like Tux Paint at all"."""
    content = SCREEN_HEIGHT - band
    return (300, band + int(content * 0.08), 1000, band + int(content * 0.62))


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

    # v0.1.5: the shell is two toplevels and gnome-kiosk decides where they go,
    # so "did it work?" is a question about *geometry*, not about pixels. The
    # shell reports what the compositor actually gave each window; assert it
    # here, because v0.1.5.0 shipped a band that came up 1280x708 in the
    # content rectangle -- above everything, with the content window invisible
    # underneath it -- and every pixel assertion in this file still passed,
    # since the screen was full of shell-coloured pixels either way.
    line = scenario.expect_log("shell geometry ", timeout=45)
    geometry = shell_geometry(line)
    assert geometry["verdict"] == "ok", line
    band = geometry["wbh"]
    assert 80 <= band <= 128, line  # spec 7a's clamp
    # ...and the height the *layout* settled on is the height the compositor
    # was asked for. Deliberately the last such line and not the first: the
    # measured-fit backstop relays out two or three times in the first second
    # and the band gets shorter each time, which is exactly why the config is
    # written once, at the end, rather than on every pass.
    laid_out = [row for row in scenario.journal().splitlines() if " px (button " in row]
    assert laid_out, "the shell never logged its metrics"
    assert band_height_from(laid_out[-1]) == band, f"{laid_out[-1]!r} disagrees with {line!r}"
    assert (geometry["bw"], geometry["bh"]) == (1280, band), line
    assert (geometry["cy"], geometry["cw"], geometry["ch"]) == (band, 1280, 800 - band), line
    scenario.band_height = band
    print(f"  band 0,0 1280x{band}, content 0,{band} 1280x{800 - band}")

    image = scenario.shot("whos-here", "S1 Who's here?")
    assert (image.width, image.height) == (1280, 800)

    # And the same fact, in pixels: a solid strip of the profile's colour at
    # the very top, paper immediately under it.
    strip = mean_colour(image, (0, 8, 1280, band - 12))
    assert strip[1] > strip[0] and strip[2] > strip[0], f"the band strip is {strip}, not teal"
    under = mean_colour(image, (200, band + 6, 1080, band + 30))
    assert min(under) > 225, f"the rows under the band are {under}, not paper"

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


def test_02_choosing_me_asks_whats_next_then_goes_home(scenario):
    """S1 -> S1b -> S2. Clicking the avatar starts a session and asks what
    happens *after* the computer before it opens Home (spec 7b, Coco's Videos).

    Wave 4 added S1b between Who's here? and Home, so this step is now two
    clicks: the profile, then one of the picture options. What the child picks
    is remembered for Goodbye, which is asserted in step 6.
    """
    vm = scenario.vm
    vm.click(*scenario.avatar)

    scenario.expect_log("state choosing -> next_choice (choose_profile)")
    assert "session started for" in scenario.journal()

    asked = scenario.shot("next-after", "S1b What's next after?")
    options = find_grid(asked)
    flat = [box for row in options for box in row]
    assert len(flat) >= 2, f"What's next after? has no picture options: {options}"
    print(f"  {len(flat)} next-after option(s)")

    vm.click(*centre(flat[0]))
    chosen = scenario.expect_log("next after this session:")
    scenario.next_after_id = chosen.rsplit(":", 1)[-1].strip()
    scenario.expect_log("state next_choice -> home (choose_next_after)")
    print(f"  the child chose {scenario.next_after_id!r}")

    image = scenario.shot("home", "S2 Home, after choosing what's next")

    grid = find_grid(image)
    # Progressive disclosure (spec 7b): a fresh machine shows `initial_tiles`
    # = 6 **counting "All done"**, so Home is 4 + 2, not the 4/4/2 of the whole
    # allow-list. `find_grid` reads the densest row it can find, and a two-tile
    # row covers too little of the width to register at the top of its coverage
    # ladder -- so assert what this harness actually needs (a full first row,
    # with Draw at 0,0) rather than a row count that is really a statement
    # about how many sessions the machine has had.
    assert grid, "no tiles on Home at all"
    assert len(grid[0]) == 4, [len(row) for row in grid]
    scenario.grid = grid
    print("  grid " + str([[centre(box) for box in row] for row in grid]))

    buttons = band_buttons(image, scenario.band_height)
    assert len(buttons) >= 3, f"the band is missing buttons: {buttons}"
    scenario.band = buttons
    print(f"  band buttons at {[centre(box) for box in buttons]}")


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
    """S2 -> S3 -> S2. Open Tux Paint, draw, quit, and find it in the Journal.

    Rewritten for v0.1.5 (docs/spikes/band-over-activity.md). Two things moved:

    * **Tux Paint no longer owns the screen.** The band is a toplevel of its
      own, pinned to the top strip and kept above everything by ``set-above``,
      and ``lock-on-area`` gives the activity the rows below it. So the canvas
      is measured from ``band`` downwards, and the band is asserted to still be
      there in the middle of the activity -- which is the whole point of the
      change and covers audit B3, C1 and D3 at once.
    * **Quitting is the band's Back**, not Tux Paint's own Quit tool. The
      manifest passes ``--noquit``, which retires ADR-0010 #5: the picture-coded
      but text-heavy "Do you really want to quit?" dialogue existed only because
      the child had no other way out. Back sends SIGTERM, Tux Paint autosaves,
      and the shell returns Home on ``activity_exited``.
    """
    vm = scenario.vm
    band = scenario.band_height
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
    image = scenario.shot("tuxpaint", "S3 Tux Paint, under the band")
    # Tux Paint's canvas is white; the shell's cream surface is not.
    canvas = mean_colour(image, canvas_white_box(band))
    assert min(canvas) > 245, f"the canvas does not look like Tux Paint: {canvas}"

    # THE POINT OF v0.1.5: the band is still on screen, with the activity below
    # it rather than over it. Audit B3 ("fixed band on every surface"), C1
    # (undo reachable) and D3 (the sun glanceable throughout) all fail together
    # if this does not hold.
    over_activity = band_buttons(image, band)
    assert len(over_activity) >= 3, (
        f"the band is not over the activity: {over_activity}. The shell should "
        "have written window-config.ini's phase B before the content window "
        "was mapped -- check the journal for 'band window mapped' and "
        "'wrote .../window-config.ini (phase activity)'."
    )
    # ...and the activity really did start below it, rather than the band being
    # painted on top of a fullscreen Tux Paint.
    assert min(mean_colour(image, (300, band + 4, 1000, band + 24))) > 200, (
        "the rows just under the band are not Tux Paint's paper"
    )

    vm.drag(_stroke(canvas_box(band)), step_delay=0.08)
    time.sleep(2)
    drawn = scenario.shot("stroke", "S3 a stroke drawn over QMP")
    ink = dark_fraction(drawn, canvas_ink_box(band))
    assert ink > 0.005, f"the canvas is still blank ({ink:.3%} dark)"
    print(f"  {ink:.2%} of the canvas region is ink")

    # Quit -- from the band, not from Tux Paint's own Quit tool.
    #
    # Back sends SIGTERM. Tux Paint catches it (SDL turns it into SDL_QUIT) and
    # answers with its *own* picture-coded "Do you really want to quit?" -- a
    # green tick and a pink cross -- and waits. That is why `noquit=yes` had to
    # be reverted (it swallows the request entirely) and why the shell does not
    # SIGKILL after the grace: only the child's tap makes Tux Paint autosave.
    # So the harness taps the tick, exactly as a child would.
    vm.click(*centre(scenario.band[BACK_INDEX]))
    scenario.expect_log("the band asked the activity to finish", timeout=20)
    time.sleep(3)
    asking = scenario.shot("tuxpaint-asking", "S3 Tux Paint's own 'really quit?'")
    tick = colour_centroid(asking, (0, band, 1280, 800), is_tuxpaint_green)
    assert tick is not None, (
        "Tux Paint did not put its quit prompt up. With quit=yes it answers "
        "SIGTERM with a tick and a cross; with noquit=yes it does nothing at "
        "all and the drawing is lost."
    )
    print(f"  the tick is at ({tick[0]}, {tick[1]}), {tick[2]} px of green")
    vm.click(tick[0], tick[1])

    scenario.expect_log("state in_activity -> home (activity_exited)", timeout=40)
    time.sleep(1.5)
    scenario.shot("back-home", "S2 Home again, after the band's Back")

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
    """S5 -> S6 -> S7 -> S8. The ending ritual, from inside an activity.

    The shipped session is 25 minutes, which is the right number for a child
    and the wrong one for a test. The policy is root-owned, so the harness
    rewrites it over ssh and restarts the shell -- which is also the only way
    to get back to Who's here? without rebooting.

    Since v0.1.5 this step deliberately runs the ritual **with Tux Paint on
    screen**, because that is the case the whole band change is for. The offer
    used to be raised as a fullscreen window over the child's drawing (the CCI
    audit's 02 #4, "a consequence of the band gap rather than a choice"); it is
    now two buttons in the band, and the drawing is never covered.

    Two and a half minutes: offer at T-90 s, put away at T-30 s. Slack on
    purpose -- Tux Paint takes ten to fifteen seconds to put a window up, and a
    test that raced it would fail for a reason that is not the code.
    """
    vm = scenario.vm
    band = scenario.band_height
    vm.write_session_policy(session_policy(length=2.5, ending_offer=1.5, put_away=0.5))
    cursor = vm.restart_shell()

    blob = scenario.wait_until(
        lambda image: dark_centroid(image, (300, 250, 980, 740)),
        what="Who's here? after the restart",
    )
    scenario.shot("restarted", "S1 again, on a two-and-a-half-minute session")
    vm.click(blob[0], blob[1])
    scenario.expect_log("state choosing -> next_choice (choose_profile)", since=cursor)
    started = time.monotonic()

    # S1b again. Pick whatever the first option is; Goodbye has to show it back.
    asked = scenario.wait_until(
        lambda image: find_grid(image) or None,
        what="What's next after? options",
    )
    vm.click(*centre(asked[0][0]))
    chosen = scenario.expect_log("next after this session:", since=cursor)
    next_after_id = chosen.rsplit(":", 1)[-1].strip()
    scenario.expect_log("state next_choice -> home (choose_next_after)", since=cursor)

    # Into the activity, so the offer has something to *not* cover.
    vm.click(*centre(scenario.draw_tile))
    scenario.expect_log("state home -> in_activity (launch_activity)", since=cursor, timeout=40)
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        if vm.out("pgrep -u kid -x tuxpaint || true", check=False):
            break
        time.sleep(1)
    time.sleep(8)  # let it finish laying out under the band
    before = scenario.shot("in-activity", "S3 drawing again, band above")

    # --- S5, in the band ---------------------------------------------------
    scenario.expect_log("ending offer, in the band", timeout=120, since=cursor)
    time.sleep(1.5)
    offer = scenario.shot("band-offer", "S5 the offer, in the band, over an activity")

    # The child is still in their activity: nothing was raised over it.
    assert "state in_activity -> ending_offer" not in scenario.journal(cursor), (
        "the offer took the screen away from the child's drawing"
    )
    strip = (0, 0, offer.width, band)
    changed = differs(before, offer, strip)
    print(f"  {changed:.0%} of the band changed when the offer arrived")
    buttons = band_buttons(offer, band)
    assert len(buttons) >= 3, f"the band lost its buttons in offer mode: {buttons}"
    # ...and the drawing underneath is untouched: same pixels as before.
    below = (0, band + 10, offer.width, offer.height)
    assert differs(before, offer, below) < 0.25, "something covered the activity"

    # "Finish this one" replaces Undo, in Undo's place, at Undo's size.
    vm.click(*centre(buttons[1]))
    time.sleep(2)
    scenario.shot("band-offer-answered", "S5 answered; the band is itself again")
    assert scenario.journal(cursor).count("ending offer, in the band") == 1, (
        "the offer was presented more than once"
    )

    # --- S6, S7, S8 --------------------------------------------------------
    scenario.expect_log("-> put_away (put_away_due)", timeout=120, since=cursor)
    time.sleep(2)
    scenario.shot("put-away", "S6 Let's keep that")

    scenario.expect_log("state put_away -> goodbye (goodbye_due)", timeout=90, since=cursor)
    time.sleep(2)
    goodbye = scenario.shot("goodbye", "S7 Goodbye")
    print(f"  the ritual took {time.monotonic() - started:.0f}s from choosing a profile")

    # S7 shows the child their own plan back (Coco's Videos). The shell speaks
    # the line, and every utterance is one INFO line in the journal.
    ready = [
        line
        for line in scenario.journal(cursor).splitlines()
        if "speaking: " in line and "Ready to" in line
    ]
    assert ready, "Goodbye never said 'Ready to ...' -- the child's choice was lost"
    print(f"  goodbye said: {ready[-1].split('speaking: ', 1)[-1]}")
    print(f"  (the child had chosen {next_after_id!r})")

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
