
import pytest


# --------------------------------------------------
# EXISTING FILE MANAGEMENT TESTS
# --------------------------------------------------

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
        manager.rename_file("/first.txt", "/second.txt")

    assert manager.read_file("/first.txt") == "First"
    assert manager.read_file("/second.txt") == "Second"


def test_rename_rejects_missing_source(manager):
    with pytest.raises(KeyError):
        manager.rename_file("/missing.txt", "/new.txt")


def test_rename_rejects_missing_destination_directory(manager):
    manager.create_file("/notes.txt", "Notes")

    with pytest.raises(ValueError):
        manager.rename_file(
            "/notes.txt",
            "/missing/notes.txt"
        )

    assert manager.read_file("/notes.txt") == "Notes"


# --------------------------------------------------
# REVISION 3: DIRECTORY MANAGEMENT TESTS
# --------------------------------------------------

def test_rename_directory_preserves_files_and_blocks(manager, disk):
    manager.create_directory("/old")
    manager.create_file("/old/notes.txt", "Important notes")

    original_blocks = manager.entries["/old/notes.txt"]["blocks"].copy()

    result = manager.rename_directory("/old", "/new")

    assert result["new_path"] == "/new"
    assert manager.read_file("/new/notes.txt") == "Important notes"
    assert manager.entries["/new/notes.txt"]["blocks"] == original_blocks
    assert "/old" not in manager.directories


def test_rename_directory_preserves_nested_directories(manager):
    manager.create_directory("/old/projects")
    manager.create_file("/old/projects/task.txt", "Complete task")

    manager.rename_directory("/old", "/new")

    assert "/new" in manager.directories
    assert "/new/projects" in manager.directories
    assert manager.read_file("/new/projects/task.txt") == "Complete task"


def test_move_directory_to_another_directory(manager):
    manager.create_directory("/source")
    manager.create_directory("/destination")
    manager.create_file("/source/data.txt", "Sample data")

    manager.rename_directory(
        "/source",
        "/destination/source"
    )

    assert manager.read_file(
        "/destination/source/data.txt"
    ) == "Sample data"

    assert "/destination/source" in manager.directories
    assert "/source" not in manager.directories


def test_directory_cannot_be_moved_inside_itself(manager):
    manager.create_directory("/parent/child")

    with pytest.raises(ValueError):
        manager.rename_directory(
            "/parent",
            "/parent/child/new"
        )


def test_delete_empty_directory(manager):
    manager.create_directory("/temporary")

    manager.delete_directory("/temporary")

    assert "/temporary" not in manager.directories


def test_delete_nonempty_directory_is_rejected(manager):
    manager.create_directory("/documents")
    manager.create_file("/documents/notes.txt", "Keep this file")

    with pytest.raises(ValueError):
        manager.delete_directory("/documents")

    assert manager.read_file("/documents/notes.txt") == "Keep this file"
