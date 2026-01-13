# YakiSuperTaskMaster (TaskMaster)

Ebbinghaus forgetting-curve-based task manager.

This repository contains a PySide6 (Qt for Python) desktop app backed by SQLite.

## Dev environment (venv)

This repo already includes a venv. Activate it and install dependencies.

```bash
source /home/yakisenbei/Documents/YakiSuperTaskMaster/bin/activate
pip install -U pip
pip install -r requirements.txt
```

## Run

```bash
source /home/yakisenbei/Documents/YakiSuperTaskMaster/bin/activate
python -m taskmaster
```

## Data location

- Default DB directory: `/home/yakisenbei/.local/share/`
- Default DB file name: `taskmaster.db` (you can choose another path in Settings)

## Notes

- Backup is a simple file copy from Settings.
- "Purge" is a *non-recoverable* logical delete (sets `purged_at`), not a physical delete.
