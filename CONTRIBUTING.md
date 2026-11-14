# Contributing

## 本地开发

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # macOS / Linux
pip install -e ".[dev]"
```

## 提交前检查

```bash
ruff check app ui tests scripts
pytest -q
python scripts/evaluate.py
```

## 代码约定

- 拓扑与告警处理放在 `app/ops/`，工作流只负责状态流转。
- 根因规则必须可复现、可单测；新增规则同步更新 `incident_labels.json` 与测试。
- LLM 只能生成摘要措辞，不得参与根因判定、置信度或派单排序。
- 新增告警字段时同步更新 CSV 生成器、Pydantic 模型和 UI 表头。
- 新增接口同步更新 README 与架构文档。

## 数据与安全

仓库内告警、拓扑与案例均为合成数据。请勿提交真实网络拓扑、设备 IP、客户信息或生产日志。

处置步骤是通用建议，不构成对具体设备的操作指令；真实环境执行前需遵循变更与安全规范。
