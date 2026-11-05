# File System Recovery and Optimization Tool

A Python Flask web application that simulates core file-system concepts:
bitmap-based free-space management, hierarchical directories, file operations,
a write-ahead recovery journal, simulated crash recovery, compaction, and
basic read/write timing measurements.

## Safety

This is an educational simulation. It only changes JSON data under `storage/`.
It does not inspect, repair, format, or modify real disks or operating-system
file systems.

## Requirements

- Python 3.10+
- Flask 3.x
- pytest 8.x (for tests)

## Run on Windows PowerShell

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000.

## Run tests

```powershell
pytest -v
```

## Main components

- `modules/disk_manager.py`: fixed-size simulated disk, bitmap allocation,
  release, and persistent JSON metadata.
- `modules/file_manager.py`: file CRUD operations and nested directories.
- `modules/recovery.py`: write-ahead journal and deterministic crash/replay demo.
- `modules/optimizer.py`: fragmentation indicator, block compaction, and timing.
- `templates/` and `static/`: responsive browser dashboard.

## Recovery demonstration

1. Create a few files.
2. Click **Simulate disk crash**. The application writes a pending CREATE
   transaction to the journal but does not apply it to the simulated disk.
3. Click **Run recovery**. The recovery manager replays the pending operation.
4. Inspect the file list and transaction journal.

## Deployment

For a public deployment, use a persistent disk/volume because the simulator
stores state in local JSON files. Set the hosting provider's start command to
`gunicorn app:app` and add `gunicorn` to requirements. Do not deploy the Flask
development server as a production server.

## Limitations and future scope

This project is a teaching simulator, not a production file system. Its
journal demonstration covers a controlled CREATE transaction; it is not a
full POSIX journaling implementation. Performance timings are local Python
operation timings and are not physical disk benchmarks. Future work could add
checksums, snapshots, concurrent-access locking, richer allocation policies,
and a persistent database.
