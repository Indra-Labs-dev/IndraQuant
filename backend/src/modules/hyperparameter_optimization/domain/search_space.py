"""Hyperparameter Optimization (docs/roadmap #8): the search-space and
result types shared by every optimization engine (Optuna, Hyperopt). Pure
data — no dependency on either optimization library here, so the engines
in `infrastructure/` stay swappable behind this same contract.
"""

from dataclasses import dataclass
from typing import Literal

ParamKind = Literal["int", "float"]


@dataclass(frozen=True)
class ParamSpec:
    name: str
    kind: ParamKind
    low: float
    high: float
    step: float | None = None


@dataclass(frozen=True)
class HpoTrial:
    trial: int
    params: dict[str, float]
    value: float | None


@dataclass(frozen=True)
class HpoResult:
    method: str
    best_params: dict[str, float]
    best_value: float | None
    trials: list[HpoTrial]
