"""Validate report evidence and same-eval-set specification ratchets (M7)."""
from __future__ import annotations

from collections import defaultdict
import math
from numbers import Real
import re

from lab9 import stats
from lab9.graders import GRADERS

_PASS_K = re.compile(r"pass_(at|hat)_(\d+)")
_TOLERANCE = 0.000050000001  # aggregate() rounds ratios to four decimal places


def finite(value) -> bool:
    try:
        return isinstance(value, Real) and math.isfinite(value)
    except (ValueError, OverflowError):
        return False


def _entries(spec: dict, section: str, problems: list[str]) -> dict:
    entries = spec.get(section, [])
    if not isinstance(entries, list):
        problems.append(f"spec {section} must be a list")
        return {}
    result = {}
    for entry in entries:
        if not isinstance(entry, dict):
            problems.append(f"invalid {section} entry")
            continue
        mid = entry.get("id") if section == "metrics" else entry.get("metric")
        name = mid if section == "metrics" else entry.get("name")
        if not isinstance(mid, str) or not mid or not isinstance(name, str) or not name:
            problems.append(f"invalid {section} identifier")
            continue
        key = mid if section == "metrics" else (name, mid)
        if key in result:
            problems.append(f"duplicate spec {section} entry {key}")
        result[key] = entry
        if not isinstance(entry.get("blocking", False), bool):
            problems.append(f"{key}: blocking must be boolean")
        thresholds = entry.get("threshold", {}) if section == "metrics" else entry
        if not isinstance(thresholds, dict):
            problems.append(f"{key}: invalid thresholds")
            continue
        for bound in ("min", "max", "max_increase"):
            if bound in thresholds and (isinstance(thresholds[bound], bool) or not finite(thresholds[bound])):
                problems.append(f"{key}: non-finite or invalid {bound}")
        if not isinstance(thresholds.get("no_significant_drop", False), bool):
            problems.append(f"{key}: no_significant_drop must be boolean")
    return result


def ratchet(spec: dict, base_spec: dict) -> list[str]:
    """A version label alone does not permit weakening a spec on the same eval set."""
    problems = []
    if spec.get("eval_set_version") != base_spec.get("eval_set_version"):
        return problems
    for section in ("metrics", "slices"):
        current = _entries(spec, section, problems)
        previous = _entries(base_spec, section, problems)
        for key, old in previous.items():
            if key not in current:
                problems.append(f"ratchet: removed {section} {key}")
                continue
            new = current[key]
            if old.get("blocking") and not new.get("blocking"):
                problems.append(f"ratchet: disabled blocking {key}")
            if section == "metrics" and old.get("kind") != new.get("kind"):
                problems.append(f"ratchet: changed metric kind {key}")
            old_th = old.get("threshold", {}) if section == "metrics" else old
            new_th = new.get("threshold", {}) if section == "metrics" else new
            if not isinstance(old_th, dict) or not isinstance(new_th, dict):
                continue
            for bound in ("min", "max", "max_increase"):
                if bound not in old_th:
                    continue
                if bound not in new_th:
                    problems.append(f"ratchet: removed {key}/{bound}")
                elif finite(old_th[bound]) and finite(new_th[bound]):
                    weaker = new_th[bound] < old_th[bound] if bound == "min" else new_th[bound] > old_th[bound]
                    if weaker:
                        problems.append(f"ratchet: loosened {key}/{bound}")
            if old_th.get("no_significant_drop") and not new_th.get("no_significant_drop"):
                problems.append(f"ratchet: removed no_significant_drop {key}")
    return problems


