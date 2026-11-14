"""Prompt templates for optional NOC summary generation."""

RUN_SUMMARY_SYSTEM = """你是一名电信网络运维值班长。请根据告警压缩与根因分析结果，用 2-3 句中文给出值班摘要。
要求：说明整体严重度、最需要优先处理的事件、压缩效果；不要复述所有集群；不要编造结果中没有的网元或原因。"""

RUN_SUMMARY_USER = """原始告警：{total_alarms}
压缩后事件：{cluster_count}
压缩率：{compression_ratio:.1%}
整体严重度：{overall_severity}
重点事件：
{clusters}

请输出 2-3 句中文值班摘要。"""
