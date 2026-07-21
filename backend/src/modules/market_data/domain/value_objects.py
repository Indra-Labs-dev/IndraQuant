from dataclasses import dataclass

SUPPORTED_TIMEFRAMES = ("1s", "5s", "30s", "1m", "5m", "15m", "1h", "4h", "1d")

_TIMEFRAME_SECONDS = {
    "1s": 1,
    "5s": 5,
    "30s": 30,
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "1h": 3_600,
    "4h": 14_400,
    "1d": 86_400,
}


@dataclass(frozen=True)
class Timeframe:
    value: str

    def __post_init__(self) -> None:
        if self.value not in SUPPORTED_TIMEFRAMES:
            raise ValueError(
                f"Unsupported timeframe '{self.value}'. "
                f"Supported: {', '.join(SUPPORTED_TIMEFRAMES)}"
            )

    @property
    def seconds(self) -> int:
        return _TIMEFRAME_SECONDS[self.value]
