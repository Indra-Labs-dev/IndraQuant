"""Rolling accuracy trend over a sequence of resolved predictions — the
pure signal behind "is the Prediction Engine actually improving?" (ADR-023).
"""


def rolling_accuracy_trend(correct_flags: list[bool], window: int = 20) -> list[float]:
    trend: list[float] = []
    running: list[int] = []
    for flag in correct_flags:
        running.append(1 if flag else 0)
        if len(running) > window:
            running.pop(0)
        trend.append(sum(running) / len(running))
    return trend
