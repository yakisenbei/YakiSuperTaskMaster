from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta

from taskmaster.constants import DEFAULT_DECAY_D, DEFAULT_NOISE_S, DEFAULT_TAU
from taskmaster.timeutil import ceil_to_minute, ensure_min_gap


@dataclass(frozen=True)
class ReviewParams:
    d: float = DEFAULT_DECAY_D
    s: float = DEFAULT_NOISE_S
    tau: float = DEFAULT_TAU
    p_target: float = 0.90
    horizon_days: int = 365


_MIN_DELTA_DAYS = 60.0 / 86400.0  # 1 minute in days


def _delta_days(eval_time: datetime, t_k: datetime) -> float:
    delta = (eval_time - t_k).total_seconds() / 86400.0
    return max(delta, _MIN_DELTA_DAYS)


def base_activation(history_times: list[datetime], eval_time: datetime, d: float) -> float:
    if not history_times:
        raise ValueError("history_times must not be empty for base_activation")

    s = 0.0
    for t_k in history_times:
        s += _delta_days(eval_time, t_k) ** (-d)
    return math.log(s)


def recall_prob(B: float, tau: float, s: float) -> float:
    return 1.0 / (1.0 + math.exp(-((B - tau) / s)))


def find_next_review(
    history_times: list[datetime],
    now: datetime,
    *,
    d: float,
    tau: float,
    s: float,
    p_target: float,
    horizon_days: int,
    max_search_days: float = 365.0,
    iters: int = 40,
) -> datetime:
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")

    # Spec default: called after completion; history must have at least 1 event.
    if not history_times:
        raise ValueError("history_times must not be empty")

    T_target = now + timedelta(days=horizon_days)

    lo = 0.0
    hi = float(max_search_days)

    for _ in range(iters):
        mid = (lo + hi) / 2.0
        candidate_time = now + timedelta(days=mid)
        # Apply minimum interval rule (>= now + 1 minute)
        candidate_time = ensure_min_gap(candidate_time, now, min_seconds=60)

        B_future = base_activation(history_times + [candidate_time], T_target, d)
        p = recall_prob(B_future, tau, s)

        if p >= p_target:
            hi = mid
        else:
            lo = mid

    result = now + timedelta(days=hi)
    result = ensure_min_gap(result, now, min_seconds=60)
    return ceil_to_minute(result)
