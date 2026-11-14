"""Evaluation for compression, root cause, impact and case retrieval.

Usage:
    python scripts/evaluate.py
"""

from __future__ import annotations

import json
import statistics
import sys
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.ops.alarms import load_alarms_csv  # noqa: E402
from app.ops.case_retriever import CaseRetriever  # noqa: E402
from app.ops.compression import compress_alarms  # noqa: E402
from app.ops.topology import load_topology  # noqa: E402


def main() -> None:
    alarms = load_alarms_csv()
    topology = load_topology()
    cases = CaseRetriever()
    labels = json.loads(
        (ROOT / "data" / "fixtures" / "incident_labels.json").read_text(encoding="utf-8")
    )
    case_eval = json.loads(
        (ROOT / "data" / "fixtures" / "case_eval.json").read_text(encoding="utf-8")
    )

    latencies: list[float] = []
    clusters = []
    for _ in range(3):
        started = time.perf_counter()
        clusters = compress_alarms(alarms, topology, cases)
        latencies.append((time.perf_counter() - started) * 1000)

    compression_ratio = 1 - len(clusters) / max(1, len(alarms))

    root_hits = 0
    impact_recalls: list[float] = []
    for incident in labels["incidents"]:
        cluster = next(
            (item for item in clusters if item.root_ne_id == incident["root_ne_id"]),
            None,
        )
        if cluster and cluster.cause_type == incident["cause_type"]:
            root_hits += 1
        expected = set(incident.get("expected_affected", []))
        actual = set(cluster.affected_node_ids) if cluster else set()
        impact_recalls.append(len(expected & actual) / max(1, len(expected)))

    case_hits = 0
    for item in case_eval:
        matches = cases.search(item["cause_type"], item["symptoms"], top_k=3)
        if any(match.case.id == item["expected"] for match in matches):
            case_hits += 1

    unknown_review = any(
        item.cause_type == "UNKNOWN" and item.needs_human_review for item in clusters
    )

    lines = [
        "# 离线评估报告",
        "",
        f"生成日期：{date.today().isoformat()}  ",
        "运行模式：离线规则 + 拓扑关联（不调用外部 LLM）  ",
        f"告警样本：{len(alarms)} 条｜网元：{topology.count} 个｜案例：{cases.count} 条",
        "",
        "## 告警压缩",
        "",
        "| 指标 | 结果 |",
        "|---|---:|",
        f"| 原始告警 | {len(alarms)} |",
        f"| 聚合事件 | {len(clusters)} |",
        f"| 压缩率 | **{compression_ratio:.1%}** |",
        f"| 平均耗时 | **{statistics.mean(latencies):.0f} ms** |",
        "",
        "## 根因与影响面",
        "",
        "| 指标 | 结果 |",
        "|---|---:|",
        f"| 根因准确率 | **{root_hits}/{len(labels['incidents'])}（{root_hits / len(labels['incidents']):.0%}）** |",
        f"| 影响面平均召回 | **{statistics.mean(impact_recalls):.0%}** |",
        f"| 低置信度转人工 | **{'是' if unknown_review else '否'}** |",
        "",
        "## 案例检索",
        "",
        "| 指标 | 结果 |",
        "|---|---:|",
        f"| Recall@3 | **{case_hits}/{len(case_eval)}（{case_hits / len(case_eval):.0%}）** |",
        "",
        "> 评估集为合成告警与合成案例，标签按拓扑与根因人工标注，用于检查压缩与定位量级，不代表真实网络环境。",
    ]
    report = "\n".join(lines) + "\n"
    output = ROOT / "reports" / "evaluation.md"
    output.parent.mkdir(exist_ok=True)
    output.write_text(report, encoding="utf-8")
    print(report)
    print(f"written to {output}")


if __name__ == "__main__":
    main()
