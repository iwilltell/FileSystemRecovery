import pytest
from modules.disk_manager import DiskManager

def test_initial_status(disk):
    assert disk.status()["free_blocks"] == 16
    assert disk.status()["used_blocks"] == 0

def test_allocate_and_release(disk):
    blocks = disk.allocate(3)
    assert blocks == [0, 1, 2]
    assert disk.status()["used_blocks"] == 3
    disk.release([0, 2])
    assert disk.status()["used_blocks"] == 1

def test_allocation_rejects_invalid_count(disk):
    for count in (0, -1, 1.5, True):
        with pytest.raises(ValueError):
            disk.allocate(count)

def test_allocation_is_atomic_when_full(disk):
    with pytest.raises(RuntimeError):
        disk.allocate(17)
    assert disk.status()["used_blocks"] == 0

def test_release_rejects_invalid_or_free_block(disk):
    with pytest.raises(ValueError):
        disk.release([20])
    with pytest.raises(ValueError):
        disk.release([0])

def test_persistence(tmp_path):
    path = tmp_path / "disk.json"
    first = DiskManager(path, total_blocks=8)
    first.allocate(2)
    second = DiskManager(path, total_blocks=8)
    assert second.status()["used_blocks"] == 2
