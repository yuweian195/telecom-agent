from app.ops.alarms import dedupe_alarms, load_alarms_csv, window_start
from app.ops.topology import load_topology


def test_sample_dataset_is_complete(alarms):
    assert len(alarms) >= 200
    assert sum(1 for alarm in alarms if alarm.severity.value == "P1") >= 4


def test_topology_has_core_to_access_layers():
    topology = load_topology()

    assert topology.count >= 80
    descendants = topology.descendants("TX-HZ-05")
    assert "OLT-HZ-01" in descendants
    assert "BS-HZ-101" in descendants
    assert topology.type_rank("CORE-HZ-01") < topology.type_rank("OLT-HZ-01")


def test_window_start_buckets():
    assert window_start(load_alarms_csv()[0].alarm_time, 10).minute % 10 == 0


def test_dedupe_removes_duplicate_ids(alarms):
    duplicated = alarms + alarms[:5]
    assert len(dedupe_alarms(duplicated)) == len(alarms)
