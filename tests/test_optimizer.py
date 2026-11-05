
import pytest

from modules.optimizer import Optimizer


# --------------------------------------------------
# EXISTING OPTIMIZATION TESTS
# --------------------------------------------------

def test_optimizer_preserves_files_and_compacts(disk, manager):
    manager.create_file("/a.txt", "a")
    manager.create_file("/b.txt", "b")
    manager.create_file("/c.txt", "c")

    manager.delete_file("/b.txt")

    before_a = manager.read_file("/a.txt")
    before_c = manager.read_file("/c.txt")

    optimizer = Optimizer(disk, manager)
    result = optimizer.optimize()

    assert result["message"].startswith("Compaction completed")
    assert manager.read_file("/a.txt") == before_a
    assert manager.read_file("/c.txt") == before_c
    assert disk.bitmap == [1, 1] + [0] * 14


def test_benchmark_returns_metrics(disk, manager):
    manager.create_file("/bench.txt", "sample")

    optimizer = Optimizer(disk, manager)
    report = optimizer.benchmark()

    assert report["files_tested"] == 1
    assert report["average_read_ms"] >= 0
    assert report["average_write_ms"] >= 0


# --------------------------------------------------
# REVISION 6: OPTIMIZATION ENHANCEMENT TESTS
# --------------------------------------------------

def test_analyze_returns_fragmentation_details(disk, manager):
    manager.create_file("/first.txt", "first")
    manager.create_file("/second.txt", "second")

    optimizer = Optimizer(disk, manager)
    report = optimizer.analyze()

    assert report["total_blocks"] == disk.total_blocks
    assert report["allocated_blocks"] == 2
    assert report["free_blocks"] == disk.total_blocks - 2
    assert len(report["file_details"]) == 2


def test_analyze_identifies_fragmented_file(disk, manager):
    manager.create_file("/first.txt", "a")
    manager.create_file("/temporary.txt", "b")
    manager.create_file("/last.txt", "c")

    manager.delete_file("/temporary.txt")

    # Create a file using blocks separated by a free block.
    manager.entries["/first.txt"]["blocks"] = [0, 2]
    manager.entries["/last.txt"]["blocks"] = [1]

    disk.bitmap = [1, 1, 1] + [0] * (
        disk.total_blocks - 3
    )

    optimizer = Optimizer(disk, manager)
    report = optimizer.analyze()

    first_file = next(
        item for item in report["file_details"]
        if item["path"] == "/first.txt"
    )

    assert first_file["is_contiguous"] is False
    assert first_file["fragmentation_runs"] == 2
    assert report["fragmented_files"] == 1


def test_integrity_validation_passes(disk, manager):
    manager.create_file("/valid.txt", "hello")

    optimizer = Optimizer(disk, manager)
    result = optimizer._validate_layout()

    assert result["valid"] is True
    assert result["files_checked"] == 1
    assert result["blocks_checked"] == 1


def test_integrity_validation_detects_duplicate_blocks(disk, manager):
    manager.create_file("/first.txt", "a")
    manager.create_file("/second.txt", "b")

    manager.entries["/second.txt"]["blocks"] = (
        manager.entries["/first.txt"]["blocks"].copy()
    )

    optimizer = Optimizer(disk, manager)

    with pytest.raises(ValueError, match="Duplicate block"):
        optimizer._validate_layout()


def test_integrity_validation_detects_bitmap_mismatch(disk, manager):
    manager.create_file("/test.txt", "hello")

    disk.bitmap = [0] * disk.total_blocks

    optimizer = Optimizer(disk, manager)

    with pytest.raises(ValueError, match="bitmap"):
        optimizer._validate_layout()


def test_compaction_preserves_allocation_integrity(disk, manager):
    manager.create_file("/first.txt", "one")
    manager.create_file("/temporary.txt", "two")
    manager.create_file("/last.txt", "three")

    manager.delete_file("/temporary.txt")

    optimizer = Optimizer(disk, manager)
    result = optimizer.optimize()

    assert result["integrity_before"]["valid"] is True
    assert result["integrity_after"]["valid"] is True
    assert optimizer._validate_layout()["valid"] is True


def test_compaction_preserves_file_metadata(disk, manager):
    manager.create_file("/notes.txt", "Important notes")

    original = manager.entries["/notes.txt"].copy()

    optimizer = Optimizer(disk, manager)
    optimizer.optimize()

    updated = manager.entries["/notes.txt"]

    assert updated["content"] == original["content"]
    assert updated["size"] == original["size"]
    assert updated["created_at"] == original["created_at"]
    assert updated["modified_at"] == original["modified_at"]


def test_optimization_history_records_runs(disk, manager):
    manager.create_file("/history.txt", "history")

    optimizer = Optimizer(disk, manager)

    optimizer.optimize()
    optimizer.optimize()

    history = optimizer.get_history()

    assert len(history) == 2
    assert history[0]["files_optimized"] == 1
    assert history[1]["files_optimized"] == 1


def test_empty_disk_benchmark_returns_zero_metrics(disk, manager):
    optimizer = Optimizer(disk, manager)

    report = optimizer.benchmark()

    assert report["files_tested"] == 0
    assert report["average_read_ms"] == 0
    assert report["average_write_ms"] == 0
    assert report["samples"] == []


def test_empty_disk_can_be_optimized(disk, manager):
    optimizer = Optimizer(disk, manager)

    result = optimizer.optimize()

    assert result["files_optimized"] == 0
    assert result["integrity_after"]["valid"] is True
    assert disk.bitmap == [0] * disk.total_blocks
