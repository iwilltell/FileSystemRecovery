"""Write-ahead journal with a deterministic interrupted-create demonstration."""
import json
import time
from pathlib import Path


class RecoveryManager:
    def __init__(self, journal_path, file_manager):
        self.path = Path(journal_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.file_manager = file_manager
        if not self.path.exists():
            self._write({"transactions": []})

    def _read(self):
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _write(self, data):
        self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def get_journal(self):
        return self._read()["transactions"]

    def simulate_crash(self):
        journal = self._read()
        if any(tx["status"] == "PENDING" for tx in journal["transactions"]):
            raise RuntimeError("A pending transaction already exists. Recover it first.")
        demo_path = "/recovery-demo.txt"
        if demo_path in self.file_manager.entries:
            demo_path = f"/recovery-demo-{int(time.time())}.txt"
        tx = {
            "id": f"TX-{int(time.time() * 1000)}",
            "operation": "CREATE",
            "path": demo_path,
            "content": "This file was restored by journal recovery.",
            "status": "PENDING",
            "created_at": time.time()
        }
        journal["transactions"].append(tx)
        self._write(journal)
        return f"Simulated crash: transaction {tx['id']} was journaled but not applied. Recover to replay it."

    def recover(self):
        journal = self._read()
        recovered = 0
        for tx in journal["transactions"]:
            if tx["status"] != "PENDING":
                continue
            if tx["operation"] == "CREATE":
                if tx["path"] not in self.file_manager.entries:
                    self.file_manager.create_file(tx["path"], tx["content"])
            tx["status"] = "COMMITTED"
            tx["recovered_at"] = time.time()
            recovered += 1
        self._write(journal)
        return f"Recovery complete. Replayed {recovered} pending transaction(s)."
