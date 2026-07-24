"""Resampling-based statistical validation for backtests (docs/roadmap
#7): Bootstrap confidence intervals, a Monte Carlo permutation test on
strategy timing, and White's (2000) Reality Check for data-snooping bias
across multiple strategy variants. Pure stdlib (`random`) — no numpy, same
convention as the rest of the domain layer.
"""

import random
from dataclasses import dataclass

_DEFAULT_ITERATIONS = 1000
_MIN_SAMPLES = 20


@dataclass(frozen=True)
class BootstrapResult:
    mean: float
    ci_low: float
    ci_high: float
    confidence: float
    explanation: str


def bootstrap_confidence_interval(
    values: list[float],
    n_iterations: int = _DEFAULT_ITERATIONS,
    confidence: float = 0.95,
    seed: int = 42,
) -> BootstrapResult:
    """Standard (non-parametric) bootstrap: resamples `values` with
    replacement `n_iterations` times, reporting the confidence interval of
    the resampled means — an interval that excludes zero means the
    observed average return is unlikely to be pure noise."""
    if len(values) < _MIN_SAMPLES:
        return BootstrapResult(
            0.0, 0.0, 0.0, confidence, "Historique insuffisant pour un bootstrap fiable."
        )

    rng = random.Random(seed)
    n = len(values)
    means = []
    for _ in range(n_iterations):
        means.append(sum(values[rng.randrange(n)] for _ in range(n)) / n)
    means.sort()

    lower_idx = int((1.0 - confidence) / 2.0 * n_iterations)
    upper_idx = min(int((1.0 - (1.0 - confidence) / 2.0) * n_iterations), n_iterations - 1)
    observed_mean = sum(values) / n
    ci_low, ci_high = means[lower_idx], means[upper_idx]

    return BootstrapResult(
        round(observed_mean, 6),
        round(ci_low, 6),
        round(ci_high, 6),
        confidence,
        f"Intervalle de confiance à {confidence * 100:.0f} % sur le rendement moyen "
        f"par période, par ré-échantillonnage bootstrap ({n_iterations} tirages) : "
        f"[{ci_low * 100:.3f} %, {ci_high * 100:.3f} %]. "
        + (
            "L'intervalle exclut zéro — le résultat est statistiquement distinguable du hasard."
            if ci_low > 0 or ci_high < 0
            else "L'intervalle inclut zéro — impossible d'exclure que le résultat soit dû au hasard."
        ),
    )


@dataclass(frozen=True)
class MonteCarloResult:
    observed_return: float
    p_value: float
    null_mean: float
    null_std: float
    explanation: str


def monte_carlo_permutation_test(
    market_returns: list[float],
    positions: list[int],
    n_iterations: int = _DEFAULT_ITERATIONS,
    seed: int = 42,
) -> MonteCarloResult:
    """Monte Carlo permutation test on strategy *timing*: shuffles WHEN the
    strategy was in/out of the market (the position mask) while keeping
    the real, unshuffled market returns — then compares the strategy's
    actual compounded return to the distribution obtained from random
    timing. (Shuffling a fixed set of already-realized returns would be
    pointless: compounding is a product, and a product's value does not
    depend on multiplication order — this must shuffle *positions*, not
    returns.)"""
    n = min(len(market_returns), len(positions))
    if n < _MIN_SAMPLES:
        return MonteCarloResult(
            0.0, 1.0, 0.0, 0.0, "Historique insuffisant pour un test de permutation fiable."
        )
    market_returns = market_returns[-n:]
    positions = positions[-n:]

    def compounded(pos_sequence: list[int]) -> float:
        total = 1.0
        for pos, r in zip(pos_sequence, market_returns):
            total *= 1.0 + pos * r
        return total - 1.0

    observed = compounded(positions)
    rng = random.Random(seed)
    shuffled = list(positions)
    null_stats = []
    for _ in range(n_iterations):
        rng.shuffle(shuffled)
        null_stats.append(compounded(shuffled))

    p_value = sum(1 for s in null_stats if s >= observed) / n_iterations
    null_mean = sum(null_stats) / len(null_stats)
    null_variance = sum((s - null_mean) ** 2 for s in null_stats) / len(null_stats)

    return MonteCarloResult(
        round(observed, 6),
        round(p_value, 4),
        round(null_mean, 6),
        round(null_variance**0.5, 6),
        f"Test de permutation Monte Carlo ({n_iterations} tirages) : rendement "
        f"composé observé {observed * 100:.2f} % vs {null_mean * 100:.2f} % en "
        f"moyenne pour un positionnement aléatoire sur les mêmes rendements de "
        f"marché — p-value {p_value:.3f}. "
        + (
            "Le résultat n'est pas qu'un effet d'ordre — le positionnement de la "
            "stratégie bat significativement le hasard."
            if p_value < 0.05
            else "Impossible d'exclure que la performance ne soit qu'un effet du "
            "hasard sur ce même historique de marché."
        ),
    )


