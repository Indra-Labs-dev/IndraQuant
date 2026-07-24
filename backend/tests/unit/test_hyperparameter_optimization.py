from src.modules.hyperparameter_optimization.application.dispatch import run_search
from src.modules.hyperparameter_optimization.domain.search_space import ParamSpec
from src.modules.hyperparameter_optimization.infrastructure.hyperopt_search import (
    optimize_with_hyperopt,
)
from src.modules.hyperparameter_optimization.infrastructure.optuna_search import (
    optimize_with_optuna,
)
from src.shared.kernel.errors import AppError

_SPECS = [ParamSpec("x", "int", 0, 20)]


def _negative_parabola(params: dict) -> float:
    # Maximized at x=13 (value 0); any other x scores lower.
    return -((params["x"] - 13) ** 2)


def test_optuna_grid_finds_optimum():
    # Grid search only visits its fixed grid points — with a coarse grid
    # over [0, 20] the true optimum (x=13) may not be an exact grid point,
    # so the best reachable value should still land close to it.
    result = optimize_with_optuna(_SPECS, _negative_parabola, "grid", n_trials=21, seed=1)
    assert abs(result.best_params["x"] - 13) <= 3


def test_optuna_random_finds_reasonable_optimum():
    result = optimize_with_optuna(_SPECS, _negative_parabola, "random", n_trials=50, seed=1)
    assert abs(result.best_params["x"] - 13) <= 2


def test_optuna_bayesian_finds_reasonable_optimum():
    result = optimize_with_optuna(_SPECS, _negative_parabola, "bayesian", n_trials=40, seed=1)
    assert abs(result.best_params["x"] - 13) <= 2


def test_optuna_reports_all_trials():
    result = optimize_with_optuna(_SPECS, _negative_parabola, "random", n_trials=15, seed=2)
    assert len(result.trials) == 15


def test_hyperopt_finds_reasonable_optimum():
    result = optimize_with_hyperopt(_SPECS, _negative_parabola, n_trials=40, seed=1)
    assert abs(result.best_params["x"] - 13) <= 2
    assert result.method == "hyperopt:bayesian_tpe"


def test_dispatch_routes_to_optuna_grid():
    result = run_search("grid", _SPECS, _negative_parabola, n_trials=21)
    assert result.method == "optuna:grid"
    assert abs(result.best_params["x"] - 13) <= 3


def test_dispatch_routes_to_hyperopt():
    result = run_search("bayesian_hyperopt", _SPECS, _negative_parabola, n_trials=30)
    assert result.method == "hyperopt:bayesian_tpe"


def test_dispatch_rejects_unknown_method():
    try:
        run_search("nonsense", _SPECS, _negative_parabola, n_trials=10)
        assert False, "expected AppError"
    except AppError as error:
        assert error.code == "unknown_method"
