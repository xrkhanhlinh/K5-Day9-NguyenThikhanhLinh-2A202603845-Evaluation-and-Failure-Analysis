"""Independent small-vector, slice and tampered-evidence regression tests."""
import copy
from itertools import combinations

import pytest

from lab9 import gate, stats
from lab9.eval import aggregate

pytestmark = pytest.mark.student
SEEDS = [11, 22, 33, 44, 55]
SPEC = {"eval_set_version": "v2", "seeds": SEEDS,
        "metrics": [{"id": "pass_rate", "kind": "capability", "blocking": True,
                     "threshold": {"min": 0.8, "no_significant_drop": True}}],
        "slices": [{"name": "unseen_domain", "metric": "pass_rate", "min": 0.95,
                    "no_significant_drop": True, "blocking": True}]}


def report():
    rows = [{"item_id": f"X-{i}", "seed": s, "pass_rate": True, "cost": 1.0,
             "slices": ["unseen_domain"] if i < 2 else []} for i in range(20) for s in SEEDS]
    return {"manifest": {"items": 20, "seeds": SEEDS[:], "eval_set_sha": "test"},
            "rows": rows, "metrics": aggregate(rows, ["pass_rate"]), "evaluator_failures": []}


def recompute(rep):
    rep["metrics"] = aggregate(rep["rows"], ["pass_rate"])


def test_pass_k_matches_enumerated_sampling_without_replacement():
    for n in range(1, 9):
        for c in range(n + 1):
            values = [True] * c + [False] * (n - c)
            for k in range(1, n + 1):
                samples = list(combinations(values, k))
                at, hat = stats.pass_at_k(n, c, k), stats.pass_hat_k(n, c, k)
                assert at == pytest.approx(sum(any(s) for s in samples) / len(samples))
                assert hat == pytest.approx(sum(all(s) for s in samples) / len(samples))
                assert hat <= c / n + 1e-12
                assert c / n <= at + 1e-12


@pytest.mark.parametrize("args", [(0, 0, 1), (-1, 0, 1), (5, -1, 2), (5, 6, 1),
    (5, 2, 0), (5, 2, 6), (5.0, 2, 1), (5, 2.5, 1), (5, 2, True),
    (True, 1, 1), (5, False, 1), (5, 2, "1"), (5, 2, None)])
def test_pass_k_rejects_invalid_arguments(args):
    for function in (stats.pass_at_k, stats.pass_hat_k):
        with pytest.raises(ValueError):
            function(*args)


def test_generic_slice_catches_regression_hidden_by_global_mean_and_ci():
    base, pr = report(), report()
    for row in pr["rows"]:
        if row["slices"]:
            row["pass_rate"] = False
    recompute(pr)
    blocked, _ = gate.check(pr, base, SPEC)
    assert pr["metrics"]["pass_rate"] == 0.9
    assert "pass_rate" not in blocked
    assert blocked == ["slice:unseen_domain/pass_rate"]


def test_slice_significant_drop_above_floor_and_nonblocking_warning():
    base, pr, spec = report(), report(), copy.deepcopy(SPEC)
    spec["slices"][0]["min"] = 0.7
    for row in pr["rows"]:
        if row["slices"] and row["seed"] == 11:
            row["pass_rate"] = False
    recompute(pr)
    assert gate.check(pr, base, spec)[0] == ["slice:unseen_domain/pass_rate"]
    spec["slices"][0]["blocking"] = False
    blocked, lines = gate.check(pr, base, spec)
    assert not blocked and any("unseen_domain" in line and "warn" in line for line in lines)


def test_missing_slice_is_blocked_instead_of_silently_skipped():
    rep, spec = report(), copy.deepcopy(SPEC)
    spec["slices"][0]["name"] = "absent"
    assert gate.check(rep, rep, spec)[0] == ["slice:absent/pass_rate"]


def test_reliability_blocks_even_when_global_mean_improves():
    base, pr, spec = report(), report(), copy.deepcopy(SPEC)
    spec["slices"] = []
    spec["metrics"].append({"id": "pass_hat_5", "kind": "capability", "blocking": True,
                            "threshold": {"min": 0.85}})
    for row in base["rows"]:
        if row["item_id"] in {"X-0", "X-1", "X-2"} and row["seed"] in {11, 22}:
            row["pass_rate"] = False
    for row in pr["rows"]:
        if row["item_id"] in {"X-3", "X-4", "X-5", "X-6"} and row["seed"] == 11:
            row["pass_rate"] = False
    for rep in (pr, base):
        rep["metrics"] = aggregate(rep["rows"], ["pass_rate"], k_values=[5])
    assert gate.check(base, base, spec)[0] == []
    assert pr["metrics"]["pass_rate"] > base["metrics"]["pass_rate"]
    assert gate.check(pr, base, spec)[0] == ["pass_hat_5"]


