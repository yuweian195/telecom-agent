"""Optional LLM summary for NOC analysis runs."""

from __future__ import annotations

import logging

from app.config import Settings, get_settings
from app.llm import prompts
from app.schemas import AlarmCluster

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._client = None
        if self.settings.llm_enabled:
            from openai import OpenAI

            self._client = OpenAI(
                api_key=self.settings.llm_api_key,
                base_url=self.settings.llm_base_url,
                timeout=self.settings.llm_timeout,
            )

    @property
    def enabled(self) -> bool:
        return self._client is not None

    @property
    def mode(self) -> str:
        return f"online:{self.settings.llm_model}" if self.enabled else "offline"

    def summarize_run(
        self,
        total_alarms: int,
        cluster_count: int,
        compression_ratio: float,
        overall_severity: str,
        clusters: list[AlarmCluster],
    ) -> str | None:
        if not self._client:
            return None
        cluster_text = "\n".join(
            f"- [{item.severity.value}] {item.root_ne_name} / {item.cause_label} / "
            f"{item.alarm_count} 条告警 / 置信度 {item.confidence:.0%}"
            for item in clusters[:6]
        )
        user = prompts.RUN_SUMMARY_USER.format(
            total_alarms=total_alarms,
            cluster_count=cluster_count,
            compression_ratio=compression_ratio,
            overall_severity=overall_severity,
            clusters=cluster_text,
        )
        try:
            response = self._client.chat.completions.create(
                model=self.settings.llm_model,
                messages=[
                    {"role": "system", "content": prompts.RUN_SUMMARY_SYSTEM},
                    {"role": "user", "content": user},
                ],
                temperature=0.2,
            )
            return (response.choices[0].message.content or "").strip() or None
        except Exception as exc:
            logger.warning("LLM summary failed, falling back to rules: %s", exc)
            return None


_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    global _client
    if _client is None:
        _client = LLMClient()
    return _client
