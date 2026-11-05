import pytest
from modules.disk_manager import DiskManager
from modules.file_manager import FileManager

@pytest.fixture
def disk(tmp_path):
    return DiskManager(tmp_path / "disk.json", total_blocks=16, block_size=8)

@pytest.fixture
def manager(disk):
    return FileManager(disk)
