"""Persistent simulated disk using a bitmap free-space map."""
import json
import os
import tempfile
from pathlib import Path


class DiskManager:
    def __init__(self, path, total_blocks=128, block_size=64):
        if total_blocks <= 0 or block_size <= 0:
            raise ValueError("Disk dimensions must be positive")
        self.path = Path(path)
        self.total_blocks = total_blocks
        self.block_size = block_size
        self.bitmap = [0] * total_blocks
        self.files = {}
        self.directories = ["/"]
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._load()

    def _load(self):
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                if data.get("total_blocks") != self.total_blocks:
                    raise ValueError("Stored disk capacity does not match configuration")
                bitmap = data["bitmap"]
                if len(bitmap) != self.total_blocks or any(v not in (0, 1) for v in bitmap):
                    raise ValueError("Disk bitmap is corrupt")
                self.bitmap = bitmap
                self.files = data.get("files", {})
                self.directories = data.get("directories", ["/"])
            except (json.JSONDecodeError, KeyError) as exc:
                raise ValueError(f"Cannot load simulated disk: {exc}") from exc
        else:
            self._save()

    def _save(self):
        payload = {
            "total_blocks": self.total_blocks,
            "block_size": self.block_size,
            "bitmap": self.bitmap,
            "files": self.files,
            "directories": self.directories,
        }
        fd, temp_name = tempfile.mkstemp(dir=str(self.path.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, self.path)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)

    def allocate(self, count):
        if not isinstance(count, int) or isinstance(count, bool) or count <= 0:
            raise ValueError("Allocation count must be a positive integer")
        free = [i for i, value in enumerate(self.bitmap) if value == 0]
        if len(free) < count:
            raise RuntimeError("Not enough free disk blocks")
        chosen = free[:count]
        for index in chosen:
            self.bitmap[index] = 1
        self._save()
        return chosen

    def release(self, block_indexes):
        indexes = list(block_indexes)
        if len(indexes) != len(set(indexes)):
            raise ValueError("Duplicate block indexes are not allowed")
        for index in indexes:
            if not isinstance(index, int) or isinstance(index, bool):
                raise ValueError("Block indexes must be integers")
            if index < 0 or index >= self.total_blocks:
                raise ValueError(f"Invalid block index: {index}")
            if self.bitmap[index] != 1:
                raise ValueError(f"Block {index} is not allocated")
        for index in indexes:
            self.bitmap[index] = 0
        self._save()

    def status(self):
        used = sum(self.bitmap)
        free = self.total_blocks - used
        return {
            "total_blocks": self.total_blocks,
            "used_blocks": used,
            "free_blocks": free,
            "usage_percent": round(used / self.total_blocks * 100, 1),
            "block_size": self.block_size,
            "capacity_bytes": self.total_blocks * self.block_size,
            "used_bytes": used * self.block_size,
        }
