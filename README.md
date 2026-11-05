# File System Recovery and Optimization Tool

A Python and Flask-based educational web application that simulates important operating system file-system concepts.

**Live Demo:** https://filesystem-recovery-tool.onrender.com

**GitHub Repository:** https://github.com/iwilltell/FileSystemRecovery

---

## 1. Project Overview

The File System Recovery and Optimization Tool is an educational application designed to demonstrate how file systems manage storage, organize files, recover from simulated crashes, and optimize disk space.

The application uses a simulated disk with fixed-size blocks and bitmap-based allocation. Users can interact with the file system through a browser-based dashboard.

**Important:** This is an educational simulation. It does not access, repair, format, or modify physical disks or real operating-system file systems.

## 2. Live Application

Try the deployed application:

https://filesystem-recovery-tool.onrender.com

The application is hosted on Render using Gunicorn and Flask.

Note: The free hosting instance may spin down after inactivity. The first visit after inactivity may take some time to load.

## 3. Main Features

- **Disk Management:** Bitmap-based block allocation and release.
- **File Management:** Create, read, update, delete, rename, and move files.
- **Directory Management:** Create, rename, list, and delete directories, including nested directories.
- **Transaction Journal:** Records file-system operations and their status.
- **Crash Recovery:** Simulates a pending transaction and replays supported operations.
- **Fragmentation Analysis:** Reports free-space runs, allocated blocks, and fragmentation details.
- **Disk Optimization:** Compacts allocated blocks while preserving file contents and metadata.
- **Optimization History:** Maintains an in-memory history of optimization runs.
- **Performance Benchmark:** Measures simulated file read and write operation times.
- **Web Dashboard:** Browser-based interface for interacting with the simulator.

## 4. Technologies Used

| Technology     | Purpose                                |
| -------------- | -------------------------------------- |
| Python 3.13    | Application logic                      |
| Flask          | Web framework and API                  |
| HTML           | Dashboard structure                    |
| CSS            | Dashboard styling                      |
| JavaScript     | Frontend interactions                  |
| JSON           | Simulated disk and journal persistence |
| pytest         | Automated testing                      |
| Gunicorn       | Production application server          |
| Git and GitHub | Version control                        |
| Render         | Cloud deployment                       |

## 5. Project Structure

```text
FileSystemRecovery/
│
├── app.py
├── requirements.txt
├── README.md
├── .python-version
├── .gitignore
│
├── modules/
│   ├── __init__.py
│   ├── disk_manager.py
│   ├── file_manager.py
│   ├── recovery.py
│   └── optimizer.py
│
├── templates/
│   └── index.html
│
├── static/
│   ├── style.css
│   └── script.js
│
├── storage/
│   └── .gitkeep
│
├── tests/
│   ├── conftest.py
│   ├── test_app.py
│   ├── test_disk_manager.py
│   ├── test_file_manager.py
│   ├── test_optimizer.py
│   └── test_recovery.py
│
└── docs/
    └── flowchart.md
```

## 6. Installation and Local Setup

### Requirements

- Python 3.13
- Flask 3.x
- pytest 8.x for testing
- Git

### Step 1: Clone the repository

```bash
git clone https://github.com/iwilltell/FileSystemRecovery.git
cd FileSystemRecovery
```

### Step 2: Create a virtual environment

Windows PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

Linux or macOS:

