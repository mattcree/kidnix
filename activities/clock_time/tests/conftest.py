from __future__ import annotations

import sys
from pathlib import Path

#: The activity SDK ships **with the image** -- `build_files/60-shell.sh` copies
#: `kidnix_activity` and `kidnix_shell` into site-packages beside the shell
#: (docs/design/activity-sdk.md section 10). In a checkout it is three
#: directories up, in `shell/`, and putting it on the path here is what lets the
#: GTK tests run without an install step and without this package declaring a
#: dependency it must not have. An installed copy always wins: the path is only
#: added when the import genuinely fails.
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


def _shell_on_path() -> bool:
    try:
        import kidnix_shell  # noqa: F401
    except ImportError:
        return False
    return True


#: True when `kidnix_shell` is importable, which is what the sun-agreement and
#: palette-agreement tests need. It is a *separate* question from HAVE_SDK
#: because `kidnix_shell` has no GTK import at module level and the SDK does.
HAVE_SHELL = HAVE_SDK and _shell_on_path()
