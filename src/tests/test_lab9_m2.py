"""Calibration boundaries: invalid labels and judges with no information."""
import math
from pathlib import Path

import pytest

from lab9 import stats
from lab9.judge import calibrate

pytestmark = pytest.mark.student


@pytest.mark.parametrize("human,judge", [([], []), (["FAIL"], []), (["MAYBE"], ["PASS"])])
def test_invalid_label_pairs_are_rejected(human, judge):
    with pytest.raises(ValueError):
        stats.confusion(human, judge)


def test_zero_denominators_and_constant_predictions_have_no_signal():
    assert stats.precision_recall(["PASS", "FAIL"], ["PASS", "PASS"]) == (0.0, 0.0)
    assert stats.cohen_kappa(["PASS", "FAIL"], ["PASS", "PASS"]) == 0.0
    assert stats.precision_recall(["PASS"], ["FAIL"]) == (0.0, 0.0)


@pytest.mark.parametrize("rates", [(0.5, 0.5, 0.5), (0.5, 0.1, 0.9), (float("nan"), 0.8, 0.9), (1.1, 0.8, 0.9)])
def test_rogan_gladen_rejects_unidentifiable_or_invalid_rates(rates):
    with pytest.raises(ValueError):
        stats.rogan_gladen(*rates)


def test_rogan_gladen_clips_upper_boundary():
    assert stats.rogan_gladen(1.0, 0.8, 0.9) == 1.0


def test_rogan_gladen_formula_also_handles_an_inverted_classifier():
    assert stats.rogan_gladen(0.5, 0.2, 0.2) == pytest.approx(0.5)


def test_constant_judge_fails_calibration_without_crashing(tmp_path):
    path = tmp_path / "constant.csv"
    path.write_text("item_id,reply,human,judge\nx,OK,PASS,PASS\n", encoding="utf-8")
    result = calibrate(path)
    assert not result["passed"]
    assert math.isnan(result["kappa"])
    assert result["corrected_fail_rate"] is None


def test_public_judges_have_different_calibration_outcomes():
    assert calibrate(Path("data/eval/judge_tone_public.csv"))["passed"]
    assert not calibrate(Path("data/eval/judge_helpful_public.csv"))["passed"]
