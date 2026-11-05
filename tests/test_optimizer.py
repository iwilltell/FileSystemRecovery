def test_optimizer_preserves_files_and_compacts(disk, manager):
    manager.create_file("/a.txt", "a")
    manager.create_file("/b.txt", "b")
    manager.create_file("/c.txt", "c")
    manager.delete_file("/b.txt")
    before_a = manager.read_file("/a.txt")
    before_c = manager.read_file("/c.txt")
    from modules.optimizer import Optimizer
    result = Optimizer(disk, manager).optimize()
    assert result["message"].startswith("Compaction completed")
    assert manager.read_file("/a.txt") == before_a
    assert manager.read_file("/c.txt") == before_c
    assert disk.bitmap == [1, 1] + [0] * 14

def test_benchmark_returns_metrics(disk, manager):
    manager.create_file("/bench.txt", "sample")
    from modules.optimizer import Optimizer
    report = Optimizer(disk, manager).benchmark()
    assert report["files_tested"] == 1
    assert report["average_read_ms"] >= 0
