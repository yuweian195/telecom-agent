# 架构说明

本文档补充 README，说明 TelecomAgent 的拓扑模型、压缩算法、工作流与扩展点。

## 1. 分层

```text
Streamlit NOC ──┐
                ├── OpsService ── LangGraph ── topology / compression / cases / runbooks
FastAPI ────────┘                              └── SQLite
```

- `services/`：分析编排、持久化、报告。
- `graph/`：状态与节点，只做流程控制。
- `ops/`：告警、拓扑、压缩、根因、案例、处置手册。
- `llm/`：可选值班摘要；失败自动回退。
- `ui/`：NOC 控制台，不承载业务规则。

## 2. 拓扑模型

`data/topology/network.json`：

```json
{
  "nodes": [{"id": "TX-HZ-05", "name": "杭州城西传输环-05", "type": "TRANSPORT", "region": "杭州"}],
  "edges": [{"source": "TX-HZ-05", "target": "OLT-HZ-01", "relation": "uplink"}]
}
```

`TopologyGraph` 提供：

- `children[node]`：直接下游；
- `descendants(node)`：BFS 影响域（含自身）；
- `type_rank(node)`：CORE 0 → TRANSPORT 1 → OLT 2 → BASE_STATION 3，用于根候选排序。

## 3. 告警处理

- `load_alarms_csv()`：读取 CSV，Pydantic 校验，跳过坏行；
- `dedupe_alarms()`：按 `alarm_id` 去重并按时间排序；
- `window_start()`：按 10 分钟对齐时间窗；
- `in_window()`：根告警与成员告警的时间差约束。

## 4. 压缩与根因

### 4.1 根候选

窗口内满足以下条件的告警进入根候选：

- 网元类型：CORE / TRANSPORT / OLT；
- 严重度：P1 / P2；
- 类型：LINK_DOWN、LINK_DEGRADED、POWER_FAILURE、SIGNAL_OVERLOAD、HIGH_TEMPERATURE、CONFIG_CHANGE。

排序键：`(拓扑层级, 严重度, 时间)`。

### 4.2 聚合

对每个根候选：

1. `descendants(root.ne_id)` 得到影响域；
2. 收集窗口内、未分配、落在影响域的告警；
3. 成员数 ≥ 2 或根告警为 P1 时生成事件；
4. 已分配告警不再进入后续根候选。

### 4.3 剩余告警

- P1/P2：按时间窗聚成“未归类”事件，标记人工复核；
- P3/P4：按告警类型聚成背景噪声事件。

### 4.4 根因映射

`infer_cause(root)`：

| 条件 | 根因 |
|---|---|
| TRANSPORT `LINK_DOWN` | FIBER_CUT |
| OLT `LINK_DOWN` | UPLINK_DOWN |
| `POWER_FAILURE` | POWER_FAILURE |
| `SIGNAL_OVERLOAD` | SIGNALING_OVERLOAD |
| `HIGH_TEMPERATURE` | OVERHEATING |
| `CONFIG_CHANGE` | CONFIG_CHANGE |
| `LINK_DEGRADED` + CRC/误码/光功率 | OPTICAL_DEGRADATION |
| 其他 | UNKNOWN |

### 4.5 置信度

基础 0.45，叠加：

- 影响网元 ≥ 3：+0.15；
- 根告警 P1：+0.10；
- 影响网元类型 ≥ 2：+0.10；
- 下游覆盖率 ≥ 30% 且影响域 ≥ 3：+0.10；
- 相似案例 ≥ 0.5：+0.08；
- 上限 0.97。

低于 `confidence_threshold`（默认 0.6）或 UNKNOWN → 人工复核。

## 5. 案例检索

`CaseRetriever`：

- 中文二元组 + ASCII 词元；
- 查询 = 根因 + 症状文本 + 根网元类型；
- 案例 = 症状 + 标签 + 标题；
- `score = 0.5 × Jaccard + 0.4 × cause_match + 0.1 × ne_type_match`；
- 返回 top-k，用于证据与处置参考。

## 6. 工作流

`OpsState` 字段：

| 字段 | 说明 |
|---|---|
| `alarms` | 标准化后的告警 |
| `clusters` | 聚合事件 |
| `topology` | 拓扑快照 |
| `overall_severity` | 最高事件严重度 |
| `compression_ratio` | 压缩率 |
| `dispatch_plan` | 派单建议 |
| `review_required` | 是否需要人工复核 |

节点：

1. `load_alarms`：加载/校验/去重；
2. `compress_alarms`：拓扑压缩 + 根因 + 案例；
3. `diagnose`：统计置信度与复核数量；
4. `assess`：整体严重度、摘要、派单、复核判断；
5. 条件边：`dispatch` 或 `human_review`；
6. `save_run`：写入 `ops_runs`。

## 7. 数据模型

`ops_runs`：

| 列 | 说明 |
|---|---|
| `id` | 12 位分析编号 |
| `total_alarms` | 原始告警数 |
| `cluster_count` | 聚合事件数 |
| `compression_ratio` | 压缩率 |
| `overall_severity` | P1–P4 |
| `created_at` | 时间 |
| `payload` | 完整 JSON（事件、拓扑、派单、trace） |

## 8. 扩展点

- **接入真实告警**：替换 CSV 来源或实现 Kafka/Webhook 消费者，保持 `Alarm` 模型。
- **动态拓扑**：将 `network.json` 换成资源系统/CMDB 同步；`TopologyGraph` 接口不变。
- **新增根因**：在 `infer_cause()` 增加映射，在 `runbooks.py` 增加处置步骤，并补测试与标签。
- **案例库扩容**：替换 `cases.jsonl`；如需向量召回，实现 `CaseRetriever.search()` 相同返回结构。
- **替换存储**：实现 `OpsRepository` 方法集，业务层不改。

## 9. TypeScript NOC 大屏

`web/` 是独立的 Vite + React 19 + TypeScript 应用：

- `src/api.ts` 拉取 `/ops/runs?limit=1` 与最新 run 详情；
- `src/App.tsx` 渲染 KPI、事件队列、拓扑和派单；
- 每 20 秒自动刷新，适合值班室大屏；
- Vite `base` 为 `/wallboard/`；
- `npm run build` 生成 `web/dist`，FastAPI 将其挂载到 `/wallboard`；
- Docker 构建阶段使用 Node 20 构建，再复制 `dist` 到 Python 镜像；
- CI 增加 `npm ci && npm run build` 检查。

开发模式：

```bash
cd web
npm run dev
# http://127.0.0.1:5173/wallboard/
```

## 10. 部署

- 单机：`streamlit run ui/streamlit_app.py` + `uvicorn app.main:app`。
- 容器：`docker compose up --build`，API 8000，UI 8501。
- 数据：默认 `data/telecom_agent.db`，生产建议挂载持久卷并替换为 PostgreSQL。
