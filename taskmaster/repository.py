from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from taskmaster.constants import VALID_GRADES
from taskmaster.timeutil import to_epoch_seconds


@dataclass(frozen=True)
class TaskRow:
    id: str
    title: str
    note: str
    status: str
    created_at: int
    updated_at: int
    next_review_at: int | None
    deleted_at: int | None
    purged_at: int | None
    tags: str
    last_completed_at: int | None
    review_count: int


def _uuid() -> str:
    return str(uuid.uuid4())


def create_task(conn: sqlite3.Connection, *, title: str, note: str, now: datetime) -> str:
    task_id = _uuid()
    now_ep = to_epoch_seconds(now)
    conn.execute(
        """
        INSERT INTO tasks(id, title, note, status, created_at, updated_at, next_review_at, deleted_at, purged_at)
        VALUES(:id, :title, :note, 'due', :now, :now, NULL, NULL, NULL)
        """,
        {"id": task_id, "title": title, "note": note, "now": now_ep},
    )
    return task_id


def update_task(conn: sqlite3.Connection, *, task_id: str, title: str, note: str, now: datetime) -> None:
    conn.execute(
        """
        UPDATE tasks
        SET title = :title,
            note = :note,
            updated_at = :now
        WHERE id = :id
        """,
        {"id": task_id, "title": title, "note": note, "now": to_epoch_seconds(now)},
    )


def list_tasks(
    conn: sqlite3.Connection,
    *,
    view: str,
    q_like: str | None,
    tags: list[str],
) -> list[TaskRow]:
    base_where, order_by = _view_where_and_order(view)

    params: dict[str, object] = {}
    where_parts: list[str] = [base_where]

    if q_like:
        where_parts.append("(t.title LIKE :q OR t.note LIKE :q)")
        params["q"] = q_like

    join_tags = ""
    having = ""

    if tags:
        join_tags = "\nJOIN task_tag_map m ON m.task_id = t.id\nJOIN task_tags g ON g.id = m.tag_id"
        placeholders = []
        for i, tag in enumerate(tags, start=1):
            key = f"tag{i}"
            params[key] = tag
            placeholders.append(f":{key}")
        where_parts.append(f"g.name IN ({', '.join(placeholders)})")
        having = f"HAVING COUNT(DISTINCT g.name) = {len(tags)}"

    sql = f"""
    WITH task_stats AS (
        SELECT
            t.*, 
            (SELECT MAX(ce.completed_at) FROM completion_events ce WHERE ce.task_id = t.id) AS last_completed_at,
            (SELECT COUNT(*) FROM completion_events ce WHERE ce.task_id = t.id) AS review_count,
            (SELECT COALESCE(GROUP_CONCAT(g2.name, ', '), '')
             FROM task_tag_map m2
             JOIN task_tags g2 ON g2.id = m2.tag_id
             WHERE m2.task_id = t.id
            ) AS tags
        FROM tasks t
    )
    SELECT
        t.id,
        t.title,
        t.note,
        t.status,
        t.created_at,
        t.updated_at,
        t.next_review_at,
        t.deleted_at,
        t.purged_at,
        t.tags,
        t.last_completed_at,
        t.review_count
    FROM task_stats t
    {join_tags}
    WHERE {' AND '.join(where_parts)}
    GROUP BY t.id
    {having}
    ORDER BY {order_by}
    """

    rows = conn.execute(sql, params).fetchall()
    return [
        TaskRow(
            id=r["id"],
            title=r["title"],
            note=r["note"],
            status=r["status"],
            created_at=r["created_at"],
            updated_at=r["updated_at"],
            next_review_at=r["next_review_at"],
            deleted_at=r["deleted_at"],
            purged_at=r["purged_at"],
            tags=r["tags"] or "",
            last_completed_at=r["last_completed_at"],
            review_count=int(r["review_count"] or 0),
        )
        for r in rows
    ]


