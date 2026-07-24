"""Minimal XGBoost fit-and-score used only for cross-validation fold
scoring (docs/roadmap #7) — same hyperparameters as the XGBoost member of
`machine_learning.infrastructure.direction_model.DirectionModel`, but
without the logistic-regression ensemble or SHAP attribution, since
cross-validation needs many fast fold fits, not a single explained
prediction."""

import numpy as np


def train_and_score(
    X_train: list[list[float]],
    y_train: list[int],
    X_test: list[list[float]],
    y_test: list[int],
) -> float | None:
    if len(X_train) < 2 or not X_test or len(set(y_train)) < 2:
        return None

    from xgboost import XGBClassifier

    model = XGBClassifier(
        n_estimators=200,
        max_depth=3,
        learning_rate=0.05,
        subsample=0.9,
        colsample_bytree=0.9,
        eval_metric="logloss",
        random_state=42,
        n_jobs=-1,
    )
    model.fit(np.asarray(X_train, dtype=np.float64), np.asarray(y_train, dtype=np.int32))
    predictions = model.predict(np.asarray(X_test, dtype=np.float64))
    return float((predictions == np.asarray(y_test, dtype=np.int32)).mean())
