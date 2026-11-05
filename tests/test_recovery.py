
import json

import pytest

from modules.recovery import RecoveryManager


# --------------------------------------------------
# EXISTING CRASH RECOVERY TESTS
# --------------------------------------------------

def test_crash_and_recover(tmp_path, manager):
    recovery = RecoveryManager(tmp_path / "journal.json", manager)

    recovery.simulate_crash()

    assert "/recovery-demo.txt" not in manager.entries

    message = recovery.recover()

    assert "Replayed 1" in message
    assert manager.read_file("/recovery-demo.txt").startswith(
        "This file"
    )
    assert recovery.get_journal()[0]["status"] == "COMMITTED"


def test_recovery_is_idempotent(tmp_path, manager):
    recovery = RecoveryManager(tmp_path / "journal.json", manager)

    recovery.simulate_crash()
    recovery.recover()

    assert "Replayed 0" in recovery.recover()


# --------------------------------------------------
# REVISION 4: JOURNAL SYSTEM ENHANCEMENT TESTS
# --------------------------------------------------

def test_record_completed_transaction(tmp_path, manager):
    recovery = RecoveryManager(tmp_path / "journal.json", manager)

    transaction = recovery.record_completed(
        "CREATE",
        "/notes.txt",
        {"size": 20}
    )

    assert transaction["operation"] == "CREATE"
    assert transaction["path"] == "/notes.txt"
    assert transaction["status"] == "COMMITTED"
    assert transaction["details"]["size"] == 20


def test_transaction_ids_are_unique(tmp_path, manager):
    recovery = RecoveryManager(tmp_path / "journal.json", manager)

    first = recovery.record_completed("CREATE", "/first.txt")
    second = recovery.record_completed("CREATE", "/second.txt")

    assert first["id"] != second["id"]


def test_journal_filter_by_operation(tmp_path, manager):
    recovery = RecoveryManager(tmp_path / "journal.json", manager)

    recovery.record_completed("CREATE", "/first.txt")
    recovery.record_completed("WRITE", "/first.txt")
    recovery.record_completed("DELETE", "/second.txt")

    results = recovery.get_journal(operation="WRITE")

    assert len(results) == 1
    assert results[0]["operation"] == "WRITE"


def test_journal_filter_by_status(tmp_path, manager):
    recovery = RecoveryManager(tmp_path / "journal.json", manager)

    recovery.record_completed("CREATE", "/first.txt")
    recovery.simulate_crash()

    results = recovery.get_journal(status="PENDING")

    assert len(results) == 1
    assert results[0]["status"] == "PENDING"


def test_journal_rejects_invalid_operation(tmp_path, manager):
    recovery = RecoveryManager(tmp_path / "journal.json", manager)

    with pytest.raises(ValueError):
        recovery.record_completed("FORMAT", "/disk")


def test_journal_rejects_empty_path(tmp_path, manager):
    recovery = RecoveryManager(tmp_path / "journal.json", manager)

    with pytest.raises(ValueError):
        recovery.record_completed("CREATE", "")


def test_journal_persists_after_restart(tmp_path, manager):
    journal_path = tmp_path / "journal.json"

    recovery = RecoveryManager(journal_path, manager)
    recovery.record_completed("WRITE", "/notes.txt")

    restarted_recovery = RecoveryManager(journal_path, manager)

    transactions = restarted_recovery.get_journal()

    assert len(transactions) == 1
    assert transactions[0]["operation"] == "WRITE"
    assert transactions[0]["status"] == "COMMITTED"


def test_pending_transaction_prevents_second_crash(tmp_path, manager):
    recovery = RecoveryManager(tmp_path / "journal.json", manager)

    recovery.simulate_crash()

    with pytest.raises(RuntimeError):
        recovery.simulate_crash()


# --------------------------------------------------
# REVISION 5: CRASH RECOVERY ENHANCEMENT TESTS
# --------------------------------------------------

