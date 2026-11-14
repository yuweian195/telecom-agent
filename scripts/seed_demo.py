"""Run one sample analysis so the TypeScript wallboard has data.

Usage:
    python scripts/seed_demo.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.schemas import OpsAnalyzeRequest  # noqa: E402
from app.services.ops import get_service  # noqa: E402


def main() -> None:
    run = get_service().analyze(OpsAnalyzeRequest())
    print(
        f"告警 {run.total_alarms} 条 → 事件 {run.cluster_count} 起，"
        f"压缩率 {run.compression_ratio:.1%}，严重度 {run.overall_severity.value}"
    )
    print(f"分析编号：{run.id}")


if __name__ == "__main__":
    main()
