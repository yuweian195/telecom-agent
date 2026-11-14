"""Generate the synthetic topology, alarm day, labels and case library.

Usage:
    python scripts/generate_sample_data.py
"""

from __future__ import annotations

import csv
import json
import random
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
random.seed(20261114)

NODES: list[dict] = [
    {"id": "CORE-HZ-01", "name": "杭州核心网 MSC-01", "type": "CORE", "region": "杭州", "vendor": "Huawei"},
    {"id": "CORE-NB-01", "name": "宁波核心网 MSC-01", "type": "CORE", "region": "宁波", "vendor": "ZTE"},
    {"id": "TX-HZ-05", "name": "杭州城西传输环-05", "type": "TRANSPORT", "region": "杭州", "vendor": "Huawei"},
    {"id": "TX-HZ-06", "name": "杭州城东传输环-06", "type": "TRANSPORT", "region": "杭州", "vendor": "Huawei"},
    {"id": "TX-NB-03", "name": "宁波北仑传输环-03", "type": "TRANSPORT", "region": "宁波", "vendor": "ZTE"},
    {"id": "TX-WZ-02", "name": "温州瓯海传输环-02", "type": "TRANSPORT", "region": "温州", "vendor": "FiberHome"},
    {"id": "OLT-HZ-01", "name": "杭州城西 OLT-01", "type": "OLT", "region": "杭州", "vendor": "Huawei"},
    {"id": "OLT-HZ-02", "name": "杭州城西 OLT-02", "type": "OLT", "region": "杭州", "vendor": "Huawei"},
    {"id": "OLT-HZ-03", "name": "杭州城东 OLT-03", "type": "OLT", "region": "杭州", "vendor": "Huawei"},
    {"id": "OLT-HZ-04", "name": "杭州城东 OLT-04", "type": "OLT", "region": "杭州", "vendor": "Huawei"},
    {"id": "OLT-NB-01", "name": "宁波北仑 OLT-01", "type": "OLT", "region": "宁波", "vendor": "ZTE"},
    {"id": "OLT-NB-02", "name": "宁波北仑 OLT-02", "type": "OLT", "region": "宁波", "vendor": "ZTE"},
    {"id": "OLT-WZ-01", "name": "温州瓯海 OLT-01", "type": "OLT", "region": "温州", "vendor": "FiberHome"},
]

EDGES: list[dict] = [
    {"source": "CORE-HZ-01", "target": "TX-HZ-05", "relation": "backbone"},
    {"source": "CORE-HZ-01", "target": "TX-HZ-06", "relation": "backbone"},
    {"source": "CORE-HZ-01", "target": "TX-WZ-02", "relation": "backbone"},
    {"source": "CORE-NB-01", "target": "TX-NB-03", "relation": "backbone"},
    {"source": "TX-HZ-05", "target": "OLT-HZ-01", "relation": "uplink"},
    {"source": "TX-HZ-05", "target": "OLT-HZ-02", "relation": "uplink"},
    {"source": "TX-HZ-06", "target": "OLT-HZ-03", "relation": "uplink"},
    {"source": "TX-HZ-06", "target": "OLT-HZ-04", "relation": "uplink"},
    {"source": "TX-NB-03", "target": "OLT-NB-01", "relation": "uplink"},
    {"source": "TX-NB-03", "target": "OLT-NB-02", "relation": "uplink"},
    {"source": "TX-WZ-02", "target": "OLT-WZ-01", "relation": "uplink"},
]

OLT_BS = {
    "OLT-HZ-01": range(101, 111),
    "OLT-HZ-02": range(111, 121),
    "OLT-HZ-03": range(121, 131),
    "OLT-HZ-04": range(131, 141),
    "OLT-NB-01": range(101, 111),
    "OLT-NB-02": range(111, 121),
    "OLT-WZ-01": range(101, 111),
}
for olt_id, numbers in OLT_BS.items():
    region = "杭州" if "HZ" in olt_id else "宁波" if "NB" in olt_id else "温州"
    prefix = "HZ" if "HZ" in olt_id else "NB" if "NB" in olt_id else "WZ"
    for number in numbers:
        node_id = f"BS-{prefix}-{number}"
        NODES.append(
            {
                "id": node_id,
                "name": f"{region}基站 {number}",
                "type": "BASE_STATION",
                "region": region,
                "vendor": "Huawei" if prefix == "HZ" else "ZTE",
            }
        )
        EDGES.append({"source": olt_id, "target": node_id, "relation": "access"})

