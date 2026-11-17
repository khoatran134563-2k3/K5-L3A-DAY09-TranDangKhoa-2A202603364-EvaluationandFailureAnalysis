"""Statistics students implement (M2 judge calibration, M4 paired bootstrap).

Rules: a judge is a classifier -- measure it like one. A higher mean is not
"better" until the paired CI of the difference excludes 0.
Reference values to self-check are in tests/test_lab9_stats.py.
"""

from __future__ import annotations

from collections.abc import Sequence

POS = "FAIL"   # the judge's job is to FIND failures, so FAIL is the positive class


def confusion(human: Sequence[str], judge: Sequence[str]) -> dict[str, int]:
    """Count predictions with FAIL as the positive class."""
    if len(human) != len(judge):
        raise ValueError("human and judge must have the same length")

    counts = {"tp": 0, "fp": 0, "fn": 0, "tn": 0}

    for actual, predicted in zip(human, judge):
        if actual not in {"PASS", "FAIL"} or predicted not in {"PASS", "FAIL"}:
            raise ValueError("labels must be PASS or FAIL")

        if actual == POS:
            key = "tp" if predicted == POS else "fn"
        else:
            key = "fp" if predicted == POS else "tn"
        counts[key] += 1

    return counts


def precision_recall(
    human: Sequence[str], judge: Sequence[str]
) -> tuple[float, float]:
    cm = confusion(human, judge)

    predicted_fail = cm["tp"] + cm["fp"]
    actual_fail = cm["tp"] + cm["fn"]

    precision = cm["tp"] / predicted_fail if predicted_fail else 0.0
    recall = cm["tp"] / actual_fail if actual_fail else 0.0
    return precision, recall


def cohen_kappa(human: Sequence[str], judge: Sequence[str]) -> float:
    cm = confusion(human, judge)
    n = sum(cm.values())
    if n == 0:
        raise ValueError("kappa is undefined for empty labels")

    observed_agreement = (cm["tp"] + cm["tn"]) / n

    human_fail = (cm["tp"] + cm["fn"]) / n
    judge_fail = (cm["tp"] + cm["fp"]) / n
    expected_agreement = (
        human_fail * judge_fail
        + (1 - human_fail) * (1 - judge_fail)
    )

    if expected_agreement == 1.0:
        raise ValueError("kappa is undefined when expected agreement is 1")

    return (
        (observed_agreement - expected_agreement)
        / (1 - expected_agreement)
    )


def rogan_gladen(
    observed_rate: float,
    sensitivity: float,
    specificity: float,
) -> float:
    """Correct observed failure prevalence and clip to [0, 1]."""
    for value in (observed_rate, sensitivity, specificity):
        if not 0.0 <= value <= 1.0:
            raise ValueError("rates must lie in [0, 1]")

    denominator = sensitivity + specificity - 1
    if denominator <= 0:
        raise ValueError(
            "judge must have sensitivity + specificity greater than 1"
        )

    corrected = (observed_rate + specificity - 1) / denominator
    return max(0.0, min(1.0, corrected))


def paired_bootstrap(
    a: Sequence[float],
    b: Sequence[float],
    *,
    n_resamples: int = 1000,
    rng: int = 2027,
    confidence: float = 0.95,
) -> tuple[float, float, float]:
    import numpy as np
    from scipy.stats import bootstrap

    left = np.asarray(a, dtype=float)
    right = np.asarray(b, dtype=float)

    if left.ndim != 1 or right.ndim != 1:
        raise ValueError("inputs must be one-dimensional")
    if left.size == 0 or left.size != right.size:
        raise ValueError("inputs must be nonempty and have equal lengths")
    if not np.isfinite(left).all() or not np.isfinite(right).all():
        raise ValueError("inputs must contain only finite values")
    if n_resamples <= 0 or not 0 < confidence < 1:
        raise ValueError("invalid bootstrap settings")

    difference = float(np.mean(left - right))

    if np.array_equal(left, right):
        return 0.0, 0.0, 0.0

    if left.size < 2:
        raise ValueError("bootstrap needs at least two paired items")

    def mean_difference(x, y, axis=-1):
        return np.mean(x - y, axis=axis)

    result = bootstrap(
        (left, right),
        mean_difference,
        paired=True,
        vectorized=True,
        n_resamples=n_resamples,
        confidence_level=confidence,
        method="percentile",
        rng=np.random.default_rng(rng),
    )

    return (
        difference,
        float(result.confidence_interval.low),
        float(result.confidence_interval.high),
    )


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
