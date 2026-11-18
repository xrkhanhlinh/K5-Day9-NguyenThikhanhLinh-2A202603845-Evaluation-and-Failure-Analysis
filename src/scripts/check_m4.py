"""Replay the Core CI steps locally and save actual command outputs as M4 evidence.

Run from src/: python -m scripts.check_m4 [--build-baseline] [--reuse-candidates]
The baseline is preserved unless --build-baseline is explicitly requested.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import yaml

from lab8.console import utf8_stdio
from lab9.eval import load_spec, per_item
from lab9.evalset import sha12
from lab9.graders import GRADERS
from lab9.stats import paired_bootstrap


def main() -> int:
    utf8_stdio()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-baseline", action="store_true")
    parser.add_argument("--reuse-candidates", action="store_true", help="reuse existing fixed/seeded reports after manifest checks")
    args = parser.parse_args()
    spec_path = Path("config/metric_spec.yaml")
    baseline_path = Path("reports/baseline_v1.json")
    spec = load_spec(spec_path)
    steps = []

    def run(name: str, command: list[str], expected: int = 0) -> str:
        print(f"[{name}] python {' '.join(command)}", flush=True)
        result = subprocess.run([sys.executable, "-B", *command], capture_output=True,
                                text=True, encoding="utf-8", env={**os.environ, "PYTHONUTF8": "1"})
        print(result.stdout, end="", flush=True)
        if result.stderr:
            print(result.stderr, end="", file=sys.stderr, flush=True)
        steps.append({"name": name, "command": ["python", *command], "expected_exit": expected,
                      "exit_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr})
        if result.returncode != expected:
            raise RuntimeError(f"{name}: expected exit {expected}, got {result.returncode}")
        return result.stdout

    run("smoke", ["-m", "lab9.smoke"])
    run("core_tests", ["-m", "pytest", "-q", "-m", "student", "-o", "addopts=", "-k", "lab9 and not advanced"])
    run("eval_set", ["-m", "lab9.evalset", "--check"])
    if args.build_baseline:
        run("baseline", ["-m", "lab9.eval", "--shape", "swarm", "--spec", str(spec_path), "--out", str(baseline_path)])
    if not baseline_path.is_file():
        raise RuntimeError("baseline missing; run again with --build-baseline")

    def read_report(path: Path, shape: str) -> dict:
        report = json.loads(path.read_text(encoding="utf-8"))
        manifest = report["manifest"]
        expected_metrics = {m["id"] for m in spec["metrics"] if m["id"] in GRADERS}
        if (report["shape"] != shape or manifest["eval_set_sha"] != sha12(Path(spec["eval_set"]))
                or manifest["seeds"] != spec["seeds"]
                or manifest["metric_spec_version"] != spec["metric_spec_version"]
                or len(report["rows"]) != manifest["items"] * len(spec["seeds"])
                or report["evaluator_failures"] or not expected_metrics <= report["metrics"].keys()):
            raise RuntimeError(f"report manifest does not match current Core spec: {path}")
        return report

    base = read_report(baseline_path, "swarm")
    run("eval_pr", ["-m", "lab9.eval", "--shape", "swarm", "--spec", str(spec_path), "--out", "reports/eval_pr.json"])
    cases = {}
    for shape, path, expected in (("swarm", "reports/eval_pr.json", 0),
                                  ("fixed", "reports/eval_fixed.json", 0),
                                  ("seeded_regression", "reports/eval_seeded_regression.json", 1)):
        if shape != "swarm" and not args.reuse_candidates:
            run(f"eval_{shape}", ["-m", "lab9.eval", "--shape", shape, "--spec", str(spec_path), "--out", path])
        report = read_report(Path(path), shape)
        output = run(f"gate_{shape}", ["-m", "lab9.gate", "--pr", path,
                                      "--baseline", str(baseline_path), "--spec", str(spec_path)], expected)
        if shape == "seeded_regression" and not re.search(r"^exit 1 — blocked: (?:[^,]+, )*pass_rate(?:, |$)", output, re.M):
            raise RuntimeError("seeded_regression must explicitly block on pass_rate, not fail by exception")
        if shape == "swarm":
            run("ci_check", ["-m", "lab9.ci_check", "--pr", path,
                             "--baseline", str(baseline_path), "--spec", str(spec_path)])
        cis = {}
        for metric in spec["metrics"]:
            if metric.get("threshold", {}).get("no_significant_drop"):
                a, b = per_item(report, metric["id"]), per_item(base, metric["id"])
                if set(a) != set(b):
                    raise RuntimeError("paired item ids do not match")
                keys = sorted(a)
                delta, low, high = paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                    n_resamples=spec["bootstrap"]["n_resamples"], rng=spec["bootstrap"]["rng"],
                    confidence=spec["bootstrap"]["confidence"])
                cis[metric["id"]] = {"delta": delta, "low": low, "high": high}
        cases[shape] = {"path": path, "run_id": report["run_id"], "gate_exit": expected,
                        "metrics": report["metrics"], "paired_ci": cis}

    reference = cases["seeded_regression"]["paired_ci"]["pass_rate"]
    if any(abs(reference[k] - v) > 0.01 for k, v in {"delta": -0.271, "low": -0.500, "high": -0.057}.items()):
        raise RuntimeError(f"bootstrap differs from the public M4 reference: {reference}")
    harness = yaml.safe_load(Path("harness_map.yaml").read_text(encoding="utf-8"))
    if harness["harness_map_version"] != "1.2" or harness["sections"]["eval"]["baseline"] != str(baseline_path).replace("\\", "/"):
        raise RuntimeError("missing harness eval registration")
    head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    dirty = bool(subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=True).stdout.strip())
    sources = sorted([*Path("lab8").rglob("*.py"), *Path("lab9").rglob("*.py"), spec_path,
                      Path("harness_map.yaml"), Path(spec["eval_set"]), Path(spec["labels"]),
                      Path("config/autonomy_policy.yaml"), Path("config/pricing.yaml"),
                      Path("config/tools.manifest.v1.1.yaml"),
                      Path("data/public_world_state.json"), Path("data/public_claims.jsonl")])
    fingerprint = hashlib.sha256()
    for path in sources:
        fingerprint.update(path.as_posix().encode() + b"\0" + hashlib.sha256(path.read_bytes()).digest())
    summary = {"passed": True, "scope": "local replay of Core CI; not a GitHub Actions run",
               "git_head": head, "working_tree_dirty": dirty, "source_sha256": fingerprint.hexdigest(),
               "eval_set_sha": base["manifest"]["eval_set_sha"], "metric_spec_version": spec["metric_spec_version"],
               "metric_spec_sha": sha12(spec_path), "labels_sha": sha12(Path(spec["labels"])),
               "bootstrap": spec["bootstrap"], "baseline_run_id": base["run_id"],
               "baseline_metrics": base["metrics"], "cases": cases, "steps": steps}
    out = Path("reports/m4_validation.json")
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    print(f"M4 LOCAL PASS; wrote {out}; pass_rate delta/CI = {reference}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
