"""The activity catalogue, and every parser in :mod:`system`.

Nothing here forks a process: :func:`kidnix_parent_panel.system.run` is
replaced by a stub everywhere it is needed, which is the reason the runner is
an argument in the first place.
"""

from __future__ import annotations

import json
from dataclasses import replace

from kidnix_parent_panel import catalogue, system

MANIFEST = """\
schema = 1
id = "tuxpaint"
name = "Draw"
audio_label = "Draw"
goal = "Making pictures -- no right answers."
order = 10
icon = "kidnix-act-tuxpaint"
icon_kind = "icon-name"
category = "make"
age_min = 3
age_max = 10
exec = ["tuxpaint"]
"""

SHELF = """\
schema = 1
id = "gcompris"
name = "Letters & numbers"
kind = "shelf"
children_dir = "gcompris"
order = 40
category = "learn"
age_min = 4
age_max = 8
exec = ["gcompris-qt"]
"""

SHELF_CHILD = """\
schema = 1
id = "gcompris.smallnumbers"
name = "Count the dots"
goal = "Counting to ten."
shelf_group_name = "Numbers"
order = 5
category = "learn"
age_min = 4
age_max = 6
exec = ["gcompris-qt"]
"""


def build(tmp_path):
    (tmp_path / "tuxpaint.toml").write_text(MANIFEST)
    (tmp_path / "gcompris.toml").write_text(SHELF)
    shelf = tmp_path / "gcompris"
    shelf.mkdir()
    (shelf / "smallnumbers.toml").write_text(SHELF_CHILD)
    return catalogue.load(tmp_path)


# --- catalogue ------------------------------------------------------------


def test_load_finds_activities_and_shelf_children(tmp_path):
    found = build(tmp_path)
    assert {"tuxpaint", "gcompris", "gcompris.smallnumbers"} == found.ids


def test_shelf_children_are_not_top_level(tmp_path):
    found = build(tmp_path)
    assert {e.id for e in found.top_level()} == {"tuxpaint", "gcompris"}
    assert [e.id for e in found.children_of("gcompris")] == ["gcompris.smallnumbers"]


def test_the_goal_line_is_kept(tmp_path):
    found = build(tmp_path)
    assert found.get("tuxpaint").goal.startswith("Making pictures")


def test_shelf_children_carry_their_group_heading(tmp_path):
    found = build(tmp_path)
    assert found.get("gcompris.smallnumbers").group_name == "Numbers"


def test_a_missing_directory_is_an_empty_catalogue(tmp_path):
    assert catalogue.load(tmp_path / "nope").entries == []


def test_a_broken_manifest_is_recorded_not_raised(tmp_path):
    (tmp_path / "broken.toml").write_text("this is not [ toml")
    found = catalogue.load(tmp_path)
    assert found.entries == []
    assert found.broken and "broken.toml" in str(found.broken[0][0])


def test_a_manifest_with_no_id_is_skipped(tmp_path):
    (tmp_path / "nameless.toml").write_text('name = "Thing"\n')
    assert catalogue.load(tmp_path).entries == []


def test_age_band_overlap():
    entry = catalogue.Entry(id="x", name="X", age_min=6, age_max=10)
    assert not entry.suits((4, 5))
    assert entry.suits((6, 8))
    assert entry.suits(None)


def test_category_labels_are_words_not_keys():
    assert catalogue.Entry(id="x", name="X", category="make").category_label() == "Making"
    assert catalogue.Entry(id="x", name="X", category="odd").category_label() == "Odd"


def test_a_shelf_knows_it_is_one(tmp_path):
    found = build(tmp_path)
    assert found.get("gcompris").is_shelf
    assert found.get("gcompris.smallnumbers").is_shelf_child


# --- system: results ------------------------------------------------------


def test_completed_message_prefers_stderr():
    assert system.Completed(1, "out", "bad thing").message == "bad thing"
    assert system.Completed(1, "out").message == "out"
    assert system.Completed(0).message == ""


