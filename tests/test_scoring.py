from app.services.scoring_service import WEIGHTS, _calculate_confidence


def test_weights_sum_to_one():
    total = sum(WEIGHTS.values())
    assert abs(total - 1.0) < 0.001


def test_confidence_levels():
    assert _calculate_confidence(5) == "LOW"
    assert _calculate_confidence(30) == "MEDIUM"
    assert _calculate_confidence(100) == "HIGH"
    assert _calculate_confidence(200) == "HIGH"
    assert _calculate_confidence(0) == "LOW"
    assert _calculate_confidence(50) == "MEDIUM"
