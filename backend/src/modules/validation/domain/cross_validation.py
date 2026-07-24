"""Cross-validation splitting strategies for time-series/financial ML
(docs/roadmap #7). All splits are causal — training indices never include
information from after the test indices — because shuffling would leak
future information into training, the cardinal sin of financial ML.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Fold:
    train_indices: list[int]
    test_indices: list[int]


@dataclass(frozen=True)
class NestedFold:
    outer_train: list[int]
    outer_test: list[int]
    inner_folds: list[Fold]


def time_series_splits(
    n: int, n_splits: int = 5, min_train_size: int | None = None
) -> list[Fold]:
    """Expanding-window time series CV: fold i trains on everything before
    it and tests on the next chronological block."""
    if n_splits < 2 or n < n_splits + 1:
        return []
    fold_size = n // (n_splits + 1)
    if fold_size < 1:
        return []
    min_train = min_train_size or fold_size

    folds: list[Fold] = []
    for i in range(n_splits):
        train_end = min_train + i * fold_size
        test_start = train_end
        test_end = min(test_start + fold_size, n)
        if test_end <= test_start or train_end < 1:
            continue
        folds.append(Fold(list(range(0, train_end)), list(range(test_start, test_end))))
    return folds


def purged_embargo_splits(
    n: int,
    n_splits: int = 5,
    embargo_frac: float = 0.02,
    label_horizon: int = 1,
) -> list[Fold]:
    """Purged K-Fold CV with embargo (López de Prado, 'Advances in
    Financial Machine Learning'): standard K-Fold, but (1) training samples
    whose label window [t, t+label_horizon) overlaps the test fold are
    purged, and (2) an embargo period placed right after the test fold is
    also excluded from training. Both correct for leakage caused by
    serially-correlated, overlapping labels near fold boundaries — a plain
    K-Fold on financial time series would otherwise train on samples whose
    label secretly depends on the test period."""
    if n_splits < 2 or n < n_splits * 2:
        return []
    fold_size = n // n_splits
    embargo = max(int(n * embargo_frac), 0)

    folds: list[Fold] = []
    for i in range(n_splits):
        test_start = i * fold_size
        test_end = n if i == n_splits - 1 else (i + 1) * fold_size
        test_indices = list(range(test_start, test_end))

        purge_start = max(test_start - label_horizon, 0)
        embargo_end = min(test_end + embargo, n)

        train_indices = [j for j in range(n) if j < purge_start or j >= embargo_end]
        if train_indices and test_indices:
            folds.append(Fold(train_indices, test_indices))
    return folds


def nested_cv_splits(
    n: int, outer_splits: int = 3, inner_splits: int = 3
) -> list[NestedFold]:
    """Nested CV: the outer loop gives an unbiased performance estimate;
    each outer training set is further split (inner loop) for
    hyperparameter selection — this prevents the optimistic bias of tuning
    and evaluating on the very same data."""
    outer = time_series_splits(n, n_splits=outer_splits)
    nested: list[NestedFold] = []
    for fold in outer:
        outer_train = fold.train_indices
        inner_local = time_series_splits(len(outer_train), n_splits=inner_splits)
        inner_global = [
            Fold(
                [outer_train[i] for i in local.train_indices],
                [outer_train[i] for i in local.test_indices],
            )
            for local in inner_local
        ]
        nested.append(NestedFold(outer_train, fold.test_indices, inner_global))
    return nested
