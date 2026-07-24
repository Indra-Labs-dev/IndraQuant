from src.modules.validation.domain.cross_validation import (
    nested_cv_splits,
    purged_embargo_splits,
    time_series_splits,
)


def test_time_series_splits_are_causal():
    folds = time_series_splits(120, n_splits=5)
    assert len(folds) == 5
    for fold in folds:
        assert max(fold.train_indices) < min(fold.test_indices)


def test_time_series_splits_expand_training_window():
    folds = time_series_splits(120, n_splits=5)
    sizes = [len(f.train_indices) for f in folds]
    assert sizes == sorted(sizes)  # strictly non-decreasing


def test_time_series_splits_empty_with_too_little_data():
    assert time_series_splits(3, n_splits=5) == []


def test_purged_embargo_splits_purge_around_test_fold():
    folds = purged_embargo_splits(100, n_splits=5, embargo_frac=0.05, label_horizon=2)
    assert len(folds) == 5
    for fold in folds:
        test_set = set(fold.test_indices)
        train_set = set(fold.train_indices)
        # No overlap between train and test.
        assert train_set.isdisjoint(test_set)
        # Nothing immediately after the test fold within the embargo should
        # appear in training.
        embargo_zone = range(max(fold.test_indices) + 1, max(fold.test_indices) + 5)
        assert not any(i in train_set for i in embargo_zone if i < 100 and i in embargo_zone)


def test_purged_embargo_splits_empty_with_too_few_splits():
    assert purged_embargo_splits(5, n_splits=5) == []


def test_nested_cv_splits_outer_test_never_in_inner_folds():
    nested = nested_cv_splits(150, outer_splits=3, inner_splits=3)
    assert len(nested) == 3
    for fold in nested:
        outer_test_set = set(fold.outer_test)
        for inner in fold.inner_folds:
            assert outer_test_set.isdisjoint(inner.train_indices)
            assert outer_test_set.isdisjoint(inner.test_indices)
            # Inner folds must stay within the outer training segment.
            assert set(inner.train_indices) <= set(fold.outer_train)
            assert set(inner.test_indices) <= set(fold.outer_train)


def test_nested_cv_splits_inner_folds_are_causal():
    nested = nested_cv_splits(150, outer_splits=2, inner_splits=3)
    for fold in nested:
        for inner in fold.inner_folds:
            assert max(inner.train_indices) < min(inner.test_indices)
