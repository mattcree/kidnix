"""The corpus is generated, and the generator is the source of truth.

`data/*.toml` says "do not edit by hand" at the top of every file. This test is
what makes that true: it re-runs `tools/gen.py` into a temporary directory and
insists the result is byte-identical to what is checked in.

If this fails, either somebody edited the TOML directly (fix the transcription
in `tools/lsdata.py` instead) or the generator changed and `data/` was not
regenerated.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
GENERATED = ["graphemes.toml", "words.toml", "tricky_words.toml", "sentences.toml", "lexicon.toml"]
HAND_WRITTEN = ["sources.toml", "parent_text.toml", "schemes/other_schemes.toml"]


@pytest.fixture(scope="module")
def regenerated(tmp_path_factory):
    out = tmp_path_factory.mktemp("data")
    env = dict(os.environ, SW_DATA_OUT=str(out))
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "gen.py")],
        cwd=ROOT, env=env, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "PROBLEMS" not in result.stdout, result.stdout
    assert "MISSING" not in result.stdout, result.stdout
    return out


@pytest.mark.parametrize("name", GENERATED)
def test_the_checked_in_data_matches_the_generator(regenerated, name):
    assert (regenerated / name).read_text() == (ROOT / "data" / name).read_text(), (
        f"data/{name} is out of date: run `uv run python tools/gen.py`"
    )


@pytest.mark.parametrize("name", GENERATED)
def test_every_generated_file_says_not_to_edit_it(name):
    assert "Do not edit by hand" in (ROOT / "data" / name).read_text()[:400]


@pytest.mark.parametrize("name", HAND_WRITTEN)
def test_hand_written_files_are_not_claimed_by_the_generator(name):
    """The three files a human maintains must not pretend to be generated."""
    assert "Do not edit by hand" not in (ROOT / "data" / name).read_text()[:400]


def test_the_generator_reports_no_unsegmentable_words(regenerated):
    """The fixture already asserted this; the name is here so a failure reads."""
    assert regenerated.exists()
