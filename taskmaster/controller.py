from __future__ import annotations

import shutil
import sqlite3
from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path

from PySide6.QtCore import (QObject, Property, QTimer, Signal, Slot)
from PySide6.QtGui import QGuiApplication

from taskmaster import db
from taskmaster.constants import (
    DUE_UPDATE_INTERVAL_MS,
    GRADE_P_TARGET,
    SEARCH_DEBOUNCE_MS,
    VALID_GRADES,
)
from taskmaster.query_parser import parse_search_query
from taskmaster.repository import (
    add_completion_event,
    add_tag_to_task,
    archive_task,
    completion_history,
    create_task,
    due_waiting_counts,
    get_task,
    list_tasks,
    list_task_tags,
    purge_task,
    remove_tag_from_task,
    restore_task,
    update_due_from_waiting,
    update_task,
)
from taskmaster.scheduler import find_next_review
from taskmaster.settings import AppSettings, default_db_path
from taskmaster.table_models import Column, TaskTableModel
from taskmaster.timeutil import (
    ceil_to_minute,
    ensure_min_gap,
    from_epoch_seconds,
    to_epoch_seconds,
    utc_now,
)


def _pick_background(theme: str) -> str:
    # Spec fixed directories first (15.1.6.2), then fallback to older path mention.
    dirs = [
        Path.home() / "Pictures" / "YakiSuperTaskMaster" / ("dark" if theme == "dark" else "light"),
        Path.home() / "Pictures" / "YakiSuperTaskMaster" / "theme",
    ]

    # 1) fixed directory rule
    d = dirs[0]
    if d.exists() and d.is_dir():
        p = d / "background.png"
        if p.exists():
            return str(p)
        for ext in (".png", ".jpg", ".jpeg", ".webp"):
            for cand in sorted(d.glob(f"*{ext}")):
                return str(cand)

    # 2) legacy direct file paths
    legacy = Path.home() / "Pictures" / "YakiSuperTaskMaster" / "theme" / ("dark.png" if theme == "dark" else "light.png")
    if legacy.exists():
        return str(legacy)

    return ""


