# Alarm Gateway

TelecomAgent 的 TypeScript/Node 告警流网关。

- 从 `data/alarms/incident_day.csv` 持续回放告警
- 每 20 条批量调用 Python `POST /ops/analyze`
- 通过 WebSocket 向 NOC 大屏推送实时告警与分析结果

## 运行

```bash
npm install
npm run dev
```

默认 `ws://127.0.0.1:8081/ws/alarms`，分析服务 `http://127.0.0.1:8000`。

## 环境变量

| 变量 | 默认值 | 说明 |
|---|---|---|
| `PORT` | `8081` | HTTP / WebSocket 端口 |
| `OPS_API_URL` | `http://127.0.0.1:8000` | Python 分析服务 |
| `ALARM_CSV` | `../data/alarms/incident_day.csv` | 告警 CSV |
| `STREAM_INTERVAL_MS` | `180` | 每条告警间隔 |
| `BATCH_SIZE` | `20` | 每新增多少条触发一次分析 |
| `WINDOW_SIZE` | `120` | 滑动窗口大小 |
| `BUFFER_SIZE` | `80` | 内存回放缓冲 |

## 接口

- `GET /health`：网关状态、批次、客户端数
- `GET /api/alarms?limit=20`：最近告警
- `WS /ws/alarms`：实时告警、分析结果
