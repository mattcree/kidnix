from __future__ import annotations

import sys
import tomllib
from pathlib import Path

import pytest

from sounds_and_words.ceiling import custom_ceiling
from sounds_and_words.corpus import load_corpus

FIXTURES = Path(__file__).parent / "fixtures"

#: The activity SDK ships **with the image** -- `build_files/60-shell.sh`
#: copies `kidnix_activity` and `kidnix_shell` into site-packages beside the
#: shell (docs/design/activity-sdk.md section 10). In a checkout it is two
#: directories up, in `shell/`, and putting it on the path here is what lets
#: the GTK tests run without an install step and without this package
#: declaring a dependency it must not have. An installed copy always wins:
#: the path is only added when the import genuinely fails.
SHELL_SRC = Path(__file__).resolve().parents[3] / "shell"


def _sdk_on_path() -> bool:
    try:
        import kidnix_activity
    except ImportError:
        if SHELL_SRC.is_dir() and str(SHELL_SRC) not in sys.path:
            sys.path.insert(0, str(SHELL_SRC))
    try:
        import kidnix_activity  # noqa: F401
    except ImportError:
        return False
    return True


#: True when `kidnix_activity` can be imported at all. Tests that need the SDK
#: skip on it; the pure-logic tests -- which are the CI floor -- never look.
HAVE_SDK = _sdk_on_path()


@pytest.fixture(scope="session")
def corpus():
    return load_corpus()


@pytest.fixture(scope="session")
def appendix7():
    with (FIXTURES / "reading_framework_appendix7.toml").open("rb") as fh:
        return tomllib.load(fh)


@pytest.fixture(scope="session")
def appendix7_ceiling(corpus, appendix7):
    f = appendix7["fixture"]
    ids = set(f["alphabet_gpcs"]) | set(f["named_gpcs"]) | set(f["added_gpcs"]) | set(
        f["footnote_variant_gpcs"]
    )
    return custom_ceiling(
        corpus,
        ids,
        scheme="reading_framework_appendix7",
        label="Reading Framework Appendix 7",
        tricky_words=set(f["exception_words"]),
        notes=("DfE Reading Framework 2023, Appendix 7, pp.144-145.",),
    )
