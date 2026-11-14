"""FastAPI service for NOC alarm analysis."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.config import BASE_DIR, get_settings
from app.db import get_repository
from app.schemas import (
    Alarm,
    CaseMatch,
    HealthResponse,
    OpsAnalyzeRequest,
    OpsRun,
    OpsRunListItem,
    Topology,
)
from app.services.ops import get_service
from app.services.reporting import run_markdown


@asynccontextmanager
async def lifespan(_: FastAPI):
    get_repository()
    yield


settings = get_settings()
app = FastAPI(
    title="TelecomAgent API",
    version=settings.version,
    description="Alarm compression, topology correlation and root-cause diagnosis.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    service = get_service()
    return HealthResponse(
        status="ok",
        version=settings.version,
        llm_mode=service.llm.mode,
        nodes=len(service.topology().nodes),
        cases=service.case_count(),
    )


@app.get("/topology", response_model=Topology)
def topology() -> Topology:
    return get_service().topology()


@app.get("/cases/search", response_model=list[CaseMatch])
def search_cases(
    cause: str = "", q: str = "", top_k: int = 5
) -> list[CaseMatch]:
    return get_service().search_cases(cause, q, top_k=max(1, min(top_k, 20)))


@app.get("/alarms/sample", response_model=list[Alarm])
def sample_alarms(limit: int = 50) -> list[Alarm]:
    from app.ops.alarms import load_alarms_csv

    return load_alarms_csv()[: max(1, min(limit, 500))]


@app.post("/ops/analyze", response_model=OpsRun)
def analyze(payload: OpsAnalyzeRequest) -> OpsRun:
    return get_service().analyze(payload)


@app.post("/ops/analyze/upload", response_model=OpsRun)
async def analyze_upload(file: Annotated[UploadFile, File(...)]) -> OpsRun:
    content = await file.read()
    try:
        return get_service().analyze_csv_bytes(content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/ops/runs", response_model=list[OpsRunListItem])
def list_runs(limit: int = 20) -> list[OpsRunListItem]:
    return get_service().list_recent(limit=max(1, min(limit, 100)))


@app.get("/ops/runs/{run_id}", response_model=OpsRun)
def get_run(run_id: str) -> OpsRun:
    run = get_service().get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="分析记录不存在")
    return run


@app.get("/ops/runs/{run_id}/report", response_class=PlainTextResponse)
def get_run_report(run_id: str) -> PlainTextResponse:
    run = get_service().get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="分析记录不存在")
    return PlainTextResponse(
        run_markdown(run),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="noc-{run_id}.md"'},
    )


# TypeScript NOC wallboard (built with `npm run build`).
WALLBOARD_DIST = BASE_DIR / "web" / "dist"
if WALLBOARD_DIST.exists():
    app.mount("/wallboard", StaticFiles(directory=WALLBOARD_DIST, html=True), name="wallboard")

    @app.get("/", include_in_schema=False)
    def wallboard_root() -> RedirectResponse:
        return RedirectResponse(url="/wallboard/")