def test_apply_result_reads_the_written_lines():
    result = system._apply_result(
        system.Completed(0, "wrote /etc/kidnix/parent.toml\nwrote /etc/kidnix/session.toml\n")
    )
    assert result.ok
    assert result.written == ("/etc/kidnix/parent.toml", "/etc/kidnix/session.toml")


def test_apply_result_names_a_dismissed_password_prompt():
    result = system._apply_result(system.Completed(126, "", ""))
    assert result.refused
    assert "did not get it" in result.message


def test_apply_result_passes_a_validation_message_through():
    result = system._apply_result(system.Completed(3, "", "error: time: nope"))
    assert not result.ok and not result.refused
    assert "nope" in result.message


def test_apply_settings_sends_the_payload_on_stdin():
    seen = {}

    def runner(argv, stdin=None, timeout=0):
        seen["argv"], seen["stdin"] = argv, stdin
        return system.Completed(0, "wrote /etc/kidnix/parent.toml\n")

    system.apply_settings({"schema": 1}, runner)
    assert seen["argv"] == [system.CONFIG_HELPER, "apply"]
    assert json.loads(seen["stdin"]) == {"schema": 1}


# --- system: the PIN ------------------------------------------------------


def test_set_pin_puts_both_pins_on_stdin_and_nothing_in_argv():
    seen = {}

    def runner(argv, stdin=None, timeout=0):
        seen["argv"], seen["stdin"] = argv, stdin
        return system.Completed(0)

    system.set_pin("2468", "1357", runner)
    assert seen["stdin"] == "2468\n1357\n"
    assert "2468" not in " ".join(seen["argv"])
    assert "1357" not in " ".join(seen["argv"])


def test_pin_messages_cover_the_documented_exit_codes():
    assert system.pin_message(system.Completed(0)) == ""
    assert "not the current PIN" in system.pin_message(system.Completed(3))
    assert "already has a PIN" in system.pin_message(system.Completed(4))
    assert system.pin_message(system.Completed(9, "", "odd")) == "odd"


def test_pin_message_never_repeats_a_digit():
    assert "1234" not in system.pin_message(system.Completed(3))


def test_pin_is_four_digits():
    assert system.pin_is_four_digits("0000")
    assert not system.pin_is_four_digits("123")
    assert not system.pin_is_four_digits("12a4")
    assert not system.pin_is_four_digits("١٢٣٤")


# --- system: bootc --------------------------------------------------------

STATUS = json.dumps(
    {
        "status": {
            "booted": {
                "image": {
                    "image": {"image": "ghcr.io/mattcree/kidnix:44"},
                    "imageDigest": "sha256:0123456789abcdefdeadbeef",
                },
                "version": "0.1.0",
            },
            "rollback": {"image": {"image": {"image": "ghcr.io/mattcree/kidnix:43"}}},
        }
    }
)


def test_parse_bootc_status():
    status = system.parse_bootc_status(STATUS)
    assert status.raw_ok
    assert status.booted_image == "ghcr.io/mattcree/kidnix:44"
    assert status.short_digest == "0123456789ab"
    assert status.can_roll_back


def test_parse_bootc_status_survives_a_schema_it_has_never_seen():
    status = system.parse_bootc_status('{"something": "else"}')
    assert status.raw_ok
    assert status.booted_image == ""
    assert not status.can_roll_back


def test_parse_bootc_status_on_rubbish_says_it_could_not_tell():
    assert not system.parse_bootc_status("not json").raw_ok


def test_a_machine_with_no_rollback_cannot_roll_back():
    status = system.parse_bootc_status(json.dumps({"status": {"booted": {}}}))
    assert not status.can_roll_back


def test_upgrade_check_no_changes():
    answer = system.parse_upgrade_check(system.Completed(0, "No changes in ghcr.io/...\n"))
    assert not answer.available and not answer.failed
    assert answer.sentence == "This machine is up to date."


def test_upgrade_check_something_waiting():
    answer = system.parse_upgrade_check(system.Completed(0, "Update available for ghcr.io/x\n"))
    assert answer.available
    assert "update waiting" in answer.sentence


