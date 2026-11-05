
import pytest

import app as app_module
from modules.disk_manager import DiskManager
from modules.file_manager import FileManager
from modules.recovery import RecoveryManager
from modules.optimizer import Optimizer


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Create an isolated Flask test client for every test."""
    test_disk = DiskManager(
        tmp_path / "test_disk.json",
        total_blocks=16,
        block_size=8
    )

    test_file_manager = FileManager(test_disk)

    test_recovery = RecoveryManager(
        tmp_path / "test_journal.json",
        test_file_manager
    )

    test_optimizer = Optimizer(
        test_disk,
        test_file_manager
    )

    monkeypatch.setattr(app_module, "disk", test_disk)
    monkeypatch.setattr(app_module, "file_manager", test_file_manager)
    monkeypatch.setattr(app_module, "recovery", test_recovery)
    monkeypatch.setattr(app_module, "optimizer", test_optimizer)

    app_module.app.config.update(TESTING=True)

    with app_module.app.test_client() as test_client:
        yield test_client


def test_home_page_loads(client):
    response = client.get("/")

    assert response.status_code == 200


def test_status_and_blocks_endpoints(client):
    status_response = client.get("/api/status")
    blocks_response = client.get("/api/blocks")

    assert status_response.status_code == 200
    assert blocks_response.status_code == 200

    blocks_data = blocks_response.get_json()

    assert len(blocks_data["bitmap"]) == 16
    assert blocks_data["block_size"] == 8


def test_file_create_read_update_delete_workflow(client):
    create_response = client.post(
        "/api/files",
        json={
            "path": "/notes.txt",
            "content": "Hello OS"
        }
    )

    assert create_response.status_code == 201
    assert create_response.get_json()["ok"] is True

    read_response = client.get("/api/files/notes.txt")

    assert read_response.status_code == 200
    assert read_response.get_json()["content"] == "Hello OS"

    update_response = client.put(
        "/api/files/notes.txt",
        json={"content": "Updated content"}
    )

    assert update_response.status_code == 200

    read_updated = client.get("/api/files/notes.txt")

    assert read_updated.get_json()["content"] == "Updated content"

    delete_response = client.delete("/api/files/notes.txt")

    assert delete_response.status_code == 200

    missing_response = client.get("/api/files/notes.txt")

    assert missing_response.status_code == 404


def test_file_rename_endpoint(client):
    client.post(
        "/api/files",
        json={
            "path": "/old.txt",
            "content": "Rename me"
        }
    )

    response = client.post(
        "/api/files/rename",
        json={
            "old_path": "/old.txt",
            "new_path": "/new.txt"
        }
    )

    assert response.status_code == 200
    assert response.get_json()["ok"] is True

    renamed_file = client.get("/api/files/new.txt")

    assert renamed_file.status_code == 200
    assert renamed_file.get_json()["content"] == "Rename me"

    old_file = client.get("/api/files/old.txt")

    assert old_file.status_code == 404


def test_directory_create_rename_and_delete_workflow(client):
    create_response = client.post(
        "/api/directories",
        json={"path": "/assignments"}
    )

    assert create_response.status_code == 201

    file_response = client.post(
        "/api/files",
        json={
            "path": "/assignments/task.txt",
            "content": "Operating Systems"
        }
    )

    assert file_response.status_code == 201

    rename_response = client.post(
        "/api/directories/rename",
        json={
            "old_path": "/assignments",
            "new_path": "/work"
        }
    )

    assert rename_response.status_code == 200

    moved_file = client.get("/api/files/work/task.txt")

    assert moved_file.status_code == 200
    assert moved_file.get_json()["content"] == "Operating Systems"

    # Delete the file before deleting its parent directory.
    delete_file_response = client.delete(
        "/api/files/work/task.txt"
    )

    assert delete_file_response.status_code == 200

    delete_directory_response = client.delete(
        "/api/directories/work"
    )

    assert delete_directory_response.status_code == 200


def test_fragmentation_and_benchmark_endpoints(client):
    create_response = client.post(
        "/api/files",
        json={
            "path": "/benchmark.txt",
            "content": "Sample data"
        }
    )

    assert create_response.status_code == 201

    fragmentation_response = client.get("/api/fragmentation")
    benchmark_response = client.get("/api/benchmark")

    assert fragmentation_response.status_code == 200
    assert "free_blocks" in fragmentation_response.get_json()

    assert benchmark_response.status_code == 200
    assert benchmark_response.get_json()["files_tested"] == 1


def test_optimize_endpoint(client):
    client.post(
        "/api/files",
        json={
            "path": "/first.txt",
            "content": "First"
        }
    )

    client.post(
        "/api/files",
        json={
            "path": "/second.txt",
            "content": "Second"
        }
    )

    response = client.post("/api/optimize")

    assert response.status_code == 200

    result = response.get_json()["result"]

    assert result["message"].startswith("Compaction completed")


def test_optimization_history_endpoint(client):
    client.post(
        "/api/files",
        json={
            "path": "/history.txt",
            "content": "History test"
        }
    )

    optimize_response = client.post("/api/optimize")

    assert optimize_response.status_code == 200

    history_response = client.get(
        "/api/optimization/history"
    )

    assert history_response.status_code == 200

    history = history_response.get_json()["history"]

    assert len(history) == 1
