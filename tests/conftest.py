import json
from pathlib import Path

import pytest

from app.config import Settings
from app.db import OpsRepository
from app.llm.client import LLMClient
from app.ops.alarms import load_alarms_csv
from app.ops.case_retriever import CaseRetriever
from app.ops.topology import load_topology
from app.services.ops import OpsService

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(llm_api_key="", database_path=tmp_path / "test.db")


@pytest.fixture
def repository(settings: Settings) -> OpsRepository:
    return OpsRepository(settings.database_path)


@pytest.fixture
def service(repository: OpsRepository, settings: Settings) -> OpsService:
    return OpsService(repository=repository, llm=LLMClient(settings))


@pytest.fixture
def alarms():
    return load_alarms_csv()


@pytest.fixture
def topology():
    return load_topology()


@pytest.fixture
def cases() -> CaseRetriever:
    return CaseRetriever()


@pytest.fixture
def labels() -> dict:
    return json.loads(
        (ROOT / "data" / "fixtures" / "incident_labels.json").read_text(encoding="utf-8")
    )
