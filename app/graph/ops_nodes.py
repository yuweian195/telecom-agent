"""LangGraph nodes for NOC alarm analysis."""

from __future__ import annotations

import time

from app.db import get_repository
from app.graph.ops_state import OpsState
from app.llm.client import get_llm_client
from app.ops.alarms import dedupe_alarms, load_alarms_csv
from app.ops.case_retriever import get_case_retriever
from app.ops.compression import compress_alarms
from app.ops.topology import load_topology
from app.schemas import Alarm, AlarmCluster, Severity

SEVERITY_RANK = {Severity.P1: 1, Severity.P2: 2, Severity.P3: 3, Severity.P4: 4}


def _step(node: str, label: str, started: float, summary: str) -> dict:
    return {
        "node": node,
        "label": label,
        "status": "ok",
        "duration_ms": int((time.perf_counter() - started) * 1000),
        "summary": summary,
    }


def load_alarms_node(state: OpsState) -> dict:
    started = time.perf_counter()
    raw = state.get("alarms_raw") or []
    if raw:
        alarms = [Alarm.model_validate(item) for item in raw]
    else:
        alarms = load_alarms_csv()
    alarms = dedupe_alarms(alarms)
    p1 = sum(1 for item in alarms if item.severity == Severity.P1)
    summary = f"接入 {len(alarms)} 条告警，其中 P1 {p1} 条"
    return {
        "alarms": [item.model_dump() for item in alarms],
        "trace": [_step("load_alarms", "接入告警", started, summary)],
    }


def compress_node(state: OpsState) -> dict:
    started = time.perf_counter()
    alarms = [Alarm.model_validate(item) for item in state["alarms"]]
    topology = load_topology()
    clusters = compress_alarms(
        alarms,
        topology,
        get_case_retriever(),
        window_minutes=int(state.get("window_minutes", 10)),
    )
    ratio = 1 - len(clusters) / max(1, len(alarms))
    summary = (
        f"压缩为 {len(clusters)} 起事件，压缩率 {ratio:.1%}；"
        f"P1 事件 {sum(1 for item in clusters if item.severity == Severity.P1)} 起"
    )
    return {
        "clusters": [item.model_dump() for item in clusters],
        "topology": topology.topology.model_dump(),
        "compression_ratio": round(ratio, 4),
        "trace": [_step("compress_alarms", "告警压缩与关联", started, summary)],
    }


def diagnose_node(state: OpsState) -> dict:
    started = time.perf_counter()
    clusters = [AlarmCluster.model_validate(item) for item in state["clusters"]]
    high_confidence = sum(1 for item in clusters if item.confidence >= 0.6)
    summary = (
        f"完成 {len(clusters)} 起事件根因定位，"
        f"{high_confidence} 起置信度 ≥ 60%，"
        f"{sum(1 for item in clusters if item.needs_human_review)} 起需人工复核"
    )
    return {"trace": [_step("diagnose", "根因定位", started, summary)]}


def assess_node(state: OpsState) -> dict:
    started = time.perf_counter()
    clusters = [AlarmCluster.model_validate(item) for item in state["clusters"]]
    overall = min(
        (item.severity for item in clusters),
        key=lambda value: SEVERITY_RANK[value],
        default=Severity.P4,
    )
    top = [item for item in clusters if item.cause_type != "NOISE"][:4]
    dispatch = [
        f"{item.id}｜{item.root_ne_name}｜{item.cause_label}｜先执行：{item.plan_steps[0]}"
        for item in top
    ]
    fallback = (
        f"接入 {len(state['alarms'])} 条告警，压缩为 {len(clusters)} 起事件"
        f"（压缩率 {state['compression_ratio']:.1%}），整体严重度 {overall.value}。"
    )
    if top:
        fallback += "重点事件：" + "；".join(
            f"{item.id} {item.cause_label} @ {item.root_ne_name}"
            f"（{item.alarm_count} 条，置信度 {item.confidence:.0%}）"
            for item in top[:3]
        )
    review_required = any(item.needs_human_review for item in clusters)

    summary = ""
    llm = get_llm_client()
    if llm.enabled:
        summary = (
            llm.summarize_run(
                len(state["alarms"]),
                len(clusters),
                state["compression_ratio"],
                overall.value,
                clusters,
            )
            or ""
        )
    if not summary:
        summary = fallback

    return {
        "overall_severity": overall.value,
        "summary": summary,
        "dispatch_plan": dispatch,
        "review_required": review_required,
        "trace": [
            _step("assess", "汇总值班结论", started, f"整体 {overall.value}，生成 {len(dispatch)} 条派单建议")
        ],
    }


def dispatch_node(state: OpsState) -> dict:
    started = time.perf_counter()
    return {
        "trace": [
            _step(
                "dispatch",
                "生成派单",
                started,
                f"已生成 {len(state.get('dispatch_plan', []))} 条派单建议",
            )
        ]
    }


def human_review_node(state: OpsState) -> dict:
    started = time.perf_counter()
    return {
        "review_required": True,
        "summary": state["summary"] + " 存在低置信度事件，已转人工复核。",
        "trace": [
            _step("human_review", "转人工复核", started, "低置信度事件已标记人工复核")
        ],
    }


def save_run_node(state: OpsState) -> dict:
    started = time.perf_counter()
    step = _step("save_run", "保存分析结果", started, "分析结果已写入 SQLite")
    trace = list(state.get("trace", [])) + [step]
    payload = {
        "id": state["run_id"],
        "created_at": state["created_at"],
        "total_alarms": len(state["alarms"]),
        "cluster_count": len(state["clusters"]),
        "compression_ratio": state["compression_ratio"],
        "overall_severity": state["overall_severity"],
        "clusters": state["clusters"],
        "summary": state["summary"],
        "dispatch_plan": state.get("dispatch_plan", []),
        "review_required": state.get("review_required", False),
        "topology": state.get("topology"),
        "trace": trace,
        "llm_mode": state.get("llm_mode", "offline"),
    }
    repository = state.get("repository") or get_repository()
    repository.save_run(
        {
            "id": payload["id"],
            "total_alarms": payload["total_alarms"],
            "cluster_count": payload["cluster_count"],
            "compression_ratio": payload["compression_ratio"],
            "overall_severity": payload["overall_severity"],
            "created_at": payload["created_at"],
            "payload": payload,
        }
    )
    return {"trace": [step]}


def route_after_assess(state: OpsState) -> str:
    return "human_review" if state.get("review_required") else "dispatch"