def get_task(conn: sqlite3.Connection, *, task_id: str) -> TaskRow | None:
    row = conn.execute(
        """
        WITH task_stats AS (
            SELECT
                t.*, 
                (SELECT MAX(ce.completed_at) FROM completion_events ce WHERE ce.task_id = t.id) AS last_completed_at,
                (SELECT COUNT(*) FROM completion_events ce WHERE ce.task_id = t.id) AS review_count,
                (SELECT COALESCE(GROUP_CONCAT(g2.name, ', '), '')
                 FROM task_tag_map m2
                 JOIN task_tags g2 ON g2.id = m2.tag_id
                 WHERE m2.task_id = t.id
                ) AS tags
            FROM tasks t
            WHERE t.id = :id
        )
        SELECT
            t.id,
            t.title,
            t.note,
            t.status,
            t.created_at,
            t.updated_at,
            t.next_review_at,
            t.deleted_at,
            t.purged_at,
            t.tags,
            t.last_completed_at,
            t.review_count
        FROM task_stats t
        """,
        {"id": task_id},
    ).fetchone()
    if not row:
        return None
    return TaskRow(
        id=row["id"],
        title=row["title"],
        note=row["note"],
        status=row["status"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        next_review_at=row["next_review_at"],
        deleted_at=row["deleted_at"],
        purged_at=row["purged_at"],
        tags=row["tags"] or "",
        last_completed_at=row["last_completed_at"],
        review_count=int(row["review_count"] or 0),
    )


def list_task_tags(conn: sqlite3.Connection, *, task_id: str) -> list[str]:
    rows = conn.execute(
        """
        SELECT g.name
        FROM task_tag_map m
        JOIN task_tags g ON g.id = m.tag_id
        WHERE m.task_id = :task_id
        ORDER BY g.name ASC
        """,
        {"task_id": task_id},
    ).fetchall()
    return [str(r["name"]) for r in rows]


def due_waiting_counts(conn: sqlite3.Connection) -> tuple[int, int]:
    due = conn.execute(
        """
        SELECT COUNT(*) AS c
        FROM tasks
        WHERE deleted_at IS NULL AND purged_at IS NULL AND status = 'due'
        """
    ).fetchone()["c"]
    waiting = conn.execute(
        """
        SELECT COUNT(*) AS c
        FROM tasks
        WHERE deleted_at IS NULL AND purged_at IS NULL AND status = 'waiting'
        """
    ).fetchone()["c"]
    return int(due), int(waiting)


def add_completion_event(
    conn: sqlite3.Connection,
    *,
    task_id: str,
    completed_at: datetime,
    grade: str,
) -> str:
    if grade not in VALID_GRADES:
        raise ValueError(f"invalid grade: {grade}")

    event_id = _uuid()
    conn.execute(
        """
        INSERT INTO completion_events(id, task_id, completed_at, grade)
        VALUES(:id, :task_id, :completed_at, :grade)
        """,
        {
            "id": event_id,
            "task_id": task_id,
            "completed_at": to_epoch_seconds(completed_at),
            "grade": grade,
        },
    )
    return event_id


def completion_history(conn: sqlite3.Connection, *, task_id: str) -> list[tuple[int, str]]:
    rows = conn.execute(
        """
        SELECT completed_at, grade
        FROM completion_events
        WHERE task_id = :task_id
        ORDER BY completed_at ASC
        """,
        {"task_id": task_id},
    ).fetchall()
    return [(int(r["completed_at"]), str(r["grade"])) for r in rows]


def set_task_waiting(conn: sqlite3.Connection, *, task_id: str, next_review_at: int, now: int) -> None:
    conn.execute(
        """
        UPDATE tasks
        SET status = 'waiting', next_review_at = :next_review_at, updated_at = :now
        WHERE id = :id
        """,
        {"id": task_id, "next_review_at": next_review_at, "now": now},
    )


def update_due_from_waiting(conn: sqlite3.Connection, *, now_epoch: int) -> int:
    cur = conn.execute(
        """
        UPDATE tasks
        SET status = 'due', updated_at = :now
        WHERE status = 'waiting'
          AND deleted_at IS NULL
          AND purged_at IS NULL
          AND next_review_at IS NOT NULL
          AND next_review_at <= :now
        """,
        {"now": now_epoch},
    )
    return int(cur.rowcount)


def archive_task(conn: sqlite3.Connection, *, task_id: str, now_epoch: int) -> None:
    conn.execute(
        """
        UPDATE tasks
        SET deleted_at = :now,
            status = 'archived',
            updated_at = :now
        WHERE id = :id
          AND deleted_at IS NULL
          AND (purged_at IS NULL)
        """,
        {"id": task_id, "now": now_epoch},
    )


def restore_task(conn: sqlite3.Connection, *, task_id: str, now_epoch: int) -> None:
    conn.execute(
        """
        UPDATE tasks
        SET deleted_at = NULL,
            status = CASE
                WHEN next_review_at IS NOT NULL AND next_review_at <= :now THEN 'due'
                ELSE 'waiting'
            END,
            updated_at = :now
        WHERE id = :id
          AND deleted_at IS NOT NULL
          AND (purged_at IS NULL)
        """,
        {"id": task_id, "now": now_epoch},
    )


def purge_task(conn: sqlite3.Connection, *, task_id: str, now_epoch: int) -> None:
    conn.execute(
        """
        UPDATE tasks
        SET purged_at = :now,
            updated_at = :now
        WHERE id = :id
          AND deleted_at IS NOT NULL
          AND purged_at IS NULL
        """,
        {"id": task_id, "now": now_epoch},
    )


def normalize_tag(name: str) -> str:
    name = name.strip().lower()
    # collapse whitespace (including full-width spaces)
    import re

    name = re.sub(r"[\s\u3000]+", " ", name)
    return name


def ensure_tag(conn: sqlite3.Connection, *, name: str, now_epoch: int) -> str:
    name = normalize_tag(name)
    tag_id = _uuid()
    conn.execute(
        """
        INSERT INTO task_tags(id, name, created_at)
        VALUES(:id, :name, :now)
        ON CONFLICT(name) DO NOTHING
        """,
        {"id": tag_id, "name": name, "now": now_epoch},
    )
    row = conn.execute("SELECT id FROM task_tags WHERE name = :name", {"name": name}).fetchone()
    return str(row["id"])


def tag_count(conn: sqlite3.Connection, *, task_id: str) -> int:
    row = conn.execute(
        "SELECT COUNT(*) AS cnt FROM task_tag_map WHERE task_id = :task_id",
        {"task_id": task_id},
    ).fetchone()
    return int(row["cnt"])


def add_tag_to_task(conn: sqlite3.Connection, *, task_id: str, tag_name: str, now_epoch: int) -> None:
    if tag_count(conn, task_id=task_id) >= 5:
        raise ValueError("tag limit reached (max 5)")
    tag_id = ensure_tag(conn, name=tag_name, now_epoch=now_epoch)
    conn.execute(
        "INSERT OR IGNORE INTO task_tag_map(task_id, tag_id) VALUES(:task_id, :tag_id)",
        {"task_id": task_id, "tag_id": tag_id},
    )


def remove_tag_from_task(conn: sqlite3.Connection, *, task_id: str, tag_name: str) -> None:
    tag_name = normalize_tag(tag_name)
    row = conn.execute("SELECT id FROM task_tags WHERE name = :name", {"name": tag_name}).fetchone()
    if not row:
        return
    conn.execute(
        "DELETE FROM task_tag_map WHERE task_id = :task_id AND tag_id = :tag_id",
        {"task_id": task_id, "tag_id": row["id"]},
    )


def _view_where_and_order(view: str) -> tuple[str, str]:
    if view == "due":
        base_where = "t.deleted_at IS NULL AND t.purged_at IS NULL AND t.status = 'due'"
        order_by = "CASE WHEN t.next_review_at IS NULL THEN 1 ELSE 0 END, t.next_review_at ASC, t.updated_at ASC"
        return base_where, order_by

    if view == "waiting":
        base_where = "t.deleted_at IS NULL AND t.purged_at IS NULL AND t.status = 'waiting'"
        order_by = "CASE WHEN t.next_review_at IS NULL THEN 1 ELSE 0 END, t.next_review_at DESC, t.updated_at DESC"
        return base_where, order_by

    if view == "archived":
        base_where = "t.deleted_at IS NOT NULL AND t.purged_at IS NULL AND t.status = 'archived'"
        order_by = "t.deleted_at DESC, t.updated_at DESC"
        return base_where, order_by

    raise ValueError(f"invalid view: {view}")
