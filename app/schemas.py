"""Pydantic models for alarms, topology, diagnosis and API."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class Severity(StrEnum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"


class Alarm(BaseModel):
    alarm_id: str
    alarm_time: datetime
    ne_id: str
    ne_name: str
    ne_type: str
    alarm_type: str
    severity: Severity
    description: str = ""
    region: str = ""
    vendor: str = ""


class TopologyNode(BaseModel):
    id: str
    name: str
    type: str
    region: str = ""
    vendor: str = ""


class TopologyEdge(BaseModel):
    source: str
    target: str
    relation: str = "uplink"


class Topology(BaseModel):
    nodes: list[TopologyNode] = Field(default_factory=list)
    edges: list[TopologyEdge] = Field(default_factory=list)


class CaseRecord(BaseModel):
    id: str
    title: str
    cause_type: str
    symptoms: list[str] = Field(default_factory=list)
    root_ne_type: str = ""
    resolution: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class CaseMatch(BaseModel):
    case: CaseRecord
    score: float


class AlarmCluster(BaseModel):
    id: str
    root_alarm: Alarm | None = None
    root_ne_id: str = ""
    root_ne_name: str = ""
    root_ne_type: str = ""
    cause_type: str = "UNKNOWN"
    cause_label: str = "未定位"
    confidence: float = 0.0
    severity: Severity = Severity.P4
    alarm_count: int = 0
    affected_node_ids: list[str] = Field(default_factory=list)
    affected_node_names: list[str] = Field(default_factory=list)
    time_start: datetime | None = None
    time_end: datetime | None = None
    evidence: list[str] = Field(default_factory=list)
    similar_cases: list[CaseMatch] = Field(default_factory=list)
    plan_steps: list[str] = Field(default_factory=list)
    needs_human_review: bool = False


class OpsAnalyzeRequest(BaseModel):
    alarms: list[Alarm] | None = None
    use_sample: bool = True
    window_minutes: int = 10


class TraceStep(BaseModel):
    node: str
    label: str
    status: str = "ok"
    duration_ms: int = 0
    summary: str = ""


class OpsRun(BaseModel):
    id: str
    created_at: datetime = Field(default_factory=datetime.now)
    total_alarms: int = 0
    cluster_count: int = 0
    compression_ratio: float = 0.0
    overall_severity: Severity = Severity.P4
    clusters: list[AlarmCluster] = Field(default_factory=list)
    summary: str = ""
    dispatch_plan: list[str] = Field(default_factory=list)
    review_required: bool = False
    topology: Topology | None = None
    trace: list[TraceStep] = Field(default_factory=list)
    llm_mode: str = "offline"


class OpsRunListItem(BaseModel):
    id: str
    created_at: datetime
    total_alarms: int
    cluster_count: int
    compression_ratio: float
    overall_severity: Severity


class HealthResponse(BaseModel):
    status: str
    version: str
    llm_mode: str
    nodes: int
    cases: int


OpsAnalyzeRequest.model_rebuild()
OpsRun.model_rebuild()