def _stationary_bootstrap_indices(
    n: int, rng: random.Random, avg_block_length: float = 8.0
) -> list[int]:
    """Politis-Romano stationary bootstrap: resamples blocks of random
    (geometrically-distributed) length starting at random points, wrapping
    around — preserves short-term serial correlation instead of treating
    every observation as independent."""
    continue_prob = 1.0 - 1.0 / avg_block_length
    indices: list[int] = []
    while len(indices) < n:
        pos = rng.randrange(n)
        indices.append(pos)
        while len(indices) < n and rng.random() < continue_prob:
            pos = (pos + 1) % n
            indices.append(pos)
    return indices[:n]


@dataclass(frozen=True)
class WhiteRealityCheckResult:
    best_candidate_index: int
    best_mean_return: float
    p_value: float
    n_candidates: int
    explanation: str


def white_reality_check(
    candidate_returns: list[list[float]],
    n_iterations: int = _DEFAULT_ITERATIONS,
    seed: int = 42,
) -> WhiteRealityCheckResult:
    """White's (2000) Reality Check for data-snooping bias: when several
    strategy variants were tried and the best one is reported, its edge
    must be judged against the "best-of-many" null distribution, not in
    isolation. Uses a stationary block bootstrap resampling all candidates
    on the *same* time indices each draw (preserving their cross-
    correlation), recentring each candidate's bootstrap mean by its own
    observed mean — the standard White construction of the null "no
    candidate has genuine skill"."""
    if not candidate_returns or any(len(c) < _MIN_SAMPLES for c in candidate_returns):
        return WhiteRealityCheckResult(
            0,
            0.0,
            1.0,
            len(candidate_returns),
            "Historique insuffisant pour un Reality Check fiable.",
        )

    n = min(len(c) for c in candidate_returns)
    candidates = [c[-n:] for c in candidate_returns]
    means = [sum(c) / n for c in candidates]
    best_index = max(range(len(means)), key=lambda i: means[i])
    observed_best = means[best_index]

    rng = random.Random(seed)
    exceed_count = 0
    for _ in range(n_iterations):
        idx = _stationary_bootstrap_indices(n, rng)
        boot_stat = max(
            (sum(candidate[i] for i in idx) / n) - means[k]
            for k, candidate in enumerate(candidates)
        )
        if boot_stat >= observed_best:
            exceed_count += 1
    p_value = exceed_count / n_iterations

    return WhiteRealityCheckResult(
        best_index,
        round(observed_best, 6),
        round(p_value, 4),
        len(candidates),
        f"Sur {len(candidates)} variante(s) de stratégie testée(s), la "
        f"meilleure (indice {best_index}) affiche un rendement moyen par "
        f"période de {observed_best * 100:.3f} %. Reality Check de White "
        f"({n_iterations} tirages bootstrap stationnaire) : p-value {p_value:.3f} — "
        + (
            "l'avantage résiste à la correction pour tests multiples, il est "
            "probablement réel."
            if p_value < 0.05
            else "l'avantage pourrait n'être que le fruit du hasard d'avoir "
            "testé plusieurs variantes (biais de data-snooping)."
        ),
    )
