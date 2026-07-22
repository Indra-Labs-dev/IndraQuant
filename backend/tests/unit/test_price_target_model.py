import random

from src.modules.machine_learning.infrastructure.price_target_model import (
    PriceTargetModel,
)


def make_dataset(n: int, noise: float, seed: int) -> tuple[list[list[float]], list[float]]:
    rng = random.Random(seed)
    rows: list[list[float]] = []
    returns: list[float] = []
    for _ in range(n):
        x = rng.uniform(-1.0, 1.0)
        rows.append([x, 0.0])
        # A clear, learnable linear relationship plus noise.
        returns.append(0.01 * x + rng.uniform(-noise, noise))
    return rows, returns


def test_expected_return_tracks_the_learnable_signal():
    rows, returns = make_dataset(400, noise=0.001, seed=1)
    model = PriceTargetModel()

    result = model.train_predict(rows, returns, latest_row=[1.0, 0.0])

    # latest_row has x=1.0, so the true signal is ~0.01 — the low-noise
    # regressor should land reasonably close to it.
    assert 0.0 < result.expected_return < 0.02


def test_interval_contains_expected_return():
    rows, returns = make_dataset(400, noise=0.02, seed=2)
    model = PriceTargetModel()

    result = model.train_predict(rows, returns, latest_row=[0.5, 0.0])

    assert result.low_return <= result.expected_return <= result.high_return
    assert result.confidence == 0.80


def test_wider_noise_yields_wider_interval():
    rows_low, returns_low = make_dataset(400, noise=0.001, seed=3)
    rows_high, returns_high = make_dataset(400, noise=0.05, seed=3)
    model = PriceTargetModel()

    low_noise = model.train_predict(rows_low, returns_low, latest_row=[0.3, 0.0])
    high_noise = model.train_predict(rows_high, returns_high, latest_row=[0.3, 0.0])

    low_width = low_noise.high_return - low_noise.low_return
    high_width = high_noise.high_return - high_noise.low_return
    assert high_width > low_width


def test_small_dataset_falls_back_to_symmetric_mae_band():
    rows, returns = make_dataset(20, noise=0.01, seed=4)
    model = PriceTargetModel()

    result = model.train_predict(rows, returns, latest_row=[0.0, 0.0])

    width_low = result.expected_return - result.low_return
    width_high = result.high_return - result.expected_return
    assert abs(width_low - width_high) < 1e-9
