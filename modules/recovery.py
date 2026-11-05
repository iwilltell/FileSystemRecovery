
"""Transaction journal and simulated filesystem crash recovery."""

import json
import time
import uuid
from pathlib import Path


class RecoveryManager:
    def __init__(self, journal_path, file_manager):
        self.path = Path(journal_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.file_manager = file_manager

        if not self.path.exists():
            self._write({"transactions": []})

    def _read(self):
        return json.loads(
            self.path.read_text(encoding="utf-8")
        )

    def _write(self, data):
        self.path.write_text(
            json.dumps(data, indent=2),
            encoding="utf-8"
        )

    def get_journal(self, operation=None, status=None):
        """Return journal transactions, optionally filtered."""

        transactions = self._read()["transactions"]

        if operation:
            transactions = [
                tx for tx in transactions
                if tx["operation"] == operation.upper()
            ]

        if status:
            transactions = [
                tx for tx in transactions
                if tx["status"] == status.upper()
            ]

        return transactions

    def record_completed(self, operation, path, details=None):
        """Record a successfully completed filesystem operation."""

        allowed_operations = {
            "CREATE", "WRITE", "DELETE", "RENAME",
            "MKDIR", "RMDIR"
        }

        operation = operation.upper()

        if operation not in allowed_operations:
            raise ValueError("Unsupported journal operation")

        if not isinstance(path, str) or not path.strip():
            raise ValueError("A transaction path is required")

        journal = self._read()

        transaction = {
            "id": f"TX-{uuid.uuid4().hex}",
            "operation": operation,
            "path": path,
            "status": "COMMITTED",
            "created_at": time.time(),
            "details": details or {}
        }

        journal["transactions"].append(transaction)
        self._write(journal)

        return transaction

    def simulate_crash(self):
        """Create a pending CREATE transaction without applying it."""

        journal = self._read()

        if any(
            tx["status"] == "PENDING"
            for tx in journal["transactions"]
        ):
            raise RuntimeError(
                "A pending transaction already exists. Recover it first."
            )

        demo_path = "/recovery-demo.txt"

        if demo_path in self.file_manager.entries:
            demo_path = (
                f"/recovery-demo-{uuid.uuid4().hex[:8]}.txt"
            )

        transaction = {
            "id": f"TX-{uuid.uuid4().hex}",
            "operation": "CREATE",
            "path": demo_path,
            "content": "This file was restored by journal recovery.",
            "status": "PENDING",
            "created_at": time.time()
        }

        journal["transactions"].append(transaction)
        self._write(journal)

        return (
            f"Simulated crash: transaction {transaction['id']} "
            "was journaled but not applied. Recover to replay it."
        )

    def recover(self):
        """Replay pending transactions and mark them committed."""

        journal = self._read()
        recovered = 0

        for transaction in journal["transactions"]:
            if transaction["status"] != "PENDING":
                continue

            if transaction["operation"] == "CREATE":
                path = transaction["path"]

                if path not in self.file_manager.entries:
                    self.file_manager.create_file(
                        path,
                        transaction["content"]
                    )

            else:
                raise RuntimeError(
                    "Unsupported pending transaction: "
                    f"{transaction['operation']}"
                )

            transaction["status"] = "COMMITTED"
            transaction["recovered_at"] = time.time()
            recovered += 1

        self._write(journal)

        return (
            f"Recovery complete. Replayed {recovered} "
            "pending transaction(s)."
        )
