from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from taskmaster.constants import SCHEMA_VERSION


@dataclass(frozen=True)
class DbInfo:
    path: Path
    schema_version: int | None


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def get_schema_version(conn: sqlite3.Connection) -> int | None:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'"
    ).fetchone()
    if not row:
        return None

    row2 = conn.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
    if not row2:
        return None
    return int(row2["version"])


def migrate(conn: sqlite3.Connection) -> int:
    current = get_schema_version(conn)

    if current is None:
        _create_v1(conn)
        current = 1

    if current != SCHEMA_VERSION:
        raise RuntimeError(
            f"Unsupported schema version: {current} (expected {SCHEMA_VERSION})"
        )

    return current


def db_info(conn: sqlite3.Connection, db_path: Path) -> DbInfo:
    return DbInfo(path=db_path, schema_version=get_schema_version(conn))


def _create_v1(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        PRAGMA foreign_keys = ON;

        CREATE TABLE IF NOT EXISTS tasks (
            id             TEXT PRIMARY KEY,
            title          TEXT NOT NULL,
            note           TEXT NOT NULL DEFAULT '',
            status         TEXT NOT NULL,
            created_at     INTEGER NOT NULL,
            updated_at     INTEGER NOT NULL,
            next_review_at INTEGER,
            deleted_at     INTEGER,
            purged_at      INTEGER,
            CHECK (status IN ('due', 'waiting', 'archived'))
        );

        CREATE TABLE IF NOT EXISTS completion_events (
            id           TEXT PRIMARY KEY,
            task_id      TEXT NOT NULL,
            completed_at INTEGER NOT NULL,
            grade        TEXT NOT NULL,
            FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS task_tags (
            id         TEXT PRIMARY KEY,
            name       TEXT NOT NULL UNIQUE,
            created_at INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS task_tag_map (
            task_id TEXT NOT NULL,
            tag_id  TEXT NOT NULL,
            PRIMARY KEY(task_id, tag_id),
            FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE CASCADE,
            FOREIGN KEY(tag_id)  REFERENCES task_tags(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_tasks_status_next_review
            ON tasks(status, next_review_at);

        CREATE INDEX IF NOT EXISTS idx_tasks_deleted
            ON tasks(deleted_at);

        CREATE INDEX IF NOT EXISTS idx_completion_events_task_time
            ON completion_events(task_id, completed_at);

        CREATE INDEX IF NOT EXISTS idx_completion_events_task_grade_time
            ON completion_events(task_id, grade, completed_at);

        CREATE INDEX IF NOT EXISTS idx_tag_map_tag
            ON task_tag_map(tag_id);

        CREATE INDEX IF NOT EXISTS idx_tag_map_task
            ON task_tag_map(task_id);
        """
    )

    conn.execute("DELETE FROM schema_version")
    conn.execute("INSERT INTO schema_version(version) VALUES (?)", (SCHEMA_VERSION,))
    conn.commit()
