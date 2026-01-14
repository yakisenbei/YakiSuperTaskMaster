from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QSettings

from taskmaster.constants import (
    APP_NAME,
    APP_ORG,
    DEFAULT_HORIZON_DAYS,
    MAX_HORIZON_DAYS,
    MIN_HORIZON_DAYS,
)


@dataclass(frozen=True)
class AppSettingsSnapshot:
    db_path: str | None
    horizon_days: int
    theme: str


class AppSettings:
    def __init__(self) -> None:
        self._q = QSettings(APP_ORG, APP_NAME)

    def snapshot(self) -> AppSettingsSnapshot:
        return AppSettingsSnapshot(
            db_path=self.db_path(),
            horizon_days=self.horizon_days(),
            theme=self.theme(),
        )

    def db_path(self) -> str | None:
        value = self._q.value("storage/db_path", "", type=str)
        return value or None

    def set_db_path(self, path: str | None) -> None:
        self._q.setValue("storage/db_path", path or "")

    def horizon_days(self) -> int:
        value = self._q.value("general/horizon_days", DEFAULT_HORIZON_DAYS, type=int)
        return max(MIN_HORIZON_DAYS, min(MAX_HORIZON_DAYS, int(value)))

    def set_horizon_days(self, days: int) -> None:
        days = max(MIN_HORIZON_DAYS, min(MAX_HORIZON_DAYS, int(days)))
        self._q.setValue("general/horizon_days", days)

    def theme(self) -> str:
        value = self._q.value("ui/theme", "light", type=str)
        return value if value in ("light", "dark") else "light"

    def set_theme(self, theme: str) -> None:
        if theme not in ("light", "dark"):
            return
        self._q.setValue("ui/theme", theme)


def default_db_path() -> Path:
    base = Path.home() / ".local" / "share"
    base.mkdir(parents=True, exist_ok=True)
    return base / "taskmaster.db"
