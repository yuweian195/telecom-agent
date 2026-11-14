"""Runbooks for each root-cause class."""

from __future__ import annotations

CAUSE_LABELS = {
    "FIBER_CUT": "光缆中断",
    "UPLINK_DOWN": "OLT 上行链路中断",
    "POWER_FAILURE": "电源故障",
    "SIGNALING_OVERLOAD": "核心网信令过载",
    "OPTICAL_DEGRADATION": "光路/光模块劣化",
    "OVERHEATING": "设备高温",
    "CONFIG_CHANGE": "配置变更",
    "NOISE": "背景噪声/例行告警",
    "UNKNOWN": "根因待定位",
}

RUNBOOKS = {
    "FIBER_CUT": [
        "远程确认光路 LOS、ODF 端口与误码计数",
        "派单现场进行 OTDR 测试，定位断点",
        "调度备用纤芯或环网倒换，先恢复业务",
        "修复后逐站确认 OLT 与基站恢复",
    ],
    "UPLINK_DOWN": [
        "确认 OLT 上行端口状态与光功率",
        "检查传输设备端口、尾纤与光模块",
        "必要时切换到备用上行链路",
        "恢复后验证 PON 口与业务",
    ],
    "POWER_FAILURE": [
        "确认站点市电状态与蓄电池剩余容量",
        "联系机房/物业确认停电原因与恢复时间",
        "调度移动油机或应急电源",
        "恢复后检查 OLT 单板与基站业务",
    ],
    "SIGNALING_OVERLOAD": [
        "确认核心网信令面 CPU、SCTP 链路与重传率",
        "启用信令流控与过载保护",
        "排查异常终端、短时呼叫风暴或外部攻击",
        "必要时扩容或分流至备用核心网元",
    ],
    "OPTICAL_DEGRADATION": [
        "检查光模块收发光功率、温度与误码计数",
        "清洁光纤连接器并复测",
        "更换劣化光模块或尾纤",
        "观察 30 分钟误码是否恢复",
    ],
    "OVERHEATING": [
        "确认机房空调、通风与设备风扇状态",
        "检查滤网与风扇模块，必要时更换",
        "临时降温并观察温度曲线",
        "复盘机房温控与设备负载",
    ],
    "CONFIG_CHANGE": [
        "核对变更单与网管操作记录",
        "对比变更前后配置与关键指标",
        "必要时回滚最近一次变更",
        "观察 15 分钟确认业务恢复",
    ],
    "NOISE": [
        "按例行工单分派，不影响主业务",
        "持续观察是否有升级趋势",
    ],
    "UNKNOWN": [
        "转人工复核，补充拓扑、日志与性能数据",
        "保留告警时间线与关联证据",
    ],
}
