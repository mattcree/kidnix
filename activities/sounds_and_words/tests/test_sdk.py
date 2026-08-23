"""Where this activity and the SDK have to agree, and what happens if they stop.

``sounds_and_words.settings.progress_dir`` computes the per-profile state
directory without importing ``kidnix_shell``, so that the guarantee-carrying
half of this activity stays importable on a machine with no shell and no GTK.
That is a duplicated spelling, and a duplicated spelling drifts unless
something re-derives it from the original. This is that something.
"""

from __future__ import annotations

import pytest

from conftest import HAVE_SDK
from sounds_and_words.settings import progress_dir

pytestmark = pytest.mark.skipif(not HAVE_SDK, reason="kidnix_activity is not importable here")


def env(tmp_path, profile: str = "sam") -> dict[str, str]:
    return {
        "HOME": str(tmp_path),
        "XDG_STATE_HOME": str(tmp_path / ".local" / "state"),
        "XDG_DATA_HOME": str(tmp_path / ".local" / "share"),
        "KIDNIX_ACTIVITY_ID": "sounds-and-words",
        "KIDNIX_PROFILE_ID": profile,
    }


def test_our_state_directory_is_the_sdks_profile_state(tmp_path):
    from kidnix_activity.env import LaunchEnv

    environment = env(tmp_path)
    launch = LaunchEnv.from_env(environment)
    assert progress_dir(environment) == launch.paths.profile_state / "sounds-and-words"


def test_the_pre_profiles_layout_agrees_too(tmp_path):
    """The right answer on a machine that has never had profiles, and the only
    one either of us is entitled to when the shell did not say which child."""
    from kidnix_activity.env import LaunchEnv

    environment = env(tmp_path, profile="")
    launch = LaunchEnv.from_env(environment)
    assert progress_dir(environment) == launch.paths.profile_state / "sounds-and-words"


def test_two_profiles_disagree_in_the_same_way_on_both_sides(tmp_path):
    from kidnix_activity.env import LaunchEnv

    sam, alex = env(tmp_path, "sam"), env(tmp_path, "alex")
    assert progress_dir(sam) != progress_dir(alex)
    assert LaunchEnv.from_env(sam).paths.profile_state != LaunchEnv.from_env(alex).paths.profile_state


def test_the_activity_id_is_the_one_the_journal_will_file_under(tmp_path):
    from kidnix_activity.env import LaunchEnv

    from sounds_and_words import ACTIVITY_ID

    assert LaunchEnv.from_env(env(tmp_path)).activity_id == ACTIVITY_ID


def test_a_process_the_shell_did_not_start_knows_it(tmp_path):
    """The SDK never guesses an activity id, and neither do we: an entry
    written without one is a card in My Things that resumes nothing."""
    from kidnix_activity.env import LaunchEnv

    bare = {"HOME": str(tmp_path)}
    assert not LaunchEnv.from_env(bare).launched_by_shell


def test_the_pure_half_of_this_package_imports_no_gtk():
    """The half that carries the guarantee must be provable headless
    (docs/design/activity-sdk.md section 2). A GTK import here would make the
    corpus tests need a display."""
    import subprocess
    import sys

    code = (
        "import sys, sounds_and_words;"
        "assert 'gi' not in sys.modules, sorted(m for m in sys.modules if m.startswith('gi'));"
        "print('clean')"
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert "clean" in result.stdout
