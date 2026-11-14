from app.schemas import OpsAnalyzeRequest


def test_analyze_sample_run_is_persisted(service):
    run = service.analyze(OpsAnalyzeRequest())

    assert run.total_alarms >= 200
    assert run.cluster_count <= 15
    assert run.compression_ratio >= 0.9
    assert run.overall_severity.value == "P1"
    assert run.review_required is True
    assert "human_review" in [step.node for step in run.trace]
    assert run.dispatch_plan

    loaded = service.get_run(run.id)
    assert loaded is not None
    assert loaded.total_alarms == run.total_alarms
    assert service.list_recent(5)[0].id == run.id


def test_analyze_custom_alarm_subset(service, alarms):
    subset = [alarm for alarm in alarms if alarm.ne_id in {"TX-HZ-05", "OLT-HZ-01", "BS-HZ-101"}][:20]
    run = service.analyze(OpsAnalyzeRequest(alarms=subset))

    assert run.total_alarms == len(subset)
    assert run.cluster_count >= 1
    assert run.topology is not None


def test_cases_search(service):
    matches = service.search_cases(symptoms="光缆 中断 OLT 批量离线", top_k=3)
    assert matches
    assert matches[0].case.cause_type == "FIBER_CUT"
