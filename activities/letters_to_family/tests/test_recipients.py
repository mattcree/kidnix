"""Who a letter may go to, read out of the grown-up's own file.

The rules being pinned: the schema is the parent panel's, the order is the
file's, a missing photo is normal rather than an error, and **nothing here ever
raises** -- a five-year-old told the computer is broken because a grown-up
mistyped a TOML key has been failed twice.
"""

from __future__ import annotations

import tomllib

from letters_to_family.recipients import (
    CONFIG_NAME,
    Recipient,
    by_id,
    config_candidates,
    load_recipients,
    recipients_from_document,
    slugify,
)

FAMILY = """
[[family]]
id = "grandad"
name = "Grandad"
relation = "Grandpa"
photo = "{photo}"

[[family]]
id = "nanna-jean"
name = "Nanna Jean"
relation = "Grandma"
photo = ""
"""


def write_parent_toml(directory, body: str):
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / CONFIG_NAME
    path.write_text(body)
    return path


def test_the_family_blocks_are_read_in_the_panels_own_schema(tmp_path):
    photo = tmp_path / "grandad.jpg"
    photo.write_bytes(b"not really a jpeg")
    write_parent_toml(tmp_path / "etc", FAMILY.format(photo=photo))

    people = load_recipients([tmp_path / "etc"])

    assert [person.id for person in people] == ["grandad", "nanna-jean"]
    assert people[0].name == "Grandad"
    assert people[0].relation == "Grandpa"
    assert people[0].photo_path == photo


def test_the_order_is_the_file_s_order_and_is_never_re_sorted(tmp_path):
    """B1: a pre-reader navigates by position, so Nanna does not move."""
    write_parent_toml(
        tmp_path,
        '[[family]]\nname = "Zoe"\n\n[[family]]\nname = "Alan"\n',
    )
    assert [p.name for p in load_recipients([tmp_path])] == ["Zoe", "Alan"]


def test_a_recipient_with_no_photo_key_gets_a_placeholder_not_an_error(tmp_path):
    write_parent_toml(tmp_path, '[[family]]\nname = "Grandad"\n')
    person = load_recipients([tmp_path])[0]
    assert person.photo == ""
    assert person.photo_path is None
    assert person.has_photo is False


def test_a_photo_path_that_is_not_there_is_the_same_as_no_photo(tmp_path):
    """A photo on a USB stick that has been unplugged. Not an error."""
    write_parent_toml(
        tmp_path, '[[family]]\nname = "Grandad"\nphoto = "/nowhere/at/all/grandad.jpg"\n'
    )
    person = load_recipients([tmp_path])[0]
    assert person.photo_path is None
    assert person.has_photo is False


def test_a_photo_that_is_a_directory_is_not_a_photo(tmp_path):
    folder = tmp_path / "pictures"
    folder.mkdir()
    write_parent_toml(tmp_path, f'[[family]]\nname = "Grandad"\nphoto = "{folder}"\n')
    assert load_recipients([tmp_path])[0].photo_path is None


def test_no_family_blocks_at_all_is_an_empty_list_and_no_exception(tmp_path):
    write_parent_toml(tmp_path, 'pin_salt = "abc"\n')
    assert load_recipients([tmp_path]) == []


def test_a_missing_parent_toml_is_an_empty_list(tmp_path):
    assert load_recipients([tmp_path / "nothing-here"]) == []


def test_a_malformed_parent_toml_is_an_empty_list_and_no_exception(tmp_path):
    write_parent_toml(tmp_path, "[[family]\nname = ")
    assert load_recipients([tmp_path]) == []


def test_etc_wins_over_usr_share(tmp_path):
    """The same rule the shell uses: /etc is the machine's, /usr/share is ours."""
    write_parent_toml(tmp_path / "etc", '[[family]]\nname = "Grandad"\n')
    write_parent_toml(tmp_path / "usr", '[[family]]\nname = "Nobody"\n')
    people = load_recipients([tmp_path / "etc", tmp_path / "usr"])
    assert [p.name for p in people] == ["Grandad"]


def test_usr_share_is_the_fallback_when_etc_has_no_file(tmp_path):
    (tmp_path / "etc").mkdir()
    write_parent_toml(tmp_path / "usr", '[[family]]\nname = "Grandad"\n')
    assert [p.name for p in load_recipients([tmp_path / "etc", tmp_path / "usr"])] == ["Grandad"]


def test_an_entry_with_no_name_is_skipped_because_it_cannot_be_announced():
    document = tomllib.loads('[[family]]\nid = "x"\n\n[[family]]\nname = "Grandad"\n')
    assert [p.name for p in recipients_from_document(document)] == ["Grandad"]


def test_a_missing_id_falls_back_to_a_slug_of_the_name():
    document = tomllib.loads('[[family]]\nname = "Nanna Jean"\n')
    assert recipients_from_document(document)[0].id == "nanna-jean"


def test_two_entries_with_the_same_id_keep_only_the_first():
    document = tomllib.loads(
        '[[family]]\nid = "g"\nname = "Grandad"\n\n[[family]]\nid = "g"\nname = "Other"\n'
    )
    assert [p.name for p in recipients_from_document(document)] == ["Grandad"]


def test_family_that_is_not_a_list_of_tables_is_ignored():
    assert recipients_from_document({"family": "grandad"}) == []
    assert recipients_from_document({"family": [1, 2, 3]}) == []


def test_the_tile_says_the_name_and_only_the_name():
    """B5's ceiling is two sentences; this is one word, and it is the word a
    child uses for the person. The relation is a grown-up's note in the panel."""
    person = Recipient(id="grandad", name="Grandad", relation="Grandpa")
    assert person.speak_text == "Grandad"
    assert "Grandpa" not in person.speak_text


def test_a_recipient_carries_no_address_of_any_kind():
    """SYNTHESIS H1: the letter never leaves the machine by itself. An address
    field here would be the first half of a feature this product does not have,
    sitting in a file a child can read."""
    fields = set(Recipient.__dataclass_fields__)
    assert fields == {"id", "name", "relation", "photo"}
    for banned in ("email", "address", "phone", "handle", "url"):
        assert banned not in fields


def test_slugify_makes_a_directory_name_out_of_anything():
    assert slugify("Nanna Jean") == "nanna-jean"
    assert slugify("  Grandad!!  ") == "grandad"
    assert slugify("???") == "someone"
    assert slugify("") == "someone"


def test_by_id_finds_one_and_says_nothing_when_there_is_no_such_person():
    people = [Recipient(id="a", name="A"), Recipient(id="b", name="B")]
    assert by_id(people, "b").name == "B"
    assert by_id(people, "c") is None


def test_the_search_path_looks_at_parent_toml_in_each_root():
    from pathlib import Path

    assert config_candidates([Path("/etc/kidnix")]) == [Path("/etc/kidnix/parent.toml")]
