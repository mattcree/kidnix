"""The flows the happy path never touches (``docs/design/FLOWS.md``, group A).

``test_scenario.py`` drives one child's *ordinary* session end to end: boot,
choose, plan, launch, draw, keep, the offer, put-away via the activity's own
tick, Goodbye, Sleeping. Everything in this file is a flow that story cannot
reach, because each of them needs the machine to be in a state the happy path
never produces -- a spent budget, a bedtime clock, a manifest that points at a
program which exits, a session ended by the child, a session nobody answered.

Covered here, by flow id:

======  =====================================================================
A6      a Journal card **resumes** rather than opening a menu about itself
A18     bedtime words: Goodnight, and the navy Sleeping screen
A19     daytime words: Resting, warm and dim, with no moon and no yawn
A20     "All done" -- the child ends it, in one press, with no confirmation
A21     the session refused **at Who's here**, before a plan is collected
A22     an activity that fails to open: a friendly line, and back to Home
A24     two children, and one of them finishing: resting is per child
A25     a whole session on Tab, Enter and Escape -- no pointer at all
A26     the caption strip, in pixels, while the shell is speaking
A28     the hard stop: the kill, the WARNING, and Goodbye claiming nothing
======  =====================================================================

**One VM, shared with the scenario.** The ``flows`` fixture wraps
``conftest.Scenario`` around the *same* guest ``test_scenario.py`` booted,
because a second boot is 60-90 s of a 12-minute budget spent proving something
the first boot already proved. ``conftest.pytest_collection_modifyitems``
guarantees the scenario runs first, on a shell nobody has interfered with.

**Every test here is independent of every other one**, which the scenario's
steps deliberately are not. Each begins by writing the session policy it needs
and restarting ``kidnix-shell.service`` -- which is also the only way back to
"Who's here?" without rebooting -- and each leaves the machine somewhere the
next restart makes irrelevant. The one thing a test may inherit is the
*Journal*, and A6 says so out loud: it uses the scenario's real drawings when
they are there and makes itself one when they are not.

Artefacts land in ``output/e2e/flows/``, one PNG per assertion worth looking
at, named for the flow it belongs to.
"""

from __future__ import annotations

import datetime
import re
import time
from pathlib import Path

import pytest
from conftest import OUTPUT, Scenario, session_policy
from pixels import (
    band_buttons,
    band_height_from,
    caption_strip_box,
    centre,
    colour_centroid,
    dark_centroid,
    dark_fraction,
    differs,
    find_grid,
    is_all_done_lavender,
    is_focus_ring_yellow,
    is_tuxpaint_green,
    mean_colour,
    read_ppm,
)

FLOWS_OUTPUT = OUTPUT / "flows"

SCREEN_WIDTH, SCREEN_HEIGHT = 1280, 800

#: Where the one big dark shape on "Who's here?" is looked for. Same box the
#: scenario uses: the avatar is >= 30 mm and centred, and nothing else on that
#: screen is dark enough to be mistaken for it.
AVATAR_BOX = (300, 250, 980, 740)

KID_HOME = "/var/home/kid"
DATA_ROOT = f"{KID_HOME}/.local/share/kidnix"
#: ``activities.default_activity_dirs``: the kid's own directory is loaded
#: after the system one and wins on an id collision, which is what makes it
#: possible to add a broken activity to a shipped image without touching it.
USER_ACTIVITIES = f"{DATA_ROOT}/activities"
TUXPAINT_MANIFEST = "/usr/share/kidnix/activities/tuxpaint.toml"
TUXPAINT_SAVED = f"{KID_HOME}/.tuxpaint/saved"

#: The band's buttons, left to right (see ``test_scenario``): Back, Undo,
#: My Things, then the Ear.
BACK_INDEX = 0
MY_THINGS_INDEX = 2

# --- the words the shell is held to ---------------------------------------
#
# Copied from `kidnix_shell.resting` and `kidnix_shell.ritual` rather than
# imported: this harness never imports the shell, because the shell under test
# is the one *inside the image* and a matching copy on the developer's machine
# would prove nothing about it.

BUDGET_REFUSAL = "That's all the computer time for today. Ready to go and play?"
BEDTIME_REFUSAL = "It's night time. kidnix is going to sleep."
RESTING_PREFIX = "kidnix is resting."
SLEEPING_LINE = "kidnix is sleeping."
ALL_DONE_SPEECH = "All done for today?"
LOST_LINE = "Time to stop now."
FAILED_TO_OPEN = "That one didn't open. Let's try something else."

#: A tile whose program exists and exits non-zero straight away -- A22's
#: "the process exits non-zero or never maps a window". ``/bin/false`` is
#: deliberate: a *missing* program is A23 (an outline-only tile that says
#: "this one isn't ready"), which is a different flow with different words.
#: ``order = 1`` puts it in the first cell, so the test can press it without
#: reading any text off the screen.
BROKEN_ID = "e2e-broken"
BROKEN_MANIFEST = f"""\
schema = 1
id = "{BROKEN_ID}"
name = "Broken"
audio_label = "Broken"
order = 1
icon = "kidnix-act-tuxpaint"
icon_kind = "icon-name"
exec = ["/bin/false"]
category = "make"
"""

#: A 1x1 opaque PNG. Enough for the Journal importer to make an entry out of:
#: it is a real image with a real mime type, which is all `import_file` asks.
TINY_PNG_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="

PARENT_TOML = "/etc/kidnix/parent.toml"
PARENT_BACKUP = "/etc/kidnix/parent.toml.e2e-bak"

#: A second child, **appended** to the machine's own parent.toml. TOML lets an
#: array of tables be continued anywhere in the file, so this adds a sibling
#: without touching the PIN, the "What's next after?" options or any access
#: setting -- all of which stay the ones the image ships. A different colour
#: pair and a different badge, because colour is never the sole carrier of
#: identity (accessibility review M2).
SECOND_CHILD = """
[[profiles]]
id = "e2e-sibling"
name = "Sam"
colour_primary = "#8a4f0f"
colour_secondary = "#62b0f0"
avatar = "face-smile"
badge = "leaf"
age_band = "4-5"
skip_next_choice = false
allowed_activity_ids = []
"""

#: How much of the caption strip has to be ink before we believe there is a
#: sentence in it. A 20 pt line across a 1268 px strip is a couple of percent
#: of the sampled pixels; blank paper is zero, because @kid-paper is #fbf7ef
#: and nothing else is drawn in there.
CAPTION_INK_MIN = 0.004
CAPTION_INK_THRESHOLD = 150


# --------------------------------------------------------------------------- #
# fixture
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="module")
def flows(scenario):
    """The scenario's VM, with its own output directory and its own bookkeeping.

    Depending on ``scenario`` is what shares the boot. It also means a broken
    scenario stops this module before it starts, which is right: if the child
    cannot get to Home at all, nothing here is a meaningful failure.
    """
    FLOWS_OUTPUT.mkdir(parents=True, exist_ok=True)
    for stale in list(FLOWS_OUTPUT.glob("*.ppm")) + list(FLOWS_OUTPUT.glob("*.png")):
        stale.unlink()
    story = Scenario(scenario.vm, FLOWS_OUTPUT)
    story.metrics_line = ""
    story.band_height = 0
    try:
        yield story
    finally:
        # Leave the image as we found it: the broken manifest is the only
        # thing here that would outlive the run on a non-snapshot disk.
        scenario.vm.ssh(f"rm -f {USER_ACTIVITIES}/{BROKEN_ID}.toml", check=False)


