from pathlib import Path

from flask import Flask, jsonify, render_template, request

from modules.disk_manager import DiskManager
from modules.file_manager import FileManager
from modules.recovery import RecoveryManager
from modules.optimizer import Optimizer


BASE = Path(__file__).resolve().parent
STORAGE = BASE / "storage"
STORAGE.mkdir(exist_ok=True)

app = Flask(__name__)

disk = DiskManager(
    STORAGE / "disk.json",
    total_blocks=128,
    block_size=64
)

file_manager = FileManager(disk)
recovery = RecoveryManager(STORAGE / "journal.json", file_manager)
optimizer = Optimizer(disk, file_manager)


@app.get("/")
def home():
    return render_template("index.html")


@app.get("/api/status")
def api_status():
    return jsonify(disk.status())


@app.get("/api/blocks")
def api_blocks():
    return jsonify({
        "bitmap": disk.bitmap,
        "block_size": disk.block_size
    })


@app.get("/api/files")
def api_files():
    return jsonify(file_manager.list_files())


@app.get("/api/directories")
def api_directories():
    return jsonify(file_manager.list_directories())


@app.post("/api/files")
def api_create_file():
    data = request.get_json(silent=True) or {}

    try:
        path = data.get("path", data.get("name", ""))
        content = data.get("content", "")

        item = file_manager.create_file(path, content)

        recovery.record_completed(
            "CREATE",
            item["path"],
            {"size": item["size"]}
        )

        return jsonify({"ok": True, "file": item}), 201

    except (ValueError, RuntimeError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@app.get("/api/files/<path:file_path>")
def api_read_file(file_path):
    try:
        return jsonify({
            "ok": True,
            "content": file_manager.read_file(file_path)
        })

    except (KeyError, ValueError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 404


@app.put("/api/files/<path:file_path>")
def api_update_file(file_path):
    data = request.get_json(silent=True) or {}

    try:
        item = file_manager.write_file(
            file_path,
            data.get("content", "")
        )

        recovery.record_completed(
            "WRITE",
            item["path"],
            {"size": item["size"]}
        )

        return jsonify({"ok": True, "file": item})

    except (KeyError, ValueError, RuntimeError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@app.delete("/api/files/<path:file_path>")
def api_delete_file(file_path):
    try:
        file_manager.delete_file(file_path)

        recovery.record_completed(
            "DELETE",
            "/" + file_path.lstrip("/")
        )

        return jsonify({"ok": True})

    except (KeyError, ValueError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@app.post("/api/files/rename")
def api_rename_file():
    data = request.get_json(silent=True) or {}

    try:
        old_path = data.get("old_path", "")
        new_path = data.get("new_path", "")

        item = file_manager.rename_file(old_path, new_path)

        recovery.record_completed(
            "RENAME",
            item["path"],
            {
                "old_path": old_path,
                "new_path": item["path"]
            }
        )

        return jsonify({"ok": True, "file": item})

    except (KeyError, ValueError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@app.post("/api/directories")
def api_create_directory():
    data = request.get_json(silent=True) or {}

    try:
        directory = file_manager.create_directory(
            data.get("path", "")
        )

        recovery.record_completed("MKDIR", directory)

        return jsonify({
            "ok": True,
            "directory": directory
        }), 201

    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@app.post("/api/directories/rename")
def api_rename_directory():
    data = request.get_json(silent=True) or {}

    try:
        old_path = data.get("old_path", "")
        new_path = data.get("new_path", "")

        result = file_manager.rename_directory(old_path, new_path)

        recovery.record_completed(
            "RENAME",
            result["new_path"],
            {
                "old_path": result["old_path"],
                "new_path": result["new_path"],
                "moved_files": result["moved_files"],
                "moved_directories": result["moved_directories"]
            }
        )

        return jsonify({"ok": True, "result": result})

    except (KeyError, ValueError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@app.delete("/api/directories/<path:directory_path>")
def api_delete_directory(directory_path):
    try:
        file_manager.delete_directory(directory_path)

        recovery.record_completed(
            "RMDIR",
            "/" + directory_path.lstrip("/")
        )

        return jsonify({"ok": True})

    except (KeyError, ValueError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@app.post("/api/crash")
def api_crash():
    try:
        return jsonify({
            "ok": True,
            "message": recovery.simulate_crash()
        })

    except RuntimeError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@app.post("/api/recover")
def api_recover():
    try:
        message = recovery.recover()

        return jsonify({
            "ok": True,
            "message": message,
            "report": recovery.get_recovery_report()
        })

    except (RuntimeError, ValueError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@app.get("/api/recovery/report")
def api_recovery_report():
    return jsonify({
        "ok": True,
        "report": recovery.get_recovery_report()
    })


@app.get("/api/journal")
def api_journal():
    operation = request.args.get("operation")
    status = request.args.get("status")

    return jsonify(
        recovery.get_journal(
            operation=operation,
            status=status
        )
    )


@app.post("/api/optimize")
def api_optimize():
    try:
        return jsonify({
            "ok": True,
            "result": optimizer.optimize()
        })

    except (ValueError, RuntimeError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@app.get("/api/optimization/history")
def api_optimization_history():
    return jsonify({
        "ok": True,
        "history": optimizer.get_history()
    })


@app.get("/api/benchmark")
def api_benchmark():
    return jsonify(optimizer.benchmark())


@app.get("/api/fragmentation")
def api_fragmentation():
    return jsonify(optimizer.analyze())


@app.errorhandler(404)
def not_found(_error):
    return jsonify({
        "ok": False,
        "error": "Resource not found"
    }), 404


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False
    )