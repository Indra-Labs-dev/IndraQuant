"""XGBoost + logistic-regression ensemble for next-candle direction, with
SHAP attribution for the XGBoost member (ADR-017). Infrastructure layer:
this is the only file that knows the ML libraries.
"""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class TrainedPrediction:
    prob_up: float
    model_probs: dict[str, float]
    model_accuracies: dict[str, float]
    test_accuracy: float
    baseline_accuracy: float
    training_rows: int
    shap_contributions: list[float]


class DirectionModel:
    def train_predict(
        self,
        rows: list[list[float]],
        labels: list[int],
        latest_row: list[float],
    ) -> TrainedPrediction:
        from sklearn.linear_model import LogisticRegression
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler
        from xgboost import XGBClassifier
        import shap

        X = np.asarray(rows, dtype=np.float64)
        y = np.asarray(labels, dtype=np.int32)
        latest = np.asarray([latest_row], dtype=np.float64)

        split = int(len(X) * 0.8)
        X_train, X_test = X[:split], X[split:]
        y_train, y_test = y[:split], y[split:]

        xgb = XGBClassifier(
            n_estimators=200,
            max_depth=3,
            learning_rate=0.05,
            subsample=0.9,
            colsample_bytree=0.9,
            eval_metric="logloss",
            random_state=42,
            n_jobs=-1,
        )
        logistic = make_pipeline(
            StandardScaler(), LogisticRegression(max_iter=1000, random_state=42)
        )

        # The two members are independent — fitting them concurrently uses
        # more of the machine's cores instead of training one after the
        # other (ADR-027).
        with ThreadPoolExecutor(max_workers=2) as executor:
            xgb_future = executor.submit(xgb.fit, X_train, y_train)
            logistic_future = executor.submit(logistic.fit, X_train, y_train)
            xgb_future.result()
            logistic_future.result()

        xgb_acc = float((xgb.predict(X_test) == y_test).mean())
        log_acc = float((logistic.predict(X_test) == y_test).mean())

        xgb_prob = float(xgb.predict_proba(latest)[0, 1])
        log_prob = float(logistic.predict_proba(latest)[0, 1])
        prob_up = (xgb_prob + log_prob) / 2.0

        explainer = shap.TreeExplainer(xgb)
        shap_values = explainer.shap_values(latest)
        contributions = np.asarray(shap_values).reshape(-1).tolist()

        baseline = float(max(y_test.mean(), 1.0 - y_test.mean())) if len(y_test) else 0.5
        return TrainedPrediction(
            prob_up=prob_up,
            model_probs={"xgboost": xgb_prob, "logistic_regression": log_prob},
            model_accuracies={"xgboost": xgb_acc, "logistic_regression": log_acc},
            test_accuracy=(xgb_acc + log_acc) / 2.0,
            baseline_accuracy=baseline,
            training_rows=len(X_train),
            shap_contributions=contributions,
        )
