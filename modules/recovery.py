
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
        self.last_recovery_report = {
            "total": 0,
            "committed": 0,
            "failed": 0,
            "skipped": 0,
            "transactions": []
        }

        if not self.path.exists():
            self._write({"transactions": []})

    def _read(self):
        data = json.loads(
            self.path.read_text(encoding="utf-8")
        )

        if not isinstance(data, dict):
            raise ValueError("Invalid journal format")

        if not isinstance(data.get("transactions"), list):
            raise ValueError("Journal transactions must be a list")

        return data

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

        if not isinstance(operation, str):
            raise ValueError("Operation must be text")

        operation = operation.upper()

        if operation not in allowed_operations:
            raise ValueError("Unsupported journal operation")

        if not isinstance(path, str) or not path.strip():
            raise ValueError("A transaction path is required")

        if details is not None and not isinstance(details, dict):
            raise ValueError("Transaction details must be a dictionary")

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
            "created_at": time.time(),
            "recovery_attempts": 0
        }

        journal["transactions"].append(transaction)
        self._write(journal)

        return (
            f"Simulated crash: transaction {transaction['id']} "
            "was journaled but not applied. Recover to replay it."
        )

    def _apply_transaction(self, transaction):
        """Apply a supported pending transaction safely."""

        operation = transaction.get("operation")
        path = transaction.get("path")

        if operation == "CREATE":
            if not isinstance(path, str) or not path:
                raise ValueError("CREATE transaction has an invalid path")

            if path in self.file_manager.entries:
                existing_content = self.file_manager.read_file(path)

                if existing_content == transaction.get("content"):
                    return "ALREADY_APPLIED"

                raise ValueError(
                    f"Cannot recover CREATE: another file exists at {path}"
                )

            self.file_manager.create_file(
                path,
                transaction.get("content", "")
            )

            return "APPLIED"

        raise ValueError(
            f"Unsupported pending transaction: {operation}"
        )

    def get_recovery_report(self):
        """Return the most recent recovery summary."""

        return self.last_recovery_report

    def recover(self):
        """Recover all pending transactions and produce a report."""

        journal = self._read()

        report = {
            "total": 0,
            "committed": 0,
            "failed": 0,
            "skipped": 0,
            "transactions": []
        }

        for transaction in journal["transactions"]:
            if transaction.get("status") != "PENDING":
                report["skipped"] += 1
                continue

            report["total"] += 1
            transaction_id = transaction.get("id", "UNKNOWN")

            transaction["recovery_attempts"] = (
                transaction.get("recovery_attempts", 0) + 1
            )

            try:
                result = self._apply_transaction(transaction)

                transaction["status"] = "COMMITTED"
                transaction["recovered_at"] = time.time()
                transaction.pop("last_error", None)

                report["committed"] += 1

                report["transactions"].append({
                    "id": transaction_id,
                    "status": "COMMITTED",
                    "result": result
                })

            except Exception as exc:
                transaction["last_error"] = str(exc)
                transaction["last_failed_at"] = time.time()

                report["failed"] += 1

                report["transactions"].append({
                    "id": transaction_id,
                    "status": "FAILED",
                    "error": str(exc)
                })

            # Save after each transaction so completed work
            # is not lost if a later transaction fails.
            self._write(journal)

        self.last_recovery_report = report

        return (
            f"Recovery complete. Replayed {report['committed']} "
            f"pending transaction(s). "
            f"Failed: {report['failed']}. "
            f"Skipped: {report['skipped']}."
        )
