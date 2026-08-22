"""Pagination, offline suggestions, count words, and the CLI."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from kidnix_shell.cli import build_parser, main
from kidnix_shell.suggestions import BY_ACTIVITY, GENERAL, offline_suggestion
from kidnix_shell.util import clamp, paginate


def test_paginate_splits_evenly() -> None:
    assert paginate(list(range(8)), 4) == [[0, 1, 2, 3], [4, 5, 6, 7]]


def test_paginate_keeps_a_short_last_page() -> None:
    assert paginate(list(range(5)), 4) == [[0, 1, 2, 3], [4]]


def test_paginate_gives_one_empty_page_for_nothing() -> None:
    assert paginate([], 12) == [[]]


def test_paginate_rejects_a_nonsense_page_size() -> None:
    with pytest.raises(ValueError):
        paginate([1, 2], 0)


def test_twelve_activities_fit_on_one_page() -> None:
    """Spec S2 / SYNTHESIS B2: at most 12 tiles, one page."""
    assert len(paginate(list(range(12)), 12)) == 1
    assert len(paginate(list(range(13)), 12)) == 2


def test_clamp() -> None:
    assert clamp(5, 0, 10) == 5
    assert clamp(-1, 0, 10) == 0
    assert clamp(99, 0, 10) == 10


def test_an_offline_suggestion_is_keyed_to_the_activity() -> None:
    line = offline_suggestion("tuxpaint", "make", today=date(2026, 8, 18))
    assert line in BY_ACTIVITY["tuxpaint"]


def test_an_unknown_activity_falls_back_to_its_category() -> None:
    line = offline_suggestion("something-new", "make", today=date(2026, 8, 18))
    assert "paper" in line or "show" in line


def test_there_is_always_a_line() -> None:
    assert offline_suggestion("", "", today=date(2026, 8, 18)) in GENERAL


def test_the_suggestion_is_stable_within_a_day() -> None:
    first = offline_suggestion("tuxpaint", "make", today=date(2026, 8, 18))
    second = offline_suggestion("tuxpaint", "make", today=date(2026, 8, 18))
    assert first == second


def test_no_suggestion_promises_the_child_will_come_back() -> None:
    """SYNTHESIS D6: the system has no interest in whether the child returns."""
    everything = [line for lines in [*BY_ACTIVITY.values(), GENERAL] for line in lines]
    for line in everything:
        lowered = line.lower()
        assert "tomorrow" not in lowered
        assert "next time" not in lowered
        assert "come back" not in lowered


def test_the_goodbye_headline_uses_words_not_digits() -> None:
    pytest.importorskip("gi")
    from kidnix_shell.screens.goodbye import count_phrase

    assert count_phrase(0) == "nothing"
    assert count_phrase(3) == "three things"
    assert count_phrase(12) == "12 things"


# --- CLI -----------------------------------------------------------------


def test_the_parser_accepts_the_documented_flags() -> None:
    args = build_parser().parse_args(["--demo", "--windowed", "--run-seconds", "5"])
    assert args.demo and args.windowed and args.run_seconds == 5


def test_validate_manifests_takes_an_optional_directory() -> None:
    assert build_parser().parse_args(["--validate-manifests"]).validate_manifests == ""
    assert build_parser().parse_args(["--validate-manifests", "/x"]).validate_manifests == "/x"


def test_validate_manifests_passes_on_good_files(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    (tmp_path / "a.toml").write_text('id = "a"\nname = "A"\nexec = ["a"]\n', encoding="utf-8")
    assert main(["--validate-manifests", str(tmp_path)]) == 0
    assert "1 valid, 0 invalid" in capsys.readouterr().out


def test_validate_manifests_fails_on_a_bad_file(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    (tmp_path / "a.toml").write_text('id = "a"\n', encoding="utf-8")
    assert main(["--validate-manifests", str(tmp_path)]) == 1
    assert "0 valid, 1 invalid" in capsys.readouterr().out


def test_validate_manifests_reports_a_missing_directory(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    assert main(["--validate-manifests", str(tmp_path / "nope")]) == 0
    assert "no such directory" in capsys.readouterr().out


def test_the_shipped_manifests_pass_the_ci_gate() -> None:
    shipped = Path(__file__).resolve().parents[2] / "system_files/usr/share/kidnix/activities"
    if not shipped.is_dir():
        pytest.skip("running outside the kidnix checkout")
    assert main(["--validate-manifests", str(shipped)]) == 0
