
"""Fragmentation analysis, safe compaction and read/write benchmarks."""

import time


class Optimizer:
    def __init__(self, disk, file_manager):
        self.disk = disk
        self.file_manager = file_manager
        self.history = []

    def _validate_layout(self):
        """Check that file block references and the disk bitmap agree."""

        bitmap = self.disk.bitmap
        total_blocks = self.disk.total_blocks

        if len(bitmap) != total_blocks:
            raise ValueError("Disk bitmap size does not match disk capacity")

        referenced_blocks = []

        for path, entry in self.file_manager.entries.items():
            blocks = entry.get("blocks", [])

            if not isinstance(blocks, list):
                raise ValueError(f"Invalid block list for {path}")

            if not blocks:
                raise ValueError(f"File has no allocated blocks: {path}")

            for block in blocks:
                if not isinstance(block, int) or isinstance(block, bool):
                    raise ValueError(f"Invalid block index in {path}")

                if block < 0 or block >= total_blocks:
                    raise ValueError(f"Block index out of range in {path}")

                referenced_blocks.append(block)

        if len(referenced_blocks) != len(set(referenced_blocks)):
            raise ValueError("Duplicate block references detected")

        expected_bitmap = [0] * total_blocks

        for block in referenced_blocks:
            expected_bitmap[block] = 1

        if bitmap != expected_bitmap:
            raise ValueError(
                "Disk bitmap does not match file block references"
            )

        return {
            "valid": True,
            "files_checked": len(self.file_manager.entries),
            "blocks_checked": len(referenced_blocks)
        }

    @staticmethod
    def _count_runs(blocks):
        """Count groups of consecutive block numbers."""

        if not blocks:
            return 0

        ordered = sorted(blocks)
        runs = 1

        for index in range(1, len(ordered)):
            if ordered[index] != ordered[index - 1] + 1:
                runs += 1

        return runs

    def analyze(self):
        """Analyse free space, allocated space and file fragmentation."""

        bitmap = self.disk.bitmap

        free_blocks = [
            index for index, bit in enumerate(bitmap) if bit == 0
        ]

        allocated_blocks = [
            index for index, bit in enumerate(bitmap) if bit == 1
        ]

        file_details = []

        for path in sorted(self.file_manager.entries):
            blocks = self.file_manager.entries[path]["blocks"]
            runs = self._count_runs(blocks)

            file_details.append({
                "path": path,
                "block_count": len(blocks),
                "fragmentation_runs": runs,
                "is_contiguous": runs <= 1
            })

        free_runs = self._count_runs(free_blocks)
        allocated_runs = self._count_runs(allocated_blocks)

        fragmented_files = sum(
            1 for item in file_details
            if not item["is_contiguous"]
        )

        return {
            "total_blocks": self.disk.total_blocks,
            "free_blocks": len(free_blocks),
            "free_space_runs": free_runs,
            "allocated_blocks": len(allocated_blocks),
            "allocated_space_runs": allocated_runs,
            "allocated_contiguous": allocated_runs <= 1,
            "fragmented_files": fragmented_files,
            "file_details": file_details,
            "fragmentation_indicator": max(0, free_runs - 1)
        }

    def optimize(self):
        """Compact allocated blocks safely and preserve file metadata."""

        integrity_before = self._validate_layout()
        before = self.analyze()

        original_bitmap = self.disk.bitmap.copy()

        original_blocks = {
            path: entry["blocks"].copy()
            for path, entry in self.file_manager.entries.items()
        }

        cursor = 0

        try:
            for path in sorted(self.file_manager.entries):
                entry = self.file_manager.entries[path]
                count = len(entry["blocks"])

                entry["blocks"] = list(range(cursor, cursor + count))
                cursor += count

            if cursor > self.disk.total_blocks:
                raise ValueError("Compaction exceeds available disk capacity")

            self.disk.bitmap = [
                1 if index < cursor else 0
                for index in range(self.disk.total_blocks)
            ]

            integrity_after = self._validate_layout()

            self.disk._save()

        except Exception:
            for path, blocks in original_blocks.items():
                self.file_manager.entries[path]["blocks"] = blocks

            self.disk.bitmap = original_bitmap
            self.disk._save()
            raise

        after = self.analyze()

        result = {
            "before": before,
            "after": after,
            "integrity_before": integrity_before,
            "integrity_after": integrity_after,
            "blocks_reorganized": cursor,
            "files_optimized": len(original_blocks),
            "history_number": len(self.history) + 1,
            "message": (
                "Compaction completed successfully. "
                "File contents and metadata were preserved."
            )
        }

        self.history.append({
            "timestamp": time.time(),
            "files_optimized": len(original_blocks),
            "blocks_reorganized": cursor,
            "fragmentation_before": before["fragmentation_indicator"],
            "fragmentation_after": after["fragmentation_indicator"]
        })

        return result

    def get_history(self):
        """Return optimization runs recorded during this app session."""

        return self.history.copy()

    def benchmark(self):
        """Measure simulated file read and write operation times."""

        samples = []

        for path in sorted(self.file_manager.entries):
            start = time.perf_counter()
            content = self.file_manager.read_file(path)
            read_ms = (time.perf_counter() - start) * 1000

            start = time.perf_counter()
            self.file_manager.write_file(path, content)
            write_ms = (time.perf_counter() - start) * 1000

            samples.append({
                "path": path,
                "read_ms": round(read_ms, 4),
                "write_ms": round(write_ms, 4)
            })

        count = len(samples)

        average_read = (
            sum(item["read_ms"] for item in samples) / count
            if count else 0
        )

        average_write = (
            sum(item["write_ms"] for item in samples) / count
            if count else 0
        )

        return {
            "files_tested": count,
            "average_read_ms": round(average_read, 4),
            "average_write_ms": round(average_write, 4),
            "samples": samples
        }
