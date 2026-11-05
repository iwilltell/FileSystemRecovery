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
disk = DiskManager(STORAGE / "disk.json", total_blocks=128, block_size=64)
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
    return jsonify({"bitmap": disk.bitmap, "block_size": disk.block_size})


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
        item = file_manager.create_file(data.get("path", data.get("name", "")),
                                        data.get("content", ""))
        return jsonify({"ok": True, "file": item}), 201
    except (ValueError, RuntimeError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@app.get("/api/files/<path:file_path>")
def api_read_file(file_path):
    try:
        return jsonify({"ok": True, "content": file_manager.read_file(file_path)})
    except (KeyError, ValueError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 404


@app.put("/api/files/<path:file_path>")
def api_update_file(file_path):
    data = request.get_json(silent=True) or {}
    try:
        item = file_manager.write_file(file_path, data.get("content", ""))
        return jsonify({"ok": True, "file": item})
    except (KeyError, ValueError, RuntimeError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@app.delete("/api/files/<path:file_path>")
def api_delete_file(file_path):
    try:
        file_manager.delete_file(file_path)
        return jsonify({"ok": True})
    except (KeyError, ValueError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@app.post("/api/directories")
def api_create_directory():
    data = request.get_json(silent=True) or {}
    try:
        return jsonify({"ok": True, "directory": file_manager.create_directory(data.get("path", ""))}), 201
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@app.post("/api/crash")
def api_crash():
    try:
        return jsonify({"ok": True, "message": recovery.simulate_crash()})
    except RuntimeError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@app.post("/api/recover")
def api_recover():
    try:
        return jsonify({"ok": True, "message": recovery.recover()})
    except RuntimeError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@app.get("/api/journal")
def api_journal():
    return jsonify(recovery.get_journal())


@app.post("/api/optimize")
def api_optimize():
    return jsonify({"ok": True, "result": optimizer.optimize()})


@app.get("/api/benchmark")
def api_benchmark():
    return jsonify(optimizer.benchmark())


@app.get("/api/fragmentation")
def api_fragmentation():
    return jsonify(optimizer.analyze())


@app.errorhandler(404)
def not_found(_error):
    return jsonify({"ok": False, "error": "Resource not found"}), 404


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