# --------------------------------------------------------------------------- #
# driving the shell
# --------------------------------------------------------------------------- #


def guest_now(vm) -> datetime.datetime:
    """The guest's *own* local clock.

    Not the host's. QEMU gives the VM a UTC RTC and the disk we ship has no
    timezone set from the host, so on a British summer afternoon the guest is
    an hour behind the machine running these tests -- which is invisible
    everywhere else in the harness (``conftest.session_policy`` puts bedtime
    six hours away, and an hour either way is still six-ish hours away) and
    fatal here, where the window has to land *on* the shell's idea of now.
    """
    return datetime.datetime.fromisoformat(vm.out("date +%Y-%m-%dT%H:%M:%S"))


def bedtime_policy(vm, length: float = 25, budget: float = 600) -> str:
    """A ``session.toml`` whose bedtime window contains the guest's **now**.

    The mirror of ``conftest.session_policy``, which pins the window six hours
    away so a test run at eight in the evening is not refused. Here the refusal
    is the point: ``Session.may_start`` checks ``is_bedtime`` first, so this is
    the one policy that reaches the night vocabulary on the shipped image.
    """
    now = guest_now(vm)
    start = (now - datetime.timedelta(minutes=5)).replace(second=0, microsecond=0)
    end = (now + datetime.timedelta(hours=6)).replace(second=0, microsecond=0)
    return (
        f"length_minutes = {length}\n"
        f"daily_budget_minutes = {budget}\n"
        "ending_offer_minutes = 6\n"
        "put_away_minutes = 2\n"
        "min_session_minutes = 5\n"
        f'bedtime_start = "{start:%H:%M}"\n'
        f'bedtime_end = "{end:%H:%M}"\n'
    )


def restart(story, policy: str) -> str:
    """Write the policy, restart the shell, and learn the new band geometry.

    Returns the journal cursor taken *before* the restart, so every assertion
    in a test can be scoped to this shell and cannot match the previous one's
    identical lines.

    It also starts every child's day again. ``rested_at`` and the spent
    seconds live in the profile's own ``usage.toml`` and survive a shell
    restart **on purpose** (ADR-0014: a restarted shell must not hand back a
    sitting the ritual has already ended) -- which for these tests means the
    flow before this one can leave the face dimmed and the budget spent. A
    scenario that wants yesterday's state writes it; nobody inherits it by
    accident.
    """
    story.vm.ssh(
        "rm -f /var/home/kid/.local/state/kidnix/usage.toml"
        " /var/home/kid/.local/state/kidnix/profiles/*/usage.toml",
        check=False,
    )
    story.vm.write_session_policy(policy)
    cursor = story.vm.restart_shell()
    laid_out = [
        line for line in story.journal(cursor).splitlines() if re.search(r"\bband \d+ px \(", line)
    ]
    assert laid_out, "the shell came back but never logged its metrics"
    # The *last* one: the measured-fit backstop relays out two or three times
    # in the first second and the band gets shorter each time.
    story.metrics_line = laid_out[-1]
    story.band_height = band_height_from(laid_out[-1])
    print(f"  band window {story.band_height} px -- {laid_out[-1]}")
    return cursor


def two_faces(image):
    """The two avatars on a two-child "Who's here?", left one first.

    The row is ``halign: CENTER`` with two children in it, so it is symmetric
    about the middle of the panel and each face is wholly on its own side of
    it. Splitting ``AVATAR_BOX`` down the middle and asking for the dark blob
    in each half is therefore the same trick ``press_the_face`` uses, done
    twice -- no pixel positions, and nothing that a re-layout invalidates.

    Returns ``(first, second)``, each a ``dark_centroid`` tuple, or ``None``
    while there is only one face painted (which is what the wait is for).
    """
    left, top, right, bottom = AVATAR_BOX
    middle = (left + right) // 2
    first = dark_centroid(image, (left, top, middle - 4, bottom))
    second = dark_centroid(image, (middle + 4, top, right, bottom))
    if first is None or second is None:
        return None
    return (first, second)


def face_ink(image, blob, threshold: int = 110) -> float:
    """How much ink is in one face's own bounding box, with a little margin.

    ``blob`` is a ``dark_centroid`` tuple taken from a reference frame, so the
    same box can be measured in a later one -- which is how "this face got
    dimmer and that one did not" is asserted without trusting either face to
    be the same size as the other.

    ``threshold`` is the ruler. The default (110) sees anything inkish, which
    is right for "is a face there". Asserting a **dim** needs a harder one:
    the resting treatment is ``opacity: 0.7``, which blends a #16181d stroke
    to a mean of ~90 -- still "dark" at 110, so the fraction barely moves
    while the child sees the face fade (proven the hard way: the first run of
    A24 measured 10.7% -> 9.9% on a visibly dimmed face). At 60, a full
    stroke counts and a dimmed one does not, so the fraction collapses on the
    rested face and holds on the live one.
    """
    left, top, right, bottom = blob[3]
    return dark_fraction(image, (left - 10, top - 10, right + 10, bottom + 10), threshold=threshold)


def press_the_face(story, timeout: float = 60.0) -> tuple:
    """Wait for "Who's here?" to paint, then press the child's own avatar."""
    blob = story.wait_until(
        lambda image: dark_centroid(image, AVATAR_BOX),
        timeout=timeout,
        what="Who's here? after the restart",
    )
    story.vm.click(blob[0], blob[1])
    return blob


def choose_next_after(story, cursor: str) -> str:
    """S1b: press the first picture option. Returns the id the shell logged."""
    options = story.wait_until(
        lambda image: find_grid(image) or None,
        timeout=30,
        what="What's next after? options",
    )
    story.vm.click(*centre(options[0][0]))
    chosen = story.expect_log("next after this session:", since=cursor)
    story.expect_log("state next_choice -> home (choose_next_after)", since=cursor)
    time.sleep(1.5)
    return chosen.rsplit(":", 1)[-1].strip()


def start_a_session(story, cursor: str) -> None:
    """Who's here -> What's next after -> Home, with a pointer."""
    press_the_face(story)
    story.expect_log("state choosing -> next_choice (choose_profile)", since=cursor)
    choose_next_after(story, cursor)


# --------------------------------------------------------------------------- #
# reading the guest back
# --------------------------------------------------------------------------- #


def spoken(text: str) -> list:
    """Every line the shell said, in order. ``SpeechManager.speak`` logs one
    INFO ``speaking: <text>`` per utterance and nothing else does."""
    return [
        line.split("speaking: ", 1)[-1].strip()
        for line in text.splitlines()
        if "speaking: " in line
    ]


