"""State for the NOC analysis workflow."""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict


class OpsState(TypedDict, total=False):
    run_id: str
    created_at: str
    llm_mode: str
    repository: Any

    alarms_raw: list[dict]
    window_minutes: int
    alarms: list[dict]
    clusters: list[dict]
    topology: dict

    overall_severity: str
    compression_ratio: float
    summary: str
    dispatch_plan: list[str]
    review_required: bool

    trace: Annotated[list[dict], operator.add]
