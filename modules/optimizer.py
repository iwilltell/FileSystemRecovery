"""Fragmentation analysis, compaction and simple read/write benchmarks."""
import time
from modules.file_manager import FileManager


class Optimizer:
    def __init__(self, disk, file_manager):
        self.disk = disk
        self.file_manager = file_manager

    def analyze(self):
        bitmap = self.disk.bitmap
        free_runs = 0
        in_free_run = False
        for bit in bitmap:
            if bit == 0 and not in_free_run:
                free_runs += 1
                in_free_run = True
            elif bit == 1:
                in_free_run = False
        allocated = [i for i, bit in enumerate(bitmap) if bit]
        contiguous = bool(allocated) and allocated == list(range(allocated[0], allocated[0] + len(allocated)))
        return {
            "free_blocks": bitmap.count(0),
            "free_space_runs": free_runs,
            "allocated_blocks": len(allocated),
            "allocated_contiguous": contiguous,
            "fragmentation_indicator": max(0, free_runs - 1)
        }

    def optimize(self):
        before = self.analyze()
        cursor = 0
        for path in sorted(self.file_manager.entries):
            entry = self.file_manager.entries[path]
            count = len(entry["blocks"])
            new_blocks = list(range(cursor, cursor + count))
            entry["blocks"] = new_blocks
            cursor += count
        self.disk.bitmap = [1 if i < cursor else 0 for i in range(self.disk.total_blocks)]
        self.disk._save()
        after = self.analyze()
        return {"before": before, "after": after,
                "message": "Compaction completed; file contents and metadata were preserved."}

    def benchmark(self):
        samples = []
        for path in sorted(self.file_manager.entries):
            start = time.perf_counter()
            self.file_manager.read_file(path)
            read_ms = (time.perf_counter() - start) * 1000
            start = time.perf_counter()
            self.file_manager.write_file(path, self.file_manager.read_file(path))
            write_ms = (time.perf_counter() - start) * 1000
            samples.append({"path": path, "read_ms": round(read_ms, 4),
                            "write_ms": round(write_ms, 4)})
        count = len(samples) or 1
        return {
            "files_tested": len(samples),
            "average_read_ms": round(sum(x["read_ms"] for x in samples) / count, 4),
            "average_write_ms": round(sum(x["write_ms"] for x in samples) / count, 4),
            "samples": samples
        }