```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Start the application

```bash
python app.py
```

Open:

http://127.0.0.1:5000

## 7. Running Tests

Run the complete test suite:

```bash
python -m pytest -v
```

Run Flask integration tests:

```bash
python -m pytest tests/test_app.py -v
```

The test suite covers disk management, file operations, directory operations, recovery, optimization, and application API workflows.

Tests use temporary storage to avoid modifying the application's normal disk and journal data.

## 8. API Documentation

| Method | Endpoint                    | Purpose                    |
| ------ | --------------------------- | -------------------------- |
| GET    | `/`                         | Load dashboard             |
| GET    | `/api/status`               | View disk status           |
| GET    | `/api/blocks`               | View allocation bitmap     |
| GET    | `/api/files`                | List files                 |
| POST   | `/api/files`                | Create a file              |
| GET    | `/api/files/<path>`         | Read a file                |
| PUT    | `/api/files/<path>`         | Update a file              |
| DELETE | `/api/files/<path>`         | Delete a file              |
| POST   | `/api/files/rename`         | Rename or move a file      |
| GET    | `/api/directories`          | List directories           |
| POST   | `/api/directories`          | Create a directory         |
| POST   | `/api/directories/rename`   | Rename or move a directory |
| DELETE | `/api/directories/<path>`   | Delete a directory         |
| GET    | `/api/journal`              | View transaction journal   |
| POST   | `/api/crash`                | Simulate a disk crash      |
| POST   | `/api/recover`              | Execute recovery           |
| GET    | `/api/recovery/report`      | View recovery report       |
| GET    | `/api/fragmentation`        | Analyze fragmentation      |
| POST   | `/api/optimize`             | Compact allocated blocks   |
| GET    | `/api/optimization/history` | View optimization history  |
| GET    | `/api/benchmark`            | Run read/write benchmarks  |

### Example API requests

Create a file:

```json
{
  "path": "/notes.txt",
  "content": "Operating Systems Project"
}
```

Update a file:

```json
{
  "content": "Updated project content"
}
```

Rename a file:

```json
{
  "old_path": "/notes.txt",
  "new_path": "/updated-notes.txt"
}
```

Create a directory:

```json
{
  "path": "/assignments"
}
```

Rename a directory:

```json
{
  "old_path": "/assignments",
  "new_path": "/college-work"
}
```

Filter journal transactions:

```text
/api/journal?operation=CREATE&status=COMPLETED
```

## 9. Recovery Demonstration

1. Start the application.
2. Create files using the dashboard.
3. Select **Simulate disk crash**.
4. The recovery manager records a pending CREATE transaction.
5. Select **Run recovery**.
6. The recovery manager attempts to replay the pending operation.
7. Inspect the file list, journal, and recovery report.

This demonstrates a controlled recovery workflow using simulated disk data.

## 10. Disk Optimization Demonstration

1. Create several files.
2. Delete one or more files to create free-space gaps.
3. Open fragmentation analysis.
4. Observe the allocation and free-space statistics.
5. Run disk optimization.
6. Compare the before-and-after fragmentation reports.
7. Inspect optimization history.

The compaction process rearranges simulated block references while preserving file contents.

## 11. Deployment

The application is deployed on Render.

Deployment configuration:

| Setting           | Value                                   |
| ----------------- | --------------------------------------- |
| Platform          | Render                                  |
| Runtime           | Python                                  |
| Build command     | `pip install -r requirements.txt`       |
| Start command     | `gunicorn app:app --bind 0.0.0.0:$PORT` |
| Repository branch | `main`                                  |

The application uses JSON files for simulated disk and journal storage.

**Hosting limitation:** Render's free web services use an ephemeral filesystem. Disk and journal data may be lost after restarts, redeployments, or instance replacement. The free plan does not provide persistent disks. This deployment is intended for educational demonstration, not permanent data storage.

## 12. Limitations

- The application simulates file-system behavior rather than operating on physical storage devices.
- Crash recovery demonstrates a controlled CREATE transaction and is not a complete production journaling implementation.
- Performance measurements represent local Python operation timings, not physical disk benchmarks.
- Optimization history is stored in application memory and resets when the application restarts.
- Hosted JSON data is not guaranteed to persist on the Render free plan.
- The application is designed for educational demonstration rather than production deployment.

## 13. Future Scope

Possible improvements include:

- Persistent optimization history.
- File checksums and data-integrity verification.
- Snapshot and rollback support.
- Concurrent-access protection.
- Additional block-allocation algorithms.
- More detailed recovery scenarios.
- Database-backed metadata storage.
- Improved visualization of disk allocation.
- Persistent cloud storage.

## 14. References

- Python documentation: https://docs.python.org/3/
- Flask documentation: https://flask.palletsprojects.com/
- pytest documentation: https://docs.pytest.org/
- Gunicorn documentation: https://gunicorn.org/
- Render documentation: https://render.com/docs
- Git documentation: https://git-scm.com/doc

## 15. Academic and Development Note

This project was developed as an educational Operating Systems project. Development tools, including AI assistance where applicable, should be acknowledged accurately in the submitted project report according to the institution's academic guidelines.

The student should understand the implementation, testing approach, design decisions, and limitations before the project demonstration and viva.