@pytest.mark.parametrize("change", ["duplicate", "missing", "undeclared_seed", "failures",
    "null", "nan_row", "inf_row", "nan_summary", "inf_summary", "forged_summary",
    "retag_all", "retag_one", "manifest_seeds", "missing_metric", "bad_manifest"])
def test_tampering_cannot_turn_a_report_green(change):
    base, pr = report(), report()
    if change == "duplicate":
        pr["rows"][-1] = copy.deepcopy(pr["rows"][0])
        recompute(pr)  # length and mean still look valid
    elif change == "missing":
        pr["rows"].pop()
        recompute(pr)
    elif change == "undeclared_seed":
        pr["rows"][0]["seed"] = 1234
    elif change == "failures":
        pr["evaluator_failures"] = ["all scores green, but an evaluator crashed"]
    elif change == "null":
        pr["rows"][0]["pass_rate"] = None
    elif change in ("nan_row", "inf_row"):
        pr["rows"][0]["pass_rate"] = float("nan" if change == "nan_row" else "inf")
    elif change in ("nan_summary", "inf_summary"):
        pr["metrics"]["pass_rate"] = float("nan" if change == "nan_summary" else "inf")
    elif change == "forged_summary":
        pr["rows"][0]["pass_rate"] = False
    elif change in ("retag_one", "retag_all"):
        for row in pr["rows"][:1 if change == "retag_one" else 5]:
            row["slices"] = []
    elif change == "manifest_seeds":
        pr["manifest"]["seeds"] = SEEDS[:-1]
    elif change == "missing_metric":
        del pr["metrics"]["pass_rate"]
    elif change == "bad_manifest":
        pr["manifest"] = None
    blocked, lines = gate.check(pr, base, SPEC)
    assert blocked == ["integrity"]
    assert all("INTEGRITY" in line for line in lines)
    assert gate.integrity_check(base, pr, SPEC), "baseline needs the same validation"


@pytest.mark.parametrize("change", ["remove_metric", "disable_metric", "lower_min", "remove_min",
    "drop_ci", "remove_slice", "disable_slice", "lower_slice_min", "drop_slice_ci", "change_kind"])
def test_ratchet_cannot_be_bypassed_by_metric_version_bump(change):
    rep, loose = report(), copy.deepcopy(SPEC)
    loose["metric_spec_version"] = "999.0"
    metric, slice_entry = loose["metrics"][0], loose["slices"][0]
    if change == "remove_metric":
        loose["metrics"] = []
    elif change == "disable_metric":
        metric["blocking"] = False
    elif change == "lower_min":
        metric["threshold"]["min"] = 0.1
    elif change == "remove_min":
        del metric["threshold"]["min"]
    elif change == "drop_ci":
        del metric["threshold"]["no_significant_drop"]
    elif change == "remove_slice":
        loose["slices"] = []
    elif change == "disable_slice":
        slice_entry["blocking"] = False
    elif change == "lower_slice_min":
        slice_entry["min"] = 0.1
    elif change == "drop_slice_ci":
        del slice_entry["no_significant_drop"]
    elif change == "change_kind":
        metric["kind"] = "system"
    assert gate.check(rep, rep, loose, SPEC)[0] == ["integrity"]


@pytest.mark.parametrize("bound", ["max", "max_increase"])
def test_ratchet_rejects_increasing_an_upper_bound(bound):
    rep, previous = report(), copy.deepcopy(SPEC)
    previous["metrics"][0]["threshold"][bound] = 1
    loose = copy.deepcopy(previous)
    loose["metrics"][0]["threshold"][bound] = 2
    assert gate.check(rep, rep, loose, previous)[0] == ["integrity"]


def test_stricter_spec_and_honest_row_reordering_are_allowed():
    base, pr, strict = report(), report(), copy.deepcopy(SPEC)
    strict["metrics"][0]["threshold"]["min"] = 0.9
    pr["rows"].reverse()
    assert gate.check(pr, base, strict, SPEC)[0] == []
