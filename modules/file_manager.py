
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

        clean_path = path.replace("\\", "/")
        parts = clean_path.split("/")

        if any(part in (".", "..") for part in parts):
            raise ValueError("Relative path components are not allowed")

        normalized = "/" + "/".join(part for part in parts if part)

        if normalized == "/":
            raise ValueError("Root cannot be used as a file or directory path")

        return normalized

    def create_directory(self, path):
        normalized = self._normalize(path)

        if normalized in self.entries:
            raise ValueError("A file already exists at this path")

        parts = normalized.strip("/").split("/")
        current = ""

        for part in parts:
            current += "/" + part

            if current in self.entries:
                raise ValueError(f"A file already exists at: {current}")

            if current not in self.directories:
                parent = current.rsplit("/", 1)[0] or "/"

                if parent not in self.directories:
                    raise ValueError(
                        f"Parent directory does not exist: {parent}"
                    )

                self.directories.append(current)

        self.disk._save()
        return normalized

    def create_file(self, path, content=""):
        normalized = self._normalize(path)

        if normalized in self.entries:
            raise ValueError("A file with this path already exists")

        if normalized in self.directories:
            raise ValueError("A directory already exists at this path")

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
            "content": content,
            "size": size,
            "blocks": blocks,
            "created_at": time.time(),
            "modified_at": time.time()
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

        old.update({
            "content": content,
            "size": size,
            "blocks": blocks,
            "modified_at": time.time()
        })

        self.disk._save()
        return self._public_entry(normalized)

    def delete_file(self, path):
        normalized = self._normalize(path)

        if normalized not in self.entries:
            raise KeyError(f"File not found: {normalized}")

        entry = self.entries.pop(normalized)
        self.disk.release(entry["blocks"])
        self.disk._save()

    def rename_file(self, old_path, new_path):
        """Rename or move a file while preserving allocated blocks."""

        old_path = self._normalize(old_path)
        new_path = self._normalize(new_path)

        if old_path not in self.entries:
            raise KeyError(f"File not found: {old_path}")

        if new_path in self.entries:
            raise ValueError("Destination file already exists")

        if new_path in self.directories:
            raise ValueError("A directory already exists at the destination")

        parent = new_path.rsplit("/", 1)[0] or "/"

        if parent not in self.directories:
            raise ValueError(
                f"Destination directory does not exist: {parent}"
            )

        self.entries[new_path] = self.entries.pop(old_path)
        self.disk._save()

        return self._public_entry(new_path)

    def rename_directory(self, old_path, new_path):
        """Rename or move a directory and preserve its complete contents."""

        old_path = self._normalize(old_path)
        new_path = self._normalize(new_path)

        if old_path not in self.directories:
            raise KeyError(f"Directory not found: {old_path}")

        if new_path in self.directories or new_path in self.entries:
            raise ValueError("Destination path already exists")

        if new_path.startswith(old_path + "/"):
            raise ValueError("A directory cannot be moved inside itself")

        parent = new_path.rsplit("/", 1)[0] or "/"

        if parent not in self.directories:
            raise ValueError(
                f"Destination directory does not exist: {parent}"
            )

        affected_directories = [
            directory
            for directory in self.directories
            if directory == old_path
            or directory.startswith(old_path + "/")
        ]

        affected_files = [
            file_path
            for file_path in self.entries
            if file_path.startswith(old_path + "/")
        ]

        directory_mapping = {
            directory: new_path + directory[len(old_path):]
            for directory in affected_directories
        }

        file_mapping = {
            file_path: new_path + file_path[len(old_path):]
            for file_path in affected_files
        }

        new_directory_paths = set(directory_mapping.values())
        new_file_paths = set(file_mapping.values())

        if len(new_directory_paths) != len(directory_mapping):
            raise ValueError("Directory destination conflict")

        if len(new_file_paths) != len(file_mapping):
            raise ValueError("File destination conflict")

        for destination in new_directory_paths:
            if destination in self.entries and destination not in file_mapping:
                raise ValueError("A file conflicts with the destination")

            if destination in self.directories and destination not in directory_mapping:
                raise ValueError("A directory conflicts with the destination")

        for destination in new_file_paths:
            if destination in self.entries and destination not in file_mapping:
                raise ValueError("A file conflicts with the destination")

            if destination in self.directories and destination not in directory_mapping:
                raise ValueError("A directory conflicts with the destination")

        for old_file in affected_files:
            self.entries[file_mapping[old_file]] = self.entries.pop(old_file)

        self.directories = [
            directory
            for directory in self.directories
            if directory not in affected_directories
        ]

        self.directories.extend(directory_mapping.values())
        self.directories = sorted(set(self.directories))

        self.disk.directories = self.directories
        self.disk._save()

        return {
            "old_path": old_path,
            "new_path": new_path,
            "moved_directories": len(affected_directories),
            "moved_files": len(affected_files)
        }

    def delete_directory(self, path):
        """Delete an empty directory without deleting its contents."""

        normalized = self._normalize(path)

        if normalized not in self.directories:
            raise KeyError(f"Directory not found: {normalized}")

        has_subdirectories = any(
            directory.startswith(normalized + "/")
            for directory in self.directories
        )

        has_files = any(
            file_path.startswith(normalized + "/")
            for file_path in self.entries
        )

        if has_subdirectories or has_files:
            raise ValueError(
                "Directory is not empty. Delete its contents first."
            )

        self.directories.remove(normalized)
        self.disk._save()

    def list_files(self):
        return [
            self._public_entry(path)
            for path in sorted(self.entries)
        ]

    def list_directories(self):
        return sorted(self.directories)

    def _public_entry(self, path, elapsed_ms=None):
        item = self.entries[path]

        result = {
            "path": path,
            "name": path.rsplit("/", 1)[-1],
            "size": item["size"],
            "blocks": item["blocks"],
            "block_count": len(item["blocks"]),
            "modified_at": item["modified_at"]
        }

        if elapsed_ms is not None:
            result["operation_ms"] = round(elapsed_ms, 4)

        return result
