
import pytest


def test_create_read_delete(manager, disk):
    manager.create_file("/hello.txt", "hello world")

    assert manager.read_file("/hello.txt") == "hello world"
    assert disk.status()["used_blocks"] == 2

    manager.delete_file("/hello.txt")

    assert disk.status()["used_blocks"] == 0


def test_directory_and_nested_file(manager):
    manager.create_directory("/docs/projects")
    manager.create_file("/docs/projects/notes.txt", "abc")

    assert manager.read_file("/docs/projects/notes.txt") == "abc"


def test_missing_parent_and_duplicate(manager):
    with pytest.raises(ValueError):
        manager.create_file("/missing/a.txt", "x")

    manager.create_file("/a.txt", "x")

    with pytest.raises(ValueError):
        manager.create_file("/a.txt", "again")


def test_write_grows_and_shrinks(manager, disk):
    manager.create_file("/edit.txt", "a")

    manager.write_file("/edit.txt", "abcdefghijklmnop")

    assert disk.status()["used_blocks"] == 2

    manager.write_file("/edit.txt", "z")

    assert disk.status()["used_blocks"] == 1


# --------------------------------------------------
# REVISION 2: FILE RENAME AND MOVE TESTS
# --------------------------------------------------


def test_rename_file_preserves_content_and_blocks(manager, disk):
    manager.create_file("/old.txt", "Hello!")

    original_blocks = manager.entries["/old.txt"]["blocks"].copy()
    used_before = disk.status()["used_blocks"]

    result = manager.rename_file("/old.txt", "/new.txt")

    assert result["path"] == "/new.txt"
    assert manager.read_file("/new.txt") == "Hello!"
    assert manager.entries["/new.txt"]["blocks"] == original_blocks
    assert disk.status()["used_blocks"] == used_before
    assert "/old.txt" not in manager.entries


def test_move_file_to_another_directory(manager):
    manager.create_directory("/documents")
    manager.create_file("/notes.txt", "My notes")

    manager.rename_file(
        "/notes.txt",
        "/documents/notes.txt"
    )

    assert manager.read_file("/documents/notes.txt") == "My notes"

    with pytest.raises(KeyError):
        manager.read_file("/notes.txt")


def test_rename_rejects_existing_destination(manager):
    manager.create_file("/first.txt", "First")
    manager.create_file("/second.txt", "Second")

    with pytest.raises(ValueError):
        manager.rename_file(
            "/first.txt",
            "/second.txt"
        )

    assert manager.read_file("/first.txt") == "First"
    assert manager.read_file("/second.txt") == "Second"


def test_rename_rejects_missing_source(manager):
    with pytest.raises(KeyError):
        manager.rename_file(
            "/missing.txt",
            "/new.txt"
        )


def test_rename_rejects_missing_destination_directory(manager):
    manager.create_file("/notes.txt", "Notes")

    with pytest.raises(ValueError):
        manager.rename_file(
            "/notes.txt",
            "/missing/notes.txt"
        )

    assert manager.read_file("/notes.txt") == "Notes"
