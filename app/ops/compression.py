"""Topology-aware alarm compression and root-cause clustering."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from app.ops.alarms import SEVERITY_RANK, dedupe_alarms, in_window, window_start
from app.ops.case_retriever import CaseRetriever, get_case_retriever
from app.ops.runbooks import CAUSE_LABELS, RUNBOOKS
from app.ops.topology import TopologyGraph
from app.schemas import Alarm, AlarmCluster, Severity

ROOT_ALARM_TYPES = {
    "LINK_DOWN",
    "LINK_DEGRADED",
    "POWER_FAILURE",
    "SIGNAL_OVERLOAD",
    "HIGH_TEMPERATURE",
    "CONFIG_CHANGE",
}


def infer_cause(root: Alarm) -> str:
    alarm_type = root.alarm_type
    ne_type = root.ne_type
    description = root.description or ""
    if alarm_type == "LINK_DOWN" and ne_type == "TRANSPORT":
        return "FIBER_CUT"
    if alarm_type == "LINK_DOWN" and ne_type == "OLT":
        return "UPLINK_DOWN"
    if alarm_type == "POWER_FAILURE":
        return "POWER_FAILURE"
    if alarm_type == "SIGNAL_OVERLOAD":
        return "SIGNALING_OVERLOAD"
    if alarm_type == "HIGH_TEMPERATURE":
        return "OVERHEATING"
    if alarm_type == "CONFIG_CHANGE":
        return "CONFIG_CHANGE"
    if alarm_type == "LINK_DEGRADED" and any(
        word in description for word in ("CRC", "误码", "光功率", "LOS")
    ):
        return "OPTICAL_DEGRADATION"
    else:
        return "UNKNOWN"


def _severity(members: list[Alarm]) -> Severity:
    return min((item.severity for item in members), key=lambda value: SEVERITY_RANK[value])


def _confidence(
    root: Alarm,
    members: list[Alarm],
    affected: set[str],
    topology: TopologyGraph,
    similar_score: float,
) -> float:
    score = 0.45
    if len(affected) >= 3:
        score += 0.15
    if root.severity == Severity.P1:
        score += 0.10
    types = {topology.node(node_id).type for node_id in affected if topology.node(node_id)}
    if len(types) >= 2:
        score += 0.10
    descendants = topology.descendants(root.ne_id)
    if len(descendants) >= 3 and len(members) >= max(2, len(descendants) * 0.3):
        score += 0.10
    if similar_score >= 0.5:
        score += 0.08
    return round(min(0.97, score), 2)


def _build_cluster(
    root: Alarm,
    members: list[Alarm],
    topology: TopologyGraph,
    retriever: CaseRetriever,
    *,
    is_noise: bool,
    confidence_threshold: float,
) -> AlarmCluster:
    cause_type = "NOISE" if is_noise else infer_cause(root)
    descendants = topology.descendants(root.ne_id) if not is_noise else {root.ne_id}
    affected = set(descendants)
    affected.update(item.ne_id for item in members)
    affected = {node_id for node_id in affected if topology.node(node_id)}
    affected_names = [topology.node(node_id).name for node_id in sorted(affected)]

    symptom_text = " ".join(
        f"{item.alarm_type} {item.description}" for item in members[:30]
    )
    similar = retriever.search(
        cause_type, symptom_text, root.ne_type, top_k=2
    )
    similar_score = similar[0].score if similar else 0.0

    confidence = 0.35 if is_noise else _confidence(
        root, members, affected, topology, similar_score
    )
    severity = _severity(members)
    types = sorted(
        {topology.node(node_id).type for node_id in affected if topology.node(node_id)}
    )
    evidence = [
        f"根告警：{root.ne_name} / {root.alarm_type} / {root.severity.value}",
        f"时间窗内聚合 {len(members)} 条告警，覆盖 {len(affected)} 个网元",
        f"影响节点类型：{'、'.join(types) or '未知'}",
    ]
    if similar:
        evidence.append(f"相似案例：{similar[0].case.title}（{similar[0].score:.0%}）")

    plan = list(RUNBOOKS.get(cause_type, RUNBOOKS["UNKNOWN"]))
    if not is_noise and similar and similar[0].score >= 0.65:
        plan = plan + [f"参考案例 {similar[0].case.id}：{similar[0].case.resolution[0]}"]

    times = [item.alarm_time for item in members]
    return AlarmCluster(
        id="",
        root_alarm=root,
        root_ne_id=root.ne_id,
        root_ne_name=root.ne_name,
        root_ne_type=root.ne_type,
        cause_type=cause_type,
        cause_label=CAUSE_LABELS.get(cause_type, CAUSE_LABELS["UNKNOWN"]),
        confidence=confidence,
        severity=severity,
        alarm_count=len(members),
        affected_node_ids=sorted(affected),
        affected_node_names=affected_names,
        time_start=min(times),
        time_end=max(times),
        evidence=evidence,
        similar_cases=similar,
        plan_steps=plan,
        needs_human_review=(not is_noise)
        and (confidence < confidence_threshold or cause_type == "UNKNOWN"),
    )


def compress_alarms(
    alarms: list[Alarm],
    topology: TopologyGraph,
    retriever: CaseRetriever | None = None,
    window_minutes: int = 10,
    confidence_threshold: float = 0.6,
) -> list[AlarmCluster]:
    retriever = retriever or get_case_retriever()
    alarms = dedupe_alarms(alarms)
    groups: dict[datetime, list[Alarm]] = defaultdict(list)
    for alarm in alarms:
        groups[window_start(alarm.alarm_time, window_minutes)].append(alarm)

    clusters: list[AlarmCluster] = []
    assigned: set[str] = set()

    for group in groups.values():
        candidates = [
            alarm
            for alarm in group
            if alarm.ne_type in ("CORE", "TRANSPORT", "OLT")
            and alarm.severity in (Severity.P1, Severity.P2)
            and alarm.alarm_type in ROOT_ALARM_TYPES
        ]
        candidates.sort(
            key=lambda alarm: (
                topology.type_rank(alarm.ne_id),
                SEVERITY_RANK[alarm.severity],
                alarm.alarm_time,
            )
        )
        for root in candidates:
            if root.alarm_id in assigned:
                continue
            descendants = topology.descendants(root.ne_id)
            members = [
                alarm
                for alarm in group
                if alarm.alarm_id not in assigned
                and alarm.ne_id in descendants
                and in_window(alarm.alarm_time, root.alarm_time, window_minutes)
            ]
            if len(members) < 2 and root.severity != Severity.P1:
                continue
            clusters.append(
                _build_cluster(
                    root,
                    members,
                    topology,
                    retriever,
                    is_noise=False,
                    confidence_threshold=confidence_threshold,
                )
            )
            assigned.update(item.alarm_id for item in members)

    remaining = [alarm for alarm in alarms if alarm.alarm_id not in assigned]
    high_remaining = [
        alarm for alarm in remaining if alarm.severity in (Severity.P1, Severity.P2)
    ]
    low_remaining = [
        alarm for alarm in remaining if alarm.severity in (Severity.P3, Severity.P4)
    ]

    high_windows: dict[datetime, list[Alarm]] = defaultdict(list)
    for alarm in high_remaining:
        high_windows[window_start(alarm.alarm_time, window_minutes)].append(alarm)

    for group in high_windows.values():
        root = min(group, key=lambda item: item.alarm_time)
        cluster = _build_cluster(
            root,
            group,
            topology,
            retriever,
            is_noise=True,
            confidence_threshold=confidence_threshold,
        )
        cluster.cause_type = "UNKNOWN"
        cluster.cause_label = CAUSE_LABELS["UNKNOWN"]
        cluster.confidence = 0.35
        cluster.needs_human_review = True
        cluster.plan_steps = list(RUNBOOKS["UNKNOWN"])
        cluster.evidence.insert(0, "存在未归类的 P1/P2 告警，规则无法确认根因")
        clusters.append(cluster)

    noise_groups: dict[str, list[Alarm]] = defaultdict(list)
    for alarm in low_remaining:
        noise_groups[alarm.alarm_type].append(alarm)

    for group in noise_groups.values():
        root = min(group, key=lambda item: item.alarm_time)
        clusters.append(
            _build_cluster(
                root,
                group,
                topology,
                retriever,
                is_noise=True,
                confidence_threshold=confidence_threshold,
            )
        )

    clusters.sort(
        key=lambda cluster: (
            SEVERITY_RANK[cluster.severity],
            cluster.time_start or datetime.max,
        )
    )
    for index, cluster in enumerate(clusters, start=1):
        cluster.id = f"C{index:02d}"
    return clusters
