from modules.recovery import RecoveryManager

def test_crash_and_recover(tmp_path, manager):
    recovery = RecoveryManager(tmp_path / "journal.json", manager)
    recovery.simulate_crash()
    assert "/recovery-demo.txt" not in manager.entries
    message = recovery.recover()
    assert "Replayed 1" in message
    assert manager.read_file("/recovery-demo.txt").startswith("This file")
    assert recovery.get_journal()[0]["status"] == "COMMITTED"

def test_recovery_is_idempotent(tmp_path, manager):
    recovery = RecoveryManager(tmp_path / "journal.json", manager)
    recovery.simulate_crash()
    recovery.recover()
    assert "Replayed 0" in recovery.recover()
