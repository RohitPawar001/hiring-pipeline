import pytest
from app.pipeline import validate_move, STAGES


def test_normal_forward_moves():
    # Valid forward sequence: Applied -> Screening -> Interview -> Offer -> Hired
    assert validate_move("Applied", "Screening") is None
    assert validate_move("Screening", "Interview") is None
    assert validate_move("Interview", "Offer") is None
    assert validate_move("Offer", "Hired") is None


def test_skipping_stages_fails():
    assert validate_move("Applied", "Interview") is not None
    assert validate_move("Applied", "Offer") is not None
    assert validate_move("Applied", "Hired") is not None
    assert validate_move("Screening", "Offer") is not None
    assert validate_move("Screening", "Hired") is not None
    assert validate_move("Interview", "Hired") is not None


def test_backward_moves_fail():
    assert validate_move("Screening", "Applied") is not None
    assert validate_move("Interview", "Screening") is not None
    assert validate_move("Offer", "Interview") is not None


def test_rejecting_from_non_final_stages_works():
    for stage in ["Applied", "Screening", "Interview", "Offer"]:
        assert validate_move(stage, "Rejected") is None


def test_leaving_final_stages_fails():
    for final_stage in ["Hired", "Rejected"]:
        for target in STAGES:
            err = validate_move(final_stage, target)
            assert err is not None
            assert "final outcome" in err


def test_invalid_target_stage_fails():
    assert validate_move("Applied", "UnknownStage") is not None
    assert validate_move("Applied", "random_string") is not None
