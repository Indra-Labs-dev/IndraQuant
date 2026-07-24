"""Hyperopt-backed Bayesian search (docs/roadmap #8) — a second, distinct
Tree-structured Parzen Estimator implementation from Optuna's, offered as
an alternative engine since the roadmap names both libraries explicitly.
"""

from collections.abc import Callable

from src.modules.hyperparameter_optimization.domain.search_space import (
    HpoResult,
    HpoTrial,
    ParamSpec,
)


def optimize_with_hyperopt(
    param_specs: list[ParamSpec],
    objective_fn: Callable[[dict], float],
    n_trials: int = 30,
    seed: int = 42,
) -> HpoResult:
    from hyperopt import Trials, fmin, hp, tpe

    space = {}
    for spec in param_specs:
        if spec.kind == "int":
            space[spec.name] = hp.quniform(spec.name, spec.low, spec.high, spec.step or 1)
        else:
            space[spec.name] = hp.uniform(spec.name, spec.low, spec.high)

    int_names = {spec.name for spec in param_specs if spec.kind == "int"}

    def _clean(raw_params: dict) -> dict:
        return {
            name: (int(value) if name in int_names else float(value))
            for name, value in raw_params.items()
        }

    def objective(raw_params: dict) -> float:
        try:
            score = objective_fn(_clean(raw_params))
        except Exception:
            score = float("-inf")
        # Hyperopt always minimizes — negate the score we want to maximize.
        return -score

    trials = Trials()
    try:
        import numpy as np

        rstate = np.random.default_rng(seed)
    except Exception:
        rstate = None

    fmin(
        objective,
        space,
        algo=tpe.suggest,
        max_evals=n_trials,
        trials=trials,
        rstate=rstate,
        show_progressbar=False,
    )

    hpo_trials: list[HpoTrial] = []
    best_value: float | None = None
    best_params: dict = {}
    for i, trial in enumerate(trials.trials):
        loss = trial["result"].get("loss")
        value = -loss if loss is not None else None
        raw_vals = {k: v[0] for k, v in trial["misc"]["vals"].items() if v}
        params = _clean(raw_vals) if raw_vals else {}
        hpo_trials.append(HpoTrial(trial=i, params=params, value=value))
        if value is not None and (best_value is None or value > best_value):
            best_value = value
            best_params = params

    return HpoResult(
        method="hyperopt:bayesian_tpe",
        best_params=best_params,
        best_value=best_value,
        trials=hpo_trials,
    )
