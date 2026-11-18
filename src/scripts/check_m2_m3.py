"""Generate M2/M3 evidence from graders and public fixtures; never edit reports by hand.

Run from src/: python -m scripts.check_m2_m3 [--section m2|m3|all]
This is a diagnostic check, not the M4 release gate.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from lab8.console import utf8_stdio
from lab8.shapes import SHAPES
from lab9.eval import load_spec, run_eval
from lab9.graders import GRADERS
from lab9.judge import calibrate
from lab9.variant_agent import make_shape
from lab9.variants import register


def write_report(name: str, report: dict) -> None:
    if report.get("evaluator_failures"):
        raise RuntimeError(f"refusing to save broken evaluation: {report['evaluator_failures']}")
    path = Path("reports") / name
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    print(f"wrote {path}", flush=True)


def check_m2() -> bool:
    results = {name: calibrate(Path(f"data/eval/judge_{name}_public.csv")) for name in ("tone", "helpful")}
    write_report("judge_calibration_m2.json", results)
    for name, result in results.items():
        print(name, {k: v for k, v in result.items() if k != "disagreements"}, flush=True)
    return results["tone"]["passed"] and not results["helpful"]["passed"]


def check_m3() -> bool:
    register()
    SHAPES["m3_misreport"] = make_shape("m3_misreport", {"no_override", "misreport"})
    spec = load_spec()
    reports = {}
    for shape in ("fixed", "seeded_regression", "honest_refactor", "m3_misreport"):
        print(f"Evaluating {shape}...", flush=True)
        report = run_eval(shape, spec)
        write_report(f"eval_{shape}.json", report)
        reports[shape] = report

    # Same definition as lab9.mutation.detect: an explanatory grader must flag
    # each failing seeded row; false alarms count any flag on the fixed rows.
    bad_value = {m["id"]: "max" in (m.get("threshold") or {}) for m in spec["metrics"]
                 if m["id"] in GRADERS and m["id"] != "pass_rate"}

    def flagged(row):
        return any(row.get(mid) is bad for mid, bad in bad_value.items())

    broken = [r for r in reports["seeded_regression"]["rows"] if r["pass_rate"] is False]
    detected = sum(flagged(r) for r in broken)
    fixed = reports["fixed"]["rows"]
    honest = reports["honest_refactor"]["rows"]
    false_alarms = sum(flagged(r) for r in fixed)
    honest_alarms = sum(flagged(r) for r in honest)
    fm08 = reports["m3_misreport"]["rows"]
    fm08_bad = [r for r in fm08 if r["reply_amount_correct"] is False]
    summary = {
        "run_ids": {name: r["run_id"] for name, r in reports.items()},
        "eval_set_sha": reports["fixed"]["manifest"]["eval_set_sha"],
        "metric_spec_version": spec["metric_spec_version"],
        "failing_seeded_rows": len(broken), "detected_rows": detected,
        "detection_rate": detected / len(broken) if broken else 0.0,
        "fixed_rows": len(fixed), "fixed_false_alarms": false_alarms,
        "fixed_false_alarm_rate": false_alarms / len(fixed),
        "honest_refactor_rows": len(honest), "honest_refactor_false_alarms": honest_alarms,
        "fm08_failed_reply_rows": len(fm08_bad),
        "fm08_failed_claims": sorted({r["item_id"] for r in fm08_bad}),
        "fm08_ledger_and_lab8_pass": all(r["pass_rate"] and r["refund_amount_correct"] for r in fm08),
        "metrics": {name: r["metrics"] for name, r in reports.items()},
    }
    summary["passed"] = (summary["detection_rate"] >= 0.80
                         and summary["fixed_false_alarm_rate"] <= 0.10
                         and honest_alarms == 0 and bool(fm08_bad)
                         and summary["fm08_ledger_and_lab8_pass"])
    write_report("m3_diagnostics.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    return summary["passed"]


def main() -> int:
    utf8_stdio()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--section", choices=("all", "m2", "m3"), default="all")
    args = parser.parse_args()
    results = []
    if args.section in ("all", "m2"):
        results.append(check_m2())
    if args.section in ("all", "m3"):
        results.append(check_m3())
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
