from fastapi.testclient import TestClient

import app.main as main


def test_health_endpoint():
    client = TestClient(main.app)
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["nodes"] >= 80
    assert payload["cases"] >= 6


def test_topology_endpoint():
    client = TestClient(main.app)
    response = client.get("/topology")

    assert response.status_code == 200
    assert len(response.json()["nodes"]) >= 80


def test_case_search_endpoint():
    client = TestClient(main.app)
    response = client.get("/cases/search", params={"cause": "FIBER_CUT", "q": "光缆"})

    assert response.status_code == 200
    assert response.json()[0]["case"]["id"] == "CASE-001"


def test_analyze_endpoint(monkeypatch, service):
    monkeypatch.setattr(main, "get_service", lambda: service)
    client = TestClient(main.app)
    response = client.post("/ops/analyze", json={})

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_alarms"] >= 200
    assert payload["compression_ratio"] >= 0.9

    detail = client.get(f"/ops/runs/{payload['id']}")
    assert detail.status_code == 200
    report = client.get(f"/ops/runs/{payload['id']}/report")
    assert report.status_code == 200
    assert "NOC 告警分析报告" in report.text


def test_upload_endpoint(monkeypatch, service, tmp_path):
    monkeypatch.setattr(main, "get_service", lambda: service)
    client = TestClient(main.app)
    csv_text = (
        "alarm_id,alarm_time,ne_id,ne_name,ne_type,alarm_type,severity,description,region,vendor\n"
        "A1,2026-11-14T03:12:05,TX-HZ-05,杭州城西传输环-05,TRANSPORT,LINK_DOWN,P1,光缆中断,杭州,Huawei\n"
        "A2,2026-11-14T03:12:20,OLT-HZ-01,杭州城西 OLT-01,OLT,LINK_DOWN,P1,上行中断,杭州,Huawei\n"
    )
    response = client.post(
        "/ops/analyze/upload",
        files={"file": ("alarms.csv", csv_text.encode("utf-8"), "text/csv")},
    )

    assert response.status_code == 200
    assert response.json()["total_alarms"] == 2
