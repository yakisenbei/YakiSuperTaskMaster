# TaskMaster

TaskMaster is a buttonless task manager based on an Ebbinghaus/ACT-R-like forgetting curve.

## Run

Use the venv Python (per spec):

```bash
/home/yakisenbei/Documents/YakiSuperTaskMaster/bin/python -m taskmaster
```

## Notes

- DB is stored at `~/.local/share/taskmaster.db` by default.
- Times are stored as UTC epoch seconds; UI displays local time.
