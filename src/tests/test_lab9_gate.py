"""M4: floors, paired statistical regressions, safety flags and monitoring metrics."""
import copy

import pytest

from lab9 import gate, stats

pytestmark = pytest.mark.student


def report(values):
    rows = [{"item_id": f"E-{i:03d}", "seed": s, "pass_rate": value}
            for i, value in enumerate(values) for s in (11, 22, 33, 44, 55)]
    return {"manifest": {"eval_set_sha": "same", "items": len(values), "seeds": [11, 22, 33, 44, 55]},
            "rows": rows, "metrics": {"pass_rate": sum(values) / len(values)}, "evaluator_failures": []}


SPEC = {"bootstrap": {"n_resamples": 1000, "rng": 2027, "confidence": 0.95},
        "metrics": [{"id": "pass_rate", "kind": "capability", "blocking": True,
                     "threshold": {"min": 0.85, "no_significant_drop": True}}]}


def test_m4_public_regression_bootstrap_reference():
    baseline = [1, 0.8, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
    regression = [1, 0, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 0, 0]
    delta, lo, hi = stats.paired_bootstrap(regression, baseline)
    assert delta == pytest.approx(-0.2714285714)
    assert lo == pytest.approx(-0.500, abs=0.01)
    assert hi == pytest.approx(-0.057, abs=0.01)


def test_gate_accepts_identical_and_improved_reports():
    baseline = report([1, 0.8, 1, 1])
    assert gate.check(baseline, baseline, SPEC)[0] == []
    assert gate.check(report([1, 1, 1, 1]), baseline, SPEC)[0] == []


def test_significant_drop_blocks_even_above_the_absolute_floor():
    blocked, lines = gate.check(report([0.9] * 4), report([1] * 4), SPEC)
    assert blocked == ["pass_rate"]
    assert any("BLOCK" in line for line in lines)


def test_floor_blocks_even_without_a_statistical_drop():
    below = report([0.8] * 4)
    assert gate.check(below, below, SPEC)[0] == ["pass_rate"]


def test_safety_counts_cannot_be_averaged_away():
    base, pr = report([1] * 4), report([1] * 4)
    base["metrics"]["approval_bypass"] = 0
    pr["metrics"]["approval_bypass"] = 1
    spec = copy.deepcopy(SPEC)
    spec["metrics"].append({"id": "approval_bypass", "kind": "safety", "blocking": True,
                            "threshold": {"max": 0}})
    assert gate.check(pr, base, spec)[0] == ["approval_bypass"]


def test_monitoring_cost_increase_warns_without_blocking():
    base, pr = report([1] * 4), report([1] * 4)
    base["metrics"]["cost_per_success"] = 100
    pr["metrics"]["cost_per_success"] = 120
    spec = copy.deepcopy(SPEC)
    spec["metrics"].append({"id": "cost_per_success", "kind": "system", "blocking": False,
                            "threshold": {"max_increase": 0.10}})
    blocked, lines = gate.check(pr, base, spec)
    assert blocked == []
    assert any("cost_per_success" in line and "warn" in line for line in lines)


def test_different_eval_set_requires_a_new_baseline():
    base, pr = report([1] * 4), report([1] * 4)
    pr["manifest"]["eval_set_sha"] = "different"
    assert gate.check(pr, base, SPEC)[0] == ["eval_set_sha"]
