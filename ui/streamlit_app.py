"""TelecomAgent NOC console.

Run from the repository root:
    streamlit run ui/streamlit_app.py
"""

from __future__ import annotations

import html
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.ops.alarms import load_alarms_csv  # noqa: E402
from app.schemas import (  # noqa: E402
    OpsAnalyzeRequest,
    OpsRun,
    Severity,
)
from app.services.ops import get_service  # noqa: E402
from app.services.reporting import run_markdown  # noqa: E402

st.set_page_config(
    page_title="TelecomAgent · NOC 值班台",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
<style>
  [data-testid="stSidebar"] { display: none; }
  [data-testid="stHeader"] { background: #070d17; }
  [data-testid="stToolbar"] { visibility: hidden; height: 0; }
  .stApp { background: #070d17; color: #d7e3f4; }
  .block-container { max-width: 1440px; padding-top: 2.4rem; padding-bottom: 3rem; }
  h1, h2, h3 { font-family: "Consolas", "JetBrains Mono", "Courier New", monospace; }

  .noc-header {
    display: flex; justify-content: space-between; align-items: flex-end; gap: 24px;
    border-bottom: 1px solid #1e2d45; padding: 10px 0 14px; margin-bottom: 4px;
  }
  .noc-kicker { font-family: "Consolas", monospace; font-size: .64rem; letter-spacing: .26em; color: #5b708c; }
  .noc-brand {
    font-family: "Consolas", "JetBrains Mono", monospace; font-size: 1.85rem; font-weight: 700;
    letter-spacing: .06em; color: #7df9a6; line-height: 1.15;
  }
  .noc-brand span { color: #d7e3f4; }
  .noc-status { font-family: "Consolas", monospace; font-size: .7rem; color: #8aa0bb; text-align: right; line-height: 1.9; }
  .noc-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #7df9a6; box-shadow: 0 0 9px #7df9a6; margin-right: 6px; }
  .noc-sub { font-family: "Consolas", monospace; font-size: .68rem; color: #5b708c; letter-spacing: .12em; margin: 0 0 14px; }

  div[role="radiogroup"] { flex-direction: row; gap: 2px; border-bottom: 1px solid #1e2d45; padding-bottom: 0; margin-bottom: 18px; }
  div[role="radiogroup"] label { padding: 6px 14px; border-right: 1px solid #16243a; }
  div[role="radiogroup"] label p { font-family: "Consolas", monospace; font-size: .82rem; color: #8aa0bb; }
  div[role="radiogroup"] label:has(input:checked) { background: #0e1a2b; border-bottom: 2px solid #7df9a6; }
  div[role="radiogroup"] label:has(input:checked) p { color: #7df9a6; }

  .noc-panel {
    background: #0b1424; border: 1px solid #1e2d45; padding: 16px 18px; margin-bottom: 12px;
    font-family: "Consolas", "JetBrains Mono", monospace;
  }
  .noc-panel-title { font-size: .66rem; letter-spacing: .2em; color: #6f86a3; text-transform: uppercase; }
  .noc-big { font-family: "Consolas", monospace; font-size: 1.9rem; color: #e8f1ff; line-height: 1.2; }
  .noc-big small { font-size: .72rem; color: #6f86a3; }
  .noc-metric-strip { display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; margin: 8px 0 16px; }
  .noc-metric { background: #0b1424; border: 1px solid #1e2d45; padding: 12px 14px; }
  .noc-metric .label { font-family: "Consolas", monospace; font-size: .62rem; letter-spacing: .14em; color: #6f86a3; }
  .noc-metric .value { font-family: "Consolas", monospace; font-size: 1.4rem; color: #e8f1ff; margin-top: 4px; }
  .noc-sev {
    display: inline-block; font-family: "Consolas", monospace; font-size: .68rem; font-weight: 700;
    padding: 2px 7px; border: 1px solid; letter-spacing: .08em;
  }
  .sev-P1 { color: #ff6b6b; border-color: #ff6b6b; background: rgba(255,107,107,.08); }
  .sev-P2 { color: #f5b942; border-color: #f5b942; background: rgba(245,185,66,.08); }
  .sev-P3 { color: #58c7f3; border-color: #58c7f3; background: rgba(88,199,243,.08); }
  .sev-P4 { color: #8aa0bb; border-color: #40536c; background: rgba(138,160,187,.06); }

  .noc-cluster { border-left: 3px solid #243854; background: #0a1220; padding: 13px 16px; margin: 10px 0; }
  .noc-cluster.P1 { border-left-color: #ff6b6b; }
  .noc-cluster.P2 { border-left-color: #f5b942; }
  .noc-cluster.P3 { border-left-color: #58c7f3; }
  .noc-cluster.P4 { border-left-color: #40536c; }
  .noc-cluster-head { display: flex; justify-content: space-between; gap: 12px; align-items: center; }
  .noc-cluster-title { font-family: "Consolas", monospace; font-size: .94rem; color: #e8f1ff; font-weight: 700; }
  .noc-meta { font-family: "Consolas", monospace; font-size: .7rem; color: #7188a5; line-height: 1.8; }
  .noc-evidence { font-size: .75rem; color: #9fb3cc; line-height: 1.8; margin-top: 7px; }
  .noc-plan { border: 1px solid #1e2d45; background: #0e1a2b; padding: 9px 11px; margin-top: 9px; font-size: .75rem; color: #b9cbe2; line-height: 1.8; }
  .noc-warn { border: 1px solid #f5b942; color: #f5b942; padding: 5px 9px; font-size: .72rem; }
  .noc-ok { border: 1px solid #2f8f62; color: #7df9a6; padding: 5px 9px; font-size: .72rem; }
  .noc-bar { height: 5px; background: #16243a; margin-top: 5px; }
  .noc-bar-fill { height: 100%; background: #7df9a6; }
  .noc-chip { display: inline-block; border: 1px solid #243854; color: #8aa0bb; padding: 2px 6px; margin: 3px 3px 0 0; font-size: .68rem; }
  .noc-table { width: 100%; border-collapse: collapse; font-family: "Consolas", monospace; font-size: .76rem; }
  .noc-table th { text-align: left; color: #6f86a3; font-weight: 400; border-bottom: 1px solid #1e2d45; padding: 8px 8px; letter-spacing: .08em; }
  .noc-table td { border-bottom: 1px solid #132033; padding: 8px 8px; color: #b9cbe2; }
  .noc-empty { border: 1px dashed #243854; padding: 44px 24px; text-align: center; color: #5b708c; font-family: "Consolas", monospace; }
  .noc-empty b { display: block; color: #7df9a6; font-size: .95rem; margin-bottom: 6px; letter-spacing: .08em; }
  .topo-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
  .topo-col { background: #0b1424; border: 1px solid #1e2d45; padding: 10px; max-height: 560px; overflow-y: auto; }
  .topo-head { font-family: "Consolas", monospace; font-size: .64rem; letter-spacing: .16em; color: #7df9a6; margin-bottom: 8px; }
  .topo-node { border: 1px solid #243854; padding: 5px 7px; margin: 5px 0; font-family: "Consolas", monospace; font-size: .68rem; color: #8aa0bb; }
  .topo-node.affected { border-color: #ff6b6b; color: #ffb3b3; background: rgba(255,107,107,.08); }
  .noc-step { display: grid; grid-template-columns: 150px 1fr 60px; gap: 8px; padding: 5px 0; border-bottom: 1px dotted #1e2d45; font-size: .72rem; }
  .noc-step b { color: #b9cbe2; }
  .noc-step span { color: #7188a5; }
  .noc-step i { color: #5b708c; font-style: normal; text-align: right; }
  .stButton > button[kind="primary"] { border-radius: 0; font-family: "Consolas", monospace; }
  .stButton > button { border-radius: 0; }
</style>
""",
    unsafe_allow_html=True,
)

SEVERITY_LABEL = {
    Severity.P1: "P1-紧急",
    Severity.P2: "P2-重要",
    Severity.P3: "P3-一般",
    Severity.P4: "P4-提示",
}


def severity_badge(level: Severity) -> str:
    return f'<span class="noc-sev sev-{level.value}">{SEVERITY_LABEL[level]}</span>'


def render_run(run: OpsRun, key_prefix: str = "main") -> None:
    incidents = [item for item in run.clusters if item.cause_type != "NOISE"]
    review = (
        '<span class="noc-warn">HUMAN REVIEW</span>'
        if run.review_required
        else '<span class="noc-ok">AUTO DISPATCH</span>'
    )
    st.markdown(
        f"""
        <div class="noc-panel">
          <div class="noc-cluster-head">
            <div>
              <div class="noc-panel-title">ANALYSIS RUN / {run.id}</div>
              <div class="noc-big">{len(incidents)} <small>ACTIVE INCIDENTS</small></div>
              <div class="noc-meta">{run.created_at.strftime('%Y-%m-%d %H:%M:%S')} · {run.llm_mode}</div>
            </div>
            <div style="text-align:right;">{severity_badge(run.overall_severity)}<div style="margin-top:8px;">{review}</div></div>
          </div>
        </div>
        <div class="noc-metric-strip">
          <div class="noc-metric"><div class="label">RAW ALARMS</div><div class="value">{run.total_alarms}</div></div>
          <div class="noc-metric"><div class="label">CLUSTERS</div><div class="value">{run.cluster_count}</div></div>
          <div class="noc-metric"><div class="label">COMPRESSION</div><div class="value">{run.compression_ratio:.1%}</div></div>
          <div class="noc-metric"><div class="label">P1 EVENTS</div><div class="value">{sum(1 for item in run.clusters if item.severity == Severity.P1)}</div></div>
          <div class="noc-metric"><div class="label">AFFECTED NEs</div><div class="value">{len({node for item in run.clusters for node in item.affected_node_ids})}</div></div>
        </div>
        <div class="noc-panel"><div class="noc-panel-title">值班摘要</div>
        <div class="noc-evidence" style="font-size:.84rem;color:#d7e3f4;">{html.escape(run.summary)}</div></div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="noc-panel-title" style="margin-top:10px;">事件队列</div>', unsafe_allow_html=True)
    for cluster in incidents:
        similar = "".join(
            f'<div class="noc-meta">↳ {match.case.id} {html.escape(match.case.title)} · {match.score:.0%}</div>'
            for match in cluster.similar_cases
        )
        steps = "".join(
            f'<div>▸ {html.escape(step)}</div>' for step in cluster.plan_steps[:4]
        )
        evidence = "".join(
            f'<div>· {html.escape(item)}</div>' for item in cluster.evidence
        )
        review_flag = (
            '<span class="noc-warn">需人工复核</span>'
            if cluster.needs_human_review
            else ""
        )
        st.markdown(
            f"""
            <div class="noc-cluster {cluster.severity.value}">
              <div class="noc-cluster-head">
                <div>
                  <div class="noc-cluster-title">{cluster.id} // {html.escape(cluster.cause_label)}</div>
                  <div class="noc-meta">{html.escape(cluster.root_ne_name)} · {cluster.root_ne_type} · {cluster.alarm_count} 条告警 · 影响 {len(cluster.affected_node_ids)} 网元</div>
                </div>
                <div style="text-align:right;">{severity_badge(cluster.severity)} {review_flag}
                  <div class="noc-meta">置信度 {cluster.confidence:.0%}</div>
                </div>
              </div>
              <div class="noc-bar"><div class="noc-bar-fill" style="width:{cluster.confidence * 100:.0f}%;"></div></div>
              <div class="noc-evidence">{evidence}</div>
              <div class="noc-plan">{steps}</div>
              {similar}
            </div>
            """,
            unsafe_allow_html=True,
        )

    noise = [item for item in run.clusters if item.cause_type == "NOISE"]
    if noise:
        with st.expander(f"背景噪声 / 例行告警（{len(noise)} 组，{sum(item.alarm_count for item in noise)} 条）"):
            for cluster in noise:
                st.markdown(
                    f'<div class="noc-cluster P4"><div class="noc-cluster-title">{cluster.id} · '
                    f'{html.escape(cluster.cause_label)}</div>'
                    f'<div class="noc-meta">{cluster.alarm_count} 条 · {html.escape(cluster.root_ne_name)} · '
                    f'置信度 {cluster.confidence:.0%}</div></div>',
                    unsafe_allow_html=True,
                )

    if run.dispatch_plan:
        st.markdown('<div class="noc-panel"><div class="noc-panel-title">派单建议</div>', unsafe_allow_html=True)
        for item in run.dispatch_plan:
            st.markdown(f'<div class="noc-evidence">▸ {html.escape(item)}</div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with st.expander("查看分析轨迹", expanded=False):
        steps = "".join(
            f'<div class="noc-step"><b>{html.escape(step.node)}</b>'
            f'<span>{html.escape(step.summary)}</span><i>{step.duration_ms} ms</i></div>'
            for step in run.trace
        )
        st.markdown(f'<div class="noc-panel">{steps}</div>', unsafe_allow_html=True)

    st.download_button(
        "下载 NOC 分析报告",
        data=run_markdown(run),
        file_name=f"noc-{run.id}.md",
        mime="text/markdown",
        key=f"download_run_{key_prefix}_{run.id}",
    )


service = get_service()
if "run_result" not in st.session_state:
    st.session_state.run_result = service.analyze(OpsAnalyzeRequest()).model_dump(mode="json")
run = OpsRun.model_validate(st.session_state.run_result)
dataset_alarms = load_alarms_csv()

st.markdown(
    f"""
    <div class="noc-header">
      <div>
        <div class="noc-kicker">TELECOM // NETWORK OPERATIONS CENTER</div>
        <div class="noc-brand">Telecom<span>Agent</span> NOC 值班台</div>
        <div class="noc-sub">ALARM COMPRESSION · TOPOLOGY CORRELATION · ROOT CAUSE</div>
      </div>
      <div class="noc-status">
        <span><span class="noc-dot"></span>DATASET ONLINE</span><br/>
        接入告警 {len(dataset_alarms)} 条 · 网元 {len(run.topology.nodes) if run.topology else 0} 个<br/>
        运行模式 {run.llm_mode}
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

page = st.radio(
    "导航",
    ["值班总览", "告警分析", "拓扑视图", "案例库", "历史记录"],
    horizontal=True,
    label_visibility="collapsed",
)

if page == "值班总览":
    render_run(run)

elif page == "告警分析":
    st.markdown('<div class="noc-panel-title">告警输入</div>', unsafe_allow_html=True)
    uploaded = st.file_uploader("上传告警 CSV", type=["csv"], key="alarm_csv")
    col_a, col_b = st.columns([0.5, 0.5])
    with col_a:
        if st.button("重新分析样例数据", type="primary", key="run_sample"):
            st.session_state.run_result = service.analyze(OpsAnalyzeRequest()).model_dump(mode="json")
            st.rerun()
    with col_b:
        if uploaded is not None and st.button("分析上传 CSV", key="run_upload"):
            try:
                result = service.analyze_csv_bytes(uploaded.getvalue())
                st.session_state.run_result = result.model_dump(mode="json")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
    st.markdown(
        '<div class="noc-meta">CSV 字段：alarm_id, alarm_time, ne_id, ne_name, ne_type, alarm_type, severity, description, region, vendor</div>',
        unsafe_allow_html=True,
    )
    render_run(OpsRun.model_validate(st.session_state.run_result))

elif page == "拓扑视图":
    topology = service.topology()
    regions = sorted({node.region for node in topology.nodes if node.region})
    region = st.selectbox(
        "区域",
        options=regions,
        index=regions.index("杭州") if "杭州" in regions else 0,
        key="topo_region",
    )
    affected = {
        node_id
        for cluster in run.clusters
        if cluster.cause_type != "NOISE"
        for node_id in cluster.affected_node_ids
    }
    by_type: dict[str, list] = {"CORE": [], "TRANSPORT": [], "OLT": [], "BASE_STATION": []}
    for node in topology.nodes:
        if node.region == region and node.type in by_type:
            by_type[node.type].append(node)

    columns = []
    for type_name, label in (
        ("CORE", "CORE / 核心网"),
        ("TRANSPORT", "TRANSPORT / 传输"),
        ("OLT", "OLT / 接入"),
        ("BASE_STATION", "BASE STATION / 基站"),
    ):
        nodes_html = "".join(
            f'<div class="topo-node {"affected" if node.id in affected else ""}">'
            f'{html.escape(node.name)}<br/><span style="color:#5b708c;">{node.id}</span></div>'
            for node in by_type[type_name]
        )
        columns.append(
            f'<div class="topo-col"><div class="topo-head">{label} · {len(by_type[type_name])}</div>'
            f'{nodes_html}</div>'
        )
    st.markdown(
        '<div class="noc-panel"><div class="noc-panel-title">拓扑视图 / 红色为本次受影响网元</div>'
        f'<div class="topo-grid">{"".join(columns)}</div></div>',
        unsafe_allow_html=True,
    )

elif page == "案例库":
    st.markdown('<div class="noc-panel-title">故障案例检索</div>', unsafe_allow_html=True)
    query = st.text_input(
        "症状关键词",
        value="光缆 中断 OLT 批量离线",
        label_visibility="collapsed",
        placeholder="例如：光缆 中断 OLT 批量离线",
    )
    if st.button("检索案例", key="run_case_search"):
        st.session_state.case_matches = [match.model_dump(mode="json") for match in service.search_cases(symptoms=query, top_k=5)]
    matches = st.session_state.get("case_matches", [])
    if matches:
        for item in matches:
            case = item["case"]
            symptoms = "".join(f'<span class="noc-chip">{html.escape(tag)}</span>' for tag in case["symptoms"])
            steps = "".join(f'<div>▸ {html.escape(step)}</div>' for step in case["resolution"])
            st.markdown(
                f'<div class="noc-cluster P3"><div class="noc-cluster-title">{case["id"]} // {html.escape(case["title"])}</div>'
                f'<div class="noc-meta">{html.escape(case["cause_type"])} · 根网元类型 {html.escape(case["root_ne_type"])} · 相似度 {item["score"]:.0%}</div>'
                f'<div>{symptoms}</div><div class="noc-plan">{steps}</div></div>',
                unsafe_allow_html=True,
            )
    else:
        st.markdown('<div class="noc-empty"><b>案例库待检索</b>输入症状关键词，匹配历史故障案例与处置方案。</div>', unsafe_allow_html=True)

else:
    runs = service.list_recent(20)
    if runs:
        st.dataframe(
            [
                {
                    "时间": item.created_at.strftime("%m-%d %H:%M"),
                    "告警": item.total_alarms,
                    "事件": item.cluster_count,
                    "压缩率": f"{item.compression_ratio:.1%}",
                    "严重度": item.overall_severity.value,
                }
                for item in runs
            ],
            width="stretch",
            hide_index=True,
        )
        options = {
            f"{item.created_at.strftime('%m-%d %H:%M')} · {item.id}": item.id for item in runs
        }
        chosen = st.selectbox("调阅分析记录", options=list(options.keys()))
        detail = service.get_run(options[chosen])
        if detail:
            render_run(detail, key_prefix="history")
    else:
        st.markdown('<div class="noc-empty"><b>暂无分析记录</b>运行一次告警分析后，结果会自动归档。</div>', unsafe_allow_html=True)
