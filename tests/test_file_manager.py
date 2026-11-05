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