NODE_MAP = {node["id"]: node for node in NODES}
ALARMS: list[dict] = []


def add_alarm(
    moment: datetime,
    ne_id: str,
    alarm_type: str,
    severity: str,
    description: str,
) -> None:
    node = NODE_MAP[ne_id]
    ALARMS.append(
        {
            "alarm_id": f"A{len(ALARMS) + 1:05d}",
            "alarm_time": moment.isoformat(timespec="seconds"),
            "ne_id": ne_id,
            "ne_name": node["name"],
            "ne_type": node["type"],
            "alarm_type": alarm_type,
            "severity": severity,
            "description": description,
            "region": node["region"],
            "vendor": node["vendor"],
        }
    )


def incident_a() -> None:
    start = datetime(2026, 11, 14, 3, 12, 5)
    add_alarm(start, "TX-HZ-05", "LINK_DOWN", "P1", "光缆中断，上行链路 LOS，CRC 错误率 100%")
    add_alarm(start + timedelta(seconds=15), "OLT-HZ-01", "LINK_DOWN", "P1", "上行链路中断，PON 口批量掉线")
    add_alarm(start + timedelta(seconds=20), "OLT-HZ-02", "LINK_DOWN", "P1", "上行链路中断，PON 口批量掉线")
    add_alarm(start + timedelta(seconds=30), "OLT-HZ-03", "LINK_DEGRADED", "P2", "链路 CRC 错误率上升")
    add_alarm(start + timedelta(seconds=35), "OLT-HZ-04", "LINK_DEGRADED", "P2", "链路误码率上升")
    bs_ids = [f"BS-HZ-{n}" for n in range(101, 141)]
    for index, bs_id in enumerate(bs_ids[:20]):
        add_alarm(start + timedelta(seconds=60 + index * 3), bs_id, "CELL_DOWN", "P1", "小区退服，用户无覆盖")
    for index, bs_id in enumerate(bs_ids[20:40]):
        add_alarm(start + timedelta(seconds=90 + index * 3), bs_id, "CELL_DOWN", "P2", "小区退服，业务中断")
    for index, bs_id in enumerate(bs_ids[:20]):
        add_alarm(start + timedelta(seconds=120 + index * 2), bs_id, "CALL_DROP", "P3", "呼叫建立失败率升高")
    for index in range(10):
        add_alarm(
            start + timedelta(seconds=150 + index * 2),
            f"OLT-HZ-0{1 + index % 4}",
            "TRAFFIC_CONGESTION",
            "P3",
            "上行带宽利用率超过 85%",
        )
    for index in range(5):
        add_alarm(
            start + timedelta(seconds=180 + index * 2),
            f"OLT-HZ-0{1 + index % 4}",
            "HIGH_TEMPERATURE",
            "P3",
            "设备温度 68℃，风扇转速异常",
        )


def incident_b() -> None:
    start = datetime(2026, 11, 14, 3, 40, 10)
    add_alarm(start, "OLT-NB-01", "POWER_FAILURE", "P1", "市电中断，蓄电池放电，剩余电量 42%")
    for index, number in enumerate(range(101, 111)):
        add_alarm(
            start + timedelta(seconds=25 + index * 4),
            f"BS-NB-{number}",
            "CELL_DOWN",
            "P1",
            "基站退服，市电与备电均异常",
        )
    for index, number in enumerate(range(101, 111)):
        add_alarm(
            start + timedelta(seconds=60 + index * 2),
            f"BS-NB-{number}",
            "CALL_DROP",
            "P2",
            "呼叫成功率下降",
        )
    for index in range(5):
        add_alarm(
            start + timedelta(seconds=90 + index * 3),
            f"BS-NB-{101 + index}",
            "HIGH_TEMPERATURE",
            "P3",
            "机房温度 35℃",
        )
    for index in range(5):
        add_alarm(
            start + timedelta(seconds=100 + index * 2),
            "OLT-NB-01",
            "CONFIG_CHANGE",
            "P4",
            "网管下发电源节能配置",
        )


