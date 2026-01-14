from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtCore import Slot

from taskmaster.repository import TaskRow
from taskmaster.timeutil import format_local, from_epoch_seconds, remaining_until, utc_now


@dataclass(frozen=True)
class Column:
    header: str
    key: str


class TaskTableModel(QAbstractTableModel):
    def __init__(self, columns: list[Column], parent=None) -> None:
        super().__init__(parent)
        self._columns = columns
        self._rows: list[TaskRow] = []

    def setRows(self, rows: list[TaskRow]) -> None:  # Qt slot style
        self.beginResetModel()
        self._rows = list(rows)
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # type: ignore[override]
        if parent.isValid():
            return 0
        return len(self._rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # type: ignore[override]
        if parent.isValid():
            return 0
        return len(self._columns)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):  # type: ignore[override]
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal and 0 <= section < len(self._columns):
            return self._columns[section].header
        return None

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):  # type: ignore[override]
        if not index.isValid() or not (0 <= index.row() < len(self._rows)):
            return None

        row = self._rows[index.row()]
        col = self._columns[index.column()].key

        if role == Qt.DisplayRole:
            return self._display_value(row, col)

        if role == Qt.UserRole:
            return row.id

        return None

    def roleNames(self):  # type: ignore[override]
        roles = super().roleNames()
        roles[int(Qt.UserRole)] = b"taskId"
        return roles

    @Slot(int, result=str)
    def taskIdAtRow(self, row: int) -> str:
        if not (0 <= row < len(self._rows)):
            return ""
        return self._rows[row].id

    @Slot(str, result=int)
    def findRowByTaskId(self, task_id: str) -> int:
        for i, r in enumerate(self._rows):
            if r.id == task_id:
                return i
        return -1

    @Slot(int, int, result=str)
    def cellDisplay(self, row: int, column: int) -> str:
        if not (0 <= row < len(self._rows)):
            return ""
        if not (0 <= column < len(self._columns)):
            return ""
        return self._display_value(self._rows[row], self._columns[column].key)

    def rowAt(self, row: int) -> TaskRow | None:
        if not (0 <= row < len(self._rows)):
            return None
        return self._rows[row]

    def _display_value(self, row: TaskRow, col: str) -> str:
        now = utc_now()

        if col == "title":
            return row.title
        if col == "last_completed":
            return format_local(from_epoch_seconds(row.last_completed_at)) if row.last_completed_at else ""
        if col == "review_count":
            return str(row.review_count)
        if col == "next_review_at":
            return format_local(from_epoch_seconds(row.next_review_at)) if row.next_review_at else ""
        if col == "remaining":
            return remaining_until(now, from_epoch_seconds(row.next_review_at)) if row.next_review_at else ""
        if col == "archived_at":
            return format_local(from_epoch_seconds(row.deleted_at)) if row.deleted_at else ""
        if col == "tags":
            return row.tags

        return ""
