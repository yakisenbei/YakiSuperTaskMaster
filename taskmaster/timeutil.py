from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


def utc_now() -> datetime:
    return datetime.now(UTC)


def to_epoch_seconds(dt: datetime) -> int:
    if dt.tzinfo is None:
        raise ValueError("datetime must be timezone-aware")
    return int(dt.timestamp())


def from_epoch_seconds(epoch_seconds: int) -> datetime:
    return datetime.fromtimestamp(int(epoch_seconds), tz=UTC)


def ceil_to_minute(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        raise ValueError("datetime must be timezone-aware")
    # Ceiling to the next minute (or keep if already on minute boundary)
    truncated = dt.replace(second=0, microsecond=0)
    if dt == truncated:
        return dt
    return truncated + timedelta(minutes=1)


def ensure_min_gap(candidate: datetime, reference: datetime, *, min_seconds: int) -> datetime:
    if candidate.tzinfo is None or reference.tzinfo is None:
        raise ValueError("datetime must be timezone-aware")
    min_dt = reference + timedelta(seconds=min_seconds)
    return max(candidate, min_dt)


def format_local(dt: datetime | None) -> str:
    if dt is None:
        return ""
    # Convert to local time for display
    local_dt = dt.astimezone()
    return local_dt.strftime("%Y-%m-%d %H:%M")


@dataclass(frozen=True)
class Remaining:
    days: int
    hours: int
    minutes: int

    def __str__(self) -> str:
        parts: list[str] = []
        if self.days:
            parts.append(f"{self.days}d")
        if self.hours or self.days:
            parts.append(f"{self.hours}h")
        parts.append(f"{self.minutes}m")
        return " ".join(parts)


def remaining_until(now: datetime, target: datetime | None) -> str:
    if target is None:
        return ""
    if now.tzinfo is None or target.tzinfo is None:
        raise ValueError("datetime must be timezone-aware")
    delta = target - now
    total_seconds = int(delta.total_seconds())
    if total_seconds <= 0:
        return "0m"

    minutes = total_seconds // 60
    days = minutes // (24 * 60)
    minutes -= days * 24 * 60
    hours = minutes // 60
    minutes -= hours * 60
    return str(Remaining(days=days, hours=hours, minutes=minutes))
