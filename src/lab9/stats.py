"""Statistics students implement (M2 judge calibration, M4 paired bootstrap).

Rules: a judge is a classifier -- measure it like one. A higher mean is not
"better" until the paired CI of the difference excludes 0.
Reference values to self-check are in tests/test_lab9_stats.py.
"""

from __future__ import annotations

from collections.abc import Sequence
import math

POS = "FAIL"   # the judge's job is to FIND failures, so FAIL is the positive class


def confusion(human: Sequence[str], judge: Sequence[str]) -> dict[str, int]:
    """tp/fp/fn/tn with FAIL as positive."""
    if len(human) != len(judge) or not len(human):
        raise ValueError("human and judge must have the same non-zero length")
    counts = dict.fromkeys(("tp", "fp", "fn", "tn"), 0)
    for h, j in zip(human, judge):
        h, j = str(h).strip().upper(), str(j).strip().upper()
        if h not in ("PASS", POS) or j not in ("PASS", POS):
            raise ValueError("labels must be PASS or FAIL")
        key = ("tp" if h == POS else "fp") if j == POS else ("fn" if h == POS else "tn")
        counts[key] += 1
    return counts


def precision_recall(human: Sequence[str], judge: Sequence[str]) -> tuple[float, float]:
    cm = confusion(human, judge)
    predicted = cm["tp"] + cm["fp"]
    actual = cm["tp"] + cm["fn"]
    return (cm["tp"] / predicted if predicted else 0.0,
            cm["tp"] / actual if actual else 0.0)


def cohen_kappa(human: Sequence[str], judge: Sequence[str]) -> float:
    """kappa = (p_o - p_e) / (1 - p_e). Raise ValueError when undefined (p_e == 1):
    a constant judge has no signal and must FAIL calibration, not pass on a technicality."""
    cm = confusion(human, judge)
    n = sum(cm.values())
    expected = ((cm["tp"] + cm["fn"]) * (cm["tp"] + cm["fp"])
                + (cm["tn"] + cm["fp"]) * (cm["tn"] + cm["fn"]))
    denominator = n * n - expected
    if denominator == 0:
        raise ValueError("kappa is undefined when expected agreement is 1")
    return (n * (cm["tp"] + cm["tn"]) - expected) / denominator


def rogan_gladen(observed_rate: float, sensitivity: float, specificity: float) -> float:
    """Correct an observed failure rate for judge error; clip to [0, 1]."""
    if any(not math.isfinite(v) or not 0 <= v <= 1
           for v in (observed_rate, sensitivity, specificity)):
        raise ValueError("rates must be finite and between 0 and 1")
    denominator = sensitivity + specificity - 1
    if math.isclose(denominator, 0.0, abs_tol=1e-12):
        raise ValueError("Rogan-Gladen is undefined when sensitivity + specificity = 1")
    return max(0.0, min(1.0, (observed_rate + specificity - 1) / denominator))


def paired_bootstrap(a: Sequence[float], b: Sequence[float], *, n_resamples: int = 1000,
                     rng: int = 2027, confidence: float = 0.95) -> tuple[float, float, float]:
    """a[i], b[i] = per-item mean over seeds, SAME items, SAME order.
    Return (mean(a)-mean(b), lo, hi) with scipy.stats.bootstrap(paired=True, method="percentile",
    rng=numpy.random.default_rng(rng)). If a == b everywhere return (0.0, 0.0, 0.0)."""
    import numpy as np
    from scipy.stats import bootstrap

    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    if a.ndim != 1 or b.ndim != 1 or a.shape != b.shape or not a.size:
        raise ValueError("paired samples must be non-empty 1-D arrays of equal length")
    if not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError("paired samples must contain only finite values")
    if not isinstance(n_resamples, int) or isinstance(n_resamples, bool) or n_resamples < 1:
        raise ValueError("n_resamples must be a positive integer")
    if not 0 < confidence < 1:
        raise ValueError("confidence must be between 0 and 1")
    if np.array_equal(a, b):
        return 0.0, 0.0, 0.0
    if a.size < 2:
        raise ValueError("bootstrap needs at least two paired items")

    def difference(x, y, axis=-1):
        return np.mean(x, axis=axis) - np.mean(y, axis=axis)

    result = bootstrap((a, b), difference, paired=True, method="percentile",
                       n_resamples=n_resamples, rng=np.random.default_rng(rng),
                       confidence_level=confidence)
    return (float(difference(a, b)), float(result.confidence_interval.low),
            float(result.confidence_interval.high))


def pass_at_k(n: int, c: int, k: int) -> float:
    """Probability that AT LEAST ONE of k trials drawn from n (c of them passing) passes.
    Unbiased estimator (Chen et al. 2021): 1 - C(n-c, k) / C(n, k). Raise ValueError if k > n."""
    # TODO M6
    raise NotImplementedError


def pass_hat_k(n: int, c: int, k: int) -> float:
    """pass^k (tau-bench, Yao et al. 2024): probability that ALL k trials drawn from n pass.
    Unbiased estimator: C(c, k) / C(n, k). Raise ValueError if k > n.
    pass^k <= pass@1 <= pass@k; a reliable agent keeps pass^k close to pass@1."""
    # TODO M6
    raise NotImplementedError
