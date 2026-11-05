
from modules.recovery import RecoveryManager

import pytest


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