def test_a_failed_check_is_not_reassurance():
    # A pull refused by the signature policy exits non-zero. Reporting that as
    # "up to date" would be the one lie this tab must not tell.
    answer = system.parse_upgrade_check(system.Completed(1, "", "Source image rejected"))
    assert answer.failed and not answer.available
    assert "could not check" in answer.sentence


# --- system: the signature policy ----------------------------------------

POLICY = json.dumps(
    {
        "default": [{"type": "insecureAcceptAnything"}],
        "transports": {
            "docker": {
                "ghcr.io/mattcree/kidnix": [
                    {
                        "type": "sigstoreSigned",
                        "keyPath": "/etc/pki/containers/kidnix.pub",
                        "signedIdentity": {"type": "matchRepository"},
                    }
                ],
                "ghcr.io/ublue-os": [{"type": "insecureAcceptAnything"}],
            }
        },
    }
)


def test_signature_policy_verifies_when_the_key_is_present():
    result = system.parse_signature_policy(POLICY, key_exists=lambda _p: True)
    assert result.verified
    assert result.key_path == "/etc/pki/containers/kidnix.pub"
    assert "refused" in result.sentence


def test_signature_policy_fails_closed_without_the_key():
    result = system.parse_signature_policy(POLICY, key_exists=lambda _p: False)
    assert not result.verified
    assert "not on this machine" in result.reason
    assert result.sentence.startswith("Updates are NOT verifiable")


def test_signature_policy_notices_an_uncovered_repository():
    result = system.parse_signature_policy(
        POLICY, repo="ghcr.io/somebody/else", key_exists=lambda _p: True
    )
    assert not result.verified
    assert "covers" in result.reason


def test_signature_policy_calls_accept_anything_unverified():
    policy = json.dumps(
        {
            "transports": {
                "docker": {"ghcr.io/mattcree/kidnix": [{"type": "insecureAcceptAnything"}]}
            }
        }
    )
    result = system.parse_signature_policy(policy, key_exists=lambda _p: True)
    assert not result.verified
    assert "without checking who signed" in result.reason


def test_signature_policy_on_rubbish():
    assert not system.parse_signature_policy("not json").verified


def test_the_most_precise_scope_wins():
    policy = json.dumps(
        {
            "transports": {
                "docker": {
                    "ghcr.io": [{"type": "insecureAcceptAnything"}],
                    "ghcr.io/mattcree/kidnix": [{"type": "sigstoreSigned", "keyPath": "/k.pub"}],
                }
            }
        }
    )
    result = system.parse_signature_policy(policy, key_exists=lambda _p: True)
    assert result.verified and result.scope == "ghcr.io/mattcree/kidnix"


def test_a_bare_registry_scope_still_covers_the_repository():
    policy = json.dumps(
        {"transports": {"docker": {"ghcr.io": [{"type": "sigstoreSigned", "keyPath": "/k.pub"}]}}}
    )
    assert system.parse_signature_policy(policy, key_exists=lambda _p: True).verified


# --- system: the helpers --------------------------------------------------


def test_export_passes_a_destination_through(tmp_path):
    seen = {}

    def runner(argv, stdin=None, timeout=0):
        seen["argv"] = argv
        return system.Completed(0, f"Saved to: {tmp_path}/kidnix-kid.tar.gz\n")

    system.export_to(tmp_path, runner)
    assert seen["argv"] == [system.EXPORT_HELPER, str(tmp_path)]


def test_export_with_no_destination_asks_for_none():
    seen = {}

    def runner(argv, stdin=None, timeout=0):
        seen["argv"] = argv
        return system.Completed(0)

    system.export_to(None, runner)
    assert seen["argv"] == [system.EXPORT_HELPER]


def test_wipe_passes_yes_because_the_panel_already_confirmed_twice():
    seen = {}

    def runner(argv, stdin=None, timeout=0):
        seen["argv"] = argv
        return system.Completed(0)

    system.wipe(runner)
    assert seen["argv"] == [system.WIPE_HELPER, "--yes"]


