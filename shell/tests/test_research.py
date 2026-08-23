"""``research.toml``: the switch every instrument is behind (spec 7d #10).

The safety review's finding was not that the logging was wrong, it was that
"the research default and the shipped default are the same file". So the thing
that has to be provable here is the **negative**: with the file the image ships
(or with no file at all, or with a broken one) nothing anywhere emits a line.
"""

from __future__ import annotations

import logging
import tomllib
from pathlib import Path

import pytest

from kidnix_shell.research import (
    BURST_LOG_PREFIX,
    BURST_PRESSES,
    BURST_WINDOW_SECONDS,
    BurstDetector,
    ResearchConfig,
    load_research,
    parse_research,
)

#: The file the image actually ships. Read, not paraphrased: a test that
#: asserted against its own copy of the defaults would pass while the shipped
#: file said something else.
SHIPPED = Path(__file__).resolve().parents[2] / "system_files/etc/kidnix/research.toml"


# --- the shipped file ----------------------------------------------------


def test_the_shipped_file_turns_everything_off() -> None:
    assert SHIPPED.is_file(), SHIPPED
    data = tomllib.loads(SHIPPED.read_text(encoding="utf-8"))
    config = parse_research(data.get("research"), str(SHIPPED))
    assert not config.enabled
    assert not config.hover_logging
    assert not config.hover_selection
    assert not config.pin_logging
    assert not config.burst_logging
    assert config.journal_path == ""


def test_the_defaults_are_off_before_any_file_is_read() -> None:
    """A machine with no research.toml is not a machine in a study."""
    config = ResearchConfig()
    assert not (
        config.enabled or config.hover_logging or config.pin_logging or config.burst_logging
    )
    assert load_research(None) == config
    assert load_research(Path("/nonexistent/research.toml")) == config


@pytest.mark.parametrize(
    "text",
    [
        "this is not toml {{{",
        "schema = 1",  # no [research] table at all
        "[research]\nenabled = 'yes'",  # a string where a bool belongs
        "research = 7",  # not a table
    ],
)
def test_anything_malformed_means_off(tmp_path: Path, text: str) -> None:
    """Failure-closed. Every way of getting this file wrong means silence."""
    path = tmp_path / "research.toml"
    path.write_text(text, encoding="utf-8")
    assert load_research(path) == ResearchConfig()


# --- the master switch ---------------------------------------------------


def test_enabled_false_overrides_every_individual_key() -> None:
    """ "enabled is a master switch" is the contract, so it is a test."""
    config = parse_research(
        {
            "enabled": False,
            "hover_instrumentation": True,
            "hover_record_selection": True,
            "pin_attempt_logging": True,
            "burst_click_detection": True,
        }
    )
    assert config.hover_instrumentation  # the key itself round-trips...
    assert not config.hover_logging  # ...and buys nothing
    assert not config.hover_selection
    assert not config.pin_logging
    assert not config.burst_logging


def test_recording_a_selection_needs_both_switches() -> None:
    """Dwell is a legibility measurement; dwell-plus-outcome is a model of a child."""
    config = parse_research({"enabled": True, "hover_instrumentation": True})
    assert config.hover_logging
    assert not config.hover_selection

    both = parse_research(
        {"enabled": True, "hover_instrumentation": True, "hover_record_selection": True}
    )
    assert both.hover_selection


def test_turning_it_on_says_so_loudly(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """A study is a thing somebody switched on and must be able to see."""
    path = tmp_path / "research.toml"
    path.write_text("[research]\nenabled = true\nhover_instrumentation = true\n", encoding="utf-8")
    with caplog.at_level(logging.WARNING, logger="kidnix_shell.research"):
        config = load_research(path)
    assert config.hover_logging
    assert "RESEARCH INSTRUMENTATION IS ON" in caplog.text


# --- the burst detector (CCI #54) ----------------------------------------


def study() -> ResearchConfig:
    return ResearchConfig(enabled=True, burst_click_detection=True)


def test_three_presses_inside_a_second_on_nothing_is_a_burst() -> None:
    detector = BurstDetector(research=study())
    assert BURST_PRESSES == 3
    assert BURST_WINDOW_SECONDS == 1.0
    assert not detector.press(0.0)
    assert not detector.press(0.3)
    assert detector.press(0.6)
    assert detector.bursts == 1


def test_a_slower_rhythm_is_not_a_burst() -> None:
    """Two presses either side of the window are two presses, not a burst."""
    detector = BurstDetector(research=study())
    for at in (0.0, 0.9, 1.95, 3.0):
        assert not detector.press(at)
    assert detector.bursts == 0


def test_one_burst_is_one_line_however_long_the_drumming_goes_on() -> None:
    detector = BurstDetector(research=study())
    fired = [detector.press(index * 0.1) for index in range(12)]
    # Twelve presses in 1.2 s: four complete runs of three, not ten overlapping
    # ones -- the count resets on the press that fires.
    assert sum(fired) == 4
    assert detector.bursts == 4


def test_a_press_that_hits_a_control_clears_the_run() -> None:
    """The child found something. That is the opposite of what this measures."""
    detector = BurstDetector(research=study())
    detector.press(0.0)
    detector.press(0.1)
    detector.press(0.2, on_target=True)
    assert not detector.press(0.3)
    assert detector.bursts == 0


def test_the_detector_counts_but_logs_nothing_when_research_is_off(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """**The assertion the safety review asked for.**

    The wiring is unconditional -- turning a study on must not also turn on a
    code path nobody has ever run -- so what has to be provable is that the
    shipped configuration writes nothing.
    """
    detector = BurstDetector()  # i.e. the shipped ResearchConfig()
    with caplog.at_level(logging.INFO, logger="kidnix_shell.research"):
        for at in (0.0, 0.2, 0.4, 0.6):
            detector.press(at)
    assert detector.bursts == 1  # counted in memory, for this process only
    assert BURST_LOG_PREFIX not in caplog.text


def test_the_line_carries_nothing_but_a_count(caplog: pytest.LogCaptureFixture) -> None:
    """No coordinates, no screen, no activity, nothing the child made."""
    detector = BurstDetector(research=study())
    with caplog.at_level(logging.INFO, logger="kidnix_shell.research"):
        for at in (0.0, 0.2, 0.4):
            detector.press(at)
    line = next(m for m in caplog.messages if m.startswith(BURST_LOG_PREFIX))
    assert line == f"{BURST_LOG_PREFIX}: presses=3 window_ms=1000"
