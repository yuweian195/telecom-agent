"""Alarm loading, normalization and time windows."""

from __future__ import annotations

import csv
from datetime import datetime, timedelta
from pathlib import Path

from app.config import get_settings
from app.schemas import Alarm, Severity

SEVERITY_RANK = {Severity.P1: 1, Severity.P2: 2, Severity.P3: 3, Severity.P4: 4}


def load_alarms_csv(path: Path | None = None) -> list[Alarm]:
    target = Path(path or get_settings().alarms_csv)
    alarms: list[Alarm] = []
    with target.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            try:
                alarms.append(Alarm.model_validate(row))
            except Exception:
                continue
    alarms.sort(key=lambda item: item.alarm_time)
    return alarms


def dedupe_alarms(alarms: list[Alarm]) -> list[Alarm]:
    seen: set[str] = set()
    unique: list[Alarm] = []
    for alarm in alarms:
        if alarm.alarm_id in seen:
            continue
        seen.add(alarm.alarm_id)
        unique.append(alarm)
    return sorted(unique, key=lambda item: item.alarm_time)


def window_start(moment: datetime, minutes: int = 10) -> datetime:
    minute = (moment.minute // max(1, minutes)) * max(1, minutes)
    return moment.replace(minute=minute, second=0, microsecond=0)


def window_seconds(minutes: int) -> int:
    return max(1, minutes) * 60


def duration_seconds(start: datetime | None, end: datetime | None) -> float:
    if start is None or end is None:
        return 0.0
    return (end - start).total_seconds()


def in_window(moment: datetime, anchor: datetime, minutes: int) -> bool:
    return abs((moment - anchor).total_seconds()) <= timedelta(minutes=minutes).total_seconds()