class TaskMasterController(QObject):
    viewChanged = Signal()
    statusMessageChanged = Signal()
    themeChanged = Signal()
    horizonDaysChanged = Signal()
    dbLabelChanged = Signal()
    countsChanged = Signal()
    backgroundChanged = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._settings = AppSettings()
        self._db_path = Path(self._settings.db_path() or str(default_db_path()))
        self._conn: sqlite3.Connection | None = None

        self._view = "due"  # due|waiting|archived|settings
        self._search_query = ""
        self._status_message = ""

        self._dueModel = TaskTableModel(
            [
                Column("Title", "title"),
                Column("Last Completed", "last_completed"),
                Column("Review Count", "review_count"),
                Column("Next Review At", "next_review_at"),
                Column("Tags", "tags"),
            ],
            parent=self,
        )
        self._waitingModel = TaskTableModel(
            [
                Column("Title", "title"),
                Column("Next Review At", "next_review_at"),
                Column("Remaining", "remaining"),
                Column("Review Count", "review_count"),
                Column("Tags", "tags"),
            ],
            parent=self,
        )
        self._archivedModel = TaskTableModel(
            [
                Column("Title", "title"),
                Column("Archived At", "archived_at"),
                Column("Last Completed", "last_completed"),
                Column("Review Count", "review_count"),
                Column("Tags", "tags"),
            ],
            parent=self,
        )

        self._due_count = 0
        self._waiting_count = 0

        self._searchTimer = QTimer(self)
        self._searchTimer.setSingleShot(True)
        self._searchTimer.timeout.connect(self.refresh)

        self._dueTimer = QTimer(self)
        self._dueTimer.timeout.connect(self._tick_due_update)

        self._open_db()
        self.refresh()
        self._dueTimer.start(DUE_UPDATE_INTERVAL_MS)

    # ---------- properties ----------

    @Property(str, notify=viewChanged)
    def currentView(self) -> str:
        return self._view

    @Property(QObject, constant=True)
    def dueModel(self) -> QObject:
        return self._dueModel

    @Property(QObject, constant=True)
    def waitingModel(self) -> QObject:
        return self._waitingModel

    @Property(QObject, constant=True)
    def archivedModel(self) -> QObject:
        return self._archivedModel

    @Property(str, notify=statusMessageChanged)
    def statusMessage(self) -> str:
        return self._status_message

    @Property(int, notify=countsChanged)
    def dueCount(self) -> int:
        return self._due_count

    @Property(int, notify=countsChanged)
    def waitingCount(self) -> int:
        return self._waiting_count

    @Property(str, notify=themeChanged)
    def theme(self) -> str:
        return self._settings.theme()

    @Property(int, notify=horizonDaysChanged)
    def horizonDays(self) -> int:
        return self._settings.horizon_days()

    @Property(str, notify=dbLabelChanged)
    def dbLabel(self) -> str:
        return self._db_path.name if self._db_path else "(not set)"

    @Property(str, notify=dbLabelChanged)
    def dbTooltip(self) -> str:
        info = self._db_info()
        ver = info.schema_version if info else None
        return f"{self._db_path}\nSchema: {ver}"

    @Property(str, notify=dbLabelChanged)
    def dbPath(self) -> str:
        return str(self._db_path) if self._db_path else ""

    @Property(str, notify=backgroundChanged)
    def backgroundPath(self) -> str:
        return _pick_background(self._settings.theme())

    # ---------- internal ----------

    def _open_db(self) -> None:
        self._conn = db.connect(self._db_path)
        db.migrate(self._conn)

    def _require_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError("DB not initialized")
        return self._conn

    def _db_info(self):
        if self._conn is None:
            return None
        return db.db_info(self._conn, self._db_path)

    def _set_status(self, msg: str) -> None:
        self._status_message = msg
        self.statusMessageChanged.emit()

    def _update_counts(self) -> None:
        conn = self._require_conn()
        self._due_count, self._waiting_count = due_waiting_counts(conn)
        self.countsChanged.emit()

    def _tick_due_update(self) -> None:
        conn = self._require_conn()
        changed = update_due_from_waiting(conn, now_epoch=to_epoch_seconds(utc_now()))
        if changed:
            conn.commit()
            self.refresh()

    def _refresh_view(self, view: str) -> None:
        conn = self._require_conn()
        text, tags = parse_search_query(self._search_query)
        q_like = f"%{text}%" if text else None
        rows = list_tasks(conn, view=view, q_like=q_like, tags=tags)

        if view == "due":
            self._dueModel.setRows(rows)
        elif view == "waiting":
            self._waitingModel.setRows(rows)
        elif view == "archived":
            self._archivedModel.setRows(rows)

    # ---------- slots (navigation) ----------

    @Slot(str)
    def setView(self, view: str) -> None:
        if view not in ("due", "waiting", "archived", "settings"):
            return
        self._view = view
        self.viewChanged.emit()
        if view in ("due", "waiting", "archived"):
            self.refresh()

    # ---------- slots (search/refresh) ----------

    @Slot(str)
    def setSearchQuery(self, query: str) -> None:
        self._search_query = query
        self._searchTimer.start(SEARCH_DEBOUNCE_MS)

    @Slot()
    def refresh(self) -> None:
        conn = self._require_conn()
        update_due_from_waiting(conn, now_epoch=to_epoch_seconds(utc_now()))
        conn.commit()

        for v in ("due", "waiting", "archived"):
            self._refresh_view(v)

        self._update_counts()

    # ---------- slots (details) ----------

    @Slot(str, result="QVariantMap")
    def taskDetail(self, task_id: str):
        conn = self._require_conn()
        t = get_task(conn, task_id=task_id)
        if t is None:
            return {}

        tags_list = list_task_tags(conn, task_id=task_id)

        return {
            "id": t.id,
            "title": t.title,
            "note": t.note,
            "status": t.status,
            "createdAt": int(t.created_at),
            "updatedAt": int(t.updated_at),
            "nextReviewAt": int(t.next_review_at) if t.next_review_at is not None else None,
            "archivedAt": int(t.deleted_at) if t.deleted_at is not None else None,
            "purgedAt": int(t.purged_at) if t.purged_at is not None else None,
            "lastCompletedAt": int(t.last_completed_at) if t.last_completed_at is not None else None,
            "reviewCount": int(t.review_count),
            "tagsText": t.tags or "",
            "tags": tags_list,
        }

    @Slot(str, result="QStringList")
    def taskTags(self, task_id: str):
        conn = self._require_conn()
        return list_task_tags(conn, task_id=task_id)

    @Slot(str, result="QVariantList")
    def taskHistory(self, task_id: str):
        conn = self._require_conn()
        hist = completion_history(conn, task_id=task_id)
        return [
            {"completedAt": int(ep), "grade": str(g)}
            for ep, g in hist
        ]

    # ---------- slots (CRUD) ----------

    @Slot(str, str)
    def newTask(self, title: str, note: str) -> None:
        title = (title or "").strip()
        if not title:
            self._set_status("Title is required")
            return
        conn = self._require_conn()
        try:
            with conn:
                create_task(conn, title=title, note=note or "", now=utc_now())
            self._set_status("Task created")
            self.refresh()
        except Exception as e:
            self._set_status(f"Failed to create task: {e}")

    @Slot(str, str, str)
    def editTask(self, task_id: str, title: str, note: str) -> None:
        title = (title or "").strip()
        if not title:
            self._set_status("Title is required")
            return
        conn = self._require_conn()
        try:
            with conn:
                update_task(conn, task_id=task_id, title=title, note=note or "", now=utc_now())
            self._set_status("Task updated")
            self.refresh()
        except Exception as e:
            self._set_status(f"Failed to update task: {e}")

    # ---------- slots (complete/archive/restore/purge) ----------

    @Slot(str, str)
    def completeTask(self, task_id: str, grade: str) -> None:
        if self._view == "waiting":
            self._set_status("Complete is disabled in Waiting")
            return
        if grade not in VALID_GRADES:
            self._set_status("Invalid grade")
            return

        conn = self._require_conn()
        now = utc_now()
        now_epoch = to_epoch_seconds(now)

        try:
            with conn:
                # Ensure min gap for completed_at vs last event
                history = completion_history(conn, task_id=task_id)
                completed_at = now
                if history:
                    last_epoch, _last_grade = history[-1]
                    last_dt = from_epoch_seconds(last_epoch)
                    completed_at = ensure_min_gap(completed_at, last_dt, min_seconds=60)
                completed_at = ceil_to_minute(completed_at)

                add_completion_event(conn, task_id=task_id, completed_at=completed_at, grade=grade)

                history2 = completion_history(conn, task_id=task_id)
                history_times = [from_epoch_seconds(ep) for ep, _g in history2]

                p_target = float(GRADE_P_TARGET[grade])
                next_dt = find_next_review(
                    history_times,
                    completed_at,
                    d=0.5,
                    tau=0.0,
                    s=0.4,
                    p_target=p_target,
                    horizon_days=self.horizonDays,
                )

                set_epoch = to_epoch_seconds(next_dt)
                conn.execute(
                    "UPDATE tasks SET status='waiting', next_review_at=:n, updated_at=:u WHERE id=:id",
                    {"id": task_id, "n": set_epoch, "u": now_epoch},
                )

            self._set_status(f"Completed ({grade})")
            self.refresh()
        except Exception as e:
            self._set_status(f"Failed to complete: {e}")

    @Slot(str)
    def archiveTask(self, task_id: str) -> None:
        conn = self._require_conn()
        try:
            with conn:
                archive_task(conn, task_id=task_id, now_epoch=to_epoch_seconds(utc_now()))
            self._set_status("Archived")
            self.refresh()
        except Exception as e:
            self._set_status(f"Failed to archive: {e}")

    @Slot(str)
    def restoreTask(self, task_id: str) -> None:
        conn = self._require_conn()
        try:
            with conn:
                restore_task(conn, task_id=task_id, now_epoch=to_epoch_seconds(utc_now()))
            self._set_status("Restored")
            self.refresh()
        except Exception as e:
            self._set_status(f"Failed to restore: {e}")

    @Slot(str)
    def purgeTask(self, task_id: str) -> None:
        conn = self._require_conn()
        try:
            with conn:
                purge_task(conn, task_id=task_id, now_epoch=to_epoch_seconds(utc_now()))
            self._set_status("Purged")
            self.refresh()
        except Exception as e:
            self._set_status(f"Failed to purge: {e}")

    # ---------- tags ----------

    @Slot(str, str)
    def addTag(self, task_id: str, tag: str) -> None:
        conn = self._require_conn()
        try:
            with conn:
                add_tag_to_task(conn, task_id=task_id, tag_name=tag, now_epoch=to_epoch_seconds(utc_now()))
            self._set_status("Tag added")
            self.refresh()
        except Exception as e:
            self._set_status(f"Failed to add tag: {e}")

    @Slot(str, str)
    def removeTag(self, task_id: str, tag: str) -> None:
        conn = self._require_conn()
        try:
            with conn:
                remove_tag_from_task(conn, task_id=task_id, tag_name=tag)
            self._set_status("Tag removed")
            self.refresh()
        except Exception as e:
            self._set_status(f"Failed to remove tag: {e}")

    # ---------- clipboard ----------

    @Slot(str)
    def copyText(self, text: str) -> None:
        cb = QGuiApplication.clipboard()
        cb.setText(text or "")
        self._set_status("Copied")

    # ---------- settings ----------

    @Slot(int)
    def setHorizonDays(self, days: int) -> None:
        self._settings.set_horizon_days(days)
        self.horizonDaysChanged.emit()
        self._set_status("Horizon days updated (applies to future completes)")

    @Slot(str)
    def setTheme(self, theme: str) -> None:
        self._settings.set_theme(theme)
        self.themeChanged.emit()
        self.backgroundChanged.emit()
        self._set_status("Theme updated")

    @Slot(str)
    def setDbPath(self, path: str) -> None:
        p = Path(path).expanduser()
        self._settings.set_db_path(str(p))
        self._db_path = p

        if self._conn is not None:
            self._conn.close()
            self._conn = None

        self._open_db()
        self.dbLabelChanged.emit()
        self._set_status("DB switched")
        self.refresh()

    @Slot(str)
    def backupDbTo(self, dest_path: str) -> None:
        dest = Path(dest_path).expanduser()
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            if self._conn is not None:
                self._conn.commit()
            shutil.copy2(self._db_path, dest)
            self._set_status(f"Backup created: {dest.name}")
        except Exception as e:
            self._set_status(f"Backup failed: {e}")

    @Slot()
    def recalculateAll(self) -> None:
        conn = self._require_conn()
        now = utc_now()
        now_epoch = to_epoch_seconds(now)

        try:
            with conn:
                rows = conn.execute(
                    """
                    SELECT id FROM tasks
                    WHERE deleted_at IS NULL AND purged_at IS NULL AND status IN ('due','waiting')
                    """
                ).fetchall()

                for r in rows:
                    task_id = r["id"]
                    hist = completion_history(conn, task_id=task_id)
                    if not hist:
                        conn.execute(
                            "UPDATE tasks SET status='due', next_review_at=NULL, updated_at=:u WHERE id=:id",
                            {"id": task_id, "u": now_epoch},
                        )
                        continue

                    history_times = [from_epoch_seconds(ep) for ep, _g in hist]
                    last_grade = hist[-1][1]
                    p_target = float(GRADE_P_TARGET.get(last_grade, 0.90))
                    last_completed_dt = history_times[-1]

                    next_dt = find_next_review(
                        history_times,
                        last_completed_dt,
                        d=0.5,
                        tau=0.0,
                        s=0.4,
                        p_target=p_target,
                        horizon_days=self.horizonDays,
                    )
                    conn.execute(
                        "UPDATE tasks SET next_review_at=:n, status='waiting', updated_at=:u WHERE id=:id",
                        {"id": task_id, "n": to_epoch_seconds(next_dt), "u": now_epoch},
                    )

                update_due_from_waiting(conn, now_epoch=now_epoch)

            self._set_status("Recalculated all tasks")
            self.refresh()
        except Exception as e:
            self._set_status(f"Recalculate failed: {e}")
