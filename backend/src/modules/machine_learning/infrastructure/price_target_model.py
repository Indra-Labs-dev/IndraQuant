"""XGBoost regressor estimating the next candle's log-return, with a
prediction interval built from the empirical distribution of the model's own
residuals on held-out data (ADR-025) — never a single number, and grounded
in the model's actually observed error rather than an assumed distribution.
"""

from dataclasses import dataclass

import numpy as np

_CONFIDENCE = 0.80
_MIN_RESIDUALS_FOR_EMPIRICAL_QUANTILES = 10


@dataclass(frozen=True)
class PriceTargetTrainingResult:
    expected_return: float
    low_return: float
    high_return: float
    confidence: float
    test_mae: float


class PriceTargetModel:
    def train_predict(
        self,
        rows: list[list[float]],
        returns: list[float],
        latest_row: list[float],
    ) -> PriceTargetTrainingResult:
        from xgboost import XGBRegressor

        X = np.asarray(rows, dtype=np.float64)
        y = np.asarray(returns, dtype=np.float64)
        latest = np.asarray([latest_row], dtype=np.float64)

        split = int(len(X) * 0.8)
        X_train, X_test = X[:split], X[split:]
        y_train, y_test = y[:split], y[split:]

        model = XGBRegressor(
            n_estimators=200,
            max_depth=3,
            learning_rate=0.05,
            subsample=0.9,
            colsample_bytree=0.9,
            random_state=42,
        )
        model.fit(X_train, y_train)

        residuals = y_test - model.predict(X_test) if len(X_test) else np.array([])
        test_mae = float(np.mean(np.abs(residuals))) if len(residuals) else 0.0
        expected_return = float(model.predict(latest)[0])

        tail = (1.0 - _CONFIDENCE) / 2.0
        if len(residuals) >= _MIN_RESIDUALS_FOR_EMPIRICAL_QUANTILES:
            low_residual = float(np.quantile(residuals, tail))
            high_residual = float(np.quantile(residuals, 1.0 - tail))
        else:
            # Not enough held-out residuals to trust empirical quantiles yet
            # — fall back to a symmetric band from the test MAE.
            low_residual = -test_mae
            high_residual = test_mae

        return PriceTargetTrainingResult(
            expected_return=expected_return,
            low_return=expected_return + low_residual,
            high_return=expected_return + high_residual,
            confidence=_CONFIDENCE,
            test_mae=test_mae,
        )
