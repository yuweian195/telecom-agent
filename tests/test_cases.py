def test_fiber_cut_case_is_first(cases):
    matches = cases.search(
        "FIBER_CUT",
        "传输链路中断 OLT 批量离线 基站退服 CRC 错误率上升 LOS",
        "TRANSPORT",
    )

    assert matches
    assert matches[0].case.id == "CASE-001"


def test_power_case_is_first(cases):
    matches = cases.search(
        "POWER_FAILURE",
        "市电中断 蓄电池放电 OLT 离线 基站批量退服",
        "OLT",
    )

    assert matches
    assert matches[0].case.id == "CASE-002"


def test_case_search_respects_top_k(cases):
    matches = cases.search("UNKNOWN", "告警", "", top_k=2)
    assert len(matches) <= 2
