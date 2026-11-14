"""Compiled LangGraph workflow for NOC analysis."""

from __future__ import annotations

from functools import lru_cache

from langgraph.graph import END, StateGraph

from app.graph import ops_nodes
from app.graph.ops_state import OpsState


@lru_cache(maxsize=1)
def get_ops_graph():
    builder = StateGraph(OpsState)
    builder.add_node("load_alarms", ops_nodes.load_alarms_node)
    builder.add_node("compress_alarms", ops_nodes.compress_node)
    builder.add_node("diagnose", ops_nodes.diagnose_node)
    builder.add_node("assess", ops_nodes.assess_node)
    builder.add_node("dispatch", ops_nodes.dispatch_node)
    builder.add_node("human_review", ops_nodes.human_review_node)
    builder.add_node("save_run", ops_nodes.save_run_node)

    builder.set_entry_point("load_alarms")
    builder.add_edge("load_alarms", "compress_alarms")
    builder.add_edge("compress_alarms", "diagnose")
    builder.add_edge("diagnose", "assess")
    builder.add_conditional_edges(
        "assess",
        ops_nodes.route_after_assess,
        {"dispatch": "dispatch", "human_review": "human_review"},
    )
    builder.add_edge("dispatch", "save_run")
    builder.add_edge("human_review", "save_run")
    builder.add_edge("save_run", END)
    return builder.compile()
