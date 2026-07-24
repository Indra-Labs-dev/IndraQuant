from collections.abc import Callable

from src.modules.hyperparameter_optimization.domain.search_space import (
    HpoResult,
    ParamSpec,
)
from src.modules.hyperparameter_optimization.infrastructure.hyperopt_search import (
    optimize_with_hyperopt,
)
from src.modules.hyperparameter_optimization.infrastructure.optuna_search import (
    optimize_with_optuna,
)
from src.shared.kernel.errors import AppError

_METHODS = ("grid", "random", "bayesian_optuna", "bayesian_hyperopt")


def run_search(
    method: str,
    param_specs: list[ParamSpec],
    objective_fn: Callable[[dict], float],
    n_trials: int,
    seed: int = 42,
) -> HpoResult:
    """Dispatches to the requested optimization engine (docs/roadmap #8):
    'grid' and 'random' and 'bayesian_optuna' all run through Optuna's own
    samplers (GridSampler / RandomSampler / TPESampler); 'bayesian_hyperopt'
    runs through Hyperopt's own TPE implementation — a second, independent
    Bayesian engine, as the roadmap names both libraries explicitly."""
    if method == "bayesian_hyperopt":
        return optimize_with_hyperopt(param_specs, objective_fn, n_trials, seed)
    if method in ("grid", "random", "bayesian_optuna"):
        optuna_method = "bayesian" if method == "bayesian_optuna" else method
        return optimize_with_optuna(param_specs, objective_fn, optuna_method, n_trials, seed)
    raise AppError(
        "unknown_method",
        f"Méthode d'optimisation inconnue : {method}. Valeurs possibles : "
        f"{', '.join(_METHODS)}.",
        422,
    )
