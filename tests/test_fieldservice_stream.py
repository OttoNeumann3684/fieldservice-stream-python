from src.fieldservice_stream import decide_dispatch


def test_unsafe_follow_up_is_urgent():
    decision = decide_dispatch("awaiting review", "Technician reports an unsafe exposed wire")
    assert decision.priority == "urgent"
    assert "Safety" in decision.reason


def test_assigned_order_stays_scheduled():
    decision = decide_dispatch("assigned", "Bring a replacement filter")
    assert decision.priority == "scheduled"