def journal_entries(vm) -> list:
    """Every ``entry.json`` under the kid's data root, sorted. Never raises."""
    found = vm.out(f"find {DATA_ROOT} -name entry.json 2>/dev/null | sort || true", check=False)
    return found.splitlines()


def caption_ink(story, image) -> float:
    """How much of the caption strip is ink rather than paper."""
    box = caption_strip_box(story.metrics_line, SCREEN_WIDTH)
    assert box is not None, (
        f"no caption strip in the shell's own metrics line: {story.metrics_line!r}. "
        "Either captions are switched off in parent.toml (they default on) or "
        "this image predates the strip entirely."
    )
    return dark_fraction(image, box, threshold=CAPTION_INK_THRESHOLD)


def expect_caption(story, what: str, timeout: float = 6.0) -> float:
    """Poll the caption strip until there is text in it. A26.

    The strip holds a line for four seconds, so this has to look *while* the
    shell is speaking rather than after the journal has confirmed it did --
    which is why it polls the framebuffer instead of taking one screenshot.
    """
    scratch = story.output_dir / "caption.ppm"
    deadline = time.monotonic() + timeout
    best = 0.0
    while True:
        image = read_ppm(story.vm.qmp.screendump(scratch))
        ink = caption_ink(story, image)
        best = max(best, ink)
        if ink >= CAPTION_INK_MIN:
            print(f"  caption strip carries {what}: {ink:.2%} ink")
            return ink
        if time.monotonic() >= deadline:
            break
        time.sleep(0.4)
    raise AssertionError(
        f"the caption strip was blank paper while the shell said {what} "
        f"(best {best:.3%} ink, floor {CAPTION_INK_MIN:.1%}). Every spoken line "
        "is supposed to appear there for four seconds -- the hook is inside "
        "SpeechManager.speak, before the 'is speech enabled?' check."
    )


def tab_until(story, wanted, limit: int = 22, settle: float = 0.7, since: str = "") -> str:
    """Press Tab until the shell speaks one of ``wanted``. Returns what it said.

    This is how a keyboard-only test knows where the ring is without an
    accessibility bus: **keyboard focus speaks immediately and ungated**
    (spec 7b), so the last ``speaking:`` line in the journal *is* the focused
    control's label. Matching on the label rather than counting presses means
    the test does not encode how many controls the band happens to have.

    ``since`` is a cursor from just before the screen arrived: every screen's
    ``on_enter`` calls ``focus_first``, so the ring is already somewhere before
    a single Tab is pressed, and if it is already where we want it, pressing
    Tab would walk a whole cycle to get back.
    """
    targets = [w.lower() for w in wanted]
    heard: list = []
    if since:
        already = spoken(story.vm.shell_journal(since))
        if already and already[-1].lower() in targets:
            print(f"  focus arrived on {already[-1]!r}")
            return already[-1]
        heard.extend(already)
    for _ in range(limit):
        mark = story.vm.journal_cursor()
        story.vm.key("tab")
        time.sleep(settle)
        said = spoken(story.vm.shell_journal(mark))
        heard.extend(said)
        for line in said:
            if line.lower() in targets:
                print(f"  tab -> {line!r}")
                return line
    raise AssertionError(
        f"Tab never reached any of {list(wanted)} in {limit} presses. Heard: {heard}"
    )


