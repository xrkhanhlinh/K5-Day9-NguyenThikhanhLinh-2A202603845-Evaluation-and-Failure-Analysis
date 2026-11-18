"""Reproduce M5-M7 evidence using the unchanged public mutation/trap CLIs.

From src/: python -m scripts.check_advanced [--base-spec PATH]
Reports are generated from evaluations, never edited. The mutation hook only saves
the reports that the original CLI evaluates, avoiding a second set of trials.
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import redirect_stdout
from hashlib import sha256
import io
import json
from pathlib import Path

from lab8.console import utf8_stdio
from lab8.shapes import SHAPES
from lab9 import evalset, gate, mutation, stats, traps
from lab9.eval import load_spec, per_item, run_eval
from lab9.variant_agent import make_shape


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def capture(function, args):
    stream = io.StringIO()
    with redirect_stdout(stream):
        status = function(args)
    output = stream.getvalue()
    print(output, end="", flush=True)
    return {"exit": status, "stdout": output}


def main(argv=None):
    utf8_stdio()
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-spec")
    args = parser.parse_args(argv)
    spec_path = "config/metric_spec_v2.yaml"
    spec = load_spec(Path(spec_path))
    base_path = "reports/baseline_v2.json"
    base = json.loads(Path(base_path).read_text(encoding="utf-8"))
    base_spec = load_spec(Path(args.base_spec)) if args.base_spec else spec
    assert evalset.main(["--v2"]) == 0
    assert not gate.check(base, base, spec, base_spec)[0], "baseline self-gate failed"
    coverage = Counter(fm for item in evalset.load_jsonl(Path(spec["eval_set"])) for fm in item["failure_modes"])
    reports, steps = {}, {}

    def saving_eval(shape, current_spec, seeds=None):
        name = "swarm_aa" if shape == "swarm" and seeds is not None else shape
        print(f"Evaluating {name} ...", flush=True)
        report = run_eval(shape, current_spec, seeds)
        write(f"reports/eval_{name}_v2.json", report)
        reports[name] = report
        return report

    original = mutation.run_eval
    mutation.run_eval = saving_eval
    try:
        # These are the public CLI entry points, including their unmodified output.
        steps["aa"] = capture(mutation.main, ["--spec", spec_path, "--aa", "66,77,88,99,110"])
        mutation_args = ["--spec", spec_path, "--baseline", base_path]
        if args.base_spec:
            mutation_args += ["--base-spec", args.base_spec]
        steps["mutation"] = capture(mutation.main, mutation_args)
    finally:
        mutation.run_eval = original
    assert reports["swarm"]["metrics"] == base["metrics"], "committed baseline differs from a fresh swarm run"
    assert reports["swarm"]["rows"] == base["rows"], "committed baseline rows differ from fresh evaluation"
    aa_delta = {mid: reports["swarm_aa"]["metrics"][mid] - value
                for mid, value in base["metrics"].items()}
    assert all(value == 0 for value in aa_delta.values()), "MockLLM A/A delta is not zero"
    cases = {}
    for name, report in reports.items():
        if name == "swarm_aa":
            continue  # deliberately different seeds: A/A compares metrics, not paired gates
        blocked, lines = gate.check(report, base, spec, base_spec)
        ci = {}
        for mid in ("pass_rate", "refund_amount_correct", "proposal_amount_correct"):
            a, b = per_item(report, mid), per_item(base, mid)
            keys = sorted(a)
            delta, low, high = stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys])
            ci[mid] = {"delta": delta, "low": low, "high": high}
        cases[name] = {"run_id": report["run_id"], "metrics": report["metrics"],
                       "gate_exit": int(bool(blocked)), "blocked": blocked, "lines": lines, "paired_ci": ci}
    # Outcome checks must catch a DB override even when the trace has no override event.
    for name, switches in {"quiet_override": {"quiet_override"}, "misreport": {"no_override", "misreport"}}.items():
        SHAPES[name] = make_shape(name, switches)
        report = saving_eval(name, spec)
        blocked, lines = gate.check(report, base, spec, base_spec)
        assert blocked, f"{name} survived"
        if name == "quiet_override":
            assert report["metrics"]["db_fact_kept"] == 1.0
            assert "proposal_amount_correct" in blocked or "refund_amount_correct" in blocked
        else:
            assert "reply_amount_correct" in blocked
        cases[name] = {"run_id": report["run_id"], "metrics": report["metrics"],
                       "gate_exit": 1, "blocked": blocked, "lines": lines}
    steps["traps"] = capture(traps.main, ["--pr", "reports/eval_slice_regression_v2.json",
        "--baseline", base_path, "--spec", spec_path])
    trap_results = {}
    for name in traps.build(reports["slice_regression"], spec):
        gate_args = ["--pr", f"reports/traps/{name}.json", "--baseline", base_path]
        if name == "loosened_spec":
            gate_args += ["--spec", f"reports/traps/{name}.spec.yaml", "--base-spec", spec_path]
        else:
            gate_args += ["--spec", spec_path]
        result = capture(gate.main, gate_args)
        assert result["exit"] == 1 and "INTEGRITY" in result["stdout"], f"trap {name} survived"
        trap_results[name] = result
    assert "slice:money_movement/pass_rate" in cases["slice_regression"]["blocked"]
    assert "pass_hat_5" in cases["flaky_regression"]["blocked"]
    assert all(step["exit"] == 0 for step in steps.values())
    source_paths = sorted([*Path("lab9").glob("*.py"), *Path("config").glob("*v2.yaml"),
                           Path("config/fm_map.yaml"), Path(spec["eval_set"]), Path(spec["labels"])])
    fingerprints = {p.as_posix(): sha256(p.read_bytes()).hexdigest() for p in source_paths}
    summary = {"passed": True, "eval_set_sha": base["manifest"]["eval_set_sha"],
               "baseline_run_id": base["run_id"], "items": base["manifest"]["items"],
               "seeds": spec["seeds"], "aa_seeds": reports["swarm_aa"]["manifest"]["seeds"],
               "metric_spec_version": spec["metric_spec_version"], "coverage": dict(sorted(coverage.items())),
               "aa_delta": aa_delta, "cases": cases, "steps": steps, "traps": trap_results,
               "source_files_sha256": fingerprints}
    write("reports/advanced_validation.json", summary)
    print("M5-M7 PASS: A/A zero; mutation 3/3, false alarms 0; traps 4/4; quiet override + FM-08 blocked.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
