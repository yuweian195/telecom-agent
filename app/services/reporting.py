"""Markdown report rendering for NOC analysis runs."""

from __future__ import annotations

from app.schemas import OpsRun

_SEVERITY_LABEL = {"P1": "P1-紧急", "P2": "P2-重要", "P3": "P3-一般", "P4": "P4-提示"}


def run_markdown(run: OpsRun) -> str:
    lines = [
        "# NOC 告警分析报告",
        "",
        f"- 分析编号：{run.id}",
        f"- 生成时间：{run.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 原始告警：{run.total_alarms} 条",
        f"- 聚合事件：{run.cluster_count} 起",
        f"- 压缩率：**{run.compression_ratio:.1%}**",
        f"- 整体严重度：**{_SEVERITY_LABEL.get(run.overall_severity.value, run.overall_severity.value)}**",
        f"- 人工复核：{'是' if run.review_required else '否'}",
        "",
        "## 值班摘要",
        "",
        run.summary,
        "",
        "## 事件列表",
        "",
        "| 事件 | 严重度 | 根因 | 根网元 | 告警数 | 影响网元 | 置信度 |",
        "|---|---|---|---|---:|---:|---:|",
    ]
    for cluster in run.clusters:
        lines.append(
            f"| {cluster.id} | {_SEVERITY_LABEL.get(cluster.severity.value, cluster.severity.value)} "
            f"| {cluster.cause_label} | {cluster.root_ne_name} | {cluster.alarm_count} "
            f"| {len(cluster.affected_node_ids)} | {cluster.confidence:.0%} |"
        )

    lines += ["", "## 重点事件", ""]
    for cluster in [item for item in run.clusters if item.cause_type != "NOISE"][:5]:
        lines += [
            f"### {cluster.id} · {cluster.cause_label} · {cluster.root_ne_name}",
            "",
            f"- 严重度：{_SEVERITY_LABEL.get(cluster.severity.value, cluster.severity.value)}",
            f"- 置信度：{cluster.confidence:.0%}",
            f"- 告警数：{cluster.alarm_count}",
            f"- 影响网元：{len(cluster.affected_node_ids)} 个",
            f"- 时间范围：{cluster.time_start} ~ {cluster.time_end}",
            "",
            "证据：",
        ]
        lines += [f"- {item}" for item in cluster.evidence]
        lines += ["", "处置步骤："]
        lines += [f"{index}. {item}" for index, item in enumerate(cluster.plan_steps, start=1)]
        if cluster.similar_cases:
            lines += ["", "相似案例："]
            lines += [
                f"- {match.case.id} {match.case.title}（{match.score:.0%}）"
                for match in cluster.similar_cases
            ]
        lines.append("")

    if run.dispatch_plan:
        lines += ["## 派单建议", ""]
        lines += [f"- {item}" for item in run.dispatch_plan]

    lines += [
        "",
        "> 本报告由拓扑关联与规则引擎生成；处置前请结合现场情况确认，避免直接执行高风险操作。",
    ]
    return "\n".join(lines) + "\n"