def incident_c() -> None:
    start = datetime(2026, 11, 14, 4, 5, 30)
    add_alarm(start, "CORE-HZ-01", "SIGNAL_OVERLOAD", "P1", "MSC 信令过载，CPU 92%，SCTP 重传率上升")
    for index, ne_id in enumerate(["TX-HZ-05", "TX-HZ-06"] * 3):
        add_alarm(
            start + timedelta(seconds=20 + index * 6),
            ne_id,
            "TRAFFIC_CONGESTION",
            "P2",
            "核心网侧信令链路利用率超过 90%",
        )
    for index, number in enumerate(range(101, 126)):
        add_alarm(
            start + timedelta(seconds=45 + index * 2),
            f"BS-HZ-{number}",
            "CALL_DROP",
            "P2",
            "呼叫建立失败，S1 接口信令超时",
        )
    for index, number in enumerate(range(126, 136)):
        add_alarm(
            start + timedelta(seconds=80 + index * 3),
            f"BS-HZ-{number}",
            "CALL_DROP",
            "P3",
            "呼叫建立失败率轻微升高",
        )
    for index in range(5):
        add_alarm(
            start + timedelta(seconds=110 + index * 2),
            "CORE-HZ-01",
            "CONFIG_CHANGE",
            "P4",
            "信令流控参数调整",
        )


def incident_d() -> None:
    """Unclassified high-severity alarms that must be routed to human review."""
    start = datetime(2026, 11, 14, 5, 10, 0)
    add_alarm(start, "OLT-WZ-01", "SERVICE_DEGRADED", "P1", "业务质量下降，原因不明，需人工确认")
    add_alarm(start + timedelta(seconds=20), "BS-WZ-101", "CELL_DOWN", "P2", "小区退服，原因待确认")
    add_alarm(start + timedelta(seconds=35), "BS-WZ-102", "CELL_DOWN", "P2", "小区退服，原因待确认")


def noise() -> None:
    start = datetime(2026, 11, 14, 2, 0, 0)
    types = ["HIGH_TEMPERATURE", "CONFIG_CHANGE", "TRAFFIC_CONGESTION", "LINK_DEGRADED"]
    candidates = [node["id"] for node in NODES if node["type"] in ("OLT", "TRANSPORT", "BASE_STATION")]
    for index in range(62):
        moment = start + timedelta(minutes=index * 3 + random.randint(0, 2), seconds=random.randint(0, 59))
        ne_id = random.choice(candidates)
        alarm_type = random.choice(types)
        severity = random.choice(["P3", "P4", "P4"])
        add_alarm(moment, ne_id, alarm_type, severity, f"例行巡检告警：{alarm_type}")


def main() -> None:
    incident_a()
    incident_b()
    incident_c()
    incident_d()
    noise()
    ALARMS.sort(key=lambda item: item["alarm_time"])

    (DATA / "topology").mkdir(parents=True, exist_ok=True)
    (DATA / "alarms").mkdir(parents=True, exist_ok=True)
    (DATA / "fixtures").mkdir(parents=True, exist_ok=True)
    (DATA / "cases").mkdir(parents=True, exist_ok=True)

    topology = {"nodes": NODES, "edges": EDGES}
    (DATA / "topology" / "network.json").write_text(
        json.dumps(topology, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    csv_path = DATA / "alarms" / "incident_day.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "alarm_id",
                "alarm_time",
                "ne_id",
                "ne_name",
                "ne_type",
                "alarm_type",
                "severity",
                "description",
                "region",
                "vendor",
            ],
        )
        writer.writeheader()
        writer.writerows(ALARMS)

    labels = {
        "dataset": "incident_day",
        "total_alarms": len(ALARMS),
        "incidents": [
            {
                "id": "INC-A",
                "title": "城西传输环光缆中断",
                "root_ne_id": "TX-HZ-05",
                "cause_type": "FIBER_CUT",
                "expected_cluster_min": 30,
                "expected_affected": [f"BS-HZ-{number}" for number in range(101, 121)],
            },
            {
                "id": "INC-B",
                "title": "北仑 OLT 电源故障",
                "root_ne_id": "OLT-NB-01",
                "cause_type": "POWER_FAILURE",
                "expected_cluster_min": 10,
                "expected_affected": [f"BS-NB-{number}" for number in range(101, 111)],
            },
            {
                "id": "INC-C",
                "title": "核心网信令过载",
                "root_ne_id": "CORE-HZ-01",
                "cause_type": "SIGNALING_OVERLOAD",
                "expected_cluster_min": 20,
                "expected_affected": [f"BS-HZ-{number}" for number in range(101, 136)],
            },
        ],
    }
    (DATA / "fixtures" / "incident_labels.json").write_text(
        json.dumps(labels, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"alarms: {len(ALARMS)}, nodes: {len(NODES)}, edges: {len(EDGES)}")


if __name__ == "__main__":
    main()
