import { useCallback, useEffect, useState } from "react";
import { fetchLatestRun } from "./api";
import { connectAlarmStream } from "./live";
import type { AlarmCluster, LiveAlarm, LiveAnalysis, OpsRun, Severity, TopologyNode } from "./types";

const REFRESH_SECONDS = 20;

const SEVERITY_LABEL: Record<Severity, string> = {
  P1: "P1 紧急",
  P2: "P2 重要",
  P3: "P3 一般",
  P4: "P4 提示",
};

const TYPE_LABEL: Record<string, string> = {
  CORE: "CORE / 核心网",
  TRANSPORT: "TRANSPORT / 传输",
  OLT: "OLT / 接入",
  BASE_STATION: "BASE STATION / 基站",
};

function pct(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

function time(value: string): string {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleTimeString("zh-CN", { hour12: false });
}

function clusterCard(cluster: AlarmCluster) {
  const firstStep = cluster.plan_steps[0] ?? "转人工复核";
  const firstCase = cluster.similar_cases[0];
  return (
    <article className={`incident sev-${cluster.severity}`} key={cluster.id}>
      <div className="incident-head">
        <div>
          <div className="incident-id">{cluster.id} // {cluster.cause_label}</div>
          <div className="incident-ne">
            {cluster.root_ne_name} · {cluster.root_ne_type} · {cluster.alarm_count} 条告警 · 影响{" "}
            {cluster.affected_node_ids.length} 网元
          </div>
        </div>
        <div className="incident-right">
          <span className={`sev sev-${cluster.severity}`}>{SEVERITY_LABEL[cluster.severity]}</span>
          {cluster.needs_human_review && <span className="review">需人工复核</span>}
        </div>
      </div>
      <div className="confidence-row">
        <span>置信度 {pct(cluster.confidence)}</span>
        <span className="confidence-track">
          <span className="confidence-fill" style={{ width: `${cluster.confidence * 100}%` }} />
        </span>
      </div>
      <div className="incident-plan">▸ {firstStep}</div>
      {firstCase && (
        <div className="incident-case">
          ↳ {firstCase.case.id} {firstCase.case.title} · {pct(firstCase.score)}
        </div>
      )}
    </article>
  );
}

function topologyColumn(nodes: TopologyNode[], affected: Set<string>, type: string) {
  return (
    <div className="topo-col" key={type}>
      <div className="topo-head">
        {TYPE_LABEL[type] ?? type} · {nodes.length}
      </div>
      {nodes.length === 0 && <div className="topo-empty">—</div>}
      {nodes.map((node) => (
        <div className={`topo-node ${affected.has(node.id) ? "affected" : ""}`} key={node.id}>
          {node.name}
          <span>{node.id}</span>
        </div>
      ))}
    </div>
  );
}

export default function App() {
  const [run, setRun] = useState<OpsRun | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [countdown, setCountdown] = useState(REFRESH_SECONDS);
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null);
  const [region, setRegion] = useState("杭州");
  const [liveAlarms, setLiveAlarms] = useState<LiveAlarm[]>([]);
  const [liveStatus, setLiveStatus] = useState<"connecting" | "online" | "offline">("connecting");
  const [liveAnalysis, setLiveAnalysis] = useState<LiveAnalysis | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await fetchLatestRun();
      setRun(data);
      setUpdatedAt(new Date());
      setCountdown(REFRESH_SECONDS);
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "无法连接 FastAPI");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
    const timer = window.setInterval(() => void load(), REFRESH_SECONDS * 1000);
    return () => window.clearInterval(timer);
  }, [load]);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setCountdown((value) => (value <= 1 ? REFRESH_SECONDS : value - 1));
    }, 1000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(
    () =>
      connectAlarmStream({
        onAlarm: (alarm) => setLiveAlarms((current) => [alarm, ...current].slice(0, 8)),
        onAnalysis: (analysis) => {
          setLiveAnalysis(analysis);
          void load();
        },
        onStatus: setLiveStatus,
      }),
    [load],
  );

  const incidents = run?.clusters.filter((item) => item.cause_type !== "NOISE") ?? [];
  const noise = run?.clusters.filter((item) => item.cause_type === "NOISE") ?? [];
  const regions = run ? Array.from(new Set(run.topology.nodes.map((node) => node.region))) : [];
  const activeRegion = regions.includes(region) ? region : regions[0] ?? "";
  const affected = new Set(
    incidents.flatMap((item) => item.affected_node_ids),
  );
  const regionNodes = run
    ? run.topology.nodes.filter((node) => node.region === activeRegion)
    : [];
  const nodeTypes = ["CORE", "TRANSPORT", "OLT", "BASE_STATION"];

  return (
    <div className="wallboard">
      <header className="topbar">
        <div>
          <div className="eyebrow">TELECOM // NETWORK OPERATIONS CENTER</div>
          <h1>
            TelecomAgent <span>NOC</span>
          </h1>
          <div className="subline">ALARM COMPRESSION · TOPOLOGY CORRELATION · ROOT CAUSE</div>
        </div>
        <div className="status">
          <div>
            <span className="live-dot" /> LIVE · 自动刷新 {countdown}s
          </div>
          <div>{updatedAt ? `最后更新 ${updatedAt.toLocaleTimeString("zh-CN", { hour12: false })}` : "等待首次数据"}</div>
          <div>{run ? `RUN ${run.id} · ${run.llm_mode}` : "API 未连接"}</div>
        </div>
      </header>

      {error && (
        <div className="error-strip">
          数据加载失败：{error}
          <button type="button" onClick={() => void load()}>
            重试
          </button>
        </div>
      )}

      <section className="kpis">
        <div className="kpi">
          <span>RAW ALARMS</span>
          <b>{run?.total_alarms ?? "—"}</b>
        </div>
        <div className="kpi">
          <span>CLUSTERS</span>
          <b>{run?.cluster_count ?? "—"}</b>
        </div>
        <div className="kpi">
          <span>COMPRESSION</span>
          <b>{run ? pct(run.compression_ratio) : "—"}</b>
        </div>
        <div className="kpi">
          <span>P1 EVENTS</span>
          <b>{run ? run.clusters.filter((item) => item.severity === "P1").length : "—"}</b>
        </div>
        <div className="kpi">
          <span>REVIEW</span>
          <b className={run?.review_required ? "warn" : "ok"}>{run ? (run.review_required ? "REQUIRED" : "AUTO") : "—"}</b>
        </div>
      </section>

      <main className="main-grid">
        <section className="panel incidents-panel">
          <div className="panel-head">
            <span>INCIDENT QUEUE</span>
            <span>{incidents.length} ACTIVE · {noise.length} NOISE GROUPS</span>
          </div>
          <div className="incident-list">
            {!run && !loading && <div className="empty">WAITING FOR ANALYSIS RUN</div>}
            {loading && !run && <div className="empty">CONNECTING TO API…</div>}
            {incidents.map(clusterCard)}
            {run && incidents.length === 0 && <div className="empty">NO ACTIVE INCIDENTS</div>}
          </div>
        </section>

        <section className="panel topology-panel">
          <div className="panel-head">
            <span>TOPOLOGY / {activeRegion}</span>
            <span>RED = AFFECTED</span>
          </div>
          <div className="region-tabs">
            {regions.map((name) => (
              <button
                type="button"
                className={name === activeRegion ? "active" : ""}
                key={name}
                onClick={() => setRegion(name)}
              >
                {name}
              </button>
            ))}
          </div>
          <div className="topo-grid">
            {nodeTypes.map((type) =>
              topologyColumn(
                regionNodes.filter((node) => node.type === type),
                affected,
                type,
              ),
            )}
          </div>
        </section>
      </main>

      <section className="panel live-panel">
        <div className="panel-head">
          <span>LIVE ALARM FEED / WS</span>
          <span>
            {liveStatus === "online" ? "STREAM ONLINE" : liveStatus === "offline" ? "GATEWAY OFFLINE" : "CONNECTING"}
            {liveAnalysis
              ? ` · RUN ${liveAnalysis.run_id.slice(0, 8)} · ${liveAnalysis.cluster_count} CLUSTERS`
              : ""}
          </span>
        </div>
        <div className="live-feed">
          {liveStatus !== "online" && (
            <div className="live-offline">
              实时网关未连接。启动 <code>gateway</code> 后会自动接入：<code>cd gateway && npm run dev</code>
            </div>
          )}
          {liveStatus === "online" && liveAlarms.length === 0 && (
            <div className="live-offline">等待告警流…</div>
          )}
          {liveAlarms.map((alarm, index) => (
            <div className="live-row" key={`${alarm.alarm_id}-${index}`}>
              <span className={`sev sev-${alarm.severity}`}>{alarm.severity}</span>
              <span className="live-time">{time(alarm.alarm_time)}</span>
              <span className="live-ne">{alarm.ne_name}</span>
              <span className="live-type">{alarm.alarm_type}</span>
              <span className="live-desc">{alarm.description}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="bottom-grid">
        <div className="panel summary-panel">
          <div className="panel-head">
            <span>SHIFT SUMMARY</span>
            <span>{run ? time(run.created_at) : "—"}</span>
          </div>
          <p>{run?.summary ?? "等待分析结果。"}</p>
        </div>
        <div className="panel dispatch-panel">
          <div className="panel-head">
            <span>DISPATCH ORDER</span>
            <span>{run?.dispatch_plan.length ?? 0} ITEMS</span>
          </div>
          <ol>
            {(run?.dispatch_plan ?? []).slice(0, 5).map((item) => (
              <li key={item}>{item}</li>
            ))}
            {run && run.dispatch_plan.length === 0 && <li>无派单建议</li>}
          </ol>
        </div>
      </section>

      <footer>
        <span>DATA: SYNTHETIC INCIDENT DAY · 223 ALARMS / 83 NEs</span>
        <span>TelecomAgent · TypeScript NOC wallboard</span>
      </footer>
    </div>
  );
}