def test_run_reports_a_missing_binary_instead_of_raising():
    result = system.run(["/nonexistent/kidnix-nothing"])
    assert result.returncode == 127
    assert "not on this machine" in result.stderr


# --- running a helper without freezing the window -------------------------
#
# tasks.run_async needs GTK only for GLib, and its synchronous path needs
# nothing at all, so the half that matters is testable here.


def test_run_async_synchronous_calls_back_with_the_answer():
    from kidnix_parent_panel.ui import tasks

    seen = []
    tasks.run_async(lambda: "done", seen.append, synchronous=True)
    assert seen == ["done"]


def test_run_async_hands_an_exception_to_the_callback_rather_than_dying():
    from kidnix_parent_panel.ui import tasks

    def boom():
        raise RuntimeError("the helper blew up")

    seen = []
    tasks.run_async(boom, seen.append, synchronous=True)
    assert isinstance(seen[0], RuntimeError)
    assert "blew up" in str(seen[0])


def test_run_async_on_a_thread_eventually_answers():
    """The threaded path, driven by a real main loop.

    Without this the only thing proved about ``run_async`` is the branch the
    panel never takes in normal use.
    """
    import pytest

    gi = pytest.importorskip("gi")
    gi.require_version("Gtk", "4.0")
    from gi.repository import GLib

    from kidnix_parent_panel.ui import tasks

    loop = GLib.MainLoop()
    seen = []

    def done(result):
        seen.append(result)
        loop.quit()

    GLib.timeout_add(5000, loop.quit)  # never hang a test suite
    tasks.run_async(lambda: 41 + 1, done)
    loop.run()
    assert seen == [42]


# --- family photographs the CHILD can open ---------------------------------
#
# The bug: the Family tab stored the path the file chooser returned, which is
# nearly always under /var/home/parent -- 0700 parent:parent, so `kid` cannot
# even stat it. `Recipient.photo_path` caught the PermissionError, answered
# None, and the Letters activity drew its placeholder face. A grown-up who had
# chosen four photographs saw four identical drawn faces and nothing anywhere
# said why.


def a_picture(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 32)
    return path


def test_a_chosen_photograph_is_copied_where_the_child_can_read_it(tmp_path):
    store = tmp_path / "photos"
    store.mkdir()
    source = a_picture(tmp_path / "parent-home" / "granny.png")

    result = system.install_photo(str(source), "granny", store)

    assert result.ok
    assert result.path == str(store / "granny.png")
    assert (store / "granny.png").read_bytes() == source.read_bytes()
    assert (store / "granny.png").stat().st_mode & 0o777 == 0o644
    # The original is not moved, renamed or touched.
    assert source.is_file()


def test_applying_twice_leaves_the_copy_exactly_where_it_is(tmp_path):
    store = tmp_path / "photos"
    store.mkdir()
    a_picture(store / "granny.png")
    result = system.install_photo(str(store / "granny.png"), "granny", store)
    assert result.ok
    assert result.path == str(store / "granny.png")


def test_changing_the_kind_of_picture_does_not_leave_the_old_one_behind(tmp_path):
    store = tmp_path / "photos"
    store.mkdir()
    a_picture(store / "granny.png")
    source = a_picture(tmp_path / "elsewhere" / "new.jpg")

    result = system.install_photo(str(source), "granny", store)

    assert result.path == str(store / "granny.jpg")
    assert not (store / "granny.png").exists()


def test_a_photograph_that_is_gone_clears_the_path_and_says_so(tmp_path):
    """The honest answer. A stored path that resolves to nothing is exactly
    the state that produced four identical drawn faces and no explanation."""
    store = tmp_path / "photos"
    store.mkdir()
    result = system.install_photo(str(tmp_path / "never-existed.png"), "granny", store)
    assert result.path == ""
    assert not result.ok
    assert "could not be read" in result.message


def test_a_file_that_is_not_a_picture_is_refused_by_name(tmp_path):
    store = tmp_path / "photos"
    store.mkdir()
    source = tmp_path / "granny.pdf"
    source.write_bytes(b"%PDF")
    result = system.install_photo(str(source), "granny", store)
    assert result.path == ""
    assert "not a kind of picture" in result.message