def _report(report: dict, label: str, spec: dict, metric_specs: dict) -> tuple[list[str], set, dict]:
    problems, keys, tags_of = [], set(), {}

    def bad(message):
        problems.append(f"{label}: {message}")

    if not isinstance(report, dict):
        return [f"{label}: report must be an object"], keys, tags_of
    manifest, rows, metrics = report.get("manifest"), report.get("rows"), report.get("metrics")
    if not isinstance(manifest, dict) or not isinstance(rows, list) or not isinstance(metrics, dict):
        return [f"{label}: missing/invalid manifest, rows or metrics"], keys, tags_of
    if not isinstance(manifest.get("eval_set_sha"), str) or not manifest["eval_set_sha"]:
        bad("missing eval_set_sha")
    failures = report.get("evaluator_failures")
    if not isinstance(failures, list) or failures:
        bad("missing or non-empty evaluator_failures")
    seeds, items = manifest.get("seeds"), manifest.get("items")
    if (not isinstance(seeds, list) or not seeds
            or any(type(s) is not int for s in seeds) or len(set(seeds)) != len(seeds)):
        return problems + [f"{label}: seeds must be distinct integers"], keys, tags_of
    if type(items) is not int or items < 1:
        return problems + [f"{label}: manifest items must be positive"], keys, tags_of
    if len(rows) != items * len(seeds):
        bad("row count != manifest items x seeds")
    if "seeds" in spec and (len(spec["seeds"]) != len(seeds) or set(spec["seeds"]) != set(seeds)):
        bad("manifest seeds differ from the spec")
    graded = [mid for mid, m in metric_specs.items()
              if mid in GRADERS or (m.get("kind") in ("safety", "capability")
                                    and mid != "pass_5" and not _PASS_K.fullmatch(mid))]
    values = {mid: [] for mid in graded}
    by_item = defaultdict(list)
    item_seeds = defaultdict(set)
    costs = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            bad(f"row {index} is not an object")
            continue
        item, seed = row.get("item_id"), row.get("seed")
        if not isinstance(item, str) or not item or type(seed) is not int:
            bad(f"row {index}: invalid item_id/seed")
            continue
        key = (item, seed)
        if key in keys:
            bad(f"duplicate item/seed {key}")
        keys.add(key)
        item_seeds[item].add(seed)
        if seed not in seeds:
            bad(f"{key}: undeclared seed")
        tags = row.get("slices", [])
        if not isinstance(tags, list) or any(not isinstance(t, str) or not t for t in tags):
            bad(f"{key}: invalid slice tags")
        elif len(set(tags)) != len(tags):
            bad(f"{key}: duplicate slice tags")
        else:
            tags = frozenset(tags)
            if item in tags_of and tags_of[item] != tags:
                bad(f"{item}: slice tags differ across seeds")
            tags_of[item] = tags
        for mid in graded:
            value = row.get(mid)
            if not finite(value) or not 0 <= value <= 1:
                bad(f"{key}: missing/non-finite/out-of-range graded value {mid}")
            else:
                values[mid].append(value)
        if finite(row.get("pass_rate")) and 0 <= row["pass_rate"] <= 1:
            by_item[item].append(bool(row["pass_rate"]))
        if "cost" in row:
            if not finite(row["cost"]) or row["cost"] < 0:
                bad(f"{key}: invalid cost")
            else:
                costs.append(row["cost"])
    if len(item_seeds) != items:
        bad("distinct item count differs from manifest")
    if any(ss != set(seeds) for ss in item_seeds.values()):
        bad("an item does not cover every manifest seed")
    for mid in metric_specs:
        if mid not in metrics:
            bad(f"summary metric missing: {mid}")
    for mid, value in metrics.items():
        if value is None and mid == "cost_per_success":
            continue  # undefined if there are no successes; checked below when costs are present
        if not finite(value):
            bad(f"non-finite/invalid summary metric {mid}")
    computed = {}
    for mid, vals in values.items():
        if len(vals) == len(rows) and vals:
            computed[mid] = sum(vals) if metric_specs[mid].get("kind") == "safety" else round(sum(vals) / len(vals), 4)
    if by_item and sum(map(len, by_item.values())) == len(rows):
        computed["pass_5"] = round(sum(all(v) for v in by_item.values()) / len(by_item), 4)
        for mid in metrics:
            match = _PASS_K.fullmatch(mid)
            if match:
                k = int(match[2])
                fn = stats.pass_at_k if match[1] == "at" else stats.pass_hat_k
                try:
                    computed[mid] = round(sum(fn(len(v), sum(v), k) for v in by_item.values()) / len(by_item), 4)
                except ValueError:
                    bad(f"undefined {mid}: insufficient runs")
        if costs:
            if len(costs) != len(rows):
                bad("cost missing on some rows")
            else:
                passes = sum(sum(v) for v in by_item.values())
                computed["cost_per_success"] = round(sum(costs) / passes, 4) if passes else None
    for mid, expected in computed.items():
        if mid not in metrics:
            continue
        actual = metrics[mid]
        if expected is None:
            if actual is not None:
                bad(f"summary {mid} disagrees with rows")
        elif not finite(actual) or not math.isclose(actual, expected, rel_tol=0, abs_tol=_TOLERANCE):
            bad(f"summary {mid} disagrees with rows")
    return problems, keys, tags_of


def audit_reports(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> list[str]:
    if not isinstance(spec, dict) or (base_spec is not None and not isinstance(base_spec, dict)):
        return ["spec must be an object"]
    problems = []
    metrics = _entries(spec, "metrics", problems)
    slices = _entries(spec, "slices", problems)
    for name, mid in slices:
        if mid not in metrics:
            problems.append(f"slice {name}: unknown metric {mid}")
    for candidate in (spec, base_spec):
        if candidate is None:
            continue
        if "seeds" in candidate:
            seeds = candidate["seeds"]
            if (not isinstance(seeds, list) or not seeds or any(type(s) is not int for s in seeds)
                    or len(set(seeds)) != len(seeds)):
                problems.append("spec seeds must be distinct integers")
    if not metrics:
        problems.append("spec has no metrics")
    if base_spec is not None:
        problems += ratchet(spec, base_spec)
    if problems:
        return problems
    pp, pk, pt = _report(pr, "PR", spec, metrics)
    # When a spec adds metrics, the baseline must be re-run with those graders too.
    bp, bk, bt = _report(base, "baseline", base_spec or spec, metrics)
    problems += pp + bp
    if pk != bk:
        problems.append("PR (item_id, seed) set differs from baseline")
    if pt != bt:
        problems.append("PR item slice tags differ from baseline")
    return problems
