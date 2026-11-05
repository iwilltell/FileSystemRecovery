"""Hierarchical directories and file operations over the simulated disk."""
import math
import time


class FileManager:
    def __init__(self, disk):
        self.disk = disk
        self.entries = disk.files
        self.directories = disk.directories

    @staticmethod
    def _normalize(path):
        if not isinstance(path, str) or not path.strip():
            raise ValueError("A file or directory path is required")
        clean = "/" + "/".join(part for part in path.replace("\\", "/").split("/") if part)
        if clean == "/":
            raise ValueError("Root cannot be used as a file path")
        if any(part in (".", "..") for part in path.replace("\\", "/").split("/")):
            raise ValueError("Relative path components are not allowed")
        return clean

    def create_directory(self, path):
        normalized = self._normalize(path)
        parts = normalized.strip("/").split("/")
        current = ""
        for part in parts:
            current += "/" + part
            if current not in self.directories:
                parent = current.rsplit("/", 1)[0] or "/"
                if parent not in self.directories:
                    raise ValueError(f"Parent directory does not exist: {parent}")
                self.directories.append(current)
        self.disk._save()
        return normalized

    def create_file(self, path, content=""):
        normalized = self._normalize(path)
        if normalized in self.entries:
            raise ValueError("A file with this path already exists")
        parent = normalized.rsplit("/", 1)[0] or "/"
        if parent not in self.directories:
            raise ValueError(f"Directory does not exist: {parent}")
        if not isinstance(content, str):
            raise ValueError("File content must be text")
        size = len(content.encode("utf-8"))
        count = max(1, math.ceil(size / self.disk.block_size))
        started = time.perf_counter()
        blocks = self.disk.allocate(count)
        self.entries[normalized] = {
            "content": content, "size": size, "blocks": blocks,
            "created_at": time.time(), "modified_at": time.time()
        }
        self.disk._save()
        elapsed = (time.perf_counter() - started) * 1000
        return self._public_entry(normalized, elapsed)

    def read_file(self, path):
        normalized = self._normalize(path)
        if normalized not in self.entries:
            raise KeyError(f"File not found: {normalized}")
        return self.entries[normalized]["content"]

    def write_file(self, path, content):
        normalized = self._normalize(path)
        if normalized not in self.entries:
            raise KeyError(f"File not found: {normalized}")
        if not isinstance(content, str):
            raise ValueError("File content must be text")
        old = self.entries[normalized]
        size = len(content.encode("utf-8"))
        required = max(1, math.ceil(size / self.disk.block_size))
        old_blocks = old["blocks"]
        if required > len(old_blocks):
            extra = self.disk.allocate(required - len(old_blocks))
            blocks = old_blocks + extra
        elif required < len(old_blocks):
            blocks = old_blocks[:required]
            self.disk.release(old_blocks[required:])
        else:
            blocks = old_blocks
        old.update({"content": content, "size": size, "blocks": blocks, "modified_at": time.time()})
        self.disk._save()
        return self._public_entry(normalized)

    def delete_file(self, path):
        normalized = self._normalize(path)
        if normalized not in self.entries:
            raise KeyError(f"File not found: {normalized}")
        entry = self.entries.pop(normalized)
        self.disk.release(entry["blocks"])
        self.disk._save()

    def list_files(self):
        return [self._public_entry(path) for path in sorted(self.entries)]

    def list_directories(self):
        return sorted(self.directories)

    def _public_entry(self, path, elapsed_ms=None):
        item = self.entries[path]
        result = {
            "path": path, "name": path.rsplit("/", 1)[-1],
            "size": item["size"], "blocks": item["blocks"],
            "block_count": len(item["blocks"]),
            "modified_at": item["modified_at"]
        }
        if elapsed_ms is not None:
            result["operation_ms"] = round(elapsed_ms, 4)
        return result