def test_no_photograph_at_all_is_not_a_problem(tmp_path):
    result = system.install_photo("", "granny", tmp_path / "photos")
    assert result.ok
    assert result.path == ""


def test_without_the_store_the_path_is_kept_and_the_parent_is_warned(tmp_path):
    """A developer's laptop has no /var/lib/kidnix. Losing the path a parent
    chose would be worse than keeping one that does not resolve there."""
    source = a_picture(tmp_path / "granny.png")
    result = system.install_photo(str(source), "granny", tmp_path / "nowhere")
    assert result.path == str(source)
    assert "is not on this machine" in result.message


def test_install_photos_rewrites_the_list_and_collects_the_sentences(tmp_path):
    from kidnix_parent_panel import model as M

    store = tmp_path / "photos"
    store.mkdir()
    here = a_picture(tmp_path / "src" / "granny.png")
    family = [
        M.Recipient(id="granny", name="Granny", photo=str(here)),
        M.Recipient(id="grandad", name="Grandad", photo=str(tmp_path / "gone.png")),
        M.Recipient(id="auntie", name="Auntie Jo"),
    ]

    out, messages = system.install_photos(family, store)

    assert out[0].photo == str(store / "granny.png")
    assert out[1].photo == ""
    assert out[2].photo == ""
    assert len(messages) == 1
    assert messages[0].startswith("Grandad: ")


def test_a_copy_that_fails_is_reported_and_not_stored(tmp_path):
    store = tmp_path / "photos"
    store.mkdir()
    source = a_picture(tmp_path / "granny.png")

    def refuse(_src, _dst):
        raise OSError(13, "Permission denied")

    result = system.install_photo(str(source), "granny", store, copy=refuse)
    assert result.path == ""
    assert "could not be copied" in result.message


def test_apply_copies_the_photographs_before_it_writes_anything(tmp_path):
    """End to end through `PanelState.save`, which is where it has to happen:
    the *panel* copies, as the grown-up who chose the file. A root helper asked
    to copy a caller-named path into a world-readable directory would copy
    anything the caller could name and could not read."""
    from kidnix_parent_panel import model as M
    from kidnix_parent_panel.ui.state import PanelState

    store = tmp_path / "photos"
    store.mkdir()
    source = a_picture(tmp_path / "parent-home" / "granny.png")

    panel = M.PanelModel()
    panel.add_child("Rosie")
    granny = panel.add_recipient("Granny")
    panel.family[0] = replace(granny, photo=str(source))

    seen = {}

    def runner(argv, stdin=None, timeout=0):
        seen["stdin"] = stdin
        return system.Completed(0, "wrote /etc/kidnix/parent.toml\n")

    state = PanelState(
        panel=panel,
        activities=catalogue.Catalogue(),
        runner=runner,
        etc=tmp_path,
        usr=tmp_path,
        synchronous=True,
        photo_dir=store,
    )
    result = state.save()

    assert result.ok
    assert (store / "granny.png").is_file()
    assert str(store / "granny.png") in seen["stdin"]
    assert str(source) not in seen["stdin"]
    assert state.panel.family[0].photo == str(store / "granny.png")


def test_a_photograph_that_could_not_be_copied_is_said_out_loud_after_a_save(tmp_path):
    from kidnix_parent_panel import model as M
    from kidnix_parent_panel.ui.state import PanelState

    store = tmp_path / "photos"
    store.mkdir()
    panel = M.PanelModel()
    panel.add_child("Rosie")
    granny = panel.add_recipient("Granny")
    panel.family[0] = replace(granny, photo=str(tmp_path / "gone.png"))

    state = PanelState(
        panel=panel,
        activities=catalogue.Catalogue(),
        runner=lambda *a, **k: system.Completed(0, "wrote /etc/kidnix/parent.toml\n"),
        etc=tmp_path,
        usr=tmp_path,
        synchronous=True,
        photo_dir=store,
    )
    result = state.save()
    assert result.ok
    assert "Granny:" in result.message
