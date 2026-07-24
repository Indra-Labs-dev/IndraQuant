"""Optuna-backed search (docs/roadmap #8). Optuna's own samplers cover
three of the five named techniques from a single engine: `GridSampler`
(Grid Search), `RandomSampler` (Random Search) and `TPESampler` (a
Bayesian/Tree-structured Parzen Estimator optimizer — Bayesian
Optimization)."""

from collections.abc import Callable
from typing import Literal

from src.modules.hyperparameter_optimization.domain.search_space import (
    HpoResult,
    HpoTrial,
    ParamSpec,
)

OptunaMethod = Literal["grid", "random", "bayesian"]


def _grid_values(spec: ParamSpec, points: int = 6) -> list:
    if spec.kind == "int":
        step = int(spec.step) if spec.step else max(1, int((spec.high - spec.low) // points) or 1)
        return list(range(int(spec.low), int(spec.high) + 1, step))
    step = (spec.high - spec.low) / max(points - 1, 1)
    return [round(spec.low + i * step, 6) for i in range(points)]


def optimize_with_optuna(
    param_specs: list[ParamSpec],
    objective_fn: Callable[[dict], float],
    method: OptunaMethod,
    n_trials: int = 30,
    seed: int = 42,
) -> HpoResult:
    import optuna

    optuna.logging.set_verbosity(optuna.logging.WARNING)

    def suggest(trial: "optuna.Trial") -> dict:
        params = {}
        for spec in param_specs:
            if spec.kind == "int":
                params[spec.name] = trial.suggest_int(
                    spec.name, int(spec.low), int(spec.high), step=int(spec.step or 1)
                )
            else:
                params[spec.name] = trial.suggest_float(spec.name, spec.low, spec.high)
        return params

    def objective(trial: "optuna.Trial") -> float:
        return objective_fn(suggest(trial))

    if method == "grid":
        search_space = {spec.name: _grid_values(spec) for spec in param_specs}
        sampler = optuna.samplers.GridSampler(search_space)
        total_combinations = 1
        for values in search_space.values():
            total_combinations *= len(values)
        n_trials = min(n_trials, total_combinations)
    elif method == "random":
        sampler = optuna.samplers.RandomSampler(seed=seed)
    else:
        sampler = optuna.samplers.TPESampler(seed=seed)

    study = optuna.create_study(direction="maximize", sampler=sampler)
    study.optimize(objective, n_trials=n_trials, catch=(Exception,))

    trials = [
        HpoTrial(trial=t.number, params=dict(t.params), value=t.value)
        for t in study.trials
    ]
    completed = [t for t in study.trials if t.value is not None]
    best = max(completed, key=lambda t: t.value) if completed else None

    return HpoResult(
        method=f"optuna:{method}",
        best_params=dict(best.params) if best else {},
        best_value=best.value if best else None,
        trials=trials,
    )
