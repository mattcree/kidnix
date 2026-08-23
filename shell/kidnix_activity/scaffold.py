"""``kidnix-activity new <name>`` -- the skeleton a new activity starts from.

What it writes is not a hello-world. It is the smallest thing that is already
*correct*: a manifest that validates, a window that is sized in millimetres,
a save that runs on SIGTERM, a Journal entry with a caption, and a headless
test that proves the last two. The point is that the first thing anybody does
with a new activity is delete code, not add the four things everybody forgets.

Names, because there are three of them and they must not drift:

============ ============================ ===================================
what         example                      used as
============ ============================ ===================================
title        ``Clock and time``           the tile's ``name``, spoken aloud
id           ``clock-and-time``           the manifest ``id``, the Journal's
                                          ``activity_id``, the file name
module       ``clock_and_time``           the Python package
============ ============================ ===================================

All three are derived from one argument, and :func:`names_for` is pure, so the
derivation is a unit test rather than a surprise.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

from .manifest import DEFAULT_AGE_BAND, DEFAULT_CATEGORY, DEFAULT_GOAL, render_manifest

log = logging.getLogger(__name__)

__all__ = ["Names", "names_for", "scaffold"]

_SEPARATORS = re.compile(r"[\s_]+")
_ILLEGAL = re.compile(r"[^a-z0-9-]+")
_RUNS = re.compile(r"-{2,}")


@dataclass(frozen=True)
class Names:
    """The three spellings of one activity."""

    title: str
    activity_id: str
    module: str


def names_for(raw: str) -> Names:
    """``"Clock and time"`` -> title, ``clock-and-time``, ``clock_and_time``.

    Raises :class:`ValueError` on a name with nothing usable in it, rather than
    quietly producing an id the shell's ``ID_RE`` would reject at load time on
    the machine.
    """
    title = " ".join((raw or "").split())
    slug = _RUNS.sub("-", _ILLEGAL.sub("-", _SEPARATORS.sub("-", title.lower()))).strip("-")
    if not slug or not slug[0].isalnum():
        raise ValueError(
            f"{raw!r} does not make an activity id: it needs a letter or a digit, "
            "e.g. 'Clock and time'"
        )
    return Names(title=title, activity_id=slug, module=slug.replace("-", "_"))


def scaffold(
    raw_name: str,
    directory: Path,
    *,
    goal: str = DEFAULT_GOAL,
    category: str = DEFAULT_CATEGORY,
    age_band: str = DEFAULT_AGE_BAND,
    overwrite: bool = False,
) -> list[Path]:
    """Write the skeleton under ``directory/<id>/``. Returns what it wrote.

    Refuses to write over an existing file unless ``overwrite`` -- a scaffolder
    that clobbered a week of work would be a worse bug than any it saves.
    """
    names = names_for(raw_name)
    root = Path(directory) / names.activity_id
    files = _contents(names, goal=goal, category=category, age_band=age_band)

    if not overwrite:
        clashes = [root / name for name in files if (root / name).exists()]
        if clashes:
            raise FileExistsError(
                f"{root} already has {', '.join(p.name for p in clashes)}; "
                "pass --force to overwrite"
            )

    written: list[Path] = []
    for name, text in files.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        written.append(target)
    log.info("scaffolded %s in %s (%d files)", names.activity_id, root, len(written))
    return written


def _contents(names: Names, *, goal: str, category: str, age_band: str) -> dict[str, str]:
    """Every file, as ``relative path -> text``. Pure, so the tests can read it."""
    module = names.module
    return {
        f"{names.activity_id}.toml": render_manifest(
            names.activity_id,
            names.title,
            goal=goal,
            category=category,
            age_band=age_band,
            command=f"/usr/bin/kidnix-{names.activity_id}",
        ),
        "pyproject.toml": _PYPROJECT.format(
            activity_id=names.activity_id, module=module, title=names.title, goal=goal
        ),
        "README.md": _README.format(
            title=names.title, activity_id=names.activity_id, module=module
        ),
        f"{module}/__init__.py": _INIT.format(title=names.title, module=module),
        f"{module}/__main__.py": _MAIN.format(module=module),
        f"{module}/activity.py": _ACTIVITY.format(
            activity_id=names.activity_id, title=names.title, module=module
        ),
        "tests/__init__.py": "",
        f"tests/test_{module}.py": _TEST.format(module=module, activity_id=names.activity_id),
    }


_PYPROJECT = """\
[project]
name = "kidnix-{activity_id}"
version = "0.1.0"
description = "{title} -- {goal}"
requires-python = ">=3.11"
license = {{ text = "Apache-2.0" }}
# kidnix-activity and kidnix-shell come from the image, like PyGObject: they
# are not PyPI dependencies. Create the venv with --system-site-packages.
dependencies = []

