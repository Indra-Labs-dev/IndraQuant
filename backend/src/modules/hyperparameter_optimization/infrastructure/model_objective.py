"""XGBoost objective for hyperparameter optimization (docs/roadmap #8):
scores a candidate hyperparameter set by its mean accuracy across the same
Time Series CV folds used by the Validation module (docs/roadmap #7) —
reused here rather than duplicated, so both features stay consistent
about what "cross-validated accuracy" means.
"""

import numpy as np

from src.modules.validation.domain.cross_validation import time_series_splits

_CV_SPLITS = 4


def cross_validated_accuracy(
    rows: list[list[float]],
    labels: list[int],
    n_estimators: int,
    max_depth: int,
    learning_rate: float,
) -> float:
    from xgboost import XGBClassifier

    folds = time_series_splits(len(rows), n_splits=_CV_SPLITS)
    if not folds:
        return -1.0

    accuracies = []
    for fold in folds:
        X_train = np.asarray([rows[i] for i in fold.train_indices], dtype=np.float64)
        y_train = np.asarray([labels[i] for i in fold.train_indices], dtype=np.int32)
        X_test = np.asarray([rows[i] for i in fold.test_indices], dtype=np.float64)
        y_test = np.asarray([labels[i] for i in fold.test_indices], dtype=np.int32)
        if len(set(y_train.tolist())) < 2:
            continue

        model = XGBClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            learning_rate=learning_rate,
            subsample=0.9,
            colsample_bytree=0.9,
            eval_metric="logloss",
            random_state=42,
            n_jobs=-1,
        )
        model.fit(X_train, y_train)
        accuracies.append(float((model.predict(X_test) == y_test).mean()))

    return sum(accuracies) / len(accuracies) if accuracies else -1.0
