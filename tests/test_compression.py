from app.ops.compression import compress_alarms
from app.schemas import Severity


def test_compression_reduces_alarm_volume(alarms, topology, cases):
    clusters = compress_alarms(alarms, topology, cases, window_minutes=10)

    ratio = 1 - len(clusters) / len(alarms)
    assert ratio >= 0.9
    assert len(clusters) <= 15


def test_fiber_cut_root_cause(alarms, topology, cases):
    clusters = compress_alarms(alarms, topology, cases)
    cluster = next(item for item in clusters if item.root_ne_id == "TX-HZ-05")

    assert cluster.cause_type == "FIBER_CUT"
    assert cluster.severity == Severity.P1
    assert cluster.alarm_count >= 40
    assert cluster.confidence >= 0.9
    assert "BS-HZ-101" in cluster.affected_node_ids
    assert any("OTDR" in step for step in cluster.plan_steps)


def test_power_failure_root_cause(alarms, topology, cases):
    clusters = compress_alarms(alarms, topology, cases)
    cluster = next(item for item in clusters if item.root_ne_id == "OLT-NB-01")

    assert cluster.cause_type == "POWER_FAILURE"
    assert cluster.severity == Severity.P1
    assert "BS-NB-101" in cluster.affected_node_ids


def test_core_signaling_root_cause(alarms, topology, cases):
    clusters = compress_alarms(alarms, topology, cases)
    cluster = next(item for item in clusters if item.root_ne_id == "CORE-HZ-01")

    assert cluster.cause_type == "SIGNALING_OVERLOAD"
    assert cluster.severity == Severity.P1
    assert cluster.confidence >= 0.9


def test_unclassified_high_severity_goes_to_human_review(alarms, topology, cases):
    clusters = compress_alarms(alarms, topology, cases)
    review_clusters = [item for item in clusters if item.needs_human_review]

    assert review_clusters
    assert any(item.cause_type == "UNKNOWN" for item in review_clusters)
    assert any("人工复核" in step for item in review_clusters for step in item.plan_steps)


def test_noise_clusters_are_marked(alarms, topology, cases):
    clusters = compress_alarms(alarms, topology, cases)
    noise = [item for item in clusters if item.cause_type == "NOISE"]

    assert noise
    assert all(item.confidence < 0.6 for item in noise)