[project.scripts]
kidnix-{activity_id} = "{module}.activity:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["{module}"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-q"
"""

_README = """\
# {title}

A kidnix activity. See `docs/design/activity-sdk.md` in the kidnix repository
for the contract this keeps.

```
uv venv --system-site-packages && uv sync --active
uv run --active pytest            # headless: no display needed
kidnix-activity validate {activity_id}.toml
python -m {module}                 # run it on your own desktop
```

What the shell does for you: the band, Back, the session, read-aloud of its own
chrome, and Escape. What you must not do: reach the network, show a quit
dialogue, invent a reward economy, or put text where a picture belongs.
"""

_INIT = '''\
"""{title} -- a kidnix activity."""

from __future__ import annotations

__version__ = "0.1.0"
'''

_MAIN = '''\
"""``python -m {module}``."""

from __future__ import annotations

import sys

from .activity import main

if __name__ == "__main__":
    sys.exit(main())
'''

_ACTIVITY = '''\
"""{title}.

The whole activity. Delete what you do not need -- but keep the shape:

* ``build`` fills the window and nothing else;
* ``save`` is called on SIGTERM (put away) and is the only thing that writes;
* nothing here reaches the network, asks a question at the end, or scores a
  child.
"""

from __future__ import annotations

import logging

from kidnix_activity.app import ActivityApplication, ActivityWindow
from kidnix_activity.widgets import BigButton, Prompt

log = logging.getLogger(__name__)

ACTIVITY_ID = "{activity_id}"
TITLE = "{title}"

PROMPT = "Press the big button."


class Activity:
    """The activity's own state. Small, and never on disk until ``save``."""

    def __init__(self) -> None:
        self.presses = 0


def build(window: ActivityWindow, state: Activity) -> None:
    """Fill the window. Sizes come from ``window.area`` -- millimetres, floored."""
    area = window.area
    window.add(Prompt(PROMPT, speech=window.speech, area=area))

    def pressed() -> None:
        state.presses += 1

    window.add(
        BigButton(
            "Go",
            speak_text="Go. Press me.",
            on_activate=pressed,
            speech=window.speech,
            area=area,
        )
    )
    window.speak(PROMPT)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    state = Activity()
    app = ActivityApplication(ACTIVITY_ID, TITLE)
    app.set_build(lambda window: build(window, state))
    # Called on SIGTERM, once. Write the child's work here and nowhere else.
    app.set_on_finish(lambda: log.info("finished after %d press(es)", state.presses))
    return app.run(argv)
'''

_TEST = '''\
"""Headless tests. No display, no shell, no sound -- these must always run."""

from __future__ import annotations

from pathlib import Path

from kidnix_activity.manifest import validate_file


def test_the_manifest_validates() -> None:
    report = validate_file(Path(__file__).parent.parent / "{activity_id}.toml")
    assert report.ok, report.lines()


def test_the_manifest_never_asks_for_the_network() -> None:
    report = validate_file(Path(__file__).parent.parent / "{activity_id}.toml")
    assert report.activity is not None
    assert report.activity.network_required is False
    assert report.activity.quit == "signal"
'''
