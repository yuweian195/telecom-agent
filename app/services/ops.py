"""AIOps analysis service."""

from __future__ import annotations

import csv
import io
import uuid
from datetime import datetime

from app.db import OpsRepository, get_repository
from app.graph.ops_workflow import get_ops_graph
from app.llm.client import LLMClient, get_llm_client
from app.ops.case_retriever import get_case_retriever
from app.ops.topology import load_topology
from app.schemas import (
    Alarm,
    CaseMatch,
    OpsAnalyzeRequest,
    OpsRun,
    OpsRunListItem,
    Severity,
    Topology,
)


class OpsService:
    def __init__(
        self,
        repository: OpsRepository | None = None,
        llm: LLMClient | None = None,
    ) -> None:
        self.repository = repository or get_repository()
        self.llm = llm or get_llm_client()

    def analyze(self, payload: OpsAnalyzeRequest) -> OpsRun:
        run_id = uuid.uuid4().hex[:12]
        created_at = datetime.now().isoformat(timespec="seconds")
        alarms_raw = [item.model_dump() for item in payload.alarms or []]
        initial_state = {
            "run_id": run_id,
            "created_at": created_at,
            "llm_mode": self.llm.mode,
            "repository": self.repository,
            "alarms_raw": alarms_raw,
            "window_minutes": payload.window_minutes,
            "trace": [],
        }
        final_state = get_ops_graph().invoke(initial_state)
        return OpsRun(
            id=run_id,
            created_at=created_at,
            total_alarms=len(final_state["alarms"]),
            cluster_count=len(final_state["clusters"]),
            compression_ratio=final_state["compression_ratio"],
            overall_severity=Severity(final_state["overall_severity"]),
            clusters=final_state["clusters"],
            summary=final_state["summary"],
            dispatch_plan=final_state.get("dispatch_plan", []),
            review_required=final_state.get("review_required", False),
            topology=Topology.model_validate(final_state["topology"]),
            trace=final_state["trace"],
            llm_mode=final_state.get("llm_mode", self.llm.mode),
        )

    def analyze_csv_bytes(self, content: bytes) -> OpsRun:
        text = content.decode("utf-8-sig", errors="ignore")
        alarms: list[Alarm] = []
        for row in csv.DictReader(io.StringIO(text)):
            try:
                alarms.append(Alarm.model_validate(row))
            except Exception:
                continue
        if not alarms:
            raise ValueError("CSV 中没有解析出有效告警")
        return self.analyze(
            OpsAnalyzeRequest(alarms=alarms, use_sample=False)
        )

    def get_run(self, run_id: str) -> OpsRun | None:
        payload = self.repository.get_run(run_id)
        if payload is None:
            return None
        return OpsRun.model_validate(payload)

    def list_recent(self, limit: int = 20) -> list[OpsRunListItem]:
        return [
            OpsRunListItem(
                id=item["id"],
                created_at=item["created_at"],
                total_alarms=item["total_alarms"],
                cluster_count=item["cluster_count"],
                compression_ratio=item["compression_ratio"],
                overall_severity=Severity(item["overall_severity"]),
            )
            for item in self.repository.list_runs(limit)
        ]

    def topology(self) -> Topology:
        return load_topology().topology

    def search_cases(
        self, causes: str = "", symptoms: str = "", top_k: int = 5
    ) -> list[CaseMatch]:
        return get_case_retriever().search(causes, symptoms, top_k=top_k)

    def case_count(self) -> int:
        return get_case_retriever().count


_service: OpsService | None = None


def get_service() -> OpsService:
    global _service
    if _service is None:
        _service = OpsService()
    return _service
