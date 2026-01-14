from __future__ import annotations

APP_ORG = "Yaki"
APP_NAME = "TaskMaster"

SCHEMA_VERSION = 1

DEFAULT_HORIZON_DAYS = 365
MAX_HORIZON_DAYS = 365
MIN_HORIZON_DAYS = 1

# Scheduling constants (tunable)
DEFAULT_DECAY_D = 0.5
DEFAULT_NOISE_S = 0.4
DEFAULT_TAU = 0.0
DEFAULT_P_TARGET = 0.90

GRADE_P_TARGET = {
    "again": 0.98,
    "hard": 0.95,
    "good": 0.90,
    "easy": 0.85,
}

VALID_GRADES = tuple(GRADE_P_TARGET.keys())

# UI
SEARCH_DEBOUNCE_MS = 150
DUE_UPDATE_INTERVAL_MS = 60_000