def test_recovery_processes_multiple_pending_transactions(
    tmp_path, manager
):
    journal_path = tmp_path / "journal.json"

    transactions = [
        {
            "id": "TX-001",
            "operation": "CREATE",
            "path": "/first.txt",
            "content": "First recovered file",
            "status": "PENDING",
            "created_at": 1000,
            "recovery_attempts": 0
        },
        {
            "id": "TX-002",
            "operation": "CREATE",
            "path": "/second.txt",
            "content": "Second recovered file",
            "status": "PENDING",
            "created_at": 1001,
            "recovery_attempts": 0
        }
    ]

    journal_path.write_text(
        json.dumps({"transactions": transactions}),
        encoding="utf-8"
    )

    recovery = RecoveryManager(journal_path, manager)
    message = recovery.recover()

    assert "Replayed 2" in message
    assert manager.read_file("/first.txt") == "First recovered file"
    assert manager.read_file("/second.txt") == "Second recovered file"

    assert all(
        tx["status"] == "COMMITTED"
        for tx in recovery.get_journal()
    )


def test_recovery_detects_already_applied_file(tmp_path, manager):
    journal_path = tmp_path / "journal.json"

    manager.create_file("/existing.txt", "Existing content")

    transactions = [
        {
            "id": "TX-003",
            "operation": "CREATE",
            "path": "/existing.txt",
            "content": "Existing content",
            "status": "PENDING",
            "created_at": 1000,
            "recovery_attempts": 0
        }
    ]

    journal_path.write_text(
        json.dumps({"transactions": transactions}),
        encoding="utf-8"
    )

    recovery = RecoveryManager(journal_path, manager)
    recovery.recover()

    report = recovery.get_recovery_report()

    assert report["committed"] == 1
    assert report["transactions"][0]["result"] == "ALREADY_APPLIED"
    assert manager.read_file("/existing.txt") == "Existing content"


def test_recovery_report_tracks_failed_transactions(tmp_path, manager):
    journal_path = tmp_path / "journal.json"

    transactions = [
        {
            "id": "TX-004",
            "operation": "UNSUPPORTED",
            "path": "/unknown.txt",
            "status": "PENDING",
            "created_at": 1000,
            "recovery_attempts": 0
        }
    ]

    journal_path.write_text(
        json.dumps({"transactions": transactions}),
        encoding="utf-8"
    )

    recovery = RecoveryManager(journal_path, manager)
    recovery.recover()

    report = recovery.get_recovery_report()

    assert report["total"] == 1
    assert report["committed"] == 0
    assert report["failed"] == 1

    assert recovery.get_journal()[0]["status"] == "PENDING"
    assert recovery.get_journal()[0]["recovery_attempts"] == 1
    assert "Unsupported pending transaction" in (
        recovery.get_journal()[0]["last_error"]
    )


def test_failed_transaction_can_be_retried(tmp_path, manager):
    journal_path = tmp_path / "journal.json"

    transactions = [
        {
            "id": "TX-005",
            "operation": "UNSUPPORTED",
            "path": "/unknown.txt",
            "status": "PENDING",
            "created_at": 1000,
            "recovery_attempts": 0
        }
    ]

    journal_path.write_text(
        json.dumps({"transactions": transactions}),
        encoding="utf-8"
    )

    recovery = RecoveryManager(journal_path, manager)

    recovery.recover()
    recovery.recover()

    transaction = recovery.get_journal()[0]

    assert transaction["status"] == "PENDING"
    assert transaction["recovery_attempts"] == 2


def test_recovery_report_tracks_skipped_transactions(tmp_path, manager):
    recovery = RecoveryManager(tmp_path / "journal.json", manager)

    recovery.record_completed("CREATE", "/already-completed.txt")

    recovery.recover()

    report = recovery.get_recovery_report()

    assert report["total"] == 0
    assert report["committed"] == 0
    assert report["failed"] == 0
    assert report["skipped"] == 1


def test_recovery_report_contains_transaction_ids(tmp_path, manager):
    recovery = RecoveryManager(tmp_path / "journal.json", manager)

    recovery.simulate_crash()
    transaction_id = recovery.get_journal()[0]["id"]

    recovery.recover()

    report = recovery.get_recovery_report()

    assert report["transactions"][0]["id"] == transaction_id
    assert report["transactions"][0]["status"] == "COMMITTED"