def scribble(story) -> tuple:
    """Drag a zig-zag across Tux Paint's paper, and say where it went.

    Not decoration. Tux Paint answers "please finish" with its own tick and
    cross **when there is something to lose**; asked to quit a canvas nobody
    has touched it simply sits there, which cost this file forty-five seconds
    of polling for a dialogue that was never going to come. A child leaving an
    activity has drawn something, so the test draws something.
    """
    content = SCREEN_HEIGHT - story.band_height
    top = story.band_height + int(content * 0.29)
    bottom = story.band_height + int(content * 0.43)
    left, right = 430, 880
    span = right - left
    story.vm.drag(
        [
            (left, (top + bottom) // 2),
            (left + span // 4, bottom),
            (left + span // 2, top),
            (right, (top + bottom) // 2),
        ],
        step_delay=0.08,
    )
    time.sleep(1.5)
    return (left - 30, top - 20, right + 20, bottom + 20)


def wait_for_tick(story, timeout: float = 45.0) -> tuple:
    """Poll the framebuffer for Tux Paint's own green "Yes, I'm done!".

    Not a fixed sleep. SIGTERM sent while Tux Paint is still painting its
    splash does not always raise the dialogue, and the shell's one re-ask
    comes at the end of ``quit_grace`` (30 s for this manifest) -- so the
    honest wait covers the grace rather than assuming the first ask landed.
    """
    scratch = story.output_dir / "tick.ppm"
    box = (150, story.band_height + 20, 1130, 630)
    deadline = time.monotonic() + timeout
    while True:
        image = read_ppm(story.vm.qmp.screendump(scratch))
        tick = colour_centroid(image, box, is_tuxpaint_green)
        if tick is not None:
            return tick
        if time.monotonic() >= deadline:
            raise AssertionError(
                f"Tux Paint's quit prompt never appeared within {timeout:.0f}s. With "
                "quit = 'confirm' it answers SIGTERM with a tick and a cross and "
                "waits; nothing there means it was killed, or never asked."
            )
        time.sleep(1.0)


def kill_the_activity(story, name: str, cursor: str) -> None:
    """SIGKILL a running activity from outside and wait for the shell to notice.

    Used only to *clean up* after a flow whose subject was the launch, not the
    exit. SIGKILL rather than SIGTERM because SIGTERM is Tux Paint's own
    "really quit?" dialogue, and answering it is a different test's job.
    """
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        if story.vm.out(f"pgrep -u kid -x {name} || true", check=False):
            break
        time.sleep(1)
    else:
        pytest.fail(f"{name} never appeared in the process table")
    # Past FAST_FAIL_SECONDS, so the shell reads this as a quit and not as a
    # program that never opened.
    time.sleep(4)
    story.vm.ssh(f"pkill -KILL -u kid -x {name} || true", check=False)
    story.expect_log("state in_activity -> home (activity_exited)", since=cursor, timeout=40)


# --------------------------------------------------------------------------- #
# A21 -- the session refused at the door
# --------------------------------------------------------------------------- #


def test_a21_the_session_is_refused_at_whos_here(flows):
    """A21. A budget that cannot afford the floor is refused **before** a plan.

    The panel's blocker (impl. notes 21.1) was that the third sitting of a
    60-minute day used to be whatever was left: the child tapped her face,
    answered "What's next after?" with a plan she had just committed to out
    loud, reached Home, and was told to put things away ninety seconds later.
    The ruling was a floor and a refusal *at the door* -- so what this proves
    is an ordering, not a message: the daytime refusal is spoken and
    ``NEXT_CHOICE`` is never entered at all.

    One minute of budget against a three-minute floor, rather than a budget of
    zero, because "refused whole rather than truncated" is the actual rule.
    """
    story = flows
    cursor = restart(story, session_policy(length=25, budget=1, min_session=3))
    press_the_face(story)

    story.expect_log("state choosing -> sleeping (goodnight)", since=cursor, timeout=30)
    log = story.journal(cursor)
    said = spoken(log)
    assert BUDGET_REFUSAL in said, f"the refusal was never spoken; heard {said}"
    assert SLEEPING_LINE not in said, (
        f"night vocabulary at {datetime.datetime.now():%H:%M} -- the refusal is "
        "supposed to be in daytime words"
    )

    # The ordering that is the whole flow: no plan was collected, and no clock
    # was ever started.
    assert "-> next_choice" not in log, (
        "the shell asked 'What's next after?' for a session it then refused"
    )
    assert "session started for" not in log, "a session began despite the refusal"

    time.sleep(2)
    image = story.shot("a21-refused", "A21 the refusal at Who's here")
    surface = mean_colour(image, (100, story.band_height + 60, 1180, 740))
    assert surface[0] > surface[2] + 10, (
        f"the refusal screen is {surface}, which is not the warm Resting surface"
    )
    assert min(surface) > 110, f"the refusal screen is {surface}, too dark for daytime"
    print(f"  PASS A21: refused at Who's here in daytime words, surface {surface}")


# --------------------------------------------------------------------------- #
# A18 -- bedtime, on the image
# --------------------------------------------------------------------------- #


def test_a18_bedtime_speaks_night_words_and_sleeps(flows):
    """A18/A19. The other vocabulary, earned by the clock rather than a flag.

    A19's daytime half is asserted at the end of the "All done" flow below;
    this is the half the e2e has never reached, because every run happens in
    the daytime and ``conftest.session_policy`` moves bedtime out of the way on
    purpose. Here the window is moved *over* now, so ``may_start`` refuses for
    ``BEDTIME`` and the shell shows the one screen where a moon is true.

    The two must not be interchangeable, so the assertion is on both channels
    a pre-reader actually gets: the sentence, and the colour of the screen.
    """
    story = flows
    cursor = restart(story, bedtime_policy(story.vm))
    press_the_face(story)

    story.expect_log("state choosing -> sleeping (goodnight)", since=cursor, timeout=30)
    said = spoken(story.journal(cursor))
    assert BEDTIME_REFUSAL in said, f"bedtime never said its own line; heard {said}"
    assert not any(line.startswith(RESTING_PREFIX) for line in said), (
        f"daytime words at bedtime: {said}"
    )

    time.sleep(2)
    image = story.shot("a18-goodnight", "A18 Goodnight, and the Sleeping screen")
    surface = mean_colour(image, (100, story.band_height + 60, 1180, 740))
    assert max(surface) < 100, f"the Sleeping screen is {surface}, not dim navy"
    assert surface[2] > surface[0], f"the Sleeping screen is {surface}, not navy"
    # The dim is on the *window*, not on a centred box inside it (forum #36).
    corner = mean_colour(image, (10, SCREEN_HEIGHT - 60, 200, SCREEN_HEIGHT - 10))
    assert max(corner) < 110, (
        f"the bottom-left corner is {corner}: the dim is a box in the middle of "
        "a lit screen, not the surface itself"
    )
    print(f"  PASS A18: bedtime words and a navy Sleeping screen, surface {surface}")


# --------------------------------------------------------------------------- #
# A20 + A26 + A19 -- the child ends it, and the day ends in Resting
# --------------------------------------------------------------------------- #


def test_a20_all_done_ends_the_session_and_a19_it_rests(flows):
    """A20, A26, A19. "All done" from Home, and where the ending lands.

    Every automated ending on this machine until now has been clock-driven,
    and SYNTHESIS D5 says a third of real endings are the child's. So: find
    the one tile whose fill is not paper (the lavender "All done", pinned to
    cell 7 so a child who navigates by reaching finds it in the same place on
    every grid), press it once, and assert that one press is the whole of it --
    no confirmation, no bribe, straight into the ritual.

    Two more flows fall out of the same forty seconds. **A26**: the caption
    strip under the band carries the put-away line in pixels, which is the
    moment a deaf child either presses on or loses the drawing. **A19**: the
    session ends at four in the afternoon, so the last screen must be Resting
    -- warm, no moon -- and must not say the sleeping line.
    """
    story = flows
    vm = story.vm
    cursor = restart(story, session_policy(length=25, budget=600))
    start_a_session(story, cursor)

    home = story.shot("a20-home", "A20 Home, with All done pinned at cell 7")
    lavender = colour_centroid(
        home, (0, story.band_height + 8, SCREEN_WIDTH, SCREEN_HEIGHT), is_all_done_lavender
    )
    assert lavender is not None, (
        "no lavender tile on Home. 'All done' is the only control in the shell "
        "whose fill is not paper (theme.css button.tile.all-done, #e9e6f7)."
    )
    x, y, pixels = lavender
    print(f"  All done at ({x}, {y}), {pixels} px of lavender")

    # ...and it is where the ruling pins it: the last cell of the second row.
    grid = find_grid(home)
    placed = False
    for row_index, row in enumerate(grid):
        for column, box in enumerate(row):
            if box[0] <= x <= box[2] and box[1] <= y <= box[3]:
                print(f"  it is grid cell (row {row_index}, column {column}) of {len(row)}")
                assert column == len(row) - 1, (
                    "All done is not the last cell of its row; ALL_DONE_INDEX = 7 "
                    "puts it there on a 4x2 page and on a 4x3 one alike"
                )
                placed = True
    if not placed:
        # The coverage ladder does not always resolve the second row of a full
        # Home; the colour did, and that is the fact the flow is about.
        assert x > SCREEN_WIDTH * 0.55 and y > story.band_height + 0.35 * (
            SCREEN_HEIGHT - story.band_height
        ), f"All done is at ({x}, {y}), which is not the right-hand end of a lower row"
        print("  (find_grid did not resolve the row; position checked against the page)")

    vm.click(x, y)
    story.expect_log("state home -> put_away (im_finished)", since=cursor, timeout=30)
    ink = expect_caption(story, "the put-away line")  # A26
    story.shot("a20-put-away", "A20/A26 Put away, with the line captioned under the band")

    said = spoken(story.journal(cursor))
    assert ALL_DONE_SPEECH in said, f"the tile never said its own line; heard {said[-6:]}"
    after = said[said.index(ALL_DONE_SPEECH) + 1 :]
    assert not any("sure" in line.lower() for line in after), (
        f"something asked the child to confirm they had had enough: {after}"
    )
    print(f"  PASS A20: one press reached Put away; PASS A26: {ink:.2%} ink in the strip")

    # --- and on to Goodbye, and A19 ---------------------------------------
    story.expect_log("state put_away -> goodbye (goodbye_due)", since=cursor, timeout=60)
    time.sleep(2)
    goodbye = story.shot("a20-goodbye", "S7 Goodbye, reached by the child's own press")
    buttons = [box for row in find_grid(goodbye) for box in row]
    assert buttons, "Goodbye has no buttons"
    vm.click(*centre(buttons[-1]))  # "Show a grown-up" first, the ending last

    story.expect_log("state goodbye -> sleeping (goodnight)", since=cursor, timeout=30)
    time.sleep(2.5)  # the screen change, not the state change
    image = story.shot("a19-resting", "A19 Resting: daytime words, no moon")
    resting = mean_colour(image, (100, story.band_height + 60, 1180, 740))
    assert min(resting) > 110, f"the ending screen is {resting}: navy, not the warm Resting one"
    assert resting[0] > resting[2] + 15, f"the ending screen is {resting}, not warm"

    said = spoken(story.journal(cursor))
    assert any(line.startswith(RESTING_PREFIX) for line in said), (
        f"the daytime ending never said the resting line; heard {said[-6:]}"
    )
    assert SLEEPING_LINE not in said, (
        f"'{SLEEPING_LINE}' at {datetime.datetime.now():%H:%M}: Resting and "
        "Sleeping are not interchangeable (forum #17)"
    )
    # The ending *button* only learned its daytime voice in the commit after
    # the image under test was built, so its wording is reported, not asserted.
    ending_words = [line for line in said if "Goodnight" in line or "Time to rest" in line]
    print(f"  the ending button said {ending_words}")
    print(f"  PASS A19: the day ended in Resting, surface {resting}")


# --------------------------------------------------------------------------- #
# A22 -- an activity that fails to open
# --------------------------------------------------------------------------- #


def test_a22_an_activity_that_fails_to_open(flows):
    """A22. The child presses a tile, the program exits, and nobody sees an error.

    FLOWS.md has this UNCOVERED, and the regression it guards against is real
    and recent (impl. notes 19.2): the shell "sat in IN_ACTIVITY with nothing
    on screen", which for a child is a blank screen behind a band. The contract
    is three things at once -- a friendly sentence, the detail in the parent's
    journal only, and ``IN_ACTIVITY`` left through its one exit.

    The failure is *installed*, not simulated: a manifest in the kid's own
    activity directory, pointing at ``/bin/false``. That directory is loaded
    after the system one by design, so the shipped image is not touched.
    """
    story = flows
    vm = story.vm
    # `runuser -u kid -- mkdir -p`, not `install -d -o kid`: GNU install applies
    # the ownership it is given to the *last* component only, so the parents it
    # invents on a machine where the shell has not written anything yet come out
    # root-owned -- and the child's own Journal can then never be created.
    vm.ssh(
        f"runuser -u kid -- mkdir -p {USER_ACTIVITIES} && "
        f"cat >{USER_ACTIVITIES}/{BROKEN_ID}.toml <<'KIDNIX_E2E_EOF'\n"
        f"{BROKEN_MANIFEST}KIDNIX_E2E_EOF\n"
        f"chown kid:kid {USER_ACTIVITIES}/{BROKEN_ID}.toml"
    )
    try:
        cursor = restart(story, session_policy(length=25, budget=600))
        start_a_session(story, cursor)

        home = story.shot("a22-home", "A22 Home, with the broken tile in cell 0")
        grid = find_grid(home)
        assert grid and grid[0], "no tiles on Home at all"
        vm.click(*centre(grid[0][0]))

        launched = story.expect_log(f"launched {BROKEN_ID}", since=cursor, timeout=30)
        assert "/bin/false" in launched, launched
        story.expect_log("state home -> in_activity (launch_activity)", since=cursor, timeout=20)

        # The parent's half: one WARNING with the reason, and nowhere else.
        failure = story.expect_log("it did not open", since=cursor, timeout=30)
        assert BROKEN_ID in failure, failure

        # The child's half: a sentence, and the screen they came from.
        story.expect_log("state in_activity -> home (activity_exited)", since=cursor, timeout=30)
        said = spoken(story.journal(cursor))
        assert FAILED_TO_OPEN in said, f"the shell said nothing about it; heard {said[-6:]}"
        assert not any("exit" in line.lower() or "error" in line.lower() for line in said), (
            f"an adult error message reached the child: {said}"
        )

        time.sleep(1.5)
        back = story.shot("a22-back-home", "A22 back on Home, not on a blank screen")
        assert find_grid(back), "the child was left somewhere with no tiles on it"
        surface = mean_colour(back, (100, story.band_height + 60, 1180, 740))
        assert min(surface) > 180, f"the surface behind the band is {surface}, not paper"
        print(f"  PASS A22: {FAILED_TO_OPEN!r}, one WARNING, and Home again")
    finally:
        vm.ssh(f"rm -f {USER_ACTIVITIES}/{BROKEN_ID}.toml", check=False)


# --------------------------------------------------------------------------- #
# A6 -- resume a Journal card
# --------------------------------------------------------------------------- #


def test_a6_a_journal_card_resumes(flows):
    """A6. Press your own picture and be back inside it -- not shown a menu.

    "The biggest untested child affordance" (FLOWS.md): no card has ever been
    pressed on a real image. Sugar's resume-not-open is the one great uncopied
    idea in the product and the whole reason My Things is not a file browser.

    What the shipped Tux Paint manifest supports decides what this can assert.
    With ``exec_resume`` the launch argv has to carry the entry's own file;
    without it the contract is a *plain launch* -- the shell says "Open Draw to
    find it" rather than pretending -- and the assertion is that the argv is
    the plain one. The manifest is read out of the guest so the branch is
    chosen by the image, not by this file.
    """
    story = flows
    vm = story.vm
    cursor = restart(story, session_policy(length=25, budget=600))
    start_a_session(story, cursor)

    # The scenario's own drawings are usually here already. When they are not
    # -- this module run on its own -- make one the way an activity does, by
    # dropping a file where the importer is watching.
    entries = journal_entries(vm)
    if not entries:
        print("  no drawings yet; putting one where the importer will find it")
        vm.ssh(
            f"runuser -u kid -- mkdir -p {TUXPAINT_SAVED} && "
            f"echo {TINY_PNG_BASE64} | base64 -d >{TUXPAINT_SAVED}/e2e-flows.png && "
            f"chown kid:kid {TUXPAINT_SAVED}/e2e-flows.png"
        )
        story.expect_log("journal kept", since=cursor, timeout=40)
        entries = journal_entries(vm)
    assert entries, "the Journal is empty and the importer never filled it"
    print(f"  {len(entries)} thing(s) in My Things")

    home = story.shot("a6-home", "A6 Home, before opening My Things")
    band = band_buttons(home, story.band_height)
    assert len(band) > MY_THINGS_INDEX, f"the band is missing buttons: {band}"
    vm.click(*centre(band[MY_THINGS_INDEX]))
    story.expect_log("state home -> journal (open_journal)", since=cursor, timeout=20)

    time.sleep(1.5)
    cards = story.shot("a6-my-things", "A6 My Things")
    boxes = [box for row in find_grid(cards) for box in row]
    assert boxes, "My Things is empty -- there is no card to press"
    print(f"  {len(boxes)} card(s): {[centre(box) for box in boxes]}")

    vm.click(*centre(boxes[0]))
    launched = story.expect_log("launched tuxpaint", since=cursor, timeout=40)
    story.expect_log("state journal -> in_activity (launch_activity)", since=cursor, timeout=20)

    argv = launched.rsplit("): ", 1)[-1].strip()
    resumable = "exec_resume" in vm.out(f"cat {TUXPAINT_MANIFEST}", check=False)
    if resumable:
        assert ".png" in argv or "/" in argv, (
            f"the manifest declares exec_resume, so the card had to hand the file to it: {argv}"
        )
        print(f"  PASS A6: the card resumed into {argv}")
    else:
        assert argv == "['tuxpaint']", (
            f"the shipped manifest has no exec_resume, so a card is a plain "
            f"launch and the argv carries no file: {argv}"
        )
        print(f"  PASS A6: the card launched Draw plainly ({argv}); tuxpaint.toml")
        print("           declares no exec_resume, so 'Open Draw to find it' is the contract")

    # ...and the activity really is on screen, which is the "be back inside it"
    # half of the flow. Asked as "did the content area stop being My Things?"
    # rather than "is it white": Tux Paint opens on its own splash, so a test
    # that looked for the canvas would be testing how long a splash lasts.
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        if vm.out("pgrep -u kid -x tuxpaint || true", check=False):
            break
        time.sleep(1)
    time.sleep(6)
    opened = story.shot("a6-resumed", "A6 the activity, opened from the card")
    below = (0, story.band_height + 20, SCREEN_WIDTH, SCREEN_HEIGHT)
    changed = differs(cards, opened, below)
    assert changed > 0.35, (
        f"only {changed:.0%} of the content area changed: the card was pressed "
        "and the screen still shows the menu about it"
    )
    assert len(band_buttons(opened, story.band_height)) >= 3, "the band did not survive the resume"
    print(f"  {changed:.0%} of the content area is the activity now")

    kill_the_activity(story, "tuxpaint", cursor)


# --------------------------------------------------------------------------- #
# A25 -- a whole session without a pointer
# --------------------------------------------------------------------------- #


def test_a25_a_whole_session_on_the_keyboard(flows):
    """A25. Tab, Enter and Escape, from Who's here to All done.

    The accessibility reviewer's blocker was absolute: "there is no keyboard
    route to Back, Undo, My Things, the Ear, the sun or the gate, **ever**".
    ``test_gtk_smoke.py`` proves the ring in-process, by calling
    ``Keyboard.key()``; this drives the real compositor, where the shell's own
    ``.kid-focus`` has to draw on whichever of its two toplevels gnome-kiosk
    has *not* focused, and where the keys have to arrive at all.

    Where the ring is, is read from the shell's own voice: keyboard focus
    speaks immediately and ungated (spec 7b), so the last ``speaking:`` line
    names the focused control. Matching the label rather than counting presses
    means this test does not encode how many controls the band happens to have.

    **What this run found, and does not pretend away.** Inside an activity the
    compositor gives the keyboard to the *activity's* toplevel, and the shell's
    controller is on the shell's own two windows -- it cannot be on somebody
    else's. So Escape never reaches the shell's Back from inside a drawing. On
    Tux Paint it is worse than nothing: Escape is Tux Paint's own quit key, so
    it raises Tux Paint's "really quit?" prompt, and the SIGTERM the band sends
    afterwards *dismisses* that prompt rather than answering it -- measured on
    the image, twice. Everything on a shell surface is reachable by key;
    **leaving an activity is not**, and that is the one step below that uses
    the pointer, alongside the tick, which belongs to another toolkit
    altogether. Spec 7d #7's "a whole session completes on key values alone"
    is therefore not yet true on this image; it wants an ADR or a fix, not a
    quieter test.
    """
    story = flows
    vm = story.vm
    cursor = restart(story, session_policy(length=25, budget=600))

    child = vm.out(r"""sed -n 's/^name = "\(.*\)"/\1/p' /etc/kidnix/parent.toml | head -1""")
    plans = vm.out(r"""sed -n 's/^audio_label = "\(.*\)"/\1/p' /etc/kidnix/parent.toml""")
    assert child, "could not read the child's name out of parent.toml"
    plan_labels = [line.strip() for line in plans.splitlines() if line.strip()]
    assert plan_labels, "could not read the What's next after? options out of parent.toml"

    # S1: wait for the screen, then never touch the pointer again.
    story.wait_until(lambda image: dark_centroid(image, AVATAR_BOX), timeout=60, what="Who's here?")
    tab_until(story, [child])
    ringed = story.shot("a25-focus-ring", "A25 the shell's own focus ring, on the child's face")
    ring = colour_centroid(
        ringed, (0, story.band_height, SCREEN_WIDTH, SCREEN_HEIGHT), is_focus_ring_yellow
    )
    assert ring is not None, (
        "nothing on the content window is wearing .kid-focus. The ring is the "
        "shell's own CSS class precisely because :focus-visible stops drawing "
        "on the toplevel the compositor did not focus."
    )
    print(f"  the ring is at ({ring[0]}, {ring[1]}), {ring[2]} px of @kid-highlight")
    vm.key("ret")
    story.expect_log("state choosing -> next_choice (choose_profile)", since=cursor, timeout=25)

    # S1b: a plan, on the keyboard.
    mark = vm.journal_cursor()
    tab_until(story, plan_labels, since=mark)
    vm.key("ret")
    story.expect_log("state next_choice -> home (choose_next_after)", since=cursor, timeout=25)
    time.sleep(1.5)
    story.shot("a25-home", "A25 Home, reached without a pointer")

    # The band, and Escape: Tab to My Things, open it, and come back out with
    # the key that is Back. Both halves of the ring in one move -- a band
    # control activated from a content-focused window, and Escape meaning the
    # shell's own Back and nothing else.
    tab_until(story, ["My Things"])
    vm.key("ret")
    story.expect_log("state home -> journal (open_journal)", since=cursor, timeout=25)
    time.sleep(1.5)
    story.shot("a25-my-things", "A25 My Things, opened from the band with Enter")
    vm.key("esc")
    story.expect_log("state journal -> home (back)", since=cursor, timeout=25)
    print("  PASS A25: Escape is Back on the shell's own surfaces")
    time.sleep(1.5)

    # S2 -> S3.
    mark = vm.journal_cursor()
    tab_until(story, ["Draw"], since=mark)
    vm.key("ret")
    story.expect_log("launched tuxpaint", since=cursor, timeout=40)
    story.expect_log("state home -> in_activity (launch_activity)", since=cursor, timeout=20)
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        if vm.out("pgrep -u kid -x tuxpaint || true", check=False):
            break
        time.sleep(1)
    time.sleep(12)  # Tux Paint fades its splash in before it handles a signal
    scribble(story)  # something to lose, so the quit prompt has a reason to exist
    story.shot("a25-in-activity", "A25 inside Draw, launched with Enter")

    # ...and out again, with the band's Back **by pointer**, for a reason worth
    # writing down (see the docstring): inside an activity the keys are the
    # activity's, and pressing Escape here would put *Tux Paint's* quit prompt
    # up rather than the shell's Back -- which the shell's own SIGTERM then
    # cancels, leaving the child inside a drawing nobody can leave.
    print(
        "  FINDING A25: inside an activity the keyboard belongs to the activity. "
        "gnome-kiosk focuses the activity's toplevel and the shell's controller is "
        "on its own two windows only, so Escape never reaches the shell's Back; on "
        "Tux Paint it raises Tux Paint's own quit prompt instead, which the band's "
        "SIGTERM then dismisses. Leaving an activity is the one step of a session "
        "a child on a switch cannot take. Measured here, on the image."
    )
    surface = read_ppm(vm.qmp.screendump(story.output_dir / "a25-band.ppm"))
    buttons = band_buttons(surface, story.band_height)
    assert buttons, f"the band has no buttons over the activity: {buttons}"
    vm.click(*centre(buttons[BACK_INDEX]))
    story.expect_log("the band asked the activity to finish", since=cursor, timeout=25)

    tick = wait_for_tick(story)
    story.shot("a25-asking", "A25 Tux Paint asked whether to finish")
    vm.click(tick[0], tick[1])  # somebody else's toolkit; no key of ours reaches it
    story.expect_log("state in_activity -> home (activity_exited)", since=cursor, timeout=40)
    time.sleep(2)

    # ...and the way a child who has had enough gets out.
    mark = vm.journal_cursor()
    tab_until(story, [ALL_DONE_SPEECH], since=mark)
    vm.key("ret")
    story.expect_log("state home -> put_away (im_finished)", since=cursor, timeout=30)
    story.shot("a25-all-done", "A25 All done, pressed with Enter")
    print(
        "  PASS A25: Who's here -> plan -> My Things -> Home -> Draw -> All done, "
        "every shell surface driven on key values alone"
    )


# --------------------------------------------------------------------------- #
# A28 -- the hard stop, and telling the truth about it
# --------------------------------------------------------------------------- #


def test_a28_the_hard_stop_tells_the_truth(flows):
    """A28. The tick is never answered, so the drawing is destroyed -- and said so.

    The scenario's ending is the good one: the child finds Tux Paint's tick,
    the drawing is autosaved, "Let's keep that" is a true sentence. This is the
    same three and a half minutes with the tick left alone, which is the case
    spec 7c's honesty rule exists for. Three facts have to hold together, and
    they are three different audiences:

    * the **parent** gets ``put-away: killed tuxpaint with unsaved work
      possible`` at WARNING, once;
    * the **child** gets "Time to stop now." -- not "Let's keep that", and no
      keep earcon, because nothing flew anywhere;
    * **Goodbye** counts ``journal.made_on_today()`` and nothing else, so it
      cannot claim to have kept what was killed.

    The Journal is emptied first. Not to make the assertion easier -- to make
    it mean anything: with the scenario's two real drawings still in it,
    Goodbye would rightly count them and "nothing was claimed" would be
    unfalsifiable.
    """
    story = flows
    vm = story.vm
    # A day on which nothing has been kept yet.
    vm.ssh(f"rm -rf {DATA_ROOT}/profiles/*/journal {DATA_ROOT}/journal", check=False)

    # 3 minutes: offer at T-89 s, put-away at T-60 s, hard stop at T-0. The
    # windows are proportional with floors (impl. 21.1), so this is the
    # shortest sitting the shipped arithmetic will grant.
    cursor = restart(story, session_policy(length=3, budget=600, min_session=3))
    press_the_face(story)
    story.expect_log("state choosing -> next_choice (choose_profile)", since=cursor)
    started = time.monotonic()
    choose_next_after(story, cursor)

    assert not journal_entries(vm), "the Journal was not empty at the start of the sitting"

    grid = find_grid(story.shot("a28-home", "A28 Home, on a three-minute sitting"))
    assert grid and grid[0], "no tiles on Home"
    vm.click(*centre(grid[0][0]))
    story.expect_log("state home -> in_activity (launch_activity)", since=cursor, timeout=40)
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        if vm.out("pgrep -u kid -x tuxpaint || true", check=False):
            break
        time.sleep(1)
    time.sleep(8)

    # Something on the canvas that only Tux Paint's own tick could have saved.
    inked = scribble(story)
    drawn = story.shot("a28-drawing", "A28 something on the canvas, never saved")
    ink = dark_fraction(drawn, inked)
    assert ink > 0.005, f"the canvas is still blank ({ink:.3%} dark) -- nothing to lose"

    # The offer arrives and is deliberately ignored: an unanswered offer
    # latches, and the ritual carries on without the child.
    story.expect_log("ending offer, in the band", since=cursor, timeout=150)
    story.expect_log("put-away: asked tuxpaint to finish", since=cursor, timeout=150)
    expect_caption(story, "the put-away question, over the activity")  # A26
    story.shot("a28-asking", "A26/A28 the question captioned in the band, over the drawing")

    # ...and nobody answers it. Not the tick, not Back, nothing.
    killed = story.expect_log("with unsaved work possible", since=cursor, timeout=150)
    assert "tuxpaint" in killed, killed
    assert story.journal(cursor).count("with unsaved work possible") == 1, (
        "the hard stop killed more than once"
    )
    print(f"  parent's journal: {killed}")

    story.expect_log("state in_activity -> put_away", since=cursor, timeout=30)
    time.sleep(2)
    story.shot("a28-time-to-stop", "A28 'Time to stop now.' -- no keep, no flight")
    said = spoken(story.journal(cursor))
    assert LOST_LINE in said, f"the shell never said {LOST_LINE!r}; heard {said[-6:]}"
    assert "Let's keep that." not in said, (
        "the shell said 'Let's keep that' about a drawing it had just destroyed"
    )
    assert "Press the tick" not in " ".join(said[said.index(LOST_LINE) :]), (
        "the shell was still asking for a tick after it had killed the activity"
    )

    # S7: nothing is claimed, because nothing reached the Journal.
    story.expect_log("state put_away -> goodbye (goodbye_due)", since=cursor, timeout=90)
    time.sleep(2)
    story.shot("a28-goodbye", "A28 Goodbye, claiming nothing")
    print(f"  the sitting took {time.monotonic() - started:.0f}s from choosing a profile")

    assert not journal_entries(vm), (
        f"something reached the Journal after a SIGKILL: {journal_entries(vm)}"
    )
    said = spoken(story.journal(cursor))
    claims = [line for line in said if line.startswith("You ")]
    assert not claims, f"Goodbye claimed something was kept: {claims}"
    print(f"  PASS A28: killed once, {LOST_LINE!r} spoken, Goodbye claimed nothing")


# --------------------------------------------------------------------------- #
# A24 (+ A19, A20) -- two children, and one of them finishing
# --------------------------------------------------------------------------- #


def test_a24_a_siblings_afternoon_survives_the_other_ones_ending(flows):
    """A24. ADR-0014, on the shipped image: resting is per child.

    Matt's first hands-on session found it from the other side -- "once you
    pick me on the front page, it doesn't seem like you can actually get back
    out" -- and the defect underneath was that the *machine* rested. Child A
    pressed "All done" at ten past four, the screen went to Resting until the
    next window or tomorrow, and child B could not start without a grown-up at
    the gate. P1 #10 ("instant switching, both of us") claimed otherwise.

    Four facts, and every one of them is a thing a five-year-old can check:

    1. A finishes the ritual and **"Who's here?" comes back** -- not Resting.
       The shell must not even flash the Resting screen past them, so the
       assertion is on the log: ``sleeping -> choosing (wake)`` follows
       ``goodbye -> sleeping`` with no tick in between.
    2. **A's face is dimmed and B's is not**, measured in pixels rather than
       believed: each face is compared with *itself* before the sitting, so
       A's box loses ink and B's does not.
    3. **Pressing A's face says why and stays put.** The resting line, the same
       one the Resting screen would have used, and no state change at all --
       no ``next_choice``, no ``sleeping``.
    4. **B's face still starts B's sitting**, which is the sentence P1 #10 has
       been making all along.

    The second child is appended to the machine's own ``parent.toml`` rather
    than replacing it, so the PIN, the "What's next after?" options and every
    access setting are the ones the image ships. It is put back afterwards.
    """
    story = flows
    vm = story.vm
    vm.ssh(f"cp -a {PARENT_TOML} {PARENT_BACKUP}")
    try:
        vm.ssh(f"cat >>{PARENT_TOML} <<'KIDNIX_E2E_EOF'\n{SECOND_CHILD}\nKIDNIX_E2E_EOF")
        cursor = restart(story, session_policy(length=25, budget=600))

        story.wait_until(two_faces, timeout=60, what="Who's here? with two faces on it")
        start = story.shot("a24-two-faces", "A24 two children, both able to start")
        both = two_faces(start)
        assert both is not None, "the two faces were there and then were not"
        first, second = both
        print(f"  faces at {first[:2]} and {second[:2]}")

        # --- the first child has a whole sitting, and ends it ---------------
        vm.click(first[0], first[1])
        story.expect_log("state choosing -> next_choice (choose_profile)", since=cursor)
        choose_next_after(story, cursor)

        home = story.shot("a24-home", "A24 the first child's Home")
        lavender = colour_centroid(
            home, (0, story.band_height + 8, SCREEN_WIDTH, SCREEN_HEIGHT), is_all_done_lavender
        )
        assert lavender is not None, "no lavender 'All done' tile on Home"
        vm.click(lavender[0], lavender[1])
        story.expect_log("state home -> put_away (im_finished)", since=cursor, timeout=30)
        story.expect_log("state put_away -> goodbye (goodbye_due)", since=cursor, timeout=60)

        # Reaching Goodbye is what rests *that child* (ADR-0014).
        rested = story.expect_log("resting until the day rolls", since=cursor, timeout=30)
        assert "child" in rested, rested

        time.sleep(2)
        goodbye = story.shot("a24-goodbye", "A24 Goodbye, for one of the two")
        buttons = [box for row in find_grid(goodbye) for box in row]
        assert buttons, "Goodbye has no buttons"
        vm.click(*centre(buttons[-1]))  # the ending, not "Show a grown-up"

        # --- 1. Who's here comes back, and Resting is never shown -----------
        story.expect_log("state goodbye -> sleeping (goodnight)", since=cursor, timeout=30)
        story.expect_log("state sleeping -> choosing (wake)", since=cursor, timeout=15)
        log = story.journal(cursor)
        assert "somebody here may start a session again" in log, (
            "the shell woke, but not for the reason ADR-0014 gives"
        )
        said = spoken(log)
        assert not any(line.startswith(RESTING_PREFIX) for line in said), (
            "the Resting screen spoke its line on a machine where a sibling "
            f"could still start: {said[-6:]}"
        )
        assert SLEEPING_LINE not in said, f"night vocabulary at four in the afternoon: {said[-6:]}"

        # --- 2. one face is dimmed, and it is the right one -----------------
        #
        # Each face is compared with **itself** before the sitting rather than
        # with its neighbour: the two tiles are not the same width (a name is
        # never abbreviated, so the tile grows to fit it), which makes an ink
        # *fraction* comparison between them a comparison of name lengths.
        time.sleep(2.5)
        image = story.shot("a24-one-resting", "A24 one face resting, one ready")
        was_rested, was_live = face_ink(start, first, 60), face_ink(start, second, 60)
        now_rested, now_live = face_ink(image, first, 60), face_ink(image, second, 60)
        assert now_rested < was_rested * 0.85, (
            f"the face whose sitting is over has {now_rested:.2%} ink where it "
            f"had {was_rested:.2%}: it is not being drawn any differently, so a "
            "child cannot see whose turn is over"
        )
        assert now_live > was_live * 0.85, (
            f"the sibling's face went from {was_live:.2%} ink to {now_live:.2%} "
            "as well -- the dim is landing on the whole screen rather than on "
            "the one child who has finished"
        )
        print(
            f"  rested face {was_rested:.2%} -> {now_rested:.2%} ink; "
            f"sibling {was_live:.2%} -> {now_live:.2%}"
        )

        # --- 3. pressing the rested face says why, and stays put ------------
        tap = vm.journal_cursor()
        vm.click(first[0], first[1])
        time.sleep(3)
        after = story.journal(tap)
        heard = spoken(after)
        assert any(line.startswith(RESTING_PREFIX) for line in heard), (
            f"pressing a resting face said nothing about resting; heard {heard}"
        )
        assert "-> next_choice" not in after, "a rested child started a second sitting"
        assert "-> sleeping" not in after, (
            "pressing one child's face sent the whole machine to Resting, which "
            "is the defect ADR-0014 exists to fix"
        )
        story.shot("a24-refused", "A24 the rested face, answered where it was pressed")

        # --- 4. ...and the sibling can still start --------------------------
        vm.click(second[0], second[1])
        story.expect_log("state choosing -> next_choice (choose_profile)", since=tap, timeout=30)
        started = story.expect_log("session started for", since=tap, timeout=15)
        print(f"  the sibling started anyway: {started}")
        story.shot("a24-sibling-started", "A24 the second child's own sitting")
        print(
            "  PASS A24: one child's ending is one child's ending -- "
            "Who's here returned, the face said why, the sibling started"
        )
    finally:
        vm.ssh(f"mv {PARENT_BACKUP} {PARENT_TOML}", check=False)
        restart(story, session_policy())


# --------------------------------------------------------------------------- #


def test_zz_every_flow_left_a_picture(flows):
    """The artefacts, and a roll-call of the flows this module actually drove.

    Deliberately *not* a fixed count: ``-k`` is how anybody iterates on one of
    these flows, and a subset run should not fail on the size of its own
    contact sheet. What it does assert is that every shot a step claimed to
    take is a real, non-empty image on disk -- a screendump that came back
    empty is a silent failure everywhere else.
    """
    story = flows
    assert story.shots, "no screenshots at all"
    for path, _caption in story.shots:
        assert Path(path).exists() and Path(path).stat().st_size > 1000, path
    flows_seen = sorted({Path(png).stem.split("-", 2)[1] for png, _ in story.shots})
    print(f"  {len(story.shots)} screenshots in {story.output_dir}")
    print(f"  flows driven: {', '.join(flows_seen)}")
